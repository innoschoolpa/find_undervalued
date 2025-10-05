"""
메트릭 수집 및 관리 모듈

시스템의 성능, 에러, 캐시 등의 메트릭을 수집하고 관리합니다.
"""

import logging
import time
from threading import RLock
from typing import Any, Dict, List, Optional

from logging_utils import ErrorType


def _monotonic():
    """현재 시간을 monotonic clock으로 반환"""
    return time.monotonic()


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
            'empty_payloads': {'price': 0, 'financial': 0},
            # ✅ 품질 필터 및 리스크 제약 메트릭 추가
            'quality_filter_rejections': 0,
            'quality_filter_rejection_reasons': {},
            'risk_constraint_violations': 0,
            'risk_constraint_violation_reasons': {},
            # ✅ 시작 시간 기록
            'start_time': _monotonic()
        }
        
        # 히스토그램 버킷 정의 (초 단위)
        self.duration_buckets = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0]
        
        # 히스토그램 데이터
        self.analysis_histogram = [0] * (len(self.duration_buckets) + 1)
        self.sector_histogram = [0] * (len(self.duration_buckets) + 1)
        
        # 스레드 안전성을 위한 락
        self.lock = RLock()
    
    def record_api_call(self, success: bool = True, error_type: str = None):
        """API 호출 기록"""
        with self.lock:
            self.metrics['api_calls']['total'] += 1
            if success:
                self.metrics['api_calls']['success'] += 1
            else:
                self.metrics['api_calls']['error'] += 1
                if error_type:
                    self.metrics['errors_by_type'][error_type] = \
                        self.metrics['errors_by_type'].get(error_type, 0) + 1
    
    def record_api_retry_attempt_error(self):
        """API 재시도 중간 실패 기록 (최종 성공/실패와 별도 집계)"""
        with self.lock:
            self.metrics['api_retry_attempt_errors'] += 1
    
    def record_valuation_skip(self, skip_type: str):
        """밸류에이션 스킵 기록 (PER/PBR 등)"""
        with self.lock:
            if skip_type in self.metrics['valuation_skips']:
                self.metrics['valuation_skips'][skip_type] += 1
    
    def record_empty_payload(self, payload_type: str):
        """빈 페이로드 기록"""
        with self.lock:
            if payload_type in self.metrics['empty_payloads']:
                self.metrics['empty_payloads'][payload_type] += 1
    
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
            p90 = self.get_percentiles(self.analysis_histogram, self.duration_buckets, 90)
            p95 = self.get_percentiles(self.analysis_histogram, self.duration_buckets, 95)
            if p90 > 5.0:
                logging.warning(f"[SLO] 분석 p90 {p90:.1f}s > 5s")
            if p95 > 10.0:
                logging.warning(f"[SLO] 분석 p95 {p95:.1f}s > 10s")
            
            # 상위 카테고리별 에러 집계 (SRE 대시보드용)
            errors_by_category = {}
            for error_type, count in self.metrics['errors_by_type'].items():
                category = ErrorType.get_category(error_type)
                errors_by_category[category] = errors_by_category.get(category, 0) + count
            
            # 데이터 품질 점수 계산 (결측 필드 기반)
            total_analyzed = self.metrics['stocks_analyzed']
            missing_fields = self.metrics['missing_financial_fields']
            data_quality_score = max(0, 100 - (missing_fields / max(1, total_analyzed)) * 10) if total_analyzed > 0 else 0
            
            # 필터 통과율 계산
            total_failures = self.metrics['quality_filter_rejections'] + self.metrics['risk_constraint_violations']
            filter_pass_rate = max(0, 100 - (total_failures / max(1, total_analyzed)) * 100) if total_analyzed > 0 else 0
            
            return {
                'runtime_seconds': _monotonic() - self.metrics['start_time'],
                'stocks_analyzed': self.metrics['stocks_analyzed'],
                'api_calls': self.metrics['api_calls'].copy(),
                'api_success_rate': self.get_api_success_rate(),
                'cache_hit_rates': {
                    'price': self.get_cache_hit_rate('price'),
                    'financial': self.get_cache_hit_rate('financial'),
                    'sector': self.get_cache_hit_rate('sector')
                },
                'avg_analysis_duration': self.metrics['analysis_duration']['avg'],
                'avg_sector_evaluation': self.metrics['sector_evaluation']['avg'],
                'errors_by_type': self.metrics['errors_by_type'].copy(),
                'errors_by_category': errors_by_category,  # SRE 대시보드용 상위 카테고리
                'sector_sample_insufficient': self.metrics['sector_sample_insufficient'],
                'sector_sample_insufficient_by_sector': self.metrics.get('sector_sample_insufficient_by_sector', {}),
                'analysis_p50': self.get_percentiles(self.analysis_histogram, self.duration_buckets, 50),
                'analysis_p90': p90,
                'analysis_p95': p95,
                'sector_p50': self.get_percentiles(self.sector_histogram, self.duration_buckets, 50),
                'sector_p90': self.get_percentiles(self.sector_histogram, self.duration_buckets, 90),
                'sector_p95': self.get_percentiles(self.sector_histogram, self.duration_buckets, 95),
                # ✅ 누락된 메트릭 추가
                'quality_filter_rejections': self.metrics['quality_filter_rejections'],
                'quality_filter_rejection_reasons': self.metrics['quality_filter_rejection_reasons'].copy(),
                'risk_constraint_violations': self.metrics['risk_constraint_violations'],
                'risk_constraint_violation_reasons': self.metrics['risk_constraint_violation_reasons'].copy(),
                'data_quality_score': data_quality_score,
                'filter_pass_rate': filter_pass_rate,
                'missing_financial_fields': self.metrics['missing_financial_fields']
            }





