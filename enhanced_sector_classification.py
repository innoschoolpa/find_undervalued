#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
향상된 업종 분류 시스템
더 세밀한 업종 분류 및 업종별 특화 분석
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class SectorLevel(Enum):
    """업종 분류 레벨"""
    MAJOR = "major"           # 대분류 (예: 기술, 금융, 제조업)
    MEDIUM = "medium"         # 중분류 (예: 반도체, 은행, 자동차)
    DETAILED = "detailed"     # 세분류 (예: 메모리반도체, 소비자은행, 전기차)
    SPECIALIZED = "specialized"  # 특화분류 (예: HBM메모리, 핀테크, 자율주행)

@dataclass
class SectorClassification:
    """업종 분류 정보"""
    code: str
    name: str
    level: SectorLevel
    parent_code: Optional[str] = None
    keywords: List[str] = None
    characteristics: Dict[str, Any] = None
    risk_factors: List[str] = None
    growth_drivers: List[str] = None

@dataclass
class SectorMetrics:
    """업종별 지표"""
    sector_code: str
    avg_per: float
    avg_pbr: float
    avg_roe: float
    avg_roa: float
    avg_debt_ratio: float
    avg_growth_rate: float
    market_cap_ratio: float
    volatility: float
    correlation_kospi: float
    last_updated: datetime

