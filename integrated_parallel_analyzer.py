# integrated_parallel_analyzer.py
import typer
import pandas as pd
import numpy as np
import logging
import time
import os
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import queue
from rich.console import Console
from rich.progress import Progress
from rich.table import Table
from rich.panel import Panel
from typing import List, Dict, Any, Optional
from kis_data_provider import KISDataProvider
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
logger = logging.getLogger(__name__)

# Rich Console 초기화
console = Console()

# TPS 제한을 고려한 레이트리미터 클래스
class TPSRateLimiter:
    """KIS OpenAPI TPS 제한을 고려한 레이트리미터"""
    
    def __init__(self, max_tps: int = 8):  # 안전 마진을 위해 8로 설정
        self.max_tps = max_tps
        self.requests = queue.Queue()
        self.lock = Lock()
    
    def acquire(self):
        """요청 허가를 받습니다."""
        with self.lock:
            now = time.time()
            
            # 1초 이전의 요청들을 제거
            while not self.requests.empty():
                try:
                    request_time = self.requests.get_nowait()
                    if now - request_time < 1.0:
                        self.requests.put(request_time)
                        break
                except queue.Empty:
                    break
            
            # TPS 제한 확인
            if self.requests.qsize() >= self.max_tps:
                # 가장 오래된 요청이 1초가 지날 때까지 대기
                oldest_request = self.requests.get()
                sleep_time = 1.0 - (now - oldest_request)
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            # 현재 요청 기록
            self.requests.put(time.time())

# 전역 레이트리미터 인스턴스
rate_limiter = TPSRateLimiter(max_tps=8)

class IntegratedParallelAnalyzer:
    """통합 분석을 위한 병렬 처리 클래스"""
    
    def __init__(self):
        self.opinion_analyzer = InvestmentOpinionAnalyzer()
        self.estimate_analyzer = EstimatePerformanceAnalyzer()
        self.provider = KISDataProvider()
        self.kospi_data = None
        self._load_kospi_data()
    
    def _load_kospi_data(self):
        """KOSPI 마스터 데이터를 로드합니다."""
        try:
            # KOSPI 마스터 데이터 로드
            kospi_file = 'kospi_code.xlsx'
            if os.path.exists(kospi_file):
                self.kospi_data = pd.read_excel(kospi_file)
                console.print(f"✅ KOSPI 마스터 데이터 로드 완료: {len(self.kospi_data)}개 종목")
            else:
                console.print(f"⚠️ {kospi_file} 파일을 찾을 수 없습니다.")
                self.kospi_data = pd.DataFrame()
        except Exception as e:
            console.print(f"❌ KOSPI 데이터 로드 실패: {e}")
            self.kospi_data = pd.DataFrame()
    
    def get_top_market_cap_stocks(self, count: int = 100, min_market_cap: float = 500) -> List[Dict[str, Any]]:
        """시가총액 상위 종목들을 반환합니다."""
        if self.kospi_data is None or self.kospi_data.empty:
            return []
        
        # 시가총액 기준으로 정렬하고 필터링 (우선주 제외)
        filtered_stocks = self.kospi_data[
            (self.kospi_data['시가총액'] >= min_market_cap) &
            (~self.kospi_data['한글명'].str.contains('우$', na=False))  # 우선주 제외
        ].nlargest(count, '시가총액')
        
        stocks = []
        for _, stock in filtered_stocks.iterrows():
            stocks.append({
                'symbol': stock['단축코드'],
                'name': stock['한글명'],
                'market_cap': stock['시가총액'],
                'sector': str(stock.get('지수업종대분류', ''))
            })
        
        return stocks
    
    def analyze_single_stock_integrated(self, symbol: str, name: str, days_back: int = 30) -> Dict[str, Any]:
        """단일 종목의 통합 분석을 수행합니다."""
        try:
            # TPS 제한 적용
            rate_limiter.acquire()
            
            # 투자의견 분석
            opinion_analysis = self.opinion_analyzer.analyze_single_stock(symbol, days_back=days_back)
            
            # 추정실적 분석
            estimate_analysis = self.estimate_analyzer.analyze_single_stock(symbol)
            
            # 통합 분석
            integrated_analysis = create_integrated_analysis(opinion_analysis, estimate_analysis)
            
            return {
                'symbol': symbol,
                'name': name,
                'status': 'success',
                'integrated_score': integrated_analysis.get('integrated_score', 0),
                'integrated_grade': integrated_analysis.get('integrated_grade', 'N/A'),
                'investment_recommendation': integrated_analysis.get('investment_recommendation', 'N/A'),
                'risk_assessment': integrated_analysis.get('risk_assessment', 'N/A'),
                'analysis': integrated_analysis
            }
            
        except Exception as e:
            logger.error(f"❌ {name} ({symbol}) 분석 실패: {e}")
            return {
                'symbol': symbol,
                'name': name,
                'status': 'error',
                'error': str(e),
                'integrated_score': 0,
                'integrated_grade': 'F',
                'investment_recommendation': '분석 실패',
                'risk_assessment': '높음'
            }

