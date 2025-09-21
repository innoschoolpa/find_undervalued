"""
정성적 리스크 분석이 통합된 향상된 분석기
업종별 특화 분석 + 정성적 리스크 분석을 모두 통합한 최종 시스템
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import yaml
from pathlib import Path

from enhanced_sector_integrated_analyzer import (
    EnhancedSectorIntegratedAnalyzer,
    SectorAnalysisConfig
)
from qualitative_risk_analyzer import (
    QualitativeRiskAnalyzer,
    RiskType,
    RiskLevel
)
from sector_specific_analyzer import SectorSpecificAnalyzer

logger = logging.getLogger(__name__)

@dataclass
class QualitativeAnalysisConfig:
    """정성적 분석 설정"""
    enable_qualitative_risk: bool = True
    qualitative_weight_ratio: float = 0.2  # 정성적 분석이 전체 점수에 미치는 비율
    risk_threshold_high: float = 70.0  # 높은 리스크 임계값
    risk_threshold_medium: float = 50.0  # 보통 리스크 임계값
    enable_risk_penalty: bool = True  # 리스크 페널티 적용 여부

class QualitativeIntegratedScoreCalculator:
    """정성적 리스크가 통합된 점수 계산기"""
    
    def __init__(self, sector_config: SectorAnalysisConfig, qualitative_config: QualitativeAnalysisConfig):
        self.sector_config = sector_config
        self.qualitative_config = qualitative_config
        self.logger = logging.getLogger(__name__)
    
    def calculate_comprehensive_score(self, data: Dict[str, Any]) -> tuple[float, Dict[str, float]]:
        """종합 점수 계산 (업종별 + 정성적 리스크 통합)"""
        try:
            # 1. 업종별 분석 점수 계산
            sector_score, sector_breakdown = self._calculate_sector_score(data)
            
            # 2. 정성적 리스크 점수 계산
            qualitative_score, qualitative_breakdown = self._calculate_qualitative_score(data)
            
            # 3. 점수 통합
            if self.qualitative_config.enable_qualitative_risk:
                # 가중치 적용
                sector_weight = 1.0 - self.qualitative_config.qualitative_weight_ratio
                qualitative_weight = self.qualitative_config.qualitative_weight_ratio
                
                # 기본 통합 점수
                integrated_score = (sector_score * sector_weight) + (qualitative_score * qualitative_weight)
                
                # 리스크 조정 계수 적용
                risk_adjustment = data.get('qualitative_risk', {}).get('risk_adjustment_factor', 1.0)
                final_score = integrated_score * risk_adjustment
                
                # 통합 breakdown
                final_breakdown = {}
                for key, value in sector_breakdown.items():
                    if isinstance(value, (int, float)):
                        final_breakdown[f"업종_{key}"] = value * sector_weight
                for key, value in qualitative_breakdown.items():
                    if isinstance(value, (int, float)):
                        final_breakdown[f"정성_{key}"] = value * qualitative_weight
                
                final_breakdown['통합_점수'] = integrated_score
                final_breakdown['리스크_조정'] = risk_adjustment
                final_breakdown['최종_점수'] = final_score
            else:
                final_score = sector_score
                final_breakdown = sector_breakdown
            
            return min(100, max(0, final_score)), final_breakdown
            
        except Exception as e:
            self.logger.error(f"종합 점수 계산 실패: {e}")
            return 0.0, {'error': str(e)}
    
    def _calculate_sector_score(self, data: Dict[str, Any]) -> tuple[float, Dict[str, float]]:
        """업종별 분석 점수 계산"""
        sector_analysis = data.get('sector_analysis', {})
        if not sector_analysis:
            return 50.0, {'업종_분석': 50.0}
        
        sector_score_data = sector_analysis.get('sector_analysis', {})
        total_score = sector_score_data.get('total_score', 50.0)
        
        breakdown = {
            '업종_분석': total_score,
            '업종_등급': sector_score_data.get('sector_grade', 'C')
        }
        
        # 업종별 세부 breakdown 추가
        sector_breakdown = sector_score_data.get('breakdown', {})
        for key, value in sector_breakdown.items():
            if isinstance(value, (int, float)):
                breakdown[f"업종_{key}"] = value
        
        return total_score, breakdown
    
    def _calculate_qualitative_score(self, data: Dict[str, Any]) -> tuple[float, Dict[str, float]]:
        """정성적 리스크 점수 계산"""
        qualitative_risk = data.get('qualitative_risk', {})
        if not qualitative_risk:
            return 50.0, {'정성적_분석': 50.0}
        
        # 리스크 점수를 반전 (높은 리스크 = 낮은 점수)
        risk_score = qualitative_risk.get('comprehensive_risk_score', 50.0)
        qualitative_score = 100.0 - risk_score  # 리스크 반전
        
        breakdown = {
            '정성적_분석': qualitative_score,
            '리스크_레벨': qualitative_risk.get('comprehensive_risk_level', '보통'),
            '리스크_점수': risk_score
        }
        
        # 개별 리스크 breakdown 추가
        individual_risks = qualitative_risk.get('individual_risks', {})
        for risk_type, assessment in individual_risks.items():
            if hasattr(assessment, 'score'):
                risk_score_reversed = 100.0 - assessment.score
                breakdown[f"정성_{risk_type}"] = risk_score_reversed
        
        return qualitative_score, breakdown

class EnhancedQualitativeIntegratedAnalyzer:
    """정성적 리스크가 통합된 최종 향상된 분석기"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.logger = logging.getLogger(__name__)
        
        # 설정 초기화
        self.sector_config = SectorAnalysisConfig()
        self.qualitative_config = QualitativeAnalysisConfig()
        
        # 컴포넌트 초기화
        self.sector_analyzer = SectorSpecificAnalyzer()
        self.qualitative_risk_analyzer = QualitativeRiskAnalyzer()
        self.score_calculator = QualitativeIntegratedScoreCalculator(
            self.sector_config, self.qualitative_config
        )
        
        # Mock 데이터 제공자 (실제로는 API 연동)
        self.data_provider = MockDataProvider()
    
    def analyze_single_stock_comprehensive(self, symbol: str, name: str, 
                                         days_back: int = 30) -> Dict[str, Any]:
        """단일 종목 종합 분석 (업종별 + 정성적 리스크)"""
        try:
            self.logger.info(f"🔍 {name}({symbol}) 종합 분석 시작")
            
            # 1. 기본 데이터 수집
            basic_info = self.data_provider.get_stock_basic_info(symbol, name)
            financial_data = basic_info.get('financial_data', {})
            sector_name = basic_info.get('sector', '기타')
            market_cap = basic_info.get('market_cap', 0)
            
            # 2. 업종별 특화 분석
            sector_analysis = self.sector_analyzer.analyze_stock_by_sector(
                symbol, sector_name, financial_data, "normal"
            )
            
            # 3. 정성적 리스크 분석
            qualitative_risk = self.qualitative_risk_analyzer.analyze_comprehensive_risk(
                symbol, sector_name, financial_data
            )
            
            # 4. 통합 데이터 구성
            integrated_data = {
                'symbol': symbol,
                'name': name,
                'market_cap': market_cap,
                'sector': sector_name,
                'financial_data': financial_data,
                'sector_analysis': sector_analysis,
                'qualitative_risk': qualitative_risk,
                'analysis_timestamp': self._get_timestamp()
            }
            
            # 5. 종합 점수 계산
            final_score, score_breakdown = self.score_calculator.calculate_comprehensive_score(integrated_data)
            
            # 6. 등급 결정
            grade = self._determine_grade(final_score)
            
            # 7. 리스크 등급 결정
            risk_level = qualitative_risk.get('comprehensive_risk_level', '보통')
            risk_grade = self._determine_risk_grade(qualitative_risk.get('comprehensive_risk_score', 50))
            
            # 8. 투자 추천 생성
            recommendation = self._generate_investment_recommendation(final_score, risk_level)
            
            # 9. 결과 구성
            result = {
                'symbol': symbol,
                'name': name,
                'market_cap': market_cap,
                'sector': sector_name,
                'comprehensive_score': final_score,
                'comprehensive_grade': grade,
                'risk_level': risk_level,
                'risk_grade': risk_grade,
                'investment_recommendation': recommendation,
                'score_breakdown': score_breakdown,
                'sector_analysis': sector_analysis,
                'qualitative_risk': qualitative_risk,
                'financial_data': financial_data,
                'analysis_timestamp': integrated_data['analysis_timestamp'],
                'status': 'success'
            }
            
            self.logger.info(f"✅ {name}({symbol}) 종합 분석 완료: {final_score:.1f}점 ({grade}) | 리스크: {risk_level}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ {name}({symbol}) 종합 분석 실패: {e}")
            return {
                'symbol': symbol,
                'name': name,
                'comprehensive_score': 0,
                'comprehensive_grade': 'F',
                'risk_level': '높음',
                'risk_grade': 'D',
                'investment_recommendation': '투자 자제',
                'status': 'error',
                'error': str(e)
            }
    
    def _determine_grade(self, score: float) -> str:
        """점수에 따른 등급 결정"""
        if score >= 90:
            return "S"  # 최고 등급
        elif score >= 85:
            return "A+"
        elif score >= 75:
            return "A"
        elif score >= 65:
            return "B+"
        elif score >= 55:
            return "B"
        elif score >= 45:
            return "C+"
        elif score >= 35:
            return "C"
        elif score >= 25:
            return "D"
        else:
            return "F"
    
    def _determine_risk_grade(self, risk_score: float) -> str:
        """리스크 점수에 따른 등급 결정"""
        if risk_score >= 80:
            return "D"  # 높은 리스크
        elif risk_score >= 60:
            return "C"  # 보통 리스크
        elif risk_score >= 40:
            return "B"  # 낮은 리스크
        else:
            return "A"  # 매우 낮은 리스크
    
    def _generate_investment_recommendation(self, score: float, risk_level: str) -> str:
        """투자 추천 생성"""
        if score >= 80 and risk_level in ['매우_낮음', '낮음']:
            return "강력 매수"
        elif score >= 70 and risk_level in ['매우_낮음', '낮음', '보통']:
            return "매수"
        elif score >= 60 and risk_level in ['낮음', '보통']:
            return "신중 매수"
        elif score >= 50 and risk_level in ['보통']:
            return "중립"
        elif score >= 40 and risk_level in ['보통', '높음']:
            return "신중 매도"
        elif score >= 30:
            return "매도"
        else:
            return "강력 매도"
    
    def _get_timestamp(self) -> str:
        """현재 시간 문자열 반환"""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def analyze_multiple_stocks(self, symbols: List[str], names: List[str]) -> List[Dict[str, Any]]:
        """다중 종목 종합 분석"""
        results = []
        
        for symbol, name in zip(symbols, names):
            try:
                result = self.analyze_single_stock_comprehensive(symbol, name)
                results.append(result)
            except Exception as e:
                self.logger.error(f"종목 분석 실패 {symbol}: {e}")
                results.append({
                    'symbol': symbol,
                    'name': name,
                    'status': 'error',
                    'error': str(e)
                })
        
        return results
    
    def find_premium_undervalued_stocks(self, symbols: List[str], names: List[str], 
                                       min_score: float = 60.0, max_risk_level: str = "보통") -> List[Dict[str, Any]]:
        """프리미엄 저평가 종목 발굴 (고점수 + 저리스크)"""
        results = self.analyze_multiple_stocks(symbols, names)
        
        # 필터링 조건
        premium_stocks = []
        for result in results:
            if result.get('status') != 'success':
                continue
            
            score = result.get('comprehensive_score', 0)
            risk_level = result.get('risk_level', '높음')
            
            # 점수와 리스크 조건 확인
            if score >= min_score:
                # 리스크 레벨 매핑
                risk_levels = ['매우_낮음', '낮음', '보통', '높음', '매우_높음']
                risk_threshold = risk_levels.index(max_risk_level) if max_risk_level in risk_levels else 2
                current_risk = risk_levels.index(risk_level) if risk_level in risk_levels else 4
                
                if current_risk <= risk_threshold:
                    premium_stocks.append(result)
        
        # 점수 순으로 정렬
        premium_stocks.sort(key=lambda x: x.get('comprehensive_score', 0), reverse=True)
        
        return premium_stocks
    
    def generate_analysis_report(self, results: List[Dict[str, Any]]) -> str:
        """분석 결과 리포트 생성"""
        if not results:
            return "분석 결과가 없습니다."
        
        report = []
        report.append("=" * 80)
        report.append("🎯 종합 저평가 가치주 분석 리포트")
        report.append("=" * 80)
        
        # 상위 10개 종목
        top_stocks = results[:10]
        
        for i, stock in enumerate(top_stocks, 1):
            if stock.get('status') != 'success':
                continue
            
            symbol = stock.get('symbol', 'N/A')
            name = stock.get('name', 'N/A')
            score = stock.get('comprehensive_score', 0)
            grade = stock.get('comprehensive_grade', 'F')
            risk_level = stock.get('risk_level', '높음')
            recommendation = stock.get('investment_recommendation', '투자 자제')
            
            report.append(f"\n{i:2d}. {name} ({symbol})")
            report.append(f"    종합 점수: {score:.1f}점 ({grade})")
            report.append(f"    리스크 레벨: {risk_level}")
            report.append(f"    투자 추천: {recommendation}")
        
        # 통계 정보
        successful_results = [r for r in results if r.get('status') == 'success']
        if successful_results:
            avg_score = sum(r.get('comprehensive_score', 0) for r in successful_results) / len(successful_results)
            report.append(f"\n📊 분석 통계:")
            report.append(f"    분석 종목 수: {len(successful_results)}")
            report.append(f"    평균 점수: {avg_score:.1f}점")
            
            # 등급별 분포
            grade_dist = {}
            for result in successful_results:
                grade = result.get('comprehensive_grade', 'F')
                grade_dist[grade] = grade_dist.get(grade, 0) + 1
            
            report.append(f"    등급 분포: {dict(grade_dist)}")
        
        report.append("\n" + "=" * 80)
        return "\n".join(report)

