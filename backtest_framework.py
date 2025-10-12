#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
백테스트 프레임워크
룩어헤드 바이어스 방지, 시점 일관성 보장
"""

import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """백테스트 설정"""
    start_date: datetime
    end_date: datetime
    rebalance_frequency: str  # 'monthly', 'quarterly'
    initial_capital: float = 100_000_000  # 1억원
    max_stocks: int = 20
    max_weight_per_stock: float = 0.10  # 10%
    max_sector_weight: float = 0.30  # 30%
    transaction_cost: float = 0.0015  # 0.15% (편도)
    slippage: float = 0.001  # 0.1%
    
    # 가치주 선정 기준
    score_threshold: float = 110.0
    mos_threshold: float = 20.0
    
    # 데이터 정합성
    financial_lag_days: int = 90  # 재무제표 공시 후 90일 지연
    price_lag_days: int = 2  # 가격 데이터 2영업일 지연


@dataclass
class BacktestResult:
    """백테스트 결과"""
    config: BacktestConfig
    total_return: float  # 총 수익률 (%)
    annualized_return: float  # 연환산 수익률 (%)
    sharpe_ratio: float
    max_drawdown: float  # 최대 낙폭 (%)
    win_rate: float  # 승률 (%)
    turnover: float  # 평균 회전율 (%)
    avg_holding_period: int  # 평균 보유 기간 (일)
    
    # 거래 내역
    trades: List[Dict]
    portfolio_values: List[Dict]
    monthly_returns: List[Dict]
    
    # 벤치마크 대비
    benchmark_return: float
    alpha: float
    beta: float
    
    # 메타데이터
    start_date: datetime
    end_date: datetime
    days: int
    rebalance_count: int


class BacktestEngine:
    """백테스트 엔진 (룩어헤드 방지)"""
    
    def __init__(self, config: BacktestConfig, data_provider):
        """
        Args:
            config: 백테스트 설정
            data_provider: 데이터 제공자 (KISDataProvider 등)
        """
        self.config = config
        self.data_provider = data_provider
        
        # 상태 관리
        self.portfolio = {}  # {symbol: {shares: int, avg_price: float}}
        self.cash = config.initial_capital
        self.portfolio_values = []
        self.trades = []
        
        # 캐시
        self.price_cache = {}
        self.financial_cache = {}
    
    def run(self) -> BacktestResult:
        """
        백테스트 실행
        
        Returns:
            BacktestResult
        """
        logger.info(f"🚀 백테스트 시작: {self.config.start_date.date()} ~ {self.config.end_date.date()}")
        
        # 리밸런싱 날짜 생성
        rebalance_dates = self._generate_rebalance_dates()
        logger.info(f"📅 리밸런싱 일정: {len(rebalance_dates)}회")
        
        # 각 리밸런싱 시점마다 실행
        for i, rebalance_date in enumerate(rebalance_dates):
            logger.info(f"📊 리밸런싱 {i+1}/{len(rebalance_dates)}: {rebalance_date.date()}")
            
            try:
                # 1. 가치주 선정 (룩어헤드 방지!)
                candidates = self._select_value_stocks(rebalance_date)
                
                if not candidates:
                    logger.warning(f"⚠️ {rebalance_date.date()} 가치주 없음, 현금 유지")
                    continue
                
                # 2. 포트폴리오 구성
                target_portfolio = self._construct_portfolio(candidates, rebalance_date)
                
                # 3. 리밸런싱 (매수/매도)
                self._rebalance(target_portfolio, rebalance_date)
                
                # 4. 포트폴리오 가치 기록
                portfolio_value = self._calculate_portfolio_value(rebalance_date)
                self.portfolio_values.append({
                    'date': rebalance_date.isoformat(),
                    'value': portfolio_value,
                    'cash': self.cash,
                    'positions': len(self.portfolio)
                })
                
            except Exception as e:
                logger.error(f"❌ 리밸런싱 실패 ({rebalance_date.date()}): {e}")
                continue
        
        # 결과 계산
        result = self._calculate_result(rebalance_dates)
        
        logger.info(f"✅ 백테스트 완료: 수익률 {result.total_return:.2f}%, Sharpe {result.sharpe_ratio:.2f}")
        
        return result
    
    def _generate_rebalance_dates(self) -> List[datetime]:
        """리밸런싱 날짜 생성"""
        dates = []
        current = self.config.start_date
        
        if self.config.rebalance_frequency == 'monthly':
            delta = timedelta(days=30)  # 대략 1개월
        elif self.config.rebalance_frequency == 'quarterly':
            delta = timedelta(days=90)  # 대략 3개월
        else:
            delta = timedelta(days=30)
        
        while current <= self.config.end_date:
            dates.append(current)
            current += delta
        
        return dates
    
    def _select_value_stocks(self, as_of_date: datetime) -> List[Dict]:
        """
        가치주 선정 (룩어헤드 방지!)
        
        Args:
            as_of_date: 기준 시점
        
        Returns:
            가치주 리스트
        """
        # ⚠️ 핵심: 재무 데이터는 as_of_date 이전에 공시된 것만 사용
        financial_cutoff = as_of_date - timedelta(days=self.config.financial_lag_days)
        price_cutoff = as_of_date - timedelta(days=self.config.price_lag_days)
        
        logger.debug(f"재무 컷오프: {financial_cutoff.date()}, 가격 컷오프: {price_cutoff.date()}")
        
        # TODO: 실제로는 data_provider에서 시점 일관성 보장된 데이터 조회
        # 여기서는 예시 구현
        
        candidates = []
        
        # 유니버스 조회 (예: KOSPI 200)
        universe = self._get_universe(as_of_date)
        
        for symbol in universe:
            try:
                # 재무 데이터 (financial_cutoff 이전)
                financial = self._get_financial_data(symbol, financial_cutoff)
                
                # 가격 데이터 (price_cutoff 기준)
                price = self._get_price_data(symbol, price_cutoff)
                
                if not financial or not price:
                    continue
                
                # 가치주 평가
                score = self._evaluate_stock(financial, price)
                
                if score >= self.config.score_threshold:
                    candidates.append({
                        'symbol': symbol,
                        'score': score,
                        'price': price['close'],
                        'financial': financial
                    })
                
            except Exception as e:
                logger.debug(f"종목 {symbol} 평가 실패: {e}")
                continue
        
        # 점수순 정렬
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        # 최대 종목 수 제한
        return candidates[:self.config.max_stocks]
    
    def _get_universe(self, as_of_date: datetime) -> List[str]:
        """
        유니버스 조회 (시점 일관성)
        
        실제로는 as_of_date 시점의 KOSPI/KOSDAQ 구성종목 조회
        """
        # TODO: 실제 구현
        # 임시: 고정 유니버스
        return [
            '005930', '000660', '035420', '005380', '035720',
            '051910', '006400', '068270', '207940', '066570'
        ]
    
    def _get_financial_data(self, symbol: str, cutoff_date: datetime) -> Optional[Dict]:
        """
        재무 데이터 조회 (cutoff_date 이전 공시분만)
        
        ⚠️ 룩어헤드 방지: cutoff_date 이후 데이터 절대 사용 금지!
        """
        # 캐시 확인
        cache_key = f"{symbol}_{cutoff_date.date()}"
        if cache_key in self.financial_cache:
            return self.financial_cache[cache_key]
        
        # TODO: 실제로는 DART API 또는 DB에서 cutoff_date 이전 최신 재무제표 조회
        # 여기서는 더미 데이터
        data = {
            'per': 12.5,
            'pbr': 1.2,
            'roe': 15.0,
            'eps': 5000,
            'bps': 50000,
            'quarter': '2023-Q2',
            'report_date': cutoff_date - timedelta(days=180)
        }
        
        self.financial_cache[cache_key] = data
        return data
    
    def _get_price_data(self, symbol: str, as_of_date: datetime) -> Optional[Dict]:
        """
        가격 데이터 조회 (as_of_date 기준)
        
        ⚠️ 룩어헤드 방지: as_of_date 이후 데이터 절대 사용 금지!
        """
        # 캐시 확인
        cache_key = f"{symbol}_{as_of_date.date()}"
        if cache_key in self.price_cache:
            return self.price_cache[cache_key]
        
        # TODO: 실제로는 data_provider에서 as_of_date 기준 종가 조회
        # 여기서는 더미 데이터
        data = {
            'close': 60000,
            'volume': 1000000,
            'date': as_of_date
        }
        
        self.price_cache[cache_key] = data
        return data
    
    def _evaluate_stock(self, financial: Dict, price: Dict) -> float:
        """
        종목 평가 (점수 계산)
        
        실제로는 value_stock_finder.py의 evaluate_value_stock() 로직 사용
        """
        # 간단한 점수 계산 (예시)
        per = financial['per']
        pbr = financial['pbr']
        roe = financial['roe']
        
        score = 0.0
        
        # PER 점수 (낮을수록 좋음)
        if per > 0 and per <= 15:
            score += 20
        elif per <= 20:
            score += 15
        
        # PBR 점수 (낮을수록 좋음)
        if pbr > 0 and pbr <= 1.5:
            score += 20
        elif pbr <= 2.0:
            score += 15
        
        # ROE 점수 (높을수록 좋음)
        if roe >= 15:
            score += 20
        elif roe >= 10:
            score += 15
        
        return score
    
    def _construct_portfolio(self, candidates: List[Dict], as_of_date: datetime) -> Dict:
        """
        포트폴리오 구성 (비중 최적화)
        
        Args:
            candidates: 가치주 후보
            as_of_date: 기준 시점
        
        Returns:
            {symbol: target_weight}
        """
        if not candidates:
            return {}
        
        # 균등 비중 (간단한 방식)
        n = len(candidates)
        base_weight = 1.0 / n
        
        # 최대 비중 제한
        max_weight = min(self.config.max_weight_per_stock, 1.0 / n * 1.5)
        
        portfolio = {}
        for candidate in candidates:
            symbol = candidate['symbol']
            weight = min(base_weight, max_weight)
            portfolio[symbol] = weight
        
        # 정규화 (합이 1.0이 되도록)
        total_weight = sum(portfolio.values())
        if total_weight > 0:
            portfolio = {k: v / total_weight for k, v in portfolio.items()}
        
        return portfolio
    
    def _rebalance(self, target_portfolio: Dict, as_of_date: datetime):
        """
        리밸런싱 (매수/매도 실행)
        
        Args:
            target_portfolio: {symbol: target_weight}
            as_of_date: 실행 시점
        """
        # 현재 포트폴리오 가치
        total_value = self._calculate_portfolio_value(as_of_date)
        
        # 목표 포지션 계산
        target_positions = {}
        for symbol, target_weight in target_portfolio.items():
            price_data = self._get_price_data(symbol, as_of_date)
            if not price_data:
                continue
            
            price = price_data['close']
            target_value = total_value * target_weight
            target_shares = int(target_value / price)
            
            target_positions[symbol] = target_shares
        
        # 매도 (포트폴리오에는 있지만 목표에 없는 종목)
        for symbol in list(self.portfolio.keys()):
            if symbol not in target_positions:
                self._sell_all(symbol, as_of_date)
        
        # 조정 (목표와 현재 차이만큼 매수/매도)
        for symbol, target_shares in target_positions.items():
            current_shares = self.portfolio.get(symbol, {}).get('shares', 0)
            diff = target_shares - current_shares
            
            if diff > 0:
                self._buy(symbol, diff, as_of_date)
            elif diff < 0:
                self._sell(symbol, abs(diff), as_of_date)
    
    def _buy(self, symbol: str, shares: int, as_of_date: datetime):
        """매수 실행"""
        price_data = self._get_price_data(symbol, as_of_date)
        if not price_data:
            return
        
        price = price_data['close']
        
        # 슬리피지 적용
        execution_price = price * (1 + self.config.slippage)
        
        # 총 비용 (가격 + 거래비용)
        total_cost = execution_price * shares * (1 + self.config.transaction_cost)
        
        if total_cost > self.cash:
            logger.warning(f"현금 부족: {symbol} {shares}주 매수 불가")
            return
        
        # 포트폴리오 업데이트
        if symbol in self.portfolio:
            # 평균 단가 업데이트
            old_shares = self.portfolio[symbol]['shares']
            old_avg_price = self.portfolio[symbol]['avg_price']
            new_shares = old_shares + shares
            new_avg_price = (old_avg_price * old_shares + execution_price * shares) / new_shares
            
            self.portfolio[symbol] = {
                'shares': new_shares,
                'avg_price': new_avg_price
            }
        else:
            self.portfolio[symbol] = {
                'shares': shares,
                'avg_price': execution_price
            }
        
        # 현금 차감
        self.cash -= total_cost
        
        # 거래 기록
        self.trades.append({
            'date': as_of_date.isoformat(),
            'symbol': symbol,
            'action': 'BUY',
            'shares': shares,
            'price': execution_price,
            'cost': total_cost
        })
        
        logger.debug(f"매수: {symbol} {shares}주 @ {execution_price:,.0f}원")
    
    def _sell(self, symbol: str, shares: int, as_of_date: datetime):
        """매도 실행"""
        if symbol not in self.portfolio:
            return
        
        current_shares = self.portfolio[symbol]['shares']
        if shares > current_shares:
            shares = current_shares
        
        price_data = self._get_price_data(symbol, as_of_date)
        if not price_data:
            return
        
        price = price_data['close']
        
        # 슬리피지 적용
        execution_price = price * (1 - self.config.slippage)
        
        # 총 수익 (가격 - 거래비용)
        total_proceeds = execution_price * shares * (1 - self.config.transaction_cost)
        
        # 포트폴리오 업데이트
        self.portfolio[symbol]['shares'] -= shares
        
        if self.portfolio[symbol]['shares'] == 0:
            del self.portfolio[symbol]
        
        # 현금 증가
        self.cash += total_proceeds
        
        # 거래 기록
        self.trades.append({
            'date': as_of_date.isoformat(),
            'symbol': symbol,
            'action': 'SELL',
            'shares': shares,
            'price': execution_price,
            'proceeds': total_proceeds
        })
        
        logger.debug(f"매도: {symbol} {shares}주 @ {execution_price:,.0f}원")
    
    def _sell_all(self, symbol: str, as_of_date: datetime):
        """전량 매도"""
        if symbol in self.portfolio:
            shares = self.portfolio[symbol]['shares']
            self._sell(symbol, shares, as_of_date)
    
    def _calculate_portfolio_value(self, as_of_date: datetime) -> float:
        """포트폴리오 총 가치 계산"""
        stock_value = 0.0
        
        for symbol, position in self.portfolio.items():
            price_data = self._get_price_data(symbol, as_of_date)
            if price_data:
                stock_value += price_data['close'] * position['shares']
        
        return self.cash + stock_value
    
    def _calculate_result(self, rebalance_dates: List[datetime]) -> BacktestResult:
        """백테스트 결과 계산"""
        if not self.portfolio_values:
            raise ValueError("포트폴리오 가치 기록 없음")
        
        # 수익률 계산
        initial_value = self.config.initial_capital
        final_value = self.portfolio_values[-1]['value']
        total_return = (final_value / initial_value - 1) * 100
        
        # 연환산 수익률
        days = (self.config.end_date - self.config.start_date).days
        years = days / 365.25
        annualized_return = ((final_value / initial_value) ** (1 / years) - 1) * 100 if years > 0 else 0
        
        # 샤프 비율 (간단한 계산)
        returns = []
        for i in range(1, len(self.portfolio_values)):
            r = (self.portfolio_values[i]['value'] / self.portfolio_values[i-1]['value'] - 1) * 100
            returns.append(r)
        
        if returns:
            avg_return = statistics.mean(returns)
            std_return = statistics.stdev(returns) if len(returns) > 1 else 0
            sharpe_ratio = (avg_return / std_return * (252 ** 0.5)) if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        # 최대 낙폭 (MDD)
        peak = initial_value
        max_dd = 0.0
        
        for pv in self.portfolio_values:
            value = pv['value']
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        return BacktestResult(
            config=self.config,
            total_return=total_return,
            annualized_return=annualized_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_dd,
            win_rate=0.0,  # TODO: 승률 계산
            turnover=0.0,  # TODO: 회전율 계산
            avg_holding_period=0,  # TODO: 평균 보유기간 계산
            trades=self.trades,
            portfolio_values=self.portfolio_values,
            monthly_returns=[],  # TODO: 월별 수익률
            benchmark_return=0.0,  # TODO: 벤치마크 수익률
            alpha=0.0,
            beta=1.0,
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            days=days,
            rebalance_count=len(rebalance_dates)
        )


# ===== 사용 예시 =====
if __name__ == "__main__":
    # 백테스트 설정
    config = BacktestConfig(
        start_date=datetime(2022, 1, 1),
        end_date=datetime(2023, 12, 31),
        rebalance_frequency='monthly',
        initial_capital=100_000_000,
        max_stocks=20
    )
    
    # 백테스트 엔진 초기화 (실제로는 KISDataProvider 전달)
    engine = BacktestEngine(config, data_provider=None)
    
    # 백테스트 실행
    # result = engine.run()
    # print(f"총 수익률: {result.total_return:.2f}%")
    # print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
    # print(f"MDD: {result.max_drawdown:.2f}%")

