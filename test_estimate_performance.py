# test_estimate_performance.py
import logging
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from estimate_performance_analyzer import EstimatePerformanceAnalyzer
from estimate_performance_client import EstimatePerformanceClient

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

# Rich Console 초기화
console = Console()

def test_single_stock_analysis():
    """단일 종목 추정실적 분석 테스트"""
    console.print("\n🧪 [bold blue]단일 종목 추정실적 분석 테스트[/bold blue]")
    console.print("="*60)
    
    analyzer = EstimatePerformanceAnalyzer()
    
    # 삼성전자 테스트
    symbol = "005930"
    console.print(f"\n📊 [bold yellow]{symbol} (삼성전자) 추정실적 분석[/bold yellow]")
    
    try:
        analysis = analyzer.analyze_single_stock(symbol)
        
        if analysis['status'] == 'success':
            # 요약 정보 표시
            summary = analysis['summary']
            
            table = Table(title=f"{symbol} 추정실적 요약")
            table.add_column("항목", style="cyan")
            table.add_column("값", style="green")
            
            table.add_row("종목명", summary.name)
            table.add_row("현재가", f"{summary.current_price:,}원")
            table.add_row("등락률", f"{summary.change_rate:+.2f}%")
            table.add_row("", "")  # 빈 행
            
            table.add_row("매출액", f"{summary.latest_revenue:,.0f}원")
            table.add_row("매출액 성장률", f"{summary.latest_revenue_growth:+.1f}%")
            table.add_row("영업이익", f"{summary.latest_operating_profit:,.0f}원")
            table.add_row("영업이익 성장률", f"{summary.latest_operating_profit_growth:+.1f}%")
            table.add_row("순이익", f"{summary.latest_net_profit:,.0f}원")
            table.add_row("순이익 성장률", f"{summary.latest_net_profit_growth:+.1f}%")
            table.add_row("", "")  # 빈 행
            
            table.add_row("EPS", f"{summary.latest_eps:,.0f}원")
            table.add_row("PER", f"{summary.latest_per:.1f}배")
            table.add_row("ROE", f"{summary.latest_roe:.1f}%")
            table.add_row("EV/EBITDA", f"{summary.latest_ev_ebitda:.1f}배")
            table.add_row("", "")  # 빈 행
            
            table.add_row("매출액 트렌드", summary.revenue_trend)
            table.add_row("영업이익 트렌드", summary.profit_trend)
            table.add_row("EPS 트렌드", summary.eps_trend)
            table.add_row("데이터 품질", f"{summary.data_quality_score:.2f}")
            table.add_row("최근 업데이트", summary.latest_update_date)
            
            console.print(table)
            
            # 상세 보고서 생성
            report = analyzer.generate_report(analysis)
            console.print(Panel(report, title="📋 상세 분석 보고서", border_style="green"))
            
            # 재무건전성 분석
            financial_health = analysis.get('financial_health', {})
            if financial_health:
                console.print("\n💪 [bold yellow]재무건전성 분석[/bold yellow]")
                console.print(f"종합 점수: {financial_health.get('health_score', 0)}/100점 ({financial_health.get('health_grade', 'N/A')}등급)")
                
                factors = financial_health.get('factors', [])
                if factors:
                    console.print("주요 요인:")
                    for factor in factors:
                        console.print(f"  • {factor}")
            
            # 밸류에이션 분석
            valuation = analysis.get('valuation_analysis', {})
            if valuation:
                console.print("\n💰 [bold yellow]밸류에이션 분석[/bold yellow]")
                console.print(f"종합 점수: {valuation.get('overall_score', 0)}/100점 ({valuation.get('overall_grade', 'N/A')}등급)")
                
                if 'per' in valuation:
                    per_data = valuation['per']
                    console.print(f"PER: {per_data['value']:.1f}배 ({per_data['grade']}등급) - {per_data['interpretation']}")
                
                if 'ev_ebitda' in valuation:
                    ev_ebitda_data = valuation['ev_ebitda']
                    console.print(f"EV/EBITDA: {ev_ebitda_data['value']:.1f}배 ({ev_ebitda_data['grade']}등급) - {ev_ebitda_data['interpretation']}")
            
            # 성장성 분석
            growth = analysis.get('growth_analysis', {})
            if growth:
                console.print("\n📈 [bold yellow]성장성 분석[/bold yellow]")
                
                if 'revenue_growth' in growth:
                    revenue_growth_data = growth['revenue_growth']
                    console.print(f"매출액 성장률: {revenue_growth_data['value']:+.1f}% ({revenue_growth_data['grade']}등급) - {revenue_growth_data['interpretation']}")
                
                if 'profit_growth' in growth:
                    profit_growth_data = growth['profit_growth']
                    console.print(f"영업이익 성장률: {profit_growth_data['value']:+.1f}% ({profit_growth_data['grade']}등급) - {profit_growth_data['interpretation']}")
                
                if 'eps_growth' in growth:
                    eps_growth_data = growth['eps_growth']
                    console.print(f"EPS 성장률: {eps_growth_data['value']:+.1f}% ({eps_growth_data['grade']}등급) - {eps_growth_data['interpretation']}")
        
        else:
            console.print(f"[red]❌ 분석 실패: {analysis.get('message', '알 수 없는 오류')}[/red]")
            
    except Exception as e:
        console.print(f"[red]❌ 테스트 실패: {e}[/red]")

