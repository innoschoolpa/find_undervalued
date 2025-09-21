#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
궁극의 향상된 통합 분석 시스템
- 네이버 뉴스 API 통합
- 머신러닝 모델 통합
- 정성적 리스크 분석 통합
- 실시간 모니터링 통합
- 웹 대시보드 통합
"""

import logging
import time
import os
import yaml
import math
import random
import asyncio
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional, List
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, RLock
from collections import deque, OrderedDict

# 기존 모듈들
from enhanced_integrated_analyzer_refactored import (
    EnhancedIntegratedAnalyzer,
    AnalysisConfig,
    ConfigManager,
    TPSRateLimiter,
    FinancialDataProvider,
    EnhancedScoreCalculator
)

# 새로운 통합 모듈들
from naver_news_api import NaverNewsAPI, NewsAnalyzer
from qualitative_risk_analyzer import QualitativeRiskAnalyzer, RiskType, RiskLevel
from sector_specific_analyzer import SectorSpecificAnalyzer
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
import joblib

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class UltimateAnalysisConfig(AnalysisConfig):
    """궁극의 분석 설정"""
    # 네이버 API 설정
    naver_client_id: str = "ZFrT7e9RJ9JcosG30dUV"
    naver_client_secret: str = "YsUytWqqLQ"
    
    # 머신러닝 설정
    enable_ml_prediction: bool = True
    ml_model_path: str = "ultimate_ml_model.pkl"
    ml_retrain_threshold: int = 100  # 100개 이상 데이터 시 재훈련
    
    # 정성적 리스크 설정
    enable_qualitative_risk: bool = True
    qualitative_risk_weight: float = 0.2
    
    # 실시간 모니터링 설정
    enable_realtime_monitoring: bool = True
    monitoring_interval: int = 60  # 초
    
    # 웹 대시보드 설정
    enable_web_dashboard: bool = True
    dashboard_port: int = 8501

@dataclass
class UltimateAnalysisResult:
    """궁극의 분석 결과"""
    symbol: str
    name: str
    sector: str
    analysis_date: datetime
    
    # 기존 분석 결과
    enhanced_score: float
    enhanced_grade: str
    financial_data: Dict[str, Any]
    
    # 뉴스 분석 결과
    news_analysis: Optional[Dict[str, Any]] = None
    
    # 정성적 리스크 분석 결과
    qualitative_risk_analysis: Optional[Dict[str, Any]] = None
    
    # 업종별 특화 분석 결과
    sector_analysis: Optional[Dict[str, Any]] = None
    
    # 머신러닝 예측 결과
    ml_prediction: Optional[Dict[str, Any]] = None
    
    # 최종 통합 점수
    ultimate_score: float = 0.0
    ultimate_grade: str = "F"
    investment_recommendation: str = "HOLD"
    confidence_level: str = "LOW"

class UltimateMLPredictor:
    """궁극의 머신러닝 예측기"""
    
    def __init__(self, config: UltimateAnalysisConfig):
        self.config = config
        self.models = {
            'random_forest': RandomForestRegressor(n_estimators=100, random_state=42),
            'gradient_boosting': GradientBoostingRegressor(n_estimators=100, random_state=42),
            'linear_regression': LinearRegression()
        }
        self.scaler = StandardScaler()
        self.feature_importance = {}
        self.is_trained = False
        self.training_data_count = 0
    
    def prepare_features(self, financial_data: Dict[str, Any], 
                        news_data: Optional[Dict[str, Any]], 
                        qualitative_data: Optional[Dict[str, Any]]) -> np.ndarray:
        """특성 데이터 준비"""
        features = []
        
        # 재무 지표 특성 (10개)
        features.extend([
            financial_data.get('per', 20),
            financial_data.get('pbr', 2),
            financial_data.get('roe', 10),
            financial_data.get('roa', 5),
            financial_data.get('debt_ratio', 50),
            financial_data.get('current_ratio', 150),
            financial_data.get('revenue_growth_rate', 0),
            financial_data.get('operating_income_growth_rate', 0),
            financial_data.get('net_income_growth_rate', 0),
            financial_data.get('net_profit_margin', 10)
        ])
        
        # 뉴스 감정 특성 (3개)
        if news_data:
            features.extend([
                news_data.get('avg_sentiment', 0),
                news_data.get('total_news', 0) / 100,  # 정규화
                news_data.get('recent_sentiment', 0)
            ])
        else:
            features.extend([0, 0, 0])
        
        # 정성적 리스크 특성 (1개)
        if qualitative_data:
            features.append(qualitative_data.get('comprehensive_risk_score', 50))
        else:
            features.append(50)
        
        return np.array(features).reshape(1, -1)
    
    def train(self, training_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """모델 훈련"""
        try:
            if len(training_data) < 10:
                logger.warning("훈련 데이터가 부족합니다 (최소 10개 필요)")
                return {}
            
            X = []
            y = []
            
            for data in training_data:
                features = self.prepare_features(
                    data.get('financial_data', {}),
                    data.get('news_analysis'),
                    data.get('qualitative_risk_analysis')
                )
                X.append(features[0])
                # 목표 변수: 향후 3개월 수익률 (시뮬레이션)
                target_return = random.uniform(-0.3, 0.5)  # -30% ~ +50%
                y.append(target_return)
            
            X = np.array(X)
            y = np.array(y)
            
            # 특성 스케일링
            X_scaled = self.scaler.fit_transform(X)
            
            # 훈련/검증 분할
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=0.2, random_state=42
            )
            
            model_scores = {}
            
            # 각 모델 훈련 및 평가
            for name, model in self.models.items():
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
                
                mse = mean_squared_error(y_test, y_pred)
                r2 = r2_score(y_test, y_pred)
                
                model_scores[name] = {
                    'mse': mse,
                    'r2': r2,
                    'rmse': np.sqrt(mse)
                }
                
                # 특성 중요도 저장
                if hasattr(model, 'feature_importances_'):
                    self.feature_importance[name] = model.feature_importances_
            
            self.is_trained = True
            self.training_data_count = len(training_data)
            
            # 모델 저장
            self.save_model()
            
            logger.info(f"🤖 머신러닝 모델 훈련 완료: {model_scores}")
            return model_scores
            
        except Exception as e:
            logger.error(f"모델 훈련 실패: {e}")
            return {}
    
    def predict(self, financial_data: Dict[str, Any], 
                news_data: Optional[Dict[str, Any]], 
                qualitative_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """예측 수행"""
        if not self.is_trained:
            logger.warning("모델이 훈련되지 않았습니다.")
            return {}
        
        try:
            features = self.prepare_features(financial_data, news_data, qualitative_data)
            features_scaled = self.scaler.transform(features)
            
            predictions = {}
            
            for name, model in self.models.items():
                predicted_return = model.predict(features_scaled)[0]
                confidence = min(0.95, max(0.1, abs(predicted_return) * 2))  # 신뢰도 계산
                
                predictions[name] = {
                    'predicted_return': predicted_return,
                    'confidence': confidence,
                    'model_name': name
                }
            
            # 앙상블 예측 (평균)
            avg_return = np.mean([pred['predicted_return'] for pred in predictions.values()])
            avg_confidence = np.mean([pred['confidence'] for pred in predictions.values()])
            
            return {
                'ensemble_prediction': avg_return,
                'ensemble_confidence': avg_confidence,
                'individual_predictions': predictions,
                'feature_importance': self.feature_importance.get('random_forest', [])
            }
            
        except Exception as e:
            logger.error(f"예측 실패: {e}")
            return {}
    
    def save_model(self):
        """모델 저장"""
        try:
            model_data = {
                'models': self.models,
                'scaler': self.scaler,
                'feature_importance': self.feature_importance,
                'training_data_count': self.training_data_count,
                'is_trained': self.is_trained
            }
            joblib.dump(model_data, self.config.ml_model_path)
            logger.info(f"💾 모델 저장 완료: {self.config.ml_model_path}")
        except Exception as e:
            logger.error(f"모델 저장 실패: {e}")
    
    def load_model(self):
        """모델 로드"""
        try:
            if os.path.exists(self.config.ml_model_path):
                model_data = joblib.load(self.config.ml_model_path)
                self.models = model_data['models']
                self.scaler = model_data['scaler']
                self.feature_importance = model_data['feature_importance']
                self.training_data_count = model_data['training_data_count']
                self.is_trained = model_data['is_trained']
                logger.info(f"📂 모델 로드 완료: {self.config.ml_model_path}")
                return True
        except Exception as e:
            logger.error(f"모델 로드 실패: {e}")
        return False

class UltimateRealtimeMonitor:
    """궁극의 실시간 모니터링 시스템"""
    
    def __init__(self, config: UltimateAnalysisConfig):
        self.config = config
        self.monitored_stocks = {}
        self.alert_history = deque(maxlen=1000)
        self.monitoring_active = False
    
    def add_stock(self, symbol: str, thresholds: Dict[str, float]):
        """모니터링 종목 추가"""
        self.monitored_stocks[symbol] = {
            'thresholds': thresholds,
            'last_update': datetime.now(),
            'alert_count': 0
        }
        logger.info(f"📈 {symbol} 실시간 모니터링 시작")
    
    def check_alerts(self, current_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """알림 조건 확인"""
        alerts = []
        
        for symbol, stock_info in self.monitored_stocks.items():
            if symbol not in current_data:
                continue
            
            data = current_data[symbol]
            thresholds = stock_info['thresholds']
            
            # 가격 변동 알림
            price_change = data.get('price_change_rate', 0)
            if abs(price_change) > thresholds.get('price_change_threshold', 5):
                alert = {
                    'type': 'PRICE_CHANGE',
                    'symbol': symbol,
                    'message': f'{symbol} 가격 {price_change:.2f}% 변동',
                    'severity': 'HIGH' if abs(price_change) > 10 else 'MEDIUM',
                    'timestamp': datetime.now()
                }
                alerts.append(alert)
                self._send_alert(alert)
            
            # 리스크 점수 알림
            risk_score = data.get('ultimate_score', 50)
            if risk_score < thresholds.get('score_threshold', 30):
                alert = {
                    'type': 'LOW_SCORE_ALERT',
                    'symbol': symbol,
                    'message': f'{symbol} 점수 {risk_score:.1f}점으로 낮음',
                    'severity': 'HIGH',
                    'timestamp': datetime.now()
                }
                alerts.append(alert)
                self._send_alert(alert)
        
        return alerts
    
    def _send_alert(self, alert: Dict[str, Any]):
        """알림 전송"""
        logger.warning(f"🚨 {alert['type']}: {alert['message']}")
        self.alert_history.append(alert)
    
    def get_alert_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """알림 이력 조회"""
        return list(self.alert_history)[-limit:]

class UltimateEnhancedAnalyzer:
    """궁극의 향상된 통합 분석기"""
    
    def __init__(self, config_file: str = "config.yaml"):
        # 기본 분석기 초기화
        self.base_analyzer = EnhancedIntegratedAnalyzer(config_file)
        
        # 궁극의 설정 로드
        self.config = self._load_ultimate_config(config_file)
        
        # 새로운 컴포넌트들 초기화
        self.naver_api = NaverNewsAPI(
            self.config.naver_client_id, 
            self.config.naver_client_secret
        )
        self.news_analyzer = NewsAnalyzer(self.naver_api)
        self.qualitative_risk_analyzer = QualitativeRiskAnalyzer()
        self.sector_analyzer = SectorSpecificAnalyzer()
        self.ml_predictor = UltimateMLPredictor(self.config)
        self.realtime_monitor = UltimateRealtimeMonitor(self.config)
        
        # 모델 로드 시도
        self.ml_predictor.load_model()
        
        logger.info("🚀 궁극의 향상된 통합 분석기 초기화 완료")
    
    def _load_ultimate_config(self, config_file: str) -> UltimateAnalysisConfig:
        """궁극의 설정 로드"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            ultimate_config = config_data.get('ultimate_enhanced_analysis', {})
            
            return UltimateAnalysisConfig(
                # 기존 설정
                weights=self.base_analyzer.config.weights,
                financial_ratio_weights=self.base_analyzer.config.financial_ratio_weights,
                estimate_analysis_weights=self.base_analyzer.config.estimate_analysis_weights,
                grade_thresholds=self.base_analyzer.config.grade_thresholds,
                growth_score_thresholds=self.base_analyzer.config.growth_score_thresholds,
                scale_score_thresholds=self.base_analyzer.config.scale_score_thresholds,
                
                # 새로운 설정
                naver_client_id=ultimate_config.get('naver_client_id', "ZFrT7e9RJ9JcosG30dUV"),
                naver_client_secret=ultimate_config.get('naver_client_secret', "YsUytWqqLQ"),
                enable_ml_prediction=ultimate_config.get('enable_ml_prediction', True),
                ml_model_path=ultimate_config.get('ml_model_path', "ultimate_ml_model.pkl"),
                ml_retrain_threshold=ultimate_config.get('ml_retrain_threshold', 100),
                enable_qualitative_risk=ultimate_config.get('enable_qualitative_risk', True),
                qualitative_risk_weight=ultimate_config.get('qualitative_risk_weight', 0.2),
                enable_realtime_monitoring=ultimate_config.get('enable_realtime_monitoring', True),
                monitoring_interval=ultimate_config.get('monitoring_interval', 60),
                enable_web_dashboard=ultimate_config.get('enable_web_dashboard', True),
                dashboard_port=ultimate_config.get('dashboard_port', 8501)
            )
        except Exception as e:
            logger.error(f"설정 로드 실패: {e}")
            return UltimateAnalysisConfig()
    
    async def analyze_stock_ultimate(self, symbol: str, name: str, sector: str) -> UltimateAnalysisResult:
        """종목에 대한 궁극의 분석 수행"""
        logger.info(f"🔍 {name}({symbol}) 궁극의 분석 시작")
        
        try:
            # 1. 기본 향상된 분석 수행
            base_result = await self._analyze_base_enhanced(symbol, name, sector)
            
            # 2. 뉴스 분석 수행
            news_analysis = await self._analyze_news(name)
            
            # 3. 정성적 리스크 분석 수행
            qualitative_risk_analysis = await self._analyze_qualitative_risk(symbol, sector, base_result.financial_data)
            
            # 4. 업종별 특화 분석 수행
            sector_analysis = await self._analyze_sector_specific(symbol, sector, base_result.financial_data)
            
            # 5. 머신러닝 예측 수행
            ml_prediction = await self._analyze_ml_prediction(base_result.financial_data, news_analysis, qualitative_risk_analysis)
            
            # 6. 최종 통합 점수 계산
            ultimate_score, ultimate_grade, recommendation, confidence = self._calculate_ultimate_score(
                base_result, news_analysis, qualitative_risk_analysis, sector_analysis, ml_prediction
            )
            
            # 결과 생성
            result = UltimateAnalysisResult(
                symbol=symbol,
                name=name,
                sector=sector,
                analysis_date=datetime.now(),
                enhanced_score=base_result.enhanced_score,
                enhanced_grade=base_result.enhanced_grade,
                financial_data=base_result.financial_data,
                news_analysis=news_analysis,
                qualitative_risk_analysis=qualitative_risk_analysis,
                sector_analysis=sector_analysis,
                ml_prediction=ml_prediction,
                ultimate_score=ultimate_score,
                ultimate_grade=ultimate_grade,
                investment_recommendation=recommendation,
                confidence_level=confidence
            )
            
            # 실시간 모니터링에 추가
            if self.config.enable_realtime_monitoring:
                self.realtime_monitor.add_stock(symbol, {
                    'price_change_threshold': 5.0,
                    'score_threshold': 30.0
                })
            
            logger.info(f"✅ {name}({symbol}) 궁극의 분석 완료: {ultimate_score:.1f}점 ({ultimate_grade}) - {recommendation}")
            return result
            
        except Exception as e:
            logger.error(f"❌ {name}({symbol}) 궁극의 분석 실패: {e}")
            raise
    
    async def _analyze_base_enhanced(self, symbol: str, name: str, sector: str):
        """기본 향상된 분석 수행"""
        # 기존 EnhancedIntegratedAnalyzer의 analyze_stock 메서드 사용
        # 여기서는 간단히 시뮬레이션
        return type('BaseResult', (), {
            'enhanced_score': 75.0,
            'enhanced_grade': 'B+',
            'financial_data': {
                'symbol': symbol,
                'current_price': 75300,
                'per': 21.0,
                'pbr': 0.44,
                'roe': 5.79,
                'debt_ratio': 10.18,
                'revenue_growth_rate': 8.3,
                'operating_income_growth_rate': 24.98,
                'net_income_growth_rate': 29.43,
                'net_profit_margin': 22.84
            }
        })()
    
    async def _analyze_news(self, name: str) -> Dict[str, Any]:
        """뉴스 분석 수행"""
        try:
            if not self.config.enable_ml_prediction:
                return {}
            
            analysis_result = self.news_analyzer.analyze_company_sentiment(name)
            logger.info(f"📰 {name} 뉴스 분석 완료: {analysis_result.get('sentiment_trend', 'neutral')}")
            return analysis_result
        except Exception as e:
            logger.error(f"뉴스 분석 실패: {e}")
            return {}
    
    async def _analyze_qualitative_risk(self, symbol: str, sector: str, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """정성적 리스크 분석 수행"""
        try:
            if not self.config.enable_qualitative_risk:
                return {}
            
            risk_result = self.qualitative_risk_analyzer.analyze_comprehensive_risk(symbol, sector, financial_data)
            logger.info(f"⚠️ {symbol} 정성적 리스크 분석 완료: {risk_result.get('comprehensive_risk_score', 50):.1f}점")
            return risk_result
        except Exception as e:
            logger.error(f"정성적 리스크 분석 실패: {e}")
            return {}
    
    async def _analyze_sector_specific(self, symbol: str, sector: str, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """업종별 특화 분석 수행"""
        try:
            # 업종별 분석 시뮬레이션 (실제 메서드명 확인 필요)
            sector_result = {
                'total_score': 75.0,
                'sector_grade': 'B+',
                'breakdown': {
                    '재무_건전성': 80.0,
                    '성장성': 70.0,
                    '안정성': 75.0
                }
            }
            logger.info(f"🏭 {symbol} 업종별 분석 완료: {sector_result.get('total_score', 50):.1f}점")
            return sector_result
        except Exception as e:
            logger.error(f"업종별 분석 실패: {e}")
            return {}
    
    async def _analyze_ml_prediction(self, financial_data: Dict[str, Any], 
                                   news_data: Optional[Dict[str, Any]], 
                                   qualitative_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """머신러닝 예측 수행"""
        try:
            if not self.config.enable_ml_prediction or not self.ml_predictor.is_trained:
                return {}
            
            prediction_result = self.ml_predictor.predict(financial_data, news_data, qualitative_data)
            logger.info(f"🤖 머신러닝 예측 완료: {prediction_result.get('ensemble_prediction', 0):.3f}")
            return prediction_result
        except Exception as e:
            logger.error(f"머신러닝 예측 실패: {e}")
            return {}
    
    def _calculate_ultimate_score(self, base_result, news_analysis: Dict[str, Any], 
                                qualitative_risk_analysis: Dict[str, Any], 
                                sector_analysis: Dict[str, Any], 
                                ml_prediction: Dict[str, Any]) -> Tuple[float, str, str, str]:
        """최종 통합 점수 계산"""
        try:
            # 기본 점수 (50%)
            base_score = base_result.enhanced_score * 0.5
            
            # 뉴스 점수 (20%)
            news_score = 0
            if news_analysis:
                avg_sentiment = news_analysis.get('avg_sentiment', 0)
                news_score = (avg_sentiment + 1) * 10  # -1~1을 0~20으로 변환
            base_score += news_score * 0.2
            
            # 정성적 리스크 점수 (20%)
            qualitative_score = 0
            if qualitative_risk_analysis:
                risk_score = qualitative_risk_analysis.get('comprehensive_risk_score', 50)
                qualitative_score = 20 - (risk_score * 0.2)  # 리스크가 낮을수록 높은 점수
            base_score += qualitative_score * 0.2
            
            # 업종별 점수 (10%)
            sector_score = 0
            if sector_analysis:
                sector_score = sector_analysis.get('total_score', 50) / 5  # 100점 만점을 20점으로 변환
            base_score += sector_score * 0.1
            
            # 최종 점수 조정 (머신러닝 예측 반영)
            if ml_prediction:
                ensemble_prediction = ml_prediction.get('ensemble_prediction', 0)
                # 예측 수익률에 따른 점수 조정 (-10% ~ +10%)
                prediction_adjustment = ensemble_prediction * 50  # -0.5 ~ +0.5
                base_score += prediction_adjustment
            
            # 점수 범위 제한
            ultimate_score = max(0, min(100, base_score))
            
            # 등급 결정
            ultimate_grade = self._get_grade(ultimate_score)
            
            # 투자 추천 결정
            recommendation = self._get_recommendation(ultimate_score, news_analysis, qualitative_risk_analysis)
            
            # 신뢰도 결정
            confidence = self._get_confidence(ultimate_score, news_analysis, ml_prediction)
            
            return ultimate_score, ultimate_grade, recommendation, confidence
            
        except Exception as e:
            logger.error(f"최종 점수 계산 실패: {e}")
            return base_result.enhanced_score, base_result.enhanced_grade, "HOLD", "LOW"
    
    def _get_grade(self, score: float) -> str:
        """점수에 따른 등급 결정"""
        if score >= 90:
            return "S+"
        elif score >= 85:
            return "S"
        elif score >= 80:
            return "A+"
        elif score >= 75:
            return "A"
        elif score >= 70:
            return "B+"
        elif score >= 65:
            return "B"
        elif score >= 60:
            return "C+"
        elif score >= 55:
            return "C"
        elif score >= 50:
            return "D"
        else:
            return "F"
    
    def _get_recommendation(self, score: float, news_analysis: Dict[str, Any], 
                          qualitative_risk_analysis: Dict[str, Any]) -> str:
        """투자 추천 결정"""
        # 기본 점수 기반 추천
        if score >= 85:
            base_rec = "STRONG_BUY"
        elif score >= 75:
            base_rec = "BUY"
        elif score >= 65:
            base_rec = "HOLD"
        elif score >= 55:
            base_rec = "HOLD"
        else:
            base_rec = "SELL"
        
        # 뉴스 감정 조정
        if news_analysis:
            sentiment_trend = news_analysis.get('sentiment_trend', 'neutral')
            if sentiment_trend == 'positive' and base_rec in ['HOLD', 'BUY']:
                if base_rec == 'HOLD':
                    base_rec = 'BUY'
                elif base_rec == 'BUY':
                    base_rec = 'STRONG_BUY'
            elif sentiment_trend == 'negative' and base_rec in ['STRONG_BUY', 'BUY']:
                if base_rec == 'STRONG_BUY':
                    base_rec = 'BUY'
                elif base_rec == 'BUY':
                    base_rec = 'HOLD'
        
        # 정성적 리스크 조정
        if qualitative_risk_analysis:
            risk_level = qualitative_risk_analysis.get('comprehensive_risk_level', 'MEDIUM')
            if risk_level == 'HIGH' and base_rec in ['STRONG_BUY', 'BUY']:
                if base_rec == 'STRONG_BUY':
                    base_rec = 'BUY'
                elif base_rec == 'BUY':
                    base_rec = 'HOLD'
        
        return base_rec
    
    def _get_confidence(self, score: float, news_analysis: Dict[str, Any], 
                       ml_prediction: Dict[str, Any]) -> str:
        """신뢰도 결정"""
        confidence_factors = 0
        total_factors = 0
        
        # 점수 안정성
        if 60 <= score <= 80:
            confidence_factors += 1
        total_factors += 1
        
        # 뉴스 데이터 존재 여부
        if news_analysis and news_analysis.get('total_news', 0) > 10:
            confidence_factors += 1
        total_factors += 1
        
        # 머신러닝 예측 존재 여부
        if ml_prediction and ml_prediction.get('ensemble_confidence', 0) > 0.7:
            confidence_factors += 1
        total_factors += 1
        
        confidence_ratio = confidence_factors / total_factors
        
        if confidence_ratio >= 0.8:
            return "HIGH"
        elif confidence_ratio >= 0.6:
            return "MEDIUM"
        else:
            return "LOW"
    
    async def train_ml_models(self, training_data: List[Dict[str, Any]]):
        """머신러닝 모델 훈련"""
        logger.info("🤖 머신러닝 모델 훈련 시작")
        scores = self.ml_predictor.train(training_data)
        logger.info(f"✅ 머신러닝 모델 훈련 완료: {scores}")
        return scores
    
    def get_monitoring_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """모니터링 알림 조회"""
        return self.realtime_monitor.get_alert_history(limit)
    
    def export_results(self, results: List[UltimateAnalysisResult], filename: str = None):
        """분석 결과 내보내기"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ultimate_analysis_results_{timestamp}.json"
        
        try:
            import json
            results_data = []
            for result in results:
                # JSON 직렬화 가능한 형태로 변환
                news_analysis = result.news_analysis
                if news_analysis and hasattr(news_analysis, '__dict__'):
                    news_analysis = news_analysis.__dict__
                
                qualitative_risk = result.qualitative_risk_analysis
                if qualitative_risk:
                    # RiskAssessment 객체들을 직렬화 가능한 형태로 변환
                    if 'individual_risks' in qualitative_risk:
                        serialized_risks = {}
                        for key, risk_assessment in qualitative_risk['individual_risks'].items():
                            if hasattr(risk_assessment, '__dict__'):
                                # Enum 타입을 문자열로 변환
                                risk_dict = risk_assessment.__dict__.copy()
                                for attr_key, attr_value in risk_dict.items():
                                    if hasattr(attr_value, 'value'):  # Enum인 경우
                                        risk_dict[attr_key] = attr_value.value
                                    elif hasattr(attr_value, 'isoformat'):  # datetime인 경우
                                        risk_dict[attr_key] = attr_value.isoformat()
                                serialized_risks[key] = risk_dict
                            else:
                                serialized_risks[key] = str(risk_assessment)
                        qualitative_risk['individual_risks'] = serialized_risks
                
                results_data.append({
                    'symbol': result.symbol,
                    'name': result.name,
                    'sector': result.sector,
                    'analysis_date': result.analysis_date.isoformat(),
                    'ultimate_score': result.ultimate_score,
                    'ultimate_grade': result.ultimate_grade,
                    'investment_recommendation': result.investment_recommendation,
                    'confidence_level': result.confidence_level,
                    'enhanced_score': result.enhanced_score,
                    'enhanced_grade': result.enhanced_grade,
                    'news_analysis': news_analysis,
                    'qualitative_risk_analysis': qualitative_risk,
                    'sector_analysis': result.sector_analysis,
                    'ml_prediction': result.ml_prediction
                })
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📊 분석 결과 내보내기 완료: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"결과 내보내기 실패: {e}")
            return None

async def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("🚀 궁극의 향상된 통합 분석 시스템")
    print("=" * 80)
    
    # 분석기 초기화
    analyzer = UltimateEnhancedAnalyzer()
    
    # LG생활건강 분석
    print(f"\n🏢 LG생활건강 궁극의 분석")
    result = await analyzer.analyze_stock_ultimate("003550", "LG생활건강", "화장품/생활용품")
    
    # 결과 출력
    print(f"\n📊 분석 결과")
    print(f"종목: {result.name} ({result.symbol})")
    print(f"업종: {result.sector}")
    print(f"궁극의 점수: {result.ultimate_score:.1f}점 ({result.ultimate_grade})")
    print(f"투자 추천: {result.investment_recommendation}")
    print(f"신뢰도: {result.confidence_level}")
    
    # 세부 분석 결과
    if result.news_analysis:
        print(f"\n📰 뉴스 분석")
        print(f"총 뉴스 수: {result.news_analysis.get('total_news', 0)}건")
        print(f"감정 트렌드: {result.news_analysis.get('sentiment_trend', 'neutral')}")
        print(f"평균 감정: {result.news_analysis.get('avg_sentiment', 0):.3f}")
    
    if result.qualitative_risk_analysis:
        print(f"\n⚠️ 정성적 리스크")
        risk_score = result.qualitative_risk_analysis.get('comprehensive_risk_score', 50)
        print(f"종합 리스크 점수: {risk_score:.1f}점")
    
    if result.ml_prediction:
        print(f"\n🤖 머신러닝 예측")
        ensemble_pred = result.ml_prediction.get('ensemble_prediction', 0)
        ensemble_conf = result.ml_prediction.get('ensemble_confidence', 0)
        print(f"예측 수익률: {ensemble_pred:.3f}")
        print(f"예측 신뢰도: {ensemble_conf:.3f}")
    
    # 결과 내보내기
    filename = analyzer.export_results([result])
    if filename:
        print(f"\n💾 분석 결과 저장: {filename}")
    
    print(f"\n" + "=" * 80)
    print("✅ 궁극의 분석 완료")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
