#!/usr/bin/env python3
"""
오리온(271560) 종목 종합 분석
"""

from enhanced_integrated_analyzer_refactored import EnhancedIntegratedAnalyzer
from price_display_enhancer import display_detailed_price_info

def analyze_orion():
    """오리온 종목 종합 분석"""
    print("오리온(271560) 종합 분석 시작...")
    print("=" * 60)
    
    analyzer = EnhancedIntegratedAnalyzer()
    
    try:
        # 오리온 종목 분석
        result = analyzer.analyze_single_stock('271560', '오리온')
        
        print(f"\n[기본 정보]")
        print(f"종목명: {result.name} ({result.symbol})")
        print(f"종합 점수: {result.enhanced_score:.1f}점 ({result.enhanced_grade})")
        print(f"분석 상태: {result.status}")
        
        # 상세 가격 정보 표시
        price_data = {
            'symbol': result.symbol,
            'name': result.name,
            'current_price': result.current_price,
            'w52_high': result.price_data.get('w52_high') if result.price_data else None,
            'w52_low': result.price_data.get('w52_low') if result.price_data else None,
            'market_cap': result.market_cap
        }
        
        print(display_detailed_price_info(price_data))
        
        # 재무 정보
        print(f"\n[재무 정보]")
        if result.financial_data:
            print(f"ROE: {result.financial_data.get('roe', 'N/A')}%")
            print(f"ROA: {result.financial_data.get('roa', 'N/A')}%")
            print(f"부채비율: {result.financial_data.get('debt_ratio', 'N/A')}%")
            print(f"자기자본비율: {result.financial_data.get('equity_ratio', 'N/A')}%")
            print(f"매출증가율: {result.financial_data.get('revenue_growth_rate', 'N/A')}%")
            print(f"영업이익증가율: {result.financial_data.get('operating_income_growth_rate', 'N/A')}%")
            print(f"순이익증가율: {result.financial_data.get('net_income_growth_rate', 'N/A')}%")
            print(f"순이익률: {result.financial_data.get('net_profit_margin', 'N/A')}%")
            print(f"영업이익률: {result.financial_data.get('gross_profit_margin', 'N/A')}%")
            print(f"유동비율: {result.financial_data.get('current_ratio', 'N/A')}")
        
        # 가격 정보
        print(f"\n[가격 정보]")
        if result.price_data:
            print(f"PER: {result.price_data.get('per', 'N/A')}배")
            print(f"PBR: {result.price_data.get('pbr', 'N/A')}배")
            print(f"EPS: {result.price_data.get('eps', 'N/A')}원")
            print(f"BPS: {result.price_data.get('bps', 'N/A')}원")
            print(f"거래량: {result.price_data.get('volume', 'N/A'):,}주" if result.price_data.get('volume') else "거래량: N/A")
        
        # 투자의견 분석
        print(f"\n[투자의견 분석]")
        if result.opinion_analysis:
            print(f"매수 의견: {result.opinion_analysis.get('buy', 'N/A')}개")
            print(f"보유 의견: {result.opinion_analysis.get('hold', 'N/A')}개")
            print(f"매도 의견: {result.opinion_analysis.get('sell', 'N/A')}개")
            print(f"목표가: {result.opinion_analysis.get('target_price', 'N/A')}원")
            print(f"요약: {result.opinion_analysis.get('summary', 'N/A')}")
        
        # 추정실적 분석
        print(f"\n[추정실적 분석]")
        if result.estimate_analysis:
            print(f"정확도: {result.estimate_analysis.get('accuracy', 'N/A')}")
            print(f"편향도: {result.estimate_analysis.get('bias', 'N/A')}")
            print(f"수정 추세: {result.estimate_analysis.get('revision_trend', 'N/A')}")
            print(f"요약: {result.estimate_analysis.get('summary', 'N/A')}")
        
        # 섹터 분석
        print(f"\n[섹터 분석]")
        if result.sector_analysis:
            print(f"섹터 등급: {result.sector_analysis.get('grade', 'N/A')}")
            print(f"섹터 점수: {result.sector_analysis.get('total_score', 'N/A')}")
            print(f"섹터 리더 여부: {'예' if result.sector_analysis.get('is_leader', False) else '아니오'}")
            print(f"기본 점수: {result.sector_analysis.get('base_score', 'N/A')}")
            print(f"리더 보너스: {result.sector_analysis.get('leader_bonus', 'N/A')}")
        
        # 점수 세부 내역
        print(f"\n[점수 세부 내역]")
        if result.score_breakdown:
            for key, value in result.score_breakdown.items():
                print(f"{key}: {value:.1f}점")
        
        # 투자 추천
        print(f"\n[투자 추천]")
        if result.enhanced_score >= 80:
            recommendation = "강력 매수"
        elif result.enhanced_score >= 70:
            recommendation = "매수"
        elif result.enhanced_score >= 60:
            recommendation = "신중한 매수"
        elif result.enhanced_score >= 50:
            recommendation = "보유"
        else:
            recommendation = "매도 고려"
        
        print(f"종합 추천: {recommendation}")
        print(f"근거: 종합 점수 {result.enhanced_score:.1f}점으로 {result.enhanced_grade} 등급")
        
        # 리스크 분석
        print(f"\n[리스크 분석]")
        if result.risk_score:
            print(f"리스크 점수: {result.risk_score:.1f}")
            if result.risk_score >= 70:
                risk_level = "높음"
            elif result.risk_score >= 50:
                risk_level = "보통"
            else:
                risk_level = "낮음"
            print(f"리스크 수준: {risk_level}")
        
        if result.error:
            print(f"\n[분석 중 오류] {result.error}")
        
    except Exception as e:
        print(f"[분석 실패] {e}")
    
    finally:
        analyzer.close()
        print(f"\n[분석 완료]")

if __name__ == "__main__":
    analyze_orion()
