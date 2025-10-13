#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
점수 설명 모듈 (XAI - Explainable AI)
'왜 이 점수인가?' 기여도 분해

작성: 2025-10-12
버전: v2.2.2
"""

import logging
from typing import Dict, List, Tuple
import pandas as pd

logger = logging.getLogger(__name__)


class ScoreExplainer:
    """
    점수 설명 및 기여도 분해
    
    사용자가 점수를 이해할 수 있도록 각 컴포넌트의 기여도를 계산하고 시각화
    """
    
    def __init__(self):
        """초기화"""
        # 최대 점수 구성
        self.max_scores = {
            'per': 20,
            'pbr': 20,
            'roe': 20,
            'quality': 43,  # FCF(15) + Coverage(10) + F-Score(18)
            'sector_bonus': 10,
            'mos': 35,
            'total': 148
        }
        
        logger.info("✅ ScoreExplainer 초기화 완료")
    
    def explain_score(self, evaluation_result: Dict) -> Dict:
        """
        점수 설명 생성
        
        Args:
            evaluation_result: evaluate_value_stock 결과
        
        Returns:
            설명 딕셔너리 (컴포넌트별 기여도, 백분율 등)
        """
        details = evaluation_result.get('details', {})
        total_score = evaluation_result.get('value_score', 0)
        
        # 컴포넌트별 점수
        components = {
            'PER': {
                'score': details.get('per_score', 0),
                'max': self.max_scores['per'],
                'description': 'PER 퍼센타일 점수'
            },
            'PBR': {
                'score': details.get('pbr_score', 0),
                'max': self.max_scores['pbr'],
                'description': 'PBR 퍼센타일 점수'
            },
            'ROE': {
                'score': details.get('roe_score', 0),
                'max': self.max_scores['roe'],
                'description': 'ROE 퍼센타일 점수'
            },
            '품질지표': {
                'score': details.get('quality_score', 0),
                'max': self.max_scores['quality'],
                'description': 'FCF Yield + Coverage + F-Score'
            },
            '섹터보너스': {
                'score': details.get('sector_bonus', 0),
                'max': self.max_scores['sector_bonus'],
                'description': '업종 기준 충족 보너스'
            },
            'MoS': {
                'score': details.get('mos_score', 0),
                'max': self.max_scores['mos'],
                'description': 'Margin of Safety (안전마진)'
            }
        }
        
        # 리스크 감점 (v2.2.2)
        risk_penalty = details.get('risk_penalty', 0)
        if risk_penalty != 0:
            components['리스크감점'] = {
                'score': risk_penalty,
                'max': 0,
                'description': '회계/이벤트/유동성 리스크'
            }
        
        # 백분율 계산
        for name, info in components.items():
            score = info['score']
            max_score = info['max']
            
            if max_score > 0:
                pct = (score / max_score) * 100
                info['percentage'] = pct
                info['contribution'] = (score / self.max_scores['total']) * 100
            else:
                info['percentage'] = 0
                info['contribution'] = (score / self.max_scores['total']) * 100  # 감점은 음수
        
        return {
            'total_score': total_score,
            'max_score': self.max_scores['total'],
            'score_percentage': (total_score / self.max_scores['total']) * 100,
            'components': components,
            'grade': evaluation_result.get('grade', 'N/A'),
            'recommendation': evaluation_result.get('recommendation', 'N/A')
        }
    
    def generate_explanation_text(self, explanation: Dict) -> str:
        """
        설명 텍스트 생성 (마크다운 형식)
        
        Args:
            explanation: explain_score 결과
        
        Returns:
            마크다운 텍스트
        """
        text = f"""## 📊 점수 상세 분석

**총점**: {explanation['total_score']:.1f}/{explanation['max_score']} ({explanation['score_percentage']:.1f}%)  
**등급**: {explanation['grade']}  
**추천**: {explanation['recommendation']}

### 🎯 컴포넌트별 기여도

