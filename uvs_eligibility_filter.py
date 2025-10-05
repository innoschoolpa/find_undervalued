"""
UVS 자격 필터 모듈

가치 스타일, 저평가, 품질/리스크 통과를 확인하는 UVS 자격 필터를 제공합니다.
"""

import logging
from typing import Any, Dict, List

from metrics import MetricsCollector


class UVSEligibilityFilter:
    """UVS 자격 필터 (가치 스타일 ∧ 저평가 ∧ 품질/리스크 통과)"""
    
    def __init__(self, metrics_collector: MetricsCollector = None):
        self.metrics = metrics_collector
        # UVS 자격 기준
        self.uvs_criteria = {
            'min_value_style_score': 70.0,     # 최소 가치 스타일 점수
            'max_valuation_percentile': 40.0,   # 최대 가치 퍼센타일 (40% 이하)
            'min_margin_of_safety': 0.15,       # 최소 안전마진 15%
            'min_quality_score': 60.0,          # 최소 품질 점수
            'max_risk_score': 0.3,              # 최대 리스크 점수 (30% 이하)
            'min_confidence_score': 0.6         # 최소 신뢰도 점수
        }
    
    def check_uvs_eligibility(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        UVS 자격 검증
        
        Args:
            metrics: 분석 메트릭 딕셔너리
                - value_style_score: 가치 스타일 점수
                - valuation_percentile: 가치 퍼센타일
                - margin_of_safety: 안전마진
                - quality_score: 품질 점수
                - risk_score: 리스크 점수
                - confidence_score: 신뢰도 점수
        
        Returns:
            Dict: is_eligible, eligibility_reasons, uvs_score
        """
        result = {
            'is_eligible': False,
            'eligibility_reasons': [],
            'uvs_score': 0.0,
            'failed_criteria': []
        }
        
        try:
            # 1. 가치 스타일 검증
            value_style_result = self._check_value_style(metrics)
            result['eligibility_reasons'].extend(value_style_result['reasons'])
            if not value_style_result['passed']:
                result['failed_criteria'].extend(value_style_result['failed_criteria'])
            
            # 2. 저평가 검증
            undervalued_result = self._check_undervalued(metrics)
            result['eligibility_reasons'].extend(undervalued_result['reasons'])
            if not undervalued_result['passed']:
                result['failed_criteria'].extend(undervalued_result['failed_criteria'])
            
            # 3. 품질/리스크 검증
            quality_risk_result = self._check_quality_risk(metrics)
            result['eligibility_reasons'].extend(quality_risk_result['reasons'])
            if not quality_risk_result['passed']:
                result['failed_criteria'].extend(quality_risk_result['failed_criteria'])
            
            # 4. 전체 자격 판정
            all_passed = (
                value_style_result['passed'] and 
                undervalued_result['passed'] and 
                quality_risk_result['passed']
            )
            
            result['is_eligible'] = all_passed
            
            # 5. UVS 점수 계산
            if all_passed:
                result['uvs_score'] = self._calculate_uvs_score(metrics)
            else:
                result['uvs_score'] = 0.0
            
            # 메트릭 기록
            if self.metrics:
                if not all_passed:
                    self.metrics.record_uvs_eligibility_filter_skips(1)
            
        except Exception as e:
            logging.warning(f"UVS 자격 검증 실패: {e}")
            result['eligibility_reasons'].append(f'eligibility_check_error: {str(e)}')
            result['failed_criteria'].append('system_error')
        
        return result
    
    def _check_value_style(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """가치 스타일 검증"""
        result = {
            'passed': False,
            'reasons': [],
            'failed_criteria': []
        }
        
        try:
            value_style_score = metrics.get('value_style_score', 0)
            confidence_score = metrics.get('confidence_score', 0)
            
            # 가치 스타일 점수 검증
            if value_style_score >= self.uvs_criteria['min_value_style_score']:
                result['reasons'].append(f'value_style_score_pass_{value_style_score:.1f}')
            else:
                result['failed_criteria'].append(f'value_style_score_{value_style_score:.1f}_below_{self.uvs_criteria["min_value_style_score"]}')
            
            # 신뢰도 점수 검증
            if confidence_score >= self.uvs_criteria['min_confidence_score']:
                result['reasons'].append(f'confidence_score_pass_{confidence_score:.2f}')
            else:
                result['failed_criteria'].append(f'confidence_score_{confidence_score:.2f}_below_{self.uvs_criteria["min_confidence_score"]}')
            
            # 전체 통과 여부
            result['passed'] = (
                value_style_score >= self.uvs_criteria['min_value_style_score'] and
                confidence_score >= self.uvs_criteria['min_confidence_score']
            )
            
        except Exception as e:
            logging.warning(f"가치 스타일 검증 실패: {e}")
            result['failed_criteria'].append('value_style_check_error')
        
        return result
    
    def _check_undervalued(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """저평가 검증"""
        result = {
            'passed': False,
            'reasons': [],
            'failed_criteria': []
        }
        
        try:
            valuation_percentile = metrics.get('valuation_percentile', 50)
            margin_of_safety = metrics.get('margin_of_safety', 0)
            
            # 가치 퍼센타일 검증 (낮을수록 좋음)
            if valuation_percentile <= self.uvs_criteria['max_valuation_percentile']:
                result['reasons'].append(f'valuation_percentile_pass_{valuation_percentile:.1f}%')
            else:
                result['failed_criteria'].append(f'valuation_percentile_{valuation_percentile:.1f}%_above_{self.uvs_criteria["max_valuation_percentile"]}%')
            
            # 안전마진 검증
            if margin_of_safety >= self.uvs_criteria['min_margin_of_safety']:
                result['reasons'].append(f'margin_of_safety_pass_{margin_of_safety:.2f}')
            else:
                result['failed_criteria'].append(f'margin_of_safety_{margin_of_safety:.2f}_below_{self.uvs_criteria["min_margin_of_safety"]}')
            
            # 전체 통과 여부
            result['passed'] = (
                valuation_percentile <= self.uvs_criteria['max_valuation_percentile'] and
                margin_of_safety >= self.uvs_criteria['min_margin_of_safety']
            )
            
        except Exception as e:
            logging.warning(f"저평가 검증 실패: {e}")
            result['failed_criteria'].append('undervalued_check_error')
        
        return result
    
    def _check_quality_risk(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """품질/리스크 검증"""
        result = {
            'passed': False,
            'reasons': [],
            'failed_criteria': []
        }
        
        try:
            quality_score = metrics.get('quality_score', 0)
            risk_score = metrics.get('risk_score', 1.0)
            
            # 품질 점수 검증
            if quality_score >= self.uvs_criteria['min_quality_score']:
                result['reasons'].append(f'quality_score_pass_{quality_score:.1f}')
            else:
                result['failed_criteria'].append(f'quality_score_{quality_score:.1f}_below_{self.uvs_criteria["min_quality_score"]}')
            
            # 리스크 점수 검증 (낮을수록 좋음)
            if risk_score <= self.uvs_criteria['max_risk_score']:
                result['reasons'].append(f'risk_score_pass_{risk_score:.2f}')
            else:
                result['failed_criteria'].append(f'risk_score_{risk_score:.2f}_above_{self.uvs_criteria["max_risk_score"]}')
            
            # 전체 통과 여부
            result['passed'] = (
                quality_score >= self.uvs_criteria['min_quality_score'] and
                risk_score <= self.uvs_criteria['max_risk_score']
            )
            
        except Exception as e:
            logging.warning(f"품질/리스크 검증 실패: {e}")
            result['failed_criteria'].append('quality_risk_check_error')
        
        return result
    
    def _calculate_uvs_score(self, metrics: Dict[str, Any]) -> float:
        """UVS 점수 계산 (0~100)"""
        try:
            # 각 지표별 점수 계산
            value_style_score = metrics.get('value_style_score', 0)
            valuation_percentile = metrics.get('valuation_percentile', 50)
            margin_of_safety = metrics.get('margin_of_safety', 0)
            quality_score = metrics.get('quality_score', 0)
            risk_score = metrics.get('risk_score', 1.0)
            confidence_score = metrics.get('confidence_score', 0)
            
            # 가치 점수 (저평가 + 안전마진)
            valuation_score = max(0, 100 - valuation_percentile)  # 퍼센타일 역순
            mos_score = min(100, margin_of_safety * 200)  # 50% MoS = 100점
            value_component = (valuation_score + mos_score) / 2
            
            # 품질 점수 (기존 품질 점수 사용)
            quality_component = quality_score
            
            # 리스크 점수 (리스크가 낮을수록 높은 점수)
            risk_component = max(0, 100 - risk_score * 200)  # 50% 리스크 = 0점
            
            # 가중 평균 (가치 40%, 품질 30%, 리스크 20%, 신뢰도 10%)
            uvs_score = (
                value_component * 0.4 +
                quality_component * 0.3 +
                risk_component * 0.2 +
                confidence_score * 100 * 0.1
            )
            
            return min(100, max(0, uvs_score))
            
        except Exception as e:
            logging.warning(f"UVS 점수 계산 실패: {e}")
            return 0.0
    
    def get_uvs_grade(self, uvs_score: float) -> str:
        """UVS 점수를 등급으로 변환"""
        if uvs_score >= 90:
            return 'A+'
        elif uvs_score >= 80:
            return 'A'
        elif uvs_score >= 70:
            return 'B+'
        elif uvs_score >= 60:
            return 'B'
        elif uvs_score >= 50:
            return 'C+'
        elif uvs_score >= 40:
            return 'C'
        elif uvs_score >= 30:
            return 'D'
        else:
            return 'F'
    
    def filter_uvs_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """UVS 후보 필터링"""
        try:
            uvs_candidates = []
            
            for candidate in candidates:
                eligibility_result = self.check_uvs_eligibility(candidate.get('metrics', {}))
                
                if eligibility_result['is_eligible']:
                    # UVS 자격 통과한 종목만 추가
                    uvs_candidate = candidate.copy()
                    uvs_candidate['uvs_score'] = eligibility_result['uvs_score']
                    uvs_candidate['uvs_grade'] = self.get_uvs_grade(eligibility_result['uvs_score'])
                    uvs_candidate['eligibility_reasons'] = eligibility_result['eligibility_reasons']
                    uvs_candidates.append(uvs_candidate)
            
            # UVS 점수 순으로 정렬
            uvs_candidates.sort(key=lambda x: x.get('uvs_score', 0), reverse=True)
            
            return uvs_candidates
            
        except Exception as e:
            logging.error(f"UVS 후보 필터링 실패: {e}")
            return []













