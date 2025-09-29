# price_display_enhancer.py
"""
가격 표시 강화 모듈
- 현재가 및 52주 위치 정보를 더 상세하게 표시
- 가격 변동률 및 기술적 분석 정보 제공
- 시각적 가격 차트 및 위치 표시
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PriceDisplayEnhancer:
    """가격 표시 강화 클래스"""
    
    def __init__(self):
        self.price_ranges = {
            'very_low': (0, 20),      # 매우 저위치
            'low': (20, 40),          # 저위치
            'medium_low': (40, 60),   # 중하위치
            'medium_high': (60, 80),  # 중상위치
            'high': (80, 100)         # 고위치
        }
    
    def format_price(self, price: Optional[float]) -> str:
        """가격을 읽기 쉬운 형태로 포맷팅"""
        if price is None or price <= 0:
            return "N/A"
        
        if price >= 100000:  # 10만원 이상
            return f"{price/10000:,.1f}만원"
        elif price >= 10000:  # 1만원 이상
            return f"{price/1000:,.0f}천원"
        else:
            return f"{price:,.0f}원"
    
    def format_market_cap(self, market_cap: Optional[float]) -> str:
        """시가총액을 읽기 쉬운 형태로 포맷팅"""
        if market_cap is None or market_cap <= 0:
            return "N/A"
        
        if market_cap >= 100000:  # 10조원 이상
            return f"{market_cap/100000:,.1f}십조원"
        elif market_cap >= 10000:  # 1조원 이상
            return f"{market_cap/10000:,.1f}조원"
        else:
            return f"{market_cap:,.0f}억원"
    
    def calculate_price_position(self, current_price: float, w52_high: float, w52_low: float) -> Tuple[float, str, str]:
        """52주 위치 계산 및 분석"""
        if not all([current_price, w52_high, w52_low]) or w52_high <= w52_low:
            return 0.0, "N/A", "데이터 부족"
        
        position = ((current_price - w52_low) / (w52_high - w52_low)) * 100
        position = max(0, min(100, position))  # 0-100% 범위로 제한
        
        # 위치별 분석
        if position >= 80:
            level = "고위치"
            analysis = "52주 고가 근처 - 매도 고려"
        elif position >= 60:
            level = "중상위"
            analysis = "52주 중상위 - 신중한 접근"
        elif position >= 40:
            level = "중하위"
            analysis = "52주 중하위 - 적정 수준"
        else:
            level = "저위치"
            analysis = "52주 저가 근처 - 매수 기회"
        
        return position, level, analysis
    
    def calculate_price_change_rate(self, current_price: float, w52_high: float, w52_low: float) -> Dict[str, Any]:
        """가격 변동률 계산"""
        if not all([current_price, w52_high, w52_low]):
            return {"high_change": "N/A", "low_change": "N/A", "range": "N/A"}
        
        high_change = ((current_price - w52_high) / w52_high) * 100
        low_change = ((current_price - w52_low) / w52_low) * 100
        range_size = ((w52_high - w52_low) / w52_low) * 100
        
        return {
            "high_change": f"{high_change:+.1f}%",
            "low_change": f"{low_change:+.1f}%",
            "range": f"{range_size:.1f}%"
        }
    
    def create_price_visualization(self, current_price: float, w52_high: float, w52_low: float, width: int = 20) -> str:
        """가격 위치 시각화"""
        if not all([current_price, w52_high, w52_low]) or w52_high <= w52_low:
            return "데이터 부족"
        
        position = ((current_price - w52_low) / (w52_high - w52_low)) * 100
        position = max(0, min(100, position))
        
        # 시각화 생성
        current_pos = int((position / 100) * width)
        visualization = "[" + "=" * current_pos + "●" + "=" * (width - current_pos - 1) + "]"
        
        return f"{visualization} {position:.0f}%"
    
    def get_technical_analysis(self, current_price: float, w52_high: float, w52_low: float) -> Dict[str, str]:
        """기술적 분석 정보"""
        if not all([current_price, w52_high, w52_low]) or w52_high <= w52_low:
            return {"trend": "N/A", "support": "N/A", "resistance": "N/A", "recommendation": "N/A"}
        
        position = ((current_price - w52_low) / (w52_high - w52_low)) * 100
        
        # 추세 분석
        if position >= 80:
            trend = "강한 상승 추세"
            recommendation = "매도 고려"
        elif position >= 60:
            trend = "상승 추세"
            recommendation = "신중한 매수"
        elif position >= 40:
            trend = "횡보 추세"
            recommendation = "관망"
        else:
            trend = "하락 추세"
            recommendation = "매수 기회"
        
        # 지지선/저항선
        support = w52_low
        resistance = w52_high
        
        return {
            "trend": trend,
            "support": self.format_price(support),
            "resistance": self.format_price(resistance),
            "recommendation": recommendation
        }
    
    def display_detailed_price_info(self, stock_data: Dict[str, Any]) -> str:
        """상세한 가격 정보 표시"""
        symbol = stock_data.get('symbol', 'N/A')
        name = stock_data.get('name', 'N/A')
        current_price = stock_data.get('current_price')
        w52_high = stock_data.get('w52_high')
        w52_low = stock_data.get('w52_low')
        market_cap = stock_data.get('market_cap')
        
        output = []
        output.append(f"\n[{name} ({symbol}) 상세 가격 정보]")
        output.append("=" * 60)
        
        # 기본 가격 정보
        output.append(f"현재가: {self.format_price(current_price)}")
        output.append(f"52주 최고가: {self.format_price(w52_high)}")
        output.append(f"52주 최저가: {self.format_price(w52_low)}")
        output.append(f"시가총액: {self.format_market_cap(market_cap)}")
        
        if all([current_price, w52_high, w52_low]):
            # 52주 위치 분석
            position, level, analysis = self.calculate_price_position(current_price, w52_high, w52_low)
            output.append(f"\n52주 위치: {level} ({position:.1f}%)")
            output.append(f"분석: {analysis}")
            
            # 가격 변동률
            changes = self.calculate_price_change_rate(current_price, w52_high, w52_low)
            output.append(f"\n가격 변동률:")
            output.append(f"  - 52주 고가 대비: {changes['high_change']}")
            output.append(f"  - 52주 저가 대비: {changes['low_change']}")
            output.append(f"  - 52주 변동폭: {changes['range']}")
            
            # 시각화
            visualization = self.create_price_visualization(current_price, w52_high, w52_low)
            output.append(f"\n가격 위치 시각화:")
            output.append(f"  {visualization}")
            
            # 기술적 분석
            technical = self.get_technical_analysis(current_price, w52_high, w52_low)
            output.append(f"\n기술적 분석:")
            output.append(f"  - 추세: {technical['trend']}")
            output.append(f"  - 지지선: {technical['support']}")
            output.append(f"  - 저항선: {technical['resistance']}")
            output.append(f"  - 추천: {technical['recommendation']}")
        
        output.append("=" * 60)
        return "\n".join(output)
    
    def create_price_summary(self, stocks_data: list) -> str:
        """여러 종목의 가격 요약 정보"""
        if not stocks_data:
            return "표시할 데이터가 없습니다."
        
        output = []
        output.append(f"\n[종목별 가격 요약 ({len(stocks_data)}개 종목)]")
        output.append("=" * 100)
        output.append(f"{'종목명':<15} {'현재가':<12} {'52주위치':<12} {'분석':<20} {'추천':<15}")
        output.append("-" * 100)
        
        for stock in stocks_data:
            name = stock.get('name', 'N/A')[:12]
            current_price = stock.get('current_price')
            w52_high = stock.get('w52_high')
            w52_low = stock.get('w52_low')
            
            price_display = self.format_price(current_price)
            
            if all([current_price, w52_high, w52_low]):
                position, level, analysis = self.calculate_price_position(current_price, w52_high, w52_low)
                technical = self.get_technical_analysis(current_price, w52_high, w52_low)
                recommendation = technical['recommendation']
            else:
                level = "N/A"
                analysis = "데이터 부족"
                recommendation = "N/A"
            
            output.append(f"{name:<15} {price_display:<12} {level:<12} {analysis:<20} {recommendation:<15}")
        
        output.append("=" * 100)
        return "\n".join(output)

# 전역 인스턴스
price_enhancer = PriceDisplayEnhancer()

# 편의 함수들
def format_price(price: Optional[float]) -> str:
    """가격 포맷팅"""
    return price_enhancer.format_price(price)

def format_market_cap(market_cap: Optional[float]) -> str:
    """시가총액 포맷팅"""
    return price_enhancer.format_market_cap(market_cap)

def calculate_price_position(current_price: float, w52_high: float, w52_low: float) -> Tuple[float, str, str]:
    """52주 위치 계산"""
    return price_enhancer.calculate_price_position(current_price, w52_high, w52_low)

def display_detailed_price_info(stock_data: Dict[str, Any]) -> str:
    """상세 가격 정보 표시"""
    return price_enhancer.display_detailed_price_info(stock_data)

def create_price_summary(stocks_data: list) -> str:
    """가격 요약 정보 생성"""
    return price_enhancer.create_price_summary(stocks_data)
