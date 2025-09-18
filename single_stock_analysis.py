#!/usr/bin/env python3
"""
상위 1종목 집중 투자 수익률 분석
"""

import sys
import logging
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

console = Console()

def analyze_single_stock_performance():
    """상위 1종목(SK하이닉스) 집중 투자 수익률 분석"""
    
    console.print("🎯 [bold green]상위 1종목 집중 투자 수익률 분석[/bold green]")
    console.print("=" * 60)
    
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
        console.print(f"🎯 분석 종목: SK하이닉스 (000660)")
        
        # SK하이닉스 단일 종목 백테스팅
        console.print("\n🚀 [bold yellow]SK하이닉스 단일 종목 백테스팅 실행[/bold yellow]")
        
        result = engine.run_backtest(
            symbols=["000660"],
            start_date=start_date,
            end_date=end_date,
            parameters=None  # 기본 파라미터 사용
        )
        
        # 결과 분석
        console.print("\n📊 [bold cyan]SK하이닉스 단일 종목 투자 결과[/bold cyan]")
        
        result_table = Table(title="SK하이닉스 집중 투자 성과")
        result_table.add_column("지표", style="cyan")
        result_table.add_column("값", style="green")
        
        result_table.add_row("총 수익률", f"{result.total_return:.2%}")
        result_table.add_row("연평균 수익률", f"{result.annualized_return:.2%}")
        result_table.add_row("샤프 비율", f"{result.sharpe_ratio:.2f}")
        result_table.add_row("최대 낙폭", f"{result.max_drawdown:.2%}")
        result_table.add_row("승률", f"{result.win_rate:.1%}")
        
        console.print(result_table)
        
        # 비교 분석을 위한 3종목 포트폴리오 결과
        console.print("\n🔄 [bold yellow]3종목 포트폴리오와 비교 분석[/bold yellow]")
        
        # 3종목 포트폴리오 백테스팅
        portfolio_result = engine.run_backtest(
            symbols=["005930", "000660", "373220"],  # 삼성전자, SK하이닉스, LG에너지솔루션
            start_date=start_date,
            end_date=end_date,
            parameters=None
        )
        
        # 비교 테이블
        comparison_table = Table(title="집중투자 vs 분산투자 비교")
        comparison_table.add_column("지표", style="cyan")
        comparison_table.add_column("SK하이닉스 집중", style="green")
        comparison_table.add_column("3종목 분산", style="blue")
        comparison_table.add_column("차이", style="yellow")
        
        # 수익률 비교
        return_diff = result.total_return - portfolio_result.total_return
        comparison_table.add_row(
            "총 수익률", 
            f"{result.total_return:.2%}", 
            f"{portfolio_result.total_return:.2%}",
            f"{return_diff:+.2%}"
        )
        
        # 연평균 수익률 비교
        annual_diff = result.annualized_return - portfolio_result.annualized_return
        comparison_table.add_row(
            "연평균 수익률", 
            f"{result.annualized_return:.2%}", 
            f"{portfolio_result.annualized_return:.2%}",
            f"{annual_diff:+.2%}"
        )
        
        # 샤프 비율 비교
        sharpe_diff = result.sharpe_ratio - portfolio_result.sharpe_ratio
        comparison_table.add_row(
            "샤프 비율", 
            f"{result.sharpe_ratio:.2f}", 
            f"{portfolio_result.sharpe_ratio:.2f}",
            f"{sharpe_diff:+.2f}"
        )
        
        # 최대 낙폭 비교
        drawdown_diff = result.max_drawdown - portfolio_result.max_drawdown
        comparison_table.add_row(
            "최대 낙폭", 
            f"{result.max_drawdown:.2%}", 
            f"{portfolio_result.max_drawdown:.2%}",
            f"{drawdown_diff:+.2%}"
        )
        
        console.print(comparison_table)
        
        # 투자 전략 권장사항
        console.print("\n💡 [bold magenta]투자 전략 분석 및 권장사항[/bold magenta]")
        
        if result.total_return > portfolio_result.total_return:
            console.print("✅ [green]집중투자가 더 높은 수익률을 달성했습니다![/green]")
            if result.sharpe_ratio > portfolio_result.sharpe_ratio:
                console.print("✅ [green]위험 대비 수익률도 더 우수합니다.[/green]")
            else:
                console.print("⚠️ [yellow]하지만 위험 대비 수익률은 분산투자가 더 좋습니다.[/yellow]")
        else:
            console.print("⚠️ [yellow]분산투자가 더 안정적인 수익률을 보여줍니다.[/yellow]")
        
        # 리스크 분석
        if result.max_drawdown > portfolio_result.max_drawdown:
            console.print("⚠️ [red]집중투자의 최대 낙폭이 더 큽니다. 리스크 관리가 필요합니다.[/red]")
        
        # 최종 권장사항
        console.print("\n🎯 [bold cyan]최종 권장사항[/bold cyan]")
        
        if result.sharpe_ratio > 1.0 and result.total_return > 0.1:
            console.print("🚀 [bold green]SK하이닉스 집중투자를 추천합니다![/bold green]")
            console.print("   - 높은 수익률과 우수한 위험 대비 수익률")
        elif result.sharpe_ratio > portfolio_result.sharpe_ratio:
            console.print("⚖️ [bold yellow]상황에 따른 선택을 권장합니다:[/bold yellow]")
            console.print("   - 공격적 투자: SK하이닉스 집중투자")
            console.print("   - 안정적 투자: 3종목 분산투자")
        else:
            console.print("🛡️ [bold blue]분산투자를 추천합니다.[/bold blue]")
            console.print("   - 더 안정적이고 균형잡힌 수익률")
        
        return {
            'single_stock': result,
            'portfolio': portfolio_result,
            'analysis_period': f"{start_date} ~ {end_date}"
        }
        
    except Exception as e:
        console.print(f"[red]❌ 분석 중 오류 발생: {e}[/red]")
        logger.error(f"Error during analysis: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    analyze_single_stock_performance()
