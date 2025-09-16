# main.py
import typer
import pandas as pd
import logging
from rich.console import Console
from rich.progress import Progress
from kis_data_provider import KISDataProvider
from typing import List, Dict, Any

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

# Rich Console 초기화
console = Console()

# Typer CLI 앱 생성
app = typer.Typer(help="KIS API 기반 주식 데이터 수집 및 분석 시스템")

# [추가] 저평가 가치 점수를 계산하는 함수
def calculate_valuation_score(stock_info: Dict[str, Any]) -> float:
    """
    PBR과 PER을 기반으로 가치 점수를 계산합니다.
    - PBR, PER이 0 이하일 경우 점수 계산에서 제외합니다.
    - 점수가 높을수록 저평가된 것으로 간주합니다.
    """
    pbr = stock_info.get('pbr', 0)
    per = stock_info.get('per', 0)
    
    score = 0
    
    # PBR 점수 (낮을수록 높음)
    if pbr and 0 < pbr < 1:
        score += (1 - pbr) * 50  # PBR 0에 가까울수록 50점에 근접
    
    # PER 점수 (낮을수록 높음)
    if per and 0 < per < 10:
        score += (10 - per) * 5   # PER 0에 가까울수록 50점에 근접

    return round(score, 2)

@app.command(name="find-undervalued")
def find_undervalued_stocks(
    symbols_str: str = typer.Option("005930,000660,035420,005380,051910,035720,373220,000270", "--symbols", "-s", help="분석할 종목 코드 (쉼표로 구분)"),
    history: bool = typer.Option(False, "--history", "-h", help="일봉 데이터도 함께 조회합니다.")
):
    """지정된 종목들의 가치를 분석하고 저평가된 순서로 정렬하여 보여줍니다."""
    
    symbols: List[str] = [s.strip() for s in symbols_str.split(',')]
    console.print(f"🚀 [bold green]{len(symbols)}개[/bold green] 종목에 대한 가치 분석을 시작합니다...")

    provider = KISDataProvider()
    all_stock_info = []

    with Progress(console=console) as progress:
        task = progress.add_task("[cyan]데이터 수집 및 분석 중...", total=len(symbols))
        for symbol in symbols:
            price_info = provider.get_stock_price_info(symbol)
            if price_info:
                # [추가] 점수 계산 로직 호출
                score = calculate_valuation_score(price_info)
                price_info['score'] = score
                all_stock_info.append(price_info)
                progress.update(task, advance=1, description=f"[cyan]분석 중... {symbol} 완료")
            else:
                progress.update(task, advance=1, description=f"[red]분석 중... {symbol} 실패")

    if not all_stock_info:
        console.print("[bold red]❌ 모든 종목의 데이터를 수집하지 못했습니다. API 키와 종목 코드를 확인해주세요.[/bold red]")
        return

    # Pandas DataFrame으로 변환
    df = pd.DataFrame(all_stock_info)
    
    # [추가] 'score' 컬럼을 기준으로 내림차순 정렬
    df = df.sort_values(by='score', ascending=False).reset_index(drop=True)
    
    console.print("\n📊 [bold yellow]저평가 가치주 분석 결과 (Score가 높을수록 저평가)[/bold yellow]")
    console.print(df)

    # 일봉 데이터 조회 (옵션)
    if history and not df.empty:
        console.print("\n" + "="*50)
        console.print("📜 [bold yellow]일봉 데이터 조회 (가장 저평가된 종목)[/bold yellow]")
        
        # [추가] 가장 점수가 높은(저평가된) 종목의 일봉 데이터를 예시로 조회
        top_symbol = df.iloc[0]['symbol']
        console.print(f"L 예시 종목: [bold cyan]{top_symbol}[/bold cyan] (Score: {df.iloc[0]['score']})")
        
        history_df = provider.get_daily_price_history(top_symbol, days=5)
        if not history_df.empty:
            console.print(history_df)
        else:
            console.print("[red]일봉 데이터를 가져오지 못했습니다.[/red]")

if __name__ == "__main__":
    app()