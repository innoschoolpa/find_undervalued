#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integrated Undervalued Stock Analysis System
- Backtesting-based optimization recommendation (default)
- Support for conventional methods (optional)
"""

import os
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from decimal import Decimal

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

# Project module imports
from enhanced_integrated_analyzer import EnhancedIntegratedAnalyzer
from kospi_master_download import kospi_master_download, get_kospi_master_dataframe

app = typer.Typer()
console = Console()

# --- Constants ---
PREFERRED_STOCK_SUFFIXES = {"우", "우B", "우(전환)", "우선", "1우", "2우"}
ANALYSIS_TIMEOUT_SECONDS_DEFAULT = 30
MAX_RETRY_PER_STOCK = 1  # 경량 재시도 1회

# --- Helper Functions ---

def serialize_for_json(obj):
    """
    Convert various Python/NumPy/Decimal/Datetime containers to JSON-serializable.
    - Handles: dict/list/tuple/set, numpy scalars/arrays (flatten basic), Decimal, datetime/date, objects with __dict__
    """
    import numpy as np
    from datetime import date, datetime

    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if hasattr(obj, "tolist"):  # numpy arrays
        try:
            return obj.tolist()
        except Exception:
            pass
    # numpy scalars
    np_types = ("int_", "int8", "int16", "int32", "int64",
                "float_", "float16", "float32", "float64", "bool_")
    if obj.__class__.__name__ in np_types:
        try:
            return obj.item()
        except Exception:
            return float(obj)
    if isinstance(obj, dict):
        return {serialize_for_json(k): serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [serialize_for_json(x) for x in obj]
    if hasattr(obj, "__dict__"):
        return {k: serialize_for_json(v) for k, v in obj.__dict__.items()}
    return str(obj)

def _safe_str(x: Any) -> str:
    try:
        return str(x) if x is not None else ""
    except Exception:
        return ""

def _is_preferred_stock_name(name: Optional[str]) -> bool:
    """
    우선주 식별: 접미형('우','1우','2우','우B','우선'), 괄호 표기('우(전환)') 등 정규식 기반.
    - 부분 포함이 아닌 '정규 패턴'으로만 판정하여 오검출 축소
    """
    if not name:
        return False
    import re
    # 공백/괄호/숫자 변형 포함, 예: 삼성전자우, 삼성전자 1우, 삼성전자우B, 삼성전자우(전환)
    pattern = r"(우|[12]우|우B|우선)(?:$|\)|\s)"
    return bool(re.search(pattern, name))

def _update_kospi_master_data() -> bool:
    """
    Downloads and updates the KOSPI master data file.

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    console.print("\n🔄 [bold yellow]Step 0: Auto-updating KOSPI Master Data[/bold yellow]")
    kospi_file = 'kospi_code.xlsx'
    try:
        if os.path.exists(kospi_file):
            console.print("📊 Found existing KOSPI master data. Updating...")
        else:
            console.print("📥 Downloading KOSPI master data...")

        kospi_master_download(os.getcwd(), verbose=False)
        df = get_kospi_master_dataframe(os.getcwd())
        df.to_excel(kospi_file, index=False)
        console.print(f"✅ KOSPI master data update complete: {len(df)} stocks")
        return True
    except ImportError:
        console.print("[red]Error: 'openpyxl' package is required. Please run 'pip install openpyxl'[/red]")
        return False
    except Exception as e:
        console.print(f"⚠️ KOSPI master data update failed: {e}")
        console.print("Proceeding with existing data if available...")
        return False