def analyze_single_stock_safe(symbol: str, name: str, market_cap: float, sector: str, 
                            analyzer: IntegratedParallelAnalyzer, days_back: int = 30) -> Dict[str, Any]:
    """안전한 단일 종목 분석 (병렬 처리용)"""
    try:
        return analyzer.analyze_single_stock_integrated(symbol, name, days_back)
    except Exception as e:
        return {
            'symbol': symbol,
            'name': name,
            'status': 'error',
            'error': str(e),
            'integrated_score': 0,
            'integrated_grade': 'F',
            'investment_recommendation': '분석 실패',
            'risk_assessment': '높음'
        }

# Typer CLI 앱 생성
app = typer.Typer(help="통합 분석 병렬 처리 시스템")

@app.command()
def test_parallel_integrated_analysis(
    count: int = typer.Option(20, help="분석할 종목 수 (기본값: 20개)"),
    display: int = typer.Option(10, help="표시할 결과 수 (기본값: 10개)"),
    max_workers: int = typer.Option(3, help="병렬 워커 수 (기본값: 3개, TPS 제한 고려)"),
    min_market_cap: float = typer.Option(500, help="최소 시가총액 (억원, 기본값: 500억원)"),
    min_score: float = typer.Option(50, help="최소 통합 점수 (기본값: 50점)"),
    days_back: int = typer.Option(30, help="투자의견 분석 기간 (일, 기본값: 30일)")
):
    """통합 분석 시스템의 병렬 처리 테스트"""
    analyzer = IntegratedParallelAnalyzer()
    
    console.print(f"🚀 [bold]통합 분석 병렬 처리 테스트[/bold]")
    console.print(f"📊 분석 대상: 시가총액 상위 {count}개 종목")
    console.print(f"⚡ 병렬 워커: {max_workers}개 (TPS 제한: 초당 8건)")
    console.print(f"🎯 최소 통합 점수: {min_score}점")
    console.print(f"💰 최소 시가총액: {min_market_cap:,}억원")
    console.print(f"📅 투자의견 분석 기간: {days_back}일")
    
    # 1단계: 시가총액 상위 종목 선별
    console.print(f"\n📊 [bold]1단계: 시가총액 상위 종목 선별[/bold]")
    
    if analyzer.kospi_data is None or analyzer.kospi_data.empty:
        console.print("❌ KOSPI 데이터를 로드할 수 없습니다.")
        return
    
    # 시가총액 상위 종목 가져오기
    top_stocks = analyzer.get_top_market_cap_stocks(count, min_market_cap)
    
    if not top_stocks:
        console.print("❌ 분석할 종목이 없습니다.")
        return
    
    console.print(f"✅ {len(top_stocks)}개 종목 선별 완료")
    
    # 2단계: 병렬 통합 분석 수행
    console.print(f"\n⚡ [bold]2단계: 병렬 통합 분석 수행 (TPS 제한 적용)[/bold]")
    
    analysis_results = []
    start_time = time.time()
    
    with Progress() as progress:
        task = progress.add_task("병렬 통합 분석 진행 중...", total=len(top_stocks))
        
        # ThreadPoolExecutor를 사용한 병렬 처리
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 각 종목에 대한 Future 생성
            future_to_stock = {}
            for stock in top_stocks:
                future = executor.submit(
                    analyze_single_stock_safe,
                    stock['symbol'], stock['name'], stock['market_cap'], stock['sector'],
                    analyzer, days_back
                )
                future_to_stock[future] = (stock['symbol'], stock['name'])
            
            # 완료된 작업들을 처리
            for future in as_completed(future_to_stock):
                symbol, name = future_to_stock[future]
                try:
                    result = future.result()
                    analysis_results.append(result)
                    
                    # 결과 표시
                    if result['status'] == 'error':
                        console.print(f"❌ {name} ({symbol}) 분석 실패: {result['error']}")
                    else:
                        score = result['integrated_score']
                        grade = result['integrated_grade']
                        recommendation = result['investment_recommendation']
                        
                        console.print(f"✅ {name} ({symbol}) 통합 분석 완료 - 점수: {score:.1f}점 ({grade}등급) - {recommendation}")
                    
                    progress.update(task, advance=1)
                    
                except Exception as e:
                    console.print(f"❌ {name} ({symbol}) Future 처리 실패: {e}")
                    progress.update(task, advance=1)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # 3단계: 결과 분석
    console.print(f"\n📊 [bold]3단계: 병렬 처리 결과 분석[/bold]")
    
    if not analysis_results:
        console.print("❌ 분석 결과가 없습니다.")
        return
    
    # 성공한 분석만 필터링
    successful_results = [r for r in analysis_results if r['status'] == 'success']
    error_count = len(analysis_results) - len(successful_results)
    
    console.print(f"✅ 성공한 분석: {len(successful_results)}개")
    if error_count > 0:
        console.print(f"❌ 실패한 분석: {error_count}개")
    
    console.print(f"⏱️ 총 소요 시간: {total_time:.2f}초")
    console.print(f"⚡ 평균 처리 속도: {len(top_stocks)/total_time:.2f}종목/초")
    
    # 4단계: 점수별 필터링 및 정렬
    console.print(f"\n🎯 [bold]4단계: 점수별 필터링 (최소 {min_score}점 이상)[/bold]")
    
    filtered_results = [r for r in successful_results if r['integrated_score'] >= min_score]
    filtered_results.sort(key=lambda x: x['integrated_score'], reverse=True)
    
    console.print(f"✅ {min_score}점 이상 종목: {len(filtered_results)}개")
    
    if not filtered_results:
        console.print(f"⚠️ {min_score}점 이상인 종목이 없습니다.")
        return
    
    # 5단계: 결과 표시
    console.print(f"\n🏆 [bold]5단계: 상위 {min(display, len(filtered_results))}개 종목 결과[/bold]")
    
    # 결과 테이블 생성
    table = Table(title=f"통합 분석 상위 {min(display, len(filtered_results))}개 종목")
    table.add_column("순위", style="cyan", width=4)
    table.add_column("종목코드", style="white", width=8)
    table.add_column("종목명", style="white", width=12)
    table.add_column("시가총액", style="blue", width=10)
    table.add_column("통합점수", style="green", width=10)
    table.add_column("등급", style="yellow", width=6)
    table.add_column("투자추천", style="white", width=15)
    table.add_column("리스크", style="red", width=8)
    
    for i, result in enumerate(filtered_results[:display], 1):
        # 시가총액 정보 추가 (원래 데이터에서 찾기)
        market_cap_info = ""
        for stock in top_stocks:
            if stock['symbol'] == result['symbol']:
                market_cap_info = f"{stock['market_cap']:,}억"
                break
        
        table.add_row(
            str(i),
            result['symbol'],
            result['name'][:10] + "..." if len(result['name']) > 10 else result['name'],
            market_cap_info,
            f"{result['integrated_score']:.1f}",
            result['integrated_grade'],
            result['investment_recommendation'][:12] + "..." if len(result['investment_recommendation']) > 12 else result['investment_recommendation'],
            result['risk_assessment']
        )
    
    console.print(table)
    
    # 6단계: 통계 정보
    console.print(f"\n📈 [bold]6단계: 통계 정보[/bold]")
    
    if filtered_results:
        scores = [r['integrated_score'] for r in filtered_results]
        avg_score = np.mean(scores)
        max_score = max(scores)
        min_score = min(scores)
        
        # 등급별 분포
        grade_distribution = {}
        for result in filtered_results:
            grade = result['integrated_grade']
            grade_distribution[grade] = grade_distribution.get(grade, 0) + 1
        
        # 추천별 분포
        recommendation_distribution = {}
        for result in filtered_results:
            recommendation = result['investment_recommendation']
            recommendation_distribution[recommendation] = recommendation_distribution.get(recommendation, 0) + 1
        
        console.print(f"📊 통합 점수 통계:")
        console.print(f"  • 평균 점수: {avg_score:.1f}점")
        console.print(f"  • 최고 점수: {max_score:.1f}점")
        console.print(f"  • 최저 점수: {min_score:.1f}점")
        
        console.print(f"\n🏆 등급별 분포:")
        for grade, count in sorted(grade_distribution.items()):
            console.print(f"  • {grade}등급: {count}개")
        
        console.print(f"\n💡 투자 추천 분포:")
        for recommendation, count in recommendation_distribution.items():
            console.print(f"  • {recommendation}: {count}개")
    
    # 7단계: 상위 3개 종목 상세 분석
    if len(filtered_results) >= 3:
        console.print(f"\n🔍 [bold]7단계: 상위 3개 종목 상세 분석[/bold]")
        
        for i, result in enumerate(filtered_results[:3], 1):
            console.print(f"\n🏅 [bold cyan]{i}위: {result['name']} ({result['symbol']})[/bold cyan]")
            console.print(f"통합 점수: {result['integrated_score']:.1f}점 ({result['integrated_grade']}등급)")
            console.print(f"투자 추천: {result['investment_recommendation']}")
            console.print(f"리스크 평가: {result['risk_assessment']}")
            
            # 상세 분석 정보 표시
            analysis = result.get('analysis', {})
            if analysis:
                # 투자의견 정보
                if analysis.get('total_opinions', 0) > 0:
                    console.print(f"투자의견: 총 {analysis['total_opinions']}건 (매수: {analysis.get('buy_opinions', 0)}건)")
                    console.print(f"컨센서스: {analysis.get('consensus_score', 0):.2f}")
                    console.print(f"평균 목표가: {analysis.get('avg_target_price', 0):,.0f}원")
                
                # 추정실적 정보
                if analysis.get('current_price', 0) > 0:
                    console.print(f"현재가: {analysis['current_price']:,}원")
                    console.print(f"매출액: {analysis.get('latest_revenue', 0):,.0f}원")
                    console.print(f"PER: {analysis.get('latest_per', 0):.1f}배")
                    console.print(f"ROE: {analysis.get('latest_roe', 0):.1f}%")

