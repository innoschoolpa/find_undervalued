# main.py
import typer
import pandas as pd
import logging
from rich.console import Console
from rich.progress import Progress
from rich.table import Table
from kis_data_provider import KISDataProvider
from typing import List, Dict, Any
import investment_opinion_cli
from enhanced_integrated_analyzer import EnhancedIntegratedAnalyzer
from market_risk_analyzer import create_market_risk_analyzer

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

# Rich Console 초기화
console = Console()

# Typer CLI 앱 생성
app = typer.Typer(help="KIS API 기반 주식 데이터 수집 및 분석 시스템")

# 투자의견 CLI 서브앱 등록
app.add_typer(investment_opinion_cli.app, name="opinion", help="투자의견 분석 관련 명령어")

# 추정실적 CLI 서브앱 등록
import estimate_performance_cli
app.add_typer(estimate_performance_cli.app, name="estimate", help="추정실적 분석 관련 명령어")

# 통합 분석 CLI 서브앱 등록
import integrated_analysis_cli
app.add_typer(integrated_analysis_cli.app, name="integrated", help="투자의견 + 추정실적 통합 분석 관련 명령어")

# 통합 병렬 분석 CLI 서브앱 등록
import integrated_parallel_analyzer
app.add_typer(integrated_parallel_analyzer.app, name="parallel", help="통합 분석 병렬 처리 관련 명령어")

# 향상된 통합 분석 CLI 서브앱 등록
import enhanced_integrated_analyzer
app.add_typer(enhanced_integrated_analyzer.app, name="enhanced", help="재무비율 분석이 통합된 향상된 분석 시스템")

# 백테스팅 최적화 기능 import
from backtesting_engine import BacktestingEngine, ParameterOptimizer

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
        console.print(f"🎯 [bold blue]사용자 지정 종목[/bold blue]을 사용합니다 ({len(symbols)}개 종목)")
    
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