def _get_stock_name(analyzer: EnhancedIntegratedAnalyzer, symbol: str) -> str:
    """
    A unified function to retrieve the stock name using available methods in the analyzer.
    
    Args:
        analyzer: The instance of the analyzer class.
        symbol: The stock symbol.

    Returns:
        The stock name or the symbol itself as a fallback.
    """
    # Ensure symbol is string and properly formatted
    symbol_str = _safe_str(symbol).zfill(6)  # Pad with zeros to 6 digits
    
    # Try to get from KOSPI index first (dict / DataFrame / Series 모두 대응)
    if hasattr(analyzer, '_kospi_index') and analyzer._kospi_index is not None:
        try:
            idx = analyzer._kospi_index
            for test_symbol in (symbol_str, _safe_str(symbol)):
                # dict-like
                if isinstance(idx, dict) and test_symbol in idx:
                    row = idx[test_symbol]
                    name = None
                    if isinstance(row, dict):
                        name = row.get("한글명") or row.get("name")
                    else:
                        # pandas Series / namedtuple / object
                        name = getattr(row, "한글명", None) or getattr(row, "name", None)
                    if name:
                        return _safe_str(name)
                # pandas DataFrame
                try:
                    import pandas as pd
                    if "DataFrame" in type(idx).__name__:
                        if test_symbol in getattr(idx, "index", []):
                            row = idx.loc[test_symbol]
                            name = None
                            if hasattr(row, "to_dict"):
                                rd = row.to_dict()
                                name = rd.get("한글명") or rd.get("name")
                            if name:
                                return _safe_str(name)
                except Exception:
                    pass
        except Exception as e:
            console.print(f"[yellow]⚠️ Error getting stock name for {symbol}: {e}[/yellow]")
    
    # Try analyzer's internal method if available
    if hasattr(analyzer, '_get_stock_name'):
        try:
            return analyzer._get_stock_name(symbol)
        except Exception:
            pass  # Fallback to the next method
    
    # If all else fails, return the symbol
    return symbol_str

def _run_analysis_on_symbols(analyzer: EnhancedIntegratedAnalyzer, symbols: List[str],
                             analysis_timeout_sec: int) -> List[Dict[str, Any]]:
    """
    Runs the enhanced analysis for a list of stock symbols with a progress bar and timeout.

    Args:
        analyzer: The instance of the analyzer class.
        symbols: A list of stock symbols to analyze.

    Returns:
        A list of dictionaries, where each dictionary contains the analysis result for a stock.
    """
    results = []
    with Progress(console=console) as progress:
        task = progress.add_task("[cyan]Analyzing stocks...", total=len(symbols))
        
        for symbol in symbols:
            stock_name = _get_stock_name(analyzer, symbol)
            console.print(f"🔍 Analyzing {symbol} ({stock_name})...")
            
            result_data = None
            try:
                attempts = 0
                last_err: Optional[Exception] = None
                while attempts <= MAX_RETRY_PER_STOCK:
                    attempts += 1
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        start_time = time.time()
                        future = executor.submit(analyzer.analyze_single_stock_enhanced, symbol, stock_name)
                        try:
                            result_data = future.result(timeout=analysis_timeout_sec)
                            elapsed = time.time() - start_time
                            console.print(f"✅ Analysis for {symbol} complete ({elapsed:.1f}s){' (retry)' if attempts>1 else ''}")
                            break
                        except FutureTimeout as te:
                            last_err = te
                            console.print(f"[red]⏱️ Analysis for {symbol} timed out (>{analysis_timeout_sec}s){' - retrying' if attempts<=MAX_RETRY_PER_STOCK else ''}[/red]")
                        except Exception as e:
                            last_err = e
                            console.print(f"[red]❌ Error analyzing {symbol}: {e}{' - retrying' if attempts<=MAX_RETRY_PER_STOCK else ''}[/red]")
                if result_data is None and last_err:
                    console.print(f"[yellow]↪ Skipped {symbol} after retries: {last_err}[/yellow]")
            except FutureTimeout:
                # 이 블록은 이론상 도달하지 않음(상단에서 처리)
                console.print(f"[red]⏱️ Analysis for {symbol} timed out[/red]")
            except Exception as e:
                console.print(f"[red]❌ Error analyzing {symbol}: {e}[/red]")

            if result_data and result_data.get('status') == 'success':
                results.append(result_data)
            
            progress.update(task, advance=1)
            
    return results


