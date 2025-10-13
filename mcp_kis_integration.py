#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP KIS API 통합 모듈
실제 KIS API 호출을 MCP 스타일로 래핑
"""

import json
import time
import logging
import threading
import os
import random
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, List, Callable, Tuple

import requests
from kis_rate_limiter import KISGlobalRateLimiter  # ✅ 전역 Rate Limiter

logger = logging.getLogger(__name__)

# ✅ 민감 정보 키 목록 (로그 마스킹용)
SENSITIVE_HEADER_KEYS = ("appkey", "appsecret", "authorization", "password", "token")

# ✅ API 엔드포인트/TR_ID 상수화 (오타 방지 + 유지보수성)
API_ENDPOINTS = {
    # 기본시세
    'CURRENT_PRICE': ('quotations/inquire-price', 'FHKST01010100'),
    'ASKING_PRICE': ('quotations/inquire-asking-price-exp-ccn', 'FHKST01010200'),
    'CHART_DAILY': ('quotations/inquire-daily-itemchartprice', 'FHKST03010100'),
    'MULTI_PRICE': ('quotations/inquire-multi-price', 'FHKST11300006'),
    
    # 종목정보
    'STOCK_INFO': ('quotations/search-info', 'CTPF1604R'),
    'FINANCIAL_RATIO': ('finance/financial-ratio', 'FHKST66430300'),
    'INCOME_STATEMENT': ('quotations/inquire-income-statement', 'FHKST66430200'),
    'BALANCE_SHEET': ('quotations/inquire-balance-sheet', 'FHKST66430100'),
    'DAILY_PRICE': ('quotations/inquire-daily-price', 'FHKST01010400'),
    
    # 시세분석
    'INVESTOR_TREND': ('quotations/inquire-investor', 'FHKST01010900'),
    'INVESTOR_DAILY': ('quotations/inquire-daily-investorprice', 'FHKST03010200'),
    'PROGRAM_TRADE': ('quotations/program-trade-by-stock', 'FHKST01010600'),
    'CREDIT_BALANCE': ('quotations/credit-balance', 'FHKST13350200'),  # ✅ 수정 (FHKST133500200 → FHKST13350200)
    
    # 순위
    'MARKET_CAP_RANK': ('quotations/inquire-market-cap', 'FHPST01740000'),
    'VOLUME_RANK': ('quotations/volume-rank', 'FHPST01710000'),
    'PER_RANK': ('quotations/inquire-financial-ratio', 'FHPST01750000'),
    'UPDOWN_RANK': ('ranking/fluctuation', 'FHPST01700000'),
    'ASKING_RANK': ('ranking/asking-price-volume', 'FHPST01720000'),
    'DIVIDEND_RANK': ('ranking/dividend-rate', 'HHKDB13470100'),
}

# ✅ 섹터 보정 매핑 (KIS API 오류 수정)
SECTOR_CORRECTION_MAP = {
    # 지주회사 (KIS가 '금융'으로 잘못 분류하는 경우)
    '034730': '지주회사',  # SK
    '003550': '지주회사',  # LG
    '267250': '지주회사',  # HD현대
    '000080': '지주회사',  # 하이트진로홀딩스
    '001680': '지주회사',  # 대상홀딩스
    '003670': '철강',      # 포스코홀딩스 (지주회사이지만 철강 특성)
    '071050': '지주회사',  # 한국금융지주
    '000270': '운송장비',  # 기아 (정확한 분류)
    
    # 기타 잘못 분류된 종목들
    '402340': 'IT',        # SK스퀘어 (금융 아님, IT 투자회사)
    '035720': 'IT',        # 카카오 (금융 아님)
    '035420': 'IT',        # NAVER (금융 아님)
    
    # 참고: 금융지주는 금융이 맞음
    # '055550': '금융',  # 신한지주 - 금융 OK
    # '105560': '금융',  # KB금융 - 금융 OK  
    # '086790': '금융',  # 하나금융지주 - 금융 OK
    # '316140': '금융',  # 우리금융지주 - 금융 OK
    # '138040': '금융',  # 메리츠금융지주 - 금융 OK
}

# ✅ ETF/ETN/ETP 필터링 키워드 (보수적 필터링 - 일반 종목 오탐 방지)
ETF_KEYWORDS = (
    # 브랜드 (확실한 ETP) - 단어 경계 패딩으로 오탐 방지
    " KODEX ", " TIGER ", " ARIRANG ", " KOSEF ", " HANARO ", " KBSTAR ", " ACE ", " KINDEX ",
    # 상품 유형 (확실한 ETP)
    " ETF ", " ETN ", " ETP ",
    # 전략 키워드 (보수적)
    "레버리지", "인버스", "선물", "합성", "지수추종",
    # 주의: SMART는 일반 종목(스마트폰 등)에도 포함되어 제외
    # 주의: INDEX, TRUST, FUTURE는 일반 종목명에도 포함될 수 있어 제외
)

# ✅ 허용된 시장 구분
_ALLOWED_MARKETS = {"J", "Q", "NX", "UN"}

# ✅ 시장 코드 별칭 (사용자 친화적 입력 + 한글/변형 지원)
_MARKET_ALIAS = {
    "KOSPI": "J", "kospi": "J", "코스피": "J", "KOSPI200": "J",
    "KOSDAQ": "Q", "kosdaq": "Q", "코스닥": "Q",
    "J": "J", "Q": "Q",
    "NX": "NX", "nx": "NX", "NEXT": "NX", "next": "NX", "넥스트": "NX",
    "UN": "UN", "un": "UN", "통합": "UN", "전체": "UN"
}

class MCPKISIntegration:
    """MCP 스타일의 KIS API 통합 클래스 (KISDataProvider 방식 사용)"""
    
    # ✅ 모멘텀 기간 설정 (ChatGPT 권장 - 표기 일관성)
    MOM_LOOKBACK_D = 60  # 60D (3M) 또는 100D (5M) 중 택1
    MOM_LABEL = f"{int(MOM_LOOKBACK_D/20)}M({MOM_LOOKBACK_D}D)"  # 자동 라벨
    
    # ✅ 종목명→코드 캐시 (클래스 레벨, 프로세스 생명주기 동안 유지)
    _name_code_cache: Optional[Dict[str, str]] = None
    _cache_lock_static = threading.Lock()
    
    # ✅ 토큰 캐시 파일 경로 (환경변수 지원 + 플랫폼별 기본값)
    @staticmethod
    def _get_default_token_cache_path() -> str:
        """
        토큰 캐시 파일 경로 자동 결정
        
        우선순위:
        1. 환경변수 KIS_TOKEN_CACHE_DIR
        2. 사용자 홈 디렉토리 ~/.kis/
        3. 현재 디렉토리 (폴백)
        
        Note:
            파일명을 "token_cache.json"으로 통일 (운영 혼선 방지)
        """
        # 환경변수 확인
        cache_dir = os.environ.get("KIS_TOKEN_CACHE_DIR")
        if cache_dir:
            cache_path = Path(cache_dir)
            cache_path.mkdir(parents=True, exist_ok=True)
            return str(cache_path / "token_cache.json")  # ✅ 통일
        
        # 홈 디렉토리 사용 (멀티프로세스 안전)
        try:
            from pathlib import Path
            home = Path.home()
            kis_dir = home / ".kis"
            kis_dir.mkdir(parents=True, exist_ok=True)
            return str(kis_dir / "token_cache.json")  # ✅ 통일
        except Exception:
            # 폴백: 현재 디렉토리
            return "token_cache.json"  # ✅ 통일 (dot 제거)
    
    TOKEN_CACHE_FILE = _get_default_token_cache_path.__func__()
    
    def _init_session(self) -> requests.Session:
        """
        세션 초기화 (공통 로직, 중복 제거)
        
        Returns:
            설정된 requests.Session
        """
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0  # 직접 재시도 로직 구현
        )
        session.mount('https://', adapter)
        session.headers.update({
            'User-Agent': 'KIS-API-Client/1.0',
            'Connection': 'keep-alive',
            'Accept-Encoding': 'gzip, deflate'
        })
        return session
    
    def __init__(self, oauth_manager, request_interval: float = 0.5, timeout: tuple = (10, 30), backoff_cap: float = 30.0):
        """
        Args:
            request_interval: API 호출 간격 (기본 0.5초 = 2건/초, 안전 마진 90%)
            backoff_cap: 백오프 최대 시간 (기본 30초, 혼잡 시 과도한 재시도 방지)
        
        Note:
            공식 유량 제한:
            - 실전투자: 20건/초 (0.05초 간격)
            - 모의투자: 2건/초 (0.5초 간격)
            
            ⚠️ 초과 시 EGW00201 오류 및 AppKey 일시 차단 발생!
            
            안전 설정 (차단 방지, 90% 마진):
            - 실전투자: 0.5초 (2건/초) ← 현재 설정
            - 장시간 운영: 1.0초 (1건/초) 권장
            
            이전 권장값 0.10~0.15초는 50개 이상 연속 조회 시 차단 위험
        """
        self.oauth_manager = oauth_manager
        self.base_url = "https://openapi.koreainvestment.com:9443"
        
        # OAuth 매니저 호환성 처리 (appkey/app_key 모두 지원)
        appkey = getattr(oauth_manager, 'appkey', None) or getattr(oauth_manager, 'app_key', None)
        appsecret = getattr(oauth_manager, 'appsecret', None) or getattr(oauth_manager, 'app_secret', None)
        
        # 기존 KISDataProvider와 동일한 헤더 구성
        self.headers = {
            "content-type": "application/json; charset=utf-8",
            "appkey": appkey,
            "appsecret": appsecret,
        }
        
        # ✅ 세션 초기화 (공통 메서드 사용)
        self.session = self._init_session()
        
        # ✅ 멀티스레드 안전성을 위한 Lock
        self._lock = threading.Lock()
        self._cache_lock = threading.Lock()
        self._token_lock = threading.Lock()  # 토큰 캐시 파일 I/O 보호
        self._session_lock = threading.Lock()  # 세션 요청 보호 (requests.Session은 스레드 세이프 아님)
        
        # Rate limiting 설정 (인자화 + 적응형)
        # KIS API 공식 제한: 실전 20건/초, 모의 2건/초
        # ⚠️ 차단 방지: 0.5초 간격(2건/초, 90% 마진) - 장기 운영 안전값
        self.last_request_time = 0
        self.request_interval = request_interval  # 환경별 조절 가능
        self.timeout = timeout  # (connect, read) 타임아웃
        self.backoff_cap = backoff_cap  # 백오프 최대 시간 (초)
        self.consecutive_500_errors = 0
        self.max_consecutive_500_errors = 2  # ✅ 최대 연속 500 오류 횟수 (빠른 차단 감지)
        
        # ✅ 적응형 레이트 리밋 (500 오류 시 자동 슬로우다운)
        self._adaptive_rate = False  # 적응형 활성화 여부
        self._slow_mode_until = 0.0  # 슬로우 모드 종료 시각
        self._slow_mode_duration = 120.0  # 슬로우 모드 지속 시간 (2분, 차단 복구 대기)
        
        # ✅ 회로차단기 (Circuit Breaker) - 엔드포인트별 실패 카운터 + 쿨다운
        from collections import defaultdict
        self._fail_counts: Dict[str, int] = defaultdict(int)  # ✅ 미존재 키 자동 0 (KeyError 방지)
        self._fail_metadata: Dict[str, float] = defaultdict(float)  # 마지막 실패 시각
        self._success_metadata: Dict[str, float] = defaultdict(float)  # 마지막 성공 시각 (시간 기반 복구용)
        self.max_endpoint_failures = 5  # 엔드포인트별 최대 연속 실패
        self.circuit_cooldown = 60.0  # 회로차단 후 재시도 쿨다운 (초)
        self.circuit_recovery_time = 120.0  # 성공 유지 시 완전 복구 시간 (초)
        
        # ✅ 선호 엔드포인트 캐시 (첫 성공 경로 기억)
        self._preferred_endpoints: Dict[str, str] = {}  # 기능명 → 선호 엔드포인트
        
        # ✅ ETF 필터 (인스턴스 레벨 복사 - 전역 사이드이펙트 방지)
        self._etf_keywords: List[str] = list(ETF_KEYWORDS)  # 글로벌 복사
        self._etp_whitelist: set = set()  # 화이트리스트
        
        # ✅ 섹터 보정 맵 (인스턴스 레벨 복사 - 전역 사이드이펙트 방지)
        self._sector_overrides: Dict[str, str] = dict(SECTOR_CORRECTION_MAP)  # 글로벌 복사
        
        # 캐시 설정 (엔드포인트별 차등 TTL + 진짜 LRU)
        self.cache: OrderedDict[str, Tuple[dict, float]] = OrderedDict()  # (데이터, 타임스탬프)
        self.cache_maxsize = 2000  # 캐시 무한증가 방지
        self.cache_ttl = {
            'default': 60,       # 기본 1분
            'quotations': 10,    # 현재가 10초 (실시간성)
            'ranking': 300,      # 순위 5분 (자주 변하지 않음)
            'financial': 3600,   # 재무 1시간 (거의 변하지 않음)
            'dividend': 7200     # 배당 2시간 (거의 변하지 않음)
        }
        
        # ✅ 엔드포인트별 TTL 오버라이드 (운영 중 미세 조정)
        self.cache_ttl_overrides: Dict[str, float] = {
            'quotations/inquire-price': 5,  # 현재가는 5초로 더 짧게
            'quotations/inquire-asking-price-exp-ccn': 5,  # 호가도 5초
            'quote/news-title': 30,  # 뉴스 30초
            'quotations/news-title': 30,
            'news/news-title': 30,
            'quotations/inquire-daily-itemchartprice': 7200,  # ✅ 차트 2시간 (500 오류 방지 강화)
        }
    
    def _safe_params(self, params: Optional[Dict]) -> Dict:
        """
        로그 출력용 파라미터 마스킹 (PII/Key 유출 방지)
        
        Args:
            params: 원본 파라미터
            
        Returns:
            민감 정보가 마스킹된 딕셔너리
            
        Note:
            ✅ 대소문자 무관 마스킹 (AppKey, APPKEY, appkey 모두 처리)
            운영 환경에서 로그에 찍힐 때 appkey, appsecret, authorization 등 노출 방지
        """
        if not params:
            return {}
        
        redacted = {}
        for k, v in params.items():
            # ✅ 대소문자 무관 비교
            redacted[k] = '***REDACTED***' if str(k).lower() in SENSITIVE_HEADER_KEYS else v
        
        return redacted
    
    def _safe_headers(self, headers: Optional[Dict]) -> Dict:
        """
        로그 출력용 헤더 마스킹 (appkey/appsecret/authorization 등)
        
        Args:
            headers: 원본 헤더
            
        Returns:
            민감 정보가 마스킹된 딕셔너리
            
        Note:
            ✅ 대소문자 무관 마스킹 (Authorization, AUTHORIZATION, authorization 모두 처리)
            헤더를 로그에 찍을 때 민감 정보 노출 방지
        """
        if not headers:
            return {}
        
        redacted = {}
        for k, v in headers.items():
            # ✅ 대소문자 무관 비교
            redacted[k] = '***REDACTED***' if str(k).lower() in SENSITIVE_HEADER_KEYS else v
        
        return redacted
    
    def _safe_positive(self, value: Any) -> Optional[float]:
        """
        안전한 양수 변환 (0 또는 음수는 결측으로 처리)
        
        Args:
            value: 변환할 값
            
        Returns:
            양수이면 float, 아니면 None (결측)
            
        Note:
            PER/PBR 같은 비율 지표는 0 또는 음수가 의미 없음
            우선주/특수종목에서 0 반환 시 결측 처리
            
        Example:
            _safe_positive(15.5) → 15.5
            _safe_positive(0) → None
            _safe_positive(-10) → None
            _safe_positive("") → None
        """
        try:
            f = self._to_float(value, 0.0)
            return f if f > 0 else None
        except Exception:
            return None
    
    def _winsorize(self, value: Optional[float], lo: float, hi: float) -> Optional[float]:
        """
        ✅ v2.3: 윈저라이즈 (이상치 클램핑)
        
        과도한 이상치를 상한/하한으로 클램핑하여 하드 탈락 대신 소프트 감점
        
        Args:
            value: 원본 값
            lo: 하한
            hi: 상한
            
        Returns:
            클램핑된 값 (None이면 None 반환)
            
        Example:
            _winsorize(500, 0, 100) → 100  # 500 → 100 클램핑
            _winsorize(15, 0, 100) → 15    # 정상 범위
            _winsorize(None, 0, 100) → None
        """
        if value is None:
            return None
        return max(lo, min(value, hi))
    
    def _to_float(self, value: Any, default: float = 0.0, support_kor_units: bool = False) -> float:
        """
        안전한 float 변환 (콤마/공백/빈문자/단위 방어)
        KIS API 응답이 문자열("1,234.5", "3.5%", "1억원")인 경우 대응
        
        Args:
            value: 변환할 값
            default: 기본값
            support_kor_units: 한글 단위('조', '억', '만') 지원 여부
            
        Returns:
            float 값 (변환 실패 시 default)
            
        Example:
            _to_float("1,234.5") → 1234.5
            _to_float("3.5%") → 3.5
            _to_float("1억원") → 0.0 (기본)
            _to_float("3억5천만", support_kor_units=True) → 350000000.0
        """
        try:
            if value is None:
                return default
            if isinstance(value, (int, float)):
                return float(value)
            
            # ✅ 문자열 정규화: 콤마, 공백, %, 억원 등 제거
            s = str(value).strip().replace(',', '').replace('%', '').replace('억원', '')
            
            # ✅ 한글 단위 지원 (선택적)
            if support_kor_units:
                # '조' → e12, '억' → e8, '만' → e4
                s = s.replace('조', 'e12').replace('억', 'e8').replace('만', 'e4')
                # '천'은 혼동 우려로 제외 (e3보다 *1000 명시 권장)
            
            return float(s) if s else default
        except (ValueError, TypeError):
            return default
    
    def _first_output(self, data: Optional[dict]) -> Optional[list]:
        """
        API 응답에서 첫 번째 유효한 output 필드 반환
        
        Note:
            KIS API는 output, output1, output2 중 하나에 데이터를 담음
            이 헬퍼로 통일된 접근 가능
            
        Returns:
            output 리스트 또는 None
        """
        if not data:
            return None
        
        for key in ('output', 'output1', 'output2'):
            value = data.get(key)
            if value:
                return value
        
        return None
    
    def _trading_value_to_won(self, acml_tr_pbmn: Any) -> float:
        """
        누적거래대금 단위를 원(₩)으로 환산 (환경변수 지원)
        
        Args:
            acml_tr_pbmn: API 응답의 누적거래대금 필드
            
        Returns:
            거래대금 (원 단위)
            
        Note:
            환경변수 KIS_TRADING_VALUE_UNIT으로 단위 지정:
            - "won": 원 단위 그대로
            - "thousand": 천원 단위 (×1,000)
            - "million": 백만원 단위 (×1,000,000) ← 기본값
            
            실전 검증 방법:
            1. 종목 1개의 acml_tr_pbmn 값 확인
            2. 현재가 × 거래량과 비교
            3. 단위가 맞지 않으면 환경변수로 조정
            
        Example:
            # Windows
            set KIS_TRADING_VALUE_UNIT=million
            
            # Linux/Mac
            export KIS_TRADING_VALUE_UNIT=million
        """
        import os
        
        unit = os.environ.get("KIS_TRADING_VALUE_UNIT", "million").lower()
        base = self._to_float(acml_tr_pbmn, 0.0)
        
        if unit == "won":
            return base
        elif unit == "thousand":
            return base * 1_000
        else:  # "million" (기본값)
            return base * 1_000_000
    
    def _to_int(self, value: Any, default: int = 0) -> int:
        """
        안전한 int 변환 (NaN 방어 + _to_float 기반)
        
        Args:
            value: 변환할 값
            default: 기본값
            
        Returns:
            정수 (변환 실패 시 default)
        """
        try:
            f = self._to_float(value, default)
            # NaN 체크 (f == f는 NaN일 때 False)
            return int(f) if f == f else default
        except (ValueError, TypeError):
            return default
    
    def _norm_ratio(self, x: float) -> float:
        """
        재무비율 단위 정규화 (퍼센트 → 배수)
        
        Args:
            x: 원본 비율 (퍼센트일 수도, 배수일 수도 있음)
            
        Returns:
            배수 (예: 120% → 1.2)
            
        Note:
            KIS API는 유동비율, 부채비율 등을 퍼센트(120.0)로 주는 경우가 많음
            10을 초과하면 퍼센트로 간주하고 100으로 나눔
            
        Example:
            _norm_ratio(120.0) → 1.2  (120% → 1.2배)
            _norm_ratio(1.2) → 1.2    (이미 배수)
            _norm_ratio(0) → 0.0
        """
        if x is None or x != x:  # None or NaN
            return 0.0
        
        # 10을 초과하면 퍼센트일 가능성 높음 → /100
        return x / 100.0 if x > 10.0 else x
    
    def _normalize_params_for_cache_key(self, params: Optional[Dict]) -> Dict:
        """
        캐시 키 생성 전용 파라미터 정규화 (실제 요청에는 영향 없음!)
        
        캐시 키 일관성을 위한 정규화:
        1. 키 대문자화 (FID_COND_MRKT_DIV_CODE vs fid_cond_mrkt_div_code)
        2. 빈 문자열 → None (FID_INPUT_DATE_1: "" vs None)
        
        ⚠️ 주의: 이 함수는 캐시 키 생성에만 사용!
                실제 API 요청에는 원본 params를 그대로 전달해야 함
                (KIS API는 빈 문자열 = "당일/전체"로 해석하는 필드가 많음)
        """
        if not params:
            return {}
        
        normalized = {}
        for k, v in params.items():
            # 키 대문자화
            key = k.upper() if isinstance(k, str) else k
            
            # 값 정규화 (캐시 키 일관성)
            if isinstance(v, str) and v.strip() == "":
                # 빈 문자열 → None
                value = None
            elif isinstance(v, list):
                # 리스트 → 공백 조인 문자열 (멀티시세 케이스)
                value = " ".join(map(str, v))
            else:
                value = v
            
            normalized[key] = value
        
        return normalized
    
    def _validate_market(self, market_type: str) -> str:
        """
        시장 구분 코드 검증 + 별칭 지원 (오타 방지)
        
        Args:
            market_type: 시장 구분 (J/Q/NX/UN 또는 kospi/kosdaq 등 별칭)
            
        Returns:
            유효한 코드 (잘못된 경우 기본값 "J")
            
        Example:
            _validate_market("J") → "J"
            _validate_market("KOSPI") → "J"
            _validate_market("kosdaq") → "Q"
            _validate_market("NEXT") → "NX"
            _validate_market("UN") → "UN"
        """
        # 별칭 매핑 시도
        code = _MARKET_ALIAS.get((market_type or "").strip(), None)
        
        if code and code in _ALLOWED_MARKETS:
            return code
        
        # 별칭도 없고 유효하지도 않으면 경고 후 기본값
        logger.warning(f"⚠️ 잘못된 market_type '{market_type}', 기본값 'J' 사용")
        return "J"
    
    def _expand_market_types(self, market_type: str) -> List[str]:
        """
        시장 구분 코드를 실제 API 호출용 리스트로 확장
        
        Args:
            market_type: 시장 구분 (J/Q/NX/UN)
            
        Returns:
            API 호출용 시장 코드 리스트
            
        Note:
            UN(통합)은 KIS REST API가 직접 지원하지 않으므로
            J(KOSPI) + Q(KOSDAQ)로 쪼개서 병합 처리
            
        Example:
            _expand_market_types("J") → ["J"]
            _expand_market_types("UN") → ["J", "Q"]
            _expand_market_types("Q") → ["Q"]
        """
        code = self._validate_market(market_type)
        
        # UN(통합)은 KOSPI + KOSDAQ으로 확장
        if code == "UN":
            return ["J", "Q"]
        
        return [code]
    
    def _is_etp(self, name: str) -> bool:
        """
        ETF/ETN/ETP 여부 판단 (강화된 필터 + 화이트리스트 지원)
        
        Args:
            name: 종목명
            
        Returns:
            ETF/ETN/ETP이면 True
            
        Note:
            ✅ 인스턴스 레벨 필터 (전역 사이드이펙트 없음)
            ✅ 단어 경계 패딩으로 오탐 방지 (SMART 등)
            update_etp_filters()로 화이트리스트/블랙리스트 관리 가능
        """
        if not name:
            return False
        
        # ✅ 앞뒤 공백 패딩 (단어 경계 매칭용)
        upper_name = f" {name.upper()} "
        
        # 화이트리스트 체크 (오탐 방지)
        for pattern in self._etp_whitelist:
            if pattern.upper() in upper_name:
                return False  # 화이트리스트에 있으면 ETP 아님
        
        # ✅ 인스턴스 필드 사용 (전역 오염 방지 + 단어 경계 매칭)
        return any(keyword in upper_name for keyword in self._etf_keywords)
    
    def _is_preferred_stock(self, symbol: str, name: str) -> bool:
        """
        ✅ v2.3: 우선주 여부 판단
        
        Args:
            symbol: 종목코드 (6자리)
            name: 종목명
            
        Returns:
            우선주이면 True
            
        Note:
            KOSPI 우선주 규칙: 종목코드 끝자리가 5, 7이거나 종목명에 '우' 포함
        """
        if not symbol or not name:
            return False
        
        # 1. 종목코드 끝자리 체크 (5, 7 = 우선주)
        if len(symbol) == 6 and symbol[-1] in ('5', '7'):
            return True
        
        # 2. 종목명에 '우' 포함 (예: '삼성전자우', 'SK텔레콤우')
        if '우' in name and not ('우리' in name or '우성' in name):
            return True
        
        return False
    
    def _compute_per_pbr(self, price: float, eps: float, bps: float) -> Tuple[Optional[float], Optional[float]]:
        """
        PER/PBR 계산 헬퍼 (중복 로직 제거 + 0/음수 방어)
        
        Args:
            price: 주가
            eps: 주당순이익
            bps: 주당순자산
            
        Returns:
            (PER, PBR) 튜플 (계산 불가 시 None)
        """
        # ✅ 분자/분모 모두 양수 확인 (비정상 음수 데이터 방어)
        per = (price / eps) if eps and eps > 0 and price > 0 else None
        pbr = (price / bps) if bps and bps > 0 and price > 0 else None
        return per, pbr
    
    def _normalize_sector(self, sector: str) -> str:
        """
        섹터명 표준화 (보정·보너스 일관성 + 섹터 캡 정확성)
        
        Note:
            ✅ 보험 → 금융 통합 (섹터 캡 정확성)
            ✅ 지주회사 명시적 분리
            ✅ KIS 섹터명 다양성 대응
            ✅ ChatGPT 권장: NFC 정규화 + 전각/반각 통일 + 공백 제거
        """
        if not sector:
            return '기타'
        
        # ✅ 1단계: 전처리 강화 (사용자 권장 - 완벽한 정규화)
        import unicodedata
        import re
        
        original = sector.strip()
        
        # NFC 정규화 (한글 조합 통일)
        s = unicodedata.normalize('NFC', original)
        
        # ✅ 공백 완전 제거 (앞뒤 + 중간 모두)
        s = s.strip().replace(" ", "").replace("\t", "").replace("\n", "")
        
        # ✅ 구분점 완전 제거 (모든 변형 흡수)
        # 전기·전자, 전기•전자, 전기-전자, 전기/전자, 전기.전자 등
        s = re.sub(r"[·•\.\,/\-\u2219\u2027\u00B7\u00B7]", "", s)
        
        # 소문자화 (매칭 용이)
        s_lower = s.lower()
        
        # ✅ 정규식 테이블 매칭 (사용자 권장 - 최우선)
        regex_table = {
            r"^전기전자$": "전기전자",
            r"^(it서비스|it|소프트웨어|인터넷)$": "기술업",
            r"^(운송장비부품|운송장비)$": "운송장비",
            r"^(운송|해운|항공)$": "운송",
            r"^금융$": "금융",
            r"^(전기가스|공익)$": "전기가스",
            r"^(바이오|제약)$": "바이오/제약",
            r"^(제조업|기계장비|산업재)$": "제조업",
            r"^지주회사$": "지주회사",
            r"^(건설|건설자재)$": "건설",
            r"^(통신|통신서비스)$": "통신",
        }
        
        for pattern, standard in regex_table.items():
            if re.match(pattern, s_lower):
                return standard  # 정규식 매칭 성공 → 즉시 반환
        
        # ✅ 디버깅 (첫 5회만)
        if not hasattr(self, '_sector_debug_count'):
            self._sector_debug_count = 0
        if self._sector_debug_count < 5:
            logger.info(f"🔍 섹터 정규화: '{original}' → s='{s}', s_lower='{s_lower}'")
            self._sector_debug_count += 1
        
        # ✅ 1단계: 우선순위 매핑 (명확한 분류)
        priority_mapping = {
            # 금융 (보험·증권·은행 통합) - ✅ 자기 자신 매핑 포함!
            '금융': '금융',  # ✅ 핵심! API에서 '금융' 반환 시 대응
            '금융업': '금융',
            '보험': '금융',
            '손해보험': '금융',
            '생명보험': '금융',
            '증권': '금융',
            '은행': '금융',
            '카드': '금융',
            '캐피탈': '금융',
            '저축은행': '금융',
            
            # ✅ IT/기술업 (ChatGPT 권장 추가)
            'it': 'IT',
            'it서비스': 'IT',
            'itservice': 'IT',
            '정보기술': 'IT',
            '기술업': 'IT',
            '소프트웨어': 'IT',
            'software': 'IT',
            
            # 특수 섹터 - ✅ 자기 자신 매핑 포함
            '지주회사': '지주회사',
            '투자': '지주회사',
            
            # 산업 섹터 - ✅ 자기 자신 매핑 포함
            '전기전자': '전기전자',  # ✅ 자기 자신
            '전기·전자': '전기전자',
            '전기/전자': '전기전자',
            
            '전기가스': '전기가스',  # ✅ 자기 자신
            '전기·가스': '전기가스',
            
            '운송장비': '운송장비',  # ✅ 자기 자신
            '운송장비·부품': '운송장비',
            '자동차': '운송장비',
            
            '운송': '운송',  # ✅ 자기 자신
            '운수창고': '운송',
            '운수/창고': '운송',
            '운송·창고': '운송',
            '항공': '운송',
            '해운': '운송',
            
            '통신': '통신',  # ✅ 자기 자신
            '통신업': '통신',
            
            '서비스': '서비스',  # ✅ 자기 자신
            '서비스업': '서비스',
            
            '제조업': '제조업',  # ✅ 자기 자신
            '제조': '제조업',
            '기계·장비': '제조업',
            '기계': '제조업',
            
            # ✅ 추가 매핑
            '바이오/제약': '바이오/제약',  # ✅ 자기 자신
            '제약': '바이오/제약',
            '바이오': '바이오/제약',
        }
        
        # ✅ 우선순위 매핑 체크 (원본 우선, 정규화 후보)
        for keyword, standard in priority_mapping.items():
            # 원본 sector에 키워드가 포함되어 있으면 즉시 매칭 (정규화 전 원본)
            if keyword in original:
                if self._sector_debug_count < 5:
                    logger.info(f"  → 매칭: '{keyword}' in '{original}' → '{standard}'")
                return standard
            
            # 정규화된 s에 키워드가 포함되어 있으면 매칭
            if keyword in s:
                if self._sector_debug_count < 5:
                    logger.info(f"  → 매칭: '{keyword}' in '{s}' → '{standard}'")
                return standard
            
            # 정규화된 s_lower에 정규화된 keyword가 포함되어 있으면 매칭
            keyword_norm = keyword.lower().replace('·', '').replace('/', '').replace(' ', '')
            if keyword_norm in s_lower:
                if self._sector_debug_count < 5:
                    logger.info(f"  → 매칭: '{keyword_norm}' in '{s_lower}' → '{standard}'")
                return standard
        
        # ✅ 2단계: 폴백 (매핑 안 된 경우 '기타')
        if s:
            logger.debug(f"⚠️ 섹터 매핑 누락: '{original}' (정규화: '{s}') → '기타'로 분류")
            return '기타'
        
        return '기타'
    
    # ✅ 클래스 레벨 캐시 (마스터파일 섹터 맵)
    _master_sector_cache: Dict[str, str] = {}
    
    # ✅ 명시적 오버라이드 (ChatGPT 권장 - 오분류 방지)
    EXPLICIT_SECTOR_OVERRIDES = {
        # ✅ 명확한 섹터 분류 (섹터 매핑 오류 방지)
        "033780": "필수소비재",  # KT&G (담배)
        "047810": "제조업",      # 한국항공우주산업 (방산)
        "373220": "전기전자",    # LG에너지솔루션 (2차전지)
        
        # ✅ 금융 (은행/증권/보험/지주)
        "316140": "금융",        # 우리금융지주
        "024110": "금융",        # 기업은행
        "086790": "금융",        # 하나금융지주
        "055550": "금융",        # 신한지주
        "105560": "금융",        # KB금융
        "138040": "금융",        # 메리츠금융지주
        "000810": "금융",        # 삼성화재
        "032830": "금융",        # 삼성생명
        
        # ✅ 건설
        "028260": "건설",        # 삼성물산 (건설부문)
        "047040": "건설",        # 대우건설
        "000720": "건설",        # 현대건설
        
        # ✅ 운송장비 (자동차)
        "005380": "운송장비",    # 현대차
        "000270": "운송장비",    # 기아
        "012330": "운송장비",    # 현대모비스
        
        # ✅ 운송 (해운/항공/물류)
        "086280": "운송",        # 현대글로비스
        "011200": "운송",        # HMM
        
        # ✅ 통신
        "017670": "통신",        # SK텔레콤
        "030200": "통신",        # KT
        "032640": "통신",        # LG유플러스
        
        # ✅ 전기전자
        "005930": "전기전자",    # 삼성전자
        "000660": "전기전자",    # SK하이닉스
        "006400": "전기전자",    # 삼성SDI
        "018260": "전기전자",    # 삼성에스디에스
        "066570": "전기전자",    # LG전자
        "009150": "전기전자",    # 삼성전기
    }
    
    def _get_sector_specific_criteria(self, sector: str) -> Dict[str, float]:
        """✅ 업종별 가치주 평가 기준 반환 (ChatGPT 권장)"""
        sector_criteria = {
            '금융': {'per_max': 12.0, 'pbr_max': 1.2, 'roe_min': 12.0},
            '금융업': {'per_max': 12.0, 'pbr_max': 1.2, 'roe_min': 12.0},
            '기술업': {'per_max': 25.0, 'pbr_max': 3.0, 'roe_min': 15.0},
            'IT': {'per_max': 25.0, 'pbr_max': 3.0, 'roe_min': 15.0},
            '제조업': {'per_max': 18.0, 'pbr_max': 2.0, 'roe_min': 10.0},
            '바이오/제약': {'per_max': 50.0, 'pbr_max': 5.0, 'roe_min': 8.0},
            '통신': {'per_max': 15.0, 'pbr_max': 2.0, 'roe_min': 8.0},
            '통신업': {'per_max': 15.0, 'pbr_max': 2.0, 'roe_min': 8.0},
            '건설': {'per_max': 12.0, 'pbr_max': 1.5, 'roe_min': 8.0},
            '건설업': {'per_max': 12.0, 'pbr_max': 1.5, 'roe_min': 8.0},
            '운송': {'per_max': 15.0, 'pbr_max': 1.5, 'roe_min': 10.0},
            '운송장비': {'per_max': 15.0, 'pbr_max': 1.5, 'roe_min': 10.0},
            '전기전자': {'per_max': 15.0, 'pbr_max': 1.5, 'roe_min': 10.0},
        }
        # 정규화된 섹터명으로 매칭 시도
        normalized = sector.strip().replace(' ', '').lower() if sector else ''
        for key, val in sector_criteria.items():
            if key.replace(' ', '').lower() in normalized or normalized in key.replace(' ', '').lower():
                return val
        # 기본값
        return {'per_max': 15.0, 'pbr_max': 1.5, 'roe_min': 10.0}
    
    def _get_sector_for_symbol(self, symbol: str, stock_name: str = "") -> str:
        """
        종목의 섹터 조회 + 오버라이드 + 표준화 (원스톱)
        
        Args:
            symbol: 종목코드
            stock_name: 종목명 (선택, 폴백용)
            
        Returns:
            정규화된 섹터명
            
        Note:
            1. 인스턴스 오버라이드 우선
            2. 마스터파일 섹터 (KIS 권장!)
            3. API 조회 폴백
            4. 종목명 기반 폴백 (ChatGPT 권장)
            5. 표준화 적용
        """
        sector = ""
        
        # 0. ✅ 명시적 오버라이드 (최최우선, ChatGPT 권장)
        if symbol in self.EXPLICIT_SECTOR_OVERRIDES:
            sector = self.EXPLICIT_SECTOR_OVERRIDES[symbol]
            logger.debug(f"✅ 명시적 오버라이드: {symbol} → {sector}")
            return sector  # 이미 표준화됨
        
        # 1. 인스턴스 오버라이드 확인
        if symbol in self._sector_overrides:
            sector = self._sector_overrides[symbol]
            return self._normalize_sector(sector)
        
        # 2. ✅ 마스터파일 섹터 조회 (KIS 권장, 최우선!)
        if not MCPKISIntegration._master_sector_cache:
            # 최초 1회만 로드
            try:
                import pandas as pd
                df = pd.read_excel('kospi_code.xlsx')
                
                # ✅ KOSPI200 섹터업종 코드 → 섹터명 매핑 (KIS 공식)
                kospi200_sector_map = {
                    '1': '건설',
                    '2': '운송장비',  # 조선
                    '5': '전기전자',  # IT
                    '6': '금융',
                    '7': '제조업',  # 음식료
                    '9': '제조업',  # 산업재
                    'A': '바이오/제약',
                    'B': 'IT',  # 게임/미디어
                }
                
                # ✅ 지수업종 대분류 코드 → 섹터명 매핑
                industry_large_map = {
                    16: '제조업',  # 섬유의복
                    19: '유통',
                    21: '지주회사',
                    26: '건설',
                    27: '제조업',  # 전기전자/기계
                    29: 'IT',  # 서비스업
                    30: 'IT',  # 오락문화
                }
                
                for _, row in df.iterrows():
                    code = str(row.get('단축코드', '')).strip()
                    if not code or len(code) != 6 or not code.isdigit():
                        continue
                    
                    sector = None
                    
                    # ✅ 1순위: KRX 섹터 플래그 (가장 정확!)
                    if row.get('KRX은행') == 'Y' or row.get('KRX증권') == 'Y' or row.get('KRX섹터_보험') == 'Y':
                        sector = '금융'
                    elif row.get('KRX자동차') == 'Y':
                        sector = '운송장비'
                    elif row.get('KRX반도체') == 'Y':
                        sector = '전기전자'
                    elif row.get('KRX미디어통신') == 'Y':
                        sector = '통신'
                    elif row.get('KRX섹터_운송') == 'Y' or row.get('KRX선박') == 'Y':
                        sector = '운송'
                    elif row.get('KRX바이오') == 'Y':
                        sector = '바이오/제약'
                    elif row.get('KRX에너지화학') == 'Y':
                        sector = '제조업'
                    elif row.get('KRX철강') == 'Y':
                        sector = '제조업'
                    elif row.get('KRX건설') == 'Y':
                        sector = '건설'
                    
                    # ✅ 2순위: KOSPI200 섹터업종 코드
                    if not sector:
                        kospi200_code = str(row.get('KOSPI200섹터업종', '')).strip()
                        if kospi200_code and kospi200_code != '0':
                            sector = kospi200_sector_map.get(kospi200_code)
                    
                    # ✅ 3순위: 지수업종 대분류
                    if not sector:
                        large_code = row.get('지수업종대분류')
                        if large_code and large_code != 0:
                            sector = industry_large_map.get(large_code)
                    
                    # 캐시에 저장
                    if sector:
                        MCPKISIntegration._master_sector_cache[code] = sector
                
                logger.info(f"✅ 마스터파일 섹터 캐시 로드: {len(MCPKISIntegration._master_sector_cache)}개")
            except Exception as e:
                logger.warning(f"⚠️ 마스터파일 섹터 로드 실패: {e}")
        
        # 마스터파일에서 조회
        if symbol in MCPKISIntegration._master_sector_cache:
            sector = MCPKISIntegration._master_sector_cache[symbol]
            logger.debug(f"✅ 마스터파일 섹터: {symbol} → {sector}")
            # ✅ "제조업"이 아니면 바로 반환 (정확한 분류)
            # "제조업"은 종목명 폴백으로 정제 필요 (과대매칭 보정)
            if sector != "제조업":
                return sector  # 이미 표준화됨
        
        # 3. ✅ API 조회 완전 비활성화 (500 오류 방지)
        # ⚠️ 대량 종목 처리 시 API 호출하면 AppKey 차단 발생!
        # → 마스터파일 + 종목명 폴백만 사용
        if sector and sector.strip() and sector.strip() != "제조업":
            logger.debug(f"✅ {symbol} 섹터 이미 제공됨 ('{sector}'), API 조회 생략")
        # API 조회 부분 완전 제거!
        
        # 3. ✅ 종목명 기반 폴백 (ChatGPT 권장 - 섹터 API 실패 대응)
        # ✅ "제조업"도 폴백 대상에 포함 (과대매칭 보정)
        if (not sector or sector.strip() == "" or sector.strip() == "제조업") and stock_name:
            # ✅ "보통주" 제거 후 매칭
            import re
            name_clean = stock_name.replace('보통주', '').replace('우선주', '').strip()
            
            # ✅ 정규식 기반 키워드 매칭 (우선순위 순서, ChatGPT 권장)
            NAME_KEYWORDS = [
                (r"(금융지주|은행|생명보험|손해보험|손보|생보|증권|카드|캐피탈|저축은행|자산운용)", "금융"),
                # ✅ 통신 (KT&G 제외)
                (r"(?:^| )(kt|케이티|sk텔레콤|lg유플러스)(?:$| )(?!.*앤지)(?!.*&g)", "통신"),
                # ✅ 담배/식품 (우선 처리)
                (r"(케이티앤지|kt&g|담배|필수소비재)", "필수소비재"),
                # ✅ 방산/항공우주
                (r"(항공우주|korea aerospace|kai|방산|미사일|레이다)", "제조업"),
                # 2차전지
                (r"(에너지솔루션|배터리|2차전지)", "전기전자"),
                (r"(반도체|하이닉스|sdi|전자|디스플레이)", "전기전자"),
                (r"(자동차|현대차|기아|모비스|운송장비|부품)", "운송장비"),
                (r"(항공|대한항공|아시아나|해운|hmm|에이치엠엠|물류|로지스틱스|글로비스)", "운송"),
                (r"(전력|가스|유틸리티|전기공사|한전|한국전력)", "전기가스"),
                (r"(지주|홀딩스|holdings)", "지주회사"),
                (r"(바이오|제약|pharma|bio|cell|트리온|셀트리온)", "바이오/제약"),
                # ↓ 가장 마지막: 과대매칭 방지 (ChatGPT 권장)
                (r"(기계|장비|중공업|로템|케미칼|화학)", "제조업"),
            ]
            
            for pattern, sec in NAME_KEYWORDS:
                if re.search(pattern, name_clean, re.IGNORECASE):
                    sector = sec
                    logger.info(f"✅ 종목명 폴백: {symbol} {name_clean} → {sec}")
                    break
        
        # 4. 표준화
        result = self._normalize_sector(sector) if sector else "기타"
        
        # ✅ 디버깅 (매핑 추적)
        if result == '기타' and stock_name and len(stock_name) > 2:
            logger.warning(f"⚠️ 섹터 미분류: {symbol} '{stock_name}' (API섹터: '{sector}') → 기타")
        
        return result
    
    def update_sector_overrides(self, overrides: Dict[str, str]):
        """
        섹터 보정 매핑 외부 주입 (운영 중 확장)
        
        Args:
            overrides: 종목코드 → 섹터명 매핑
            
        Example:
            mcp.update_sector_overrides({
                '123456': 'IT',  # 새로운 보정
                '789012': '바이오'  # 추가 보정
            })
            
        Note:
            ✅ 인스턴스 레벨 맵 (전역 사이드이펙트 없음)
        """
        self._sector_overrides.update(overrides)
        logger.debug(f"섹터 보정 매핑 업데이트: {len(overrides)}개 추가")
    
    def update_etp_filters(self, allow_list: List[str] = None, block_list: List[str] = None):
        """
        ETF/ETN/ETP 필터 외부 주입 (오탐/미탐 대응)
        
        Args:
            allow_list: ETF로 분류되지 않을 종목명 패턴 (화이트리스트)
            block_list: 강제로 ETF로 분류할 종목명 패턴 (블랙리스트)
            
        Example:
            # 오탐 방지 (ETF가 아닌데 필터링된 경우)
            mcp.update_etp_filters(allow_list=['TR제약', 'ETN산업'])
            
            # 미탐 방지 (ETF인데 통과한 경우)
            mcp.update_etp_filters(block_list=['신종ETP', '특별상품'])
            
        Note:
            ✅ 인스턴스 레벨 필터 (전역 사이드이펙트 없음)
            ✅ 블랙리스트는 자동으로 공백 패딩 (단어 경계 매칭)
            운영 중 발견되는 오탐/미탐 케이스를 즉시 대응 가능
        """
        if allow_list:
            self._etp_whitelist.update(allow_list)
            logger.info(f"ETF 화이트리스트 추가: {allow_list}")
        
        if block_list:
            # ✅ 공백 패딩 추가 (단어 경계 매칭용)
            padded = [f" {keyword.strip()} " for keyword in block_list]
            self._etf_keywords.extend(padded)
            logger.info(f"ETF 블랙리스트 추가: {block_list}")
    
    def search_stock_by_name(self, name: str) -> Optional[str]:
        """
        종목명으로 종목코드 검색 (메모리 캐시 + 디스크 I/O 최소화)
        
        Args:
            name: 종목명 (부분 일치 가능)
            
        Returns:
            종목코드 (6자리) 또는 None
            
        Note:
            1. 메모리 캐시 우선 (프로세스 생명주기 동안 유지)
            2. KOSPI 마스터 파일 (첫 호출 시만 로드)
            3. 시가총액 API (폴백)
            
        Example:
            code = mcp.search_stock_by_name("삼성전자")  # "005930"
            code = mcp.search_stock_by_name("시프트업")   # "462870"
        """
        try:
            if not name or not isinstance(name, str):
                return None
            
            search_name = name.strip().upper()
            
            # ✅ 0단계: 메모리 캐시 확인 (가장 빠름, < 0.001초)
            with MCPKISIntegration._cache_lock_static:
                if MCPKISIntegration._name_code_cache is not None:
                    # 정확한 일치
                    if search_name in MCPKISIntegration._name_code_cache:
                        code = MCPKISIntegration._name_code_cache[search_name]
                        logger.debug(f"✅ 캐시 히트 (정확): '{name}' → {code}")
                        return code
                    
                    # ✅ 부분 일치 스코어링 (비결정성 제거)
                    candidates = []
                    for cached_name, cached_code in MCPKISIntegration._name_code_cache.items():
                        if search_name in cached_name:
                            # 전방 일치가 더 높은 점수
                            score = 3 if cached_name.startswith(search_name) else 1
                            # 길이 차이가 작을수록 높은 점수
                            score += 1.0 / (1 + abs(len(search_name) - len(cached_name)))
                            candidates.append((score, len(cached_name), cached_name, cached_code))
                        elif cached_name in search_name:
                            score = 2 if search_name.startswith(cached_name) else 1
                            score += 1.0 / (1 + abs(len(search_name) - len(cached_name)))
                            candidates.append((score, len(cached_name), cached_name, cached_code))
                    
                    if candidates:
                        # 스코어 내림차순, 길이 오름차순 정렬 (가장 유사한 것 우선)
                        candidates.sort(key=lambda x: (-x[0], x[1]))
                        best_match = candidates[0]
                        logger.debug(f"✅ 캐시 히트 (부분, 스코어={best_match[0]:.1f}): '{name}' → {best_match[3]} ({best_match[2]})")
                        return best_match[3]
            
            # 1단계: KOSPI 마스터 파일에서 검색 + 캐시 구축 (첫 호출만)
            try:
                import pandas as pd
                
                kospi_file = Path("kospi_code.xlsx")
                if kospi_file.exists():
                    # ✅ 캐시 구축 (프로세스 레벨, 1회만)
                    with MCPKISIntegration._cache_lock_static:
                        if MCPKISIntegration._name_code_cache is None:
                            logger.info("📚 종목명 캐시 구축 중... (Excel 로드)")
                            
                            try:
                                df = pd.read_excel(kospi_file)
                                
                                if '한글명' in df.columns and '단축코드' in df.columns:
                                    temp_cache = {}
                                    for _, row in df.iterrows():
                                        stock_name = str(row['한글명']).upper()
                                        stock_code = str(row['단축코드']).zfill(6)
                                        temp_cache[stock_name] = stock_code
                                    
                                    # ✅ 성공 시에만 전역 캐시 할당
                                    MCPKISIntegration._name_code_cache = temp_cache
                                    logger.info(f"✅ 종목명 캐시 구축 완료: {len(MCPKISIntegration._name_code_cache)}개")
                                else:
                                    logger.warning("⚠️ KOSPI 마스터 파일 컬럼 불일치 (한글명/단축코드 없음)")
                                    MCPKISIntegration._name_code_cache = {}  # 빈 캐시로 초기화
                                    
                            except Exception as load_err:
                                logger.warning(f"⚠️ KOSPI 마스터 파일 로딩 실패, 캐시 무효화: {load_err}")
                                MCPKISIntegration._name_code_cache = {}  # 빈 캐시로 초기화
                    
                    # 캐시에서 재검색 (재귀 호출) - 빈 캐시여도 안전
                    if MCPKISIntegration._name_code_cache:
                        return self.search_stock_by_name(name)
                    
            except Exception as e:
                logger.debug(f"KOSPI 마스터 파일 검색 실패: {e}")
            
            # 2단계: 시가총액 상위 종목에서 검색 (API 사용)
            logger.debug(f"시가총액 API로 종목명 검색 시도: '{name}'")
            market_cap_stocks = self.get_market_cap_ranking(limit=500)
            
            if market_cap_stocks:
                for stock in market_cap_stocks:
                    stock_name = (stock.get('hts_kor_isnm') or '').upper()
                    if search_name in stock_name or stock_name in search_name:
                        code = stock.get('mksc_shrn_iscd')
                        if code:
                            logger.debug(f"✅ 종목명 검색 성공 (API): '{name}' → {code} ({stock.get('hts_kor_isnm')})")
                            return code
            
            logger.warning(f"⚠️ 종목명 검색 실패: '{name}' (코드를 찾을 수 없음)")
            return None
            
        except Exception as e:
            logger.error(f"종목명 검색 중 오류: {name}, {e}")
            return None
    
    def _resolve_symbol(self, code_or_name: str) -> Optional[str]:
        """
        종목코드 또는 종목명을 종목코드로 변환
        
        Args:
            code_or_name: 종목코드(6자리) 또는 종목명
            
        Returns:
            종목코드 (6자리) 또는 None
            
        Example:
            code = mcp._resolve_symbol("005930")    # "005930" (그대로)
            code = mcp._resolve_symbol("삼성전자")   # "005930" (변환)
        """
        try:
            input_str = str(code_or_name).strip()
            
            # 이미 6자리 숫자면 종목코드로 간주
            if len(input_str) == 6 and input_str.isdigit():
                return input_str
            
            # 종목명으로 검색
            return self.search_stock_by_name(input_str)
            
        except Exception as e:
            logger.error(f"종목 코드/이름 변환 실패: {code_or_name}, {e}")
            return None
    
    def _rate_limit(self):
        """API 요청 속도를 제어합니다 (전역 Rate Limiter 사용)"""
        # ✅ 전역 Rate Limiter 사용 - KISDataProvider와 동일한 Lock 공유
        # 적응형 레이트 리밋 (슬로우 모드)
        if self._adaptive_rate and time.time() < self._slow_mode_until:
            interval = self.request_interval * 4.0  # 4배 느리게
            logger.debug(f"🐢 슬로우 모드: 간격 {interval:.2f}초 (남은 시간: {self._slow_mode_until - time.time():.1f}초)")
        else:
            interval = self.request_interval
            # 슬로우 모드 종료
            if self._adaptive_rate and time.time() >= self._slow_mode_until:
                self._adaptive_rate = False
                logger.info("⚡ 슬로우 모드 종료, 정상 속도 복귀")
        
        # 전역 Rate Limiter 호출
        KISGlobalRateLimiter.rate_limit(interval)
    
    def _load_cached_token(self) -> Optional[str]:
        """
        디스크에서 캐시된 토큰 로드 (24시간 유효성 확인, 멀티프로세스 안전)
        
        ✅ 기존 kis_token_manager.py 형식과 호환:
        - 기존: {"token": "...", "expires_at": "2025-10-10T10:00:00"}
        - 신규: {"access_token": "...", "issue_time": 123456, "expires_in": 86400}
        
        Returns:
            유효한 토큰이 있으면 반환, 없으면 None
        """
        # ✅ 멀티프로세스 파일 락 (filelock)
        lock_path = f"{self.TOKEN_CACHE_FILE}.lock"
        try:
            from filelock import FileLock
            lock = FileLock(lock_path, timeout=5)
        except ImportError:
            # filelock 없으면 스레드 락만 사용 (폴백)
            logger.warning(
                "⚠️ filelock 미설치 - 멀티프로세스 환경에서 토큰 캐시 경합 가능. "
                "설치 권장: pip install filelock"
            )
            lock = self._token_lock
        
        with lock:
            try:
                from pathlib import Path
                cache_file = Path(self.TOKEN_CACHE_FILE)
                
                if not cache_file.exists():
                    return None
                
                # ✅ 파싱 실패 시 즉시 캐시 삭제 후 복구
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache = json.load(f)
                except (json.JSONDecodeError, ValueError) as parse_err:
                    logger.warning(f"⚠️ 토큰 캐시 손상, 삭제 후 재발급: {parse_err}")
                    try:
                        cache_file.unlink(missing_ok=True)
                    except Exception:
                        pass
                    return None
                
                # ✅ 기존 형식 호환 (kis_token_manager.py + value_stock_finder.py)
                if 'token' in cache and 'expires_at' in cache:
                    token = cache.get('token')
                    expires_at_value = cache.get('expires_at')
                    
                    if not token or not expires_at_value:
                        return None
                    
                    # expires_at 파싱 (ISO 형식 문자열 or epoch timestamp 숫자)
                    try:
                        now = datetime.now()
                        
                        # ✅ 숫자(epoch timestamp) vs 문자열(ISO format) 구분
                        if isinstance(expires_at_value, (int, float)):
                            # epoch timestamp → datetime 변환
                            expires_at = datetime.fromtimestamp(expires_at_value)
                        elif isinstance(expires_at_value, str):
                            # ISO format string → datetime 변환
                            expires_at = datetime.fromisoformat(expires_at_value)
                        else:
                            logger.warning(f"알 수 없는 expires_at 타입: {type(expires_at_value)}")
                            return None
                        
                        # 1시간 여유 (기존 시스템과 동일)
                        if expires_at > now + timedelta(hours=1):
                            remaining = expires_at - now
                            hours = remaining.total_seconds() / 3600
                            logger.debug(f"✅ 캐시된 토큰 사용 [기존 형식] (남은 시간: {hours:.1f}시간)")
                            return token
                        else:
                            logger.debug("⏰ 캐시된 토큰이 만료되었습니다 [기존 형식]")
                            return None
                    except Exception as e:
                        logger.warning(f"expires_at 파싱 실패: {e}")
                        return None
                
                # ✅ 신규 형식 (우리가 만든 형식)
                elif 'access_token' in cache and 'issue_time' in cache:
                    token = cache.get('access_token')
                    issue_time = cache.get('issue_time')
                    expires_in = cache.get('expires_in', 86400)  # 기본 24시간
                    
                    if not token or not issue_time:
                        return None
                    
                    # 만료 시간 확인 (5분 여유)
                    elapsed = time.time() - issue_time
                    if elapsed >= (expires_in - 300):
                        logger.debug("⏰ 캐시된 토큰이 만료되었습니다 [신규 형식]")
                        return None
                    
                    # 남은 시간 계산
                    remaining = expires_in - elapsed
                    hours = remaining / 3600
                    logger.debug(f"✅ 캐시된 토큰 사용 [신규 형식] (남은 시간: {hours:.1f}시간)")
                    return token
                
                else:
                    logger.warning("⚠️ 알 수 없는 캐시 형식입니다. 새 토큰을 발급합니다.")
                    return None
                
            except Exception as e:
                logger.warning(f"토큰 캐시 로드 실패: {e}")
                return None
    
    def _save_token_cache(self, token: str, expires_in: int = 86400):
        """
        토큰을 디스크에 캐싱 (24시간 유효, 원자적 쓰기 + 안전한 퍼미션)
        
        ✅ 기존 kis_token_manager.py 형식 사용 (호환성)
        ✅ 멀티스레드/프로세스 안전 (파일 락 + 원자적 교체)
        
        Args:
            token: 액세스 토큰
            expires_in: 만료 시간 (초, 기본 86400초 = 24시간)
        """
        # ✅ 멀티프로세스 파일 락 (filelock)
        lock_path = f"{self.TOKEN_CACHE_FILE}.lock"
        try:
            from filelock import FileLock
            lock = FileLock(lock_path, timeout=5)
        except ImportError:
            # filelock 없으면 스레드 락만 사용 (폴백)
            logger.warning(
                "⚠️ filelock 미설치 - 멀티프로세스 환경에서 토큰 캐시 경합 가능. "
                "설치 권장: pip install filelock"
            )
            lock = self._token_lock
        
        with lock:
            try:
                from pathlib import Path
                import os
                
                cache_file = Path(self.TOKEN_CACHE_FILE)
                tmp_file = cache_file.with_suffix(".tmp")
                
                # ✅ 기존 형식 사용 (kis_token_manager.py와 호환)
                expires_at = datetime.now() + timedelta(seconds=expires_in)
                cache = {
                    'token': token,  # 기존 시스템 키명
                    'expires_at': expires_at.isoformat()  # 기존 시스템 키명
                }
                
                # 캐시 디렉토리 생성
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                
                # ✅ 원자적 쓰기: 임시 파일에 쓰고 rename (레이스 방지)
                with open(tmp_file, 'w', encoding='utf-8') as f:
                    json.dump(cache, f, indent=2)
                
                # ✅ 파일 퍼미션: 소유자만 읽기/쓰기 (0o600)
                try:
                    os.chmod(tmp_file, 0o600)
                except Exception:
                    pass  # Windows에서는 실패할 수 있음
                
                # ✅ 원자적 교체 (Windows 안전성: os.replace 사용)
                os.replace(str(tmp_file), str(cache_file))
                
                logger.debug(f"💾 토큰 캐시 저장 완료 (만료: {expires_at.strftime('%Y-%m-%d %H:%M:%S')})")
                
            except Exception as e:
                logger.warning(f"토큰 캐시 저장 실패: {e}")
    
    def _send_request(self, path: str, tr_id: str, params: dict, max_retries: int = 2, _total_attempts: int = 0) -> Optional[dict]:
        """
        KISDataProvider와 동일한 방식의 API 요청 메서드
        중앙 집중화된 API GET 요청 (재시도 로직 + 회로차단기 + 쿨다운)
        
        Args:
            _total_attempts: Internal recursion guard (세션 재생성 무한루프 방지)
        """
        # ✅ 재귀 호출 무한루프 방지 (세션 재생성 포함 최대 시도)
        max_total_attempts = max_retries + 3  # retries + session recreate tries
        if _total_attempts > max_total_attempts:
            logger.error(f"❌ 최대 시도 횟수 초과 ({_total_attempts}회) → 중단")
            return None
        
        # ✅ 회로차단기: 엔드포인트별 실패 카운터 + 쿨다운 복구
        if self._fail_counts[path] >= self.max_endpoint_failures:
            # 쿨다운 확인 (60초 후 자동 재시도)
            last_fail_time = self._fail_metadata.get(path, 0)
            cooldown_remaining = self.circuit_cooldown - (time.time() - last_fail_time)
            
            if cooldown_remaining > 0:
                logger.error(f"🚫 Circuit open for {path} (쿨다운 {int(cooldown_remaining)}초 남음)")
                return None
            else:
                # 쿨다운 후 카운터 반으로 감소 (점진 복구)
                old_count = self._fail_counts[path]
                self._fail_counts[path] = max(0, old_count // 2)
                logger.info(f"⚡ Circuit 쿨다운 완료: {path} (카운터 {old_count} → {self._fail_counts[path]})")
                # 재시도 진행
        
        # ✅ 연속 500 오류가 너무 많으면 세션 재생성 후 재시도
        if self.consecutive_500_errors >= self.max_consecutive_500_errors:
            logger.error(f"❌ 연속 500 오류 {self.consecutive_500_errors}회 초과 - AppKey 차단 의심 (EGW00201)")
            logger.error("⏸️  30초 대기 후 재시도 (일반적으로 5~10분 내 자동 해제)")
            logger.error("💡 지속 시: 프로그램 중단 → 5~10분 대기 → 재실행 권장")
            time.sleep(30)  # 30초 대기 (일반적으로 수 초~수 분 내 자동 해제)
            
            # ✅ 세션 재생성 (공통 메서드 사용, 세션 락 보호)
            with self._session_lock:
                try:
                    self.session.close()
                except Exception:
                    pass
                
                try:
                    self.session = self._init_session()
                    logger.info("✅ 세션 재생성 완료, 재귀 호출로 재시도")
                except Exception as e:
                    logger.error(f"❌ 세션 재생성 실패: {e}")
                    self.consecutive_500_errors = 0
                    return None
            
            # ✅ 세션 재생성 성공 시 재귀 호출로 재시도 (무한루프 방지)
            self.consecutive_500_errors = 0
            return self._send_request(path, tr_id, params, max_retries=1, _total_attempts=_total_attempts + 1)
        
        for attempt in range(max_retries + 1):
            try:
                self._rate_limit()
                
                # ✅ 캐시된 토큰 우선 사용 (1일 1회 발급 제한 준수)
                token = self._load_cached_token()
                
                # 캐시에 없거나 만료된 경우에만 새로 발급
                if not token:
                    logger.info("🔄 새로운 토큰 발급 중...")
                    
                    # OAuth 매니저 호환성 처리 (get_rest_token/get_valid_token 모두 지원)
                    if hasattr(self.oauth_manager, 'get_rest_token'):
                        token = self.oauth_manager.get_rest_token()
                    elif hasattr(self.oauth_manager, 'get_valid_token'):
                        token = self.oauth_manager.get_valid_token()
                    else:
                        logger.error("OAuth 매니저에서 토큰 가져오기 메서드를 찾을 수 없습니다")
                        return None
                    
                    if not token:
                        logger.error("OAuth 토큰을 가져올 수 없습니다")
                        return None
                    
                    # ✅ 새로 발급받은 토큰 캐싱 (24시간 유효)
                    self._save_token_cache(token, expires_in=86400)
                
                # 헤더 구성 (KISDataProvider와 동일)
                headers = {
                    **self.headers, 
                    "authorization": f"Bearer {token}", 
                    "tr_id": tr_id
                }
                
                url = f"{self.base_url}{path}"
                
                # ✅ 세션 요청 (스레드 세이프 보호 - 최소 범위만 잠금)
                with self._session_lock:
                    response = self.session.get(
                        url, 
                        headers=headers, 
                        params=params, 
                        timeout=self.timeout
                    )
                # 락 밖에서 처리 (JSON 파싱, 상태 체크 등 → 동시성 ↑)
                response.raise_for_status()
                
                # ✅ JSON 파싱 실패 대처 (HTML 에러페이지 등)
                try:
                    data = response.json()
                except ValueError as json_err:
                    # ✅ Content-Type 확인으로 더 명확한 진단
                    content_type = response.headers.get("Content-Type", "")
                    logger.error(
                        f"❌ JSON 파싱 실패 ({tr_id}): {json_err}. "
                        f"Content-Type={content_type}, "
                        f"응답 일부: {response.text[:200]}"
                    )
                    return None
                
                # ✅ rt_cd가 있는 경우만 체크 (일부 엔드포인트는 rt_cd 없음)
                if 'rt_cd' in data and data.get('rt_cd') != '0':
                    # ✅ 디버깅 정보 풍부화 (msg1, msg_cd, 종목코드 등) + 민감정보 마스킹
                    error_msg = data.get('msg1') or data.get('msg_cd') or 'unknown'
                    logger.warning(
                        f"⚠️ API 오류 (rt_cd={data.get('rt_cd')}): "
                        f"tr_id={tr_id}, path={path}, msg={error_msg}, params={self._safe_params(params)}"
                    )
                    return None
                
                # ✅ 페이징 지원: tr_cont 헤더를 body에 추가
                tr_cont = response.headers.get('tr_cont', '')
                if tr_cont:
                    data['tr_cont'] = tr_cont
                
                # 성공적인 요청 시 카운터 리셋 + 점진 감소
                if self.consecutive_500_errors > 0:
                    logger.debug(f"✅ 요청 성공, 500 오류 카운터 리셋 ({self.consecutive_500_errors} → 0)")
                self.consecutive_500_errors = 0
                
                # ✅ 회로차단기 시간 기반 복구 (일정 시간 성공 유지 시 완전 리셋)
                current_time = time.time()
                last_success = self._success_metadata.get(path, 0)
                
                if self._fail_counts.get(path, 0) > 0:
                    # 마지막 성공 후 일정 시간 경과 시 완전 리셋
                    if last_success > 0 and (current_time - last_success) >= self.circuit_recovery_time:
                        old_count = self._fail_counts[path]
                        self._fail_counts[path] = 0
                        logger.info(f"✅ 회로차단기 완전 복구: {path} ({old_count} → 0, {self.circuit_recovery_time:.0f}초 무오류)")
                    else:
                        # 점진 감소 (즉시 0이 아닌 천천히 회복)
                        old_count = self._fail_counts[path]
                        self._fail_counts[path] = max(0, old_count - 1)
                        logger.debug(f"✅ 회로차단기 카운터 감소: {path} ({old_count} → {self._fail_counts[path]})")
                
                # 마지막 성공 시각 기록
                self._success_metadata[path] = current_time
                
                return data
                
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code
                
                # ✅ 401 Unauthorized: 토큰 캐시 파기 후 재발급 시도
                if status == 401:
                    logger.warning("🔐 401 Unauthorized: 토큰 캐시 파기 후 1회 재발급 시도")
                    try:
                        from pathlib import Path
                        Path(self.TOKEN_CACHE_FILE).unlink(missing_ok=True)
                    except Exception as del_err:
                        logger.debug(f"토큰 캐시 삭제 실패(무시): {del_err}")
                    if attempt < max_retries:
                        time.sleep(0.5 * (2 ** attempt))
                        continue
                    else:
                        logger.error("❌ 401 복구 실패 (최대 재시도 초과)")
                        return None
                
                # ✅ 일시적 오류 (429, 500, 502, 503, 504) → 재시도
                transient_errors = {429, 500, 502, 503, 504}
                if status in transient_errors:
                    if status == 500:
                        self.consecutive_500_errors += 1
                        # ✅ 적응형 레이트 리밋: 2회 이상 500 발생 시 즉시 슬로우 모드 (AppKey 차단 방지)
                        if self.consecutive_500_errors >= 2:
                            self._adaptive_rate = True
                            self._slow_mode_until = time.time() + self._slow_mode_duration
                            logger.warning(f"⚠️ 연속 500 오류 {self.consecutive_500_errors}회 → {self._slow_mode_duration:.0f}초간 슬로우 모드 (간격 4배, AppKey 차단 방지)")
                    if attempt < max_retries:
                        # ✅ Retry-After 헤더 존중 (숫자/HTTP-date 모두 파싱)
                        retry_after = e.response.headers.get("Retry-After")
                        if retry_after:
                            try:
                                # 숫자 형식 시도
                                backoff = float(retry_after)
                            except ValueError:
                                # HTTP-date 형식 시도 (timezone-aware 보장)
                                try:
                                    from email.utils import parsedate_to_datetime
                                    from datetime import timezone
                                    
                                    retry_dt = parsedate_to_datetime(retry_after)
                                    
                                    # ✅ timezone-aware datetime 보장
                                    if retry_dt.tzinfo is None:
                                        retry_dt = retry_dt.replace(tzinfo=timezone.utc)
                                    
                                    now_utc = datetime.now(timezone.utc)
                                    backoff = max(0.0, (retry_dt - now_utc).total_seconds())
                                except Exception:
                                    # 파싱 실패 시 기본 백오프 (500 에러는 더 길게)
                                    if status == 500:
                                        base = 5.0 * (2 ** attempt)  # 500 에러는 5배 더 긴 대기 (차단 방지)
                                    else:
                                        base = 2.0 * (2 ** attempt)
                                    backoff = min(self.backoff_cap, base)
                        else:
                            # 기본 백오프 (500 에러는 더 길게, 차단 방지)
                            if status == 500:
                                base = 5.0 * (2 ** attempt)  # 5초, 10초, 20초, 30초...
                            else:
                                base = 2.0 * (2 ** attempt)  # 2초, 4초, 8초, 16초...
                            backoff = min(self.backoff_cap, base)  # 인자화된 캡
                        
                        # ✅ 하한선: request_interval 이상 (빠른 재시도 방지)
                        backoff = max(self.request_interval * 3, backoff)  # 최소 1.5초 (차단 방지)
                        
                        # ✅ 강한 지터 추가 (동시 재시도 분산)
                        backoff += random.uniform(0, 1.0)
                        
                        logger.warning(
                            f"⚠️ 일시적 오류 {status} → {backoff:.1f}s 후 재시도 "
                            f"({attempt + 1}/{max_retries}) tr_id={tr_id}"
                        )
                        time.sleep(backoff)
                        continue
                    else:
                        logger.error(f"❌ 최대 재시도 초과 {status} tr_id={tr_id}")
                        return None
                else:
                    # ✅ 비과도성 4xx도 회로차단기 카운트 증가 (403/404/422 등)
                    self._fail_counts[path] += 1
                    self._fail_metadata[path] = time.time()  # 마지막 실패 시각 기록
                    logger.error(f"❌ 고정 오류 HTTP {status} tr_id={tr_id}")
                    return None
                    
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries:
                    backoff = 0.3 * (2 ** attempt)
                    logger.debug(f"🔄 연결 오류 재시도 {attempt + 1}/{max_retries}, {backoff:.1f}s")
                    time.sleep(backoff)
                    continue
                else:
                    self._fail_counts[path] += 1  # ✅ 회로차단기 카운터 증가
                    self._fail_metadata[path] = time.time()  # 마지막 실패 시각 기록
                    logger.error(f"❌ 연결 실패 tr_id={tr_id}")
                    return None
                    
            except requests.exceptions.Timeout as e:
                if attempt < max_retries:
                    backoff = 0.3 * (2 ** attempt)
                    logger.debug(f"🔄 타임아웃 재시도 {attempt + 1}/{max_retries}, {backoff:.1f}s")
                    time.sleep(backoff)
                    continue
                else:
                    self._fail_counts[path] += 1  # ✅ 회로차단기 카운터 증가
                    self._fail_metadata[path] = time.time()  # 마지막 실패 시각 기록
                    logger.error(f"❌ 타임아웃 tr_id={tr_id}")
                    return None
                    
            except Exception as e:
                self._fail_counts[path] += 1  # ✅ 회로차단기 카운터 증가
                self._fail_metadata[path] = time.time()  # 마지막 실패 시각 기록
                logger.error(f"❌ 예외 tr_id={tr_id}: {e}")
                return None
        
        return None
    
    def _make_api_call(self, endpoint: str, params: Dict = None, tr_id: str = "", use_cache: bool = True) -> Optional[Dict]:
        """
        API 호출 래퍼 (캐시 지원, 엔드포인트별 차등 TTL)
        실제 호출은 _send_request 사용
        """
        # ✅ 엔드포인트 검증 (assert → ValueError, 프로덕션 안전)
        if endpoint.startswith("/"):
            raise ValueError(f"엔드포인트는 상대경로여야 합니다: {endpoint}")
        
        # ✅ uapi 접두사 자동 보정 (명확한 케이스 분리)
        if endpoint.startswith("uapi/domestic-stock/v1/"):
            endpoint = endpoint[len("uapi/domestic-stock/v1/"):]
            logger.debug(f"⚠️ 자동 수정: uapi/domestic-stock/v1/ 접두사 제거 → {endpoint}")
        elif endpoint.startswith("/uapi/domestic-stock/v1/"):
            endpoint = endpoint[len("/uapi/domestic-stock/v1/"):]
            logger.debug(f"⚠️ 자동 수정: /uapi/domestic-stock/v1/ 접두사 제거 → {endpoint}")
        elif endpoint.startswith("uapi/"):
            logger.warning(f"⚠️ 불완전한 uapi 접두사: {endpoint} (자동 수정 불가)")
        
        # ✅ 캐시 키 생성 (정규화된 파라미터 사용 + tr_id 포함으로 충돌 방지)
        # 주의: 캐시 키에만 정규화 적용, 실제 요청에는 원본 params 사용!
        original_params = params or {}
        normalized_for_cache = self._normalize_params_for_cache_key(original_params)
        cache_key = f"{endpoint}:{tr_id}:{json.dumps(normalized_for_cache, sort_keys=True, ensure_ascii=False)}"
        
        # ✅ 캐시 TTL 결정 (오버라이드 우선, 없으면 패턴 매칭)
        if endpoint in self.cache_ttl_overrides:
            ttl = self.cache_ttl_overrides[endpoint]
        elif 'quotations' in endpoint:
            ttl = self.cache_ttl['quotations']
        elif 'ranking' in endpoint:
            ttl = self.cache_ttl['ranking']
        elif 'financial' in endpoint or 'finance' in endpoint:
            ttl = self.cache_ttl['financial']
        elif 'dividend' in endpoint:
            ttl = self.cache_ttl['dividend']
        else:
            ttl = self.cache_ttl['default']
        
        # ✅ 캐시 확인 (Lock으로 보호, LRU 방식)
        if use_cache:
            with self._cache_lock:
                if cache_key in self.cache:
                    cached_data, timestamp = self.cache.pop(cache_key)  # 제거
                    if time.time() - timestamp < ttl:
                        # ✅ 히트 시 뒤로 이동 (LRU)
                        self.cache[cache_key] = (cached_data, timestamp)
                        logger.debug(f"✓ 캐시 사용: {endpoint} (TTL={ttl}초)")
                        return cached_data
                    # TTL 만료된 경우 재생성
        
        # KISDataProvider의 _send_request 방식 사용 (원본 params 전달!)
        path = f"/uapi/domestic-stock/v1/{endpoint}"
        data = self._send_request(path, tr_id, original_params)  # ✅ 원본 유지 (빈 문자열 보존)
        
        # ✅ 캐시 저장 (Lock으로 보호, 진짜 LRU)
        if data and use_cache:
            with self._cache_lock:
                # ✅ 캐시 무한증가 방지: LRU 방식 (가장 오래 미사용 항목 제거)
                if len(self.cache) >= self.cache_maxsize:
                    self.cache.popitem(last=False)  # OrderedDict: 가장 앞(오래된) 항목 제거
                    logger.debug(f"🗑️ 캐시 한계 도달, LRU 항목 제거")
                
                self.cache[cache_key] = (data, time.time())
                logger.debug(f"💾 캐시 저장: {endpoint} (TTL={ttl}초, 크기={len(self.cache)}/{self.cache_maxsize})")
        
        return data
    
    def _fetch_all_pages(self, endpoint: str, base_params: Dict, tr_id: str, 
                        ctx_keys: Optional[Dict[str, str]] = None, 
                        max_pages: int = 10, 
                        use_cache: bool = True,
                        min_batch_size: Optional[int] = None) -> List[Dict]:
        """
        페이지네이션 지원 API 호출 (자동 다음 페이지 수집)
        
        Args:
            endpoint: API 엔드포인트
            base_params: 기본 파라미터
            tr_id: 거래 ID
            ctx_keys: 컨텍스트 키 매핑 {"in": "CTX_AREA_FK100", "out": "ctx_area_fk100"}
            max_pages: 최대 페이지 수 (무한루프 방지)
            use_cache: 캐시 사용 여부
            min_batch_size: 페이지 데이터가 이 값보다 작으면 종료 (None이면 휴리스틱 비활성화)
            
        Returns:
            모든 페이지의 데이터를 합친 리스트
            
        Note:
            KIS API는 두 가지 페이징 방식 지원:
            1. tr_cont 헤더 (F/M/D/E)
            2. CTX_AREA_FK 파라미터
            
        Example:
            # tr_cont 방식 (대부분의 API)
            rows = self._fetch_all_pages(
                "quotations/inquire-daily-price",
                {"FID_INPUT_ISCD": "005930"},
                "FHKST01010400"
            )
            
            # CTX 방식 (일부 랭킹 API)
            rows = self._fetch_all_pages(
                "ranking/dividend-rate",
                {"GB1": "0", "UPJONG": "0001"},
                "HHKDB13470100",
                ctx_keys={"in": "CTS_AREA", "out": "cts_area"}
            )
        """
        try:
            all_rows = []
            ctx_token = ""  # 컨텍스트 토큰
            page_count = 0  # ✅ 안전한 페이지 카운터
            
            ctx_in_key = (ctx_keys or {}).get("in", "")
            ctx_out_key = (ctx_keys or {}).get("out", "")
            
            for page_num in range(max_pages):
                # 파라미터 구성
                params = dict(base_params)
                
                # 컨텍스트 토큰이 있으면 추가
                if ctx_token and ctx_in_key:
                    params[ctx_in_key] = ctx_token
                
                # API 호출
                data = self._make_api_call(endpoint, params, tr_id, use_cache)
                
                if not data:
                    logger.debug(f"📄 페이지 {page_num + 1}: API 응답 없음")
                    break
                
                # 데이터 추출 (output2 우선 - 차트 데이터는 output2에 있음!)
                page_data = data.get("output2") or data.get("output") or data.get("output1") or []
                
                if not page_data:
                    logger.debug(f"📄 페이지 {page_num + 1}: 데이터 없음")
                    break
                
                # 리스트가 아니면 리스트로 변환
                if isinstance(page_data, dict):
                    page_data = [page_data]
                
                all_rows.extend(page_data)
                page_count += 1  # ✅ 페이지 카운터 증가
                
                # ✅ 차트 수집 로그 간소화 (중복 제거)
                if 'itemchartprice' in endpoint and page_count == 1:
                    # 첫 페이지만 INFO, 나머지는 DEBUG
                    logger.debug(f"📄 차트 수집: {len(page_data)}개 (1페이지)")
                else:
                    logger.debug(f"📄 페이지 {page_count}: {len(page_data)}개 수집 (누적: {len(all_rows)}개)")
                
                # 다음 페이지 토큰 확인
                # 2. CTX 토큰 방식 (우선 체크)
                if ctx_out_key:
                    # CTX 방식은 tr_cont 무시하고 토큰으로만 제어
                    new_token = data.get(ctx_out_key, "")
                    if not new_token or new_token == ctx_token:
                        logger.debug(f"📄 페이징 완료: CTX 토큰 없음 또는 중복")
                        break
                    ctx_token = new_token
                else:
                    # 1. tr_cont 헤더 방식
                    tr_cont = data.get("tr_cont", "")
                    if tr_cont in ("F", "M"):
                        # F(다음 페이지 있음), M(중간) → 계속
                        pass
                    elif tr_cont in ("D", "", None):
                        # D(완료), 빈값, None → 종료
                        logger.debug(f"📄 페이징 완료: tr_cont={tr_cont or '없음'}")
                        break
                    else:
                        # ✅ 알 수 없는 값 → 보수적으로 한 번 더 시도 후 종료
                        logger.warning(f"⚠️ 알 수 없는 tr_cont='{tr_cont}' → 다음 페이지 시도 후 종료 예정")
                        # 다음 루프에서 데이터 없으면 자동 종료됨
                        pass
                
                # ✅ 데이터가 적으면 마지막 페이지로 판단 (옵션화)
                if min_batch_size and len(page_data) < min_batch_size:
                    logger.debug(f"📄 페이징 완료: 적은 데이터({len(page_data)}개, 최소={min_batch_size})")
                    break
            
            logger.debug(f"✅ 페이지네이션 완료: 총 {len(all_rows)}개 ({page_count}페이지)")
            return all_rows
            
        except Exception as e:
            logger.error(f"❌ 페이지네이션 실패: {e}")
            return []
    
    # === 국내주식 기본시세 ===
    
    def get_current_price(self, symbol: str, market_type: str = "J") -> Optional[Dict]:
        """
        주식현재가 시세 조회
        
        Args:
            symbol: 종목코드
            market_type: 시장구분 (J:KRX, NX:NXT, UN:통합) - 신규 추가!
        """
        try:
            market_type = self._validate_market(market_type)  # ✅ 검증
            data = self._make_api_call(
                endpoint="quotations/inquire-price",
                params={
                    "FID_COND_MRKT_DIV_CODE": market_type,  # NX, UN 추가 지원
                    "FID_INPUT_ISCD": symbol
                },
                tr_id="FHKST01010100"  # 주식현재가 시세 TR_ID
            )
            # ✅ _first_output() 활용으로 중복 제거
            return self._first_output(data)
        except Exception as e:
            logger.error(f"현재가 조회 실패: {symbol}, {e}")
            return None
    
    def get_asking_price(self, symbol: str) -> Optional[Dict]:
        """주식현재가 호가/예상체결 조회"""
        try:
            data = self._make_api_call(
                endpoint="quotations/inquire-asking-price-exp-ccn",
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol
                },
                tr_id="FHKST01010200"  # 주식호가 TR_ID
            )
            # ✅ _first_output() 활용
            return self._first_output(data)
        except Exception as e:
            logger.error(f"호가 조회 실패: {symbol}, {e}")
            return None
    
    def get_chart_data(self, symbol: str, period: str = "D", days: int = 365, 
                      use_pagination: bool = True, market_type: str = "J") -> Optional[List[Dict]]:
        """
        차트 데이터 조회 (일/주/월봉, 페이지네이션 지원)
        
        Args:
            symbol: 종목코드
            period: 기간 구분 (D:일봉, W:주봉, M:월봉)
            days: 조회 기간 (일)
            use_pagination: 페이지네이션 사용 여부 (True: 전체 데이터, False: 1페이지만)
            market_type: 시장구분 (J:KRX, NX:NXT, UN:통합)
            
        Note:
            현재 모든 기간(일/주/월)에 동일 엔드포인트 사용
            TODO: KIS API가 기간별 엔드포인트 분리 시 period에 따라 분기 필요
        """
        try:
            period_map = {
                "D": "D",  # 일봉
                "W": "W",  # 주봉
                "M": "M"   # 월봉
            }
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            base_params = {
                "FID_COND_MRKT_DIV_CODE": market_type,
                "FID_INPUT_ISCD": symbol,
                "FID_INPUT_DATE_1": start_date.strftime("%Y%m%d"),
                "FID_INPUT_DATE_2": end_date.strftime("%Y%m%d"),
                "FID_PERIOD_DIV_CODE": period_map.get(period, "D"),
                "FID_ORG_ADJ_PRC": "0"  # 0:수정주가, 1:원주가
            }
            
            # ✅ 페이지네이션 지원
            if use_pagination:
                all_data = self._fetch_all_pages(
                    endpoint="quotations/inquire-daily-itemchartprice",
                    base_params=base_params,
                    tr_id="FHKST03010100",
                    max_pages=20  # 최대 20페이지 (충분한 데이터)
                )
                return all_data if all_data else None
            else:
                # 기존 방식 (1페이지만)
                data = self._make_api_call(
                    endpoint="quotations/inquire-daily-itemchartprice",
                    params=base_params,
                    tr_id="FHKST03010100"
                )
                # ✅ 반환 키 통일 (output2/output/output1 모두 시도)
                if not data:
                    return None
                return data.get('output2') or data.get('output') or data.get('output1')
            
        except Exception as e:
            logger.error(f"차트 데이터 조회 실패: {symbol}, {e}")
            return None
    
    # === 종목정보 ===
    
    def get_stock_basic_info(self, symbol: str) -> Optional[Dict]:
        """
        주식기본조회 (종목명, 업종 등)
        
        Note:
            종목명이 비어있는 경우 current_price API에서 폴백
        """
        try:
            data = self._make_api_call(
                endpoint="quotations/search-info",
                params={
                    "PDNO": symbol,
                    "PRDT_TYPE_CD": "300"  # 주식
                },
                tr_id="CTPF1604R"  # 종목정보 조회 TR_ID
            )
            if data and 'output' in data:
                output = data['output']
                result = None
                if isinstance(output, list) and len(output) > 0:
                    result = output[0]
                elif isinstance(output, dict):
                    result = output
                
                # ✅ 종목명이 비어있으면 current_price에서 보강
                if result and not result.get('prdt_name'):
                    logger.debug(f"종목명 없음, current_price에서 폴백 시도: {symbol}")
                    price_data = self.get_current_price(symbol)
                    if price_data and price_data.get('hts_kor_isnm'):
                        result['prdt_name'] = price_data['hts_kor_isnm']
                        logger.debug(f"✅ 종목명 폴백 성공: {result['prdt_name']}")
                
                return result
            return None
        except Exception as e:
            logger.error(f"종목 기본 정보 조회 실패: {symbol}, {e}")
            return None
    
    def get_financial_ratios(self, symbol: str) -> Optional[Dict]:
        """국내주식 재무비율 조회 (PER, PBR, ROE 등)"""
        try:
            data = self._make_api_call(
                endpoint="finance/financial-ratio",
                params={
                    "FID_DIV_CLS_CODE": "0",              # 0:년, 1:분기
                    "FID_COND_MRKT_DIV_CODE": "J",        # ✅ 대문자 통일
                    "FID_INPUT_ISCD": symbol               # ✅ 대문자 통일
                },
                tr_id="FHKST66430300"  # 재무비율 TR_ID
            )
            
            if data and 'output' in data:
                output = data['output']
                if isinstance(output, list) and len(output) > 0:
                    return output[0]  # 최신 데이터
                elif isinstance(output, dict):
                    return output
            return None
        except Exception as e:
            logger.error(f"재무비율 조회 실패: {symbol}, {e}")
            return None
    
    def get_income_statement(self, symbol: str) -> Optional[Dict]:
        """국내주식 손익계산서 조회"""
        try:
            data = self._make_api_call(
                endpoint="quotations/inquire-income-statement",
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol
                },
                tr_id="FHKST66430200"  # 손익계산서 TR_ID
            )
            if data and 'output' in data:
                return data['output']
            return None
        except Exception as e:
            logger.error(f"손익계산서 조회 실패: {symbol}, {e}")
            return None
    
    def get_balance_sheet(self, symbol: str) -> Optional[Dict]:
        """국내주식 대차대조표 조회"""
        try:
            data = self._make_api_call(
                endpoint="quotations/inquire-balance-sheet",
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol
                },
                tr_id="FHKST66430100"  # 대차대조표 TR_ID
            )
            if data and 'output' in data:
                return data['output']
            return None
        except Exception as e:
            logger.error(f"대차대조표 조회 실패: {symbol}, {e}")
            return None
    
    def get_daily_prices(self, symbol: str) -> Optional[List[Dict]]:
        """일자별 시세 조회 (✅ 함수명 수정: dividend_info → daily_prices)"""
        try:
            data = self._make_api_call(
                endpoint="quotations/inquire-daily-price",
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol,
                    "FID_PERIOD_DIV_CODE": "D",
                    "FID_ORG_ADJ_PRC": "0"
                },
                tr_id="FHKST01010400"  # 일자별 시세 TR_ID
            )
            if data and 'output' in data:
                return data['output']
            return None
        except Exception as e:
            logger.error(f"일자별 시세 조회 실패: {symbol}, {e}")
            return None
    
    # === 시세분석 ===
    
    def get_investor_trend(self, symbol: str, market_type: str = "J") -> Optional[Dict]:
        """
        투자자별 매매동향 조회 (실시간)
        
        Args:
            symbol: 종목코드
            market_type: 시장구분 (J:KRX, NX:NXT, UN:통합) - 신규 추가!
        """
        try:
            data = self._make_api_call(
                endpoint="quotations/inquire-investor",
                params={
                    "FID_COND_MRKT_DIV_CODE": market_type,  # NX, UN 추가 지원
                    "FID_INPUT_ISCD": symbol,
                    "FID_INPUT_DATE_1": "",  # 당일
                    "FID_INPUT_DATE_2": "",
                    "FID_PERIOD_DIV_CODE": "D"  # D:일, W:주, M:월
                },
                tr_id="FHKST01010900"  # 투자자별 매매동향 TR_ID
            )
            # ✅ _first_output() 활용
            return self._first_output(data)
        except Exception as e:
            logger.error(f"투자자 동향 조회 실패: {symbol}, {e}")
            return None
    
    def get_investor_trend_daily(self, symbol: str, start_date: str = "", end_date: str = "", 
                                use_pagination: bool = True, market_type: str = "J") -> Optional[List[Dict]]:
        """
        종목별 투자자매매동향(일별) 조회 (페이지네이션 지원)
        HTS [0416] 종목별 일별동향 화면 기능
        
        Args:
            symbol: 종목코드 (6자리)
            start_date: 조회 시작일자 (YYYYMMDD, 미입력시 최근 30일)
            end_date: 조회 종료일자 (YYYYMMDD, 미입력시 당일)
            use_pagination: 페이지네이션 사용 여부 (True: 전체 데이터, False: 1페이지만)
            market_type: 시장구분 (J:KRX, NX:NXT, UN:통합)
            
        Returns:
            일자별 투자자 매매동향 리스트
        """
        try:
            # 날짜 기본값 설정
            if not end_date:
                end_date = datetime.now().strftime("%Y%m%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
            
            base_params = {
                "FID_COND_MRKT_DIV_CODE": market_type,
                "FID_INPUT_ISCD": symbol,
                "FID_INPUT_DATE_1": start_date,
                "FID_INPUT_DATE_2": end_date,
                "FID_PERIOD_DIV_CODE": "D"  # D:일별
            }
            
            # ✅ 페이지네이션 지원
            if use_pagination:
                all_data = self._fetch_all_pages(
                    endpoint="quotations/inquire-daily-investorprice",
                    base_params=base_params,
                    tr_id="FHKST03010200",
                    max_pages=10
                )
                return all_data if all_data else None
            else:
                # 기존 방식 (1페이지만)
                data = self._make_api_call(
                    endpoint="quotations/inquire-daily-investorprice",
                    params=base_params,
                    tr_id="FHKST03010200"
                )
                return data.get('output') if data else None
            
        except Exception as e:
            logger.error(f"종목별 투자자매매동향(일별) 조회 실패: {symbol}, {e}")
            return None
    
    def get_program_trade(self, symbol: str, market_type: str = "J") -> Optional[Dict]:
        """
        프로그램매매 현황 조회
        
        Args:
            symbol: 종목코드
            market_type: 시장구분 (J:KRX, NX:NXT, UN:통합)
        """
        try:
            data = self._make_api_call(
                endpoint="quotations/program-trade-by-stock",
                params={
                    "FID_COND_MRKT_DIV_CODE": market_type,
                    "FID_INPUT_ISCD": symbol,
                    "FID_INPUT_DATE_1": "",  # 당일
                    "FID_INPUT_DATE_2": ""
                },
                tr_id="FHKST01010600"  # 프로그램매매 종목별 TR_ID
            )
            # ✅ _first_output() 활용
            return self._first_output(data)
        except Exception as e:
            logger.error(f"프로그램매매 조회 실패: {symbol}, {e}")
            return None
    
    def get_credit_balance(self, symbol: str, market_type: str = "J") -> Optional[Dict]:
        """
        신용잔고 현황 조회 (비활성화: 404 오류 회피)
        
        Args:
            symbol: 종목코드
            market_type: 시장구분 (J:KRX, NX:NXT, UN:통합)
            
        Note:
            ⚠️ 이 API는 404 오류를 반환하므로 비활성화됨
            → 항상 None 반환
        """
        # ✅ 404 오류 회피: API 호출 스킵
        logger.debug(f"신용잔고 조회 스킵 (404 오류 회피): {symbol}")
        return None
            
    # === 순위분석 ===
    
    def get_market_cap_ranking(self, limit: int = 100, market_type: str = "J") -> Optional[List[Dict]]:
        """
        시가총액 순위 조회 (정식 KIS API 사용 + UN 통합 지원)
        
        Args:
            limit: 조회할 최대 종목 수 (기본 100개, 실제로는 50~100개 수준 반환)
            market_type: 시장구분 (J:코스피, Q:코스닥, NX:NXT, UN:통합) - UN 병합 지원!
            
        Note:
            KIS API는 일정 수량(50~100개 수준)만 반환
            UN(통합) 시 KOSPI(J) + KOSDAQ(Q)를 병합하여 중복 제거 후 상위 limit 반환
        """
        def _call_once(market_code: str) -> List[Dict]:
            """단일 시장 시가총액 조회"""
            d = self._make_api_call(
                endpoint="quotations/inquire-market-cap",
                params={
                    "FID_COND_MRKT_DIV_CODE": market_code,
                    "FID_INPUT_ISCD": "0000",
                    "FID_PERIOD_DIV_CODE": "0",
                    "FID_ORG_ADJ_PRC": "0"
                },
                tr_id="FHPST01740000"
            )
            if d and 'output' in d:
                return d['output']
            return []
        
        market_type = self._validate_market(market_type)
        collected: List[Dict] = []
        
        if market_type == "UN":
            # ✅ 통합: KOSPI(J) + KOSDAQ(Q) 병합 후 중복 제거
            j_stocks = _call_once("J")
            q_stocks = _call_once("Q")
            
            seen = set()
            for row in (j_stocks + q_stocks):
                code = row.get('mksc_shrn_iscd')
                if code and code not in seen:
                    seen.add(code)
                    collected.append(row)
            
            if collected:
                # 시가총액 기준 재정렬 (병합 후 순서 보장)
                collected.sort(
                    key=lambda x: self._to_float(x.get('hts_avls', 0)), 
                    reverse=True
                )
                logger.debug(f"✅ 시총 통합(J+Q) 병합: {len(collected)}개 (중복 제거 완료)")
                return collected[:limit]
        else:
            # 단일 시장
            one = _call_once(market_type)
            if one:
                logger.debug(f"✅ 시총 {market_type} 응답: {len(one)}개")
                return one[:limit]
            else:
                collected = []  # 폴백 준비
        
        # ✅ API 실패 시 KOSPI 마스터 파일 사용 (조건 개선)
        if not collected:
            logger.warning(f"⚠️ 시가총액 API 실패, KOSPI 마스터 파일로 대체 시도...")
        
        try:
            try:
                import pandas as pd
            except ImportError:
                logger.warning("⚠️ pandas 미설치로 KOSPI 마스터 파일 사용 불가")
                return None
            
            from pathlib import Path
            
            kospi_file = Path("kospi_code.xlsx")
            if kospi_file.exists():
                df = pd.read_excel(kospi_file)
                
                # 시가총액으로 정렬
                if '시가총액' in df.columns:
                    df = df.sort_values('시가총액', ascending=False).head(limit)
                    
                    results = []
                    for _, row in df.iterrows():
                        code = row.get('단축코드')
                        if code and isinstance(code, str) and len(code) == 6:
                            if not (code.startswith('F') or code.startswith('Q')):
                                market_cap = row.get('시가총액', 0)
                                if market_cap and market_cap > 0:
                                    # 종목명에서 "보통주" 제거, "우선주"는 "우"로 축약
                                    name = row.get('한글명', '')
                                    name = name.replace('보통주', '')
                                    if '우선주' in name:
                                        name = name.replace('우선주', '우')
                                    name = name.strip()
                                    
                                    results.append({
                                        'mksc_shrn_iscd': code,
                                        'hts_kor_isnm': name,  # ✨ 정리된 종목명
                                        'hts_avls': market_cap / 100_000_000.0,  # ✅ 항상 억원 단위
                                        'stck_prpr': row.get('기준가', 0),
                                        'acml_vol': row.get('전일거래량', 0),
                                        'prdy_ctrt': 0
                                    })
                    
                    logger.debug(f"✅ KOSPI 마스터에서 시가총액 상위 {len(results)}개 조회")
                    return results
        except Exception as fallback_error:
            logger.error(f"KOSPI 마스터 파일도 실패: {fallback_error}")
        
        return None
    
    def get_volume_ranking(self, limit: int = 30, market_type: str = "J") -> Optional[List[Dict]]:
        """
        거래량 순위 조회 (UN 통합 지원)
        
        Args:
            limit: 조회할 최대 종목 수 (기본 30개, 실제로도 약 30개만 반환)
            market_type: 시장구분 (J:KRX, Q:KOSDAQ, NX:NXT, UN:통합)
            
        Note:
            KIS API는 약 30개만 반환 (페이징 미지원)
            UN(통합) 시 J+Q 병합 후 거래량 재정렬
        """
        try:
            all_results: List[Dict] = []
            
            # ✅ UN은 J+Q로 확장
            for m in self._expand_market_types(market_type):
                data = self._make_api_call(
                    endpoint="quotations/volume-rank",
                    params={
                        "FID_COND_MRKT_DIV_CODE": m,
                        "FID_COND_SCR_DIV_CODE": "20171",
                        "FID_INPUT_ISCD": "0000",
                        "FID_DIV_CLS_CODE": "0",
                        "FID_BLNG_CLS_CODE": "0",
                        "FID_TRGT_CLS_CODE": "111111111",
                        "FID_TRGT_EXLS_CLS_CODE": "0000000000",
                        "FID_INPUT_PRICE_1": "",
                        "FID_INPUT_PRICE_2": "",
                        "FID_VOL_CNT": "",
                        "FID_INPUT_DATE_1": ""
                    },
                    tr_id="FHPST01710000"
                )
                
                if data and 'output' in data:
                    all_results.extend(data['output'])
            
            if all_results:
                # ✅ 중복 제거 + 거래량 재정렬
                seen = set()
                unique = []
                for row in all_results:
                    code = row.get('mksc_shrn_iscd')
                    if code and code not in seen:
                        seen.add(code)
                        unique.append(row)
                
                # 거래량 기준 재정렬
                unique.sort(key=lambda x: self._to_int(x.get('acml_vol', 0)), reverse=True)
                logger.debug(f"✅ 거래량 순위 조회 완료: {len(unique)}개")
                return unique[:limit]
            
            return None
            
        except Exception as e:
            logger.error(f"거래량 순위 조회 실패: {e}")
            return None
    
    def get_per_ranking(self, limit: int = 100, market_type: str = "J") -> Optional[List[Dict]]:
        """
        재무비율(PER/PBR/ROE) 순위 조회 (UN 통합 지원)
        
        Args:
            limit: 조회할 최대 종목 수 (기본 100개, 실제로는 50~100개 수준 반환)
            market_type: 시장구분 (J:KRX, Q:KOSDAQ, NX:NXT, UN:통합)
            
        Note:
            KIS API는 일정 수량(50~100개 수준)만 반환 (페이징 미지원)
            UN(통합) 시 J+Q 병합 후 PER 재정렬
        """
        try:
            all_results: List[Dict] = []
            
            # ✅ UN은 J+Q로 확장
            for m in self._expand_market_types(market_type):
                data = self._make_api_call(
                    endpoint="quotations/inquire-financial-ratio",
                    params={
                        "FID_COND_MRKT_DIV_CODE": m,
                        "FID_COND_SCR_DIV_CODE": "20172",  # PER (재무비율)
                        "FID_INPUT_ISCD": "0000",
                        "FID_DIV_CLS_CODE": "0",  # 전체
                        "FID_INPUT_PRICE_1": "",
                        "FID_INPUT_PRICE_2": "",
                        "FID_VOL_CNT": "",
                        "FID_INPUT_DATE_1": ""
                    },
                    tr_id="FHPST01750000"
                )
                
                if data and 'output' in data:
                    all_results.extend(data['output'])
            
            if all_results:
                # ✅ 중복 제거 + PER 재정렬
                seen = set()
                unique = []
                for row in all_results:
                    code = row.get('mksc_shrn_iscd')
                    if code and code not in seen:
                        seen.add(code)
                        unique.append(row)
                
                # PER 기준 재정렬 (낮은 순)
                unique.sort(key=lambda x: self._to_float(x.get('per', 999)))
                logger.debug(f"✅ 재무비율 순위 조회 완료: {len(unique)}개")
                return unique[:limit]
            
            return None
                
        except Exception as e:
            logger.error(f"재무비율 순위 조회 실패: {e}")
            return None
    
    def get_updown_ranking(self, limit: int = 100, updown_type: str = "0", market_type: str = "J") -> Optional[List[Dict]]:
        """
        등락률 순위 조회 (UN 통합 지원)
        
        Args:
            limit: 조회할 종목 수 (기본 100개, 실제로는 50~100개 수준 반환)
            updown_type: 0:상승률, 1:하락률, 2:보합
            market_type: 시장구분 (J:KRX, Q:KOSDAQ, NX:NXT, UN:통합)
            
        Note:
            KIS API는 일정 수량(50~100개 수준)만 반환
            UN(통합) 시 J+Q 병합 후 등락률 재정렬
        """
        try:
            all_results: List[Dict] = []
            
            # ✅ UN은 J+Q로 확장
            for m in self._expand_market_types(market_type):
                data = self._make_api_call(
                    endpoint="ranking/fluctuation",
                    params={
                        "FID_COND_MRKT_DIV_CODE": m,
                        "FID_COND_SCR_DIV_CODE": "20170",  # 등락률
                        "FID_INPUT_ISCD": "0000",
                        "FID_DIV_CLS_CODE": updown_type,  # 0:상승, 1:하락, 2:보합
                        "FID_INPUT_PRICE_1": "",
                        "FID_INPUT_PRICE_2": "",
                        "FID_VOL_CNT": "",
                        "FID_INPUT_DATE_1": ""
                    },
                    tr_id="FHPST01700000"
                )
                
                if data and 'output' in data:
                    all_results.extend(data['output'])
            
            if all_results:
                # ✅ 중복 제거 + 등락률 재정렬
                seen = set()
                unique = []
                for row in all_results:
                    code = row.get('mksc_shrn_iscd')
                    if code and code not in seen:
                        seen.add(code)
                        unique.append(row)
                
                # 등락률 기준 재정렬 (상승=내림차순, 하락=오름차순)
                reverse = (updown_type == "0")  # 상승률은 높은 순
                unique.sort(
                    key=lambda x: self._to_float(x.get('prdy_ctrt', 0)), 
                    reverse=reverse
                )
                logger.debug(f"✅ 등락률 순위 조회 완료: {len(unique)}개")
                return unique[:limit]
            
            return None
                
        except Exception as e:
            logger.error(f"등락률 순위 조회 실패: {e}")
            return None
    
    def get_asking_price_ranking(self, limit: int = 100, market_type: str = "J") -> Optional[List[Dict]]:
        """
        호가잔량 순위 조회 (UN 통합 지원)
        
        Args:
            limit: 조회할 종목 수 (기본 100개, 실제로는 50~100개 수준 반환)
            market_type: 시장구분 (J:KRX, Q:KOSDAQ, NX:NXT, UN:통합)
            
        Note:
            KIS API는 일정 수량(50~100개 수준)만 반환
            UN(통합) 시 J+Q 병합 후 호가잔량 재정렬
        """
        try:
            all_results: List[Dict] = []
            
            # ✅ UN은 J+Q로 확장
            for m in self._expand_market_types(market_type):
                data = self._make_api_call(
                    endpoint="ranking/asking-price-volume",
                    params={
                        "FID_COND_MRKT_DIV_CODE": m,
                        "FID_COND_SCR_DIV_CODE": "20173",  # 호가잔량
                        "FID_INPUT_ISCD": "0000",
                        "FID_DIV_CLS_CODE": "0",  # 전체
                        "FID_INPUT_PRICE_1": "",
                        "FID_INPUT_PRICE_2": "",
                        "FID_VOL_CNT": "",
                        "FID_INPUT_DATE_1": ""
                    },
                    tr_id="FHPST01720000"
                )
                
                if data and 'output' in data:
                    all_results.extend(data['output'])
            
            if all_results:
                # ✅ 중복 제거 + 호가잔량 재정렬
                seen = set()
                unique = []
                for row in all_results:
                    code = row.get('mksc_shrn_iscd')
                    if code and code not in seen:
                        seen.add(code)
                        unique.append(row)
                
                # 호가잔량 기준 재정렬 (많은 순)
                unique.sort(
                    key=lambda x: self._to_int(x.get('total_askp_rsqn', 0)), 
                    reverse=True
                )
                logger.debug(f"✅ 호가잔량 순위 조회 완료: {len(unique)}개")
                return unique[:limit]
            
            return None
                
        except Exception as e:
            logger.error(f"호가잔량 순위 조회 실패: {e}")
            return None
    
    def get_multiple_current_price(self, symbols: List[str], market_type: str = "J") -> Optional[List[Dict]]:
        """
        관심종목(멀티종목) 시세조회 [국내주식-205]
        
        Args:
            symbols: 종목코드 리스트 (30개 초과 시 자동 청크 처리)
            market_type: 시장구분 (J:KRX, NX:NXT, UN:통합)
        
        Returns:
            여러 종목의 현재가 정보 리스트
            
        Note:
            ✅ 공식 엔드포인트: inquire-multiple-price (쉼표 구분)
            ✅ 입력 정합성: 6자리 숫자만, 중복 제거, 빈 리스트 방지
            ✅ 청크 실패 복원력: 실패 시 지수 백오프 + 1회 재시도
            
        API Reference:
            URL: /uapi/domestic-stock/v1/quotations/inquire-multiple-price
            TR_ID: FHKST11300006
            분류: 국내주식 > 시세분석
        """
        try:
            if not symbols:
                return None
            
            # ✅ 입력 정합성: 6자리 숫자만, 중복 제거
            uniq = []
            seen = set()
            for s in symbols:
                if not s:
                    continue
                s = str(s).strip()
                if len(s) == 6 and s.isdigit() and s not in seen:
                    uniq.append(s)
                    seen.add(s)
            
            if not uniq:
                logger.warning("⚠️ 멀티시세 입력에 유효한 6자리 종목코드가 없습니다.")
                return None
            
            # ✅ 30개 초과 시 자동 청크 처리
            results: List[Dict] = []
            chunk_size = 30
            
            for i in range(0, len(uniq), chunk_size):
                # ✅ 청크 간 레이트리밋 준수 (연속 호출 방지)
                if i > 0:
                    self._rate_limit()
                
                chunk = uniq[i:i+chunk_size]
                chunk_num = i // chunk_size + 1
                
                # ✅ 쉼표로 구분된 종목코드 문자열
                symbol_string = ",".join(chunk)
                
                data = self._make_api_call(
                    endpoint="quotations/inquire-multiple-price",  # ✅ 공식 엔드포인트
                    params={
                        "FID_COND_MRKT_DIV_CODE": market_type,
                        "FID_INPUT_ISCD": symbol_string  # ✅ 쉼표 구분 문자열
                    },
                    tr_id="FHKST11300006"
                )
                
                if data and 'output' in data:
                    results.extend(data['output'])
                else:
                    # ✅ 청크 실패 시 지수 백오프 + 1회 재시도
                    backoff = min(2.0, 0.5 * (2 ** chunk_num))
                    logger.warning(f"⚠️ 청크 {chunk_num} 실패 → {backoff:.1f}s 후 1회 재시도")
                    time.sleep(backoff)
                    
                    # 재시도
                    data2 = self._make_api_call(
                        endpoint="quotations/inquire-multiple-price",
                        params={
                            "FID_COND_MRKT_DIV_CODE": market_type,
                            "FID_INPUT_ISCD": symbol_string
                        },
                        tr_id="FHKST11300006"
                    )
                    if data2 and 'output' in data2:
                        results.extend(data2['output'])
                        logger.debug(f"✅ 청크 {chunk_num} 재시도 성공")
                    else:
                        logger.error(f"❌ 청크 {chunk_num} 재시도 실패 (스킵)")
            
            return results if results else None
                
        except Exception as e:
            logger.error(f"관심종목 시세 조회 실패: {e}")
            return None
    
    # === 업종/기타 ===
    
    def get_sector_index(self, sector_code: str) -> Optional[Dict]:
        """
        주요 대표종목 시세 정보 (섹터별 스냅샷)
        
        Note:
            "섹터 지수"가 아닌 해당 섹터의 "대표 종목 묶음" 제공
            실용적인 시장 현황 파악용
        """
        try:
            # ✅ 주요 대형주 정보 (섹터코드 통일: 4자리 형식 사용)
            major_stocks = {
                "0001": [  # 코스피 종합
                    ("005930", "삼성전자"),
                    ("000660", "SK하이닉스"),
                    ("005380", "현대차")
                ],
                "1001": [  # 코스닥 종합 (✅ 실제 코스닥 종목으로 수정)
                    ("247540", "에코프로비엠"),
                    ("091990", "셀트리온헬스케어"),
                    ("293490", "카카오게임즈")
                ],
                "2001": [  # 코스피200
                    ("005930", "삼성전자"),
                    ("000660", "SK하이닉스"),
                    ("005380", "현대차")
                ]
            }
            
            stocks = major_stocks.get(sector_code, [("005930", "삼성전자")])
            index_name_map = {
                "0001": "코스피 주요종목",
                "1001": "코스닥 주요종목",
                "2001": "코스피200 주요종목"
            }
            
            # 주요 종목들의 현재가 조회
            stock_info = []
            for stock_code, stock_name in stocks:
                stock_data = self.get_current_price(stock_code)
                if stock_data:
                    stock_info.append({
                        'code': stock_code,
                        'name': stock_name,
                        'price': self._to_float(stock_data.get('stck_prpr')),
                        'change': self._to_float(stock_data.get('prdy_vrss')),
                        'change_rate': self._to_float(stock_data.get('prdy_ctrt')),
                        'volume': self._to_int(stock_data.get('acml_vol'))
                    })
            
            if stock_info:
                return {
                    'category': index_name_map.get(sector_code, f"주요종목{sector_code}"),
                    'stocks': stock_info,
                    'count': len(stock_info)
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"주요 종목 정보 조회 실패: {sector_code}, {e}")
            return None
    
    def get_market_status(self, holiday_checker: Optional[Callable[[datetime], bool]] = None) -> Optional[Dict]:
        """
        시장 상태 정보 (시간 기반 간이 판정 + 한국 시간대 + 휴장일 지원)
        
        Args:
            holiday_checker: 휴장일 판정 함수 (선택, datetime → bool)
            
        Note:
            실제 거래 환경의 장후 단일가는 16:00~18:00이지만,
            간이 판정을 위해 15:40~16:00로 축약
        """
        try:
            # ✅ 한국 시간대 사용 (서버 로컬 시간 의존 방지)
            try:
                from zoneinfo import ZoneInfo
                now = datetime.now(ZoneInfo("Asia/Seoul"))
            except ImportError:
                # Python < 3.9 또는 zoneinfo 미설치 시 로컬 시간 사용
                logger.debug("zoneinfo 없음, 로컬 시간 사용")
                now = datetime.now()
            hour = now.hour
            minute = now.minute
            weekday = now.weekday()  # 0=월요일, 6=일요일
            
            # ✅ 휴장일 체크 (외부 함수)
            if holiday_checker and holiday_checker(now):
                return {
                    'status': '휴장 (공휴일)',
                    'is_open': False,
                    'current_time': now.strftime('%Y-%m-%d %H:%M:%S'),
                    'weekday': ['월', '화', '수', '목', '금', '토', '일'][weekday],
                    'note': '공휴일 또는 임시 휴장'
                }
            
            # 주말 체크
            is_weekend = weekday >= 5
            
            # 장 운영 시간: 평일 09:00 ~ 15:30
            is_market_open = not is_weekend and ((9 <= hour < 15) or (hour == 15 and minute <= 30))
            
            # 장전 시간외: 08:30 ~ 08:59
            is_pre_market = (not is_weekend) and (hour == 8 and 30 <= minute <= 59)
            
            # 장후 시간외: 15:40 ~ 16:00 (간이 판정, 실제는 18:00까지)
            is_after_market = (not is_weekend) and (
                (hour == 15 and minute >= 40) or (hour == 16 and minute < 1)  # ✅ 16:00:xx까지
            )
            
            if is_weekend:
                status_text = "주말 휴장"
            elif is_market_open:
                status_text = "정규장 개장 중"
            elif is_pre_market:
                status_text = "장전 시간외"
            elif is_after_market:
                status_text = "장후 시간외"
            else:
                status_text = "장 마감"
            
            return {
                'status': status_text,
                'is_open': is_market_open,
                'current_time': now.strftime('%Y-%m-%d %H:%M:%S'),
                'weekday': ['월', '화', '수', '목', '금', '토', '일'][weekday],
                'market_hours': '09:00 ~ 15:30 (정규장)',
                'pre_market': '08:30 ~ 09:00 (장전 시간외)',
                'after_market': '15:40 ~ 16:00 (장후 시간외)'
            }
        except Exception as e:
            logger.error(f"시장 상태 조회 실패: {e}")
            return None
    
    def get_news_title(self) -> Optional[List[Dict]]:
        """
        종합 시황/공시 제목 조회 (폴백 경로 + 선호 엔드포인트 캐시)
        
        Note:
            뉴스 전용 TR_ID가 없어 tr_id 생략 (엔드포인트 자체가 뉴스 전용)
            ✅ 실패 시 선호 엔드포인트 무효화 (네트워크 플립 대응)
        """
        try:
            # ✅ 선호 엔드포인트가 있으면 먼저 시도 (지연 감소)
            preferred = self._preferred_endpoints.get('news')
            candidates = ("quote/news-title", "quotations/news-title", "news/news-title")
            
            if preferred:
                candidates = (preferred,) + tuple(c for c in candidates if c != preferred)
            
            for endpoint in candidates:
                data = self._make_api_call(
                    endpoint, 
                    {"FID_COND_MRKT_DIV_CODE": "J"},
                    tr_id=""  # ✅ 뉴스는 TR_ID 불필요
                )
                if data and data.get('output'):
                    # ✅ 성공한 엔드포인트 기억
                    self._preferred_endpoints['news'] = endpoint
                    return data['output']
            
            # ✅ 모든 후보 실패 시 선호 엔드포인트 무효화 (네트워크 플립 복구)
            if 'news' in self._preferred_endpoints:
                old_pref = self._preferred_endpoints.pop('news')
                logger.debug(f"🔄 뉴스 선호 엔드포인트 무효화: {old_pref}")
            
            logger.warning("⚠️ 뉴스 엔드포인트 후보 모두 실패")
            return None
        except Exception as e:
            logger.error(f"뉴스 제목 조회 실패: {e}")
            return None
    
    # === 실시간시세 ===
    
    def get_realtime_price(self, symbol: str) -> Optional[Dict]:
        """실시간 현재가 조회 (체결가)"""
        try:
            # 주의: 실시간은 웹소켓 권장, REST는 지연 시세
            data = self._make_api_call(
                endpoint="quotations/inquire-price",
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol
                },
                tr_id="FHKST01010100",
                use_cache=False  # 실시간은 캐시 안 함
            )
            # ✅ _first_output() 활용
            return self._first_output(data)
        except Exception as e:
            logger.error(f"실시간 가격 조회 실패: {symbol}, {e}")
            return None
    
    def get_realtime_asking_price(self, symbol: str) -> Optional[Dict]:
        """실시간 호가 조회"""
        try:
            # 주의: 실시간은 웹소켓 권장, REST는 지연 시세
            data = self._make_api_call(
                endpoint="quotations/inquire-asking-price-exp-ccn",
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol
                },
                tr_id="FHKST01010200",
                use_cache=False  # 실시간은 캐시 안 함
            )
            # ✅ _first_output() 활용
            return self._first_output(data)
        except Exception as e:
            logger.error(f"실시간 호가 조회 실패: {symbol}, {e}")
            return None
    
    # === 종합 분석 메서드 ===
    
    def analyze_stock_comprehensive(self, code_or_name: str) -> Optional[Dict]:
        """
        종합적인 종목 분석 (종목코드 또는 종목명)
        
        Args:
            code_or_name: 종목코드(6자리) 또는 종목명
            
        Returns:
            종합 분석 결과 딕셔너리 또는 None
            
        Example:
            # 종목코드로 조회
            analysis = mcp.analyze_stock_comprehensive("005930")
            
            # 종목명으로 조회
            analysis = mcp.analyze_stock_comprehensive("삼성전자")
            analysis = mcp.analyze_stock_comprehensive("시프트업")
        """
        try:
            # ✅ 종목코드/종목명 → 종목코드 변환
            symbol = self._resolve_symbol(code_or_name)
            
            if not symbol:
                logger.error(f"❌ 종목을 찾을 수 없습니다: '{code_or_name}'")
                return None
            
            if symbol != code_or_name:
                logger.info(f"🔍 종목명 '{code_or_name}' → 코드 '{symbol}' 변환")
            
            # 기본 정보 수집
            basic_info = self.get_stock_basic_info(symbol)
            current_price = self.get_current_price(symbol)
            financial_ratios = self.get_financial_ratios(symbol)
            investor_trend = self.get_investor_trend(symbol)
            chart_data = self.get_chart_data(symbol)
            
            if not basic_info or not current_price:
                return None
            
            # 분석 결과 구성
            # ✅ 재무지표 출처 일관화: financial_ratios 우선, 없으면 basic_info
            fin = financial_ratios or {}
            price_val = self._to_float(current_price.get('stck_prpr'), 0)  # ✅ 안전한 변환
            
            # ✅ PER, PBR 계산 (공통 헬퍼 사용)
            eps = self._to_float(fin.get('eps'), 0)
            bps = self._to_float(fin.get('bps'), 0)
            per, pbr = self._compute_per_pbr(price_val, eps, bps)
            
            # 계산 실패 시 basic_info 폴백
            if per is None:
                per = self._to_float(basic_info.get('per'))
            if pbr is None:
                pbr = self._to_float(basic_info.get('pbr'))
            
            # ✅ 종목명 가져오기 (여러 소스에서 폴백)
            stock_name = (
                basic_info.get('prdt_name') or 
                basic_info.get('prdt_abrv_name') or 
                current_price.get('hts_kor_isnm') or 
                basic_info.get('hts_kor_isnm') or
                f"종목{symbol}"  # 최후의 수단
            )
            
            # ✅ 섹터 보정 및 표준화 적용 (인스턴스 필드 사용)
            sector = basic_info.get('bstp_kor_isnm', '')
            if symbol in self._sector_overrides:
                sector = self._sector_overrides[symbol]
            sector = self._normalize_sector(sector)  # ✅ 표준화
            
            analysis = {
                'symbol': symbol,
                'name': stock_name,
                'current_price': price_val,
                'change_rate': self._to_float(current_price.get('prdy_ctrt')),  # ✅ 통일
                'market_cap': self._to_float(basic_info.get('hts_avls')) * 100_000_000,  # ✅ 안전한 파싱
                'sector': sector,  # ✅ 보정된 섹터
                
                # ✅ 기본 지표 (financial_ratios 우선)
                'valuation_metrics': {
                    'per': per,
                    'pbr': pbr,
                    'roe': self._to_float(fin.get('roe_val') or basic_info.get('roe')),
                    'roa': self._to_float(fin.get('roa_val') or basic_info.get('roa')),
                    'debt_ratio': self._to_float(fin.get('debt_ratio') or basic_info.get('debt_ratio')),
                    'current_ratio': self._to_float(fin.get('current_ratio') or basic_info.get('current_ratio')),
                    'dividend_yield': self._to_float(basic_info.get('dvyd')) if basic_info.get('dvyd') else None
                },
                
                # ✅ 거래 정보 (안전한 파싱)
                'trading_info': {
                    'volume': self._to_int(current_price.get('acml_vol')),
                    'trading_value': self._to_int(current_price.get('acml_tr_pbmn')),
                    'high_52w': self._to_float(current_price.get('w52_hgpr')),
                    'low_52w': self._to_float(current_price.get('w52_lwpr'))
                },
                
                # 투자자 동향
                'investor_trend': self._analyze_investor_trend(investor_trend),
                
                # 기술적 분석
                'technical_analysis': self._analyze_technical(chart_data),
                
                # 종합 점수
                'comprehensive_score': self._calculate_comprehensive_score(
                    basic_info, current_price, financial_ratios, investor_trend, chart_data
                )
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"종합 분석 실패: {symbol}, {e}")
            return None
    
    def _analyze_investor_trend(self, investor_data: Optional[Dict]) -> Dict:
        """투자자 동향 분석"""
        if not investor_data:
            return {'sentiment': 'neutral', 'score': 50}
        
        try:
            # ✅ 안전한 숫자 파싱 (_to_int 사용)
            institutional = self._to_int(investor_data.get('ntby_qty'))
            foreign = self._to_int(investor_data.get('frgn_ntby_qty'))
            individual = self._to_int(investor_data.get('prsn_ntby_qty'))
            
            # 스마트머니 지표 (기관 + 외국인)
            smart_money = institutional + foreign
            
            # 감정 점수 계산 (0-100)
            if smart_money > 10000:  # 1만주 이상 순매수
                sentiment_score = min(100, 70 + min(20, smart_money / 5000))
                sentiment = 'positive'
            elif smart_money < -10000:  # 1만주 이상 순매도
                sentiment_score = max(0, 30 + max(-20, smart_money / 5000))
                sentiment = 'negative'
            else:
                sentiment_score = 50
                sentiment = 'neutral'
            
            # ✅ return을 else 블록 밖으로 이동!
            return {
                'sentiment': sentiment,
                'score': sentiment_score,
                'institutional_net': institutional,
                'foreign_net': foreign,
                'individual_net': individual,
                'smart_money': smart_money
            }
                
        except Exception as e:
            logger.error(f"투자자 동향 분석 실패: {e}")
            return {'sentiment': 'neutral', 'score': 50}
    
    def _analyze_technical(self, chart_data: Optional[List[Dict]]) -> Dict:
        """기술적 분석"""
        if not chart_data or len(chart_data) < 20:
            return {'trend': 'neutral', 'momentum': 'neutral', 'score': 50}
        
        try:
            # 최근 20일 데이터로 분석
            recent_data = chart_data[-20:]
            
            # 단순 이동평균 계산 (✅ 안전한 숫자 파싱)
            prices = [self._to_float(d.get('stck_clpr')) for d in recent_data]
            sma_5 = sum(prices[-5:]) / 5
            sma_20 = sum(prices) / 20
            
            # 추세 분석
            if sma_5 > sma_20 * 1.02:
                trend = 'uptrend'
                trend_score = 70
            elif sma_5 < sma_20 * 0.98:
                trend = 'downtrend'
                trend_score = 30
            else:
                trend = 'sideways'
                trend_score = 50
            
            # 모멘텀 분석 (RSI 유사)
            gains = []
            losses = []
            for i in range(1, len(prices)):
                change = prices[i] - prices[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
            
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            
            if avg_loss == 0:
                momentum_score = 95  # ✅ 100 → 95 캡핑 (과도한 값 방지)
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                momentum_score = rsi
            
            # 종합 기술적 점수
            technical_score = (trend_score + momentum_score) / 2
            
            return {
                'trend': trend,
                'momentum': 'strong' if momentum_score > 70 else 'weak' if momentum_score < 30 else 'neutral',
                'score': technical_score,
                'sma_5': sma_5,
                'sma_20': sma_20,
                'rsi': momentum_score
                }
                
        except Exception as e:
            logger.error(f"기술적 분석 실패: {e}")
            return {'trend': 'neutral', 'momentum': 'neutral', 'score': 50}
    
    def _calculate_growth_score(self, chart_data: Optional[List[Dict]], current_price: Optional[Dict]) -> float:
        """
        성장성 점수 계산 (차트 데이터 기반)
        
        Args:
            chart_data: 차트 데이터 (일봉)
            current_price: 현재가 정보
            
        Returns:
            성장성 점수 (0~100)
            
        Note:
            - 12개월 수익률 (가격 성장)
            - 거래대금 모멘텀 (관심도 증가)
            - 52주 고점 대비 위치
        """
        try:
            if not chart_data or len(chart_data) < 60:
                return 50  # 데이터 부족 시 중립
            
            score = 50  # 기본 점수
            
            # 1. 12개월 수익률 (최대 30점)
            if len(chart_data) >= 250:  # 12개월 데이터
                price_12m_ago = self._to_float(chart_data[-250].get('stck_clpr'))
                price_now = self._to_float(chart_data[-1].get('stck_clpr'))
                
                if price_12m_ago > 0:
                    return_12m = ((price_now - price_12m_ago) / price_12m_ago) * 100
                    
                    if return_12m > 50:
                        score += 30
                    elif return_12m > 30:
                        score += 20
                    elif return_12m > 10:
                        score += 10
                    elif return_12m < -30:
                        score -= 20
                    elif return_12m < -10:
                        score -= 10
            
            # 2. 거래대금 모멘텀 (최대 20점)
            if current_price and len(chart_data) >= 20:
                # 최근 20일 평균 거래대금
                recent_20 = chart_data[-20:]
                avg_trading_value = sum(
                    self._to_float(d.get('acml_tr_pbmn', 0)) 
                    for d in recent_20
                ) / 20
                
                # 전체 평균 대비
                if len(chart_data) >= 60:
                    prev_60 = chart_data[-80:-20]  # 20~80일 전
                    avg_prev = sum(
                        self._to_float(d.get('acml_tr_pbmn', 0)) 
                        for d in prev_60
                    ) / 60
                    
                    if avg_prev > 0:
                        momentum = ((avg_trading_value - avg_prev) / avg_prev) * 100
                        
                        if momentum > 50:
                            score += 20
                        elif momentum > 20:
                            score += 10
                        elif momentum < -30:
                            score -= 10
            
            # 3. 52주 고점 대비 위치 (최대 +10점)
            if current_price:
                current = self._to_float(current_price.get('stck_prpr'))
                high_52w = self._to_float(current_price.get('w52_hgpr'))
                
                if high_52w > 0 and current > 0:
                    position = (current / high_52w) * 100
                    
                    if position > 95:  # 고점 갱신 근처
                        score += 10
                    elif position > 85:
                        score += 5
                    elif position < 60:  # 고점 대비 많이 하락
                        score -= 5
            
            return max(0, min(100, score))  # 0~100 범위
            
        except Exception as e:
            logger.debug(f"성장성 점수 계산 실패: {e}")
            return 50  # 오류 시 중립
    
    def _calculate_comprehensive_score(self, basic_info: Dict, current_price: Dict,
                                     financial_ratios: Optional[Dict],
                                     investor_trend: Optional[Dict],
                                     chart_data: Optional[List[Dict]]) -> Dict:
        """종합 점수 계산 (✅ 재무지표 출처 일관화: financial_ratios 우선)"""
        try:
            scores = {}
            weights = {
                'valuation': 0.3,      # 밸류에이션 30%
                'profitability': 0.25,  # 수익성 25%
                'stability': 0.2,       # 안정성 20%
                'growth': 0.15,         # 성장성 15%
                'sentiment': 0.1        # 투자자 감정 10%
            }
            
            # ✅ 재무지표 우선 사용 (_to_float으로 안전하게)
            fin = financial_ratios or {}
            price_val = self._to_float(current_price.get('stck_prpr'), 0)
            
            # ✅ PER, PBR 계산 (공통 헬퍼 사용)
            eps = self._to_float(fin.get('eps'), 0)
            bps = self._to_float(fin.get('bps'), 0)
            per, pbr = self._compute_per_pbr(price_val, eps, bps)
            
            # 계산 실패 시 basic_info 폴백
            if per is None:
                per = self._to_float(basic_info.get('per'))
            if pbr is None:
                pbr = self._to_float(basic_info.get('pbr'))
            
            # 밸류에이션 점수 (PER, PBR 기준)
            valuation_score = 50
            
            if per and per > 0:
                if per < 15:
                    valuation_score += 20
                elif per < 25:
                    valuation_score += 10
                elif per > 50:
                    valuation_score -= 20
            
            if pbr and pbr > 0:
                if pbr < 1.5:
                    valuation_score += 20
                elif pbr < 2.5:
                    valuation_score += 10
                elif pbr > 5:
                    valuation_score -= 20
            
            # 수익성 점수 (ROE, ROA 기준) - ✅ financial_ratios 우선
            profitability_score = 50
            roe = self._to_float(fin.get('roe_val') or basic_info.get('roe'), 0)
            roa = self._to_float(fin.get('roa_val') or basic_info.get('roa'), 0)
            
            if roe and roe > 0:
                if roe > 15:
                    profitability_score = 80
                elif roe > 10:
                    profitability_score = 70
                elif roe > 5:
                    profitability_score = 60
            else:
                profitability_score = 40
            
            # 안정성 점수 (부채비율, 유동비율 기준) - ✅ financial_ratios 우선
            stability_score = 50
            debt_ratio = self._to_float(fin.get('debt_ratio') or basic_info.get('debt_ratio'), 0)
            
            # ✅ 유동비율 단위 정규화 (퍼센트 → 배수)
            current_ratio_raw = self._to_float(fin.get('current_ratio') or basic_info.get('current_ratio'), 0)
            current_ratio = self._norm_ratio(current_ratio_raw)  # 배수 기준으로 통일 (예: 120% → 1.2)
            
            if debt_ratio > 0:  # ✅ 데이터가 있을 때만
                if debt_ratio < 30:
                    stability_score = 80
                elif debt_ratio < 50:
                    stability_score = 70
                elif debt_ratio < 70:
                    stability_score = 60
                else:
                    stability_score = 40
            
            # ✅ 배수 기준으로 비교 (1.0 = 100%)
            if current_ratio >= 2.0:
                stability_score += 10
            elif current_ratio > 0 and current_ratio < 1.0:
                stability_score -= 20
            
            # ✅ 성장성 점수 (차트 데이터 기반 계산)
            growth_score = self._calculate_growth_score(chart_data, current_price)
            
            # 투자자 감정 점수
            sentiment_score = 50
            if investor_trend:
                sentiment_analysis = self._analyze_investor_trend(investor_trend)
                sentiment_score = sentiment_analysis['score']
            
            # 가중평균 계산
            total_score = (
                valuation_score * weights['valuation'] +
                profitability_score * weights['profitability'] +
                stability_score * weights['stability'] +
                growth_score * weights['growth'] +
                sentiment_score * weights['sentiment']
            )
            
            return {
                'total_score': round(total_score, 1),
                'component_scores': {
                    'valuation': valuation_score,
                    'profitability': profitability_score,
                    'stability': stability_score,
                    'growth': growth_score,
                    'sentiment': sentiment_score
                },
                'grade': self._get_grade(total_score),
                'recommendation': self._get_recommendation(total_score)
            }
            
        except Exception as e:
            logger.error(f"종합 점수 계산 실패: {e}")
            return {'total_score': 50, 'grade': 'C', 'recommendation': 'HOLD'}
    
    def _get_grade(self, score: float) -> str:
        """점수에 따른 등급 반환"""
        if score >= 80:
            return 'A+'
        elif score >= 70:
            return 'A'
        elif score >= 60:
            return 'B+'
        elif score >= 50:
            return 'B'
        elif score >= 40:
            return 'C+'
        elif score >= 30:
            return 'C'
        else:
            return 'D'
    
    def _get_recommendation(self, score: float) -> str:
        """점수에 따른 추천 반환"""
        if score >= 75:
            return 'STRONG_BUY'
        elif score >= 65:
            return 'BUY'
        elif score >= 55:
            return 'HOLD'
        elif score >= 45:
            return 'WEAK_HOLD'
        else:
            return 'SELL'
    
    def get_dividend_ranking(self, limit: int = 100, use_pagination: bool = True) -> Optional[List[Dict]]:
        """
        배당률 상위 종목 조회 (페이지네이션 지원, 가치주 발굴에 유용)
        
        Args:
            limit: 조회할 최대 종목 수
            use_pagination: 페이지네이션 사용 여부 (True: 전체 데이터, False: 1페이지만)
        """
        try:
            from datetime import datetime, timedelta
            
            # 최근 1년 기준
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            
            base_params = {
                "GB1": "0",  # 전체
                "UPJONG": "0001",  # 코스피 종합
                "GB2": "0",  # 전체
                "GB3": "2",  # 현금배당
                "F_DT": start_date.strftime("%Y%m%d"),
                "T_DT": end_date.strftime("%Y%m%d"),
                "GB4": "0"  # 전체
            }
            
            # ✅ 페이지네이션 지원 (CTX 토큰 방식)
            if use_pagination:
                all_data = self._fetch_all_pages(
                    endpoint="ranking/dividend-rate",
                    base_params=base_params,
                    tr_id="HHKDB13470100",
                    ctx_keys={"in": "CTS_AREA", "out": "cts_area"},  # ✨ CTX 방식
                    max_pages=5,  # 배당 데이터는 많지 않으므로 5페이지 충분
                    use_cache=True
                )
                
                if all_data:
                    logger.debug(f"📊 배당률 순위 페이지네이션: {len(all_data)}개 (요청: {limit}개)")
                    return all_data[:limit]
                else:
                    logger.warning("⚠️ 배당률 순위 조회 실패: 데이터 없음")
                    return None
            else:
                # 기존 방식 (1페이지만)
                base_params["CTS_AREA"] = " "  # 초기값
                data = self._make_api_call(
                    endpoint="ranking/dividend-rate",
                    params=base_params,
                    tr_id="HHKDB13470100",
                    use_cache=True
                )
                
                if data and 'output' in data:
                    results = data['output']
                    logger.debug(f"📊 배당률 순위 API 응답: {len(results)}개 (요청: {limit}개)")
                    return results[:limit]
                
                logger.warning("⚠️ 배당률 순위 조회 실패: output 없음")
                return None
            
        except Exception as e:
            logger.error(f"❌ 배당률 순위 조회 실패: {e}")
            return None
    
    def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """종목 기본 정보 조회 (섹터 포함)"""
        try:
            data = self._make_api_call(
                endpoint="quotations/search-info",
                params={
                    "PDNO": symbol,
                    "PRDT_TYPE_CD": "300"  # 주식
                },
                tr_id="CTPF1604R"
            )
            
            if data and 'output' in data:
                output = data['output']
                if isinstance(output, list) and len(output) > 0:
                    return output[0]
                elif isinstance(output, dict):
                    return output
            return None
            
        except Exception as e:
            logger.error(f"종목 정보 조회 실패: {symbol}, {e}")
            return None
    
    def find_real_value_stocks(
        self, 
        limit: int = 50, 
        criteria: Dict = None, 
        candidate_pool_size: int = 200, 
        stock_universe: List[str] = None,
        sector_caps: Dict[str, float] = None,
        min_trading_value: float = 1_000_000_000,  # ✅ 10억원 (중소형주 포함, 유동성 확보)
        momentum_filter: Dict = None,
        quality_check: bool = True,
        sector_neutral: bool = True,
        max_position_weight: float = 0.10,
        momentum_scoring: bool = True,
        score_weights: Dict[str, float] = None,
        exclude_holdings: bool = True,  # ✅ NEW: 지주회사 제외 (SOTP 필요)
        exclude_policy_risk: bool = True  # ✅ NEW: 정책 민감 기업 제외
    ) -> Optional[List[Dict]]:
        """
        진짜 가치주 발굴 (밸류 + 품질 + 리스크 관리 + 섹터 중립화) 🎯
        
        Args:
            limit: 발굴할 최대 종목 수
            criteria: 가치주 기준 (per_max, pbr_max, roe_min, min_volume)
            candidate_pool_size: 후보군 크기 (기본 200개)
            stock_universe: 외부에서 제공하는 종목 리스트 (코드 리스트)
            
            ✅ 리스크 관리 파라미터 (초보수적 기본값)
            sector_caps: 섹터별 최대 비중 제한 
                예: {'금융': 0.15, '제조': 0.40, '기타': 0.30}
                기본값: {'금융': 0.20, '지주회사': 0.15, '기타': 0.35}
                ※ 보험은 금융에 포함됨
                ※ ChatGPT 권장: 은행 2~3개, 정책·사이클 민감 감점
            
            min_trading_value: 최소 거래대금 (원)
                예: 10_000_000_000 (100억)
                기본값: 5_000_000_000 (50억) - 체결 리스크 축소
            
            momentum_filter: 모멘텀 필터 (극단 하락 제외)
                예: {'min_3m_return': -30.0}  # 최근 3개월 -30% 이상 하락 제외
                기본값: None (필터 없음)
            
            quality_check: 품질 체크 활성화 (부채비율, 유동비율)
                기본값: True
            
            ✅ NEW: 엣지 강화 파라미터 (군중과의 차별화)
            sector_neutral: 섹터 내 퍼센타일 랭킹 활성화
                True: 같은 섹터끼리만 비교 (섹터 편향 제거)
                기본값: True
            
            max_position_weight: 개별 종목 최대 비중
                예: 0.10 = 10% (특정 종목 과도 집중 방지)
                기본값: 0.10
            
            momentum_scoring: 모멘텀 가점 활성화
                True: 6개월 수익률로 추가 점수 (가치+모멘텀 조합)
                기본값: True
            
            score_weights: 점수 가중치 커스터마이징
                예: {'value': 0.60, 'investor': 0.10, 'trading': 0.10, ...}
                기본값: {'value': 0.50, 'investor': 0.10, 'trading': 0.10, 
                         'technical': 0.10, 'dividend': 0.05, 'stability': 0.10, 'sector': 0.05}
            
            ✅ NEW: 보수 필터 (ChatGPT 권장)
            exclude_holdings: 지주회사·투자회사 제외
                True: SOTP 없이 평가 불가능한 지주/투자회사 제외
                기본값: True
            
            exclude_policy_risk: 정책·사이클 민감 기업 제외
                True: 한국전력/항공/해운 등 제외
                기본값: True
            
        Returns:
            가치주 리스트 (점수순 정렬)
            
        Note:
            각 순위 API는 30~100개 수준만 반환하므로 여러 API를 조합
            - 거래량: 약 30개
            - 시가총액: 약 50~100개
            - PER: 약 50~100개
            - 배당: 약 100개
            → 총 200~300개 수준의 후보군 확보 가능
            
        Example:
            # 기본 전략 (ChatGPT A- 등급)
            stocks = mcp.find_real_value_stocks(limit=20)
            # → 금융 20%, 지주 제외, 정책/사이클 제외, 거래대금 50억+
            
            # 초보수적 전략 (ChatGPT A0 등급)
            stocks = mcp.find_real_value_stocks(
                limit=20,
                sector_caps={'금융': 0.15, '지주회사': 0.10, '기타': 0.30},
                min_trading_value=10_000_000_000,
                momentum_filter={'min_3m_return': -30.0},
                max_position_weight=0.08  # 개별 상한 8%
            )
            
        운영 가이드 (ChatGPT 권장):
            - 리밸런스 주기: 월 1회 (모멘텀 창과 정합)
            - 리스크 제어: 종목당 -15%/월 초과 하락 시 모멘텀 리셋
            - 현금 정책: 종목 수×상한 < 100%이면 현금 보유 (방어적)
            - 모멘텀 기준: N≥252→6M, 126≤N<252→6M, 60≤N<126→3M
            - 섹터 캡: 금융(보험 포함) 20%, 지주 0%, 정책/사이클 0%
            
        신뢰도 등급 (ChatGPT 평가):
            - 데이터: A (KIS/거래소 공식)
            - 신호: A- (섹터 분산, 리스크 제외, 모멘텀)
            - 포트폴리오: A- (비중 관리, 현금 정책)
            → 종합: A- (실전 투자 가능)
        """
        try:
            # ✅ 품질 메트릭 추적 (ChatGPT 권장)
            quality_metrics = {
                'sector_coverage': 0.0,
                'momentum_success': 0.0,
                'price_fetch_rate': 0.0,
                'total_candidates': 0,
                'sector_mapped': 0,
            }
            
            # ✅ 기본 기준 설정
            if criteria is None:
                criteria = {
                    'per_max': 18.0,   # ✅ 15 → 18 완화 (더 많은 종목 발견)
                    'pbr_max': 2.0,    # ✅ 1.5 → 2.0 완화
                    'roe_min': 8.0,    # ✅ 10 → 8 완화
                    'min_volume': 100000  # ✅ 100만 → 10만 완화 (유동성 기준)
                }
            
            # ✅ 섹터 비중 제한 설정 (초보수적 기본값)
            if sector_caps is None:
                sector_caps = {
                    '금융': 0.20,  # ✅ 금융 20% (보험 포함, ChatGPT 권장: 은행 2~3개)
                    '지주회사': 0.15,  # ✅ 지주회사 15% (NAV 갭·유동성 리스크)
                    '기타': 0.35   # ✅ 기타 섹터 35% (더 강한 분산)
                }
            
            # ✅ 품질 기준 설정 (파라미터화, 배수 기준 통일)
            quality_criteria = {
                'max_debt_ratio': 200.0,    # 부채비율 200% 이하
                'min_current_ratio': 1.0,   # ✅ 유동비율 1.0배(100%) 이상 (배수 기준)
                'min_eps': 0.0               # EPS 양수 (적자 제외)
            } if quality_check else None
            
            # ✅ 점수 가중치 설정 (커스터마이징 가능)
            if score_weights is None:
                score_weights = {
                    'value': 0.50,      # 가치 50%
                    'investor': 0.10,   # 투자자 10%
                    'trading': 0.10,    # 거래 10%
                    'technical': 0.10,  # 기술 10%
                    'dividend': 0.05,   # 배당 5%
                    'stability': 0.10,  # 안정 10%
                    'sector': 0.05      # 섹터 5%
                }
            
            # ✅ 가중치 합이 1.0인지 검증
            weight_sum = sum(score_weights.values())
            if abs(weight_sum - 1.0) > 0.01:
                logger.warning(
                    f"⚠️ 점수 가중치 합이 1.0이 아님 ({weight_sum:.2f}) → 자동 정규화"
                )
                score_weights = {k: v / weight_sum for k, v in score_weights.items()}
            
            logger.info(
                f"🎯 가치주 발굴 시작: "
                f"✅ 업종별 기준 적용 (금융 12/1.2/12%, 제조 18/2.0/10%, 운송·전기 15/1.5/10%) | "
                f"섹터 제한={sector_caps}, 거래대금≥{min_trading_value or 0:,.0f}원, "
                f"품질체크={'ON' if quality_check else 'OFF'} | "
                f"가중치=가치{score_weights['value']*100:.0f}%"
            )
            
            # 1단계: 후보 수집
            candidates = []
            
            # ✅ 외부 종목 리스트가 제공된 경우 (기존 시스템 활용!)
            if stock_universe:
                # Dict 형태 {코드: 전체데이터} 지원
                if isinstance(stock_universe, dict):
                    logger.debug(f"✅ 외부 종목 유니버스 사용 (전체 데이터): {len(stock_universe)}개")
                    for symbol, data in list(stock_universe.items())[:candidate_pool_size]:
                        if isinstance(data, dict):
                            # 전체 데이터가 제공됨 (중복 조회 방지!)
                            candidates.append({
                                'mksc_shrn_iscd': symbol,
                                'hts_kor_isnm': data.get('name', ''),
                                'stck_prpr': str(data.get('current_price', 0)),
                                'acml_vol': str(data.get('volume', 0)),
                                'prdy_ctrt': str(data.get('change_rate', 0)),
                                '_preloaded_data': data  # ✅ 전체 데이터 보관
                            })
                        else:
                            # 종목명만 제공됨 (기존 방식)
                            candidates.append({
                                'mksc_shrn_iscd': symbol,
                                'hts_kor_isnm': data if isinstance(data, str) else '',
                                'stck_prpr': '0',
                                'acml_vol': '0',
                                'prdy_ctrt': '0'
                            })
                    logger.debug(f"✅ 1단계 완료: {len(candidates)}개 후보 (외부 딕셔너리)")
                # List 형태 [코드1, 코드2, ...] 지원
                elif isinstance(stock_universe, list):
                    logger.debug(f"✅ 외부 종목 유니버스 사용 (코드 리스트): {len(stock_universe)}개")
                    for symbol in stock_universe[:candidate_pool_size]:
                        candidates.append({
                            'mksc_shrn_iscd': symbol,
                            'hts_kor_isnm': '',  # 나중에 조회
                            'stck_prpr': '0',
                            'acml_vol': '0',
                            'prdy_ctrt': '0'
                        })
                    logger.debug(f"✅ 1단계 완료: {len(candidates)}개 후보 (외부 리스트)")
            else:
                # 기존 방식: 순위 API 조합
                # 📌 각 API는 30~100개씩만 반환하므로 여러 API를 조합해서 다양한 종목 확보
                
                # 1-1. 거래량 상위 종목 (유동성) - 약 30개
                logger.debug(f"1-1단계: 거래량 상위 종목 조회 (약 30개)...")
                volume_stocks = self.get_volume_ranking()
                if volume_stocks:
                    candidates.extend(volume_stocks)
                    logger.debug(f"✅ 거래량 상위 {len(volume_stocks)}개 조회")
                else:
                    logger.warning("⚠️ 거래량 순위 조회 실패")
                
                # 1-2. 시가총액 상위 종목 (대형주) - 약 50~100개
                if len(candidates) < candidate_pool_size:
                    logger.debug(f"1-2단계: 시가총액 상위 종목 조회 (약 50~100개)...")
                    market_cap_stocks = self.get_market_cap_ranking()
                    if market_cap_stocks:
                        for stock in market_cap_stocks:
                            symbol = stock.get('mksc_shrn_iscd', '')
                            if symbol and not any(c.get('mksc_shrn_iscd') == symbol for c in candidates):
                                candidates.append(stock)
                        logger.debug(f"✅ 시가총액 상위 {len(market_cap_stocks)}개 추가 (중복 제외 후: {len(candidates)}개)")
                
                # 1-3. PER 순위 (저PER 가치주) - 약 50~100개
                if len(candidates) < candidate_pool_size:
                    logger.debug(f"1-3단계: PER 순위 조회 (약 50~100개)...")
                    per_stocks = self.get_per_ranking()
                    if per_stocks:
                        for stock in per_stocks:
                            symbol = stock.get('mksc_shrn_iscd', '')
                            if symbol and not any(c.get('mksc_shrn_iscd') == symbol for c in candidates):
                                candidates.append(stock)
                        logger.debug(f"✅ PER 순위 {len(per_stocks)}개 추가 (중복 제외 후: {len(candidates)}개)")
                
                # 1-4. 배당률 상위 종목 (가치주 특성) - 약 100개
                if len(candidates) < candidate_pool_size:
                    logger.debug(f"1-4단계: 배당률 상위 종목 조회 (약 100개)...")
                    dividend_stocks = self.get_dividend_ranking(limit=100)
                    if dividend_stocks:
                        added = 0
                        for stock in dividend_stocks:
                            symbol = stock.get('stk_shrn_cd', '') or stock.get('mksc_shrn_iscd', '')
                            if symbol and len(symbol) == 6:
                                if not any(c.get('mksc_shrn_iscd') == symbol for c in candidates):
                                    candidates.append({
                                        'mksc_shrn_iscd': symbol,
                                        'hts_kor_isnm': stock.get('hts_kor_isnm', ''),
                                        'stck_prpr': stock.get('stck_prpr', '0'),
                                        'acml_vol': stock.get('acml_vol', '0'),
                                        'prdy_ctrt': stock.get('prdy_ctrt', '0')
                                    })
                                    added += 1
                        logger.debug(f"✅ 배당주 {added}개 추가 (중복 제외 후: {len(candidates)}개)")
                
                logger.debug(f"✅ 1단계 완료: 총 {len(candidates)}개 후보 종목 (목표: {candidate_pool_size}개)")
            
            # 2단계: 각 종목의 재무비율 조회 및 가치주 판별
            value_stocks = []
            checked_count = 0
            
            logger.info(f"2단계 시작: {len(candidates)}개 종목 재무 분석... [✅ v2.3 소프트 필터 적용]")
            logger.info(f"🔍 [DEBUG] 탈락 추적 활성화 - 모든 탈락 사유를 INFO 레벨로 출력합니다")
            
            # ✅ 중복 API 호출 방지: 전체 데이터가 이미 있는지 확인
            preloaded_count = sum(1 for c in candidates if c.get('_preloaded_data'))
            
            if preloaded_count > 0:
                logger.info(f"✅ 외부에서 {preloaded_count}개 종목 데이터 제공 (재조회 생략)")
                # 전체 데이터를 price_map으로 변환
                price_map = {}
                for c in candidates:
                    symbol = c.get('mksc_shrn_iscd')
                    preloaded = c.get('_preloaded_data')
                    if symbol and preloaded:
                        # 기존 데이터 형식으로 변환 (필드명 매핑)
                        price_map[symbol] = {
                            'stck_prpr': str(preloaded.get('current_price', 0)),
                            'acml_vol': str(preloaded.get('volume', 0)),
                            'prdy_ctrt': str(preloaded.get('change_rate', 0)),
                            'hts_avls': str(preloaded.get('market_cap', 0) / 100000000),  # 원 → 억원
                            'per': str(preloaded.get('per', 0)),
                            'pbr': str(preloaded.get('pbr', 0)),
                            'eps': str(preloaded.get('eps', 0)),
                            'bps': str(preloaded.get('bps', 0)),
                            # ✅ 거래대금 필드 추가
                            'acml_tr_pbmn': str(preloaded.get('trading_value', 0)),
                        }
                quality_metrics['price_fetch_rate'] = 1.0  # 100% 제공됨
            else:
                # ✅ 성능 최적화: 배치로 현재가 조회 (하지만 API 안정성 우선)
                # 개별 조회 방식 사용 (배치 API는 404 오류 발생)
                symbols_to_fetch = [c.get('mksc_shrn_iscd') for c in candidates if c.get('mksc_shrn_iscd')]
                logger.info(f"📦 개별 조회로 {len(symbols_to_fetch)}개 종목 시세 수집")
                price_map = self._hydrate_current_prices(symbols_to_fetch, use_batch=False)
                logger.info(f"✅ 배치 조회 완료: {len(price_map)}/{len(symbols_to_fetch)}개")
                
                # ✅ 품질 메트릭: 시세 수집 성공률
                quality_metrics['price_fetch_rate'] = len(price_map) / max(len(symbols_to_fetch), 1)
            
            # ✅ 재무비율 캐시 (중복 조회 방지)
            financial_cache: Dict[str, Dict] = {}
            
            for stock in candidates:
                try:
                    symbol = stock.get('mksc_shrn_iscd', '')
                    if not symbol or len(symbol) != 6:
                        continue
                    
                    # ✅ v2.3: ETF/ETN/ETP 및 우선주 제외 (강화된 필터)
                    name = stock.get('hts_kor_isnm') or ""
                    if self._is_etp(name):
                        logger.debug(f"⏭️ {symbol} ETF/ETN 제외: {name}")
                        continue
                    if self._is_preferred_stock(symbol, name):
                        logger.debug(f"⏭️ {symbol} 우선주 제외: {name}")
                        continue
                    
                    # ✅ 배치 조회한 시세 데이터 사용 (개별 호출 제거!)
                    current_price_data = price_map.get(symbol)
                    if not current_price_data:
                        logger.info(f"⏭️ {symbol} {name} 시세 데이터 없음 (배치 조회 실패)")
                        continue
                    
                    # ✅ 재무비율 조회 (외부 데이터 재사용 우선!)
                    financial = financial_cache.get(symbol)
                    
                    # ✅ 외부에서 제공된 데이터 확인 (중복 API 호출 방지!)
                    preloaded = stock.get('_preloaded_data')
                    if preloaded and isinstance(preloaded, dict):
                        # ✅ 외부 데이터에 PER, PBR 등이 있으면 재사용 (0도 유효한 값!)
                        if 'per' in preloaded and 'pbr' in preloaded:
                            financial = {
                                'per': str(preloaded.get('per', 0)),
                                'pbr': str(preloaded.get('pbr', 0)),
                                'eps': str(preloaded.get('eps', 0)),
                                'bps': str(preloaded.get('bps', 0)),
                                'roe': str(preloaded.get('roe', 0)),
                                # ✅ v2.1.1: 기타 재무 데이터 (없으면 None - 더미값 150.0 제거)
                                'debt_ratio': str(preloaded.get('debt_ratio')) if preloaded.get('debt_ratio') else None,
                                'current_ratio': str(preloaded.get('current_ratio')) if preloaded.get('current_ratio') else None
                            }
                            financial_cache[symbol] = financial
                            # ✅ 첫 번째 종목만 디버깅 로그
                            if checked_count == 0:
                                logger.info(f"🔍 [DEBUG] {symbol} 외부 데이터 사용: PER={preloaded.get('per')}, PBR={preloaded.get('pbr')}, ROE={preloaded.get('roe')}")
                            else:
                                logger.debug(f"✅ {symbol} 재무비율 외부 데이터 재사용 (API 호출 생략)")
                    
                    # 외부 데이터에 없으면 API로 조회 (최소화)
                    if financial is None and quality_check:
                        # ⚠️ 품질 체크가 켜져 있을 때만 재무비율 API 호출
                        financial = self.get_financial_ratios(symbol)
                        if financial:
                            financial_cache[symbol] = financial
                    elif financial is None:
                        # ✅ v2.1.1: 품질 체크 OFF면 외부 데이터만으로 처리 (더미값 제거)
                        financial = {
                            'per': str(current_price_data.get('per', 0)),
                            'pbr': str(current_price_data.get('pbr', 0)),
                            'roe': str(current_price_data.get('roe', 0)) if current_price_data.get('roe') else None,
                            'debt_ratio': None,  # 데이터 없음 (더미값 150.0 제거)
                            'current_ratio': None,  # 데이터 없음 (더미값 150.0 제거)
                        }
                        # ✅ 디버깅: 외부 데이터 확인
                        if checked_count == 1:
                            logger.info(f"🔍 [DEBUG] {symbol} financial 생성: {financial}")
                    
                    checked_count += 1
                    
                    if not financial:
                        logger.info(f"⏭️ {symbol} {name} financial 데이터 없음")
                        continue
                    
                    # ✅ v2.3: 거래량 단위 변환 (KIS API는 천주 단위)
                    volume_raw = self._to_int(current_price_data.get('acml_vol'))
                    volume = volume_raw * 1000  # 천주 → 주 변환
                    
                    min_vol_threshold = criteria.get('min_volume', 0)
                    if volume < min_vol_threshold:
                        logger.info(f"⏭️ {symbol} {stock_name} 거래량 부족: {volume:,}주 ({volume_raw:,}천주) < {min_vol_threshold:,}주")
                        continue
                    
                    # ✅ NEW: 거래대금 확인 (환경변수 지원 단위 변환)
                    if min_trading_value:
                        # ✅ 단위 안전 변환 (환경변수 KIS_TRADING_VALUE_UNIT)
                        trading_value_원 = self._trading_value_to_won(
                            current_price_data.get('acml_tr_pbmn')
                        )
                        
                        # ✅ 단위 검증 (가격 × 거래량 추정치와 비교)
                        price = self._to_float(current_price_data.get('stck_prpr'))
                        volume = self._to_float(current_price_data.get('acml_vol'))
                        estimated_value = price * volume
                        
                        if estimated_value > 0 and trading_value_원 < estimated_value * 0.01:
                            current_unit = os.environ.get("KIS_TRADING_VALUE_UNIT", "million")
                            logger.warning(
                                f"⚠️ {symbol} 거래대금 단위 의심: "
                                f"API={trading_value_원:,.0f}원 < 추정치={estimated_value:,.0f}원 × 1% | "
                                f"현재 단위={current_unit} → 환경변수 KIS_TRADING_VALUE_UNIT 확인 필요"
                            )
                        
                        if trading_value_원 < min_trading_value:
                            logger.debug(
                                f"⏭️ {symbol} 유동성 부족: "
                                f"거래대금 {trading_value_원:,.0f}원 < {min_trading_value:,.0f}원"
                            )
                            continue
                    
                    # ✅ 종목명 먼저 가져오기 (섹터 폴백에 사용)
                    # ⚠️ 500 오류 방지: API 호출 대신 외부 데이터 또는 기본값 사용
                    stock_name = (
                        current_price_data.get('hts_kor_isnm', '') or 
                        name or 
                        f"종목{symbol}"  # API 호출 없이 바로 기본값 사용
                    )
                    
                    # ✅ 섹터 조회: 외부 데이터 우선, 없으면 마스터파일/종목명 폴백
                    # ⚠️ 500 오류 방지: 외부 데이터에 섹터가 있으면 재조회하지 않음!
                    preloaded = stock.get('_preloaded_data')
                    if preloaded and isinstance(preloaded, dict) and preloaded.get('sector'):
                        # 외부 데이터에 섹터가 있으면 바로 사용 (API 호출 0번!)
                        sector = preloaded.get('sector')
                        logger.debug(f"✅ {symbol} 섹터 외부 데이터 사용: {sector}")
                    else:
                        # 외부 데이터에 섹터가 없으면 조회 (마스터파일 + 종목명 폴백)
                        sector = self._get_sector_for_symbol(symbol, stock_name)
                    
                    # ✨ "보통주" 제거, "우선주"는 "우"로 축약
                    stock_name = stock_name.replace('보통주', '')
                    if '우선주' in stock_name:
                        stock_name = stock_name.replace('우선주', '우')
                    stock_name = stock_name.strip()
                    
                    # ✅ 안전한 숫자 파싱
                    market_cap_억 = self._to_float(current_price_data.get('hts_avls'))
                    price = self._to_float(current_price_data.get('stck_prpr'))
                    
                    # ✅ PER, PBR 우선순위: 외부 데이터 → 계산 (safe_positive 사용)
                    # (0 또는 음수는 자동으로 None 처리)
                    per_raw = self._safe_positive(financial.get('per'))
                    pbr_raw = self._safe_positive(financial.get('pbr'))
                    
                    # ✅ PER/PBR이 없으면 EPS/BPS로 계산 시도
                    if per_raw is None or pbr_raw is None:
                        eps = self._safe_positive(financial.get('eps'))
                        bps = self._safe_positive(financial.get('bps'))
                        
                        if eps and bps and price > 0:
                            per_calc, pbr_calc = self._compute_per_pbr(price, eps, bps)
                            if per_raw is None and per_calc:
                                per_raw = per_calc
                            if pbr_raw is None and pbr_calc:
                                pbr_raw = pbr_calc
                    
                    # ✅ v2.3: 윈저라이즈 (이상치 클램핑) - 하드 탈락 대신 소프트 감점
                    # 결측은 제외하되, 이상치는 클램핑하여 후보 유지
                    if per_raw is None or pbr_raw is None:
                        logger.info(f"⏭️ {symbol} {name} PER/PBR 결측으로 제외 (PER={per_raw}, PBR={pbr_raw})")
                        continue
                    
                    per = self._winsorize(per_raw, 0.01, 100.0)  # PER 100 초과 → 100
                    pbr = self._winsorize(pbr_raw, 0.01, 8.0)    # PBR 8 초과 → 8
                    
                    # ✅ ROE 필드명 양쪽 지원 (음수 허용 - 정책에 따라)
                    roe = self._to_float(financial.get('roe') or financial.get('roe_val'), 0.0)
                    
                    # ✅ 업종별 기준 적용 (ChatGPT 권장 - 업종별 차별화)
                    sector_criteria = self._get_sector_specific_criteria(sector)
                    
                    # ✅ NEW: 품질 체크 (적자, 부채, 유동성)
                    if quality_criteria:
                        # EPS 양수 체크 (적자 기업 제외)
                        eps = self._to_float(financial.get('eps'))
                        if eps < quality_criteria['min_eps']:
                            logger.debug(f"⏭️ {symbol} EPS 음수 제외: EPS={eps:.2f}")
                            continue
                        
                        # 부채비율 체크
                        debt_ratio = self._to_float(financial.get('debt_ratio'))
                        if debt_ratio > quality_criteria['max_debt_ratio']:
                            logger.debug(
                                f"⏭️ {symbol} 부채비율 과다: "
                                f"{debt_ratio:.1f}% > {quality_criteria['max_debt_ratio']}%"
                            )
                            continue
                        
                        # ✅ 유동비율 체크 (단위 정규화 후 배수 기준 비교)
                        current_ratio_raw = self._to_float(financial.get('current_ratio'))
                        current_ratio = self._norm_ratio(current_ratio_raw)  # 배수로 정규화
                        if current_ratio > 0 and current_ratio < quality_criteria['min_current_ratio']:
                            logger.debug(
                                f"⏭️ {symbol} 유동비율 부족: "
                                f"{current_ratio:.2f}배 < {quality_criteria['min_current_ratio']:.2f}배"
                            )
                            continue
                    
                    # ✅ v2.3: 하드 필터 → 소프트 점수 변경
                    # 기준 미달이어도 후보 유지, 점수만 감점
                    sector_fit_score = 0
                    
                    # 업종별 기준 충족도를 점수로 변환 (0~30점)
                    per_fit = min(1.0, sector_criteria['per_max'] / max(per, 0.1))  # 낮을수록 좋음
                    pbr_fit = min(1.0, sector_criteria['pbr_max'] / max(pbr, 0.1))
                    roe_fit = min(1.0, roe / max(sector_criteria['roe_min'], 0.1)) if roe > 0 else 0
                    
                    # 3개 기준 평균 (0~1) → 0~30점
                    sector_fit_score = (per_fit + pbr_fit + roe_fit) / 3.0 * 30
                    
                    # ✅ 3개 기준 모두 충족하면 보너스 +10점
                    meets_all_criteria = (
                        per > 0 and per <= sector_criteria['per_max'] and
                        pbr > 0 and pbr <= sector_criteria['pbr_max'] and
                        roe >= sector_criteria['roe_min']
                    )
                    if meets_all_criteria:
                        sector_fit_score += 10
                    
                    # ✅ v2.3: 모든 종목의 평가 결과를 INFO로 출력 (탈락 추적)
                    logger.info(
                        f"🔍 [{checked_count:3d}] {symbol} {stock_name[:15]:15s} [{sector:10s}]: "
                        f"PER={per:5.1f}(≤{sector_criteria['per_max']:4.1f}), "
                        f"PBR={pbr:4.2f}(≤{sector_criteria['pbr_max']:4.2f}), "
                        f"ROE={roe:5.1f}%(≥{sector_criteria['roe_min']:4.1f}) "
                        f"→ 적합도={sector_fit_score:4.1f}점 {'✅완전충족' if meets_all_criteria else ''}"
                    )
                    
                    # ✅ v2.3: 모든 종목을 후보로 유지 (점수로만 차별화)
                    if True:  # 항상 True - 하드 필터 제거
                        # ✅ NEW: 모멘텀 필터 (극단 하락 제외)
                        if momentum_filter:
                            # 52주 최고가 대비 현재가 위치 (하락폭 체크)
                            high_52w = self._to_float(current_price_data.get('w52_hgpr'))  # 52주 최고가
                            if high_52w > 0:
                                decline_from_high = ((price - high_52w) / high_52w) * 100
                                
                                min_return = momentum_filter.get('min_3m_return', -999)
                                if decline_from_high < min_return:
                                    logger.debug(
                                        f"⏭️ {symbol} 극단 하락 제외: "
                                        f"52주 고가 대비 {decline_from_high:.1f}% < {min_return}%"
                                    )
                                    continue
                        
                        # ✅ 다차원 점수 계산 (MCP 데이터 활용)
                        
                        # 1. 기본 가치 점수 (50%) - PER/PBR/ROE
                        value_score = self._calculate_value_score(per, pbr, roe)
                        
                        # 2. 투자자 동향 점수 (10%) - 외국인/기관 매매
                        investor_score = self._calculate_investor_score(symbol)
                        
                        # 3. 거래 품질 점수 (10%) - 거래대금/회전율
                        trading_score = self._calculate_trading_quality_score(current_price_data)
                        
                        # 4. 기술적 점수 (10%) - 52주 위치/안정성
                        technical_score = self._calculate_technical_score(current_price_data)
                        
                        # 5. 배당 점수 (5%)
                        dividend_score = self._calculate_dividend_score(symbol)
                        
                        # 6. 안정성 점수 (10%) - 신용잔고/변동성
                        stability_score = self._calculate_stability_score(symbol, financial)
                        
                        # ✅ v2.3: 종합 점수 계산 (업종 적합도 반영)
                        # sector_fit_score는 이미 0~40점 범위 (기본 30 + 보너스 10)
                        final_score = (
                            value_score * score_weights.get('value', 0.40) +        # 50% → 40%
                            sector_fit_score * 0.20 +                                # ✅ NEW: 20% (업종 적합도)
                            investor_score * score_weights.get('investor', 0.10) +
                            trading_score * score_weights.get('trading', 0.10) +
                            technical_score * score_weights.get('technical', 0.10) +
                            dividend_score * score_weights.get('dividend', 0.05) +
                            stability_score * score_weights.get('stability', 0.05)   # 10% → 5%
                        )
                        final_score = min(100, final_score)
                        
                        value_stocks.append({
                            'symbol': symbol,
                            'name': stock_name,
                            'price': price,
                            'per': per,
                            'pbr': pbr,
                            'roe': roe,
                            'volume': volume,
                            'change_rate': self._to_float(current_price_data.get('prdy_ctrt')),
                            'score': final_score,
                            'sector': sector,
                            'debt_ratio': self._to_float(financial.get('debt_ratio')),
                            'current_ratio': self._to_float(financial.get('current_ratio')),
                            'market_cap': market_cap_억 * 100_000_000,
                            # ✅ 세부 점수 저장 (분석용)
                            'score_breakdown': {
                                'value': round(value_score, 1),
                                'sector_fit': round(sector_fit_score, 1),  # ✅ v2.3: 업종 적합도
                                'investor': round(investor_score, 1),
                                'trading': round(trading_score, 1),
                                'technical': round(technical_score, 1),
                                'dividend': round(dividend_score, 1),
                                'stability': round(stability_score, 1),
                                'meets_all_criteria': meets_all_criteria  # ✅ v2.3: 완전충족 플래그
                            }
                        })
                        
                        logger.info(
                            f"✅ 가치주 발견: {stock_name} [{sector}] | "
                            f"종합={final_score:.1f} "
                            f"(가치{value_score:.0f} 투자자{investor_score:.0f} "
                            f"거래{trading_score:.0f} 기술{technical_score:.0f})"
                        )
                    
                    # 진행 상황 로깅
                    if checked_count % 20 == 0:
                        logger.debug(f"진행: {checked_count}개 분석, {len(value_stocks)}개 가치주 발굴")
                    
                    # 충분한 종목 발굴 시 종료 (하지만 후보가 충분하면 계속)
                    if len(value_stocks) >= limit and checked_count >= 50:
                        logger.debug(f"목표 달성: {len(value_stocks)}개 발굴 (조기 종료)")
                        break
                        
                except Exception as e:
                    logger.debug(f"종목 {symbol} 분석 실패: {e}")
                    continue
            
            # 점수순 정렬 (1차)
            value_stocks.sort(key=lambda x: x['score'], reverse=True)
            
            # ✅ 품질 메트릭: 섹터 커버리지 (ChatGPT 권장)
            if value_stocks:
                sectors_with_data = [s for s in value_stocks if s.get('sector') and s['sector'] != '기타']
                quality_metrics['total_candidates'] = len(value_stocks)
                quality_metrics['sector_mapped'] = len(sectors_with_data)
                quality_metrics['sector_coverage'] = len(sectors_with_data) / len(value_stocks)
            
            # ✅ NEW: 섹터 내 퍼센타일 랭킹 (섹터 편향 제거 + 소표본 보정)
            if sector_neutral and len(value_stocks) >= 5:
                logger.info("🎯 섹터 내 퍼센타일 랭킹 적용...")
                
                # 섹터별 그룹화
                from collections import defaultdict
                sector_groups = defaultdict(list)
                for stock in value_stocks:
                    sector_groups[stock['sector']].append(stock)
                
                # ✅ 글로벌 퍼센타일 먼저 계산 (소표본 섹터용 폴백)
                all_sorted_per = sorted(value_stocks, key=lambda x: x['per'])
                all_sorted_pbr = sorted(value_stocks, key=lambda x: x['pbr'])
                all_sorted_roe = sorted(value_stocks, key=lambda x: x['roe'], reverse=True)
                
                for i, stock in enumerate(all_sorted_per):
                    stock['global_per_percentile'] = 100.0 * (len(all_sorted_per) - i) / len(all_sorted_per)
                for i, stock in enumerate(all_sorted_pbr):
                    stock['global_pbr_percentile'] = 100.0 * (len(all_sorted_pbr) - i) / len(all_sorted_pbr)
                for i, stock in enumerate(all_sorted_roe):
                    stock['global_roe_percentile'] = 100.0 * (i + 1) / len(all_sorted_roe)
                
                # 섹터 내 PER, PBR, ROE 퍼센타일 계산
                for sector, stocks_in_sector in sector_groups.items():
                    # ✅ 소표본 보정: n이 작을수록 글로벌 비중 증가
                    n = len(stocks_in_sector)
                    use_blending = n < 5
                    
                    # 동적 블렌딩 가중치 (n이 작을수록 글로벌 의존 ↑)
                    if use_blending:
                        # blend_global = min(0.8, 5/(n+1))
                        # n=1: 0.8333 (글로벌 83%)
                        # n=2: 0.8 (글로벌 80%)
                        # n=3: 0.8 (글로벌 80%)
                        # n=4: 0.8 (글로벌 80%)
                        blend_global = min(0.8, 5.0 / (n + 1))
                        blend_sector = 1.0 - blend_global
                    else:
                        blend_sector = 1.0
                        blend_global = 0.0
                    
                    if len(stocks_in_sector) < 2:
                        # 섹터 내 종목이 1개면 글로벌 퍼센타일 100% 사용
                        for stock in stocks_in_sector:
                            stock['per_percentile'] = stock['global_per_percentile']
                            stock['pbr_percentile'] = stock['global_pbr_percentile']
                            stock['roe_percentile'] = stock['global_roe_percentile']
                        logger.debug(f"📊 {sector}: 1개 종목 → 글로벌 퍼센타일 사용")
                        continue
                    
                    # PER 낮을수록 좋음 → 낮은 순위 = 높은 퍼센타일
                    sorted_by_per = sorted(stocks_in_sector, key=lambda x: x['per'])
                    for i, stock in enumerate(sorted_by_per):
                        sector_pct = 100.0 * (len(sorted_by_per) - i) / len(sorted_by_per)
                        
                        # ✅ 동적 블렌딩 (n이 작을수록 글로벌 의존 ↑)
                        stock['per_percentile'] = sector_pct * blend_sector + stock['global_per_percentile'] * blend_global
                    
                    # PBR 낮을수록 좋음
                    sorted_by_pbr = sorted(stocks_in_sector, key=lambda x: x['pbr'])
                    for i, stock in enumerate(sorted_by_pbr):
                        sector_pct = 100.0 * (len(sorted_by_pbr) - i) / len(sorted_by_pbr)
                        stock['pbr_percentile'] = sector_pct * blend_sector + stock['global_pbr_percentile'] * blend_global
                    
                    # ROE 높을수록 좋음 → 높은 순위 = 높은 퍼센타일
                    sorted_by_roe = sorted(stocks_in_sector, key=lambda x: x['roe'], reverse=True)
                    for i, stock in enumerate(sorted_by_roe):
                        sector_pct = 100.0 * (i + 1) / len(sorted_by_roe)
                        stock['roe_percentile'] = sector_pct * blend_sector + stock['global_roe_percentile'] * blend_global
                    
                    # ✅ 블렌딩 사용 시 로그 (동적 가중치 표시)
                    if use_blending:
                        logger.debug(
                            f"📊 {sector}: {n}개 → "
                            f"섹터({blend_sector*100:.0f}%) + 글로벌({blend_global*100:.0f}%) 블렌딩"
                        )
                
                # 섹터 내 종합 점수로 재계산 (기존 점수 40% + 퍼센타일 60%)
                for stock in value_stocks:
                    per_pct = stock.get('per_percentile', 50.0)
                    pbr_pct = stock.get('pbr_percentile', 50.0)
                    roe_pct = stock.get('roe_percentile', 50.0)
                    
                    # 퍼센타일 종합 점수 (PER 40%, PBR 30%, ROE 30%)
                    percentile_score = (per_pct * 0.40 + pbr_pct * 0.30 + roe_pct * 0.30)
                    
                    # 기존 점수와 블렌딩 (기존 40% + 퍼센타일 60%)
                    stock['original_score'] = stock['score']
                    stock['score'] = stock['score'] * 0.40 + percentile_score * 0.60
                
                logger.info(f"✅ 섹터 내 퍼센타일 적용 완료 ({len(sector_groups)}개 섹터)")
            
            # ✅ NEW: 모멘텀 가점 (6개월 수익률, 선형 스케일)
            # ✅ 500 오류 방지: 상위 10개만 적용 (대량 차트 API 호출 방지)
            if momentum_scoring and len(value_stocks) >= 5:
                # ✅ API 부하 방지: 상위 10개만 모멘텀 계산 (30→10 감소)
                momentum_candidates = value_stocks[:min(10, len(value_stocks))]
                logger.info(f"📈 모멘텀 가점 계산 중 (상위 {len(momentum_candidates)}개 종목만, 500 오류 방지)...")
                
                momentum_added = 0
                momentum_failed = []
                
                for idx, stock in enumerate(momentum_candidates):
                    try:
                        symbol = stock['symbol']
                        name = stock.get('name', symbol)
                        
                        # ✅ 500 오류 방지: 호출 간 지연 강화 (ChatGPT 권장)
                        if idx > 0:
                            # 매 호출마다 2초 대기 (차트 API는 무거움)
                            time.sleep(2.0)
                            if idx % 3 == 0:
                                logger.debug(f"⏸️ 차트 API 부하 방지: 2초 간격 ({idx}/{len(momentum_candidates)})")
                        
                        # ✅ 500 오류 방지: 페이지네이션 비활성화 (1페이지만 조회)
                        # 300일 전체 대신 100일만 조회 (API 부하 감소)
                        chart_data = self.get_chart_data(symbol, period='D', days=100, use_pagination=False)
                        
                        if not chart_data:
                            momentum_failed.append((name, "차트 데이터 없음"))
                            continue
                        
                        # ✅ 최소 데이터 체크
                        if len(chart_data) < 60:
                            momentum_failed.append((name, f"데이터 부족 ({len(chart_data)}일)"))
                            continue
                        
                        # ✅ 역순 정렬 (최신이 마지막)
                        chart_data = sorted(chart_data, key=lambda x: x.get('stck_bsop_date', ''), reverse=False)
                        
                        # ✅ 어댑티브 모멘텀 창 (ChatGPT 권장)
                        N = len(chart_data)
                        
                        # ✅ 모멘텀 설정 상수 사용 (일관성)
                        target_lookback = self.MOM_LOOKBACK_D
                        
                        if N >= target_lookback:
                            lookback = target_lookback
                            period_label = f"{int(target_lookback/20)}M"  # 60D→3M, 100D→5M
                            max_bonus = 20.0 if target_lookback >= 100 else 10.0
                        elif N >= 60:  # 최소 3개월
                            lookback = min(N - 1, 60)
                            period_label = "3M"
                            max_bonus = 10.0  # ✅ 짧은 기간은 가점 축소
                        else:
                            momentum_failed.append((name, f"데이터 부족 ({N}일)"))
                            continue
                        
                        # 실제 사용된 데이터 길이
                        actual_days = lookback
                        
                        price_past = self._to_float(chart_data[-lookback].get('stck_clpr'))
                        price_now = self._to_float(chart_data[-1].get('stck_clpr'))
                        
                        if not price_past or price_past <= 0:
                            momentum_failed.append((name, f"{period_label} 전 가격 없음"))
                            continue
                        
                        if not price_now or price_now <= 0:
                            momentum_failed.append((name, "현재 가격 없음"))
                            continue
                        
                        ret_pct = ((price_now - price_past) / price_past) * 100.0
                        
                        # ✅ 어댑티브 스케일 (기간에 따라 조정)
                        if period_label == "6M":
                            # -30% ~ +50% → -10점 ~ +20점
                            if ret_pct >= 50:
                                bump = max_bonus
                            elif ret_pct <= -30:
                                bump = -10.0
                            else:
                                bump = -10.0 + (ret_pct + 30.0) * 0.375
                        else:  # 3M
                            # -20% ~ +30% → -5점 ~ +10점
                            if ret_pct >= 30:
                                bump = max_bonus
                            elif ret_pct <= -20:
                                bump = -5.0
                            else:
                                bump = -5.0 + (ret_pct + 20.0) * 0.30
                        
                        stock['score'] = self._clamp_score(stock['score'] + bump)
                        stock[f'momentum_{period_label.lower()}'] = ret_pct
                        stock['momentum_period'] = f"{period_label}({actual_days}D)"  # ✅ 실제 길이 명시
                        
                        if 'score_breakdown' not in stock:
                            stock['score_breakdown'] = {}
                        stock['score_breakdown']['momentum_bonus'] = round(bump, 1)
                        momentum_added += 1
                        
                        # ✅ 라벨 정합 (실제 데이터 길이 명시) - DEBUG 레벨
                        logger.debug(
                            f"📈 {name}: {period_label} 수익률 {ret_pct:+.1f}% → 모멘텀 {bump:+.1f}점 "
                            f"(실제 {actual_days}D/{N}D)"
                        )
                        
                    except Exception as e:
                        momentum_failed.append((stock.get('name', stock.get('symbol', '?')), str(e)))
                        logger.debug(f"모멘텀 계산 실패 ({stock.get('name', '?')}): {e}")
                        continue
                
                # ✅ 모멘텀 요약 정보 (ChatGPT 권장)
                success_rate = momentum_added / len(momentum_candidates) * 100 if momentum_candidates else 0
                logger.info(
                    f"✅ 모멘텀 가점 완료: {momentum_added}/{len(momentum_candidates)}개 "
                    f"(성공률 {success_rate:.0f}%, 전체 {len(value_stocks)}개 중 상위만 계산)"
                )
                
                # ✅ 품질 메트릭: 모멘텀 성공률 (전체 대비 비율)
                # 상위 10개만 계산하므로, 전체 대비 성공한 비율로 표시
                quality_metrics['momentum_success'] = success_rate / 100.0
                quality_metrics['momentum_enabled'] = True
                
                # ✅ 실패 원인 요약 (상세 로깅)
                if momentum_failed:
                    logger.warning(f"⚠️ 모멘텀 계산 실패: {len(momentum_failed)}개")
                    for name, reason in momentum_failed[:3]:  # ✅ 3개까지
                        logger.debug(f"  ⚠️ {name}: {reason}")
            else:
                # ✅ 모멘텀 비활성화 시 메트릭 설정
                if not momentum_scoring:
                    quality_metrics['momentum_enabled'] = False
                    quality_metrics['momentum_success'] = 0.0
            
            # ✅ NEW: 지주회사·정책·사이클 리스크 제외 (ChatGPT 보수 필터)
            excluded_stocks = []
            filtered_stocks = []
            
            for stock in value_stocks:
                sector = stock.get('sector', '')
                name = stock.get('name', '')
                symbol = stock.get('symbol', '')
                should_exclude = False
                exclude_reason = ""
                
                # 1. 지주회사·투자회사 제외 (SOTP 필요)
                if exclude_holdings and ('지주회사' in sector or '스퀘어' in name):
                    should_exclude = True
                    exclude_reason = "지주/투자회사 (SOTP 평가 필요)"
                
                # 2. 정책 민감 기업 제외 (공기업 등) - ✅ elif 제거 (독립 체크)
                if not should_exclude and exclude_policy_risk:
                    if any(keyword in name for keyword in ['한국전력', '한국가스공사', '한국수력원자력']):
                        should_exclude = True
                        exclude_reason = "정책 민감 (요금·규제 리스크)"
                
                # 3. 사이클 민감 기업 제외 (항공·해운) - ✅ elif 제거 (독립 체크)
                if not should_exclude and exclude_policy_risk:
                    if any(keyword in name for keyword in ['항공', '에이치엠엠', 'HMM', '해운']):
                        should_exclude = True
                        exclude_reason = "사이클 민감 (운임·유가 리스크)"
                
                if should_exclude:
                    excluded_stocks.append((name, exclude_reason))
                    logger.debug(f"🚫 제외: {name} [{sector}] - {exclude_reason}")
                else:
                    filtered_stocks.append(stock)
            
            if excluded_stocks:
                logger.info(f"🚫 리스크 제외: {len(excluded_stocks)}개 종목 (지주·정책·사이클)")
                for name, reason in excluded_stocks:  # ✅ 전체 로그 (중요!)
                    logger.info(f"  🚫 {name}: {reason}")
            
            value_stocks = filtered_stocks
            
            # 재정렬 (퍼센타일 + 모멘텀 + 리스크 조정 반영)
            value_stocks.sort(key=lambda x: x['score'], reverse=True)
            
            # ✅ 섹터 다양성 확보: 파라미터화된 섹터 비중 제한
            if len(value_stocks) >= 5:  # ✅ 5개 이상이면 다양성 적용
                diversified_stocks = []
                sector_count = {}
                target_limit = min(limit, len(value_stocks))  # 실제 발견된 수와 목표 중 작은 값
                
                # ✅ 목표 개수 명시적 로깅 (사용자 혼란 방지)
                logger.info(f"📊 섹터 다양성 목표: {len(value_stocks)}개 가치주 → 최대 {target_limit}개 선정 (섹터캡/비중상한 적용)")
                
                # ✅ 섹터별 최대치 계산 함수 (파라미터화)
                def get_sector_cap(sector: str, target: int) -> int:
                    """파라미터화된 섹터 비중 제한 적용"""
                    normalized = self._normalize_sector(sector)
                    
                    # 섹터 키워드 매칭
                    for sector_keyword, cap_ratio in sector_caps.items():
                        if sector_keyword in normalized:
                            return max(1, int(target * cap_ratio))
                    
                    # 기타 섹터 (기본값)
                    default_cap = sector_caps.get('기타', 0.50)
                    return max(1, int(target * default_cap))
                
                logger.info(
                    f"📊 섹터 다양성 적용: {sector_caps}, 목표: {target_limit}개"
                )
                
                # 2-pass 방식: 먼저 제한 내에서 채우고, 부족하면 추가
                pass1_stocks = []
                pass1_count = {}
                
                # Pass 1: 섹터 최대치 엄수 (✅ 섹터별 차등 적용)
                for stock in value_stocks:
                    sector = stock['sector']
                    if sector not in pass1_count:
                        pass1_count[sector] = 0
                    
                    # ✅ 섹터별 최대치 적용 (금융 30%, 기타 50%)
                    sector_cap = get_sector_cap(sector, target_limit)
                    
                    if pass1_count[sector] < sector_cap:
                        pass1_stocks.append(stock)
                        pass1_count[sector] += 1
                
                diversified_stocks = pass1_stocks
                sector_count = pass1_count.copy()
                
                # Pass 2: 목표 미달이면 남은 종목 추가 (✅ 최대치 미달 섹터 우선)
                if len(diversified_stocks) < target_limit:
                    remaining_stocks = [s for s in value_stocks if s not in diversified_stocks]
                    
                    # ✅ 최대치에 도달한 섹터 제외하고 추가
                    added = 0
                    for stock in remaining_stocks:
                        if len(diversified_stocks) >= target_limit:
                            break
                        
                        sector = stock['sector']
                        current_count = sector_count.get(sector, 0)
                        sector_cap = get_sector_cap(sector, target_limit)  # ✅ 섹터별 최대치
                        
                        # 섹터 최대치 미달인 경우만 추가
                        if current_count < sector_cap:
                            diversified_stocks.append(stock)
                            sector_count[sector] = current_count + 1
                            added += 1
                            logger.debug(f"📊 Pass 2: {stock['name']} [{sector}] 추가 ({current_count+1}/{sector_cap})")
                    
                    if added > 0:
                        logger.debug(f"📊 Pass 2: {added}개 추가 (섹터별 최대치 준수)")
                    else:
                        logger.warning(f"⚠️ Pass 2: 추가 불가 (모든 섹터가 최대치 도달)")
                
                # 섹터 분포 로깅
                logger.debug(f"📊 최종 섹터 분포: {dict(sector_count)}")
                value_stocks = diversified_stocks
            
            # ✅ 개별 종목 최대 비중 제한 (워터필링 방식, ChatGPT 권장)
            final_pick = value_stocks[:limit]
            
            if final_pick and max_position_weight < 1.0:
                # 초기 균등 비중
                n = len(final_pick)
                weights = [1.0 / n] * n
                
                # ✅ 워터필링: 캡핑 + 잔여 재분배 반복 (ChatGPT 권장)
                max_iterations = 10
                for iteration in range(max_iterations):
                    # 1. 캡핑
                    capped = [min(w, max_position_weight) for w in weights]
                    
                    # 2. 잔여 비중 계산
                    leftover = 1.0 - sum(capped)
                    
                    if leftover < 1e-9:  # 잔여가 없으면 종료
                        weights = capped
                        break
                    
                    # 3. 수용 가능한 종목에게 재분배
                    capacity_idx = [i for i, w in enumerate(capped) if w < max_position_weight]
                    
                    if not capacity_idx:  # 모두 캡에 도달하면 종료
                        weights = capped
                        logger.warning(
                            f"⚠️ 모든 종목이 {max_position_weight*100:.0f}% 상한 도달 "
                            f"(총 비중 {sum(capped)*100:.1f}%)"
                        )
                        break
                    
                    # 4. 균등 분배 (수용 가능한 종목들에게)
                    add_each = leftover / len(capacity_idx)
                    grew = 0.0
                    for i in capacity_idx:
                        room = max_position_weight - capped[i]
                        delta = min(add_each, room)
                        capped[i] += delta
                        grew += delta
                    
                    weights = capped
                    
                    if grew < 1e-10:  # 더 이상 분배 불가
                        break
                
                # 비중 기록
                for i, stock in enumerate(final_pick):
                    stock['proposed_weight'] = round(weights[i], 4)
                
                capped_count = len([w for w in weights if w >= max_position_weight - 1e-6])
                total_weight = sum(weights)
                
                # ✅ 데이터 품질 스코어 계산 (ChatGPT 권장)
                sector_cov = quality_metrics.get('sector_coverage', 0.0)
                momentum_suc = quality_metrics.get('momentum_success', 0.0)
                price_fetch = quality_metrics.get('price_fetch_rate', 0.0)
                
                data_quality = 0.4 * sector_cov + 0.4 * momentum_suc + 0.2 * price_fetch
                
                # ✅ 품질 기반 권장 현금 비중 (ChatGPT 권장)
                if data_quality < 0.75:
                    recommended_cash = 0.20
                elif data_quality < 0.90:
                    recommended_cash = 0.10
                else:
                    recommended_cash = 0.00
                
                # ✅ 총 비중 정책 로깅 (ChatGPT 권장)
                if total_weight < 0.95:  # 95% 미만
                    cash_pct = (1.0 - total_weight) * 100
                    logger.info(
                        f"📊 비중 계산 완료: {capped_count}/{n}개 종목 캡핑 "
                        f"(주식 {total_weight*100:.1f}%, 현금 {cash_pct:.1f}%)"
                    )
                    logger.info(
                        f"📊 데이터 품질 스코어: {data_quality:.2f} "
                        f"(섹터 {sector_cov:.2f}, 모멘텀 {momentum_suc:.2f}, 시세 {price_fetch:.2f})"
                    )
                    
                    # ✅ 현금 보유 권장은 실제로 필요할 때만 (ChatGPT 권장)
                    if recommended_cash > 0:
                        logger.info(
                            f"💡 현금 보유: 데이터 품질 회복 전까지 방어적 현금 {recommended_cash*100:.1f}% 보유 권장 "
                            f"(현재 {cash_pct:.1f}%)"
                        )
                    else:
                        logger.info(f"✅ 데이터 품질 양호: 현금 비중은 포트폴리오 정책에 따름")
                else:
                    logger.debug(
                        f"📊 비중 계산 완료: {capped_count}/{n}개 종목 캡핑 "
                        f"(총 비중 {total_weight*100:.1f}%)"
                    )
            else:
                # 균등 비중 (기본값)
                for stock in final_pick:
                    stock['proposed_weight'] = round(1.0 / len(final_pick), 4) if final_pick else 0.0
            
            # ✅ 최종 요약 로그
            filtered_counts = {
                '후보군': len(candidates),
                '분석': checked_count,
                '가치주': len(value_stocks),
                '최종': min(len(value_stocks), limit)
            }
            
            filter_summary = []
            if min_trading_value:
                filter_summary.append(f"거래대금≥{min_trading_value/1e8:.0f}억")
            if quality_check:
                filter_summary.append("품질체크")
            if momentum_filter:
                filter_summary.append("모멘텀필터")
            if sector_neutral:
                filter_summary.append("섹터중립")
            if momentum_scoring:
                filter_summary.append("모멘텀가점")
            
            logger.info(
                f"✅ 가치주 발굴 완료: {filtered_counts['최종']}개 선정 | "
                f"경로: {filtered_counts['후보군']}→{filtered_counts['분석']}→{filtered_counts['가치주']}→{filtered_counts['최종']} | "
                f"필터: {', '.join(filter_summary) if filter_summary else '기본'} | "
                f"개별비중상한: {max_position_weight*100:.0f}%"
            )
            
            # ✅ 품질 지표 요약 (ChatGPT 권장 + 모멘텀 활성화 상태 표시)
            sector_cov = quality_metrics.get('sector_coverage', 0.0)
            momentum_suc = quality_metrics.get('momentum_success', 0.0)
            momentum_enabled = quality_metrics.get('momentum_enabled', False)
            price_fetch = quality_metrics.get('price_fetch_rate', 0.0)
            total_cands = quality_metrics.get('total_candidates', 0)
            sector_mapped = quality_metrics.get('sector_mapped', 0)
            
            # 모멘텀 상태 표시
            if momentum_enabled:
                momentum_label = f"모멘텀성공 {momentum_suc*100:.0f}%"
            else:
                momentum_label = "모멘텀 비활성화"
            
            logger.info(
                f"📊 품질 지표: "
                f"섹터커버리지 {sector_cov*100:.1f}% ({sector_mapped}/{total_cands}) | "
                f"{momentum_label} | "
                f"시세수집 {price_fetch*100:.0f}%"
            )
            
            # ✅ 최종 선정 종목 명시적 출력
            if final_pick:
                logger.info("=" * 80)
                logger.info(f"📋 최종 선정 종목 ({len(final_pick)}개):")
                logger.info("=" * 80)
                
                # 섹터별 분류
                sector_summary = {}
                for stock in final_pick:
                    sector = stock.get('sector', '기타')
                    if sector not in sector_summary:
                        sector_summary[sector] = []
                    sector_summary[sector].append(stock)
                
                # 섹터별 출력
                for idx, stock in enumerate(final_pick, 1):
                    weight = stock.get('proposed_weight', 0) * 100
                    score = stock.get('score', 0)
                    sector = stock.get('sector', '기타')
                    name = stock.get('name', '?')
                    symbol = stock.get('symbol', '?')
                    risk_note = stock.get('risk_note', '')
                    momentum_period = stock.get('momentum_period', '')
                    
                    risk_tag = f" ⚠️{risk_note}" if risk_note else ""
                    momentum_tag = f" [{momentum_period}]" if momentum_period else ""
                    
                    logger.info(
                        f"{idx:2d}. {name:12s} [{sector:8s}] "
                        f"점수={score:5.1f} 비중={weight:5.1f}%{momentum_tag}{risk_tag}"
                    )
                
                # 섹터 분포 요약
                logger.info("=" * 80)
                logger.info("📊 섹터 분포:")
                for sector, stocks in sorted(sector_summary.items(), key=lambda x: -len(x[1])):
                    count = len(stocks)
                    pct = (count / len(final_pick)) * 100
                    logger.info(f"  {sector:12s}: {count:2d}개 ({pct:5.1f}%)")
                logger.info("=" * 80)
                
                # ✅ 포트폴리오 메타 정보 (ChatGPT 권장)
                total_stock_weight = sum(s.get('proposed_weight', 0) for s in final_pick)
                cash_weight = 1.0 - total_stock_weight
                
                # ✅ 실제 모멘텀 기간 집계 (ChatGPT 권장)
                momentum_enabled = quality_metrics.get('momentum_enabled', False)
                if momentum_enabled:
                    momentum_periods = [s.get('momentum_period', '') for s in final_pick if s.get('momentum_period')]
                    if momentum_periods:
                        # 가장 많이 사용된 기간
                        from collections import Counter
                        period_count = Counter(momentum_periods)
                        most_common = period_count.most_common(1)[0][0] if period_count else f'{self.MOM_LABEL}'
                    else:
                        most_common = f'{self.MOM_LABEL} (계산 실패)'
                else:
                    most_common = '비활성화'
                
                logger.info("💼 포트폴리오 요약:")
                logger.info(f"  📈 주식 비중: {total_stock_weight*100:5.1f}%")
                logger.info(f"  💵 현금 비중: {cash_weight*100:5.1f}%")
                logger.info(f"  📊 섹터 수: {len(sector_summary)}개")
                logger.info(f"  🎯 리밸런스 주기: 월 1회 권장")
                logger.info(f"  📊 모멘텀 기준: {most_common}")
                logger.info("=" * 80)
            
            return final_pick
            
        except Exception as e:
            logger.error(f"가치주 발굴 실패: {e}")
            return None
    
    def _clamp_score(self, x: float, lo: float = 0.0, hi: float = 100.0) -> float:
        """
        점수를 범위 내로 클램핑 (NaN 방어 포함)
        
        Args:
            x: 원본 점수
            lo: 최소값 (기본 0.0)
            hi: 최대값 (기본 100.0)
            
        Returns:
            [lo, hi] 범위로 클램핑된 점수
        """
        try:
            if x != x:  # NaN 체크
                return lo
            return max(lo, min(hi, float(x)))
        except Exception:
            return lo
    
    def _clamp01(self, x: float) -> float:
        """
        0~1 범위로 클램핑 (NaN 방어)
        
        Args:
            x: 원본 값
            
        Returns:
            [0.0, 1.0] 범위로 클램핑된 값
        """
        try:
            if x != x:  # NaN 체크
                return 0.0
            return max(0.0, min(1.0, float(x)))
        except Exception:
            return 0.0
    
    def _calculate_value_score(self, per: float, pbr: float, roe: float) -> float:
        """
        가치주 기본 점수 (PER/PBR/ROE)
        
        ✅ 개선: 선형 스케일로 부드러운 점수 분포 (구간별 → 연속)
        - PER: 0~30 구간에서 선형 (낮을수록 좋음)
        - PBR: 0~3 구간에서 선형 (낮을수록 좋음)
        - ROE: 0~20% 구간에서 선형 (높을수록 좋음)
        """
        try:
            # PER 정규화 (0~30 범위, 30 초과는 30으로 클램프)
            s_per = self._clamp01((30.0 - min(per, 30.0)) / 30.0)
            
            # PBR 정규화 (0~3 범위, 3 초과는 3으로 클램프)
            s_pbr = self._clamp01((3.0 - min(pbr, 3.0)) / 3.0)
            
            # ROE 정규화 (0~20% 범위, 음수는 0, 20 초과는 20으로 클램프)
            s_roe = self._clamp01(min(max(roe, 0.0), 20.0) / 20.0)
            
            # 가중 평균 (PER 40%, PBR 30%, ROE 30%)
            return 100.0 * (0.4 * s_per + 0.3 * s_pbr + 0.3 * s_roe)
        except:
            return 50.0
    
    def _calculate_investor_score(self, symbol: str) -> float:
        """
        투자자 동향 점수 (⚠️ 500 오류 방지: API 호출 제거)
        
        Note:
            투자자 동향은 10% 가중치
            → 대량 종목 처리 시 API 호출하면 AppKey 차단 위험
            → 기본 점수 50점 반환 (중립)
            → 정확한 투자자 동향이 필요하면 외부 데이터에서 미리 제공
        """
        # ⚠️ 500 오류 방지: get_investor_trend() 호출 완전 제거
        # 대량 종목 처리 시 이 함수가 300번 호출되면 AppKey 차단됨
        return 50.0  # 중립 점수 (투자자 가중치는 10%로 영향 제한적)
    
    def _calculate_trading_quality_score(self, current_price_data: Dict) -> float:
        """
        거래 품질 점수 (거래대금, 회전율 proxy)
        
        ✅ 개선: 유동성 비율 기반 선형 스케일 (0~5% 구간)
        """
        try:
            if not current_price_data:
                return 50.0
            
            vol = self._to_float(current_price_data.get('acml_vol'))
            mcap_억 = self._to_float(current_price_data.get('hts_avls'))  # 억원
            price = self._to_float(current_price_data.get('stck_prpr'))
            
            if vol <= 0 or price <= 0 or mcap_억 <= 0:
                return 50.0
            
            # 러프한 유동성 지표: (거래대금 / 시총)
            trading_value = price * vol
            mcap = mcap_억 * 100_000_000
            liq_ratio = trading_value / max(1.0, mcap)
            
            # 0~5% 구간에서 선형 점수화 (5% 이상은 100점)
            s = self._clamp01(min(liq_ratio, 0.05) / 0.05)
            return 100.0 * s
        except Exception:
            return 50.0
    
    def _calculate_technical_score(self, current_price_data: Dict) -> float:
        """
        기술적 점수 (52주 고점·저점 대비 위치)
        
        ✅ 개선: 단순 선형 스케일 (저점=0점, 고점=100점 근처)
        """
        try:
            price = self._to_float(current_price_data.get('stck_prpr'))
            high = self._to_float(current_price_data.get('w52_hgpr'))
            low = self._to_float(current_price_data.get('w52_lwpr'))
            
            if high <= 0 or low <= 0 or price <= 0 or high <= low:
                return 50.0
            
            # 0(저점)=30점, 1(고점)=80점 사이로 선형 매핑
            pos = (price - low) / (high - low)
            base = 30 + pos * 50  # 30~80 사이
            return self._clamp_score(base)
        except Exception:
            return 50.0
    
    def _calculate_dividend_score(self, symbol: str) -> float:
        """
        배당률 기반 점수 (⚠️ 500 오류 방지: API 호출 제거)
        
        Note:
            배당률은 5% 가중치밖에 안 되므로 API 호출 비용 대비 효과 낮음
            → 기본 점수 50점 반환 (중립)
            → 정확한 배당률이 필요하면 외부 데이터에서 미리 제공해야 함
        """
        # ⚠️ 500 오류 방지: get_stock_basic_info() 호출 완전 제거
        # 대량 종목 처리 시 이 함수가 300번 호출되면 AppKey 차단됨
        return 50.0  # 중립 점수 (배당 가중치는 5%로 영향 미미)
    
    def _hydrate_current_prices(self, symbols: List[str], market_type: str = "J", use_batch: bool = False) -> Dict[str, Dict]:
        """
        배치로 현재가 정보 조회 (개별 조회 우선)
        
        Args:
            symbols: 종목 코드 리스트
            market_type: 시장 구분
            use_batch: 멀티시세 API 사용 여부 (기본: False, 404 오류 회피)
            
        Returns:
            {종목코드: 시세데이터} 딕셔너리
            
        Note:
            ⚠️ 멀티시세 API(inquire-multiple-price)는 404 오류 발생
            → 기본적으로 개별 조회(inquire-price) 사용
            → use_batch=True 시 멀티시세 시도 후 개별 조회 폴백
            
        Example:
            price_map = mcp._hydrate_current_prices(['005930', '000660', ...])
            data = price_map.get('005930')  # O(1) 조회
        """
        try:
            if not symbols:
                return {}
            
            # ✅ 중복 제거 + 유효성 체크
            symbols = [s for s in {str(s).zfill(6) for s in symbols} if s.isdigit() and len(s) == 6]
            
            # ✅ 멀티시세 API 스킵 (404 오류 회피)
            multi_prices = None
            if use_batch:
                logger.debug("📦 멀티시세 API 시도 중...")
                multi_prices = self.get_multiple_current_price(symbols, market_type)
            else:
                logger.debug(f"📦 개별 조회 모드로 {len(symbols)}개 종목 처리")
            
            # ✅ 멀티시세 미사용 또는 실패 시 개별 조회
            if not multi_prices:
                if not use_batch:
                    logger.info(f"📦 개별 조회로 {len(symbols)}개 종목 시세 수집 시작")
                else:
                    logger.warning(f"⚠️ 멀티시세 API 실패, 개별 조회로 폴백: {len(symbols)}개")
                price_map = {}
                
                for i, symbol in enumerate(symbols):
                    try:
                        # 레이트 리밋 준수
                        if i > 0 and i % 10 == 0:
                            logger.debug(f"📦 개별 조회 진행: {i}/{len(symbols)}")
                        
                        cur = self.get_current_price(symbol, market_type)
                        if cur:
                            price_map[symbol] = cur
                    except Exception as e:
                        logger.debug(f"개별 조회 실패 {symbol}: {e}")
                        continue
                
                logger.info(f"✅ 개별 조회 완료: {len(price_map)}/{len(symbols)}개")
                return price_map
            
            # 멀티시세 성공 시 인덱싱
            price_map = {}
            for row in multi_prices:
                code = (
                    row.get('mksc_shrn_iscd') or
                    row.get('stck_shrn_iscd') or
                    row.get('stock_code') or
                    row.get('srtn_cd') or
                    row.get('stk_shrn_cd')
                )
                if code:
                    code = str(code).zfill(6)
                    price_map[code] = row
            
            logger.debug(f"✅ 배치 시세 조회 완료: {len(price_map)}/{len(symbols)}개")
            return price_map
            
        except Exception as e:
            logger.warning(f"배치 시세 조회 실패: {e}")
            return {}
    
    def _calculate_stability_score(self, symbol: str, financial: Dict) -> float:
        """
        안정성 점수 (부채비율↓, 유동비율↑)
        
        ✅ 개선: 단위 정규화 + 선형 스케일
        - 부채: 0~300% 범위에서 선형 (낮을수록 좋음)
        - 유동: 배수 정규화 후 0.5~2.5 범위 (높을수록 좋음)
        
        Note:
            신용잔고 체크 제거 (404 오류 회피)
        """
        try:
            debt = self._to_float((financial or {}).get('debt_ratio'))  # %
            
            # ✅ 유동비율 단위 정규화 (퍼센트 → 배수)
            curr_raw = self._to_float((financial or {}).get('current_ratio'))
            curr = self._norm_ratio(curr_raw)  # 배수 (예: 120% → 1.2)
            
            # 부채 0~300% 범위 (300 초과는 300으로 클램프)
            debt_s = 1.0 - self._clamp01(min(debt, 300.0) / 300.0)
            
            # ✅ 유동비율 0.5~2.5 배수 범위 (0.5 미만은 0.5, 2.5 초과는 2.5)
            curr_s = self._clamp01((min(max(curr, 0.5), 2.5) - 0.5) / 2.0)
            
            # ✅ 신용잔고 체크 제거 (404 오류 회피)
            # 가중 평균 (부채 60%, 유동 40%)
            return 100.0 * (0.6 * debt_s + 0.4 * curr_s)
        except Exception:
            return 50.0
    
    def export_portfolio_to_excel(
        self,
        stocks: List[Dict],
        filename: str = None,
        strategy_name: str = "가치주 포트폴리오"
    ) -> Optional[str]:
        """
        포트폴리오를 엑셀로 내보내기 (실전 기록용)
        
        Args:
            stocks: find_real_value_stocks() 결과
            filename: 저장할 파일명 (기본: portfolio_YYYYMMDD_HHMMSS.xlsx)
            strategy_name: 전략 이름
            
        Returns:
            저장된 파일 경로
            
        Example:
            stocks = mcp.find_real_value_stocks(limit=30)
            filepath = mcp.export_portfolio_to_excel(stocks, strategy_name="보수형 가치주")
        """
        try:
            import pandas as pd
            from datetime import datetime
            
            if not stocks:
                logger.warning("내보낼 종목이 없습니다")
                return None
            
            # 기본 파일명 생성
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"portfolio_{timestamp}.xlsx"
            
            # DataFrame 생성
            df_data = []
            for i, stock in enumerate(stocks, 1):
                row = {
                    '순위': i,
                    '종목코드': stock['symbol'],
                    '종목명': stock['name'],
                    '섹터': stock['sector'],
                    '현재가': f"{stock['price']:,.0f}",
                    'PER': f"{stock['per']:.2f}",
                    'PBR': f"{stock['pbr']:.2f}",
                    'ROE': f"{stock['roe']:.1f}%",
                    '거래량': f"{stock['volume']:,.0f}",
                    '전일대비': f"{stock.get('change_rate', 0):+.2f}%",
                    '종합점수': f"{stock['score']:.1f}",
                    '시가총액': f"{stock['market_cap']/1e8:.0f}억",
                    '부채비율': f"{stock.get('debt_ratio', 0):.1f}%",
                    '유동비율': f"{stock.get('current_ratio', 0):.1f}%",
                }
                
                # 추가 정보 (있는 경우)
                if 'momentum_6m' in stock:
                    row['6M수익률'] = f"{stock['momentum_6m']:+.1f}%"
                if 'position_weight' in stock:
                    row['권장비중'] = f"{stock['position_weight']*100:.1f}%"
                if 'per_percentile' in stock:
                    row['섹터내PER순위'] = f"{stock['per_percentile']:.0f}%"
                
                # ✅ 세부 점수 (다차원 분석)
                if 'score_breakdown' in stock:
                    breakdown = stock['score_breakdown']
                    row['가치점수'] = f"{breakdown.get('value', 0):.1f}"
                    row['투자자점수'] = f"{breakdown.get('investor', 0):.1f}"
                    row['거래품질'] = f"{breakdown.get('trading', 0):.1f}"
                    row['기술점수'] = f"{breakdown.get('technical', 0):.1f}"
                    row['배당점수'] = f"{breakdown.get('dividend', 0):.1f}"
                    row['안정성'] = f"{breakdown.get('stability', 0):.1f}"
                
                df_data.append(row)
            
            df = pd.DataFrame(df_data)
            
            # 엑셀 저장 (여러 시트)
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # 시트 1: 종목 리스트
                df.to_excel(writer, sheet_name='종목리스트', index=False)
                
                # 시트 2: 요약 정보
                summary_data = {
                    '항목': [
                        '전략명',
                        '생성일시',
                        '총 종목수',
                        '평균 PER',
                        '평균 PBR',
                        '평균 ROE',
                        '총 시가총액',
                        '섹터 수'
                    ],
                    '값': [
                        strategy_name,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        len(stocks),
                        f"{sum(s['per'] for s in stocks) / len(stocks):.2f}",
                        f"{sum(s['pbr'] for s in stocks) / len(stocks):.2f}",
                        f"{sum(s['roe'] for s in stocks) / len(stocks):.1f}%",
                        f"{sum(s['market_cap'] for s in stocks)/1e12:.2f}조원",
                        len(set(s['sector'] for s in stocks))
                    ]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='요약', index=False)
                
                # 시트 3: 섹터 분포
                sector_dist = {}
                for stock in stocks:
                    sector = stock['sector']
                    sector_dist[sector] = sector_dist.get(sector, 0) + 1
                
                sector_df = pd.DataFrame([
                    {'섹터': k, '종목수': v, '비중': f"{v/len(stocks)*100:.1f}%"}
                    for k, v in sorted(sector_dist.items(), key=lambda x: x[1], reverse=True)
                ])
                sector_df.to_excel(writer, sheet_name='섹터분포', index=False)
            
            logger.info(f"✅ 포트폴리오 엑셀 저장 완료: {filename}")
            return filename
            
        except ImportError:
            logger.error("pandas 또는 openpyxl이 설치되지 않았습니다")
            return None
        except Exception as e:
            logger.error(f"엑셀 내보내기 실패: {e}")
            return None
    
    def calculate_portfolio_metrics(
        self,
        stocks: List[Dict],
        benchmark_return: float = 0.0
    ) -> Optional[Dict]:
        """
        포트폴리오 메트릭 계산 (모니터링용)
        
        Args:
            stocks: 포트폴리오 종목 리스트
            benchmark_return: 벤치마크 수익률 (%)
            
        Returns:
            메트릭 딕셔너리
            {
                'total_stocks': 종목수,
                'avg_per': 평균 PER,
                'avg_pbr': 평균 PBR,
                'avg_roe': 평균 ROE,
                'avg_score': 평균 점수,
                'total_market_cap': 총 시가총액,
                'sector_count': 섹터 수,
                'sector_distribution': 섹터별 비중,
                'quality_score': 품질 점수 (0-100),
                'concentration_risk': 집중도 리스크 (0-100, 낮을수록 좋음)
            }
            
        Example:
            metrics = mcp.calculate_portfolio_metrics(stocks)
            print(f"평균 PER: {metrics['avg_per']:.2f}")
        """
        try:
            if not stocks or len(stocks) == 0:
                return None
            
            # 기본 통계
            total_stocks = len(stocks)
            avg_per = sum(s['per'] for s in stocks) / total_stocks
            avg_pbr = sum(s['pbr'] for s in stocks) / total_stocks
            avg_roe = sum(s['roe'] for s in stocks) / total_stocks
            avg_score = sum(s['score'] for s in stocks) / total_stocks
            total_market_cap = sum(s['market_cap'] for s in stocks)
            
            # 섹터 분포
            sector_dist = {}
            for stock in stocks:
                sector = stock['sector']
                market_cap = stock['market_cap']
                sector_dist[sector] = sector_dist.get(sector, 0) + market_cap
            
            sector_distribution = {
                k: v / total_market_cap * 100
                for k, v in sector_dist.items()
            }
            
            # 품질 점수 (ROE, 부채비율, 유동비율 기반)
            quality_scores = []
            for stock in stocks:
                score = 0
                # ROE 가점
                if stock['roe'] >= 15:
                    score += 40
                elif stock['roe'] >= 10:
                    score += 30
                elif stock['roe'] >= 7:
                    score += 20
                
                # 부채비율 가점
                debt_ratio = stock.get('debt_ratio', 200)
                if debt_ratio < 50:
                    score += 30
                elif debt_ratio < 100:
                    score += 20
                elif debt_ratio < 150:
                    score += 10
                
                # 유동비율 가점
                current_ratio = stock.get('current_ratio', 100)
                if current_ratio >= 200:
                    score += 30
                elif current_ratio >= 150:
                    score += 20
                elif current_ratio >= 100:
                    score += 10
                
                quality_scores.append(score)
            
            avg_quality = sum(quality_scores) / len(quality_scores)
            
            # 집중도 리스크 (HHI: Herfindahl-Hirschman Index)
            weights = [s['market_cap'] / total_market_cap for s in stocks]
            hhi = sum(w**2 for w in weights) * 10000  # 0-10000 스케일
            concentration_risk = min(100, hhi / 100)  # 0-100 스케일
            
            metrics = {
                'total_stocks': total_stocks,
                'avg_per': round(avg_per, 2),
                'avg_pbr': round(avg_pbr, 2),
                'avg_roe': round(avg_roe, 1),
                'avg_score': round(avg_score, 1),
                'total_market_cap': total_market_cap,
                'total_market_cap_str': f"{total_market_cap/1e12:.2f}조원",
                'sector_count': len(sector_dist),
                'sector_distribution': {
                    k: round(v, 1) for k, v in 
                    sorted(sector_distribution.items(), key=lambda x: x[1], reverse=True)
                },
                'quality_score': round(avg_quality, 1),
                'concentration_risk': round(concentration_risk, 1),
                'risk_level': '낮음' if concentration_risk < 30 else ('중간' if concentration_risk < 60 else '높음')
            }
            
            logger.debug(f"📊 포트폴리오 메트릭: {metrics}")
            return metrics
            
        except Exception as e:
            logger.error(f"메트릭 계산 실패: {e}")
            return None
    
    def generate_rebalancing_orders(
        self,
        current_portfolio: List[Dict],
        target_portfolio: List[Dict],
        min_change_threshold: float = 0.05
    ) -> Optional[Dict]:
        """
        리밸런싱 주문 생성 (기존 → 목표 포트폴리오 전환)
        
        Args:
            current_portfolio: 현재 보유 종목 리스트
                [{'symbol': '005930', 'quantity': 10, 'avg_price': 70000}, ...]
            target_portfolio: 목표 포트폴리오 (find_real_value_stocks 결과)
            min_change_threshold: 최소 변경 비율 (기본 5%, 이하는 유지)
            
        Returns:
            {
                'sell': [{'symbol': ..., 'quantity': ..., 'reason': ...}, ...],
                'buy': [{'symbol': ..., 'target_weight': ..., 'reason': ...}, ...],
                'hold': [{'symbol': ..., 'quantity': ..., 'reason': ...}, ...],
                'summary': {
                    'sell_count': ...,
                    'buy_count': ...,
                    'hold_count': ...,
                    'turnover_rate': ...
                }
            }
            
        Example:
            current = [
                {'symbol': '005930', 'quantity': 10, 'avg_price': 70000},
                {'symbol': '000660', 'quantity': 5, 'avg_price': 100000}
            ]
            target = mcp.find_real_value_stocks(limit=30)
            orders = mcp.generate_rebalancing_orders(current, target)
            
            print(f"매도: {len(orders['sell'])}개")
            print(f"매수: {len(orders['buy'])}개")
        """
        try:
            if not target_portfolio:
                logger.warning("목표 포트폴리오가 비어있습니다")
                return None
            
            # 현재 보유 종목 코드 집합
            current_symbols = set(p['symbol'] for p in current_portfolio) if current_portfolio else set()
            target_symbols = set(s['symbol'] for s in target_portfolio)
            
            # 주문 분류
            sell_orders = []
            buy_orders = []
            hold_orders = []
            
            # 1. 매도 대상 (목표에 없는 종목)
            for current in (current_portfolio or []):
                symbol = current['symbol']
                if symbol not in target_symbols:
                    sell_orders.append({
                        'symbol': symbol,
                        'quantity': current['quantity'],
                        'avg_price': current.get('avg_price', 0),
                        'reason': '목표 포트폴리오에서 제외됨'
                    })
            
            # 2. 매수 대상 (새로 진입하는 종목)
            for target in target_portfolio:
                symbol = target['symbol']
                if symbol not in current_symbols:
                    buy_orders.append({
                        'symbol': symbol,
                        'name': target['name'],
                        'price': target['price'],
                        'target_weight': target.get('position_weight', 1.0 / len(target_portfolio)),
                        'score': target['score'],
                        'reason': f"신규 진입 (점수: {target['score']:.1f})"
                    })
                else:
                    # 이미 보유 중인 종목
                    hold_orders.append({
                        'symbol': symbol,
                        'name': target['name'],
                        'price': target['price'],
                        'score': target['score'],
                        'reason': '보유 유지 (목표 포트폴리오 포함)'
                    })
            
            # 요약 통계
            total_current = len(current_symbols)
            total_target = len(target_symbols)
            turnover_rate = (len(sell_orders) + len(buy_orders)) / max(total_current, total_target) * 100 if max(total_current, total_target) > 0 else 0
            
            summary = {
                'sell_count': len(sell_orders),
                'buy_count': len(buy_orders),
                'hold_count': len(hold_orders),
                'turnover_rate': round(turnover_rate, 1),
                'current_total': total_current,
                'target_total': total_target
            }
            
            result = {
                'sell': sell_orders,
                'buy': buy_orders,
                'hold': hold_orders,
                'summary': summary
            }
            
            logger.info(
                f"📋 리밸런싱 주문: "
                f"매도 {summary['sell_count']}개, "
                f"매수 {summary['buy_count']}개, "
                f"유지 {summary['hold_count']}개 | "
                f"회전율: {summary['turnover_rate']:.1f}%"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"리밸런싱 주문 생성 실패: {e}")
            return None
    
    def _get_sector_bonus(self, sector: str, per: float, pbr: float) -> float:
        """
        섹터별 보너스 점수 (상대적 저평가 섹터 가점)
        
        ✅ 개선: 간결한 선형 스케일 + 밸류 저평가 추가 가점
        """
        try:
            s = (sector or '').strip()
            base = 50.0
            
            # 경기순환/디스카운트 섹터 가점
            if s in ('지주회사', '철강', '에너지', '정유', '조선', '통신'):
                base += 10.0
            
            # 극단 저평가 시 추가 가점
            cheap = 0.0
            if per > 0 and per < 12:
                cheap += 10.0
            if pbr > 0 and pbr < 1.0:
                cheap += 10.0
            
            return min(100.0, base + cheap)
        except:
            return 50.0
    
    def clear_cache(self):
        """캐시 초기화 (멀티스레드 안전)"""
        with self._cache_lock:  # ✅ Lock으로 보호
            self.cache.clear()
        logger.info("KIS API 캐시 초기화 완료")
    
    def close(self):
        """세션 종료 및 리소스 정리"""
        if hasattr(self, 'session') and self.session:
            self.session.close()
            logger.info("KIS API 세션 종료 완료")
    
    def __enter__(self):
        """컨텍스트 매니저 진입 (with문 지원)"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료 (with문 지원)"""
        self.close()
        return False  # 예외를 전파


