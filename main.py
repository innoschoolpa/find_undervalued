#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
통합 저평가 가치주 분석 시스템
- 백테스팅 기반 최적화 추천 (기본값)
- 기존 방식 지원 (옵션)
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from rich.panel import Panel

# 프로젝트 모듈 임포트
from enhanced_integrated_analyzer import EnhancedIntegratedAnalyzer
from backtesting_engine import BacktestingEngine
from market_risk_analyzer import MarketRiskAnalyzer, create_market_risk_analyzer
from kospi_master_download import kospi_master_download, get_kospi_master_dataframe

app = typer.Typer()
console = Console()

def calculate_valuation_score(stock_info: Dict[str, Any]) -> float:
    """종목 정보를 바탕으로 가치 점수를 계산합니다."""
    
    score = 0
    
    # PER 점수 (낮을수록 좋음)
    per = stock_info.get('per', 0)
    if per > 0:
        if per < 10:
            score += 30
        elif per < 15:
            score += 25
        elif per < 20:
            score += 20
        elif per < 30:
            score += 15
        else:
            score += 5
    
    # PBR 점수 (낮을수록 좋음)
    pbr = stock_info.get('pbr', 0)
    if pbr > 0:
        if pbr < 1:
            score += 25
        elif pbr < 1.5:
            score += 20
        elif pbr < 2:
            score += 15
        elif pbr < 3:
            score += 10
        else:
            score += 5
    
    # ROE 점수 (높을수록 좋음)
    roe = stock_info.get('roe', 0)
    if roe > 0:
        if roe > 20:
            score += 20
        elif roe > 15:
            score += 15
        elif roe > 10:
            score += 10
        elif roe > 5:
            score += 5
    
    # 시가총액 점수 (적당한 크기)
    market_cap = stock_info.get('market_cap', 0)
    if market_cap > 0:
        if 1000 <= market_cap <= 50000:  # 1천억 ~ 5조
            score += 15
        elif 500 <= market_cap < 1000 or 50000 < market_cap <= 100000:
            score += 10
        else:
            score += 5
    
    # 거래량 점수 (활발한 거래)
    volume = stock_info.get('volume', 0)
    if volume > 0:
        if volume > 1000000:  # 100만주 이상
            score += 10
        elif volume > 500000:  # 50만주 이상
            score += 5

    return round(score, 2)

