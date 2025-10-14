#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
유니버스 품질 자동 진단 카드
필터 전후 ETF/우선주·리츠 제거율, 섹터 커버리지, 시총 커버리지 시각화
"""

import logging
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import Counter
import re

logger = logging.getLogger(__name__)

@dataclass
class UniverseDiagnosticResult:
    """유니버스 진단 결과"""
    total_stocks: int
    filtered_stocks: int
    etf_removed: int
    etn_removed: int
    reit_removed: int
    preferred_removed: int
    sector_coverage: Dict[str, int]
    market_cap_coverage: Dict[str, float]
    filter_effectiveness: Dict[str, float]
    quality_metrics: Dict[str, Any]

class UniverseQualityDiagnostic:
    """유니버스 품질 자동 진단 클래스"""
    
    def __init__(self):
        """초기화"""
        # ETF/ETN/REIT 필터링 키워드
        self.etf_keywords = {
            'ETF', 'ETN', 'ETP', 'KODEX', 'TIGER', 'ARIRANG', 'KOSEF', 
            'HANARO', 'KBSTAR', 'ACE', 'KINDEX', '레버리지', '인버스'
        }
        
        # 우선주 키워드
        self.preferred_keywords = {
            '우선주', '우B', '우선', 'PREFERRED'
        }
        
        # REIT 키워드
        self.reit_keywords = {
            'REIT', '리츠', '부동산투자'
        }
        
        # 섹터 분류
        self.sector_categories = {
            '금융': ['금융', '은행', '증권', '보험', '카드'],
            'IT': ['IT', '소프트웨어', '하드웨어', '인터넷', '게임'],
            '제조업': ['제조', '화학', '철강', '자동차', '전자'],
            '건설': ['건설', '건자재', '시멘트'],
            '유통': ['유통', '소매', '백화점', '마트'],
            '통신': ['통신', '방송', '미디어'],
            '에너지': ['에너지', '전력', '가스', '석유'],
            '바이오': ['바이오', '제약', '의료'],
            '기타': []
        }
    
    def diagnose_universe_quality(self, original_stocks: List[Dict], filtered_stocks: List[Dict]) -> UniverseDiagnosticResult:
        """
        유니버스 품질 진단
        
        Args:
            original_stocks: 필터링 전 원본 종목 리스트
            filtered_stocks: 필터링 후 종목 리스트
            
        Returns:
            UniverseDiagnosticResult: 진단 결과
        """
        try:
            # 기본 통계
            total_stocks = len(original_stocks)
            filtered_stocks_count = len(filtered_stocks)
            
            # 필터링 효과 분석
            filter_analysis = self._analyze_filter_effectiveness(original_stocks, filtered_stocks)
            
            # 섹터 커버리지 분석
            sector_coverage = self._analyze_sector_coverage(filtered_stocks)
            
            # 시가총액 커버리지 분석
            market_cap_coverage = self._analyze_market_cap_coverage(original_stocks, filtered_stocks)
            
            # 품질 메트릭 계산
            quality_metrics = self._calculate_quality_metrics(original_stocks, filtered_stocks)
            
            return UniverseDiagnosticResult(
                total_stocks=total_stocks,
                filtered_stocks=filtered_stocks_count,
                etf_removed=filter_analysis['etf_removed'],
                etn_removed=filter_analysis['etn_removed'],
                reit_removed=filter_analysis['reit_removed'],
                preferred_removed=filter_analysis['preferred_removed'],
                sector_coverage=sector_coverage,
                market_cap_coverage=market_cap_coverage,
                filter_effectiveness=filter_analysis['effectiveness'],
                quality_metrics=quality_metrics
            )
            
        except Exception as e:
            logger.error(f"유니버스 품질 진단 중 오류: {e}")
            return UniverseDiagnosticResult(
                total_stocks=0, filtered_stocks=0, etf_removed=0, etn_removed=0,
                reit_removed=0, preferred_removed=0, sector_coverage={},
                market_cap_coverage={}, filter_effectiveness={}, quality_metrics={}
            )
    
    def _analyze_filter_effectiveness(self, original_stocks: List[Dict], filtered_stocks: List[Dict]) -> Dict[str, Any]:
        """필터링 효과 분석"""
        original_names = {stock.get('name', '') for stock in original_stocks}
        filtered_names = {stock.get('name', '') for stock in filtered_stocks}
        
        # 제거된 종목들 분석
        removed_names = original_names - filtered_names
        
        etf_removed = 0
        etn_removed = 0
        reit_removed = 0
        preferred_removed = 0
        
        for name in removed_names:
            name_upper = name.upper()
            
            # ETF/ETN 제거 분석
            if any(keyword in name_upper for keyword in self.etf_keywords):
                if 'ETF' in name_upper:
                    etf_removed += 1
                elif 'ETN' in name_upper:
                    etn_removed += 1
            
            # REIT 제거 분석
            if any(keyword in name_upper for keyword in self.reit_keywords):
                reit_removed += 1
            
            # 우선주 제거 분석
            if any(keyword in name for keyword in self.preferred_keywords):
                preferred_removed += 1
        
        # 필터링 효과성 계산
        total_removed = len(removed_names)
        effectiveness = {
            'total_removed': total_removed,
            'removal_rate': (total_removed / len(original_names)) * 100 if original_names else 0,
            'etf_removal_rate': (etf_removed / len(original_names)) * 100 if original_names else 0,
            'etn_removal_rate': (etn_removed / len(original_names)) * 100 if original_names else 0,
            'reit_removal_rate': (reit_removed / len(original_names)) * 100 if original_names else 0,
            'preferred_removal_rate': (preferred_removed / len(original_names)) * 100 if original_names else 0
        }
        
        return {
            'etf_removed': etf_removed,
            'etn_removed': etn_removed,
            'reit_removed': reit_removed,
            'preferred_removed': preferred_removed,
            'effectiveness': effectiveness
        }
    
    def _analyze_sector_coverage(self, stocks: List[Dict]) -> Dict[str, int]:
        """섹터 커버리지 분석"""
        sector_counts = Counter()
        
        for stock in stocks:
            sector = stock.get('sector', '미분류')
            sector_counts[sector] += 1
        
        return dict(sector_counts)
    
    def _analyze_market_cap_coverage(self, original_stocks: List[Dict], filtered_stocks: List[Dict]) -> Dict[str, float]:
        """시가총액 커버리지 분석"""
        # 원본 시가총액 분포
        original_market_caps = [stock.get('market_cap', 0) for stock in original_stocks if stock.get('market_cap', 0) > 0]
        filtered_market_caps = [stock.get('market_cap', 0) for stock in filtered_stocks if stock.get('market_cap', 0) > 0]
        
        if not original_market_caps:
            return {}
        
        # 시가총액 구간별 분석
        original_total = sum(original_market_caps)
        filtered_total = sum(filtered_market_caps)
        
        # 상위 10%, 20%, 50% 커버리지
        original_sorted = sorted(original_market_caps, reverse=True)
        filtered_sorted = sorted(filtered_market_caps, reverse=True)
        
        top_10_threshold = original_sorted[int(len(original_sorted) * 0.1)] if original_sorted else 0
        top_20_threshold = original_sorted[int(len(original_sorted) * 0.2)] if original_sorted else 0
        top_50_threshold = original_sorted[int(len(original_sorted) * 0.5)] if original_sorted else 0
        
        coverage = {
            'total_market_cap_original': original_total,
            'total_market_cap_filtered': filtered_total,
            'market_cap_coverage_rate': (filtered_total / original_total) * 100 if original_total > 0 else 0,
            'top_10_coverage': len([cap for cap in filtered_market_caps if cap >= top_10_threshold]) / max(1, len([cap for cap in original_market_caps if cap >= top_10_threshold])) * 100,
            'top_20_coverage': len([cap for cap in filtered_market_caps if cap >= top_20_threshold]) / max(1, len([cap for cap in original_market_caps if cap >= top_20_threshold])) * 100,
            'top_50_coverage': len([cap for cap in filtered_market_caps if cap >= top_50_threshold]) / max(1, len([cap for cap in original_market_caps if cap >= top_50_threshold])) * 100
        }
        
        return coverage
    
    def _calculate_quality_metrics(self, original_stocks: List[Dict], filtered_stocks: List[Dict]) -> Dict[str, Any]:
        """품질 메트릭 계산"""
        if not filtered_stocks:
            return {}
        
        # 평균 PER, PBR, ROE
        per_values = [stock.get('per', 0) for stock in filtered_stocks if stock.get('per', 0) > 0]
        pbr_values = [stock.get('pbr', 0) for stock in filtered_stocks if stock.get('pbr', 0) > 0]
        roe_values = [stock.get('roe', 0) for stock in filtered_stocks if stock.get('roe', 0) > 0]
        
        metrics = {
            'avg_per': sum(per_values) / len(per_values) if per_values else 0,
            'avg_pbr': sum(pbr_values) / len(pbr_values) if pbr_values else 0,
            'avg_roe': sum(roe_values) / len(roe_values) if roe_values else 0,
            'median_per': sorted(per_values)[len(per_values)//2] if per_values else 0,
            'median_pbr': sorted(pbr_values)[len(pbr_values)//2] if pbr_values else 0,
            'median_roe': sorted(roe_values)[len(roe_values)//2] if roe_values else 0,
            'per_range': (min(per_values), max(per_values)) if per_values else (0, 0),
            'pbr_range': (min(pbr_values), max(pbr_values)) if pbr_values else (0, 0),
            'roe_range': (min(roe_values), max(roe_values)) if roe_values else (0, 0)
        }
        
        return metrics
    
    def create_diagnostic_dashboard(self, diagnostic_result: UniverseDiagnosticResult) -> go.Figure:
        """진단 대시보드 생성"""
        # 서브플롯 생성
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                '필터링 효과',
                '섹터 커버리지',
                '시가총액 커버리지',
                '품질 메트릭'
            ),
            specs=[[{"type": "bar"}, {"type": "pie"}],
                   [{"type": "bar"}, {"type": "bar"}]]
        )
        
        # 1. 필터링 효과
        filter_data = [
            diagnostic_result.etf_removed,
            diagnostic_result.etn_removed,
            diagnostic_result.reit_removed,
            diagnostic_result.preferred_removed
        ]
        filter_labels = ['ETF', 'ETN', 'REIT', '우선주']
        
        fig.add_trace(
            go.Bar(x=filter_labels, y=filter_data, name='제거된 종목 수'),
            row=1, col=1
        )
        
        # 2. 섹터 커버리지
        if diagnostic_result.sector_coverage:
            sectors = list(diagnostic_result.sector_coverage.keys())
            counts = list(diagnostic_result.sector_coverage.values())
            
            fig.add_trace(
                go.Pie(labels=sectors, values=counts, name='섹터 분포'),
                row=1, col=2
            )
        
        # 3. 시가총액 커버리지
        if diagnostic_result.market_cap_coverage:
            coverage_data = [
                diagnostic_result.market_cap_coverage.get('top_10_coverage', 0),
                diagnostic_result.market_cap_coverage.get('top_20_coverage', 0),
                diagnostic_result.market_cap_coverage.get('top_50_coverage', 0)
            ]
            coverage_labels = ['상위 10%', '상위 20%', '상위 50%']
            
            fig.add_trace(
                go.Bar(x=coverage_labels, y=coverage_data, name='시가총액 커버리지 (%)'),
                row=2, col=1
            )
        
        # 4. 품질 메트릭
        if diagnostic_result.quality_metrics:
            quality_data = [
                diagnostic_result.quality_metrics.get('avg_per', 0),
                diagnostic_result.quality_metrics.get('avg_pbr', 0),
                diagnostic_result.quality_metrics.get('avg_roe', 0)
            ]
            quality_labels = ['평균 PER', '평균 PBR', '평균 ROE']
            
            fig.add_trace(
                go.Bar(x=quality_labels, y=quality_data, name='평균 지표'),
                row=2, col=2
            )
        
        # 레이아웃 업데이트
        fig.update_layout(
            title_text="유니버스 품질 진단 대시보드",
            showlegend=False,
            height=800
        )
        
        return fig
    
    def generate_diagnostic_report(self, diagnostic_result: UniverseDiagnosticResult) -> str:
        """진단 보고서 생성"""
        report = []
        
        report.append("📊 유니버스 품질 진단 보고서")
        report.append("=" * 50)
        
        # 기본 통계
        report.append(f"📈 기본 통계:")
        report.append(f"  • 원본 종목 수: {diagnostic_result.total_stocks:,}개")
        report.append(f"  • 필터링 후: {diagnostic_result.filtered_stocks:,}개")
        report.append(f"  • 제거율: {((diagnostic_result.total_stocks - diagnostic_result.filtered_stocks) / diagnostic_result.total_stocks * 100):.1f}%")
        
        # 필터링 효과
        report.append(f"\n🔍 필터링 효과:")
        report.append(f"  • ETF 제거: {diagnostic_result.etf_removed}개")
        report.append(f"  • ETN 제거: {diagnostic_result.etn_removed}개")
        report.append(f"  • REIT 제거: {diagnostic_result.reit_removed}개")
        report.append(f"  • 우선주 제거: {diagnostic_result.preferred_removed}개")
        
        # 섹터 커버리지
        if diagnostic_result.sector_coverage:
            report.append(f"\n🏢 섹터 커버리지:")
            for sector, count in sorted(diagnostic_result.sector_coverage.items(), key=lambda x: x[1], reverse=True):
                report.append(f"  • {sector}: {count}개")
        
        # 시가총액 커버리지
        if diagnostic_result.market_cap_coverage:
            report.append(f"\n💰 시가총액 커버리지:")
            report.append(f"  • 상위 10% 커버리지: {diagnostic_result.market_cap_coverage.get('top_10_coverage', 0):.1f}%")
            report.append(f"  • 상위 20% 커버리지: {diagnostic_result.market_cap_coverage.get('top_20_coverage', 0):.1f}%")
            report.append(f"  • 상위 50% 커버리지: {diagnostic_result.market_cap_coverage.get('top_50_coverage', 0):.1f}%")
        
        # 품질 메트릭
        if diagnostic_result.quality_metrics:
            report.append(f"\n📊 품질 메트릭:")
            report.append(f"  • 평균 PER: {diagnostic_result.quality_metrics.get('avg_per', 0):.1f}배")
            report.append(f"  • 평균 PBR: {diagnostic_result.quality_metrics.get('avg_pbr', 0):.1f}배")
            report.append(f"  • 평균 ROE: {diagnostic_result.quality_metrics.get('avg_roe', 0):.1f}%")
        
        return "\n".join(report)


# 사용 예시
if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)
    
    diagnostic = UniverseQualityDiagnostic()
    
    # 테스트 데이터
    original_stocks = [
        {'name': '삼성전자', 'sector': '전기전자', 'market_cap': 1000000000000, 'per': 15.0, 'pbr': 1.2, 'roe': 12.0},
        {'name': 'KODEX 200', 'sector': 'ETF', 'market_cap': 500000000000, 'per': 0, 'pbr': 0, 'roe': 0},
        {'name': 'SK하이닉스', 'sector': '전기전자', 'market_cap': 800000000000, 'per': 8.0, 'pbr': 0.8, 'roe': 15.0},
        {'name': '삼성전자우', 'sector': '전기전자', 'market_cap': 200000000000, 'per': 14.0, 'pbr': 1.1, 'roe': 11.0},
    ]
    
    filtered_stocks = [
        {'name': '삼성전자', 'sector': '전기전자', 'market_cap': 1000000000000, 'per': 15.0, 'pbr': 1.2, 'roe': 12.0},
        {'name': 'SK하이닉스', 'sector': '전기전자', 'market_cap': 800000000000, 'per': 8.0, 'pbr': 0.8, 'roe': 15.0},
    ]
    
    # 진단 실행
    result = diagnostic.diagnose_universe_quality(original_stocks, filtered_stocks)
    
    # 보고서 생성
    report = diagnostic.generate_diagnostic_report(result)
    print(report)
