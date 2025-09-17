# estimate_performance_cli.py
import typer
import pandas as pd
import logging
from rich.console import Console
from rich.progress import Progress
from rich.table import Table
from rich.panel import Panel
from datetime import datetime, timedelta
from typing import List, Optional
from estimate_performance_analyzer import EstimatePerformanceAnalyzer

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

# Rich Console 초기화
console = Console()

# Typer CLI 앱 생성
app = typer.Typer(help="KIS API 기반 추정실적 분석 시스템")

@app.command(name="analyze-estimate")
def analyze_estimate_performance(
    symbol: str = typer.Argument(..., help="분석할 종목 코드 (예: 005930)"),
    export_csv: bool = typer.Option(False, "--export-csv", help="CSV 파일로 내보내기"),
    show_details: bool = typer.Option(True, "--details", help="상세 분석 표시")
):
    """단일 종목의 추정실적을 분석합니다."""
    
    console.print(f"🔍 [bold green]{symbol} 종목 추정실적 분석을 시작합니다...[/bold green]")
    
    try:
        analyzer = EstimatePerformanceAnalyzer()
        
        with Progress(console=console) as progress:
            task = progress.add_task("[cyan]추정실적 데이터 수집 및 분석 중...", total=100)
            
            # 분석 수행
            analysis = analyzer.analyze_single_stock(symbol)
            progress.update(task, advance=100)
        
        if analysis['status'] == 'success':
            summary = analysis['summary']
            
            # 요약 테이블 생성
            table = Table(title=f"{symbol} 추정실적 분석 결과")
            table.add_column("항목", style="cyan", width=20)
            table.add_column("값", style="green", width=15)
            
            table.add_row("종목명", summary.name)
            table.add_row("현재가", f"{summary.current_price:,}원")
            table.add_row("등락률", f"{summary.change_rate:+.2f}%")
            table.add_row("", "")  # 빈 행
            
            table.add_row("매출액", f"{summary.latest_revenue:,.0f}원")
            table.add_row("매출액 성장률", f"{summary.latest_revenue_growth:+.1f}%")
            table.add_row("영업이익", f"{summary.latest_operating_profit:,.0f}원")
            table.add_row("영업이익 성장률", f"{summary.latest_operating_profit_growth:+.1f}%")
            table.add_row("순이익", f"{summary.latest_net_profit:,.0f}원")
            table.add_row("순이익 성장률", f"{summary.latest_net_profit_growth:+.1f}%")
            table.add_row("", "")  # 빈 행
            
            table.add_row("EPS", f"{summary.latest_eps:,.0f}원")
            table.add_row("PER", f"{summary.latest_per:.1f}배")
            table.add_row("ROE", f"{summary.latest_roe:.1f}%")
            table.add_row("EV/EBITDA", f"{summary.latest_ev_ebitda:.1f}배")
            table.add_row("", "")  # 빈 행
            
            table.add_row("매출액 트렌드", summary.revenue_trend)
            table.add_row("영업이익 트렌드", summary.profit_trend)
            table.add_row("EPS 트렌드", summary.eps_trend)
            table.add_row("데이터 품질", f"{summary.data_quality_score:.2f}")
            table.add_row("최근 업데이트", summary.latest_update_date)
            
            console.print(table)
            
            if show_details:
                # 상세 보고서 표시
                report = analyzer.generate_report(analysis)
                console.print(Panel(report, title="📋 상세 분석 보고서", border_style="green"))
                
                # 재무건전성 분석
                financial_health = analysis.get('financial_health', {})
                if financial_health:
                    console.print("\n💪 [bold yellow]재무건전성 분석[/bold yellow]")
                    
                    health_table = Table()
                    health_table.add_column("지표", style="cyan")
                    health_table.add_column("점수", style="green")
                    health_table.add_column("등급", style="yellow")
                    
                    health_table.add_row(
                        "종합 점수",
                        f"{financial_health.get('health_score', 0)}/100점",
                        financial_health.get('health_grade', 'N/A')
                    )
                    
                    console.print(health_table)
                    
                    factors = financial_health.get('factors', [])
                    if factors:
                        console.print("\n📊 주요 요인:")
                        for factor in factors:
                            console.print(f"  • {factor}")
                
                # 밸류에이션 분석
                valuation = analysis.get('valuation_analysis', {})
                if valuation:
                    console.print("\n💰 [bold yellow]밸류에이션 분석[/bold yellow]")
                    
                    valuation_table = Table()
                    valuation_table.add_column("지표", style="cyan")
                    valuation_table.add_column("값", style="green")
                    valuation_table.add_column("등급", style="yellow")
                    valuation_table.add_column("해석", style="white")
                    
                    if 'per' in valuation:
                        per_data = valuation['per']
                        valuation_table.add_row(
                            "PER",
                            f"{per_data['value']:.1f}배",
                            per_data['grade'],
                            per_data['interpretation']
                        )
                    
                    if 'ev_ebitda' in valuation:
                        ev_ebitda_data = valuation['ev_ebitda']
                        valuation_table.add_row(
                            "EV/EBITDA",
                            f"{ev_ebitda_data['value']:.1f}배",
                            ev_ebitda_data['grade'],
                            ev_ebitda_data['interpretation']
                        )
                    
                    valuation_table.add_row(
                        "종합 점수",
                        f"{valuation.get('overall_score', 0)}/100점",
                        valuation.get('overall_grade', 'N/A'),
                        ""
                    )
                    
                    console.print(valuation_table)
                
                # 성장성 분석
                growth = analysis.get('growth_analysis', {})
                if growth:
                    console.print("\n📈 [bold yellow]성장성 분석[/bold yellow]")
                    
                    growth_table = Table()
                    growth_table.add_column("지표", style="cyan")
                    growth_table.add_column("값", style="green")
                    growth_table.add_column("등급", style="yellow")
                    growth_table.add_column("해석", style="white")
                    
                    if 'revenue_growth' in growth:
                        revenue_growth_data = growth['revenue_growth']
                        growth_table.add_row(
                            "매출액 성장률",
                            f"{revenue_growth_data['value']:+.1f}%",
                            revenue_growth_data['grade'],
                            revenue_growth_data['interpretation']
                        )
                    
                    if 'profit_growth' in growth:
                        profit_growth_data = growth['profit_growth']
                        growth_table.add_row(
                            "영업이익 성장률",
                            f"{profit_growth_data['value']:+.1f}%",
                            profit_growth_data['grade'],
                            profit_growth_data['interpretation']
                        )
                    
                    if 'eps_growth' in growth:
                        eps_growth_data = growth['eps_growth']
                        growth_table.add_row(
                            "EPS 성장률",
                            f"{eps_growth_data['value']:+.1f}%",
                            eps_growth_data['grade'],
                            eps_growth_data['interpretation']
                        )
                    
                    console.print(growth_table)
            
            # CSV 내보내기
            if export_csv:
                df = analyzer.export_to_dataframe(analysis)
                if not df.empty:
                    filename = f"estimate_performance_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    df.to_csv(filename, index=False, encoding='utf-8-sig')
                    console.print(f"\n💾 분석 결과가 {filename}에 저장되었습니다.")
                else:
                    console.print("\n⚠️ CSV 내보내기를 위한 데이터가 없습니다.")
        
        else:
            console.print(f"[red]❌ 분석 실패: {analysis.get('message', '알 수 없는 오류')}[/red]")
            
    except Exception as e:
        console.print(f"[red]❌ 분석 중 오류 발생: {e}[/red]")

