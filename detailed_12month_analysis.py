#!/usr/bin/env python3
"""
12개월 기간 상세 분석 - 집중투자 vs 분산투자
"""

import sys
import logging
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

console = Console()

def detailed_12month_analysis():
    """12개월 기간 상세 분석"""
    
    console.print("📊 [bold green]12개월 기간 상세 분석: 집중투자 vs 분산투자[/bold green]")
    console.print("=" * 70)
    
    try:
        # 백테스팅 엔진 초기화
        from backtesting_engine import BacktestingEngine
        from enhanced_integrated_analyzer import EnhancedIntegratedAnalyzer
        
        analyzer = EnhancedIntegratedAnalyzer()
        engine = BacktestingEngine()
        engine.initialize(analyzer.provider)
        
        # 분석 기간 설정
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")  # 12개월
        
        console.print(f"📅 분석 기간: {start_date} ~ {end_date} (12개월)")
        
        # 1. SK하이닉스 단일 종목 분석
        console.print("\n🎯 [bold yellow]1. SK하이닉스 단일 종목 분석[/bold yellow]")
        
        sk_result = engine.run_backtest(
            symbols=["000660"],
            start_date=start_date,
            end_date=end_date,
            parameters=None
        )
        
        # 2. 3종목 포트폴리오 분석
        console.print("\n🎯 [bold yellow]2. 3종목 포트폴리오 분석[/bold yellow]")
        
        portfolio_result = engine.run_backtest(
            symbols=["005930", "000660", "373220"],  # 삼성전자, SK하이닉스, LG에너지솔루션
            start_date=start_date,
            end_date=end_date,
            parameters=None
        )
        
        # 3. 개별 종목별 성과 분석
        console.print("\n🎯 [bold yellow]3. 개별 종목별 성과 분석[/bold yellow]")
        
        samsung_result = engine.run_backtest(
            symbols=["005930"],
            start_date=start_date,
            end_date=end_date,
            parameters=None
        )
        
        lg_result = engine.run_backtest(
            symbols=["373220"],
            start_date=start_date,
            end_date=end_date,
            parameters=None
        )
        
        # 결과 표시
        console.print("\n📊 [bold cyan]개별 종목 성과 비교 (12개월)[/bold cyan]")
        
        individual_table = Table(title="개별 종목 성과")
        individual_table.add_column("종목", style="cyan")
        individual_table.add_column("종목명", style="white")
        individual_table.add_column("총 수익률", style="green")
        individual_table.add_column("연평균 수익률", style="blue")
        individual_table.add_column("샤프 비율", style="yellow")
        individual_table.add_column("최대 낙폭", style="red")
        
        individual_table.add_row(
            "005930", "삼성전자", 
            f"{samsung_result.total_return:.2%}",
            f"{samsung_result.annualized_return:.2%}",
            f"{samsung_result.sharpe_ratio:.2f}",
            f"{samsung_result.max_drawdown:.2%}"
        )
        
        individual_table.add_row(
            "000660", "SK하이닉스", 
            f"{sk_result.total_return:.2%}",
            f"{sk_result.annualized_return:.2%}",
            f"{sk_result.sharpe_ratio:.2f}",
            f"{sk_result.max_drawdown:.2%}"
        )
        
        individual_table.add_row(
            "373220", "LG에너지솔루션", 
            f"{lg_result.total_return:.2%}",
            f"{lg_result.annualized_return:.2%}",
            f"{lg_result.sharpe_ratio:.2f}",
            f"{lg_result.max_drawdown:.2%}"
        )
        
        console.print(individual_table)
        
        # 포트폴리오 vs 집중투자 비교
        console.print("\n📊 [bold cyan]포트폴리오 vs 집중투자 비교 (12개월)[/bold cyan]")
        
        comparison_table = Table(title="전략별 성과 비교")
        comparison_table.add_column("지표", style="cyan")
        comparison_table.add_column("SK하이닉스 집중", style="green")
        comparison_table.add_column("3종목 분산", style="blue")
        comparison_table.add_column("차이", style="yellow")
        comparison_table.add_column("우위", style="magenta")
        
        # 수익률 비교
        return_diff = sk_result.total_return - portfolio_result.total_return
        return_winner = "집중투자" if return_diff > 0 else "분산투자"
        comparison_table.add_row(
            "총 수익률", 
            f"{sk_result.total_return:.2%}", 
            f"{portfolio_result.total_return:.2%}",
            f"{return_diff:+.2%}",
            return_winner
        )
        
        # 연평균 수익률 비교
        annual_diff = sk_result.annualized_return - portfolio_result.annualized_return
        annual_winner = "집중투자" if annual_diff > 0 else "분산투자"
        comparison_table.add_row(
            "연평균 수익률", 
            f"{sk_result.annualized_return:.2%}", 
            f"{portfolio_result.annualized_return:.2%}",
            f"{annual_diff:+.2%}",
            annual_winner
        )
        
        # 샤프 비율 비교
        sharpe_diff = sk_result.sharpe_ratio - portfolio_result.sharpe_ratio
        sharpe_winner = "집중투자" if sharpe_diff > 0 else "분산투자"
        comparison_table.add_row(
            "샤프 비율", 
            f"{sk_result.sharpe_ratio:.2f}", 
            f"{portfolio_result.sharpe_ratio:.2f}",
            f"{sharpe_diff:+.2f}",
            sharpe_winner
        )
        
        # 최대 낙폭 비교
        drawdown_diff = sk_result.max_drawdown - portfolio_result.max_drawdown
        drawdown_winner = "분산투자" if drawdown_diff > 0 else "집중투자"
        comparison_table.add_row(
            "최대 낙폭", 
            f"{sk_result.max_drawdown:.2%}", 
            f"{portfolio_result.max_drawdown:.2%}",
            f"{drawdown_diff:+.2%}",
            drawdown_winner
        )
        
        console.print(comparison_table)
        
        # 기간별 성과 분석
        console.print("\n📊 [bold cyan]기간별 성과 변화 분석[/bold cyan]")
        
        period_analysis = Table(title="3개월 vs 12개월 성과 비교")
        period_analysis.add_column("전략", style="cyan")
        period_analysis.add_column("3개월 수익률", style="green")
        period_analysis.add_column("12개월 수익률", style="blue")
        period_analysis.add_column("변화", style="yellow")
        
        # 3개월 결과 (이전 분석에서)
        sk_3month_return = 0.2504  # 25.04%
        portfolio_3month_return = 0.0352  # 3.52%
        
        sk_change = sk_result.total_return - sk_3month_return
        portfolio_change = portfolio_result.total_return - portfolio_3month_return
        
        period_analysis.add_row(
            "SK하이닉스 집중",
            f"{sk_3month_return:.2%}",
            f"{sk_result.total_return:.2%}",
            f"{sk_change:+.2%}"
        )
        
        period_analysis.add_row(
            "3종목 분산",
            f"{portfolio_3month_return:.2%}",
            f"{portfolio_result.total_return:.2%}",
            f"{portfolio_change:+.2%}"
        )
        
        console.print(period_analysis)
        
        # 투자 전략 권장사항
        console.print("\n💡 [bold magenta]12개월 기간 투자 전략 분석[/bold magenta]")
        
        # 최고 성과 종목 찾기
        individual_returns = {
            "삼성전자": samsung_result.total_return,
            "SK하이닉스": sk_result.total_return,
            "LG에너지솔루션": lg_result.total_return
        }
        
        best_stock = max(individual_returns, key=individual_returns.get)
        best_return = individual_returns[best_stock]
        
        console.print(f"🏆 [bold green]최고 성과 종목: {best_stock} ({best_return:.2%})[/bold green]")
        
        # 전략별 우위 분석
        if portfolio_result.total_return > sk_result.total_return:
            console.print("✅ [green]분산투자가 집중투자보다 우수한 성과를 보여줍니다.[/green]")
            console.print(f"   - 분산투자: {portfolio_result.total_return:.2%}")
            console.print(f"   - 집중투자: {sk_result.total_return:.2%}")
            console.print(f"   - 차이: {portfolio_result.total_return - sk_result.total_return:.2%}")
        else:
            console.print("✅ [green]집중투자가 분산투자보다 우수한 성과를 보여줍니다.[/green]")
        
        # 리스크 분석
        if sk_result.max_drawdown > portfolio_result.max_drawdown:
            console.print("⚠️ [yellow]집중투자의 리스크가 더 높습니다.[/yellow]")
            console.print(f"   - 집중투자 최대 낙폭: {sk_result.max_drawdown:.2%}")
            console.print(f"   - 분산투자 최대 낙폭: {portfolio_result.max_drawdown:.2%}")
        
        # 최종 권장사항
        console.print("\n🎯 [bold cyan]12개월 기간 최종 권장사항[/bold cyan]")
        
        if portfolio_result.sharpe_ratio > sk_result.sharpe_ratio:
            console.print("🛡️ [bold blue]분산투자를 추천합니다![/bold blue]")
            console.print("   - 더 높은 수익률과 우수한 위험 대비 수익률")
            console.print("   - 더 낮은 리스크 (최대 낙폭)")
            console.print("   - 안정적인 장기 투자 전략")
        else:
            console.print("🚀 [bold green]집중투자를 추천합니다![/bold green]")
            console.print("   - 높은 수익률과 우수한 위험 대비 수익률")
        
        # 기간별 전략 권장
        console.print("\n📅 [bold magenta]기간별 전략 권장[/bold magenta]")
        console.print("• [green]단기 (3개월 이하): SK하이닉스 집중투자[/green]")
        console.print("• [blue]장기 (12개월 이상): 3종목 분산투자[/blue]")
        console.print("• [yellow]중기 (6개월): 상황에 따른 선택[/yellow]")
        
        return {
            'sk_result': sk_result,
            'portfolio_result': portfolio_result,
            'samsung_result': samsung_result,
            'lg_result': lg_result,
            'analysis_period': f"{start_date} ~ {end_date}"
        }
        
    except Exception as e:
        console.print(f"[red]❌ 분석 중 오류 발생: {e}[/red]")
        logger.error(f"Error during analysis: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    detailed_12month_analysis()
