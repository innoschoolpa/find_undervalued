"""
멀티-모델 합의 시스템
- Core-5(가치) 외 보조 가치모델과 합의 스코어 적용
- Residual-Income, DCF-lite 등 다양한 모델 통합
- 앙상블 학습을 통한 신뢰도 향상
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

class ValuationModel(Enum):
    """가치평가 모델"""
    CORE_5_VALUE = "core_5_value"           # 핵심 5개 가치지표
    RESIDUAL_INCOME = "residual_income"     # 잔여이익 모델
    DCF_LITE = "dcf_lite"                   # 간소화된 DCF
    EARNINGS_POWER = "earnings_power"       # 수익력 기반 모델
    ASSET_BASED = "asset_based"             # 자산 기반 모델
    SECTOR_RELATIVE = "sector_relative"     # 섹터 상대 모델
    MOMENTUM_ADJUSTED = "momentum_adjusted" # 모멘텀 조정 모델

@dataclass
class ModelResult:
    """모델 결과"""
    model_name: str
    intrinsic_value: float = 0.0
    confidence_score: float = 0.0
    model_weight: float = 0.0
    input_quality: float = 0.0
    historical_accuracy: float = 0.0
    calculation_details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.calculation_details is None:
            self.calculation_details = {}

@dataclass
class EnsembleResult:
    """앙상블 결과"""
    consensus_value: float = 0.0
    consensus_confidence: float = 0.0
    model_agreement: float = 0.0
    disagreement_measure: float = 0.0
    outlier_detected: bool = False
    recommended_weight: float = 0.0
    individual_results: List[ModelResult] = None
    
    def __post_init__(self):
        if self.individual_results is None:
            self.individual_results = []

class MultiModelEnsembleSystem:
    """멀티-모델 앙상블 시스템"""
    
    def __init__(self):
        self.model_weights = self._initialize_model_weights()
        self.model_accuracy_history = {}
        self.ensemble_performance_history = []
        
    def _initialize_model_weights(self) -> Dict[str, float]:
        """모델 가중치 초기화"""
        return {
            ValuationModel.CORE_5_VALUE.value: 0.30,      # 핵심 모델
            ValuationModel.RESIDUAL_INCOME.value: 0.20,   # 잔여이익 모델
            ValuationModel.DCF_LITE.value: 0.15,          # DCF 모델
            ValuationModel.EARNINGS_POWER.value: 0.15,    # 수익력 모델
            ValuationModel.ASSET_BASED.value: 0.10,       # 자산 기반 모델
            ValuationModel.SECTOR_RELATIVE.value: 0.05,   # 섹터 상대 모델
            ValuationModel.MOMENTUM_ADJUSTED.value: 0.05  # 모멘텀 조정 모델
        }
    
    def calculate_core_5_value(self, financial_data: Dict[str, Any], 
                              market_cap: float) -> ModelResult:
        """핵심 5개 가치지표 모델"""
        logger.info("핵심 5개 가치지표 모델 계산")
        
        try:
            # EV/EBIT 점수
            ev_ebit_score = self._calculate_ev_ebit_score(financial_data, market_cap)
            
            # FCF Yield 점수
            fcf_yield_score = self._calculate_fcf_yield_score(financial_data, market_cap)
            
            # Owner Earnings Yield 점수
            owner_earnings_score = self._calculate_owner_earnings_score(financial_data, market_cap)
            
            # Earnings Quality 점수
            earnings_quality_score = self._calculate_earnings_quality_score(financial_data, market_cap)
            
            # Shareholder Yield 점수
            shareholder_yield_score = self._calculate_shareholder_yield_score(financial_data, market_cap)
            
            # 종합 점수 계산
            scores = [ev_ebit_score, fcf_yield_score, owner_earnings_score, 
                     earnings_quality_score, shareholder_yield_score]
            weights = [0.25, 0.25, 0.20, 0.15, 0.15]
            
            weighted_score = sum(score * weight for score, weight in zip(scores, weights))
            
            # 내재가치 추정 (점수를 가격 프리미엄으로 변환)
            intrinsic_value = market_cap * (1 + weighted_score / 100)
            
            # 신뢰도 계산
            confidence = min(0.9, weighted_score / 100)  # 최대 90% 신뢰도
            
            return ModelResult(
                model_name=ValuationModel.CORE_5_VALUE.value,
                intrinsic_value=intrinsic_value,
                confidence_score=confidence,
                model_weight=self.model_weights[ValuationModel.CORE_5_VALUE.value],
                input_quality=self._assess_input_quality(financial_data),
                historical_accuracy=self._get_historical_accuracy(ValuationModel.CORE_5_VALUE.value),
                calculation_details={
                    'individual_scores': {
                        'ev_ebit': ev_ebit_score,
                        'fcf_yield': fcf_yield_score,
                        'owner_earnings': owner_earnings_score,
                        'earnings_quality': earnings_quality_score,
                        'shareholder_yield': shareholder_yield_score
                    },
                    'weighted_score': weighted_score
                }
            )
            
        except Exception as e:
            logger.error(f"Core 5 Value 모델 계산 실패: {e}")
            return ModelResult(model_name=ValuationModel.CORE_5_VALUE.value)
    
    def calculate_residual_income(self, financial_data: Dict[str, Any], 
                                market_cap: float) -> ModelResult:
        """잔여이익 모델"""
        logger.info("잔여이익 모델 계산")
        
        try:
            # 잔여이익 계산
            net_income = financial_data.get('net_income', 0)
            book_value = financial_data.get('book_value', market_cap)
            cost_of_equity = 0.12  # 12% 자본비용 가정
            
            residual_income = net_income - (book_value * cost_of_equity)
            
            # 영구성장률 가정 (2%)
            growth_rate = 0.02
            
            # 잔여이익의 현재가치
            if cost_of_equity > growth_rate:
                pv_residual_income = residual_income / (cost_of_equity - growth_rate)
            else:
                pv_residual_income = residual_income / cost_of_equity
            
            # 내재가치 = 장부가치 + 잔여이익 현재가치
            intrinsic_value = book_value + pv_residual_income
            
            # 신뢰도 계산
            confidence = min(0.8, abs(residual_income) / (net_income + 1e-6))
            
            return ModelResult(
                model_name=ValuationModel.RESIDUAL_INCOME.value,
                intrinsic_value=intrinsic_value,
                confidence_score=confidence,
                model_weight=self.model_weights[ValuationModel.RESIDUAL_INCOME.value],
                input_quality=self._assess_input_quality(financial_data),
                historical_accuracy=self._get_historical_accuracy(ValuationModel.RESIDUAL_INCOME.value),
                calculation_details={
                    'residual_income': residual_income,
                    'book_value': book_value,
                    'cost_of_equity': cost_of_equity,
                    'growth_rate': growth_rate,
                    'pv_residual_income': pv_residual_income
                }
            )
            
        except Exception as e:
            logger.error(f"Residual Income 모델 계산 실패: {e}")
            return ModelResult(model_name=ValuationModel.RESIDUAL_INCOME.value)
    
    def calculate_dcf_lite(self, financial_data: Dict[str, Any], 
                          market_cap: float) -> ModelResult:
        """간소화된 DCF 모델"""
        logger.info("간소화된 DCF 모델 계산")
        
        try:
            # 현재 FCF
            current_fcf = financial_data.get('free_cash_flow', 0)
            
            # 성장률 추정
            revenue_growth = financial_data.get('revenue_growth', 0.05)
            margin_expansion = financial_data.get('margin_expansion', 0.01)
            estimated_growth = min(0.15, max(0.02, revenue_growth + margin_expansion))
            
            # 할인률 (WACC 추정)
            cost_of_equity = 0.12
            cost_of_debt = 0.06
            debt_ratio = financial_data.get('debt_ratio', 0.3)
            tax_rate = 0.25
            
            wacc = cost_of_equity * (1 - debt_ratio) + cost_of_debt * debt_ratio * (1 - tax_rate)
            
            # 5년 예측 기간
            forecast_years = 5
            terminal_growth = 0.02
            
            # 예측 FCF 계산
            forecast_fcf = []
            for year in range(1, forecast_years + 1):
                year_fcf = current_fcf * (1 + estimated_growth) ** year
                forecast_fcf.append(year_fcf)
            
            # 터미널 가치
            terminal_fcf = forecast_fcf[-1] * (1 + terminal_growth)
            terminal_value = terminal_fcf / (wacc - terminal_growth)
            
            # 현재가치 계산
            pv_forecast = 0
            for year, fcf in enumerate(forecast_fcf, 1):
                pv_forecast += fcf / (1 + wacc) ** year
            
            pv_terminal = terminal_value / (1 + wacc) ** forecast_years
            
            intrinsic_value = pv_forecast + pv_terminal
            
            # 신뢰도 계산
            confidence = min(0.85, 0.5 + abs(estimated_growth - 0.05) * 2)
            
            return ModelResult(
                model_name=ValuationModel.DCF_LITE.value,
                intrinsic_value=intrinsic_value,
                confidence_score=confidence,
                model_weight=self.model_weights[ValuationModel.DCF_LITE.value],
                input_quality=self._assess_input_quality(financial_data),
                historical_accuracy=self._get_historical_accuracy(ValuationModel.DCF_LITE.value),
                calculation_details={
                    'current_fcf': current_fcf,
                    'estimated_growth': estimated_growth,
                    'wacc': wacc,
                    'forecast_fcf': forecast_fcf,
                    'terminal_value': terminal_value,
                    'pv_forecast': pv_forecast,
                    'pv_terminal': pv_terminal
                }
            )
            
        except Exception as e:
            logger.error(f"DCF Lite 모델 계산 실패: {e}")
            return ModelResult(model_name=ValuationModel.DCF_LITE.value)
    
    def calculate_earnings_power(self, financial_data: Dict[str, Any], 
                                market_cap: float) -> ModelResult:
        """수익력 기반 모델"""
        logger.info("수익력 기반 모델 계산")
        
        try:
            # 평균 수익력 계산 (최근 3년)
            earnings_history = financial_data.get('earnings_history', [])
            if len(earnings_history) < 3:
                earnings_history = [financial_data.get('net_income', 0)] * 3
            
            avg_earnings = np.mean(earnings_history[-3:])
            
            # 수익력의 안정성 평가
            earnings_volatility = np.std(earnings_history[-3:]) / (abs(avg_earnings) + 1e-6)
            stability_factor = max(0.5, 1 - earnings_volatility)
            
            # 적정 PER 추정 (수익력 안정성 기반)
            base_per = 15.0  # 기본 PER
            stability_adjusted_per = base_per * stability_factor
            
            # 내재가치 계산
            intrinsic_value = avg_earnings * stability_adjusted_per
            
            # 신뢰도 계산
            confidence = stability_factor * 0.8
            
            return ModelResult(
                model_name=ValuationModel.EARNINGS_POWER.value,
                intrinsic_value=intrinsic_value,
                confidence_score=confidence,
                model_weight=self.model_weights[ValuationModel.EARNINGS_POWER.value],
                input_quality=self._assess_input_quality(financial_data),
                historical_accuracy=self._get_historical_accuracy(ValuationModel.EARNINGS_POWER.value),
                calculation_details={
                    'avg_earnings': avg_earnings,
                    'earnings_volatility': earnings_volatility,
                    'stability_factor': stability_factor,
                    'adjusted_per': stability_adjusted_per
                }
            )
            
        except Exception as e:
            logger.error(f"Earnings Power 모델 계산 실패: {e}")
            return ModelResult(model_name=ValuationModel.EARNINGS_POWER.value)
    
    def calculate_asset_based(self, financial_data: Dict[str, Any], 
                             market_cap: float) -> ModelResult:
        """자산 기반 모델"""
        logger.info("자산 기반 모델 계산")
        
        try:
            # 자산 가치 계산
            total_assets = financial_data.get('total_assets', market_cap)
            total_liabilities = financial_data.get('total_liabilities', market_cap * 0.5)
            
            # 순자산가치
            net_asset_value = total_assets - total_liabilities
            
            # 무형자산 조정 (브랜드, 특허 등)
            intangible_assets = financial_data.get('intangible_assets', 0)
            adjusted_nav = net_asset_value + intangible_assets * 0.5  # 50% 할인
            
            # 자산 회전율 기반 조정
            asset_turnover = financial_data.get('asset_turnover', 1.0)
            efficiency_multiplier = min(1.5, max(0.5, asset_turnover))
            
            intrinsic_value = adjusted_nav * efficiency_multiplier
            
            # 신뢰도 계산
            confidence = min(0.7, efficiency_multiplier / 1.5)
            
            return ModelResult(
                model_name=ValuationModel.ASSET_BASED.value,
                intrinsic_value=intrinsic_value,
                confidence_score=confidence,
                model_weight=self.model_weights[ValuationModel.ASSET_BASED.value],
                input_quality=self._assess_input_quality(financial_data),
                historical_accuracy=self._get_historical_accuracy(ValuationModel.ASSET_BASED.value),
                calculation_details={
                    'total_assets': total_assets,
                    'total_liabilities': total_liabilities,
                    'net_asset_value': net_asset_value,
                    'adjusted_nav': adjusted_nav,
                    'efficiency_multiplier': efficiency_multiplier
                }
            )
            
        except Exception as e:
            logger.error(f"Asset Based 모델 계산 실패: {e}")
            return ModelResult(model_name=ValuationModel.ASSET_BASED.value)
    
    def calculate_sector_relative(self, financial_data: Dict[str, Any], 
                                 market_cap: float, sector_data: Dict[str, Any]) -> ModelResult:
        """섹터 상대 모델"""
        logger.info("섹터 상대 모델 계산")
        
        try:
            # 섹터 평균 배수
            sector_avg_per = sector_data.get('avg_per', 15.0)
            sector_avg_pbr = sector_data.get('avg_pbr', 1.5)
            sector_avg_ev_ebit = sector_data.get('avg_ev_ebit', 12.0)
            
            # 현재 기업의 수익/자산
            current_earnings = financial_data.get('net_income', 0)
            current_book_value = financial_data.get('book_value', market_cap)
            current_ebit = financial_data.get('operating_income', current_earnings)
            
            # 섹터 평균 대비 상대적 평가
            if current_earnings > 0:
                per_based_value = current_earnings * sector_avg_per
            else:
                per_based_value = market_cap
            
            if current_book_value > 0:
                pbr_based_value = current_book_value * sector_avg_pbr
            else:
                pbr_based_value = market_cap
            
            if current_ebit > 0:
                ev_ebit_based_value = current_ebit * sector_avg_ev_ebit
            else:
                ev_ebit_based_value = market_cap
            
            # 가중 평균
            intrinsic_value = (
                per_based_value * 0.4 +
                pbr_based_value * 0.3 +
                ev_ebit_based_value * 0.3
            )
            
            # 신뢰도 계산
            confidence = 0.6  # 섹터 상대 모델은 보통 신뢰도
            
            return ModelResult(
                model_name=ValuationModel.SECTOR_RELATIVE.value,
                intrinsic_value=intrinsic_value,
                confidence_score=confidence,
                model_weight=self.model_weights[ValuationModel.SECTOR_RELATIVE.value],
                input_quality=self._assess_input_quality(financial_data),
                historical_accuracy=self._get_historical_accuracy(ValuationModel.SECTOR_RELATIVE.value),
                calculation_details={
                    'sector_avg_per': sector_avg_per,
                    'sector_avg_pbr': sector_avg_pbr,
                    'sector_avg_ev_ebit': sector_avg_ev_ebit,
                    'per_based_value': per_based_value,
                    'pbr_based_value': pbr_based_value,
                    'ev_ebit_based_value': ev_ebit_based_value
                }
            )
            
        except Exception as e:
            logger.error(f"Sector Relative 모델 계산 실패: {e}")
            return ModelResult(model_name=ValuationModel.SECTOR_RELATIVE.value)
    
    def calculate_momentum_adjusted(self, financial_data: Dict[str, Any], 
                                   market_cap: float) -> ModelResult:
        """모멘텀 조정 모델"""
        logger.info("모멘텀 조정 모델 계산")
        
        try:
            # 기본 가치 (Core 5 모델 사용)
            core_result = self.calculate_core_5_value(financial_data, market_cap)
            base_value = core_result.intrinsic_value
            
            # 모멘텀 지표들
            revenue_growth = financial_data.get('revenue_growth', 0)
            earnings_growth = financial_data.get('earnings_growth', 0)
            price_momentum = financial_data.get('price_momentum_6m', 0)
            
            # 모멘텀 점수 계산
            momentum_score = (
                revenue_growth * 0.4 +
                earnings_growth * 0.4 +
                price_momentum * 0.2
            )
            
            # 모멘텀 조정 (과도한 조정 방지)
            momentum_multiplier = 1 + min(0.2, max(-0.2, momentum_score * 0.1))
            
            intrinsic_value = base_value * momentum_multiplier
            
            # 신뢰도 계산 (모멘텀이 강할수록 신뢰도 감소)
            momentum_volatility = abs(momentum_score)
            confidence = max(0.4, core_result.confidence_score - momentum_volatility * 0.2)
            
            return ModelResult(
                model_name=ValuationModel.MOMENTUM_ADJUSTED.value,
                intrinsic_value=intrinsic_value,
                confidence_score=confidence,
                model_weight=self.model_weights[ValuationModel.MOMENTUM_ADJUSTED.value],
                input_quality=self._assess_input_quality(financial_data),
                historical_accuracy=self._get_historical_accuracy(ValuationModel.MOMENTUM_ADJUSTED.value),
                calculation_details={
                    'base_value': base_value,
                    'momentum_score': momentum_score,
                    'momentum_multiplier': momentum_multiplier,
                    'revenue_growth': revenue_growth,
                    'earnings_growth': earnings_growth,
                    'price_momentum': price_momentum
                }
            )
            
        except Exception as e:
            logger.error(f"Momentum Adjusted 모델 계산 실패: {e}")
            return ModelResult(model_name=ValuationModel.MOMENTUM_ADJUSTED.value)
    
    def _calculate_ev_ebit_score(self, financial_data: Dict[str, Any], market_cap: float) -> float:
        """EV/EBIT 점수 계산 (간소화)"""
        ebit = financial_data.get('operating_income', 0)
        net_debt = financial_data.get('net_debt', 0)
        
        if ebit <= 0:
            return 0
        
        ev = market_cap + net_debt
        ev_ebit = ev / ebit
        
        # 10 이하면 100점, 20 이하면 50점, 그 이상은 0점
        if ev_ebit <= 10:
            return 100
        elif ev_ebit <= 20:
            return 100 - (ev_ebit - 10) * 5
        else:
            return 0
    
    def _calculate_fcf_yield_score(self, financial_data: Dict[str, Any], market_cap: float) -> float:
        """FCF Yield 점수 계산 (간소화)"""
        fcf = financial_data.get('free_cash_flow', 0)
        
        if fcf <= 0 or market_cap <= 0:
            return 0
        
        fcf_yield = fcf / market_cap
        
        # 10% 이상이면 100점, 5% 이상이면 50점, 그 이하는 비례
        return min(100, max(0, fcf_yield * 1000))
    
    def _calculate_owner_earnings_score(self, financial_data: Dict[str, Any], market_cap: float) -> float:
        """Owner Earnings 점수 계산 (간소화)"""
        net_income = financial_data.get('net_income', 0)
        depreciation = financial_data.get('depreciation', 0)
        maintenance_capex = financial_data.get('maintenance_capex', 0)
        
        owner_earnings = net_income + depreciation - maintenance_capex
        
        if owner_earnings <= 0 or market_cap <= 0:
            return 0
        
        owner_earnings_yield = owner_earnings / market_cap
        
        return min(100, max(0, owner_earnings_yield * 1000))
    
    def _calculate_earnings_quality_score(self, financial_data: Dict[str, Any], market_cap: float) -> float:
        """Earnings Quality 점수 계산 (간소화)"""
        net_income = financial_data.get('net_income', 0)
        operating_cash_flow = financial_data.get('operating_cash_flow', 0)
        
        if net_income <= 0:
            return 0
        
        # 현금 전환율
        cash_conversion = operating_cash_flow / net_income if net_income > 0 else 0
        
        # 1.0 이상이면 100점, 0.5 이상이면 50점
        return min(100, max(0, cash_conversion * 100))
    
    def _calculate_shareholder_yield_score(self, financial_data: Dict[str, Any], market_cap: float) -> float:
        """Shareholder Yield 점수 계산 (간소화)"""
        dividend = financial_data.get('dividend', 0)
        shares_repurchased = financial_data.get('shares_repurchased', 0)
        
        if market_cap <= 0:
            return 0
        
        dividend_yield = dividend / market_cap
        buyback_yield = shares_repurchased / market_cap
        
        total_yield = dividend_yield + buyback_yield
        
        return min(100, max(0, total_yield * 1000))
    
    def _assess_input_quality(self, financial_data: Dict[str, Any]) -> float:
        """입력 데이터 품질 평가"""
        required_fields = [
            'net_income', 'operating_income', 'free_cash_flow',
            'total_assets', 'book_value', 'revenue_growth'
        ]
        
        available_fields = sum(1 for field in required_fields if field in financial_data and financial_data[field] is not None)
        
        return available_fields / len(required_fields)
    
    def _get_historical_accuracy(self, model_name: str) -> float:
        """모델별 과거 정확도"""
        # 실제 구현시 과거 성과 데이터 사용
        accuracy_map = {
            ValuationModel.CORE_5_VALUE.value: 0.75,
            ValuationModel.RESIDUAL_INCOME.value: 0.70,
            ValuationModel.DCF_LITE.value: 0.65,
            ValuationModel.EARNINGS_POWER.value: 0.68,
            ValuationModel.ASSET_BASED.value: 0.60,
            ValuationModel.SECTOR_RELATIVE.value: 0.55,
            ValuationModel.MOMENTUM_ADJUSTED.value: 0.62
        }
        
        return accuracy_map.get(model_name, 0.5)
    
    def calculate_ensemble_consensus(self, financial_data: Dict[str, Any], 
                                   market_cap: float, sector_data: Dict[str, Any] = None) -> EnsembleResult:
        """앙상블 합의 계산"""
        logger.info("앙상블 합의 계산")
        
        # 모든 모델 실행
        model_results = [
            self.calculate_core_5_value(financial_data, market_cap),
            self.calculate_residual_income(financial_data, market_cap),
            self.calculate_dcf_lite(financial_data, market_cap),
            self.calculate_earnings_power(financial_data, market_cap),
            self.calculate_asset_based(financial_data, market_cap),
            self.calculate_sector_relative(financial_data, market_cap, sector_data or {}),
            self.calculate_momentum_adjusted(financial_data, market_cap)
        ]
        
        # 유효한 결과만 필터링
        valid_results = [r for r in model_results if r.intrinsic_value > 0]
        
        if not valid_results:
            return EnsembleResult()
        
        # 가중 평균 계산 (신뢰도와 과거 정확도 고려)
        weights = []
        values = []
        
        for result in valid_results:
            # 종합 가중치 = 모델 가중치 × 신뢰도 × 입력 품질 × 과거 정확도
            combined_weight = (
                result.model_weight * 
                result.confidence_score * 
                result.input_quality * 
                result.historical_accuracy
            )
            weights.append(combined_weight)
            values.append(result.intrinsic_value)
        
        # 정규화
        total_weight = sum(weights)
        if total_weight == 0:
            weights = [1/len(valid_results)] * len(valid_results)
        else:
            weights = [w / total_weight for w in weights]
        
        # 합의 가치 계산
        consensus_value = sum(v * w for v, w in zip(values, weights))
        
        # 모델 합의도 계산
        value_std = np.std(values)
        value_mean = np.mean(values)
        disagreement_measure = value_std / value_mean if value_mean > 0 else 1.0
        
        # 이상치 탐지
        outlier_detected = disagreement_measure > 0.3  # 30% 이상 차이시 이상치
        
        # 합의 신뢰도
        avg_confidence = np.mean([r.confidence_score for r in valid_results])
        consensus_confidence = avg_confidence * (1 - disagreement_measure)
        
        # 모델 합의도
        model_agreement = 1 - disagreement_measure
        
        # 권장 가중치 (불확실성이 높을수록 축소)
        recommended_weight = max(0.5, consensus_confidence)
        
        return EnsembleResult(
            consensus_value=consensus_value,
            consensus_confidence=consensus_confidence,
            model_agreement=model_agreement,
            disagreement_measure=disagreement_measure,
            outlier_detected=outlier_detected,
            recommended_weight=recommended_weight,
            individual_results=valid_results
        )
    
    def get_ensemble_summary(self, ensemble_result: EnsembleResult) -> Dict[str, Any]:
        """앙상블 요약 정보"""
        if not ensemble_result.individual_results:
            return {'error': 'no_results'}
        
        summary = {
            'consensus_value': ensemble_result.consensus_value,
            'consensus_confidence': ensemble_result.consensus_confidence,
            'model_agreement': ensemble_result.model_agreement,
            'outlier_detected': ensemble_result.outlier_detected,
            'recommended_weight': ensemble_result.recommended_weight,
            'model_count': len(ensemble_result.individual_results),
            'model_details': {}
        }
        
        # 모델별 상세 정보
        for result in ensemble_result.individual_results:
            summary['model_details'][result.model_name] = {
                'intrinsic_value': result.intrinsic_value,
                'confidence_score': result.confidence_score,
                'model_weight': result.model_weight,
                'input_quality': result.input_quality,
                'historical_accuracy': result.historical_accuracy
            }
        
        return summary

def main():
    """메인 실행 함수 - 테스트"""
    print("="*80)
    print("멀티-모델 앙상블 시스템 테스트")
    print("="*80)
    
    # 시스템 초기화
    ensemble_system = MultiModelEnsembleSystem()
    
    # 테스트 데이터
    test_financial_data = {
        'net_income': 10000000000,      # 100억
        'operating_income': 12000000000, # 120억
        'free_cash_flow': 8000000000,   # 80억
        'total_assets': 100000000000,   # 1조
        'total_liabilities': 40000000000, # 4000억
        'book_value': 60000000000,      # 6000억
        'revenue_growth': 0.08,         # 8%
        'earnings_growth': 0.12,        # 12%
        'debt_ratio': 0.4,              # 40%
        'asset_turnover': 1.2,
        'margin_expansion': 0.02,
        'dividend': 2000000000,         # 20억
        'shares_repurchased': 1000000000, # 10억
        'earnings_history': [9000000000, 9500000000, 10000000000],
        'price_momentum_6m': 0.05,
        'intangible_assets': 5000000000  # 50억
    }
    
    test_sector_data = {
        'avg_per': 15.0,
        'avg_pbr': 1.5,
        'avg_ev_ebit': 12.0
    }
    
    market_cap = 80000000000  # 8000억
    
    print(f"시장가치: {market_cap:,}원")
    print(f"재무 데이터: {len(test_financial_data)}개 항목")
    print()
    
    # 앙상블 합의 계산
    ensemble_result = ensemble_system.calculate_ensemble_consensus(
        test_financial_data, market_cap, test_sector_data
    )
    
    # 결과 출력
    print("="*60)
    print("앙상블 합의 결과")
    print("="*60)
    print(f"합의 내재가치: {ensemble_result.consensus_value:,.0f}원")
    print(f"합의 신뢰도: {ensemble_result.consensus_confidence:.1%}")
    print(f"모델 합의도: {ensemble_result.model_agreement:.1%}")
    print(f"불일치 정도: {ensemble_result.disagreement_measure:.1%}")
    print(f"이상치 탐지: {'예' if ensemble_result.outlier_detected else '아니오'}")
    print(f"권장 가중치: {ensemble_result.recommended_weight:.1%}")
    
    print(f"\n{'='*60}")
    print("개별 모델 결과")
    print(f"{'='*60}")
    
    for result in ensemble_result.individual_results:
        print(f"\n{result.model_name}:")
        print(f"  내재가치: {result.intrinsic_value:,.0f}원")
        print(f"  신뢰도: {result.confidence_score:.1%}")
        print(f"  모델 가중치: {result.model_weight:.1%}")
        print(f"  입력 품질: {result.input_quality:.1%}")
        print(f"  과거 정확도: {result.historical_accuracy:.1%}")
    
    # MoS 계산
    current_price = 70000
    consensus_mos = (ensemble_result.consensus_value - current_price) / ensemble_result.consensus_value
    
    print(f"\n{'='*60}")
    print("최종 투자 신호")
    print(f"{'='*60}")
    print(f"현재 주가: {current_price:,}원")
    print(f"합의 내재가치: {ensemble_result.consensus_value:,.0f}원")
    print(f"안전마진: {consensus_mos:.1%}")
    print(f"투자 신호: {'BUY' if consensus_mos > 0.2 else 'WATCH' if consensus_mos > 0.1 else 'PASS'}")
    
    print(f"\n{'='*80}")
    print("멀티-모델 앙상블 시스템 테스트 완료!")
    print("="*80)

if __name__ == "__main__":
    main()

