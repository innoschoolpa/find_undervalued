#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
백테스팅 엔진 모듈

투자 전략의 과거 성과를 검증하는 백테스팅 기능을 제공합니다.
"""

import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import json

@dataclass
class BacktestConfig:
    """백테스팅 설정 데이터 클래스"""
    start_date: str = "2020-01-01"
    end_date: str = "2024-12-31"
    initial_capital: float = 100000000  # 1억원
    transaction_cost: float = 0.0015  # 0.15%
    rebalance_frequency: str = "monthly"  # monthly, quarterly, yearly
    max_positions: int = 20
    min_weight: float = 0.01  # 1%
    max_weight: float = 0.15  # 15%

@dataclass
class BacktestResult:
    """백테스팅 결과 데이터 클래스"""
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    profit_factor: float
    equity_curve: List[float] = field(default_factory=list)
    trades: List[Dict[str, Any]] = field(default_factory=list)
    monthly_returns: List[float] = field(default_factory=list)

class BacktestingEngine:
    """백테스팅 엔진 클래스"""
    
    def __init__(self, config: Optional[BacktestConfig] = None):
        self.logger = logging.getLogger(__name__)
        
        if config:
            self.config = config
        else:
            self.config = self._load_config_from_env()
        
        self.portfolio_history = []
        self.trade_history = []
        self.equity_curve = []
        
        self.logger.info("백테스팅 엔진 초기화 완료")
    
    def _load_config_from_env(self) -> BacktestConfig:
        """환경변수에서 설정 로드"""
        return BacktestConfig(
            start_date=os.getenv('BACKTEST_START_DATE', '2020-01-01'),
            end_date=os.getenv('BACKTEST_END_DATE', '2024-12-31'),
            initial_capital=float(os.getenv('BACKTEST_INITIAL_CAPITAL', '100000000')),
            transaction_cost=float(os.getenv('BACKTEST_TRANSACTION_COST', '0.0015')),
            rebalance_frequency=os.getenv('BACKTEST_REBALANCE_FREQUENCY', 'monthly'),
            max_positions=int(os.getenv('BACKTEST_MAX_POSITIONS', '20')),
            min_weight=float(os.getenv('BACKTEST_MIN_WEIGHT', '0.01')),
            max_weight=float(os.getenv('BACKTEST_MAX_WEIGHT', '0.15'))
        )
    
    def _load_price_data(self, symbols: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """가격 데이터 로드 (시뮬레이션)"""
        # 실제 구현에서는 KIS API나 다른 데이터 소스에서 로드
        # 여기서는 시뮬레이션 데이터 생성
        
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        price_data = pd.DataFrame(index=date_range)
        
        for symbol in symbols:
            # 랜덤 워크로 가격 시뮬레이션
            np.random.seed(hash(symbol) % 2**32)  # 재현 가능한 랜덤
            returns = np.random.normal(0.0005, 0.02, len(date_range))  # 일일 수익률
            prices = 100 * np.cumprod(1 + returns)  # 초기 가격 100원에서 시작
            
            price_data[symbol] = prices
        
        return price_data
    
    def _calculate_portfolio_weights(self, scores: Dict[str, float], date: str) -> Dict[str, float]:
        """포트폴리오 가중치 계산"""
        if not scores:
            return {}
        
        # 점수 기반 정렬 및 필터링
        sorted_symbols = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # 최대 포지션 수 제한
        selected_symbols = sorted_symbols[:self.config.max_positions]
        
        # 가중치 계산 (점수 기반)
        total_score = sum(score for _, score in selected_symbols)
        weights = {}
        
        for symbol, score in selected_symbols:
            weight = score / total_score if total_score > 0 else 0
            
            # 가중치 제한 적용
            weight = max(self.config.min_weight, min(self.config.max_weight, weight))
            weights[symbol] = weight
        
        # 가중치 정규화
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {symbol: weight / total_weight for symbol, weight in weights.items()}
        
        return weights
    
    def _calculate_transaction_cost(self, old_weights: Dict[str, float], 
                                  new_weights: Dict[str, float], 
                                  portfolio_value: float) -> float:
        """거래 비용 계산"""
        total_turnover = 0
        
        all_symbols = set(old_weights.keys()) | set(new_weights.keys())
        
        for symbol in all_symbols:
            old_weight = old_weights.get(symbol, 0)
            new_weight = new_weights.get(symbol, 0)
            turnover = abs(new_weight - old_weight)
            total_turnover += turnover
        
        return total_turnover * portfolio_value * self.config.transaction_cost
    
    def _rebalance_portfolio(self, current_weights: Dict[str, float],
                           target_weights: Dict[str, float],
                           portfolio_value: float) -> Tuple[Dict[str, float], float]:
        """포트폴리오 리밸런싱"""
        # 거래 비용 계산
        transaction_cost = self._calculate_transaction_cost(current_weights, target_weights, portfolio_value)
        
        # 거래 비용 차감
        adjusted_value = portfolio_value - transaction_cost
        
        # 새로운 포지션 크기 계산
        new_positions = {}
        for symbol, weight in target_weights.items():
            new_positions[symbol] = weight * adjusted_value
        
        return new_positions, transaction_cost
    
    def run_backtest(self, strategy_function, symbols: List[str]) -> BacktestResult:
        """백테스팅 실행"""
        self.logger.info(f"백테스팅 시작: {self.config.start_date} ~ {self.config.end_date}")
        
        # 가격 데이터 로드
        price_data = self._load_price_data(symbols, self.config.start_date, self.config.end_date)
        
        # 초기 설정
        portfolio_value = self.config.initial_capital
        current_weights = {}
        equity_curve = [portfolio_value]
        trades = []
        
        # 리밸런싱 날짜 생성
        if self.config.rebalance_frequency == "monthly":
            rebalance_dates = pd.date_range(
                start=self.config.start_date, 
                end=self.config.end_date, 
                freq='MS'  # Month Start
            )
        elif self.config.rebalance_frequency == "quarterly":
            rebalance_dates = pd.date_range(
                start=self.config.start_date, 
                end=self.config.end_date, 
                freq='QS'  # Quarter Start
            )
        else:  # yearly
            rebalance_dates = pd.date_range(
                start=self.config.start_date, 
                end=self.config.end_date, 
                freq='YS'  # Year Start
            )
        
        # 백테스팅 실행
        for date in rebalance_dates:
            if date not in price_data.index:
                continue
            
            # 전략 함수로 점수 계산
            current_prices = {symbol: price_data.loc[date, symbol] for symbol in symbols if symbol in price_data.columns}
            scores = strategy_function(current_prices, date.strftime('%Y-%m-%d'))
            
            if scores:
                # 목표 가중치 계산
                target_weights = self._calculate_portfolio_weights(scores, date.strftime('%Y-%m-%d'))
                
                # 포트폴리오 리밸런싱
                new_positions, transaction_cost = self._rebalance_portfolio(
                    current_weights, target_weights, portfolio_value
                )
                
                # 포트폴리오 가치 업데이트
                portfolio_value = sum(new_positions.values())
                current_weights = target_weights
                
                # 거래 기록
                trade_record = {
                    'date': date.strftime('%Y-%m-%d'),
                    'transaction_cost': transaction_cost,
                    'portfolio_value': portfolio_value,
                    'positions': new_positions.copy(),
                    'weights': target_weights.copy()
                }
                trades.append(trade_record)
                
                equity_curve.append(portfolio_value)
        
        # 결과 계산
        result = self._calculate_performance_metrics(equity_curve, trades)
        
        self.logger.info(f"백테스팅 완료: 총 수익률 {result.total_return:.2%}")
        return result
    
    def _calculate_performance_metrics(self, equity_curve: List[float], trades: List[Dict[str, Any]]) -> BacktestResult:
        """성과 지표 계산"""
        if len(equity_curve) < 2:
            return BacktestResult(0, 0, 0, 0, 0, 0, 0, 0)
        
        equity_series = pd.Series(equity_curve)
        
        # 기본 수익률 지표
        total_return = (equity_series.iloc[-1] / equity_series.iloc[0]) - 1
        
        # 연환산 수익률
        days = len(equity_curve) - 1
        annualized_return = (1 + total_return) ** (365 / days) - 1
        
        # 일일 수익률 계산
        daily_returns = equity_series.pct_change().dropna()
        
        # 변동성
        volatility = daily_returns.std() * np.sqrt(365)
        
        # 샤프 비율 (무위험 수익률 3% 가정)
        risk_free_rate = 0.03
        sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        # 최대 낙폭
        cumulative_returns = (1 + daily_returns).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # 거래 통계
        total_trades = len(trades)
        winning_trades = sum(1 for trade in trades if trade['portfolio_value'] > self.config.initial_capital)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # 월별 수익률
        monthly_returns = []
        for trade in trades:
            if len(monthly_returns) == 0:
                prev_value = self.config.initial_capital
            else:
                prev_value = monthly_returns[-1]
            
            monthly_return = (trade['portfolio_value'] / prev_value) - 1
            monthly_returns.append(monthly_return)
        
        # 수익 팩터
        gross_profit = sum(monthly_returns[i] for i in range(len(monthly_returns)) if monthly_returns[i] > 0)
        gross_loss = abs(sum(monthly_returns[i] for i in range(len(monthly_returns)) if monthly_returns[i] < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return BacktestResult(
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            total_trades=total_trades,
            profit_factor=profit_factor,
            equity_curve=equity_curve,
            trades=trades,
            monthly_returns=monthly_returns
        )
    
    def save_results(self, result: BacktestResult, filename: str = None) -> str:
        """백테스팅 결과 저장"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"backtest_results_{timestamp}.json"
        
        # JSON 직렬화 가능한 형태로 변환
        result_dict = {
            'total_return': result.total_return,
            'annualized_return': result.annualized_return,
            'volatility': result.volatility,
            'sharpe_ratio': result.sharpe_ratio,
            'max_drawdown': result.max_drawdown,
            'win_rate': result.win_rate,
            'total_trades': result.total_trades,
            'profit_factor': result.profit_factor,
            'equity_curve': result.equity_curve,
            'monthly_returns': result.monthly_returns,
            'trades': result.trades
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"백테스팅 결과 저장: {filename}")
        return filename

