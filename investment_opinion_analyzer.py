# investment_opinion_analyzer.py
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter
from investment_opinion_client import InvestmentOpinionClient
from investment_opinion_models import (
    ProcessedInvestmentOpinion,
    InvestmentOpinionSummary
)

logger = logging.getLogger(__name__)


class InvestmentOpinionAnalyzer:
    """투자의견 데이터를 분석하고 인사이트를 제공하는 클래스"""

    def __init__(self, config_path: str = 'config.yaml'):
        self.client = InvestmentOpinionClient(config_path)

    def analyze_single_stock(
        self, 
        symbol: str, 
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        단일 종목의 투자의견을 종합 분석합니다.
        
        Args:
            symbol: 종목코드
            days_back: 분석 기간 (일)
            
        Returns:
            종합 분석 결과
        """
        logger.info(f"🔍 {symbol} 종목 투자의견 분석 시작 (기간: {days_back}일)")
        
        # 투자의견 데이터 조회
        opinions = self.client.get_investment_opinions(symbol, days_back=days_back)
        
        if not opinions:
            logger.warning(f"⚠️ {symbol} 종목의 투자의견 데이터가 없습니다.")
            return {
                'symbol': symbol,
                'analysis_period': f"{days_back}일",
                'total_opinions': 0,
                'status': 'no_data',
                'message': '투자의견 데이터가 없습니다.'
            }
        
        # 기본 요약 생성
        summary = InvestmentOpinionSummary.from_opinions(symbol, opinions)
        
        # 상세 분석 수행
        analysis = {
            'symbol': symbol,
            'analysis_period': f"{days_back}일",
            'total_opinions': len(opinions),
            'status': 'success',
            'summary': summary,
            'detailed_analysis': self._perform_detailed_analysis(opinions),
            'trend_analysis': self._analyze_trends(opinions),
            'consensus_analysis': self._analyze_consensus(opinions),
            'target_price_analysis': self._analyze_target_prices(opinions),
            'brokerage_analysis': self._analyze_brokerage_distribution(opinions)
        }
        
        logger.info(f"✅ {symbol} 종목 분석 완료: {len(opinions)}건의 의견 분석")
        return analysis

    def analyze_multiple_stocks(
        self, 
        symbols: List[str], 
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        여러 종목의 투자의견을 비교 분석합니다.
        
        Args:
            symbols: 종목코드 리스트
            days_back: 분석 기간 (일)
            
        Returns:
            비교 분석 결과
        """
        logger.info(f"🔍 {len(symbols)}개 종목 투자의견 비교 분석 시작")
        
        # 각 종목별 분석
        stock_analyses = {}
        for symbol in symbols:
            try:
                stock_analyses[symbol] = self.analyze_single_stock(symbol, days_back)
            except Exception as e:
                logger.error(f"❌ {symbol} 종목 분석 실패: {e}")
                stock_analyses[symbol] = {
                    'symbol': symbol,
                    'status': 'error',
                    'error': str(e)
                }
        
        # 비교 분석 수행
        comparison = self._perform_comparison_analysis(stock_analyses)
        
        return {
            'analysis_period': f"{days_back}일",
            'total_stocks': len(symbols),
            'successful_analyses': len([s for s in stock_analyses.values() if s.get('status') == 'success']),
            'stock_analyses': stock_analyses,
            'comparison_analysis': comparison
        }

    def _perform_detailed_analysis(self, opinions: List[ProcessedInvestmentOpinion]) -> Dict[str, Any]:
        """상세 분석을 수행합니다."""
        if not opinions:
            return {}
        
        # 의견 분포
        opinion_counts = Counter(op.current_opinion for op in opinions)
        
        # 날짜별 분석
        date_analysis = {}
        for opinion in opinions:
            date = opinion.business_date
            if date not in date_analysis:
                date_analysis[date] = []
            date_analysis[date].append(opinion)
        
        # 최근 7일간의 의견 변화
        recent_opinions = sorted(opinions, key=lambda x: x.business_date, reverse=True)[:7]
        recent_changes = [op for op in recent_opinions if op.opinion_change == "변경"]
        
        return {
            'opinion_distribution': dict(opinion_counts),
            'daily_opinion_count': {date: len(ops) for date, ops in date_analysis.items()},
            'recent_changes': len(recent_changes),
            'most_active_date': max(date_analysis.keys()) if date_analysis else None,
            'total_brokerages': len(set(op.brokerage_firm for op in opinions))
        }

    def _analyze_trends(self, opinions: List[ProcessedInvestmentOpinion]) -> Dict[str, Any]:
        """트렌드 분석을 수행합니다."""
        if not opinions:
            return {}
        
        # 시간순 정렬
        sorted_opinions = sorted(opinions, key=lambda x: x.business_date)
        
        # 최근 3개 의견과 과거 3개 의견 비교
        if len(sorted_opinions) >= 6:
            recent_3 = sorted_opinions[-3:]
            older_3 = sorted_opinions[:3]
            
            recent_sentiment = self._calculate_sentiment_score(recent_3)
            older_sentiment = self._calculate_sentiment_score(older_3)
            
            sentiment_trend = "상승" if recent_sentiment > older_sentiment else "하락" if recent_sentiment < older_sentiment else "보합"
        else:
            sentiment_trend = "데이터 부족"
        
        # 목표가 트렌드
        target_prices = [op.target_price for op in opinions if op.target_price > 0]
        if len(target_prices) >= 2:
            target_trend = "상승" if target_prices[-1] > target_prices[0] else "하락" if target_prices[-1] < target_prices[0] else "보합"
        else:
            target_trend = "데이터 부족"
        
        return {
            'sentiment_trend': sentiment_trend,
            'target_price_trend': target_trend,
            'opinion_change_frequency': len([op for op in opinions if op.opinion_change == "변경"]) / len(opinions) * 100
        }

    def _analyze_consensus(self, opinions: List[ProcessedInvestmentOpinion]) -> Dict[str, Any]:
        """컨센서스 분석을 수행합니다."""
        if not opinions:
            return {}
        
        # 최근 의견들만 분석 (최근 10개)
        recent_opinions = sorted(opinions, key=lambda x: x.business_date, reverse=True)[:10]
        
        # 의견 분류
        buy_keywords = ['매수', 'BUY', 'Strong Buy', '적극매수', '매수추천']
        sell_keywords = ['매도', 'SELL', 'Strong Sell', '적극매도', '매도추천']
        hold_keywords = ['보유', 'HOLD', '중립', '관망']
        
        consensus_scores = []
        for opinion in recent_opinions:
            opinion_text = opinion.current_opinion.upper()
            
            if any(keyword.upper() in opinion_text for keyword in buy_keywords):
                consensus_scores.append(1)  # 매수
            elif any(keyword.upper() in opinion_text for keyword in sell_keywords):
                consensus_scores.append(-1)  # 매도
            elif any(keyword.upper() in opinion_text for keyword in hold_keywords):
                consensus_scores.append(0)  # 보유
            else:
                consensus_scores.append(0)  # 기타는 보유로 분류
        
        avg_consensus = sum(consensus_scores) / len(consensus_scores) if consensus_scores else 0
        
        return {
            'consensus_score': round(avg_consensus, 2),
            'consensus_level': self._interpret_consensus(avg_consensus),
            'sample_size': len(recent_opinions)
        }

    def _analyze_target_prices(self, opinions: List[ProcessedInvestmentOpinion]) -> Dict[str, Any]:
        """목표가 분석을 수행합니다."""
        target_prices = [op.target_price for op in opinions if op.target_price > 0]
        
        if not target_prices:
            return {'status': 'no_data'}
        
        # 통계 계산
        avg_target = sum(target_prices) / len(target_prices)
        max_target = max(target_prices)
        min_target = min(target_prices)
        
        # 현재가 대비 상승률 (마지막 전일종가 기준)
        last_close = opinions[-1].previous_close if opinions else 0
        if last_close > 0:
            avg_upside = (avg_target - last_close) / last_close * 100
        else:
            avg_upside = 0
        
        return {
            'avg_target_price': round(avg_target, 2),
            'max_target_price': max_target,
            'min_target_price': min_target,
            'price_range': max_target - min_target,
            'avg_upside_potential': round(avg_upside, 2),
            'target_count': len(target_prices),
            'coverage_rate': len(target_prices) / len(opinions) * 100
        }

    def _analyze_brokerage_distribution(self, opinions: List[ProcessedInvestmentOpinion]) -> Dict[str, Any]:
        """증권사 분포 분석을 수행합니다."""
        brokerage_counts = Counter(op.brokerage_firm for op in opinions)
        
        # 상위 증권사
        top_brokerages = brokerage_counts.most_common(5)
        
        # 증권사별 평균 목표가
        brokerage_targets = {}
        for opinion in opinions:
            firm = opinion.brokerage_firm
            if opinion.target_price > 0:
                if firm not in brokerage_targets:
                    brokerage_targets[firm] = []
                brokerage_targets[firm].append(opinion.target_price)
        
        brokerage_avg_targets = {
            firm: sum(prices) / len(prices) 
            for firm, prices in brokerage_targets.items()
        }
        
        return {
            'total_brokerages': len(brokerage_counts),
            'top_brokerages': top_brokerages,
            'brokerage_avg_targets': brokerage_avg_targets,
            'concentration_ratio': top_brokerages[0][1] / len(opinions) * 100 if top_brokerages else 0
        }

    def _perform_comparison_analysis(self, stock_analyses: Dict[str, Any]) -> Dict[str, Any]:
        """종목 간 비교 분석을 수행합니다."""
        successful_analyses = {k: v for k, v in stock_analyses.items() if v.get('status') == 'success'}
        
        if not successful_analyses:
            return {'status': 'no_data'}
        
        # 각 지표별 비교
        comparisons = {}
        
        # 평균 목표가 비교
        target_prices = {}
        for symbol, analysis in successful_analyses.items():
            if 'target_price_analysis' in analysis and analysis['target_price_analysis'].get('avg_target_price'):
                target_prices[symbol] = analysis['target_price_analysis']['avg_target_price']
        
        if target_prices:
            comparisons['target_price_ranking'] = sorted(target_prices.items(), key=lambda x: x[1], reverse=True)
        
        # 컨센서스 점수 비교
        consensus_scores = {}
        for symbol, analysis in successful_analyses.items():
            if 'consensus_analysis' in analysis and analysis['consensus_analysis'].get('consensus_score'):
                consensus_scores[symbol] = analysis['consensus_analysis']['consensus_score']
        
        if consensus_scores:
            comparisons['consensus_ranking'] = sorted(consensus_scores.items(), key=lambda x: x[1], reverse=True)
        
        # 총 의견 수 비교
        opinion_counts = {}
        for symbol, analysis in successful_analyses.items():
            if analysis.get('total_opinions'):
                opinion_counts[symbol] = analysis['total_opinions']
        
        if opinion_counts:
            comparisons['opinion_count_ranking'] = sorted(opinion_counts.items(), key=lambda x: x[1], reverse=True)
        
        return comparisons

    def _calculate_sentiment_score(self, opinions: List[ProcessedInvestmentOpinion]) -> float:
        """감정 점수를 계산합니다."""
        if not opinions:
            return 0
        
        buy_keywords = ['매수', 'BUY', 'Strong Buy', '적극매수']
        sell_keywords = ['매도', 'SELL', 'Strong Sell', '적극매도']
        
        total_score = 0
        for opinion in opinions:
            opinion_text = opinion.current_opinion.upper()
            if any(keyword.upper() in opinion_text for keyword in buy_keywords):
                total_score += 1
            elif any(keyword.upper() in opinion_text for keyword in sell_keywords):
                total_score -= 1
        
        return total_score / len(opinions)

    def _interpret_consensus(self, score: float) -> str:
        """컨센서스 점수를 해석합니다."""
        if score >= 0.5:
            return "강한 매수"
        elif score >= 0.2:
            return "매수"
        elif score >= -0.2:
            return "중립"
        elif score >= -0.5:
            return "매도"
        else:
            return "강한 매도"

    def generate_report(
        self, 
        analysis_result: Dict[str, Any], 
        format: str = 'text'
    ) -> str:
        """분석 결과를 보고서 형태로 생성합니다."""
        if analysis_result.get('status') != 'success':
            return f"분석 실패: {analysis_result.get('message', '알 수 없는 오류')}"
        
        symbol = analysis_result['symbol']
        summary = analysis_result['summary']
        
        report = f"""
📊 투자의견 분석 보고서
{'='*50}

📈 종목: {symbol}
📅 분석 기간: {analysis_result['analysis_period']}
📋 총 의견 수: {summary.total_opinions}건

📊 의견 분포:
  • 매수: {summary.buy_opinions}건
  • 보유: {summary.hold_opinions}건
  • 매도: {summary.sell_opinions}건

🎯 목표가 분석:
  • 평균 목표가: {summary.avg_target_price:,}원
  • 최고 목표가: {summary.max_target_price:,}원
  • 최저 목표가: {summary.min_target_price:,}원
  • 평균 상승률: {summary.avg_upside:+.2f}%

📈 트렌드: {summary.opinion_trend}
📅 최근 의견: {summary.most_recent_date}

🔍 상세 분석:
"""
        
        # 상세 분석 추가
        detailed = analysis_result.get('detailed_analysis', {})
        if detailed:
            report += f"  • 최근 의견 변경: {detailed.get('recent_changes', 0)}건\n"
            report += f"  • 참여 증권사: {detailed.get('total_brokerages', 0)}개\n"
        
        # 컨센서스 분석 추가
        consensus = analysis_result.get('consensus_analysis', {})
        if consensus:
            report += f"  • 컨센서스 점수: {consensus.get('consensus_score', 0):.2f}\n"
            report += f"  • 컨센서스 해석: {consensus.get('consensus_level', 'N/A')}\n"
        
        # 목표가 분석 추가
        target_analysis = analysis_result.get('target_price_analysis', {})
        if target_analysis and target_analysis.get('status') != 'no_data':
            report += f"  • 목표가 커버리지: {target_analysis.get('coverage_rate', 0):.1f}%\n"
        
        return report

    def export_to_dataframe(self, analysis_result: Dict[str, Any]) -> pd.DataFrame:
        """분석 결과를 DataFrame으로 변환합니다."""
        if analysis_result.get('status') != 'success':
            return pd.DataFrame()
        
        symbol = analysis_result['symbol']
        summary = analysis_result['summary']
        
        data = {
            'symbol': [symbol],
            'total_opinions': [summary.total_opinions],
            'buy_opinions': [summary.buy_opinions],
            'hold_opinions': [summary.hold_opinions],
            'sell_opinions': [summary.sell_opinions],
            'avg_target_price': [summary.avg_target_price],
            'max_target_price': [summary.max_target_price],
            'min_target_price': [summary.min_target_price],
            'avg_upside': [summary.avg_upside],
            'opinion_trend': [summary.opinion_trend],
            'most_recent_date': [summary.most_recent_date]
        }
        
        # 상세 분석 데이터 추가
        detailed = analysis_result.get('detailed_analysis', {})
        data.update({
            'recent_changes': [detailed.get('recent_changes', 0)],
            'total_brokerages': [detailed.get('total_brokerages', 0)]
        })
        
        # 컨센서스 분석 데이터 추가
        consensus = analysis_result.get('consensus_analysis', {})
        data.update({
            'consensus_score': [consensus.get('consensus_score', 0)],
            'consensus_level': [consensus.get('consensus_level', 'N/A')]
        })
        
        return pd.DataFrame(data)