def calculate_valuation_score(stock_info: Dict[str, Any]) -> float:
    """
    Calculates a valuation score for a stock based on its financial metrics.

    Args:
        stock_info: A dictionary containing financial data like per, pbr, roe, etc.

    Returns:
        The calculated valuation score.
    """
    score = 0.0
    
    # 단위 주의:
    # - market_cap: 100M KRW(=억) 기준으로 들어온다고 가정 (표시 로직과 일치)
    # - per/pbr/roe/volume: analyzer 출력 형식을 그대로 사용
    scoring_map = {
        'per': (stock_info.get('per', 0), [(10, 30), (15, 25), (20, 20), (30, 15)]),
        'pbr': (stock_info.get('pbr', 0), [(1, 25), (1.5, 20), (2, 15), (3, 10)]),
        'roe': (stock_info.get('roe', 0), [(-float('inf'), 0), (5, 5), (10, 10), (15, 15), (20, 20)]), # Reversed for increasing score
        # market_cap tiers는 아래의 범위 가점 로직으로만 사용(중복 가중 제거)
        'market_cap': (stock_info.get('market_cap', 0), []),
        'volume': (stock_info.get('volume', 0), [(-float('inf'), 0), (500000, 5), (1000000, 10)]) # Reversed for increasing score
    }

    # PER and PBR (lower is better)
    for metric in ['per', 'pbr']:
        value, tiers = scoring_map[metric]
        if value > 0:
            for threshold, points in tiers:
                if value < threshold:
                    score += points
                    break
            else: # If no break
                score += 5

    # ROE and Volume (higher is better)
    for metric in ['roe', 'volume']:
        value, tiers = scoring_map[metric]
        points_to_add = 0
        if value > 0:
            for threshold, points in reversed(tiers): # Check from highest to lowest
                 if value > threshold:
                     points_to_add = points
                     break
        score += points_to_add

    # Market Cap (specific ranges are better)
    market_cap, _ = scoring_map['market_cap']
    # 1000억~5조 구간 가점 (중형~대형의 유동성·안정성 균형)
    if 1000 <= market_cap <= 50000:
        score += 15
    elif 500 <= market_cap < 1000 or 50000 < market_cap <= 100000:
        score += 10
    elif market_cap > 0:
        score += 5
    
    return round(score, 2)

# --- Typer Commands ---

