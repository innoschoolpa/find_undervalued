"""
베이지안 MoS(안전마진) 업데이트 시스템
- 분기 실적마다 IV(내재가치) 분포 갱신
- 베이지안 추론을 통한 신호 내구성 향상
- "가치 함정" 조기 식별
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from scipy import stats
from scipy.stats import beta, gamma, norm
import warnings
warnings.filterwarnings('ignore')

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class IntrinsicValueDistribution:
    """내재가치 분포"""
    mean: float = 0.0
    std: float = 0.0
    confidence_interval_95: Tuple[float, float] = (0.0, 0.0)
    distribution_type: str = "normal"  # normal, lognormal, beta
    parameters: Dict[str, float] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}

@dataclass
class BayesianMOSUpdate:
    """베이지안 MoS 업데이트"""
    prior_mos: float = 0.0
    posterior_mos: float = 0.0
    update_confidence: float = 0.0
    evidence_strength: float = 0.0
    convergence_rate: float = 0.0
    risk_adjustment: float = 0.0

@dataclass
class FinancialEvidence:
    """재무 증거"""
    # 실적 관련
    revenue_growth: float = 0.0
    earnings_growth: float = 0.0
    margin_expansion: float = 0.0
    cash_flow_growth: float = 0.0
    
    # 품질 관련
    roe_change: float = 0.0
    debt_ratio_change: float = 0.0
    asset_turnover_change: float = 0.0
    
    # 시장 관련
    market_share_change: float = 0.0
    competitive_position: float = 0.0
    industry_trend: float = 0.0
    
    # 위험 관련
    volatility_change: float = 0.0
    beta_change: float = 0.0
    credit_rating_change: float = 0.0

class BayesianMOSSystem:
    """베이지안 MoS 업데이트 시스템"""
    
    def __init__(self):
        self.stock_iv_distributions = {}  # 종목별 IV 분포
        self.mos_history = {}  # MoS 이력
        self.evidence_history = {}  # 증거 이력
        
        # 베이지안 파라미터
        self.prior_parameters = {
            'alpha': 2.0,  # 베타 분포 파라미터
            'beta': 2.0,   # 베타 분포 파라미터
            'learning_rate': 0.3,  # 학습률
            'decay_factor': 0.9,   # 시간 감쇠
            'min_evidence_weight': 0.1  # 최소 증거 가중치
        }
        
    def initialize_stock_distribution(self, symbol: str, initial_iv: float, 
                                    initial_volatility: float = 0.2) -> IntrinsicValueDistribution:
        """종목별 초기 IV 분포 설정"""
        logger.info(f"종목 {symbol} 초기 IV 분포 설정")
        
        # 초기 분포는 정규분포로 가정
        iv_dist = IntrinsicValueDistribution(
            mean=initial_iv,
            std=initial_iv * initial_volatility,
            confidence_interval_95=(
                initial_iv - 1.96 * initial_iv * initial_volatility,
                initial_iv + 1.96 * initial_iv * initial_volatility
            ),
            distribution_type="normal",
            parameters={'mu': initial_iv, 'sigma': initial_iv * initial_volatility}
        )
        
        self.stock_iv_distributions[symbol] = iv_dist
        return iv_dist
    
    def calculate_evidence_strength(self, evidence: FinancialEvidence) -> float:
        """증거 강도 계산"""
        # 각 증거의 가중치
        evidence_weights = {
            'earnings_growth': 0.25,
            'cash_flow_growth': 0.20,
            'roe_change': 0.15,
            'margin_expansion': 0.15,
            'debt_ratio_change': 0.10,
            'market_share_change': 0.10,
            'volatility_change': 0.05
        }
        
        # 증거 점수 계산
        evidence_scores = {
            'earnings_growth': max(-1, min(1, evidence.earnings_growth / 0.1)),  # 10% 성장 = 1점
            'cash_flow_growth': max(-1, min(1, evidence.cash_flow_growth / 0.15)),
            'roe_change': max(-1, min(1, evidence.roe_change / 0.05)),  # 5%p 변화 = 1점
            'margin_expansion': max(-1, min(1, evidence.margin_expansion / 0.03)),
            'debt_ratio_change': max(-1, min(1, -evidence.debt_ratio_change / 0.05)),  # 부채 감소 = 양수
            'market_share_change': max(-1, min(1, evidence.market_share_change / 0.02)),
            'volatility_change': max(-1, min(1, -evidence.volatility_change / 0.05))  # 변동성 감소 = 양수
        }
        
        # 가중 평균 증거 강도
        total_evidence = sum(
            evidence_scores[metric] * weight 
            for metric, weight in evidence_weights.items()
        )
        
        # 0-1 범위로 정규화
        evidence_strength = (total_evidence + 1) / 2
        
        return evidence_strength
    
    def update_iv_distribution(self, symbol: str, new_evidence: FinancialEvidence, 
                             current_price: float) -> IntrinsicValueDistribution:
        """IV 분포 베이지안 업데이트"""
        logger.info(f"종목 {symbol} IV 분포 업데이트")
        
        if symbol not in self.stock_iv_distributions:
            # 초기 분포가 없으면 현재 가격 기반으로 설정
            self.initialize_stock_distribution(symbol, current_price * 1.2)
        
        current_dist = self.stock_iv_distributions[symbol]
        
        # 증거 강도 계산
        evidence_strength = self.calculate_evidence_strength(new_evidence)
        
        # 새로운 IV 추정 (간단한 모델)
        # 증거에 따른 IV 조정
        if evidence_strength > 0.6:  # 강한 긍정적 증거
            iv_adjustment = 1.1
        elif evidence_strength > 0.4:  # 약한 긍정적 증거
            iv_adjustment = 1.05
        elif evidence_strength < 0.4:  # 약한 부정적 증거
            iv_adjustment = 0.95
        else:  # 강한 부정적 증거
            iv_adjustment = 0.9
        
        # 새로운 IV 분포 파라미터 계산
        new_mean = current_dist.mean * iv_adjustment
        
        # 불확실성 조정 (증거가 강할수록 불확실성 감소)
        uncertainty_reduction = evidence_strength * self.prior_parameters['learning_rate']
        new_std = current_dist.std * (1 - uncertainty_reduction)
        
        # 최소 불확실성 보장
        new_std = max(new_std, current_dist.mean * 0.1)
        
        # 새로운 분포 생성
        updated_dist = IntrinsicValueDistribution(
            mean=new_mean,
            std=new_std,
            confidence_interval_95=(
                new_mean - 1.96 * new_std,
                new_mean + 1.96 * new_std
            ),
            distribution_type="normal",
            parameters={'mu': new_mean, 'sigma': new_std}
        )
        
        # 분포 업데이트
        self.stock_iv_distributions[symbol] = updated_dist
        
        # 이력 저장
        if symbol not in self.evidence_history:
            self.evidence_history[symbol] = []
        self.evidence_history[symbol].append({
            'timestamp': datetime.now(),
            'evidence': new_evidence,
            'evidence_strength': evidence_strength,
            'iv_adjustment': iv_adjustment
        })
        
        return updated_dist
    
    def calculate_bayesian_mos(self, symbol: str, current_price: float, 
                             new_evidence: FinancialEvidence) -> BayesianMOSUpdate:
        """베이지안 MoS 계산"""
        logger.info(f"종목 {symbol} 베이지안 MoS 계산")
        
        # IV 분포 업데이트
        updated_dist = self.update_iv_distribution(symbol, new_evidence, current_price)
        
        # 기존 MoS 계산
        prior_iv = self.stock_iv_distributions[symbol].mean
        prior_mos = (prior_iv - current_price) / prior_iv if prior_iv > 0 else 0
        
        # 업데이트된 MoS 계산
        posterior_iv = updated_dist.mean
        posterior_mos = (posterior_iv - current_price) / posterior_iv if posterior_iv > 0 else 0
        
        # 증거 강도
        evidence_strength = self.calculate_evidence_strength(new_evidence)
        
        # 업데이트 신뢰도 (분포의 불확실성 기반)
        confidence = 1 - (updated_dist.std / updated_dist.mean) if updated_dist.mean > 0 else 0
        
        # 수렴률 (이전 업데이트 대비 변화율)
        if symbol in self.mos_history and len(self.mos_history[symbol]) > 0:
            last_mos = self.mos_history[symbol][-1]['mos']
            convergence_rate = abs(posterior_mos - last_mos) / max(abs(last_mos), 0.01)
        else:
            convergence_rate = 1.0  # 첫 업데이트
        
        # 리스크 조정 (불확실성이 높을수록 MoS 축소)
        risk_adjustment = min(1.0, confidence / 0.8)  # 80% 신뢰도 기준
        
        # 최종 MoS (리스크 조정 적용)
        final_mos = posterior_mos * risk_adjustment
        
        # 결과 생성
        mos_update = BayesianMOSUpdate(
            prior_mos=prior_mos,
            posterior_mos=final_mos,
            update_confidence=confidence,
            evidence_strength=evidence_strength,
            convergence_rate=convergence_rate,
            risk_adjustment=risk_adjustment
        )
        
        # 이력 저장
        if symbol not in self.mos_history:
            self.mos_history[symbol] = []
        self.mos_history[symbol].append({
            'timestamp': datetime.now(),
            'mos': final_mos,
            'confidence': confidence,
            'evidence_strength': evidence_strength,
            'iv_mean': updated_dist.mean,
            'iv_std': updated_dist.std
        })
        
        return mos_update
    
    def detect_value_trap(self, symbol: str, lookback_periods: int = 4) -> Dict[str, Any]:
        """가치 함정 탐지"""
        logger.info(f"종목 {symbol} 가치 함정 탐지")
        
        if symbol not in self.mos_history or len(self.mos_history[symbol]) < lookback_periods:
            return {'is_value_trap': False, 'confidence': 0.0, 'reason': 'insufficient_data'}
        
        # 최근 MoS 이력 분석
        recent_history = self.mos_history[symbol][-lookback_periods:]
        
        # 가치 함정 지표들
        mos_trend = [h['mos'] for h in recent_history]
        confidence_trend = [h['confidence'] for h in recent_history]
        evidence_trend = [h['evidence_strength'] for h in recent_history]
        
        # 1. MoS 지속적 하락
        mos_decline = (mos_trend[0] - mos_trend[-1]) / max(mos_trend[0], 0.01)
        
        # 2. 신뢰도 하락
        confidence_decline = (confidence_trend[0] - confidence_trend[-1]) / max(confidence_trend[0], 0.01)
        
        # 3. 증거 강도 약화
        evidence_decline = (evidence_trend[0] - evidence_trend[-1]) / max(evidence_trend[0], 0.01)
        
        # 4. 변동성 증가 (불확실성 증가)
        iv_std_trend = [h['iv_std'] for h in recent_history]
        volatility_increase = (iv_std_trend[-1] - iv_std_trend[0]) / max(iv_std_trend[0], 0.01)
        
        # 가치 함정 점수 (0-1, 높을수록 함정 가능성)
        trap_score = (
            mos_decline * 0.4 +           # MoS 하락
            confidence_decline * 0.3 +    # 신뢰도 하락
            evidence_decline * 0.2 +      # 증거 약화
            volatility_increase * 0.1     # 불확실성 증가
        )
        
        is_value_trap = trap_score > 0.3  # 30% 이상이면 가치 함정 의심
        
        # 함정 유형 분류
        trap_type = "none"
        if is_value_trap:
            if mos_decline > 0.2:
                trap_type = "earnings_deterioration"
            elif confidence_decline > 0.2:
                trap_type = "uncertainty_increase"
            elif evidence_decline > 0.2:
                trap_type = "competitive_decline"
            else:
                trap_type = "general_deterioration"
        
        return {
            'is_value_trap': is_value_trap,
            'trap_score': trap_score,
            'trap_type': trap_type,
            'confidence': min(trap_score * 2, 1.0),
            'indicators': {
                'mos_decline': mos_decline,
                'confidence_decline': confidence_decline,
                'evidence_decline': evidence_decline,
                'volatility_increase': volatility_increase
            },
            'recommendation': self._get_trap_recommendation(trap_type, trap_score)
        }
    
    def _get_trap_recommendation(self, trap_type: str, trap_score: float) -> str:
        """가치 함정 권고사항"""
        if trap_score < 0.2:
            return "정상 범위 - 지속 관찰"
        elif trap_score < 0.4:
            return "주의 필요 - 신호 모니터링 강화"
        elif trap_score < 0.6:
            return "경계 필요 - 포지션 축소 고려"
        else:
            return "위험 신호 - 매도 검토 필요"
    
    def get_portfolio_mos_summary(self, portfolio_symbols: List[str]) -> Dict[str, Any]:
        """포트폴리오 MoS 종합 요약"""
        logger.info("포트폴리오 MoS 종합 요약")
        
        portfolio_mos = []
        portfolio_confidence = []
        value_traps = []
        
        for symbol in portfolio_symbols:
            if symbol in self.mos_history:
                latest_mos = self.mos_history[symbol][-1]
                portfolio_mos.append(latest_mos['mos'])
                portfolio_confidence.append(latest_mos['confidence'])
                
                # 가치 함정 체크
                trap_info = self.detect_value_trap(symbol)
                if trap_info['is_value_trap']:
                    value_traps.append({
                        'symbol': symbol,
                        'trap_type': trap_info['trap_type'],
                        'trap_score': trap_info['trap_score']
                    })
        
        if not portfolio_mos:
            return {'error': 'no_data'}
        
        summary = {
            'portfolio_size': len(portfolio_symbols),
            'avg_mos': np.mean(portfolio_mos),
            'median_mos': np.median(portfolio_mos),
            'mos_std': np.std(portfolio_mos),
            'min_mos': np.min(portfolio_mos),
            'max_mos': np.max(portfolio_mos),
            'avg_confidence': np.mean(portfolio_confidence),
            'high_confidence_ratio': sum(1 for c in portfolio_confidence if c > 0.7) / len(portfolio_confidence),
            'value_traps': value_traps,
            'trap_count': len(value_traps),
            'trap_ratio': len(value_traps) / len(portfolio_symbols)
        }
        
        return summary
    
    def export_analysis_report(self, symbols: List[str]) -> Dict[str, Any]:
        """분석 보고서 생성"""
        logger.info("베이지안 MoS 분석 보고서 생성")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'analysis_type': 'Bayesian MOS Update',
            'stocks_analyzed': len(symbols),
            'stock_details': {},
            'portfolio_summary': self.get_portfolio_mos_summary(symbols)
        }
        
        # 종목별 상세 분석
        for symbol in symbols:
            if symbol in self.mos_history:
                latest_mos = self.mos_history[symbol][-1]
                trap_info = self.detect_value_trap(symbol)
                
                report['stock_details'][symbol] = {
                    'current_mos': latest_mos['mos'],
                    'confidence': latest_mos['confidence'],
                    'evidence_strength': latest_mos['evidence_strength'],
                    'iv_mean': latest_mos['iv_mean'],
                    'iv_std': latest_mos['iv_std'],
                    'value_trap_analysis': trap_info,
                    'history_length': len(self.mos_history[symbol])
                }
        
        return report

def main():
    """메인 실행 함수 - 테스트"""
    print("="*80)
    print("베이지안 MoS 업데이트 시스템 테스트")
    print("="*80)
    
    # 시스템 초기화
    bayesian_system = BayesianMOSSystem()
    
    # 테스트 종목들
    test_stocks = {
        'SAMSUNG': {
            'current_price': 70000,
            'initial_iv': 85000,
            'scenarios': [
                {
                    'name': '긍정적 실적',
                    'evidence': FinancialEvidence(
                        earnings_growth=0.15,
                        cash_flow_growth=0.20,
                        roe_change=0.03,
                        margin_expansion=0.02
                    )
                },
                {
                    'name': '부정적 실적',
                    'evidence': FinancialEvidence(
                        earnings_growth=-0.05,
                        cash_flow_growth=-0.10,
                        roe_change=-0.02,
                        debt_ratio_change=0.05
                    )
                }
            ]
        },
        'LG': {
            'current_price': 45000,
            'initial_iv': 55000,
            'scenarios': [
                {
                    'name': '안정적 성장',
                    'evidence': FinancialEvidence(
                        earnings_growth=0.08,
                        cash_flow_growth=0.10,
                        roe_change=0.01,
                        market_share_change=0.01
                    )
                }
            ]
        }
    }
    
    # 각 종목별 시나리오 테스트
    for symbol, stock_data in test_stocks.items():
        print(f"\n{'='*60}")
        print(f"종목: {symbol}")
        print(f"{'='*60}")
        
        current_price = stock_data['current_price']
        initial_iv = stock_data['initial_iv']
        
        # 초기 분포 설정
        bayesian_system.initialize_stock_distribution(symbol, initial_iv)
        initial_mos = (initial_iv - current_price) / initial_iv
        print(f"초기 MoS: {initial_mos:.1%}")
        
        # 각 시나리오별 업데이트
        for scenario in stock_data['scenarios']:
            print(f"\n시나리오: {scenario['name']}")
            print("-" * 40)
            
            mos_update = bayesian_system.calculate_bayesian_mos(
                symbol, current_price, scenario['evidence']
            )
            
            print(f"Prior MoS: {mos_update.prior_mos:.1%}")
            print(f"Posterior MoS: {mos_update.posterior_mos:.1%}")
            print(f"업데이트 신뢰도: {mos_update.update_confidence:.1%}")
            print(f"증거 강도: {mos_update.evidence_strength:.1%}")
            print(f"리스크 조정: {mos_update.risk_adjustment:.1%}")
            
            # 가치 함정 분석
            trap_analysis = bayesian_system.detect_value_trap(symbol)
            if trap_analysis['is_value_trap']:
                print(f"⚠️ 가치 함정 탐지: {trap_analysis['trap_type']} (점수: {trap_analysis['trap_score']:.2f})")
                print(f"권고사항: {trap_analysis['recommendation']}")
    
    # 포트폴리오 요약
    print(f"\n{'='*80}")
    print("포트폴리오 MoS 요약")
    print(f"{'='*80}")
    
    portfolio_summary = bayesian_system.get_portfolio_mos_summary(list(test_stocks.keys()))
    if 'error' not in portfolio_summary:
        print(f"평균 MoS: {portfolio_summary['avg_mos']:.1%}")
        print(f"평균 신뢰도: {portfolio_summary['avg_confidence']:.1%}")
        print(f"고신뢰도 비율: {portfolio_summary['high_confidence_ratio']:.1%}")
        print(f"가치 함정 종목: {portfolio_summary['trap_count']}개")
    
    print(f"\n{'='*80}")
    print("베이지안 MoS 시스템 테스트 완료!")
    print("="*80)

if __name__ == "__main__":
    main()