@app.command(name="compare-estimates")
def compare_estimate_performances(
    symbols_str: str = typer.Option("005930,000660,035420,051910", "--symbols", "-s", help="비교할 종목 코드들 (쉼표로 구분)"),
    export_csv: bool = typer.Option(False, "--export-csv", help="CSV 파일로 내보내기"),
    ranking_only: bool = typer.Option(False, "--ranking-only", help="랭킹만 표시")
):
    """여러 종목의 추정실적을 비교 분석합니다."""
    
    symbols: List[str] = [s.strip() for s in symbols_str.split(',')]
    console.print(f"🔍 [bold green]{len(symbols)}개 종목 추정실적 비교 분석을 시작합니다...[/bold green]")
    console.print(f"📊 분석 종목: {', '.join(symbols)}")
    
    try:
        analyzer = EstimatePerformanceAnalyzer()
        
        with Progress(console=console) as progress:
            task = progress.add_task("[cyan]다중 종목 추정실적 분석 중...", total=len(symbols))
            
            # 다중 종목 분석 수행
            analysis = analyzer.analyze_multiple_stocks(symbols)
            progress.update(task, advance=len(symbols))
        
        console.print(f"\n✅ 분석 완료: {analysis['successful_analyses']}/{analysis['total_stocks']}개 종목")
        
        # 종목별 요약 테이블
        table = Table(title=f"{len(symbols)}개 종목 추정실적 비교")
        table.add_column("종목코드", style="cyan", width=8)
        table.add_column("종목명", style="white", width=12)
        table.add_column("현재가", style="green", width=10)
        table.add_column("매출액(억)", style="blue", width=12)
        table.add_column("매출성장률", style="magenta", width=10)
        table.add_column("영업이익(억)", style="yellow", width=12)
        table.add_column("EPS", style="red", width=8)
        table.add_column("PER", style="cyan", width=8)
        table.add_column("ROE", style="green", width=8)
        table.add_column("품질점수", style="white", width=8)
        
        all_data = []
        
        for symbol, stock_analysis in analysis['stock_analyses'].items():
            if stock_analysis.get('status') == 'success':
                summary = stock_analysis['summary']
                row_data = [
                    symbol,
                    summary.name[:10] + "..." if len(summary.name) > 10 else summary.name,
                    f"{summary.current_price:,}",
                    f"{summary.latest_revenue/100000000:.0f}",
                    f"{summary.latest_revenue_growth:+.1f}%",
                    f"{summary.latest_operating_profit/100000000:.0f}",
                    f"{summary.latest_eps:,.0f}",
                    f"{summary.latest_per:.1f}",
                    f"{summary.latest_roe:.1f}%",
                    f"{summary.data_quality_score:.2f}"
                ]
                table.add_row(*row_data)
                
                # CSV 내보내기용 데이터 수집
                if export_csv:
                    df_row = analyzer.export_to_dataframe(stock_analysis)
                    if not df_row.empty:
                        all_data.append(df_row)
            else:
                table.add_row(symbol, "오류", "-", "-", "-", "-", "-", "-", "-", "-")
        
        console.print(table)
        
        if not ranking_only:
            # 비교 분석 결과
            comparison = analysis.get('comparison_analysis', {})
            if comparison and comparison.get('status') != 'no_data':
                console.print("\n🏆 [bold yellow]비교 분석 결과[/bold yellow]")
                
                # PER 랭킹 (낮을수록 좋음)
                if 'per_ranking' in comparison:
                    console.print("\n💰 [bold green]PER 랭킹 (낮을수록 저평가)[/bold green]")
                    for i, (symbol, per) in enumerate(comparison['per_ranking'], 1):
                        console.print(f"  {i}. {symbol}: {per:.1f}배")
                
                # ROE 랭킹 (높을수록 좋음)
                if 'roe_ranking' in comparison:
                    console.print("\n📈 [bold green]ROE 랭킹 (높을수록 수익성 우수)[/bold green]")
                    for i, (symbol, roe) in enumerate(comparison['roe_ranking'], 1):
                        console.print(f"  {i}. {symbol}: {roe:.1f}%")
        
        # CSV 내보내기
        if export_csv and all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            filename = f"estimate_performances_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            combined_df.to_csv(filename, index=False, encoding='utf-8-sig')
            console.print(f"\n💾 비교 분석 결과가 {filename}에 저장되었습니다.")
        
    except Exception as e:
        console.print(f"[red]❌ 비교 분석 중 오류 발생: {e}[/red]")

