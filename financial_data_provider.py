"""
금융 데이터 제공자 모듈

재무 데이터 조회 및 분석을 담당하는 FinancialDataProvider를 제공합니다.
"""

import logging
import os
from datetime import datetime
from statistics import median
from typing import Any, Dict, List, Optional, Tuple

from abc import ABC, abstractmethod
from config_manager import ConfigManager
from utils.metrics import MetricsCollector
from utils.data_utils import DataValidator, DataConverter


class DataProvider(ABC):
    """데이터 제공자 추상 클래스"""
    
    @abstractmethod
    def get_financial_data(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """금융 데이터 조회"""
        pass
    
    @abstractmethod
    def get_price_data(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """가격 데이터 조회"""
        pass


class FinancialDataProvider(DataProvider):
    """재무 데이터 제공자 (API 호출, 캐싱, 검증)"""
    
    def __init__(self, metrics_collector: MetricsCollector = None, cache=None):
        self.metrics = metrics_collector
        self.cache = cache
        self.data_validator = DataValidator()
        self.data_converter = DataConverter()
        self._sector_metrics: Dict[str, Dict[str, Any]] = {}

        # 설정 로드
        self.config_manager = ConfigManager()

        # API 설정
        self.api_base_url = (
            self.config_manager.get('kis_api.base_url')
            or self.config_manager.get('kis.base_url')
            or self.config_manager.get('kis_api_base_url', 'https://openapi.koreainvestment.com:9443')
        )
        self.api_key = (
            self.config_manager.get('kis_api.app_key')
            or self.config_manager.get('kis.api_key')
            or self.config_manager.get('kis_api_key')
        )
        self.api_secret = (
            self.config_manager.get('kis_api.app_secret')
            or self.config_manager.get('kis.api_secret')
            or self.config_manager.get('kis_api_secret')
        )

        # 캐시 설정
        self.cache_ttl = int(
            self.config_manager.get('cache.ttl_seconds')
            or self.config_manager.get('cache_ttl_seconds', 3600)
        )

        if not self.api_key or not self.api_secret:
            logging.warning("KIS API 키가 설정되지 않았습니다. config.yaml 또는 환경변수를 확인하세요.")
    
    def get_financial_data(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        재무 데이터 조회 (캐시 우선, API 호출)
        
        Args:
            symbol: 종목 코드
            **kwargs: 추가 파라미터
        
        Returns:
            Dict: 재무 데이터
        """
        try:
            # 캐시 확인
            cache_key = f"financial_data_{symbol}"
            if self.cache:
                cached_data = self.cache.get(cache_key)
                if cached_data:
                    if self.metrics:
                        self.metrics.record_cache_hits(1)
                    return cached_data
            
            # API 호출
            financial_data = self._fetch_financial_data_from_api(symbol, **kwargs)
            
            # 데이터 검증 및 변환
            if financial_data:
                is_valid = self.data_validator.validate_financial_data(financial_data)
                if is_valid:
                    converted_data = self.data_converter.convert_financial_data(financial_data)
                else:
                    converted_data = {}
            else:
                converted_data = {}
            
            # 캐시 저장
            if self.cache and converted_data:
                self.cache.set(cache_key, converted_data, ttl=self.cache_ttl)
            
            # 메트릭 기록
            if self.metrics:
                self.metrics.record_api_calls(symbol)
            
            return converted_data
            
        except Exception as e:
            logging.error(f"재무 데이터 조회 실패 [{symbol}]: {e}")
            logging.error(f"예외 상세 정보: {type(e).__name__}: {str(e)}")
            import traceback
            logging.error(f"스택 트레이스: {traceback.format_exc()}")
            if self.metrics:
                self.metrics.record_api_errors(symbol, 'api_error')
            return {}
    
    def get_price_data(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        가격 데이터 조회
        
        Args:
            symbol: 종목 코드
            **kwargs: 추가 파라미터
        
        Returns:
            Dict: 가격 데이터
        """
        try:
            logging.debug(f"get_price_data 시작: {symbol}")
            
            # 캐시 확인
            cache_key = f"price_data_{symbol}"
            if self.cache:
                cached_data = self.cache.get(cache_key)
                if cached_data:
                    logging.debug(f"캐시에서 데이터 반환: {symbol}")
                    if self.metrics:
                        self.metrics.record_cache_hits(1)
                    return cached_data
            
            # API 호출
            logging.debug(f"API 호출 시작: {symbol}")
            price_data = self._fetch_price_data_from_api(symbol, **kwargs)
            logging.debug(f"API 응답 데이터: {price_data}")
            
            # 데이터 검증 및 변환
            if price_data:
                logging.debug(f"데이터 검증 시작: {symbol}")
                is_valid = self.data_validator.validate_price_data(price_data)
                logging.debug(f"검증 결과: {is_valid}")
                
                if is_valid:
                    converted_data = self.data_converter.convert_price_data(price_data)
                    logging.debug(f"변환 결과: {converted_data}")
                else:
                    logging.warning(f"데이터 검증 실패: {symbol}")
                    converted_data = {}
            else:
                logging.warning(f"API 응답 데이터가 비어있음: {symbol}")
                converted_data = {}
            
            # 캐시 저장
            if self.cache and converted_data:
                self.cache.set(cache_key, converted_data, ttl=self.cache_ttl)
                logging.debug(f"캐시에 저장: {symbol}")
            
            # 메트릭 기록
            if self.metrics:
                self.metrics.record_api_calls(symbol)
            
            logging.debug(f"get_price_data 완료: {symbol}, 결과: {converted_data}")
            return converted_data
            
        except Exception as e:
            logging.error(f"가격 데이터 조회 실패 [{symbol}]: {e}")
            logging.error(f"예외 상세 정보: {type(e).__name__}: {str(e)}")
            import traceback
            logging.error(f"스택 트레이스: {traceback.format_exc()}")
            if self.metrics:
                self.metrics.record_api_errors(symbol, 'api_error')
            return {}
    
    def _fetch_financial_data_from_api(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """API에서 재무 데이터 조회 (실제 KIS API 구현)"""
        try:
            # KIS API를 통한 실제 데이터 조회
            from kis_data_provider import KISDataProvider
            
            kis_provider = KISDataProvider()
            price_info = kis_provider.get_stock_price_info(symbol)
            
            if price_info:
                # KIS API 응답에서 재무 지표 추출
                return {
                    'symbol': symbol,
                    'per': price_info.get('per', 0),
                    'pbr': price_info.get('pbr', 0),
                    'eps': price_info.get('eps', 0),
                    'bps': price_info.get('bps', 0),
                    'dividend_yield': price_info.get('dividend_yield', 0),
                    'market_cap': price_info.get('market_cap', 0),
                    'listed_shares': price_info.get('listed_shares', 0),
                    'trading_value': price_info.get('trading_value', 0),
                    'foreign_holdings': price_info.get('foreign_holdings', 0),
                    'foreign_net_buy': price_info.get('foreign_net_buy', 0),
                    'program_net_buy': price_info.get('program_net_buy', 0),
                    'vol_turnover': price_info.get('vol_turnover', 0),
                    'margin_rate': price_info.get('margin_rate', 0),
                    'sector': price_info.get('sector', ''),
                    'market_status': price_info.get('market_status', 0)
                }
            else:
                # API 호출 실패시 빈 데이터 반환
                return {}
                
        except Exception as e:
            logging.error(f"KIS API 재무 데이터 조회 실패 [{symbol}]: {e}")
            return {}
    
    def _fetch_price_data_from_api(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """API에서 가격 데이터 조회 (실제 KIS API 구현)"""
        try:
            # KIS API를 통한 실제 데이터 조회
            from kis_data_provider import KISDataProvider
            
            kis_provider = KISDataProvider()
            price_info = kis_provider.get_stock_price_info(symbol)
            
            if price_info:
                # KIS API 응답을 표준 형식으로 변환
                return {
                    'symbol': symbol,
                    'current_price': price_info.get('current_price', 0),
                    'open_price': price_info.get('open_price', 0),
                    'high_price': price_info.get('high_price', 0),
                    'low_price': price_info.get('low_price', 0),
                    'volume': price_info.get('volume', 0),
                    'market_cap': price_info.get('market_cap', 0),
                    'high_52w': price_info.get('w52_high', 0),
                    'low_52w': price_info.get('w52_low', 0),
                    'per': price_info.get('per', 0),
                    'pbr': price_info.get('pbr', 0),
                    'eps': price_info.get('eps', 0),
                    'bps': price_info.get('bps', 0),
                    'change_rate': price_info.get('change_rate', 0),
                    'trading_value': price_info.get('trading_value', 0)
                }
            else:
                # API 호출 실패시 빈 데이터 반환
                return {}
                
        except Exception as e:
            logging.error(f"KIS API 가격 데이터 조회 실패 [{symbol}]: {e}")
            return {}
    
    def get_sector_data(self, sector: str) -> Dict[str, Any]:
        """섹터 데이터 조회"""
        try:
            normalized_sector = str(sector or '').strip() or '기타'

            if normalized_sector in self._sector_metrics:
                return self._sector_metrics[normalized_sector]

            # 캐시 확인
            cache_key = f"sector_data_{normalized_sector}"
            if self.cache:
                cached_data = self.cache.get(cache_key)
                if cached_data:
                    self._sector_metrics[normalized_sector] = cached_data
                    return cached_data
            
            # API 호출 (실제 구현 필요)
            sector_data = self._fetch_sector_data_from_api(normalized_sector)
            
            # 캐시 저장
            if self.cache and sector_data:
                self.cache.set(cache_key, sector_data, ttl=self.cache_ttl)
            
            if sector_data:
                self._sector_metrics[normalized_sector] = sector_data

            return sector_data
            
        except Exception as e:
            logging.error(f"섹터 데이터 조회 실패 [{sector}]: {e}")
            return {}
    
    def refresh_sector_statistics(self, stocks: List[Dict[str, Any]]) -> None:
        """주어진 종목 데이터로 섹터 통계를 갱신합니다."""
        sectors: Dict[str, List[Tuple[float, float, float]]] = {}

        for entry in stocks:
            sector_name = str(entry.get('sector') or '').strip() or '기타'
            per = DataValidator.safe_float_optional(entry.get('per'))
            pbr = DataValidator.safe_float_optional(entry.get('pbr'))
            roe = DataValidator.safe_float_optional(entry.get('roe'))

            if per is None and pbr is None and roe is None:
                continue

            sectors.setdefault(sector_name, []).append((per, pbr, roe))

        for sector_name, tuples in sectors.items():
            metrics = self._calculate_sector_metrics(sector_name, tuples)
            if metrics:
                cache_key = f"sector_data_{sector_name}"
                self._sector_metrics[sector_name] = metrics
                if self.cache:
                    self.cache.set(cache_key, metrics, ttl=self.cache_ttl)

    def _calculate_sector_metrics(self, sector: str, tuples: List[Tuple[Optional[float], Optional[float], Optional[float]]]) -> Dict[str, Any]:
        filtered_per = [t[0] for t in tuples if t[0] is not None and t[0] > 0]
        filtered_pbr = [t[1] for t in tuples if t[1] is not None and t[1] > 0]
        filtered_roe = [t[2] for t in tuples if t[2] is not None]

        if len(filtered_per) < 3 and len(filtered_pbr) < 3 and len(filtered_roe) < 3:
            return {}

        def _percentiles(values: List[float]) -> Dict[str, float]:
            if not values:
                return {'p25': 0.0, 'p50': 0.0, 'p75': 0.0}
            sorted_vals = sorted(values)
            n = len(sorted_vals)
            p25_index = max(0, int(0.25 * (n - 1)))
            p50 = median(sorted_vals)
            p75_index = min(n - 1, int(0.75 * (n - 1)))
            return {
                'p25': float(sorted_vals[p25_index]),
                'p50': float(p50),
                'p75': float(sorted_vals[p75_index])
            }

        per_percentiles = _percentiles(filtered_per)
        pbr_percentiles = _percentiles(filtered_pbr)
        roe_percentiles = _percentiles(filtered_roe)

        avg_pe = per_percentiles['p50'] or 20.0
        avg_pb = pbr_percentiles['p50'] or 2.0
        avg_roe = roe_percentiles['p50'] or 10.0

        return {
            'sector': sector,
            'avg_pe_ratio': avg_pe,
            'avg_pb_ratio': avg_pb,
            'avg_roe': avg_roe,
            'per_percentiles': per_percentiles,
            'pbr_percentiles': pbr_percentiles,
            'roe_percentiles': roe_percentiles,
            'sample_size': len(tuples),
            'valuation_score': min(100.0, max(0.0, avg_roe + 40.0)),
            'updated_at': datetime.utcnow().isoformat() + 'Z'
        }

    def _fetch_sector_data_from_api(self, sector: str) -> Dict[str, Any]:
        """API에서 섹터 데이터 조회"""

        # NOTE: 실제 KIS API 제공 여부와 무관하게 기본 통계값을 제공한다.
        #       업종별 평균과 분포 추정을 통해 상대 평가에 활용할 수 있도록 구성.

        normalized_sector = str(sector or '').strip() or '기타'

        sector_defaults = {
            '금융업': {'pe': 9.5, 'pb': 0.85, 'roe': 0.11, 'roe_spread': 0.04},
            '기술업': {'pe': 28.0, 'pb': 3.8, 'roe': 0.14, 'roe_spread': 0.06},
            '제조업': {'pe': 15.0, 'pb': 1.8, 'roe': 0.12, 'roe_spread': 0.05},
            '바이오/제약': {'pe': 45.0, 'pb': 6.5, 'roe': 0.09, 'roe_spread': 0.08},
            '에너지/화학': {'pe': 13.0, 'pb': 1.3, 'roe': 0.10, 'roe_spread': 0.05},
            '소비재': {'pe': 18.0, 'pb': 2.4, 'roe': 0.13, 'roe_spread': 0.05},
            '통신업': {'pe': 12.0, 'pb': 1.6, 'roe': 0.10, 'roe_spread': 0.03},
            '건설업': {'pe': 11.0, 'pb': 1.1, 'roe': 0.09, 'roe_spread': 0.04},
            '기타': {'pe': 20.0, 'pb': 2.0, 'roe': 0.12, 'roe_spread': 0.05},
        }

        defaults = sector_defaults.get(normalized_sector, sector_defaults['기타'])

        avg_pe = float(defaults['pe'])
        avg_pb = float(defaults['pb'])
        avg_roe = float(defaults['roe'])
        roe_spread = float(defaults['roe_spread'])

        def _estimate_percentiles(avg: float, low_factor: float = 0.8, high_factor: float = 1.2) -> Dict[str, float]:
            return {
                'p25': max(0.0, avg * low_factor),
                'p50': avg,
                'p75': avg * high_factor
            }

        per_percentiles = _estimate_percentiles(avg_pe)
        pbr_percentiles = _estimate_percentiles(avg_pb)

        roe_percentiles = {
            'p25': max(0.0, (avg_roe - roe_spread) * 100.0),
            'p50': avg_roe * 100.0,
            'p75': (avg_roe + roe_spread) * 100.0
        }

        valuation_score = min(100.0, max(0.0, (avg_roe * 100.0) + 40.0))

        return {
            'sector': normalized_sector,
            'avg_pe_ratio': avg_pe,
            'avg_pb_ratio': avg_pb,
            'avg_roe': avg_roe * 100.0,
            'avg_roa': avg_roe * 0.7 * 100.0,
            'avg_debt_to_equity': 0.5,
            'sector_growth_rate': 0.05,
            'sector_volatility': 0.25,
            'per_percentiles': per_percentiles,
            'pbr_percentiles': pbr_percentiles,
            'roe_percentiles': roe_percentiles,
            'sample_size': 0,
            'valuation_score': min(valuation_score, 30.0),
            'updated_at': datetime.utcnow().isoformat() + 'Z',
            'synthetic': True
        }
    
    def batch_get_financial_data(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """여러 종목의 재무 데이터 일괄 조회"""
        try:
            results = {}
            
            for symbol in symbols:
                try:
                    data = self.get_financial_data(symbol)
                    if data:
                        results[symbol] = data
                except Exception as e:
                    logging.warning(f"종목 {symbol} 재무 데이터 조회 실패: {e}")
                    results[symbol] = {}
            
            return results
            
        except Exception as e:
            logging.error(f"일괄 재무 데이터 조회 실패: {e}")
            return {}
    
    def get_data_quality_score(self, data: Dict[str, Any]) -> float:
        """데이터 품질 점수 계산 (0~100)"""
        try:
            if not data:
                return 0.0
            
            # 필수 필드 존재 여부 확인
            required_fields = ['revenue', 'net_income', 'total_assets', 'eps']
            missing_fields = sum(1 for field in required_fields if field not in data or data[field] is None)
            
            # 필드 완성도 점수
            completeness_score = (len(required_fields) - missing_fields) / len(required_fields) * 100
            
            # 데이터 유효성 점수 (0보다 큰 값들의 비율)
            numeric_fields = ['revenue', 'net_income', 'total_assets', 'eps', 'pe_ratio', 'pb_ratio']
            valid_fields = sum(1 for field in numeric_fields 
                             if field in data and isinstance(data[field], (int, float)) and data[field] > 0)
            
            validity_score = valid_fields / len(numeric_fields) * 100
            
            # 전체 품질 점수 (완성도 70%, 유효성 30%)
            quality_score = completeness_score * 0.7 + validity_score * 0.3
            
            return min(100, max(0, quality_score))
            
        except Exception as e:
            logging.warning(f"데이터 품질 점수 계산 실패: {e}")
            return 0.0
    
    def is_data_fresh(self, data: Dict[str, Any], max_age_hours: int = 24) -> bool:
        """데이터 신선도 확인"""
        try:
            if 'timestamp' not in data:
                return False
            
            import datetime
            data_time = data['timestamp']
            current_time = datetime.datetime.now()
            
            age_hours = (current_time - data_time).total_seconds() / 3600
            
            return age_hours <= max_age_hours
            
        except Exception as e:
            logging.warning(f"데이터 신선도 확인 실패: {e}")
            return False
    
    def clear_cache(self, pattern: str = None):
        """캐시 삭제"""
        try:
            if self.cache:
                if pattern:
                    self.cache.clear_pattern(pattern)
                else:
                    self.cache.clear()
                logging.info(f"캐시 삭제 완료: {pattern or '전체'}")
        except Exception as e:
            logging.warning(f"캐시 삭제 실패: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
        try:
            if self.cache:
                return self.cache.get_stats()
            else:
                return {'cache_enabled': False}
        except Exception as e:
            logging.warning(f"캐시 통계 조회 실패: {e}")
            return {'error': str(e)}



