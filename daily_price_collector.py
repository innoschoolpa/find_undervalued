#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
일별 시세 수집 스케줄러

목적:
- 매일 장마감 후 자동 시세 수집
- 증분 업데이트 (변경된 것만)
- 섹터 통계 자동 재계산

실행:
- python daily_price_collector.py  (백그라운드 실행)
- 스케줄: 매일 15:40 (평일)
"""

import logging
import time
from datetime import date, datetime
from typing import List, Dict, Any
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from db_cache_manager import DBCacheManager
from kis_data_provider import KISDataProvider
from config_manager import ConfigManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/daily_collector.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class DailyPriceCollector:
    """일별 시세 수집기"""
    
    def __init__(self):
        """초기화"""
        self.db = DBCacheManager()
        
        # KIS Data Provider 초기화
        config = ConfigManager()
        self.data_provider = KISDataProvider(config)
        
        logger.info("✅ DailyPriceCollector 초기화 완료")
    
    def collect_all_stocks(self, max_stocks: int = 1000) -> Dict[str, Any]:
        """
        전체 종목 시세 수집
        
        Args:
            max_stocks: 수집할 최대 종목 수
        
        Returns:
            수집 결과
        """
        logger.info(f"📊 일별 시세 수집 시작: {date.today()} ({max_stocks}개 종목)")
        
        start_time = time.time()
        results = {
            'date': date.today(),
            'attempted': 0,
            'succeeded': 0,
            'failed': 0,
            'api_calls': 0,
            'errors': []
        }
        
        try:
            # 1. 전체 종목 리스트 조회
            logger.info("  1단계: 종목 리스트 조회")
            all_stocks = self.data_provider.get_stock_universe(max_count=max_stocks)
            
            if not all_stocks:
                logger.error("❌ 종목 리스트 조회 실패")
                return results
            
            results['attempted'] = len(all_stocks)
            logger.info(f"  ✅ {len(all_stocks)}개 종목 조회 완료")
            
            # 2. 스냅샷 데이터 변환
            logger.info("  2단계: 스냅샷 데이터 변환")
            snapshots = []
            
            for code, data in all_stocks.items():
                try:
                    # 섹터 정규화 (ValueStockFinder의 로직 사용)
                    sector_raw = data.get('sector', '기타')
                    sector_normalized = self._normalize_sector_name(sector_raw)
                    
                    snapshot = {
                        'code': code,
                        'name': data.get('name'),
                        'sector': sector_raw,
                        'sector_normalized': sector_normalized,
                        'price': data.get('price') or data.get('close_price'),
                        'open_price': data.get('open_price'),
                        'high_price': data.get('high_price'),
                        'low_price': data.get('low_price'),
                        'volume': data.get('volume'),
                        'market_cap': data.get('market_cap'),
                        'per': data.get('per'),
                        'pbr': data.get('pbr'),
                        'roe': data.get('roe'),
                        'debt_ratio': data.get('debt_ratio'),
                        'dividend_yield': data.get('dividend_yield'),
                        'data_source': 'KIS'
                    }
                    
                    snapshots.append(snapshot)
                    results['succeeded'] += 1
                
                except Exception as e:
                    logger.error(f"  ❌ {code} 변환 실패: {e}")
                    results['failed'] += 1
                    results['errors'].append(f"{code}: {e}")
            
            # 3. DB 저장
            logger.info(f"  3단계: DB 저장 ({len(snapshots)}개)")
            saved = self.db.save_snapshots(snapshots, snapshot_date=date.today())
            logger.info(f"  ✅ 저장 완료: {saved}개")
            
            # 4. 섹터 통계 재계산
            logger.info("  4단계: 섹터 통계 재계산")
            sector_stats = self.db.compute_sector_stats(snapshot_date=date.today())
            logger.info(f"  ✅ 섹터 통계: {len(sector_stats)}개")
            
            # 5. 수집 로그 기록
            duration = time.time() - start_time
            results['duration_seconds'] = duration
            results['api_calls'] = len(all_stocks)  # 실제로는 더 많을 수 있음
            
            self._log_collection(results)
            
            logger.info(f"✅ 일별 시세 수집 완료: {results['succeeded']}/{results['attempted']}개 "
                       f"(소요: {duration:.1f}초)")
        
        except Exception as e:
            logger.error(f"❌ 시세 수집 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
            results['errors'].append(str(e))
        
        return results
    
    def collect_stale_stocks(self, max_age_days: int = 1) -> Dict[str, Any]:
        """
        증분 업데이트 (오래된 종목만)
        
        Args:
            max_age_days: 최대 경과 일수
        
        Returns:
            수집 결과
        """
        logger.info(f"📊 증분 업데이트 시작: {date.today()}")
        
        start_time = time.time()
        results = {
            'date': date.today(),
            'attempted': 0,
            'succeeded': 0,
            'failed': 0,
            'api_calls': 0,
            'errors': []
        }
        
        try:
            # 1. 업데이트 필요한 종목 조회
            stale_codes = self.db.get_stale_stocks(max_age_days=max_age_days)
            
            if not stale_codes:
                logger.info("✅ 모든 종목 최신 상태 (증분 업데이트 불필요)")
                return results
            
            results['attempted'] = len(stale_codes)
            logger.info(f"  업데이트 대상: {len(stale_codes)}개")
            
            # 2. API 호출하여 데이터 수집
            snapshots = []
            for code in stale_codes:
                try:
                    # KIS API 호출 (개별 종목)
                    stock_data = self.data_provider.get_stock_data(code)
                    
                    if stock_data:
                        snapshot = {
                            'code': code,
                            'name': stock_data.get('name'),
                            'sector': stock_data.get('sector'),
                            'sector_normalized': self._normalize_sector_name(stock_data.get('sector', '기타')),
                            'price': stock_data.get('price'),
                            'per': stock_data.get('per'),
                            'pbr': stock_data.get('pbr'),
                            'roe': stock_data.get('roe'),
                        }
                        snapshots.append(snapshot)
                        results['succeeded'] += 1
                    else:
                        results['failed'] += 1
                
                except Exception as e:
                    logger.error(f"  ❌ {code} 수집 실패: {e}")
                    results['failed'] += 1
                    results['errors'].append(f"{code}: {e}")
            
            # 3. DB 저장
            if snapshots:
                saved = self.db.save_snapshots(snapshots)
                logger.info(f"  ✅ 저장 완료: {saved}개")
            
            # 4. 섹터 통계 재계산
            sector_stats = self.db.compute_sector_stats()
            logger.info(f"  ✅ 섹터 통계: {len(sector_stats)}개")
            
            duration = time.time() - start_time
            results['duration_seconds'] = duration
            results['api_calls'] = len(stale_codes)
            
            logger.info(f"✅ 증분 업데이트 완료: {results['succeeded']}/{results['attempted']}개 "
                       f"(소요: {duration:.1f}초)")
        
        except Exception as e:
            logger.error(f"❌ 증분 업데이트 실패: {e}")
            results['errors'].append(str(e))
        
        return results
    
    def _normalize_sector_name(self, sector: str) -> str:
        """
        섹터명 정규화 (ValueStockFinder와 동일한 로직)
        
        Args:
            sector: 원본 섹터명
        
        Returns:
            정규화된 섹터명
        """
        if not sector or sector.strip() == '':
            return '기타분야'
        
        s = sector.strip().lower()
        
        # 키워드 매칭 (길이 순 정렬 - 구체적인 것 우선)
        mappings = [
            (['전기', '전자', '반도체', '디스플레이'], '전기전자'),
            (['에너지', '화학', '정유', '석유'], '에너지/화학'),
            (['자동차', '운송', '조선', '항공'], '운송장비'),
            (['건설', '건축', '토목'], '건설'),
            (['금융', '은행', '보험', '증권'], '금융서비스'),
        ]
        
        for keywords, normalized in mappings:
            if any(kw in s for kw in keywords):
                return normalized
        
        return '기타분야'
    
    def _log_collection(self, results: Dict[str, Any]):
        """수집 로그 기록"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO collection_log (
                        collection_date,
                        stocks_attempted,
                        stocks_succeeded,
                        stocks_failed,
                        api_calls,
                        duration_seconds,
                        error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    results['date'],
                    results['attempted'],
                    results['succeeded'],
                    results['failed'],
                    results.get('api_calls', 0),
                    results.get('duration_seconds', 0),
                    '\n'.join(results.get('errors', [])[:10])  # 최대 10개 오류만
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"❌ 수집 로그 기록 실패: {e}")


