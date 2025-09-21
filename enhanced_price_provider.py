#!/usr/bin/env python3
"""
현재가 데이터 제공을 위한 향상된 프로바이더
여러 데이터 소스를 통합하여 안정적인 현재가 정보 제공
"""

import requests
import time
import logging
import pandas as pd
from typing import Dict, Optional, Any
from kis_data_provider import KISDataProvider
from kis_token_manager import KISTokenManager
import yaml
import json

logger = logging.getLogger(__name__)

class EnhancedPriceProvider:
    """현재가 데이터를 안정적으로 제공하는 향상된 프로바이더"""
    
    def __init__(self, config_path: str = 'config.yaml'):
        self.kis_provider = KISDataProvider(config_path)
        self.token_manager = KISTokenManager(config_path)
        
        # KOSPI 마스터 데이터 로드 (대체 데이터 소스)
        self.kospi_data = self._load_kospi_master_data()
        
        # 캐시 설정
        self.price_cache = {}
        self.cache_expiry = {}
        self.cache_duration = 300  # 5분 캐시
        
    def _load_kospi_master_data(self) -> Optional[pd.DataFrame]:
        """KOSPI 마스터 데이터 로드"""
        try:
            # 여러 가능한 파일 경로 시도
            possible_paths = [
                'kospi_code.xlsx',
                'kospi_code.mst',
                'data/kospi_code.xlsx',
                'cache/kospi_code.xlsx'
            ]
            
            for path in possible_paths:
                try:
                    if path.endswith('.xlsx'):
                        df = pd.read_excel(path)
                        if '종목코드' in df.columns and '현재가' in df.columns:
                            logger.info(f"✅ KOSPI 마스터 데이터 로드 성공: {path}")
                            return df.set_index('종목코드')
                    elif path.endswith('.mst'):
                        # .mst 파일 처리 (필요시)
                        pass
                except Exception as e:
                    logger.debug(f"⚠️ {path} 로드 실패: {e}")
                    continue
            
            logger.warning("⚠️ KOSPI 마스터 데이터를 찾을 수 없습니다.")
            return None
            
        except Exception as e:
            logger.error(f"❌ KOSPI 마스터 데이터 로드 실패: {e}")
            return None
    
    def get_current_price(self, symbol: str, max_retries: int = 3) -> Optional[float]:
        """
        종목의 현재가를 조회합니다.
        여러 데이터 소스를 시도하여 안정적인 현재가 제공
        """
        # 캐시 확인
        if self._is_cached(symbol):
            return self.price_cache[symbol]
        
        # 1. KIS API에서 현재가 조회
        for attempt in range(max_retries):
            try:
                logger.info(f"📊 {symbol} 현재가 조회 시도 {attempt + 1}/{max_retries}")
                
                # 토큰 갱신 확인
                self.token_manager.authenticate()
                
                price_info = self.kis_provider.get_stock_price_info(symbol)
                
                if price_info and price_info.get('current_price', 0) > 0:
                    current_price = float(price_info['current_price'])
                    self._cache_price(symbol, current_price)
                    logger.info(f"✅ {symbol} 현재가 조회 성공: {current_price:,}원")
                    return current_price
                
                # API 제한 대기
                time.sleep(2.0)
                
            except Exception as e:
                logger.warning(f"⚠️ {symbol} KIS API 조회 실패 (시도 {attempt + 1}): {e}")
                time.sleep(3.0)
        
        # 2. KOSPI 마스터 데이터에서 현재가 조회
        if self.kospi_data is not None:
            try:
                # 종목코드 정규화 (6자리로 맞춤)
                normalized_symbol = symbol.zfill(6)
                
                if normalized_symbol in self.kospi_data.index:
                    price_data = self.kospi_data.loc[normalized_symbol]
                    current_price = float(price_data.get('현재가', 0))
                    
                    if current_price > 0:
                        self._cache_price(symbol, current_price)
                        logger.info(f"✅ {symbol} KOSPI 마스터에서 현재가 조회: {current_price:,}원")
                        return current_price
                        
            except Exception as e:
                logger.warning(f"⚠️ {symbol} KOSPI 마스터 데이터 조회 실패: {e}")
        
        # 3. 대체 API 시도 (필요시 구현)
        logger.warning(f"⚠️ {symbol} 모든 데이터 소스에서 현재가 조회 실패")
        return None
    
    def get_comprehensive_price_data(self, symbol: str) -> Dict[str, Any]:
        """종목의 종합적인 가격 데이터를 조회합니다."""
        result = {
            'current_price': None,
            'price_change': None,
            'price_change_rate': None,
            'volume': None,
            'per': None,
            'pbr': None,
            'eps': None,
            'bps': None,
            'market_cap': None,
            'w52_high': None,
            'w52_low': None
        }
        
        try:
            # KIS API에서 종합 데이터 조회
            price_info = self.kis_provider.get_stock_price_info(symbol)
            
            if price_info:
                result.update({
                    'current_price': price_info.get('current_price'),
                    'price_change': price_info.get('change_price'),
                    'price_change_rate': price_info.get('change_rate'),
                    'volume': price_info.get('volume'),
                    'per': price_info.get('per'),
                    'pbr': price_info.get('pbr'),
                    'eps': price_info.get('eps'),
                    'bps': price_info.get('bps'),
                    'market_cap': price_info.get('market_cap'),
                    'w52_high': price_info.get('w52_high'),
                    'w52_low': price_info.get('w52_low')
                })
                
                # 현재가가 없으면 별도 조회
                if not result['current_price']:
                    result['current_price'] = self.get_current_price(symbol)
            
        except Exception as e:
            logger.warning(f"⚠️ {symbol} 종합 가격 데이터 조회 실패: {e}")
            
            # 현재가만이라도 조회 시도
            result['current_price'] = self.get_current_price(symbol)
        
        return result
    
    def get_52week_data(self, symbol: str) -> Dict[str, Any]:
        """52주 고점/저점 데이터를 조회합니다."""
        try:
            # KIS API에서 52주 데이터 조회
            price_info = self.kis_provider.get_stock_price_info(symbol)
            
            if price_info:
                return {
                    'w52_high': price_info.get('w52_high'),
                    'w52_low': price_info.get('w52_low'),
                    'current_price': price_info.get('current_price')
                }
            
            # 대체 방법: 일봉 데이터에서 52주 고저 계산
            try:
                daily_data = self.kis_provider.get_daily_price_history(symbol, 365)
                if daily_data is not None and not daily_data.empty and 'close' in daily_data.columns:
                    return {
                        'w52_high': daily_data['close'].max(),
                        'w52_low': daily_data['close'].min(),
                        'current_price': daily_data['close'].iloc[-1] if len(daily_data) > 0 else None
                    }
            except Exception as e:
                logger.debug(f"⚠️ {symbol} 일봉 데이터로 52주 계산 실패: {e}")
                
        except Exception as e:
            logger.warning(f"⚠️ {symbol} 52주 데이터 조회 실패: {e}")
        
        return {'w52_high': None, 'w52_low': None, 'current_price': None}
    
    def calculate_price_position(self, symbol: str) -> Optional[float]:
        """52주 가격 위치를 계산합니다."""
        try:
            data = self.get_52week_data(symbol)
            
            current_price = data.get('current_price', 0)
            w52_high = data.get('w52_high', 0)
            w52_low = data.get('w52_low', 0)
            
            if current_price and w52_high and w52_low and w52_high > w52_low:
                position = ((current_price - w52_low) / (w52_high - w52_low)) * 100
                return max(0, min(100, position))  # 0~100 범위 제한
            
        except Exception as e:
            logger.warning(f"⚠️ {symbol} 가격 위치 계산 실패: {e}")
        
        return None
    
    def _is_cached(self, symbol: str) -> bool:
        """캐시된 데이터가 유효한지 확인"""
        if symbol not in self.price_cache:
            return False
        
        if symbol not in self.cache_expiry:
            return False
        
        return time.time() < self.cache_expiry[symbol]
    
    def _cache_price(self, symbol: str, price: float):
        """가격 데이터를 캐시에 저장"""
        self.price_cache[symbol] = price
        self.cache_expiry[symbol] = time.time() + self.cache_duration
    
    def clear_cache(self):
        """캐시 초기화"""
        self.price_cache.clear()
        self.cache_expiry.clear()
        logger.info("🧹 가격 캐시 초기화 완료")
    
    def get_bulk_prices(self, symbols: list) -> Dict[str, float]:
        """여러 종목의 현재가를 일괄 조회"""
        results = {}
        
        for symbol in symbols:
            try:
                price = self.get_current_price(symbol)
                results[symbol] = price
                
                # API 제한 고려한 대기
                time.sleep(0.2)
                
            except Exception as e:
                logger.warning(f"⚠️ {symbol} 일괄 조회 실패: {e}")
                results[symbol] = None
        
        return results

def test_price_provider():
    """가격 프로바이더 테스트"""
    import logging
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    provider = EnhancedPriceProvider()
    
    # 테스트 종목들
    test_symbols = ['000660', '005380', '105560']  # SK하이닉스, 현대차, KB금융
    
    print("🧪 가격 프로바이더 테스트 시작")
    print("=" * 50)
    
    for symbol in test_symbols:
        print(f"\n📊 {symbol} 테스트:")
        
        # 현재가 조회
        price = provider.get_current_price(symbol)
        if price:
            print(f"✅ 현재가: {price:,}원")
        else:
            print("❌ 현재가 조회 실패")
        
        # 종합 데이터 조회
        data = provider.get_comprehensive_price_data(symbol)
        print(f"📋 종합 데이터: {data}")
        
        # 52주 데이터 및 가격 위치 계산
        w52_data = provider.get_52week_data(symbol)
        print(f"📈 52주 데이터: {w52_data}")
        
        position = provider.calculate_price_position(symbol)
        if position is not None:
            print(f"📍 가격 위치: {position:.1f}%")
        else:
            print("❌ 가격 위치 계산 실패")

if __name__ == "__main__":
    test_price_provider()
