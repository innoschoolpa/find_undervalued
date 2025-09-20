#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
대량 데이터 수집 실행기
- 1년 이상의 과거 데이터 수집
- 상위 KOSPI 종목 대상
- 데이터 품질 검증 및 저장
"""

import os
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import logging
from pathlib import Path
import json

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def collect_bulk_historical_data():
    """대량 과거 데이터 수집 실행"""
    try:
        from kis_data_provider import KISDataProvider
        from historical_data_cache import HistoricalDataCache
        from bulk_data_collector import BulkDataCollector
        
        # 초기화
        kis_provider = KISDataProvider()
        cache_system = HistoricalDataCache()
        collector = BulkDataCollector(kis_provider, cache_system, max_workers=3)
        
        logger.info("🚀 대량 과거 데이터 수집 시작")
        
        # 1. 상위 KOSPI 종목 데이터 수집 (1년)
        logger.info("📊 상위 50개 KOSPI 종목 데이터 수집 (365일)")
        results = collector.collect_top_kospi_stocks(count=50, days=365)
        
        if results.get('success', True):  # success가 없으면 기본적으로 성공으로 간주
            summary = results.get('summary', {})
            logger.info(f"✅ 수집 완료: {summary.get('successful', 0)}개 성공, {summary.get('failed', 0)}개 실패")
            logger.info(f"📈 총 레코드: {summary.get('total_records', 0)}건")
            logger.info(f"⏱️ 소요 시간: {summary.get('duration_seconds', 0):.1f}초")
            
            # 2. 실패한 종목 재수집
            failed_symbols = summary.get('failed_symbols', [])
            if failed_symbols:
                logger.info(f"🔄 실패한 종목 재수집: {len(failed_symbols)}개")
                retry_results = collector.retry_failed_collections(failed_symbols, days=365)
                
                retry_summary = retry_results.get('summary', {})
                logger.info(f"✅ 재수집 완료: {retry_summary.get('successful', 0)}개 성공")
            
            # 3. 수집 보고서 저장
            report_file = collector.save_collection_report(results)
            if report_file:
                logger.info(f"📄 수집 보고서 저장: {report_file}")
            
            # 4. 캐시 상태 확인
            cache_status = cache_system.get_cache_status()
            logger.info(f"💾 캐시 상태: {cache_status.get('total_symbols', 0)}개 종목, {cache_status.get('total_records', 0)}건")
            
            return True
        else:
            logger.error(f"❌ 데이터 수집 실패: {results.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 대량 데이터 수집 오류: {e}")
        return False

def collect_specific_symbols():
    """특정 종목 데이터 수집"""
    try:
        from kis_data_provider import KISDataProvider
        from historical_data_cache import HistoricalDataCache
        from bulk_data_collector import BulkDataCollector
        
        # 초기화
        kis_provider = KISDataProvider()
        cache_system = HistoricalDataCache()
        collector = BulkDataCollector(kis_provider, cache_system, max_workers=2)
        
        # 주요 종목 리스트
        major_symbols = [
            '005930',  # 삼성전자
            '000660',  # SK하이닉스
            '373220',  # LG에너지솔루션
            '207940',  # 삼성바이오로직스
            '012450',  # 한화에어로스페이스
            '006400',  # 삼성SDI
            '035420',  # NAVER
            '051910',  # LG화학
            '068270',  # 셀트리온
            '323410',  # 카카오뱅크
        ]
        
        logger.info(f"🎯 주요 종목 데이터 수집: {len(major_symbols)}개")
        
        # 2년 데이터 수집
        results = collector.collect_historical_data_bulk(major_symbols, days=730)
        
        summary = results.get('summary', {})
        logger.info(f"✅ 수집 완료: {summary.get('successful', 0)}개 성공")
        logger.info(f"📈 총 레코드: {summary.get('total_records', 0)}건")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 특정 종목 수집 오류: {e}")
        return False

def validate_data_quality():
    """데이터 품질 검증"""
    try:
        from historical_data_cache import HistoricalDataCache
        
        cache_system = HistoricalDataCache()
        status = cache_system.get_cache_status()
        
        logger.info("🔍 데이터 품질 검증 시작")
        
        # 각 종목별 데이터 품질 확인
        recent_updates = status.get('recent_updates', [])
        
        for update in recent_updates[:10]:  # 상위 10개만 확인
            symbol = update['symbol']
            record_count = update['record_count']
            
            # 데이터 조회
            data = cache_system.get_cached_data(symbol, '2024-01-01', '2024-12-31')
            
            if data is not None and not data.empty:
                # 데이터 품질 점수 계산
                quality_score = calculate_data_quality_score(data)
                logger.info(f"📊 {symbol}: {len(data)}건, 품질 {quality_score:.2f}")
            else:
                logger.warning(f"⚠️ {symbol}: 데이터 없음")
        
        logger.info("✅ 데이터 품질 검증 완료")
        return True
        
    except Exception as e:
        logger.error(f"❌ 데이터 품질 검증 오류: {e}")
        return False

def calculate_data_quality_score(data: pd.DataFrame) -> float:
    """데이터 품질 점수 계산"""
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
        logger.error(f"데이터 품질 점수 계산 실패: {e}")
        return 0.0

def main():
    """메인 실행 함수"""
    logger.info("🚀 대량 과거 데이터 수집 시스템 시작")
    
    # 1. 주요 종목 데이터 수집
    logger.info("\n=== 1단계: 주요 종목 데이터 수집 ===")
    if collect_specific_symbols():
        logger.info("✅ 주요 종목 수집 완료")
    else:
        logger.error("❌ 주요 종목 수집 실패")
        return
    
    # 2. 대량 데이터 수집
    logger.info("\n=== 2단계: 대량 데이터 수집 ===")
    if collect_bulk_historical_data():
        logger.info("✅ 대량 데이터 수집 완료")
    else:
        logger.error("❌ 대량 데이터 수집 실패")
        return
    
    # 3. 데이터 품질 검증
    logger.info("\n=== 3단계: 데이터 품질 검증 ===")
    if validate_data_quality():
        logger.info("✅ 데이터 품질 검증 완료")
    else:
        logger.error("❌ 데이터 품질 검증 실패")
        return
    
    logger.info("\n🎉 모든 데이터 수집 작업 완료!")

if __name__ == "__main__":
    main()


