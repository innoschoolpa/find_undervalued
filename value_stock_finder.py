#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
저평가 가치주 발굴 시스템
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import logging
import concurrent.futures
import threading
import time
from functools import lru_cache
from typing import Any, Dict, Optional
import os
import math
import statistics
from collections import Counter
import textwrap  # ✅ 에러 메시지 길이 제한용

from financial_data_provider import FinancialDataProvider
from sector_contextualizer import SectorCycleContextualizer
from sector_utils import get_sector_benchmarks

# Streamlit 페이지 설정 (최상단에서 한 번만)
st.set_page_config(
    page_title="저평가 가치주 발굴 시스템",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ✅ 로깅 설정 (중복 방지 + 환경변수 레벨 제어)
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
_logger = logging.getLogger(__name__)
if not _logger.handlers:  # 핸들러 중복 추가 방지
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format='%(levelname)s:%(name)s:%(message)s'
    )
logger = _logger

# ✅ Streamlit ScriptRunContext 경고 숨기기 (ChatGPT 권장)
logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)

# ✅ MCP 통합 모듈 (임포트 로그 중복 방지)
_mcp_import_logged = False
try:
    from mcp_kis_integration import MCPKISIntegration
    MCP_AVAILABLE = True
    if not _mcp_import_logged:
        logger.info("MCP 모듈 로드 성공")
        _mcp_import_logged = True
except ImportError as e:
    if not _mcp_import_logged:
        logger.warning(f"MCP 모듈 로드 실패: {e}")
        _mcp_import_logged = True
    MCP_AVAILABLE = False

@st.cache_resource
def _get_analyzer():
    """분석기 캐시 (재실행 비용 절감)"""
    logger.info("✅ 분석기 초기화 (최초 1회만)")
    from enhanced_integrated_analyzer_refactored import EnhancedIntegratedAnalyzer
    return EnhancedIntegratedAnalyzer()

@st.cache_resource
def _get_mcp_integration():
    """MCP 통합 모듈 캐시 (ChatGPT 권장 - 중복 초기화 방지)"""
    if not MCP_AVAILABLE:
        return None
    logger.info("✅ MCP 통합 모듈 초기화 (최초 1회만)")
    return MCPKISIntegration(oauth_manager=None)

@st.cache_data(ttl=300)  # 5분 TTL
def _cached_universe_from_api(max_count: int):
    """유니버스 API 캐시 (재실행 비용 절감)"""
    try:
        from kis_data_provider import KISDataProvider
        kis = KISDataProvider()
        stocks = kis.get_kospi_stock_list(max_count)
        if stocks and len(stocks) > 0:
            # 시가총액순으로 정렬하고 지정된 개수만큼 선택
            sorted_stocks = sorted(stocks, key=lambda x: x.get('market_cap', 0), reverse=True)
            
            # ✅ 전체 데이터를 딕셔너리로 변환 (중복 API 호출 방지!)
            # 기존: {코드: 종목명} → 현재가 등을 다시 조회해야 함
            # 개선: {코드: 전체데이터} → 재조회 불필요
            stock_universe = {}
            for stock in sorted_stocks[:max_count]:
                if 'code' in stock:
                    # 전체 데이터 저장 (코드만 키로 사용, 나머지는 값으로)
                    stock_universe[stock['code']] = stock
            
            return stock_universe, True
        else:
            return None, False
    except Exception as e:
        logger.error(f"API 종목 리스트 조회 실패: {e}")
        return None, False

class TokenBucket:
    """API 호출 한도 관리를 위한 토큰버킷"""
    
    def __init__(self, rate_per_sec: float, capacity: int):
        self.rate = rate_per_sec
        self.capacity = capacity
        self.tokens = capacity
        self.ts = time.monotonic()
        self.lock = threading.Lock()
    
    def take(self, n: int = 1, timeout: float = 10.0) -> bool:
        """토큰 n개 소비 (반복문으로 대기, 타임아웃 포함)"""
        deadline = time.monotonic() + timeout if timeout else None
        while True:
            with self.lock:
                now = time.monotonic()
                self.tokens = min(self.capacity, self.tokens + (now - self.ts) * self.rate)
                self.ts = now
                if self.tokens >= n:
                    self.tokens -= n
                    return True
                need = n - self.tokens
                sleep_time = max(0.0, need / self.rate)
            if deadline and time.monotonic() + sleep_time > deadline:
                return False
            time.sleep(sleep_time)

