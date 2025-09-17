# test_investment_opinion.py
import logging
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from investment_opinion_analyzer import InvestmentOpinionAnalyzer
from investment_opinion_client import InvestmentOpinionClient

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

# Rich Console 초기화
console = Console()

def test_single_stock_analysis():
    """단일 종목 투자의견 분석 테스트"""
    console.print("\n🧪 [bold blue]단일 종목 투자의견 분석 테스트[/bold blue]")
    console.print("="*60)
    
    analyzer = InvestmentOpinionAnalyzer()
    
    # 삼성전자 테스트
    symbol = "005930"
    console.print(f"\n📊 [bold yellow]{symbol} (삼성전자) 투자의견 분석[/bold yellow]")
    
    try:
        analysis = analyzer.analyze_single_stock(symbol, days_back=30)
        
        if analysis['status'] == 'success':
            # 요약 정보 표시
            summary = analysis['summary']
            
            table = Table(title=f"{symbol} 투자의견 요약")
            table.add_column("항목", style="cyan")
            table.add_column("값", style="green")
            
            table.add_row("총 의견 수", f"{summary.total_opinions}건")
            table.add_row("매수 의견", f"{summary.buy_opinions}건")
            table.add_row("보유 의견", f"{summary.hold_opinions}건")
            table.add_row("매도 의견", f"{summary.sell_opinions}건")
            table.add_row("평균 목표가", f"{summary.avg_target_price:,}원")
            table.add_row("평균 상승률", f"{summary.avg_upside:+.2f}%")
            table.add_row("트렌드", summary.opinion_trend)
            table.add_row("최근 의견일", summary.most_recent_date)
            
            console.print(table)
            
            # 상세 보고서 생성
            report = analyzer.generate_report(analysis)
            console.print(Panel(report, title="📋 상세 분석 보고서", border_style="green"))
            
        else:
            console.print(f"[red]❌ 분석 실패: {analysis.get('message', '알 수 없는 오류')}[/red]")
            
    except Exception as e:
        console.print(f"[red]❌ 테스트 실패: {e}[/red]")

def test_multiple_stocks_analysis():
    """다중 종목 투자의견 비교 분석 테스트"""
    console.print("\n🧪 [bold blue]다중 종목 투자의견 비교 분석 테스트[/bold blue]")
    console.print("="*60)
    
    analyzer = InvestmentOpinionAnalyzer()
    
    # 주요 종목들
    symbols = ["005930", "000660", "035420", "051910"]  # 삼성전자, SK하이닉스, NAVER, LG화학
    
    console.print(f"\n📊 [bold yellow]{len(symbols)}개 종목 투자의견 비교 분석[/bold yellow]")
    
    try:
        analysis = analyzer.analyze_multiple_stocks(symbols, days_back=30)
        
        console.print(f"✅ 분석 완료: {analysis['successful_analyses']}/{analysis['total_stocks']}개 종목")
        
        # 종목별 요약 테이블
        table = Table(title="종목별 투자의견 요약")
        table.add_column("종목코드", style="cyan")
        table.add_column("총 의견", style="white")
        table.add_column("매수", style="green")
        table.add_column("보유", style="yellow")
        table.add_column("매도", style="red")
        table.add_column("평균 목표가", style="blue")
        table.add_column("상승률", style="magenta")
        table.add_column("트렌드", style="white")
        
        for symbol, stock_analysis in analysis['stock_analyses'].items():
            if stock_analysis.get('status') == 'success':
                summary = stock_analysis['summary']
                table.add_row(
                    symbol,
                    f"{summary.total_opinions}",
                    f"{summary.buy_opinions}",
                    f"{summary.hold_opinions}",
                    f"{summary.sell_opinions}",
                    f"{summary.avg_target_price:,}",
                    f"{summary.avg_upside:+.1f}%",
                    summary.opinion_trend
                )
            else:
                table.add_row(symbol, "오류", "-", "-", "-", "-", "-", "-")
        
        console.print(table)
        
        # 비교 분석 결과
        comparison = analysis.get('comparison_analysis', {})
        if comparison and comparison.get('status') != 'no_data':
            console.print("\n🏆 [bold yellow]비교 분석 결과[/bold yellow]")
            
            # 목표가 랭킹
            if 'target_price_ranking' in comparison:
                console.print("\n📈 [bold green]평균 목표가 랭킹[/bold green]")
                for i, (symbol, price) in enumerate(comparison['target_price_ranking'], 1):
                    console.print(f"  {i}. {symbol}: {price:,}원")
            
            # 컨센서스 랭킹
            if 'consensus_ranking' in comparison:
                console.print("\n🎯 [bold green]컨센서스 점수 랭킹[/bold green]")
                for i, (symbol, score) in enumerate(comparison['consensus_ranking'], 1):
                    console.print(f"  {i}. {symbol}: {score:.2f}")
            
            # 의견 수 랭킹
            if 'opinion_count_ranking' in comparison:
                console.print("\n📊 [bold green]투자의견 수 랭킹[/bold green]")
                for i, (symbol, count) in enumerate(comparison['opinion_count_ranking'], 1):
                    console.print(f"  {i}. {symbol}: {count}건")
        
    except Exception as e:
        console.print(f"[red]❌ 테스트 실패: {e}[/red]")