@app.command(name="find-undervalued")
def find_undervalued_stocks(
    symbols_str: str = typer.Option(None, "--symbols", "-s", help="분석할 종목 코드 (쉼표로 구분). 미입력시 시가총액 상위 종목 사용"),
    count: int = typer.Option(15, "--count", "-c", help="동적 로드시 가져올 종목 수 (기본값: 15개)"),
    min_market_cap: float = typer.Option(500, "--min-market-cap", help="최소 시가총액 (억원, 기본값: 500억원)"),
    history: bool = typer.Option(False, "--history", "-h", help="일봉 데이터도 함께 조회합니다.")
):
    """지정된 종목들의 가치를 분석하고 저평가된 순서로 정렬하여 보여줍니다."""
    
    # 종목 코드 처리
    if symbols_str is None:
        # 동적으로 시가총액 상위 종목 가져오기
        try:
            analyzer = EnhancedIntegratedAnalyzer()
            top_stocks = analyzer.get_top_market_cap_stocks(count=count, min_market_cap=min_market_cap)
            symbols = [stock['symbol'] for stock in top_stocks]
            console.print(f"🎯 [bold blue]시가총액 상위 종목[/bold blue]을 동적으로 로드했습니다 ({len(symbols)}개 종목)")
            console.print(f"📊 조건: 상위 {count}개, 최소 시가총액 {min_market_cap:,}억원")
            stock_names = [f"{stock['symbol']}({stock['name']})" for stock in top_stocks[:5]]
            console.print(f"📈 로드된 종목: {', '.join(stock_names)}...")
        except Exception as e:
            console.print(f"[yellow]⚠️ 동적 종목 로드 실패: {e}[/yellow]")
            console.print("[yellow]기본 종목 목록을 사용합니다.[/yellow]")
            # 폴백용 기본 종목 목록
            symbols = ["005930", "000660", "035420", "005380", "051910", "035720", "373220", "000270"]
    else:
        symbols = [s.strip() for s in symbols_str.split(',')]
        console.print(f"📊 [bold blue]사용자 지정 {len(symbols)}개 종목[/bold blue]을 분석합니다")
    
    # 분석기 초기화
    analyzer = EnhancedIntegratedAnalyzer()
    
    # 종목별 분석 결과 저장
    results = []
    
    with Progress(console=console) as progress:
        task = progress.add_task("[cyan]종목 분석 중...", total=len(symbols))
        
        for symbol in symbols:
            try:
                # 종목명 조회
                if hasattr(analyzer, '_get_stock_name'):
                    stock_name = analyzer._get_stock_name(symbol)
                else:
                    try:
                        if hasattr(analyzer, '_kospi_index') and symbol in analyzer._kospi_index:
                            stock_name = analyzer._kospi_index[symbol].한글명
                        else:
                            stock_name = symbol
                    except:
                        stock_name = symbol
                
                # 상세 분석 실행 (타임아웃 적용)
                console.print(f"🔍 {symbol} ({stock_name}) 분석 시작...")
                try:
                    # Windows 호환 타임아웃 적용 (ThreadPoolExecutor 사용)
                    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
                    import time
                    
                    start_time = time.time()
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(analyzer.analyze_single_stock_enhanced, symbol, stock_name)
                        try:
                            result = future.result(timeout=30)  # 30초 타임아웃
                            elapsed = time.time() - start_time
                            console.print(f"✅ {symbol} 분석 완료 ({elapsed:.1f}초)")
                        except FutureTimeout:
                            console.print(f"[red]⏱️ {symbol} 분석 타임아웃 (30초 초과)[/red]")
                            result = None
                    
                except Exception as e:
                    console.print(f"[red]❌ {symbol} 분석 오류: {e}[/red]")
                    result = None
                
                if result and result.get('status') == 'success':
                    # 가치 점수 계산
                    stock_info = {
                        'per': result.get('financial_data', {}).get('per', 0),
                        'pbr': result.get('financial_data', {}).get('pbr', 0),
                        'roe': result.get('financial_data', {}).get('roe', 0),
                        'market_cap': result.get('market_cap', 0),
                        'volume': result.get('financial_data', {}).get('volume', 0)
                    }
                    
                    valuation_score = calculate_valuation_score(stock_info)
                    
                    results.append({
                        'symbol': symbol,
                        'name': stock_name,
                        'current_price': result.get('current_price', 0),
                        'market_cap': result.get('market_cap', 0),
                        'enhanced_score': result.get('enhanced_score', 0),
                        'enhanced_grade': result.get('enhanced_grade', 'F'),
                        'valuation_score': valuation_score,
                        'per': stock_info['per'],
                        'pbr': stock_info['pbr'],
                        'roe': stock_info['roe'],
                        'volume': stock_info['volume']
                    })
                
                progress.update(task, advance=1, description=f"[cyan]분석 중... {symbol} 완료")
                
            except Exception as e:
                progress.update(task, advance=1, description=f"[red]분석 중... {symbol} 실패")
                continue
    
    if not results:
        console.print("[red]❌ 분석 결과가 없습니다.[/red]")
        return
    
    # 가치 점수 기준으로 정렬
    results.sort(key=lambda x: x['valuation_score'], reverse=True)
    
    # 결과 표시
    console.print(f"\n📈 [bold green]TOP {min(10, len(results))} 저평가 가치주[/bold green]")
    
    table = Table(title="저평가 가치주 분석 결과")
    table.add_column("순위", style="bold cyan", justify="center")
    table.add_column("종목코드", style="cyan")
    table.add_column("종목명", style="white")
    table.add_column("가치점수", style="green", justify="right")
    table.add_column("종합점수", style="yellow", justify="right")
    table.add_column("등급", style="blue", justify="center")
    table.add_column("현재가", style="magenta", justify="right")
    table.add_column("PER", style="cyan", justify="right")
    table.add_column("PBR", style="cyan", justify="right")
    table.add_column("ROE", style="cyan", justify="right")
    table.add_column("시가총액", style="white", justify="right")
    
    for i, stock in enumerate(results[:10], 1):
        table.add_row(
            str(i),
            stock['symbol'],
            stock['name'][:8] + "..." if len(stock['name']) > 8 else stock['name'],
            f"{stock['valuation_score']:.1f}",
            f"{stock['enhanced_score']:.1f}",
            stock['enhanced_grade'],
            f"{stock['current_price']:,}원" if stock['current_price'] > 0 else "N/A",
            f"{stock['per']:.2f}" if stock['per'] > 0 else "N/A",
            f"{stock['pbr']:.2f}" if stock['pbr'] > 0 else "N/A",
            f"{stock['roe']:.2f}%" if stock['roe'] > 0 else "N/A",
            f"{stock['market_cap']:,}억원" if stock['market_cap'] > 0 else "N/A"
        )
    
    console.print(table)
    
    # 일봉 데이터 표시 (옵션)
    if history and results:
        console.print("\n📊 [bold yellow]일봉 데이터 (최근 5일)[/bold yellow]")
        
        history_df = analyzer.provider.get_daily_price_data(results[0]['symbol'], days_back=5)
        if history_df is not None and not history_df.empty:
            console.print(history_df)
        else:
            console.print("[red]일봉 데이터를 가져오지 못했습니다.[/red]")

