#!/usr/bin/env python3
"""
가치 투자 철학 테스트 스크립트
- 워렌 버핏 스타일의 가치 투자 원칙 테스트
- 4대 핵심 원칙과 5단계 실행 계획 검증
"""

from enhanced_integrated_analyzer_refactored import EnhancedIntegratedAnalyzer

def test_value_investing_philosophy():
    """가치 투자 철학 테스트"""
    print("가치 투자 철학 테스트 시작...")
    print("=" * 60)
    
    analyzer = EnhancedIntegratedAnalyzer()
    
    try:
        # 테스트 종목들
        test_stocks = [
            ('005930', '삼성전자'),
            ('271560', '오리온'),
            ('000660', 'SK하이닉스'),
            ('035420', 'NAVER'),
            ('207940', '삼성바이오로직스')
        ]
        
        print(f"\n[가치 투자 철학 기반 분석]")
        print("=" * 60)
        
        for symbol, name in test_stocks:
            print(f"\n--- {name} ({symbol}) 가치 투자 분석 ---")
            
            try:
                # 가치 투자 철학 기반 분석
                result = analyzer.analyze_with_value_philosophy(symbol, name)
                
                if result['success']:
                    basic_result = result['basic_result']
                    value_analysis = result['value_analysis']
                    buy_signal = result['buy_signal']
                    
                    print(f"기본 분석 점수: {basic_result.enhanced_score:.1f}점 ({basic_result.enhanced_grade})")
                    print(f"현재가: {basic_result.current_price:,.0f}원")
                    
                    if value_analysis:
                        print(f"내재가치: {value_analysis.intrinsic_value.fair_value:,.0f}원")
                        print(f"안전마진: {value_analysis.margin_of_safety.discount_percentage:.1f}%")
                        print(f"안전마진 수준: {value_analysis.margin_of_safety.safety_level.value}")
                        print(f"매수 신호: {'예' if buy_signal else '아니오'}")
                        
                        # 비즈니스 분석 점수
                        business = value_analysis.business_analysis
                        print(f"비즈니스 모델: {business.business_model_score:.1f}/100")
                        print(f"경쟁 우위: {business.competitive_advantage_score:.1f}/100")
                        print(f"재무 건전성: {business.financial_strength_score:.1f}/100")
                        
                        # 경제적 해자
                        if business.moats:
                            print("경제적 해자:")
                            for moat in business.moats:
                                print(f"  - {moat.moat_type.value}: {moat.strength:.1f}점")
                    else:
                        print("가치 투자 분석을 사용할 수 없습니다.")
                    
                    print(f"가치 투자 리포트:")
                    print(result['value_report'])
                    
                else:
                    print(f"분석 실패: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"분석 중 오류: {e}")
            
            print("-" * 40)
        
        # 매수 신호가 있는 종목들 조회
        print(f"\n[매수 신호가 있는 종목들]")
        print("=" * 60)
        
        if hasattr(analyzer, 'value_investing'):
            buy_signals = analyzer.value_investing.get_buy_signals()
            if buy_signals:
                for item in buy_signals:
                    print(f"{item.name} ({item.symbol}): {item.margin_of_safety.recommendation}")
                    print(f"  현재가: {item.current_price:,.0f}원")
                    print(f"  목표가: {item.target_buy_price:,.0f}원")
                    print(f"  안전마진: {item.margin_of_safety.discount_percentage:.1f}%")
            else:
                print("현재 매수 신호가 있는 종목이 없습니다.")
        else:
            print("가치 투자 철학 모듈을 사용할 수 없습니다.")
        
        print(f"\n[가치 투자 철학 요약]")
        print("=" * 60)
        print("1. 기업을 사라 (Buy a Business, Not a Stock)")
        print("   - 주식이 아닌 실제 사업의 소유권을 구매")
        print("   - 비즈니스 모델과 경쟁 우위를 철저히 분석")
        
        print("\n2. 안전마진을 확보하라 (Margin of Safety)")
        print("   - 내재가치 대비 할인된 가격에 매수")
        print("   - 미래 예측의 불확실성에 대한 보호막")
        
        print("\n3. 경제적 해자를 찾아라 (Economic Moat)")
        print("   - 지속 가능한 경쟁 우위 확보")
        print("   - 무형자산, 네트워크 효과, 비용 우위 등")
        
        print("\n4. 올바른 기질을 갖춰라 (Right Temperament)")
        print("   - 인내심과 독립적 사고")
        print("   - 시장의 소음에 흔들리지 않는 정신력")
        
        print("\n5단계 실행 계획:")
        print("1. 목록 작성 - 소유하고 싶은 훌륭한 기업 목록")
        print("2. 가치 평가 - 내재가치를 보수적으로 추정")
        print("3. 매수 가격 설정 - 안전마진을 확보할 수 있는 가격")
        print("4. 기다림 - 정해둔 가격에 도달할 때까지 대기")
        print("5. 결정적 행동 - 기회가 왔을 때 단호하게 매수")
        
    except Exception as e:
        print(f"테스트 실패: {e}")
    
    finally:
        analyzer.close()
        print(f"\n[테스트 완료]")

if __name__ == "__main__":
    test_value_investing_philosophy()


