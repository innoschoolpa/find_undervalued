#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS API 관리자 모듈

한국투자증권 Open API와의 연동을 관리합니다.
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from kis_token_manager import get_token_manager

try:
    from config_manager import ConfigManager
except ImportError:  # pragma: no cover
    ConfigManager = None
import hashlib
import time

@dataclass
class KISAPIConfig:
    """KIS API 설정 데이터 클래스"""
    api_key: str
    api_secret: str
    base_url: str = "https://openapi.koreainvestment.com:9443"
    max_tps: int = 8
    cache_ttl_price: float = 5.0
    cache_ttl_financial: float = 900.0
    cache_max_keys: int = 2000
    timeout: int = 30
    retry_count: int = 3

class KISAPIManager:
    """KIS API 관리자 클래스"""
    
    def __init__(self, config: Optional[KISAPIConfig] = None):
        self.logger = logging.getLogger(__name__)
        
        if config:
            self.config = config
        elif ConfigManager:
            self.config = self._load_config_from_manager()
        else:
            self.config = self._load_config_from_env()
        
        self.access_token = None
        self.token_expires_at = None
        self.request_count = 0
        self.last_request_time = 0
        self.cache = {}
        self.token_manager = get_token_manager()
        
        self.logger.info("KIS API Manager 초기화 완료")
    
    def _load_config_from_env(self) -> KISAPIConfig:
        """환경변수에서 설정 로드"""
        return KISAPIConfig(
            api_key=os.getenv('KIS_API_KEY', ''),
            api_secret=os.getenv('KIS_API_SECRET', ''),
            base_url=os.getenv('KIS_API_BASE_URL', 'https://openapi.koreainvestment.com:9443'),
            max_tps=int(os.getenv('KIS_MAX_TPS', '8')),
            cache_ttl_price=float(os.getenv('KIS_CACHE_TTL_PRICE', '5.0')),
            cache_ttl_financial=float(os.getenv('KIS_CACHE_TTL_FINANCIAL', '900.0')),
            cache_max_keys=int(os.getenv('KIS_CACHE_MAX_KEYS', '2000')),
            timeout=int(os.getenv('API_TIMEOUT', '30')),
            retry_count=int(os.getenv('API_RETRY_COUNT', '3'))
        )

    def _load_config_from_manager(self) -> KISAPIConfig:
        """ConfigManager에서 설정 로드"""
        manager = ConfigManager()
        return KISAPIConfig(
            api_key=manager.get('kis_api.app_key') or manager.get('kis.api_key') or manager.get('kis_api_key', ''),
            api_secret=manager.get('kis_api.app_secret') or manager.get('kis.api_secret') or manager.get('kis_api_secret', ''),
            base_url=manager.get('kis_api.base_url') or manager.get('kis.base_url') or manager.get('kis_api_base_url', 'https://openapi.koreainvestment.com:9443'),
            max_tps=manager.get('kis_api.max_tps') or manager.get('kis.max_tps') or manager.get('kis_max_tps', 8),
            cache_ttl_price=manager.get('kis_api.cache_ttl_price') or manager.get('kis.cache_ttl_price') or manager.get('kis_cache_ttl_price', 5.0),
            cache_ttl_financial=manager.get('kis_api.cache_ttl_financial') or manager.get('kis.cache_ttl_financial') or manager.get('kis_cache_ttl_financial', 900.0),
            cache_max_keys=manager.get('kis_api.cache_max_keys') or manager.get('kis.cache_max_keys') or manager.get('kis_cache_max_keys', 2000),
            timeout=manager.get('kis_api.timeout') or manager.get('kis.timeout') or manager.get('api_timeout', 30),
            retry_count=manager.get('kis_api.retry_count') or manager.get('kis.retry_count') or manager.get('api_retry_count', 3),
        )
    
    def _check_api_credentials(self) -> bool:
        """API 자격 증명 확인"""
        if not self.config.api_key or not self.config.api_secret:
            self.logger.warning("KIS API 키가 설정되지 않았습니다. 환경변수를 확인하세요.")
            return False
        return True
    
    def _rate_limit_check(self) -> None:
        """Rate Limiting 체크"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < (1.0 / self.config.max_tps):
            sleep_time = (1.0 / self.config.max_tps) - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def _get_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """캐시 키 생성"""
        key_data = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any], ttl: float) -> bool:
        """캐시 유효성 검사"""
        if not cache_entry:
            return False
        
        cache_time = cache_entry.get('timestamp', 0)
        return (time.time() - cache_time) < ttl
    
    def _cleanup_cache(self) -> None:
        """캐시 정리"""
        if len(self.cache) > self.config.cache_max_keys:
            # 가장 오래된 캐시 항목들 제거
            sorted_items = sorted(self.cache.items(), key=lambda x: x[1].get('timestamp', 0))
            items_to_remove = len(self.cache) - self.config.cache_max_keys
            
            for key, _ in sorted_items[:items_to_remove]:
                del self.cache[key]
    
    def get_access_token(self) -> Optional[str]:
        """액세스 토큰 획득"""
        if not self._check_api_credentials():
            return None
        
        # 기존 토큰 매니저가 내부적으로 만료 여부를 관리하므로 그대로 위임한다.
        try:
            token = self.token_manager.get_valid_token()
            if token:
                self.access_token = token
                # 토큰 매니저는 24시간 만료 정책을 적용하므로 여기서는 정보 목적 정도로만 유지
                self.token_expires_at = datetime.now() + timedelta(hours=24)
                return self.access_token
            self.logger.error("KIS 토큰을 가져오지 못했습니다.")
            return None
        except Exception as e:
            self.logger.error(f"액세스 토큰 획득 실패: {e}")
            return None
    
    def get_stock_price(self, symbol: str, period: str = "D", count: int = 100) -> Optional[Dict[str, Any]]:
        """주식 가격 데이터 조회"""
        cache_key = self._get_cache_key('stock_price', {'symbol': symbol, 'period': period, 'count': count})
        cache_entry = self.cache.get(cache_key)
        
        if self._is_cache_valid(cache_entry, self.config.cache_ttl_price):
            self.logger.debug(f"캐시에서 가격 데이터 반환: {symbol}")
            return cache_entry['data']
        
        access_token = self.get_access_token()
        if not access_token:
            return None
        
        try:
            self._rate_limit_check()
            
            url = f"{self.config.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'appkey': self.config.api_key,
                'appsecret': self.config.api_secret,
                'tr_id': 'FHKST01010100'
            }
            params = {
                'fid_cond_mrkt_div_code': 'J',
                'fid_input_iscd': symbol,
                'fid_input_date_1': '',
                'fid_input_date_2': '',
                'fid_period_div_code': period,
                'fid_org_adj_prc': '1'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=self.config.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # 캐시에 저장
            self.cache[cache_key] = {
                'data': data,
                'timestamp': time.time()
            }
            self._cleanup_cache()
            
            self.logger.info(f"주식 가격 데이터 조회 완료: {symbol}")
            return data
            
        except Exception as e:
            self.logger.error(f"주식 가격 데이터 조회 실패 ({symbol}): {e}")
            return None
    
    def get_financial_data(self, symbol: str, year: int = 2024) -> Optional[Dict[str, Any]]:
        """재무 데이터 조회"""
        cache_key = self._get_cache_key('financial_data', {'symbol': symbol, 'year': year})
        cache_entry = self.cache.get(cache_key)
        
        if self._is_cache_valid(cache_entry, self.config.cache_ttl_financial):
            self.logger.debug(f"캐시에서 재무 데이터 반환: {symbol}")
            return cache_entry['data']
        
        access_token = self.get_access_token()
        if not access_token:
            return None
        
        try:
            self._rate_limit_check()
            
            url = f"{self.config.base_url}/uapi/domestic-stock/v1/finance/annual-index"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'appkey': self.config.api_key,
                'appsecret': self.config.api_secret,
                'tr_id': 'FHKST01010100'
            }
            params = {
                'fid_cond_mrkt_div_code': 'J',
                'fid_input_iscd': symbol,
                'fid_div_cls_code': '0',
                'fid_input_date_1': f'{year}1231',
                'fid_input_date_2': f'{year}0101'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=self.config.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # 캐시에 저장
            self.cache[cache_key] = {
                'data': data,
                'timestamp': time.time()
            }
            self._cleanup_cache()
            
            self.logger.info(f"재무 데이터 조회 완료: {symbol}")
            return data
            
        except Exception as e:
            self.logger.error(f"재무 데이터 조회 실패 ({symbol}): {e}")
            return None
    
    def get_market_data(self, symbols: List[str]) -> Dict[str, Any]:
        """여러 종목의 시장 데이터 조회"""
        results = {}
        
        for symbol in symbols:
            try:
                price_data = self.get_stock_price(symbol)
                financial_data = self.get_financial_data(symbol)
                
                if price_data and financial_data:
                    results[symbol] = {
                        'price': price_data,
                        'financial': financial_data,
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    self.logger.warning(f"데이터 조회 실패: {symbol}")
                    
            except Exception as e:
                self.logger.error(f"종목 데이터 조회 중 오류 ({symbol}): {e}")
        
        return results
    
    def get_api_status(self) -> Dict[str, Any]:
        """API 상태 정보 반환"""
        return {
            'api_key_configured': bool(self.config.api_key and self.config.api_secret),
            'access_token_valid': bool(self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at),
            'request_count': self.request_count,
            'cache_size': len(self.cache),
            'cache_max_size': self.config.cache_max_keys,
            'rate_limit_tps': self.config.max_tps,
            'last_request_time': self.last_request_time
        }

def create_kis_api_manager() -> KISAPIManager:
    """KIS API Manager 인스턴스 생성"""
    return KISAPIManager()

if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)
    
    manager = create_kis_api_manager()
    status = manager.get_api_status()
    
    print("KIS API Manager 상태:")
    for key, value in status.items():
        print(f"  {key}: {value}")