@app.command(name="high-quality-estimates")
def analyze_high_quality_estimates(
    symbols_str: str = typer.Option("005930,000660,035420,051910,006400", "--symbols", "-s", help="분석할 종목 코드들 (쉼표로 구분)"),
    min_quality: float = typer.Option(0.7, "--min-quality", "-q", help="최소 품질 점수 (0-1)"),
    export_csv: bool = typer.Option(False, "--export-csv", help="CSV 파일로 내보내기")
):
    """데이터 품질이 높은 종목들의 추정실적을 분석합니다."""
    
    symbols: List[str] = [s.strip() for s in symbols_str.split(',')]
    console.print(f"🔍 [bold green]고품질 추정실적 종목 분석을 시작합니다...[/bold green]")
    console.print(f"📊 분석 종목: {', '.join(symbols)}")
    console.print(f"🎯 최소 품질 점수: {min_quality}")
    
    try:
        analyzer = EstimatePerformanceAnalyzer()
        
        with Progress(console=console) as progress:
            task = progress.add_task("[cyan]고품질 추정실적 분석 중...", total=len(symbols))
            
            # 고품질 종목 분석 수행
            analysis = analyzer.analyze_high_quality_stocks(symbols, min_quality)
            progress.update(task, advance=len(symbols))
        
        if analysis.get('status') == 'no_data':
            console.print(f"[yellow]⚠️ 품질점수 {min_quality} 이상인 종목이 없습니다.[/yellow]")
            return
        
        console.print(f"\n✅ 분석 완료: {analysis['high_quality_stocks']}/{analysis['total_stocks']}개 종목이 고품질 기준을 충족")
        
        # 고품질 종목 테이블
        table = Table(title=f"고품질 추정실적 종목 (품질점수 ≥ {min_quality})")
        table.add_column("종목코드", style="cyan", width=8)
        table.add_column("종목명", style="white", width=12)
        table.add_column("현재가", style="green", width=10)
        table.add_column("매출액(억)", style="blue", width=12)
        table.add_column("매출성장률", style="magenta", width=10)
        table.add_column("영업이익(억)", style="yellow", width=12)
        table.add_column("EPS", style="red", width=8)
        table.add_column("PER", style="cyan", width=8)
        table.add_column("ROE", style="green", width=8)
        table.add_column("품질점수", style="white", width=8)
        
        all_data = []
        
        for symbol, stock_analysis in analysis['stock_analyses'].items():
            if stock_analysis.get('status') == 'success':
                summary = stock_analysis['summary']
                row_data = [
                    symbol,
                    summary.name[:10] + "..." if len(summary.name) > 10 else summary.name,
                    f"{summary.current_price:,}",
                    f"{summary.latest_revenue/100000000:.0f}",
                    f"{summary.latest_revenue_growth:+.1f}%",
                    f"{summary.latest_operating_profit/100000000:.0f}",
                    f"{summary.latest_eps:,.0f}",
                    f"{summary.latest_per:.1f}",
                    f"{summary.latest_roe:.1f}%",
                    f"{summary.data_quality_score:.2f}"
                ]
                table.add_row(*row_data)
                
                # CSV 내보내기용 데이터 수집
                if export_csv:
                    df_row = analyzer.export_to_dataframe(stock_analysis)
                    if not df_row.empty:
                        all_data.append(df_row)
        
        console.print(table)
        
        # 고품질 종목들의 특징 분석
        if analysis['stock_analyses']:
            console.print("\n📊 [bold yellow]고품질 종목 특징 분석[/bold yellow]")
            
            # 평균 지표 계산
            successful_analyses = [s for s in analysis['stock_analyses'].values() if s.get('status') == 'success']
            if successful_analyses:
                avg_per = sum(s['summary'].latest_per for s in successful_analyses) / len(successful_analyses)
                avg_roe = sum(s['summary'].latest_roe for s in successful_analyses) / len(successful_analyses)
                avg_quality = sum(s['summary'].data_quality_score for s in successful_analyses) / len(successful_analyses)
                
                console.print(f"  • 평균 PER: {avg_per:.1f}배")
                console.print(f"  • 평균 ROE: {avg_roe:.1f}%")
                console.print(f"  • 평균 품질점수: {avg_quality:.2f}")
        
        # CSV 내보내기
        if export_csv and all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            filename = f"high_quality_estimates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            combined_df.to_csv(filename, index=False, encoding='utf-8-sig')
            console.print(f"\n💾 고품질 추정실적 분석 결과가 {filename}에 저장되었습니다.")
        
    except Exception as e:
        console.print(f"[red]❌ 고품질 분석 중 오류 발생: {e}[/red]")

