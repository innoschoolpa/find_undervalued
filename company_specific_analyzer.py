#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기업별 맞춤화 분석 시스템
개별 기업의 특성을 반영한 맞춤형 분석
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)

class CompanyType(Enum):
    """기업 유형"""
    LARGE_CAP = "large_cap"           # 대형주
    MID_CAP = "mid_cap"               # 중형주
    SMALL_CAP = "small_cap"           # 소형주
    GROWTH = "growth"                 # 성장주
    VALUE = "value"                   # 가치주
    DIVIDEND = "dividend"             # 배당주
    CYCLICAL = "cyclical"             # 경기순환주
    DEFENSIVE = "defensive"           # 방어주
    TECHNOLOGY = "technology"         # 기술주
    FINANCIAL = "financial"           # 금융주

class BusinessModel(Enum):
    """사업 모델"""
    B2B = "b2b"                       # 기업간 거래
    B2C = "b2c"                       # 기업-소비자
    PLATFORM = "platform"             # 플랫폼
    MANUFACTURING = "manufacturing"   # 제조업
    SERVICE = "service"               # 서비스업
    HOLDING = "holding"               # 지주회사
    CONGLOMERATE = "conglomerate"     # 대기업집단

@dataclass
class CompanyProfile:
    """기업 프로필"""
    symbol: str
    name: str
    company_type: CompanyType
    business_model: BusinessModel
    market_cap: float
    business_characteristics: Dict[str, Any]
    competitive_advantages: List[str]
    risk_factors: List[str]
    growth_drivers: List[str]
    financial_structure: Dict[str, Any]
    management_quality: Dict[str, Any]
    esg_profile: Dict[str, Any]
    last_updated: datetime

@dataclass
class CompanySpecificMetrics:
    """기업별 맞춤 지표"""
    symbol: str
    industry_benchmark: Dict[str, float]
    peer_comparison: Dict[str, float]
    historical_trends: Dict[str, List[float]]
    cyclical_patterns: Dict[str, Any]
    seasonal_factors: Dict[str, float]
    management_metrics: Dict[str, float]
    innovation_metrics: Dict[str, float]
    sustainability_metrics: Dict[str, float]