class EnhancedSectorClassifier:
    """향상된 업종 분류기"""
    
    def __init__(self):
        self.sector_hierarchy = {}
        self.sector_keywords = {}
        self.sector_characteristics = {}
        self._initialize_sector_data()
        
        logger.info("🏭 향상된 업종 분류기 초기화 완료")
    
    def _initialize_sector_data(self):
        """업종 데이터 초기화"""
        
        # 대분류 (Major Sectors)
        major_sectors = {
            'TECH': SectorClassification(
                code='TECH',
                name='기술',
                level=SectorLevel.MAJOR,
                keywords=['기술', 'IT', '소프트웨어', '하드웨어', '반도체', '전자'],
                characteristics={
                    'growth_potential': 'high',
                    'volatility': 'high',
                    'innovation_cycle': 'fast',
                    'regulatory_risk': 'medium'
                },
                risk_factors=['기술 변화', '경쟁 심화', '규제 변화'],
                growth_drivers=['디지털 전환', 'AI 발전', '5G 확산']
            ),
            'FINANCE': SectorClassification(
                code='FINANCE',
                name='금융',
                level=SectorLevel.MAJOR,
                keywords=['금융', '은행', '보험', '증권', '카드'],
                characteristics={
                    'growth_potential': 'medium',
                    'volatility': 'medium',
                    'innovation_cycle': 'medium',
                    'regulatory_risk': 'high'
                },
                risk_factors=['금리 변동', '부실채권', '규제 강화'],
                growth_drivers=['금융혁신', '핀테크', 'ESG 투자']
            ),
            'MANUFACTURING': SectorClassification(
                code='MANUFACTURING',
                name='제조업',
                level=SectorLevel.MAJOR,
                keywords=['제조', '생산', '공장', '산업', '화학', '철강'],
                characteristics={
                    'growth_potential': 'medium',
                    'volatility': 'medium',
                    'innovation_cycle': 'slow',
                    'regulatory_risk': 'low'
                },
                risk_factors=['원자재 가격', '환율 변동', '수요 변동'],
                growth_drivers=['스마트팩토리', '친환경 전환', '글로벌 확장']
            ),
            'HEALTHCARE': SectorClassification(
                code='HEALTHCARE',
                name='헬스케어',
                level=SectorLevel.MAJOR,
                keywords=['의료', '바이오', '제약', '헬스케어', '병원'],
                characteristics={
                    'growth_potential': 'high',
                    'volatility': 'high',
                    'innovation_cycle': 'slow',
                    'regulatory_risk': 'high'
                },
                risk_factors=['규제 승인', '임상시험', '특허 만료'],
                growth_drivers=['고령화', '바이오혁신', '디지털헬스']
            ),
            'CONSUMER': SectorClassification(
                code='CONSUMER',
                name='소비재',
                level=SectorLevel.MAJOR,
                keywords=['소비', '유통', '식품', '의류', '화장품'],
                characteristics={
                    'growth_potential': 'medium',
                    'volatility': 'low',
                    'innovation_cycle': 'medium',
                    'regulatory_risk': 'low'
                },
                risk_factors=['소비 심리', '유통비용', '브랜드 이미지'],
                growth_drivers=['온라인 쇼핑', '프리미엄화', '건강 트렌드']
            )
        }
        
        # 중분류 (Medium Sectors)
        medium_sectors = {
            # 기술 대분류 하위
            'SEMICONDUCTOR': SectorClassification(
                code='SEMICONDUCTOR',
                name='반도체',
                level=SectorLevel.MEDIUM,
                parent_code='TECH',
                keywords=['반도체', '칩', '웨이퍼', '메모리', '시스템반도체'],
                characteristics={
                    'growth_potential': 'high',
                    'volatility': 'very_high',
                    'innovation_cycle': 'very_fast',
                    'capital_intensity': 'very_high'
                },
                risk_factors=['사이클 변동', '기술 격차', '수급 불균형'],
                growth_drivers=['AI/5G', '자동차용 반도체', '메모리 고도화']
            ),
            'SOFTWARE': SectorClassification(
                code='SOFTWARE',
                name='소프트웨어',
                level=SectorLevel.MEDIUM,
                parent_code='TECH',
                keywords=['소프트웨어', 'SaaS', '클라우드', '플랫폼', '앱'],
                characteristics={
                    'growth_potential': 'very_high',
                    'volatility': 'high',
                    'innovation_cycle': 'fast',
                    'capital_intensity': 'low'
                },
                risk_factors=['경쟁 심화', '기술 변화', '데이터 보안'],
                growth_drivers=['클라우드 전환', 'AI 통합', '디지털 전환']
            ),
            'ELECTRONICS': SectorClassification(
                code='ELECTRONICS',
                name='전자',
                level=SectorLevel.MEDIUM,
                parent_code='TECH',
                keywords=['전자', '디스플레이', '부품', '스마트폰', 'TV'],
                characteristics={
                    'growth_potential': 'medium',
                    'volatility': 'medium',
                    'innovation_cycle': 'medium',
                    'capital_intensity': 'high'
                },
                risk_factors=['가격 경쟁', '기술 변화', '수요 변동'],
                growth_drivers=['OLED 확산', '자동차 전자화', 'IoT 확산']
            ),
            
            # 금융 대분류 하위
            'BANKING': SectorClassification(
                code='BANKING',
                name='은행',
                level=SectorLevel.MEDIUM,
                parent_code='FINANCE',
                keywords=['은행', '상업은행', '저축은행', '특수은행'],
                characteristics={
                    'growth_potential': 'low',
                    'volatility': 'medium',
                    'innovation_cycle': 'slow',
                    'capital_requirement': 'high'
                },
                risk_factors=['금리 리스크', '신용 리스크', '규제 리스크'],
                growth_drivers=['핀테크 협력', 'ESG 금융', '디지털 뱅킹']
            ),
            'INSURANCE': SectorClassification(
                code='INSURANCE',
                name='보험',
                level=SectorLevel.MEDIUM,
                parent_code='FINANCE',
                keywords=['보험', '생명보험', '손해보험', '재보험'],
                characteristics={
                    'growth_potential': 'medium',
                    'volatility': 'low',
                    'innovation_cycle': 'slow',
                    'investment_risk': 'medium'
                },
                risk_factors=['재해 리스크', '금리 리스크', '장수 리스크'],
                growth_drivers=['고령화', '보험 상품 다양화', '디지털 보험']
            ),
            
            # 제조업 대분류 하위
            'AUTOMOTIVE': SectorClassification(
                code='AUTOMOTIVE',
                name='자동차',
                level=SectorLevel.MEDIUM,
                parent_code='MANUFACTURING',
                keywords=['자동차', '차량', '부품', '모터', '배터리'],
                characteristics={
                    'growth_potential': 'medium',
                    'volatility': 'medium',
                    'innovation_cycle': 'medium',
                    'capital_intensity': 'very_high'
                },
                risk_factors=['수요 변동', '환경 규제', '기술 변화'],
                growth_drivers=['전기차 전환', '자율주행', '모빌리티 서비스']
            ),
            'CHEMICAL': SectorClassification(
                code='CHEMICAL',
                name='화학',
                level=SectorLevel.MEDIUM,
                parent_code='MANUFACTURING',
                keywords=['화학', '석유화학', '정밀화학', '플라스틱', '페인트'],
                characteristics={
                    'growth_potential': 'medium',
                    'volatility': 'high',
                    'innovation_cycle': 'slow',
                    'environmental_risk': 'high'
                },
                risk_factors=['원유 가격', '환경 규제', '수요 변동'],
                growth_drivers=['친환경 전환', '신소재 개발', '바이오 화학']
            ),
            
            # 헬스케어 대분류 하위
            'BIOTECH': SectorClassification(
                code='BIOTECH',
                name='바이오',
                level=SectorLevel.MEDIUM,
                parent_code='HEALTHCARE',
                keywords=['바이오', '생명공학', '유전자', '세포', '항체'],
                characteristics={
                    'growth_potential': 'very_high',
                    'volatility': 'very_high',
                    'innovation_cycle': 'slow',
                    'regulatory_hurdle': 'very_high'
                },
                risk_factors=['임상시험 실패', '규제 승인', '특허 만료'],
                growth_drivers=['정밀의료', '세포치료', '유전자치료']
            ),
            'PHARMACEUTICAL': SectorClassification(
                code='PHARMACEUTICAL',
                name='제약',
                level=SectorLevel.MEDIUM,
                parent_code='HEALTHCARE',
                keywords=['제약', '약물', '의약품', '원료의약품'],
                characteristics={
                    'growth_potential': 'high',
                    'volatility': 'medium',
                    'innovation_cycle': 'slow',
                    'patent_risk': 'high'
                },
                risk_factors=['특허 만료', '약가 인하', '부작용'],
                growth_drivers=['신약 개발', '해외 진출', '제네릭']
            )
        }
        
        # 세분류 (Detailed Sectors)
        detailed_sectors = {
            # 반도체 중분류 하위
            'MEMORY_SEMICONDUCTOR': SectorClassification(
                code='MEMORY_SEMICONDUCTOR',
                name='메모리반도체',
                level=SectorLevel.DETAILED,
                parent_code='SEMICONDUCTOR',
                keywords=['메모리', 'DRAM', 'NAND', '플래시', 'HBM'],
                characteristics={
                    'growth_potential': 'high',
                    'volatility': 'very_high',
                    'innovation_cycle': 'fast',
                    'sector_cycle': 'strong'
                },
                risk_factors=['메모리 사이클', '기술 격차', '수급 불균형'],
                growth_drivers=['AI 서버', '데이터센터', '모바일 고도화']
            ),
            'SYSTEM_SEMICONDUCTOR': SectorClassification(
                code='SYSTEM_SEMICONDUCTOR',
                name='시스템반도체',
                level=SectorLevel.DETAILED,
                parent_code='SEMICONDUCTOR',
                keywords=['시스템', 'SoC', 'AP', 'MCU', '센서'],
                characteristics={
                    'growth_potential': 'very_high',
                    'volatility': 'high',
                    'innovation_cycle': 'fast',
                    'design_complexity': 'high'
                },
                risk_factors=['설계 복잡도', '공정 기술', '경쟁 심화'],
                growth_drivers=['AI 칩', '자동차 전자화', 'IoT 확산']
            ),
            
            # 자동차 중분류 하위
            'ELECTRIC_VEHICLE': SectorClassification(
                code='ELECTRIC_VEHICLE',
                name='전기차',
                level=SectorLevel.DETAILED,
                parent_code='AUTOMOTIVE',
                keywords=['전기차', 'EV', '배터리', '충전', '모터'],
                characteristics={
                    'growth_potential': 'very_high',
                    'volatility': 'high',
                    'innovation_cycle': 'fast',
                    'regulatory_support': 'high'
                },
                risk_factors=['배터리 기술', '충전 인프라', '정부 지원'],
                growth_drivers=['환경 규제', '배터리 기술 발전', '인프라 확충']
            ),
            'AUTONOMOUS_DRIVING': SectorClassification(
                code='AUTONOMOUS_DRIVING',
                name='자율주행',
                level=SectorLevel.DETAILED,
                parent_code='AUTOMOTIVE',
                keywords=['자율주행', 'ADAS', '센서', '라이다', '카메라'],
                characteristics={
                    'growth_potential': 'very_high',
                    'volatility': 'very_high',
                    'innovation_cycle': 'fast',
                    'technology_barrier': 'very_high'
                },
                risk_factors=['기술 복잡도', '안전성 검증', '규제 승인'],
                growth_drivers=['AI 기술', '센서 기술', '5G 네트워크']
            )
        }
        
        # 특화분류 (Specialized Sectors)
        specialized_sectors = {
            'HBM_MEMORY': SectorClassification(
                code='HBM_MEMORY',
                name='HBM메모리',
                level=SectorLevel.SPECIALIZED,
                parent_code='MEMORY_SEMICONDUCTOR',
                keywords=['HBM', '고대역폭', 'AI', '서버', 'GPU'],
                characteristics={
                    'growth_potential': 'very_high',
                    'volatility': 'very_high',
                    'technology_barrier': 'very_high',
                    'market_concentration': 'high'
                },
                risk_factors=['기술 독점', '수요 집중', '공급 제한'],
                growth_drivers=['AI 서버 폭증', 'GPU 성능 향상', '데이터센터 확장']
            ),
            'FINTECH': SectorClassification(
                code='FINTECH',
                name='핀테크',
                level=SectorLevel.SPECIALIZED,
                parent_code='BANKING',
                keywords=['핀테크', '모바일', '결제', '송금', '대출'],
                characteristics={
                    'growth_potential': 'very_high',
                    'volatility': 'high',
                    'innovation_cycle': 'fast',
                    'regulatory_uncertainty': 'medium'
                },
                risk_factors=['규제 변화', '경쟁 심화', '보안 리스크'],
                growth_drivers=['디지털 전환', '금융 포용성', 'API 개방']
            )
        }
        
        # 모든 분류를 하나의 딕셔너리에 통합
        all_sectors = {
            **major_sectors,
            **medium_sectors,
            **detailed_sectors,
            **specialized_sectors
        }
        
        self.sector_hierarchy = all_sectors
        
        # 키워드 매핑 생성
        for code, sector in all_sectors.items():
            if sector.keywords:
                for keyword in sector.keywords:
                    if keyword not in self.sector_keywords:
                        self.sector_keywords[keyword] = []
                    self.sector_keywords[keyword].append(code)
    
    def classify_company(self, company_name: str, business_description: str = "", 
                        current_sector: str = "") -> List[SectorClassification]:
        """회사 분류"""
        classifications = []
        
        # 1. 회사명 기반 분류
        name_classifications = self._classify_by_name(company_name)
        classifications.extend(name_classifications)
        
        # 2. 사업 설명 기반 분류
        if business_description:
            desc_classifications = self._classify_by_description(business_description)
            classifications.extend(desc_classifications)
        
        # 3. 현재 업종 기반 분류
        if current_sector:
            current_classifications = self._classify_by_current_sector(current_sector)
            classifications.extend(current_classifications)
        
        # 중복 제거 및 우선순위 정렬
        unique_classifications = self._deduplicate_and_rank(classifications)
        
        return unique_classifications
    
    def _classify_by_name(self, company_name: str) -> List[SectorClassification]:
        """회사명 기반 분류"""
        classifications = []
        
        # 직접 매칭
        for code, sector in self.sector_hierarchy.items():
            if any(keyword in company_name for keyword in sector.keywords):
                classifications.append(sector)
        
        # 특별한 회사명 패턴 매칭
        name_patterns = {
            '삼성': ['SEMICONDUCTOR', 'ELECTRONICS', 'SOFTWARE'],
            'SK': ['SEMICONDUCTOR', 'CHEMICAL', 'ENERGY'],
            'LG': ['ELECTRONICS', 'CHEMICAL', 'ENERGY'],
            '현대': ['AUTOMOTIVE', 'HEAVY_INDUSTRY'],
            '기아': ['AUTOMOTIVE'],
            'NAVER': ['SOFTWARE', 'FINTECH'],
            '카카오': ['SOFTWARE', 'FINTECH'],
            '셀트리온': ['BIOTECH', 'PHARMACEUTICAL'],
            '삼성바이오': ['BIOTECH', 'PHARMACEUTICAL']
        }
        
        for pattern, sector_codes in name_patterns.items():
            if pattern in company_name:
                for sector_code in sector_codes:
                    if sector_code in self.sector_hierarchy:
                        classifications.append(self.sector_hierarchy[sector_code])
        
        return classifications
    
    def _classify_by_description(self, description: str) -> List[SectorClassification]:
        """사업 설명 기반 분류"""
        classifications = []
        
        # 키워드 매칭
        for keyword, sector_codes in self.sector_keywords.items():
            if keyword in description.lower():
                for sector_code in sector_codes:
                    if sector_code in self.sector_hierarchy:
                        classifications.append(self.sector_hierarchy[sector_code])
        
        return classifications
    
    def _classify_by_current_sector(self, current_sector: str) -> List[SectorClassification]:
        """현재 업종 기반 분류"""
        classifications = []
        
        # 현재 업종 매핑
        sector_mapping = {
            '반도체': 'SEMICONDUCTOR',
            '전자': 'ELECTRONICS',
            '소프트웨어': 'SOFTWARE',
            '은행': 'BANKING',
            '보험': 'INSURANCE',
            '자동차': 'AUTOMOTIVE',
            '화학': 'CHEMICAL',
            '바이오': 'BIOTECH',
            '제약': 'PHARMACEUTICAL'
        }
        
        for korean_name, english_code in sector_mapping.items():
            if korean_name in current_sector:
                if english_code in self.sector_hierarchy:
                    classifications.append(self.sector_hierarchy[english_code])
        
        return classifications
    
    def _deduplicate_and_rank(self, classifications: List[SectorClassification]) -> List[SectorClassification]:
        """중복 제거 및 우선순위 정렬"""
        # 중복 제거
        unique_classifications = {}
        for classification in classifications:
            if classification.code not in unique_classifications:
                unique_classifications[classification.code] = classification
        
        # 우선순위 정렬 (특화 > 세분 > 중분 > 대분)
        priority_order = {
            SectorLevel.SPECIALIZED: 1,
            SectorLevel.DETAILED: 2,
            SectorLevel.MEDIUM: 3,
            SectorLevel.MAJOR: 4
        }
        
        sorted_classifications = sorted(
            unique_classifications.values(),
            key=lambda x: priority_order.get(x.level, 5)
        )
        
        return sorted_classifications
    
    def get_sector_metrics(self, sector_code: str) -> Optional[SectorMetrics]:
        """업종별 지표 조회"""
        # 실제로는 데이터베이스나 API에서 조회
        # 여기서는 시뮬레이션 데이터
        mock_metrics = {
            'SEMICONDUCTOR': SectorMetrics(
                sector_code='SEMICONDUCTOR',
                avg_per=15.2,
                avg_pbr=1.8,
                avg_roe=12.5,
                avg_roa=8.3,
                avg_debt_ratio=45.2,
                avg_growth_rate=8.5,
                market_cap_ratio=25.3,
                volatility=0.35,
                correlation_kospi=0.78,
                last_updated=datetime.now()
            ),
            'BANKING': SectorMetrics(
                sector_code='BANKING',
                avg_per=4.8,
                avg_pbr=0.4,
                avg_roe=8.2,
                avg_roa=0.9,
                avg_debt_ratio=95.8,
                avg_growth_rate=3.2,
                market_cap_ratio=15.7,
                volatility=0.18,
                correlation_kospi=0.85,
                last_updated=datetime.now()
            ),
            'AUTOMOTIVE': SectorMetrics(
                sector_code='AUTOMOTIVE',
                avg_per=12.5,
                avg_pbr=1.2,
                avg_roe=10.8,
                avg_roa=6.2,
                avg_debt_ratio=52.3,
                avg_growth_rate=5.8,
                market_cap_ratio=12.4,
                volatility=0.28,
                correlation_kospi=0.72,
                last_updated=datetime.now()
            )
        }
        
        return mock_metrics.get(sector_code)
    
    def analyze_sector_opportunities(self, sector_code: str) -> Dict[str, Any]:
        """업종별 투자 기회 분석"""
        if sector_code not in self.sector_hierarchy:
            return {}
        
        sector = self.sector_hierarchy[sector_code]
        metrics = self.get_sector_metrics(sector_code)
        
        if not metrics:
            return {}
        
        # 성장성 점수 (0-100)
        growth_score = min(100, metrics.avg_growth_rate * 10)
        
        # 수익성 점수 (0-100)
        profitability_score = min(100, (metrics.avg_roe + metrics.avg_roa) * 5)
        
        # 안정성 점수 (0-100, 높을수록 안정적)
        stability_score = max(0, 100 - metrics.volatility * 200)
        
        # 밸류에이션 점수 (0-100, 낮을수록 저평가)
        valuation_score = max(0, 100 - (metrics.avg_per / 30) * 100)
        
        # 종합 점수
        total_score = (
            growth_score * 0.3 +
            profitability_score * 0.25 +
            stability_score * 0.25 +
            valuation_score * 0.2
        )
        
        # 투자 등급
        if total_score >= 80:
            grade = 'A'
            recommendation = 'STRONG_BUY'
        elif total_score >= 70:
            grade = 'B'
            recommendation = 'BUY'
        elif total_score >= 60:
            grade = 'C'
            recommendation = 'HOLD'
        elif total_score >= 50:
            grade = 'D'
            recommendation = 'SELL'
        else:
            grade = 'F'
            recommendation = 'STRONG_SELL'
        
        return {
            'sector_code': sector_code,
            'sector_name': sector.name,
            'total_score': total_score,
            'grade': grade,
            'recommendation': recommendation,
            'scores': {
                'growth': growth_score,
                'profitability': profitability_score,
                'stability': stability_score,
                'valuation': valuation_score
            },
            'metrics': asdict(metrics) if metrics else None,
            'characteristics': sector.characteristics,
            'risk_factors': sector.risk_factors,
            'growth_drivers': sector.growth_drivers,
            'analysis_date': datetime.now().isoformat()
        }
    
    def get_sector_hierarchy(self, sector_code: str) -> Dict[str, Any]:
        """업종 계층 구조 조회"""
        if sector_code not in self.sector_hierarchy:
            return {}
        
        sector = self.sector_hierarchy[sector_code]
        
        # 부모 업종들 찾기
        parents = []
        current_sector = sector
        while current_sector.parent_code:
            if current_sector.parent_code in self.sector_hierarchy:
                parent = self.sector_hierarchy[current_sector.parent_code]
                parents.append(asdict(parent))
                current_sector = parent
            else:
                break
        
        # 자식 업종들 찾기
        children = []
        for code, child_sector in self.sector_hierarchy.items():
            if child_sector.parent_code == sector_code:
                children.append(asdict(child_sector))
        
        return {
            'current': asdict(sector),
            'parents': parents,
            'children': children,
            'level': sector.level.value,
            'depth': len(parents)
        }
    
    def export_sector_data(self, filename: str = None):
        """업종 데이터 내보내기"""
        if filename is None:
            filename = f"sector_classification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        export_data = {
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'total_sectors': len(self.sector_hierarchy),
                'version': '1.0'
            },
            'sectors': {}
        }
        
        for code, sector in self.sector_hierarchy.items():
            export_data['sectors'][code] = asdict(sector)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"💾 업종 분류 데이터 내보내기 완료: {filename}")
        return filename

