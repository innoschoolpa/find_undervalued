# integrated_analysis_cli.py
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
from estimate_performance_analyzer import EstimatePerformanceAnalyzer
from test_integrated_analysis import (
    create_integrated_analysis,
    create_integrated_comparison,
    display_integrated_analysis,
    display_integrated_comparison
)

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

# Rich Console 초기화
console = Console()

# Typer CLI 앱 생성
app = typer.Typer(help="투자의견 + 추정실적 통합 분석 시스템")

@app.command(name="analyze-integrated")
def analyze_integrated_stock(
    symbol: str = typer.Argument(..., help="분석할 종목 코드 (예: 005930)"),
    days_back: int = typer.Option(30, "--days", "-d", help="투자의견 분석 기간 (일)"),
    export_csv: bool = typer.Option(False, "--export-csv", help="CSV 파일로 내보내기"),
    show_details: bool = typer.Option(True, "--details", help="상세 분석 표시")
):
    """단일 종목의 투자의견과 추정실적을 통합 분석합니다."""
    
    console.print(f"🔍 [bold green]{symbol} 종목 통합 분석을 시작합니다...[/bold green]")
    console.print(f"📅 투자의견 분석 기간: 최근 {days_back}일")
    
    try:
        # 분석기 초기화
        opinion_analyzer = InvestmentOpinionAnalyzer()
        estimate_analyzer = EstimatePerformanceAnalyzer()
        
        with Progress(console=console) as progress:
            task = progress.add_task("[cyan]통합 분석 중...", total=100)
            
            # 투자의견 분석
            progress.update(task, advance=20, description="[cyan]투자의견 분석 중...")
            opinion_analysis = opinion_analyzer.analyze_single_stock(symbol, days_back=days_back)
            
            # 추정실적 분석
            progress.update(task, advance=40, description="[cyan]추정실적 분석 중...")
            estimate_analysis = estimate_analyzer.analyze_single_stock(symbol)
            
            # 통합 분석
            progress.update(task, advance=20, description="[cyan]통합 분석 중...")
            integrated_analysis = create_integrated_analysis(opinion_analysis, estimate_analysis)
            
            progress.update(task, advance=20, description="[cyan]완료!")
        
        # 결과 출력
        display_integrated_analysis(integrated_analysis)
        
        if show_details:
            # 상세 분석 패널
            console.print("\n📋 [bold yellow]상세 통합 분석[/bold yellow]")
            
            # 투자의견 상세
            if opinion_analysis.get('status') == 'success':
                opinion_report = opinion_analyzer.generate_report(opinion_analysis)
                console.print(Panel(opinion_report[:500] + "...", title="📊 투자의견 분석", border_style="blue"))
            
            # 추정실적 상세
            if estimate_analysis.get('status') == 'success':
                estimate_report = estimate_analyzer.generate_report(estimate_analysis)
                console.print(Panel(estimate_report[:500] + "...", title="📈 추정실적 분석", border_style="green"))
        
        # CSV 내보내기
        if export_csv:
            export_integrated_to_csv(integrated_analysis, symbol)
        
    except Exception as e:
        console.print(f"[red]❌ 통합 분석 중 오류 발생: {e}[/red]")