class ValueStockFinder:
    """저평가 가치주 발굴 시스템"""
    
    # UI 업데이트 상수
    UI_UPDATE_INTERVAL = 0.25  # 초 단위
    
    # 블랙리스트 상수 (단일화)
    # ✅ 047050 제거 (포스코인터내셔널 - 폴백 리스트에 포함)
    BAD_CODES = {'068290'}
    
    # 미리보기 샘플 크기 상수
    SAMPLE_PREVIEW_SIZE = 20
    
    def __init__(self):
        # KIS OAuth 매니저 초기화 (config.yaml에서 설정 로드)
        import yaml
        try:
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                kis_config = config.get('kis_api', {})
        except Exception as e:
            logger.warning(f"config.yaml 로드 실패: {e}")
            kis_config = {}
        
        # KISOAuthManager는 이 파일 하단에 정의될 예정이므로,
        # 간단한 OAuth 매니저 클래스를 여기서 생성
        class SimpleOAuthManager:
            def __init__(self, appkey, appsecret, is_test=False):
                self.appkey = appkey
                self.appsecret = appsecret
                self.is_test = is_test
                self.base_url = ("https://openapivts.koreainvestment.com:29443" if is_test 
                                else "https://openapi.koreainvestment.com:9443")
                self._rest_token = None
                
            def get_rest_token(self):
                # ✅ 토큰 캐시에서 로드 + 만료 가드 (크리티컬 - 실패 루프 방지)
                import json
                import time
                try:
                    with open('.kis_token_cache.json', 'r') as f:
                        cache = json.load(f)
                    token = cache.get('token')
                    exp = cache.get('expires_at')  # epoch sec
                    # 만료 60초 전부터 무효화하여 상위 레이어에서 재발급 트리거
                    if not token or (exp and time.time() > exp - 60):
                        return None
                    return token
                except:
                    return None
        
        self.oauth_manager = SimpleOAuthManager(
            appkey=kis_config.get('app_key', ''),
            appsecret=kis_config.get('app_secret', ''),
            is_test=kis_config.get('test_mode', False)
        )
        
        # MCP KIS 통합 초기화 (캐싱으로 중복 방지)
        self.mcp_integration = self._get_mcp_integration()
        
        # 가치주 평가 기준 (업종별 동적 기준으로 대체)
        self.default_value_criteria = {
            'per_max': 15.0,      # PER 15배 이하 (기본값)
            'pbr_max': 1.5,       # PBR 1.5배 이하 (기본값)
            'roe_min': 10.0,      # ROE 10% 이상 (기본값)
            'dividend_min': 2.0,  # 배당수익률 2% 이상
            'debt_ratio_max': 50.0,  # 부채비율 50% 이하
            'current_ratio_min': 100.0  # 유동비율 100% 이상
        }

        # 섹터 데이터 제공자 및 맥락화 도구 초기화
        self.data_provider = FinancialDataProvider()
        self.sector_context = SectorCycleContextualizer()
        self._analyzer = None
        self._last_api_success = False  # API 성공 여부 추적
        
        # API 호출 한도 관리 (초당 2회, 최대 10개 토큰)
        self.rate_limiter = TokenBucket(rate_per_sec=2.0, capacity=10)
        
        # 스레드 안전성을 위한 락 (부분 동시성 허용)
        self._analyzer_sem = threading.BoundedSemaphore(3)  # 최대 3개 동시 분석
        self._analyzer_init_lock = threading.Lock()  # analyzer 초기화용
        
        # 프라임 캐시 안전 가드
        self._primed_cache = {}
        
        # 실패 캐시 (한 번 실패한 코드는 다음 실행에서 제외) - TTL 및 크기 제한 관리
        self._failed_codes = set()
        self._failed_codes_ttl = {}  # code -> last_failed_ts
        self._failed_codes_max = 500
        self._failed_codes_ttl_sec = 1800  # 30분
        self._failed_lock = threading.Lock()  # 🔒 멀티스레드 안전성

    def _gc_failed_codes(self):
        """실패 캐시 가비지 컬렉션 (TTL 만료 및 크기 제한)"""
        now = time.time()
        with self._failed_lock:  # 🔒 멀티스레드 보호
            # TTL 만료
            for code, ts in list(self._failed_codes_ttl.items()):
                if now - ts > self._failed_codes_ttl_sec:
                    self._failed_codes_ttl.pop(code, None)
                    self._failed_codes.discard(code)
            # 크기 제한
            if len(self._failed_codes) > self._failed_codes_max:
                # 오래된 것부터 제거
                for code, _ in sorted(self._failed_codes_ttl.items(), key=lambda x: x[1])[:len(self._failed_codes)-self._failed_codes_max]:
                    self._failed_codes_ttl.pop(code, None)
                    self._failed_codes.discard(code)

    def _get_mcp_integration(self):
        """MCP 통합 초기화 (중복 방지, ChatGPT 권장 - 전역 캐시 사용)"""
        # ✅ 전역 싱글톤 사용 (중복 초기화 완전 제거)
        return _get_mcp_integration()
    
    @property
    def analyzer(self):
        if self._analyzer is None:
            with self._analyzer_init_lock:
                if self._analyzer is None:  # double-check locking
                    self._analyzer = _get_analyzer()
        return self._analyzer
    
    def get_sector_specific_criteria(self, sector: str) -> Dict[str, float]:
        """업종별 가치주 평가 기준 반환"""
        # sector_utils.py의 벤치마크를 기반으로 한 업종별 기준
        sector_criteria = {
            '금융업': {
                'per_max': 12.0,    # 금융업은 낮은 PER 선호
                'pbr_max': 1.2,     # 낮은 PBR
                'roe_min': 12.0,    # 높은 ROE 요구
                'dividend_min': 3.0,  # 높은 배당
                'debt_ratio_max': 90.0,  # 금융업은 부채비율이 높을 수 있음
                'current_ratio_min': 80.0
            },
            '기술업': {
                'per_max': 25.0,    # 기술주는 높은 PER 허용
                'pbr_max': 3.0,     # 높은 PBR 허용
                'roe_min': 15.0,    # 높은 ROE 요구
                'dividend_min': 1.0,  # 배당 요구 낮음
                'debt_ratio_max': 40.0,
                'current_ratio_min': 120.0
            },
            '제조업': {
                'per_max': 18.0,    # 적정 PER
                'pbr_max': 2.0,     # 적정 PBR
                'roe_min': 10.0,    # 표준 ROE
                'dividend_min': 2.0,
                'debt_ratio_max': 50.0,
                'current_ratio_min': 100.0
            },
            '바이오/제약': {
                'per_max': 50.0,    # 바이오는 매우 높은 PER 허용
                'pbr_max': 5.0,     # 높은 PBR 허용
                'roe_min': 8.0,     # ROE 요구 낮음 (투자 단계)
                'dividend_min': 0.5,  # 배당 거의 없음
                'debt_ratio_max': 30.0,
                'current_ratio_min': 150.0
            },
            '에너지/화학': {
                'per_max': 15.0,    # 사이클 특성 고려
                'pbr_max': 1.8,     # 적정 PBR
                'roe_min': 8.0,     # 사이클로 인한 낮은 ROE
                'dividend_min': 2.5,
                'debt_ratio_max': 45.0,
                'current_ratio_min': 110.0
            },
            '소비재': {
                'per_max': 20.0,    # 안정적 PER
                'pbr_max': 2.5,     # 적정 PBR
                'roe_min': 12.0,    # 안정적 ROE
                'dividend_min': 2.0,
                'debt_ratio_max': 40.0,
                'current_ratio_min': 120.0
            },
            '통신업': {
                'per_max': 15.0,    # 안정적 PER
                'pbr_max': 2.0,     # 적정 PBR
                'roe_min': 8.0,     # 안정적 ROE
                'dividend_min': 3.0,  # 높은 배당
                'debt_ratio_max': 60.0,  # 높은 부채 허용
                'current_ratio_min': 90.0
            },
            '건설업': {
                'per_max': 12.0,    # 보수적 PER
                'pbr_max': 1.5,     # 보수적 PBR
                'roe_min': 8.0,     # 사이클 특성
                'dividend_min': 2.5,
                'debt_ratio_max': 55.0,
                'current_ratio_min': 110.0
            }
        }
        
        # 정규화된 섹터명 사용
        normalized_sector = self._normalize_sector_name(sector)
        return sector_criteria.get(normalized_sector, self.default_value_criteria)
    
    def _normalize_sector_name(self, sector: str) -> str:
        """섹터명 정규화 (공백/구분점 제거 + 다국어/동의어 매핑)"""
        if not sector:
            return '기타'
        s = str(sector).strip().lower()

        # 1) 전처리: 내부 공백/중점 제거, 한글 '·' 포함 각종 구분자 제거
        for ch in [' ', '·', '.', '/', '\\', '-', '_']:
            s = s.replace(ch, '')
        # 2) 대표 키워드 치환 (흔한 변형 흡수)
        s = (s
             .replace('전기전자', '전기전자')
             .replace('it서비스', 'it')
             .replace('정보기술', 'it')
             .replace('통신서비스', '통신')
             .replace('운송장비부품', '운송장비'))

        # 3) 규칙 기반 매핑
        rules = [
            (['금융','은행','증권','보험'], '금융업'),
            (['it','아이티','기술','반도체','전자','소프트웨어','인터넷'], '기술업'),
            (['제조','자동차','완성차','기계','산업재'], '제조업'),
            (['바이오','제약','의료','헬스케어'], '바이오/제약'),
            (['에너지','화학','석유','정유'], '에너지/화학'),
            (['소비','유통','식품','리테일'], '소비재'),
            (['통신','텔레콤'], '통신업'),
            (['건설','부동산','디벨로퍼'], '건설업'),
            (['전기전자'], '전기전자'),   # 세부 섹터를 그대로 인정
            (['운송장비'], '운송장비'),
            (['운송','해운','항공'], '운송'),
        ]
        for kws, label in rules:
            if any(k in s for k in kws):
                return label
        return '기타'
    
    def _get_sector_criteria_display(self, sector_name: str) -> str:
        """업종별 기준을 간단한 문자열로 표시"""
        c = self.get_sector_specific_criteria(sector_name) or self.default_value_criteria
        per = self._safe_num(c.get('per_max'), 0)
        pbr = self._safe_num(c.get('pbr_max'), 1)
        roe = self._safe_num(c.get('roe_min'), 0)
        return f"PER≤{per}, PBR≤{pbr}, ROE≥{roe}%"
    
    def is_value_stock_unified(self, stock_data: Dict[str, Any], options: Dict[str, Any]) -> bool:
        """✅ 가치주 판단 로직 통일 (업종별 기준 완화)"""
        # 업종별 가치주 기준 체크
        sector_name = stock_data.get('sector_name', stock_data.get('sector', ''))
        criteria = self.get_sector_specific_criteria(sector_name)
        
        per = stock_data.get('per', 0)
        pbr = stock_data.get('pbr', 0)
        roe = stock_data.get('roe', 0)
        value_score = stock_data.get('value_score', 0)
        
        per_ok = per <= criteria['per_max'] if per > 0 else False
        pbr_ok = pbr <= criteria['pbr_max'] if pbr > 0 else False
        roe_ok = roe >= criteria['roe_min'] if roe > 0 else False
        
        # ✅ 업종별 기준 3개 모두 충족 + 점수 50점 이상 (완화)
        criteria_met_count = sum([per_ok, pbr_ok, roe_ok])
        score_threshold = 50.0 if criteria_met_count == 3 else 60.0  # 3개 충족 시 50점, 아니면 60점
        
        return criteria_met_count == 3 and value_score >= score_threshold
        
    def format_pct_or_na(self, value: Optional[float], precision: int = 1) -> str:
        """퍼센트 값 포맷팅 (None/NaN일 경우 N/A)"""
        return "N/A" if value is None or not isinstance(value, (int, float)) or not math.isfinite(value) else f"{value:.{precision}f}%"
    
    def format_percentile(self, percentile: Optional[float], cap: float = 99.5) -> str:
        """백분위(높을수록 좋음) 그대로 표시 - 사용자 설정 상한 적용"""
        return "N/A" if percentile is None else f"{min(cap, percentile):.1f}%"
    
    def _safe_num(self, x, d=1, default='N/A'):
        """안전한 숫자 포맷팅"""
        try:
            return f"{float(x):.{d}f}"
        except Exception:
            return default
    
    def _pos_or_none(self, x):
        """양수만 반환, 0/음수/NaN은 None (사용자 권장 - 완전 가드)"""
        try:
            x = float(x)
            return x if (math.isfinite(x) and x > 0) else None
        except Exception:
            return None
    
    def fmt_ratio(self, x, unit="", nd=2, na="N/A"):
        """✅ 숫자 포맷 공용 헬퍼 (크리티컬 - None/NaN 방어)"""
        if not isinstance(x, (int, float)) or not math.isfinite(x):
            return na
        return f"{x:.{nd}f}{unit}"
    
    def _relative_vs_median(self, value: float, p50: Optional[float]) -> Optional[float]:
        """섹터 중앙값 대비 상대치 계산"""
        if value is None or p50 in (None, 0) or value <= 0:
            return None
        return (value / p50 - 1.0) * 100.0
    
    def _normalize_sector_key(self, sector_name: str) -> str:
        """캐시 키용 표면 정규화"""
        return (sector_name or '기타').strip() or '기타'
    
    def refresh_sector_stats_and_clear_cache(self, stocks):
        """섹터 통계 갱신 및 캐시 클리어 헬퍼"""
        self.data_provider.refresh_sector_statistics(stocks)
        self._cached_sector_data.cache_clear()
    
    def _percentile_from_breakpoints(self, value: float, p: Dict[str, float]) -> Optional[float]:
        """
        p10, p25, p50, p75, p90 일부가 없을 때 정규분포 근사로 p10/p90을 추정하고,
        선형 보간으로 0~100% 퍼센타일을 계산한다.
        - 적응형 tail_z: IQR이 좁을수록 꼬리를 더 벌림 (최대 1.96)
        - 단조성/경계값 안전장치 포함
        """
        # ✅ 입력값 안전장치 강화 (사용자 권장 - NaN/음수/None 조기 리턴)
        if value is None or not isinstance(value, (int, float)) or not math.isfinite(value):
            return None
        if not p:
            return None
        p25, p50, p75 = p.get("p25"), p.get("p50"), p.get("p75")
        # ✅ 퍼센타일 값도 finite 체크
        if not all(isinstance(x, (int, float)) and math.isfinite(x) for x in (p25, p50, p75)):
            return None

        p10 = p.get("p10")
        p90 = p.get("p90")

        # --- 적응형 tail z 계산: IQR이 좁을수록 z를 키움 (최대 1.96)
        iqr = max(1e-9, (p75 - p25))
        spread_ratio = iqr / max(1e-6, abs(p50))  # 분포가 중앙값 대비 얼마나 퍼져있는가
        # spread_ratio가 작을수록 꼬리를 더 멀리(=z↑). 0.05 이하일 때 1.96, 0.30 이상이면 1.2816.
        def map_ratio_to_z(r):
            lo_r, hi_r = 0.05, 0.30
            lo_z, hi_z = 1.96, 1.2816
            if r <= lo_r: return lo_z
            if r >= hi_r: return hi_z
            t = (r - lo_r) / (hi_r - lo_r)
            return lo_z + (hi_z - lo_z) * t
        tail_z = map_ratio_to_z(spread_ratio)

        if p10 is None or p90 is None:
            sigma = iqr / 1.349
            est_p10 = p50 - tail_z * sigma
            est_p90 = p50 + tail_z * sigma
            if p10 is None: p10 = est_p10
            if p90 is None: p90 = est_p90

        eps = 1e-9
        p25 = min(p25, p50 - eps); p10 = min(p10, p25 - eps)
        p75 = max(p75, p50 + eps); p90 = max(p90, p75 + eps)

        def lin(a,b,ya,yb,x):
            if b <= a: return ya
            t = max(0.0, min(1.0, (x-a)/(b-a)))
            return ya + (yb-ya)*t

        if value <= p10: return 0.0
        if value >= p90: return 100.0
        if value <= p25: return lin(p10,p25,10.0,25.0,value)
        if value <= p50: return lin(p25,p50,25.0,50.0,value)
        if value <= p75: return lin(p50,p75,50.0,75.0,value)
        return lin(p75,p90,75.0,90.0,value)

    
    def _percentile_or_range_score(self, value, percentiles, rng, higher_is_better, cap=25.0, percentile_cap=99.5):
        """
        percentiles가 없으면 range 기반 정규화로 대체
        """
        if percentiles:
            pct = self._percentile_from_breakpoints(value, percentiles)
            if pct is not None:
                pct = min(percentile_cap, pct)  # 사용자 설정 상한 적용
                if not higher_is_better:
                    pct = 100.0 - pct
                return max(0.0, min(cap, cap * (pct/100.0)))

        # 🔁 fallback: 범위 정규화
        lo, hi = (rng or (0.0, 1.0))
        if hi == lo:
            logger.debug(f"Range fallback: lo=hi={lo}, value={value}")
            return 0.0
        t = (value - lo) / (hi - lo)
        t = 1.0 - max(0.0, min(1.0, t)) if not higher_is_better else max(0.0, min(1.0, t))
        return cap * t
    
    @lru_cache(maxsize=256)
    def _cached_sector_data(self, sector_name: str):
        """섹터 데이터와 벤치마크를 캐시하여 API 부담 감소"""
        # 의미 정규화(매핑) 후, 키 정규화
        normalized = self._normalize_sector_key(self._normalize_sector_name(sector_name))
        stats = self.data_provider.get_sector_data(normalized)
        bench = get_sector_benchmarks(normalized, None, stats)
        return stats, bench

    def _augment_sector_data(self, symbol: str, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """섹터 평균 및 상대 지표 계산"""
        raw_sector = (
            stock_data.get('sector')
            or stock_data.get('sector_analysis', {}).get('sector_name', '')
            or stock_data.get('industry', '')
        )
        sector_name = self._normalize_sector_name(raw_sector)   # ← 정규화 강제
        sector_stats, benchmarks = self._cached_sector_data(sector_name)
        
        # 🔍 빠른 체크 포인트(로그) - 간소화 (사용자 권장)
        # DEBUG 모드에서만 상세 출력, 운영 모드에서는 요약만
        log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
        if log_level == 'DEBUG':
            logger.debug(f"[SECTOR] {symbol} {stock_data.get('name', '')} raw='{raw_sector}' -> norm='{sector_name}', "
                        f"sample={sector_stats.get('sample_size') if sector_stats else 0}")
        # INFO 레벨에서는 로그 생략 (과도한 출력 방지)

        per = stock_data.get('per') or 0
        pbr = stock_data.get('pbr') or 0
        roe = stock_data.get('roe') or 0

        per_percentiles = sector_stats.get('per_percentiles', {}) if sector_stats else {}
        pbr_percentiles = sector_stats.get('pbr_percentiles', {}) if sector_stats else {}
        roe_percentiles = sector_stats.get('roe_percentiles', {}) if sector_stats else {}

        # 섹터 중앙값 대비 상대치 계산 (가드 포함)
        per_p50 = per_percentiles.get('p50')
        pbr_p50 = pbr_percentiles.get('p50')
        
        relative_per = self._relative_vs_median(per, per_p50)
        relative_pbr = self._relative_vs_median(pbr, pbr_p50)


        roe_percentile = self._percentile_from_breakpoints(roe, roe_percentiles)

        return {
            'symbol': symbol,
            'sector_name': sector_name,
            'sector_benchmarks': benchmarks,
            'sector_stats': sector_stats,
            'relative_per': relative_per,
            'relative_pbr': relative_pbr,
            'sector_percentile': roe_percentile
        }

    def _evaluate_sector_adjusted_metrics(self, stock_data: Dict[str, Any], percentile_cap: float = 99.5) -> Dict[str, Any]:
        stats = stock_data.get('sector_stats', {}) or {}
        benchmarks = stock_data.get('sector_benchmarks') or get_sector_benchmarks(stock_data.get('sector_name', '기타'), None, stats)

        per = stock_data.get('per') or 0
        pbr = stock_data.get('pbr') or 0
        roe = stock_data.get('roe') or 0

        # 퍼센타일 기반 스코어링 (PER/PBR/ROE 통일) + fallback
        per_percentiles = stats.get('per_percentiles', {}) if stats else {}
        pbr_percentiles = stats.get('pbr_percentiles', {}) if stats else {}
        roe_percentiles = stats.get('roe_percentiles', {}) if stats else {}
        
        per_range = benchmarks.get('per_range', (5, 20))
        pbr_range = benchmarks.get('pbr_range', (0.5, 2.0))
        roe_range = benchmarks.get('roe_range', (5, 20))

        # 음수/0 PER → 스코어 0, relative=None
        per_val = stock_data.get('per') or 0.0
        pbr_val = stock_data.get('pbr') or 0.0
        roe_val = stock_data.get('roe') or 0.0

        per_raw = 0.0 if per_val <= 0 else self._percentile_or_range_score(per_val, per_percentiles, per_range, higher_is_better=False, percentile_cap=percentile_cap)
        pbr_raw = self._percentile_or_range_score(pbr_val, pbr_percentiles, pbr_range, higher_is_better=False, percentile_cap=percentile_cap)
        roe_raw = self._percentile_or_range_score(roe_val, roe_percentiles, roe_range, higher_is_better=True, percentile_cap=percentile_cap)

        raw_total = per_raw + pbr_raw + roe_raw

        sector_data_for_context = {
            'sample_size': stats.get('sample_size', 0),
            'average_score': stats.get('valuation_score', 60.0)
        }

        sector_name = stock_data.get('sector_name', '기타')
        try:
            context_result = self.sector_context.apply_sector_contextualization(
                stock_data.get('symbol', ''),
                sector_name,
                raw_total,
                sector_data_for_context
            )
        except Exception as exc:
            logger.warning(f"섹터 맥락화 실패: {exc}")
            context_result = {
                'adjusted_score': raw_total,
                'total_adjustment_factor': 1.0,
                'contextualization_applied': False
            }

        adjusted_total = context_result.get('adjusted_score', raw_total)
        adjustment_factor = (adjusted_total / raw_total) if raw_total > 0 else 1.0
        
        # 🔧 신뢰도 조건에서만 섹터조정 적용
        sample_size = stats.get('sample_size', 0) or 0
        if sample_size < 30 or not context_result.get('contextualization_applied', False):
            adjustment_factor = 1.0
        else:
            # 🔧 과도 보정 방지: 0.9x ~ 1.1x로 클립 (사용자 권장 - 안정성 강화)
            adjustment_factor = max(0.9, min(1.1, adjustment_factor))

        # 🔧 조정은 합계에만 1회 적용 (지표별 재가중치 왜곡 방지)
        raw_total = per_raw + pbr_raw + roe_raw
        adj_total = raw_total * adjustment_factor
        scale = adj_total / raw_total if raw_total > 0 else 1.0
        per_score = per_raw * scale
        pbr_score = pbr_raw * scale
        roe_score = roe_raw * scale

        # 상한 적용된 퍼센타일 저장 (일관성 확보)
        capped_sector_pct = None
        raw_sector_pct = stock_data.get('sector_percentile')
        if raw_sector_pct is not None:
            capped_sector_pct = min(percentile_cap, raw_sector_pct)

        return {
            'per_score': per_score,
            'pbr_score': pbr_score,
            'roe_score': roe_score,
            'relative_per': stock_data.get('relative_per'),
            'relative_pbr': stock_data.get('relative_pbr'),
            'sector_percentile': capped_sector_pct,
            'sector_adjustment': adjustment_factor,
            'raw_component_scores': {
                'per': per_raw,
                'pbr': pbr_raw,
                'roe': roe_raw,
                'total': raw_total
            },
            'sector_context': context_result
        }
    def get_stock_data(self, symbol: str, name: str):
        """종목 데이터 조회 (프라임 데이터 재사용)"""
        try:
            # 프라임 데이터 재사용 (폴백 시 이중 호출 방지)
            primed = getattr(self, "_primed_cache", {}).get(symbol)
            if primed:
                # analyzer 재호출 대신 primed 사용
                fd = primed.get('financial_data') or {}
                pd = primed.get('price_data') or {}
                
                # ✅ EPS/BPS 추출 및 실시간 PER/PBR 재계산
                eps = fd.get('eps', 0) or 0
                bps = fd.get('bps', 0) or 0
                current_price = primed.get('current_price', 0) or 0
                
                if current_price > 0:
                    per_realtime = (current_price / eps) if eps > 0 else 0
                    pbr_realtime = (current_price / bps) if bps > 0 else 0
                else:
                    per_realtime = fd.get('per', 0) or 0
                    pbr_realtime = fd.get('pbr', 0) or 0
                
                stock = {
                    'symbol': symbol, 'name': name,
                    'current_price': current_price,
                    'per': per_realtime,  # ✅ 실시간 재계산
                    'pbr': pbr_realtime,  # ✅ 실시간 재계산
                    'roe': fd.get('roe', 0),
                    'eps': eps,  # ✅ 저장
                    'bps': bps,  # ✅ 저장
                    'market_cap': primed.get('market_cap'),
                    'volume': pd.get('volume', 0), 'change': pd.get('price_change_rate', 0),
                    'sector': fd.get('sector', ''), 'sector_analysis': primed.get('sector_analysis', {}),
                    'financial_data': fd
                }
                # ✅ 종목명 보정 통일 (사용자 권장 - 일관된 키 사용)
                stock['name'] = stock.get('name') or stock.get('financial_data', {}).get('name') or symbol
                return stock
            
            # 평소 경로 (API 성공 시 실시간 호출, 부분 동시성 허용)
            with self._analyzer_sem:
                result = self.analyzer.analyze_single_stock(symbol, name)
            
            if result.status.name == 'SUCCESS':
                # ✅ EPS/BPS 추출 (PER/PBR 실시간 재계산용)
                fd = result.financial_data if result.financial_data else {}
                eps = fd.get('eps', 0) or 0
                bps = fd.get('bps', 0) or 0
                current_price = result.current_price or 0
                
                # ✅ 실시간 현재가로 PER/PBR 재계산 (크리티컬!)
                if current_price > 0:
                    per_realtime = (current_price / eps) if eps > 0 else 0
                    pbr_realtime = (current_price / bps) if bps > 0 else 0
                else:
                    # 현재가 없으면 KIS API 값 사용
                    per_realtime = fd.get('per', 0) or 0
                    pbr_realtime = fd.get('pbr', 0) or 0
                
                stock = {
                    'symbol': symbol,
                    'name': name,
                    'current_price': current_price,
                    'per': per_realtime,  # ✅ 실시간 재계산
                    'pbr': pbr_realtime,  # ✅ 실시간 재계산
                    'roe': fd.get('roe', 0) if fd else 0,
                    'eps': eps,  # ✅ 저장
                    'bps': bps,  # ✅ 저장
                    'market_cap': result.market_cap,
                    'volume': result.price_data.get('volume', 0) if result.price_data else 0,
                    'change': result.price_data.get('price_change_rate', 0) if result.price_data else 0,
                    'sector': fd.get('sector') if fd else '',
                    'sector_analysis': getattr(result, 'sector_analysis', {}),
                    'financial_data': fd
                }
                # ✅ 종목명 보정 통일 (사용자 권장 - 일관된 키 사용)
                stock['name'] = stock.get('name') or stock.get('financial_data', {}).get('name') or symbol
                return stock
            else:
                return None
                
        except Exception as e:
            logger.error(f"데이터 조회 오류: {name} - {e}")
            return None
    
    def analyze_single_stock_parallel(self, symbol_name_pair, options):
        """단일 종목 분석 (병렬 처리용)"""
        symbol, name = symbol_name_pair
        
        # 종목명이 없으면 빈 문자열로 (나중에 API에서 채워짐)
        if not name or name == '0':
            name = ''
        
        try:
            # 모든 모드에서 API 한도 체크 (폴백 필터링용으로 짧은 타임아웃)
            timeout = 5.0 if hasattr(self, '_is_fallback_filtering') else 10.0
            if not self.rate_limiter.take(1, timeout=timeout):
                logger.warning("Rate limit wait timed out")
                return None
            # 데이터 조회
            stock_data = self.get_stock_data(symbol, name)
            
            if stock_data:
                # 섹터 메타데이터 확장
                sector_meta = self._augment_sector_data(symbol, stock_data)
                stock_data.update(sector_meta)

                # 가치주 평가
                value_analysis = self.evaluate_value_stock(stock_data, options.get('percentile_cap', 99.5))
                
                if value_analysis:
                    # 가치주 기준 충족 여부 확인 (통일된 로직 사용)
                    stock_data['value_score'] = value_analysis['value_score']
                    is_value_stock = self.is_value_stock_unified(stock_data, options)
                    
                    # 개별 기준 충족 여부도 계산 (표시용)
                    sector_name = stock_data.get('sector_name', stock_data.get('sector', ''))
                    criteria = self.get_sector_specific_criteria(sector_name)
                    per_ok = stock_data['per'] <= criteria['per_max'] if stock_data['per'] > 0 else False
                    pbr_ok = stock_data['pbr'] <= criteria['pbr_max'] if stock_data['pbr'] > 0 else False
                    roe_ok = stock_data['roe'] >= criteria['roe_min'] if stock_data['roe'] > 0 else False
                    score_ok = value_analysis['value_score'] >= options['score_min']
                    
                    return {
                        'symbol': symbol,
                        'name': name,
                        'current_price': stock_data['current_price'],
                        'per': stock_data['per'],
                        'pbr': stock_data['pbr'],
                        'roe': stock_data['roe'],
                        'value_score': value_analysis['value_score'],
                        'grade': value_analysis['grade'],
                        'recommendation': value_analysis['recommendation'],
                        'safety_margin': value_analysis['details'].get('safety_margin', 0),
                        'intrinsic_value': value_analysis['details'].get('intrinsic_value', 0),
                        'is_value_stock': is_value_stock,
                        'per_ok': per_ok,
                        'pbr_ok': pbr_ok,
                        'roe_ok': roe_ok,
                        'score_ok': score_ok,
                        'sector': stock_data.get('sector_name', stock_data.get('sector', '')),
                        'relative_per': value_analysis['details'].get('relative_per'),
                        'relative_pbr': value_analysis['details'].get('relative_pbr'),
                        'sector_percentile': value_analysis['details'].get('sector_percentile'),
                        'sector_adjustment': value_analysis['details'].get('sector_adjustment'),
                        'confidence': value_analysis['details'].get('confidence', 'UNKNOWN'),
                        # 진단용 컬럼 추가
                        'per_score': value_analysis['details'].get('per_score', 0),
                        'pbr_score': value_analysis['details'].get('pbr_score', 0),
                        'roe_score': value_analysis['details'].get('roe_score', 0),
                        'margin_score': value_analysis['details'].get('margin_score', 0)
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"병렬 분석 오류: {name} - {e}")
            return None
    
    def _estimate_analysis_time(self, stock_count: int, api_strategy: str) -> str:
        """분석 예상 소요 시간 계산 (레이트리미터 기반 정확도 향상)"""
        if api_strategy == "빠른 모드 (병렬 처리)":
            # QPS 기반 현실적 계산
            qps = max(0.5, self.rate_limiter.rate)  # ex) 2.0
            time_seconds = stock_count / qps
        elif api_strategy == "안전 모드 (배치 처리)":
            if stock_count <= 50:
                time_seconds = (stock_count / 3) * (3 + 1)  # 배치 크기 3, 지연 1초
            elif stock_count <= 150:
                time_seconds = (stock_count / 5) * (3 + 0.8)  # 배치 크기 5, 지연 0.8초
            else:
                time_seconds = (stock_count / 8) * (3 + 0.5)  # 배치 크기 8, 지연 0.5초
        else:  # 순차 모드
            time_seconds = stock_count * 3  # 순차 처리
        
        if time_seconds < 60:
            return f"약 {int(time_seconds)}초"
        elif time_seconds < 3600:
            return f"약 {int(time_seconds/60)}분 {int(time_seconds%60)}초"
        else:
            hours = int(time_seconds/3600)
            minutes = int((time_seconds%3600)/60)
            return f"약 {hours}시간 {minutes}분"
    
    def _justified_multiples(self, per, pbr, roe, sector, payout_hint=None):
        """✅ 정당 멀티플 계산 (Justified PER/PBR - CFA 교과서 방식)"""
        # 1) 섹터별 요구수익률(r)과 유보율(b) 기본값
        sector_r = {
            "금융": 0.10, "금융업": 0.10,
            "통신": 0.105, "통신업": 0.105,
            "제조업": 0.115, "필수소비재": 0.11,
            "운송": 0.12, "운송장비": 0.12,
            "전기전자": 0.12, "IT": 0.125,
            "건설": 0.12, "건설업": 0.12,
            "기타": 0.115
        }
        sector_b = {
            "금융": 0.40, "금융업": 0.40,
            "통신": 0.55, "통신업": 0.55,
            "제조업": 0.35, "필수소비재": 0.40,
            "운송": 0.35, "운송장비": 0.35,
            "전기전자": 0.35, "IT": 0.30,
            "건설": 0.35, "건설업": 0.35,
            "기타": 0.35
        }
        
        r = sector_r.get(sector, 0.115)
        b = (payout_hint if payout_hint is not None else sector_b.get(sector, 0.35))
        
        # 2) 지속성장률 g = ROE × b
        roe_decimal = roe / 100.0 if roe > 0 else 0.0
        g = max(0.0, roe_decimal * b)
        
        # 과열 체크: g >= r이면 비정상 가정
        if g >= r or roe_decimal <= 0:
            return None, None
        
        # 3) 정당 멀티플 계산
        pb_star = (roe_decimal - g) / (r - g) if roe_decimal > 0 else None
        pe_star = (1 - b) / (r - g) if (1 - b) > 0 else None
        
        return pb_star, pe_star
    
    def compute_mos_score(self, per, pbr, roe, sector):
        """✅ 안전마진(MoS) 점수 계산 (0~100점)"""
        pb_star, pe_star = self._justified_multiples(per, pbr, roe, sector)
        
        if pb_star is None and pe_star is None:
            return 0
        
        mos_list = []
        
        # PBR 경로
        if pb_star and pbr and pbr > 0:
            mos_pb = max(0.0, pb_star / pbr - 1.0)
            mos_list.append(mos_pb)
        
        # PER 경로
        if pe_star and per and per > 0:
            mos_pe = max(0.0, pe_star / per - 1.0)
            mos_list.append(mos_pe)
        
        if not mos_list:
            return 0
        
        # 보수적 접근: 두 경로의 평균 (또는 min으로 더 보수화 가능)
        mos = sum(mos_list) / len(mos_list)
        
        # 0~100% 클리핑 후 점수화
        mos = max(0.0, min(mos, 1.0))
        return round(mos * 100)  # 0~100 점수
    
    def calculate_intrinsic_value(self, stock_data):
        """내재가치 계산 (섹터 타깃 PBR 기반, 가드 포함)"""
        try:
            price = float(stock_data.get('current_price', 0) or 0)
            pbr = float(stock_data.get('pbr', 0) or 0)
            roe = float(stock_data.get('roe', 0) or 0)
            sector_stats = stock_data.get('sector_stats', {}) or {}
            
            # BPS 역산 (pbr<=0 이거나 price<=0 이면 불가)
            if price <= 0 or pbr <= 0:
                return None
            
            bps = price / pbr
            
            # 섹터 중앙 PBR/ROE
            pbr_med = (sector_stats.get('pbr_percentiles', {}) or {}).get('p50', 1.0) or 1.0
            roe_med = (sector_stats.get('roe_percentiles', {}) or {}).get('p50', 8.0) or 8.0
            
            # ROE 기반 조정계수 (0.7~1.4 클램프)
            roe_adj = roe / roe_med if roe_med > 0 else 1.0
            roe_adj = max(0.7, min(1.4, roe_adj))
            
            # 타깃 PBR: 업종 중앙값 × ROE 조정, 0.5~3.0 클램프
            target_pbr = max(0.5, min(3.0, pbr_med * roe_adj))
            
            # ✅ 퀄리티 방어막 (사용자 권장) - 저품질 기업 상한 하향
            debt_ratio = float(stock_data.get('debt_ratio', 0) or 0)
            current_ratio = float(stock_data.get('current_ratio', 0) or 0)
            
            if roe < 5.0 or debt_ratio > 200.0:
                target_pbr = min(target_pbr, 1.5)  # 저ROE 또는 고부채 → PBR 상한 1.5
            
            # ✅ 유동비율 반영 (크리티컬 - 단기 지급능력 방어)
            if current_ratio and current_ratio < 80:
                target_pbr = min(target_pbr, 1.4)  # 낮은 유동비율 → PBR 상한 1.4
            
            intrinsic_value = bps * target_pbr
            
            # 안전마진 계산
            safety_margin = ((intrinsic_value - price) / price) * 100
            
            # 신뢰도 플래그 (섹터 샘플 수 기반)
            sample_size = (sector_stats.get('sample_size', 0) or 0)
            confidence = "HIGH" if sample_size >= 30 else "MEDIUM" if sample_size >= 10 else "LOW"
            
            return {
                'intrinsic_value': intrinsic_value,
                'safety_margin': safety_margin,
                'bps': bps,
                'target_pbr': target_pbr,
                'roe_adjustment': roe_adj,
                'confidence': confidence
            }
        except Exception as e:
            logger.warning(f"내재가치 계산 실패: {e}")
            return None
    
    def evaluate_value_stock(self, stock_data, percentile_cap: float = 99.5):
        """가치주 평가"""
        try:
            score = 0
            details = {}
            
            dao = self._evaluate_sector_adjusted_metrics(stock_data, percentile_cap)

            score += dao['per_score']
            score += dao['pbr_score']
            score += dao['roe_score']
            details.update({
                'per_score': dao['per_score'],
                'pbr_score': dao['pbr_score'],
                'roe_score': dao['roe_score'],
                'relative_per': dao.get('relative_per'),
                'relative_pbr': dao.get('relative_pbr'),
                'sector_percentile': dao.get('sector_percentile'),
                'sector_adjustment': dao.get('sector_adjustment', 1.0),
                'sector_context': dao.get('sector_context'),
                'raw_component_scores': dao.get('raw_component_scores')
            })
            
            # ✅ 업종별 기준 충족 보너스 (가치주 선정 강화)
            sector_name = stock_data.get('sector_name', stock_data.get('sector', ''))
            criteria = self.get_sector_specific_criteria(sector_name)
            
            per = stock_data.get('per', 0)
            pbr = stock_data.get('pbr', 0)
            roe = stock_data.get('roe', 0)
            
            sector_bonus = 0
            criteria_met = []
            
            # 각 기준 충족 시 보너스 (최대 15점)
            if per > 0 and per <= criteria['per_max']:
                sector_bonus += 5
                criteria_met.append('PER')
            if pbr > 0 and pbr <= criteria['pbr_max']:
                sector_bonus += 5
                criteria_met.append('PBR')
            if roe > 0 and roe >= criteria['roe_min']:
                sector_bonus += 5
                criteria_met.append('ROE')
            
            # 3개 기준 모두 충족 시 추가 보너스 (완벽한 가치주)
            if len(criteria_met) == 3:
                sector_bonus += 10
                logger.info(f"✅ {stock_data.get('name', stock_data.get('symbol'))}: 업종 기준 완벽 충족 (+{sector_bonus}점)")
            elif criteria_met:
                logger.debug(f"⚠️ {stock_data.get('name', stock_data.get('symbol'))}: 부분 충족 {criteria_met} (+{sector_bonus}점)")
            
            score += sector_bonus
            details['sector_bonus'] = sector_bonus
            details['criteria_met'] = criteria_met
            
            # 4. ✅ 안전마진(MoS) 평가 (35점) - Justified Multiple 방식
            sector_name = stock_data.get('sector_name', stock_data.get('sector', ''))
            per = stock_data.get('per', 0)
            pbr = stock_data.get('pbr', 0)
            roe = stock_data.get('roe', 0)
            
            # Justified Multiple 기반 MoS 점수 (0~100점)
            mos_raw_score = self.compute_mos_score(per, pbr, roe, sector_name)
            # 35점 만점으로 스케일링
            mos_score = round(mos_raw_score * 0.35)
            
            score += mos_score
            details['mos_score'] = mos_score
            details['mos_raw'] = mos_raw_score
            
            # 기존 내재가치도 참고용으로 보관
            intrinsic_data = self.calculate_intrinsic_value(stock_data)
            if intrinsic_data:
                details['safety_margin'] = intrinsic_data['safety_margin']
                details['intrinsic_value'] = intrinsic_data['intrinsic_value']
                details['confidence'] = intrinsic_data.get('confidence', 'UNKNOWN')
            else:
                details['safety_margin'] = 0
                details['intrinsic_value'] = 0
                details['confidence'] = 'UNKNOWN'
            
            # ✅ 등급 결정 (MoS 반영으로 점수 체계 변경)
            # 총점 구성: PER/PBR/ROE(~60점) + 섹터보너스(최대25점) + MoS(35점) = 최대 120점
            if score >= 90:
                grade = "A+ (매우 우수)"
            elif score >= 75:
                grade = "A (우수)"
            elif score >= 60:
                grade = "B+ (양호)"
            elif score >= 50:
                grade = "B (보통)"
            elif score >= 40:
                grade = "C+ (주의)"
            else:
                grade = "C (위험)"
            
            # 업종별 기준으로 추천 결정
            sector_name = stock_data.get('sector_name', stock_data.get('sector', ''))
            criteria = self.get_sector_specific_criteria(sector_name)
            
            per = stock_data.get('per', 0)
            pbr = stock_data.get('pbr', 0)
            roe = stock_data.get('roe', 0)
            safety_margin = details.get('safety_margin', 0)
            
            # 업종별 기준 적용
            per_pass = per <= criteria['per_max'] if per > 0 else False
            pbr_pass = pbr <= criteria['pbr_max'] if pbr > 0 else False
            roe_pass = roe >= criteria['roe_min'] if roe > 0 else False
            
            # ✅ 하드가드: 적자(ROE<0) + 고PBR(>3) 조합은 무조건 SELL (사용자 권장)
            if roe < 0 and pbr > 3:
                recommendation = "SELL"
            # ✅ 업종 기준 완벽 충족 시 추천 강화 (3개 기준 모두 충족)
            elif len(criteria_met) == 3 and score >= 60:
                recommendation = "STRONG_BUY"  # 업종 기준 완벽하면 60점부터 강력매수
            elif len(criteria_met) == 3 and score >= 50:
                recommendation = "BUY"  # 업종 기준 완벽하면 50점부터 매수
            # 기존 추천 로직 (안전마진 기반)
            elif score >= 70 and per_pass and pbr_pass:
                recommendation = "STRONG_BUY"
            elif score >= 60 and (per_pass or pbr_pass):
                recommendation = "BUY"
            elif score >= 50:
                recommendation = "HOLD"
            else:
                recommendation = "SELL"
            
            # ✅ 보수화 패널티 시스템 (사용자 권장 - 중복 방지, 명확한 의도)
            penalties = 0
            if per <= 0:
                penalties += 1
            if roe < 0:
                penalties += 1
            if (pbr and pbr > 5) and (roe and roe < 5):
                penalties += 1
            
            # 패널티에 따라 한 단계씩 하향
            def downgrade(r):
                order = ["STRONG_BUY", "BUY", "HOLD", "SELL"]
                idx = order.index(r) if r in order else 2
                return order[min(idx + 1, len(order) - 1)]
            
            # ✅ 패널티 상한 적용 (크리티컬 - 한 방에 SELL까지 떨어지는 것 방지)
            max_downgrade_steps = 2
            for _ in range(min(penalties, max_downgrade_steps)):
                recommendation = downgrade(recommendation)
            
            return {
                'value_score': score,
                'grade': grade,
                'recommendation': recommendation,
                'details': details
            }
            
        except Exception as e:
            logger.error(f"가치주 평가 오류: {e}")
            return None
    
    def render_header(self):
        """헤더 렌더링"""
        st.title("💎 저평가 가치주 발굴 시스템")
        st.markdown("**목적**: 업종별 특성을 반영한 저평가 가치주 발굴")
        st.markdown("**기준**: 각 업종별 PER, PBR, ROE 기준에 따른 상대적 저평가 종목 선별")
        st.markdown("---")
        
        # 현재 시간 표시
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.sidebar.markdown(f"**업데이트 시간:** {current_time}")
    
    def render_sidebar(self):
        """사이드바 렌더링"""
        st.sidebar.title("🎯 가치주 스크리닝")
        
        # 분석 모드 선택
        analysis_mode = st.sidebar.radio(
            "분석 모드",
            ["전체 종목 스크리닝", "개별 종목 분석"]
        )
        
        # 분석 설정
        st.sidebar.subheader("📊 분석 설정")
        
        # 분석 대상 종목 수 (250종목까지 확장)
        max_stocks = st.sidebar.slider("분석 대상 종목 수", 5, 250, 15, 1)
        
        # API 호출 전략 선택
        api_strategy = st.sidebar.selectbox(
            "API 호출 전략",
            ["안전 모드 (배치 처리)", "빠른 모드 (병렬 처리)", "순차 모드 (안전)"],
            help="안전 모드: API 한도 고려한 배치 처리\n빠른 모드: 병렬 처리 (API 한도 위험)\n순차 모드: 하나씩 순서대로 처리"
        )
        
        # 가치주 기준 설정
        st.sidebar.subheader("🎯 가치주 기준")
        
        per_max = st.sidebar.slider("PER 최대값", 5.0, 30.0, 15.0, 0.5)
        pbr_max = st.sidebar.slider("PBR 최대값", 0.5, 3.0, 1.5, 0.1)
        roe_min = st.sidebar.slider("ROE 최소값", 5.0, 25.0, 10.0, 0.5)
        score_min = st.sidebar.slider("최소 점수", 40.0, 90.0, 60.0, 5.0)
        
        # 빠른 모드 튜닝 파라미터
        st.sidebar.subheader("⚙️ 성능 튜닝")
        fast_latency = st.sidebar.slider(
            "빠른 모드 지연 추정(초)", 0.3, 1.5, 0.7, 0.1,
            help="빠른 모드 동시성 계산에 사용됩니다(낮을수록 워커↑)."
        )
        
        # 퍼센타일 상한 설정
        percentile_cap = st.sidebar.slider(
            "퍼센타일 상한(표시/스코어)", 98.0, 99.9, 99.5, 0.1,
            help="퍼센타일 표시와 스코어 계산에 모두 적용됩니다. 낮을수록 과포화 감소하고 점수 계산도 달라집니다."
        )
        
        # 개별 종목 분석인 경우에만 종목 선택
        selected_symbol = None
        if analysis_mode == "개별 종목 분석":
            stock_options = {
                '005930': '삼성전자',
                '003550': 'LG생활건강',
                '000270': '기아',
                '035420': 'NAVER',
                '012330': '현대모비스',
                '005380': '현대차',
                '000660': 'SK하이닉스',
                '035720': '카카오',
                '051910': 'LG화학',
                '006400': '삼성SDI'
            }
            
            selected_symbol = st.sidebar.selectbox(
                "분석 종목 선택",
                options=list(stock_options.keys()),
                format_func=lambda x: f"{x} - {stock_options[x]}"
            )
        
        # 개발자 도구 (캐시 클리어)
        dev_exp = st.sidebar.expander("🔧 개발자 도구")
        with dev_exp:
            if st.button("캐시 클리어", help="모든 캐시를 클리어하여 재계산합니다"):
                st.cache_data.clear()
                st.cache_resource.clear()
                st.success("캐시가 클리어되었습니다!")
                st.rerun()
        
        # 업종별 기준 정보 표시
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📊 업종별 가치주 기준")
        
        exp = st.sidebar.expander("업종별 기준 보기")
        with exp:
            st.markdown("**금융업**: PER ≤ 12배, PBR ≤ 1.2배, ROE ≥ 12%")
            st.markdown("**기술업**: PER ≤ 25배, PBR ≤ 3.0배, ROE ≥ 15%")
            st.markdown("**제조업**: PER ≤ 18배, PBR ≤ 2.0배, ROE ≥ 10%")
            st.markdown("**바이오/제약**: PER ≤ 50배, PBR ≤ 5.0배, ROE ≥ 8%")
            st.markdown("**에너지/화학**: PER ≤ 15배, PBR ≤ 1.8배, ROE ≥ 8%")
            st.markdown("**소비재**: PER ≤ 20배, PBR ≤ 2.5배, ROE ≥ 12%")
            st.markdown("**통신업**: PER ≤ 15배, PBR ≤ 2.0배, ROE ≥ 8%")
            st.markdown("**건설업**: PER ≤ 12배, PBR ≤ 1.5배, ROE ≥ 8%")

        return {
            'analysis_mode': analysis_mode,
            'selected_symbol': selected_symbol,
            'max_stocks': max_stocks,
            'api_strategy': api_strategy,
            'per_max': per_max,
            'pbr_max': pbr_max,
            'roe_min': roe_min,
            'score_min': score_min,
            'fast_latency': fast_latency,
            'percentile_cap': percentile_cap
        }
    
    def get_stock_universe_from_api(self, max_count: int = 250):
        """KIS API로 시가총액순 종목 리스트 가져오기 (캐시 적용)"""
        try:
            # 캐시된 API 호출
            stock_universe, api_success = _cached_universe_from_api(max_count)
            
            if stock_universe and api_success:
                # 섹터 정보가 없으므로 여기서는 통계 갱신 생략
                # 실제 섹터는 analyze_single_stock_parallel에서 확보됨
                logger.info(f"캐시된 API에서 {len(stock_universe)}개 종목을 가져왔습니다 (섹터는 분석 단계에서 자동 보강).")
                return stock_universe, True
            else:
                logger.warning("캐시된 API에서 종목 리스트를 가져오지 못했습니다. 기본 종목을 사용합니다.")
                fallback = self._get_fallback_stock_list()
                # 요청된 개수만큼만 반환
                return dict(list(fallback.items())[:max_count]), False
                
        except Exception as e:
            logger.error(f"캐시된 API 종목 리스트 조회 실패: {e}")
            fallback = self._get_fallback_stock_list()
            # 요청된 개수만큼만 반환
            return dict(list(fallback.items())[:max_count]), False
    
    def _get_fallback_stock_list(self):
        """API 실패 시 사용할 기본 종목 리스트 (정제된 200개)"""
        # 잘못된 티커 블랙리스트 (클래스 상수 사용)
        BAD_FALLBACK = self.BAD_CODES
        
        # 중복 제거 및 품질 검증된 종목 리스트
        # ✅ 검증된 대형주만 유지 (사용자 권장 - 오류/중복 완전 제거)
        fallback_stocks = {
            # 시총 상위 30개 (검증 완료)
            '005930': '삼성전자',
            '000660': 'SK하이닉스',
            '373220': 'LG에너지솔루션',
            '207940': '삼성바이오로직스',
            '005380': '현대차',
            '051910': 'LG화학',
            '006400': '삼성SDI',
            '005490': '포스코홀딩스',  # ✅ 수정 (POSCO → 포스코홀딩스)
            '035420': 'NAVER',
            '000270': '기아',
            '068270': '셀트리온',
            '105560': 'KB금융',
            '055550': '신한지주',
            '012330': '현대모비스',
            '086790': '하나금융지주',
            '096770': 'SK이노베이션',
            '066570': 'LG전자',
            '017670': 'SK텔레콤',
            '015760': '한국전력',
            '003490': '대한항공',
            '000810': '삼성화재',
            '018260': '삼성에스디에스',
            '034730': 'SK',
            '028260': '삼성물산',
            '086280': '현대글로비스',
            '032830': '삼성생명',
            '009150': '삼성전기',
            '035720': '카카오',
            '034020': '두산에너빌리티',
            # 추가 대형주 (필요시 확장)
            '030200': 'KT',
            '024110': '기업은행',
            '323410': '카카오뱅크',
            '010130': '고려아연',
            '009540': 'HD한국조선해양',
            '012450': '한화에어로스페이스',
            '047050': '포스코인터내셔널',  # ✅ 수정 (포스코홀딩스 → 포스코인터내셔널)
            '003550': 'LG',
            '004020': '현대제철',
            '034220': 'LG디스플레이',
            # ✅ 068290 삭제 (잘못된 삼성전자 중복)
            # ✅ 중복 제거: 028260, 025890 등
        }
        
        # ✅ 품질 검증 + 블랙리스트 제거 + 중복 제거 (사용자 권장)
        validated_stocks = {}
        seen_names = set()
        
        for code, name in fallback_stocks.items():
            if (isinstance(code, str) and code.isdigit() and len(code) == 6 
                and isinstance(name, str) and name.strip()
                and code not in self.BAD_CODES
                and name not in seen_names):
                validated_stocks[code] = name.strip()
                seen_names.add(name.strip())
        
        logger.info(f"✅ Fallback 종목 리스트 검증 완료: {len(validated_stocks)}개 종목 (중복 제거)")
        return validated_stocks
    
    def _get_fallback_stock_list_old(self):
        """레거시 폴백 리스트 (사용 안 함 - 참고용)"""
        # 소형주 리스트는 제거됨 (오류가 많고 실제로 사용되지 않음)
        fallback_stocks_legacy = {
            # 레거시 코드 (참고용, 실제로는 위의 검증된 리스트만 사용)
            '001390': 'KG케미칼', '001420': '태원물산', '001430': '세아베스틸', '001440': '대한전선', '001450': '현대해상',
            '001460': 'BYC', '001470': '삼부토건', '001500': '현대차증권', '001510': 'SK증권', '001520': '동양',
            '001525': '동양우', '001530': '동양방송', '001540': '안국약품', '001550': '조비', '001560': '제일연마',
            '001580': '대림제지', '001590': '대한제당', '001600': '남성', '001620': '동국시스템즈', '001630': '종근당바이오',
            '001680': '대상', '001690': '대상홀딩스', '001720': '신영증권', '001725': '신영증권우', '001740': 'SK네트웍스',
            '001750': '한양증권', '001755': '한양증권우', '001770': '신화실업', '001780': '알루코', '001790': '대한제당',
            '001800': '오리온홀딩스', '001810': '무림SP', '001820': '삼화콘덴서', '001840': '이건산업', '001850': '화천기공',
            '001860': '남광토건', '001870': '대한제분', '001880': '한화에어로스페이스', '001890': '동국제강', '001920': '삼화콘덴서',
            '001940': 'KISCO홀딩스', '001950': 'CJ', '001960': 'CJ제일제당', '002020': '코오롱', '002025': '코오롱우',
            '002030': '아세아', '002040': 'KCC', '002070': '비비안', '002100': '경농', '002140': '고려산업',
            '002150': '도화엔지니어링', '002200': '한국수출포장', '002210': '동성제약', '002220': '한일철강', '002240': '고려제약',
            '002270': '롯데푸드', '002290': '삼성물산', '002300': '한국주철관', '002310': '아세아시멘트', '002320': '한진',
            '002350': '넥센타이어', '002355': '넥센타이어1우B', '002360': 'SH에너지화학', '002390': '한독', '002410': '범양건영',
            '002420': '세기상사', '002450': '삼익악기', '002460': '화성산업', '002500': '가온전선', '002520': '제일약품',
            '002530': '한진중공업', '002540': '흥국화재', '002550': '조선내화', '002560': '제일약품', '002570': '제일약품우',
            '002990': '제일약품2우B', '003000': '제일약품3우B', '003010': '조선내화'
        }
        # ✅ 레거시 리스트 완전 제거됨 (사용자 권장)
        return {}
    
    def _is_tradeable(self, code: str, name: str):
        """종목의 실거래성 간단 검증 (가벼운 체크) + 프라임 데이터 반환"""
        # 실패 캐시 체크
        with self._failed_lock:  # 🔒 멀티스레드 보호
            if code in self._failed_codes:
                return False, None
            
        try:
            # 간단한 가격 조회로 실거래성 확인 (부분 동시성 허용)
            # 폴백 필터링용으로 짧은 타임아웃 사용
            with self._analyzer_sem:
                result = self.analyzer.analyze_single_stock(code, name)
            if result.status.name == 'SUCCESS' and result.current_price > 0:
                # 프라임 데이터 반환 (이중 호출 방지)
                primed_data = {
                    'symbol': code, 'name': name, 'current_price': result.current_price,
                    'financial_data': result.financial_data, 'price_data': result.price_data,
                    'market_cap': result.market_cap, 'sector_analysis': getattr(result, 'sector_analysis', {})
                }
                return True, primed_data
            else:
                # 실패한 코드는 캐시에 추가 (TTL 관리)
                with self._failed_lock:  # 🔒 멀티스레드 보호
                    self._failed_codes.add(code)
                    self._failed_codes_ttl[code] = time.time()
                self._gc_failed_codes()
            return False, None
        except Exception as e:
            logger.debug(f"실거래성 검증 실패: {code} - {e}")
            # 실패한 코드는 캐시에 추가 (TTL 관리)
            with self._failed_lock:  # 🔒 멀티스레드 보호
                self._failed_codes.add(code)
                self._failed_codes_ttl[code] = time.time()
            self._gc_failed_codes()
            return False, None
    
    def get_stock_universe(self, max_count=250):
        """분석 대상 종목 유니버스 반환 (API 우선, 실패 시 기본값)"""
        result = self.get_stock_universe_from_api(max_count)
        
        # 결과/플래그 해석
        if isinstance(result, tuple):
            stock_universe, api_success = result
            self._last_api_success = api_success
        else:
            # (레거시 대응) dict 단독 반환 시에는 성공으로 간주
            stock_universe = result
            self._last_api_success = True
        
        # ✅ 공통 경로에서 폴백 후처리 수행 (소규모 병렬 처리로 가속화)
        if not self._last_api_success:
            filtered = {}
            primed = {}  # 프라임 데이터 저장
            original_count = len(stock_universe)  # 원본 개수 추적
            
            # 소규모 쓰레드풀로 체크 병렬화 (TokenBucket이 QPS 제한)
            self._is_fallback_filtering = True  # 폴백 필터링 플래그
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
                futs = []
                items = list(stock_universe.items())
                for code, name in items[:max_count * 2]:  # 과도 프리페치 방지
                    futs.append(ex.submit(self._is_tradeable, code, name))
                    
                for ((code, name), fut) in zip(items, futs):
                    ok, primed_data = fut.result()
                    if ok: 
                        filtered[code] = name
                    if primed_data: 
                        primed[code] = primed_data
                    if len(filtered) >= max_count: 
                        break
            
            if filtered:
                stock_universe = filtered
                self._primed_cache = primed  # 폴백 시 결과를 프라임 캐시로
                self._fallback_original_count = original_count  # 원본 개수 저장
                logger.info(f"폴백 유니버스 필터링: {original_count}개 → {len(stock_universe)}개로 축소")
                
                # primed_data에서 섹터명 수집하여 통계 갱신
                if primed:
                    sector_stocks = []
                    for code, primed_data in primed.items():
                        if 'sector_analysis' in primed_data:
                            sector_name = primed_data['sector_analysis'].get('sector_name', '기타')
                            sector_stocks.append({
                                'code': code,
                                'name': primed_data.get('name', ''),
                                'sector': sector_name,
                                'market_cap': primed_data.get('market_cap', 0)
                            })
                    if sector_stocks:
                        try:
                            self.refresh_sector_stats_and_clear_cache(sector_stocks)
                            logger.info(f"폴백에서 수집한 {len(sector_stocks)}개 종목으로 섹터 통계 갱신")
                        except Exception as e:
                            logger.warning(f"폴백 섹터 통계 갱신 실패: {e}")
                            
            delattr(self, '_is_fallback_filtering')  # 플래그 정리
        else:
            # ✅ API 성공 시, 이전 폴백에서 남았을 수 있는 프라임 캐시 초기화
            if hasattr(self, "_primed_cache"):
                self._primed_cache.clear()
        
        logger.info(f"get_stock_universe 반환: {type(stock_universe)}, 길이: {len(stock_universe) if hasattr(stock_universe, '__len__') else 'N/A'}")
        return stock_universe
    
    def screen_all_stocks(self, options):
        """전체 종목 스크리닝"""
        st.header("📊 가치주 스크리닝 결과")
        
        max_stocks = options['max_stocks']
        
        # 사용자가 선택한 종목 수만 로딩
        with st.spinner(f"📊 실시간 종목 리스트 로딩 중... ({max_stocks}개 종목)"):
            stock_universe = self.get_stock_universe(max_stocks)
            
        # 타입 안전성 확인
        if not isinstance(stock_universe, dict):
            logger.error(f"stock_universe가 딕셔너리가 아닙니다: {type(stock_universe)}")
            st.error("종목 데이터 형식 오류가 발생했습니다.")
            return
        
        # 데이터 소스 표시 - API 성공 여부를 정확하게 판단
        api_success = getattr(self, '_last_api_success', False)
        
        if api_success:
            st.success(f"✅ **실시간 KIS API 데이터**: {len(stock_universe)}개 종목 로딩 완료")
        else:
            # 폴백 필터링 정보 표시
            if hasattr(self, '_fallback_original_count'):
                original_count = self._fallback_original_count
                st.warning(f"⚠️ **기본 종목 사용**: {len(stock_universe)}개 종목 (원본 {original_count}개 중 거래성 검증 후 {len(stock_universe)}개)")
            else:
                st.warning(f"⚠️ **기본 종목 사용**: {len(stock_universe)}개 종목 (API 연결 실패)")
        
        # 분석 대상 종목 정보 표시
        st.info(f"📈 **분석 대상**: {len(stock_universe)}개 종목")
        
        # 대용량 분석 경고
        if len(stock_universe) > 100:
            st.warning("⚠️ **대용량 분석**: 100종목 이상은 분석 시간이 오래 걸릴 수 있습니다.")
            st.info(f"💡 **예상 소요 시간**: {self._estimate_analysis_time(len(stock_universe), options['api_strategy'])}")
        
        # 종목 목록 미리보기 (대용량일 때는 샘플만 표시)
        with st.expander("📋 분석 대상 종목 목록"):
            # BAD_FALLBACK와 동일한 규칙으로 미리보기 필터링 (혼선 방지)
            BAD_PREVIEW = self.BAD_CODES
            
            def _preview_filtered_items(items, limit):
                out = []
                for code, name in items:
                    if code in BAD_PREVIEW:
                        continue
                    out.append((code, name))
                    if len(out) >= limit:
                        break
                return out
            
            if len(stock_universe) > 50:
                # 대용량일 때는 샘플만 표시
                sample_size = min(self.SAMPLE_PREVIEW_SIZE, len(stock_universe))
                sample_items = _preview_filtered_items(list(stock_universe.items()), sample_size)
                sample_stocks = dict(sample_items)
                stock_df = pd.DataFrame([
                    {'종목코드': code, '종목명': name} 
                    for code, name in sample_stocks.items()
                ])
                st.dataframe(stock_df, use_container_width=True, hide_index=True)
                st.info(f"📊 위는 전체 {len(stock_universe)}개 종목 중 처음 {len(sample_stocks)}개 샘플입니다.")
            else:
                # 전체 표시 시에도 블랙리스트 필터링
                filtered_items = _preview_filtered_items(list(stock_universe.items()), len(stock_universe))
                stock_df = pd.DataFrame([
                    {'종목코드': code, '종목명': name} 
                    for code, name in filtered_items
                ])
                st.dataframe(stock_df, use_container_width=True, hide_index=True)
        
        # API 호출 전략에 따른 처리 방식 선택
        api_strategy = options['api_strategy']
        
        # 빠른 모드 튜닝 파라미터
        fast_latency = options.get('fast_latency', 0.7)
        
        # 진행률 표시
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.empty()
        
        results = []
        stock_items = list(stock_universe.items())
        error_samples = []  # 에러 샘플링용
        err_counter = Counter()  # 에러 카운터
        
        # UI 디바운스 (깜빡임 완화)
        last_ui_update = 0.0
        
        if api_strategy == "안전 모드 (배치 처리)":
            # 대용량 분석을 위한 동적 배치 크기 조정
            if len(stock_items) <= 50:
                batch_size = 3
                base_delay = 1.0
            elif len(stock_items) <= 150:
                batch_size = 5
                base_delay = 0.8
            else:  # 250종목
                batch_size = 8
                base_delay = 0.5
            
            status_text.text(f"🛡️ 안전 모드 시작: {len(stock_universe)}개 종목, 배치 크기: {batch_size}")
            
            # 동적 백오프 변수
            backoff = 1.0
            
            # 배치별로 처리
            for batch_start in range(0, len(stock_items), batch_size):
                batch_end = min(batch_start + batch_size, len(stock_items))
                batch = stock_items[batch_start:batch_end]
                
                current_time = time.time()
                if current_time - last_ui_update > self.UI_UPDATE_INTERVAL:
                    status_text.text(f"📊 배치 {batch_start//batch_size + 1} 처리 중: {len(batch)}개 종목")
                    last_ui_update = current_time
                
                # 현재 배치 병렬 처리
                batch_error = False
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(3, len(batch))) as executor:
                    future_to_stock = {
                        executor.submit(self.analyze_single_stock_parallel, (symbol, name), options): (symbol, name)
                        for symbol, name in batch
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_stock):
                        symbol, name = future_to_stock[future]
                        try:
                            result = future.result()
                            if result:
                                results.append(result)
                        except Exception as e:
                            msg = f"{name} 분석 오류: {e}"
                            logger.error(msg)
                            if len(error_samples) < 3:
                                # ✅ 메시지 길이 제한 (사용자 권장 - UI 깔끔화)
                                error_samples.append(textwrap.shorten(msg, width=120, placeholder="..."))
                            err_counter[type(e).__name__] += 1
                            batch_error = True
                
                # 진행률 업데이트
                completed_count = batch_end
                progress = completed_count / len(stock_items)
                progress_bar.progress(progress)
                
                current_time = time.time()
                if current_time - last_ui_update > self.UI_UPDATE_INTERVAL:
                    status_text.text(f"📊 배치 완료: {completed_count}/{len(stock_items)} 완료 ({progress*100:.1f}%)")
                    last_ui_update = current_time
                
                # 실시간 결과 미리보기
                value_stocks = [r for r in results if r['is_value_stock']]
                if value_stocks:
                    results_container.info(f"🎯 현재까지 발견된 가치주: {len(value_stocks)}개")
                
                # 동적 백오프 적용
                if batch_end < len(stock_items):
                    if batch_error:
                        backoff = min(backoff * 1.5, 4.0)  # 최대 4배
                        logger.warning(f"배치 오류 감지, 백오프 증가: {backoff:.1f}x")
                    else:
                        backoff = max(backoff / 1.2, 1.0)  # 점진적 감소
                    
                    delay = base_delay * backoff
                    time.sleep(delay)
            
            status_text.text("✅ 안전 모드 분석 완료!")
            
        elif api_strategy == "빠른 모드 (병렬 처리)":
            # ✅ 워커 수 단순화 (크리티컬 - 내부 속성 접근 제거, 버전 호환성)
            # 고정 상수로 단순화 (세마포어 내부 구현 의존성 제거)
            max_workers = min(8, max(4, len(stock_universe)))
            
            status_text.text(f"⚡ 빠른 모드 시작: {len(stock_universe)}개 종목, {max_workers}개 워커")
            st.warning("⚠️ 빠른 모드는 API 호출 한도 초과 위험이 있습니다!")
            st.info(f"💡 레이트리미터 적용으로 실제 처리 속도는 초당 {self.rate_limiter.rate}개 종목으로 제한됩니다.")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_stock = {
                    executor.submit(self.analyze_single_stock_parallel, (symbol, name), options): (symbol, name)
                    for symbol, name in stock_items
                }
                
                completed_count = 0
                for future in concurrent.futures.as_completed(future_to_stock):
                    symbol, name = future_to_stock[future]
                    try:
                        result = future.result()
                        if result:
                            results.append(result)
                    except Exception as e:
                        msg = f"{name} 분석 오류: {e}"
                        logger.error(msg)
                        if len(error_samples) < 3:
                            # ✅ 메시지 길이 제한 (사용자 권장 - UI 깔끔화)
                            error_samples.append(textwrap.shorten(msg, width=120, placeholder="..."))
                        err_counter[type(e).__name__] += 1
                    
                    completed_count += 1
                    progress = completed_count / len(stock_items)
                    progress_bar.progress(progress)
                    current_time = time.time()
                    if current_time - last_ui_update > self.UI_UPDATE_INTERVAL:
                        status_text.text(f"📊 분석 진행: {completed_count}/{len(stock_items)} 완료 ({progress*100:.1f}%)")
                        last_ui_update = current_time
                    
                    value_stocks = [r for r in results if r['is_value_stock']]
                    if value_stocks:
                        results_container.info(f"🎯 현재까지 발견된 가치주: {len(value_stocks)}개")
            
            status_text.text("✅ 빠른 모드 분석 완료!")
            
        else:  # 순차 모드
            # 순차 처리 방식
            status_text.text(f"🐌 순차 모드 시작: {len(stock_universe)}개 종목")
            
            for i, (symbol, name) in enumerate(stock_items):
                status_text.text(f"📊 분석 중: {name} ({symbol})")
                
                try:
                    result = self.analyze_single_stock_parallel((symbol, name), options)
                    if result:
                        results.append(result)
                except Exception as e:
                    msg = f"{name} 분석 오류: {e}"
                    logger.error(msg)
                    if len(error_samples) < 3:
                        # ✅ 메시지 길이 제한 (사용자 권장 - UI 깔끔화)
                        error_samples.append(textwrap.shorten(msg, width=120, placeholder="..."))
                    err_counter[type(e).__name__] += 1
                
                # 진행률 업데이트
                progress = (i + 1) / len(stock_items)
                progress_bar.progress(progress)
                
                current_time = time.time()
                if current_time - last_ui_update > self.UI_UPDATE_INTERVAL:
                    status_text.text(f"📊 순차 진행: {i+1}/{len(stock_items)} 완료 ({progress*100:.1f}%)")
                    last_ui_update = current_time
                
                value_stocks = [r for r in results if r['is_value_stock']]
                if value_stocks:
                    results_container.info(f"🎯 현재까지 발견된 가치주: {len(value_stocks)}개")
            
            status_text.text("✅ 순차 모드 분석 완료!")
        
        results_container.empty()
        
        # 에러 요약 표시
        if err_counter:
            error_summary = ", ".join([f"{k}: {v}" for k, v in err_counter.most_common()])
            st.info(f"에러 요약: {error_summary}")
        if error_samples:
            st.info("일부 오류가 발생했습니다(샘플):\n- " + "\n- ".join(error_samples))
        
        # 결과 표시
        if results:
            # 가치주만 필터링
            value_stocks = [r for r in results if r['is_value_stock']]
            
            # 통계 표시
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("전체 분석 종목", f"{len(results)}개")
            
            with col2:
                st.metric("가치주 발견", f"{len(value_stocks)}개")
            
            with col3:
                if results:
                    avg_score = sum(r['value_score'] for r in results) / len(results)
                    st.metric("평균 점수", f"{avg_score:.1f}점")
            
            with col4:
                if value_stocks:
                    avg_value_score = sum(r['value_score'] for r in value_stocks) / len(value_stocks)
                    st.metric("가치주 평균 점수", f"{avg_value_score:.1f}점")
            
            # 추가 신뢰도 힌트
            if results:
                col5, col6 = st.columns(2)
                with col5:
                    # 섹터조정 중앙값
                    sector_adjustments = [r.get('sector_adjustment', 1.0) for r in results]
                    if sector_adjustments:
                        median_adjustment = statistics.median(sector_adjustments)
                        st.metric("섹터조정 중앙값", f"{median_adjustment:.2f}x")
                        
                        # 🔧 극단적 섹터조정 경고
                        if median_adjustment < 0.7:
                            st.warning("⚠️ 섹터조정이 0.7x 미만으로 계산되었습니다(표본 부족/과도 보정 가능). 보정 범위를 제한했습니다.")
                
                with col6:
                    # 신뢰도 분포
                    confidence_counts = {}
                    for r in results:
                        conf = r.get('confidence', 'UNKNOWN')
                        confidence_counts[conf] = confidence_counts.get(conf, 0) + 1
                    if confidence_counts:
                        high_conf = confidence_counts.get('HIGH', 0)
                        st.metric("HIGH 신뢰도", f"{high_conf}개", 
                                help="HIGH 신뢰도 = 섹터 표본 ≥30개 종목")
            
            # ==========================================
            # 🎯 투자 추천 종목을 맨 위로! (가장 중요)
            # ==========================================
            
            # 추천 통계 계산
            rec_counts_all = {}
            for r in results:
                rec = r['recommendation']
                rec_counts_all[rec] = rec_counts_all.get(rec, 0) + 1
            
            st.markdown("---")  # 구분선
            st.subheader("🎯 투자 추천 종목 (전체 분석 결과)")
            st.caption(f"💡 추천 등급: STRONG_BUY({rec_counts_all.get('STRONG_BUY', 0)}) / BUY({rec_counts_all.get('BUY', 0)}) / HOLD({rec_counts_all.get('HOLD', 0)}) / SELL({rec_counts_all.get('SELL', 0)})")
            
            # 추천 등급별로 필터링
            strong_buy_stocks = [r for r in results if r['recommendation'] == 'STRONG_BUY']
            buy_stocks = [r for r in results if r['recommendation'] == 'BUY']
            hold_stocks = [r for r in results if r['recommendation'] == 'HOLD']
            sell_stocks = [r for r in results if r['recommendation'] == 'SELL']
            
            # STRONG_BUY 종목
            if strong_buy_stocks:
                with st.expander(f"🌟 STRONG_BUY ({len(strong_buy_stocks)}개)", expanded=True):
                    strong_buy_df = pd.DataFrame([
                        {
                            '종목코드': s['symbol'],
                            '종목명': s['name'],
                            '섹터': s.get('sector', 'N/A'),
                            '현재가': f"{s.get('current_price', 0):,.0f}원",
                            'PER': f"{s.get('per', 0):.1f}배" if s.get('per') else 'N/A',
                            'PBR': f"{s.get('pbr', 0):.2f}배" if s.get('pbr') else 'N/A',
                            'ROE': f"{s.get('roe', 0):.1f}%" if s.get('roe') else 'N/A',
                            '안전마진': f"{s.get('safety_margin', 0):.1f}%",
                            '가치점수': f"{s.get('value_score', 0):.1f}점"
                        }
                        for s in strong_buy_stocks
                    ])
                    st.dataframe(strong_buy_df, use_container_width=True, hide_index=True)
            
            # BUY 종목
            if buy_stocks:
                with st.expander(f"✅ BUY ({len(buy_stocks)}개)", expanded=True):
                    buy_df = pd.DataFrame([
                        {
                            '종목코드': s['symbol'],
                            '종목명': s['name'],
                            '섹터': s.get('sector', 'N/A'),
                            '현재가': f"{s.get('current_price', 0):,.0f}원",
                            'PER': f"{s.get('per', 0):.1f}배" if s.get('per') else 'N/A',
                            'PBR': f"{s.get('pbr', 0):.2f}배" if s.get('pbr') else 'N/A',
                            'ROE': f"{s.get('roe', 0):.1f}%" if s.get('roe') else 'N/A',
                            '안전마진': f"{s.get('safety_margin', 0):.1f}%",
                            '가치점수': f"{s.get('value_score', 0):.1f}점"
                        }
                        for s in buy_stocks
                    ])
                    st.dataframe(buy_df, use_container_width=True, hide_index=True)
            
            # HOLD 종목
            if hold_stocks:
                with st.expander(f"⚠️ HOLD ({len(hold_stocks)}개)", expanded=False):
                    hold_df = pd.DataFrame([
                        {
                            '종목코드': s['symbol'],
                            '종목명': s['name'],
                            '섹터': s.get('sector', 'N/A'),
                            '현재가': f"{s.get('current_price', 0):,.0f}원",
                            'PER': f"{s.get('per', 0):.1f}배" if s.get('per') else 'N/A',
                            'PBR': f"{s.get('pbr', 0):.2f}배" if s.get('pbr') else 'N/A',
                            'ROE': f"{s.get('roe', 0):.1f}%" if s.get('roe') else 'N/A',
                            '안전마진': f"{s.get('safety_margin', 0):.1f}%",
                            '가치점수': f"{s.get('value_score', 0):.1f}점"
                        }
                        for s in hold_stocks
                    ])
                    st.dataframe(hold_df, use_container_width=True, hide_index=True)
            
            # SELL 종목
            if sell_stocks:
                with st.expander(f"❌ SELL ({len(sell_stocks)}개)", expanded=False):
                    sell_df = pd.DataFrame([
                        {
                            '종목코드': s['symbol'],
                            '종목명': s['name'],
                            '섹터': s.get('sector', 'N/A'),
                            '현재가': f"{s.get('current_price', 0):,.0f}원",
                            'PER': f"{s.get('per', 0):.1f}배" if s.get('per') else 'N/A',
                            'PBR': f"{s.get('pbr', 0):.2f}배" if s.get('pbr') else 'N/A',
                            'ROE': f"{s.get('roe', 0):.1f}%" if s.get('roe') else 'N/A',
                            '안전마진': f"{s.get('safety_margin', 0):.1f}%",
                            '가치점수': f"{s.get('value_score', 0):.1f}점"
                        }
                        for s in sell_stocks
                    ])
                    st.dataframe(sell_df, use_container_width=True, hide_index=True)
            
            # 가치주 결과 테이블
            if value_stocks:
                st.subheader(f"🎯 발견된 가치주 목록 ({len(value_stocks)}개)")
                st.caption(f"✅ 기준 통과: {len(value_stocks)}개 / 전체 분석: {len(results)}개")
                
                # 점수순 정렬
                value_stocks.sort(key=lambda x: x['value_score'], reverse=True)
                
                # 테이블 데이터 준비
                table_data = []
                for stock in value_stocks:
                    table_data.append({
                        '종목명': stock['name'],
                        '종목코드': f"{stock['symbol']}".zfill(6),
                        '섹터': stock.get('sector', ''),
                        '현재가': f"{stock['current_price']:,}원",
                        'PER': "N/A" if stock['per'] <= 0 else f"{stock['per']:.1f}배",
                        'PBR': "N/A" if stock['pbr'] <= 0 else f"{stock['pbr']:.2f}배", 
                        'ROE': f"{stock['roe']:.1f}%",
                        '가치주점수': f"{stock['value_score']:.1f}점",
                        '등급': stock['grade'],
                        '추천': stock['recommendation'],
                        '안전마진': f"{stock['safety_margin']:+.1f}%",
                        '내재가치': f"{stock['intrinsic_value']:,.0f}원",
                        '섹터 대비 PER': self.format_pct_or_na(stock.get('relative_per')),
                        '섹터 대비 PBR': self.format_pct_or_na(stock.get('relative_pbr')),
                        'ROE 퍼센타일': self.format_percentile(stock.get('sector_percentile'), options.get('percentile_cap', 99.5)),
                        '섹터조정': f"{stock.get('sector_adjustment', 1.0):.2f}x",
                        # 진단용 컬럼 추가
                        'PER점수': f"{stock.get('per_score', 0):.1f}",
                        'PBR점수': f"{stock.get('pbr_score', 0):.1f}",
                        'ROE점수': f"{stock.get('roe_score', 0):.1f}",
                        '마진점수': f"{stock.get('margin_score', 0):.1f}"
                    })
                
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True)
                
                # 가치주 목록 CSV 다운로드 버튼
                st.download_button(
                    label="📥 가치주 목록 CSV 다운로드",
                    data=df.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"value_stocks_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
                
                # 상위 가치주 차트
                st.subheader("📈 상위 가치주 비교")
                
                top_5 = value_stocks[:5]
                
                if top_5:
                    fig = go.Figure()
                    
                    # 가치주 점수 바 차트
                    fig.add_trace(go.Bar(
                        x=[stock['name'] for stock in top_5],
                        y=[stock['value_score'] for stock in top_5],
                        name='가치주 점수',
                        text=[f"{stock['safety_margin']:+.1f}%" for stock in top_5],
                        textposition='outside'
                    ))
                    
                    fig.update_layout(
                        title="상위 5개 가치주 점수 비교 (상단: 안전마진)",
                        xaxis_title="종목",
                        yaxis_title="가치주 점수",
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("차트 표시를 위한 충분한 가치주가 없습니다.")
                
            else:
                st.warning("⚠️ 설정한 기준에 맞는 가치주를 찾을 수 없습니다.")
                st.info("""
                **기준을 완화해보세요:**
                - PER 최대값을 높여보세요
                - PBR 최대값을 높여보세요
                - ROE 최소값을 낮춰보세요
                - 최소 점수를 낮춰보세요
                """)
            
            # 추천 통계 먼저 계산
            rec_counts_local = {}
            for r in results:
                rec = r['recommendation']
                rec_counts_local[rec] = rec_counts_local.get(rec, 0) + 1
            
            # ✅ 추천 종목은 위에 이미 표시됨 (1563-1656) - 중복 제거!
            
            # 전체 결과 요약 테이블
            st.markdown("---")  # 구분선
            st.subheader(f"📋 전체 분석 결과 요약 ({len(results)}개 종목)")
            st.caption("💡 모든 종목의 상세 정보를 한눈에 확인")
            
            summary_data = []
            for stock in results:
                summary_data.append({
                    '종목명': stock['name'],
                    '종목코드': f"{stock['symbol']}".zfill(6),
                    '섹터': stock.get('sector', ''),
                    '현재가': f"{stock['current_price']:,}원",
                    'PER': "N/A" if stock['per'] <= 0 else f"{stock['per']:.1f}배",
                    'PBR': "N/A" if stock['pbr'] <= 0 else f"{stock['pbr']:.2f}배",
                    'ROE': f"{stock['roe']:.1f}%",
                    '가치주점수': stock['value_score'],  # 숫자로 저장
                    '가치주점수_표시': f"{stock['value_score']:.1f}점",  # 표시용
                    '등급': stock['grade'],
                    '가치주여부': "✅" if stock['is_value_stock'] else "❌",
                    '업종기준': self._get_sector_criteria_display(stock.get('sector', '')),
                    '섹터 대비 PER': self.format_pct_or_na(stock.get('relative_per')),
                    '섹터 대비 PBR': self.format_pct_or_na(stock.get('relative_pbr')),
                    'ROE 퍼센타일': self.format_percentile(stock.get('sector_percentile'), options.get('percentile_cap', 99.5)),
                    # 진단용 컬럼 추가
                    'PER점수': f"{stock.get('per_score', 0):.1f}",
                    'PBR점수': f"{stock.get('pbr_score', 0):.1f}",
                    'ROE점수': f"{stock.get('roe_score', 0):.1f}",
                    '마진점수': f"{stock.get('margin_score', 0):.1f}",
                    '섹터조정': f"{stock.get('sector_adjustment', 1.0):.2f}x"
                })
            
            summary_df = pd.DataFrame(summary_data)
            # 가치주 점수순 정렬 (내림차순)
            summary_df = summary_df.sort_values('가치주점수', ascending=False)
            
            # 표시용 컬럼으로 변경
            summary_df['가치주점수'] = summary_df['가치주점수_표시']
            summary_df = summary_df.drop('가치주점수_표시', axis=1)
            st.dataframe(summary_df, use_container_width=True)
            
            # 전체 요약 CSV 다운로드 버튼
            st.download_button(
                label="📥 전체 요약 CSV 다운로드",
                data=summary_df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"summary_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
            
            # (중복 제거됨 - 위쪽에 이미 표시됨)
            
        else:
            st.error("데이터 조회에 실패했습니다.")
    
    def render_individual_analysis(self, options):
        """개별 종목 분석 렌더링"""
        st.header("💎 개별 종목 가치주 분석")
        
        selected_symbol = options['selected_symbol']
        
        # 종목 선택 가드
        if not selected_symbol:
            st.warning("왼쪽 사이드바에서 종목을 선택해주세요.")
            return
        stock_options = {
            '005930': '삼성전자',
            '003550': 'LG생활건강',
            '000270': '기아',
            '035420': 'NAVER',
            '012330': '현대모비스',
            '005380': '현대차',
            '000660': 'SK하이닉스',
            '035720': '카카오',
            '051910': 'LG화학',
            '006400': '삼성SDI'
        }
        
        name = stock_options[selected_symbol]
        
        # 데이터 조회
        with st.spinner(f"{name} 가치주 분석 중..."):
            stock_data = self.get_stock_data(selected_symbol, name)
            if stock_data:
                # 섹터 메타데이터 확장 (누락된 부분 추가)
                sector_meta = self._augment_sector_data(selected_symbol, stock_data)
                stock_data.update(sector_meta)
        
        if stock_data:
            # 가치주 평가
            value_analysis = self.evaluate_value_stock(stock_data, options.get('percentile_cap', 99.5))
            
            if value_analysis:
                # 섹터 벤치마크 한 번만 계산
                sector_benchmarks = stock_data.get('sector_benchmarks', get_sector_benchmarks(stock_data.get('sector_name', '기타'), None, stock_data.get('sector_stats')))
                # 가치주 점수 표시
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        label="가치주 점수",
                        value=f"{value_analysis['value_score']:.1f}점",
                        delta=f"{value_analysis['grade']}"
                    )
                
                with col2:
                    st.metric(
                        label="현재가",
                        value=f"{stock_data['current_price']:,}원"
                    )
                
                with col3:
                    if value_analysis['details']['intrinsic_value'] > 0:
                        st.metric(
                            label="내재가치",
                            value=f"{value_analysis['details']['intrinsic_value']:,.0f}원"
                        )
                
                # 신뢰도 플래그 표시 (컬러 배지)
                conf = value_analysis['details'].get('confidence')
                if conf:
                    # 신뢰도별 컬러
                    color_map = {
                        'HIGH': 'green',
                        'MEDIUM': 'orange', 
                        'LOW': 'red'
                    }
                    conf_color = color_map.get(conf, 'gray')
                    
                    st.markdown(f"""
                    <div style="
                        background-color: {conf_color}20;
                        border: 2px solid {conf_color};
                        border-radius: 8px;
                        padding: 8px 12px;
                        text-align: center;
                        margin: 8px 0;
                        font-weight: bold;
                        color: {conf_color};
                    ">
                        내재가치 추정 신뢰도: {conf} (섹터 샘플 기반)
                    </div>
                    """, unsafe_allow_html=True)
                
                # 가치주 기준 충족 여부
                st.subheader("📊 가치주 기준 충족 여부")
                
                criteria_col1, criteria_col2, criteria_col3 = st.columns(3)
                
                # 업종별 정책 기준과 섹터 벤치마크 기준 모두 계산
                policy = self.get_sector_specific_criteria(stock_data.get('sector_name', ''))
                per_policy, pbr_policy, roe_policy = policy['per_max'], policy['pbr_max'], policy['roe_min']
                
                # 이미 계산된 sector_benchmarks 재사용 (키 가드 포함)
                per_threshold = sector_benchmarks.get('per_range', (5.0, 20.0))[1]
                pbr_threshold = sector_benchmarks.get('pbr_range', (0.5, 2.0))[1]
                roe_threshold = sector_benchmarks.get('roe_range', (5.0, 20.0))[0]

                with criteria_col1:
                    per_ok = stock_data['per'] <= min(options['per_max'], per_policy)
                    st.metric(
                        label="PER 기준",
                        value=f"{stock_data['per']:.1f}배",
                        delta=f"{'✅ 충족' if per_ok else '❌ 미충족'} (정책 {per_policy:.1f}, 섹터 {per_threshold:.1f})"
                    )
                
                with criteria_col2:
                    pbr_ok = stock_data['pbr'] <= min(options['pbr_max'], pbr_policy)
                    st.metric(
                        label="PBR 기준",
                        value=f"{stock_data['pbr']:.2f}배",
                        delta=f"{'✅ 충족' if pbr_ok else '❌ 미충족'} (정책 {pbr_policy:.2f}, 섹터 {pbr_threshold:.2f})"
                    )
                
                with criteria_col3:
                    roe_ok = stock_data['roe'] >= max(options['roe_min'], roe_policy)
                    st.metric(
                        label="ROE 기준",
                        value=f"{stock_data['roe']:.1f}%",
                        delta=f"{'✅ 충족' if roe_ok else '❌ 미충족'} (정책 {roe_policy:.1f}%, 섹터 {roe_threshold:.1f}%)"
                    )
                
                # 투자 추천
                st.subheader("🎯 투자 추천")
                
                recommendation_color = "green" if value_analysis['recommendation'] == 'STRONG_BUY' else "orange" if value_analysis['recommendation'] == 'BUY' else "red"
                
                st.markdown(f"""
                <div style="
                    background-color: {recommendation_color}20;
                    border: 2px solid {recommendation_color};
                    border-radius: 10px;
                    padding: 20px;
                    text-align: center;
                    margin: 10px 0;
                ">
                    <h2 style="color: {recommendation_color}; margin: 0;">{value_analysis['recommendation']}</h2>
                    <p style="color: {recommendation_color}; margin: 5px 0 0 0;">{value_analysis['grade']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # 상세 분석
                st.subheader("🔍 상세 분석")
                
                detail_col1, detail_col2 = st.columns(2)
                
                rel_per = value_analysis['details'].get('relative_per')
                rel_pbr = value_analysis['details'].get('relative_pbr')
                sector_percentile = value_analysis['details'].get('sector_percentile')

                rel_per_text = (f"섹터 대비 {rel_per:+.1f}%" if rel_per is not None else "데이터 없음")
                rel_pbr_text = (f"섹터 대비 {rel_pbr:+.1f}%" if rel_pbr is not None else "데이터 없음")
                # ROE 퍼센타일은 상한 적용하여 표시
                percentile_text = (self.format_percentile(sector_percentile, options.get('percentile_cap', 99.5))
                                   if sector_percentile is not None else "데이터 없음")
                
                with detail_col1:
                    st.info(f"""
                    **PER 분석** (섹터 조정)
                    - 현재 PER: {stock_data['per']:.1f}배
                    - 섹터 기준 상한: {per_threshold:.1f}배
                    - 상대 PER: {rel_per_text}
                    - 점수: {value_analysis['details']['per_score']:.1f}점
                    """)
                
                with detail_col2:
                    st.info(f"""
                    **PBR 분석** (섹터 조정)
                    - 현재 PBR: {stock_data['pbr']:.2f}배
                    - 섹터 기준 상한: {pbr_threshold:.2f}배
                    - 상대 PBR: {rel_pbr_text}
                    - 점수: {value_analysis['details']['pbr_score']:.1f}점
                    """)
                
                detail_col3, detail_col4 = st.columns(2)
                
                with detail_col3:
                    st.info(f"""
                    **ROE 분석** (섹터 퍼센타일)
                    - 현재 ROE: {stock_data['roe']:.1f}%
                    - 섹터 기준 하한: {roe_threshold:.1f}%
                    - 섹터 퍼센타일: {percentile_text}
                    - 점수: {value_analysis['details']['roe_score']:.1f}점
                    """)
                
                with detail_col4:
                    if value_analysis['details']['intrinsic_value'] > 0:
                        st.info(f"""
                        **안전마진 분석** (25점 만점)
                        - 내재가치: {value_analysis['details']['intrinsic_value']:,.0f}원
                        - 안전마진: {value_analysis['details']['safety_margin']:+.1f}%
                        - 점수: {value_analysis['details']['margin_score']:.1f}점
                        - 평가: {'매우 안전' if value_analysis['details']['safety_margin'] >= 30 else '안전' if value_analysis['details']['safety_margin'] >= 20 else '주의'}
                        """)
                
                # 업종별 가치주 기준으로 최종 판단 (통일된 로직 사용)
                stock_data['value_score'] = value_analysis['value_score']
                is_value_stock = self.is_value_stock_unified(stock_data, options)
                
                if is_value_stock:
                    st.success("🎉 **이 종목은 저평가 가치주입니다!**")
                    st.markdown("""
                    **가치주 특징:**
                    - ✅ 저평가된 밸류에이션 (PER, PBR)
                    - ✅ 우수한 수익성 (ROE)
                    - ✅ 충분한 안전마진
                    - ✅ 장기 투자 가치 있음
                    """)
                else:
                    st.warning("⚠️ **이 종목은 가치주 기준을 충족하지 않습니다.**")
                    st.markdown("""
                    **개선 필요 사항:**
                    - PER 또는 PBR이 높음
                    - ROE가 부족함
                    - 안전마진 부족
                    - 추가 분석 필요
                    """)
                
            else:
                st.error("가치주 평가 실패")
        else:
            st.error("데이터 조회 실패")
    
    # === MCP 헬퍼 메서드들 ===
    
    def analyze_stock_with_mcp(self, symbol: str) -> Optional[Dict]:
        """MCP를 활용한 종목 분석"""
        if not self.mcp_integration:
            logger.warning("MCP 통합이 초기화되지 않았습니다")
            return None
        
        try:
            # 현재가와 재무비율 조회
            price_data = self.mcp_integration.get_current_price(symbol)
            financial = self.mcp_integration.get_financial_ratios(symbol)
            
            if not price_data or not financial:
                return None
            
            # 데이터 구성
            price = float(price_data.get('stck_prpr', 0))
            eps = float(financial.get('eps', 0) or 0)
            bps = float(financial.get('bps', 0) or 0)
            roe = float(financial.get('roe_val', 0) or 0)
            
            per = (price / eps) if eps > 0 else None
            pbr = (price / bps) if bps > 0 else None
            
            return {
                'symbol': symbol,
                'name': price_data.get('hts_kor_isnm', ''),
                'sector': price_data.get('bstp_kor_isnm', ''),
                'current_price': price,
                'per': per,
                'pbr': pbr,
                'roe': roe,
                'volume': int(price_data.get('acml_vol', 0)),
                'market_cap': float(price_data.get('hts_avls', 0)) * 100000000
            }
        except Exception as e:
            logger.error(f"MCP 종목 분석 실패: {symbol}, {e}")
            return None
    
    def get_market_rankings(self, ranking_type: str = "volume", limit: int = 100):
        """시장 순위 조회"""
        if not self.mcp_integration:
            return None
        
        try:
            if ranking_type == "volume":
                return self.mcp_integration.get_volume_ranking(limit)
            elif ranking_type == "market_cap":
                return self.mcp_integration.get_market_cap_ranking(limit)
            elif ranking_type == "per":
                return self.mcp_integration.get_per_ranking(limit)
            return None
        except Exception as e:
            logger.error(f"순위 조회 실패: {e}")
            return None
    
    def render_value_analysis(self, options):
        """가치주 분석 렌더링"""
        if options['analysis_mode'] == "전체 종목 스크리닝":
            self.screen_all_stocks(options)
        else:
            self.render_individual_analysis(options)
    
    def run(self):
        """메인 실행 함수"""
        try:
            self.render_header()
            options = self.render_sidebar()
            self._last_fast_latency = options.get('fast_latency', 0.7)
            
            # 탭 추가: MCP 고급 분석 + 기본 가치주 스크리닝
            if self.mcp_integration:
                tab1, tab2 = st.tabs(["🚀 MCP 실시간 분석", "🎯 가치주 스크리닝"])
                
                with tab1:
                    self.render_mcp_tab()
                
                with tab2:
                    self.render_value_analysis(options)
            else:
                st.warning("⚠️ MCP 통합이 비활성화되었습니다. 기본 가치주 스크리닝만 제공됩니다.")
                self.render_value_analysis(options)
            
        except Exception as e:
            st.error(f"시스템 실행 중 오류가 발생했습니다: {e}")
            logger.error(f"시스템 오류: {e}")
    
    def render_mcp_tab(self):
        """MCP 실시간 분석 탭 렌더링"""
        st.markdown("### 🚀 MCP KIS API 실시간 데이터")
        
        # 서브탭
        sub_tab1, sub_tab2, sub_tab3, sub_tab4, sub_tab5 = st.tabs([
            "💎 자동 가치주 발굴", "📈 실시간 시장", "🏢 섹터 분석", "📊 순위 분석", "🔍 종목 심화"
        ])
        
        with sub_tab1:
            self.render_mcp_value_finder()
        
        with sub_tab2:
            self.render_realtime_market()
        
        with sub_tab3:
            self.render_sector_analysis()
        
        with sub_tab4:
            self.render_ranking_analysis()
        
        with sub_tab5:
            self.render_stock_detail()
    
    def render_mcp_value_finder(self):
        """MCP 자동 가치주 발굴 렌더링"""
        st.markdown("#### 💎 MCP 실시간 가치주 자동 발굴")
        
        st.info("""
        **🚀 MCP가 수집하는 데이터:**
        - 거래량 순위 (실시간 활발한 종목)
        - 현재가 및 시가총액
        - 재무비율 (PER, PBR, ROE)
        - 섹터 정보
        - 부채비율, 유동비율
        
        **🎯 업종별 가치주 기준 (ChatGPT 권장):**
        - **금융**: PER ≤ 12, PBR ≤ 1.2, ROE ≥ 12%
        - **제조업**: PER ≤ 18, PBR ≤ 2.0, ROE ≥ 10%
        - **통신**: PER ≤ 15, PBR ≤ 2.0, ROE ≥ 8%
        - **건설**: PER ≤ 12, PBR ≤ 1.5, ROE ≥ 8%
        - **운송·전기전자**: PER ≤ 15, PBR ≤ 1.5, ROE ≥ 10%
        - 3개 기준 모두 충족 시 보너스 +25점
        """)
        
        st.success("✅ **업종별 기준 자동 적용**: 각 업종에 맞는 PER/PBR/ROE 기준으로 필터링됩니다.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            limit = st.number_input("발굴할 종목 수", min_value=5, max_value=50, value=20, step=5)
        
        with col2:
            candidate_pool = st.number_input("후보군 크기", min_value=50, max_value=500, value=300, step=50)
        
        # ✅ UI 기본값은 참고용으로만 표시 (실제로는 업종별 기준 사용)
        st.caption("💡 아래 값은 참고용입니다. 실제로는 업종별 기준이 적용됩니다.")
        
        col3, col4, col5, col6 = st.columns(4)
        
        with col3:
            per_max = st.number_input("참고: 최대 PER", min_value=5.0, max_value=50.0, value=15.0, step=1.0, disabled=True)
        
        with col4:
            pbr_max = st.number_input("참고: 최대 PBR", min_value=0.5, max_value=5.0, value=1.5, step=0.1, disabled=True)
        
        with col5:
            roe_min = st.number_input("참고: 최소 ROE (%)", min_value=0.0, max_value=30.0, value=10.0, step=1.0, disabled=True)
        
        with col6:
            min_volume = st.number_input("최소 거래량", min_value=10000, max_value=1000000, value=100000, step=10000)
        
        if st.button("🚀 MCP 가치주 자동 발굴 시작", type="primary", key="mcp_find"):
            with st.spinner(f"MCP로 {candidate_pool}개 종목 분석 중... (약 {candidate_pool//10}초 소요)"):
                start_time = time.time()
                
                # 기존 시스템에서 종목 유니버스 가져오기
                universe_data = self.get_stock_universe(max_count=candidate_pool)
                
                # ✅ 전체 데이터 전달 (중복 API 호출 방지!)
                # 기존: list(universe_data.keys()) → 코드만 전달 → mcp가 재조회 (600번 호출!)
                # 개선: universe_data 그대로 → 전체 데이터 전달 → mcp가 재사용 (300번 호출)
                stock_universe = universe_data if isinstance(universe_data, dict) else None
                
                if stock_universe:
                    logger.info(f"✅ 기존 시스템에서 {len(stock_universe)}개 종목 전체 데이터 확보 (중복 API 호출 방지)")
                else:
                    logger.warning("⚠️ 종목 유니버스 조회 실패, MCP 순위 API 사용")
                
                # MCP 가치주 발굴 (종목 유니버스 전달)
                value_stocks = self.mcp_integration.find_real_value_stocks(
                    limit=limit,
                    criteria={
                        'per_max': per_max,
                        'pbr_max': pbr_max,
                        'roe_min': roe_min,
                        'min_volume': min_volume
                    },
                    candidate_pool_size=candidate_pool,
                    stock_universe=stock_universe,  # ✅ 외부 유니버스 전달!
                    quality_check=False,  # ✅ 재무비율 API 호출 생략 (500 에러 방지)
                    min_trading_value=None,  # ✅ 거래대금 필터 비활성화 (데이터 불일치 회피)
                    momentum_scoring=False  # ⚠️ 차트 API 500 오류 지속 → 완전 비활성화
                )
                
                elapsed_time = time.time() - start_time
                
                if value_stocks and len(value_stocks) > 0:
                    # ✅ 목표 vs 실제 명확화 (사용자 권장)
                    actual_count = len(value_stocks)
                    target_count = limit
                    shortage_reason = ""
                    if actual_count < target_count:
                        shortage_reason = f" (목표 {target_count}개 → 실제 {actual_count}개: 섹터캡/비중상한/리스크제외)"
                    
                    st.success(f"✅ {actual_count}개 가치주 발굴 완료!{shortage_reason} (소요 시간: {elapsed_time:.1f}초)")
                    
                    # 요약 통계
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        # 목표 개수도 함께 표시
                        delta_text = f"목표 {target_count}개" if actual_count < target_count else None
                        st.metric("발굴 종목", f"{actual_count}개", delta=delta_text)
                    with col2:
                        # ✅ 0으로 나눔 방지 (크리티컬)
                        valid_scores = [s['score'] for s in value_stocks if isinstance(s.get('score'), (int, float)) and math.isfinite(s['score'])]
                        avg_score = (sum(valid_scores) / len(valid_scores)) if valid_scores else float('nan')
                        st.metric("평균 점수", self.fmt_ratio(avg_score, "점", 1))
                    with col3:
                        # ✅ 0으로 나눔 방지 (크리티컬)
                        valid_per = [s['per'] for s in value_stocks if isinstance(s.get('per'), (int, float)) and math.isfinite(s['per']) and s['per'] < 100]
                        avg_per = (sum(valid_per) / len(valid_per)) if valid_per else float('nan')
                        st.metric("평균 PER", self.fmt_ratio(avg_per, "배", 1))
                    with col4:
                        # ✅ 0으로 나눔 방지 (크리티컬)
                        valid_pbr = [s['pbr'] for s in value_stocks if isinstance(s.get('pbr'), (int, float)) and math.isfinite(s['pbr']) and s['pbr'] < 10]
                        avg_pbr = (sum(valid_pbr) / len(valid_pbr)) if valid_pbr else float('nan')
                        st.metric("평균 PBR", self.fmt_ratio(avg_pbr, "배", 2))
                    
                    # 섹터 분포
                    st.markdown("##### 📊 섹터 분포")
                    sector_counts = {}
                    for stock in value_stocks:
                        sector = stock.get('sector', '기타')
                        sector_counts[sector] = sector_counts.get(sector, 0) + 1
                    
                    sector_df = pd.DataFrame([
                        {'섹터': sector, '종목 수': count}
                        for sector, count in sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)
                    ])
                    st.dataframe(sector_df, use_container_width=True)
                    
                    # 상위 가치주
                    st.markdown("##### 🏆 상위 가치주 (점수순)")
                    df = pd.DataFrame([
                        {
                            '순위': idx + 1,
                            '종목코드': stock['symbol'],
                            '종목명': stock['name'],
                            '섹터': stock.get('sector', 'N/A'),
                            '현재가': f"{stock['price']:,.0f}",
                            'PER': f"{stock['per']:.1f}" if stock['per'] < 100 else "N/A",
                            'PBR': f"{stock['pbr']:.2f}" if stock['pbr'] < 10 else "N/A",
                            'ROE': f"{stock['roe']:.1f}%",
                            '거래량': f"{stock['volume']:,}",
                            '등락률': f"{stock['change_rate']:+.2f}%",
                            '점수': f"{stock['score']:.1f}",
                            '비중': f"{stock.get('proposed_weight', 0)*100:.1f}%",  # ✅ 신규!
                            '모멘텀': stock.get('momentum_period', '-'),  # ✅ 신규!
                            '시가총액': f"{stock.get('market_cap', 0)/1e8:,.0f}억"
                        }
                        for idx, stock in enumerate(value_stocks[:30])
                    ])
                    
                    st.dataframe(df, use_container_width=True, height=600)
                    
                    # CSV 다운로드
                    csv = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="📥 CSV 다운로드",
                        data=csv,
                        file_name=f"mcp_value_stocks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                    
                    # 상세 분석
                    st.markdown("##### 🔍 종목별 상세 분석")
                    selected_stock = st.selectbox(
                        "종목 선택",
                        options=[(s['symbol'], s['name']) for s in value_stocks],
                        format_func=lambda x: f"{x[1]} ({x[0]})"
                    )
                    
                    if selected_stock:
                        stock_detail = next((s for s in value_stocks if s['symbol'] == selected_stock[0]), None)
                        if stock_detail:
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("종목명", stock_detail['name'])
                                st.metric("섹터", stock_detail.get('sector', 'N/A'))
                            with col2:
                                st.metric("현재가", f"{stock_detail['price']:,.0f}원")
                                st.metric("시가총액", f"{stock_detail.get('market_cap', 0)/1e8:,.0f}억")
                            with col3:
                                st.metric("PER", f"{stock_detail['per']:.2f}배" if stock_detail['per'] < 100 else "N/A")
                                st.metric("PBR", f"{stock_detail['pbr']:.2f}배" if stock_detail['pbr'] < 10 else "N/A")
                            with col4:
                                st.metric("ROE", f"{stock_detail['roe']:.2f}%")
                                st.metric("가치 점수", f"{stock_detail['score']:.1f}/100점")
                            
                            # 추가 재무 정보
                            st.markdown("##### 💰 추가 재무 정보")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                debt_ratio = stock_detail.get('debt_ratio', 0)
                                st.metric("부채비율", f"{debt_ratio:.1f}%")
                            with col2:
                                current_ratio = stock_detail.get('current_ratio', 0)
                                st.metric("유동비율", f"{current_ratio:.1f}%")
                            with col3:
                                volume = stock_detail['volume']
                                st.metric("거래량", f"{volume:,}주")
                            
                            # 가치 평가
                            st.markdown("##### 📈 가치 평가")
                            score = stock_detail['score']
                            st.progress(score / 100)
                            
                            if score >= 80:
                                st.success("🌟 **매우 우수한 가치주**")
                            elif score >= 70:
                                st.info("✅ **우수한 가치주**")
                            elif score >= 60:
                                st.warning("⚠️ **괜찮은 가치주**")
                            else:
                                st.warning("📊 **평균적인 가치주**")
                
                else:
                    st.warning(f"""
                    ⚠️ 조건에 맞는 가치주를 찾을 수 없습니다.
                    
                    **조건 완화 제안:**
                    - PER 최대값 증가 (현재: {per_max})
                    - PBR 최대값 증가 (현재: {pbr_max})
                    - ROE 최소값 감소 (현재: {roe_min})
                    - 후보군 크기 증가 (현재: {candidate_pool})
                    """)
    
    def render_realtime_market(self):
        """실시간 시장 분석"""
        st.markdown("#### 📈 실시간 시장 분석")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 시장 상태")
            if st.button("조회", key="market_status"):
                with st.spinner("시장 상태 조회 중..."):
                    status = self.mcp_integration.get_market_status()
                    if status:
                        st.success(f"""
                        **상태**: {status.get('status', 'N/A')}  
                        **현재 시각**: {status.get('current_time', 'N/A')}  
                        **요일**: {status.get('weekday', 'N/A')}  
                        **장 운영**: {status.get('market_hours', 'N/A')}
                        """)
                    else:
                        st.error("시장 상태 정보를 가져올 수 없습니다")
        
        with col2:
            st.markdown("##### 주요 종목")
            if st.button("조회", key="major_stocks"):
                with st.spinner("주요 종목 조회 중..."):
                    # 거래량 상위 5개
                    rankings = self.mcp_integration.get_volume_ranking(limit=5)
                    if rankings:
                        st.dataframe({
                            '종목명': [r.get('hts_kor_isnm', '') for r in rankings],
                            '현재가': [f"{int(r.get('stck_prpr', 0)):,}" for r in rankings],
                            '등락률': [f"{float(r.get('prdy_ctrt', 0)):+.2f}%" for r in rankings],
                            '거래량': [f"{int(r.get('acml_vol', 0)):,}" for r in rankings]
                        })
                    else:
                        st.error("데이터를 가져올 수 없습니다")
    
    def render_sector_analysis(self):
        """섹터 분석"""
        st.markdown("#### 🏢 섹터별 분석")
        
        symbol = st.text_input("종목 코드", value="005930", key="sector_symbol")
        
        if st.button("분석", key="sector_analyze"):
            with st.spinner("섹터 분석 중..."):
                analysis = self.analyze_stock_with_mcp(symbol)
                if analysis:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("종목명", analysis.get('name', 'N/A'))
                        st.metric("섹터", analysis.get('sector', 'N/A'))
                    with col2:
                        st.metric("현재가", f"{analysis.get('current_price', 0):,.0f}원")
                        st.metric("거래량", f"{analysis.get('volume', 0):,}")
                    with col3:
                        per = analysis.get('per')
                        pbr = analysis.get('pbr')
                        st.metric("PER", f"{per:.2f}" if per else "N/A")
                        st.metric("PBR", f"{pbr:.2f}" if pbr else "N/A")
                else:
                    st.error("분석 실패")
    
    def render_ranking_analysis(self):
        """순위 분석"""
        st.markdown("#### 📊 순위 분석")
        
        ranking_type = st.selectbox(
            "순위 유형",
            ["거래량", "시가총액", "PER"],
            key="ranking_type"
        )
        
        limit = st.slider("조회 개수", 10, 100, 30, key="ranking_limit")
        
        if st.button("조회", key="ranking_query"):
            with st.spinner(f"{ranking_type} 순위 조회 중..."):
                type_map = {"거래량": "volume", "시가총액": "market_cap", "PER": "per"}
                rankings = self.get_market_rankings(type_map[ranking_type], limit)
                
                if rankings:
                    df = pd.DataFrame({
                        '순위': range(1, len(rankings) + 1),
                        '종목코드': [r.get('mksc_shrn_iscd', '') for r in rankings],
                        '종목명': [r.get('hts_kor_isnm', '') for r in rankings],
                        '현재가': [f"{int(r.get('stck_prpr', 0)):,}" for r in rankings],
                        '등락률': [f"{float(r.get('prdy_ctrt', 0)):+.2f}%" for r in rankings],
                        '거래량': [f"{int(r.get('acml_vol', 0)):,}" for r in rankings]
                    })
                    st.dataframe(df, use_container_width=True)
                else:
                    st.error("데이터를 가져올 수 없습니다")
    
    def render_stock_detail(self):
        """종목 심화 분석"""
        st.markdown("#### 🔍 종목 심화 분석")
        
        symbol = st.text_input("종목 코드", value="005930", key="detail_symbol")
        
        if st.button("분석", key="detail_analyze"):
            with st.spinner("심화 분석 중..."):
                analysis = self.analyze_stock_with_mcp(symbol)
                
                if analysis:
                    # 기본 정보
                    st.markdown("##### 기본 정보")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("종목명", analysis.get('name', 'N/A'))
                    with col2:
                        st.metric("현재가", f"{analysis.get('current_price', 0):,.0f}원")
                    with col3:
                        st.metric("시가총액", f"{analysis.get('market_cap', 0)/1e8:,.0f}억")
                    with col4:
                        st.metric("섹터", analysis.get('sector', 'N/A'))
                    
                    # 재무 비율
                    st.markdown("##### 재무 비율")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        per = analysis.get('per')
                        st.metric("PER", f"{per:.2f}" if per else "N/A")
                    with col2:
                        pbr = analysis.get('pbr')
                        st.metric("PBR", f"{pbr:.2f}" if pbr else "N/A")
                    with col3:
                        roe = analysis.get('roe', 0)
                        st.metric("ROE", f"{roe:.2f}%")
                    
                    # 가치 평가
                    if per and pbr:
                        st.markdown("##### 가치 평가")
                        score = 0
                        if per < 15: score += 30
                        elif per < 20: score += 20
                        if pbr < 1.0: score += 30
                        elif pbr < 1.5: score += 20
                        if roe > 15: score += 30
                        elif roe > 10: score += 20
                        
                        st.progress(score / 100)
                        st.info(f"**가치 점수**: {score}/100점")
                else:
                    st.error("분석 실패")

def main():
    """메인 실행 함수"""
    try:
        finder = ValueStockFinder()
        finder.run()
    except Exception as e:
        st.error(f"시스템 실행 중 오류가 발생했습니다: {e}")
        logger.error(f"시스템 오류: {e}")

if __name__ == "__main__":
    main()
