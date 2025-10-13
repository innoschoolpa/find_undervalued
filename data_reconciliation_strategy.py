#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
데이터 조정 전략 (Data Reconciliation Strategy)
KIS와 DART 재무자료 불일치 시 처리 방법

작성: 2025-10-12
버전: v2.2.2
"""

import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ReconciliationStrategy(Enum):
    """불일치 처리 전략"""
    
    PREFER_DART = "dart"          # DART 우선 (공식 공시)
    PREFER_KIS = "kis"            # KIS 우선 (최신 데이터)
    AVERAGE = "average"           # 평균값 사용
    CONSERVATIVE = "conservative" # 보수적 값 (낮은 ROE, 높은 부채비율)
    FLAG_AND_SKIP = "skip"        # 불일치 종목 제외
    WEIGHTED_BLEND = "weighted"   # 가중 평균 (신뢰도 기반)


class DataReconciliator:
    """
    데이터 조정기
    
    KIS와 DART 데이터 불일치 시 적절한 값을 선택하거나 조정
    """
    
    def __init__(self, strategy: ReconciliationStrategy = ReconciliationStrategy.CONSERVATIVE):
        """
        초기화
        
        Args:
            strategy: 기본 조정 전략
        """
        self.strategy = strategy
        
        # 메트릭별 허용 오차 (%)
        self.tolerance = {
            'roe': 10.0,      # ROE: ±10%
            'per': 15.0,      # PER: ±15%
            'pbr': 10.0,      # PBR: ±10%
            'debt_ratio': 20.0,  # 부채비율: ±20%
            'revenue': 5.0,   # 매출액: ±5%
        }
        
        # 신뢰도 가중치
        self.confidence_weights = {
            'dart': 0.7,  # DART는 공식 공시이므로 높은 가중치
            'kis': 0.3    # KIS는 실시간이지만 추정치 포함
        }
        
        logger.info(f"✅ DataReconciliator 초기화 (전략: {strategy.value})")
    
    def reconcile_metric(self, metric_name: str, kis_value: float, dart_value: float, 
                         strategy: Optional[ReconciliationStrategy] = None) -> Tuple[float, Dict]:
        """
        단일 메트릭 조정
        
        Args:
            metric_name: 메트릭 이름 ('roe', 'per', 'pbr' 등)
            kis_value: KIS 값
            dart_value: DART 값
            strategy: 조정 전략 (None이면 기본 전략 사용)
        
        Returns:
            (조정된 값, 메타데이터)
        """
        if strategy is None:
            strategy = self.strategy
        
        # 차이 계산
        diff = abs(kis_value - dart_value)
        avg_value = (kis_value + dart_value) / 2
        diff_pct = (diff / max(avg_value, 0.01)) * 100
        
        # 허용 오차 확인
        tolerance = self.tolerance.get(metric_name, 10.0)
        is_within_tolerance = diff_pct <= tolerance
        
        metadata = {
            'metric': metric_name,
            'kis': kis_value,
            'dart': dart_value,
            'diff': diff,
            'diff_pct': diff_pct,
            'tolerance': tolerance,
            'within_tolerance': is_within_tolerance,
            'strategy_used': strategy.value
        }
        
        # 허용 오차 내면 평균 사용
        if is_within_tolerance:
            reconciled = avg_value
            metadata['reason'] = '허용 오차 내 - 평균 사용'
            logger.debug(f"✅ {metric_name} 허용 오차 내: KIS {kis_value:.1f} ≈ DART {dart_value:.1f}")
        
        # 허용 오차 초과 시 전략 적용
        else:
            if strategy == ReconciliationStrategy.PREFER_DART:
                reconciled = dart_value
                metadata['reason'] = 'DART 우선 (공식 공시)'
                logger.info(f"📊 {metric_name} DART 우선: {dart_value:.1f} (KIS {kis_value:.1f}와 {diff_pct:.1f}% 차이)")
            
            elif strategy == ReconciliationStrategy.PREFER_KIS:
                reconciled = kis_value
                metadata['reason'] = 'KIS 우선 (최신 데이터)'
                logger.info(f"📡 {metric_name} KIS 우선: {kis_value:.1f} (DART {dart_value:.1f}와 {diff_pct:.1f}% 차이)")
            
            elif strategy == ReconciliationStrategy.AVERAGE:
                reconciled = avg_value
                metadata['reason'] = '평균값 사용'
                logger.info(f"📊 {metric_name} 평균 사용: {reconciled:.1f} (차이 {diff_pct:.1f}%)")
            
            elif strategy == ReconciliationStrategy.CONSERVATIVE:
                # 보수적 선택 (투자 안전성 우선)
                if metric_name in ['roe', 'revenue', 'operating_income']:
                    # 수익성 지표는 낮은 값 (보수적)
                    reconciled = min(kis_value, dart_value)
                    metadata['reason'] = '보수적 (낮은 수익성)'
                elif metric_name in ['debt_ratio', 'per', 'pbr']:
                    # 리스크 지표는 높은 값 (보수적)
                    reconciled = max(kis_value, dart_value)
                    metadata['reason'] = '보수적 (높은 리스크)'
                else:
                    reconciled = avg_value
                    metadata['reason'] = '평균값 (기본)'
                
                logger.info(f"⚖️ {metric_name} 보수적 선택: {reconciled:.1f} (차이 {diff_pct:.1f}%)")
            
            elif strategy == ReconciliationStrategy.WEIGHTED_BLEND:
                # 신뢰도 기반 가중 평균
                w_dart = self.confidence_weights['dart']
                w_kis = self.confidence_weights['kis']
                
                reconciled = dart_value * w_dart + kis_value * w_kis
                metadata['reason'] = f'가중 평균 (DART {w_dart*100:.0f}%, KIS {w_kis*100:.0f}%)'
                logger.info(f"⚖️ {metric_name} 가중 평균: {reconciled:.1f}")
            
            elif strategy == ReconciliationStrategy.FLAG_AND_SKIP:
                reconciled = None  # 불일치 종목은 제외
                metadata['reason'] = '불일치로 제외'
                logger.warning(f"🚫 {metric_name} 불일치 제외: {diff_pct:.1f}% 차이")
            
            else:
                reconciled = avg_value
                metadata['reason'] = '기본값 (평균)'
        
        metadata['reconciled_value'] = reconciled
        return reconciled, metadata
    
    def reconcile_stock_data(self, stock_code: str, kis_data: Dict, dart_data: Dict,
                            strategy: Optional[ReconciliationStrategy] = None) -> Tuple[Dict, List[Dict]]:
        """
        종목 전체 데이터 조정
        
        Args:
            stock_code: 종목코드
            kis_data: KIS 데이터
            dart_data: DART 데이터
            strategy: 조정 전략
        
        Returns:
            (조정된 데이터, 메타데이터 리스트)
        """
        if strategy is None:
            strategy = self.strategy
        
        reconciled = {
            'symbol': stock_code,
            'data_sources': []
        }
        
        metadata_list = []
        
        # KIS 데이터 기반
        if kis_data:
            reconciled.update(kis_data)
            reconciled['data_sources'].append('KIS')
        
        # DART 데이터와 비교 및 조정
        if dart_data:
            reconciled['data_sources'].append('DART')
            
            # 공통 메트릭 조정
            common_metrics = ['roe', 'debt_ratio']
            
            for metric in common_metrics:
                kis_val = kis_data.get(metric)
                dart_val = dart_data.get(metric)
                
                if kis_val is not None and dart_val is not None and kis_val > 0 and dart_val > 0:
                    # 조정
                    reconciled_val, meta = self.reconcile_metric(
                        metric, kis_val, dart_val, strategy
                    )
                    
                    if reconciled_val is not None:
                        reconciled[f'{metric}_reconciled'] = reconciled_val
                        reconciled[f'{metric}_kis'] = kis_val
                        reconciled[f'{metric}_dart'] = dart_val
                        
                        metadata_list.append(meta)
                    else:
                        # FLAG_AND_SKIP인 경우
                        reconciled[f'{metric}_flagged'] = True
                        metadata_list.append(meta)
            
            # DART 전용 데이터 추가
            if 'operating_margin' in dart_data:
                reconciled['operating_margin'] = dart_data['operating_margin']
            if 'net_margin' in dart_data:
                reconciled['net_margin'] = dart_data['net_margin']
        
        return reconciled, metadata_list
    
    def generate_reconciliation_report(self, metadata_list: List[Dict]) -> str:
        """
        조정 결과 리포트 생성
        
        Args:
            metadata_list: reconcile_stock_data의 메타데이터 리스트
        
        Returns:
            마크다운 리포트
        """
        if not metadata_list:
            return "## 조정 내역 없음"
        
        report = "## 📊 데이터 조정 내역\n\n"
        
        for meta in metadata_list:
            metric = meta['metric']
            kis = meta['kis']
            dart = meta['dart']
            reconciled = meta.get('reconciled_value', 0)
            diff_pct = meta['diff_pct']
            reason = meta['reason']
            
            status = "✅" if meta['within_tolerance'] else "⚠️"
            
            report += f"{status} **{metric.upper()}**\n"
            report += f"  - KIS: {kis:.2f}\n"
            report += f"  - DART: {dart:.2f}\n"
            report += f"  - 차이: {diff_pct:.1f}%\n"
            
            if reconciled:
                report += f"  - **조정값**: {reconciled:.2f}\n"
            
            report += f"  - 사유: {reason}\n\n"
        
        return report


# ===== 사용 예시 =====
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    print("\n" + "="*60)
    print("🧪 데이터 조정 전략 테스트")
    print("="*60)
    
    # 테스트 케이스: ROE 불일치
    test_cases = [
        {
            'name': '소폭 불일치 (허용 오차 내)',
            'kis_roe': 12.0,
            'dart_roe': 13.0,  # 8.3% 차이
            'expected': 'average'
        },
        {
            'name': '중간 불일치',
            'kis_roe': 15.0,
            'dart_roe': 20.0,  # 28% 차이
            'expected': 'conservative'
        },
        {
            'name': '대폭 불일치',
            'kis_roe': 10.0,
            'dart_roe': 138.58,  # 큰 차이 (실제 삼성전자 케이스)
            'expected': 'dart_preferred'
        }
    ]
    
    # 전략별 테스트
    strategies = [
        ReconciliationStrategy.CONSERVATIVE,
        ReconciliationStrategy.PREFER_DART,
        ReconciliationStrategy.AVERAGE,
        ReconciliationStrategy.WEIGHTED_BLEND
    ]
    
    for strategy in strategies:
        print(f"\n{'='*60}")
        print(f"전략: {strategy.value.upper()}")
        print(f"{'='*60}")
        
        reconciliator = DataReconciliator(strategy=strategy)
        
        for test_case in test_cases:
            print(f"\n📋 {test_case['name']}")
            
            kis_roe = test_case['kis_roe']
            dart_roe = test_case['dart_roe']
            
            reconciled, meta = reconciliator.reconcile_metric(
                'roe', kis_roe, dart_roe
            )
            
            print(f"   KIS: {kis_roe:.1f}%")
            print(f"   DART: {dart_roe:.1f}%")
            print(f"   차이: {meta['diff_pct']:.1f}%")
            print(f"   → 조정값: {reconciled:.1f}%")
            print(f"   사유: {meta['reason']}")
    
    # 전체 종목 데이터 조정 테스트
    print(f"\n{'='*60}")
    print("🔍 전체 종목 데이터 조정 테스트")
    print(f"{'='*60}")
    
    reconciliator = DataReconciliator(strategy=ReconciliationStrategy.CONSERVATIVE)
    
    # 모의 데이터
    kis_data = {
        'symbol': '005930',
        'name': '삼성전자',
        'roe': 12.0,
        'debt_ratio': 150.0,
        'per': 15.0
    }
    
    dart_data = {
        'roe': 138.58,
        'debt_ratio': 883.1,
        'operating_margin': 2.54,
        'net_margin': 5.59
    }
    
    reconciled_data, metadata_list = reconciliator.reconcile_stock_data(
        '005930', kis_data, dart_data
    )
    
    print(f"\n📊 조정 결과:")
    print(f"   데이터 소스: {reconciled_data['data_sources']}")
    print(f"   ROE (조정): {reconciled_data.get('roe_reconciled', 0):.2f}%")
    print(f"   ROE (KIS): {reconciled_data.get('roe_kis', 0):.2f}%")
    print(f"   ROE (DART): {reconciled_data.get('roe_dart', 0):.2f}%")
    print(f"   부채비율 (조정): {reconciled_data.get('debt_ratio_reconciled', 0):.1f}%")
    
    # 리포트 생성
    print(f"\n📄 조정 리포트:")
    print("-" * 60)
    report = reconciliator.generate_reconciliation_report(metadata_list)
    print(report)
    
    print("\n✅ 데이터 조정 전략 테스트 완료!")


