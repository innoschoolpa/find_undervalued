# investment_opinion_cli.py
import typer
import pandas as pd
import logging
from rich.console import Console
from rich.progress import Progress
from rich.table import Table
from rich.panel import Panel
from datetime import datetime, timedelta
from typing import List, Optional
from investment_opinion_analyzer import InvestmentOpinionAnalyzer

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

# Rich Console 초기화
console = Console()

# Typer CLI 앱 생성
app = typer.Typer(help="KIS API 기반 투자의견 분석 시스템")

@app.command(name="analyze-opinion")
def analyze_investment_opinion(
    symbol: str = typer.Argument(..., help="분석할 종목 코드 (예: 005930)"),
    days_back: int = typer.Option(30, "--days", "-d", help="분석 기간 (일)"),
    export_csv: bool = typer.Option(False, "--export-csv", help="CSV 파일로 내보내기"),
    show_details: bool = typer.Option(True, "--details", help="상세 분석 표시")
):
    """단일 종목의 투자의견을 분석합니다."""
    
    console.print(f"🔍 [bold green]{symbol} 종목 투자의견 분석을 시작합니다...[/bold green]")
    console.print(f"📅 분석 기간: 최근 {days_back}일")
    
    try:
        analyzer = InvestmentOpinionAnalyzer()
        
        with Progress(console=console) as progress:
            task = progress.add_task("[cyan]투자의견 데이터 수집 및 분석 중...", total=100)
            
            # 분석 수행
            analysis = analyzer.analyze_single_stock(symbol, days_back=days_back)
            progress.update(task, advance=100)
        
        if analysis['status'] == 'success':
            summary = analysis['summary']
            
            # 요약 테이블 생성
            table = Table(title=f"{symbol} 투자의견 분석 결과")
            table.add_column("항목", style="cyan", width=20)
            table.add_column("값", style="green", width=15)
            
            table.add_row("분석 기간", f"{days_back}일")
            table.add_row("총 의견 수", f"{summary.total_opinions}건")
            table.add_row("매수 의견", f"{summary.buy_opinions}건")
            table.add_row("보유 의견", f"{summary.hold_opinions}건")
            table.add_row("매도 의견", f"{summary.sell_opinions}건")
            table.add_row("평균 목표가", f"{summary.avg_target_price:,}원")
            table.add_row("최고 목표가", f"{summary.max_target_price:,}원")
            table.add_row("최저 목표가", f"{summary.min_target_price:,}원")
            table.add_row("평균 상승률", f"{summary.avg_upside:+.2f}%")
            table.add_row("투자의견 트렌드", summary.opinion_trend)
            table.add_row("최근 의견일", summary.most_recent_date)
            
            console.print(table)
            
            if show_details:
                # 상세 보고서 표시
                report = analyzer.generate_report(analysis)
                console.print(Panel(report, title="📋 상세 분석 보고서", border_style="green"))
                
                # 상세 분석 정보 표시
                detailed = analysis.get('detailed_analysis', {})
                if detailed:
                    console.print("\n📊 [bold yellow]상세 분석 정보[/bold yellow]")
                    
                    detail_table = Table()
                    detail_table.add_column("분석 항목", style="cyan")
                    detail_table.add_column("결과", style="white")
                    
                    detail_table.add_row("최근 의견 변경 수", f"{detailed.get('recent_changes', 0)}건")
                    detail_table.add_row("참여 증권사 수", f"{detailed.get('total_brokerages', 0)}개")
                    detail_table.add_row("가장 활발한 날", detailed.get('most_active_date', 'N/A'))
                    
                    console.print(detail_table)
                
                # 컨센서스 분석
                consensus = analysis.get('consensus_analysis', {})
                if consensus:
                    console.print("\n🎯 [bold yellow]컨센서스 분석[/bold yellow]")
                    console.print(f"컨센서스 점수: {consensus.get('consensus_score', 0):.2f}")
                    console.print(f"컨센서스 해석: {consensus.get('consensus_level', 'N/A')}")
                    console.print(f"분석 샘플 수: {consensus.get('sample_size', 0)}건")
                
                # 목표가 분석
                target_analysis = analysis.get('target_price_analysis', {})
                if target_analysis and target_analysis.get('status') != 'no_data':
                    console.print("\n💰 [bold yellow]목표가 분석[/bold yellow]")
                    console.print(f"목표가 커버리지: {target_analysis.get('coverage_rate', 0):.1f}%")
                    console.print(f"목표가 범위: {target_analysis.get('price_range', 0):,.0f}원")
                
                # 증권사 분석
                brokerage_analysis = analysis.get('brokerage_analysis', {})
                if brokerage_analysis:
                    console.print("\n🏢 [bold yellow]증권사 분석[/bold yellow]")
                    console.print(f"총 증권사 수: {brokerage_analysis.get('total_brokerages', 0)}개")
                    
                    top_brokerages = brokerage_analysis.get('top_brokerages', [])
                    if top_brokerages:
                        console.print("상위 증권사:")
                        for i, (firm, count) in enumerate(top_brokerages[:3], 1):
                            console.print(f"  {i}. {firm}: {count}건")
            
            # CSV 내보내기
            if export_csv:
                df = analyzer.export_to_dataframe(analysis)
                if not df.empty:
                    filename = f"investment_opinion_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    df.to_csv(filename, index=False, encoding='utf-8-sig')
                    console.print(f"\n💾 분석 결과가 {filename}에 저장되었습니다.")
                else:
                    console.print("\n⚠️ CSV 내보내기를 위한 데이터가 없습니다.")
        
        else:
            console.print(f"[red]❌ 분석 실패: {analysis.get('message', '알 수 없는 오류')}[/red]")
            
    except Exception as e:
        console.print(f"[red]❌ 분석 중 오류 발생: {e}[/red]")

