# test_integrated_analysis.py
import logging
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import Dict, List, Any
from investment_opinion_analyzer import InvestmentOpinionAnalyzer
from estimate_performance_analyzer import EstimatePerformanceAnalyzer

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

# Rich Console 초기화
console = Console()

def test_integrated_single_stock_analysis():
    """단일 종목의 투자의견과 추정실적을 통합 분석"""
    console.print("\n🧪 [bold blue]단일 종목 통합 분석 테스트[/bold blue]")
    console.print("="*60)
    
    symbol = "005930"  # 삼성전자
    console.print(f"\n📊 [bold yellow]{symbol} (삼성전자) 통합 분석[/bold yellow]")
    
    try:
        # 분석기 초기화
        opinion_analyzer = InvestmentOpinionAnalyzer()
        estimate_analyzer = EstimatePerformanceAnalyzer()
        
        # 투자의견 분석
        console.print("🔍 투자의견 분석 중...")
        opinion_analysis = opinion_analyzer.analyze_single_stock(symbol, days_back=30)
        
        # 추정실적 분석
        console.print("📈 추정실적 분석 중...")
        estimate_analysis = estimate_analyzer.analyze_single_stock(symbol)
        
        # 통합 분석 결과 생성
        integrated_analysis = create_integrated_analysis(opinion_analysis, estimate_analysis)
        
        # 결과 출력
        display_integrated_analysis(integrated_analysis)
        
    except Exception as e:
        console.print(f"[red]❌ 통합 분석 실패: {e}[/red]")

def test_integrated_multiple_stocks_analysis():
    """여러 종목의 투자의견과 추정실적을 통합 비교 분석"""
    console.print("\n🧪 [bold blue]다중 종목 통합 비교 분석 테스트[/bold blue]")
    console.print("="*60)
    
    symbols = ["005930", "000660", "035420", "051910"]  # 삼성전자, SK하이닉스, NAVER, LG화학
    console.print(f"\n📊 [bold yellow]{len(symbols)}개 종목 통합 비교 분석[/bold yellow]")
    console.print(f"분석 종목: {', '.join(symbols)}")
    
    try:
        # 분석기 초기화
        opinion_analyzer = InvestmentOpinionAnalyzer()
        estimate_analyzer = EstimatePerformanceAnalyzer()
        
        integrated_analyses = {}
        
        for symbol in symbols:
            console.print(f"\n🔍 {symbol} 통합 분석 중...")
            
            try:
                # 투자의견 분석
                opinion_analysis = opinion_analyzer.analyze_single_stock(symbol, days_back=30)
                
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
        
        # 통합 비교 분석
        comparison_analysis = create_integrated_comparison(integrated_analyses)
        
        # 결과 출력
        display_integrated_comparison(comparison_analysis)
        
    except Exception as e:
        console.print(f"[red]❌ 통합 비교 분석 실패: {e}[/red]")