def run_daily_collection():
    """매일 자동 실행되는 함수"""
    logger.info("=" * 60)
    logger.info(f"🔄 일별 시세 수집 시작: {datetime.now()}")
    logger.info("=" * 60)
    
    try:
        collector = DailyPriceCollector()
        results = collector.collect_all_stocks(max_stocks=1000)
        
        logger.info("=" * 60)
        logger.info(f"✅ 수집 완료: {results['succeeded']}/{results['attempted']}개")
        logger.info(f"⏱️  소요 시간: {results.get('duration_seconds', 0):.1f}초")
        logger.info(f"📞 API 호출: {results.get('api_calls', 0)}회")
        if results.get('failed', 0) > 0:
            logger.warning(f"⚠️  실패: {results['failed']}개")
        logger.info("=" * 60)
    
    except Exception as e:
        logger.error(f"❌ 일별 수집 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())


def main():
    """메인 함수 (스케줄러 시작)"""
    logger.info("=" * 60)
    logger.info("📊 일별 시세 수집 스케줄러 시작")
    logger.info("=" * 60)
    logger.info("스케줄: 매일 15:40 (평일)")
    logger.info("=" * 60)
    
    # 스케줄러 생성
    scheduler = BlockingScheduler()
    
    # 매일 15:40 (평일) 실행
    scheduler.add_job(
        run_daily_collection,
        trigger=CronTrigger(
            day_of_week='mon-fri',
            hour=15,
            minute=40
        ),
        id='daily_price_collection',
        name='일별 시세 수집',
        replace_existing=True
    )
    
    logger.info("✅ 스케줄러 등록 완료")
    logger.info("다음 실행 시간:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.name}: {job.next_run_time}")
    
    try:
        # 스케줄러 시작
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 스케줄러 종료")


if __name__ == "__main__":
    # 즉시 실행 테스트 (옵션)
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--now':
        logger.info("📊 즉시 실행 모드")
        run_daily_collection()
    else:
        # 정상 스케줄러 모드
        main()