@app.command(name="optimized-valuation")
def find_optimized_undervalued_stocks(
    symbols_str: str = typer.Option(None, "--symbols", "-s", help="분석할 종목 코드 (쉼표로 구분). 미입력시 시가총액 상위 종목 자동 선정"),
    count: int = typer.Option(30, "--count", "-c", help="동적 로드시 가져올 종목 수 (기본값: 30개)"),
    min_market_cap: float = typer.Option(2000, "--min-market-cap", help="최소 시가총액 (억원, 기본값: 2000억원)"),
    optimization_iterations: int = typer.Option(50, "--iterations", "-i", help="최적화 반복 횟수 (기본값: 50회)"),
    backtest_period: str = typer.Option("12", "--period", "-p", help="백테스팅 기간 (개월, 기본값: 12개월)"),
    show_backtest: bool = typer.Option(True, "--show-backtest", help="백테스팅 결과 표시 여부"),
    exclude_preferred: bool = typer.Option(True, "--exclude-preferred", help="우선주 제외 여부 (기본값: True)"),
    use_ensemble_params: bool = typer.Option(True, "--ensemble", help="앙상블 파라미터 사용 여부 (기본값: True, 최적화된 안정성)")
):
    """백테스팅으로 최적화된 파라미터를 사용하여 저평가 가치주를 추천합니다."""
    
    console.print("🚀 [bold green]백테스팅 최적화 기반 저평가 가치주 추천 시스템[/bold green]")
    console.print("=" * 60)
    
    # 1단계: 종목 리스트 준비
    if symbols_str is None:
        try:
            console.print("🔍 [bold yellow]시가총액 상위 종목 자동 선정 중...[/bold yellow]")
            analyzer = EnhancedIntegratedAnalyzer()
            
            # 시가총액 상위 종목 조회
            top_stocks = analyzer.get_top_market_cap_stocks(
                count=count * 2,  # 여유분을 두고 조회
                min_market_cap=min_market_cap
            )
            
            # 우선주 제외 (옵션)
            if exclude_preferred:
                filtered_stocks = []
                for stock in top_stocks:
                    symbol = stock['symbol']
                    name = stock['name']
                    # 우선주 필터링
                    if not (name.endswith(('우', '우A', '우B', '우C', '우(전환)')) or 
                           symbol.endswith(('5', '6'))):
                        filtered_stocks.append(stock)
                top_stocks = filtered_stocks
                console.print(f"🚫 우선주 제외 후 {len(top_stocks)}개 종목 남음")
            
            # 요청된 개수만큼 선정
            selected_stocks = top_stocks[:count]
            symbols = [stock['symbol'] for stock in selected_stocks]
            
            console.print(f"📊 [bold blue]시가총액 상위 {len(symbols)}개 종목[/bold blue]을 분석 대상으로 선정했습니다")
            console.print(f"💰 최소 시가총액: {min_market_cap:,}억원")
            console.print(f"🚫 우선주 제외: {'예' if exclude_preferred else '아니오'}")
            
            # 선정된 종목 미리보기
            preview_stocks = selected_stocks[:5]
            preview_names = [f"{stock['symbol']}({stock['name']})" for stock in preview_stocks]
            console.print(f"📈 선정된 종목 미리보기: {', '.join(preview_names)}...")
            
        except Exception as e:
            console.print(f"[red]❌ 종목 로드 실패: {e}[/red]")
            console.print("[yellow]기본 종목 목록을 사용합니다.[/yellow]")
            # 폴백용 기본 종목 목록 (우선주 제외)
            symbols = ["005930", "000660", "035420", "051910", "006400", "035720", "373220", "000270"]
    else:
        symbols = [s.strip() for s in symbols_str.split(',')]
        console.print(f"📊 [bold blue]사용자 지정 {len(symbols)}개 종목[/bold blue]을 분석합니다")
    
    # 2단계: 백테스팅 기간 설정
    from datetime import datetime, timedelta
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=int(backtest_period) * 30)).strftime("%Y-%m-%d")
    
    console.print(f"📅 백테스팅 기간: {start_date} ~ {end_date} ({backtest_period}개월)")
    console.print(f"🔄 최적화 반복: {optimization_iterations}회")
    
    # 3단계: 파라미터 최적화 실행
    console.print("\n🔍 [bold yellow]1단계: 파라미터 최적화 실행[/bold yellow]")
    
    # 앙상블 파라미터 시스템 사용 옵션 (CLI에서 전달받음)
    # use_ensemble_params = True  # True: 앙상블 파라미터, False: 최적화 실행
    
    if True:
        console.print("🎯 [bold blue]앙상블 파라미터 시스템 사용 (최적화된 안정성)[/bold blue]")
        
        # 앙상블 파라미터 시스템 초기화
        from ensemble_parameters import EnsembleParameterSystem
        ensemble_system = EnsembleParameterSystem()
        
        # analyzer 초기화 (앙상블 모드에서 필요)
        analyzer = EnhancedIntegratedAnalyzer()
        
        # 테스트 조건들 (다양한 시장 상황)
        test_conditions = [
            {'period': '3months', 'stocks': 3, 'market': 'bull'},
            {'period': '6months', 'stocks': 5, 'market': 'bear'},
            {'period': '12months', 'stocks': 10, 'market': 'volatile'},
            {'period': '3months', 'stocks': 30, 'market': 'stable'}
        ]
        
        console.print("🔄 앙상블 성능 평가 중...")
        
        # 앙상블 성능 평가
        ensemble_results = ensemble_system.evaluate_ensemble_performance(test_conditions)
        
        # 최종 앙상블 파라미터 생성
        optimal_params = ensemble_system.get_ensemble_parameters(ensemble_results['ensemble_weights'])
        
        console.print("✅ [bold green]앙상블 파라미터 적용 완료![/bold green]")
        console.print(f"📊 [yellow]신뢰도 점수: {ensemble_results['confidence_score']:.3f}[/yellow]")
        console.print(f"🏆 [yellow]권장 조합: {ensemble_results['recommended_combination']}[/yellow]")
        console.print("📈 [yellow]앙상블 모드: 여러 전략의 장점을 종합한 안정적 평가[/yellow]")
        
        # 앙상블 파라미터를 사용하므로 최적화 건너뛰기
        # 하지만 백테스팅 검증을 위해 engine 초기화
        engine = BacktestingEngine()
        engine.initialize(analyzer.provider)
    else:
        try:
            # 백테스팅 엔진 초기화
            engine = BacktestingEngine()
            analyzer = EnhancedIntegratedAnalyzer()
            engine.initialize(analyzer.provider)
            
            # 최적화 실행
            optimizer = ParameterOptimizer(engine)
            optimal_params = optimizer.optimize_parameters(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
                optimization_method="random_search",
                max_iterations=optimization_iterations
            )
            
            console.print("✅ [bold green]파라미터 최적화 완료![/bold green]")
            
        except Exception as e:
            console.print(f"[red]❌ 파라미터 최적화 실패: {e}[/red]")
            console.print("[yellow]기본 파라미터로 진행합니다.[/yellow]")
            optimal_params = None
    
    # 최적 파라미터 표시
    if optimal_params:
        if True:
            console.print("\n🎯 [bold cyan]앙상블 파라미터 (최적화된 안정성)[/bold cyan]")
            param_table = Table(title="앙상블 파라미터")
        else:
            console.print("\n🎯 [bold cyan]최적화된 파라미터[/bold cyan]")
            param_table = Table(title="최적화된 파라미터")
        
        param_table.add_column("구분", style="cyan")
        param_table.add_column("값", style="green")
        
        for category, params in optimal_params.items():
            if isinstance(params, dict):
                for key, value in params.items():
                    if category == 'weights':
                        param_table.add_row(f"{category}.{key}", f"{value:.2f}%")
                    else:
                        param_table.add_row(f"{category}.{key}", str(value))
            else:
                param_table.add_row(category, str(params))
        
        console.print(param_table)
    
    # 4단계: 최적화된 파라미터로 종목 분석
    console.print("\n📊 [bold yellow]2단계: 최적화된 파라미터로 종목 분석[/bold yellow]")
    
    try:
        # 최적화된 파라미터 적용
        if optimal_params:
            analyzer.weights = optimal_params.get('weights', analyzer.weights)
            analyzer.financial_ratio_weights = optimal_params.get('financial_ratio_weights', analyzer.financial_ratio_weights)
            analyzer.grade_thresholds = optimal_params.get('grade_thresholds', analyzer.grade_thresholds)
            console.print("✅ 최적화된 파라미터가 적용되었습니다")
        
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
                        # KOSPI 데이터에서 종목명 조회
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
                            'financial_ratios': result.get('financial_ratios', {}),
                            'opinion_analysis': result.get('opinion_analysis', {}),
                            'estimate_analysis': result.get('estimate_analysis', {}),
                            'growth_analysis': result.get('growth_analysis', {}),
                            'scale_analysis': result.get('scale_analysis', {}),
                            'current_price': result.get('current_price', 0),
                            'market_cap': result.get('market_cap', 0)
                        })
                    
                    progress.update(task, advance=1, description=f"[cyan]분석 중... {symbol} 완료")
                    
                except Exception as e:
                    progress.update(task, advance=1, description=f"[red]분석 중... {symbol} 실패")
                    continue
        
        if not analysis_results:
            console.print("[red]❌ 분석 결과가 없습니다.[/red]")
            return
        
        # 5단계: 결과 정렬 및 표시
        console.print("\n🏆 [bold yellow]3단계: 최적화된 저평가 가치주 추천[/bold yellow]")
        
        # 점수 기준으로 정렬
        analysis_results.sort(key=lambda x: x['enhanced_score'], reverse=True)
        
        # 상위 10개 종목 표시
        top_picks = analysis_results[:10]
        
        console.print(f"\n📈 [bold green]TOP {len(top_picks)} 저평가 가치주 추천[/bold green]")
        
        recommendation_table = Table(title="최적화된 저평가 가치주 추천")
        recommendation_table.add_column("순위", style="bold cyan", justify="center")
        recommendation_table.add_column("종목코드", style="cyan")
        recommendation_table.add_column("종목명", style="white")
        recommendation_table.add_column("종합점수", style="green", justify="right")
        recommendation_table.add_column("등급", style="yellow", justify="center")
        recommendation_table.add_column("현재가", style="blue", justify="right")
        recommendation_table.add_column("시가총액", style="magenta", justify="right")
        
        for i, stock in enumerate(top_picks, 1):
            recommendation_table.add_row(
                str(i),
                stock['symbol'],
                stock['name'][:8] + "..." if len(stock['name']) > 8 else stock['name'],
                f"{stock['enhanced_score']:.1f}",
                stock['enhanced_grade'],
                f"{stock['current_price']:,}원" if stock['current_price'] > 0 else "N/A",
                f"{stock['market_cap']:,}억원" if stock['market_cap'] > 0 else "N/A"
            )
        
        console.print(recommendation_table)
        
        # 6단계: 백테스팅 결과 표시 (옵션)
        if show_backtest and optimal_params:
            console.print("\n📊 [bold yellow]4단계: 백테스팅 성과 검증[/bold yellow]")
            
            try:
                # 최적 파라미터로 백테스팅 실행
                backtest_result = engine.run_backtest(
                    symbols=symbols,
                    start_date=start_date,
                    end_date=end_date,
                    parameters=optimal_params
                )
                
                # 백테스팅 결과 요약 표시
                console.print("\n🎯 [bold cyan]백테스팅 성과 요약[/bold cyan]")
                performance_table = Table(title="백테스팅 성과")
                performance_table.add_column("지표", style="cyan")
                performance_table.add_column("값", style="green", justify="right")
                
                performance_table.add_row("총 수익률", f"{backtest_result.total_return:.2%}")
                performance_table.add_row("연평균 수익률", f"{backtest_result.annualized_return:.2%}")
                performance_table.add_row("샤프 비율", f"{backtest_result.sharpe_ratio:.2f}")
                performance_table.add_row("최대 낙폭", f"{backtest_result.max_drawdown:.2%}")
                performance_table.add_row("승률", f"{backtest_result.win_rate:.2%}")
                
                console.print(performance_table)
                
            except Exception as e:
                console.print(f"[yellow]⚠️ 백테스팅 실행 실패: {e}[/yellow]")
        
        # 6단계: 시장 리스크 분석 통합
        console.print("\n🔍 [bold yellow]6단계: 시장 리스크 분석 통합[/bold yellow]")
        
        try:
            # 시장 리스크 분석기 초기화
            risk_analyzer = create_market_risk_analyzer(analyzer.provider)
            
            # 포트폴리오 리스크 분석
            portfolio_risk = risk_analyzer.analyze_portfolio_risk(symbols)
            
            # 리스크 분석 결과 표시
            risk_analyzer.display_risk_analysis(portfolio_risk)
            
            # 백테스팅 결과에 리스크 조정 적용
            if 'backtest_result' in locals() and backtest_result:
                adjusted_return = backtest_result.total_return * portfolio_risk['portfolio_adjustment_factor']
                adjusted_sharpe = backtest_result.sharpe_ratio * portfolio_risk['portfolio_adjustment_factor']
                
                console.print(f"\n📊 [bold cyan]리스크 조정된 백테스팅 결과[/bold cyan]")
                console.print(f"• 원래 수익률: {backtest_result.total_return:.2%}")
                console.print(f"• 조정된 수익률: {adjusted_return:.2%}")
                console.print(f"• 조정 계수: {portfolio_risk['portfolio_adjustment_factor']:.2f}")
                console.print(f"• 포트폴리오 리스크: {portfolio_risk['portfolio_risk_grade']}")
                console.print(f"• 투자 권장: {portfolio_risk['portfolio_recommendation']}")
                
                # 조정된 결과를 backtest_result에 추가
                backtest_result.adjusted_total_return = adjusted_return
                backtest_result.adjusted_sharpe_ratio = adjusted_sharpe
                backtest_result.risk_adjustment_factor = portfolio_risk['portfolio_adjustment_factor']
                backtest_result.portfolio_risk_grade = portfolio_risk['portfolio_risk_grade']
                backtest_result.portfolio_recommendation = portfolio_risk['portfolio_recommendation']
            
        except Exception as e:
            console.print(f"[red]⚠️ 시장 리스크 분석 실패: {e}[/red]")
            portfolio_risk = None
        
        # 7단계: 결과 저장
        try:
            import json
            from datetime import datetime
            
            # JSON 직렬화 가능한 형태로 변환
            def serialize_recommendations(recommendations):
                serialized = []
                for rec in recommendations:
                    serialized_rec = {
                        'symbol': rec.get('symbol', ''),
                        'name': rec.get('name', ''),
                        'enhanced_score': rec.get('enhanced_score', 0),
                        'enhanced_grade': rec.get('enhanced_grade', 'F'),
                        'current_price': rec.get('current_price', 0),
                        'market_cap': rec.get('market_cap', 0)
                    }
                    serialized.append(serialized_rec)
                return serialized
            
            result_data = {
                'timestamp': datetime.now().isoformat(),
                'optimization_settings': {
                    'symbols': symbols,
                    'start_date': start_date,
                    'end_date': end_date,
                    'iterations': optimization_iterations
                },
                'optimal_parameters': optimal_params,
                'recommendations': serialize_recommendations(top_picks),
                'market_risk_analysis': portfolio_risk if 'portfolio_risk' in locals() and portfolio_risk else None,
                'backtest_result': {
                    'total_return': backtest_result.total_return if 'backtest_result' in locals() else None,
                    'sharpe_ratio': backtest_result.sharpe_ratio if 'backtest_result' in locals() else None,
                    'max_drawdown': backtest_result.max_drawdown if 'backtest_result' in locals() else None,
                    'adjusted_total_return': getattr(backtest_result, 'adjusted_total_return', None) if 'backtest_result' in locals() else None,
                    'adjusted_sharpe_ratio': getattr(backtest_result, 'adjusted_sharpe_ratio', None) if 'backtest_result' in locals() else None,
                    'risk_adjustment_factor': getattr(backtest_result, 'risk_adjustment_factor', None) if 'backtest_result' in locals() else None,
                    'portfolio_risk_grade': getattr(backtest_result, 'portfolio_risk_grade', None) if 'backtest_result' in locals() else None,
                    'portfolio_recommendation': getattr(backtest_result, 'portfolio_recommendation', None) if 'backtest_result' in locals() else None,
                } if show_backtest and optimal_params else None
            }
            
            filename = f"optimized_valuation_{int(datetime.now().timestamp())}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            console.print(f"\n💾 [bold green]분석 결과가 {filename}에 저장되었습니다.[/bold green]")
            
        except Exception as e:
            console.print(f"[yellow]⚠️ 결과 저장 실패: {e}[/yellow]")
        
        console.print("\n🎉 [bold green]최적화된 저평가 가치주 추천 완료![/bold green]")
        
    except Exception as e:
        console.print(f"[red]❌ 종목 분석 실패: {e}[/red]")

if __name__ == "__main__":
    app()
