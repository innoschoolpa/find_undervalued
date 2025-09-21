"""
정성적 리스크 분석기
저평가 가치주 발굴을 위한 정성적 리스크 요소 통합 분석
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import requests
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

class RiskType(Enum):
    """리스크 타입 열거형"""
    POLICY = "정책_리스크"
    ESG = "ESG_리스크"
    SENTIMENT = "시장_감정_리스크"
    REGULATORY = "규제_리스크"
    COMPETITION = "경쟁_리스크"
    TECHNOLOGY = "기술_리스크"
    MARKET_CYCLE = "시장_사이클_리스크"
    LIQUIDITY = "유동성_리스크"

class RiskLevel(Enum):
    """리스크 레벨 열거형"""
    VERY_LOW = "매우_낮음"
    LOW = "낮음"
    MEDIUM = "보통"
    HIGH = "높음"
    VERY_HIGH = "매우_높음"

@dataclass
class RiskAssessment:
    """리스크 평가 결과"""
    risk_type: RiskType
    risk_level: RiskLevel
    score: float  # 0-100 (높을수록 위험)
    description: str
    confidence: float  # 0-1 (신뢰도)
    sources: List[str]  # 정보 출처
    last_updated: datetime

class BaseRiskAnalyzer(ABC):
    """리스크 분석기의 기본 클래스"""
    
    def __init__(self, risk_type: RiskType):
        self.risk_type = risk_type
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def analyze_risk(self, symbol: str, sector: str, data: Dict[str, Any]) -> RiskAssessment:
        """리스크 분석 수행"""
        pass
    
    def _normalize_risk_score(self, raw_score: float) -> Tuple[float, RiskLevel]:
        """원시 점수를 정규화하고 리스크 레벨 결정"""
        normalized_score = max(0, min(100, raw_score))
        
        if normalized_score >= 80:
            risk_level = RiskLevel.VERY_HIGH
        elif normalized_score >= 60:
            risk_level = RiskLevel.HIGH
        elif normalized_score >= 40:
            risk_level = RiskLevel.MEDIUM
        elif normalized_score >= 20:
            risk_level = RiskLevel.LOW
        else:
            risk_level = RiskLevel.VERY_LOW
        
        return normalized_score, risk_level

class PolicyRiskAnalyzer(BaseRiskAnalyzer):
    """정책 리스크 분석기"""
    
    def __init__(self):
        super().__init__(RiskType.POLICY)
        self.policy_keywords = {
            'regulatory': ['규제', '제재', '규제강화', '정부정책', '법안'],
            'tax': ['세금', '세제', '세율', '조세'],
            'trade': ['무역', '수출', '수입', '관세', 'FTA'],
            'subsidy': ['보조금', '지원금', '인센티브', '세제혜택']
        }
    
    def analyze_risk(self, symbol: str, sector: str, data: Dict[str, Any]) -> RiskAssessment:
        """정책 리스크 분석"""
        try:
            # 웹 검색을 통한 정책 관련 뉴스 수집
            policy_news = self._search_policy_news(symbol, sector)
            
            # 정책 리스크 점수 계산
            risk_score = self._calculate_policy_risk_score(sector, policy_news)
            
            # 정규화 및 레벨 결정
            normalized_score, risk_level = self._normalize_risk_score(risk_score)
            
            # 설명 생성
            description = self._generate_policy_description(risk_level, policy_news)
            
            return RiskAssessment(
                risk_type=self.risk_type,
                risk_level=risk_level,
                score=normalized_score,
                description=description,
                confidence=0.8,  # 웹 검색 기반이므로 중간 신뢰도
                sources=[f"정책_뉴스_{len(policy_news)}건"],
                last_updated=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"정책 리스크 분석 실패 {symbol}: {e}")
            return self._create_default_risk_assessment()
    
    def _search_policy_news(self, symbol: str, sector: str) -> List[Dict[str, Any]]:
        """정책 관련 뉴스 검색 (Mock 구현)"""
        # 실제로는 뉴스 API나 웹 스크래핑을 사용
        # 여기서는 Mock 데이터 반환
        
        mock_news = [
            {
                'title': f'{sector} 업계 정책 변화 예상',
                'content': f'{sector} 관련 정부 정책이 변화할 가능성이 있습니다.',
                'date': datetime.now() - timedelta(days=7),
                'sentiment': 'negative'
            },
            {
                'title': f'{sector} 규제 완화 논의',
                'content': f'{sector} 업계 규제 완화에 대한 논의가 진행 중입니다.',
                'date': datetime.now() - timedelta(days=3),
                'sentiment': 'positive'
            }
        ]
        
        return mock_news
    
    def _calculate_policy_risk_score(self, sector: str, news_list: List[Dict[str, Any]]) -> float:
        """정책 리스크 점수 계산"""
        base_score = 30.0  # 기본 점수
        
        # 업종별 기본 정책 리스크
        sector_risk_multiplier = {
            '게임업': 1.5,  # 게임업은 정책 리스크 높음
            '반도체': 1.3,  # 반도체는 무역 정책 리스크
            '제조업': 1.1,  # 제조업은 보통
            '금융업': 1.4,  # 금융업은 규제 리스크 높음
            '바이오': 1.2,  # 바이오는 승인 리스크
            '기타': 1.0
        }
        
        multiplier = sector_risk_multiplier.get(sector, 1.0)
        base_score *= multiplier
        
        # 뉴스 감정 분석
        negative_news_count = sum(1 for news in news_list if news.get('sentiment') == 'negative')
        positive_news_count = sum(1 for news in news_list if news.get('sentiment') == 'positive')
        
        if negative_news_count > positive_news_count:
            base_score += 20
        elif positive_news_count > negative_news_count:
            base_score -= 15
        
        return base_score
    
    def _generate_policy_description(self, risk_level: RiskLevel, news_list: List[Dict[str, Any]]) -> str:
        """정책 리스크 설명 생성"""
        descriptions = {
            RiskLevel.VERY_HIGH: "정책 변화로 인한 매우 높은 리스크",
            RiskLevel.HIGH: "정책 변화로 인한 높은 리스크",
            RiskLevel.MEDIUM: "정책 변화로 인한 보통 수준의 리스크",
            RiskLevel.LOW: "정책 변화로 인한 낮은 리스크",
            RiskLevel.VERY_LOW: "정책 변화로 인한 매우 낮은 리스크"
        }
        
        base_description = descriptions.get(risk_level, "정책 리스크 평가 중")
        
        if news_list:
            recent_news = f" 최근 관련 뉴스 {len(news_list)}건 발견"
            return base_description + recent_news
        
        return base_description
    
    def _create_default_risk_assessment(self) -> RiskAssessment:
        """기본 리스크 평가 결과 생성"""
        return RiskAssessment(
            risk_type=self.risk_type,
            risk_level=RiskLevel.MEDIUM,
            score=50.0,
            description="정책 리스크 분석 실패",
            confidence=0.0,
            sources=[],
            last_updated=datetime.now()
        )

class ESGRiskAnalyzer(BaseRiskAnalyzer):
    """ESG 리스크 분석기"""
    
    def __init__(self):
        super().__init__(RiskType.ESG)
        self.esg_categories = {
            'environmental': ['환경', '탄소', '에너지', '폐기물', '오염'],
            'social': ['사회', '노동', '인권', '안전', '지역사회'],
            'governance': ['지배구조', '이사회', '내부통제', '윤리', '투명성']
        }
    
    def analyze_risk(self, symbol: str, sector: str, data: Dict[str, Any]) -> RiskAssessment:
        """ESG 리스크 분석"""
        try:
            # ESG 관련 뉴스 검색
            esg_news = self._search_esg_news(symbol, sector)
            
            # ESG 리스크 점수 계산
            risk_score = self._calculate_esg_risk_score(sector, esg_news, data)
            
            # 정규화 및 레벨 결정
            normalized_score, risk_level = self._normalize_risk_score(risk_score)
            
            # 설명 생성
            description = self._generate_esg_description(risk_level, esg_news)
            
            return RiskAssessment(
                risk_type=self.risk_type,
                risk_level=risk_level,
                score=normalized_score,
                description=description,
                confidence=0.7,  # ESG 평가는 신뢰도 보통
                sources=[f"ESG_뉴스_{len(esg_news)}건"],
                last_updated=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"ESG 리스크 분석 실패 {symbol}: {e}")
            return self._create_default_risk_assessment()
    
    def _search_esg_news(self, symbol: str, sector: str) -> List[Dict[str, Any]]:
        """ESG 관련 뉴스 검색 (Mock 구현)"""
        mock_news = [
            {
                'title': f'{sector} 기업 ESG 경영 강화',
                'content': f'{sector} 업계 기업들의 ESG 경영이 강화되고 있습니다.',
                'category': 'governance',
                'sentiment': 'positive'
            }
        ]
        
        return mock_news
    
    def _calculate_esg_risk_score(self, sector: str, news_list: List[Dict[str, Any]], data: Dict[str, Any]) -> float:
        """ESG 리스크 점수 계산"""
        base_score = 40.0  # 기본 점수
        
        # 업종별 ESG 리스크
        sector_esg_risk = {
            '게임업': 45.0,  # 게임업은 사회적 이슈 리스크
            '반도체': 35.0,  # 반도체는 환경 리스크
            '제조업': 50.0,  # 제조업은 환경/사회 리스크 높음
            '금융업': 30.0,  # 금융업은 지배구조 리스크
            '바이오': 40.0,  # 바이오는 윤리 리스크
            '기타': 40.0
        }
        
        base_score = sector_esg_risk.get(sector, 40.0)
        
        # 뉴스 감정 분석
        negative_news_count = sum(1 for news in news_list if news.get('sentiment') == 'negative')
        if negative_news_count > 0:
            base_score += negative_news_count * 10
        
        return base_score
    
    def _generate_esg_description(self, risk_level: RiskLevel, news_list: List[Dict[str, Any]]) -> str:
        """ESG 리스크 설명 생성"""
        descriptions = {
            RiskLevel.VERY_HIGH: "ESG 관련 매우 높은 리스크",
            RiskLevel.HIGH: "ESG 관련 높은 리스크",
            RiskLevel.MEDIUM: "ESG 관련 보통 수준의 리스크",
            RiskLevel.LOW: "ESG 관련 낮은 리스크",
            RiskLevel.VERY_LOW: "ESG 관련 매우 낮은 리스크"
        }
        
        return descriptions.get(risk_level, "ESG 리스크 평가 중")
    
    def _create_default_risk_assessment(self) -> RiskAssessment:
        """기본 리스크 평가 결과 생성"""
        return RiskAssessment(
            risk_type=self.risk_type,
            risk_level=RiskLevel.MEDIUM,
            score=50.0,
            description="ESG 리스크 분석 실패",
            confidence=0.0,
            sources=[],
            last_updated=datetime.now()
        )

class SentimentRiskAnalyzer(BaseRiskAnalyzer):
    """시장 감정 리스크 분석기"""
    
    def __init__(self):
        super().__init__(RiskType.SENTIMENT)
        self.sentiment_indicators = {
            'positive': ['상승', '급등', '호재', '긍정', '성장'],
            'negative': ['하락', '급락', '악재', '부정', '우려']
        }
    
    def analyze_risk(self, symbol: str, sector: str, data: Dict[str, Any]) -> RiskAssessment:
        """시장 감정 리스크 분석"""
        try:
            # 시장 감정 데이터 수집
            sentiment_data = self._collect_sentiment_data(symbol, sector)
            
            # 감정 리스크 점수 계산
            risk_score = self._calculate_sentiment_risk_score(sentiment_data, data)
            
            # 정규화 및 레벨 결정
            normalized_score, risk_level = self._normalize_risk_score(risk_score)
            
            # 설명 생성
            description = self._generate_sentiment_description(risk_level, sentiment_data)
            
            return RiskAssessment(
                risk_type=self.risk_type,
                risk_level=risk_level,
                score=normalized_score,
                description=description,
                confidence=0.6,  # 감정 분석은 신뢰도 낮음
                sources=[f"감정_분석_{len(sentiment_data)}건"],
                last_updated=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"시장 감정 리스크 분석 실패 {symbol}: {e}")
            return self._create_default_risk_assessment()
    
    def _collect_sentiment_data(self, symbol: str, sector: str) -> Dict[str, Any]:
        """시장 감정 데이터 수집 (Mock 구현)"""
        return {
            'news_sentiment': 0.3,  # -1 (부정) ~ 1 (긍정)
            'social_media_sentiment': 0.1,
            'analyst_sentiment': 0.5,
            'volume_spike': False,
            'volatility': 0.8  # 0-1
        }
    
    def _calculate_sentiment_risk_score(self, sentiment_data: Dict[str, Any], data: Dict[str, Any]) -> float:
        """감정 리스크 점수 계산"""
        base_score = 50.0
        
        # 뉴스 감정 분석
        news_sentiment = sentiment_data.get('news_sentiment', 0)
        if news_sentiment < -0.5:
            base_score += 30  # 매우 부정적
        elif news_sentiment < 0:
            base_score += 15  # 부정적
        elif news_sentiment > 0.5:
            base_score -= 10  # 매우 긍정적
        elif news_sentiment > 0:
            base_score -= 5   # 긍정적
        
        # 변동성 분석
        volatility = sentiment_data.get('volatility', 0.5)
        if volatility > 0.8:
            base_score += 20  # 높은 변동성
        elif volatility > 0.6:
            base_score += 10  # 중간 변동성
        
        # 거래량 급증
        if sentiment_data.get('volume_spike', False):
            base_score += 15
        
        return base_score
    
    def _generate_sentiment_description(self, risk_level: RiskLevel, sentiment_data: Dict[str, Any]) -> str:
        """감정 리스크 설명 생성"""
        descriptions = {
            RiskLevel.VERY_HIGH: "시장 감정이 매우 부정적이며 높은 리스크",
            RiskLevel.HIGH: "시장 감정이 부정적이며 높은 리스크",
            RiskLevel.MEDIUM: "시장 감정이 중립적이며 보통 수준의 리스크",
            RiskLevel.LOW: "시장 감정이 긍정적이며 낮은 리스크",
            RiskLevel.VERY_LOW: "시장 감정이 매우 긍정적이며 매우 낮은 리스크"
        }
        
        return descriptions.get(risk_level, "시장 감정 리스크 평가 중")
    
    def _create_default_risk_assessment(self) -> RiskAssessment:
        """기본 리스크 평가 결과 생성"""
        return RiskAssessment(
            risk_type=self.risk_type,
            risk_level=RiskLevel.MEDIUM,
            score=50.0,
            description="시장 감정 리스크 분석 실패",
            confidence=0.0,
            sources=[],
            last_updated=datetime.now()
        )

class QualitativeRiskAnalyzer:
    """정성적 리스크 통합 분석기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.analyzers = {
            RiskType.POLICY: PolicyRiskAnalyzer(),
            RiskType.ESG: ESGRiskAnalyzer(),
            RiskType.SENTIMENT: SentimentRiskAnalyzer(),
        }
        self.risk_weights = {
            RiskType.POLICY: 0.3,
            RiskType.ESG: 0.25,
            RiskType.SENTIMENT: 0.25,
            RiskType.REGULATORY: 0.2,  # 향후 구현
        }
    
    def analyze_comprehensive_risk(self, symbol: str, sector: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """종합적인 정성적 리스크 분석"""
        try:
            self.logger.info(f"🔍 {symbol} 정성적 리스크 분석 시작")
            
            risk_assessments = {}
            total_risk_score = 0.0
            total_weight = 0.0
            
            # 각 리스크 타입별 분석 수행
            for risk_type, analyzer in self.analyzers.items():
                try:
                    assessment = analyzer.analyze_risk(symbol, sector, data)
                    risk_assessments[risk_type.value] = assessment
                    
                    # 가중 평균 계산
                    weight = self.risk_weights.get(risk_type, 0.1)
                    total_risk_score += assessment.score * weight
                    total_weight += weight
                    
                except Exception as e:
                    self.logger.error(f"{risk_type.value} 분석 실패: {e}")
                    continue
            
            # 종합 리스크 점수 계산
            if total_weight > 0:
                comprehensive_score = total_risk_score / total_weight
            else:
                comprehensive_score = 50.0  # 기본값
            
            # 종합 리스크 레벨 결정
            _, comprehensive_level = self._normalize_risk_score(comprehensive_score)
            
            # 리스크 조정 계수 계산 (0.5-1.5 범위)
            risk_adjustment_factor = self._calculate_risk_adjustment_factor(comprehensive_score)
            
            result = {
                'comprehensive_risk_score': comprehensive_score,
                'comprehensive_risk_level': comprehensive_level.value,
                'risk_adjustment_factor': risk_adjustment_factor,
                'individual_risks': risk_assessments,
                'analysis_timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
                'status': 'success'
            }
            
            self.logger.info(f"✅ {symbol} 정성적 리스크 분석 완료: {comprehensive_score:.1f}점 ({comprehensive_level.value})")
            return result
            
        except Exception as e:
            self.logger.error(f"정성적 리스크 분석 실패 {symbol}: {e}")
            return {
                'comprehensive_risk_score': 50.0,
                'comprehensive_risk_level': '보통',
                'risk_adjustment_factor': 1.0,
                'individual_risks': {},
                'status': 'error',
                'error': str(e)
            }
    
    def _normalize_risk_score(self, raw_score: float) -> Tuple[float, RiskLevel]:
        """원시 점수를 정규화하고 리스크 레벨 결정"""
        normalized_score = max(0, min(100, raw_score))
        
        if normalized_score >= 80:
            risk_level = RiskLevel.VERY_HIGH
        elif normalized_score >= 60:
            risk_level = RiskLevel.HIGH
        elif normalized_score >= 40:
            risk_level = RiskLevel.MEDIUM
        elif normalized_score >= 20:
            risk_level = RiskLevel.LOW
        else:
            risk_level = RiskLevel.VERY_LOW
        
        return normalized_score, risk_level
    
    def _calculate_risk_adjustment_factor(self, risk_score: float) -> float:
        """리스크 점수에 따른 조정 계수 계산"""
        # 리스크가 높을수록 조정 계수를 낮춤 (최종 점수 감소)
        if risk_score >= 80:
            return 0.5  # 매우 높은 리스크
        elif risk_score >= 60:
            return 0.7  # 높은 리스크
        elif risk_score >= 40:
            return 1.0  # 보통 리스크
        elif risk_score >= 20:
            return 1.2  # 낮은 리스크 (보너스)
        else:
            return 1.5  # 매우 낮은 리스크 (큰 보너스)
    
    def get_risk_summary(self, risk_analysis: Dict[str, Any]) -> str:
        """리스크 분석 결과 요약"""
        if risk_analysis.get('status') != 'success':
            return "정성적 리스크 분석 실패"
        
        score = risk_analysis.get('comprehensive_risk_score', 50)
        level = risk_analysis.get('comprehensive_risk_level', '보통')
        
        summary = f"종합 리스크 점수: {score:.1f}점 ({level})"
        
        # 개별 리스크 요약
        individual_risks = risk_analysis.get('individual_risks', {})
        if individual_risks:
            high_risks = []
            for risk_type, assessment in individual_risks.items():
                if assessment.score >= 60:
                    high_risks.append(f"{risk_type}({assessment.score:.1f}점)")
            
            if high_risks:
                summary += f" | 주요 리스크: {', '.join(high_risks)}"
        
        return summary
