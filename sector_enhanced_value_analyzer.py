"""
섹터 정보를 적극적으로 활용한 고도화된 가치주 분석 시스템
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

class SectorEnhancedValueAnalyzer:
    """섹터 정보를 적극 활용한 가치주 분석기"""
    
    def __init__(self, value_stock_finder, sector_index_provider):
        """
        섹터 강화 가치주 분석기 초기화
        
        Args:
            value_stock_finder: 기존 ValueStockFinder 인스턴스
            sector_index_provider: SectorIndexProvider 인스턴스
        """
        self.finder = value_stock_finder
        self.sector_provider = sector_index_provider
        
        # 섹터별 특성 데이터베이스
        self.sector_characteristics = {
            "금융업": {
                "typical_per_range": (8, 15),
                "typical_pbr_range": (0.8, 1.5),
                "typical_roe_range": (8, 15),
                "volatility_factor": 0.8,  # 낮은 변동성
                "growth_expectation": 0.05,  # 낮은 성장 기대
                "dividend_importance": 0.9,  # 배당 중요도 높음
                "cyclical_sensitivity": 0.7,  # 경기 민감도 중간
                "value_weight": 0.8,  # 가치주 비중 높음
                "growth_weight": 0.2
            },
            "기술업": {
                "typical_per_range": (15, 40),
                "typical_pbr_range": (2.0, 6.0),
                "typical_roe_range": (12, 25),
                "volatility_factor": 1.5,  # 높은 변동성
                "growth_expectation": 0.15,  # 높은 성장 기대
                "dividend_importance": 0.2,  # 배당 중요도 낮음
                "cyclical_sensitivity": 0.9,  # 경기 민감도 높음
                "value_weight": 0.3,
                "growth_weight": 0.7
            },
            "제조업": {
                "typical_per_range": (10, 20),
                "typical_pbr_range": (1.0, 2.5),
                "typical_roe_range": (8, 18),
                "volatility_factor": 1.0,
                "growth_expectation": 0.08,
                "dividend_importance": 0.6,
                "cyclical_sensitivity": 0.8,
                "value_weight": 0.6,
                "growth_weight": 0.4
            },
            "바이오/제약": {
                "typical_per_range": (20, 60),
                "typical_pbr_range": (3.0, 8.0),
                "typical_roe_range": (5, 20),
                "volatility_factor": 1.8,
                "growth_expectation": 0.12,
                "dividend_importance": 0.1,
                "cyclical_sensitivity": 0.4,
                "value_weight": 0.2,
                "growth_weight": 0.8
            },
            "소비재": {
                "typical_per_range": (12, 25),
                "typical_pbr_range": (1.5, 3.0),
                "typical_roe_range": (10, 20),
                "volatility_factor": 0.9,
                "growth_expectation": 0.07,
                "dividend_importance": 0.7,
                "cyclical_sensitivity": 0.6,
                "value_weight": 0.5,
                "growth_weight": 0.5
            },
            "에너지/화학": {
                "typical_per_range": (8, 18),
                "typical_pbr_range": (0.8, 2.0),
                "typical_roe_range": (6, 16),
                "volatility_factor": 1.2,
                "growth_expectation": 0.06,
                "dividend_importance": 0.8,
                "cyclical_sensitivity": 0.9,
                "value_weight": 0.7,
                "growth_weight": 0.3
            }
        }
    
    def analyze_sector_rotation_opportunities(self) -> Dict[str, Any]:
        """섹터 로테이션 기회 분석"""
        try:
            # 실시간 섹터 지수 데이터 수집
            sector_indices = self.finder.get_sector_indices()
            
            if not sector_indices:
                return {"error": "섹터 지수 데이터를 가져올 수 없습니다"}
            
            rotation_analysis = {
                "timestamp": datetime.now().isoformat(),
                "sector_performance": {},
                "rotation_signals": {},
                "recommendations": []
            }
            
            # 섹터별 성과 분석
            for market_code, index_data in sector_indices.items():
                market_name = index_data.get('market_name', 'Unknown')
                change_rate = index_data.get('change_rate', 0)
                volume_ratio = index_data.get('volume', 0) / max(1, index_data.get('prev_volume', 1))
                
                # 섹터별 특성 고려한 점수 계산
                sector_char = self.sector_characteristics.get(market_name, {})
                volatility_factor = sector_char.get('volatility_factor', 1.0)
                
                # 정규화된 성과 점수 (변동성 조정)
                normalized_performance = change_rate / volatility_factor
                
                rotation_analysis["sector_performance"][market_name] = {
                    "change_rate": change_rate,
                    "normalized_performance": normalized_performance,
                    "volume_ratio": volume_ratio,
                    "sentiment_score": index_data.get('sentiment_score', 50),
                    "volatility_factor": volatility_factor
                }
            
            # 로테이션 시그널 생성
            performances = list(rotation_analysis["sector_performance"].values())
            if performances:
                avg_performance = np.mean([p["normalized_performance"] for p in performances])
                
                for sector_name, perf_data in rotation_analysis["sector_performance"].items():
                    relative_strength = perf_data["normalized_performance"] - avg_performance
                    
                    if relative_strength > 2.0:
                        signal = "STRONG_BUY"
                        reason = "섹터 강세 지속"
                    elif relative_strength > 0.5:
                        signal = "BUY"
                        reason = "섹터 상대 강세"
                    elif relative_strength < -2.0:
                        signal = "AVOID"
                        reason = "섹터 약세 지속"
                    elif relative_strength < -0.5:
                        signal = "HOLD"
                        reason = "섹터 상대 약세"
                    else:
                        signal = "NEUTRAL"
                        reason = "섹터 중립"
                    
                    rotation_analysis["rotation_signals"][sector_name] = {
                        "signal": signal,
                        "reason": reason,
                        "relative_strength": relative_strength,
                        "confidence": min(100, abs(relative_strength) * 20)
                    }
            
            # 투자 추천 생성
            sorted_sectors = sorted(
                rotation_analysis["sector_performance"].items(),
                key=lambda x: x[1]["normalized_performance"],
                reverse=True
            )
            
            for i, (sector_name, perf_data) in enumerate(sorted_sectors[:3]):
                rotation_analysis["recommendations"].append({
                    "rank": i + 1,
                    "sector": sector_name,
                    "action": "OVERWEIGHT" if i == 0 else "NEUTRAL",
                    "reason": f"섹터 성과 {i+1}위",
                    "expected_return": perf_data["normalized_performance"]
                })
            
            return rotation_analysis
            
        except Exception as e:
            logger.error(f"섹터 로테이션 분석 중 오류: {e}")
            return {"error": str(e)}
    
    def find_sector_relative_value_stocks(self, target_sectors: List[str] = None) -> Dict[str, Any]:
        """섹터 상대 가치주 발굴"""
        try:
            if not target_sectors:
                target_sectors = ["금융업", "제조업", "소비재", "에너지/화학"]
            
            value_opportunities = {
                "timestamp": datetime.now().isoformat(),
                "sector_analysis": {},
                "top_opportunities": []
            }
            
            for sector_name in target_sectors:
                sector_char = self.sector_characteristics.get(sector_name, {})
                
                # 섹터별 가치주 기준 설정
                value_criteria = {
                    "per_max": sector_char.get("typical_per_range", (10, 20))[0] * 0.8,  # 20% 할인
                    "pbr_max": sector_char.get("typical_pbr_range", (1.0, 2.0))[0] * 0.9,
                    "roe_min": sector_char.get("typical_roe_range", (8, 15))[0],
                    "dividend_min": 2.0 if sector_char.get("dividend_importance", 0.5) > 0.6 else 1.0
                }
                
                # 섹터 내 가치주 스크리닝 (시뮬레이션)
                sector_stocks = self._simulate_sector_screening(sector_name, value_criteria)
                
                value_opportunities["sector_analysis"][sector_name] = {
                    "criteria": value_criteria,
                    "sector_characteristics": sector_char,
                    "potential_stocks": len(sector_stocks),
                    "avg_value_score": np.mean([s["value_score"] for s in sector_stocks]) if sector_stocks else 0
                }
                
                # 상위 기회 추가
                for stock in sector_stocks[:3]:  # 상위 3개만
                    stock["sector"] = sector_name
                    value_opportunities["top_opportunities"].append(stock)
            
            # 전체 상위 기회 정렬
            value_opportunities["top_opportunities"].sort(
                key=lambda x: x["value_score"], 
                reverse=True
            )
            
            return value_opportunities
            
        except Exception as e:
            logger.error(f"섹터 상대 가치주 발굴 중 오류: {e}")
            return {"error": str(e)}
    
    def _simulate_sector_screening(self, sector_name: str, criteria: Dict[str, float]) -> List[Dict[str, Any]]:
        """섹터 내 가치주 스크리닝 (시뮬레이션)"""
        # 실제로는 KIS API에서 해당 섹터 종목들을 가져와서 분석
        # 여기서는 시뮬레이션 데이터 생성
        
        import random
        random.seed(hash(sector_name) % 2**32)
        
        stocks = []
        for i in range(random.randint(5, 15)):
            # 섹터 특성에 맞는 데이터 생성
            sector_char = self.sector_characteristics.get(sector_name, {})
            per_range = sector_char.get("typical_per_range", (10, 20))
            pbr_range = sector_char.get("typical_pbr_range", (1.0, 2.0))
            roe_range = sector_char.get("typical_roe_range", (8, 15))
            
            per = random.uniform(per_range[0] * 0.5, per_range[1] * 1.2)
            pbr = random.uniform(pbr_range[0] * 0.6, pbr_range[1] * 1.1)
            roe = random.uniform(roe_range[0] * 0.8, roe_range[1] * 1.3)
            
            # 가치 점수 계산
            value_score = self._calculate_sector_adjusted_value_score(
                per, pbr, roe, sector_char, criteria
            )
            
            if value_score > 60:  # 가치주 기준
                stocks.append({
                    "symbol": f"{sector_name[:2]}{i:04d}",
                    "name": f"{sector_name} 가치주 {i+1}",
                    "per": round(per, 2),
                    "pbr": round(pbr, 2),
                    "roe": round(roe, 2),
                    "value_score": round(value_score, 1),
                    "sector_adjustment": 1.0,
                    "recommendation": "BUY" if value_score > 75 else "HOLD"
                })
        
        return sorted(stocks, key=lambda x: x["value_score"], reverse=True)
    
    def _calculate_sector_adjusted_value_score(self, per: float, pbr: float, roe: float, 
                                             sector_char: Dict[str, Any], criteria: Dict[str, float]) -> float:
        """섹터 특성 고려한 가치 점수 계산"""
        try:
            score = 0
            
            # PER 점수 (낮을수록 좋음)
            if per > 0 and per <= criteria["per_max"]:
                per_score = max(0, 30 - (per / criteria["per_max"]) * 30)
                score += per_score
            
            # PBR 점수 (낮을수록 좋음)
            if pbr > 0 and pbr <= criteria["pbr_max"]:
                pbr_score = max(0, 25 - (pbr / criteria["pbr_max"]) * 25)
                score += pbr_score
            
            # ROE 점수 (높을수록 좋음)
            if roe >= criteria["roe_min"]:
                roe_score = min(30, (roe / criteria["roe_min"]) * 20)
                score += roe_score
            
            # 섹터 특성 조정
            value_weight = sector_char.get("value_weight", 0.5)
            growth_weight = sector_char.get("growth_weight", 0.5)
            
            # 가치주 보정 (가치 중심 섹터일수록 가점)
            value_bonus = (value_weight - 0.5) * 10
            
            # 성장주 보정 (성장 중심 섹터에서는 ROE 가중치 증가)
            growth_bonus = growth_weight * 5
            
            final_score = score + value_bonus + growth_bonus
            
            return max(0, min(100, final_score))
            
        except Exception as e:
            logger.error(f"섹터 조정 가치 점수 계산 중 오류: {e}")
            return 50.0
    
    def analyze_sector_cycle_position(self, sector_name: str) -> Dict[str, Any]:
        """섹터 사이클 위치 분석"""
        try:
            # 섹터 특성 가져오기
            sector_char = self.sector_characteristics.get(sector_name, {})
            
            # 실시간 섹터 데이터
            sector_indices = self.finder.get_sector_indices()
            market_sentiment = self.finder.get_market_sentiment("0001")
            
            # 사이클 위치 추정 (시뮬레이션)
            cycle_position = {
                "sector": sector_name,
                "current_phase": "UNKNOWN",
                "cycle_percentage": 50,  # 0-100%
                "recommended_action": "HOLD",
                "time_horizon": "MEDIUM",
                "risk_level": "MEDIUM",
                "factors": {
                    "volatility_factor": sector_char.get("volatility_factor", 1.0),
                    "cyclical_sensitivity": sector_char.get("cyclical_sensitivity", 0.5),
                    "growth_expectation": sector_char.get("growth_expectation", 0.1)
                }
            }
            
            # 시장 심리 기반 사이클 추정
            if market_sentiment:
                sentiment_score = market_sentiment.get("sentiment_score", 50)
                
                if sentiment_score > 70:
                    cycle_position["current_phase"] = "EXPANSION"
                    cycle_position["cycle_percentage"] = 75
                    cycle_position["recommended_action"] = "OVERWEIGHT"
                elif sentiment_score > 60:
                    cycle_position["current_phase"] = "RECOVERY"
                    cycle_position["cycle_percentage"] = 60
                    cycle_position["recommended_action"] = "BUY"
                elif sentiment_score > 40:
                    cycle_position["current_phase"] = "MATURE"
                    cycle_position["cycle_percentage"] = 50
                    cycle_position["recommended_action"] = "NEUTRAL"
                elif sentiment_score > 30:
                    cycle_position["current_phase"] = "DECLINE"
                    cycle_position["cycle_percentage"] = 25
                    cycle_position["recommended_action"] = "UNDERWEIGHT"
                else:
                    cycle_position["current_phase"] = "RECESSION"
                    cycle_position["cycle_percentage"] = 10
                    cycle_position["recommended_action"] = "AVOID"
            
            # 섹터별 특성 조정
            cyclical_sensitivity = sector_char.get("cyclical_sensitivity", 0.5)
            if cyclical_sensitivity > 0.7:
                cycle_position["risk_level"] = "HIGH"
                cycle_position["time_horizon"] = "SHORT"
            elif cyclical_sensitivity < 0.3:
                cycle_position["risk_level"] = "LOW"
                cycle_position["time_horizon"] = "LONG"
            
            return cycle_position
            
        except Exception as e:
            logger.error(f"섹터 사이클 분석 중 오류: {e}")
            return {"error": str(e)}
    
    def generate_sector_enhanced_portfolio(self, risk_tolerance: str = "MEDIUM", 
                                         investment_horizon: str = "MEDIUM") -> Dict[str, Any]:
        """섹터 강화 포트폴리오 생성"""
        try:
            # 리스크 허용도별 설정
            risk_configs = {
                "LOW": {"max_sector_weight": 0.3, "min_diversification": 5},
                "MEDIUM": {"max_sector_weight": 0.4, "min_diversification": 4},
                "HIGH": {"max_sector_weight": 0.5, "min_diversification": 3}
            }
            
            config = risk_configs.get(risk_tolerance, risk_configs["MEDIUM"])
            
            # 섹터 로테이션 분석
            rotation_analysis = self.analyze_sector_rotation_opportunities()
            
            # 섹터 상대 가치주 분석
            value_analysis = self.find_sector_relative_value_stocks()
            
            # 포트폴리오 구성
            portfolio = {
                "timestamp": datetime.now().isoformat(),
                "risk_tolerance": risk_tolerance,
                "investment_horizon": investment_horizon,
                "sector_allocation": {},
                "recommended_stocks": [],
                "rebalancing_signals": [],
                "risk_metrics": {}
            }
            
            # 섹터 배분 결정
            if "sector_performance" in rotation_analysis:
                sorted_sectors = sorted(
                    rotation_analysis["sector_performance"].items(),
                    key=lambda x: x[1]["normalized_performance"],
                    reverse=True
                )
                
                total_weight = 0
                for i, (sector_name, perf_data) in enumerate(sorted_sectors):
                    if i >= config["min_diversification"]:
                        break
                    
                    # 가중치 계산 (성과 기반)
                    base_weight = 1.0 / config["min_diversification"]
                    performance_multiplier = min(2.0, 1.0 + (perf_data["normalized_performance"] / 10))
                    sector_weight = min(config["max_sector_weight"], base_weight * performance_multiplier)
                    
                    portfolio["sector_allocation"][sector_name] = {
                        "target_weight": round(sector_weight, 3),
                        "performance_score": perf_data["normalized_performance"],
                        "volatility_factor": perf_data.get("volatility_factor", 1.0),
                        "recommendation": rotation_analysis["rotation_signals"].get(sector_name, {}).get("signal", "NEUTRAL")
                    }
                    
                    total_weight += sector_weight
            
            # 포트폴리오 가중치 정규화
            if total_weight > 0:
                for sector_name in portfolio["sector_allocation"]:
                    portfolio["sector_allocation"][sector_name]["target_weight"] /= total_weight
            
            # 추천 종목 추가
            if "top_opportunities" in value_analysis:
                for stock in value_analysis["top_opportunities"][:10]:  # 상위 10개
                    portfolio["recommended_stocks"].append({
                        "symbol": stock["symbol"],
                        "name": stock["name"],
                        "sector": stock["sector"],
                        "value_score": stock["value_score"],
                        "recommendation": stock["recommendation"],
                        "expected_return": stock.get("expected_return", 0)
                    })
            
            # 리밸런싱 시그널
            portfolio["rebalancing_signals"] = [
                "주간 성과 리뷰 권장",
                "월간 섹터 로테이션 체크",
                "분기별 포트폴리오 재조정"
            ]
            
            # 리스크 메트릭
            portfolio["risk_metrics"] = {
                "diversification_score": len(portfolio["sector_allocation"]),
                "concentration_risk": max([alloc["target_weight"] for alloc in portfolio["sector_allocation"].values()]) if portfolio["sector_allocation"] else 0,
                "volatility_estimate": np.mean([alloc.get("volatility_factor", 1.0) for alloc in portfolio["sector_allocation"].values()]) if portfolio["sector_allocation"] else 1.0
            }
            
            return portfolio
            
        except Exception as e:
            logger.error(f"섹터 강화 포트폴리오 생성 중 오류: {e}")
            return {"error": str(e)}

# 테스트 함수
def test_sector_enhanced_analyzer():
    """섹터 강화 분석기 테스트"""
    try:
        from value_stock_finder import ValueStockFinder
        from sector_index_provider import SectorIndexProvider
        from kis_token_manager import get_token_manager
        
        # 초기화
        finder = ValueStockFinder()
        # finder의 OAuth 매니저 활용
        sector_provider = SectorIndexProvider(finder.oauth_manager)
        
        # 섹터 강화 분석기 초기화
        analyzer = SectorEnhancedValueAnalyzer(finder, sector_provider)
        
        print("=== 섹터 강화 가치주 분석기 테스트 ===")
        
        # 1. 섹터 로테이션 기회 분석
        print("\n1. 섹터 로테이션 기회 분석")
        rotation = analyzer.analyze_sector_rotation_opportunities()
        if "sector_performance" in rotation:
            for sector, data in list(rotation["sector_performance"].items())[:3]:
                print(f"  {sector}: {data['change_rate']:+.2f}% (정규화: {data['normalized_performance']:+.2f})")
        
        # 2. 섹터 상대 가치주 발굴
        print("\n2. 섹터 상대 가치주 발굴")
        value_stocks = analyzer.find_sector_relative_value_stocks()
        if "top_opportunities" in value_stocks:
            for stock in value_stocks["top_opportunities"][:3]:
                print(f"  {stock['name']}: 점수 {stock['value_score']:.1f} ({stock['recommendation']})")
        
        # 3. 섹터 사이클 분석
        print("\n3. 섹터 사이클 분석")
        cycle = analyzer.analyze_sector_cycle_position("금융업")
        if "current_phase" in cycle:
            print(f"  금융업: {cycle['current_phase']} (추천: {cycle['recommended_action']})")
        
        # 4. 포트폴리오 생성
        print("\n4. 섹터 강화 포트폴리오")
        portfolio = analyzer.generate_sector_enhanced_portfolio("MEDIUM", "MEDIUM")
        if "sector_allocation" in portfolio:
            for sector, allocation in list(portfolio["sector_allocation"].items())[:3]:
                print(f"  {sector}: {allocation['target_weight']:.1%} ({allocation['recommendation']})")
        
        print("\n=== 테스트 완료 ===")
        
    except Exception as e:
        print(f"FAILED: 테스트 실행 중 오류: {e}")

if __name__ == "__main__":
    test_sector_enhanced_analyzer()
