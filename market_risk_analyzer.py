#!/usr/bin/env python3
"""
시장 리스크 분석기 - 현재가 위치와 리스크를 자동으로 분석하여 투자 권장에 반영
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

logger = logging.getLogger(__name__)
console = Console()

class MarketRiskAnalyzer:
    """시장 리스크 분석기"""
    
    def __init__(self, kis_provider):
        self.provider = kis_provider
        self._kospi_index = None
    
    def _to_float(self, x, default=0.0):
        """안전한 float 변환"""
        try:
            v = float(x)
            return v if v == v else default  # NaN 체크
        except Exception:
            return default
    
    def _clamp(self, x, lo=0.0, hi=100.0):
        """값을 지정된 범위로 클램프"""
        try:
            return max(lo, min(hi, float(x)))
        except Exception:
            return None
    
    def _ensure_kospi_index(self):
        """KOSPI 인덱스 캐시 초기화 (한 번만)"""
        if self._kospi_index is None:
            try:
                from enhanced_integrated_analyzer import EnhancedIntegratedAnalyzer
                analyzer = EnhancedIntegratedAnalyzer()
                self._kospi_index = getattr(analyzer, "_kospi_index", {}) or {}
            except Exception:
                self._kospi_index = {}
        
    def analyze_stock_risk(self, symbol: str) -> Dict[str, Any]:
        """개별 종목의 시장 리스크 분석"""
        
        try:
            # 현재가 정보 가져오기
            price_info = self.provider.get_stock_price_info(symbol)
            
            if not price_info:
                return self._create_default_risk_profile(symbol)
            
            current_price = self._to_float(price_info.get('current_price'))
            w52_high = price_info['w52_high']
            w52_low = price_info['w52_low']
            per = self._to_float(price_info.get('per'))
            pbr = self._to_float(price_info.get('pbr'))
            change_rate = self._to_float(price_info.get('change_rate'))
            foreign_net_buy = self._to_float(price_info.get('foreign_net_buy'))
            program_net_buy = self._to_float(price_info.get('program_net_buy'))
            
            # 현재가 위치 계산 (안전 가드 적용)
            try:
                if w52_high is None or w52_low is None or float(w52_high) <= float(w52_low):
                    price_position = None
                else:
                    price_position = self._clamp(((float(current_price) - float(w52_low)) /
                                                 (float(w52_high) - float(w52_low))) * 100)
            except Exception:
                price_position = None
            
            # 외국인 동향 트렌드 분석
            foreign_trend = self._analyze_foreign_trend(symbol, foreign_net_buy)
            
            # 리스크 점수 계산 (외국인 트렌드 반영)
            risk_score = self._calculate_risk_score(
                price_position, per, pbr, change_rate, 
                foreign_net_buy, program_net_buy, foreign_trend
            )
            
            # 리스크 등급 결정
            risk_grade = self._determine_risk_grade(risk_score)
            
            # 투자 권장 결정 (외국인 트렌드 고려)
            recommendation = self._determine_recommendation(risk_score, price_position, per, foreign_trend)
            
            # 조정 계수 계산 (백테스팅 결과에 적용할 가중치)
            adjustment_factor = self._calculate_adjustment_factor(risk_score, price_position, per)
            
            # 종목명 가져오기
            stock_name = self._get_stock_name(symbol)
            
            return {
                'symbol': symbol,
                'stock_name': stock_name,
                'current_price': current_price,
                'price_position': price_position,
                'risk_score': risk_score,
                'risk_grade': risk_grade,
                'recommendation': recommendation,
                'adjustment_factor': adjustment_factor,
                'price_info': price_info,
                'foreign_trend': foreign_trend,  # 외국인 트렌드 정보 추가
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing stock risk for {symbol}: {e}")
            return self._create_default_risk_profile(symbol)
    
    def _calculate_risk_score(self, price_position: float, per: float, pbr: float, 
                            change_rate: float, foreign_net_buy: float, 
                            program_net_buy: float, foreign_trend: Dict[str, Any] = None) -> int:
        """리스크 점수 계산 (0-10, 높을수록 위험)"""
        
        risk_score = 0
        
        # 현재가 위치 리스크 (0-4점) - 52주 최고가 근처는 높은 리스크
        pp = price_position if isinstance(price_position, (int, float)) else 50.0
        if pp > 95:
            risk_score += 4  # 52주 최고가 근처는 매우 높은 리스크
        elif pp > 90:
            risk_score += 3
        elif pp > 80:
            risk_score += 2
        elif pp > 60:
            risk_score += 1
        
        # 밸류에이션 리스크 (0-3점) - 수익성 부진 고려
        if per < 0:  # 적자 기업
            risk_score += 3  # 적자 기업은 높은 리스크
        elif per > 25:
            risk_score += 2
        elif per > 20:
            risk_score += 1
        elif per < 8:
            risk_score -= 1  # 저평가 시 리스크 감소
        
        # PBR 리스크 (0-2점)
        if pbr > 3:
            risk_score += 2
        elif pbr > 2:
            risk_score += 1
        elif pbr < 0.8:
            risk_score -= 1  # 저평가 시 리스크 감소
        
        # 당일 변동성 리스크 (0-1점)
        if abs(change_rate) > 10:
            risk_score += 1
        
        # 외국인 매매 리스크 (0-3점) - 규모별 차등 반영
        if foreign_net_buy < -500000:  # 초대량 매도
            risk_score += 3
        elif foreign_net_buy < -200000:  # 대량 매도
            risk_score += 2
        elif foreign_net_buy < -100000:  # 중량 매도
            risk_score += 1
        elif foreign_net_buy > 200000:  # 대량 매수 (안정성 증가)
            risk_score -= 1
        
        # 외국인 트렌드 리스크 (0-2점) - 연속성 고려
        if foreign_trend:
            if foreign_trend.get('consecutive_selling_days', 0) >= 3:
                risk_score += 2  # 연속 3일 이상 매도
            elif foreign_trend.get('consecutive_selling_days', 0) >= 2:
                risk_score += 1  # 연속 2일 매도
            elif foreign_trend.get('consecutive_buying_days', 0) >= 3:
                risk_score -= 1  # 연속 3일 이상 매수 (안정성 증가)
        
        # 프로그램 매매 리스크 (0-2점)
        if program_net_buy is not None:
            if program_net_buy < -200000:  # 초대량 프로그램 매도
                risk_score += 2
            elif program_net_buy > 200000:  # 초대량 프로그램 매수
                risk_score -= 1
        
        return max(0, min(10, risk_score))  # 0-10 범위로 제한
    
    def _analyze_foreign_trend(self, symbol: str, current_foreign_net_buy: float) -> Dict[str, Any]:
        """외국인 투자자 동향 트렌드 분석"""
        try:
            # 최근 5일간의 외국인 매매 데이터 분석
            price_history = self.provider.get_daily_price_history(symbol, 5)
            
            if price_history is None or price_history.empty:
                return {
                    'consecutive_selling_days': 0,
                    'consecutive_buying_days': 0,
                    'trend_strength': 'neutral',
                    'recent_activity': 'unknown'
                }
            
            # 외국인 매매 데이터 추출 (컬럼명 확인 필요)
            foreign_data = []
            for _, row in price_history.iterrows():
                # 외국인 매매 데이터 컬럼 찾기
                foreign_col = None
                for col in price_history.columns:
                    if 'foreign' in col.lower() or '외국인' in col:
                        foreign_col = col
                        break
                
                if foreign_col and foreign_col in price_history.columns:
                    try:
                        foreign_data.append(float(row[foreign_col] or 0))
                    except Exception:
                        foreign_data.append(0.0)
                else:
                    foreign_data.append(0.0)
            
            # 연속 매도/매수 일수 계산
            consecutive_selling = 0
            consecutive_buying = 0
            
            for i in range(len(foreign_data) - 1, -1, -1):  # 최근부터 역순
                if foreign_data[i] < -50000:  # 5만주 이상 매도
                    consecutive_selling += 1
                    consecutive_buying = 0
                elif foreign_data[i] > 50000:  # 5만주 이상 매수
                    consecutive_buying += 1
                    consecutive_selling = 0
                else:
                    break
            
            # 트렌드 강도 분석
            total_selling = sum(1 for x in foreign_data if x < -50000)
            total_buying = sum(1 for x in foreign_data if x > 50000)
            
            if total_selling >= 3:
                trend_strength = 'strong_selling'
            elif total_selling >= 2:
                trend_strength = 'moderate_selling'
            elif total_buying >= 3:
                trend_strength = 'strong_buying'
            elif total_buying >= 2:
                trend_strength = 'moderate_buying'
            else:
                trend_strength = 'neutral'
            
            # 최근 활동 분석
            if current_foreign_net_buy < -100000:
                recent_activity = 'heavy_selling'
            elif current_foreign_net_buy < -50000:
                recent_activity = 'moderate_selling'
            elif current_foreign_net_buy > 100000:
                recent_activity = 'heavy_buying'
            elif current_foreign_net_buy > 50000:
                recent_activity = 'moderate_buying'
            else:
                recent_activity = 'neutral'
            
            return {
                'consecutive_selling_days': consecutive_selling,
                'consecutive_buying_days': consecutive_buying,
                'trend_strength': trend_strength,
                'recent_activity': recent_activity,
                'total_selling_days': total_selling,
                'total_buying_days': total_buying
            }
            
        except Exception as e:
            logger.debug(f"외국인 트렌드 분석 실패 {symbol}: {e}")
            return {
                'consecutive_selling_days': 0,
                'consecutive_buying_days': 0,
                'trend_strength': 'neutral',
                'recent_activity': 'unknown'
            }
    
    def _determine_risk_grade(self, risk_score: int) -> str:
        """리스크 등급 결정"""
        if risk_score >= 8:
            return "매우 높음"
        elif risk_score >= 6:
            return "높음"
        elif risk_score >= 4:
            return "중간"
        elif risk_score >= 2:
            return "낮음"
        else:
            return "매우 낮음"
    
    def _determine_recommendation(self, risk_score: int, price_position: float, per: float = 0, foreign_trend: Dict[str, Any] = None) -> str:
        """투자 권장 결정 (외국인 동향 고려)"""
        
        # price_position 안전 가드
        pp = price_position if isinstance(price_position, (int, float)) else 50.0
        
        # 기본 권장 결정
        if risk_score >= 8:
            base_recommendation = "매도 고려"
        elif risk_score >= 6:
            base_recommendation = "신중한 접근"
        elif risk_score >= 4:
            if per < 0:
                base_recommendation = "신중한 접근"
            elif pp > 90:
                base_recommendation = "신중한 접근"
            else:
                base_recommendation = "적정 투자"
        elif risk_score >= 2:
            if pp > 90:
                base_recommendation = "적정 투자"
            else:
                base_recommendation = "적극 매수"
        else:
            if pp > 90:
                base_recommendation = "적정 투자"
            else:
                base_recommendation = "강력 매수"
        
        # 외국인 동향에 따른 권장 조정
        if foreign_trend:
            consecutive_selling = foreign_trend.get('consecutive_selling_days', 0)
            consecutive_buying = foreign_trend.get('consecutive_buying_days', 0)
            trend_strength = foreign_trend.get('trend_strength', 'neutral')
            recent_activity = foreign_trend.get('recent_activity', 'neutral')
            
            # 외국인 연속 매도 시 권장 강화
            if consecutive_selling >= 3:
                if base_recommendation in ["적극 매수", "강력 매수"]:
                    return "신중한 접근"
                elif base_recommendation == "적정 투자":
                    return "신중한 접근"
                elif base_recommendation == "신중한 접근":
                    return "매도 고려"
            elif consecutive_selling >= 2:
                if base_recommendation in ["적극 매수", "강력 매수"]:
                    return "적정 투자"
                elif base_recommendation == "적정 투자":
                    return "신중한 접근"
            
            # 외국인 연속 매수 시 권장 강화
            elif consecutive_buying >= 3:
                if base_recommendation == "신중한 접근":
                    return "적정 투자"
                elif base_recommendation == "적정 투자":
                    return "적극 매수"
                elif base_recommendation == "적극 매수":
                    return "강력 매수"
            elif consecutive_buying >= 2:
                if base_recommendation == "신중한 접근":
                    return "적정 투자"
                elif base_recommendation == "적정 투자":
                    return "적극 매수"
            
            # 강한 매도 트렌드 시 권장 강화
            if trend_strength == 'strong_selling':
                if base_recommendation in ["적극 매수", "강력 매수"]:
                    return "신중한 접근"
                elif base_recommendation == "적정 투자":
                    return "신중한 접근"
            elif trend_strength == 'strong_buying':
                if base_recommendation == "신중한 접근":
                    return "적정 투자"
                elif base_recommendation == "적정 투자":
                    return "적극 매수"
            
            # 최근 대량 매도/매수 활동 고려
            if recent_activity == 'heavy_selling':
                if base_recommendation in ["적극 매수", "강력 매수"]:
                    return "신중한 접근"
                elif base_recommendation == "적정 투자":
                    return "신중한 접근"
            elif recent_activity == 'heavy_buying':
                if base_recommendation == "신중한 접근":
                    return "적정 투자"
                elif base_recommendation == "적정 투자":
                    return "적극 매수"
        
        return base_recommendation
    
    def _calculate_adjustment_factor(self, risk_score: int, price_position: float, per: float = 0) -> float:
        """백테스팅 결과 조정 계수 계산 (0.3-1.5)"""
        
        # price_position 안전 가드
        pp = price_position if isinstance(price_position, (int, float)) else 50.0
        
        # 기본 조정 계수
        base_factor = 1.0
        
        # 리스크 점수에 따른 조정
        if risk_score >= 8:
            base_factor *= 0.4  # 매우 위험한 경우 60% 할인
        elif risk_score >= 6:
            base_factor *= 0.6  # 위험한 경우 40% 할인
        elif risk_score >= 4:
            base_factor *= 0.8  # 중간 위험 시 20% 할인
        elif risk_score >= 2:
            base_factor *= 1.0   # 낮은 위험 시 그대로
        else:
            base_factor *= 1.2   # 매우 낮은 위험 시 20% 프리미엄
        
        # 현재가 위치에 따른 추가 조정
        if pp > 90:
            base_factor *= 0.7  # 최고가 근처 시 추가 할인
        elif pp > 80:
            base_factor *= 0.85  # 높은 위치 시 할인
        
        # 수익성 부진 추가 조정
        if per < 0:  # 적자 기업
            base_factor *= 0.6  # 적자 기업은 추가 40% 할인
        elif per > 30:  # 매우 고평가
            base_factor *= 0.8  # 고평가 시 추가 20% 할인
        
        return max(0.2, min(1.5, base_factor))  # 0.2-1.5 범위로 제한
    
    def _create_default_risk_profile(self, symbol: str = "UNKNOWN") -> Dict[str, Any]:
        """기본 리스크 프로필 생성"""
        return {
            'symbol': symbol,
            'current_price': 0,
            'price_position': 50,
            'risk_score': 5,
            'risk_grade': '중간',
            'recommendation': '신중한 접근',
            'adjustment_factor': 0.8,
            'price_info': {},
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def _get_stock_name(self, symbol: str) -> str:
        """종목 코드로부터 종목명 가져오기"""
        try:
            # KOSPI 마스터 데이터에서 종목명 찾기 (캐시된 인덱스 사용)
            self._ensure_kospi_index()
            if symbol in self._kospi_index:
                stock_info = self._kospi_index[symbol]
                # Pandas 객체에서 한글명 가져오기
                if hasattr(stock_info, '한글명'):
                    return stock_info.한글명
                elif hasattr(stock_info, '__getattr__'):
                    try:
                        return getattr(stock_info, '한글명', '')
                    except:
                        pass
            
            # 하드코딩된 주요 종목명 (백업)
            stock_names = {
                '005930': '삼성전자',
                '000660': 'SK하이닉스',
                '373220': 'LG에너지솔루션',
                '035420': 'NAVER',
                '207940': '삼성바이오로직스',
                '006400': '삼성SDI',
                '051910': 'LG화학',
                '068270': '셀트리온',
                '035720': '카카오',
                '000270': '기아'
            }
            
            return stock_names.get(symbol, "")
            
        except Exception as e:
            logger.debug(f"Error getting stock name for {symbol}: {e}")
            return ""
    
    def _display_detailed_analysis(self, risk_analysis: Dict[str, Any]):
        """상세 분석 정보 표시"""
        
        symbol = risk_analysis['symbol']
        stock_name = risk_analysis.get('stock_name', symbol)
        price_info = risk_analysis.get('price_info', {})
        per = self._to_float(price_info.get('per'))
        pbr = self._to_float(price_info.get('pbr'))
        price_position = risk_analysis.get('price_position')
        pp = price_position if isinstance(price_position, (int, float)) else None
        risk_score = risk_analysis['risk_score']
        foreign_trend = risk_analysis.get('foreign_trend', {})
        
        # 상세 분석 정보
        console.print(f"\n💡 [bold yellow]{stock_name}({symbol}) 상세 분석 정보[/bold yellow]")
        
        # 수익성 분석
        if per < 0:
            console.print(f"❌ [red]수익성 부진: PER {per:.1f}배 (적자)[/red]")
            console.print("   - 영업이익 적자로 수익성 개선 필요")
            console.print("   - 단기적으로는 신중한 접근 권장")
        elif per > 25:
            console.print(f"⚠️ [yellow]고평가: PER {per:.1f}배[/yellow]")
            console.print("   - 밸류에이션 리스크 존재")
        elif per < 10:
            console.print(f"✅ [green]저평가: PER {per:.1f}배[/green]")
            console.print("   - 상대적으로 저평가된 상태")
        
        # PBR 분석
        if pbr > 3:
            console.print(f"⚠️ [yellow]PBR 고평가: {pbr:.1f}배[/yellow]")
            console.print("   - 순자산 대비 주가가 높음")
        elif pbr < 1:
            console.print(f"✅ [green]PBR 저평가: {pbr:.1f}배[/green]")
            console.print("   - 순자산 대비 주가가 낮음")
        
        # 현재가 위치 분석
        if pp is not None and pp > 95:
            console.print(f"🚨 [red]52주 최고가 근처: {pp:.1f}%[/red]")
            console.print("   - 매우 높은 조정 위험")
            console.print("   - 단기 매도 고려 필요")
        elif pp is not None and pp > 90:
            console.print(f"⚠️ [yellow]52주 최고가 근처: {pp:.1f}%[/yellow]")
            console.print("   - 단기 조정 가능성 높음")
            console.print("   - 신중한 접근 권장")
        elif pp is not None and pp < 20:
            console.print(f"✅ [green]52주 최저가 근처: {pp:.1f}%[/green]")
            console.print("   - 상승 여력 존재")
        
        # 리스크 요인
        risk_factors = []
        if per < 0:
            risk_factors.append("• 수익성 부진 (적자)")
        if pbr > 3:
            risk_factors.append("• PBR 고평가")
        if pp is not None and pp > 95:
            risk_factors.append("• 52주 최고가 근처 (매우 높은 조정 위험)")
        elif pp is not None and pp > 90:
            risk_factors.append("• 52주 최고가 근처 (조정 위험)")
        
        if risk_factors:
            console.print(f"\n⚠️ [bold red]주요 리스크 요인[/bold red]")
            for factor in risk_factors:
                console.print(f"  {factor}")
        
        # 외국인 투자자 동향 분석
        if foreign_trend:
            console.print(f"\n🌍 [bold blue]외국인 투자자 동향 분석[/bold blue]")
            
            # 연속 매도/매수 일수
            consecutive_selling = foreign_trend.get('consecutive_selling_days', 0)
            consecutive_buying = foreign_trend.get('consecutive_buying_days', 0)
            
            if consecutive_selling >= 3:
                console.print(f"❌ [red]연속 {consecutive_selling}일 매도 중 (매우 부정적)[/red]")
            elif consecutive_selling >= 2:
                console.print(f"⚠️ [yellow]연속 {consecutive_selling}일 매도 중 (부정적)[/yellow]")
            elif consecutive_buying >= 3:
                console.print(f"✅ [green]연속 {consecutive_buying}일 매수 중 (긍정적)[/green]")
            elif consecutive_buying >= 2:
                console.print(f"👍 [green]연속 {consecutive_buying}일 매수 중 (약간 긍정적)[/green]")
            else:
                console.print("➖ [white]외국인 동향 중립적[/white]")
            
            # 트렌드 강도
            trend_strength = foreign_trend.get('trend_strength', 'neutral')
            if trend_strength == 'strong_selling':
                console.print("🔴 [red]강한 매도 트렌드 (위험)[/red]")
            elif trend_strength == 'moderate_selling':
                console.print("🟡 [yellow]중간 매도 트렌드 (주의)[/yellow]")
            elif trend_strength == 'strong_buying':
                console.print("🟢 [green]강한 매수 트렌드 (긍정적)[/green]")
            elif trend_strength == 'moderate_buying':
                console.print("🔵 [blue]중간 매수 트렌드 (안정적)[/blue]")
            
            # 최근 활동
            recent_activity = foreign_trend.get('recent_activity', 'neutral')
            if recent_activity == 'heavy_selling':
                console.print("🚨 [red]최근 대량 매도 발생 (매우 위험)[/red]")
            elif recent_activity == 'moderate_selling':
                console.print("⚠️ [yellow]최근 중간 매도 발생 (주의)[/yellow]")
            elif recent_activity == 'heavy_buying':
                console.print("🎉 [green]최근 대량 매수 발생 (매우 긍정적)[/green]")
            elif recent_activity == 'moderate_buying':
                console.print("👍 [green]최근 중간 매수 발생 (긍정적)[/green]")
        
        # 투자 전략
        console.print(f"\n🎯 [bold green]투자 전략[/bold green]")
        if per < 0:
            console.print("• 적자 기업으로 수익성 개선 대기")
            console.print("• 장기 성장성 검토 후 투자 결정")
            console.print("• 분할 매수로 리스크 분산")
        elif pp is not None and pp > 95:
            console.print("• 52주 최고가 근처로 매우 높은 조정 위험")
            console.print("• 단기 매도 또는 손절 고려")
            console.print("• 기술적 지지선 붕괴 시 추가 하락 가능")
        elif pp is not None and pp > 90:
            console.print("• 52주 최고가 근처로 조정 위험 높음")
            console.print("• 신중한 접근 및 분할 매도 고려")
            console.print("• 기술적 지지선 확인 후 재진입")
        elif risk_score >= 6:
            console.print("• 높은 리스크로 신중한 접근")
            console.print("• 기술적 지지선 확인 후 투자")
            console.print("• 손절 기준 설정 필수")
        else:
            console.print("• 적정 수준의 리스크")
            console.print("• 분할 매수 전략 고려")
            console.print("• 장기 투자 관점에서 접근")
    
    def analyze_market_foreign_trend(self, symbols: List[str]) -> Dict[str, Any]:
        """시장 전체 외국인 동향 분석"""
        try:
            total_foreign_net_buy = 0
            selling_stocks = 0
            buying_stocks = 0
            heavy_selling_stocks = 0
            heavy_buying_stocks = 0
            
            foreign_trends = []
            
            for symbol in symbols:
                try:
                    price_info = self.provider.get_stock_price_info(symbol)
                    if price_info and 'foreign_net_buy' in price_info:
                        foreign_net_buy = self._to_float(price_info.get('foreign_net_buy'))
                        total_foreign_net_buy += foreign_net_buy
                        
                        if foreign_net_buy < -100000:
                            heavy_selling_stocks += 1
                            selling_stocks += 1
                        elif foreign_net_buy < 0:
                            selling_stocks += 1
                        elif foreign_net_buy > 100000:
                            heavy_buying_stocks += 1
                            buying_stocks += 1
                        elif foreign_net_buy > 0:
                            buying_stocks += 1
                        
                        # 개별 종목 트렌드 분석
                        foreign_trend = self._analyze_foreign_trend(symbol, foreign_net_buy)
                        foreign_trends.append({
                            'symbol': symbol,
                            'foreign_net_buy': foreign_net_buy,
                            'trend': foreign_trend
                        })
                        
                except Exception as e:
                    logger.debug(f"시장 외국인 동향 분석 중 오류 {symbol}: {e}")
                    continue
            
            # 시장 전체 트렌드 분석
            total_stocks = len(symbols)
            selling_ratio = (selling_stocks / total_stocks) * 100 if total_stocks > 0 else 0
            buying_ratio = (buying_stocks / total_stocks) * 100 if total_stocks > 0 else 0
            
            # 시장 전체 외국인 동향 등급
            if selling_ratio >= 70:
                market_trend = 'strong_selling'
                market_sentiment = '매우 부정적'
            elif selling_ratio >= 50:
                market_trend = 'moderate_selling'
                market_sentiment = '부정적'
            elif buying_ratio >= 70:
                market_trend = 'strong_buying'
                market_sentiment = '매우 긍정적'
            elif buying_ratio >= 50:
                market_trend = 'moderate_buying'
                market_sentiment = '긍정적'
            else:
                market_trend = 'neutral'
                market_sentiment = '중립적'
            
            return {
                'total_foreign_net_buy': total_foreign_net_buy,
                'selling_stocks': selling_stocks,
                'buying_stocks': buying_stocks,
                'heavy_selling_stocks': heavy_selling_stocks,
                'heavy_buying_stocks': heavy_buying_stocks,
                'selling_ratio': selling_ratio,
                'buying_ratio': buying_ratio,
                'market_trend': market_trend,
                'market_sentiment': market_sentiment,
                'foreign_trends': foreign_trends,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"시장 외국인 동향 분석 실패: {e}")
            return {
                'total_foreign_net_buy': 0,
                'selling_stocks': 0,
                'buying_stocks': 0,
                'heavy_selling_stocks': 0,
                'heavy_buying_stocks': 0,
                'selling_ratio': 0,
                'buying_ratio': 0,
                'market_trend': 'unknown',
                'market_sentiment': '분석 불가',
                'foreign_trends': [],
                'analysis_timestamp': datetime.now().isoformat()
            }
    
    def analyze_portfolio_risk(self, symbols: List[str], analysis_results: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """포트폴리오 전체 리스크 분석"""
        
        individual_risks = []
        total_adjustment = 0
        
        for symbol in symbols:
            risk_analysis = self.analyze_stock_risk(symbol)
            individual_risks.append(risk_analysis)
            total_adjustment += risk_analysis['adjustment_factor']
        
        # 종합점수 정보가 있으면 정렬
        if analysis_results:
            # 종합점수 기준으로 정렬된 순서에 맞춰 individual_risks 재정렬
            symbol_to_score = {result['symbol']: result['enhanced_score'] for result in analysis_results}
            individual_risks.sort(key=lambda x: symbol_to_score.get(x['symbol'], 0), reverse=True)
        
        # 포트폴리오 평균 리스크
        avg_risk_score = sum(r['risk_score'] for r in individual_risks) / len(individual_risks)
        avg_adjustment_factor = total_adjustment / len(individual_risks)
        
        # 포트폴리오 리스크 등급
        portfolio_risk_grade = self._determine_risk_grade(avg_risk_score)
        portfolio_recommendation = self._determine_recommendation(avg_risk_score, 50)
        
        return {
            'portfolio_risk_score': avg_risk_score,
            'portfolio_risk_grade': portfolio_risk_grade,
            'portfolio_recommendation': portfolio_recommendation,
            'portfolio_adjustment_factor': avg_adjustment_factor,
            'individual_risks': individual_risks,
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def display_risk_analysis(self, risk_analysis: Dict[str, Any]):
        """리스크 분석 결과 표시"""
        
        if 'individual_risks' in risk_analysis:
            # 포트폴리오 분석 결과
            self._display_portfolio_risk(risk_analysis)
        else:
            # 개별 종목 분석 결과
            self._display_individual_risk(risk_analysis)
    
    def _display_individual_risk(self, risk_analysis: Dict[str, Any]):
        """개별 종목 리스크 분석 결과 표시"""
        
        symbol = risk_analysis['symbol']
        current_price = risk_analysis['current_price']
        price_position = risk_analysis['price_position']
        risk_score = risk_analysis['risk_score']
        risk_grade = risk_analysis['risk_grade']
        recommendation = risk_analysis['recommendation']
        adjustment_factor = risk_analysis['adjustment_factor']
        
        # 종목명 가져오기
        stock_name = self._get_stock_name(symbol)
        display_name = f"{symbol}({stock_name})" if stock_name else symbol
        
        console.print(f"\n🔍 [bold cyan]{display_name} 리스크 분석 결과[/bold cyan]")
        
        risk_table = Table(title=f"{display_name} 시장 리스크 분석")
        risk_table.add_column("지표", style="cyan")
        risk_table.add_column("값", style="green")
        risk_table.add_column("분석", style="yellow")
        
        pp = price_position if isinstance(price_position, (int, float)) else None
        pp_text = f"{pp:.1f}%" if pp is not None else "N/A"
        pp_label = ("매우 높음" if (pp is not None and pp > 80)
                    else "적정" if (pp is not None and pp > 40)
                    else "낮음" if pp is not None else "정보 부족")
        risk_table.add_row("현재가", f"{current_price:,.0f}원", "")
        risk_table.add_row("52주 대비 위치", pp_text, pp_label)
        risk_table.add_row("리스크 점수", f"{risk_score}/10", risk_grade)
        risk_table.add_row("투자 권장", recommendation, "")
        risk_table.add_row("조정 계수", f"{adjustment_factor:.2f}", 
                          "할인" if adjustment_factor < 1.0 else "프리미엄" if adjustment_factor > 1.0 else "기본")
        
        console.print(risk_table)
        
        # 상세 분석 정보
        self._display_detailed_analysis(risk_analysis)
        
        # 경고 메시지
        if risk_score >= 6:
            console.print(f"⚠️ [red]{display_name}은(는) 높은 리스크 상태입니다![/red]")
            console.print("   - 백테스팅 결과에 조정이 필요합니다.")
            console.print("   - 신중한 투자 접근을 권장합니다.")
    
    def _display_portfolio_risk(self, risk_analysis: Dict[str, Any]):
        """포트폴리오 리스크 분석 결과 표시"""
        
        portfolio_risk_score = risk_analysis['portfolio_risk_score']
        portfolio_risk_grade = risk_analysis['portfolio_risk_grade']
        portfolio_recommendation = risk_analysis['portfolio_recommendation']
        portfolio_adjustment_factor = risk_analysis['portfolio_adjustment_factor']
        individual_risks = risk_analysis['individual_risks']
        
        console.print(f"\n🔍 [bold cyan]포트폴리오 리스크 분석 결과[/bold cyan]")
        
        portfolio_table = Table(title="포트폴리오 시장 리스크 분석")
        portfolio_table.add_column("지표", style="cyan")
        portfolio_table.add_column("값", style="green")
        portfolio_table.add_column("분석", style="yellow")
        
        portfolio_table.add_row("평균 리스크 점수", f"{portfolio_risk_score:.1f}/10", portfolio_risk_grade)
        portfolio_table.add_row("포트폴리오 권장", portfolio_recommendation, "")
        portfolio_table.add_row("평균 조정 계수", f"{portfolio_adjustment_factor:.2f}", 
                              "할인" if portfolio_adjustment_factor < 1.0 else "프리미엄" if portfolio_adjustment_factor > 1.0 else "기본")
        
        console.print(portfolio_table)
        
        # 개별 종목 리스크 요약
        console.print(f"\n📊 [bold yellow]개별 종목 리스크 요약[/bold yellow]")
        
        individual_table = Table(title="개별 종목 리스크")
        individual_table.add_column("종목", style="cyan")
        individual_table.add_column("현재가", style="white")
        individual_table.add_column("52주 위치", style="blue")
        individual_table.add_column("리스크 점수", style="red")
        individual_table.add_column("권장", style="green")
        individual_table.add_column("조정계수", style="yellow")
        
        for risk in individual_risks:
            # 종목명 가져오기
            stock_name = self._get_stock_name(risk['symbol'])
            display_name = f"{risk['symbol']}({stock_name})" if stock_name else risk['symbol']
            
            pp = risk.get('price_position')
            pp_text = f"{pp:.1f}%" if isinstance(pp, (int, float)) else "N/A"
            individual_table.add_row(
                display_name,
                f"{self._to_float(risk.get('current_price')):,.0f}원",
                pp_text,
                f"{risk.get('risk_score', 0)}/10",
                risk.get('recommendation', 'N/A'),
                f"{self._to_float(risk.get('adjustment_factor'), 1.0):.2f}"
            )
        
        console.print(individual_table)
    
    def display_market_foreign_trend(self, market_trend: Dict[str, Any]):
        """시장 전체 외국인 동향 표시"""
        
        console.print(f"\n🌍 [bold blue]시장 전체 외국인 투자자 동향[/bold blue]")
        
        # 시장 전체 요약
        total_net_buy = market_trend.get('total_foreign_net_buy', 0)
        selling_stocks = market_trend.get('selling_stocks', 0)
        buying_stocks = market_trend.get('buying_stocks', 0)
        heavy_selling = market_trend.get('heavy_selling_stocks', 0)
        heavy_buying = market_trend.get('heavy_buying_stocks', 0)
        selling_ratio = market_trend.get('selling_ratio', 0)
        buying_ratio = market_trend.get('buying_ratio', 0)
        market_sentiment = market_trend.get('market_sentiment', '분석 불가')
        
        # 시장 전체 요약 테이블
        summary_table = Table(title="시장 전체 외국인 동향 요약")
        summary_table.add_column("지표", style="cyan")
        summary_table.add_column("값", style="white")
        summary_table.add_column("비율", style="green")
        
        summary_table.add_row("전체 순매수", f"{total_net_buy:,.0f}주", "")
        summary_table.add_row("매도 종목", f"{selling_stocks}개", f"{selling_ratio:.1f}%")
        summary_table.add_row("매수 종목", f"{buying_stocks}개", f"{buying_ratio:.1f}%")
        summary_table.add_row("대량 매도", f"{heavy_selling}개", "")
        summary_table.add_row("대량 매수", f"{heavy_buying}개", "")
        summary_table.add_row("시장 심리", market_sentiment, "")
        
        console.print(summary_table)
        
        # 시장 심리 해석 (강화된 시각화)
        console.print(f"\n📊 [bold]시장 심리 해석[/bold]")
        
        # 시장 심리 상태 박스
        if market_sentiment == '매우 부정적':
            console.print(Panel(
                "🔴 [bold red]외국인 투자자들이 대규모로 매도 중입니다.[/bold red]\n"
                "• 시장 전체 조정 위험 높음\n"
                "• 신중한 투자 접근 필요\n"
                "• 단기 매도 또는 손절 고려",
                title="[red]매우 부정적[/red]",
                border_style="red"
            ))
        elif market_sentiment == '부정적':
            console.print(Panel(
                "🟡 [bold yellow]외국인 투자자들이 매도 우세입니다.[/bold yellow]\n"
                "• 시장 불안정성 증가\n"
                "• 투자 시 주의 필요\n"
                "• 분할 매수 전략 고려",
                title="[yellow]부정적[/yellow]",
                border_style="yellow"
            ))
        elif market_sentiment == '매우 긍정적':
            console.print(Panel(
                "🟢 [bold green]외국인 투자자들이 대규모로 매수 중입니다.[/bold green]\n"
                "• 시장 전체 상승 모멘텀\n"
                "• 투자 기회 증가\n"
                "• 적극적 투자 전략 고려",
                title="[green]매우 긍정적[/green]",
                border_style="green"
            ))
        elif market_sentiment == '긍정적':
            console.print(Panel(
                "🔵 [bold blue]외국인 투자자들이 매수 우세입니다.[/bold blue]\n"
                "• 시장 안정성 증가\n"
                "• 투자 환경 양호\n"
                "• 균형 잡힌 투자 전략",
                title="[blue]긍정적[/blue]",
                border_style="blue"
            ))
        else:
            console.print(Panel(
                "➖ [bold white]외국인 투자자 동향이 중립적입니다.[/bold white]\n"
                "• 시장 균형 상태\n"
                "• 개별 종목 분석 중요\n"
                "• 펀더멘털 중심 투자",
                title="[white]중립적[/white]",
                border_style="white"
            ))
        
        # 개별 종목 외국인 동향 (상위 10개)
        foreign_trends = market_trend.get('foreign_trends', [])
        if foreign_trends:
            # 매도/매수 규모순으로 정렬
            sorted_trends = sorted(foreign_trends, key=lambda x: x['foreign_net_buy'])
            
            console.print(f"\n📈 [bold]개별 종목 외국인 동향 (상위 10개)[/bold]")
            trend_table = Table()
            trend_table.add_column("종목코드", style="cyan", width=8)
            trend_table.add_column("종목명", style="white", width=12)
            trend_table.add_column("외국인 순매수", style="green", width=15)
            trend_table.add_column("동향", style="yellow", width=10)
            trend_table.add_column("상태", style="magenta", width=8)
            
            for trend in sorted_trends[:10]:  # 상위 10개만 표시
                symbol = trend['symbol']
                foreign_net_buy = trend['foreign_net_buy']
                trend_info = trend['trend']
                
                # 종목명 가져오기
                stock_name = self._get_stock_name(symbol)
                display_name = stock_name[:8] + "..." if len(stock_name) > 8 else stock_name
                
                # 동향 텍스트 및 색상
                if foreign_net_buy < -100000:
                    trend_text = "대량매도"
                    trend_style = "red"
                    status_icon = "🔴"
                elif foreign_net_buy < 0:
                    trend_text = "매도"
                    trend_style = "yellow"
                    status_icon = "🟡"
                elif foreign_net_buy > 100000:
                    trend_text = "대량매수"
                    trend_style = "green"
                    status_icon = "🟢"
                elif foreign_net_buy > 0:
                    trend_text = "매수"
                    trend_style = "blue"
                    status_icon = "🔵"
                else:
                    trend_text = "중립"
                    trend_style = "white"
                    status_icon = "⚪"
                
                # 연속성 정보 추가
                consecutive_selling = trend_info.get('consecutive_selling_days', 0)
                consecutive_buying = trend_info.get('consecutive_buying_days', 0)
                
                if consecutive_selling >= 3:
                    status_text = f"{status_icon} 연속{consecutive_selling}일"
                elif consecutive_buying >= 3:
                    status_text = f"{status_icon} 연속{consecutive_buying}일"
                else:
                    status_text = f"{status_icon} 단발성"
                
                trend_table.add_row(
                    symbol,
                    display_name,
                    f"{foreign_net_buy:,.0f}주",
                    f"[{trend_style}]{trend_text}[/{trend_style}]",
                    status_text
                )
            
            console.print(trend_table)
        
        # 시장 전체 외국인 동향 분석 완료
        console.print(f"\n✅ [green]시장 전체 외국인 동향 분석이 완료되었습니다.[/green]")

def create_market_risk_analyzer(kis_provider):
    """시장 리스크 분석기 생성"""
    return MarketRiskAnalyzer(kis_provider)
