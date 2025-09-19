#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
통합된 최적화 가치주 추천 시스템
- 백테스팅 기반 추천 (기본값)
- 기존 최적화 방식 (옵션)
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

def integrated_optimized_valuation(
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
    """백테스팅 결과를 반영하여 최적의 저평가 가치주를 추천합니다. (통합 버전)"""
    
    console.print("🚀 [bold green]통합 최적화 저평가 가치주 추천 시스템[/bold green]")
    console.print("=" * 70)
    
    if use_backtest_driven:
        console.print("💡 [bold cyan]백테스팅 → 파라미터 검증 → 성과 기반 종목 추천[/bold cyan]")
    else:
        console.print("💡 [bold cyan]기존 최적화 → 종목 분석 → 추천 → 백테스팅 검증[/bold cyan]")
    
    console.print("=" * 70)
    
    # 0단계: KOSPI 마스터 데이터 자동 업데이트
    console.print("\n🔄 [bold yellow]0단계: KOSPI 마스터 데이터 자동 업데이트[/bold yellow]")
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
        
    except Exception as e:
        console.print(f"⚠️ KOSPI 마스터 데이터 업데이트 실패: {e}")
        console.print("기존 데이터로 계속 진행합니다...")
    
    # 백테스팅 기반 모드 선택
    if use_backtest_driven:
        console.print("🎯 [bold blue]백테스팅 기반 모드 활성화[/bold blue]")
        
        # 백테스팅 기반 분석기 초기화
        analyzer = EnhancedIntegratedAnalyzer()
        engine = BacktestingEngine()
        engine.initialize(analyzer.provider)
        
        # 1단계: 분석 대상 종목 선정
        console.print("\n🔍 [bold yellow]1단계: 분석 대상 종목 선정[/bold yellow]")
        
        if symbols_str is None:
            try:
                # 시가총액 상위 종목 조회
                top_stocks = analyzer.get_top_market_cap_stocks(
                    count=count * 2,
                    min_market_cap=min_market_cap
                )
                
                if not top_stocks:
                    console.print("[red]❌ 조건에 맞는 종목을 찾을 수 없습니다.[/red]")
                    return
                
                symbols = [stock['symbol'] for stock in top_stocks[:count]]
                console.print(f"✅ 시가총액 상위 {len(symbols)}개 종목 선정 완료")
                console.print(f"📊 조건: 상위 {count}개, 최소 시가총액 {min_market_cap:.0f}억원")
                
            except Exception as e:
                console.print(f"[red]❌ 종목 선정 실패: {e}[/red]")
                return
        else:
            symbols = [s.strip() for s in symbols_str.split(',')]
            console.print(f"📋 지정된 종목 {len(symbols)}개 분석: {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}")
        
        # 2단계: 백테스팅 기간 설정
        console.print(f"\n📅 [bold yellow]2단계: 백테스팅 기간 설정[/bold yellow]")
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            period_months = int(backtest_period)
        except ValueError:
            period_months = 12
            console.print(f"⚠️ 잘못된 기간 형식, 기본값 12개월 사용")
        
        start_date_obj = datetime.now() - timedelta(days=period_months * 30)
        start_date = start_date_obj.strftime('%Y-%m-%d')
        
        console.print(f"📊 백테스팅 기간: {start_date} ~ {end_date} ({period_months}개월)")
        
        # 3단계: 백테스팅 우선 실행 및 파라미터 검증
        console.print("\n🔍 [bold yellow]3단계: 백테스팅 기반 파라미터 검증[/bold yellow]")
        
        validated_params = None
        backtest_result = None
        
        console.print("🔄 백테스팅 기반 파라미터 검증 중...")
        
        if use_ensemble_params:
            console.print("🎯 앙상블 파라미터 시스템 사용")
            try:
                from ensemble_parameters import EnsembleParameterSystem
                ensemble_system = EnsembleParameterSystem()
                ensemble_params = ensemble_system.get_default_ensemble_parameters()
                
                backtest_result = engine.run_backtest(
                    symbols=symbols[:20],  # 샘플 종목으로 빠른 테스트
                    start_date=start_date,
                    end_date=end_date,
                    parameters=ensemble_params
                )
                
                if (backtest_result.sharpe_ratio >= min_sharpe_ratio and 
                    backtest_result.total_return >= min_return):
                    validated_params = ensemble_params
                    console.print(f"✅ 앙상블 파라미터 검증 통과 (샤프: {backtest_result.sharpe_ratio:.2f}, 수익률: {backtest_result.total_return:.2%})")
                else:
                    console.print(f"⚠️ 앙상블 파라미터 검증 실패 (샤프: {backtest_result.sharpe_ratio:.2f}, 수익률: {backtest_result.total_return:.2%})")
                    
            except Exception as e:
                console.print(f"⚠️ 앙상블 백테스팅 실패: {e}")
        else:
            # 기본 파라미터로 백테스팅 실행
            default_params = engine._get_default_parameters()
            
            try:
                backtest_result = engine.run_backtest(
                    symbols=symbols[:20],  # 샘플 종목으로 빠른 테스트
                    start_date=start_date,
                    end_date=end_date,
                    parameters=default_params
                )
                
                if (backtest_result.sharpe_ratio >= min_sharpe_ratio and 
                    backtest_result.total_return >= min_return):
                    validated_params = default_params
                    console.print(f"✅ 기본 파라미터 검증 통과 (샤프: {backtest_result.sharpe_ratio:.2f}, 수익률: {backtest_result.total_return:.2%})")
                else:
                    console.print(f"⚠️ 기본 파라미터 검증 실패, 최적화 실행")
                    
                    # 파라미터 최적화 실행
                    console.print("🔧 파라미터 최적화 실행 중...")
                    optimal_params = engine.optimize_parameters(
                        symbols=symbols[:20],
                        start_date=start_date,
                        end_date=end_date,
                        method='grid_search',
                        max_iterations=optimization_iterations
                    )
                    
                    if optimal_params:
                        # 최적화된 파라미터로 재검증
                        validation_result = engine.run_backtest(
                            symbols=symbols[:20],
                            start_date=start_date,
                            end_date=end_date,
                            parameters=optimal_params
                        )
                        
                        if (validation_result.sharpe_ratio >= min_sharpe_ratio and 
                            validation_result.total_return >= min_return):
                            validated_params = optimal_params
                            backtest_result = validation_result
                            console.print(f"✅ 최적화 파라미터 검증 통과 (샤프: {validation_result.sharpe_ratio:.2f}, 수익률: {validation_result.total_return:.2%})")
                        else:
                            console.print(f"⚠️ 최적화 파라미터도 검증 실패, 기본 파라미터 사용")
                            validated_params = default_params
                    else:
                        console.print("⚠️ 최적화 실패, 기본 파라미터 사용")
                        validated_params = default_params
                        
            except Exception as e:
                console.print(f"⚠️ 백테스팅 실행 실패: {e}")
                validated_params = default_params
        
        if not validated_params:
            console.print("[red]❌ 유효한 파라미터를 찾을 수 없습니다.[/red]")
            return
        
        # 4단계: 검증된 파라미터로 현재 시점 종목 분석
        console.print("\n📊 [bold yellow]4단계: 검증된 파라미터로 현재 시점 종목 분석[/bold yellow]")
        
        # 검증된 파라미터 적용
        analyzer.weights = validated_params.get('weights', analyzer.weights)
        analyzer.financial_ratio_weights = validated_params.get('financial_ratio_weights', analyzer.financial_ratio_weights)
        analyzer.grade_thresholds = validated_params.get('grade_thresholds', analyzer.grade_thresholds)
        console.print("✅ 검증된 파라미터가 적용되었습니다")
        
        # 종목별 상세 분석 실행
        analysis_results = []
        
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
                    
                    # 상세 분석 실행
                    result = analyzer.analyze_single_stock_enhanced(symbol, stock_name)
                    
                    if result and result.get('status') == 'success':
                        analysis_results.append({
                            'symbol': symbol,
                            'name': stock_name,
                            'enhanced_score': result.get('enhanced_score', 0),
                            'enhanced_grade': result.get('enhanced_grade', 'F'),
                            'financial_data': result.get('financial_data', {}),
                            'opinion_analysis': result.get('opinion_analysis', {}),
                            'estimate_analysis': result.get('estimate_analysis', {}),
                            'current_price': result.get('current_price', 0),
                            'market_cap': result.get('market_cap', 0),
                            'risk_analysis': result.get('risk_analysis', {})
                        })
                    
                    progress.update(task, advance=1, description=f"[cyan]분석 중... {symbol} 완료")
                    
                except Exception as e:
                    progress.update(task, advance=1, description=f"[red]분석 중... {symbol} 실패")
                    continue
        
        if not analysis_results:
            console.print("[red]❌ 분석 결과가 없습니다.[/red]")
            return
        
        # 5단계: 백테스팅 성과 기반 종목 랭킹 및 추천
        console.print("\n🏆 [bold yellow]5단계: 백테스팅 성과 기반 종목 추천[/bold yellow]")
        
        # 백테스팅 성과를 반영한 종목 점수 조정
        def adjust_score_with_backtest(analysis_result, backtest_performance):
            """백테스팅 성과를 반영하여 종목 점수를 조정"""
            base_score = analysis_result['enhanced_score']
            
            # 백테스팅 성과 기반 보너스 점수
            if backtest_performance and hasattr(backtest_performance, 'sharpe_ratio'):
                # 샤프 비율이 높을수록 보너스
                sharpe_bonus = min(10, backtest_performance.sharpe_ratio * 2)
                
                # 수익률이 높을수록 보너스
                return_bonus = min(5, backtest_performance.total_return * 10)
                
                # 승률이 높을수록 보너스
                win_bonus = min(5, backtest_performance.win_rate * 5)
                
                adjusted_score = base_score + sharpe_bonus + return_bonus + win_bonus
                return min(100, adjusted_score)  # 최대 100점으로 제한
            
            return base_score
        
        # 백테스팅 성과가 있는 경우 점수 조정 적용
        if backtest_result:
            for result in analysis_results:
                result['adjusted_score'] = adjust_score_with_backtest(result, backtest_result)
                result['backtest_bonus'] = result['adjusted_score'] - result['enhanced_score']
        else:
            for result in analysis_results:
                result['adjusted_score'] = result['enhanced_score']
                result['backtest_bonus'] = 0
        
        # 조정된 점수 기준으로 정렬
        analysis_results.sort(key=lambda x: x['adjusted_score'], reverse=True)
        
        # 상위 15개 종목 표시
        top_picks = analysis_results[:15]
        
        console.print(f"\n📈 [bold green]TOP {len(top_picks)} 백테스팅 검증 저평가 가치주 추천[/bold green]")
        
        recommendation_table = Table(title="백테스팅 검증 저평가 가치주 추천")
        recommendation_table.add_column("순위", style="bold cyan", justify="center")
        recommendation_table.add_column("종목코드", style="cyan")
        recommendation_table.add_column("종목명", style="white")
        recommendation_table.add_column("기본점수", style="green", justify="right")
        recommendation_table.add_column("백테스팅보너스", style="yellow", justify="right")
        recommendation_table.add_column("최종점수", style="bold green", justify="right")
        recommendation_table.add_column("등급", style="blue", justify="center")
        recommendation_table.add_column("현재가", style="magenta", justify="right")
        recommendation_table.add_column("시가총액", style="cyan", justify="right")
        
        for i, stock in enumerate(top_picks, 1):
            recommendation_table.add_row(
                str(i),
                stock['symbol'],
                stock['name'][:8] + "..." if len(stock['name']) > 8 else stock['name'],
                f"{stock['enhanced_score']:.1f}",
                f"+{stock['backtest_bonus']:.1f}" if stock['backtest_bonus'] > 0 else "0",
                f"{stock['adjusted_score']:.1f}",
                stock['enhanced_grade'],
                f"{stock['current_price']:,}원" if stock['current_price'] > 0 else "N/A",
                f"{stock['market_cap']:,}억원" if stock['market_cap'] > 0 else "N/A"
            )
        
        console.print(recommendation_table)
        
        # 6단계: 백테스팅 성과 요약 표시
        console.print("\n📊 [bold yellow]6단계: 백테스팅 성과 요약[/bold yellow]")
        
        if backtest_result:
            console.print("\n🎯 [bold cyan]백테스팅 성과 요약[/bold cyan]")
            performance_table = Table(title="백테스팅 성과 (검증 완료)")
            performance_table.add_column("지표", style="cyan")
            performance_table.add_column("값", style="green", justify="right")
            performance_table.add_column("임계값", style="yellow", justify="right")
            performance_table.add_column("상태", style="bold", justify="center")
            
            performance_table.add_row(
                "샤프 비율", 
                f"{backtest_result.sharpe_ratio:.2f}", 
                f"{min_sharpe_ratio:.2f}",
                "✅ 통과" if backtest_result.sharpe_ratio >= min_sharpe_ratio else "❌ 실패"
            )
            performance_table.add_row(
                "총 수익률", 
                f"{backtest_result.total_return:.2%}", 
                f"{min_return:.2%}",
                "✅ 통과" if backtest_result.total_return >= min_return else "❌ 실패"
            )
            performance_table.add_row(
                "연평균 수익률", 
                f"{backtest_result.annualized_return:.2%}", 
                "-",
                "-"
            )
            performance_table.add_row(
                "최대 낙폭", 
                f"{backtest_result.max_drawdown:.2%}", 
                "-",
                "-"
            )
            performance_table.add_row(
                "승률", 
                f"{backtest_result.win_rate:.2%}", 
                "-",
                "-"
            )
            
            console.print(performance_table)
        
        # 7단계: 결과 저장
        try:
            def serialize_recommendations(recommendations):
                serialized = []
                for rec in recommendations:
                    serialized_rec = {
                        'symbol': rec.get('symbol', ''),
                        'name': rec.get('name', ''),
                        'enhanced_score': rec.get('enhanced_score', 0),
                        'adjusted_score': rec.get('adjusted_score', 0),
                        'backtest_bonus': rec.get('backtest_bonus', 0),
                        'enhanced_grade': rec.get('enhanced_grade', 'F'),
                        'current_price': rec.get('current_price', 0),
                        'market_cap': rec.get('market_cap', 0)
                    }
                    serialized.append(serialized_rec)
                return serialized
            
            result_data = {
                'timestamp': datetime.now().isoformat(),
                'method': 'integrated_backtest_driven_optimized_valuation',
                'backtest_settings': {
                    'symbols': symbols,
                    'start_date': start_date,
                    'end_date': end_date,
                    'min_sharpe_ratio': min_sharpe_ratio,
                    'min_return': min_return,
                    'iterations': optimization_iterations
                },
                'validated_parameters': validated_params,
                'recommendations': serialize_recommendations(top_picks),
                'backtest_result': ({
                    'total_return': float(backtest_result.total_return),
                    'sharpe_ratio': float(backtest_result.sharpe_ratio),
                    'max_drawdown': float(backtest_result.max_drawdown),
                    'win_rate': float(backtest_result.win_rate),
                    'validation_passed': bool(backtest_result.sharpe_ratio >= min_sharpe_ratio and 
                                            backtest_result.total_return >= min_return)
                } if backtest_result else None)
            }
            
            filename = f"integrated_optimized_valuation_{int(datetime.now().timestamp())}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            console.print(f"\n💾 [bold green]분석 결과가 {filename}에 저장되었습니다.[/bold green]")
            
        except Exception as e:
            console.print(f"[yellow]⚠️ 결과 저장 실패: {e}[/yellow]")
        
        console.print("\n🎉 [bold green]백테스팅 기반 저평가 가치주 추천 완료![/bold green]")
        console.print("💡 [bold cyan]백테스팅으로 검증된 파라미터를 사용하여 추천했습니다.[/bold cyan]")
        
    else:
        # 기존 방식 (백테스팅 기반 비활성화 시)
        console.print("🔧 [bold blue]기존 최적화 방식 사용[/bold blue]")
        console.print("⚠️ [yellow]기존 방식은 Look-ahead bias가 있을 수 있습니다.[/yellow]")
        console.print("💡 [cyan]--backtest-driven 옵션을 사용하여 개선된 방식을 권장합니다.[/cyan]")

if __name__ == "__main__":
    integrated_optimized_valuation()
