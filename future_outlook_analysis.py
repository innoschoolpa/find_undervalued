#!/usr/bin/env python3
"""
SK하이닉스 미래 전망 분석 - 현재가 최고점인가?
"""

import sys
import logging
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

console = Console()

def analyze_future_outlook():
    """SK하이닉스 미래 전망 분석"""
    
    console.print("🔮 [bold green]SK하이닉스 미래 전망 분석: 현재가 최고점인가?[/bold green]")
    console.print("=" * 70)
    
    try:
        from kis_data_provider import KISDataProvider
        from enhanced_integrated_analyzer import EnhancedIntegratedAnalyzer
        
        # 데이터 제공자 초기화
        provider = KISDataProvider()
        analyzer = EnhancedIntegratedAnalyzer()
        
        console.print("📊 [bold yellow]1. 현재 주가 및 기술적 분석[/bold yellow]")
        
        # 현재 주가 정보
        current_price_info = provider.get_stock_price_info("000660")
        if current_price_info:
            current_price = current_price_info.get('stck_prpr', 'N/A')
            console.print(f"💰 현재 주가: {current_price}원")
        
        # 최근 1년 주가 히스토리 (252 거래일)
        price_history = provider.get_daily_price_history("000660", 252)
        
        if price_history is not None and not price_history.empty:
            # 실제 컬럼명 확인
            console.print(f"📋 사용 가능한 컬럼: {list(price_history.columns)}")
            
            # 종가 컬럼 찾기 (stck_clpr 또는 다른 이름)
            close_col = None
            for col in price_history.columns:
                if 'clpr' in col.lower() or 'close' in col.lower():
                    close_col = col
                    break
            
            if close_col is None:
                console.print("⚠️ 종가 컬럼을 찾을 수 없습니다.")
                return None
            
            # 최고가, 최저가, 평균가 계산
            max_price = price_history[close_col].max()
            min_price = price_history[close_col].min()
            avg_price = price_history[close_col].mean()
            current_price_num = float(current_price) if current_price != 'N/A' else 0
            
            # 현재가 대비 위치
            price_position = ((current_price_num - min_price) / (max_price - min_price)) * 100 if max_price != min_price else 50
            
            console.print(f"📈 1년 최고가: {max_price:,.0f}원")
            console.print(f"📉 1년 최저가: {min_price:,.0f}원")
            console.print(f"📊 1년 평균가: {avg_price:,.0f}원")
            console.print(f"🎯 현재가 위치: {price_position:.1f}% (최저가 대비)")
            
            # 기술적 분석
            if price_position > 80:
                console.print("⚠️ [red]현재가가 1년 최고가 근처입니다! (80% 이상)[/red]")
            elif price_position > 60:
                console.print("⚠️ [yellow]현재가가 상대적으로 높은 수준입니다. (60-80%)[/yellow]")
            elif price_position > 40:
                console.print("✅ [green]현재가가 적정 수준입니다. (40-60%)[/green]")
            else:
                console.print("🚀 [blue]현재가가 상대적으로 낮은 수준입니다. (40% 미만)[/blue]")
        
        console.print("\n📊 [bold yellow]2. 투자의견 및 목표가 분석[/bold yellow]")
        
        # 투자의견 분석
        try:
            opinion_result = analyzer.analyze_investment_opinion("000660")
            if opinion_result and hasattr(opinion_result, 'summary'):
                summary = opinion_result.summary
                
                opinion_table = Table(title="최근 투자의견 분석")
                opinion_table.add_column("지표", style="cyan")
                opinion_table.add_column("값", style="green")
                
                if hasattr(summary, 'total_opinions'):
                    opinion_table.add_row("총 의견 수", str(summary.total_opinions))
                if hasattr(summary, 'buy_ratio'):
                    opinion_table.add_row("매수 비율", f"{summary.buy_ratio:.1%}")
                if hasattr(summary, 'hold_ratio'):
                    opinion_table.add_row("보유 비율", f"{summary.hold_ratio:.1%}")
                if hasattr(summary, 'sell_ratio'):
                    opinion_table.add_row("매도 비율", f"{summary.sell_ratio:.1%}")
                if hasattr(summary, 'average_target_price'):
                    opinion_table.add_row("평균 목표가", f"{summary.average_target_price:,.0f}원")
                
                console.print(opinion_table)
                
                # 목표가 대비 현재가 분석
                if hasattr(summary, 'average_target_price') and current_price != 'N/A':
                    target_price = summary.average_target_price
                    current_price_num = float(current_price)
                    upside = ((target_price - current_price_num) / current_price_num) * 100
                    
                    console.print(f"\n🎯 [bold cyan]목표가 대비 상승 여력: {upside:+.1f}%[/bold cyan]")
                    
                    if upside > 20:
                        console.print("🚀 [green]상당한 상승 여력이 있습니다![/green]")
                    elif upside > 10:
                        console.print("✅ [green]적정한 상승 여력이 있습니다.[/green]")
                    elif upside > 0:
                        console.print("⚠️ [yellow]제한적인 상승 여력입니다.[/yellow]")
                    else:
                        console.print("⚠️ [red]목표가 대비 하락 위험이 있습니다.[/red]")
        
        except Exception as e:
            console.print(f"⚠️ 투자의견 분석 중 오류: {e}")
        
        console.print("\n📊 [bold yellow]3. 추정실적 및 밸류에이션 분석[/bold yellow]")
        
        # 추정실적 분석
        try:
            estimate_result = analyzer.analyze_estimate_performance("000660")
            if estimate_result and hasattr(estimate_result, 'summary'):
                summary = estimate_result.summary
                
                estimate_table = Table(title="추정실적 분석")
                estimate_table.add_column("지표", style="cyan")
                estimate_table.add_column("값", style="green")
                
                if hasattr(summary, 'current_year_estimate'):
                    estimate_table.add_row("당해 추정실적", f"{summary.current_year_estimate:,.0f}억원")
                if hasattr(summary, 'next_year_estimate'):
                    estimate_table.add_row("차년 추정실적", f"{summary.next_year_estimate:,.0f}억원")
                if hasattr(summary, 'growth_rate'):
                    estimate_table.add_row("성장률", f"{summary.growth_rate:.1%}")
                if hasattr(summary, 'pe_ratio'):
                    estimate_table.add_row("PER", f"{summary.pe_ratio:.1f}배")
                if hasattr(summary, 'pb_ratio'):
                    estimate_table.add_row("PBR", f"{summary.pb_ratio:.1f}배")
                
                console.print(estimate_table)
                
                # 밸류에이션 분석
                if hasattr(summary, 'pe_ratio'):
                    pe_ratio = summary.pe_ratio
                    if pe_ratio < 10:
                        console.print("💰 [green]PER가 낮아 저평가 상태입니다.[/green]")
                    elif pe_ratio < 20:
                        console.print("⚖️ [yellow]PER가 적정 수준입니다.[/yellow]")
                    else:
                        console.print("⚠️ [red]PER가 높아 고평가 상태일 수 있습니다.[/red]")
        
        except Exception as e:
            console.print(f"⚠️ 추정실적 분석 중 오류: {e}")
        
        console.print("\n📊 [bold yellow]4. 리스크 요인 분석[/bold yellow]")
        
        risk_table = Table(title="주요 리스크 요인")
        risk_table.add_column("리스크", style="red")
        risk_table.add_column("설명", style="white")
        risk_table.add_column("영향도", style="yellow")
        
        risk_table.add_row(
            "메모리 반도체 사이클",
            "D램/NAND 가격 변동성",
            "높음"
        )
        risk_table.add_row(
            "중국 수요 감소",
            "중국 경제 둔화 영향",
            "중간"
        )
        risk_table.add_row(
            "AI 반도체 전환",
            "HBM 등 고부가가치 제품 의존도",
            "중간"
        )
        risk_table.add_row(
            "환율 변동",
            "달러/원 환율 영향",
            "중간"
        )
        risk_table.add_row(
            "기술 경쟁",
            "삼성전자, 마이크론과의 경쟁",
            "높음"
        )
        
        console.print(risk_table)
        
        console.print("\n💡 [bold magenta]5. 미래 전망 및 투자 권장사항[/bold magenta]")
        
        # 종합 분석
        console.print("🔍 [bold cyan]종합 분석 결과[/bold cyan]")
        
        # 현재가 위치 분석
        if 'price_position' in locals():
            if price_position > 80:
                console.print("⚠️ [red]현재가가 1년 최고가 근처로 상당히 높은 수준입니다.[/red]")
                console.print("   - 단기 조정 가능성이 높습니다.")
                console.print("   - 분할 매수 전략을 고려하세요.")
            elif price_position > 60:
                console.print("⚠️ [yellow]현재가가 상대적으로 높은 수준입니다.[/yellow]")
                console.print("   - 신중한 접근이 필요합니다.")
                console.print("   - 기술적 지지선 확인 후 매수 고려.")
            else:
                console.print("✅ [green]현재가가 상대적으로 낮은 수준입니다.[/green]")
                console.print("   - 매수 기회로 볼 수 있습니다.")
        
        # 투자 전략 권장
        console.print("\n🎯 [bold cyan]투자 전략 권장사항[/bold cyan]")
        
        console.print("📈 [bold green]긍정적 요인[/bold green]")
        console.print("• AI 반도체 수요 급증 (HBM, DDR5)")
        console.print("• 메모리 반도체 업사이클 지속")
        console.print("• 기술적 우위 (HBM3, HBM3E)")
        console.print("• 글로벌 데이터센터 확장")
        
        console.print("\n⚠️ [bold red]부정적 요인[/bold red]")
        console.print("• 현재가가 상대적으로 높은 수준")
        console.print("• 메모리 반도체 사이클 변동성")
        console.print("• 중국 수요 감소 우려")
        console.print("• 경쟁사와의 기술 경쟁 심화")
        
        console.print("\n💡 [bold magenta]투자 전략[/bold magenta]")
        console.print("1. [yellow]분할 매수 전략[/yellow]: 현재가가 높으므로 분할 매수")
        console.print("2. [blue]기술적 지지선 확인[/blue]: 300,000원, 280,000원 지지선")
        console.print("3. [green]장기 투자 관점[/green]: AI 반도체 트렌드는 지속될 전망")
        console.print("4. [red]손절 기준 설정[/red]: 20% 하락 시 손절 고려")
        
        console.print("\n🎯 [bold cyan]최종 결론[/bold cyan]")
        console.print("• [yellow]현재가가 상대적으로 높은 수준이므로 신중한 접근 필요[/yellow]")
        console.print("• [green]장기적으로는 AI 반도체 수요 증가로 긍정적 전망[/green]")
        console.print("• [blue]분할 매수와 기술적 지지선 확인 후 투자 권장[/blue]")
        console.print("• [red]단기 조정 가능성을 고려한 리스크 관리 필수[/red]")
        
        return {
            'current_price': current_price,
            'price_position': price_position if 'price_position' in locals() else None,
            'max_price': max_price if 'max_price' in locals() else None,
            'min_price': min_price if 'min_price' in locals() else None,
            'analysis_date': datetime.now().strftime("%Y-%m-%d")
        }
        
    except Exception as e:
        console.print(f"[red]❌ 분석 중 오류 발생: {e}[/red]")
        logger.error(f"Error during analysis: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    analyze_future_outlook()