@app.command(name="compare-integrated")
def compare_integrated_stocks(
    symbols_str: str = typer.Option("005930,000660,035420,051910", "--symbols", "-s", help="비교할 종목 코드들 (쉼표로 구분)"),
    days_back: int = typer.Option(30, "--days", "-d", help="투자의견 분석 기간 (일)"),
    export_csv: bool = typer.Option(False, "--export-csv", help="CSV 파일로 내보내기"),
    ranking_only: bool = typer.Option(False, "--ranking-only", help="랭킹만 표시")
):
    """여러 종목의 투자의견과 추정실적을 통합 비교 분석합니다."""
    
    symbols: List[str] = [s.strip() for s in symbols_str.split(',')]
    console.print(f"🔍 [bold green]{len(symbols)}개 종목 통합 비교 분석을 시작합니다...[/bold green]")
    console.print(f"📊 분석 종목: {', '.join(symbols)}")
    console.print(f"📅 투자의견 분석 기간: 최근 {days_back}일")
    
    try:
        # 분석기 초기화
        opinion_analyzer = InvestmentOpinionAnalyzer()
        estimate_analyzer = EstimatePerformanceAnalyzer()
        
        integrated_analyses = {}
        
        with Progress(console=console) as progress:
            task = progress.add_task("[cyan]다중 종목 통합 분석 중...", total=len(symbols))
            
            for i, symbol in enumerate(symbols):
                try:
                    # 투자의견 분석
                    opinion_analysis = opinion_analyzer.analyze_single_stock(symbol, days_back=days_back)
                    
                    # 추정실적 분석
                    estimate_analysis = estimate_analyzer.analyze_single_stock(symbol)
                    
                    # 통합 분석
                    integrated_analysis = create_integrated_analysis(opinion_analysis, estimate_analysis)
                    integrated_analyses[symbol] = integrated_analysis
                    
                except Exception as e:
                    console.print(f"[red]❌ {symbol} 분석 실패: {e}[/red]")
                    integrated_analyses[symbol] = {
                        'symbol': symbol,
                        'status': 'error',
                        'error': str(e)
                    }
                
                progress.update(task, advance=1, description=f"[cyan]분석 중... {symbol} 완료")
        
        # 통합 비교 분석
        comparison_analysis = create_integrated_comparison(integrated_analyses)
        
        # 결과 출력
        if not ranking_only:
            display_integrated_comparison(comparison_analysis)
        else:
            display_rankings_only(comparison_analysis)
        
        # CSV 내보내기
        if export_csv:
            export_comparison_to_csv(comparison_analysis, symbols)
        
    except Exception as e:
        console.print(f"[red]❌ 통합 비교 분석 중 오류 발생: {e}[/red]")

