#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
최적 종목 수 찾기 시스템
- 다양한 종목 수별 백테스팅 수행
- 수익률 극대화 지점 찾기
- 리스크-수익률 최적점 분석
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel

# 프로젝트 모듈 임포트
from enhanced_integrated_analyzer import EnhancedIntegratedAnalyzer
from backtesting_engine import BacktestingEngine

app = typer.Typer()
console = Console()

class OptimalCountFinder:
    """최적 종목 수를 찾는 클래스"""
    
    def __init__(self):
        self.analyzer = EnhancedIntegratedAnalyzer()
        self.engine = BacktestingEngine()
        self.engine.initialize(self.analyzer.provider)
        self.results = []
    
    def run_count_sweep_test(self, 
                            count_range: List[int] = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
                            min_market_cap: float = 1000,
                            backtest_period: str = "24",
                            min_sharpe_ratio: float = 0.2,
                            min_return: float = 0.03,
                            optimization_iterations: int = 30) -> List[Dict]:
        """다양한 종목 수별 백테스팅 수행"""
        
        console.print("🔍 [bold green]최적 종목 수 찾기 백테스팅 시작[/bold green]")
        console.print("=" * 60)
        
        # 백테스팅 기간 설정
        end_date = datetime.now().strftime('%Y-%m-%d')
        period_months = int(backtest_period)
        start_date = (datetime.now() - timedelta(days=period_months * 30)).strftime('%Y-%m-%d')
        
        console.print(f"📅 백테스팅 기간: {start_date} ~ {end_date} ({period_months}개월)")
        console.print(f"🎯 테스트할 종목 수: {count_range}")
        console.print(f"💰 최소 시가총액: {min_market_cap:,}억원")
        console.print()
        
        # 시가총액 상위 종목 조회 (최대 개수만큼)
        max_count = max(count_range)
        top_stocks = self.analyzer.get_top_market_cap_stocks(
            count=max_count * 2,
            min_market_cap=min_market_cap
        )
        
        if not top_stocks:
            console.print("[red]❌ 조건에 맞는 종목을 찾을 수 없습니다.[/red]")
            return []
        
        console.print(f"✅ 분석 대상 종목 {len(top_stocks)}개 확보")
        console.print()
        
        # 각 종목 수별 백테스팅 수행
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("종목 수별 백테스팅 진행", total=len(count_range))
            
            for i, count in enumerate(count_range):
                progress.update(task, description=f"종목 수 {count}개 백테스팅 중...")
                
                try:
                    # 상위 count개 종목 선택
                    symbols = [stock['symbol'] for stock in top_stocks[:count]]
                    
                    # 백테스팅 수행
                    result = self._run_single_backtest(
                        symbols, start_date, end_date, 
                        min_sharpe_ratio, min_return, optimization_iterations
                    )
                    
                    if result:
                        result['count'] = count
                        result['symbols_count'] = len(symbols)
                        self.results.append(result)
                        
                        console.print(f"✅ 종목 수 {count}개: 수익률 {result['total_return']:.2%}, 샤프 {result['sharpe_ratio']:.2f}")
                    else:
                        console.print(f"❌ 종목 수 {count}개: 백테스팅 실패")
                    
                except Exception as e:
                    console.print(f"❌ 종목 수 {count}개: 오류 - {e}")
                
                progress.advance(task)
                time.sleep(1)  # API 제한 고려
        
        return self.results
    
    def _run_single_backtest(self, symbols: List[str], start_date: str, end_date: str,
                           min_sharpe_ratio: float, min_return: float, 
                           optimization_iterations: int) -> Optional[Dict]:
        """단일 백테스팅 수행"""
        
        try:
            # 파라미터 최적화 실행
            optimized_params = self.engine.optimize_parameters(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
                optimization_method="random_search",
                max_iterations=optimization_iterations
            )
            
            if optimized_params and optimized_params.get('best_performance'):
                performance = optimized_params['best_performance']
                return {
                    'total_return': performance.get('total_return', 0),
                    'sharpe_ratio': performance.get('sharpe_ratio', 0),
                    'max_drawdown': performance.get('max_drawdown', 0),
                    'win_rate': performance.get('win_rate', 0),
                    'validation_passed': True
                }
            
        except Exception as e:
            console.print(f"백테스팅 오류: {e}")
        
        return None
    
    def analyze_results(self) -> Dict[str, Any]:
        """백테스팅 결과 분석"""
        
        if not self.results:
            return {}
        
        # 결과를 DataFrame으로 변환
        df = pd.DataFrame(self.results)
        
        # 최적 지점 찾기
        analysis = {
            'total_tests': len(self.results),
            'count_range': [r['count'] for r in self.results],
            'max_return_count': df.loc[df['total_return'].idxmax(), 'count'],
            'max_return': df['total_return'].max(),
            'max_sharpe_count': df.loc[df['sharpe_ratio'].idxmax(), 'count'],
            'max_sharpe': df['sharpe_ratio'].max(),
            'min_drawdown_count': df.loc[df['max_drawdown'].idxmin(), 'count'],
            'min_drawdown': df['max_drawdown'].min(),
            'max_win_rate_count': df.loc[df['win_rate'].idxmax(), 'count'],
            'max_win_rate': df['win_rate'].max(),
            'results': self.results
        }
        
        return analysis
    
    def display_results(self, analysis: Dict[str, Any]):
        """결과 표시"""
        
        if not analysis:
            console.print("[red]❌ 분석할 결과가 없습니다.[/red]")
            return
        
        console.print("\n🎯 [bold green]최적 종목 수 분석 결과[/bold green]")
        console.print("=" * 60)
        
        # 요약 테이블
        summary_table = Table(title="종목 수별 성과 요약")
        summary_table.add_column("종목 수", style="cyan", justify="center")
        summary_table.add_column("총 수익률", style="green", justify="right")
        summary_table.add_column("샤프 비율", style="blue", justify="right")
        summary_table.add_column("최대 낙폭", style="red", justify="right")
        summary_table.add_column("승률", style="yellow", justify="right")
        
        for result in analysis['results']:
            summary_table.add_row(
                str(result['count']),
                f"{result['total_return']:.2%}",
                f"{result['sharpe_ratio']:.2f}",
                f"{result['max_drawdown']:.2%}",
                f"{result['win_rate']:.1%}"
            )
        
        console.print(summary_table)
        
        # 최적 지점 분석
        console.print("\n🏆 [bold yellow]최적 지점 분석[/bold yellow]")
        
        optimal_panel = Panel(
            f"""📈 최고 수익률: {analysis['max_return_count']}종목 ({analysis['max_return']:.2%})
📊 최고 샤프 비율: {analysis['max_sharpe_count']}종목 ({analysis['max_sharpe']:.2f})
📉 최저 낙폭: {analysis['min_drawdown_count']}종목 ({analysis['min_drawdown']:.2%})
🎯 최고 승률: {analysis['max_win_rate_count']}종목 ({analysis['max_win_rate']:.1%})

💡 권장 종목 수: {analysis['max_return_count']}개 (최고 수익률 달성)""",
            title="최적화 결과",
            border_style="green"
        )
        
        console.print(optimal_panel)
    
    def save_results(self, analysis: Dict[str, Any], filename: str = None):
        """결과 저장"""
        
        if not filename:
            timestamp = int(time.time())
            filename = f"optimal_count_analysis_{timestamp}.json"
        
        # 결과 저장
        save_data = {
            'timestamp': datetime.now().isoformat(),
            'analysis': analysis,
            'method': 'optimal_count_finder'
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        console.print(f"💾 결과가 {filename}에 저장되었습니다.")
        return filename

@app.command()
def find_optimal_count(
    count_range: str = typer.Option("5,10,15,20,25,30,35,40,45,50", "--counts", "-c", 
                                   help="테스트할 종목 수 범위 (쉼표로 구분)"),
    min_market_cap: float = typer.Option(1000, "--min-market-cap", 
                                        help="최소 시가총액 (억원)"),
    backtest_period: str = typer.Option("24", "--period", "-p", 
                                       help="백테스팅 기간 (개월)"),
    min_sharpe_ratio: float = typer.Option(0.2, "--min-sharpe", 
                                          help="최소 샤프 비율 임계값"),
    min_return: float = typer.Option(0.03, "--min-return", 
                                    help="최소 수익률 임계값"),
    optimization_iterations: int = typer.Option(30, "--iterations", "-i", 
                                               help="최적화 반복 횟수"),
    save_results: bool = typer.Option(True, "--save", help="결과 저장 여부")
):
    """최적 종목 수 찾기"""
    
    # 종목 수 범위 파싱
    try:
        count_list = [int(x.strip()) for x in count_range.split(',')]
        count_list = sorted(count_list)
    except ValueError:
        console.print("[red]❌ 잘못된 종목 수 범위 형식입니다.[/red]")
        return
    
    # 최적화 실행
    finder = OptimalCountFinder()
    
    # 백테스팅 수행
    results = finder.run_count_sweep_test(
        count_range=count_list,
        min_market_cap=min_market_cap,
        backtest_period=backtest_period,
        min_sharpe_ratio=min_sharpe_ratio,
        min_return=min_return,
        optimization_iterations=optimization_iterations
    )
    
    if not results:
        console.print("[red]❌ 백테스팅 결과가 없습니다.[/red]")
        return
    
    # 결과 분석
    analysis = finder.analyze_results()
    
    # 결과 표시
    finder.display_results(analysis)
    
    # 결과 저장
    if save_results:
        finder.save_results(analysis)

if __name__ == "__main__":
    app()
