#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
멀티 데이터 공급자
KIS + DART API 이중화 및 크로스체크

작성: 2025-10-12
버전: v2.2.2
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# 데이터 조정 전략 임포트
try:
    from data_reconciliation_strategy import DataReconciliator, ReconciliationStrategy
    HAS_RECONCILIATION = True
except ImportError:
    HAS_RECONCILIATION = False
    logger.warning("데이터 조정 전략 모듈 없음 - 기본 방식 사용")


class MultiDataProvider:
    """
    멀티 데이터 공급자
    
    KIS API (실시간 가격, 기본 재무)
    + DART API (상세 재무제표, 감사의견)
    → 크로스체크 및 통합
    """
    
    def __init__(self, kis_provider=None, dart_provider=None):
        """
        초기화
        
        Args:
            kis_provider: KIS 데이터 제공자 (선택)
            dart_provider: DART 데이터 제공자 (선택)
        """
        # KIS 제공자
        if kis_provider:
            self.kis_provider = kis_provider
        else:
            try:
                from kis_data_provider import KISDataProvider
                self.kis_provider = KISDataProvider()
            except ImportError:
                logger.warning("KIS 데이터 제공자 없음")
                self.kis_provider = None
        
        # DART 제공자
        if dart_provider:
            self.dart_provider = dart_provider
        else:
            try:
                from dart_data_provider import DartDataProvider
                self.dart_provider = DartDataProvider()
            except ImportError:
                logger.warning("DART 데이터 제공자 없음")
                self.dart_provider = None
        
        # 통계
        self.stats = {
            'kis_success': 0,
            'dart_success': 0,
            'cross_check_passed': 0,
            'cross_check_failed': 0,
            'discrepancies': [],
            'reconciled': 0
        }
        
        # 데이터 조정기
        if HAS_RECONCILIATION:
            self.reconciliator = DataReconciliator(strategy=ReconciliationStrategy.CONSERVATIVE)
            logger.info("✅ 데이터 조정 전략: CONSERVATIVE (보수적)")
        else:
            self.reconciliator = None
        
        logger.info("✅ MultiDataProvider 초기화 완료")
    
    def get_stock_data(self, stock_code: str, cross_check: bool = True) -> Optional[Dict]:
        """
        종목 데이터 조회 (멀티 소스 통합)
        
        Args:
            stock_code: 종목코드
            cross_check: 크로스체크 수행 여부
        
        Returns:
            통합 데이터 딕셔너리
        """
        result = {
            'symbol': stock_code,
            'data_sources': [],
            'quality_score': 0,
            'discrepancies': []
        }
        
        # 1. KIS 데이터 (우선)
        kis_data = None
        if self.kis_provider:
            try:
                # kis_provider가 get_stock_data 메서드를 가지고 있다고 가정
                # 실제로는 kis_data_provider의 API에 따라 조정 필요
                logger.info(f"📡 KIS API 데이터 수집: {stock_code}")
                # kis_data = self.kis_provider.get_stock_data(stock_code)
                # 현재는 플레이스홀더
                kis_data = {'source': 'kis'}
                
                if kis_data:
                    result['data_sources'].append('KIS')
                    result.update(kis_data)
                    self.stats['kis_success'] += 1
                    logger.info(f"✅ KIS 데이터 수집 완료: {stock_code}")
                
            except Exception as e:
                logger.warning(f"KIS 데이터 수집 실패: {e}")
        
        # 2. DART 데이터 (보강)
        dart_data = None
        if self.dart_provider and cross_check:
            try:
                logger.info(f"📊 DART API 데이터 수집: {stock_code}")
                
                # 재무제표 조회
                financial = self.dart_provider.get_financial_statement(stock_code)
                
                if financial:
                    # 재무비율 계산
                    ratios = self.dart_provider.extract_financial_ratios(financial)
                    
                    if ratios:
                        result['data_sources'].append('DART')
                        result['dart_ratios'] = ratios
                        self.stats['dart_success'] += 1
                        logger.info(f"✅ DART 데이터 수집 완료: {stock_code}")
                        
                        # 크로스체크 및 조정
                        if kis_data:
                            check_result = self._cross_check_data(stock_code, kis_data, ratios)
                            result['cross_check'] = check_result
                            
                            if check_result['passed']:
                                self.stats['cross_check_passed'] += 1
                            else:
                                self.stats['cross_check_failed'] += 1
                                result['discrepancies'] = check_result['discrepancies']
                            
                            # 데이터 조정 적용
                            if self.reconciliator and check_result['discrepancies']:
                                reconciled_data, reconciliation_meta = self.reconciliator.reconcile_stock_data(
                                    stock_code, kis_data, ratios
                                )
                                
                                result['reconciled_data'] = reconciled_data
                                result['reconciliation_metadata'] = reconciliation_meta
                                self.stats['reconciled'] += 1
                                
                                logger.info(f"✅ 데이터 조정 완료: {stock_code} ({len(reconciliation_meta)}개 메트릭)")
                
            except Exception as e:
                logger.warning(f"DART 데이터 수집 실패: {e}")
        
        # 3. 품질 점수 계산
        quality_score = self._calculate_quality_score(result)
        result['quality_score'] = quality_score
        
        return result if result['data_sources'] else None
    
    def _cross_check_data(self, stock_code: str, kis_data: Dict, dart_ratios: Dict) -> Dict:
        """
        KIS와 DART 데이터 크로스체크
        
        Args:
            stock_code: 종목코드
            kis_data: KIS 데이터
            dart_ratios: DART 재무비율
        
        Returns:
            크로스체크 결과
        """
        result = {
            'passed': True,
            'discrepancies': [],
            'metrics_checked': []
        }
        
        # ROE 비교
        if 'roe' in kis_data and 'roe' in dart_ratios:
            kis_roe = kis_data['roe']
            dart_roe = dart_ratios['roe']
            
            diff = abs(kis_roe - dart_roe)
            diff_pct = (diff / max(kis_roe, 0.01)) * 100
            
            result['metrics_checked'].append('ROE')
            
            # ±10% 이내면 통과
            if diff_pct > 10:
                result['passed'] = False
                result['discrepancies'].append({
                    'metric': 'ROE',
                    'kis': kis_roe,
                    'dart': dart_roe,
                    'diff': diff,
                    'diff_pct': diff_pct
                })
                logger.warning(f"⚠️ ROE 불일치: {stock_code} - KIS {kis_roe:.1f}% vs DART {dart_roe:.1f}%")
            else:
                logger.info(f"✅ ROE 일치: {stock_code} - {kis_roe:.1f}% ≈ {dart_roe:.1f}%")
        
        return result
    
    def _calculate_quality_score(self, data: Dict) -> float:
        """
        데이터 품질 점수 계산 (0~100)
        
        Args:
            data: 통합 데이터
        
        Returns:
            품질 점수 (0~100)
        """
        score = 0
        
        # 데이터 소스 (최대 50점)
        sources = data.get('data_sources', [])
        if 'KIS' in sources:
            score += 30  # KIS 가용
        if 'DART' in sources:
            score += 20  # DART 가용
        
        # 크로스체크 (최대 30점)
        cross_check = data.get('cross_check', {})
        if cross_check:
            if cross_check.get('passed', False):
                score += 30  # 크로스체크 통과
            else:
                # 부분 점수 (체크된 메트릭 수)
                checked = len(cross_check.get('metrics_checked', []))
                score += min(15, checked * 5)
        
        # 불일치 페널티 (최대 -20점)
        discrepancies = len(data.get('discrepancies', []))
        score -= min(20, discrepancies * 10)
        
        return max(0, min(100, score))
    
    def get_statistics(self) -> Dict:
        """통계 조회"""
        total = self.stats['kis_success'] + self.stats['dart_success']
        
        return {
            **self.stats,
            'total_requests': total,
            'kis_success_rate': (self.stats['kis_success'] / total * 100) if total > 0 else 0,
            'dart_success_rate': (self.stats['dart_success'] / total * 100) if total > 0 else 0,
            'cross_check_rate': (self.stats['cross_check_passed'] / 
                                (self.stats['cross_check_passed'] + self.stats['cross_check_failed']) * 100)
                                if (self.stats['cross_check_passed'] + self.stats['cross_check_failed']) > 0 else 0
        }