@app.command(name="top-picks")
def find_top_picks(
    symbols_str: str = typer.Option("005930,000660,035420,051910,006400,035720,373220,000270", "--symbols", "-s", help="검색할 종목 코드들 (쉼표로 구분)"),
    days_back: int = typer.Option(30, "--days", "-d", help="투자의견 분석 기간 (일)"),
    min_score: float = typer.Option(60, "--min-score", help="최소 통합 점수"),
    max_stocks: int = typer.Option(5, "--max-stocks", help="최대 추천 종목 수"),
    export_csv: bool = typer.Option(False, "--export-csv", help="CSV 파일로 내보내기")
):
    """통합 분석을 통해 최고의 투자 후보를 찾습니다."""
    
    symbols: List[str] = [s.strip() for s in symbols_str.split(',')]
    console.print(f"🔍 [bold green]최고의 투자 후보를 찾는 중...[/bold green]")
    console.print(f"📊 검색 종목: {len(symbols)}개")
    console.print(f"🎯 최소 통합 점수: {min_score}점")
    console.print(f"📈 최대 추천 종목: {max_stocks}개")
    
    try:
        # 분석기 초기화
        opinion_analyzer = InvestmentOpinionAnalyzer()
        estimate_analyzer = EstimatePerformanceAnalyzer()
        
        top_picks = []
        
        with Progress(console=console) as progress:
            task = progress.add_task("[cyan]종목 스크리닝 중...", total=len(symbols))
            
            for symbol in symbols:
                try:
                    # 투자의견 분석
                    opinion_analysis = opinion_analyzer.analyze_single_stock(symbol, days_back=days_back)
                    
                    # 추정실적 분석
                    estimate_analysis = estimate_analyzer.analyze_single_stock(symbol)
                    
                    # 통합 분석
                    integrated_analysis = create_integrated_analysis(opinion_analysis, estimate_analysis)
                    
                    # 최소 점수 이상인 경우만 포함
                    if integrated_analysis.get('integrated_score', 0) >= min_score:
                        top_picks.append(integrated_analysis)
                    
                except Exception as e:
                    console.print(f"[yellow]⚠️ {symbol} 분석 실패: {e}[/yellow]")
                
                progress.update(task, advance=1, description=f"[cyan]스크리닝 중... {symbol}")
        
        # 점수순으로 정렬
        top_picks.sort(key=lambda x: x.get('integrated_score', 0), reverse=True)
        
        # 최대 개수만큼 선택
        top_picks = top_picks[:max_stocks]
        
        if not top_picks:
            console.print(f"[yellow]⚠️ 최소 점수 {min_score}점 이상인 종목이 없습니다.[/yellow]")
            return
        
        console.print(f"\n🏆 [bold green]최고의 투자 후보 {len(top_picks)}개[/bold green]")
        
        # 상위 종목 테이블
        table = Table(title="최고의 투자 후보")
        table.add_column("순위", style="cyan", width=4)
        table.add_column("종목코드", style="white", width=8)
        table.add_column("통합점수", style="green", width=10)
        table.add_column("등급", style="yellow", width=6)
        table.add_column("투자추천", style="white", width=15)
        table.add_column("리스크", style="red", width=8)
        table.add_column("컨센서스", style="blue", width=10)
        table.add_column("밸류점수", style="magenta", width=10)
        table.add_column("재무점수", style="cyan", width=10)
        table.add_column("PER", style="white", width=8)
        table.add_column("ROE", style="green", width=8)
        
        for i, pick in enumerate(top_picks, 1):
            table.add_row(
                str(i),
                pick['symbol'],
                f"{pick['integrated_score']:.1f}",
                pick['integrated_grade'],
                pick['investment_recommendation'][:12] + "..." if len(pick['investment_recommendation']) > 12 else pick['investment_recommendation'],
                pick['risk_assessment'],
                f"{pick.get('consensus_score', 0):.2f}",
                f"{pick.get('valuation_score', 0)}",
                f"{pick.get('financial_health_score', 0)}",
                f"{pick.get('latest_per', 0):.1f}",
                f"{pick.get('latest_roe', 0):.1f}%"
            )
        
        console.print(table)
        
        # 상위 3개 종목 상세 분석
        console.print("\n📋 [bold yellow]상위 3개 종목 상세 분석[/bold yellow]")
        for i, pick in enumerate(top_picks[:3], 1):
            console.print(f"\n🏅 [bold cyan]{i}위: {pick['symbol']} (통합점수: {pick['integrated_score']:.1f}점)[/bold cyan]")
            console.print(f"투자 추천: {pick['investment_recommendation']}")
            console.print(f"리스크 평가: {pick['risk_assessment']}")
            
            if pick.get('total_opinions', 0) > 0:
                console.print(f"투자의견: 매수 {pick.get('buy_opinions', 0)}건, 보유 {pick.get('hold_opinions', 0)}건, 매도 {pick.get('sell_opinions', 0)}건")
                console.print(f"평균 목표가: {pick.get('avg_target_price', 0):,.0f}원 (상승률: {pick.get('avg_upside', 0):+.1f}%)")
            
            if pick.get('current_price', 0) > 0:
                console.print(f"현재가: {pick['current_price']:,}원")
                console.print(f"매출액: {pick.get('latest_revenue', 0):,.0f}원 (성장률: {pick.get('latest_revenue_growth', 0):+.1f}%)")
                console.print(f"영업이익: {pick.get('latest_operating_profit', 0):,.0f}원 (성장률: {pick.get('latest_operating_profit_growth', 0):+.1f}%)")
                console.print(f"EPS: {pick.get('latest_eps', 0):,.0f}원, PER: {pick.get('latest_per', 0):.1f}배, ROE: {pick.get('latest_roe', 0):.1f}%")
        
        # CSV 내보내기
        if export_csv:
            export_top_picks_to_csv(top_picks)
        
    except Exception as e:
        console.print(f"[red]❌ 투자 후보 검색 중 오류 발생: {e}[/red]")