"""
        
        components = explanation['components']
        
        # 기여도 순으로 정렬
        sorted_components = sorted(
            components.items(),
            key=lambda x: abs(x[1]['score']),
            reverse=True
        )
        
        for name, info in sorted_components:
            score = info['score']
            max_score = info['max']
            pct = info.get('percentage', 0)
            contribution = info.get('contribution', 0)
            desc = info['description']
            
            # 기호
            symbol = "✅" if score > 0 else ("⚠️" if score < 0 else "⚪")
            
            if max_score > 0:
                text += f"{symbol} **{name}**: {score:.1f}/{max_score} ({pct:.0f}%) - {desc}\n"
                text += f"   - 총점 기여: {contribution:+.1f}%\n\n"
            else:
                # 감점
                text += f"{symbol} **{name}**: {score:.1f}점 - {desc}\n"
                text += f"   - 총점 영향: {contribution:+.1f}%\n\n"
        
        return text
    
    def create_contribution_table(self, explanation: Dict) -> pd.DataFrame:
        """
        기여도 테이블 생성
        
        Args:
            explanation: explain_score 결과
        
        Returns:
            pandas DataFrame
        """
        components = explanation['components']
        
        rows = []
        for name, info in components.items():
            rows.append({
                '항목': name,
                '점수': f"{info['score']:.1f}",
                '최대': f"{info['max']}" if info['max'] > 0 else "-",
                '달성률': f"{info.get('percentage', 0):.0f}%" if info['max'] > 0 else "-",
                '기여도': f"{info.get('contribution', 0):+.1f}%",
                '설명': info['description']
            })
        
        df = pd.DataFrame(rows)
        
        # 기여도 절대값으로 정렬
        df['_abs_contribution'] = df['기여도'].str.rstrip('%').astype(float).abs()
        df = df.sort_values('_abs_contribution', ascending=False).drop('_abs_contribution', axis=1)
        
        return df
    
    def generate_improvement_suggestions(self, explanation: Dict) -> List[str]:
        """
        개선 제안 생성
        
        Args:
            explanation: explain_score 결과
        
        Returns:
            개선 제안 리스트
        """
        suggestions = []
        components = explanation['components']
        
        # 낮은 점수 항목 찾기 (50% 미만)
        for name, info in components.items():
            if info['max'] > 0:
                pct = info.get('percentage', 0)
                
                if pct < 50:
                    if name == 'PER':
                        suggestions.append("📉 PER이 높습니다. 섹터 평균보다 낮은 PER 종목을 고려하세요.")
                    elif name == 'PBR':
                        suggestions.append("📉 PBR이 높습니다. 장부가치 대비 저평가된 종목을 찾아보세요.")
                    elif name == 'ROE':
                        suggestions.append("📉 ROE가 낮습니다. 자본 효율성이 높은 종목을 선택하세요.")
                    elif name == '품질지표':
                        suggestions.append("⚠️ 품질 지표가 낮습니다. FCF, 이자보상배율, F-Score를 확인하세요.")
                    elif name == 'MoS':
                        suggestions.append("⚠️ 안전마진이 부족합니다. Justified Multiple 대비 저평가 종목을 찾으세요.")
        
        # 리스크 감점 (v2.2.2)
        if '리스크감점' in components:
            penalty = components['리스크감점']['score']
            if penalty < -20:
                suggestions.append("🚨 심각한 리스크 감지! 회계 및 이벤트 리스크를 면밀히 검토하세요.")
            elif penalty < -10:
                suggestions.append("⚠️ 리스크 요인이 있습니다. 주의 깊게 모니터링하세요.")
        
        # 종합 추천
        total_pct = explanation['score_percentage']
        if total_pct >= 75:
            suggestions.insert(0, "✅ 우수한 가치주입니다! 포트폴리오 검토를 권장합니다.")
        elif total_pct >= 50:
            suggestions.insert(0, "📊 양호한 수준입니다. 추가 분석 후 판단하세요.")
        else:
            suggestions.insert(0, "⚠️ 점수가 낮습니다. 다른 종목을 고려하세요.")
        
        return suggestions


# ===== 사용 예시 =====
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    explainer = ScoreExplainer()
    
    # 테스트 평가 결과
    test_result = {
        'value_score': 85.5,
        'grade': 'A',
        'recommendation': 'BUY',
        'details': {
            'per_score': 15.0,
            'pbr_score': 12.0,
            'roe_score': 16.0,
            'quality_score': 25.0,
            'sector_bonus': 10.0,
            'mos_score': 20.0,
            'risk_penalty': -12.5
        }
    }
    
    # 설명 생성
    explanation = explainer.explain_score(test_result)
    
    print("\n" + "="*60)
    print("📊 점수 설명 예시")
    print("="*60)
    
    # 텍스트 설명
    text = explainer.generate_explanation_text(explanation)
    print(text)
    
    # 기여도 테이블
    print("### 📋 기여도 테이블\n")
    table = explainer.create_contribution_table(explanation)
    print(table.to_string(index=False))
    
    # 개선 제안
    print("\n### 💡 개선 제안\n")
    suggestions = explainer.generate_improvement_suggestions(explanation)
    for i, suggestion in enumerate(suggestions, 1):
        print(f"{i}. {suggestion}")
    
    print("\n✅ ScoreExplainer 테스트 완료!")