def create_integrated_analysis(opinion_analysis: Dict[str, Any], estimate_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """투자의견과 추정실적 분석을 통합하여 종합 분석 결과를 생성합니다."""
    
    integrated = {
        'symbol': opinion_analysis.get('symbol', estimate_analysis.get('symbol', '')),
        'analysis_timestamp': datetime.now().isoformat(),
        'opinion_analysis': opinion_analysis,
        'estimate_analysis': estimate_analysis,
        'integrated_score': 0,
        'integrated_grade': 'N/A',
        'investment_recommendation': 'N/A',
        'risk_assessment': 'N/A'
    }
    
    # 투자의견 분석 결과가 있는 경우
    if opinion_analysis.get('status') == 'success':
        opinion_summary = opinion_analysis.get('summary')
        if opinion_summary:
            integrated['total_opinions'] = opinion_summary.total_opinions
            integrated['buy_opinions'] = opinion_summary.buy_opinions
            integrated['hold_opinions'] = opinion_summary.hold_opinions
            integrated['sell_opinions'] = opinion_summary.sell_opinions
            integrated['consensus_score'] = opinion_analysis.get('consensus_analysis', {}).get('consensus_score', 0)
            integrated['avg_target_price'] = opinion_summary.avg_target_price
            integrated['avg_upside'] = opinion_summary.avg_upside
            integrated['opinion_trend'] = opinion_summary.opinion_trend
    
    # 추정실적 분석 결과가 있는 경우
    if estimate_analysis.get('status') == 'success':
        estimate_summary = estimate_analysis.get('summary')
        if estimate_summary:
            integrated['current_price'] = estimate_summary.current_price
            integrated['latest_revenue'] = estimate_summary.latest_revenue
            integrated['latest_revenue_growth'] = estimate_summary.latest_revenue_growth
            integrated['latest_operating_profit'] = estimate_summary.latest_operating_profit
            integrated['latest_operating_profit_growth'] = estimate_summary.latest_operating_profit_growth
            integrated['latest_eps'] = estimate_summary.latest_eps
            integrated['latest_per'] = estimate_summary.latest_per
            integrated['latest_roe'] = estimate_summary.latest_roe
            integrated['revenue_trend'] = estimate_summary.revenue_trend
            integrated['profit_trend'] = estimate_summary.profit_trend
            integrated['eps_trend'] = estimate_summary.eps_trend
            integrated['data_quality_score'] = estimate_summary.data_quality_score
            
            # 재무건전성 점수
            financial_health = estimate_analysis.get('financial_health', {})
            integrated['financial_health_score'] = financial_health.get('health_score', 0)
            
            # 밸류에이션 점수
            valuation = estimate_analysis.get('valuation_analysis', {})
            integrated['valuation_score'] = valuation.get('overall_score', 0)
    
    # 통합 점수 계산
    integrated_score = calculate_integrated_score(integrated)
    integrated['integrated_score'] = integrated_score
    integrated['integrated_grade'] = get_integrated_grade(integrated_score)
    
    # 투자 추천 생성
    integrated['investment_recommendation'] = generate_investment_recommendation(integrated)
    
    # 리스크 평가
    integrated['risk_assessment'] = assess_risk(integrated)
    
    return integrated

def calculate_integrated_score(integrated: Dict[str, Any]) -> float:
    """통합 점수를 계산합니다 (0-100)."""
    score = 0
    
    # 투자의견 점수 (30%)
    if 'consensus_score' in integrated:
        consensus_score = integrated['consensus_score']
        # -1~1 범위를 0~30점으로 변환
        opinion_score = (consensus_score + 1) * 15  # -1~1 -> 0~30
        score += max(0, min(30, opinion_score))
    
    # 추정실적 점수 (40%)
    if 'financial_health_score' in integrated and 'valuation_score' in integrated:
        financial_score = integrated['financial_health_score'] * 0.2  # 20점 만점
        valuation_score = integrated['valuation_score'] * 0.2  # 20점 만점
        score += financial_score + valuation_score
    
    # 성장성 점수 (20%)
    if 'latest_revenue_growth' in integrated:
        revenue_growth = integrated['latest_revenue_growth']
        if revenue_growth > 20:
            growth_score = 20
        elif revenue_growth > 10:
            growth_score = 15
        elif revenue_growth > 0:
            growth_score = 10
        elif revenue_growth > -10:
            growth_score = 5
        else:
            growth_score = 0
        score += growth_score
    
    # 데이터 품질 점수 (10%)
    if 'data_quality_score' in integrated:
        quality_score = integrated['data_quality_score'] * 10
        score += quality_score
    
    return min(100, max(0, score))

def get_integrated_grade(score: float) -> str:
    """통합 점수를 등급으로 변환합니다."""
    if score >= 80: return 'A'
    elif score >= 60: return 'B'
    elif score >= 40: return 'C'
    elif score >= 20: return 'D'
    else: return 'F'

def generate_investment_recommendation(integrated: Dict[str, Any]) -> str:
    """투자 추천을 생성합니다."""
    score = integrated['integrated_score']
    consensus_score = integrated.get('consensus_score', 0)
    valuation_score = integrated.get('valuation_score', 0)
    financial_score = integrated.get('financial_health_score', 0)
    
    if score >= 80:
        return "강력 매수 추천"
    elif score >= 60:
        if consensus_score > 0.3 and valuation_score >= 40:
            return "매수 추천"
        else:
            return "적극 검토 추천"
    elif score >= 40:
        if consensus_score > 0 and financial_score >= 40:
            return "보유 추천"
        else:
            return "신중 검토"
    elif score >= 20:
        return "관망 추천"
    else:
        return "매도 검토"

def assess_risk(integrated: Dict[str, Any]) -> str:
    """리스크를 평가합니다."""
    risk_factors = []
    
    # 데이터 품질 리스크
    data_quality = integrated.get('data_quality_score', 0)
    if data_quality < 0.5:
        risk_factors.append("데이터 품질 낮음")
    
    # 재무건전성 리스크
    financial_score = integrated.get('financial_health_score', 0)
    if financial_score < 40:
        risk_factors.append("재무건전성 우려")
    
    # 성장성 리스크
    revenue_growth = integrated.get('latest_revenue_growth', 0)
    if revenue_growth < -10:
        risk_factors.append("매출 감소 우려")
    
    # 의견 분산 리스크
    total_opinions = integrated.get('total_opinions', 0)
    if total_opinions > 0:
        buy_ratio = integrated.get('buy_opinions', 0) / total_opinions
        if buy_ratio < 0.3:
            risk_factors.append("투자의견 부정적")
    
    if len(risk_factors) == 0:
        return "낮음"
    elif len(risk_factors) <= 2:
        return "보통"
    else:
        return "높음"

def create_integrated_comparison(integrated_analyses: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """통합 분석 결과들을 비교합니다."""
    successful_analyses = {k: v for k, v in integrated_analyses.items() if v.get('status') != 'error'}
    
    if not successful_analyses:
        return {'status': 'no_data'}
    
    # 각 지표별 랭킹 생성
    rankings = {}
    
    # 통합 점수 랭킹
    integrated_scores = {symbol: analysis['integrated_score'] for symbol, analysis in successful_analyses.items()}
    if integrated_scores:
        rankings['integrated_score'] = sorted(integrated_scores.items(), key=lambda x: x[1], reverse=True)
    
    # 투자의견 컨센서스 랭킹
    consensus_scores = {symbol: analysis.get('consensus_score', 0) for symbol, analysis in successful_analyses.items()}
    if consensus_scores:
        rankings['consensus_score'] = sorted(consensus_scores.items(), key=lambda x: x[1], reverse=True)
    
    # 밸류에이션 점수 랭킹
    valuation_scores = {symbol: analysis.get('valuation_score', 0) for symbol, analysis in successful_analyses.items()}
    if valuation_scores:
        rankings['valuation_score'] = sorted(valuation_scores.items(), key=lambda x: x[1], reverse=True)
    
    # 재무건전성 점수 랭킹
    financial_scores = {symbol: analysis.get('financial_health_score', 0) for symbol, analysis in successful_analyses.items()}
    if financial_scores:
        rankings['financial_health'] = sorted(financial_scores.items(), key=lambda x: x[1], reverse=True)
    
    # PER 랭킹 (낮을수록 좋음)
    per_values = {symbol: analysis.get('latest_per', 999) for symbol, analysis in successful_analyses.items()}
    if per_values:
        rankings['per'] = sorted(per_values.items(), key=lambda x: x[1])
    
    # ROE 랭킹 (높을수록 좋음)
    roe_values = {symbol: analysis.get('latest_roe', 0) for symbol, analysis in successful_analyses.items()}
    if roe_values:
        rankings['roe'] = sorted(roe_values.items(), key=lambda x: x[1], reverse=True)
    
    return {
        'total_stocks': len(integrated_analyses),
        'successful_analyses': len(successful_analyses),
        'rankings': rankings,
        'analyses': integrated_analyses
    }

def display_integrated_analysis(integrated: Dict[str, Any]):
    """통합 분석 결과를 출력합니다."""
    symbol = integrated['symbol']
    
    # 기본 정보 테이블
    table = Table(title=f"{symbol} 통합 분석 결과")
    table.add_column("분석 영역", style="cyan", width=20)
    table.add_column("결과", style="green", width=15)
    
    table.add_row("통합 점수", f"{integrated['integrated_score']:.1f}/100점")
    table.add_row("통합 등급", integrated['integrated_grade'])
    table.add_row("투자 추천", integrated['investment_recommendation'])
    table.add_row("리스크 평가", integrated['risk_assessment'])
    table.add_row("", "")  # 빈 행
    
    # 투자의견 정보
    if integrated.get('total_opinions', 0) > 0:
        table.add_row("총 투자의견", f"{integrated['total_opinions']}건")
        table.add_row("매수 의견", f"{integrated['buy_opinions']}건")
        table.add_row("보유 의견", f"{integrated['hold_opinions']}건")
        table.add_row("매도 의견", f"{integrated['sell_opinions']}건")
        table.add_row("컨센서스 점수", f"{integrated.get('consensus_score', 0):.2f}")
        table.add_row("평균 목표가", f"{integrated.get('avg_target_price', 0):,.0f}원")
        table.add_row("평균 상승률", f"{integrated.get('avg_upside', 0):+.1f}%")
        table.add_row("의견 트렌드", integrated.get('opinion_trend', 'N/A'))
    
    table.add_row("", "")  # 빈 행
    
    # 추정실적 정보
    if integrated.get('current_price', 0) > 0:
        table.add_row("현재가", f"{integrated['current_price']:,}원")
        table.add_row("매출액", f"{integrated.get('latest_revenue', 0):,.0f}원")
        table.add_row("매출 성장률", f"{integrated.get('latest_revenue_growth', 0):+.1f}%")
        table.add_row("영업이익", f"{integrated.get('latest_operating_profit', 0):,.0f}원")
        table.add_row("영업이익 성장률", f"{integrated.get('latest_operating_profit_growth', 0):+.1f}%")
        table.add_row("EPS", f"{integrated.get('latest_eps', 0):,.0f}원")
        table.add_row("PER", f"{integrated.get('latest_per', 0):.1f}배")
        table.add_row("ROE", f"{integrated.get('latest_roe', 0):.1f}%")
        table.add_row("재무건전성", f"{integrated.get('financial_health_score', 0)}/100점")
        table.add_row("밸류에이션", f"{integrated.get('valuation_score', 0)}/100점")
        table.add_row("데이터 품질", f"{integrated.get('data_quality_score', 0):.2f}")
    
    console.print(table)
    
    # 상세 분석 패널
    console.print("\n📋 [bold yellow]통합 분석 상세[/bold yellow]")
    
    # 투자 추천 근거
    recommendation_reasons = []
    if integrated.get('consensus_score', 0) > 0.3:
        recommendation_reasons.append("투자의견 긍정적")
    if integrated.get('valuation_score', 0) > 60:
        recommendation_reasons.append("밸류에이션 우수")
    if integrated.get('financial_health_score', 0) > 60:
        recommendation_reasons.append("재무건전성 양호")
    if integrated.get('latest_revenue_growth', 0) > 10:
        recommendation_reasons.append("성장성 우수")
    
    if recommendation_reasons:
        console.print(f"투자 추천 근거: {', '.join(recommendation_reasons)}")
    
    # 리스크 요인
    risk_factors = []
    if integrated.get('data_quality_score', 0) < 0.5:
        risk_factors.append("데이터 품질 낮음")
    if integrated.get('financial_health_score', 0) < 40:
        risk_factors.append("재무건전성 우려")
    if integrated.get('latest_revenue_growth', 0) < -10:
        risk_factors.append("매출 감소")
    
    if risk_factors:
        console.print(f"리스크 요인: {', '.join(risk_factors)}")

def display_integrated_comparison(comparison: Dict[str, Any]):
    """통합 비교 분석 결과를 출력합니다."""
    if comparison.get('status') == 'no_data':
        console.print("[red]❌ 비교할 데이터가 없습니다.[/red]")
        return
    
    console.print(f"\n✅ 통합 비교 분석 완료: {comparison['successful_analyses']}/{comparison['total_stocks']}개 종목")
    
    # 종목별 통합 점수 테이블
    table = Table(title="종목별 통합 분석 결과")
    table.add_column("종목코드", style="cyan", width=8)
    table.add_column("통합점수", style="green", width=10)
    table.add_column("통합등급", style="yellow", width=8)
    table.add_column("투자추천", style="white", width=15)
    table.add_column("리스크", style="red", width=8)
    table.add_column("컨센서스", style="blue", width=10)
    table.add_column("밸류점수", style="magenta", width=10)
    table.add_column("재무점수", style="cyan", width=10)
    
    successful_analyses = {k: v for k, v in comparison['analyses'].items() if v.get('status') != 'error'}
    
    for symbol, analysis in successful_analyses.items():
        table.add_row(
            symbol,
            f"{analysis['integrated_score']:.1f}",
            analysis['integrated_grade'],
            analysis['investment_recommendation'][:12] + "..." if len(analysis['investment_recommendation']) > 12 else analysis['investment_recommendation'],
            analysis['risk_assessment'],
            f"{analysis.get('consensus_score', 0):.2f}",
            f"{analysis.get('valuation_score', 0)}",
            f"{analysis.get('financial_health_score', 0)}"
        )
    
    console.print(table)
    
    # 랭킹 표시
    rankings = comparison.get('rankings', {})
    
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

def main():
    """메인 테스트 함수"""
    console.print("🚀 [bold green]투자의견 + 추정실적 통합 분석 테스트 시작[/bold green]")
    console.print("="*70)
    
    # 테스트 실행
    test_integrated_single_stock_analysis()
    test_integrated_multiple_stocks_analysis()
    
    console.print("\n✅ [bold green]통합 분석 테스트 완료![/bold green]")

if __name__ == "__main__":
    main()