class MockDataProvider:
    """Mock 데이터 제공자 (테스트용)"""
    
    def get_stock_basic_info(self, symbol: str, name: str) -> Dict[str, Any]:
        """Mock 기본 정보 반환"""
        # 시프트업 데이터
        if symbol == "462870":
            return {
                'symbol': symbol,
                'name': name,
                'sector': '게임업',
                'market_cap': 24394 * 100000000,  # 24394억원
                'financial_data': {
                    'roe': 31.3,
                    'roa': 25.0,
                    'debt_ratio': 15.5,
                    'current_ratio': 250.0,
                    'revenue_growth_rate': 63.07,
                    'operating_income_growth_rate': 85.33,
                    'net_income_growth_rate': 106.67,
                    'net_profit_margin': 36.48,
                    'per': 15.2,
                    'pbr': 3.1
                }
            }
        # 한미반도체 데이터
        elif symbol == "042700":
            return {
                'symbol': symbol,
                'name': name,
                'sector': '반도체',
                'market_cap': 89879 * 100000000,  # 89879억원
                'financial_data': {
                    'roe': 42.29,
                    'roa': 33.38,
                    'debt_ratio': 26.71,
                    'current_ratio': 284.28,
                    'revenue_growth_rate': 63.07,
                    'operating_income_growth_rate': 85.33,
                    'net_income_growth_rate': 106.67,
                    'net_profit_margin': 36.48,
                    'per': 59.31,
                    'pbr': 13.06
                }
            }
        # 기아 데이터
        elif symbol == "000270":
            return {
                'symbol': symbol,
                'name': name,
                'sector': '제조업',
                'market_cap': 402058 * 100000000,  # 402058억원
                'financial_data': {
                    'roe': 16.54,
                    'roa': 10.05,
                    'debt_ratio': 64.58,
                    'current_ratio': 150.22,
                    'revenue_growth_rate': 6.67,
                    'operating_income_growth_rate': -18.33,
                    'net_income_growth_rate': -19.16,
                    'net_profit_margin': 8.12,
                    'per': 4.16,
                    'pbr': 0.72
                }
            }
        else:
            # 기본 데이터
            return {
                'symbol': symbol,
                'name': name,
                'sector': '기타',
                'market_cap': 100000 * 100000000,  # 100000억원
                'financial_data': {
                    'roe': 10.0,
                    'roa': 8.0,
                    'debt_ratio': 50.0,
                    'current_ratio': 150.0,
                    'revenue_growth_rate': 5.0,
                    'operating_income_growth_rate': 10.0,
                    'net_income_growth_rate': 8.0,
                    'net_profit_margin': 10.0,
                    'per': 15.0,
                    'pbr': 2.0
                }
            }