@app.command(name="find-undervalued")
def find_undervalued_stocks(
    symbols_str: str = typer.Option(None, "--symbols", "-s", help="Comma-separated stock symbols. Fetches top market cap stocks if empty."),
    count: int = typer.Option(15, "--count", "-c", help="Number of stocks to fetch if symbols are not provided."),
    min_market_cap: float = typer.Option(500, "--min-market-cap", help="Minimum market cap in 100M KRW (e.g., 500 for 50B KRW)."),
    analysis_timeout_sec: int = typer.Option(ANALYSIS_TIMEOUT_SECONDS_DEFAULT, "--analysis-timeout", help="Per-stock analysis timeout seconds."),
):
    """Analyzes and ranks specified stocks by a custom valuation score."""
    analyzer = EnhancedIntegratedAnalyzer()
    symbols = []

    if symbols_str:
        symbols = [s.strip() for s in symbols_str.split(',')]
        console.print(f"📊 [bold blue]Analyzing {len(symbols)} user-specified stocks[/bold blue]")
    else:
        try:
            console.print(f"🎯 [bold blue]Dynamically loading top {count} stocks by market cap[/bold blue]")
            top_stocks = analyzer.get_top_market_cap_stocks(count=count, min_market_cap=min_market_cap)
            symbols = [stock['symbol'] for stock in top_stocks]
            stock_names = [_get_stock_name(analyzer, s) for s in symbols[:5]]
            console.print(f"📈 Loaded stocks: {', '.join(stock_names)}...")
        except Exception as e:
            console.print(f"[yellow]⚠️ Failed to load dynamic stocks: {e}[/yellow]")
            return

    if not symbols:
        console.print("[red]No stocks to analyze.[/red]")
        return
        
    analysis_results = _run_analysis_on_symbols(analyzer, symbols, analysis_timeout_sec)
    
    if not analysis_results:
        console.print("[red]❌ No analysis results were generated.[/red]")
        return

    # Calculate valuation scores and prepare for display
    results_with_scores = []
    for res in analysis_results:
        stock_info = {
            'per': res.get('financial_data', {}).get('per', 0),
            'pbr': res.get('financial_data', {}).get('pbr', 0),
            'roe': res.get('financial_data', {}).get('roe', 0),
            'market_cap': res.get('market_cap', 0),
            'volume': res.get('financial_data', {}).get('volume', 0)
        }
        res['valuation_score'] = calculate_valuation_score(stock_info)
        results_with_scores.append(res)

    results_with_scores.sort(key=lambda x: x['valuation_score'], reverse=True)

    # Display results
    console.print(f"\n📈 [bold green]TOP {min(10, len(results_with_scores))} Undervalued Stocks by Valuation Score[/bold green]")
    table = Table(title="Undervalued Stock Analysis Results")
    headers = ["Rank", "Symbol", "Name", "Valuation Score", "Overall Score", "Grade", "Price", "PER", "PBR", "ROE", "Market Cap"]
    styles = ["cyan", "cyan", "white", "bold green", "yellow", "blue", "magenta", "cyan", "cyan", "cyan", "white"]
    justifies = ["center", "left", "left", "right", "right", "center", "right", "right", "right", "right", "right"]
    
    for header, style, justify in zip(headers, styles, justifies):
        table.add_column(header, style=style, justify=justify)
        
    for i, stock in enumerate(results_with_scores[:10], 1):
        fin_data = stock.get('financial_data', {})
        table.add_row(
            str(i),
            stock['symbol'],
            stock.get('name', 'N/A')[:10],
            f"{stock['valuation_score']:.1f}",
            f"{stock.get('enhanced_score', 0):.1f}",
            stock.get('enhanced_grade', 'F'),
            f"{stock.get('current_price', 0):,} KRW",
            f"{fin_data.get('per', 0):.2f}",
            f"{fin_data.get('pbr', 0):.2f}",
            f"{fin_data.get('roe', 0):.2f}%",
            f"{stock.get('market_cap', 0):,}억"
        )
    console.print(table)
    
    # Save results
    try:
        serialized_results = serialize_for_json(results_with_scores)
        filename = f"find_undervalued_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(serialized_results, f, ensure_ascii=False, indent=2)
        console.print(f"\n💾 [bold green]Analysis results saved to {filename}[/bold green]")
    except Exception as e:
        console.print(f"[yellow]⚠️ Failed to save results: {e}[/yellow]")


