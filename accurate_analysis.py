#!/usr/bin/env python3
"""
SK하이닉스 정확한 미래 전망 분석
"""

from kis_data_provider import KISDataProvider
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def accurate_analysis():
    """SK하이닉스 정확한 분석"""
    
    console.print("🔮 [bold green]SK하이닉스 정확한 미래 전망 분석[/bold green]")
    console.print("=" * 60)
    
    try:
        provider = KISDataProvider()
        
        # 현재가 정보
        price_info = provider.get_stock_price_info("000660")
        current_price = price_info['current_price']
        w52_high = price_info['w52_high']
        w52_low = price_info['w52_low']
        change_rate = price_info['change_rate']
        
        console.print(f"💰 현재가: {current_price:,.0f}원")
        console.print(f"📈 52주 최고가: {w52_high:,.0f}원")
        console.print(f"📉 52주 최저가: {w52_low:,.0f}원")
        console.print(f"📊 당일 등락률: {change_rate:+.2f}%")
        
        # 현재가 위치 계산 (52주 기준)
        price_position = ((current_price - w52_low) / (w52_high - w52_low)) * 100
        
        console.print(f"🎯 현재가 위치: {price_position:.1f}% (52주 최저가 대비)")
        
        # 기술적 분석
        if price_position > 90:
            console.print("🚨 [red]현재가가 52주 최고가 근처입니다! (90% 이상)[/red]")
            risk_level = "매우 높음"
        elif price_position > 80:
            console.print("⚠️ [red]현재가가 매우 높은 수준입니다! (80-90%)[/red]")
            risk_level = "높음"
        elif price_position > 60:
            console.print("⚠️ [yellow]현재가가 상대적으로 높은 수준입니다. (60-80%)[/yellow]")
            risk_level = "중간"
        elif price_position > 40:
            console.print("✅ [green]현재가가 적정 수준입니다. (40-60%)[/green]")
            risk_level = "낮음"
        else:
            console.print("🚀 [blue]현재가가 상대적으로 낮은 수준입니다. (40% 미만)[/blue]")
            risk_level = "매우 낮음"
        
        # 밸류에이션 분석
        per = price_info['per']
        pbr = price_info['pbr']
        
        console.print(f"\n📊 밸류에이션 분석:")
        console.print(f"• PER: {per:.1f}배")
        console.print(f"• PBR: {pbr:.1f}배")
        
        # PER 분석
        if per < 10:
            per_status = "저평가"
            per_color = "green"
        elif per < 20:
            per_status = "적정가"
            per_color = "yellow"
        else:
            per_status = "고평가"
            per_color = "red"
        
        console.print(f"• PER 상태: [{per_color}]{per_status}[/{per_color}]")
        
        # 외국인 매매 동향
        foreign_net_buy = price_info['foreign_net_buy']
        program_net_buy = price_info['program_net_buy']
        
        console.print(f"\n🌍 기관/외국인 매매 동향:")
        console.print(f"• 외국인 순매수: {foreign_net_buy:,.0f}주")
        console.print(f"• 프로그램 순매수: {program_net_buy:,.0f}주")
        
        # 매매 동향 분석
        if foreign_net_buy > 0:
            foreign_sentiment = "긍정적"
            foreign_color = "green"
        else:
            foreign_sentiment = "부정적"
            foreign_color = "red"
        
        if program_net_buy > 0:
            program_sentiment = "긍정적"
            program_color = "green"
        else:
            program_sentiment = "부정적"
            program_color = "red"
        
        console.print(f"• 외국인 심리: [{foreign_color}]{foreign_sentiment}[/{foreign_color}]")
        console.print(f"• 프로그램 심리: [{program_color}]{program_sentiment}[/{program_color}]")
        
        # 리스크 요인 분석
        console.print(f"\n⚠️ [bold red]주요 리스크 요인[/bold red]")
        
        risk_table = Table(title="리스크 분석")
        risk_table.add_column("리스크", style="red")
        risk_table.add_column("현재 상황", style="white")
        risk_table.add_column("영향도", style="yellow")
        
        # 현재가 리스크
        if price_position > 80:
            price_risk = "매우 높음"
            price_impact = "높음"
        elif price_position > 60:
            price_risk = "높음"
            price_impact = "중간"
        else:
            price_risk = "낮음"
            price_impact = "낮음"
        
        risk_table.add_row("현재가 리스크", f"52주 대비 {price_position:.1f}% 위치", price_impact)
        
        # 밸류에이션 리스크
        if per > 20:
            val_risk = "고평가"
            val_impact = "높음"
        elif per < 10:
            val_risk = "저평가"
            val_impact = "낮음"
        else:
            val_risk = "적정가"
            val_impact = "중간"
        
        risk_table.add_row("밸류에이션 리스크", f"PER {per:.1f}배 ({val_risk})", val_impact)
        
        # 외국인 매매 리스크
        if foreign_net_buy < -100000:
            foreign_risk = "대량 매도"
            foreign_impact = "높음"
        elif foreign_net_buy < 0:
            foreign_risk = "순매도"
            foreign_impact = "중간"
        else:
            foreign_risk = "순매수"
            foreign_impact = "낮음"
        
        risk_table.add_row("외국인 매매 리스크", f"{foreign_net_buy:,.0f}주 ({foreign_risk})", foreign_impact)
        
        console.print(risk_table)
        
        # 미래 전망 및 투자 권장사항
        console.print(f"\n💡 [bold magenta]미래 전망 및 투자 권장사항[/bold magenta]")
        
        # 종합 리스크 평가
        risk_score = 0
        if price_position > 80:
            risk_score += 3
        elif price_position > 60:
            risk_score += 2
        else:
            risk_score += 1
        
        if per > 20:
            risk_score += 2
        elif per < 10:
            risk_score -= 1
        
        if foreign_net_buy < -100000:
            risk_score += 2
        elif foreign_net_buy < 0:
            risk_score += 1
        
        # 투자 권장사항
        if risk_score >= 6:
            recommendation = "매도 고려"
            rec_color = "red"
            rec_icon = "🔴"
        elif risk_score >= 4:
            recommendation = "신중한 접근"
            rec_color = "yellow"
            rec_icon = "🟡"
        elif risk_score >= 2:
            recommendation = "적정 투자"
            rec_color = "green"
            rec_icon = "🟢"
        else:
            recommendation = "적극 매수"
            rec_color = "blue"
            rec_icon = "🔵"
        
        console.print(f"{rec_icon} [bold {rec_color}]종합 투자 권장: {recommendation}[/bold {rec_color}]")
        console.print(f"📊 리스크 점수: {risk_score}/7 (높을수록 위험)")
        
        # 구체적 투자 전략
        console.print(f"\n🎯 [bold cyan]구체적 투자 전략[/bold cyan]")
        
        if price_position > 80:
            console.print("• [red]현재가가 52주 최고가 근처로 단기 조정 가능성 높음[/red]")
            console.print("• [yellow]분할 매도 또는 손절 고려[/yellow]")
            console.print("• [blue]기술적 지지선 (300,000원, 280,000원) 확인 후 재진입[/blue]")
        elif price_position > 60:
            console.print("• [yellow]현재가가 상대적으로 높은 수준으로 신중한 접근 필요[/yellow]")
            console.print("• [green]분할 매수 전략 권장[/green]")
            console.print("• [blue]기술적 지지선 확인 후 매수 고려[/blue]")
        else:
            console.print("• [green]현재가가 상대적으로 낮은 수준으로 매수 기회[/green]")
            console.print("• [blue]적극적 매수 전략 고려[/blue]")
            console.print("• [yellow]장기 투자 관점에서 접근[/yellow]")
        
        # AI 반도체 트렌드 분석
        console.print(f"\n🤖 [bold cyan]AI 반도체 트렌드 분석[/bold cyan]")
        console.print("• [green]긍정적 요인:[/green]")
        console.print("  - HBM3, HBM3E 수요 급증")
        console.print("  - AI 서버 및 데이터센터 확장")
        console.print("  - 메모리 반도체 업사이클 지속")
        console.print("  - 기술적 우위 (HBM 시장 점유율 1위)")
        
        console.print("• [red]부정적 요인:[/red]")
        console.print("  - 메모리 반도체 사이클 변동성")
        console.print("  - 중국 수요 감소 우려")
        console.print("  - 삼성전자, 마이크론과의 경쟁 심화")
        console.print("  - 반도체 장비 투자 증가로 공급 확대")
        
        # 최종 결론
        console.print(f"\n🎯 [bold magenta]최종 결론[/bold magenta]")
        
        if price_position > 80:
            console.print("🚨 [red]현재가가 52주 최고가 근처로 단기 조정 위험이 높습니다.[/red]")
            console.print("• 과거 성과가 미래를 보장하지 않습니다.")
            console.print("• 현재가가 상당히 높은 수준이므로 신중한 접근이 필요합니다.")
            console.print("• 분할 매도 또는 손절을 고려하세요.")
        elif price_position > 60:
            console.print("⚠️ [yellow]현재가가 상대적으로 높은 수준입니다.[/yellow]")
            console.print("• AI 반도체 트렌드는 지속될 전망이지만 단기 조정 가능성이 있습니다.")
            console.print("• 분할 매수 전략으로 리스크를 분산하세요.")
        else:
            console.print("✅ [green]현재가가 상대적으로 낮은 수준으로 매수 기회입니다.[/green]")
            console.print("• AI 반도체 트렌드와 함께 장기 투자를 고려하세요.")
        
        console.print(f"\n💡 [bold cyan]핵심 메시지[/bold cyan]")
        console.print("• [yellow]과거 성과 ≠ 미래 성과[/yellow]")
        console.print("• [blue]현재가 위치와 밸류에이션을 종합적으로 고려하세요[/blue]")
        console.print("• [green]AI 반도체 트렌드는 지속되지만 사이클 변동성을 고려하세요[/green]")
        console.print("• [red]리스크 관리가 가장 중요합니다[/red]")
        
        return {
            'current_price': current_price,
            'price_position': price_position,
            'risk_score': risk_score,
            'recommendation': recommendation,
            'per': per,
            'pbr': pbr
        }
        
    except Exception as e:
        console.print(f"❌ 오류: {e}")
        return None

if __name__ == "__main__":
    accurate_analysis()
