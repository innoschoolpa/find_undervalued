"""
순위 다양화 모듈

섹터 쿼터와 동점 타이브레이커를 통한 순위 다양화를 제공합니다.
"""

import logging
from typing import Any, Dict, List, Optional

from metrics import MetricsCollector


class RankingDiversificationManager:
    """순위 다양화 클래스 (섹터 쿼터, 동점 타이브레이커)"""
    
    def __init__(self, metrics_collector: MetricsCollector = None):
        self.metrics = metrics_collector
        # 섹터 쿼터 정책
        self.sector_quota_policy = {
            'max_per_sector': 0.25,      # 섹터당 최대 25%
            'min_diversification': 0.05,  # 최소 5% (20개 섹터)
            'preferred_sectors': 10       # 선호 섹터 수
        }
        # 시가총액 밴드 정책
        self.size_band_policy = {
            'large_cap_threshold': 100000,  # 10조원 이상
            'mid_cap_threshold': 10000,     # 1조원 이상
            'small_cap_threshold': 1000,    # 1000억원 이상
            'max_per_band': 0.4            # 밴드당 최대 40%
        }
        # 동점 타이브레이커 정책
        self.tie_breaker_weights = {
            'market_cap': 0.3,            # 시가총액 30%
            'price_position': 0.25,       # 가격위치 25%
            'margin_of_safety': 0.25,     # 안전마진 25%
            'quality_score': 0.2          # 품질 점수 20%
        }
    
    def classify_size_band(self, market_cap: float) -> str:
        """시가총액 밴드 분류"""
        if market_cap >= self.size_band_policy['large_cap_threshold']:
            return 'large_cap'
        elif market_cap >= self.size_band_policy['mid_cap_threshold']:
            return 'mid_cap'
        elif market_cap >= self.size_band_policy['small_cap_threshold']:
            return 'small_cap'
        else:
            return 'micro_cap'
    
    def apply_sector_quota(self, ranked_stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """섹터 쿼터 적용"""
        try:
            # 섹터별 개수 계산
            sector_counts = {}
            sector_stocks = {}
            
            for stock in ranked_stocks:
                sector = stock.get('sector_analysis', {}).get('grade', 'Unknown')
                if sector not in sector_counts:
                    sector_counts[sector] = 0
                    sector_stocks[sector] = []
                
                sector_counts[sector] += 1
                sector_stocks[sector].append(stock)
            
            # 쿼터 적용
            total_stocks = len(ranked_stocks)
            max_per_sector = int(total_stocks * self.sector_quota_policy['max_per_sector'])
            
            diversified_stocks = []
            for sector, stocks in sector_stocks.items():
                # 상위 N개만 선택
                selected_stocks = stocks[:max_per_sector]
                diversified_stocks.extend(selected_stocks)
                
                # 메트릭 기록
                if self.metrics and len(stocks) > max_per_sector:
                    self.metrics.record_ranking_diversification_skips(
                        len(stocks) - max_per_sector
                    )
            
            # 원래 순위대로 재정렬
            diversified_stocks.sort(key=lambda x: x.get('rank', 0))
            
            return diversified_stocks
            
        except Exception as e:
            logging.warning(f"섹터 쿼터 적용 실패: {e}")
            return ranked_stocks
    
    def apply_size_band_diversification(self, ranked_stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """시가총액 밴드 다양화 적용"""
        try:
            # 밴드별 분류
            band_stocks = {}
            for stock in ranked_stocks:
                market_cap = stock.get('market_cap', 0)
                band = self.classify_size_band(market_cap)
                
                if band not in band_stocks:
                    band_stocks[band] = []
                band_stocks[band].append(stock)
            
            # 밴드별 쿼터 적용
            total_stocks = len(ranked_stocks)
            max_per_band = int(total_stocks * self.size_band_policy['max_per_band'])
            
            diversified_stocks = []
            for band, stocks in band_stocks.items():
                selected_stocks = stocks[:max_per_band]
                diversified_stocks.extend(selected_stocks)
            
            # 원래 순위대로 재정렬
            diversified_stocks.sort(key=lambda x: x.get('rank', 0))
            
            return diversified_stocks
            
        except Exception as e:
            logging.warning(f"시가총액 밴드 다양화 실패: {e}")
            return ranked_stocks
    
    def apply_tie_breaker(self, stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """동점 타이브레이커 적용"""
        def tie_breaker_key(stock):
            """타이브레이커 키 함수"""
            try:
                # 각 지표별 점수 계산
                market_cap_score = min(100, stock.get('market_cap', 0) / 10000)  # 10조원 = 100점
                price_position_score = 100 - stock.get('price_position', 50)  # 낮을수록 좋음
                margin_of_safety_score = min(100, stock.get('margin_of_safety', 0) * 200)  # 50% = 100점
                quality_score = stock.get('quality_score', 50)
                
                # 가중 평균
                tie_breaker_score = (
                    market_cap_score * self.tie_breaker_weights['market_cap'] +
                    price_position_score * self.tie_breaker_weights['price_position'] +
                    margin_of_safety_score * self.tie_breaker_weights['margin_of_safety'] +
                    quality_score * self.tie_breaker_weights['quality_score']
                )
                
                return tie_breaker_score
                
            except Exception as e:
                logging.warning(f"타이브레이커 점수 계산 실패: {e}")
                return 0
        
        try:
            # 동점 그룹별로 타이브레이커 적용
            grouped_stocks = {}
            
            for stock in stocks:
                main_score = stock.get('enhanced_score', 0)
                score_key = round(main_score, 1)  # 소수점 첫째자리까지 그룹화
                
                if score_key not in grouped_stocks:
                    grouped_stocks[score_key] = []
                grouped_stocks[score_key].append(stock)
            
            # 각 그룹 내에서 타이브레이커 정렬
            final_stocks = []
            for score_key in sorted(grouped_stocks.keys(), reverse=True):
                group_stocks = grouped_stocks[score_key]
                
                if len(group_stocks) > 1:
                    # 타이브레이커 적용
                    group_stocks.sort(key=tie_breaker_key, reverse=True)
                
                final_stocks.extend(group_stocks)
            
            return final_stocks
            
        except Exception as e:
            logging.warning(f"타이브레이커 적용 실패: {e}")
            return stocks
    
    def apply_concentration_risk_management(self, stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """집중 리스크 관리"""
        try:
            # 집중 리스크 메트릭 계산
            concentration_metrics = self.calculate_concentration_metrics(stocks)
            
            # 집중도가 높은 경우 조정
            if concentration_metrics['herfindahl_index'] > 0.3:  # 30% 이상
                # 상위 종목들의 가중치 조정
                adjusted_stocks = []
                max_weight = 0.15  # 개별 종목 최대 15%
                
                for stock in stocks:
                    adjusted_stock = stock.copy()
                    original_weight = stock.get('weight', 1.0 / len(stocks))
                    
                    if original_weight > max_weight:
                        adjusted_stock['weight'] = max_weight
                        adjusted_stock['concentration_adjusted'] = True
                    
                    adjusted_stocks.append(adjusted_stock)
                
                return adjusted_stocks
            
            return stocks
            
        except Exception as e:
            logging.warning(f"집중 리스크 관리 실패: {e}")
            return stocks
    
    def calculate_concentration_metrics(self, stocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """집중도 메트릭 계산"""
        try:
            if not stocks:
                return {'herfindahl_index': 0, 'top_10_concentration': 0}
            
            # 가중치 계산 (없으면 균등 가중)
            weights = []
            total_market_cap = sum(stock.get('market_cap', 0) for stock in stocks)
            
            for stock in stocks:
                if total_market_cap > 0:
                    weight = stock.get('market_cap', 0) / total_market_cap
                else:
                    weight = 1.0 / len(stocks)
                weights.append(weight)
            
            # 허핀달 지수 계산
            herfindahl_index = sum(w ** 2 for w in weights)
            
            # 상위 10개 집중도
            sorted_weights = sorted(weights, reverse=True)
            top_10_concentration = sum(sorted_weights[:min(10, len(sorted_weights))])
            
            return {
                'herfindahl_index': herfindahl_index,
                'top_10_concentration': top_10_concentration,
                'total_stocks': len(stocks),
                'effective_stocks': 1 / herfindahl_index if herfindahl_index > 0 else len(stocks)
            }
            
        except Exception as e:
            logging.warning(f"집중도 메트릭 계산 실패: {e}")
            return {'herfindahl_index': 0, 'top_10_concentration': 0}
    
    def apply_comprehensive_diversification(self, ranked_stocks: List[Dict[str, Any]], 
                                          max_stocks: int = None, 
                                          existing_portfolio: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """종합 다양화 적용"""
        try:
            original_count = len(ranked_stocks)
            
            # 1. 동점 타이브레이커 적용
            diversified_stocks = self.apply_tie_breaker(ranked_stocks)
            
            # 2. 섹터 쿼터 적용
            diversified_stocks = self.apply_sector_quota(diversified_stocks)
            
            # 3. 시가총액 밴드 다양화 적용
            diversified_stocks = self.apply_size_band_diversification(diversified_stocks)
            
            # 4. 집중 리스크 관리
            diversified_stocks = self.apply_concentration_risk_management(diversified_stocks)
            
            # 5. 최대 종목 수 제한 (있는 경우)
            if max_stocks and len(diversified_stocks) > max_stocks:
                diversified_stocks = diversified_stocks[:max_stocks]
            
            # 6. 기존 포트폴리오 고려 (있는 경우)
            if existing_portfolio:
                diversified_stocks = self._adjust_for_existing_portfolio(
                    diversified_stocks, existing_portfolio
                )
            
            # 집중도 메트릭 계산
            concentration_metrics = self.calculate_concentration_metrics(diversified_stocks)
            
            return {
                'diversified_stocks': diversified_stocks,
                'diversification_metrics': {
                    'original_count': original_count,
                    'final_count': len(diversified_stocks),
                    'exclusion_rate': (original_count - len(diversified_stocks)) / original_count if original_count > 0 else 0,
                    'concentration_metrics': concentration_metrics
                },
                'diversification_applied': True
            }
            
        except Exception as e:
            logging.error(f"종합 다양화 실패: {e}")
            return {
                'diversified_stocks': ranked_stocks,
                'diversification_metrics': {
                    'original_count': len(ranked_stocks),
                    'final_count': len(ranked_stocks),
                    'exclusion_rate': 0,
                    'concentration_metrics': {'herfindahl_index': 0, 'top_10_concentration': 0}
                },
                'diversification_applied': False,
                'error': str(e)
            }
    
    def _adjust_for_existing_portfolio(self, new_stocks: List[Dict[str, Any]], 
                                     existing_portfolio: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """기존 포트폴리오 고려 조정"""
        try:
            # 기존 포트폴리오의 섹터 분포 계산
            existing_sectors = {}
            for stock in existing_portfolio:
                sector = stock.get('sector_analysis', {}).get('grade', 'Unknown')
                existing_sectors[sector] = existing_sectors.get(sector, 0) + 1
            
            # 기존 포트폴리오에 없는 섹터 우선 선택
            adjusted_stocks = []
            existing_symbols = {stock.get('symbol') for stock in existing_portfolio}
            
            for stock in new_stocks:
                symbol = stock.get('symbol')
                sector = stock.get('sector_analysis', {}).get('grade', 'Unknown')
                
                # 중복 종목 제외
                if symbol in existing_symbols:
                    continue
                
                # 기존 포트폴리오에 많이 있는 섹터는 제한
                if existing_sectors.get(sector, 0) >= 3:  # 3개 이상 있으면 제한
                    continue
                
                adjusted_stocks.append(stock)
            
            return adjusted_stocks
            
        except Exception as e:
            logging.warning(f"기존 포트폴리오 고려 조정 실패: {e}")
            return new_stocks