@app.command(name="compare-opinions")
def compare_investment_opinions(
    symbols_str: str = typer.Option("005930,000660,035420,051910", "--symbols", "-s", help="비교할 종목 코드들 (쉼표로 구분)"),
    days_back: int = typer.Option(30, "--days", "-d", help="분석 기간 (일)"),
    export_csv: bool = typer.Option(False, "--export-csv", help="CSV 파일로 내보내기"),
    ranking_only: bool = typer.Option(False, "--ranking-only", help="랭킹만 표시")
):
    """여러 종목의 투자의견을 비교 분석합니다."""
    
    symbols: List[str] = [s.strip() for s in symbols_str.split(',')]
    console.print(f"🔍 [bold green]{len(symbols)}개 종목 투자의견 비교 분석을 시작합니다...[/bold green]")
    console.print(f"📅 분석 기간: 최근 {days_back}일")
    console.print(f"📊 분석 종목: {', '.join(symbols)}")
    
    try:
        analyzer = InvestmentOpinionAnalyzer()
        
        with Progress(console=console) as progress:
            task = progress.add_task("[cyan]다중 종목 투자의견 분석 중...", total=len(symbols))
            
            # 다중 종목 분석 수행
            analysis = analyzer.analyze_multiple_stocks(symbols, days_back=days_back)
            progress.update(task, advance=len(symbols))
        
        console.print(f"\n✅ 분석 완료: {analysis['successful_analyses']}/{analysis['total_stocks']}개 종목")
        
        # 종목별 요약 테이블
        table = Table(title=f"{len(symbols)}개 종목 투자의견 비교")
        table.add_column("종목코드", style="cyan", width=8)
        table.add_column("총 의견", style="white", width=8)
        table.add_column("매수", style="green", width=6)
        table.add_column("보유", style="yellow", width=6)
        table.add_column("매도", style="red", width=6)
        table.add_column("평균 목표가", style="blue", width=12)
        table.add_column("상승률", style="magenta", width=10)
        table.add_column("트렌드", style="white", width=8)
        
        all_data = []
        
        for symbol, stock_analysis in analysis['stock_analyses'].items():
            if stock_analysis.get('status') == 'success':
                summary = stock_analysis['summary']
                row_data = [
                    symbol,
                    f"{summary.total_opinions}",
                    f"{summary.buy_opinions}",
                    f"{summary.hold_opinions}",
                    f"{summary.sell_opinions}",
                    f"{summary.avg_target_price:,}",
                    f"{summary.avg_upside:+.1f}%",
                    summary.opinion_trend
                ]
                table.add_row(*row_data)
                
                # CSV 내보내기용 데이터 수집
                if export_csv:
                    df_row = analyzer.export_to_dataframe(stock_analysis)
                    if not df_row.empty:
                        all_data.append(df_row)
            else:
                table.add_row(symbol, "오류", "-", "-", "-", "-", "-", "-")
        
        console.print(table)
        
        if not ranking_only:
            # 비교 분석 결과
            comparison = analysis.get('comparison_analysis', {})
            if comparison and comparison.get('status') != 'no_data':
                console.print("\n🏆 [bold yellow]비교 분석 결과[/bold yellow]")
                
                # 목표가 랭킹
                if 'target_price_ranking' in comparison:
                    console.print("\n📈 [bold green]평균 목표가 랭킹[/bold green]")
                    for i, (symbol, price) in enumerate(comparison['target_price_ranking'], 1):
                        console.print(f"  {i}. {symbol}: {price:,}원")
                
                # 컨센서스 랭킹
                if 'consensus_ranking' in comparison:
                    console.print("\n🎯 [bold green]컨센서스 점수 랭킹[/bold green]")
                    for i, (symbol, score) in enumerate(comparison['consensus_ranking'], 1):
                        console.print(f"  {i}. {symbol}: {score:.2f}")
                
                # 의견 수 랭킹
                if 'opinion_count_ranking' in comparison:
                    console.print("\n📊 [bold green]투자의견 수 랭킹[/bold green]")
                    for i, (symbol, count) in enumerate(comparison['opinion_count_ranking'], 1):
                        console.print(f"  {i}. {symbol}: {count}건")
        
        # CSV 내보내기
        if export_csv and all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            filename = f"investment_opinions_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            combined_df.to_csv(filename, index=False, encoding='utf-8-sig')
            console.print(f"\n💾 비교 분석 결과가 {filename}에 저장되었습니다.")
        
    except Exception as e:
        console.print(f"[red]❌ 비교 분석 중 오류 발생: {e}[/red]")