@app.command()
def parallel_top_picks(
    count: int = typer.Option(50, help="스크리닝할 종목 수 (기본값: 50개)"),
    max_workers: int = typer.Option(3, help="병렬 워커 수 (기본값: 3개)"),
    min_score: float = typer.Option(60, help="최소 통합 점수 (기본값: 60점)"),
    max_picks: int = typer.Option(10, help="최대 추천 종목 수 (기본값: 10개)"),
    min_market_cap: float = typer.Option(1000, help="최소 시가총액 (억원, 기본값: 1000억원)"),
    export_csv: bool = typer.Option(False, help="CSV 파일로 내보내기")
):
    """병렬 처리를 통한 최고 투자 후보 검색"""
    analyzer = IntegratedParallelAnalyzer()
    
    console.print(f"🚀 [bold]병렬 처리 투자 후보 검색[/bold]")
    console.print(f"📊 스크리닝 대상: 시가총액 상위 {count}개 종목")
    console.print(f"⚡ 병렬 워커: {max_workers}개")
    console.print(f"🎯 최소 통합 점수: {min_score}점")
    console.print(f"📈 최대 추천 종목: {max_picks}개")
    console.print(f"💰 최소 시가총액: {min_market_cap:,}억원")
    
    # 시가총액 상위 종목 가져오기
    top_stocks = analyzer.get_top_market_cap_stocks(count, min_market_cap)
    
    if not top_stocks:
        console.print("❌ 분석할 종목이 없습니다.")
        return
    
    # 병렬 분석 수행
    analysis_results = []
    start_time = time.time()
    
    with Progress() as progress:
        task = progress.add_task("병렬 투자 후보 검색 중...", total=len(top_stocks))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_stock = {}
            for stock in top_stocks:
                future = executor.submit(
                    analyze_single_stock_safe,
                    stock['symbol'], stock['name'], stock['market_cap'], stock['sector'],
                    analyzer, 30
                )
                future_to_stock[future] = (stock['symbol'], stock['name'])
            
            for future in as_completed(future_to_stock):
                symbol, name = future_to_stock[future]
                try:
                    result = future.result()
                    if result['status'] == 'success' and result['integrated_score'] >= min_score:
                        analysis_results.append(result)
                    progress.update(task, advance=1)
                except Exception as e:
                    progress.update(task, advance=1)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # 점수순으로 정렬
    analysis_results.sort(key=lambda x: x['integrated_score'], reverse=True)
    
    # 최대 개수만큼 선택
    top_picks = analysis_results[:max_picks]
    
    console.print(f"\n✅ 스크리닝 완료: {len(top_picks)}/{len(top_stocks)}개 종목이 기준을 충족")
    console.print(f"⏱️ 소요 시간: {total_time:.2f}초")
    
    if not top_picks:
        console.print(f"⚠️ {min_score}점 이상인 종목이 없습니다.")
        return
    
    # 결과 표시
    table = Table(title=f"최고의 투자 후보 {len(top_picks)}개")
    table.add_column("순위", style="cyan", width=4)
    table.add_column("종목코드", style="white", width=8)
    table.add_column("종목명", style="white", width=12)
    table.add_column("통합점수", style="green", width=10)
    table.add_column("등급", style="yellow", width=6)
    table.add_column("투자추천", style="white", width=15)
    table.add_column("리스크", style="red", width=8)
    
    for i, pick in enumerate(top_picks, 1):
        table.add_row(
            str(i),
            pick['symbol'],
            pick['name'][:10] + "..." if len(pick['name']) > 10 else pick['name'],
            f"{pick['integrated_score']:.1f}",
            pick['integrated_grade'],
            pick['investment_recommendation'][:12] + "..." if len(pick['investment_recommendation']) > 12 else pick['investment_recommendation'],
            pick['risk_assessment']
        )
    
    console.print(table)
    
    # CSV 내보내기
    if export_csv:
        try:
            export_data = []
            for pick in top_picks:
                analysis = pick.get('analysis', {})
                export_data.append({
                    'rank': top_picks.index(pick) + 1,
                    'symbol': pick['symbol'],
                    'name': pick['name'],
                    'integrated_score': pick['integrated_score'],
                    'integrated_grade': pick['integrated_grade'],
                    'investment_recommendation': pick['investment_recommendation'],
                    'risk_assessment': pick['risk_assessment'],
                    'total_opinions': analysis.get('total_opinions', 0),
                    'consensus_score': analysis.get('consensus_score', 0),
                    'avg_target_price': analysis.get('avg_target_price', 0),
                    'current_price': analysis.get('current_price', 0),
                    'latest_per': analysis.get('latest_per', 0),
                    'latest_roe': analysis.get('latest_roe', 0),
                    'financial_health_score': analysis.get('financial_health_score', 0),
                    'valuation_score': analysis.get('valuation_score', 0)
                })
            
            df = pd.DataFrame(export_data)
            filename = f"parallel_top_picks_{int(time.time())}.csv"
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            console.print(f"\n💾 결과가 {filename}에 저장되었습니다.")
            
        except Exception as e:
            console.print(f"[red]❌ CSV 내보내기 실패: {e}[/red]")

if __name__ == "__main__":
    app()