def display_rankings_only(comparison_analysis: dict):
    """랭킹만 표시합니다."""
    rankings = comparison_analysis.get('rankings', {})
    
    console.print(f"\n✅ 분석 완료: {comparison_analysis['successful_analyses']}/{comparison_analysis['total_stocks']}개 종목")
    
    if 'integrated_score' in rankings:
        console.print("\n🏆 [bold yellow]통합 점수 랭킹[/bold yellow]")
        for i, (symbol, score) in enumerate(rankings['integrated_score'], 1):
            console.print(f"  {i}. {symbol}: {score:.1f}점")
    
    if 'consensus_score' in rankings:
        console.print("\n📊 [bold yellow]투자의견 컨센서스 랭킹[/bold yellow]")
        for i, (symbol, score) in enumerate(rankings['consensus_score'], 1):
            console.print(f"  {i}. {symbol}: {score:.2f}")
    
    if 'valuation_score' in rankings:
        console.print("\n💰 [bold yellow]밸류에이션 점수 랭킹[/bold yellow]")
        for i, (symbol, score) in enumerate(rankings['valuation_score'], 1):
            console.print(f"  {i}. {symbol}: {score}점")
    
    if 'per' in rankings:
        console.print("\n📈 [bold yellow]PER 랭킹 (낮을수록 저평가)[/bold yellow]")
        for i, (symbol, per) in enumerate(rankings['per'], 1):
            console.print(f"  {i}. {symbol}: {per:.1f}배")
    
    if 'roe' in rankings:
        console.print("\n💪 [bold yellow]ROE 랭킹 (높을수록 수익성 우수)[/bold yellow]")
        for i, (symbol, roe) in enumerate(rankings['roe'], 1):
            console.print(f"  {i}. {symbol}: {roe:.1f}%")

def export_integrated_to_csv(integrated_analysis: dict, symbol: str):
    """통합 분석 결과를 CSV로 내보내기"""
    try:
        data = {
            'symbol': [integrated_analysis['symbol']],
            'integrated_score': [integrated_analysis['integrated_score']],
            'integrated_grade': [integrated_analysis['integrated_grade']],
            'investment_recommendation': [integrated_analysis['investment_recommendation']],
            'risk_assessment': [integrated_analysis['risk_assessment']],
            'total_opinions': [integrated_analysis.get('total_opinions', 0)],
            'buy_opinions': [integrated_analysis.get('buy_opinions', 0)],
            'hold_opinions': [integrated_analysis.get('hold_opinions', 0)],
            'sell_opinions': [integrated_analysis.get('sell_opinions', 0)],
            'consensus_score': [integrated_analysis.get('consensus_score', 0)],
            'avg_target_price': [integrated_analysis.get('avg_target_price', 0)],
            'avg_upside': [integrated_analysis.get('avg_upside', 0)],
            'current_price': [integrated_analysis.get('current_price', 0)],
            'latest_revenue': [integrated_analysis.get('latest_revenue', 0)],
            'latest_revenue_growth': [integrated_analysis.get('latest_revenue_growth', 0)],
            'latest_operating_profit': [integrated_analysis.get('latest_operating_profit', 0)],
            'latest_operating_profit_growth': [integrated_analysis.get('latest_operating_profit_growth', 0)],
            'latest_eps': [integrated_analysis.get('latest_eps', 0)],
            'latest_per': [integrated_analysis.get('latest_per', 0)],
            'latest_roe': [integrated_analysis.get('latest_roe', 0)],
            'financial_health_score': [integrated_analysis.get('financial_health_score', 0)],
            'valuation_score': [integrated_analysis.get('valuation_score', 0)],
            'data_quality_score': [integrated_analysis.get('data_quality_score', 0)]
        }
        
        df = pd.DataFrame(data)
        filename = f"integrated_analysis_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        console.print(f"\n💾 통합 분석 결과가 {filename}에 저장되었습니다.")
        
    except Exception as e:
        console.print(f"[red]❌ CSV 내보내기 실패: {e}[/red]")