@app.command(name="recent-opinions")
def get_recent_opinions(
    symbol: str = typer.Argument(..., help="종목 코드 (예: 005930)"),
    limit: int = typer.Option(10, "--limit", "-l", help="조회할 최근 의견 수"),
    show_changes_only: bool = typer.Option(False, "--changes-only", help="의견 변경된 것만 표시")
):
    """특정 종목의 최근 투자의견을 조회합니다."""
    
    console.print(f"📊 [bold green]{symbol} 최근 투자의견 조회 중...[/bold green]")
    
    try:
        from investment_opinion_client import InvestmentOpinionClient
        client = InvestmentOpinionClient()
        
        if show_changes_only:
            console.print("🔄 의견이 변경된 투자의견만 조회합니다.")
            opinions = client.get_opinion_changes(symbol, days_back=90)
        else:
            opinions = client.get_recent_opinions(symbol, limit=limit)
        
        if not opinions:
            console.print(f"[yellow]⚠️ {symbol} 종목의 투자의견 데이터가 없습니다.[/yellow]")
            return
        
        # 테이블 생성
        table = Table(title=f"{symbol} 최근 투자의견")
        table.add_column("날짜", style="cyan", width=10)
        table.add_column("증권사", style="white", width=15)
        table.add_column("투자의견", style="yellow", width=20)
        table.add_column("목표가", style="green", width=10)
        table.add_column("상승률", style="magenta", width=10)
        table.add_column("변경여부", style="red", width=8)
        
        for opinion in opinions:
            table.add_row(
                opinion.business_date,
                opinion.brokerage_firm,
                opinion.current_opinion,
                f"{opinion.target_price:,}" if opinion.target_price > 0 else "-",
                f"{opinion.price_target_upside:+.1f}%" if opinion.price_target_upside != 0 else "-",
                opinion.opinion_change
            )
        
        console.print(table)
        
        # 요약 정보
        console.print(f"\n📈 [bold yellow]요약 정보[/bold yellow]")
        console.print(f"총 조회된 의견 수: {len(opinions)}건")
        
        if opinions:
            buy_count = sum(1 for op in opinions if any(keyword in op.current_opinion for keyword in ['매수', 'BUY']))
            sell_count = sum(1 for op in opinions if any(keyword in op.current_opinion for keyword in ['매도', 'SELL']))
            hold_count = len(opinions) - buy_count - sell_count
            
            console.print(f"매수 의견: {buy_count}건")
            console.print(f"보유 의견: {hold_count}건")
            console.print(f"매도 의견: {sell_count}건")
            
            # 평균 목표가
            target_prices = [op.target_price for op in opinions if op.target_price > 0]
            if target_prices:
                avg_target = sum(target_prices) / len(target_prices)
                console.print(f"평균 목표가: {avg_target:,.0f}원")
        
    except Exception as e:
        console.print(f"[red]❌ 투자의견 조회 중 오류 발생: {e}[/red]")

@app.command(name="test-opinion")
def test_investment_opinion_api():
    """투자의견 API 기능을 테스트합니다."""
    
    console.print("🧪 [bold green]투자의견 API 테스트를 시작합니다...[/bold green]")
    
    try:
        # 테스트 모듈 실행
        import test_investment_opinion
        test_investment_opinion.main()
        
    except Exception as e:
        console.print(f"[red]❌ 테스트 실행 중 오류 발생: {e}[/red]")

if __name__ == "__main__":
    app()

