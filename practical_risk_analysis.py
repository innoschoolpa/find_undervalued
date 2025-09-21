"""
실제 정성적 리스크 파악 실습 예제
투자자가 직접 활용할 수 있는 실용적인 정성적 리스크 분석 방법
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
import json

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PracticalRiskAnalyzer:
    """실용적인 정성적 리스크 분석기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_stock_qualitative_risks(self, symbol: str, name: str, sector: str) -> Dict[str, Any]:
        """종목별 정성적 리스크 분석"""
        
        print(f"\n🔍 {name}({symbol}) 정성적 리스크 분석")
        print("=" * 60)
        
        # 1. 정책 리스크 분석
        policy_risk = self._analyze_policy_risk(symbol, name, sector)
        
        # 2. ESG 리스크 분석
        esg_risk = self._analyze_esg_risk(symbol, name, sector)
        
        # 3. 시장 감정 리스크 분석
        sentiment_risk = self._analyze_sentiment_risk(symbol, name, sector)
        
        # 4. 경쟁 리스크 분석
        competition_risk = self._analyze_competition_risk(symbol, name, sector)
        
        # 5. 기술 리스크 분석
        technology_risk = self._analyze_technology_risk(symbol, name, sector)
        
        # 종합 분석
        comprehensive_analysis = self._comprehensive_risk_analysis({
            '정책_리스크': policy_risk,
            'ESG_리스크': esg_risk,
            '시장_감정_리스크': sentiment_risk,
            '경쟁_리스크': competition_risk,
            '기술_리스크': technology_risk
        })
        
        return comprehensive_analysis
    
    def _analyze_policy_risk(self, symbol: str, name: str, sector: str) -> Dict[str, Any]:
        """정책 리스크 분석"""
        print("\n🏛️ 정책 리스크 분석")
        print("-" * 30)
        
        # 업종별 정책 리스크 체크리스트
        policy_checklists = {
            '게임업': [
                '청소년 보호법 개정 추진 여부',
                '게임 시간 제한 정책 변화',
                '게임 과금 규제 강화',
                '해외 진출 시 현지 규제 환경',
                '정부의 게임 산업 지원 정책'
            ],
            '반도체': [
                '미중 무역 갈등 진행 상황',
                '반도체 수출 규제 변화',
                '한국 정부의 반도체 지원 정책',
                '글로벌 반도체 공급망 정책',
                '기술 수출 통제 강화'
            ],
            '제조업': [
                '환경 규제 강화',
                '탄소 중립 정책 영향',
                '무역 정책 변화',
                '산업 정책 방향성',
                '노동 정책 변화'
            ]
        }
        
        checklist = policy_checklists.get(sector, policy_checklists['제조업'])
        
        print("정책 리스크 체크리스트:")
        risk_score = 0
        risk_factors = []
        
        for i, item in enumerate(checklist, 1):
            # 실제로는 뉴스 검색, 정부 발표 확인 등을 통해 평가
            # 여기서는 예시로 랜덤하게 평가
            import random
            is_risk = random.choice([True, False])
            
            if is_risk:
                risk_score += random.randint(10, 20)
                risk_factors.append(f"⚠️ {item}")
                print(f"   {i}. ⚠️ {item} (리스크 발견)")
            else:
                print(f"   {i}. ✅ {item} (정상)")
        
        risk_level = self._get_risk_level(risk_score)
        
        return {
            'score': risk_score,
            'level': risk_level,
            'factors': risk_factors,
            'checklist': checklist
        }
    
    def _analyze_esg_risk(self, symbol: str, name: str, sector: str) -> Dict[str, Any]:
        """ESG 리스크 분석"""
        print("\n🌱 ESG 리스크 분석")
        print("-" * 30)
        
        esg_categories = {
            '환경(E)': [
                '탄소 배출량 관리',
                '에너지 효율성',
                '환경 오염 방지',
                '재생에너지 사용',
                '폐기물 관리'
            ],
            '사회(S)': [
                '직원 안전 관리',
                '노동 권리 보장',
                '지역사회 기여',
                '고객 보호',
                '공급망 관리'
            ],
            '지배구조(G)': [
                '이사회 독립성',
                '내부 통제 시스템',
                '윤리 경영',
                '투명한 공시',
                '주주 권리 보호'
            ]
        }
        
        risk_score = 0
        esg_risks = {}
        
        for category, items in esg_categories.items():
            print(f"\n{category} 평가:")
            category_score = 0
            
            for item in items:
                # 실제로는 ESG 리포트, 뉴스 분석 등을 통해 평가
                import random
                score = random.randint(0, 20)
                category_score += score
                
                if score > 15:
                    print(f"   ⚠️ {item} (높은 리스크: {score}점)")
                elif score > 10:
                    print(f"   ⚠️ {item} (보통 리스크: {score}점)")
                else:
                    print(f"   ✅ {item} (낮은 리스크: {score}점)")
            
            esg_risks[category] = category_score
            risk_score += category_score
        
        risk_level = self._get_risk_level(risk_score)
        
        return {
            'score': risk_score,
            'level': risk_level,
            'categories': esg_risks,
            'details': esg_categories
        }
    
    def _analyze_sentiment_risk(self, symbol: str, name: str, sector: str) -> Dict[str, Any]:
        """시장 감정 리스크 분석"""
        print("\n📈 시장 감정 리스크 분석")
        print("-" * 30)
        
        sentiment_indicators = {
            '뉴스 감정': {
                '긍정적 뉴스': 0,
                '부정적 뉴스': 0,
                '중립적 뉴스': 0
            },
            '분석가 의견': {
                '매수 의견': 0,
                '보유 의견': 0,
                '매도 의견': 0
            },
            '투자자 심리': {
                '공포/탐욕 지수': 50,  # 0-100 (50이 중립)
                'VIX 지수': 20,       # 변동성 지수
                '펀드 플로우': 0       # 자금 유입/유출
            },
            '소셜미디어': {
                '긍정적 언급': 0,
                '부정적 언급': 0,
                '중립적 언급': 0
            }
        }
        
        # 실제로는 뉴스 API, 소셜미디어 API 등을 통해 데이터 수집
        # 여기서는 예시 데이터
        import random
        
        # 뉴스 감정 분석
        sentiment_indicators['뉴스 감정']['긍정적 뉴스'] = random.randint(5, 15)
        sentiment_indicators['뉴스 감정']['부정적 뉴스'] = random.randint(3, 12)
        sentiment_indicators['뉴스 감정']['중립적 뉴스'] = random.randint(8, 20)
        
        # 분석가 의견
        sentiment_indicators['분석가 의견']['매수 의견'] = random.randint(3, 8)
        sentiment_indicators['분석가 의견']['보유 의견'] = random.randint(2, 5)
        sentiment_indicators['분석가 의견']['매도 의견'] = random.randint(0, 3)
        
        # 소셜미디어 감정
        sentiment_indicators['소셜미디어']['긍정적 언급'] = random.randint(10, 30)
        sentiment_indicators['소셜미디어']['부정적 언급'] = random.randint(5, 20)
        sentiment_indicators['소셜미디어']['중립적 언급'] = random.randint(15, 40)
        
        print("시장 감정 지표:")
        risk_score = 0
        
        # 뉴스 감정 분석
        news_sentiment = sentiment_indicators['뉴스 감정']
        positive_ratio = news_sentiment['긍정적 뉴스'] / sum(news_sentiment.values())
        if positive_ratio < 0.3:
            risk_score += 30
        elif positive_ratio < 0.5:
            risk_score += 15
        
        print(f"   📰 뉴스 감정: 긍정 {news_sentiment['긍정적 뉴스']}건, "
              f"부정 {news_sentiment['부정적 뉴스']}건, 중립 {news_sentiment['중립적 뉴스']}건")
        
        # 분석가 의견
        analyst_opinion = sentiment_indicators['분석가 의견']
        buy_ratio = analyst_opinion['매수 의견'] / sum(analyst_opinion.values())
        if buy_ratio < 0.4:
            risk_score += 20
        elif buy_ratio < 0.6:
            risk_score += 10
        
        print(f"   📊 분석가 의견: 매수 {analyst_opinion['매수 의견']}건, "
              f"보유 {analyst_opinion['보유 의견']}건, 매도 {analyst_opinion['매도 의견']}건")
        
        # 투자자 심리
        investor_sentiment = sentiment_indicators['투자자 심리']
        fear_greed = investor_sentiment['공포/탐욕 지수']
        if fear_greed < 30:  # 공포 상태
            risk_score += 25
        elif fear_greed > 70:  # 탐욕 상태
            risk_score += 15
        
        print(f"   😰😍 투자자 심리: 공포/탐욕 지수 {fear_greed}")
        
        risk_level = self._get_risk_level(risk_score)
        
        return {
            'score': risk_score,
            'level': risk_level,
            'indicators': sentiment_indicators
        }
    
    def _analyze_competition_risk(self, symbol: str, name: str, sector: str) -> Dict[str, Any]:
        """경쟁 리스크 분석"""
        print("\n🏆 경쟁 리스크 분석")
        print("-" * 30)
        
        competition_factors = {
            '시장 점유율': {
                '현재 점유율': 0,
                '경쟁사 점유율': {},
                '점유율 변화 추이': '안정'
            },
            '경쟁사 분석': {
                '주요 경쟁사': [],
                '신규 진입자': [],
                '기술 경쟁력': '보통'
            },
            '가격 경쟁': {
                '가격 경쟁력': '보통',
                '차별화 요소': [],
                '고객 충성도': '보통'
            }
        }
        
        # 실제로는 업계 리포트, 경쟁사 분석 등을 통해 평가
        import random
        
        # 시장 점유율 (예시)
        current_share = random.randint(5, 25)
        competition_factors['시장 점유율']['현재 점유율'] = current_share
        
        # 경쟁사 점유율
        competitors = ['경쟁사A', '경쟁사B', '경쟁사C']
        for competitor in competitors:
            competition_factors['시장 점유율']['경쟁사 점유율'][competitor] = random.randint(10, 30)
        
        competition_factors['경쟁사 분석']['주요 경쟁사'] = competitors
        
        risk_score = 0
        
        # 점유율 기반 리스크
        if current_share < 10:
            risk_score += 30
        elif current_share < 20:
            risk_score += 15
        
        print(f"   📊 시장 점유율: {current_share}%")
        print(f"   🏢 주요 경쟁사: {', '.join(competitors)}")
        
        # 신규 진입자 위협
        if random.choice([True, False]):
            risk_score += 20
            print("   ⚠️ 신규 진입자 위협 발견")
        else:
            print("   ✅ 신규 진입자 위협 낮음")
        
        risk_level = self._get_risk_level(risk_score)
        
        return {
            'score': risk_score,
            'level': risk_level,
            'factors': competition_factors
        }
    
    def _analyze_technology_risk(self, symbol: str, name: str, sector: str) -> Dict[str, Any]:
        """기술 리스크 분석"""
        print("\n🔬 기술 리스크 분석")
        print("-" * 30)
        
        tech_factors = {
            'R&D 투자': {
                'R&D 비중': 0,
                'R&D 투자 증가율': 0,
                '경쟁사 대비 R&D 수준': '보통'
            },
            '기술 혁신': {
                '기술 혁신 속도': '보통',
                '신기술 도입 능력': '보통',
                '기술 특허 보유': 0
            },
            '기술 대체': {
                '대체 기술 위협': '낮음',
                '기술 생명주기': '성숙기',
                '차세대 기술 준비': '보통'
            }
        }
        
        # 실제로는 기업 공시, 특허 데이터, 업계 리포트 등을 통해 평가
        import random
        
        # R&D 투자 분석
        rnd_ratio = random.randint(3, 15)
        tech_factors['R&D 투자']['R&D 비중'] = rnd_ratio
        
        if rnd_ratio < 5:
            risk_score = 40
        elif rnd_ratio < 10:
            risk_score = 20
        else:
            risk_score = 10
        
        print(f"   💰 R&D 투자 비중: {rnd_ratio}%")
        
        # 기술 혁신 평가
        innovation_speed = random.choice(['빠름', '보통', '느림'])
        tech_factors['기술 혁신']['기술 혁신 속도'] = innovation_speed
        
        if innovation_speed == '느림':
            risk_score += 30
        elif innovation_speed == '보통':
            risk_score += 15
        
        print(f"   🚀 기술 혁신 속도: {innovation_speed}")
        
        # 특허 보유 수
        patent_count = random.randint(10, 100)
        tech_factors['기술 혁신']['기술 특허 보유'] = patent_count
        print(f"   📜 특허 보유 수: {patent_count}건")
        
        risk_level = self._get_risk_level(risk_score)
        
        return {
            'score': risk_score,
            'level': risk_level,
            'factors': tech_factors
        }
    
    def _get_risk_level(self, score: int) -> str:
        """리스크 점수에 따른 레벨 결정"""
        if score >= 80:
            return "매우 높음"
        elif score >= 60:
            return "높음"
        elif score >= 40:
            return "보통"
        elif score >= 20:
            return "낮음"
        else:
            return "매우 낮음"
    
    def _comprehensive_risk_analysis(self, risk_analyses: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """종합 리스크 분석"""
        print("\n📊 종합 리스크 분석")
        print("-" * 30)
        
        total_score = 0
        risk_count = 0
        risk_summary = {}
        
        for risk_type, analysis in risk_analyses.items():
            score = analysis['score']
            level = analysis['level']
            total_score += score
            risk_count += 1
            
            risk_summary[risk_type] = {
                'score': score,
                'level': level
            }
            
            print(f"   {risk_type}: {score}점 ({level})")
        
        average_score = total_score / risk_count if risk_count > 0 else 0
        overall_level = self._get_risk_level(average_score)
        
        print(f"\n🎯 종합 리스크: {average_score:.1f}점 ({overall_level})")
        
        # 투자 권고사항
        recommendations = self._get_investment_recommendations(average_score, risk_summary)
        
        return {
            'overall_score': average_score,
            'overall_level': overall_level,
            'individual_risks': risk_summary,
            'recommendations': recommendations,
            'analysis_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def _get_investment_recommendations(self, overall_score: float, risk_summary: Dict[str, Any]) -> List[str]:
        """투자 권고사항 생성"""
        recommendations = []
        
        if overall_score >= 70:
            recommendations.extend([
                "투자 비중을 크게 축소하거나 투자를 연기하는 것을 고려",
                "고위험 요소들을 면밀히 모니터링",
                "대안 투자처 검토"
            ])
        elif overall_score >= 50:
            recommendations.extend([
                "투자 비중을 신중하게 조절",
                "주요 리스크 요소들을 지속적으로 모니터링",
                "분산 투자 전략 고려"
            ])
        elif overall_score >= 30:
            recommendations.extend([
                "정상적인 투자 진행 가능",
                "주요 리스크 변화에 주의",
                "정기적인 리스크 재평가"
            ])
        else:
            recommendations.extend([
                "적극적인 투자 고려 가능",
                "리스크 관리 체계 유지",
                "기회 활용 전략 수립"
            ])
        
        # 개별 리스크별 권고사항
        for risk_type, analysis in risk_summary.items():
            if analysis['score'] >= 60:
                if risk_type == '정책_리스크':
                    recommendations.append("정부 정책 변화를 면밀히 추적")
                elif risk_type == 'ESG_리스크':
                    recommendations.append("ESG 관련 이슈를 지속적으로 모니터링")
                elif risk_type == '시장_감정_리스크':
                    recommendations.append("시장 심리 변화에 민감하게 대응")
                elif risk_type == '경쟁_리스크':
                    recommendations.append("경쟁 환경 변화를 주의 깊게 관찰")
                elif risk_type == '기술_리스크':
                    recommendations.append("기술 트렌드 변화를 면밀히 추적")
        
        return recommendations

def main():
    """메인 함수"""
    analyzer = PracticalRiskAnalyzer()
    
    # 테스트 종목들
    test_stocks = [
        ("462870", "시프트업", "게임업"),
        ("042700", "한미반도체", "반도체"),
        ("000270", "기아", "제조업")
    ]
    
    print("🎯 정성적 리스크 파악 실습")
    print("=" * 60)
    
    for symbol, name, sector in test_stocks:
        try:
            result = analyzer.analyze_stock_qualitative_risks(symbol, name, sector)
            
            print(f"\n📋 {name} 최종 투자 권고사항:")
            print("-" * 40)
            for i, recommendation in enumerate(result['recommendations'], 1):
                print(f"   {i}. {recommendation}")
            
            print(f"\n⏰ 분석 일시: {result['analysis_date']}")
            
        except Exception as e:
            print(f"❌ {name} 분석 실패: {e}")
        
        print("\n" + "=" * 60)
    
    print("\n💡 정성적 리스크 파악의 핵심:")
    print("1. 📰 지속적인 정보 수집과 모니터링")
    print("2. 🔍 다양한 관점에서의 종합적 분석")
    print("3. ⚖️ 정량적 지표와의 균형잡힌 평가")
    print("4. 🎯 업종별 특성을 고려한 맞춤형 분석")
    print("5. 📈 시장 상황과 투자 목표에 따른 적응적 평가")

if __name__ == "__main__":
    main()