def test_client_functionality():
    """투자의견 클라이언트 기능 테스트"""
    console.print("\n🧪 [bold blue]투자의견 클라이언트 기능 테스트[/bold blue]")
    console.print("="*60)
    
    client = InvestmentOpinionClient()
    
    # 기본 조회 테스트
    symbol = "005930"
    console.print(f"\n📊 [bold yellow]{symbol} 투자의견 조회 테스트[/bold yellow]")
    
    try:
        # 최근 의견 조회
        recent_opinions = client.get_recent_opinions(symbol, limit=5)
        console.print(f"✅ 최근 {len(recent_opinions)}건의 투자의견 조회 완료")
        
        if recent_opinions:
            table = Table(title=f"{symbol} 최근 투자의견")
            table.add_column("날짜", style="cyan")
            table.add_column("증권사", style="white")
            table.add_column("의견", style="yellow")
            table.add_column("목표가", style="green")
            table.add_column("상승률", style="magenta")
            table.add_column("변경여부", style="red")
            
            for opinion in recent_opinions[:5]:  # 최대 5개만 표시
                table.add_row(
                    opinion.business_date,
                    opinion.brokerage_firm,
                    opinion.current_opinion,
                    f"{opinion.target_price:,}" if opinion.target_price > 0 else "-",
                    f"{opinion.price_target_upside:+.1f}%" if opinion.price_target_upside != 0 else "-",
                    opinion.opinion_change
                )
            
            console.print(table)
        
        # 의견 변경 조회
        console.print(f"\n🔄 [bold yellow]{symbol} 의견 변경 조회 테스트[/bold yellow]")
        changed_opinions = client.get_opinion_changes(symbol, days_back=30)
        console.print(f"✅ 최근 30일간 의견 변경: {len(changed_opinions)}건")
        
        # 증권사별 요약
        console.print(f"\n🏢 [bold yellow]{symbol} 증권사별 요약 테스트[/bold yellow]")
        brokerage_summary = client.get_brokerage_summary(symbol, days_back=30)
        console.print(f"✅ 참여 증권사: {len(brokerage_summary)}개")
        
        if brokerage_summary:
            table = Table(title="증권사별 요약")
            table.add_column("증권사", style="cyan")
            table.add_column("의견 수", style="white")
            table.add_column("최근 의견", style="yellow")
            table.add_column("평균 목표가", style="green")
            
            for firm, summary in list(brokerage_summary.items())[:5]:  # 상위 5개만 표시
                table.add_row(
                    firm,
                    str(summary['count']),
                    summary['latest_opinion'],
                    f"{summary.get('avg_target_price', 0):,.0f}" if summary.get('avg_target_price') else "-"
                )
            
            console.print(table)
        
    except Exception as e:
        console.print(f"[red]❌ 클라이언트 테스트 실패: {e}[/red]")

def test_data_export():
    """데이터 내보내기 테스트"""
    console.print("\n🧪 [bold blue]데이터 내보내기 테스트[/bold blue]")
    console.print("="*60)
    
    analyzer = InvestmentOpinionAnalyzer()
    
    try:
        # 분석 수행
        analysis = analyzer.analyze_single_stock("005930", days_back=30)
        
        if analysis['status'] == 'success':
            # DataFrame으로 변환
            df = analyzer.export_to_dataframe(analysis)
            
            if not df.empty:
                console.print("✅ DataFrame 변환 성공")
                console.print(f"📊 데이터 형태: {df.shape}")
                console.print("\n데이터 미리보기:")
                console.print(df.to_string(index=False))
            else:
                console.print("⚠️ DataFrame이 비어있습니다.")
        else:
            console.print(f"[red]❌ 분석 실패로 DataFrame 생성 불가[/red]")
            
    except Exception as e:
        console.print(f"[red]❌ 데이터 내보내기 테스트 실패: {e}[/red]")

def main():
    """메인 테스트 함수"""
    console.print("🚀 [bold green]투자의견 API 테스트 시작[/bold green]")
    console.print("="*60)
    
    # 테스트 실행
    test_client_functionality()
    test_single_stock_analysis()
    test_multiple_stocks_analysis()
    test_data_export()
    
    console.print("\n✅ [bold green]모든 테스트 완료![/bold green]")

if __name__ == "__main__":
    main()

