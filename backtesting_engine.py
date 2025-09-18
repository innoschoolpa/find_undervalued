# backtesting_engine.py
import pandas as pd
import numpy as np
import yaml
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import random
from rich.console import Console
from rich.progress import Progress
from rich.table import Table
from rich.panel import Panel

# EnhancedIntegratedAnalyzer는 함수 내부에서 import

console = Console()
logger = logging.getLogger(__name__)

@dataclass
class BacktestResult:
    """백테스팅 결과를 저장하는 데이터 클래스"""
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    parameters: Dict[str, Any]
    monthly_returns: List[float]
    equity_curve: List[float]

class PerformanceCalculator:
    """성과 지표 계산 클래스"""
    
    @staticmethod
    def calculate_returns(prices: List[float]) -> List[float]:
        """가격 리스트에서 수익률 계산"""
        if len(prices) < 2:
            return []
        
        returns = []
        for i in range(1, len(prices)):
            ret = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(ret)
        return returns
    
    @staticmethod
    def calculate_total_return(returns: List[float]) -> float:
        """총 수익률 계산"""
        if not returns:
            return 0.0
        return (1 + np.array(returns)).prod() - 1
    
    @staticmethod
    def calculate_annualized_return(returns: List[float], periods_per_year: int = 12) -> float:
        """연평균 수익률 계산"""
        if not returns:
            return 0.0
        
        total_return = PerformanceCalculator.calculate_total_return(returns)
        years = len(returns) / periods_per_year
        if years <= 0:
            return 0.0
        
        return (1 + total_return) ** (1 / years) - 1
    
    @staticmethod
    def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
        """샤프 비율 계산"""
        if not returns:
            return 0.0
        
        excess_returns = np.array(returns) - risk_free_rate / 12  # 월별 무위험 수익률
        if np.std(excess_returns) == 0:
            return 0.0
        
        return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(12)
    
    @staticmethod
    def calculate_max_drawdown(equity_curve: List[float]) -> float:
        """최대 낙폭 계산"""
        if not equity_curve:
            return 0.0
        
        peak = equity_curve[0]
        max_dd = 0.0
        
        for value in equity_curve:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_dd = max(max_dd, drawdown)
        
        return max_dd
    
    @staticmethod
    def calculate_win_rate(returns: List[float]) -> float:
        """승률 계산"""
        if not returns:
            return 0.0
        
        winning_trades = sum(1 for r in returns if r > 0)
        return winning_trades / len(returns)
    
    @staticmethod
    def calculate_profit_factor(returns: List[float]) -> float:
        """수익 팩터 계산"""
        if not returns:
            return 0.0
        
        gross_profit = sum(r for r in returns if r > 0)
        gross_loss = abs(sum(r for r in returns if r < 0))
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        
        return gross_profit / gross_loss

