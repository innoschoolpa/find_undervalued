# enhanced_integrated_analyzer.py
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
from financial_ratio_analyzer import FinancialRatioAnalyzer
from profit_ratio_analyzer import ProfitRatioAnalyzer
from stability_ratio_analyzer import StabilityRatioAnalyzer
from growth_ratio_analyzer import GrowthRatioAnalyzer
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

class EnhancedIntegratedAnalyzer:
    """재무비율 분석이 통합된 향상된 분석 클래스"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.opinion_analyzer = InvestmentOpinionAnalyzer()
        self.estimate_analyzer = EstimatePerformanceAnalyzer()
        self.provider = KISDataProvider()
        self.financial_ratio_analyzer = FinancialRatioAnalyzer(self.provider)
        self.profit_ratio_analyzer = ProfitRatioAnalyzer(self.provider)
        self.stability_ratio_analyzer = StabilityRatioAnalyzer(self.provider)
        self.growth_ratio_analyzer = GrowthRatioAnalyzer(self.provider)
        self.kospi_data = None
        
        # 설정 로드
        self.config = self._load_config(config_file)
        self._load_kospi_data()
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """설정 파일을 로드합니다."""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 향상된 통합 분석 설정이 없으면 기본값 사용
            enhanced_config = config.get('enhanced_integrated_analysis', {})
            
            # 기본 가중치 설정
            default_weights = {
                'opinion_analysis': 25,
                'estimate_analysis': 30,
                'financial_ratios': 30,
                'growth_analysis': 10,
                'scale_analysis': 5
            }
            
            # 기본 재무비율 가중치 설정
            default_financial_weights = {
                'roe_score': 8,
                'roa_score': 5,
                'debt_ratio_score': 7,
                'net_profit_margin_score': 5,
                'current_ratio_score': 3,
                'growth_score': 2
            }
            
            # 기본 추정실적 가중치 설정
            default_estimate_weights = {
                'financial_health': 15,
                'valuation': 15
            }
            
            # 기본 등급 기준 설정
            default_grade_thresholds = {
                'A_plus': 85,
                'A': 80,
                'B_plus': 75,
                'B': 70,
                'C_plus': 65,
                'C': 60,
                'D': 50,
                'F': 0
            }
            
            # 설정 병합
            self.weights = enhanced_config.get('weights', default_weights)
            self.financial_ratio_weights = enhanced_config.get('financial_ratio_weights', default_financial_weights)
            self.estimate_analysis_weights = enhanced_config.get('estimate_analysis_weights', default_estimate_weights)
            self.grade_thresholds = enhanced_config.get('grade_thresholds', default_grade_thresholds)
            self.growth_score_thresholds = enhanced_config.get('growth_score_thresholds', {
                'excellent': 20,
                'good': 10,
                'average': 0,
                'poor': -10,
                'very_poor': -100
            })
            self.scale_score_thresholds = enhanced_config.get('scale_score_thresholds', {
                'mega_cap': 100000,
                'large_cap': 50000,
                'mid_large_cap': 10000,
                'mid_cap': 5000,
                'small_cap': 1000,
                'micro_cap': 0
            })
            
            return enhanced_config
            
        except Exception as e:
            logger.warning(f"설정 파일 로드 실패, 기본값 사용: {e}")
            # 기본값으로 설정
            self.weights = {
                'opinion_analysis': 25,
                'estimate_analysis': 30,
                'financial_ratios': 30,
                'growth_analysis': 10,
                'scale_analysis': 5
            }
            self.financial_ratio_weights = {
                'roe_score': 8,
                'roa_score': 5,
                'debt_ratio_score': 7,
                'net_profit_margin_score': 5,
                'current_ratio_score': 3,
                'growth_score': 2
            }
            self.estimate_analysis_weights = {
                'financial_health': 15,
                'valuation': 15
            }
            self.grade_thresholds = {
                'A_plus': 85,
                'A': 80,
                'B_plus': 75,
                'B': 70,
                'C_plus': 65,
                'C': 60,
                'D': 50,
                'F': 0
            }
            self.growth_score_thresholds = {
                'excellent': 20,
                'good': 10,
                'average': 0,
                'poor': -10,
                'very_poor': -100
            }
            self.scale_score_thresholds = {
                'mega_cap': 100000,
                'large_cap': 50000,
                'mid_large_cap': 10000,
                'mid_cap': 5000,
                'small_cap': 1000,
                'micro_cap': 0
            }
            return {}
    
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
    
    def get_financial_ratios_data(self, symbol: str) -> Dict[str, Any]:
        """종목의 재무비율 데이터를 수집합니다."""
        financial_data = {}
        
        try:
            # 1. 재무비율 분석
            rate_limiter.acquire()
            financial_ratios = self.financial_ratio_analyzer.get_financial_ratios(symbol)
            if financial_ratios and len(financial_ratios) > 0:
                latest_ratios = financial_ratios[0]
                financial_data.update({
                    'roe': latest_ratios.get('roe', 0),
                    'roa': latest_ratios.get('roa', 0),
                    'debt_ratio': latest_ratios.get('debt_ratio', 0),
                    'equity_ratio': latest_ratios.get('equity_ratio', 0),
                    'revenue_growth_rate': latest_ratios.get('revenue_growth_rate', 0),
                    'operating_income_growth_rate': latest_ratios.get('operating_income_growth_rate', 0),
                    'net_income_growth_rate': latest_ratios.get('net_income_growth_rate', 0)
                })
        except Exception as e:
            logger.warning(f"재무비율 분석 실패 ({symbol}): {e}")
        
        try:
            # 2. 수익성비율 분석
            rate_limiter.acquire()
            profit_ratios = self.profit_ratio_analyzer.get_profit_ratios(symbol)
            if profit_ratios and len(profit_ratios) > 0:
                latest_profit = profit_ratios[0]
                financial_data.update({
                    'net_profit_margin': latest_profit.get('net_profit_margin', 0),
                    'gross_profit_margin': latest_profit.get('gross_profit_margin', 0),
                    'profitability_grade': latest_profit.get('profitability_grade', '평가불가')
                })
        except Exception as e:
            logger.warning(f"수익성비율 분석 실패 ({symbol}): {e}")
        
        try:
            # 3. 안정성비율 분석
            rate_limiter.acquire()
            stability_ratios = self.stability_ratio_analyzer.get_stability_ratios(symbol)
            if stability_ratios and len(stability_ratios) > 0:
                latest_stability = stability_ratios[0]
                financial_data.update({
                    'current_ratio': latest_stability.get('current_ratio', 0),
                    'quick_ratio': latest_stability.get('quick_ratio', 0),
                    'borrowing_dependency': latest_stability.get('borrowing_dependency', 0),
                    'stability_grade': latest_stability.get('stability_grade', '평가불가')
                })
        except Exception as e:
            logger.warning(f"안정성비율 분석 실패 ({symbol}): {e}")
        
        try:
            # 4. 성장성비율 분석
            rate_limiter.acquire()
            growth_ratios = self.growth_ratio_analyzer.get_growth_ratios(symbol)
            if growth_ratios and len(growth_ratios) > 0:
                latest_growth = growth_ratios[0]
                financial_data.update({
                    'revenue_growth_rate_annual': latest_growth.get('revenue_growth_rate', 0),
                    'operating_income_growth_rate_annual': latest_growth.get('operating_income_growth_rate', 0),
                    'equity_growth_rate': latest_growth.get('equity_growth_rate', 0),
                    'total_asset_growth_rate': latest_growth.get('total_asset_growth_rate', 0),
                    'growth_grade': latest_growth.get('growth_grade', '평가불가')
                })
        except Exception as e:
            logger.warning(f"성장성비율 분석 실패 ({symbol}): {e}")
        
        return financial_data
    
    def calculate_enhanced_integrated_score(self, opinion_analysis: Dict[str, Any], 
                                          estimate_analysis: Dict[str, Any], 
                                          financial_data: Dict[str, Any],
                                          market_cap: float) -> Dict[str, Any]:
        """향상된 통합 점수를 계산합니다."""
        score = 0
        score_breakdown = {}
        
        # 1. 투자의견 점수 (설정 가능)
        opinion_weight = self.weights['opinion_analysis']
        if 'consensus_score' in opinion_analysis:
            consensus_score = opinion_analysis['consensus_score']
            # -1~1 범위를 0~설정된 가중치로 변환
            opinion_score = (consensus_score + 1) * (opinion_weight / 2)  # -1~1 -> 0~설정가중치
            score += max(0, min(opinion_weight, opinion_score))
            score_breakdown['투자의견'] = max(0, min(opinion_weight, opinion_score))
        
        # 2. 추정실적 점수 (설정 가능)
        estimate_weight = self.weights['estimate_analysis']
        if 'financial_health_score' in estimate_analysis and 'valuation_score' in estimate_analysis:
            financial_health_weight = self.estimate_analysis_weights['financial_health']
            valuation_weight = self.estimate_analysis_weights['valuation']
            
            # 추정실적 점수를 설정된 가중치에 맞게 스케일링
            scale_factor = estimate_weight / 30  # 기본 30점에서 설정 가중치로 스케일링
            financial_score = estimate_analysis['financial_health_score'] * scale_factor * (financial_health_weight / 15)
            valuation_score = estimate_analysis['valuation_score'] * scale_factor * (valuation_weight / 15)
            
            score += financial_score + valuation_score
            score_breakdown['재무건전성'] = financial_score
            score_breakdown['밸류에이션'] = valuation_score
        
        # 3. 재무비율 점수 (설정 가능)
        financial_ratio_weight = self.weights['financial_ratios']
        financial_ratio_score = self._calculate_financial_ratio_score(financial_data)
        # 재무비율 점수를 설정된 가중치에 맞게 스케일링
        scale_factor = financial_ratio_weight / 30  # 기본 30점에서 설정 가중치로 스케일링
        financial_ratio_score_scaled = financial_ratio_score * scale_factor
        score += financial_ratio_score_scaled
        score_breakdown['재무비율'] = financial_ratio_score_scaled
        
        # 4. 성장성 점수 (설정 가능)
        growth_weight = self.weights['growth_analysis']
        if 'latest_revenue_growth' in estimate_analysis:
            revenue_growth = estimate_analysis['latest_revenue_growth']
            growth_score = self._calculate_growth_score(revenue_growth, growth_weight)
            score += growth_score
            score_breakdown['성장성'] = growth_score
        
        # 5. 규모 점수 (설정 가능)
        scale_weight = self.weights['scale_analysis']
        scale_score = self._calculate_scale_score(market_cap, scale_weight)
        score += scale_score
        score_breakdown['규모'] = scale_score
        
        return {
            'total_score': min(100, max(0, score)),
            'score_breakdown': score_breakdown
        }
    
    def _calculate_financial_ratio_score(self, financial_data: Dict[str, Any]) -> float:
        """재무비율 점수를 계산합니다."""
        score = 0
        
        # ROE 점수 (설정 가능)
        roe_weight = self.financial_ratio_weights['roe_score']
        roe = financial_data.get('roe', 0)
        if roe >= 20:
            score += roe_weight
        elif roe >= 15:
            score += roe_weight * 0.75
        elif roe >= 10:
            score += roe_weight * 0.5
        elif roe >= 5:
            score += roe_weight * 0.25
        
        # ROA 점수 (설정 가능)
        roa_weight = self.financial_ratio_weights['roa_score']
        roa = financial_data.get('roa', 0)
        if roa >= 10:
            score += roa_weight
        elif roa >= 7:
            score += roa_weight * 0.8
        elif roa >= 5:
            score += roa_weight * 0.6
        elif roa >= 3:
            score += roa_weight * 0.4
        
        # 부채비율 점수 (설정 가능) - 낮을수록 좋음
        debt_ratio_weight = self.financial_ratio_weights['debt_ratio_score']
        debt_ratio = financial_data.get('debt_ratio', 999)
        if debt_ratio <= 30:
            score += debt_ratio_weight
        elif debt_ratio <= 50:
            score += debt_ratio_weight * 0.71
        elif debt_ratio <= 70:
            score += debt_ratio_weight * 0.43
        elif debt_ratio <= 100:
            score += debt_ratio_weight * 0.14
        
        # 순이익률 점수 (설정 가능)
        net_profit_margin_weight = self.financial_ratio_weights['net_profit_margin_score']
        net_profit_margin = financial_data.get('net_profit_margin', 0)
        if net_profit_margin >= 15:
            score += net_profit_margin_weight
        elif net_profit_margin >= 10:
            score += net_profit_margin_weight * 0.8
        elif net_profit_margin >= 5:
            score += net_profit_margin_weight * 0.6
        elif net_profit_margin >= 2:
            score += net_profit_margin_weight * 0.4
        
        # 유동비율 점수 (설정 가능)
        current_ratio_weight = self.financial_ratio_weights['current_ratio_score']
        current_ratio = financial_data.get('current_ratio', 0)
        if current_ratio >= 2:
            score += current_ratio_weight
        elif current_ratio >= 1.5:
            score += current_ratio_weight * 0.67
        elif current_ratio >= 1:
            score += current_ratio_weight * 0.33
        
        # 성장성 점수 (설정 가능)
        growth_weight = self.financial_ratio_weights['growth_score']
        revenue_growth = financial_data.get('revenue_growth_rate_annual', 0)
        if revenue_growth >= 20:
            score += growth_weight
        elif revenue_growth >= 10:
            score += growth_weight * 0.5
        
        return min(30, score)  # 최대 30점
    
    def _calculate_scale_score(self, market_cap: float, max_score: float = None) -> float:
        """규모 점수를 계산합니다."""
        if max_score is None:
            max_score = self.weights['scale_analysis']
        
        thresholds = self.scale_score_thresholds
        
        if market_cap >= thresholds['mega_cap']:  # 메가캡
            return max_score
        elif market_cap >= thresholds['large_cap']:  # 대형주
            return max_score * 0.8
        elif market_cap >= thresholds['mid_large_cap']:  # 중대형주
            return max_score * 0.6
        elif market_cap >= thresholds['mid_cap']:  # 중형주
            return max_score * 0.4
        elif market_cap >= thresholds['small_cap']:  # 소형주
            return max_score * 0.2
        else:
            return 0
    
    def _calculate_growth_score(self, revenue_growth: float, max_score: float = None) -> float:
        """성장성 점수를 계산합니다."""
        if max_score is None:
            max_score = self.weights['growth_analysis']
        
        thresholds = self.growth_score_thresholds
        
        if revenue_growth >= thresholds['excellent']:  # 우수
            return max_score
        elif revenue_growth >= thresholds['good']:  # 양호
            return max_score * 0.8
        elif revenue_growth >= thresholds['average']:  # 보통
            return max_score * 0.5
        elif revenue_growth >= thresholds['poor']:  # 부진
            return max_score * 0.3
        else:  # 매우 부진
            return 0
    
    def analyze_single_stock_enhanced(self, symbol: str, name: str, days_back: int = 30) -> Dict[str, Any]:
        """단일 종목의 향상된 통합 분석을 수행합니다."""
        try:
            # 투자의견 분석
            opinion_analysis = self.opinion_analyzer.analyze_single_stock(symbol, days_back=days_back)
            
            # 추정실적 분석
            estimate_analysis = self.estimate_analyzer.analyze_single_stock(symbol)
            
            # 재무비율 데이터 수집
            financial_data = self.get_financial_ratios_data(symbol)
            
            # 시가총액 정보 및 현재가 정보 (KOSPI 데이터에서)
            market_cap = 0
            current_price = 0
            for stock in self.kospi_data.itertuples():
                if stock.단축코드 == symbol:
                    market_cap = stock.시가총액
                    current_price = stock.get('현재가', 0) if hasattr(stock, '현재가') else 0
                    break
            
            # 항상 KIS API에서 현재가 조회 (더 정확한 실시간 데이터)
            try:
                rate_limiter.acquire()
                price_info = self.provider.get_stock_price_info(symbol)
                if price_info and 'current_price' in price_info and price_info['current_price'] > 0:
                    current_price = float(price_info['current_price'])
                else:
                    logger.warning(f"현재가 데이터 없음 ({symbol})")
                    current_price = 0
            except Exception as e:
                logger.warning(f"현재가 조회 실패 ({symbol}): {e}")
                current_price = 0
            
            # 향상된 통합 점수 계산
            enhanced_score = self.calculate_enhanced_integrated_score(
                opinion_analysis, estimate_analysis, financial_data, market_cap
            )
            
            # 기존 통합 분석 결과
            integrated_analysis = create_integrated_analysis(opinion_analysis, estimate_analysis)
            
            # 향상된 분석 결과 생성
            enhanced_analysis = {
                'symbol': symbol,
                'name': name,
                'market_cap': market_cap,
                'current_price': current_price,
                'status': 'success',
                'enhanced_score': enhanced_score['total_score'],
                'score_breakdown': enhanced_score['score_breakdown'],
                'enhanced_grade': self._get_enhanced_grade(enhanced_score['total_score']),
                'financial_data': financial_data,
                'opinion_analysis': opinion_analysis,
                'estimate_analysis': estimate_analysis,
                'integrated_analysis': integrated_analysis
            }
            
            return enhanced_analysis
            
        except Exception as e:
            logger.error(f"❌ {name} ({symbol}) 향상된 분석 실패: {e}")
            return {
                'symbol': symbol,
                'name': name,
                'status': 'error',
                'error': str(e),
                'enhanced_score': 0,
                'enhanced_grade': 'F',
                'financial_data': {},
                'opinion_analysis': {},
                'estimate_analysis': {}
            }
    
    def _get_enhanced_grade(self, score: float) -> str:
        """향상된 점수를 등급으로 변환합니다."""
        thresholds = self.grade_thresholds
        
        if score >= thresholds['A_plus']: return 'A+'
        elif score >= thresholds['A']: return 'A'
        elif score >= thresholds['B_plus']: return 'B+'
        elif score >= thresholds['B']: return 'B'
        elif score >= thresholds['C_plus']: return 'C+'
        elif score >= thresholds['C']: return 'C'
        elif score >= thresholds['D']: return 'D'
        else: return 'F'
    
    def _apply_investment_philosophy_preset(self, preset_name: str):
        """투자 철학 프리셋을 적용합니다."""
        try:
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            enhanced_config = config.get('enhanced_integrated_analysis', {})
            presets = enhanced_config.get('investment_philosophy_presets', {})
            
            if preset_name in presets:
                preset_weights = presets[preset_name]
                self.weights.update(preset_weights)
                console.print(f"✅ 투자 철학 프리셋 '{preset_name}' 적용 완료")
                console.print(f"   📊 새로운 가중치: {self.weights}")
            else:
                console.print(f"⚠️ 투자 철학 프리셋 '{preset_name}'을 찾을 수 없습니다. 기본값 사용.")
                
        except Exception as e:
            console.print(f"❌ 투자 철학 프리셋 적용 실패: {e}")

def analyze_single_stock_safe_enhanced(symbol: str, name: str, market_cap: float, sector: str, 
                                     analyzer: EnhancedIntegratedAnalyzer, days_back: int = 30) -> Dict[str, Any]:
    """안전한 단일 종목 향상된 분석 (병렬 처리용)"""
    try:
        return analyzer.analyze_single_stock_enhanced(symbol, name, days_back)
    except Exception as e:
        return {
            'symbol': symbol,
            'name': name,
            'status': 'error',
            'error': str(e),
            'enhanced_score': 0,
            'enhanced_grade': 'F'
        }

# Typer CLI 앱 생성
app = typer.Typer(help="향상된 통합 분석 병렬 처리 시스템")

@app.command()
def test_enhanced_parallel_analysis(
    count: int = typer.Option(15, help="분석할 종목 수 (기본값: 15개)"),
    display: int = typer.Option(10, help="표시할 결과 수 (기본값: 10개)"),
    max_workers: int = typer.Option(2, help="병렬 워커 수 (기본값: 2개, 재무비율 분석으로 인한 높은 API 사용량 고려)"),
    min_market_cap: float = typer.Option(500, help="최소 시가총액 (억원, 기본값: 500억원)"),
    min_score: float = typer.Option(50, help="최소 향상된 통합 점수 (기본값: 50점)"),
    days_back: int = typer.Option(30, help="투자의견 분석 기간 (일, 기본값: 30일)"),
    investment_philosophy: str = typer.Option("balanced", help="투자 철학 프리셋 (balanced, value_focused, growth_focused, consensus_focused, stability_focused)")
):
    """향상된 통합 분석 시스템의 병렬 처리 테스트 (재무비율 분석 포함)"""
    analyzer = EnhancedIntegratedAnalyzer()
    
    # 투자 철학 프리셋 적용
    if investment_philosophy != "balanced":
        analyzer._apply_investment_philosophy_preset(investment_philosophy)
    
    console.print(f"🚀 [bold]향상된 통합 분석 병렬 처리 테스트[/bold]")
    console.print(f"📊 분석 대상: 시가총액 상위 {count}개 종목")
    console.print(f"⚡ 병렬 워커: {max_workers}개 (재무비율 분석으로 인한 높은 API 사용량)")
    console.print(f"🎯 최소 향상된 통합 점수: {min_score}점")
    console.print(f"💰 최소 시가총액: {min_market_cap:,}억원")
    console.print(f"📅 투자의견 분석 기간: {days_back}일")
    console.print(f"🎯 투자 철학: {investment_philosophy}")
    console.print(f"📈 분석 범위: 투자의견({analyzer.weights['opinion_analysis']}%) + 추정실적({analyzer.weights['estimate_analysis']}%) + 재무비율({analyzer.weights['financial_ratios']}%) + 성장성({analyzer.weights['growth_analysis']}%) + 규모({analyzer.weights['scale_analysis']}%)")
    
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
    
    # 2단계: 병렬 향상된 통합 분석 수행
    console.print(f"\n⚡ [bold]2단계: 병렬 향상된 통합 분석 수행 (재무비율 분석 포함)[/bold]")
    
    analysis_results = []
    start_time = time.time()
    
    with Progress() as progress:
        task = progress.add_task("병렬 향상된 통합 분석 진행 중...", total=len(top_stocks))
        
        # ThreadPoolExecutor를 사용한 병렬 처리
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 각 종목에 대한 Future 생성
            future_to_stock = {}
            for stock in top_stocks:
                future = executor.submit(
                    analyze_single_stock_safe_enhanced,
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
                        score = result['enhanced_score']
                        grade = result['enhanced_grade']
                        
                        console.print(f"✅ {name} ({symbol}) 향상된 분석 완료 - 점수: {score:.1f}점 ({grade}등급)")
                        
                        # 점수 구성 표시
                        breakdown = result.get('score_breakdown', {})
                        if breakdown:
                            breakdown_str = ", ".join([f"{k}: {v:.1f}" for k, v in breakdown.items()])
                            console.print(f"   📊 점수 구성: {breakdown_str}")
                    
                    progress.update(task, advance=1)
                    
                except Exception as e:
                    console.print(f"❌ {name} ({symbol}) Future 처리 실패: {e}")
                    progress.update(task, advance=1)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # 3단계: 결과 분석
    console.print(f"\n📊 [bold]3단계: 향상된 병렬 처리 결과 분석[/bold]")
    
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
    
    filtered_results = [r for r in successful_results if r['enhanced_score'] >= min_score]
    filtered_results.sort(key=lambda x: x['enhanced_score'], reverse=True)
    
    console.print(f"✅ {min_score}점 이상 종목: {len(filtered_results)}개")
    
    if not filtered_results:
        console.print(f"⚠️ {min_score}점 이상인 종목이 없습니다.")
        return
    
    # 5단계: 결과 표시
    console.print(f"\n🏆 [bold]5단계: 향상된 분석 상위 {min(display, len(filtered_results))}개 종목 결과[/bold]")
    
    # 결과 테이블 생성
    table = Table(title=f"향상된 통합 분석 상위 {min(display, len(filtered_results))}개 종목")
    table.add_column("순위", style="cyan", width=4)
    table.add_column("종목코드", style="white", width=8)
    table.add_column("종목명", style="white", width=12)
    table.add_column("현재가", style="bold green", width=10)
    table.add_column("시가총액", style="blue", width=10)
    table.add_column("향상점수", style="green", width=10)
    table.add_column("등급", style="yellow", width=6)
    table.add_column("ROE", style="magenta", width=8)
    table.add_column("부채비율", style="red", width=10)
    table.add_column("순이익률", style="blue", width=10)
    
    for i, result in enumerate(filtered_results[:display], 1):
        financial_data = result.get('financial_data', {})
        current_price = result.get('current_price', 0)
        
        
        table.add_row(
            str(i),
            result['symbol'],
            result['name'][:10] + "..." if len(result['name']) > 10 else result['name'],
            f"{current_price:,.0f}원" if current_price and current_price > 0 else "N/A",
            f"{result['market_cap']:,}억",
            f"{result['enhanced_score']:.1f}",
            result['enhanced_grade'],
            f"{financial_data.get('roe', 0):.1f}%" if financial_data.get('roe', 0) != 0 else "N/A",
            f"{financial_data.get('debt_ratio', 0):.1f}%" if financial_data.get('debt_ratio', 0) != 0 else "N/A",
            f"{financial_data.get('net_profit_margin', 0):.1f}%" if financial_data.get('net_profit_margin', 0) != 0 else "N/A"
        )
    
    console.print(table)
    
    # 6단계: 상세 분석 표시
    console.print(f"\n📋 [bold]6단계: 상위 3개 종목 상세 분석[/bold]")
    
    for i, result in enumerate(filtered_results[:3], 1):
        current_price = result.get('current_price', 0)
        console.print(f"\n🏅 [bold cyan]{i}위: {result['name']} ({result['symbol']})[/bold cyan]")
        console.print(f"현재가: {current_price:,.0f}원" if current_price > 0 else "현재가: N/A")
        console.print(f"시가총액: {result['market_cap']:,}억원")
        console.print(f"향상된 통합 점수: {result['enhanced_score']:.1f}점 ({result['enhanced_grade']}등급)")
        
        # 점수 구성 상세
        breakdown = result.get('score_breakdown', {})
        if breakdown:
            console.print("📊 점수 구성:")
            for category, score in breakdown.items():
                console.print(f"  • {category}: {score:.1f}점")
        
        # 재무비율 상세
        financial_data = result.get('financial_data', {})
        if financial_data:
            console.print("💰 주요 재무비율:")
            console.print(f"  • ROE: {financial_data.get('roe', 0):.1f}%")
            console.print(f"  • ROA: {financial_data.get('roa', 0):.1f}%")
            console.print(f"  • 부채비율: {financial_data.get('debt_ratio', 0):.1f}%")
            console.print(f"  • 순이익률: {financial_data.get('net_profit_margin', 0):.1f}%")
            console.print(f"  • 유동비율: {financial_data.get('current_ratio', 0):.2f}")
            console.print(f"  • 매출 성장률: {financial_data.get('revenue_growth_rate_annual', 0):.1f}%")

@app.command()
def enhanced_top_picks(
    count: int = typer.Option(20, help="스크리닝할 종목 수 (기본값: 20개)"),
    max_workers: int = typer.Option(2, help="병렬 워커 수 (기본값: 2개)"),
    min_score: float = typer.Option(60, help="최소 향상된 통합 점수 (기본값: 60점)"),
    max_picks: int = typer.Option(5, help="최대 추천 종목 수 (기본값: 5개)"),
    min_market_cap: float = typer.Option(1000, help="최소 시가총액 (억원, 기본값: 1000억원)"),
    export_csv: bool = typer.Option(False, help="CSV 파일로 내보내기"),
    investment_philosophy: str = typer.Option("balanced", help="투자 철학 프리셋 (balanced, value_focused, growth_focused, consensus_focused, stability_focused)")
):
    """향상된 통합 분석을 통한 최고 투자 후보 검색 (재무비율 분석 포함)"""
    analyzer = EnhancedIntegratedAnalyzer()
    
    # 투자 철학 프리셋 적용
    if investment_philosophy != "balanced":
        analyzer._apply_investment_philosophy_preset(investment_philosophy)
    
    console.print(f"🚀 [bold]향상된 통합 분석 투자 후보 검색[/bold]")
    console.print(f"📊 스크리닝 대상: 시가총액 상위 {count}개 종목")
    console.print(f"⚡ 병렬 워커: {max_workers}개")
    console.print(f"🎯 최소 향상된 통합 점수: {min_score}점")
    console.print(f"📈 최대 추천 종목: {max_picks}개")
    console.print(f"💰 최소 시가총액: {min_market_cap:,}억원")
    console.print(f"🎯 투자 철학: {investment_philosophy}")
    console.print(f"📈 분석 범위: 투자의견({analyzer.weights['opinion_analysis']}%) + 추정실적({analyzer.weights['estimate_analysis']}%) + 재무비율({analyzer.weights['financial_ratios']}%) + 성장성({analyzer.weights['growth_analysis']}%) + 규모({analyzer.weights['scale_analysis']}%)")
    
    # 시가총액 상위 종목 가져오기
    top_stocks = analyzer.get_top_market_cap_stocks(count, min_market_cap)
    
    if not top_stocks:
        console.print("❌ 분석할 종목이 없습니다.")
        return
    
    # 병렬 분석 수행
    analysis_results = []
    start_time = time.time()
    
    with Progress() as progress:
        task = progress.add_task("병렬 향상된 투자 후보 검색 중...", total=len(top_stocks))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_stock = {}
            for stock in top_stocks:
                future = executor.submit(
                    analyze_single_stock_safe_enhanced,
                    stock['symbol'], stock['name'], stock['market_cap'], stock['sector'],
                    analyzer, 30
                )
                future_to_stock[future] = (stock['symbol'], stock['name'])
            
            for future in as_completed(future_to_stock):
                symbol, name = future_to_stock[future]
                try:
                    result = future.result()
                    if result['status'] == 'success' and result['enhanced_score'] >= min_score:
                        analysis_results.append(result)
                    progress.update(task, advance=1)
                except Exception as e:
                    progress.update(task, advance=1)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # 점수순으로 정렬
    analysis_results.sort(key=lambda x: x['enhanced_score'], reverse=True)
    
    # 최대 개수만큼 선택
    top_picks = analysis_results[:max_picks]
    
    console.print(f"\n✅ 향상된 스크리닝 완료: {len(top_picks)}/{len(top_stocks)}개 종목이 기준을 충족")
    console.print(f"⏱️ 소요 시간: {total_time:.2f}초")
    
    if not top_picks:
        console.print(f"⚠️ {min_score}점 이상인 종목이 없습니다.")
        return
    
    # 결과 표시
    table = Table(title=f"향상된 최고의 투자 후보 {len(top_picks)}개")
    table.add_column("순위", style="cyan", width=4)
    table.add_column("종목코드", style="white", width=8)
    table.add_column("종목명", style="white", width=12)
    table.add_column("현재가", style="bold green", width=10)
    table.add_column("향상점수", style="green", width=10)
    table.add_column("등급", style="yellow", width=6)
    table.add_column("ROE", style="magenta", width=8)
    table.add_column("부채비율", style="red", width=10)
    table.add_column("순이익률", style="blue", width=10)
    table.add_column("매출성장률", style="green", width=10)
    
    for i, pick in enumerate(top_picks, 1):
        financial_data = pick.get('financial_data', {})
        current_price = pick.get('current_price', 0)
        
        
        table.add_row(
            str(i),
            pick['symbol'],
            pick['name'][:10] + "..." if len(pick['name']) > 10 else pick['name'],
            f"{current_price:,.0f}원" if current_price and current_price > 0 else "N/A",
            f"{pick['enhanced_score']:.1f}",
            pick['enhanced_grade'],
            f"{financial_data.get('roe', 0):.1f}%" if financial_data.get('roe', 0) != 0 else "N/A",
            f"{financial_data.get('debt_ratio', 0):.1f}%" if financial_data.get('debt_ratio', 0) != 0 else "N/A",
            f"{financial_data.get('net_profit_margin', 0):.1f}%" if financial_data.get('net_profit_margin', 0) != 0 else "N/A",
            f"{financial_data.get('revenue_growth_rate_annual', 0):.1f}%" if financial_data.get('revenue_growth_rate_annual', 0) != 0 else "N/A"
        )
    
    console.print(table)
    
    # CSV 내보내기
    if export_csv:
        try:
            export_data = []
            for pick in top_picks:
                financial_data = pick.get('financial_data', {})
                breakdown = pick.get('score_breakdown', {})
                
                export_data.append({
                    'rank': top_picks.index(pick) + 1,
                    'symbol': pick['symbol'],
                    'name': pick['name'],
                    'current_price': pick.get('current_price', 0),
                    'market_cap': pick['market_cap'],
                    'enhanced_score': pick['enhanced_score'],
                    'enhanced_grade': pick['enhanced_grade'],
                    'roe': financial_data.get('roe', 0),
                    'roa': financial_data.get('roa', 0),
                    'debt_ratio': financial_data.get('debt_ratio', 0),
                    'net_profit_margin': financial_data.get('net_profit_margin', 0),
                    'current_ratio': financial_data.get('current_ratio', 0),
                    'revenue_growth_rate': financial_data.get('revenue_growth_rate_annual', 0),
                    'opinion_score': breakdown.get('투자의견', 0),
                    'financial_score': breakdown.get('재무건전성', 0) + breakdown.get('밸류에이션', 0),
                    'financial_ratio_score': breakdown.get('재무비율', 0),
                    'growth_score': breakdown.get('성장성', 0),
                    'scale_score': breakdown.get('규모', 0)
                })
            
            df = pd.DataFrame(export_data)
            filename = f"enhanced_top_picks_{int(time.time())}.csv"
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            console.print(f"\n💾 향상된 분석 결과가 {filename}에 저장되었습니다.")
            
        except Exception as e:
            console.print(f"[red]❌ CSV 내보내기 실패: {e}[/red]")

@app.command()
def show_config():
    """현재 향상된 통합 분석 설정을 표시합니다."""
    analyzer = EnhancedIntegratedAnalyzer()
    
    console.print("🔧 [bold]현재 향상된 통합 분석 설정[/bold]")
    
    # 가중치 표시
    console.print("\n📊 [bold]분석 요소별 가중치[/bold]")
    table = Table(title="가중치 설정")
    table.add_column("분석 요소", style="cyan")
    table.add_column("가중치", style="green", justify="right")
    table.add_column("설명", style="white")
    
    table.add_row("투자의견", f"{analyzer.weights['opinion_analysis']}%", "증권사 투자의견 및 컨센서스")
    table.add_row("추정실적", f"{analyzer.weights['estimate_analysis']}%", "미래 실적 전망 및 투자지표")
    table.add_row("재무비율", f"{analyzer.weights['financial_ratios']}%", "ROE, ROA, 부채비율, 순이익률, 유동비율")
    table.add_row("성장성", f"{analyzer.weights['growth_analysis']}%", "매출액/영업이익 성장률")
    table.add_row("규모", f"{analyzer.weights['scale_analysis']}%", "시가총액 기반 안정성")
    
    console.print(table)
    
    # 재무비율 세부 가중치 표시
    console.print("\n💰 [bold]재무비율 세부 가중치 (30점 만점 내에서)[/bold]")
    ratio_table = Table(title="재무비율 세부 가중치")
    ratio_table.add_column("지표", style="cyan")
    ratio_table.add_column("가중치", style="green", justify="right")
    ratio_table.add_column("설명", style="white")
    
    ratio_table.add_row("ROE", f"{analyzer.financial_ratio_weights['roe_score']}점", "자기자본이익률")
    ratio_table.add_row("ROA", f"{analyzer.financial_ratio_weights['roa_score']}점", "총자산이익률")
    ratio_table.add_row("부채비율", f"{analyzer.financial_ratio_weights['debt_ratio_score']}점", "부채 수준 (낮을수록 좋음)")
    ratio_table.add_row("순이익률", f"{analyzer.financial_ratio_weights['net_profit_margin_score']}점", "매출 대비 순이익 비율")
    ratio_table.add_row("유동비율", f"{analyzer.financial_ratio_weights['current_ratio_score']}점", "단기 부채 상환 능력")
    ratio_table.add_row("성장성", f"{analyzer.financial_ratio_weights['growth_score']}점", "매출 성장률")
    
    console.print(ratio_table)
    
    # 등급 기준 표시
    console.print("\n🏆 [bold]등급 기준[/bold]")
    grade_table = Table(title="등급 기준")
    grade_table.add_column("등급", style="cyan")
    grade_table.add_column("최소 점수", style="green", justify="right")
    
    for grade, threshold in analyzer.grade_thresholds.items():
        if grade != 'F':
            grade_table.add_row(grade, f"{threshold}점 이상")
    
    grade_table.add_row("F", "5점 미만")
    console.print(grade_table)

@app.command()
def test_presets():
    """투자 철학 프리셋들을 테스트합니다."""
    console.print("🎯 [bold]투자 철학 프리셋 테스트[/bold]")
    
    presets = ["balanced", "value_focused", "growth_focused", "consensus_focused", "stability_focused"]
    
    for preset in presets:
        console.print(f"\n📊 [bold]{preset} 프리셋[/bold]")
        analyzer = EnhancedIntegratedAnalyzer()
        analyzer._apply_investment_philosophy_preset(preset)
        
        # 가중치 표시
        table = Table(title=f"{preset} 가중치")
        table.add_column("분석 요소", style="cyan")
        table.add_column("가중치", style="green", justify="right")
        
        for element, weight in analyzer.weights.items():
            table.add_row(element.replace('_', ' ').title(), f"{weight}%")
        
        console.print(table)

if __name__ == "__main__":
    app()