@app.command(name="estimate-summary")
def get_estimate_summary(
    symbol: str = typer.Argument(..., help="종목 코드 (예: 005930)")
):
    """특정 종목의 추정실적 요약 정보를 조회합니다."""
    
    console.print(f"📊 [bold green]{symbol} 추정실적 요약 조회 중...[/bold green]")
    
    try:
        from estimate_performance_client import EstimatePerformanceClient
        client = EstimatePerformanceClient()
        
        summary = client.get_estimate_summary(symbol)
        
        if not summary:
            console.print(f"[yellow]⚠️ {symbol} 종목의 추정실적 데이터가 없습니다.[/yellow]")
            return
        
        # 요약 테이블
        table = Table(title=f"{symbol} 추정실적 요약")
        table.add_column("항목", style="cyan", width=20)
        table.add_column("값", style="green", width=15)
        
        table.add_row("종목명", summary['name'])
        table.add_row("현재가", f"{summary['current_price']:,}원")
        table.add_row("등락률", f"{summary['change_rate']:+.2f}%")
        table.add_row("", "")  # 빈 행
        
        table.add_row("매출액", f"{summary['latest_revenue']:,.0f}원")
        table.add_row("매출액 성장률", f"{summary['latest_revenue_growth']:+.1f}%")
        table.add_row("영업이익", f"{summary['latest_operating_profit']:,.0f}원")
        table.add_row("영업이익 성장률", f"{summary['latest_operating_profit_growth']:+.1f}%")
        table.add_row("순이익", f"{summary['latest_net_profit']:,.0f}원")
        table.add_row("순이익 성장률", f"{summary['latest_net_profit_growth']:+.1f}%")
        table.add_row("", "")  # 빈 행
        
        table.add_row("EPS", f"{summary['latest_eps']:,.0f}원")
        table.add_row("PER", f"{summary['latest_per']:.1f}배")
        table.add_row("ROE", f"{summary['latest_roe']:.1f}%")
        table.add_row("EV/EBITDA", f"{summary['latest_ev_ebitda']:.1f}배")
        table.add_row("", "")  # 빈 행
        
        table.add_row("매출액 트렌드", summary['revenue_trend'])
        table.add_row("영업이익 트렌드", summary['profit_trend'])
        table.add_row("EPS 트렌드", summary['eps_trend'])
        table.add_row("데이터 품질", f"{summary['data_quality_score']:.2f}")
        table.add_row("최근 업데이트", summary['latest_update_date'])
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]❌ 요약 조회 중 오류 발생: {e}[/red]")

if __name__ == "__main__":
    app()
