"""
업종별 특화 분석이 통합된 향상된 분석기
기존 enhanced_integrated_analyzer_refactored.py를 확장하여 업종별 특화 분석 통합
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import yaml
from pathlib import Path

from enhanced_integrated_analyzer_refactored import (
    EnhancedIntegratedAnalyzer,
    AnalysisConfig,
    DataProvider,
    ScoreCalculator,
    DataValidator
)
from sector_specific_analyzer import (
    SectorSpecificAnalyzer,
    SectorType
)

logger = logging.getLogger(__name__)

@dataclass
class SectorAnalysisConfig:
    """업종별 분석 설정"""
    enable_sector_analysis: bool = True
    sector_weight_ratio: float = 0.3  # 업종별 분석이 전체 점수에 미치는 비율
    market_phase: str = "normal"  # normal, expansion, recession, peak
    enable_market_cycle_adjustment: bool = True

class SectorIntegratedDataProvider(DataProvider):
    """업종별 분석이 통합된 데이터 제공자"""
    
    def __init__(self, base_provider: DataProvider, sector_analyzer: SectorSpecificAnalyzer):
        self.base_provider = base_provider
        self.sector_analyzer = sector_analyzer
        self.logger = logging.getLogger(__name__)
    
    def get_stock_basic_info(self, symbol: str) -> Dict[str, Any]:
        """종목 기본 정보 조회 (업종 정보 포함)"""
        return self.base_provider.get_stock_basic_info(symbol)
    
    def get_stock_price_info(self, symbol: str) -> Dict[str, Any]:
        """주가 정보 조회"""
        return self.base_provider.get_stock_price_info(symbol)
    
    def get_financial_data(self, symbol: str) -> Dict[str, Any]:
        """재무 데이터 조회"""
        return self.base_provider.get_financial_data(symbol)
    
    def get_price_data(self, symbol: str) -> Dict[str, Any]:
        """가격 데이터 조회"""
        return self.base_provider.get_price_data(symbol)
    
    def get_sector_analysis(self, symbol: str, sector_name: str, 
                           financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """업종별 특화 분석 수행"""
        try:
            return self.sector_analyzer.analyze_stock_by_sector(
                symbol, sector_name, financial_data, "normal"
            )
        except Exception as e:
            self.logger.error(f"업종별 분석 실패 {symbol}: {e}")
            return {
                'sector_type': '기타',
                'sector_analysis': {'total_score': 50.0, 'sector_grade': 'C'},
                'adjusted_weights': {},
                'error': str(e)
            }

class SectorIntegratedScoreCalculator(ScoreCalculator):
    """업종별 분석이 통합된 점수 계산기"""
    
    def __init__(self, config: AnalysisConfig, sector_config: SectorAnalysisConfig):
        self.config = config
        self.sector_config = sector_config
        self.logger = logging.getLogger(__name__)
    
    def calculate_score(self, data: Dict[str, Any]) -> tuple[float, Dict[str, float]]:
        """통합 점수 계산 (업종별 분석 포함)"""
        try:
            # 기본 점수 계산
            base_score, base_breakdown = self._calculate_base_score(data)
            
            # 업종별 분석 점수 계산
            sector_score, sector_breakdown = self._calculate_sector_score(data)
            
            # 점수 통합
            if self.sector_config.enable_sector_analysis:
                # 업종별 분석 비율 적용
                sector_ratio = self.sector_config.sector_weight_ratio
                base_ratio = 1.0 - sector_ratio
                
                final_score = (base_score * base_ratio) + (sector_score * sector_ratio)
                
                # 통합 breakdown
                final_breakdown = {}
                for key, value in base_breakdown.items():
                    final_breakdown[f"기본_{key}"] = value * base_ratio
                for key, value in sector_breakdown.items():
                    final_breakdown[f"업종_{key}"] = value * sector_ratio
                
                final_breakdown['최종_점수'] = final_score
            else:
                final_score = base_score
                final_breakdown = base_breakdown
            
            return min(100, max(0, final_score)), final_breakdown
            
        except Exception as e:
            self.logger.error(f"점수 계산 실패: {e}")
            return 0.0, {'error': str(e)}
    
    def _calculate_base_score(self, data: Dict[str, Any]) -> tuple[float, Dict[str, float]]:
        """기본 점수 계산 (기존 로직)"""
        # 기존 EnhancedScoreCalculator 로직을 여기서 구현
        # 간단한 구현 예시
        score = 0.0
        breakdown = {}
        
        # 투자의견 점수
        opinion_data = data.get('opinion_analysis', {})
        opinion_score = self._calculate_opinion_score(opinion_data)
        score += opinion_score * 0.2
        breakdown['투자의견'] = opinion_score * 0.2
        
        # 재무비율 점수
        financial_data = data.get('financial_data', {})
        financial_score = self._calculate_financial_score(financial_data)
        score += financial_score * 0.3
        breakdown['재무비율'] = financial_score * 0.3
        
        # 성장성 점수
        growth_score = self._calculate_growth_score(financial_data)
        score += growth_score * 0.1
        breakdown['성장성'] = growth_score * 0.1
        
        # 규모 점수
        market_cap = data.get('market_cap', 0)
        scale_score = self._calculate_scale_score(market_cap)
        score += scale_score * 0.05
        breakdown['규모'] = scale_score * 0.05
        
        # 추정실적 점수 (간소화)
        estimate_score = 50.0  # 기본값
        score += estimate_score * 0.25
        breakdown['추정실적'] = estimate_score * 0.25
        
        return min(100, score), breakdown
    
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
            breakdown[f"업종_{key}"] = value
        
        return total_score, breakdown
    
    def _calculate_opinion_score(self, opinion_data: Dict[str, Any]) -> float:
        """투자의견 점수 계산"""
        consensus_score = opinion_data.get('consensus_score', 0)
        if consensus_score is None:
            return 50.0
        
        try:
            cs = float(consensus_score)
            cs = max(-1.0, min(1.0, cs))
            return (cs + 1.0) * 50.0  # -1~1 → 0~100
        except:
            return 50.0
    
    def _calculate_financial_score(self, financial_data: Dict[str, Any]) -> float:
        """재무비율 점수 계산"""
        score = 0.0
        
        # ROE 점수
        roe = DataValidator.safe_float(financial_data.get('roe', 0))
        if roe >= 20:
            score += 25
        elif roe >= 15:
            score += 20
        elif roe >= 10:
            score += 15
        elif roe >= 5:
            score += 10
        
        # 부채비율 점수
        debt_ratio = DataValidator.safe_float(financial_data.get('debt_ratio', 100))
        if debt_ratio <= 30:
            score += 25
        elif debt_ratio <= 50:
            score += 20
        elif debt_ratio <= 70:
            score += 15
        elif debt_ratio <= 100:
            score += 10
        
        # 순이익률 점수
        npm = DataValidator.safe_float(financial_data.get('net_profit_margin', 0))
        if npm >= 15:
            score += 25
        elif npm >= 10:
            score += 20
        elif npm >= 5:
            score += 15
        elif npm >= 2:
            score += 10
        
        # 유동비율 점수
        cr = DataValidator.safe_float(financial_data.get('current_ratio', 100))
        if cr >= 200:
            score += 25
        elif cr >= 150:
            score += 20
        elif cr >= 100:
            score += 15
        elif cr >= 50:
            score += 10
        
        return min(100, score)
    
    def _calculate_growth_score(self, financial_data: Dict[str, Any]) -> float:
        """성장성 점수 계산"""
        score = 0.0
        
        # 매출 성장률
        revenue_growth = DataValidator.safe_float(financial_data.get('revenue_growth_rate', 0))
        if revenue_growth > 20:
            score += 50
        elif revenue_growth > 10:
            score += 40
        elif revenue_growth > 5:
            score += 30
        elif revenue_growth > 0:
            score += 20
        
        # 영업이익 성장률
        operating_growth = DataValidator.safe_float(financial_data.get('operating_income_growth_rate', 0))
        if operating_growth > 30:
            score += 50
        elif operating_growth > 15:
            score += 40
        elif operating_growth > 5:
            score += 30
        elif operating_growth > 0:
            score += 20
        
        return min(100, score)
    
    def _calculate_scale_score(self, market_cap: float) -> float:
        """규모 점수 계산"""
        if market_cap >= 10_000_000_000_000:  # 10조원 이상
            return 100
        elif market_cap >= 1_000_000_000_000:  # 1조원 이상
            return 80
        elif market_cap >= 100_000_000_000:   # 1천억원 이상
            return 60
        elif market_cap >= 10_000_000_000:    # 1백억원 이상
            return 40
        else:
            return 20

class EnhancedSectorIntegratedAnalyzer:
    """업종별 특화 분석이 통합된 향상된 분석기"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.logger = logging.getLogger(__name__)
        
        # 설정 로드
        self.config = self._load_config(config_path)
        self.sector_config = SectorAnalysisConfig()
        
        # 컴포넌트 초기화
        self.sector_analyzer = SectorSpecificAnalyzer()
        
        # 데이터 제공자 초기화 (기존 시스템과 통합)
        from enhanced_integrated_analyzer_refactored import FinancialDataProvider, PriceDataProvider
        base_financial_provider = FinancialDataProvider()
        base_price_provider = PriceDataProvider()
        
        self.data_provider = SectorIntegratedDataProvider(
            base_financial_provider, self.sector_analyzer
        )
        
        # 점수 계산기 초기화
        self.score_calculator = SectorIntegratedScoreCalculator(
            self.config, self.sector_config
        )
    
    def _load_config(self, config_path: str) -> AnalysisConfig:
        """설정 파일 로드"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            enhanced_config = config_data.get('enhanced_integrated_analysis', {})
            return AnalysisConfig(
                weights=enhanced_config.get('weights', {}),
                financial_ratio_weights=enhanced_config.get('financial_ratio_weights', {}),
                grade_thresholds=enhanced_config.get('grade_thresholds', {})
            )
        except Exception as e:
            self.logger.warning(f"설정 로드 실패, 기본값 사용: {e}")
            return AnalysisConfig()
    
    def analyze_single_stock_enhanced(self, symbol: str, name: str, 
                                    days_back: int = 30) -> Dict[str, Any]:
        """단일 종목 향상된 분석 (업종별 특화 포함)"""
        try:
            self.logger.info(f"🔍 {name}({symbol}) 향상된 분석 시작")
            
            # 기본 데이터 수집
            basic_info = self.data_provider.get_stock_basic_info(symbol)
            financial_data = self.data_provider.get_financial_data(symbol)
            price_data = self.data_provider.get_price_data(symbol)
            
            # 업종 정보 추출
            sector_name = basic_info.get('sector', '기타')
            market_cap = basic_info.get('market_cap', 0)
            
            # 업종별 특화 분석
            sector_analysis = self.data_provider.get_sector_analysis(
                symbol, sector_name, financial_data
            )
            
            # 통합 데이터 구성
            integrated_data = {
                'symbol': symbol,
                'name': name,
                'market_cap': market_cap,
                'sector': sector_name,
                'financial_data': financial_data,
                'price_data': price_data,
                'sector_analysis': sector_analysis,
                'opinion_analysis': {},  # 향후 구현
                'estimate_analysis': {},  # 향후 구현
                'analysis_timestamp': self._get_timestamp()
            }
            
            # 통합 점수 계산
            final_score, score_breakdown = self.score_calculator.calculate_score(integrated_data)
            
            # 등급 결정
            grade = self._determine_grade(final_score)
            
            # 결과 구성
            result = {
                'symbol': symbol,
                'name': name,
                'market_cap': market_cap,
                'sector': sector_name,
                'enhanced_score': final_score,
                'enhanced_grade': grade,
                'score_breakdown': score_breakdown,
                'sector_analysis': sector_analysis,
                'financial_data': financial_data,
                'price_data': price_data,
                'analysis_timestamp': integrated_data['analysis_timestamp'],
                'status': 'success'
            }
            
            self.logger.info(f"✅ {name}({symbol}) 분석 완료: {final_score:.1f}점 ({grade})")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ {name}({symbol}) 분석 실패: {e}")
            return {
                'symbol': symbol,
                'name': name,
                'enhanced_score': 0,
                'enhanced_grade': 'F',
                'status': 'error',
                'error': str(e)
            }
    
    def _determine_grade(self, score: float) -> str:
        """점수에 따른 등급 결정"""
        if score >= 85:
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
    
    def _get_timestamp(self) -> str:
        """현재 시간 문자열 반환"""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def analyze_multiple_stocks(self, symbols: List[str], names: List[str]) -> List[Dict[str, Any]]:
        """다중 종목 분석"""
        results = []
        
        for symbol, name in zip(symbols, names):
            try:
                result = self.analyze_single_stock_enhanced(symbol, name)
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
    
    def find_undervalued_stocks(self, symbols: List[str], names: List[str], 
                               min_score: float = 40.0) -> List[Dict[str, Any]]:
        """저평가 종목 발굴"""
        results = self.analyze_multiple_stocks(symbols, names)
        
        # 점수 기준으로 필터링 및 정렬
        undervalued = [
            result for result in results 
            if result.get('enhanced_score', 0) >= min_score and result.get('status') == 'success'
        ]
        
        # 점수 순으로 정렬
        undervalued.sort(key=lambda x: x.get('enhanced_score', 0), reverse=True)
        
        return undervalued

