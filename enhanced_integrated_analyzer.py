# enhanced_integrated_analyzer.py
import typer
import pandas as pd
import logging
import time
import os
import yaml
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from collections import deque
import random
from rich.console import Console
from rich.progress import Progress
from rich.table import Table
from typing import List, Dict, Any, Tuple
from numbers import Real
from kis_data_provider import KISDataProvider
from investment_opinion_analyzer import InvestmentOpinionAnalyzer
from estimate_performance_analyzer import EstimatePerformanceAnalyzer
from financial_ratio_analyzer import FinancialRatioAnalyzer
from profit_ratio_analyzer import ProfitRatioAnalyzer
from stability_ratio_analyzer import StabilityRatioAnalyzer
from growth_ratio_analyzer import GrowthRatioAnalyzer
from test_integrated_analysis import create_integrated_analysis
# 백테스팅 관련 import는 함수 내부에서 처리

# 로깅 설정
def setup_logging(log_file: str = None, log_level: str = "INFO"):
    """로깅 설정을 초기화합니다."""
    import os
    from datetime import datetime
    
    # typer.OptionInfo 객체 처리
    if hasattr(log_level, 'value'):
        log_level = log_level.value
    if hasattr(log_file, 'value'):
        log_file = log_file.value
    
    # 로그 레벨 설정
    level = getattr(logging, str(log_level).upper(), logging.INFO)
    
    # 로그 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 콘솔 핸들러 추가
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 파일 핸들러 추가 (옵션)
    if log_file:
        # 로그 디렉토리 생성
        if os.path.dirname(str(log_file)):
            log_dir = os.path.dirname(str(log_file))
        else:
            log_dir = "logs"
        
        os.makedirs(log_dir, exist_ok=True)
        
        # 타임스탬프가 포함된 파일명 생성
        try:
            log_file_str = str(log_file)
            # OptionInfo 객체인 경우 기본값 사용
            if '<typer.models' in log_file_str or 'OptionInfo' in log_file_str:
                log_file_str = "enhanced_analysis.log"
        except:
            log_file_str = "enhanced_analysis.log"
            
        if not os.path.isabs(log_file_str):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name, ext = os.path.splitext(os.path.basename(log_file_str))
            final_log_file = os.path.join(log_dir, f"{name}_{timestamp}{ext}")
        else:
            # 절대 경로인 경우 타임스탬프 추가
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name, ext = os.path.splitext(log_file_str)
            final_log_file = f"{name}_{timestamp}{ext}"
        
        file_handler = logging.FileHandler(final_log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        # 콘솔 유무와 무관하게 조용히 동작 (환경 의존성 제거)
        # 로그 파일 경로는 logger를 통해서만 확인하도록 일원화
    
    return root_logger

# Rich Console 초기화 (console을 먼저 만들고)
console = Console()
# 기본 로깅 설정
logger = setup_logging()

# TPS 제한을 고려한 레이트리미터 클래스 (deque 기반, jitter 포함)
class TPSRateLimiter:
    """KIS OpenAPI TPS 제한을 고려한 레이트리미터 (deque 기반, jitter 포함)"""
    
    def __init__(self, max_tps: int = 8):  # 안전 마진을 위해 8로 설정
        self.max_tps = max_tps
        self.ts = deque()
        self.lock = Lock()
    
    def acquire(self):
        """요청 허가를 받습니다."""
        with self.lock:
            now = time.time()
            one_sec_ago = now - 1.0
            
            # 1초 이전 타임스탬프 제거
            while self.ts and self.ts[0] < one_sec_ago:
                self.ts.popleft()
            
            if len(self.ts) >= self.max_tps:
                sleep_time = 1.0 - (now - self.ts[0])
                if sleep_time > 0:
                    # 작은 지터로 동시성 충돌 완화
                    time.sleep(sleep_time + random.uniform(0.01, 0.08))
                
                # 윈도우 정리
                now = time.time()
                one_sec_ago = now - 1.0
                while self.ts and self.ts[0] < one_sec_ago:
                    self.ts.popleft()
            
            self.ts.append(time.time())
            time.sleep(0.002)  # 아주 짧은 간격으로 버스트 완화

# 전역 레이트리미터 인스턴스
rate_limiter = TPSRateLimiter(max_tps=8)

# Typer 입력 검증 함수들
def _positive_float(value: float):
    """양수 검증"""
    if value < 0:
        raise typer.BadParameter("0 이상이어야 합니다.")
    return value

def _positive_int(value: int):
    """양의 정수 검증"""
    if value <= 0:
        raise typer.BadParameter("1 이상이어야 합니다.")
    return value

class EnhancedIntegratedAnalyzer:
    """재무비율 분석이 통합된 향상된 분석 클래스"""
    
    # 품질 점수 임계값 상수
    QUALITY_EXCELLENT = 1.00
    QUALITY_GOOD = 0.65
    QUALITY_LOWQ = 0.50
    
    def __init__(self, config_file: str = "config.yaml"):
        self.opinion_analyzer = InvestmentOpinionAnalyzer()
        self.estimate_analyzer = EstimatePerformanceAnalyzer()
        self.provider = KISDataProvider()
        self.financial_ratio_analyzer = FinancialRatioAnalyzer(self.provider)
        self.profit_ratio_analyzer = ProfitRatioAnalyzer(self.provider)
        self.stability_ratio_analyzer = StabilityRatioAnalyzer(self.provider)
        self.growth_ratio_analyzer = GrowthRatioAnalyzer(self.provider)
        self.kospi_data = None
        # 공급자 호출 경합 완화용(부분적) 락
        self._provider_lock = Lock()
        
        # 설정 로드
        self.config = self._load_config(config_file)
        self._load_kospi_data()
    
    def _effective_weights(self) -> Tuple[Dict[str, float], float]:
        """
        self.weights에서 valuation_bonus를 분리하고,
        보너스 포함 총합을 100으로 정규화하여 일관성을 유지.
        """
        base = dict(self.weights) if isinstance(self.weights, dict) else {}
        vb = float(base.pop('valuation_bonus', 0) or 0)

        base_total = sum(base.values())
        total = base_total + vb
        if total <= 0:
            # 완전 비정상 보호
            base = {k: 0.0 for k in ('opinion_analysis','estimate_analysis','financial_ratios','growth_analysis','scale_analysis')}
            return base, 0.0

        # 전체 100으로 정규화 (보너스 포함)
        scale = 100.0 / total
        base = {k: v * scale for k, v in base.items()}
        vb = vb * scale
        return base, vb
    
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
            
            # 기본 등급 기준 설정 (더 엄격한 조정)
            default_grade_thresholds = {
                'A_plus': 80,
                'A': 70,
                'B_plus': 60,
                'B': 50,
                'C_plus': 40,
                'C': 30,
                'D': 20,
                'F': 0
            }
            
            # 설정 병합
            self.weights = enhanced_config.get('weights', default_weights)
            self.financial_ratio_weights = enhanced_config.get('financial_ratio_weights', default_financial_weights)
            self.estimate_analysis_weights = enhanced_config.get('estimate_analysis_weights', default_estimate_weights)
            self.grade_thresholds = enhanced_config.get('grade_thresholds', default_grade_thresholds)
            
            # 가중치 합계 검증 + 경고 (정규화는 _effective_weights()에서 수행)
            try:
                total = sum(self.weights.values())
                if total <= 0:
                    raise ValueError("Weights total is zero or negative")
                # ✅ 여기서는 정규화하지 않고 경고만: 최종 스케일은 _effective_weights()에서 처리
                if abs(total - 100) > 1e-6:
                    console.print(f"⚠️ 가중치 합({total})가 100이 아닙니다. 계산 시 자동 보정됩니다.")
            except Exception as e:
                console.print(f"⚠️ 가중치 검증 중 문제 발생: {e} (기본값 사용)")
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
                'A_plus': 80,
                'A': 70,
                'B_plus': 60,
                'B': 50,
                'C_plus': 40,
                'C': 30,
                'D': 20,
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
                self.kospi_data = pd.read_excel(kospi_file, engine="openpyxl")  # 명시적 엔진 지정
                # ✅ 단축코드 6자리 0패딩 강제 (문자열 기준)
                self.kospi_data['단축코드'] = (
                    self.kospi_data['단축코드']
                        .astype(str)
                        .str.replace(r'\.0$', '', regex=True)  # float로 읽힌 흔적 제거
                        .str.zfill(6)
                )
                
                # 스키마 가드 & 정규화
                required = ['단축코드', '한글명', '시가총액']
                for col in required:
                    if col not in self.kospi_data.columns:
                        raise ValueError(f"KOSPI 파일에 필수 컬럼 누락: {col}")
                
                if '지수업종대분류' not in self.kospi_data.columns:
                    self.kospi_data['지수업종대분류'] = ''
                if '현재가' not in self.kospi_data.columns:
                    self.kospi_data['현재가'] = 0
                
                console.print(f"✅ KOSPI 마스터 데이터 로드 완료: {len(self.kospi_data)}개 종목")
                
                # KOSPI 인덱스 생성 (O(1) 룩업을 위한 최적화)
                self._kospi_index = {}
                if not self.kospi_data.empty:
                    self._kospi_index = {
                        str(row.단축코드): row for row in self.kospi_data.itertuples(index=False)
                    }
            else:
                console.print(f"⚠️ {kospi_file} 파일을 찾을 수 없습니다.")
                self.kospi_data = pd.DataFrame()
                self._kospi_index = {}
        except Exception as e:
            console.print(
                "❌ KOSPI 데이터 로드 실패: "
                f"{e}\n   ↳ openpyxl 미설치 여부, 파일 경로/권한, 시트 포맷을 확인하세요."
            )
            self.kospi_data = pd.DataFrame()
            self._kospi_index = {}
    
    def get_top_market_cap_stocks(self, count: int = 100, min_market_cap: float = 500) -> List[Dict[str, Any]]:
        """시가총액 상위 종목들을 반환합니다."""
        if self.kospi_data is None or self.kospi_data.empty:
            return []
        
        # 우선주/전환/신형 등 변형 제외: 이름 기반 + (가능 시) '주식종류' 우선 사용
        pref_name_pat = r'\s*우(?:[ABC])?(?:\(.+?\))?\s*$'  # 끝 공백/괄호/서픽스 모두 커버
        exclude_name_pat = r'(스팩|리츠|ETF|ETN|인수권|BW|CB)'  # 스팩/리츠/ETF 등 제외
        has_kind_col = '주식종류' in self.kospi_data.columns
        if has_kind_col:
            is_common = self.kospi_data['주식종류'].astype(str).str.contains('보통주', na=False)
            is_excluded = self.kospi_data['한글명'].str.contains(exclude_name_pat, na=False, regex=True)
            base = self.kospi_data[(self.kospi_data['시가총액'] >= min_market_cap) & (is_common) & (~is_excluded)]
        else:
            is_pref_name = self.kospi_data['한글명'].str.contains(pref_name_pat, na=False, regex=True)
            is_excluded = self.kospi_data['한글명'].str.contains(exclude_name_pat, na=False, regex=True)
            base = self.kospi_data[(self.kospi_data['시가총액'] >= min_market_cap) & (~is_pref_name) & (~is_excluded)]
        filtered_stocks = base.nlargest(count, '시가총액')
        
        stocks = []
        for _, stock in filtered_stocks.iterrows():
            stocks.append({
                'symbol': str(stock['단축코드']),  # 문자열로 통일
                'name': stock['한글명'],
                'market_cap': stock['시가총액'],
                'sector': str(stock.get('지수업종대분류', ''))
            })
        
        return stocks
    
    def get_financial_ratios_data(self, symbol: str) -> Dict[str, Any]:
        """종목의 재무비율 데이터를 수집합니다. (고급 재시도 로직 적용)"""
        financial_data = {}
        
        # 1. 재무비율 분석 (고급 재시도 로직 + 무자료 즉시 중단)
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
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
                    break
                else:
                    # 무자료는 영구 실패로 간주(우선주/비커버리지 가능성 높음)
                    if attempt == 0:
                        logger.debug(f"⚠️ {symbol} 재무비율 무자료: 즉시 중단")
                        break
                    if attempt < max_retries:
                        logger.debug(f"🔄 {symbol} 재무비율 조회 재시도 중... ({attempt + 1}/{max_retries})")
                        time.sleep(0.5)
                        continue
                    else:
                        logger.debug(f"⚠️ {symbol} 재무비율 데이터 없음")
            except Exception as e:
                if attempt < max_retries:
                    logger.debug(f"🔄 {symbol} 재무비율 API 호출 재시도 중... ({attempt + 1}/{max_retries}): {e}")
                    time.sleep(0.5)
                    continue
                else:
                    logger.warning(f"❌ {symbol} 재무비율 API 호출 최종 실패: {e}")
        
        # 2. 수익성비율 분석 (강화된 재시도 로직 + 무자료 즉시 중단)
        max_retries = 3  # 재시도 횟수 감소 (5 → 3)
        for attempt in range(max_retries + 1):
            try:
                rate_limiter.acquire()
                profit_ratios = self.profit_ratio_analyzer.get_profit_ratios(symbol)
                if profit_ratios and len(profit_ratios) > 0:
                    latest_profit = profit_ratios[0]
                    financial_data.update({
                        'net_profit_margin': latest_profit.get('net_profit_margin', 0),
                        'gross_profit_margin': latest_profit.get('gross_profit_margin', 0),
                        'profitability_grade': latest_profit.get('profitability_grade', '평가불가')
                    })
                    break
                else:
                    # 무자료는 영구 실패로 간주(우선주/비커버리지 가능성 높음)
                    if attempt == 0:
                        logger.debug(f"⚠️ {symbol} 수익성비율 무자료: 즉시 중단")
                        break
                    if attempt < max_retries:
                        # 지수 백오프: 2초, 4초, 8초
                        wait_time = 2 ** (attempt + 1)
                        logger.debug(f"🔄 {symbol} 수익성비율 조회 재시도 중... ({attempt + 1}/{max_retries}, {wait_time}초 대기)")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.debug(f"⚠️ {symbol} 수익성비율 데이터 없음")
            except Exception as e:
                if attempt < max_retries:
                    # 지수 백오프: 2초, 4초, 8초
                    wait_time = 2 ** (attempt + 1)
                    logger.debug(f"🔄 {symbol} 수익성비율 API 호출 재시도 중... ({attempt + 1}/{max_retries}, {wait_time}초 대기): {e}")
                    time.sleep(wait_time)
                    continue
                else:
                    # 연결 오류인 경우에만 경고, 다른 오류는 디버그
                    if 'Connection' in str(e) or 'RemoteDisconnected' in str(e):
                        logger.warning(f"❌ {symbol} 수익성비율 API 연결 실패: {e}")
                    else:
                        logger.debug(f"❌ {symbol} 수익성비율 API 호출 실패: {e}")
                    
                    # 실패 시 기본값 설정
                    financial_data.update({
                        'net_profit_margin': 0,
                        'gross_profit_margin': 0,
                        'profitability_grade': '데이터없음'
                    })
        
        # 3. 안정성비율 분석 (기본 재시도 로직)
        try:
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
            logger.warning(f"❌ {symbol} 안정성비율 분석 실패: {e}")
        
        # 4. 성장성비율 분석 (기본 재시도 로직)
        try:
            rate_limiter.acquire()
            growth_ratios = self.growth_ratio_analyzer.get_growth_ratios(symbol)
            if growth_ratios and len(growth_ratios) > 0:
                latest_growth = growth_ratios[0]
                financial_data.update({
                    # 성장률 키 일원화: revenue_growth (YoY, %)
                    'revenue_growth': latest_growth.get('revenue_growth_rate', 0),
                    'operating_income_growth_rate_annual': latest_growth.get('operating_income_growth_rate', 0),
                    'equity_growth_rate': latest_growth.get('equity_growth_rate', 0),
                    'total_asset_growth_rate': latest_growth.get('total_asset_growth_rate', 0),
                    'growth_grade': latest_growth.get('growth_grade', '평가불가')
                })
        except Exception as e:
            logger.warning(f"❌ {symbol} 성장성비율 분석 실패: {e}")
        
        # 데이터 결측 플래그 추가 (실무 판단을 위한 구분)
        financial_data['__missing_flags__'] = {
            'ratios': not (self._has_numeric(financial_data, 'roe') or self._has_numeric(financial_data, 'roa')),
            'profit': not self._has_numeric(financial_data, 'net_profit_margin'),
            'stability': not self._has_numeric(financial_data, 'current_ratio'),
            'growth': not (self._has_numeric(financial_data, 'revenue_growth') or
                           self._has_numeric(financial_data, 'revenue_growth_rate'))
        }
        
        return financial_data
    
    def calculate_enhanced_integrated_score(self, opinion_analysis: Dict[str, Any], 
                                          estimate_analysis: Dict[str, Any], 
                                          financial_data: Dict[str, Any],
                                          market_cap: float, 
                                          current_price: float = None,
                                          price_position: float = None,
                                          risk_score: int = None) -> Dict[str, Any]:
        """저평가 가치주 발굴을 위한 향상된 통합 점수를 계산합니다."""
        score = 0.0
        score_breakdown = {}
        
        # 실제 계산용 가중치/보너스 분리
        base_w, vb_points = self._effective_weights()
        
        # 1. 투자의견 점수
        opinion_weight = float(base_w.get('opinion_analysis', 0.0))
        consensus_score = None
        if isinstance(opinion_analysis, dict):
            cs_top = opinion_analysis.get('consensus_score')
            cs_nested = opinion_analysis.get('consensus_analysis', {}).get('consensus_score')
            consensus_score = cs_top if cs_top is not None else cs_nested

        if consensus_score is not None:
            try:
                cs = float(consensus_score)
                cs = max(-1.0, min(1.0, cs))  # 범위 가드
                opinion_score = (cs + 1.0) * (opinion_weight / 2.0)  # -1~1 → 0~가중치
                opinion_score = max(0.0, min(opinion_weight, opinion_score))
                score += opinion_score
                score_breakdown['투자의견'] = opinion_score
            except Exception:
                score_breakdown['투자의견'] = 0
        else:
            score_breakdown['투자의견'] = 0
        
        # 2. 추정실적 점수
        estimate_weight = float(base_w.get('estimate_analysis', 0.0))
        if 'financial_health_score' in estimate_analysis and 'valuation_score' in estimate_analysis:
            financial_health_weight = self.estimate_analysis_weights['financial_health']
            valuation_weight = self.estimate_analysis_weights['valuation']
            
            # 내부 원점수(30점 기준) → 목표 포인트(estimate_weight)로 스케일
            scale_factor = estimate_weight / 30.0
            fh = max(0.0, min(15.0, float(estimate_analysis['financial_health_score'] or 0)))
            vs = max(0.0, min(15.0, float(estimate_analysis['valuation_score'] or 0)))
            financial_score = fh * scale_factor * (financial_health_weight / 15)
            valuation_score = vs * scale_factor * (valuation_weight / 15)
            
            score += financial_score + valuation_score
            score_breakdown['재무건전성'] = financial_score
            score_breakdown['밸류에이션'] = valuation_score
        
        # 3. 재무비율 점수
        fr_weight = float(base_w.get('financial_ratios', 0.0))
        fr_raw = self._calculate_financial_ratio_score(financial_data)  # 30점 만점
        fr_scaled = fr_raw * (fr_weight / 30.0)
        score += fr_scaled
        score_breakdown['재무비율'] = fr_scaled
        
        # 4. 성장성 점수
        growth_weight = float(base_w.get('growth_analysis', 0.0))
        # 성장률 소스 일원화: estimate → financial_data → 0
        revenue_growth = estimate_analysis.get('latest_revenue_growth',
                         financial_data.get('revenue_growth', 0))
        if revenue_growth is not None:
            growth_score = self._calculate_growth_score(revenue_growth, growth_weight)
            score += growth_score
            score_breakdown['성장성'] = growth_score
        
        # 5. 규모 점수
        scale_weight = float(base_w.get('scale_analysis', 0.0))
        scale_score = self._calculate_scale_score(market_cap, scale_weight)
        score += scale_score
        score_breakdown['규모'] = scale_score
        
        # 6. 저평가 보너스 점수 (valuation_bonus)
        vb = float(vb_points or 0.0)
        if vb > 0:
            vb_score = self._calculate_valuation_bonus_score(estimate_analysis, financial_data, vb)
            score += vb_score
            score_breakdown['저평가보너스'] = vb_score
        
        # 7. 52주 최고가 근처 페널티 (신규 추가)
        if price_position is not None:
            # 범위 가드
            try:
                pp = max(0.0, min(100.0, float(price_position)))
            except Exception:
                pp = None
            high_price_penalty = self._calculate_high_price_penalty(pp) if pp is not None else 0
            score -= high_price_penalty
            score_breakdown['고가페널티'] = -high_price_penalty
        
        # 8. 리스크 점수 반영 (신규 추가)
        if risk_score is not None:
            try:
                risk_score = int(round(float(risk_score)))  # 타입 가드
                risk_penalty = self._calculate_risk_penalty(risk_score)
                score -= risk_penalty
                score_breakdown['리스크페널티'] = -risk_penalty
            except Exception:
                pass  # 리스크 점수 변환 실패 시 무시
        
        return {
            'total_score': min(100, max(0, score)),
            'score_breakdown': score_breakdown
        }
    
    def _calculate_valuation_bonus_score(self, estimate_analysis: Dict[str, Any], 
                                       financial_data: Dict[str, Any], 
                                       max_bonus: float) -> float:
        """저평가 보너스 점수를 계산합니다."""
        bonus_score = 0.0

        def _safe_pos_float(v):
            try:
                x = float(v)
                return x if x > 0 and not pd.isna(x) else 0.0
            except Exception:
                return 0.0

        per = _safe_pos_float(estimate_analysis.get('per', 0))
        pbr = _safe_pos_float(estimate_analysis.get('pbr', 0))
        roe = _safe_pos_float(financial_data.get('roe', 0))

        # PER 기반 저평가 보너스
        if per > 0:
            if per <= 8:  # 매우 저평가
                bonus_score += max_bonus * 0.4
            elif per <= 12:  # 저평가
                bonus_score += max_bonus * 0.3
            elif per <= 15:  # 적정가
                bonus_score += max_bonus * 0.2
            elif per <= 20:  # 약간 고평가
                bonus_score += max_bonus * 0.1
        
        # PBR 기반 저평가 보너스
        if pbr > 0:
            if pbr <= 0.8:  # 매우 저평가
                bonus_score += max_bonus * 0.3
            elif pbr <= 1.2:  # 저평가
                bonus_score += max_bonus * 0.2
            elif pbr <= 1.5:  # 적정가
                bonus_score += max_bonus * 0.1
        
        # ROE 대비 PER 저평가 보너스
        if roe > 0 and per > 0:
            pe_roe_ratio = per / roe
            if pe_roe_ratio <= 0.5:  # 매우 저평가
                bonus_score += max_bonus * 0.3
            elif pe_roe_ratio <= 0.8:  # 저평가
                bonus_score += max_bonus * 0.2
            elif pe_roe_ratio <= 1.0:  # 적정가
                bonus_score += max_bonus * 0.1
        
        return min(max_bonus, bonus_score)
    
    def _calculate_high_price_penalty(self, price_position: float) -> float:
        """52주 최고가 근처 페널티를 계산합니다."""
        if price_position >= 95:  # 52주 최고가 95% 이상
            return 20  # 20점 페널티
        elif price_position >= 90:  # 52주 최고가 90% 이상
            return 15  # 15점 페널티
        elif price_position >= 80:  # 52주 최고가 80% 이상
            return 10  # 10점 페널티
        elif price_position >= 70:  # 52주 최고가 70% 이상
            return 5   # 5점 페널티
        else:
            return 0   # 페널티 없음
    
    def _calculate_risk_penalty(self, risk_score: int) -> float:
        """리스크 점수에 따른 페널티를 계산합니다."""
        if risk_score >= 8:  # 매우 높은 리스크
            return 25  # 25점 페널티
        elif risk_score >= 6:  # 높은 리스크
            return 20  # 20점 페널티
        elif risk_score >= 4:  # 중간 리스크
            return 15  # 15점 페널티
        elif risk_score >= 2:  # 낮은 리스크
            return 10  # 10점 페널티
        elif risk_score >= 1:  # 매우 낮은 리스크
            return 5   # 5점 페널티
        else:
            return 0   # 페널티 없음

    def _calculate_roe_score(self, roe: float) -> float:
        """ROE 점수를 계산합니다."""
        roe_weight = self.financial_ratio_weights.get('roe_score', 8)
        score = 0
        if roe >= 20:
            score += roe_weight
        elif roe >= 15:
            score += roe_weight * 0.75
        elif roe >= 10:
            score += roe_weight * 0.5
        elif roe >= 5:
            score += roe_weight * 0.25
        return score

    def _calculate_roa_score(self, roa: float) -> float:
        """ROA 점수를 계산합니다."""
        roa_weight = self.financial_ratio_weights.get('roa_score', 5)
        score = 0
        if roa >= 10:
            score += roa_weight
        elif roa >= 7:
            score += roa_weight * 0.8
        elif roa >= 5:
            score += roa_weight * 0.6
        elif roa >= 3:
            score += roa_weight * 0.4
        return score

    def _calculate_debt_ratio_score(self, debt_ratio: float) -> float:
        """부채비율 점수를 계산합니다. (낮을수록 좋음)"""
        debt_ratio_weight = self.financial_ratio_weights.get('debt_ratio_score', 7)
        score = 0
        
        # 🔧 정규화: (0 < dr < 5) 범위는 배수로 간주 → %
        try:
            dr = float(debt_ratio)
            if 0 < dr < 5:
                debt_ratio = dr * 100.0
            else:
                debt_ratio = dr
        except Exception:
            return 0
        
        # 비정상/결측 처리
        if debt_ratio < 0 or debt_ratio >= 999:
            return 0
        
        if debt_ratio <= 30:
            score += debt_ratio_weight
        elif debt_ratio <= 50:
            score += debt_ratio_weight * 0.8
        elif debt_ratio <= 70:
            score += debt_ratio_weight * 0.6
        elif debt_ratio <= 100:
            score += debt_ratio_weight * 0.4
        elif debt_ratio <= 150:
            score += debt_ratio_weight * 0.2
        return score

    def _calculate_net_profit_margin_score(self, net_profit_margin: float) -> float:
        """순이익률 점수를 계산합니다."""
        net_profit_margin_weight = self.financial_ratio_weights.get('net_profit_margin_score', 5)
        score = 0
        if net_profit_margin >= 15:
            score += net_profit_margin_weight
        elif net_profit_margin >= 10:
            score += net_profit_margin_weight * 0.8
        elif net_profit_margin >= 5:
            score += net_profit_margin_weight * 0.6
        elif net_profit_margin >= 2:
            score += net_profit_margin_weight * 0.4
        return score

    def _calculate_current_ratio_score(self, current_ratio: float) -> float:
        """유동비율 점수를 계산합니다. (200% = 2.0 이상이 이상적)"""
        current_ratio_weight = self.financial_ratio_weights.get('current_ratio_score', 3)
        score = 0
        # NOTE: 소스에 따라 배수(1.8)로 들어오는 경우가 있어 정규화
        cr = float(current_ratio) if current_ratio is not None else 0.0
        if 0 < cr <= 5.0:  # 0 < cr <= 5.0 이면 배수(=x100), 그 외는 이미 %라고 가정
            cr *= 100.0
        if cr >= 200:  # 200% 기준
            score += current_ratio_weight
        elif cr >= 150:
            score += current_ratio_weight * 0.67
        elif cr >= 100:
            score += current_ratio_weight * 0.33
        return score

    def _calculate_ratio_growth_score(self, revenue_growth: float) -> float:
        """재무비율 섹션의 성장성 점수를 계산합니다. (매출액 성장률 기준)"""
        growth_weight = self.financial_ratio_weights.get('growth_score', 2)
        g = self._normalize_pct(revenue_growth)
        score = 0
        if g >= 20:
            score += growth_weight
        elif g >= 10:
            score += growth_weight * 0.5
        return score

    def _calculate_financial_ratio_score(self, financial_data: Dict[str, Any]) -> float:
        """재무비율 점수를 계산합니다. (개선된 로직)"""
        
        # 안전한 비율 값 가져오기 (비정상 값/None은 0 또는 불리한 기본값 사용)
        roe = self._safe_get_ratio(financial_data, 'roe', 0)
        roa = self._safe_get_ratio(financial_data, 'roa', 0)
        # 부채비율은 값이 없거나 0이면 좋은 것, 비정상적인 값은 높은 값(999)으로 간주하여 낮은 점수 부여 유도
        debt_ratio = self._safe_get_ratio(financial_data, 'debt_ratio', 999) 
        net_profit_margin = self._safe_get_ratio(financial_data, 'net_profit_margin', 0)
        # 유동비율은 값이 없거나 0이면 불리한 것, 0으로 간주
        current_ratio = self._safe_get_ratio(financial_data, 'current_ratio', 0)
        
        # 성장률 소스 일원화: financial_data 내 'revenue_growth'를 최우선, 없으면 'revenue_growth_rate'
        revenue_growth = self._safe_get_ratio(
            financial_data,
            'revenue_growth',
            self._safe_get_ratio(financial_data, 'revenue_growth_rate', 0)  # 실제 키와 일치
        )

        score = 0
        score += self._calculate_roe_score(roe)
        score += self._calculate_roa_score(roa)
        score += self._calculate_debt_ratio_score(debt_ratio)
        score += self._calculate_net_profit_margin_score(net_profit_margin)
        score += self._calculate_current_ratio_score(current_ratio)
        score += self._calculate_ratio_growth_score(revenue_growth)
        
        # 재무비율 원점수는 '30점 만점'으로 고정
        return min(30.0, score)
    
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
        g = self._normalize_pct(revenue_growth)
        
        if g >= thresholds['excellent']:  # 우수
            return max_score
        elif g >= thresholds['good']:  # 양호
            return max_score * 0.8
        elif g >= thresholds['average']:  # 보통
            return max_score * 0.5
        elif g >= thresholds['poor']:  # 부진
            return max_score * 0.3
        else:  # 매우 부진
            return 0
    
    def analyze_single_stock_enhanced(self, symbol: str, name: str, days_back: int = 30) -> Dict[str, Any]:
        """단일 종목의 향상된 통합 분석을 수행합니다. (고급 재시도 로직 적용)"""
        try:
            # 우선주 스킵: 이름 기반 + (가능 시) '주식종류' 확인. 코드 접미사 휴리스틱 제거.
            sym_str = str(symbol)
            row = self._kospi_index.get(sym_str)
            import re
            is_pref_name = bool(re.search(r'\s*우(?:[ABC])?(?:\(.+?\))?\s*$', str(name)))
            if row and hasattr(row, '주식종류'):
                if getattr(row, '주식종류', '') not in ('보통주', ''):
                    logger.info(f"⏭️ {name}({symbol}) 우선주/변형주로 판단되어 분석에서 제외합니다.")
                    return {
                        'symbol': symbol, 'name': name, 'status': 'skipped_pref',
                        'enhanced_score': 0, 'enhanced_grade': 'F',
                        'financial_data': {}, 'opinion_analysis': {}, 'estimate_analysis': {}
                    }
            elif is_pref_name:
                logger.info(f"⏭️ {name}({symbol}) 우선주로 판단되어 분석에서 제외합니다.")
                return {
                    'symbol': symbol, 'name': name, 'status': 'skipped_pref',
                    'enhanced_score': 0, 'enhanced_grade': 'F',
                    'financial_data': {}, 'opinion_analysis': {}, 'estimate_analysis': {}
                }
            # 투자의견 분석 (재시도 로직 적용)
            opinion_analysis = {}
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    opinion_analysis = self.opinion_analyzer.analyze_single_stock(symbol, days_back=days_back)
                    if opinion_analysis:
                        break
                except Exception as e:
                    if attempt < max_retries:
                        logger.debug(f"🔄 {symbol} 투자의견 분석 재시도 중... ({attempt + 1}/{max_retries}): {e}")
                        time.sleep(0.5)
                        continue
                    else:
                        logger.warning(f"❌ {symbol} 투자의견 분석 최종 실패: {e}")
                        opinion_analysis = {}
            
            # 추정실적 분석 (재시도 로직 적용)
            estimate_analysis = {}
            for attempt in range(max_retries + 1):
                try:
                    estimate_analysis = self.estimate_analyzer.analyze_single_stock(symbol)
                    if estimate_analysis:
                        break
                except Exception as e:
                    if attempt < max_retries:
                        logger.debug(f"🔄 {symbol} 추정실적 분석 재시도 중... ({attempt + 1}/{max_retries}): {e}")
                        time.sleep(0.5)
                        continue
                    else:
                        logger.warning(f"❌ {symbol} 추정실적 분석 최종 실패: {e}")
                        estimate_analysis = {}
            
            # 재무비율 데이터 수집 (이미 고급 재시도 로직 적용됨)
            financial_data = self.get_financial_ratios_data(symbol)
            
            # 시가총액/현재가 (KOSPI 데이터 O(1) 룩업)
            market_cap = 0
            current_price = 0
            row = self._kospi_index.get(str(symbol))
            if row:
                market_cap = float(getattr(row, '시가총액', 0) or 0)
                current_price = float(getattr(row, '현재가', 0) or 0)
            
            # KIS API에서 현재가/52주 고저 **1회 조회** (재시도 로직 + 락)
            price_position = None  # ✅ 루프 전 안전 초기화 (재시도 실패 시 UnboundLocal 방지)
            for attempt in range(max_retries + 1):
                try:
                    rate_limiter.acquire()
                    with self._provider_lock:
                        price_info = self.provider.get_stock_price_info(symbol)
                    if price_info and 'current_price' in price_info and price_info['current_price'] > 0:
                        current_price = float(price_info['current_price'])
                        # 52주 위치 계산 (동일 응답 사용)
                        w52_high = float(price_info.get('w52_high', 0) or 0)
                        w52_low = float(price_info.get('w52_low', 0) or 0)
                        if w52_high > w52_low > 0:
                            price_position = ((current_price - w52_low) / (w52_high - w52_low)) * 100
                        break
                    else:
                        if attempt < max_retries:
                            logger.debug(f"🔄 {symbol} 현재가 조회 재시도 중... ({attempt + 1}/{max_retries})")
                            time.sleep(0.5)
                            continue
                        else:
                            logger.warning(f"⚠️ {symbol} 현재가 데이터 없음")
                            current_price = 0
                except Exception as e:
                    if attempt < max_retries:
                        logger.debug(f"🔄 {symbol} 현재가 조회 재시도 중... ({attempt + 1}/{max_retries}): {e}")
                        time.sleep(0.5)
                        continue
                    else:
                        logger.warning(f"❌ {symbol} 현재가 조회 최종 실패: {e}")
                        current_price = 0
            
            # price_position은 위 루프에서 함께 계산됨 (중복 호출 제거)
            
            # 리스크 점수 계산 (시장 리스크 분석기 사용)
            risk_score = None
            risk_analysis = {}
            try:
                from market_risk_analyzer import create_market_risk_analyzer
                risk_analyzer = create_market_risk_analyzer(self.provider)
                risk_analysis = risk_analyzer.analyze_stock_risk(symbol)
                rs = risk_analysis.get('risk_score', 0)
                try:
                    risk_score = max(0.0, min(10.0, float(rs or 0)))
                except Exception:
                    risk_score = None
            except Exception as e:
                logger.debug(f"리스크 점수 계산 실패: {e}")
            
            # 향상된 통합 점수 계산 (저평가 가치주 발굴 중심, 리스크 반영)
            enhanced_score = self.calculate_enhanced_integrated_score(
                opinion_analysis, estimate_analysis, financial_data, market_cap, 
                current_price, price_position, risk_score
            )
            
            # 기존 통합 분석 결과
            integrated_analysis = create_integrated_analysis(opinion_analysis, estimate_analysis)
            
            # 향상된 분석 결과 생성
            enhanced_analysis = {
                'symbol': symbol,
                'name': name,
                'market_cap': market_cap,
                'current_price': current_price,
                'price_position': price_position,
                'status': 'success',
                'enhanced_score': enhanced_score['total_score'],
                'score_breakdown': enhanced_score['score_breakdown'],
                'enhanced_grade': self._get_enhanced_grade(enhanced_score['total_score']),
                'financial_data': financial_data,
                'opinion_analysis': opinion_analysis,
                'estimate_analysis': estimate_analysis,
                'integrated_analysis': integrated_analysis,
                'risk_analysis': risk_analysis
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
    
    def _safe_get_ratio(self, financial_data: Dict[str, Any], key: str, default_val: float) -> float:
        """안전하게 숫자 값을 추출합니다 (numpy/NaN 대응)."""
        val = financial_data.get(key)
        # NaN, None → 기본값
        if val is None:
            return default_val
        # 판다스/넘파이 숫자 타입 포함, NaN 방지
        try:
            if isinstance(val, Real):
                return float(val) if not pd.isna(val) else default_val
        except Exception:
            pass
        # 문자열 숫자도 관대하게 허용
        try:
            f = float(val)
            return f if not pd.isna(f) else default_val
        except Exception:
            return default_val
    
    def _normalize_pct(self, x: Any) -> float:
        """성장률 입력을 % 기준으로 정규화 (0.12 → 12.0). 숫자 아님/결측은 0 처리."""
        try:
            v = float(x)
            if pd.isna(v):
                return 0.0
            return v * 100.0 if -1.0 <= v <= 1.0 else v
        except Exception:
            return 0.0
    
    def _as_pct_number(self, x: Any) -> float:
        """퍼센트 값을 정수%로 정규화하여 반환 (0.12 -> 12.0, 12 -> 12.0)."""
        v = self._normalize_pct(x)   # 0.12 -> 12.0, 12 -> 12.0
        try:
            return float(v)
        except Exception:
            return 0.0

    def _has_numeric(self, data: Dict[str, Any], key: str) -> bool:
        """해당 키가 존재하고 수치로 파싱되면 True (0 포함)."""
        if key not in data:
            return False
        try:
            v = float(data[key])
            return not pd.isna(v)
        except Exception:
            return False

    def _fmt_pct(self, x: Any, *, assume_ratio_if_abs_lt_1: bool = True) -> str:
        """퍼센트 출력 헬퍼로 N/A 표기 일관화."""
        try:
            if x is None or (isinstance(x, float) and pd.isna(x)):
                return "N/A"
            xf = float(x)
            # 값이 [-1,1] 범위면 비율로 간주하여 ×100 (명시적 제어 가능)
            if assume_ratio_if_abs_lt_1 and -1.0 <= xf <= 1.0:
                xf *= 100.0
            return f"{xf:.1f}%"
        except Exception:
            return "N/A"
    
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
    
    def analyze_batch(self, symbols: List[Tuple[str, str]], days_back: int = 30):
        """배치 분석을 수행하고 요약 메트릭을 제공합니다."""
        results = []
        no_data_counts = {"opinion": 0, "estimate": 0, "financial": 0}
        quality_pipeline = {"excellent": 0, "good": 0, "poor": 0}  # 상수 기반 임계값
        
        for sym, name in symbols:
            r = self.analyze_single_stock_enhanced(sym, name, days_back=days_back)
            results.append(r)
            
            # 간단 요약 라인 로그 - 올바른 필드명 사용
            op_ct = r.get("opinion_analysis", {}).get("total_opinions", 0) if r.get("opinion_analysis") else 0
            est_q = r.get("estimate_analysis", {}).get("quality_score")
            fin_ok = bool(r.get("financial_data"))
            
            # 품질점수별 파이프라인 분기
            if est_q is not None:
                if est_q >= self.QUALITY_EXCELLENT:
                    quality_pipeline["excellent"] += 1
                    quality_tag = "🏆 우수"
                elif est_q >= self.QUALITY_GOOD:
                    quality_pipeline["good"] += 1
                    quality_tag = "⚠️ 보통"
                else:
                    quality_pipeline["poor"] += 1
                    quality_tag = "❌ 낮음"
                    # 품질점수 < QUALITY_LOWQ 종목에 (low Q) 플래그 추가
                    if est_q < self.QUALITY_LOWQ:
                        quality_tag += " (low Q)"
            else:
                quality_tag = "N/A"
            
            # 안전한 포맷팅
            est_q_str = f"{est_q:.2f}" if est_q is not None else "N/A"
            logger.info(
                f"📊 {name}({sym}) | 의견:{op_ct}건 | 추정Q:{est_q_str} {quality_tag} | 재무:{'OK' if fin_ok else 'NONE'} | grade:{r.get('enhanced_grade')}"
            )
            
            # 메트릭 집계
            if op_ct == 0: 
                no_data_counts["opinion"] += 1
            if est_q is not None and est_q < self.QUALITY_LOWQ: 
                no_data_counts["estimate"] += 1
            if not fin_ok: 
                no_data_counts["financial"] += 1
        
        logger.info(f"✅ 배치 완료 | 의견無:{no_data_counts['opinion']} | 저품질추정:{no_data_counts['estimate']} | 재무無:{no_data_counts['financial']}")
        logger.info(f"📈 품질분포 | 우수({self.QUALITY_EXCELLENT}):{quality_pipeline['excellent']} | 보통({self.QUALITY_GOOD}):{quality_pipeline['good']} | 낮음({self.QUALITY_LOWQ}):{quality_pipeline['poor']}")
        
        # 요약 메트릭 CSV 저장
        self._save_summary_metrics(results)
        
        return results
    
    def _save_summary_metrics(self, results: list):
        """종목별 요약 메트릭을 CSV로 저장합니다."""
        try:
            import pandas as pd
            from datetime import datetime
            import os
            
            # logs 디렉토리 보장
            os.makedirs("logs", exist_ok=True)
            
            summary_data = []
            for result in results:
                symbol = result.get('symbol', '')
                name = result.get('name', '')
                opinion_count = result.get('opinion_analysis', {}).get('total_opinions', 0) if result.get('opinion_analysis') else 0
                quality_score = result.get('estimate_analysis', {}).get('quality_score')
                enhanced_grade = result.get('enhanced_grade', 'F')
                enhanced_score = result.get('enhanced_score', 0)
                current_price = result.get('current_price', 0)
                
                summary_data.append({
                    'symbol': symbol,
                    'name': name,
                    'opinion_count': opinion_count,
                    'quality_score': quality_score if quality_score is not None else 0,
                    'enhanced_grade': enhanced_grade,
                    'enhanced_score': enhanced_score,
                    'current_price': current_price,
                    'price_position': result.get('price_position', None),  # ✅ 일관성 향상
                    'risk_score': (result.get('risk_analysis', {}) or {}).get('risk_score', None),  # ✅ 대시보드용
                    'analysis_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            
            # CSV 저장
            df = pd.DataFrame(summary_data)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"logs/summary_metrics_{timestamp}.csv"
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            logger.info(f"📊 요약 메트릭 저장: {filename} ({len(summary_data)}개 종목)")
            
        except Exception as e:
            logger.warning(f"⚠️ 요약 메트릭 저장 실패: {e}")
    
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
                # 🔁 _effective_weights()와 동일 개념으로 정규화(보너스 포함)
                base = dict(self.weights)
                vb = float(base.pop('valuation_bonus', 0) or 0)
                total = sum(base.values()) + vb
                if total > 0:
                    scale = 100.0 / total
                    base = {k: v * scale for k, v in base.items()}
                    vb = vb * scale
                    # 저장 형식은 원본 형태 유지(보너스 되돌려 넣음)
                    base['valuation_bonus'] = vb
                    self.weights = base
                console.print(f"✅ 투자 철학 프리셋 '{preset_name}' 적용 완료")
                console.print(f"   📊 새로운 가중치(보너스 포함 100%): {self.weights}")
            else:
                console.print(f"⚠️ 투자 철학 프리셋 '{preset_name}'을 찾을 수 없습니다. 기본값 사용.")
                
        except Exception as e:
            console.print(f"❌ 투자 철학 프리셋 적용 실패: {e}")

def analyze_single_stock_safe_enhanced(symbol: str, name: str,
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
    count: int = typer.Option(15, callback=_positive_int, help="분석할 종목 수"),
    display: int = typer.Option(10, callback=_positive_int, help="표시할 결과 수"),
    max_workers: int = typer.Option(2, callback=_positive_int, help="병렬 워커 수 (KIS TPS 고려해 2~4 권장)"),
    min_market_cap: float = typer.Option(500, callback=_positive_float, help="최소 시가총액(억원)"),
    min_score: float = typer.Option(50, callback=_positive_float, help="최소 향상 점수"),
    days_back: int = typer.Option(30, callback=_positive_int, help="투자의견 분석 기간(일)"),
    investment_philosophy: str = typer.Option("balanced", help="투자 철학 프리셋 (balanced, value_focused, growth_focused, consensus_focused, stability_focused)"),
    log_file: str = typer.Option(None, help="로그 파일 경로 (예: logs/test_analysis.log)"),
    log_level: str = typer.Option("INFO", help="로그 레벨 (DEBUG, INFO, WARNING, ERROR)")
):
    """향상된 통합 분석 시스템의 병렬 처리 테스트 (재무비율 분석 포함)"""
    
    # 로깅 설정 초기화
    if log_file:
        setup_logging(log_file, log_level)
        logger.info(f"🧪 향상된 병렬 분석 테스트 시작 - 로그 파일: {log_file}")
    else:
        logger.info("🧪 향상된 병렬 분석 테스트 시작")
    
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
    start_time = time.perf_counter()
    
    with Progress() as progress:
        task = progress.add_task("병렬 향상된 통합 분석 진행 중...", total=len(top_stocks))
        
        # ThreadPoolExecutor를 사용한 병렬 처리
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 각 종목에 대한 Future 생성
            future_to_stock = {}
            for stock in top_stocks:
                future = executor.submit(
                    analyze_single_stock_safe_enhanced,
                    stock['symbol'], stock['name'],
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
    
    end_time = time.perf_counter()
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
    avg_speed = (len(top_stocks)/total_time) if total_time > 0 else 0.0
    console.print(f"⚡ 평균 처리 속도: {avg_speed:.2f}종목/초")
    
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
    table.add_column("52주위치", style="green", width=9)
    
    for i, result in enumerate(filtered_results[:display], 1):
        financial_data = result.get('financial_data', {})
        current_price = result.get('current_price', 0)
        price_pos = result.get('price_position', None)
        
        
        table.add_row(
            str(i),
            result['symbol'],
            result['name'][:10] + "..." if len(result['name']) > 10 else result['name'],
            f"{current_price:,.0f}원" if current_price and current_price > 0 else "N/A",
            f"{result['market_cap']:,}억",
            f"{result['enhanced_score']:.1f}",
            result['enhanced_grade'],
            analyzer._fmt_pct(financial_data.get('roe')),
            analyzer._fmt_pct(financial_data.get('debt_ratio')),
            analyzer._fmt_pct(financial_data.get('net_profit_margin')),
            f"{price_pos:.1f}%" if isinstance(price_pos, (int,float)) else "N/A"
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
        
        # 52주 위치 및 리스크
        pp = result.get('price_position', None)
        rs = (result.get('risk_analysis', {}) or {}).get('risk_score', None)
        if pp is not None:
            console.print(f"  • 52주 위치: {pp:.1f}%")
        if rs is not None:
            console.print(f"  • 리스크 점수: {rs}")
        
        # 재무비율 상세
        financial_data = result.get('financial_data', {})
        if financial_data:
            console.print("💰 주요 재무비율:")
            console.print(f"  • ROE: {analyzer._fmt_pct(financial_data.get('roe'), assume_ratio_if_abs_lt_1=True)}")
            console.print(f"  • ROA: {analyzer._fmt_pct(financial_data.get('roa'), assume_ratio_if_abs_lt_1=True)}")
            console.print(f"  • 부채비율: {analyzer._fmt_pct(financial_data.get('debt_ratio'), assume_ratio_if_abs_lt_1=True)}")
            console.print(f"  • 순이익률: {analyzer._fmt_pct(financial_data.get('net_profit_margin'), assume_ratio_if_abs_lt_1=True)}")
            console.print(f"  • 유동비율: {analyzer._fmt_pct(financial_data.get('current_ratio'), assume_ratio_if_abs_lt_1=False)}")
            console.print(f"  • 매출 성장률: {analyzer._fmt_pct(financial_data.get('revenue_growth', financial_data.get('revenue_growth_rate')))}")
            
            # 결측 플래그 시각화
            missing = financial_data.get('__missing_flags__', {})
            if missing:
                miss_keys = [k for k, v in missing.items() if v]
                if miss_keys:
                    console.print(f"  • 데이터 결측: {', '.join(miss_keys)}")

@app.command()
def enhanced_top_picks(
    count: int = typer.Option(20, help="스크리닝할 종목 수 (기본값: 20개)"),
    min_score: float = typer.Option(60, help="최소 향상된 통합 점수 (기본값: 60점)"),
    max_picks: int = typer.Option(5, help="최대 추천 종목 수 (기본값: 5개)"),
    min_market_cap: float = typer.Option(1000, help="최소 시가총액 (억원, 기본값: 1000억원)"),
    days_back: int = typer.Option(30, help="투자의견 분석 기간 (일, 기본값: 30일)"),
    export_csv: bool = typer.Option(False, help="CSV 파일로 내보내기"),
    investment_philosophy: str = typer.Option("balanced", help="투자 철학 프리셋 (balanced, value_focused, growth_focused, consensus_focused, stability_focused)"),
    log_file: str = typer.Option(None, help="로그 파일 경로 (예: logs/analysis.log)"),
    log_level: str = typer.Option("INFO", help="로그 레벨 (DEBUG, INFO, WARNING, ERROR)")
):
    """향상된 통합 분석을 통한 최고 투자 후보 검색 (고급 재시도 로직 적용)"""
    
    # OptionInfo 객체 처리
    def safe_value(v, default):
        if hasattr(v, 'value'):
            return v.value
        elif hasattr(v, '__class__') and 'OptionInfo' in str(v.__class__):
            return default
        else:
            return v
    
    count = safe_value(count, 20)
    min_score = safe_value(min_score, 60)
    max_picks = safe_value(max_picks, 5)
    min_market_cap = safe_value(min_market_cap, 1000)
    days_back = safe_value(days_back, 30)
    export_csv = safe_value(export_csv, False)
    investment_philosophy = safe_value(investment_philosophy, "balanced")
    log_file = safe_value(log_file, None)
    log_level = safe_value(log_level, "INFO")
    
    # 로깅 설정 초기화
    if log_file:
        setup_logging(log_file, log_level)
        logger.info(f"🚀 향상된 통합 분석 시작 - 로그 파일: {log_file}")
    else:
        logger.info("🚀 향상된 통합 분석 시작")
    
    analyzer = EnhancedIntegratedAnalyzer()
    
    # 투자 철학 프리셋 적용
    if investment_philosophy != "balanced":
        analyzer._apply_investment_philosophy_preset(investment_philosophy)
    
    console.print(f"🚀 [bold]향상된 통합 분석 투자 후보 검색 (고급 재시도 로직 적용)[/bold]")
    console.print(f"📊 스크리닝 대상: 시가총액 상위 {count}개 종목")
    console.print(f"⚡ 분석 방식: 직렬 처리 (고급 재시도 로직으로 안정성 우선)")
    console.print(f"🎯 최소 향상된 통합 점수: {min_score}점")
    console.print(f"📈 최대 추천 종목: {max_picks}개")
    console.print(f"💰 최소 시가총액: {min_market_cap:,}억원")
    console.print(f"🎯 투자 철학: {investment_philosophy}")
    console.print(f"📈 분석 범위: 투자의견({analyzer.weights['opinion_analysis']}%) + 추정실적({analyzer.weights['estimate_analysis']}%) + 재무비율({analyzer.weights['financial_ratios']}%) + 성장성({analyzer.weights['growth_analysis']}%) + 규모({analyzer.weights['scale_analysis']}%)")
    console.print(f"🔄 재시도 로직: 재무비율(2회), 수익성비율(3회), 투자의견/추정실적/현재가(2회)")
    
    # 시가총액 상위 종목 가져오기
    top_stocks = analyzer.get_top_market_cap_stocks(count, min_market_cap)
    
    if not top_stocks:
        console.print("❌ 분석할 종목이 없습니다.")
        return
    
    # 배치 분석 수행 (요약 메트릭 포함)
    start_time = time.perf_counter()
    
    with Progress() as progress:
        task = progress.add_task("향상된 투자 후보 검색 중...", total=len(top_stocks))
        
        # analyze_batch 사용으로 요약 메트릭 자동 생성
        batch_results = analyzer.analyze_batch([(stock['symbol'], stock['name']) for stock in top_stocks], days_back=days_back)
        progress.update(task, completed=len(top_stocks))
        
        # 필터링 적용
        analysis_results = []
        for result in batch_results:
            if result.get('status') == 'success' and result.get('enhanced_score', 0) >= min_score:
                analysis_results.append(result)
    
    end_time = time.perf_counter()
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
    table.add_column("시가총액", style="blue", width=10)
    table.add_column("ROE", style="magenta", width=8)
    table.add_column("부채비율", style="red", width=10)
    table.add_column("순이익률", style="blue", width=10)
    table.add_column("매출성장률", style="green", width=10)
    table.add_column("52주위치", style="green", width=9)
    
    for i, pick in enumerate(top_picks, 1):
        financial_data = pick.get('financial_data', {})
        current_price = pick.get('current_price', 0)
        price_pos = pick.get('price_position', None)
        
        
        table.add_row(
            str(i),
            pick['symbol'],
            pick['name'][:10] + "..." if len(pick['name']) > 10 else pick['name'],
            f"{current_price:,.0f}원" if current_price and current_price > 0 else "N/A",
            f"{pick['enhanced_score']:.1f}",
            pick['enhanced_grade'],
            f"{pick['market_cap']:,}억",
            analyzer._fmt_pct(financial_data.get('roe')),
            analyzer._fmt_pct(financial_data.get('debt_ratio')),
            analyzer._fmt_pct(financial_data.get('net_profit_margin')),
            analyzer._fmt_pct(financial_data.get('revenue_growth', financial_data.get('revenue_growth_rate'))),
            f"{price_pos:.1f}%" if isinstance(price_pos, (int,float)) else "N/A"
        )
    
    console.print(table)
    
    # CSV 내보내기
    if export_csv:
        try:
            export_data = []
            for rank, pick in enumerate(top_picks, start=1):
                financial_data = pick.get('financial_data', {})
                breakdown = pick.get('score_breakdown', {})
                
                export_data.append({
                    'rank': rank,
                    'symbol': pick['symbol'],
                    'name': pick['name'],
                    'current_price': pick.get('current_price', 0),
                    'market_cap': pick['market_cap'],
                    'enhanced_score': pick['enhanced_score'],
                    'enhanced_grade': pick['enhanced_grade'],
                    'roe': financial_data.get('roe', 0),
                    'roa': financial_data.get('roa', 0),
                    'debt_ratio': float(financial_data.get('debt_ratio', 0) or 0),
                    'net_profit_margin': financial_data.get('net_profit_margin', 0),
                    'current_ratio': financial_data.get('current_ratio', 0),
                    'revenue_growth_rate': financial_data.get('revenue_growth', financial_data.get('revenue_growth_rate', 0)),
                    'price_position': pick.get('price_position', None),
                    'risk_score': (
                        None if (pick.get('risk_analysis', {}) or {}).get('risk_score') is None
                        else max(0.0, min(10.0, float((pick.get('risk_analysis', {}) or {}).get('risk_score') or 0)))
                    ),
                    'opinion_score': breakdown.get('투자의견', 0),
                    'estimate_score': breakdown.get('재무건전성', 0) + breakdown.get('밸류에이션', 0),
                    'financial_ratio_score': breakdown.get('재무비율', 0),
                    'growth_score': breakdown.get('성장성', 0),
                    'scale_score': breakdown.get('규모', 0)
                })
            
            df = pd.DataFrame(export_data)
            # CSV 포맷 일관화 (정수%로 저장)
            df['roe'] = df['roe'].apply(analyzer._as_pct_number).round(2)
            df['debt_ratio'] = df['debt_ratio'].apply(analyzer._as_pct_number).round(2)
            df['net_profit_margin'] = df['net_profit_margin'].apply(analyzer._as_pct_number).round(2)
            df['revenue_growth_rate'] = df['revenue_growth_rate'].apply(analyzer._as_pct_number).round(2)
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
    
    # 실제 계산용 가중치 표시 (보너스 포함)
    base_w, vb = analyzer._effective_weights()
    
    console.print("\n📊 [bold]분석 요소별 가중치 (실제 계산 반영)[/bold]")
    table = Table(title="가중치 설정")
    table.add_column("분석 요소", style="cyan")
    table.add_column("가중치", style="green", justify="right")
    table.add_column("설명", style="white")
    
    table.add_row("투자의견", f"{base_w.get('opinion_analysis', 0):.2f}%", "증권사 투자의견 및 컨센서스")
    table.add_row("추정실적", f"{base_w.get('estimate_analysis', 0):.2f}%", "미래 실적 전망 및 투자지표")
    table.add_row("재무비율", f"{base_w.get('financial_ratios', 0):.2f}%", "ROE, ROA, 부채비율, 순이익률, 유동비율")
    table.add_row("성장성", f"{base_w.get('growth_analysis', 0):.2f}%", "매출액/영업이익 성장률")
    table.add_row("규모", f"{base_w.get('scale_analysis', 0):.2f}%", "시가총액 기반 안정성")
    
    if vb > 0:
        table.add_row("저평가 보너스", f"{vb:.2f}%", "PER/PBR/ROE-대비-PER 보너스")
    
    console.print(table)
    
    # 합계 표시 (가독성 향상)
    sum_base = sum(base_w.values())
    total_with_bonus = sum_base + vb
    console.print(f"\n합계(보너스 포함): {total_with_bonus:.2f}%  "
                  f"[dim](기본:{sum_base:.2f}% + 보너스:{vb:.2f}%)[/dim]")
    
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
    
    # 등급을 A+ → A → B+ → B → C+ → C → D 순으로 정렬
    label_map = {
        "A_plus": "A+", "A": "A", "B_plus": "B+", "B": "B",
        "C_plus": "C+", "C": "C", "D": "D", "F": "F"
    }
    grade_order = ['A_plus', 'A', 'B_plus', 'B', 'C_plus', 'C', 'D']
    for grade in grade_order:
        if grade in analyzer.grade_thresholds:
            threshold = analyzer.grade_thresholds[grade]
            grade_table.add_row(label_map[grade], f"{threshold}점 이상")
    
    # F 기준은 최저 등급으로 안내(일관성 유지)
    try:
        others = [v for k, v in analyzer.grade_thresholds.items() if k != 'F']
        f_max = min(others) if others else 0
        f_min = analyzer.grade_thresholds.get('F', 0)
        if others:
            grade_table.add_row("F", f"{f_min}점 이상 ~ {f_max}점 미만")
        else:
            grade_table.add_row("F", f"{f_min}점 이상 (다른 등급 설정 없음)")
    except Exception:
        grade_table.add_row("F", f"{analyzer.grade_thresholds.get('F', 0)}점 이상")
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

@app.command()
def run_backtest(
    symbols: str = typer.Option("005930,000660,035420,051910,006400", help="백테스팅할 종목 코드 (쉼표로 구분)"),
    start_date: str = typer.Option("2023-01-01", help="시작 날짜 (YYYY-MM-DD)"),
    end_date: str = typer.Option("2024-12-31", help="종료 날짜 (YYYY-MM-DD)"),
    rebalance_frequency: str = typer.Option("monthly", help="리밸런싱 주기 (monthly, quarterly)"),
    initial_capital: float = typer.Option(10000000, help="초기 자본 (원)"),
    log_file: str = typer.Option(None, help="로그 파일 경로"),
    log_level: str = typer.Option("INFO", help="로그 레벨")
):
    """백테스팅 실행"""
    
    # 로깅 설정
    if log_file:
        setup_logging(log_file, log_level)
        logger.info(f"백테스팅 시작 - 로그 파일: {log_file}")
    else:
        logger.info("백테스팅 시작")
    
    # 종목 리스트 파싱
    symbol_list = [s.strip() for s in symbols.split(",")]
    
    # 백테스팅 엔진 초기화
    from backtesting_engine import BacktestingEngine
    engine = BacktestingEngine()
    analyzer = EnhancedIntegratedAnalyzer()
    engine.initialize(analyzer.provider)
    
    # 백테스팅 실행
    result = engine.run_backtest(
        symbols=symbol_list,
        start_date=start_date,
        end_date=end_date,
        rebalance_frequency=rebalance_frequency,
        initial_capital=initial_capital
    )
    
    # 결과 표시
    engine.display_results(result)
    
    # 결과 저장
    try:
        import json
        from datetime import datetime
        
        result_data = {
            'total_return': result.total_return,
            'annualized_return': result.annualized_return,
            'sharpe_ratio': result.sharpe_ratio,
            'max_drawdown': result.max_drawdown,
            'win_rate': result.win_rate,
            'profit_factor': result.profit_factor,
            'parameters': result.parameters,
            'timestamp': datetime.now().isoformat()
        }
        
        filename = f"backtest_result_{int(time.time())}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        console.print(f"\n💾 백테스팅 결과가 {filename}에 저장되었습니다.")
        
    except Exception as e:
        console.print(f"[red]❌ 결과 저장 실패: {e}[/red]")

@app.command()
def optimize_parameters(
    symbols: str = typer.Option("005930,000660,035420,051910,006400", help="최적화할 종목 코드 (쉼표로 구분)"),
    start_date: str = typer.Option("2023-01-01", help="시작 날짜 (YYYY-MM-DD)"),
    end_date: str = typer.Option("2024-12-31", help="종료 날짜 (YYYY-MM-DD)"),
    optimization_method: str = typer.Option("grid_search", help="최적화 방법 (grid_search, random_search)"),
    max_iterations: int = typer.Option(50, help="최대 반복 횟수"),
    log_file: str = typer.Option(None, help="로그 파일 경로"),
    log_level: str = typer.Option("INFO", help="로그 레벨")
):
    """파라미터 최적화 실행"""
    
    # 로깅 설정
    if log_file:
        setup_logging(log_file, log_level)
        logger.info(f"파라미터 최적화 시작 - 로그 파일: {log_file}")
    else:
        logger.info("파라미터 최적화 시작")
    
    # 종목 리스트 파싱
    symbol_list = [s.strip() for s in symbols.split(",")]
    
    # 백테스팅 엔진 초기화
    from backtesting_engine import BacktestingEngine, ParameterOptimizer
    engine = BacktestingEngine()
    analyzer = EnhancedIntegratedAnalyzer()
    engine.initialize(analyzer.provider)
    
    # 최적화 실행
    optimizer = ParameterOptimizer(engine)
    optimal_params = optimizer.optimize_parameters(
        symbols=symbol_list,
        start_date=start_date,
        end_date=end_date,
        optimization_method=optimization_method,
        max_iterations=max_iterations
    )
    
    # 최적 파라미터 표시
    console.print("\n🎯 [bold]최적화된 파라미터[/bold]")
    
    param_table = Table(title="최적 파라미터")
    param_table.add_column("구분", style="cyan")
    param_table.add_column("값", style="green")
    
    for category, params in optimal_params.items():
        if isinstance(params, dict):
            for key, value in params.items():
                param_table.add_row(f"{category}.{key}", str(value))
        else:
            param_table.add_row(category, str(params))
    
    console.print(param_table)
    
    # 최적 파라미터로 백테스팅 실행
    console.print("\n🚀 [bold]최적 파라미터로 백테스팅 실행[/bold]")
    result = engine.run_backtest(
        symbols=symbol_list,
        start_date=start_date,
        end_date=end_date,
        parameters=optimal_params
    )
    
    engine.display_results(result)
    
    # 최적 파라미터 저장
    try:
        import json
        from datetime import datetime
        
        optimization_data = {
            'optimal_parameters': optimal_params,
            'backtest_result': {
                'total_return': result.total_return,
                'annualized_return': result.annualized_return,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown': result.max_drawdown,
                'win_rate': result.win_rate,
                'profit_factor': result.profit_factor
            },
            'optimization_settings': {
                'method': optimization_method,
                'max_iterations': max_iterations,
                'symbols': symbol_list,
                'start_date': start_date,
                'end_date': end_date
            },
            'timestamp': datetime.now().isoformat()
        }
        
        filename = f"optimization_result_{int(time.time())}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(optimization_data, f, ensure_ascii=False, indent=2)
        
        console.print(f"\n💾 최적화 결과가 {filename}에 저장되었습니다.")
        
    except Exception as e:
        console.print(f"[red]❌ 결과 저장 실패: {e}[/red]")

@app.command()
def compare_strategies(
    symbols: str = typer.Option("005930,000660,035420,051910,006400", help="비교할 종목 코드 (쉼표로 구분)"),
    start_date: str = typer.Option("2023-01-01", help="시작 날짜 (YYYY-MM-DD)"),
    end_date: str = typer.Option("2024-12-31", help="종료 날짜 (YYYY-MM-DD)"),
    strategies: str = typer.Option("balanced,value_focused,growth_focused", help="비교할 전략들 (쉼표로 구분)"),
    log_file: str = typer.Option(None, help="로그 파일 경로"),
    log_level: str = typer.Option("INFO", help="로그 레벨")
):
    """여러 전략 비교"""
    
    # 로깅 설정
    if log_file:
        setup_logging(log_file, log_level)
        logger.info(f"전략 비교 시작 - 로그 파일: {log_file}")
    else:
        logger.info("전략 비교 시작")
    
    # 종목 리스트 파싱
    symbol_list = [s.strip() for s in symbols.split(",")]
    strategy_list = [s.strip() for s in strategies.split(",")]
    
    # 백테스팅 엔진 초기화
    from backtesting_engine import BacktestingEngine
    engine = BacktestingEngine()
    analyzer = EnhancedIntegratedAnalyzer()
    engine.initialize(analyzer.provider)
    
    # 각 전략별 백테스팅 실행
    results = {}
    
    for strategy in strategy_list:
        console.print(f"\n📊 [bold]{strategy} 전략 백테스팅[/bold]")
        
        # 전략별 파라미터 적용
        analyzer._apply_investment_philosophy_preset(strategy)
        strategy_params = {
            'weights': analyzer.weights,
            'financial_ratio_weights': analyzer.financial_ratio_weights,
            'grade_thresholds': analyzer.grade_thresholds
        }
        
        # 백테스팅 실행
        result = engine.run_backtest(
            symbols=symbol_list,
            start_date=start_date,
            end_date=end_date,
            parameters=strategy_params
        )
        
        results[strategy] = result
    
    # 비교 결과 표시
    console.print("\n🏆 [bold]전략 비교 결과[/bold]")
    
    comparison_table = Table(title="전략별 성과 비교")
    comparison_table.add_column("전략", style="cyan")
    comparison_table.add_column("총 수익률", style="green", justify="right")
    comparison_table.add_column("연평균 수익률", style="green", justify="right")
    comparison_table.add_column("샤프 비율", style="yellow", justify="right")
    comparison_table.add_column("최대 낙폭", style="red", justify="right")
    comparison_table.add_column("승률", style="blue", justify="right")
    
    for strategy, result in results.items():
        comparison_table.add_row(
            strategy,
            f"{result.total_return:.2%}",
            f"{result.annualized_return:.2%}",
            f"{result.sharpe_ratio:.2f}",
            f"{result.max_drawdown:.2%}",
            f"{result.win_rate:.2%}"
        )
    
    console.print(comparison_table)
    
    # 최고 성과 전략 찾기
    best_strategy = max(results.keys(), key=lambda s: results[s].sharpe_ratio)
    console.print(f"\n🥇 [bold green]최고 성과 전략: {best_strategy}[/bold green]")
    console.print(f"   샤프 비율: {results[best_strategy].sharpe_ratio:.2f}")
    console.print(f"   총 수익률: {results[best_strategy].total_return:.2%}")

if __name__ == "__main__":
    app()