class CompanySpecificAnalyzer:
    """기업별 맞춤 분석기"""
    
    def __init__(self):
        self.company_profiles = {}
        self.industry_benchmarks = {}
        self.peer_groups = {}
        self._initialize_company_data()
        
        logger.info("🏢 기업별 맞춤 분석기 초기화 완료")
    
    def _initialize_company_data(self):
        """기업 데이터 초기화"""
        
        # 주요 기업 프로필 데이터
        major_companies = {
            '005930': CompanyProfile(
                symbol='005930',
                name='삼성전자',
                company_type=CompanyType.LARGE_CAP,
                business_model=BusinessModel.MANUFACTURING,
                market_cap=400000000000000,  # 400조원
                business_characteristics={
                    'diversification': 'high',  # 사업 다각화
                    'global_presence': 'very_high',  # 글로벌 진출
                    'r_and_d_intensity': 'very_high',  # R&D 집약도
                    'capital_intensity': 'very_high',  # 자본 집약도
                    'cycle_sensitivity': 'high'  # 사이클 민감도
                },
                competitive_advantages=[
                    '메모리 반도체 세계 1위',
                    'OLED 디스플레이 기술력',
                    '생태계 통합 역량',
                    '글로벌 제조 네트워크',
                    '대규모 R&D 투자'
                ],
                risk_factors=[
                    '메모리 반도체 사이클',
                    '중미 무역분쟁',
                    '중국 경쟁사 부상',
                    '환율 변동',
                    '기술 변화 속도'
                ],
                growth_drivers=[
                    'AI/5G 서버 메모리',
                    '자동차용 반도체',
                    'OLED 확산',
                    '시스템반도체 성장',
                    '디지털 전환 가속'
                ],
                financial_structure={
                    'debt_to_equity': 0.15,
                    'cash_ratio': 0.8,
                    'dividend_yield': 0.025,
                    'payout_ratio': 0.3
                },
                management_quality={
                    'corporate_governance': 'good',
                    'transparency': 'high',
                    'innovation_culture': 'excellent',
                    'succession_planning': 'stable'
                },
                esg_profile={
                    'environmental_score': 75,
                    'social_score': 80,
                    'governance_score': 85,
                    'esg_rating': 'A'
                },
                last_updated=datetime.now()
            ),
            '000660': CompanyProfile(
                symbol='000660',
                name='SK하이닉스',
                company_type=CompanyType.LARGE_CAP,
                business_model=BusinessModel.MANUFACTURING,
                market_cap=200000000000000,  # 200조원
                business_characteristics={
                    'diversification': 'medium',
                    'global_presence': 'high',
                    'r_and_d_intensity': 'very_high',
                    'capital_intensity': 'very_high',
                    'cycle_sensitivity': 'very_high'
                },
                competitive_advantages=[
                    'DRAM 세계 2위',
                    'NAND 기술력',
                    'HBM 선도 기술',
                    'AI 서버 메모리',
                    '고객사 다양화'
                ],
                risk_factors=[
                    '메모리 사이클 변동',
                    '기술 격차',
                    '수급 불균형',
                    '중국 경쟁사',
                    '투자 사이클'
                ],
                growth_drivers=[
                    'AI 서버 폭증',
                    '데이터센터 확장',
                    'HBM 수요 증가',
                    '5G/자동차',
                    '메모리 고도화'
                ],
                financial_structure={
                    'debt_to_equity': 0.25,
                    'cash_ratio': 0.6,
                    'dividend_yield': 0.015,
                    'payout_ratio': 0.2
                },
                management_quality={
                    'corporate_governance': 'good',
                    'transparency': 'high',
                    'innovation_culture': 'excellent',
                    'succession_planning': 'stable'
                },
                esg_profile={
                    'environmental_score': 70,
                    'social_score': 75,
                    'governance_score': 80,
                    'esg_rating': 'A-'
                },
                last_updated=datetime.now()
            ),
            '035420': CompanyProfile(
                symbol='035420',
                name='NAVER',
                company_type=CompanyType.LARGE_CAP,
                business_model=BusinessModel.PLATFORM,
                market_cap=35000000000000,  # 35조원
                business_characteristics={
                    'diversification': 'high',
                    'global_presence': 'medium',
                    'r_and_d_intensity': 'very_high',
                    'capital_intensity': 'low',
                    'cycle_sensitivity': 'medium'
                },
                competitive_advantages=[
                    '한국 검색 1위',
                    '모바일 플랫폼',
                    'AI 기술력',
                    '클라우드 서비스',
                    '글로벌 진출'
                ],
                risk_factors=[
                    '경쟁 심화',
                    '규제 변화',
                    '광고 시장 변동',
                    '기술 변화',
                    '글로벌 경쟁'
                ],
                growth_drivers=[
                    'AI 검색',
                    '클라우드 성장',
                    '핀테크 확장',
                    '글로벌 진출',
                    '디지털 전환'
                ],
                financial_structure={
                    'debt_to_equity': 0.1,
                    'cash_ratio': 0.9,
                    'dividend_yield': 0.0,
                    'payout_ratio': 0.0
                },
                management_quality={
                    'corporate_governance': 'excellent',
                    'transparency': 'very_high',
                    'innovation_culture': 'excellent',
                    'succession_planning': 'stable'
                },
                esg_profile={
                    'environmental_score': 80,
                    'social_score': 85,
                    'governance_score': 90,
                    'esg_rating': 'A+'
                },
                last_updated=datetime.now()
            )
        }
        
        self.company_profiles = major_companies
        
        # 업종별 벤치마크
        self.industry_benchmarks = {
            'SEMICONDUCTOR': {
                'avg_per': 15.2,
                'avg_pbr': 1.8,
                'avg_roe': 12.5,
                'avg_roa': 8.3,
                'avg_debt_ratio': 45.2,
                'avg_growth_rate': 8.5,
                'avg_volatility': 0.35,
                'avg_beta': 1.2
            },
            'PLATFORM': {
                'avg_per': 25.8,
                'avg_pbr': 3.2,
                'avg_roe': 18.5,
                'avg_roa': 12.3,
                'avg_debt_ratio': 25.2,
                'avg_growth_rate': 15.5,
                'avg_volatility': 0.28,
                'avg_beta': 1.1
            }
        }
        
        # 동종업계 그룹
        self.peer_groups = {
            '005930': ['000660', '373220', '066570'],  # 삼성전자 동종업계
            '000660': ['005930', '373220'],  # SK하이닉스 동종업계
            '035420': ['035720', '068270']  # NAVER 동종업계
        }
    
    def analyze_company_specific(self, symbol: str, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """기업별 맞춤 분석"""
        
        if symbol not in self.company_profiles:
            return self._create_generic_analysis(symbol, financial_data)
        
        company_profile = self.company_profiles[symbol]
        
        # 1. 업종별 벤치마크 대비 분석
        benchmark_analysis = self._analyze_vs_benchmark(symbol, financial_data)
        
        # 2. 동종업계 대비 분석
        peer_analysis = self._analyze_vs_peers(symbol, financial_data)
        
        # 3. 기업 특성 반영 분석
        characteristic_analysis = self._analyze_characteristics(company_profile, financial_data)
        
        # 4. 경쟁 우위 분석
        competitive_analysis = self._analyze_competitive_advantages(company_profile)
        
        # 5. 리스크 분석
        risk_analysis = self._analyze_risks(company_profile, financial_data)
        
        # 6. 성장 동력 분석
        growth_analysis = self._analyze_growth_drivers(company_profile, financial_data)
        
        # 7. ESG 분석
        esg_analysis = self._analyze_esg(company_profile)
        
        # 8. 종합 점수 계산
        comprehensive_score = self._calculate_comprehensive_score(
            benchmark_analysis, peer_analysis, characteristic_analysis,
            competitive_analysis, risk_analysis, growth_analysis, esg_analysis
        )
        
        return {
            'symbol': symbol,
            'name': company_profile.name,
            'company_type': company_profile.company_type.value,
            'business_model': company_profile.business_model.value,
            'comprehensive_score': comprehensive_score,
            'benchmark_analysis': benchmark_analysis,
            'peer_analysis': peer_analysis,
            'characteristic_analysis': characteristic_analysis,
            'competitive_analysis': competitive_analysis,
            'risk_analysis': risk_analysis,
            'growth_analysis': growth_analysis,
            'esg_analysis': esg_analysis,
            'company_profile': asdict(company_profile),
            'analysis_date': datetime.now().isoformat()
        }
    
    def _analyze_vs_benchmark(self, symbol: str, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """업종 벤치마크 대비 분석"""
        
        # 업종 결정
        industry = self._determine_industry(symbol)
        if industry not in self.industry_benchmarks:
            return {}
        
        benchmark = self.industry_benchmarks[industry]
        
        # 재무비율 비교
        per = financial_data.get('per', 0)
        pbr = financial_data.get('pbr', 0)
        roe = financial_data.get('roe', 0)
        roa = financial_data.get('roa', 0)
        debt_ratio = financial_data.get('debt_ratio', 0)
        
        # 벤치마크 대비 점수 (100점 만점)
        per_score = max(0, 100 - abs(per - benchmark['avg_per']) / benchmark['avg_per'] * 100)
        pbr_score = max(0, 100 - abs(pbr - benchmark['avg_pbr']) / benchmark['avg_pbr'] * 100)
        roe_score = max(0, min(100, roe / benchmark['avg_roe'] * 100))
        roa_score = max(0, min(100, roa / benchmark['avg_roa'] * 100))
        debt_score = max(0, 100 - abs(debt_ratio - benchmark['avg_debt_ratio']) / benchmark['avg_debt_ratio'] * 100)
        
        overall_score = (per_score + pbr_score + roe_score + roa_score + debt_score) / 5
        
        return {
            'industry': industry,
            'benchmark_comparison': {
                'per': {'company': per, 'benchmark': benchmark['avg_per'], 'score': per_score},
                'pbr': {'company': pbr, 'benchmark': benchmark['avg_pbr'], 'score': pbr_score},
                'roe': {'company': roe, 'benchmark': benchmark['avg_roe'], 'score': roe_score},
                'roa': {'company': roa, 'benchmark': benchmark['avg_roa'], 'score': roa_score},
                'debt_ratio': {'company': debt_ratio, 'benchmark': benchmark['avg_debt_ratio'], 'score': debt_score}
            },
            'overall_score': overall_score,
            'relative_performance': self._get_performance_level(overall_score)
        }
    
    def _analyze_vs_peers(self, symbol: str, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """동종업계 대비 분석"""
        
        if symbol not in self.peer_groups:
            return {}
        
        peer_symbols = self.peer_groups[symbol]
        
        # 동종업계 평균 계산 (실제로는 더 정교한 데이터 필요)
        peer_metrics = {
            'avg_per': 18.5,
            'avg_pbr': 2.1,
            'avg_roe': 14.2,
            'avg_roa': 9.8,
            'avg_debt_ratio': 38.5
        }
        
        # 현재 기업 지표
        company_metrics = {
            'per': financial_data.get('per', 0),
            'pbr': financial_data.get('pbr', 0),
            'roe': financial_data.get('roe', 0),
            'roa': financial_data.get('roa', 0),
            'debt_ratio': financial_data.get('debt_ratio', 0)
        }
        
        # 상대적 순위 계산
        peer_rankings = {}
        for metric, company_value in company_metrics.items():
            benchmark_value = peer_metrics[f'avg_{metric}']
            if company_value > benchmark_value:
                peer_rankings[metric] = 'above_average'
            elif company_value < benchmark_value:
                peer_rankings[metric] = 'below_average'
            else:
                peer_rankings[metric] = 'average'
        
        # 종합 순위
        above_count = sum(1 for ranking in peer_rankings.values() if ranking == 'above_average')
        total_count = len(peer_rankings)
        peer_performance = above_count / total_count * 100
        
        return {
            'peer_symbols': peer_symbols,
            'peer_metrics': peer_metrics,
            'company_metrics': company_metrics,
            'peer_rankings': peer_rankings,
            'peer_performance': peer_performance,
            'relative_ranking': self._get_ranking_level(peer_performance)
        }
    
    def _analyze_characteristics(self, company_profile: CompanyProfile, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """기업 특성 반영 분석"""
        
        characteristics = company_profile.business_characteristics
        analysis = {}
        
        # 사업 다각화 분석
        if characteristics.get('diversification') == 'high':
            analysis['diversification'] = {
                'score': 85,
                'description': '높은 사업 다각화로 리스크 분산 효과',
                'impact': 'positive'
            }
        elif characteristics.get('diversification') == 'medium':
            analysis['diversification'] = {
                'score': 65,
                'description': '적당한 사업 다각화',
                'impact': 'neutral'
            }
        else:
            analysis['diversification'] = {
                'score': 45,
                'description': '낮은 사업 다각화로 집중 리스크',
                'impact': 'negative'
            }
        
        # R&D 집약도 분석
        if characteristics.get('r_and_d_intensity') == 'very_high':
            analysis['r_and_d'] = {
                'score': 90,
                'description': '매우 높은 R&D 투자로 혁신 경쟁력',
                'impact': 'positive'
            }
        elif characteristics.get('r_and_d_intensity') == 'high':
            analysis['r_and_d'] = {
                'score': 75,
                'description': '높은 R&D 투자',
                'impact': 'positive'
            }
        else:
            analysis['r_and_d'] = {
                'score': 50,
                'description': 'R&D 투자 부족으로 혁신 경쟁력 약화 우려',
                'impact': 'negative'
            }
        
        # 사이클 민감도 분석
        cycle_sensitivity = characteristics.get('cycle_sensitivity')
        if cycle_sensitivity == 'very_high':
            analysis['cycle_sensitivity'] = {
                'score': 40,
                'description': '매우 높은 사이클 민감도로 변동성 큼',
                'impact': 'negative',
                'recommendation': '사이클 타이밍 중요'
            }
        elif cycle_sensitivity == 'high':
            analysis['cycle_sensitivity'] = {
                'score': 60,
                'description': '높은 사이클 민감도',
                'impact': 'neutral',
                'recommendation': '경기 사이클 고려 필요'
            }
        else:
            analysis['cycle_sensitivity'] = {
                'score': 80,
                'description': '낮은 사이클 민감도로 안정적',
                'impact': 'positive'
            }
        
        # 종합 특성 점수
        total_score = sum(analysis[key]['score'] for key in analysis) / len(analysis)
        
        return {
            'characteristics': analysis,
            'total_score': total_score,
            'characteristic_level': self._get_performance_level(total_score)
        }
    
    def _analyze_competitive_advantages(self, company_profile: CompanyProfile) -> Dict[str, Any]:
        """경쟁 우위 분석"""
        
        advantages = company_profile.competitive_advantages
        analysis = {}
        
        for i, advantage in enumerate(advantages):
            # 각 경쟁 우위의 강도 평가 (실제로는 더 정교한 분석 필요)
            strength_scores = {
                '세계 1위': 95,
                '세계 2위': 90,
                '선도': 85,
                '기술력': 80,
                '생태계': 75,
                '네트워크': 70,
                '투자': 65
            }
            
            max_score = 0
            for keyword, score in strength_scores.items():
                if keyword in advantage:
                    max_score = max(max_score, score)
            
            if max_score == 0:
                max_score = 70  # 기본 점수
            
            analysis[f'advantage_{i+1}'] = {
                'description': advantage,
                'strength_score': max_score,
                'sustainability': self._assess_sustainability(advantage),
                'impact': 'positive'
            }
        
        # 종합 경쟁 우위 점수
        if analysis:
            total_score = sum(analysis[key]['strength_score'] for key in analysis) / len(analysis)
        else:
            total_score = 50
        
        return {
            'competitive_advantages': analysis,
            'total_score': total_score,
            'competitive_level': self._get_performance_level(total_score)
        }
    
    def _analyze_risks(self, company_profile: CompanyProfile, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """리스크 분석"""
        
        risks = company_profile.risk_factors
        analysis = {}
        
        for i, risk in enumerate(risks):
            # 각 리스크의 심각도 평가
            severity_scores = {
                '사이클': 80,
                '무역분쟁': 75,
                '경쟁사': 70,
                '환율': 65,
                '기술': 60,
                '규제': 55,
                '수요': 50
            }
            
            max_severity = 0
            for keyword, score in severity_scores.items():
                if keyword in risk:
                    max_severity = max(max_severity, score)
            
            if max_severity == 0:
                max_severity = 50  # 기본 점수
            
            analysis[f'risk_{i+1}'] = {
                'description': risk,
                'severity_score': max_severity,
                'probability': self._assess_risk_probability(risk),
                'mitigation': self._suggest_mitigation(risk),
                'impact': 'negative'
            }
        
        # 종합 리스크 점수 (낮을수록 좋음)
        if analysis:
            total_score = 100 - sum(analysis[key]['severity_score'] for key in analysis) / len(analysis)
        else:
            total_score = 70
        
        return {
            'risk_factors': analysis,
            'total_score': total_score,
            'risk_level': self._get_risk_level(total_score)
        }
    
    def _analyze_growth_drivers(self, company_profile: CompanyProfile, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """성장 동력 분석"""
        
        drivers = company_profile.growth_drivers
        analysis = {}
        
        for i, driver in enumerate(drivers):
            # 각 성장 동력의 잠재력 평가
            potential_scores = {
                'AI': 95,
                '5G': 90,
                '자동차': 85,
                '클라우드': 80,
                '디지털': 75,
                '전환': 70,
                '확산': 65,
                '성장': 60
            }
            
            max_potential = 0
            for keyword, score in potential_scores.items():
                if keyword in driver:
                    max_potential = max(max_potential, score)
            
            if max_potential == 0:
                max_potential = 65  # 기본 점수
            
            analysis[f'driver_{i+1}'] = {
                'description': driver,
                'potential_score': max_potential,
                'timeframe': self._assess_timeframe(driver),
                'impact': 'positive'
            }
        
        # 종합 성장 동력 점수
        if analysis:
            total_score = sum(analysis[key]['potential_score'] for key in analysis) / len(analysis)
        else:
            total_score = 60
        
        return {
            'growth_drivers': analysis,
            'total_score': total_score,
            'growth_level': self._get_performance_level(total_score)
        }
    
    def _analyze_esg(self, company_profile: CompanyProfile) -> Dict[str, Any]:
        """ESG 분석"""
        
        esg_profile = company_profile.esg_profile
        
        # ESG 점수 계산
        e_score = esg_profile.get('environmental_score', 70)
        s_score = esg_profile.get('social_score', 70)
        g_score = esg_profile.get('governance_score', 70)
        
        total_esg_score = (e_score + s_score + g_score) / 3
        
        # ESG 등급 매핑
        esg_rating = esg_profile.get('esg_rating', 'B')
        rating_scores = {'A+': 95, 'A': 90, 'A-': 85, 'B+': 80, 'B': 75, 'B-': 70, 'C+': 65, 'C': 60}
        esg_score = rating_scores.get(esg_rating, 70)
        
        return {
            'environmental_score': e_score,
            'social_score': s_score,
            'governance_score': g_score,
            'total_esg_score': total_esg_score,
            'esg_rating': esg_rating,
            'esg_level': self._get_performance_level(esg_score)
        }
    
    def _calculate_comprehensive_score(self, *analyses) -> float:
        """종합 점수 계산"""
        
        weights = {
            'benchmark': 0.25,      # 업종 벤치마크 대비 25%
            'peer': 0.20,           # 동종업계 대비 20%
            'characteristics': 0.15, # 기업 특성 15%
            'competitive': 0.15,    # 경쟁 우위 15%
            'risk': 0.10,           # 리스크 10%
            'growth': 0.10,         # 성장 동력 10%
            'esg': 0.05             # ESG 5%
        }
        
        total_score = 0
        total_weight = 0
        
        for analysis in analyses:
            if analysis and 'total_score' in analysis:
                analysis_type = None
                for key in weights.keys():
                    if key in str(analysis):
                        analysis_type = key
                        break
                
                if analysis_type:
                    weight = weights[analysis_type]
                    total_score += analysis['total_score'] * weight
                    total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0
    
    def _create_generic_analysis(self, symbol: str, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """일반적인 분석 (프로필이 없는 기업)"""
        return {
            'symbol': symbol,
            'name': f'Company_{symbol}',
            'company_type': 'unknown',
            'business_model': 'unknown',
            'comprehensive_score': 50.0,
            'analysis_type': 'generic',
            'financial_data': financial_data,
            'analysis_date': datetime.now().isoformat()
        }
    
    # 헬퍼 메서드들
    def _determine_industry(self, symbol: str) -> str:
        """업종 결정"""
        industry_mapping = {
            '005930': 'SEMICONDUCTOR',
            '000660': 'SEMICONDUCTOR',
            '035420': 'PLATFORM',
            '035720': 'PLATFORM'
        }
        return industry_mapping.get(symbol, 'UNKNOWN')
    
    def _get_performance_level(self, score: float) -> str:
        """성과 레벨 결정"""
        if score >= 90: return 'excellent'
        elif score >= 80: return 'very_good'
        elif score >= 70: return 'good'
        elif score >= 60: return 'average'
        elif score >= 50: return 'below_average'
        else: return 'poor'
    
    def _get_ranking_level(self, percentage: float) -> str:
        """순위 레벨 결정"""
        if percentage >= 80: return 'top_tier'
        elif percentage >= 60: return 'above_average'
        elif percentage >= 40: return 'average'
        elif percentage >= 20: return 'below_average'
        else: return 'bottom_tier'
    
    def _get_risk_level(self, score: float) -> str:
        """리스크 레벨 결정"""
        if score >= 80: return 'low'
        elif score >= 60: return 'medium'
        elif score >= 40: return 'high'
        else: return 'very_high'
    
    def _assess_sustainability(self, advantage: str) -> str:
        """지속가능성 평가"""
        sustainable_keywords = ['기술력', '네트워크', '생태계', '브랜드']
        if any(keyword in advantage for keyword in sustainable_keywords):
            return 'high'
        return 'medium'
    
    def _assess_risk_probability(self, risk: str) -> str:
        """리스크 발생 확률 평가"""
        high_prob_keywords = ['사이클', '경쟁', '수요']
        if any(keyword in risk for keyword in high_prob_keywords):
            return 'high'
        return 'medium'
    
    def _suggest_mitigation(self, risk: str) -> str:
        """리스크 완화 방안 제안"""
        mitigation_map = {
            '사이클': '다각화 전략',
            '경쟁': '차별화 강화',
            '환율': '헤징 전략',
            '기술': 'R&D 투자',
            '규제': '정책 모니터링'
        }
        for keyword, mitigation in mitigation_map.items():
            if keyword in risk:
                return mitigation
        return '리스크 관리 강화'
    
    def _assess_timeframe(self, driver: str) -> str:
        """시간대 평가"""
        short_term_keywords = ['AI', '5G', '클라우드']
        long_term_keywords = ['전환', '확산', '성장']
        
        if any(keyword in driver for keyword in short_term_keywords):
            return 'short_term'
        elif any(keyword in driver for keyword in long_term_keywords):
            return 'long_term'
        return 'medium_term'

def main():
    """메인 실행 함수"""
    analyzer = CompanySpecificAnalyzer()
    
    # 테스트 데이터
    test_data = {
        '005930': {'per': 12.5, 'pbr': 1.2, 'roe': 15.8, 'roa': 10.2, 'debt_ratio': 25.3},
        '000660': {'per': 8.2, 'pbr': 0.8, 'roe': 18.5, 'roa': 12.1, 'debt_ratio': 35.2},
        '035420': {'per': 28.5, 'pbr': 2.8, 'roe': 22.1, 'roa': 15.8, 'debt_ratio': 15.2}
    }
    
    print("🏢 기업별 맞춤 분석 테스트")
    print("=" * 80)
    
    for symbol, financial_data in test_data.items():
        print(f"\n📊 {symbol} 기업별 맞춤 분석:")
        analysis = analyzer.analyze_company_specific(symbol, financial_data)
        
        print(f"  종합 점수: {analysis['comprehensive_score']:.1f}점")
        print(f"  기업 유형: {analysis['company_type']}")
        print(f"  사업 모델: {analysis['business_model']}")
        
        if 'benchmark_analysis' in analysis and analysis['benchmark_analysis']:
            print(f"  업종 대비 성과: {analysis['benchmark_analysis']['relative_performance']}")
        
        if 'competitive_analysis' in analysis and analysis['competitive_analysis']:
            print(f"  경쟁 우위: {analysis['competitive_analysis']['competitive_level']}")
        
        if 'risk_analysis' in analysis and analysis['risk_analysis']:
            print(f"  리스크 레벨: {analysis['risk_analysis']['risk_level']}")
        
        print("-" * 40)
    
    print("\n✅ 기업별 맞춤 분석 시스템 테스트 완료")

if __name__ == "__main__":
    main()
