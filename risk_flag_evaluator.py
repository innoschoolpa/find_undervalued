#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
리스크 플래그 평가기 v2.2.2
회계/이벤트/유동성 리스크 감지 및 점수 감점

작성: 2025-10-12
"""

import logging
import statistics
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


class RiskFlagEvaluator:
    """
    리스크 플래그 평가 및 점수 조정
    
    평가 항목:
    - 회계 리스크: OCF 적자, 순이익 변동성, 감사의견, 자본잠식
    - 이벤트 리스크: 관리종목, 불성실공시, 투자유의/경고
    - 유동성 리스크: 거래대금 부족
    """
    
    def __init__(self):
        """초기화"""
        # 관리종목 리스트 (외부 소스 또는 수동 관리)
        self.management_stocks = set()
        
        # 불성실 공시 종목
        self.unfaithful_disclosure = set()
        
        # 투자유의 종목
        self.investment_caution = set()
        
        logger.info("✅ RiskFlagEvaluator 초기화 완료")
    
    def evaluate_all_risks(self, stock_data: Dict) -> Tuple[int, List[str]]:
        """
        모든 리스크 평가
        
        Args:
            stock_data: 종목 데이터 딕셔너리
        
        Returns:
            (총 감점, 경고 메시지 리스트)
        """
        total_penalty = 0
        warnings = []
        
        try:
            # 1. 회계 리스크
            accounting_penalties = self.evaluate_accounting_risks(stock_data)
            for risk_type, penalty, msg in accounting_penalties:
                total_penalty += penalty
                warnings.append(f"{risk_type}: {msg}")
                logger.debug(f"회계 리스크 감지: {stock_data.get('symbol')} - {risk_type} ({penalty}점)")
            
            # 2. 이벤트 리스크
            event_penalties = self.evaluate_event_risks(stock_data)
            for risk_type, penalty, msg in event_penalties:
                total_penalty += penalty
                warnings.append(f"{risk_type}: {msg}")
                logger.debug(f"이벤트 리스크 감지: {stock_data.get('symbol')} - {risk_type} ({penalty}점)")
            
            # 3. 유동성 리스크
            liquidity_result = self.evaluate_liquidity_risk(stock_data)
            if liquidity_result:
                risk_type, penalty, msg = liquidity_result
                total_penalty += penalty
                warnings.append(f"{risk_type}: {msg}")
                logger.debug(f"유동성 리스크 감지: {stock_data.get('symbol')} - {risk_type} ({penalty}점)")
        
        except Exception as e:
            logger.error(f"리스크 평가 중 오류: {e}", exc_info=True)
        
        if total_penalty < 0:
            logger.info(f"⚠️ {stock_data.get('symbol', 'N/A')} 총 리스크 감점: {total_penalty}점 "
                       f"({len(warnings)}개 경고)")
        
        return total_penalty, warnings
    
    def evaluate_accounting_risks(self, stock_data: Dict) -> List[Tuple[str, int, str]]:
        """
        회계 리스크 평가
        
        Returns:
            [(리스크 타입, 감점, 메시지), ...]
        """
        penalties = []
        
        try:
            # 1. 연속 OCF 적자 (3년)
            ocf_history = stock_data.get('operating_cash_flow_history', [])
            if len(ocf_history) >= 3:
                recent_ocf = ocf_history[-3:]
                if all(ocf < 0 for ocf in recent_ocf):
                    penalties.append((
                        'OCF_DEFICIT_3Y',
                        -15,
                        f"3년 연속 OCF 적자 ({recent_ocf[-1]/1e8:.0f}억원)"
                    ))
                    logger.warning(f"🚨 {stock_data.get('symbol')}: 3년 연속 OCF 적자")
                
                # 2년 연속 적자도 체크
                elif len(recent_ocf) >= 2 and all(ocf < 0 for ocf in recent_ocf[-2:]):
                    penalties.append((
                        'OCF_DEFICIT_2Y',
                        -8,
                        f"2년 연속 OCF 적자 ({recent_ocf[-1]/1e8:.0f}억원)"
                    ))
            
            # 2. 순이익 변동성 (CV > 1.0)
            net_income_history = stock_data.get('net_income_history', [])
            if len(net_income_history) >= 3:
                try:
                    # 음수 포함 계산
                    mean_ni = statistics.mean(net_income_history)
                    stdev_ni = statistics.stdev(net_income_history)
                    
                    if mean_ni != 0:
                        cv = abs(stdev_ni / mean_ni)
                        
                        if cv > 1.5:
                            penalties.append((
                                'EXTREME_VOLATILITY',
                                -12,
                                f"순이익 극심한 변동성 (CV={cv:.2f})"
                            ))
                        elif cv > 1.0:
                            penalties.append((
                                'HIGH_VOLATILITY',
                                -8,
                                f"순이익 변동성 높음 (CV={cv:.2f})"
                            ))
                            logger.info(f"⚠️ {stock_data.get('symbol')}: CV={cv:.2f}")
                    
                except Exception as e:
                    logger.debug(f"변동성 계산 실패: {e}")
            
            # 3. 감사의견 한정/부적정
            audit_opinion = stock_data.get('audit_opinion', '적정')
            if audit_opinion in ['한정', 'Qualified']:
                penalties.append((
                    'QUALIFIED_OPINION',
                    -15,
                    "감사의견 한정"
                ))
                logger.warning(f"🚨 {stock_data.get('symbol')}: 감사의견 한정")
            
            elif audit_opinion in ['부적정', 'Adverse', '의견거절', 'Disclaimer']:
                penalties.append((
                    'ADVERSE_OPINION',
                    -30,
                    f"감사의견 {audit_opinion}"
                ))
                logger.error(f"🚨 {stock_data.get('symbol')}: 감사의견 {audit_opinion}")
            
            # 4. 자본잠식
            capital_impairment = stock_data.get('capital_impairment_ratio', 0)
            if capital_impairment > 0:
                if capital_impairment >= 50:
                    penalties.append((
                        'SEVERE_IMPAIRMENT',
                        -25,
                        f"심각한 자본잠식 ({capital_impairment:.1f}%)"
                    ))
                    logger.error(f"🚨 {stock_data.get('symbol')}: 자본잠식 {capital_impairment:.1f}%")
                else:
                    penalties.append((
                        'CAPITAL_IMPAIRMENT',
                        -15,
                        f"자본잠식 ({capital_impairment:.1f}%)"
                    ))
            
            # 5. 부채비율 극단치
            debt_ratio = stock_data.get('debt_ratio', 0)
            if debt_ratio > 0:
                if debt_ratio > 500:
                    penalties.append((
                        'EXTREME_DEBT',
                        -12,
                        f"부채비율 과다 ({debt_ratio:.0f}%)"
                    ))
                elif debt_ratio > 300:
                    penalties.append((
                        'HIGH_DEBT',
                        -6,
                        f"부채비율 높음 ({debt_ratio:.0f}%)"
                    ))
        
        except Exception as e:
            logger.error(f"회계 리스크 평가 중 오류: {e}", exc_info=True)
        
        return penalties
    
    def evaluate_event_risks(self, stock_data: Dict) -> List[Tuple[str, int, str]]:
        """
        이벤트 리스크 평가
        
        Returns:
            [(리스크 타입, 감점, 메시지), ...]
        """
        penalties = []
        symbol = stock_data.get('symbol', '')
        
        try:
            # 1. 관리종목
            is_management = (
                symbol in self.management_stocks or 
                stock_data.get('is_management_stock', False)
            )
            
            if is_management:
                penalties.append((
                    'MANAGEMENT_STOCK',
                    -30,
                    "관리종목 지정"
                ))
                logger.warning(f"🚨 {symbol}: 관리종목 → -30점")
            
            # 2. 불성실 공시
            if symbol in self.unfaithful_disclosure or stock_data.get('unfaithful_disclosure'):
                penalties.append((
                    'UNFAITHFUL_DISCLOSURE',
                    -15,
                    "불성실 공시법인"
                ))
                logger.warning(f"🚨 {symbol}: 불성실 공시")
            
            # 3. 투자유의
            if symbol in self.investment_caution or stock_data.get('investment_caution'):
                penalties.append((
                    'INVESTMENT_CAUTION',
                    -10,
                    "투자유의 종목"
                ))
            
            # 4. 시장 경고 (거래정지 등)
            if stock_data.get('market_warning') or stock_data.get('trading_halt'):
                penalties.append((
                    'MARKET_WARNING',
                    -20,
                    "시장 경고/거래정지"
                ))
                logger.warning(f"🚨 {symbol}: 시장 경고")
            
            # 5. 최근 유상증자 (1년 이내 2회 이상)
            paid_in_capital_events = stock_data.get('paid_in_capital_count_1y', 0)
            if paid_in_capital_events >= 2:
                penalties.append((
                    'FREQUENT_CAPITAL_INCREASE',
                    -8,
                    f"1년 내 {paid_in_capital_events}회 유상증자"
                ))
        
        except Exception as e:
            logger.error(f"이벤트 리스크 평가 중 오류: {e}", exc_info=True)
        
        return penalties
    
    def evaluate_liquidity_risk(self, stock_data: Dict) -> Optional[Tuple[str, int, str]]:
        """
        유동성 리스크 평가
        
        Returns:
            (리스크 타입, 감점, 메시지) 또는 None
        """
        try:
            # 일평균 거래대금
            trading_value = stock_data.get('trading_value', 0)
            
            if trading_value > 0:
                # 1억 미만: 극도로 낮은 유동성
                if trading_value < 100_000_000:
                    logger.info(
                        f"⚠️ {stock_data.get('symbol')}: "
                        f"극저유동성 (거래대금 {trading_value/1e8:.2f}억)"
                    )
                    return (
                        'EXTREME_LOW_LIQUIDITY',
                        -10,
                        f"거래대금 {trading_value/1e8:.2f}억원"
                    )
                
                # 5억 미만: 낮은 유동성
                elif trading_value < 500_000_000:
                    return (
                        'LOW_LIQUIDITY',
                        -5,
                        f"거래대금 {trading_value/1e8:.2f}억원"
                    )
        
        except Exception as e:
            logger.error(f"유동성 리스크 평가 중 오류: {e}", exc_info=True)
        
        return None
    
    def load_management_stocks(self, source='krx'):
        """
        관리종목 리스트 로드
        
        Args:
            source: 데이터 소스 ('krx', 'file', 'api')
        """
        try:
            # TODO: 실제 구현 시 KRX API 또는 파일에서 로드
            # 현재는 빈 set으로 초기화
            self.management_stocks = set()
            
            logger.info(f"관리종목 리스트 로드 완료: {len(self.management_stocks)}개 (source={source})")
        
        except Exception as e:
            logger.error(f"관리종목 리스트 로드 실패: {e}", exc_info=True)
            self.management_stocks = set()
    
    def add_management_stock(self, symbol: str):
        """관리종목 수동 추가"""
        self.management_stocks.add(symbol)
        logger.info(f"관리종목 추가: {symbol}")
    
    def remove_management_stock(self, symbol: str):
        """관리종목 제거"""
        self.management_stocks.discard(symbol)
        logger.info(f"관리종목 제거: {symbol}")
    
    def get_risk_summary(self, stock_data: Dict) -> Dict:
        """
        리스크 요약 정보 반환
        
        Returns:
            {
                'total_penalty': int,
                'risk_level': str,  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
                'warnings': List[str],
                'details': Dict
            }
        """
        total_penalty, warnings = self.evaluate_all_risks(stock_data)
        
        # 리스크 레벨 결정
        if total_penalty >= -10:
            risk_level = 'LOW'
        elif total_penalty >= -20:
            risk_level = 'MEDIUM'
        elif total_penalty >= -30:
            risk_level = 'HIGH'
        else:
            risk_level = 'CRITICAL'
        
        return {
            'total_penalty': total_penalty,
            'risk_level': risk_level,
            'warning_count': len(warnings),
            'warnings': warnings,
            'symbol': stock_data.get('symbol', 'N/A'),
            'name': stock_data.get('name', 'N/A')
        }


# ==========================================
# Dummy 클래스 (폴백용)
# ==========================================

class DummyRiskEvaluator:
    """리스크 평가기 미사용 시 폴백"""
    
    def __init__(self):
        logger.info("⚠️ DummyRiskEvaluator 사용 (리스크 감점 비활성화)")
    
    def evaluate_all_risks(self, stock_data: Dict) -> Tuple[int, List[str]]:
        return 0, []
    
    def load_management_stocks(self, source='krx'):
        pass
    
    def get_risk_summary(self, stock_data: Dict) -> Dict:
        return {
            'total_penalty': 0,
            'risk_level': 'UNKNOWN',
            'warning_count': 0,
            'warnings': [],
            'symbol': stock_data.get('symbol', 'N/A'),
            'name': stock_data.get('name', 'N/A')
        }


if __name__ == '__main__':
    # 간단한 테스트
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    evaluator = RiskFlagEvaluator()
    evaluator.load_management_stocks()
    
    # 테스트 케이스 1: 정상 종목
    test_data_normal = {
        'symbol': '000001',
        'name': '정상종목',
        'per': 10,
        'pbr': 1.0,
        'roe': 12,
        'trading_value': 5_000_000_000  # 50억
    }
    
    penalty, warnings = evaluator.evaluate_all_risks(test_data_normal)
    print(f"\n✅ 정상 종목: 감점={penalty}, 경고={len(warnings)}개")
    
    # 테스트 케이스 2: 리스크 종목
    test_data_risky = {
        'symbol': '999999',
        'name': '리스크종목',
        'per': 10,
        'pbr': 1.0,
        'roe': 12,
        'operating_cash_flow_history': [-100, -200, -150],  # 3년 연속 적자
        'audit_opinion': '한정',
        'debt_ratio': 600,
        'trading_value': 80_000_000,  # 0.8억
        'is_management_stock': True
    }
    
    penalty, warnings = evaluator.evaluate_all_risks(test_data_risky)
    print(f"\n🚨 리스크 종목: 감점={penalty}, 경고={len(warnings)}개")
    for w in warnings:
        print(f"  - {w}")
    
    # 리스크 요약
    summary = evaluator.get_risk_summary(test_data_risky)
    print(f"\n📊 리스크 레벨: {summary['risk_level']}")
    
    print("\n✅ RiskFlagEvaluator 테스트 완료!")