@app.command(name="optimized-valuation")
def find_optimized_undervalued_stocks(
    symbols_str: str = typer.Option(None, "--symbols", "-s", help="분석할 종목 코드 (쉼표로 구분). 미입력시 시가총액 상위 종목 자동 선정"),
    count: int = typer.Option(100, "--count", "-c", help="동적 로드시 가져올 종목 수 (기본값: 100개)"),
    min_market_cap: float = typer.Option(1000, "--min-market-cap", help="최소 시가총액 (억원, 기본값: 1000억원)"),
    optimization_iterations: int = typer.Option(30, "--iterations", "-i", help="최적화 반복 횟수 (기본값: 30회)"),
    backtest_period: str = typer.Option("12", "--period", "-p", help="백테스팅 기간 (개월, 기본값: 12개월)"),
    min_sharpe_ratio: float = typer.Option(0.3, "--min-sharpe", help="최소 샤프 비율 임계값 (기본값: 0.3)"),
    min_return: float = typer.Option(0.05, "--min-return", help="최소 수익률 임계값 (기본값: 0.05 = 5%)"),
    exclude_preferred: bool = typer.Option(True, "--exclude-preferred", help="우선주 제외 여부 (기본값: True)"),
    use_ensemble_params: bool = typer.Option(False, "--ensemble", help="앙상블 파라미터 사용 여부 (기본값: False)"),
    use_backtest_driven: bool = typer.Option(True, "--backtest-driven", help="백테스팅 기반 추천 사용 여부 (기본값: True)")
):
    """백테스팅 결과를 반영하여 최적의 저평가 가치주를 추천합니다. (통합 개선 버전)"""
    
    # 통합된 최적화 시스템 실행
    from integrated_optimized_valuation import integrated_optimized_valuation
    integrated_optimized_valuation(
        symbols_str=symbols_str,
        count=count,
        min_market_cap=min_market_cap,
        optimization_iterations=optimization_iterations,
        backtest_period=backtest_period,
        min_sharpe_ratio=min_sharpe_ratio,
        min_return=min_return,
        exclude_preferred=exclude_preferred,
        use_ensemble_params=use_ensemble_params,
        use_backtest_driven=use_backtest_driven
    )

@app.command(name="update-kospi")
def update_kospi_data():
    """KOSPI 마스터 데이터를 업데이트합니다."""
    
    console.print("🔄 [bold yellow]KOSPI 마스터 데이터 업데이트[/bold yellow]")
    
    try:
        # 기존 파일 확인
        kospi_file = 'kospi_code.xlsx'
        if os.path.exists(kospi_file):
            console.print("📊 기존 KOSPI 마스터 데이터를 발견했습니다.")
            console.print("🔄 최신 데이터로 업데이트 중...")
        else:
            console.print("📥 KOSPI 마스터 데이터를 다운로드 중...")
        
        # KOSPI 마스터 데이터 다운로드 및 업데이트
        kospi_master_download(os.getcwd(), verbose=False)
        df = get_kospi_master_dataframe(os.getcwd())
        try:
            df.to_excel(kospi_file, index=False)
        except ImportError as e:
            console.print("[red]openpyxl 패키지가 필요합니다: pip install openpyxl[/red]")
            raise
        console.print(f"✅ KOSPI 마스터 데이터 업데이트 완료: {len(df)}개 종목")
        
        # 업데이트된 데이터 미리보기
        console.print(f"\n📊 [bold blue]업데이트된 데이터 미리보기[/bold blue]")
        preview_table = Table(title="KOSPI 마스터 데이터 미리보기")
        preview_table.add_column("종목코드", style="cyan")
        preview_table.add_column("종목명", style="white")
        preview_table.add_column("시가총액", style="green", justify="right")
        preview_table.add_column("업종", style="yellow")
        
        # 상위 10개 종목 미리보기
        top_10 = df.head(10)
        for _, row in top_10.iterrows():
            preview_table.add_row(
                str(row.get('단축코드', '')),
                str(row.get('한글명', '')),
                f"{row.get('시가총액', 0):,}억원" if row.get('시가총액', 0) > 0 else "N/A",
                str(row.get('지수업종대분류', ''))
            )
        
        console.print(preview_table)
        
        console.print(f"\n💡 [bold cyan]사용 방법[/bold cyan]")
        console.print("• find-undervalued 명령어로 저평가 종목을 분석하세요.")
        console.print("• optimized-valuation 명령어를 다시 실행하여 최신 데이터로 분석하세요.")
        
    except Exception as e:
        console.print(f"[red]❌ KOSPI 마스터 데이터 업데이트 실패: {e}[/red]")
        console.print("인터넷 연결과 파일 권한을 확인해주세요.")

if __name__ == "__main__":
    app()