def export_comparison_to_csv(comparison_analysis: dict, symbols: List[str]):
    """비교 분석 결과를 CSV로 내보내기"""
    try:
        all_data = []
        successful_analyses = {k: v for k, v in comparison_analysis['analyses'].items() if v.get('status') != 'error'}
        
        for symbol, analysis in successful_analyses.items():
            data = {
                'symbol': analysis['symbol'],
                'integrated_score': analysis['integrated_score'],
                'integrated_grade': analysis['integrated_grade'],
                'investment_recommendation': analysis['investment_recommendation'],
                'risk_assessment': analysis['risk_assessment'],
                'total_opinions': analysis.get('total_opinions', 0),
                'buy_opinions': analysis.get('buy_opinions', 0),
                'hold_opinions': analysis.get('hold_opinions', 0),
                'sell_opinions': analysis.get('sell_opinions', 0),
                'consensus_score': analysis.get('consensus_score', 0),
                'avg_target_price': analysis.get('avg_target_price', 0),
                'avg_upside': analysis.get('avg_upside', 0),
                'current_price': analysis.get('current_price', 0),
                'latest_revenue': analysis.get('latest_revenue', 0),
                'latest_revenue_growth': analysis.get('latest_revenue_growth', 0),
                'latest_operating_profit': analysis.get('latest_operating_profit', 0),
                'latest_operating_profit_growth': analysis.get('latest_operating_profit_growth', 0),
                'latest_eps': analysis.get('latest_eps', 0),
                'latest_per': analysis.get('latest_per', 0),
                'latest_roe': analysis.get('latest_roe', 0),
                'financial_health_score': analysis.get('financial_health_score', 0),
                'valuation_score': analysis.get('valuation_score', 0),
                'data_quality_score': analysis.get('data_quality_score', 0)
            }
            all_data.append(data)
        
        if all_data:
            df = pd.DataFrame(all_data)
            filename = f"integrated_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            console.print(f"\n💾 통합 비교 분석 결과가 {filename}에 저장되었습니다.")
        
    except Exception as e:
        console.print(f"[red]❌ CSV 내보내기 실패: {e}[/red]")

def export_top_picks_to_csv(top_picks: List[dict]):
    """상위 투자 후보를 CSV로 내보내기"""
    try:
        all_data = []
        
        for i, pick in enumerate(top_picks, 1):
            data = {
                'rank': i,
                'symbol': pick['symbol'],
                'integrated_score': pick['integrated_score'],
                'integrated_grade': pick['integrated_grade'],
                'investment_recommendation': pick['investment_recommendation'],
                'risk_assessment': pick['risk_assessment'],
                'total_opinions': pick.get('total_opinions', 0),
                'buy_opinions': pick.get('buy_opinions', 0),
                'hold_opinions': pick.get('hold_opinions', 0),
                'sell_opinions': pick.get('sell_opinions', 0),
                'consensus_score': pick.get('consensus_score', 0),
                'avg_target_price': pick.get('avg_target_price', 0),
                'avg_upside': pick.get('avg_upside', 0),
                'current_price': pick.get('current_price', 0),
                'latest_revenue': pick.get('latest_revenue', 0),
                'latest_revenue_growth': pick.get('latest_revenue_growth', 0),
                'latest_operating_profit': pick.get('latest_operating_profit', 0),
                'latest_operating_profit_growth': pick.get('latest_operating_profit_growth', 0),
                'latest_eps': pick.get('latest_eps', 0),
                'latest_per': pick.get('latest_per', 0),
                'latest_roe': pick.get('latest_roe', 0),
                'financial_health_score': pick.get('financial_health_score', 0),
                'valuation_score': pick.get('valuation_score', 0),
                'data_quality_score': pick.get('data_quality_score', 0)
            }
            all_data.append(data)
        
        if all_data:
            df = pd.DataFrame(all_data)
            filename = f"top_picks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            console.print(f"\n💾 상위 투자 후보가 {filename}에 저장되었습니다.")
        
    except Exception as e:
        console.print(f"[red]❌ CSV 내보내기 실패: {e}[/red]")

if __name__ == "__main__":
    app()
