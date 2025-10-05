"""Command Line Interface for the enhanced integrated analyzer."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.table import Table

from enhanced_integrated_analyzer_refactored import (
    EnhancedIntegratedAnalyzer,
    UpgradedValueAnalysisPipeline,
    _setup_logging_if_needed,
    serialize_for_json,
)

app = typer.Typer(help="Enhanced Integrated Stock Analyzer CLI")
console = Console()


@app.command()
def analyze(
    symbol: str = typer.Argument(..., help="종목 코드 (6자리)"),
    name: str = typer.Option("", help="종목명"),
    config: str = typer.Option("config.yaml", help="설정 파일 경로"),
    output: str = typer.Option(None, help="결과 출력 파일 경로"),
    verbose: bool = typer.Option(False, help="상세 출력"),
):
    """단일 종목 분석"""
    _setup_logging_if_needed()
    
    analyzer = EnhancedIntegratedAnalyzer(config)
    try:
        result = analyzer.analyze_single_stock(symbol, name)
        
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(serialize_for_json(result), f, ensure_ascii=False, indent=2)
            typer.echo(f"결과가 {output}에 저장되었습니다.")
        else:
            # 콘솔 출력
            console.print(f"\n[bold blue]분석 결과: {result.name} ({result.symbol})[/bold blue]")
            console.print(f"상태: {result.status}")
            console.print(f"점수: {result.enhanced_score:.1f} ({result.enhanced_grade})")
            console.print(f"시가총액: {result.market_cap:,.0f}억원" if result.market_cap else "시가총액: N/A")
            console.print(f"PER: {result.per:.1f}" if result.per else "PER: N/A")
            console.print(f"PBR: {result.pbr:.1f}" if result.pbr else "PBR: N/A")
            console.print(f"ROE: {result.roe:.1f}%" if result.roe else "ROE: N/A")
            
            if result.notes:
                console.print(f"참고사항: {', '.join(result.notes)}")
                
    except Exception as e:
        typer.echo(f"분석 실패: {e}", err=True)
    finally:
        analyzer.close()


@app.command()
def scan(
    max_stocks: int = typer.Option(50, help="분석할 시총 상위 종목 수"),
    min_score: float = typer.Option(20.0, help="최소 점수"),
    max_workers: int = typer.Option(0, help="워커 수(0=자동)"),
    realtime: bool = typer.Option(True, help="실시간 데이터 포함"),
    external: bool = typer.Option(True, help="외부 분석 포함(의견/추정)"),
    config: str = typer.Option("config.yaml", help="설정 파일 경로"),
    output: str = typer.Option(None, help="결과 출력 파일 경로"),
):
    """시총 상위 종목 스캔"""
    _setup_logging_if_needed()
    
    analyzer = EnhancedIntegratedAnalyzer(
        config=config,
        include_realtime=realtime, 
        include_external=external
    )
    
    try:
        results = analyzer.analyze_top_market_cap_stocks_enhanced(
            count=max_stocks,
            min_score=min_score,
            max_workers=(None if max_workers == 0 else max_workers),
        )
        
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(serialize_for_json(results), f, ensure_ascii=False, indent=2)
            typer.echo(f"결과가 {output}에 저장되었습니다.")
        else:
            # 콘솔 테이블 출력
            table = Table(title="시총 상위 종목 분석 결과")
            table.add_column("순위", style="cyan", no_wrap=True)
            table.add_column("종목코드", style="magenta")
            table.add_column("종목명", style="green")
            table.add_column("점수", justify="right", style="yellow")
            table.add_column("등급", style="red")
            table.add_column("시가총액", justify="right", style="blue")
            
            for i, result in enumerate(results[:20], 1):  # 상위 20개만 표시
                market_cap_display = f"{result.market_cap:,.0f}억원" if result.market_cap else "N/A"
                table.add_row(
                    str(i),
                    result.symbol,
                    result.name[:15] + "..." if len(result.name) > 15 else result.name,
                    f"{result.enhanced_score:.1f}",
                    result.enhanced_grade,
                    market_cap_display
                )
            
            console.print(table)
            
    except Exception as e:
        typer.echo(f"스캔 실패: {e}", err=True)
    finally:
        analyzer.close()


@app.command()
def upgraded_pipeline(
    max_stocks: int = typer.Option(10, help="최대 분석 종목 수"),
    min_score: float = typer.Option(20.0, help="최소 점수 임계치"),
    max_workers: int = typer.Option(2, help="최대 워커 수"),
    config: str = typer.Option("config.yaml", help="설정 파일 경로"),
    output: str = typer.Option(None, help="결과 출력 파일 경로"),
    verbose: bool = typer.Option(False, help="상세 출력"),
):
    """업그레이드된 가치 분석 파이프라인 (모든 개선 사항 적용)"""
    _setup_logging_if_needed()
    
    console.print("[bold blue]업그레이드된 가치 분석 파이프라인 시작...[/bold blue]")
    console.print(f"설정: 최대 종목 {max_stocks}개, 최소 점수 {min_score}, 워커 {max_workers}개")
    
    try:
        # 업그레이드된 파이프라인 초기화
        pipeline = UpgradedValueAnalysisPipeline(config)
        
        # 파이프라인 요약 출력
        summary = pipeline.get_pipeline_summary()
        console.print(f"파이프라인: {summary['pipeline_name']} v{summary['version']}")
        console.print(f"단계: {' -> '.join(summary['stages'])}")
        
        # 기존 분석기로 종목 목록 가져오기
        legacy_analyzer = EnhancedIntegratedAnalyzer(config)
        analysis_result = legacy_analyzer.analyze_top_market_cap_stocks_enhanced(
            count=max_stocks, 
            min_score=min_score,
            max_workers=max_workers
        )
        
        # top_recommendations에서 심볼 목록 추출
        top_recommendations = analysis_result.get('top_recommendations', [])
        symbols = [(rec['symbol'], rec['name']) for rec in top_recommendations]
        
        if not symbols:
            console.print("[yellow]분석할 종목이 없습니다.[/yellow]")
            return
        
        console.print(f"분석 대상: {len(symbols)}개 종목")
        
        # 파이프라인으로 분석 실행
        results = pipeline.analyze_portfolio(symbols)
        
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(serialize_for_json(results), f, ensure_ascii=False, indent=2)
            console.print(f"[green]결과가 {output}에 저장되었습니다.[/green]")
        else:
            # 결과 요약 출력
            console.print(f"\n[bold green]분석 완료: {len(results)}개 종목[/bold green]")
            
            # 상위 결과 테이블
            table = Table(title="업그레이드된 파이프라인 분석 결과")
            table.add_column("순위", style="cyan")
            table.add_column("종목코드", style="magenta")
            table.add_column("종목명", style="green")
            table.add_column("점수", justify="right", style="yellow")
            table.add_column("등급", style="red")
            table.add_column("상태", style="blue")
            
            for i, result in enumerate(results[:15], 1):
                table.add_row(
                    str(i),
                    result.symbol,
                    result.name[:12] + "..." if len(result.name) > 12 else result.name,
                    f"{result.enhanced_score:.1f}",
                    result.enhanced_grade,
                    result.status.value
                )
            
            console.print(table)
        
        # 메트릭 요약
        metrics = pipeline.get_metrics_summary()
        if metrics:
            console.print(f"\n[bold blue]메트릭 요약:[/bold blue]")
            console.print(f"  분석된 종목: {metrics.get('stocks_analyzed', 0)}개")
            console.print(f"  API 성공률: {metrics.get('api_success_rate', 0):.1f}%")
            console.print(f"  평균 분석 시간: {metrics.get('avg_analysis_duration', 0):.2f}초")
            
    except Exception as e:
        typer.echo(f"파이프라인 실행 실패: {e}", err=True)
    finally:
        if 'legacy_analyzer' in locals():
            legacy_analyzer.close()


@app.command()
def smoke(
    symbol: str = typer.Argument("005930", help="종목 코드 (기본값: 삼성전자)"),
    name: str = typer.Option("삼성전자", help="종목명"),
    config: str = typer.Option("config.yaml", help="설정 파일 경로"),
):
    """단일 종목 스모크 테스트 (JSON 출력)"""
    _setup_logging_if_needed()
    
    analyzer = EnhancedIntegratedAnalyzer(config)
    try:
        result = analyzer.analyze_single_stock(symbol, name)
        json_output = serialize_for_json(result)
        print(json.dumps(json_output, ensure_ascii=False, indent=2))
    except Exception as e:
        typer.echo(f"스모크 테스트 실패: {e}", err=True)
    finally:
        analyzer.close()


def main():
    """CLI 메인 함수"""
    app()


if __name__ == "__main__":
    main()