# ============================================================================
# 사용 예제 (Usage Examples)
# ============================================================================
"""
# 1. 기본 사용 (권장 설정: 0.15초 간격)
from oauth_manager import OAuthManager
oauth = OAuthManager(appkey="...", appsecret="...")

# ✅ 권장 설정: request_interval=0.15 (6.7req/s, 실측 안전값)
# - KIS 공식 제한: 실전 20req/s, 모의 2req/s
# - 실측 결과: 10req/s에서도 간헐적 500 오류 발생
# - 안전한 운영값: 6~7req/s (0.15초 간격)
mcp = MCPKISIntegration(oauth, request_interval=0.15, timeout=(10, 30))

# 1-1. 컨텍스트 매니저 사용 (권장)
with MCPKISIntegration(oauth) as mcp:
    # ✅ 적응형 레이트 리밋 자동 동작:
    #    - 연속 500 오류 3회 → 30초간 슬로우 모드 (간격 2배)
    #    - 슬로우 모드 중: 0.3초 간격 (3.3req/s)
    #    - 정상 복귀 시 자동 로그
    price = mcp.get_current_price("005930")
    # 자동으로 세션 종료

# ⚠️ 중요: 토큰은 1일 1회 발급, 24시간 유효
# - 토큰은 자동으로 .kis_token_cache.json에 캐싱됩니다 (0o600 퍼미션)
# - 캐시된 토큰이 유효하면 자동으로 재사용됩니다
# - 새로운 토큰은 만료된 경우에만 발급됩니다
# - 401 Unauthorized 시 자동으로 캐시 파기 후 재발급 시도
# - 멀티스레드/프로세스 안전 (파일 락 + 원자적 쓰기)

# 2. 현재가 조회
price = mcp.get_current_price("005930")  # 삼성전자

# 3. 차트 데이터 (페이지네이션 자동)
chart = mcp.get_chart_data("005930", period="D", days=365, use_pagination=True)
print(f"차트 데이터: {len(chart)}개")

# 4. 투자자 동향 (30일 전체 데이터)
investor = mcp.get_investor_trend_daily("005930", use_pagination=True)
print(f"투자자 동향: {len(investor)}개")

# 5. 배당주 순위 (페이지네이션으로 전체 수집)
dividend = mcp.get_dividend_ranking(limit=200, use_pagination=True)
print(f"배당주: {len(dividend)}개")

# 6. 가치주 발굴 (외부 종목 유니버스 활용)
stock_universe = ["005930", "000660", "035420", "035720", ...]
value_stocks = mcp.find_real_value_stocks(
    limit=50,
    criteria={'per_max': 18, 'pbr_max': 2.0, 'roe_min': 8},
    candidate_pool_size=200,
    stock_universe=stock_universe  # ✨ 기존 시스템과 통합!
)

# 7. 종합 분석 (종목코드 또는 종목명)
# 종목코드로 조회
analysis = mcp.analyze_stock_comprehensive("005930")
print(f"종합 점수: {analysis['comprehensive_score']['total_score']}")

# ✨ 종목명으로도 조회 가능!
analysis = mcp.analyze_stock_comprehensive("삼성전자")
analysis = mcp.analyze_stock_comprehensive("시프트업")
analysis = mcp.analyze_stock_comprehensive("KB금융")

# 7-1. 종목명 검색만 (코드만 필요한 경우)
code = mcp.search_stock_by_name("시프트업")  # "462870"
code = mcp.search_stock_by_name("삼성전자")  # "005930"

# 8. 세션 종료 (컨텍스트 매니저를 쓰지 않는 경우)
mcp.close()

# 💡 캐시 관리:
# - 캐시 크기: 최대 2000개 (FIFO 방식 자동 제거)
# - 엔드포인트별 TTL: 현재가 10초, 순위 5분, 재무 1시간, 배당 2시간
# - 캐시 초기화: mcp.clear_cache()

# 💡 에러 복구:
# - 401 Unauthorized: 자동 토큰 재발급
# - 429/503: Retry-After 헤더 존중 + 지터
# - 500 연속 5회: 세션 재생성

# 💡 환경별 레이트 리밋 권장값:
# - 실전투자: request_interval=0.15 (기본값, 6.7req/s, 실측 안전)
# - 모의투자: request_interval=0.5 (2req/s, KIS 공식 제한)
# - 공격적: request_interval=0.1 (10req/s, 500 오류 위험 ↑)
# mcp = MCPKISIntegration(oauth, request_interval=0.5)  # 모의투자
"""