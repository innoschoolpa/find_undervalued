#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
포트폴리오 최적화 모듈

포트폴리오 구성 최적화 및 리스크 관리 기능을 제공합니다.
"""

import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from scipy.optimize import minimize
import json

@dataclass
class PortfolioConfig:
    """포트폴리오 설정 데이터 클래스"""
    max_stocks: int = 20
    min_weight: float = 0.01  # 1%
    max_weight: float = 0.15  # 15%
    rebalance_frequency: str = "monthly"  # monthly, quarterly, yearly
    risk_target: float = 0.12  # 12% 목표 변동성
    risk_free_rate: float = 0.03  # 3% 무위험 수익률
    transaction_cost: float = 0.0015  # 0.15%
    max_turnover: float = 0.30  # 30% 최대 회전율

@dataclass
class OptimizationResult:
    """최적화 결과 데이터 클래스"""
    optimal_weights: Dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    diversification_ratio: float
    concentration_risk: float
    optimization_method: str
    convergence_achieved: bool

class PortfolioOptimizer:
    """포트폴리오 최적화 클래스"""
    
    def __init__(self, config: Optional[PortfolioConfig] = None):
        self.logger = logging.getLogger(__name__)
        
        if config:
            self.config = config
        else:
            self.config = self._load_config_from_env()
        
        self.returns_data = None
        self.covariance_matrix = None
        
        self.logger.info("포트폴리오 최적화 엔진 초기화 완료")
    
    def _load_config_from_env(self) -> PortfolioConfig:
        """환경변수에서 설정 로드"""
        return PortfolioConfig(
            max_stocks=int(os.getenv('PORTFOLIO_MAX_STOCKS', '20')),
            min_weight=float(os.getenv('PORTFOLIO_MIN_WEIGHT', '0.01')),
            max_weight=float(os.getenv('PORTFOLIO_MAX_WEIGHT', '0.15')),
            rebalance_frequency=os.getenv('PORTFOLIO_REBALANCE_FREQUENCY', 'monthly'),
            risk_target=float(os.getenv('PORTFOLIO_RISK_TARGET', '0.12')),
            risk_free_rate=float(os.getenv('PORTFOLIO_RISK_FREE_RATE', '0.03')),
            transaction_cost=float(os.getenv('PORTFOLIO_TRANSACTION_COST', '0.0015')),
            max_turnover=float(os.getenv('PORTFOLIO_MAX_TURNOVER', '0.30'))
        )
    
    def load_data(self, returns_data: pd.DataFrame) -> None:
        """수익률 데이터 로드"""
        self.returns_data = returns_data
        self.covariance_matrix = returns_data.cov()
        
        self.logger.info(f"데이터 로드 완료: {len(returns_data.columns)}개 종목, {len(returns_data)}개 관측치")
    
    def _generate_sample_data(self, symbols: List[str], periods: int = 252) -> pd.DataFrame:
        """샘플 수익률 데이터 생성"""
        np.random.seed(42)  # 재현 가능한 결과
        
        # 각 종목별 수익률 생성
        returns_data = {}
        
        for symbol in symbols:
            # 랜덤 수익률 생성 (평균 0.0008, 표준편차 0.02)
            returns = np.random.normal(0.0008, 0.02, periods)
            returns_data[symbol] = returns
        
        return pd.DataFrame(returns_data)
    
    def mean_variance_optimization(self, expected_returns: Optional[pd.Series] = None) -> OptimizationResult:
        """평균-분산 최적화 (Markowitz)"""
        if self.returns_data is None:
            raise ValueError("수익률 데이터가 로드되지 않았습니다")
        
        n_assets = len(self.returns_data.columns)
        symbols = self.returns_data.columns.tolist()
        
        # 예상 수익률 계산
        if expected_returns is None:
            expected_returns = self.returns_data.mean() * 252  # 연환산
        
        # 공분산 행렬
        cov_matrix = self.covariance_matrix * 252  # 연환산
        
        # 목적 함수: -샤프 비율 (최대화하기 위해 음수)
        def objective(weights):
            portfolio_return = np.sum(expected_returns * weights)
            portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            sharpe_ratio = (portfolio_return - self.config.risk_free_rate) / portfolio_volatility
            return -sharpe_ratio  # 최대화하기 위해 음수
        
        # 제약 조건
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}  # 가중치 합 = 1
        ]
        
        # 경계 조건
        bounds = [(self.config.min_weight, self.config.max_weight) for _ in range(n_assets)]
        
        # 초기값
        x0 = np.array([1/n_assets] * n_assets)
        
        # 최적화 실행
        result = minimize(
            objective, x0, method='SLSQP',
            bounds=bounds, constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            optimal_weights = dict(zip(symbols, result.x))
            
            # 성과 지표 계산
            portfolio_return = np.sum(expected_returns * result.x)
            portfolio_volatility = np.sqrt(np.dot(result.x.T, np.dot(cov_matrix, result.x)))
            sharpe_ratio = (portfolio_return - self.config.risk_free_rate) / portfolio_volatility
            
            return OptimizationResult(
                optimal_weights=optimal_weights,
                expected_return=portfolio_return,
                expected_volatility=portfolio_volatility,
                sharpe_ratio=sharpe_ratio,
                diversification_ratio=self._calculate_diversification_ratio(optimal_weights),
                concentration_risk=self._calculate_concentration_risk(optimal_weights),
                optimization_method="Mean-Variance",
                convergence_achieved=True
            )
        else:
            self.logger.warning("최적화 수렴 실패")
            return OptimizationResult(
                optimal_weights={},
                expected_return=0,
                expected_volatility=0,
                sharpe_ratio=0,
                diversification_ratio=0,
                concentration_risk=0,
                optimization_method="Mean-Variance",
                convergence_achieved=False
            )
    
    def risk_parity_optimization(self) -> OptimizationResult:
        """리스크 패리티 최적화"""
        if self.returns_data is None:
            raise ValueError("수익률 데이터가 로드되지 않았습니다")
        
        n_assets = len(self.returns_data.columns)
        symbols = self.returns_data.columns.tolist()
        
        # 공분산 행렬
        cov_matrix = self.covariance_matrix * 252  # 연환산
        
        # 목적 함수: 리스크 기여도의 분산 최소화
        def objective(weights):
            portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            risk_contributions = (weights * np.dot(cov_matrix, weights)) / portfolio_volatility
            target_contribution = 1 / n_assets
            return np.sum((risk_contributions - target_contribution) ** 2)
        
        # 제약 조건
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}  # 가중치 합 = 1
        ]
        
        # 경계 조건
        bounds = [(self.config.min_weight, self.config.max_weight) for _ in range(n_assets)]
        
        # 초기값 (동일 가중)
        x0 = np.array([1/n_assets] * n_assets)
        
        # 최적화 실행
        result = minimize(
            objective, x0, method='SLSQP',
            bounds=bounds, constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            optimal_weights = dict(zip(symbols, result.x))
            
            # 성과 지표 계산
            expected_returns = self.returns_data.mean() * 252
            portfolio_return = np.sum(expected_returns * result.x)
            portfolio_volatility = np.sqrt(np.dot(result.x.T, np.dot(cov_matrix, result.x)))
            sharpe_ratio = (portfolio_return - self.config.risk_free_rate) / portfolio_volatility
            
            return OptimizationResult(
                optimal_weights=optimal_weights,
                expected_return=portfolio_return,
                expected_volatility=portfolio_volatility,
                sharpe_ratio=sharpe_ratio,
                diversification_ratio=self._calculate_diversification_ratio(optimal_weights),
                concentration_risk=self._calculate_concentration_risk(optimal_weights),
                optimization_method="Risk Parity",
                convergence_achieved=True
            )
        else:
            self.logger.warning("리스크 패리티 최적화 수렴 실패")
            return OptimizationResult(
                optimal_weights={},
                expected_return=0,
                expected_volatility=0,
                sharpe_ratio=0,
                diversification_ratio=0,
                concentration_risk=0,
                optimization_method="Risk Parity",
                convergence_achieved=False
            )
    
    def equal_weight_portfolio(self) -> OptimizationResult:
        """동일 가중 포트폴리오"""
        if self.returns_data is None:
            raise ValueError("수익률 데이터가 로드되지 않았습니다")
        
        n_assets = len(self.returns_data.columns)
        symbols = self.returns_data.columns.tolist()
        
        # 동일 가중
        equal_weights = {symbol: 1/n_assets for symbol in symbols}
        
        # 성과 지표 계산
        expected_returns = self.returns_data.mean() * 252
        weights_array = np.array([1/n_assets] * n_assets)
        cov_matrix = self.covariance_matrix * 252
        
        portfolio_return = np.sum(expected_returns * weights_array)
        portfolio_volatility = np.sqrt(np.dot(weights_array.T, np.dot(cov_matrix, weights_array)))
        sharpe_ratio = (portfolio_return - self.config.risk_free_rate) / portfolio_volatility
        
        return OptimizationResult(
            optimal_weights=equal_weights,
            expected_return=portfolio_return,
            expected_volatility=portfolio_volatility,
            sharpe_ratio=sharpe_ratio,
            diversification_ratio=self._calculate_diversification_ratio(equal_weights),
            concentration_risk=self._calculate_concentration_risk(equal_weights),
            optimization_method="Equal Weight",
            convergence_achieved=True
        )
    
    def _calculate_diversification_ratio(self, weights: Dict[str, float]) -> float:
        """다각화 비율 계산"""
        if self.returns_data is None:
            return 0
        
        symbols = list(weights.keys())
        weights_array = np.array([weights[symbol] for symbol in symbols])
        
        # 개별 자산의 가중 평균 변동성
        individual_volatilities = self.returns_data[symbols].std() * np.sqrt(252)
        weighted_avg_vol = np.sum(weights_array * individual_volatilities)
        
        # 포트폴리오 변동성
        cov_matrix = self.covariance_matrix.loc[symbols, symbols] * 252
        portfolio_vol = np.sqrt(np.dot(weights_array.T, np.dot(cov_matrix, weights_array)))
        
        return weighted_avg_vol / portfolio_vol if portfolio_vol > 0 else 0
    
    def _calculate_concentration_risk(self, weights: Dict[str, float]) -> float:
        """집중도 리스크 계산 (허핀달 지수)"""
        weights_array = np.array(list(weights.values()))
        return np.sum(weights_array ** 2)
    
    def optimize_portfolio(self, method: str = "mean_variance", 
                          expected_returns: Optional[pd.Series] = None) -> OptimizationResult:
        """포트폴리오 최적화 실행"""
        if method == "mean_variance":
            return self.mean_variance_optimization(expected_returns)
        elif method == "risk_parity":
            return self.risk_parity_optimization()
        elif method == "equal_weight":
            return self.equal_weight_portfolio()
        else:
            raise ValueError(f"지원하지 않는 최적화 방법: {method}")
    
    def compare_strategies(self, symbols: List[str]) -> Dict[str, OptimizationResult]:
        """여러 전략 비교"""
        if self.returns_data is None:
            # 샘플 데이터 생성
            self.load_data(self._generate_sample_data(symbols))
        
        strategies = ["equal_weight", "mean_variance", "risk_parity"]
        results = {}
        
        for strategy in strategies:
            try:
                result = self.optimize_portfolio(strategy)
                results[strategy] = result
                self.logger.info(f"{strategy} 전략 최적화 완료")
            except Exception as e:
                self.logger.error(f"{strategy} 전략 최적화 실패: {e}")
                results[strategy] = OptimizationResult(
                    optimal_weights={},
                    expected_return=0,
                    expected_volatility=0,
                    sharpe_ratio=0,
                    diversification_ratio=0,
                    concentration_risk=0,
                    optimization_method=strategy,
                    convergence_achieved=False
                )
        
        return results
    
    def save_optimization_results(self, results: Dict[str, OptimizationResult], 
                                filename: str = None) -> str:
        """최적화 결과 저장"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"portfolio_optimization_{timestamp}.json"
        
        # JSON 직렬화 가능한 형태로 변환
        results_dict = {}
        
        for strategy, result in results.items():
            results_dict[strategy] = {
                'optimal_weights': result.optimal_weights,
                'expected_return': result.expected_return,
                'expected_volatility': result.expected_volatility,
                'sharpe_ratio': result.sharpe_ratio,
                'diversification_ratio': result.diversification_ratio,
                'concentration_risk': result.concentration_risk,
                'optimization_method': result.optimization_method,
                'convergence_achieved': result.convergence_achieved
            }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"포트폴리오 최적화 결과 저장: {filename}")
        return filename