@app.command(name="optimized-valuation")
def find_optimized_undervalued_stocks(
    symbols_str: str = typer.Option(None, "--symbols", "-s", help="Comma-separated stock symbols. Fetches top stocks if empty."),
    count: int = typer.Option(50, "--count", "-c", help="Number of top stocks to analyze if symbols are not provided."),
    min_market_cap: float = typer.Option(1000, "--min-market-cap", help="Minimum market cap in 100M KRW."),
    exclude_preferred: bool = typer.Option(True, "--exclude-preferred", help="Exclude preferred stocks from analysis."),
    skip_kospi_update: bool = typer.Option(False, "--skip-kospi-update", help="Skip KOSPI master data auto-update step."),
    analysis_timeout_sec: int = typer.Option(ANALYSIS_TIMEOUT_SECONDS_DEFAULT, "--analysis-timeout", help="Per-stock analysis timeout seconds."),
):
    """Recommends optimized undervalued stocks based on a comprehensive analysis score."""
    console.print("🚀 [bold green]Optimized Undervalued Stock Recommendation System[/bold green]")
    
    if not skip_kospi_update:
        _update_kospi_master_data()
    
    analyzer = EnhancedIntegratedAnalyzer()
    symbols = []

    console.print("\n🔍 [bold yellow]Step 1: Selecting Stocks for Analysis[/bold yellow]")
    if symbols_str:
        symbols = [s.strip() for s in symbols_str.split(',')]
        console.print(f"📋 Analyzing {len(symbols)} specified stocks: {', '.join(symbols[:5])}...")
    else:
        try:
            top_stocks = analyzer.get_top_market_cap_stocks(count=count, min_market_cap=min_market_cap)
            if not top_stocks:
                console.print("[red]❌ Could not find any stocks matching the criteria.[/red]")
                return

            if exclude_preferred:
                initial_count = len(top_stocks)
                filtered = []
                for stock in top_stocks:
                    nm = _get_stock_name(analyzer, stock['symbol'])
                    if not _is_preferred_stock_name(nm):
                        filtered.append(stock)
                top_stocks = filtered
                console.print(f"🚫 Excluded {initial_count - len(top_stocks)} preferred stocks.")
            
            symbols = [stock['symbol'] for stock in top_stocks]
            console.print(f"✅ Selected top {len(symbols)} stocks for analysis.")
        except Exception as e:
            console.print(f"[red]❌ Failed to select stocks: {e}[/red]")
            return

    if not symbols:
        console.print("[red]No stocks to analyze.[/red]")
        return
    
    console.print("\n📊 [bold yellow]Step 2: Executing Detailed Analysis[/bold yellow]")
    analysis_results = _run_analysis_on_symbols(analyzer, symbols, analysis_timeout_sec)
    
    if not analysis_results:
        console.print("[red]❌ No analysis results were generated.[/red]")
        return
    
    console.print("\n🏆 [bold yellow]Step 3: Ranking and Recommending Stocks[/bold yellow]")
    analysis_results.sort(key=lambda x: x.get('enhanced_score', 0), reverse=True)
    top_picks = analysis_results[:min(len(analysis_results), 20)] # Recommend top 20

    console.print(f"\n📈 [bold green]TOP {len(top_picks)} Optimized Undervalued Stock Recommendations[/bold green]")
    rec_table = Table(title="Optimized Stock Recommendations")
    headers = ["Rank", "Symbol", "Name", "Overall Score", "Grade", "Price", "Market Cap", "PER", "PBR", "ROE", "52W Position"]
    styles = ["cyan", "cyan", "white", "bold green", "blue", "magenta", "cyan", "yellow", "yellow", "yellow", "magenta"]
    justifies = ["center", "left", "left", "right", "center", "right", "right", "right", "right", "right", "right"]

    for header, style, justify in zip(headers, styles, justifies):
        rec_table.add_column(header, style=style, justify=justify)

    for i, stock in enumerate(top_picks, 1):
        fin_data = stock.get('financial_data', {})
        price_position = stock.get('price_position')
        position_text = f"{price_position:.1f}%" if price_position is not None else "N/A"
        rec_table.add_row(
            str(i), stock['symbol'], stock.get('name', 'N/A')[:10],
            f"{stock.get('enhanced_score', 0):.1f}", stock.get('enhanced_grade', 'F'),
            f"{stock.get('current_price', 0):,} KRW", f"{stock.get('market_cap', 0):,}억",
            f"{fin_data.get('per', 0):.2f}", f"{fin_data.get('pbr', 0):.2f}", f"{fin_data.get('roe', 0):.2f}%",
            position_text
        )
    console.print(rec_table)

    # Step 4: Save results
    try:
        # Serialize the results for JSON
        serialized_picks = serialize_for_json(top_picks)
        
        filename = f"optimized_valuation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(serialized_picks, f, ensure_ascii=False, indent=2)
        console.print(f"\n💾 [bold green]Analysis results saved to {filename}[/bold green]")
    except Exception as e:
        console.print(f"[yellow]⚠️ Failed to save results: {e}[/yellow]")

@app.command(name="update-kospi")
def update_kospi_data():
    """Downloads and updates the KOSPI master data file."""
    if _update_kospi_master_data():
        console.print("\n💡 [bold cyan]How to use:[/bold cyan]")
        console.print("• Run 'find-undervalued' to analyze stocks with the classic valuation score.")
        console.print("• Run 'optimized-valuation' to get recommendations based on the comprehensive score.")

if __name__ == "__main__":
    app()
