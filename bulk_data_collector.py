#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
대량 데이터 수집 시스템
- 1년 이상의 과거 데이터 수집
- 배치 처리 및 오류 복구
- 데이터 품질 검증
"""

import os
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class BulkDataCollector:
    """대량 데이터 수집 클래스"""
    
    def __init__(self, kis_provider, cache_system, max_workers: int = 5):
        self.kis_provider = kis_provider
        self.cache_system = cache_system
        self.max_workers = max_workers
        self.collection_stats = {
            'total_symbols': 0,
            'successful_collections': 0,
            'failed_collections': 0,
            'total_records': 0,
            'start_time': None,
            'end_time': None
        }
    
    def collect_historical_data_bulk(self, symbols: List[str], days: int = 365) -> Dict[str, Any]:
        """대량 과거 데이터 수집"""
        logger.info(f"대량 데이터 수집 시작: {len(symbols)}개 종목, {days}일")
        self.collection_stats['start_time'] = datetime.now()
        self.collection_stats['total_symbols'] = len(symbols)
        
        results = {}
        failed_symbols = []
        
        # 병렬 처리로 데이터 수집
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 작업 제출
            future_to_symbol = {
                executor.submit(self._collect_single_symbol, symbol, days): symbol 
                for symbol in symbols
            }
            
            # 결과 처리
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    if result['success']:
                        results[symbol] = result['data']
                        self.collection_stats['successful_collections'] += 1
                        self.collection_stats['total_records'] += len(result['data'])
                        logger.info(f"✅ {symbol} 수집 완료: {len(result['data'])}건")
                    else:
                        failed_symbols.append(symbol)
                        self.collection_stats['failed_collections'] += 1
                        logger.warning(f"❌ {symbol} 수집 실패: {result['error']}")
                        
                except Exception as e:
                    failed_symbols.append(symbol)
                    self.collection_stats['failed_collections'] += 1
                    logger.error(f"❌ {symbol} 수집 오류: {e}")
        
        self.collection_stats['end_time'] = datetime.now()
        duration = self.collection_stats['end_time'] - self.collection_stats['start_time']
        
        # 결과 요약
        summary = {
            'total_symbols': len(symbols),
            'successful': len(results),
            'failed': len(failed_symbols),
            'success_rate': len(results) / len(symbols) * 100,
            'total_records': sum(len(data) for data in results.values()),
            'duration_seconds': duration.total_seconds(),
            'failed_symbols': failed_symbols
        }
        
        logger.info(f"대량 데이터 수집 완료: {summary}")
        return {
            'results': results,
            'summary': summary,
            'stats': self.collection_stats
        }
    
    def _collect_single_symbol(self, symbol: str, days: int) -> Dict[str, Any]:
        """단일 종목 데이터 수집"""
        try:
            # 캐시 확인
            if self.cache_system.is_data_fresh(symbol, max_age_days=1):
                cached_data = self.cache_system.get_cached_data(
                    symbol,
                    (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'),
                    datetime.now().strftime('%Y-%m-%d')
                )
                if cached_data is not None and not cached_data.empty:
                    return {
                        'success': True,
                        'data': cached_data,
                        'source': 'cache'
                    }
            
            # 실제 데이터 수집
            data = self.kis_provider.get_daily_price_history(symbol, days)
            
            if data is not None and not data.empty:
                # 데이터 정리
                data['date'] = pd.to_datetime(data['date'])
                data = data.sort_values('date').reset_index(drop=True)
                
                # 데이터 품질 검증
                quality_score = self._validate_data_quality(data)
                if quality_score < 0.5:
                    logger.warning(f"데이터 품질 낮음 {symbol}: {quality_score:.2f}")
                
                # 캐시 저장
                self.cache_system.cache_data(symbol, data)
                
                return {
                    'success': True,
                    'data': data,
                    'source': 'api',
                    'quality_score': quality_score
                }
            else:
                return {
                    'success': False,
                    'error': '데이터 없음',
                    'data': None
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def _validate_data_quality(self, data: pd.DataFrame) -> float:
        """데이터 품질 검증"""
        try:
            if data.empty:
                return 0.0
            
            score = 1.0
            
            # 필수 컬럼 확인
            required_columns = ['date', 'close']
            missing_columns = [col for col in required_columns if col not in data.columns]
            if missing_columns:
                score -= 0.3
            
            # 누락 데이터 체크
            missing_ratio = data.isnull().sum().sum() / (len(data) * len(data.columns))
            score -= missing_ratio * 0.3
            
            # 가격 데이터 유효성
            if 'close' in data.columns:
                negative_prices = (data['close'] <= 0).sum()
                score -= (negative_prices / len(data)) * 0.4
            
            # 시간 연속성
            if len(data) > 1:
                data_sorted = data.sort_values('date')
                date_diff = data_sorted['date'].diff().dt.days
                gaps = (date_diff > 7).sum()  # 7일 이상 간격
                score -= (gaps / len(data)) * 0.2
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"데이터 품질 검증 실패: {e}")
            return 0.0
    
    def collect_top_kospi_stocks(self, count: int = 100, days: int = 365) -> Dict[str, Any]:
        """상위 KOSPI 종목 데이터 수집"""
        try:
            # KOSPI 마스터 데이터 로드
            kospi_file = 'kospi_code.xlsx'
            if not os.path.exists(kospi_file):
                logger.error(f"KOSPI 마스터 파일 없음: {kospi_file}")
                return {'success': False, 'error': 'KOSPI 마스터 파일 없음'}
            
            df = pd.read_excel(kospi_file)
            
            # 상위 종목 선정 (시가총액 기준)
            if '시가총액' in df.columns:
                top_stocks = df.nlargest(count, '시가총액')
            else:
                # 시가총액 컬럼이 없으면 상위 N개 선택
                top_stocks = df.head(count)
            
            symbols = top_stocks['단축코드'].tolist()
            logger.info(f"상위 {count}개 KOSPI 종목 선정: {len(symbols)}개")
            
            # 데이터 수집
            return self.collect_historical_data_bulk(symbols, days)
            
        except Exception as e:
            logger.error(f"상위 KOSPI 종목 수집 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    def retry_failed_collections(self, failed_symbols: List[str], days: int = 365) -> Dict[str, Any]:
        """실패한 종목 재수집"""
        logger.info(f"실패한 종목 재수집 시작: {len(failed_symbols)}개")
        
        # 재시도 간격 (API 제한 고려)
        time.sleep(1)
        
        return self.collect_historical_data_bulk(failed_symbols, days)
    
    def save_collection_report(self, results: Dict[str, Any], filename: str = None):
        """수집 결과 보고서 저장"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"data_collection_report_{timestamp}.json"
            
            report = {
                'collection_time': datetime.now().isoformat(),
                'summary': results.get('summary', {}),
                'stats': results.get('stats', {}),
                'failed_symbols': results.get('summary', {}).get('failed_symbols', [])
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"수집 보고서 저장: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"수집 보고서 저장 실패: {e}")
            return None

def main():
    """테스트 함수"""
    from kis_data_provider import KISDataProvider
    from historical_data_cache import HistoricalDataCache
    
    # 초기화
    kis_provider = KISDataProvider()
    cache_system = HistoricalDataCache()
    collector = BulkDataCollector(kis_provider, cache_system, max_workers=3)
    
    # 테스트 종목
    test_symbols = ['005930', '000660', '373220', '207940', '012450']
    
    # 데이터 수집
    results = collector.collect_historical_data_bulk(test_symbols, days=30)
    
    # 결과 출력
    print(f"\n수집 결과:")
    print(f"성공: {results['summary']['successful']}개")
    print(f"실패: {results['summary']['failed']}개")
    print(f"성공률: {results['summary']['success_rate']:.1f}%")
    print(f"총 레코드: {results['summary']['total_records']}건")
    
    # 보고서 저장
    collector.save_collection_report(results)

if __name__ == "__main__":
    main()