def test_multiple_stocks_analysis():
    """다중 종목 추정실적 비교 분석 테스트"""
    console.print("\n🧪 [bold blue]다중 종목 추정실적 비교 분석 테스트[/bold blue]")
    console.print("="*60)
    
    analyzer = EstimatePerformanceAnalyzer()
    
    # 주요 종목들
    symbols = ["005930", "000660", "035420", "051910"]  # 삼성전자, SK하이닉스, NAVER, LG화학
    
    console.print(f"\n📊 [bold yellow]{len(symbols)}개 종목 추정실적 비교 분석[/bold yellow]")
    
    try:
        analysis = analyzer.analyze_multiple_stocks(symbols)
        
        console.print(f"✅ 분석 완료: {analysis['successful_analyses']}/{analysis['total_stocks']}개 종목")
        
        # 종목별 요약 테이블
        table = Table(title="종목별 추정실적 요약")
        table.add_column("종목코드", style="cyan")
        table.add_column("종목명", style="white")
        table.add_column("현재가", style="green")
        table.add_column("매출액(억)", style="blue")
        table.add_column("매출성장률", style="magenta")
        table.add_column("영업이익(억)", style="yellow")
        table.add_column("EPS", style="red")
        table.add_column("PER", style="cyan")
        table.add_column("ROE", style="green")
        table.add_column("품질점수", style="white")
        
        for symbol, stock_analysis in analysis['stock_analyses'].items():
            if stock_analysis.get('status') == 'success':
                summary = stock_analysis['summary']
                table.add_row(
                    symbol,
                    summary.name[:10] + "..." if len(summary.name) > 10 else summary.name,
                    f"{summary.current_price:,}",
                    f"{summary.latest_revenue/100000000:.0f}",
                    f"{summary.latest_revenue_growth:+.1f}%",
                    f"{summary.latest_operating_profit/100000000:.0f}",
                    f"{summary.latest_eps:,.0f}",
                    f"{summary.latest_per:.1f}",
                    f"{summary.latest_roe:.1f}%",
                    f"{summary.data_quality_score:.2f}"
                )
            else:
                table.add_row(symbol, "오류", "-", "-", "-", "-", "-", "-", "-", "-")
        
        console.print(table)
        
        # 비교 분석 결과
        comparison = analysis.get('comparison_analysis', {})
        if comparison and comparison.get('status') != 'no_data':
            console.print("\n🏆 [bold yellow]비교 분석 결과[/bold yellow]")
            
            # PER 랭킹
            if 'per_ranking' in comparison:
                console.print("\n💰 [bold green]PER 랭킹 (낮을수록 저평가)[/bold green]")
                for i, (symbol, per) in enumerate(comparison['per_ranking'], 1):
                    console.print(f"  {i}. {symbol}: {per:.1f}배")
            
            # ROE 랭킹
            if 'roe_ranking' in comparison:
                console.print("\n📈 [bold green]ROE 랭킹 (높을수록 수익성 우수)[/bold green]")
                for i, (symbol, roe) in enumerate(comparison['roe_ranking'], 1):
                    console.print(f"  {i}. {symbol}: {roe:.1f}%")
        
    except Exception as e:
        console.print(f"[red]❌ 테스트 실패: {e}[/red]")