def create_portfolio_optimizer(config: Optional[PortfolioConfig] = None) -> PortfolioOptimizer:
    """포트폴리오 최적화 엔진 인스턴스 생성"""
    return PortfolioOptimizer(config)

if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)
    
    # 포트폴리오 최적화 엔진 생성
    optimizer = create_portfolio_optimizer()
    
    # 테스트 종목
    test_symbols = ['005930', '000270', '035420', '012330', '005380', '000660', '035720']
    
    # 전략 비교
    results = optimizer.compare_strategies(test_symbols)
    
    print("포트폴리오 최적화 결과 비교:")
    print("=" * 60)
    
    for strategy, result in results.items():
        print(f"\n{strategy.upper()} 전략:")
        print(f"  예상 수익률: {result.expected_return:.2%}")
        print(f"  예상 변동성: {result.expected_volatility:.2%}")
        print(f"  샤프 비율: {result.sharpe_ratio:.2f}")
        print(f"  다각화 비율: {result.diversification_ratio:.2f}")
        print(f"  집중도 리스크: {result.concentration_risk:.3f}")
        print(f"  수렴 여부: {'성공' if result.convergence_achieved else '실패'}")
        
        if result.optimal_weights:
            print("  주요 종목 가중치:")
            sorted_weights = sorted(result.optimal_weights.items(), key=lambda x: x[1], reverse=True)
            for symbol, weight in sorted_weights[:5]:  # 상위 5개
                print(f"    {symbol}: {weight:.2%}")










