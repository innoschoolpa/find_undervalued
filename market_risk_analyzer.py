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
        
    def analyze_stock_risk(self, symbol: str) -> Dict[str, Any]:
        """개별 종목의 시장 리스크 분석"""
        
        try:
            # 현재가 정보 가져오기
            price_info = self.provider.get_stock_price_info(symbol)
            
            if not price_info:
                return self._create_default_risk_profile()
            
            current_price = price_info['current_price']
            w52_high = price_info['w52_high']
            w52_low = price_info['w52_low']
            change_rate = price_info['change_rate']
            per = price_info['per']
            pbr = price_info['pbr']
            foreign_net_buy = price_info['foreign_net_buy']
            program_net_buy = price_info['program_net_buy']
            
            # 현재가 위치 계산
            price_position = ((current_price - w52_low) / (w52_high - w52_low)) * 100
            
            # 리스크 점수 계산
            risk_score = self._calculate_risk_score(
                price_position, per, pbr, change_rate, 
                foreign_net_buy, program_net_buy
            )
            
            # 리스크 등급 결정
            risk_grade = self._determine_risk_grade(risk_score)
            
            # 투자 권장 결정
            recommendation = self._determine_recommendation(risk_score, price_position, per)
            
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
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing stock risk for {symbol}: {e}")
            return self._create_default_risk_profile()
    
    def _calculate_risk_score(self, price_position: float, per: float, pbr: float, 
                            change_rate: float, foreign_net_buy: float, 
                            program_net_buy: float) -> int:
        """리스크 점수 계산 (0-10, 높을수록 위험)"""
        
        risk_score = 0
        
        # 현재가 위치 리스크 (0-4점) - 52주 최고가 근처는 높은 리스크
        if price_position > 95:
            risk_score += 4  # 52주 최고가 근처는 매우 높은 리스크
        elif price_position > 90:
            risk_score += 3
        elif price_position > 80:
            risk_score += 2
        elif price_position > 60:
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
        
        # 외국인 매매 리스크 (0-1점)
        if foreign_net_buy < -100000:
            risk_score += 1
        
        return max(0, min(10, risk_score))  # 0-10 범위로 제한
    
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
    
    def _determine_recommendation(self, risk_score: int, price_position: float, per: float = 0) -> str:
        """투자 권장 결정"""
        if risk_score >= 8:
            return "매도 고려"
        elif risk_score >= 6:
            return "신중한 접근"
        elif risk_score >= 4:
            # 수익성 부진 고려
            if per < 0:
                return "신중한 접근"  # 적자 기업은 신중한 접근
            # 52주 최고가 근처는 신중한 접근
            if price_position > 90:
                return "신중한 접근"
            return "적정 투자"
        elif risk_score >= 2:
            # 52주 최고가 근처는 적정 투자로 조정
            if price_position > 90:
                return "적정 투자"
            return "적극 매수"
        else:
            # 52주 최고가 근처는 적극 매수로 조정
            if price_position > 90:
                return "적극 매수"
            return "강력 매수"
    
    def _calculate_adjustment_factor(self, risk_score: int, price_position: float, per: float = 0) -> float:
        """백테스팅 결과 조정 계수 계산 (0.3-1.5)"""
        
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
        if price_position > 90:
            base_factor *= 0.7  # 최고가 근처 시 추가 할인
        elif price_position > 80:
            base_factor *= 0.85  # 높은 위치 시 할인
        
        # 수익성 부진 추가 조정
        if per < 0:  # 적자 기업
            base_factor *= 0.6  # 적자 기업은 추가 40% 할인
        elif per > 30:  # 매우 고평가
            base_factor *= 0.8  # 고평가 시 추가 20% 할인
        
        return max(0.2, min(1.5, base_factor))  # 0.2-1.5 범위로 제한
    
    def _create_default_risk_profile(self) -> Dict[str, Any]:
        """기본 리스크 프로필 생성"""
        return {
            'symbol': 'UNKNOWN',
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
            # KOSPI 마스터 데이터에서 종목명 찾기 (우선순위)
            from enhanced_integrated_analyzer import EnhancedIntegratedAnalyzer
            analyzer = EnhancedIntegratedAnalyzer()
            if hasattr(analyzer, '_kospi_index') and analyzer._kospi_index is not None:
                if symbol in analyzer._kospi_index:
                    stock_info = analyzer._kospi_index[symbol]
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
        per = price_info.get('per', 0)
        pbr = price_info.get('pbr', 0)
        price_position = risk_analysis['price_position']
        risk_score = risk_analysis['risk_score']
        
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
        if price_position > 95:
            console.print(f"🚨 [red]52주 최고가 근처: {price_position:.1f}%[/red]")
            console.print("   - 매우 높은 조정 위험")
            console.print("   - 단기 매도 고려 필요")
        elif price_position > 90:
            console.print(f"⚠️ [yellow]52주 최고가 근처: {price_position:.1f}%[/yellow]")
            console.print("   - 단기 조정 가능성 높음")
            console.print("   - 신중한 접근 권장")
        elif price_position < 20:
            console.print(f"✅ [green]52주 최저가 근처: {price_position:.1f}%[/green]")
            console.print("   - 상승 여력 존재")
        
        # 리스크 요인
        risk_factors = []
        if per < 0:
            risk_factors.append("• 수익성 부진 (적자)")
        if pbr > 3:
            risk_factors.append("• PBR 고평가")
        if price_position > 95:
            risk_factors.append("• 52주 최고가 근처 (매우 높은 조정 위험)")
        elif price_position > 90:
            risk_factors.append("• 52주 최고가 근처 (조정 위험)")
        
        if risk_factors:
            console.print(f"\n⚠️ [bold red]주요 리스크 요인[/bold red]")
            for factor in risk_factors:
                console.print(f"  {factor}")
        
        # 투자 전략
        console.print(f"\n🎯 [bold green]투자 전략[/bold green]")
        if per < 0:
            console.print("• 적자 기업으로 수익성 개선 대기")
            console.print("• 장기 성장성 검토 후 투자 결정")
            console.print("• 분할 매수로 리스크 분산")
        elif price_position > 95:
            console.print("• 52주 최고가 근처로 매우 높은 조정 위험")
            console.print("• 단기 매도 또는 손절 고려")
            console.print("• 기술적 지지선 붕괴 시 추가 하락 가능")
        elif price_position > 90:
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
    
    def analyze_portfolio_risk(self, symbols: List[str]) -> Dict[str, Any]:
        """포트폴리오 전체 리스크 분석"""
        
        individual_risks = []
        total_adjustment = 0
        
        for symbol in symbols:
            risk_analysis = self.analyze_stock_risk(symbol)
            individual_risks.append(risk_analysis)
            total_adjustment += risk_analysis['adjustment_factor']
        
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
        
        risk_table.add_row("현재가", f"{current_price:,.0f}원", "")
        risk_table.add_row("52주 대비 위치", f"{price_position:.1f}%", 
                          "매우 높음" if price_position > 80 else "적정" if price_position > 40 else "낮음")
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
            
            individual_table.add_row(
                display_name,
                f"{risk['current_price']:,.0f}원",
                f"{risk['price_position']:.1f}%",
                f"{risk['risk_score']}/10",
                risk['recommendation'],
                f"{risk['adjustment_factor']:.2f}"
            )
        
        console.print(individual_table)
        
        # 개별 종목 상세 분석
        console.print(f"\n💡 [bold yellow]개별 종목 상세 분석[/bold yellow]")
        for risk in individual_risks:
            self._display_detailed_analysis(risk)
        
        # 포트폴리오 경고 메시지
        if portfolio_risk_score >= 6:
            console.print(f"⚠️ [red]포트폴리오가 높은 리스크 상태입니다![/red]")
            console.print("   - 백테스팅 결과에 조정이 필요합니다.")
            console.print("   - 신중한 투자 접근을 권장합니다.")

def create_market_risk_analyzer(kis_provider):
    """시장 리스크 분석기 생성"""
    return MarketRiskAnalyzer(kis_provider)
