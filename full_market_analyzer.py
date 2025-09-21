#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전체 시장 분석 시스템
KOSPI 전체 종목을 분석하여 저평가 가치주를 발굴
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import yaml
import argparse

# 기존 모듈들
from undervalued_stock_finder import UndervaluedStockFinder

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FullMarketAnalyzer:
    """전체 시장 분석기"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.finder = UndervaluedStockFinder(config_file)
        self.analysis_results = []
        
        logger.info("🌍 전체 시장 분석기 초기화 완료")
    
    async def analyze_full_market(self, 
                                max_stocks: int = 500,
                                parallel_workers: int = 10,
                                min_score: float = 30.0,
                                max_recommendations: int = 50) -> Dict[str, Any]:
        """전체 시장 분석"""
        logger.info(f"🌍 전체 시장 분석 시작 (최대 {max_stocks}개 종목)")
        
        start_time = datetime.now()
        
        # 종목 분석
        results = await self.finder.analyze_stocks(max_stocks=max_stocks, parallel_workers=parallel_workers)
        
        if not results:
            logger.warning("분석할 종목이 없습니다.")
            return {}
        
        # 저평가 가치주 발굴 (기준 완화)
        undervalued_stocks = self.finder.find_undervalued_stocks(
            min_score=min_score,
            max_stocks=max_recommendations,
            sort_by='ultimate_score'
        )
        
        end_time = datetime.now()
        analysis_time = (end_time - start_time).total_seconds()
        
        # 결과 정리
        market_analysis = {
            'analysis_info': {
                'total_analyzed': len(results),
                'undervalued_found': len(undervalued_stocks),
                'analysis_time_seconds': analysis_time,
                'analysis_date': start_time.isoformat(),
                'min_score_threshold': min_score,
                'parallel_workers': parallel_workers
            },
            'all_results': results,
            'undervalued_stocks': undervalued_stocks,
            'market_statistics': self._calculate_market_statistics(results),
            'sector_analysis': self._analyze_by_sector(results),
            'recommendations': self._generate_market_recommendations(undervalued_stocks)
        }
        
        logger.info(f"🎯 전체 시장 분석 완료: {len(results)}개 종목 분석, {len(undervalued_stocks)}개 저평가 종목 발굴")
        
        return market_analysis
    
    def _calculate_market_statistics(self, results: List[Any]) -> Dict[str, Any]:
        """시장 통계 계산"""
        if not results:
            return {}
        
        scores = [r.ultimate_score for r in results]
        grades = [r.ultimate_grade for r in results]
        recommendations = [r.investment_recommendation for r in results]
        sectors = [r.sector for r in results]
        
        # 등급별 분포
        grade_distribution = {}
        for grade in grades:
            grade_distribution[grade] = grade_distribution.get(grade, 0) + 1
        
        # 추천별 분포
        recommendation_distribution = {}
        for rec in recommendations:
            recommendation_distribution[rec] = recommendation_distribution.get(rec, 0) + 1
        
        # 업종별 분포
        sector_distribution = {}
        for sector in sectors:
            sector_distribution[sector] = sector_distribution.get(sector, 0) + 1
        
        return {
            'score_statistics': {
                'mean': np.mean(scores),
                'median': np.median(scores),
                'std': np.std(scores),
                'min': np.min(scores),
                'max': np.max(scores),
                'q25': np.percentile(scores, 25),
                'q75': np.percentile(scores, 75)
            },
            'grade_distribution': grade_distribution,
            'recommendation_distribution': recommendation_distribution,
            'sector_distribution': sector_distribution,
            'total_stocks': len(results)
        }
    
    def _analyze_by_sector(self, results: List[Any]) -> Dict[str, Dict[str, Any]]:
        """업종별 분석"""
        sector_analysis = {}
        
        for result in results:
            sector = result.sector
            if sector not in sector_analysis:
                sector_analysis[sector] = {
                    'stocks': [],
                    'avg_score': 0,
                    'recommendations': {},
                    'top_stocks': []
                }
            
            sector_analysis[sector]['stocks'].append(result)
            
            # 추천 분포
            rec = result.investment_recommendation
            sector_analysis[sector]['recommendations'][rec] = sector_analysis[sector]['recommendations'].get(rec, 0) + 1
        
        # 업종별 통계 계산
        for sector, data in sector_analysis.items():
            if data['stocks']:
                scores = [s.ultimate_score for s in data['stocks']]
                data['avg_score'] = np.mean(scores)
                data['count'] = len(data['stocks'])
                
                # 상위 종목 선택 (상위 3개)
                sorted_stocks = sorted(data['stocks'], key=lambda x: x.ultimate_score, reverse=True)
                data['top_stocks'] = sorted_stocks[:3]
        
        return sector_analysis
    
    def _generate_market_recommendations(self, undervalued_stocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """시장 추천 생성"""
        if not undervalued_stocks:
            return {
                'summary': '현재 시장에서 조건에 맞는 저평가 가치주가 발견되지 않았습니다.',
                'action': '시장 상황을 재검토하고 분석 기준을 조정해보세요.',
                'top_sectors': [],
                'investment_strategy': '보수적 접근 권장'
            }
        
        # 상위 추천 종목
        top_recommendations = undervalued_stocks[:10]
        
        # 업종별 추천 분석
        sector_performance = {}
        for stock in undervalued_stocks:
            sector = stock['sector']
            if sector not in sector_performance:
                sector_performance[sector] = []
            sector_performance[sector].append(stock['ultimate_score'])
        
        # 업종별 평균 점수
        sector_avg_scores = {}
        for sector, scores in sector_performance.items():
            sector_avg_scores[sector] = np.mean(scores)
        
        # 상위 업종
        top_sectors = sorted(sector_avg_scores.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'summary': f'{len(undervalued_stocks)}개의 저평가 가치주를 발굴했습니다.',
            'top_recommendations': top_recommendations,
            'top_sectors': [{'sector': sector, 'avg_score': score} for sector, score in top_sectors],
            'investment_strategy': self._get_investment_strategy(undervalued_stocks),
            'risk_assessment': self._assess_market_risk(undervalued_stocks)
        }
    
    def _get_investment_strategy(self, undervalued_stocks: List[Dict[str, Any]]) -> str:
        """투자 전략 제안"""
        if len(undervalued_stocks) >= 20:
            return "적극적 투자: 충분한 저평가 종목 발견, 분산 투자 추천"
        elif len(undervalued_stocks) >= 10:
            return "균형 투자: 적당한 기회 발견, 선별적 투자 추천"
        elif len(undervalued_stocks) >= 5:
            return "신중한 투자: 제한된 기회, 신중한 선별 투자"
        else:
            return "보수적 투자: 제한된 기회, 현금 보유 우선 고려"
    
    def _assess_market_risk(self, undervalued_stocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """시장 리스크 평가"""
        if not undervalued_stocks:
            return {
                'overall_risk': 'HIGH',
                'reason': '저평가 종목 부족으로 시장 과열 가능성',
                'recommendation': '시장 조정 대기 권장'
            }
        
        avg_score = np.mean([s['ultimate_score'] for s in undervalued_stocks])
        high_quality_count = len([s for s in undervalued_stocks if s['ultimate_score'] >= 70])
        
        if avg_score >= 70 and high_quality_count >= 10:
            risk_level = 'LOW'
            reason = '충분한 고품질 저평가 종목 존재'
            recommendation = '적극적 투자 가능'
        elif avg_score >= 60:
            risk_level = 'MEDIUM'
            reason = '적당한 투자 기회 존재'
            recommendation = '균형잡힌 투자 전략'
        else:
            risk_level = 'HIGH'
            reason = '저평가 종목 품질 제한적'
            recommendation = '신중한 투자 필요'
        
        return {
            'overall_risk': risk_level,
            'reason': reason,
            'recommendation': recommendation,
            'avg_score': avg_score,
            'high_quality_count': high_quality_count
        }
    
    def save_full_analysis(self, market_analysis: Dict[str, Any], filename: str = None):
        """전체 분석 결과 저장"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"full_market_analysis_{timestamp}.json"
        
        try:
            # JSON 직렬화를 위한 데이터 변환
            serializable_data = self._make_json_serializable(market_analysis)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(serializable_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 전체 시장 분석 결과 저장: {filename}")
            return filename
        except Exception as e:
            logger.error(f"결과 저장 실패: {e}")
            return None
    
    def _make_json_serializable(self, obj):
        """JSON 직렬화 가능한 형태로 변환"""
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            return self._make_json_serializable(obj.__dict__)
        elif isinstance(obj, (datetime,)):
            return obj.isoformat()
        else:
            return obj
    
    def generate_full_report(self, market_analysis: Dict[str, Any]) -> str:
        """전체 시장 보고서 생성"""
        if not market_analysis:
            return "❌ 분석 데이터가 없습니다."
        
        report = []
        info = market_analysis['analysis_info']
        stats = market_analysis['market_statistics']
        sector_analysis = market_analysis['sector_analysis']
        recommendations = market_analysis['recommendations']
        undervalued = market_analysis['undervalued_stocks']
        
        report.append("=" * 100)
        report.append("🌍 전체 시장 분석 보고서")
        report.append("=" * 100)
        report.append(f"📅 분석 일시: {info['analysis_date']}")
        report.append(f"📊 분석 종목 수: {info['total_analyzed']}개")
        report.append(f"🎯 저평가 종목 발견: {info['undervalued_found']}개")
        report.append(f"⏱️ 분석 소요 시간: {info['analysis_time_seconds']:.1f}초")
        report.append(f"🔧 병렬 처리: {info['parallel_workers']}개 워커")
        report.append("")
        
        # 시장 통계
        report.append("📈 시장 통계")
        report.append("-" * 50)
        score_stats = stats['score_statistics']
        report.append(f"평균 점수: {score_stats['mean']:.1f}점")
        report.append(f"중앙값: {score_stats['median']:.1f}점")
        report.append(f"표준편차: {score_stats['std']:.1f}점")
        report.append(f"최고점: {score_stats['max']:.1f}점")
        report.append(f"최저점: {score_stats['min']:.1f}점")
        report.append("")
        
        # 등급별 분포
        report.append("🏆 등급별 분포")
        report.append("-" * 30)
        for grade, count in stats['grade_distribution'].items():
            percentage = (count / stats['total_stocks']) * 100
            report.append(f"{grade}: {count}개 ({percentage:.1f}%)")
        report.append("")
        
        # 추천별 분포
        report.append("💡 투자 추천 분포")
        report.append("-" * 30)
        for rec, count in stats['recommendation_distribution'].items():
            percentage = (count / stats['total_stocks']) * 100
            report.append(f"{rec}: {count}개 ({percentage:.1f}%)")
        report.append("")
        
        # 업종별 분석
        report.append("🏭 업종별 분석 (상위 10개)")
        report.append("-" * 50)
        sorted_sectors = sorted(sector_analysis.items(), key=lambda x: x[1]['avg_score'], reverse=True)
        for i, (sector, data) in enumerate(sorted_sectors[:10], 1):
            report.append(f"{i:2d}. {sector}")
            report.append(f"     평균 점수: {data['avg_score']:.1f}점")
            report.append(f"     종목 수: {data['count']}개")
            if data['top_stocks']:
                top_stock = data['top_stocks'][0]
                report.append(f"     최고 점수: {top_stock.name} ({top_stock.ultimate_score:.1f}점)")
            report.append("")
        
        # 저평가 종목 추천
        if undervalued:
            report.append("🎯 저평가 가치주 추천 (상위 20개)")
            report.append("-" * 60)
            for i, stock in enumerate(undervalued[:20], 1):
                report.append(f"{i:2d}. {stock['name']} ({stock['symbol']})")
                report.append(f"     업종: {stock['sector']}")
                report.append(f"     궁극의 점수: {stock['ultimate_score']:.1f}점 ({stock['ultimate_grade']})")
                report.append(f"     투자 추천: {stock['investment_recommendation']}")
                report.append(f"     신뢰도: {stock['confidence_level']}")
                
                financial = stock['financial_data']
                report.append(f"     💰 PER: {financial['per']:.1f}, PBR: {financial['pbr']:.2f}, ROE: {financial['roe']:.1f}%")
                report.append("")
        
        # 투자 전략 및 리스크 평가
        report.append("💼 투자 전략 및 리스크 평가")
        report.append("-" * 50)
        report.append(f"📋 전략: {recommendations['investment_strategy']}")
        
        if 'risk_assessment' in recommendations:
            risk = recommendations['risk_assessment']
            report.append(f"⚠️ 전체 리스크: {risk['overall_risk']}")
            report.append(f"📝 사유: {risk['reason']}")
            report.append(f"💡 권장사항: {risk['recommendation']}")
        
        report.append("")
        report.append("⚠️ 투자 주의사항:")
        report.append("- 이 분석은 참고용이며, 투자 결정은 개인의 책임입니다.")
        report.append("- 시장 상황과 개인적 위험 감수 능력을 고려하세요.")
        report.append("- 분산 투자를 통해 리스크를 관리하세요.")
        report.append("- 정기적인 포트폴리오 리밸런싱을 권장합니다.")
        
        report.append("=" * 100)
        
        return "\n".join(report)

async def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='전체 시장 분석 시스템')
    parser.add_argument('--max-stocks', type=int, default=500, help='최대 분석 종목 수 (기본값: 500)')
    parser.add_argument('--workers', type=int, default=10, help='병렬 처리 워커 수 (기본값: 10)')
    parser.add_argument('--min-score', type=float, default=30.0, help='최소 점수 기준 (기본값: 30.0)')
    parser.add_argument('--max-recommendations', type=int, default=50, help='최대 추천 종목 수 (기본값: 50)')
    
    args = parser.parse_args()
    
    print("=" * 100)
    print("🌍 전체 시장 분석 시스템")
    print("=" * 100)
    print(f"📊 분석 설정:")
    print(f"   - 최대 분석 종목: {args.max_stocks}개")
    print(f"   - 병렬 처리 워커: {args.workers}개")
    print(f"   - 최소 점수 기준: {args.min_score}점")
    print(f"   - 최대 추천 종목: {args.max_recommendations}개")
    print("=" * 100)
    
    # 전체 시장 분석기 초기화
    analyzer = FullMarketAnalyzer()
    
    # 전체 시장 분석 실행
    print(f"\n🌍 전체 시장 분석 시작...")
    market_analysis = await analyzer.analyze_full_market(
        max_stocks=args.max_stocks,
        parallel_workers=args.workers,
        min_score=args.min_score,
        max_recommendations=args.max_recommendations
    )
    
    if not market_analysis:
        print("❌ 분석할 종목이 없습니다.")
        return
    
    # 전체 보고서 생성
    print(f"\n📊 전체 시장 보고서 생성...")
    report = analyzer.generate_full_report(market_analysis)
    print(report)
    
    # 결과 저장
    analysis_filename = analyzer.save_full_analysis(market_analysis)
    if analysis_filename:
        print(f"\n💾 전체 분석 결과 저장: {analysis_filename}")
    
    # 보고서도 파일로 저장
    report_filename = f"full_market_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"📄 전체 시장 보고서 저장: {report_filename}")
    
    print(f"\n" + "=" * 100)
    print("✅ 전체 시장 분석 완료")
    print("=" * 100)

if __name__ == "__main__":
    asyncio.run(main())
