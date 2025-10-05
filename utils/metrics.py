"""Metrics collection and management utilities."""

from __future__ import annotations

import logging
from threading import RLock
from time import monotonic as _monotonic
from typing import Any, Dict, List

from .env_utils import safe_env_float


class MetricsCollector:
    """시스템 메트릭 수집 및 관리"""
    
    def __init__(self):
        self.metrics = {
            'api_calls': {'total': 0, 'success': 0, 'error': 0},
            'cache_hits': {'price': 0, 'financial': 0, 'sector': 0},
            'cache_misses': {'price': 0, 'financial': 0, 'sector': 0},
            'analysis_duration': {'total': 0, 'count': 0, 'avg': 0},
            'sector_evaluation': {'total': 0, 'count': 0, 'avg': 0},
            'stocks_analyzed': 0,
            'errors_by_type': {},
            # ✅ 섹터 피어 샘플 크기 메트릭 추가
            'sector_sample_insufficient': 0,
            # ✅ 메트릭 개선: missing 필드 카운터 추가
            'missing_financial_fields': 0,
            # ✅ API 재시도 중간 실패 카운터 추가 (이중 집계 방지)
            'api_retry_attempt_errors': 0,
            # ✅ PER/PBR 스킵 메트릭 추가
            'valuation_skips': {'per_epsmin': 0, 'pbr_bpsmin': 0},
            # ✅ 빈 페이로드 메트릭 추가
            'empty_price_payloads': 0,
            # ✅ 품질 필터 메트릭 추가
            'quality_filter_rejections': 0,
            'quality_filter_rejection_reasons': {},
            # ✅ 리스크 제약 메트릭 추가
            'risk_constraint_violations': 0,
            'risk_constraint_violation_reasons': {},
            # ✅ 점수 계산 메트릭 추가
            'score_calculations': {'total': 0, 'errors': 0},
            'start_time': _monotonic()
        }
        # Histogram buckets for duration analysis (seconds)
        # ✅ 메트릭 개선: p95 백분위 추가 (SRE가 주로 사용)
        # 운영 기준: p90이 5초, p95가 10초 넘으면 경고 (SLO)
        self.duration_buckets = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        self.analysis_histogram = [0] * (len(self.duration_buckets) + 1)  # +1 for overflow
        self.sector_histogram = [0] * (len(self.duration_buckets) + 1)
        self.lock = RLock()
    
    def record_api_call(self, success: bool, error_type: str = None):
        """API 호출 기록 (최종 결과만)
        
        Note: This should only be called for final API results. 
        Do not call this when _with_retries has already recorded the final failure.
        """
        with self.lock:
            self.metrics['api_calls']['total'] += 1
            if success:
                self.metrics['api_calls']['success'] += 1
            else:
                self.metrics['api_calls']['error'] += 1
                if error_type:
                    self.metrics['errors_by_type'][error_type] = self.metrics['errors_by_type'].get(error_type, 0) + 1

    def record_api_attempt_error(self, error_type: str = None):
        """API 재시도 중간 실패 기록 (이중 집계 방지)"""
        with self.lock:
            self.metrics['api_retry_attempt_errors'] += 1
            if error_type:
                self.metrics['errors_by_type'][error_type] = self.metrics['errors_by_type'].get(error_type, 0) + 1

    def record_flag_error(self, error_type: str):
        """플래그 에러 기록 (스레드 안전)"""
        with self.lock:
            self.metrics['errors_by_type'][error_type] = \
                self.metrics['errors_by_type'].get(error_type, 0) + 1

    def record_valuation_skip(self, kind: str):
        """밸류에이션 스킵 기록 (스레드 안전)"""
        with self.lock:
            self.metrics['valuation_skips'][kind] = \
                self.metrics['valuation_skips'].get(kind, 0) + 1
    
    def record_cache_hit(self, cache_type: str):
        """캐시 히트 기록"""
        with self.lock:
            self.metrics['cache_hits'].setdefault(cache_type, 0)
            self.metrics['cache_hits'][cache_type] += 1
    
    def record_cache_miss(self, cache_type: str):
        """캐시 미스 기록"""
        with self.lock:
            self.metrics['cache_misses'].setdefault(cache_type, 0)
            self.metrics['cache_misses'][cache_type] += 1
    
    def record_analysis_duration(self, duration: float):
        """분석 소요 시간 기록"""
        with self.lock:
            self.metrics['analysis_duration']['total'] += duration
            self.metrics['analysis_duration']['count'] += 1
            self.metrics['analysis_duration']['avg'] = (
                self.metrics['analysis_duration']['total'] / self.metrics['analysis_duration']['count']
            )
            # Record in histogram
            bucket_idx = self._find_bucket(duration, self.duration_buckets)
            self.analysis_histogram[bucket_idx] += 1
    
    def record_sector_evaluation(self, duration: float):
        """섹터 평가 소요 시간 기록"""
        with self.lock:
            self.metrics['sector_evaluation']['total'] += duration
            self.metrics['sector_evaluation']['count'] += 1
            self.metrics['sector_evaluation']['avg'] = (
                self.metrics['sector_evaluation']['total'] / self.metrics['sector_evaluation']['count']
            )
            # Record in histogram
            bucket_idx = self._find_bucket(duration, self.duration_buckets)
            self.sector_histogram[bucket_idx] += 1
    
    def record_sector_sample_insufficient(self, sector_name: str = None):
        """섹터 피어 표본 부족 기록"""
        with self.lock:
            self.metrics['sector_sample_insufficient'] += 1
            if sector_name:
                if 'sector_sample_insufficient_by_sector' not in self.metrics:
                    self.metrics['sector_sample_insufficient_by_sector'] = {}
                self.metrics['sector_sample_insufficient_by_sector'][sector_name] = \
                    self.metrics['sector_sample_insufficient_by_sector'].get(sector_name, 0) + 1
    
    def record_missing_financial_fields(self, count: int = 1):
        """✅ missing 재무 필드 카운터: 데이터 품질 드리프트 모니터링"""
        with self.lock:
            self.metrics['missing_financial_fields'] += count
    
    def get_missing_financial_fields_count(self) -> int:
        """결측 재무 필드 총 개수 반환"""
        with self.lock:
            return self.metrics['missing_financial_fields']
    
    def record_quality_filter_rejection(self, symbol: str, rejection_reasons: List[str]):
        """품질 필터 거부 기록"""
        with self.lock:
            self.metrics['quality_filter_rejections'] += 1
            for reason in rejection_reasons:
                self.metrics['quality_filter_rejection_reasons'][reason] = \
                    self.metrics['quality_filter_rejection_reasons'].get(reason, 0) + 1
    
    def record_risk_constraint_violation(self, symbol: str, violation_reasons: List[str]):
        """리스크 제약 위반 기록"""
        with self.lock:
            self.metrics['risk_constraint_violations'] += 1
            for reason in violation_reasons:
                self.metrics['risk_constraint_violation_reasons'][reason] = \
                    self.metrics['risk_constraint_violation_reasons'].get(reason, 0) + 1
    
    def record_stocks_analyzed(self, count: int):
        """분석된 종목 수 기록"""
        with self.lock:
            self.metrics['stocks_analyzed'] += count
    
    def get_cache_hit_rate(self, cache_type: str) -> float:
        """캐시 히트율 계산"""
        with self.lock:
            hits = self.metrics['cache_hits'].get(cache_type, 0)
            misses = self.metrics['cache_misses'].get(cache_type, 0)
            total = hits + misses
            return (hits / total * 100.0) if total > 0 else 0.0
    
    def get_api_success_rate(self) -> float:
        """API 성공률 계산"""
        with self.lock:
            total = self.metrics['api_calls']['total']
            success = self.metrics['api_calls']['success']
            return (success / total * 100) if total > 0 else 0.0
    
    def _find_bucket(self, value: float, buckets: List[float]) -> int:
        """Find histogram bucket index for a value"""
        for i, bucket in enumerate(buckets):
            if value <= bucket:
                return i
        return len(buckets)  # Overflow bucket
    
    def get_percentiles(self, histogram: List[int], buckets: List[float], percentile: float) -> float:
        """Calculate percentile from histogram"""
        total = sum(histogram)
        if total == 0:
            return 0.0
        
        target = total * (percentile / 100.0)
        cumulative = 0
        
        for i, count in enumerate(histogram):
            cumulative += count
            if cumulative >= target:
                if i < len(buckets):
                    return buckets[i]
                else:
                    return buckets[-1] * 2  # Estimate for overflow
        return buckets[-1] * 2
    
    def get_summary(self) -> Dict[str, Any]:
        """메트릭 요약 반환"""
        with self.lock:
            # SLO 경고 체크
            p90_analysis = self.get_percentiles(self.analysis_histogram, self.duration_buckets, 90)
            p95_analysis = self.get_percentiles(self.analysis_histogram, self.duration_buckets, 95)
            p90_sector = self.get_percentiles(self.sector_histogram, self.duration_buckets, 90)
            p95_sector = self.get_percentiles(self.sector_histogram, self.duration_buckets, 95)
            
            # SLO 임계값 (환경변수로 조정 가능)
            analysis_p90_threshold = safe_env_float("ANALYSIS_P90_THRESHOLD", 5.0)
            analysis_p95_threshold = safe_env_float("ANALYSIS_P95_THRESHOLD", 10.0)
            sector_p90_threshold = safe_env_float("SECTOR_P90_THRESHOLD", 2.0)
            sector_p95_threshold = safe_env_float("SECTOR_P95_THRESHOLD", 5.0)
            
            # 경고 플래그
            analysis_slow = p90_analysis > analysis_p90_threshold or p95_analysis > analysis_p95_threshold
            sector_slow = p90_sector > sector_p90_threshold or p95_sector > sector_p95_threshold
            
            if analysis_slow or sector_slow:
                logging.warning(f"[SLO] Performance degradation detected: "
                              f"analysis_p90={p90_analysis:.2f}s, analysis_p95={p95_analysis:.2f}s, "
                              f"sector_p90={p90_sector:.2f}s, sector_p95={p95_sector:.2f}s")
            
            return {
                'api_calls': self.metrics['api_calls'].copy(),
                'cache_hits': self.metrics['cache_hits'].copy(),
                'cache_misses': self.metrics['cache_misses'].copy(),
                'analysis_duration': self.metrics['analysis_duration'].copy(),
                'sector_evaluation': self.metrics['sector_evaluation'].copy(),
                'stocks_analyzed': self.metrics['stocks_analyzed'],
                'errors_by_type': self.metrics['errors_by_type'].copy(),
                'sector_sample_insufficient': self.metrics['sector_sample_insufficient'],
                'missing_financial_fields': self.metrics['missing_financial_fields'],
                'api_retry_attempt_errors': self.metrics['api_retry_attempt_errors'],
                'valuation_skips': self.metrics['valuation_skips'].copy(),
                'empty_price_payloads': self.metrics['empty_price_payloads'],
                'quality_filter_rejections': self.metrics['quality_filter_rejections'],
                'quality_filter_rejection_reasons': self.metrics['quality_filter_rejection_reasons'].copy(),
                'risk_constraint_violations': self.metrics['risk_constraint_violations'],
                'risk_constraint_violation_reasons': self.metrics['risk_constraint_violation_reasons'].copy(),
                'performance_percentiles': {
                    'analysis_p90': p90_analysis,
                    'analysis_p95': p95_analysis,
                    'sector_p90': p90_sector,
                    'sector_p95': p95_sector
                },
                'slo_warnings': {
                    'analysis_slow': analysis_slow,
                    'sector_slow': sector_slow
                },
                'uptime_seconds': _monotonic() - self.metrics['start_time']
            }

    def record_api_errors(self, symbol: str, error_type: str = "unknown"):
        """API 오류 기록"""
        with self.lock:
            self.metrics['api_calls']['error'] += 1
            
            if error_type not in self.metrics['errors_by_type']:
                self.metrics['errors_by_type'][error_type] = 0
            self.metrics['errors_by_type'][error_type] += 1
            
            logging.error(f"API 오류 기록 - 종목: {symbol}, 오류 유형: {error_type}")

    def record_api_success(self, symbol: str):
        """API 성공 기록"""
        with self.lock:
            self.metrics['api_calls']['success'] += 1
            logging.debug(f"API 성공 기록 - 종목: {symbol}")

    def record_api_call(self, symbol: str):
        """API 호출 기록"""
        with self.lock:
            self.metrics['api_calls']['total'] += 1
            logging.debug(f"API 호출 기록 - 종목: {symbol}")

    def record_api_calls(self, symbol: str):
        """API 호출 기록 (복수형 - 호환성)"""
        self.record_api_call(symbol)

    def record_cache_hits(self, count: int):
        """캐시 히트 기록"""
        with self.lock:
            self.metrics['cache_hits']['price'] += count
            logging.debug(f"캐시 히트 기록: {count}회")

    def record_cache_misses(self, count: int):
        """캐시 미스 기록"""
        with self.lock:
            self.metrics['cache_misses']['price'] += count
            logging.debug(f"캐시 미스 기록: {count}회")

    def record_analysis_duration(self, duration: float):
        """분석 소요 시간 기록"""
        with self.lock:
            self.metrics['analysis_duration']['total'] += duration
            self.metrics['analysis_duration']['count'] += 1
            self.metrics['analysis_duration']['avg'] = (
                self.metrics['analysis_duration']['total'] / self.metrics['analysis_duration']['count']
            )
            
            # 히스토그램 업데이트
            bucket_index = 0
            for i, threshold in enumerate(self.duration_buckets):
                if duration <= threshold:
                    bucket_index = i
                    break
            else:
                bucket_index = len(self.duration_buckets)  # overflow bucket
            
            self.analysis_histogram[bucket_index] += 1
            logging.debug(f"분석 소요 시간 기록: {duration:.3f}초")

    def _increment_analysis_count(self):
        """분석 카운트 증가"""
        with self.lock:
            self.metrics['stocks_analyzed'] += 1

    def record_score_calculations(self, count: int):
        """점수 계산 기록"""
        with self.lock:
            self.metrics['score_calculations']['total'] += count
            logging.debug(f"점수 계산 기록: {count}회")

    def record_score_calculation_errors(self, count: int):
        """점수 계산 오류 기록"""
        with self.lock:
            self.metrics['score_calculations']['errors'] += count
            logging.debug(f"점수 계산 오류 기록: {count}회")



