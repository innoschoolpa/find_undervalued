#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
웹 대시보드 구축
Streamlit을 사용한 대화형 웹 인터페이스
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import json
import yaml
from pathlib import Path
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockDashboard:
    """주식 분석 대시보드 클래스"""
    
    def __init__(self):
        self.load_config()
        self.load_sample_data()
    
    def load_config(self):
        """설정 파일 로드"""
        try:
            with open('config.yaml', 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except:
            self.config = {}
    
    def load_sample_data(self):
        """샘플 데이터 로드"""
        # LG생활건강 분석 결과 (실제 데이터 기반)
        self.lg_data = {
            'symbol': '003550',
            'name': 'LG생활건강',
            'sector': '화장품/생활용품',
            'current_price': 75300,
            'market_cap': 118750,
            'per': 21.0,
            'pbr': 0.44,
            'roe': 5.79,
            'debt_ratio': 10.18,
            'revenue_growth': 8.3,
            'operating_growth': 24.98,
            'net_growth': 29.43,
            'net_profit_margin': 22.84,
            'current_ratio': 255.4,
            'analysis_score': 53.0,
            'grade': 'C+',
            'recommendation': 'STRONG_BUY',
            'confidence': 'HIGH'
        }
        
        # 샘플 포트폴리오 데이터
        self.portfolio_data = pd.DataFrame({
            'symbol': ['003550', '005930', '000270', '035420', '012330'],
            'name': ['LG생활건강', '삼성전자', '기아', 'NAVER', '현대모비스'],
            'price': [75300, 79400, 101400, 235000, 309000],
            'change': [1.2, -0.5, 2.1, -1.8, 0.8],
            'volume': [125000, 850000, 450000, 320000, 280000],
            'market_cap': [118750, 4528500, 440229, 367035, 284105],
            'per': [21.0, 16.0, 4.2, 19.7, 7.1],
            'pbr': [0.44, 1.2, 1.8, 2.1, 0.9],
            'roe': [5.79, 6.6, 11.2, 7.0, 8.5],
            'score': [53.0, 65.0, 90.0, 63.0, 80.0],
            'grade': ['C+', 'B', 'A+', 'B', 'A'],
            'recommendation': ['STRONG_BUY', 'BUY', 'STRONG_BUY', 'HOLD', 'BUY']
        })
    
    def render_header(self):
        """헤더 렌더링"""
        st.set_page_config(
            page_title="주식 분석 대시보드",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        st.title("📊 주식 분석 대시보드")
        st.markdown("---")
        
        # 현재 시간 표시
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.sidebar.markdown(f"**업데이트 시간:** {current_time}")
    
    def render_sidebar(self):
        """사이드바 렌더링"""
        st.sidebar.title("🎯 분석 옵션")
        
        # 종목 선택
        selected_symbol = st.sidebar.selectbox(
            "분석 종목 선택",
            options=self.portfolio_data['symbol'].tolist(),
            format_func=lambda x: f"{x} - {self.portfolio_data[self.portfolio_data['symbol'] == x]['name'].iloc[0]}"
        )
        
        # 분석 기간
        analysis_period = st.sidebar.selectbox(
            "분석 기간",
            options=["1개월", "3개월", "6개월", "1년"],
            index=2
        )
        
        # 분석 타입
        analysis_type = st.sidebar.multiselect(
            "분석 타입",
            options=["기본 분석", "정성적 리스크", "머신러닝 예측", "백테스팅"],
            default=["기본 분석", "정성적 리스크"]
        )
        
        return {
            'selected_symbol': selected_symbol,
            'analysis_period': analysis_period,
            'analysis_type': analysis_type
        }
    
    def render_overview(self, options):
        """개요 섹션 렌더링"""
        st.header("📈 종목 개요")
        
        selected_data = self.portfolio_data[self.portfolio_data['symbol'] == options['selected_symbol']].iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="현재가",
                value=f"{selected_data['price']:,}원",
                delta=f"{selected_data['change']:+.1f}%"
            )
        
        with col2:
            st.metric(
                label="시가총액",
                value=f"{selected_data['market_cap']:,}억원"
            )
        
        with col3:
            st.metric(
                label="PER",
                value=f"{selected_data['per']:.1f}배"
            )
        
        with col4:
            st.metric(
                label="PBR",
                value=f"{selected_data['pbr']:.2f}배"
            )
        
        # 추천 정보
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🎯 투자 추천")
            recommendation_color = {
                'STRONG_BUY': '🟢',
                'BUY': '🟡',
                'HOLD': '🟠',
                'SELL': '🔴'
            }
            
            recommendation = selected_data['recommendation']
            st.markdown(f"**{recommendation_color.get(recommendation, '⚪')} {recommendation}**")
        
        with col2:
            st.markdown("### 📊 분석 점수")
            score = selected_data['score']
            grade = selected_data['grade']
            
            # 점수 게이지 차트
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = score,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': f"종합 점수 ({grade})"},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 80], 'color': "yellow"},
                        {'range': [80, 100], 'color': "green"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            
            fig.update_layout(height=250)
            st.plotly_chart(fig, use_container_width=True)
    
    def render_financial_analysis(self, options):
        """재무 분석 섹션 렌더링"""
        st.header("💰 재무 분석")
        
        selected_data = self.portfolio_data[self.portfolio_data['symbol'] == options['selected_symbol']].iloc[0]
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 재무 지표 차트
            metrics = ['PER', 'PBR', 'ROE']
            values = [selected_data['per'], selected_data['pbr'], selected_data['roe']]
            
            fig = px.bar(
                x=metrics,
                y=values,
                title="주요 재무 지표",
                color=values,
                color_continuous_scale="RdYlGn"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 업종 내 비교
            sector_data = self.portfolio_data.copy()
            
            fig = px.scatter(
                sector_data,
                x='per',
                y='roe',
                size='market_cap',
                color='grade',
                hover_data=['name', 'score'],
                title="업종 내 PER vs ROE 비교",
                labels={'per': 'PER', 'roe': 'ROE(%)'}
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    def render_risk_analysis(self, options):
        """리스크 분석 섹션 렌더링"""
        st.header("⚠️ 리스크 분석")
        
        # 정성적 리스크 분석 (시뮬레이션)
        risk_data = {
            '리스크 유형': ['정책 리스크', 'ESG 리스크', '시장 감정 리스크', '경쟁 리스크', '기술 리스크'],
            '점수': [25, 40, 35, 30, 20],
            '레벨': ['낮음', '보통', '보통', '낮음', '낮음']
        }
        
        risk_df = pd.DataFrame(risk_data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 리스크 점수 차트
            fig = px.bar(
                risk_df,
                x='리스크 유형',
                y='점수',
                color='점수',
                color_continuous_scale="Reds",
                title="정성적 리스크 분석"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 리스크 레벨 분포
            risk_level_counts = risk_df['레벨'].value_counts()
            
            fig = px.pie(
                values=risk_level_counts.values,
                names=risk_level_counts.index,
                title="리스크 레벨 분포"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # 종합 리스크 점수
        st.markdown("### 📊 종합 리스크 점수")
        overall_risk_score = np.mean(risk_data['점수'])
        
        if overall_risk_score < 30:
            risk_level = "낮음"
            risk_color = "green"
        elif overall_risk_score < 60:
            risk_level = "보통"
            risk_color = "yellow"
        else:
            risk_level = "높음"
            risk_color = "red"
        
        st.markdown(f"**종합 리스크 점수: {overall_risk_score:.1f}점 ({risk_level})**")
        st.progress(overall_risk_score / 100)
    
    def render_ml_prediction(self, options):
        """머신러닝 예측 섹션 렌더링"""
        st.header("🤖 머신러닝 예측")
        
        selected_data = self.portfolio_data[self.portfolio_data['symbol'] == options['selected_symbol']].iloc[0]
        current_price = selected_data['price']
        
        # 예측 결과 (시뮬레이션)
        predictions = {
            '모델': ['Random Forest', 'Gradient Boosting', 'Linear Regression'],
            '예측가격': [
                current_price * 1.15,
                current_price * 1.08,
                current_price * 0.95
            ],
            '신뢰도': [0.85, 0.78, 0.65],
            '변동폭': ['+15%', '+8%', '-5%']
        }
        
        pred_df = pd.DataFrame(predictions)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 예측 가격 비교
            fig = px.bar(
                pred_df,
                x='모델',
                y='예측가격',
                title="모델별 예측 가격",
                color='신뢰도',
                color_continuous_scale="RdYlGn"
            )
            fig.add_hline(y=current_price, line_dash="dash", line_color="red", 
                         annotation_text=f"현재가: {current_price:,}원")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 신뢰도 차트
            fig = px.bar(
                pred_df,
                x='모델',
                y='신뢰도',
                title="모델별 신뢰도",
                color='신뢰도',
                color_continuous_scale="Blues"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # 평균 예측 결과
        avg_prediction = np.mean(predictions['예측가격'])
        avg_confidence = np.mean(predictions['신뢰도'])
        
        st.markdown("### 📈 평균 예측 결과")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="평균 예측가격",
                value=f"{avg_prediction:,.0f}원",
                delta=f"{((avg_prediction - current_price) / current_price * 100):+.1f}%"
            )
        
        with col2:
            st.metric(
                label="평균 신뢰도",
                value=f"{avg_confidence:.2f}"
            )
        
        with col3:
            expected_return = (avg_prediction - current_price) / current_price * 100
            st.metric(
                label="예상 수익률",
                value=f"{expected_return:+.1f}%"
            )
    
    def render_portfolio_overview(self):
        """포트폴리오 개요 섹션 렌더링"""
        st.header("📊 포트폴리오 개요")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 포트폴리오 구성
            portfolio_composition = self.portfolio_data[['name', 'market_cap']].copy()
            portfolio_composition['비중'] = portfolio_composition['market_cap'] / portfolio_composition['market_cap'].sum() * 100
            
            fig = px.pie(
                portfolio_composition,
                values='market_cap',
                names='name',
                title="포트폴리오 구성 (시가총액 기준)"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 등급별 분포
            grade_distribution = self.portfolio_data['grade'].value_counts()
            
            fig = px.bar(
                x=grade_distribution.index,
                y=grade_distribution.values,
                title="포트폴리오 등급 분포",
                color=grade_distribution.values,
                color_continuous_scale="RdYlGn"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # 포트폴리오 요약 테이블
        st.markdown("### 📋 포트폴리오 요약")
        
        summary_data = self.portfolio_data.copy()
        summary_data['변동률'] = summary_data['change'].apply(lambda x: f"{x:+.1f}%")
        summary_data['시가총액'] = summary_data['market_cap'].apply(lambda x: f"{x:,}억원")
        summary_data['현재가'] = summary_data['price'].apply(lambda x: f"{x:,}원")
        
        display_columns = ['name', '현재가', '변동률', 'per', 'pbr', 'roe', 'score', 'grade', 'recommendation']
        st.dataframe(
            summary_data[display_columns],
            use_container_width=True,
            hide_index=True
        )
    
    def render_news_sentiment(self):
        """뉴스 감정 분석 섹션 렌더링"""
        st.header("📰 뉴스 감정 분석")
        
        # 뉴스 감정 데이터 (시뮬레이션)
        news_data = pd.DataFrame({
            '날짜': pd.date_range(start='2025-08-21', end='2025-09-21', freq='D'),
            '감정점수': np.random.normal(0.1, 0.3, 32),
            '뉴스수': np.random.randint(5, 20, 32)
        })
        
        # 최근 30일 감정 트렌드
        fig = px.line(
            news_data,
            x='날짜',
            y='감정점수',
            title="최근 30일 뉴스 감정 트렌드",
            labels={'감정점수': '감정 점수', '날짜': '날짜'}
        )
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # 감정 분포
        sentiment_distribution = pd.DataFrame({
            '감정': ['매우 긍정', '긍정', '중립', '부정', '매우 부정'],
            '개수': [5, 12, 8, 3, 2]
        })
        
        fig = px.pie(
            sentiment_distribution,
            values='개수',
            names='감정',
            title="뉴스 감정 분포"
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    def run(self):
        """대시보드 실행"""
        self.render_header()
        
        # 사이드바에서 옵션 선택
        options = self.render_sidebar()
        
        # 메인 콘텐츠
        if options['selected_symbol']:
            self.render_overview(options)
            
            if "기본 분석" in options['analysis_type']:
                self.render_financial_analysis(options)
            
            if "정성적 리스크" in options['analysis_type']:
                self.render_risk_analysis(options)
            
            if "머신러닝 예측" in options['analysis_type']:
                self.render_ml_prediction(options)
        
        # 포트폴리오 개요
        self.render_portfolio_overview()
        
        # 뉴스 감정 분석
        self.render_news_sentiment()
        
        # 푸터
        st.markdown("---")
        st.markdown(
            """
            <div style='text-align: center; color: gray;'>
                📊 주식 분석 대시보드 | 데이터 업데이트: 실시간 | 
                <a href='#'>문의하기</a> | <a href='#'>도움말</a>
            </div>
            """,
            unsafe_allow_html=True
        )

def main():
    """메인 실행 함수"""
    try:
        dashboard = StockDashboard()
        dashboard.run()
    except Exception as e:
        st.error(f"대시보드 실행 중 오류가 발생했습니다: {e}")
        logger.error(f"대시보드 오류: {e}")

if __name__ == "__main__":
    main()

