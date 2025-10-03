"""
레짐 적응형 임계치 시스템
- 시장 레짐별 동적 임계치 조정
- 약세장/고금리 시 MoS 강화
- 강세장/완화기 시 적응형 허용폭 확대
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """시장 레짐 분류"""
    BULL = "bull"              # 강세장
    BEAR = "bear"              # 약세장  
    SIDEWAYS = "sideways"      # 횡보장
    HIGH_VOLATILITY = "high_vol"  # 고변동성
    LOW_VOLATILITY = "low_vol"    # 저변동성
    HIGH_RATE = "high_rate"    # 고금리
    LOW_RATE = "low_rate"      # 저금리

class InterestRateRegime(Enum):
    """금리 레짐 분류"""
    TIGHTENING = "tightening"  # 금리 인상기
    EASING = "easing"         # 금리 인하기
    NEUTRAL = "neutral"       # 중립

@dataclass
class RegimeIndicators:
    """레짐 지표"""
    # 시장 지표
    kospi_return_3m: float = 0.0      # 3개월 KOSPI 수익률
    kospi_return_12m: float = 0.0     # 12개월 KOSPI 수익률
    vix_level: float = 20.0           # 변동성 지수
    market_cap_change: float = 0.0    # 시총 변화율
    
    # 금리 지표
    base_rate: float = 3.5            # 기준금리
    bond_yield_10y: float = 4.0       # 10년 국채 수익률
    credit_spread: float = 0.5        # 신용 스프레드
    
    # 섹터 지표
    tech_sector_momentum: float = 0.0  # 기술주 모멘텀
    value_sector_momentum: float = 0.0 # 가치주 모멘텀
    
    # 거시 경제 지표
    gdp_growth: float = 2.0           # GDP 성장률
    inflation_rate: float = 2.0       # 인플레이션율
    unemployment_rate: float = 3.0    # 실업률

@dataclass
class AdaptiveThresholds:
    """적응형 임계치"""
    # 안전마진 임계치
    mos_threshold: float = 0.20
    mos_tightening_factor: float = 1.0  # 강화 배수
    mos_easing_factor: float = 1.0      # 완화 배수
    
    # 품질 임계치
    quality_threshold: float = 0.60
    quality_tightening_factor: float = 1.0
    quality_easing_factor: float = 1.0
    
    # 가치 점수 임계치
    value_threshold: float = 50.0
    value_tightening_factor: float = 1.0
    value_easing_factor: float = 1.0
    
    # 가격 위치 임계치
    price_position_threshold: float = 0.70  # 70분위 이하
    price_position_tightening_factor: float = 1.0
    price_position_easing_factor: float = 1.0
    
    # 레버리지 제한
    max_leverage_ratio: float = 0.30
    leverage_tightening_factor: float = 1.0
    leverage_easing_factor: float = 1.0

class RegimeAdaptiveSystem:
    """레짐 적응형 시스템"""
    
    def __init__(self):
        self.current_regime = None
        self.interest_rate_regime = None
        self.regime_indicators = RegimeIndicators()
        self.base_thresholds = AdaptiveThresholds()
        self.adaptive_thresholds = AdaptiveThresholds()
        
        # 레짐별 임계치 설정
        self.regime_configs = self._initialize_regime_configs()
        
    def _initialize_regime_configs(self) -> Dict[str, Dict[str, float]]:
        """레짐별 설정 초기화"""
        return {
            MarketRegime.BEAR.value: {
                'mos_factor': 1.3,        # 30% 강화
                'quality_factor': 1.2,    # 20% 강화
                'value_factor': 1.1,      # 10% 강화
                'price_position_factor': 0.8,  # 20% 완화 (더 낮은 가격 위치 요구)
                'leverage_factor': 0.7,   # 30% 강화 (레버리지 제한)
                'description': '약세장: 안전마진과 품질 기준 강화'
            },
            MarketRegime.BULL.value: {
                'mos_factor': 0.9,        # 10% 완화
                'quality_factor': 0.95,   # 5% 완화
                'value_factor': 0.85,     # 15% 완화
                'price_position_factor': 1.1,  # 10% 완화
                'leverage_factor': 1.2,   # 20% 완화
                'description': '강세장: 가격위치 허용폭 확대 (품질 유지)'
            },
            MarketRegime.HIGH_VOLATILITY.value: {
                'mos_factor': 1.4,        # 40% 강화
                'quality_factor': 1.3,    # 30% 강화
                'value_factor': 1.2,      # 20% 강화
                'price_position_factor': 0.7,  # 30% 강화
                'leverage_factor': 0.6,   # 40% 강화
                'description': '고변동성: 모든 기준 강화'
            },
            MarketRegime.HIGH_RATE.value: {
                'mos_factor': 1.25,       # 25% 강화
                'quality_factor': 1.15,   # 15% 강화
                'value_factor': 1.05,     # 5% 강화
                'price_position_factor': 0.9,  # 10% 강화
                'leverage_factor': 0.8,   # 20% 강화
                'description': '고금리: 안전마진과 레버리지 제한 강화'
            },
            MarketRegime.LOW_RATE.value: {
                'mos_factor': 0.95,       # 5% 완화
                'quality_factor': 0.98,   # 2% 완화
                'value_factor': 0.92,     # 8% 완화
                'price_position_factor': 1.05,  # 5% 완화
                'leverage_factor': 1.1,   # 10% 완화
                'description': '저금리: 가치 기회 확대'
            }
        }
    
    def detect_market_regime(self, indicators: RegimeIndicators) -> MarketRegime:
        """시장 레짐 감지"""
        logger.info("시장 레짐 감지 중...")
        
        # 고변동성 체크
        if indicators.vix_level > 30:
            return MarketRegime.HIGH_VOLATILITY
        
        # 저변동성 체크
        if indicators.vix_level < 15:
            return MarketRegime.LOW_VOLATILITY
        
        # 강세장/약세장 판단
        if indicators.kospi_return_3m > 0.10:  # 3개월 10% 이상
            return MarketRegime.BULL
        elif indicators.kospi_return_3m < -0.10:  # 3개월 -10% 이하
            return MarketRegime.BEAR
        else:
            return MarketRegime.SIDEWAYS
    
    def detect_interest_rate_regime(self, indicators: RegimeIndicators) -> InterestRateRegime:
        """금리 레짐 감지"""
        # 기준금리 기준
        if indicators.base_rate > 4.0:
            return InterestRateRegime.TIGHTENING
        elif indicators.base_rate < 2.0:
            return InterestRateRegime.EASING
        else:
            return InterestRateRegime.NEUTRAL
    
    def update_regime_indicators(self, market_data: Dict[str, Any]) -> RegimeIndicators:
        """레짐 지표 업데이트"""
        logger.info("레짐 지표 업데이트 중...")
        
        indicators = RegimeIndicators(
            kospi_return_3m=market_data.get('kospi_return_3m', 0.0),
            kospi_return_12m=market_data.get('kospi_return_12m', 0.0),
            vix_level=market_data.get('vix_level', 20.0),
            market_cap_change=market_data.get('market_cap_change', 0.0),
            base_rate=market_data.get('base_rate', 3.5),
            bond_yield_10y=market_data.get('bond_yield_10y', 4.0),
            credit_spread=market_data.get('credit_spread', 0.5),
            tech_sector_momentum=market_data.get('tech_momentum', 0.0),
            value_sector_momentum=market_data.get('value_momentum', 0.0),
            gdp_growth=market_data.get('gdp_growth', 2.0),
            inflation_rate=market_data.get('inflation_rate', 2.0),
            unemployment_rate=market_data.get('unemployment_rate', 3.0)
        )
        
        self.regime_indicators = indicators
        return indicators
    
    def calculate_adaptive_thresholds(self, market_regime: MarketRegime, 
                                    interest_rate_regime: InterestRateRegime) -> AdaptiveThresholds:
        """적응형 임계치 계산"""
        logger.info(f"적응형 임계치 계산: {market_regime.value}, {interest_rate_regime.value}")
        
        # 기본 임계치 복사
        adaptive = AdaptiveThresholds()
        
        # 시장 레짐별 조정
        market_config = self.regime_configs.get(market_regime.value, {})
        
        # 금리 레짐별 추가 조정
        if interest_rate_regime == InterestRateRegime.TIGHTENING:
            rate_config = self.regime_configs.get(MarketRegime.HIGH_RATE.value, {})
            # 금리 인상기에는 더욱 보수적
            rate_multiplier = 1.1
        elif interest_rate_regime == InterestRateRegime.EASING:
            rate_config = self.regime_configs.get(MarketRegime.LOW_RATE.value, {})
            # 금리 인하기에는 상대적으로 완화
            rate_multiplier = 0.95
        else:
            rate_config = {}
            rate_multiplier = 1.0
        
        # 임계치 적용
        adaptive.mos_threshold = self.base_thresholds.mos_threshold * market_config.get('mos_factor', 1.0) * rate_multiplier
        adaptive.quality_threshold = self.base_thresholds.quality_threshold * market_config.get('quality_factor', 1.0) * rate_multiplier
        adaptive.value_threshold = self.base_thresholds.value_threshold * market_config.get('value_factor', 1.0) * rate_multiplier
        adaptive.price_position_threshold = self.base_thresholds.price_position_threshold * market_config.get('price_position_factor', 1.0) * rate_multiplier
        adaptive.max_leverage_ratio = self.base_thresholds.max_leverage_ratio * market_config.get('leverage_factor', 1.0) * rate_multiplier
        
        # 배수 저장
        adaptive.mos_tightening_factor = market_config.get('mos_factor', 1.0) * rate_multiplier
        adaptive.quality_tightening_factor = market_config.get('quality_factor', 1.0) * rate_multiplier
        adaptive.value_tightening_factor = market_config.get('value_factor', 1.0) * rate_multiplier
        adaptive.price_position_tightening_factor = market_config.get('price_position_factor', 1.0) * rate_multiplier
        adaptive.leverage_tightening_factor = market_config.get('leverage_factor', 1.0) * rate_multiplier
        
        self.adaptive_thresholds = adaptive
        return adaptive
    
    def apply_regime_adaptive_filter(self, stock_analysis: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """레짐 적응형 필터 적용"""
        logger.info("레짐 적응형 필터 적용 중...")
        
        # 현재 레짐 확인
        if not self.current_regime:
            return False, "regime_not_detected", {}
        
        # 주식 분석 결과 추출
        mos = stock_analysis.get('margin_of_safety', 0.0)
        quality_score = stock_analysis.get('quality_score', 0.0)
        value_score = stock_analysis.get('value_score', 0.0)
        price_position = stock_analysis.get('price_position', 1.0)
        leverage_ratio = stock_analysis.get('leverage_ratio', 0.0)
        
        # 적응형 임계치와 비교
        filter_results = {
            'mos_pass': mos >= self.adaptive_thresholds.mos_threshold,
            'quality_pass': quality_score >= self.adaptive_thresholds.quality_threshold,
            'value_pass': value_score >= self.adaptive_thresholds.value_threshold,
            'price_position_pass': price_position <= self.adaptive_thresholds.price_position_threshold,
            'leverage_pass': leverage_ratio <= self.adaptive_thresholds.max_leverage_ratio
        }
        
        # 통과 조건: 최소 4/5 조건 만족
        pass_count = sum(filter_results.values())
        passed = pass_count >= 4
        
        # 실패 사유 분석
        if not passed:
            failed_conditions = [k for k, v in filter_results.items() if not v]
            failure_reason = f"failed_conditions: {', '.join(failed_conditions)}"
        else:
            failure_reason = "passed"
        
        # 상세 정보
        filter_details = {
            'regime': self.current_regime.value,
            'adaptive_thresholds': {
                'mos': self.adaptive_thresholds.mos_threshold,
                'quality': self.adaptive_thresholds.quality_threshold,
                'value': self.adaptive_thresholds.value_threshold,
                'price_position': self.adaptive_thresholds.price_position_threshold,
                'leverage': self.adaptive_thresholds.max_leverage_ratio
            },
            'stock_metrics': {
                'mos': mos,
                'quality_score': quality_score,
                'value_score': value_score,
                'price_position': price_position,
                'leverage_ratio': leverage_ratio
            },
            'filter_results': filter_results,
            'pass_count': pass_count,
            'total_conditions': len(filter_results)
        }
        
        return passed, failure_reason, filter_details
    
    def get_regime_recommendations(self) -> Dict[str, Any]:
        """레짐별 투자 권고사항"""
        if not self.current_regime:
            return {}
        
        regime_config = self.regime_configs.get(self.current_regime.value, {})
        
        recommendations = {
            'current_regime': self.current_regime.value,
            'description': regime_config.get('description', ''),
            'adaptive_thresholds': {
                'mos_threshold': self.adaptive_thresholds.mos_threshold,
                'quality_threshold': self.adaptive_thresholds.quality_threshold,
                'value_threshold': self.adaptive_thresholds.value_threshold,
                'price_position_threshold': self.adaptive_thresholds.price_position_threshold,
                'max_leverage_ratio': self.adaptive_thresholds.max_leverage_ratio
            },
            'tightening_factors': {
                'mos': self.adaptive_thresholds.mos_tightening_factor,
                'quality': self.adaptive_thresholds.quality_tightening_factor,
                'value': self.adaptive_thresholds.value_tightening_factor,
                'price_position': self.adaptive_thresholds.price_position_tightening_factor,
                'leverage': self.adaptive_thresholds.leverage_tightening_factor
            }
        }
        
        # 레짐별 특별 권고사항
        if self.current_regime == MarketRegime.BEAR:
            recommendations['special_advice'] = [
                "안전마진 30% 이상 확보 필수",
                "고품질 기업 선호",
                "부채비율 낮은 기업 우선",
                "현금 보유 비중 확대 고려"
            ]
        elif self.current_regime == MarketRegime.BULL:
            recommendations['special_advice'] = [
                "성장성 있는 가치주 탐색",
                "적정 가격대 매수 기회 활용",
                "섹터 로테이션 고려",
                "수익 실현 타이밍 관리"
            ]
        elif self.current_regime == MarketRegime.HIGH_VOLATILITY:
            recommendations['special_advice'] = [
                "모든 기준 강화 적용",
                "단기 변동성 무시",
                "장기 투자 관점 유지",
                "리스크 관리 우선"
            ]
        
        return recommendations
    
    def run_regime_analysis(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """종합 레짐 분석 실행"""
        logger.info("종합 레짐 분석 시작...")
        
        # 1. 지표 업데이트
        indicators = self.update_regime_indicators(market_data)
        
        # 2. 레짐 감지
        market_regime = self.detect_market_regime(indicators)
        interest_rate_regime = self.detect_interest_rate_regime(indicators)
        
        # 3. 적응형 임계치 계산
        adaptive_thresholds = self.calculate_adaptive_thresholds(market_regime, interest_rate_regime)
        
        # 4. 현재 레짐 저장
        self.current_regime = market_regime
        self.interest_rate_regime = interest_rate_regime
        
        # 5. 권고사항 생성
        recommendations = self.get_regime_recommendations()
        
        # 6. 종합 결과
        analysis_result = {
            'timestamp': datetime.now().isoformat(),
            'market_regime': market_regime.value,
            'interest_rate_regime': interest_rate_regime.value,
            'indicators': {
                'kospi_return_3m': indicators.kospi_return_3m,
                'vix_level': indicators.vix_level,
                'base_rate': indicators.base_rate,
                'bond_yield_10y': indicators.bond_yield_10y,
                'credit_spread': indicators.credit_spread
            },
            'base_thresholds': {
                'mos': self.base_thresholds.mos_threshold,
                'quality': self.base_thresholds.quality_threshold,
                'value': self.base_thresholds.value_threshold,
                'price_position': self.base_thresholds.price_position_threshold,
                'leverage': self.base_thresholds.max_leverage_ratio
            },
            'adaptive_thresholds': {
                'mos': adaptive_thresholds.mos_threshold,
                'quality': adaptive_thresholds.quality_threshold,
                'value': adaptive_thresholds.value_threshold,
                'price_position': adaptive_thresholds.price_position_threshold,
                'leverage': adaptive_thresholds.max_leverage_ratio
            },
            'adjustment_factors': {
                'mos': adaptive_thresholds.mos_tightening_factor,
                'quality': adaptive_thresholds.quality_tightening_factor,
                'value': adaptive_thresholds.value_tightening_factor,
                'price_position': adaptive_thresholds.price_position_tightening_factor,
                'leverage': adaptive_thresholds.leverage_tightening_factor
            },
            'recommendations': recommendations
        }
        
        logger.info(f"레짐 분석 완료: {market_regime.value}, {interest_rate_regime.value}")
        return analysis_result

def main():
    """메인 실행 함수 - 테스트"""
    print("="*80)
    print("레짐 적응형 임계치 시스템 테스트")
    print("="*80)
    
    # 시스템 초기화
    regime_system = RegimeAdaptiveSystem()
    
    # 테스트 시나리오들
    test_scenarios = {
        'bear_market_high_rate': {
            'kospi_return_3m': -0.15,
            'vix_level': 35,
            'base_rate': 4.5,
            'bond_yield_10y': 5.0,
            'credit_spread': 1.2
        },
        'bull_market_low_rate': {
            'kospi_return_3m': 0.12,
            'vix_level': 18,
            'base_rate': 2.0,
            'bond_yield_10y': 3.0,
            'credit_spread': 0.3
        },
        'high_volatility': {
            'kospi_return_3m': 0.05,
            'vix_level': 35,
            'base_rate': 3.5,
            'bond_yield_10y': 4.2,
            'credit_spread': 0.8
        }
    }
    
    for scenario_name, market_data in test_scenarios.items():
        print(f"\n{'='*60}")
        print(f"시나리오: {scenario_name}")
        print(f"{'='*60}")
        
        # 레짐 분석 실행
        result = regime_system.run_regime_analysis(market_data)
        
        # 결과 출력
        print(f"시장 레짐: {result['market_regime']}")
        print(f"금리 레짐: {result['interest_rate_regime']}")
        print(f"\n적응형 임계치:")
        for key, value in result['adaptive_thresholds'].items():
            base_value = result['base_thresholds'][key]
            adjustment = result['adjustment_factors'][key]
            print(f"  {key}: {base_value:.2f} → {value:.2f} (조정: {adjustment:.2f}x)")
        
        # 권고사항 출력
        if 'special_advice' in result['recommendations']:
            print(f"\n특별 권고사항:")
            for advice in result['recommendations']['special_advice']:
                print(f"  - {advice}")
    
    print(f"\n{'='*80}")
    print("레짐 적응형 시스템 테스트 완료!")
    print("="*80)

if __name__ == "__main__":
    main()