def test_client_functionality():
    """추정실적 클라이언트 기능 테스트"""
    console.print("\n🧪 [bold blue]추정실적 클라이언트 기능 테스트[/bold blue]")
    console.print("="*60)
    
    client = EstimatePerformanceClient()
    
    # 기본 조회 테스트
    symbol = "005930"
    console.print(f"\n📊 [bold yellow]{symbol} 추정실적 조회 테스트[/bold yellow]")
    
    try:
        # 추정실적 데이터 조회
        estimate_data = client.get_estimate_performance(symbol)
        
        if estimate_data:
            console.print(f"✅ 추정실적 데이터 조회 완료")
            console.print(f"종목명: {estimate_data.name}")
            console.print(f"현재가: {estimate_data.current_price:,}원")
            console.print(f"데이터 품질 점수: {estimate_data.data_quality_score:.2f}")
            console.print(f"최근 업데이트: {estimate_data.latest_update_date}")
            
            # 매출액 데이터
            if estimate_data.revenue_data:
                console.print(f"매출액 데이터: {len(estimate_data.revenue_data)}개월")
                console.print(f"최신 매출액: {estimate_data.revenue_data[0]:,.0f}원")
            
            # EPS 데이터
            if estimate_data.eps_data:
                console.print(f"EPS 데이터: {len(estimate_data.eps_data)}개월")
                console.print(f"최신 EPS: {estimate_data.eps_data[0]:,.0f}원")
            
            # PER 데이터
            if estimate_data.per_data:
                console.print(f"PER 데이터: {len(estimate_data.per_data)}개월")
                console.print(f"최신 PER: {estimate_data.per_data[0]:.1f}배")
            
        else:
            console.print(f"[yellow]⚠️ {symbol} 종목의 추정실적 데이터가 없습니다.[/yellow]")
        
        # 요약 정보 조회
        console.print(f"\n📋 [bold yellow]{symbol} 요약 정보 조회 테스트[/bold yellow]")
        summary = client.get_estimate_summary(symbol)
        
        if summary:
            console.print("✅ 요약 정보 조회 완료")
            console.print(f"종목명: {summary['name']}")
            console.print(f"현재가: {summary['current_price']:,}원")
            console.print(f"매출액: {summary['latest_revenue']:,.0f}원")
            console.print(f"영업이익: {summary['latest_operating_profit']:,.0f}원")
            console.print(f"EPS: {summary['latest_eps']:,.0f}원")
            console.print(f"PER: {summary['latest_per']:.1f}배")
            console.print(f"ROE: {summary['latest_roe']:.1f}%")
        else:
            console.print(f"[yellow]⚠️ {symbol} 종목의 요약 정보가 없습니다.[/yellow]")
        
        # 고품질 데이터 조회
        console.print(f"\n🎯 [bold yellow]고품질 추정실적 조회 테스트[/bold yellow]")
        symbols = ["005930", "000660", "035420"]
        high_quality_data = client.get_high_quality_estimates(symbols, min_quality_score=0.5)
        
        console.print(f"✅ 고품질 데이터 조회 완료: {len(high_quality_data)}/{len(symbols)}개 종목")
        
        if high_quality_data:
            table = Table(title="고품질 추정실적 종목")
            table.add_column("종목코드", style="cyan")
            table.add_column("종목명", style="white")
            table.add_column("품질점수", style="green")
            table.add_column("최신 EPS", style="blue")
            table.add_column("최신 PER", style="magenta")
            
            for symbol, data in high_quality_data.items():
                if data:
                    table.add_row(
                        symbol,
                        data.name[:10] + "..." if len(data.name) > 10 else data.name,
                        f"{data.data_quality_score:.2f}",
                        f"{data.eps_data[0]:,.0f}" if data.eps_data else "-",
                        f"{data.per_data[0]:.1f}" if data.per_data else "-"
                    )
            
            console.print(table)
        
    except Exception as e:
        console.print(f"[red]❌ 클라이언트 테스트 실패: {e}[/red]")

def test_data_export():
    """데이터 내보내기 테스트"""
    console.print("\n🧪 [bold blue]데이터 내보내기 테스트[/bold blue]")
    console.print("="*60)
    
    analyzer = EstimatePerformanceAnalyzer()
    
    try:
        # 분석 수행
        analysis = analyzer.analyze_single_stock("005930")
        
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
    console.print("🚀 [bold green]추정실적 API 테스트 시작[/bold green]")
    console.print("="*60)
    
    # 테스트 실행
    test_client_functionality()
    test_single_stock_analysis()
    test_multiple_stocks_analysis()
    test_data_export()
    
    console.print("\n✅ [bold green]모든 테스트 완료![/bold green]")

if __name__ == "__main__":
    main()
