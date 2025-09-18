#!/usr/bin/env python3
"""
SK하이닉스 현재가 및 간단한 분석
"""

from kis_data_provider import KISDataProvider
from rich.console import Console

console = Console()

def check_current_price():
    """SK하이닉스 현재가 확인"""
    
    console.print("💰 [bold green]SK하이닉스 현재가 확인[/bold green]")
    console.print("=" * 50)
    
    try:
        provider = KISDataProvider()
        
        # 현재가 정보
        price_info = provider.get_stock_price_info("000660")
        console.print(f"📊 현재가 정보: {price_info}")
        
        # 최근 30일 주가 히스토리
        price_history = provider.get_daily_price_history("000660", 30)
        
        if price_history is not None and not price_history.empty:
            console.print(f"📋 컬럼: {list(price_history.columns)}")
            console.print(f"📈 최근 5일 데이터:")
            console.print(price_history.head())
            
            # 최고가, 최저가, 현재가
            max_price = price_history['close'].max()
            min_price = price_history['close'].min()
            latest_price = price_history['close'].iloc[-1]
            
            console.print(f"\n📊 30일간 주가 분석:")
            console.print(f"• 최고가: {max_price:,.0f}원")
            console.print(f"• 최저가: {min_price:,.0f}원")
            console.print(f"• 최신가: {latest_price:,.0f}원")
            
            # 현재가 위치 계산
            if max_price != min_price:
                position = ((latest_price - min_price) / (max_price - min_price)) * 100
                console.print(f"• 현재가 위치: {position:.1f}% (최저가 대비)")
                
                if position > 80:
                    console.print("⚠️ [red]현재가가 30일 최고가 근처입니다![/red]")
                elif position > 60:
                    console.print("⚠️ [yellow]현재가가 상대적으로 높은 수준입니다.[/yellow]")
                elif position > 40:
                    console.print("✅ [green]현재가가 적정 수준입니다.[/green]")
                else:
                    console.print("🚀 [blue]현재가가 상대적으로 낮은 수준입니다.[/blue]")
        
    except Exception as e:
        console.print(f"❌ 오류: {e}")

if __name__ == "__main__":
    check_current_price()
