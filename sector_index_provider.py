"""
국내업종 현재지수 API를 활용한 섹터별 실시간 데이터 제공자
KIS API의 국내업종 현재지수[v1_국내주식-063] API를 활용합니다.
"""

import logging
import time
from typing import Dict, List, Optional, Any
import pandas as pd
from datetime import datetime
import requests
import json

logger = logging.getLogger(__name__)

class SectorIndexProvider:
    """국내업종 현재지수 API 제공자"""
    
    def __init__(self, oauth_manager):
        """
        섹터 지수 제공자 초기화 (기존 OAuth 매니저 활용)
        
        Args:
            oauth_manager: 기존 KISOAuthManager 인스턴스
        """
        self.oauth_manager = oauth_manager
        self.base_url = oauth_manager.base_url
        self.app_key = oauth_manager.appkey
        self.app_secret = oauth_manager.appsecret
        
        # 주요 업종 코드 매핑
        self.sector_codes = {
            "0001": "코스피",
            "1001": "코스닥", 
            "2001": "코스피200",
            # 추가 업종 코드들은 KIS API 문서 참조
        }
        
        # API 호출 제한
        self.last_request_time = 0
        self.request_interval = 0.1  # 100ms 간격
    
    def _rate_limit(self):
        """API 요청 속도 제어"""
        elapsed_time = time.time() - self.last_request_time
        if elapsed_time < self.request_interval:
            time.sleep(self.request_interval - elapsed_time)
        self.last_request_time = time.time()
    
    def _to_float(self, value: Any, default: float = 0.0) -> float:
        """안전하게 float 타입으로 변환"""
        if value is None or value == '':
            return default
        try:
            # 쉼표 제거 후 float 변환
            return float(str(value).replace(',', ''))
        except (ValueError, TypeError):
            return default
    
    def _get_authenticated_headers(self) -> Dict[str, str]:
        """인증된 헤더 반환 (기존 토큰 매니저 활용)"""
        # 기존 토큰 매니저에서 토큰 가져오기
        try:
            from kis_token_manager import get_token_manager
            token_manager = get_token_manager()
            token = token_manager.get_valid_token()
            
            if not token:
                raise Exception("토큰 발급 실패")
            
            return {
                "Content-Type": "application/json; charset=utf-8",
                "authorization": f"Bearer {token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "FHPUP02100000",
                "custtype": "P"  # 개인 고객
            }
        except Exception as e:
            logger.error(f"토큰 매니저에서 토큰 가져오기 실패: {e}")
            raise Exception(f"토큰 발급 실패: {e}")
    
    def get_sector_index(self, market_code: str = "0001") -> Optional[Dict[str, Any]]:
        """
        업종 현재지수 조회
        
        Args:
            market_code: 시장 코드 (0001: 코스피, 1001: 코스닥, 2001: 코스피200)
            
        Returns:
            Dict[str, Any]: 업종 지수 데이터
        """
        self._rate_limit()
        
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-index-price"
        headers = self._get_authenticated_headers()
        
        params = {
            "FID_COND_MRKT_DIV_CODE": "U",  # 업종
            "FID_INPUT_ISCD": market_code
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('rt_cd') == '0':  # 성공
                    return self._parse_sector_index_data(data.get('output', {}))
                else:
                    logger.error(f"API 응답 오류: {data.get('msg1', 'Unknown error')}")
                    return None
            else:
                logger.error(f"HTTP 오류: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"업종 지수 조회 중 오류: {e}")
            return None
    
    def _parse_sector_index_data(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """업종 지수 데이터 파싱"""
        try:
            return {
                # 기본 지수 정보
                "market_code": output.get('market_code', ''),
                "current_price": self._to_float(output.get('bstp_nmix_prpr')),
                "change": self._to_float(output.get('bstp_nmix_prdy_vrss')),
                "change_rate": self._to_float(output.get('bstp_nmix_prdy_ctrt')),
                "change_sign": output.get('prdy_vrss_sign', ''),
                
                # 거래량 정보
                "volume": self._to_float(output.get('acml_vol')),
                "prev_volume": self._to_float(output.get('prdy_vol')),
                "trading_value": self._to_float(output.get('acml_tr_pbmn')),
                "prev_trading_value": self._to_float(output.get('prdy_tr_pbmn')),
                
                # 가격 정보
                "open_price": self._to_float(output.get('bstp_nmix_oprc')),
                "high_price": self._to_float(output.get('bstp_nmix_hgpr')),
                "low_price": self._to_float(output.get('bstp_nmix_lwpr')),
                
                # 종목 현황
                "ascending_count": self._to_float(output.get('ascn_issu_cnt')),  # 상승 종목 수
                "limit_up_count": self._to_float(output.get('uplm_issu_cnt')),  # 상한 종목 수
                "unchanged_count": self._to_float(output.get('stnr_issu_cnt')),  # 보합 종목 수
                "descending_count": self._to_float(output.get('down_issu_cnt')),  # 하락 종목 수
                "limit_down_count": self._to_float(output.get('lslm_issu_cnt')),  # 하한 종목 수
                
                # 연중 최고/최저
                "year_high": self._to_float(output.get('dryy_bstp_nmix_hgpr')),
                "year_high_date": output.get('dryy_bstp_nmix_hgpr_date', ''),
                "year_low": self._to_float(output.get('dryy_bstp_nmix_lwpr')),
                "year_low_date": output.get('dryy_bstp_nmix_lwpr_date', ''),
                "year_high_ratio": self._to_float(output.get('dryy_hgpr_vrss_prpr_rate')),
                "year_low_ratio": self._to_float(output.get('dryy_lwpr_vrss_prpr_rate')),
                
                # 호가 정보
                "total_ask_quantity": self._to_float(output.get('total_askp_rsqn')),
                "total_bid_quantity": self._to_float(output.get('total_bidp_rsqn')),
                "ask_ratio": self._to_float(output.get('seln_rsqn_rate')),
                "bid_ratio": self._to_float(output.get('shnu_rsqn_rate')),
                "net_buy_quantity": self._to_float(output.get('ntby_rsqn')),
                
                # 메타데이터
                "timestamp": datetime.now().isoformat(),
                "market_name": self.sector_codes.get(output.get('market_code', ''), 'Unknown')
            }
            
        except Exception as e:
            logger.error(f"섹터 지수 데이터 파싱 중 오류: {e}")
            return {}
    
    def get_multiple_sector_indices(self, market_codes: List[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        여러 업종의 현재지수를 일괄 조회
        
        Args:
            market_codes: 조회할 시장 코드 리스트 (기본값: 코스피, 코스닥, 코스피200)
            
        Returns:
            Dict[str, Dict[str, Any]]: 시장 코드별 지수 데이터
        """
        if market_codes is None:
            market_codes = ["0001", "1001", "2001"]  # 코스피, 코스닥, 코스피200
        
        results = {}
        
        for market_code in market_codes:
            try:
                index_data = self.get_sector_index(market_code)
                if index_data:
                    results[market_code] = index_data
                    logger.info(f"업종 지수 조회 성공: {market_code} ({index_data.get('market_name', 'Unknown')})")
                else:
                    logger.warning(f"업종 지수 조회 실패: {market_code}")
                
                # API 호출 간격 조절
                time.sleep(0.2)
                
            except Exception as e:
                logger.error(f"업종 {market_code} 조회 중 오류: {e}")
                continue
        
        return results
    
    def get_sector_performance_summary(self, market_codes: List[str] = None) -> pd.DataFrame:
        """
        업종별 성과 요약 DataFrame 생성
        
        Args:
            market_codes: 조회할 시장 코드 리스트
            
        Returns:
            pd.DataFrame: 업종별 성과 요약
        """
        indices_data = self.get_multiple_sector_indices(market_codes)
        
        if not indices_data:
            return pd.DataFrame()
        
        summary_data = []
        
        for market_code, data in indices_data.items():
            summary_data.append({
                "시장": data.get('market_name', market_code),
                "현재지수": f"{data.get('current_price', 0):,.2f}",
                "전일대비": f"{data.get('change', 0):+,.2f}",
                "등락률": f"{data.get('change_rate', 0):+.2f}%",
                "거래량": f"{data.get('volume', 0):,.0f}",
                "거래대금": f"{data.get('trading_value', 0):,.0f}",
                "상승종목": int(data.get('ascending_count', 0)),
                "하락종목": int(data.get('descending_count', 0)),
                "보합종목": int(data.get('unchanged_count', 0)),
                "상한종목": int(data.get('limit_up_count', 0)),
                "하한종목": int(data.get('limit_down_count', 0)),
                "연중최고": f"{data.get('year_high', 0):,.2f}",
                "연중최저": f"{data.get('year_low', 0):,.2f}",
                "매수비율": f"{data.get('bid_ratio', 0):.1f}%",
                "매도비율": f"{data.get('ask_ratio', 0):.1f}%"
            })
        
        return pd.DataFrame(summary_data)
    
    def get_market_sentiment(self, market_code: str = "0001") -> Dict[str, Any]:
        """
        시장 심리 분석
        
        Args:
            market_code: 시장 코드
            
        Returns:
            Dict[str, Any]: 시장 심리 분석 결과
        """
        index_data = self.get_sector_index(market_code)
        
        if not index_data:
            return {}
        
        # 종목 현황 기반 심리 분석
        total_stocks = (
            index_data.get('ascending_count', 0) +
            index_data.get('descending_count', 0) +
            index_data.get('unchanged_count', 0)
        )
        
        if total_stocks > 0:
            ascending_ratio = index_data.get('ascending_count', 0) / total_stocks * 100
            descending_ratio = index_data.get('descending_count', 0) / total_stocks * 100
            unchanged_ratio = index_data.get('unchanged_count', 0) / total_stocks * 100
        else:
            ascending_ratio = descending_ratio = unchanged_ratio = 0
        
        # 매수/매도 비율
        bid_ratio = index_data.get('bid_ratio', 0)
        ask_ratio = index_data.get('ask_ratio', 0)
        
        # 심리 점수 계산 (0-100)
        sentiment_score = (
            ascending_ratio * 0.4 +  # 상승 종목 비율
            bid_ratio * 0.3 +        # 매수 비율
            (100 - descending_ratio) * 0.3  # 하락 종목 비율 (역산)
        ) / 2
        
        # 심리 상태 분류
        if sentiment_score >= 70:
            sentiment = "매우 강세"
        elif sentiment_score >= 60:
            sentiment = "강세"
        elif sentiment_score >= 50:
            sentiment = "보합"
        elif sentiment_score >= 40:
            sentiment = "약세"
        else:
            sentiment = "매우 약세"
        
        return {
            "market_code": market_code,
            "market_name": index_data.get('market_name', 'Unknown'),
            "sentiment_score": round(sentiment_score, 1),
            "sentiment": sentiment,
            "ascending_ratio": round(ascending_ratio, 1),
            "descending_ratio": round(descending_ratio, 1),
            "unchanged_ratio": round(unchanged_ratio, 1),
            "bid_ratio": bid_ratio,
            "ask_ratio": ask_ratio,
            "change_rate": index_data.get('change_rate', 0),
            "timestamp": datetime.now().isoformat()
        }

# 테스트 함수
def test_sector_index_provider():
    """섹터 지수 제공자 테스트"""
    try:
        import yaml
        from mcp_kis_integration import MCPKISIntegration
        
        # 설정 로드
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # MCP 초기화
        mcp = MCPKISIntegration({
            'app_key': config.get('kis_api', {}).get('app_key', ''),
            'app_secret': config.get('kis_api', {}).get('app_secret', ''),
            'test_mode': config.get('kis_api', {}).get('test_mode', True)
        })
        
        if not mcp.get_access_token():
            print("FAILED: OAuth 토큰 발급 실패")
            return
        
        # 섹터 지수 제공자 초기화 (기존 OAuth 매니저 활용)
        from value_stock_finder import KISOAuthManager
        oauth_manager = KISOAuthManager(
            appkey=config.get('kis_api', {}).get('app_key', ''),
            appsecret=config.get('kis_api', {}).get('app_secret', ''),
            is_test=config.get('kis_api', {}).get('test_mode', True)
        )
        
        sector_provider = SectorIndexProvider(oauth_manager)
        
        print("=== 섹터 지수 제공자 테스트 ===")
        
        # 코스피 지수 조회
        print("1. 코스피 지수 조회")
        kospi_data = sector_provider.get_sector_index("0001")
        if kospi_data:
            print(f"SUCCESS: 코스피 - {kospi_data.get('current_price', 0):,.2f} ({kospi_data.get('change_rate', 0):+.2f}%)")
        else:
            print("FAILED: 코스피 지수 조회 실패")
        
        # 여러 업종 조회
        print("\n2. 여러 업종 조회")
        multiple_data = sector_provider.get_multiple_sector_indices(["0001", "1001", "2001"])
        print(f"SUCCESS: {len(multiple_data)}개 업종 조회 완료")
        
        # 성과 요약
        print("\n3. 업종별 성과 요약")
        summary_df = sector_provider.get_sector_performance_summary()
        if not summary_df.empty:
            print(summary_df.to_string(index=False))
        
        # 시장 심리 분석
        print("\n4. 시장 심리 분석")
        sentiment = sector_provider.get_market_sentiment("0001")
        if sentiment:
            print(f"SUCCESS: {sentiment.get('market_name')} - {sentiment.get('sentiment')} ({sentiment.get('sentiment_score', 0)}점)")
        
        print("\n=== 테스트 완료 ===")
        
    except Exception as e:
        print(f"FAILED: 테스트 실행 중 오류: {e}")

if __name__ == "__main__":
    test_sector_index_provider()