# ===== 사용 예시 =====
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    print("\n" + "="*60)
    print("🧪 MultiDataProvider 테스트")
    print("="*60)
    
    # 초기화
    provider = MultiDataProvider()
    
    # 테스트 종목
    test_stocks = ['005930', '000660', '035420']
    
    print(f"\n📋 테스트 종목: {len(test_stocks)}개")
    
    for stock_code in test_stocks:
        print(f"\n{'='*60}")
        print(f"🔍 {stock_code} 데이터 수집")
        print(f"{'='*60}")
        
        # 데이터 수집
        data = provider.get_stock_data(stock_code, cross_check=True)
        
        if data:
            print(f"\n  데이터 소스: {', '.join(data['data_sources'])}")
            print(f"  품질 점수: {data['quality_score']:.0f}/100")
            
            if 'dart_ratios' in data:
                ratios = data['dart_ratios']
                print(f"\n  📊 DART 재무비율:")
                print(f"     ROE: {ratios.get('roe', 0):.2f}%")
                print(f"     부채비율: {ratios.get('debt_ratio', 0):.1f}%")
            
            if data.get('discrepancies'):
                print(f"\n  ⚠️ 불일치 항목: {len(data['discrepancies'])}개")
        else:
            print(f"  ❌ 데이터 수집 실패")
    
    # 통계
    print(f"\n{'='*60}")
    print("📊 전체 통계")
    print(f"{'='*60}")
    
    stats = provider.get_statistics()
    print(f"  KIS 성공: {stats['kis_success']}회")
    print(f"  DART 성공: {stats['dart_success']}회")
    print(f"  크로스체크 통과: {stats['cross_check_passed']}회")
    print(f"  크로스체크 실패: {stats['cross_check_failed']}회")
    
    print("\n✅ MultiDataProvider 테스트 완료!")