class DataLoader:
    """과거 데이터 로더 클래스"""
    
    def __init__(self, kis_provider):
        self.kis_provider = kis_provider
    
    def load_historical_prices(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """과거 주가 데이터 로드"""
        try:
            # KIS API를 통한 과거 데이터 조회
            price_data = self.kis_provider.get_daily_price_history(symbol, days=365)
            
            if price_data is None or price_data.empty:
                return pd.DataFrame()
            
            # 날짜 필터링
            price_data['date'] = pd.to_datetime(price_data['date'])
            mask = (price_data['date'] >= start_date) & (price_data['date'] <= end_date)
            filtered_data = price_data[mask].copy()
            
            return filtered_data[['date', 'close', 'volume']].reset_index(drop=True)
            
        except Exception as e:
            logger.warning(f"과거 데이터 로드 실패 {symbol}: {e}")
            return pd.DataFrame()
    
    def load_historical_financial_data(self, symbol: str, date: str) -> Dict[str, Any]:
        """특정 시점의 재무 데이터 로드 (시뮬레이션)"""
        # 실제로는 해당 시점의 재무 데이터를 조회해야 함
        # 현재는 랜덤 데이터로 시뮬레이션
        return {
            'roe': random.uniform(5, 25),
            'roa': random.uniform(3, 15),
            'debt_ratio': random.uniform(10, 200),
            'net_profit_margin': random.uniform(2, 20),
            'current_ratio': random.uniform(50, 300),
            'revenue_growth': random.uniform(-10, 30)
        }

class BacktestingEngine:
    """백테스팅 엔진 메인 클래스"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self.performance_calculator = PerformanceCalculator()
        self.data_loader = None
        self.results = []
        
    def initialize(self, kis_provider):
        """백테스팅 엔진 초기화"""
        self.data_loader = DataLoader(kis_provider)
        logger.info("백테스팅 엔진 초기화 완료")
    
    def run_backtest(self, 
                    symbols: List[str],
                    start_date: str,
                    end_date: str,
                    rebalance_frequency: str = "monthly",
                    initial_capital: float = 10000000,
                    parameters: Optional[Dict[str, Any]] = None) -> BacktestResult:
        """백테스팅 실행"""
        
        console.print(f"🚀 [bold]백테스팅 시작[/bold]")
        console.print(f"📅 기간: {start_date} ~ {end_date}")
        console.print(f"📊 종목 수: {len(symbols)}개")
        console.print(f"💰 초기 자본: {initial_capital:,}원")
        console.print(f"🔄 리밸런싱: {rebalance_frequency}")
        
        # 파라미터 설정
        if parameters is None:
            parameters = self._get_default_parameters()
        
        # 분석기 초기화 (파라미터 적용)
        analyzer = self._create_analyzer_with_parameters(parameters)
        
        # 백테스팅 실행
        equity_curve = [initial_capital]
        monthly_returns = []
        current_capital = initial_capital
        
        # 리밸런싱 날짜 생성
        rebalance_dates = self._generate_rebalance_dates(start_date, end_date, rebalance_frequency)
        
        with Progress() as progress:
            task = progress.add_task("백테스팅 진행 중...", total=len(rebalance_dates))
            
            for i, rebalance_date in enumerate(rebalance_dates):
                try:
                    # 해당 시점에서 포트폴리오 구성
                    portfolio = self._construct_portfolio(analyzer, symbols, rebalance_date)
                    
                    if not portfolio:
                        continue
                    
                    # 다음 리밸런싱까지의 수익률 계산
                    if i < len(rebalance_dates) - 1:
                        next_date = rebalance_dates[i + 1]
                        period_return = self._calculate_period_return(portfolio, rebalance_date, next_date)
                    else:
                        # 마지막 기간
                        period_return = self._calculate_period_return(portfolio, rebalance_date, end_date)
                    
                    # 자본 업데이트
                    current_capital *= (1 + period_return)
                    equity_curve.append(current_capital)
                    monthly_returns.append(period_return)
                    
                    progress.update(task, advance=1)
                    
                except Exception as e:
                    logger.warning(f"리밸런싱 실패 {rebalance_date}: {e}")
                    continue
        
        # 성과 지표 계산
        result = self._calculate_performance_metrics(
            monthly_returns, equity_curve, parameters
        )
        
        console.print(f"✅ 백테스팅 완료 - 총 수익률: {result.total_return:.2%}")
        return result
    
    def _get_default_parameters(self) -> Dict[str, Any]:
        """기본 파라미터 반환"""
        return {
            'weights': {
                'opinion_analysis': 25,
                'estimate_analysis': 30,
                'financial_ratios': 30,
                'growth_analysis': 10,
                'scale_analysis': 5
            },
            'financial_ratio_weights': {
                'roe_score': 8,
                'roa_score': 5,
                'debt_ratio_score': 7,
                'net_profit_margin_score': 5,
                'current_ratio_score': 3,
                'growth_score': 2
            },
            'grade_thresholds': {
                'A_plus': 80,
                'A': 70,
                'B_plus': 60,
                'B': 50,
                'C_plus': 40,
                'C': 30,
                'D': 20,
                'F': 0
            }
        }
    
    def _create_analyzer_with_parameters(self, parameters: Dict[str, Any]):
        """파라미터를 적용한 분석기 생성"""
        from enhanced_integrated_analyzer import EnhancedIntegratedAnalyzer
        analyzer = EnhancedIntegratedAnalyzer()
        
        # 가중치 적용
        if 'weights' in parameters:
            analyzer.weights = parameters['weights']
        
        if 'financial_ratio_weights' in parameters:
            analyzer.financial_ratio_weights = parameters['financial_ratio_weights']
        
        if 'grade_thresholds' in parameters:
            analyzer.grade_thresholds = parameters['grade_thresholds']
        
        return analyzer
    
    def _generate_rebalance_dates(self, start_date: str, end_date: str, frequency: str) -> List[str]:
        """리밸런싱 날짜 생성"""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        dates = []
        current = start
        
        if frequency == "monthly":
            while current <= end:
                dates.append(current.strftime("%Y-%m-%d"))
                # 다음 달 첫째 날
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1, day=1)
                else:
                    current = current.replace(month=current.month + 1, day=1)
        elif frequency == "quarterly":
            while current <= end:
                dates.append(current.strftime("%Y-%m-%d"))
                # 다음 분기 첫째 날
                if current.month in [1, 4, 7, 10]:
                    current = current.replace(month=current.month + 3, day=1)
                else:
                    current = current.replace(month=((current.month - 1) // 3 + 1) * 3 + 1, day=1)
        
        return dates
    
    def _construct_portfolio(self, analyzer, 
                           symbols: List[str], date: str) -> List[Dict[str, Any]]:
        """특정 시점에서 포트폴리오 구성"""
        portfolio = []
        
        for symbol in symbols:
            try:
                # 해당 시점의 분석 수행 (시뮬레이션)
                analysis_result = self._simulate_analysis(analyzer, symbol, date)
                
                if analysis_result and analysis_result.get('enhanced_score', 0) >= 60:
                    portfolio.append({
                        'symbol': symbol,
                        'score': analysis_result['enhanced_score'],
                        'grade': analysis_result['enhanced_grade'],
                        'weight': 1.0 / len(symbols)  # 균등 가중치
                    })
            except Exception as e:
                logger.debug(f"포트폴리오 구성 실패 {symbol}: {e}")
                continue
        
        return portfolio
    
    def _simulate_analysis(self, analyzer, 
                          symbol: str, date: str) -> Optional[Dict[str, Any]]:
        """분석 시뮬레이션 (실제로는 해당 시점의 데이터로 분석)"""
        # 실제 구현에서는 해당 시점의 데이터를 사용해야 함
        # 현재는 랜덤 시뮬레이션
        
        # 랜덤 점수 생성 (60-90점 범위)
        score = random.uniform(60, 90)
        
        # 등급 계산
        grade = analyzer._get_enhanced_grade(score)
        
        return {
            'symbol': symbol,
            'enhanced_score': score,
            'enhanced_grade': grade,
            'status': 'success'
        }
    
    def _calculate_period_return(self, portfolio: List[Dict[str, Any]], 
                               start_date: str, end_date: str) -> float:
        """기간 수익률 계산"""
        if not portfolio:
            return 0.0
        
        # 포트폴리오 수익률 시뮬레이션
        # 실제로는 각 종목의 실제 수익률을 계산해야 함
        portfolio_return = random.uniform(-0.05, 0.10)  # -5% ~ +10% 랜덤
        
        return portfolio_return
    
    def _calculate_performance_metrics(self, monthly_returns: List[float], 
                                     equity_curve: List[float], 
                                     parameters: Dict[str, Any]) -> BacktestResult:
        """성과 지표 계산"""
        
        # 기본 성과 지표
        total_return = self.performance_calculator.calculate_total_return(monthly_returns)
        annualized_return = self.performance_calculator.calculate_annualized_return(monthly_returns)
        sharpe_ratio = self.performance_calculator.calculate_sharpe_ratio(monthly_returns)
        max_drawdown = self.performance_calculator.calculate_max_drawdown(equity_curve)
        win_rate = self.performance_calculator.calculate_win_rate(monthly_returns)
        profit_factor = self.performance_calculator.calculate_profit_factor(monthly_returns)
        
        # 거래 통계
        winning_trades = sum(1 for r in monthly_returns if r > 0)
        losing_trades = sum(1 for r in monthly_returns if r < 0)
        total_trades = len(monthly_returns)
        
        # 평균 승리/패배
        avg_win = np.mean([r for r in monthly_returns if r > 0]) if winning_trades > 0 else 0
        avg_loss = np.mean([r for r in monthly_returns if r < 0]) if losing_trades > 0 else 0
        
        return BacktestResult(
            total_return=total_return,
            annualized_return=annualized_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            parameters=parameters,
            monthly_returns=monthly_returns,
            equity_curve=equity_curve
        )
    
    def display_results(self, result: BacktestResult):
        """백테스팅 결과 표시"""
        
        # 성과 요약 테이블
        summary_table = Table(title="백테스팅 성과 요약")
        summary_table.add_column("지표", style="cyan")
        summary_table.add_column("값", style="green", justify="right")
        summary_table.add_column("설명", style="white")
        
        summary_table.add_row("총 수익률", f"{result.total_return:.2%}", "전체 기간 수익률")
        summary_table.add_row("연평균 수익률", f"{result.annualized_return:.2%}", "연환산 수익률")
        summary_table.add_row("샤프 비율", f"{result.sharpe_ratio:.2f}", "위험 대비 수익률")
        summary_table.add_row("최대 낙폭", f"{result.max_drawdown:.2%}", "최대 손실률")
        summary_table.add_row("승률", f"{result.win_rate:.2%}", "수익 거래 비율")
        summary_table.add_row("수익 팩터", f"{result.profit_factor:.2f}", "총 수익 / 총 손실")
        
        console.print(summary_table)
        
        # 거래 통계 테이블
        trade_table = Table(title="거래 통계")
        trade_table.add_column("구분", style="cyan")
        trade_table.add_column("횟수", style="green", justify="right")
        trade_table.add_column("비율", style="yellow", justify="right")
        
        trade_table.add_row("총 거래", str(result.total_trades), "100.0%")
        trade_table.add_row("수익 거래", str(result.winning_trades), f"{result.winning_trades/result.total_trades*100:.1f}%")
        trade_table.add_row("손실 거래", str(result.losing_trades), f"{result.losing_trades/result.total_trades*100:.1f}%")
        trade_table.add_row("평균 수익", f"{result.avg_win:.2%}", "수익 거래 평균")
        trade_table.add_row("평균 손실", f"{result.avg_loss:.2%}", "손실 거래 평균")
        
        console.print(trade_table)
        
        # 파라미터 표시
        param_table = Table(title="사용된 파라미터")
        param_table.add_column("구분", style="cyan")
        param_table.add_column("값", style="green")
        
        for category, params in result.parameters.items():
            if isinstance(params, dict):
                for key, value in params.items():
                    param_table.add_row(f"{category}.{key}", str(value))
            else:
                param_table.add_row(category, str(params))
        
        console.print(param_table)

class ParameterOptimizer:
    """파라미터 최적화 클래스"""
    
    def __init__(self, backtesting_engine: BacktestingEngine):
        self.engine = backtesting_engine
    
    def optimize_parameters(self, 
                           symbols: List[str],
                           start_date: str,
                           end_date: str,
                           optimization_method: str = "grid_search",
                           max_iterations: int = 100) -> Dict[str, Any]:
        """파라미터 최적화"""
        
        console.print(f"🔍 [bold]파라미터 최적화 시작[/bold]")
        console.print(f"📊 최적화 방법: {optimization_method}")
        console.print(f"🔄 최대 반복: {max_iterations}회")
        
        if optimization_method == "grid_search":
            return self._grid_search_optimization(symbols, start_date, end_date, max_iterations)
        elif optimization_method == "random_search":
            return self._random_search_optimization(symbols, start_date, end_date, max_iterations)
        else:
            raise ValueError(f"지원하지 않는 최적화 방법: {optimization_method}")
    
    def _grid_search_optimization(self, symbols: List[str], start_date: str, 
                                end_date: str, max_iterations: int) -> Dict[str, Any]:
        """그리드 서치 최적화"""
        
        # 파라미터 그리드 정의
        param_grid = {
            'weights.opinion_analysis': [20, 25, 30],
            'weights.estimate_analysis': [25, 30, 35],
            'weights.financial_ratios': [25, 30, 35],
            'weights.growth_analysis': [5, 10, 15],
            'weights.scale_analysis': [5, 10, 15],
            'financial_ratio_weights.roe_score': [6, 8, 10],
            'financial_ratio_weights.debt_ratio_score': [5, 7, 9],
        }
        
        best_score = -float('inf')
        best_params = None
        iteration = 0
        
        # 그리드 조합 생성
        from itertools import product
        
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        
        for combination in product(*values):
            if iteration >= max_iterations:
                break
                
            # 파라미터 딕셔너리 생성
            params = self._create_parameter_dict(dict(zip(keys, combination)))
            
            # 백테스팅 실행
            try:
                result = self.engine.run_backtest(symbols, start_date, end_date, parameters=params)
                
                # 목적 함수 계산 (샤프 비율 - 최대 낙폭)
                score = result.sharpe_ratio - 0.5 * result.max_drawdown
                
                if score > best_score:
                    best_score = score
                    best_params = params
                
                iteration += 1
                
                if iteration % 10 == 0:
                    console.print(f"진행률: {iteration}/{max_iterations} - 현재 최고 점수: {best_score:.3f}")
                    
            except Exception as e:
                logger.warning(f"최적화 반복 실패: {e}")
                continue
        
        console.print(f"✅ 최적화 완료 - 최고 점수: {best_score:.3f}")
        return best_params
    
    def _random_search_optimization(self, symbols: List[str], start_date: str, 
                                  end_date: str, max_iterations: int) -> Dict[str, Any]:
        """랜덤 서치 최적화"""
        
        best_score = -float('inf')
        best_params = None
        
        for iteration in range(max_iterations):
            # 랜덤 파라미터 생성
            params = self._generate_random_parameters()
            
            # 백테스팅 실행
            try:
                result = self.engine.run_backtest(symbols, start_date, end_date, parameters=params)
                
                # 목적 함수 계산
                score = result.sharpe_ratio - 0.5 * result.max_drawdown
                
                if score > best_score:
                    best_score = score
                    best_params = params
                
                if iteration % 10 == 0:
                    console.print(f"진행률: {iteration}/{max_iterations} - 현재 최고 점수: {best_score:.3f}")
                    
            except Exception as e:
                logger.warning(f"최적화 반복 실패: {e}")
                continue
        
        console.print(f"✅ 최적화 완료 - 최고 점수: {best_score:.3f}")
        return best_params
    
    def _create_parameter_dict(self, flat_params: Dict[str, Any]) -> Dict[str, Any]:
        """평면 파라미터를 중첩 딕셔너리로 변환"""
        params = {
            'weights': {
                'opinion_analysis': 25,
                'estimate_analysis': 30,
                'financial_ratios': 30,
                'growth_analysis': 10,
                'scale_analysis': 5
            },
            'financial_ratio_weights': {
                'roe_score': 8,
                'roa_score': 5,
                'debt_ratio_score': 7,
                'net_profit_margin_score': 5,
                'current_ratio_score': 3,
                'growth_score': 2
            }
        }
        
        for key, value in flat_params.items():
            if key.startswith('weights.'):
                param_key = key.split('.')[1]
                params['weights'][param_key] = value
            elif key.startswith('financial_ratio_weights.'):
                param_key = key.split('.')[1]
                params['financial_ratio_weights'][param_key] = value
        
        # 가중치 정규화
        total_weight = sum(params['weights'].values())
        if total_weight != 100:
            for key in params['weights']:
                params['weights'][key] = params['weights'][key] * 100 / total_weight
        
        return params
    
    def _generate_random_parameters(self) -> Dict[str, Any]:
        """랜덤 파라미터 생성"""
        # 가중치 생성 (합이 100이 되도록)
        weights = {
            'opinion_analysis': random.randint(15, 35),
            'estimate_analysis': random.randint(20, 40),
            'financial_ratios': random.randint(20, 40),
            'growth_analysis': random.randint(5, 20),
            'scale_analysis': random.randint(0, 15)
        }
        
        # 정규화
        total = sum(weights.values())
        for key in weights:
            weights[key] = weights[key] * 100 / total
        
        return {
            'weights': weights,
            'financial_ratio_weights': {
                'roe_score': random.randint(5, 12),
                'roa_score': random.randint(3, 8),
                'debt_ratio_score': random.randint(5, 10),
                'net_profit_margin_score': random.randint(3, 8),
                'current_ratio_score': random.randint(2, 5),
                'growth_score': random.randint(1, 4)
            }
        }