def create_backtesting_engine(config: Optional[BacktestConfig] = None) -> BacktestingEngine:
    """백테스팅 엔진 인스턴스 생성"""
    return BacktestingEngine(config)

# 샘플 전략 함수
def sample_value_strategy(prices: Dict[str, float], date: str) -> Dict[str, float]:
    """샘플 밸류 투자 전략"""
    scores = {}
    
    for symbol, price in prices.items():
        # 간단한 밸류 점수 계산 (가격이 낮을수록 높은 점수)
        score = 100 / price  # 가격의 역수
        scores[symbol] = score
    
    return scores

if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)
    
    # 백테스팅 엔진 생성
    engine = create_backtesting_engine()
    
    # 테스트 종목
    test_symbols = ['005930', '000270', '035420', '012330', '005380']
    
    # 백테스팅 실행
    result = engine.run_backtest(sample_value_strategy, test_symbols)
    
    print("백테스팅 결과:")
    print(f"총 수익률: {result.total_return:.2%}")
    print(f"연환산 수익률: {result.annualized_return:.2%}")
    print(f"변동성: {result.volatility:.2%}")
    print(f"샤프 비율: {result.sharpe_ratio:.2f}")
    print(f"최대 낙폭: {result.max_drawdown:.2%}")
    print(f"승률: {result.win_rate:.2%}")
    print(f"총 거래 수: {result.total_trades}")
    print(f"수익 팩터: {result.profit_factor:.2f}")