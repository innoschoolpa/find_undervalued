#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
가치주 분석 엔진 (순수 계산/분석 로직)
UI 의존성 없이 독립적으로 테스트 가능
"""

import pandas as pd
from datetime import datetime
import logging
import concurrent.futures
import threading
import time
from functools import lru_cache
from typing import Any, Dict, Optional, List, Tuple
import os
import math
import statistics
from collections import Counter

from financial_data_provider import FinancialDataProvider
from sector_contextualizer import SectorCycleContextualizer
from sector_utils import get_sector_benchmarks

# 로깅 설정
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
_logger = logging.getLogger(__name__)
if not _logger.handlers:
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format='%(levelname)s:%(name)s:%(message)s'
    )
logger = _logger

# MCP 통합 모듈
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


class ValueStockEngine:
    """저평가 가치주 분석 엔진 (계산/분석 전용)"""
    
    # 블랙리스트 상수
    BAD_CODES = {'068290'}
    
    def __init__(self, analyzer=None, mcp_integration=None, oauth_manager=None):
        """
        Args:
            analyzer: EnhancedIntegratedAnalyzer 인스턴스 (옵션)
            mcp_integration: MCPKISIntegration 인스턴스 (옵션)
            oauth_manager: KIS OAuth 매니저 (옵션)
        """
        # OAuth 매니저 초기화
        if oauth_manager is None:
            import yaml
            try:
                with open('config.yaml', 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    kis_config = config.get('kis_api', {})
            except Exception as e:
                logger.warning(f"config.yaml 로드 실패: {e}")
                kis_config = {}
            
            class SimpleOAuthManager:
                def __init__(self, appkey, appsecret, is_test=False):
                    self.appkey = appkey
                    self.appsecret = appsecret
                    self.is_test = is_test
                    self.base_url = ("https://openapivts.koreainvestment.com:29443" if is_test 
                                    else "https://openapi.koreainvestment.com:9443")
                    self._rest_token = None
                    
                def get_rest_token(self):
                    import json
                    import time
                    try:
                        with open('.kis_token_cache.json', 'r') as f:
                            cache = json.load(f)
                        token = cache.get('token')
                        exp = cache.get('expires_at')
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
        else:
            self.oauth_manager = oauth_manager
        
        # MCP 통합
        self.mcp_integration = mcp_integration
        
        # 가치주 평가 기준
        self.default_value_criteria = {
            'per_max': 15.0,
            'pbr_max': 1.5,
            'roe_min': 10.0,
            'dividend_min': 2.0,
            'debt_ratio_max': 50.0,
            'current_ratio_min': 100.0
        }
        
        # 섹터 데이터 제공자
        self.data_provider = FinancialDataProvider()
        self.sector_context = SectorCycleContextualizer()
        self._analyzer = analyzer
        self._last_api_success = False
        
        # API 호출 한도 관리
        self.rate_limiter = TokenBucket(rate_per_sec=2.0, capacity=10)
        
        # 스레드 안전성
        self._analyzer_sem = threading.BoundedSemaphore(3)
        self._analyzer_init_lock = threading.Lock()
        
        # 프라임 캐시
        self._primed_cache = {}
        
        # 실패 캐시
        self._failed_codes = set()
        self._failed_codes_ttl = {}
        self._failed_codes_max = 500
        self._failed_codes_ttl_sec = 1800
        self._failed_lock = threading.Lock()
    
    def _gc_failed_codes(self):
        """실패 캐시 가비지 컬렉션"""
        now = time.time()
        with self._failed_lock:
            for code, ts in list(self._failed_codes_ttl.items()):
                if now - ts > self._failed_codes_ttl_sec:
                    self._failed_codes_ttl.pop(code, None)
                    self._failed_codes.discard(code)
            if len(self._failed_codes) > self._failed_codes_max:
                for code, _ in sorted(self._failed_codes_ttl.items(), key=lambda x: x[1])[:len(self._failed_codes)-self._failed_codes_max]:
                    self._failed_codes_ttl.pop(code, None)
                    self._failed_codes.discard(code)
    
    @property
    def analyzer(self):
        """Analyzer lazy loading"""
        if self._analyzer is None:
            with self._analyzer_init_lock:
                if self._analyzer is None:
                    from enhanced_integrated_analyzer_refactored import EnhancedIntegratedAnalyzer
                    self._analyzer = EnhancedIntegratedAnalyzer()
        return self._analyzer
    
    def get_sector_specific_criteria(self, sector: str) -> Dict[str, float]:
        """업종별 가치주 평가 기준 반환"""
        sector_criteria = {
            '금융업': {'per_max': 12.0, 'pbr_max': 1.2, 'roe_min': 12.0, 'dividend_min': 3.0, 'debt_ratio_max': 90.0, 'current_ratio_min': 80.0},
            '기술업': {'per_max': 25.0, 'pbr_max': 3.0, 'roe_min': 8.0, 'dividend_min': 1.0, 'debt_ratio_max': 40.0, 'current_ratio_min': 120.0},
            '제조업': {'per_max': 15.0, 'pbr_max': 1.8, 'roe_min': 10.0, 'dividend_min': 2.0, 'debt_ratio_max': 60.0, 'current_ratio_min': 110.0},
            '헬스케어': {'per_max': 30.0, 'pbr_max': 4.0, 'roe_min': 6.0, 'dividend_min': 1.0, 'debt_ratio_max': 35.0, 'current_ratio_min': 130.0},
            '에너지/화학': {'per_max': 15.0, 'pbr_max': 1.8, 'roe_min': 8.0, 'dividend_min': 3.0, 'debt_ratio_max': 50.0, 'current_ratio_min': 100.0},
            '소비재': {'per_max': 20.0, 'pbr_max': 2.5, 'roe_min': 12.0, 'dividend_min': 2.5, 'debt_ratio_max': 45.0, 'current_ratio_min': 115.0},
            '통신업': {'per_max': 15.0, 'pbr_max': 2.0, 'roe_min': 8.0, 'dividend_min': 3.5, 'debt_ratio_max': 70.0, 'current_ratio_min': 90.0},
            '건설업': {'per_max': 12.0, 'pbr_max': 1.5, 'roe_min': 8.0, 'dividend_min': 2.5, 'debt_ratio_max': 65.0, 'current_ratio_min': 105.0},
        }
        
        sector_normalized = self._normalize_sector_name(sector)
        return sector_criteria.get(sector_normalized, self.default_value_criteria)
    
    def _normalize_sector_name(self, sector: str) -> str:
        """섹터명 정규화"""
        if not sector:
            return '기타'
        s = str(sector).strip().lower()
        
        for ch in [' ', '·', '.', '/', '\\', '-', '_']:
            s = s.replace(ch, '')
        
        s = (s
             .replace('it서비스', 'it')
             .replace('정보기술', 'it')
             .replace('통신서비스', '통신')
             .replace('운송장비부품', '운송장비'))
        
        rules = [
            (['금융','은행','증권','보험'], '금융업'),
            (['it','아이티','기술','반도체','전자','소프트웨어','인터넷'], '기술업'),
            (['제조','철강','화학','에너지','유틸리티','소재'], '에너지/화학'),
            (['헬스케어','의료','제약','바이오'], '헬스케어'),
            (['소비재','유통','식품','음료'], '소비재'),
            (['통신','미디어','엔터테인먼트'], '통신업'),
            (['건설','부동산'], '건설업'),
        ]
        
        for keywords, label in rules:
            if any(kw in s for kw in keywords):
                return label
        return '제조업'
    
    def _get_sector_criteria_display(self, sector_name: str) -> str:
        """섹터 기준 표시용 문자열"""
        c = self.get_sector_specific_criteria(sector_name)
        per = self._safe_num(c.get('per_max'), 0)
        pbr = self._safe_num(c.get('pbr_max'), 1)
        roe = self._safe_num(c.get('roe_min'), 0)
        return f"PER≤{per}, PBR≤{pbr}, ROE≥{roe}%"
    
    def is_value_stock_unified(self, stock_data: Dict[str, Any], options: Dict[str, Any]) -> bool:
        """✅ 가치주 판단 로직 통일 (사용자 설정 반영)"""
        sector_name = stock_data.get('sector_name', stock_data.get('sector', ''))
        criteria = self.get_sector_specific_criteria(sector_name)
        
        per = stock_data.get('per', 0)
        pbr = stock_data.get('pbr', 0)
        roe = stock_data.get('roe', 0)
        value_score = stock_data.get('value_score', 0)
        
        per_ok = per <= criteria['per_max'] if per > 0 else False
        pbr_ok = pbr <= criteria['pbr_max'] if pbr > 0 else False
        roe_ok = roe >= criteria['roe_min'] if roe > 0 else False
        
        criteria_met_count = sum([per_ok, pbr_ok, roe_ok])
        score_threshold = options.get('score_min', 60.0)
        
        return criteria_met_count == 3 and value_score >= score_threshold
    
    def format_pct_or_na(self, value: Optional[float], precision: int = 1) -> str:
        """퍼센트 값 포맷팅"""
        return "N/A" if value is None or not isinstance(value, (int, float)) or not math.isfinite(value) else f"{value:.{precision}f}%"
    
    def format_percentile(self, percentile: Optional[float], cap: float = 99.5) -> str:
        """백분위 표시"""
        return "N/A" if percentile is None else f"{min(cap, percentile):.1f}%"
    
    def _safe_num(self, x, d=1, default='N/A'):
        """안전한 숫자 포맷팅"""
        try:
            if x is None or not isinstance(x, (int, float)) or not math.isfinite(x):
                return default
            return f"{x:.{d}f}" if d > 0 else f"{x:.0f}"
        except:
            return default
    
    def _pos_or_none(self, x):
        """양수만 반환, 아니면 None"""
        try:
            val = float(x)
            return val if val > 0 else None
        except:
            return None
    
    def fmt_ratio(self, x, unit="", nd=2, na="N/A"):
        """비율 포맷팅"""
        return na if x is None else f"{x:.{nd}f}{unit}"
    
    def _relative_vs_median(self, value: float, p50: Optional[float]) -> Optional[float]:
        """중앙값 대비 상대적 비율"""
        if p50 is None or p50 == 0:
            return None
        return ((value / p50) - 1.0) * 100.0
    
    def _normalize_sector_key(self, sector_name: str) -> str:
        """섹터 키 정규화"""
        return self._normalize_sector_name(sector_name)
    
    def refresh_sector_stats_and_clear_cache(self, stocks):
        """섹터 통계 갱신"""
        self.data_provider.refresh_sector_stats(stocks)
    
    def _percentile_from_breakpoints(self, value: float, p: Dict[str, float]) -> Optional[float]:
        """백분위 계산"""
        if not p:
            return None
        try:
            if value <= p.get('p10', float('inf')):
                return 10.0
            elif value <= p.get('p25', float('inf')):
                return 25.0
            elif value <= p.get('p50', float('inf')):
                return 50.0
            elif value <= p.get('p75', float('inf')):
                return 75.0
            elif value <= p.get('p90', float('inf')):
                return 90.0
            else:
                return 95.0
        except:
            return None
    
    # 이 파일은 계속됩니다... (다음 메시지에서 나머지 메소드 추가)