def main():
    """메인 실행 함수"""
    classifier = EnhancedSectorClassifier()
    
    # 테스트 회사들
    test_companies = [
        {'name': '삼성전자', 'description': '반도체, 디스플레이, 모바일 사업', 'current_sector': '전자'},
        {'name': 'SK하이닉스', 'description': '메모리 반도체 제조', 'current_sector': '반도체'},
        {'name': 'NAVER', 'description': '인터넷 플랫폼, 클라우드, 핀테크', 'current_sector': '소프트웨어'},
        {'name': '현대차', 'description': '자동차 제조, 전기차, 자율주행', 'current_sector': '자동차'},
        {'name': '셀트리온', 'description': '바이오의약품, 항체 치료제', 'current_sector': '바이오'}
    ]
    
    print("🏭 향상된 업종 분류 테스트")
    print("=" * 80)
    
    for company in test_companies:
        print(f"\n📊 {company['name']} 분류 결과:")
        classifications = classifier.classify_company(
            company['name'],
            company['description'],
            company['current_sector']
        )
        
        for i, classification in enumerate(classifications[:3], 1):  # 상위 3개만 표시
            print(f"  {i}. {classification.name} ({classification.code}) - {classification.level.value}")
            
            # 투자 기회 분석
            opportunity = classifier.analyze_sector_opportunities(classification.code)
            if opportunity:
                print(f"     투자 점수: {opportunity['total_score']:.1f}점 ({opportunity['grade']})")
                print(f"     추천: {opportunity['recommendation']}")
        
        print("-" * 40)
    
    # 업종 데이터 내보내기
    classifier.export_sector_data()
    
    print("\n✅ 향상된 업종 분류 시스템 테스트 완료")

if __name__ == "__main__":
    main()
