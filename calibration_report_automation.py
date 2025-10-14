#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
캘리브레이션 리포트 자동화 (주간)
최근 선택 종목들의 ex-post 분포(수익률, 변동성, 하락폭), 컷 변동과의 상관 제시
"""

import logging
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import statistics

logger = logging.getLogger(__name__)

@dataclass
class CalibrationReport:
    """캘리브레이션 리포트 데이터"""
    report_date: str
    period_days: int
    total_selections: int
    performance_metrics: Dict[str, float]
    cut_analysis: Dict[str, Any]
    sector_performance: Dict[str, Dict[str, float]]
    risk_metrics: Dict[str, float]
    recommendations: List[str]

class CalibrationReportAutomation:
    """캘리브레이션 리포트 자동화 클래스"""
    
    def __init__(self, logs_dir: str = "logs/calibration"):
        """
        Args:
            logs_dir: 로그 디렉토리 경로
        """
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # 리포트 저장 디렉토리
        self.reports_dir = self.logs_dir / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_weekly_report(self, days_back: int = 7) -> CalibrationReport:
        """
        주간 캘리브레이션 리포트 생성
        
        Args:
            days_back: 과거 며칠까지 분석할지
            
        Returns:
            CalibrationReport: 캘리브레이션 리포트
        """
        try:
            # 1. 최근 선택 종목 데이터 수집
            recent_selections = self._collect_recent_selections(days_back)
            
            if not recent_selections:
                logger.warning("최근 선택 종목 데이터가 없습니다.")
                return self._create_empty_report(days_back)
            
            # 2. 성과 메트릭 계산
            performance_metrics = self._calculate_performance_metrics(recent_selections)
            
            # 3. 컷 분석
            cut_analysis = self._analyze_cut_effectiveness(recent_selections)
            
            # 4. 섹터별 성과 분석
            sector_performance = self._analyze_sector_performance(recent_selections)
            
            # 5. 리스크 메트릭 계산
            risk_metrics = self._calculate_risk_metrics(recent_selections)
            
            # 6. 권장사항 생성
            recommendations = self._generate_recommendations(
                performance_metrics, cut_analysis, sector_performance, risk_metrics
            )
            
            # 7. 리포트 생성
            report = CalibrationReport(
                report_date=datetime.now().strftime('%Y-%m-%d'),
                period_days=days_back,
                total_selections=len(recent_selections),
                performance_metrics=performance_metrics,
                cut_analysis=cut_analysis,
                sector_performance=sector_performance,
                risk_metrics=risk_metrics,
                recommendations=recommendations
            )
            
            # 8. 리포트 저장
            self._save_report(report)
            
            return report
            
        except Exception as e:
            logger.error(f"캘리브레이션 리포트 생성 중 오류: {e}")
            return self._create_empty_report(days_back)
    
    def _collect_recent_selections(self, days_back: int) -> List[Dict[str, Any]]:
        """최근 선택 종목 데이터 수집"""
        selections = []
        
        try:
            # 로그 파일에서 최근 선택 종목 데이터 수집
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            # 로그 디렉토리에서 JSON 파일들 검색
            for log_file in self.logs_dir.glob("*.json"):
                if log_file.stat().st_mtime > cutoff_date.timestamp():
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                selections.extend(data)
                            elif isinstance(data, dict) and 'selections' in data:
                                selections.extend(data['selections'])
                    except Exception as e:
                        logger.debug(f"로그 파일 읽기 실패 {log_file}: {e}")
            
            # CSV 파일에서도 수집
            for csv_file in self.logs_dir.glob("*.csv"):
                if csv_file.stat().st_mtime > cutoff_date.timestamp():
                    try:
                        df = pd.read_csv(csv_file)
                        if not df.empty:
                            # CSV 데이터를 딕셔너리 리스트로 변환
                            csv_data = df.to_dict('records')
                            selections.extend(csv_data)
                    except Exception as e:
                        logger.debug(f"CSV 파일 읽기 실패 {csv_file}: {e}")
            
            logger.info(f"최근 {days_back}일간 {len(selections)}개 선택 종목 데이터 수집")
            return selections
            
        except Exception as e:
            logger.error(f"최근 선택 종목 데이터 수집 실패: {e}")
            return []
    
    def _calculate_performance_metrics(self, selections: List[Dict[str, Any]]) -> Dict[str, float]:
        """성과 메트릭 계산"""
        if not selections:
            return {}
        
        try:
            # 수익률 데이터 추출
            returns = []
            for selection in selections:
                # 다양한 수익률 필드명 시도
                return_fields = ['return', 'returns', 'performance', 'gain', 'profit']
                for field in return_fields:
                    if field in selection and selection[field] is not None:
                        try:
                            returns.append(float(selection[field]))
                            break
                        except (ValueError, TypeError):
                            continue
            
            if not returns:
                logger.warning("수익률 데이터를 찾을 수 없습니다.")
                return {}
            
            # 기본 통계 계산
            metrics = {
                'mean_return': statistics.mean(returns),
                'median_return': statistics.median(returns),
                'std_return': statistics.stdev(returns) if len(returns) > 1 else 0,
                'min_return': min(returns),
                'max_return': max(returns),
                'positive_count': len([r for r in returns if r > 0]),
                'negative_count': len([r for r in returns if r < 0]),
                'win_rate': len([r for r in returns if r > 0]) / len(returns) * 100,
                'total_count': len(returns)
            }
            
            # 추가 메트릭
            if len(returns) > 1:
                metrics['sharpe_ratio'] = (statistics.mean(returns) / statistics.stdev(returns)) if statistics.stdev(returns) > 0 else 0
                metrics['var_95'] = sorted(returns)[int(len(returns) * 0.05)]  # 95% VaR
                metrics['cvar_95'] = statistics.mean([r for r in returns if r <= metrics['var_95']])  # 95% CVaR
            
            return metrics
            
        except Exception as e:
            logger.error(f"성과 메트릭 계산 실패: {e}")
            return {}
    
    def _analyze_cut_effectiveness(self, selections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """컷 효과성 분석"""
        if not selections:
            return {}
        
        try:
            # 점수별 성과 분석
            score_performance = {}
            cut_ranges = [
                (0, 50, "낮음"),
                (50, 70, "보통"),
                (70, 85, "높음"),
                (85, 100, "매우높음")
            ]
            
            for min_score, max_score, label in cut_ranges:
                range_selections = [
                    s for s in selections 
                    if min_score <= s.get('score', 0) < max_score
                ]
                
                if range_selections:
                    returns = []
                    for selection in range_selections:
                        return_fields = ['return', 'returns', 'performance', 'gain', 'profit']
                        for field in return_fields:
                            if field in selection and selection[field] is not None:
                                try:
                                    returns.append(float(selection[field]))
                                    break
                                except (ValueError, TypeError):
                                    continue
                    
                    if returns:
                        score_performance[label] = {
                            'count': len(returns),
                            'mean_return': statistics.mean(returns),
                            'win_rate': len([r for r in returns if r > 0]) / len(returns) * 100,
                            'std_return': statistics.stdev(returns) if len(returns) > 1 else 0
                        }
            
            # 현재 컷라인 효과성 평가
            current_cut = 70  # 기본 컷라인 (실제로는 동적으로 가져와야 함)
            above_cut = [s for s in selections if s.get('score', 0) >= current_cut]
            below_cut = [s for s in selections if s.get('score', 0) < current_cut]
            
            cut_analysis = {
                'score_performance': score_performance,
                'current_cut': current_cut,
                'above_cut_count': len(above_cut),
                'below_cut_count': len(below_cut),
                'cut_effectiveness': self._calculate_cut_effectiveness(above_cut, below_cut)
            }
            
            return cut_analysis
            
        except Exception as e:
            logger.error(f"컷 효과성 분석 실패: {e}")
            return {}
    
    def _calculate_cut_effectiveness(self, above_cut: List[Dict], below_cut: List[Dict]) -> Dict[str, float]:
        """컷라인 효과성 계산"""
        try:
            # 위쪽과 아래쪽의 평균 수익률 비교
            above_returns = []
            below_returns = []
            
            for selection in above_cut:
                return_fields = ['return', 'returns', 'performance', 'gain', 'profit']
                for field in return_fields:
                    if field in selection and selection[field] is not None:
                        try:
                            above_returns.append(float(selection[field]))
                            break
                        except (ValueError, TypeError):
                            continue
            
            for selection in below_cut:
                return_fields = ['return', 'returns', 'performance', 'gain', 'profit']
                for field in return_fields:
                    if field in selection and selection[field] is not None:
                        try:
                            below_returns.append(float(selection[field]))
                            break
                        except (ValueError, TypeError):
                            continue
            
            if not above_returns or not below_returns:
                return {}
            
            above_mean = statistics.mean(above_returns)
            below_mean = statistics.mean(below_returns)
            
            effectiveness = {
                'above_cut_mean': above_mean,
                'below_cut_mean': below_mean,
                'performance_gap': above_mean - below_mean,
                'effectiveness_ratio': above_mean / below_mean if below_mean != 0 else float('inf'),
                'above_cut_win_rate': len([r for r in above_returns if r > 0]) / len(above_returns) * 100,
                'below_cut_win_rate': len([r for r in below_returns if r > 0]) / len(below_returns) * 100
            }
            
            return effectiveness
            
        except Exception as e:
            logger.error(f"컷라인 효과성 계산 실패: {e}")
            return {}
    
    def _analyze_sector_performance(self, selections: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """섹터별 성과 분석"""
        if not selections:
            return {}
        
        try:
            sector_data = {}
            
            # 섹터별로 그룹화
            for selection in selections:
                sector = selection.get('sector', '미분류')
                if sector not in sector_data:
                    sector_data[sector] = []
                
                # 수익률 데이터 추가
                return_fields = ['return', 'returns', 'performance', 'gain', 'profit']
                for field in return_fields:
                    if field in selection and selection[field] is not None:
                        try:
                            sector_data[sector].append(float(selection[field]))
                            break
                        except (ValueError, TypeError):
                            continue
            
            # 섹터별 통계 계산
            sector_performance = {}
            for sector, returns in sector_data.items():
                if returns:
                    sector_performance[sector] = {
                        'count': len(returns),
                        'mean_return': statistics.mean(returns),
                        'median_return': statistics.median(returns),
                        'std_return': statistics.stdev(returns) if len(returns) > 1 else 0,
                        'win_rate': len([r for r in returns if r > 0]) / len(returns) * 100,
                        'min_return': min(returns),
                        'max_return': max(returns)
                    }
            
            return sector_performance
            
        except Exception as e:
            logger.error(f"섹터별 성과 분석 실패: {e}")
            return {}
    
    def _calculate_risk_metrics(self, selections: List[Dict[str, Any]]) -> Dict[str, float]:
        """리스크 메트릭 계산"""
        if not selections:
            return {}
        
        try:
            # 수익률 데이터 추출
            returns = []
            for selection in selections:
                return_fields = ['return', 'returns', 'performance', 'gain', 'profit']
                for field in return_fields:
                    if field in selection and selection[field] is not None:
                        try:
                            returns.append(float(selection[field]))
                            break
                        except (ValueError, TypeError):
                            continue
            
            if not returns:
                return {}
            
            # 리스크 메트릭 계산
            risk_metrics = {
                'volatility': statistics.stdev(returns) if len(returns) > 1 else 0,
                'var_95': sorted(returns)[int(len(returns) * 0.05)] if len(returns) > 20 else min(returns),
                'var_99': sorted(returns)[int(len(returns) * 0.01)] if len(returns) > 100 else min(returns),
                'max_drawdown': self._calculate_max_drawdown(returns),
                'downside_deviation': self._calculate_downside_deviation(returns),
                'calmar_ratio': self._calculate_calmar_ratio(returns)
            }
            
            return risk_metrics
            
        except Exception as e:
            logger.error(f"리스크 메트릭 계산 실패: {e}")
            return {}
    
    def _calculate_max_drawdown(self, returns: List[float]) -> float:
        """최대 낙폭 계산"""
        if not returns:
            return 0.0
        
        try:
            cumulative = 1.0
            peak = 1.0
            max_dd = 0.0
            
            for ret in returns:
                cumulative *= (1 + ret / 100)  # 수익률을 퍼센트로 가정
                if cumulative > peak:
                    peak = cumulative
                drawdown = (peak - cumulative) / peak
                if drawdown > max_dd:
                    max_dd = drawdown
            
            return max_dd * 100  # 퍼센트로 반환
            
        except Exception as e:
            logger.error(f"최대 낙폭 계산 실패: {e}")
            return 0.0
    
    def _calculate_downside_deviation(self, returns: List[float]) -> float:
        """하방 변동성 계산"""
        if not returns:
            return 0.0
        
        try:
            negative_returns = [r for r in returns if r < 0]
            if not negative_returns:
                return 0.0
            
            return statistics.stdev(negative_returns) if len(negative_returns) > 1 else 0.0
            
        except Exception as e:
            logger.error(f"하방 변동성 계산 실패: {e}")
            return 0.0
    
    def _calculate_calmar_ratio(self, returns: List[float]) -> float:
        """칼마 비율 계산 (연환산 수익률 / 최대 낙폭)"""
        if not returns:
            return 0.0
        
        try:
            annual_return = statistics.mean(returns) * 252  # 연환산 (252 거래일)
            max_dd = self._calculate_max_drawdown(returns)
            
            return annual_return / max_dd if max_dd > 0 else 0.0
            
        except Exception as e:
            logger.error(f"칼마 비율 계산 실패: {e}")
            return 0.0
    
    def _generate_recommendations(self, performance_metrics: Dict, cut_analysis: Dict, 
                                sector_performance: Dict, risk_metrics: Dict) -> List[str]:
        """권장사항 생성"""
        recommendations = []
        
        try:
            # 성과 기반 권장사항
            if performance_metrics:
                win_rate = performance_metrics.get('win_rate', 0)
                if win_rate < 50:
                    recommendations.append(f"⚠️ 승률이 {win_rate:.1f}%로 낮습니다. 선택 기준을 재검토하세요.")
                elif win_rate > 70:
                    recommendations.append(f"✅ 승률이 {win_rate:.1f}%로 우수합니다. 현재 전략을 유지하세요.")
                
                sharpe_ratio = performance_metrics.get('sharpe_ratio', 0)
                if sharpe_ratio < 0.5:
                    recommendations.append("⚠️ 샤프 비율이 낮습니다. 리스크 대비 수익률을 개선하세요.")
                elif sharpe_ratio > 1.0:
                    recommendations.append("✅ 샤프 비율이 우수합니다. 현재 리스크 관리가 효과적입니다.")
            
            # 컷라인 기반 권장사항
            if cut_analysis and 'cut_effectiveness' in cut_analysis:
                effectiveness = cut_analysis['cut_effectiveness']
                performance_gap = effectiveness.get('performance_gap', 0)
                
                if performance_gap < 2.0:
                    recommendations.append("⚠️ 컷라인 위아래 성과 차이가 작습니다. 컷라인 조정을 고려하세요.")
                elif performance_gap > 5.0:
                    recommendations.append("✅ 컷라인이 효과적으로 작동하고 있습니다.")
            
            # 섹터 기반 권장사항
            if sector_performance:
                best_sector = max(sector_performance.items(), key=lambda x: x[1].get('mean_return', 0))
                worst_sector = min(sector_performance.items(), key=lambda x: x[1].get('mean_return', 0))
                
                if best_sector[1].get('mean_return', 0) > worst_sector[1].get('mean_return', 0) + 3.0:
                    recommendations.append(f"📈 {best_sector[0]} 섹터가 우수한 성과를 보이고 있습니다.")
                    recommendations.append(f"📉 {worst_sector[0]} 섹터의 선택 기준을 재검토하세요.")
            
            # 리스크 기반 권장사항
            if risk_metrics:
                max_dd = risk_metrics.get('max_drawdown', 0)
                if max_dd > 20:
                    recommendations.append(f"⚠️ 최대 낙폭이 {max_dd:.1f}%로 높습니다. 리스크 관리 강화가 필요합니다.")
                
                volatility = risk_metrics.get('volatility', 0)
                if volatility > 15:
                    recommendations.append(f"⚠️ 변동성이 {volatility:.1f}%로 높습니다. 포트폴리오 분산을 고려하세요.")
            
            # 기본 권장사항
            if not recommendations:
                recommendations.append("📊 데이터가 충분하지 않아 구체적인 권장사항을 제공할 수 없습니다.")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"권장사항 생성 실패: {e}")
            return ["❌ 권장사항 생성 중 오류가 발생했습니다."]
    
    def _save_report(self, report: CalibrationReport):
        """리포트 저장"""
        try:
            # JSON 형태로 저장
            report_data = {
                'report_date': report.report_date,
                'period_days': report.period_days,
                'total_selections': report.total_selections,
                'performance_metrics': report.performance_metrics,
                'cut_analysis': report.cut_analysis,
                'sector_performance': report.sector_performance,
                'risk_metrics': report.risk_metrics,
                'recommendations': report.recommendations
            }
            
            # 파일명 생성
            filename = f"calibration_report_{report.report_date}.json"
            filepath = self.reports_dir / filename
            
            # 저장
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"캘리브레이션 리포트 저장 완료: {filepath}")
            
        except Exception as e:
            logger.error(f"리포트 저장 실패: {e}")
    
    def _create_empty_report(self, days_back: int) -> CalibrationReport:
        """빈 리포트 생성"""
        return CalibrationReport(
            report_date=datetime.now().strftime('%Y-%m-%d'),
            period_days=days_back,
            total_selections=0,
            performance_metrics={},
            cut_analysis={},
            sector_performance={},
            risk_metrics={},
            recommendations=["📊 분석할 데이터가 없습니다."]
        )
    
    def create_report_dashboard(self, report: CalibrationReport) -> go.Figure:
        """리포트 대시보드 생성"""
        # 서브플롯 생성
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                '성과 메트릭',
                '컷라인 효과성',
                '섹터별 성과',
                '리스크 메트릭'
            ),
            specs=[[{"type": "bar"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "bar"}]]
        )
        
        # 1. 성과 메트릭
        if report.performance_metrics:
            metrics = ['평균수익률', '승률', '샤프비율']
            values = [
                report.performance_metrics.get('mean_return', 0),
                report.performance_metrics.get('win_rate', 0),
                report.performance_metrics.get('sharpe_ratio', 0) * 10  # 스케일 조정
            ]
            
            fig.add_trace(
                go.Bar(x=metrics, y=values, name='성과 메트릭'),
                row=1, col=1
            )
        
        # 2. 컷라인 효과성
        if report.cut_analysis and 'cut_effectiveness' in report.cut_analysis:
            effectiveness = report.cut_analysis['cut_effectiveness']
            cut_metrics = ['컷라인 위', '컷라인 아래', '성과차이']
            cut_values = [
                effectiveness.get('above_cut_mean', 0),
                effectiveness.get('below_cut_mean', 0),
                effectiveness.get('performance_gap', 0)
            ]
            
            fig.add_trace(
                go.Bar(x=cut_metrics, y=cut_values, name='컷라인 효과성'),
                row=1, col=2
            )
        
        # 3. 섹터별 성과
        if report.sector_performance:
            sectors = list(report.sector_performance.keys())
            sector_returns = [report.sector_performance[s].get('mean_return', 0) for s in sectors]
            
            fig.add_trace(
                go.Bar(x=sectors, y=sector_returns, name='섹터별 성과'),
                row=2, col=1
            )
        
        # 4. 리스크 메트릭
        if report.risk_metrics:
            risk_metrics = ['변동성', '최대낙폭', '하방변동성']
            risk_values = [
                report.risk_metrics.get('volatility', 0),
                report.risk_metrics.get('max_drawdown', 0),
                report.risk_metrics.get('downside_deviation', 0)
            ]
            
            fig.add_trace(
                go.Bar(x=risk_metrics, y=risk_values, name='리스크 메트릭'),
                row=2, col=2
            )
        
        # 레이아웃 업데이트
        fig.update_layout(
            title_text=f"캘리브레이션 리포트 ({report.report_date})",
            showlegend=False,
            height=800
        )
        
        return fig
    
    def generate_report_summary(self, report: CalibrationReport) -> str:
        """리포트 요약 생성"""
        summary = []
        
        summary.append(f"📊 캘리브레이션 리포트 ({report.report_date})")
        summary.append("=" * 50)
        
        # 기본 정보
        summary.append(f"📈 분석 기간: {report.period_days}일")
        summary.append(f"📊 총 선택 종목: {report.total_selections}개")
        
        # 성과 메트릭
        if report.performance_metrics:
            summary.append(f"\n💰 성과 메트릭:")
            summary.append(f"  • 평균 수익률: {report.performance_metrics.get('mean_return', 0):.2f}%")
            summary.append(f"  • 승률: {report.performance_metrics.get('win_rate', 0):.1f}%")
            summary.append(f"  • 샤프 비율: {report.performance_metrics.get('sharpe_ratio', 0):.2f}")
        
        # 컷라인 분석
        if report.cut_analysis and 'cut_effectiveness' in report.cut_analysis:
            effectiveness = report.cut_analysis['cut_effectiveness']
            summary.append(f"\n🎯 컷라인 효과성:")
            summary.append(f"  • 컷라인 위 평균 수익률: {effectiveness.get('above_cut_mean', 0):.2f}%")
            summary.append(f"  • 컷라인 아래 평균 수익률: {effectiveness.get('below_cut_mean', 0):.2f}%")
            summary.append(f"  • 성과 차이: {effectiveness.get('performance_gap', 0):.2f}%")
        
        # 섹터별 성과
        if report.sector_performance:
            summary.append(f"\n🏢 섹터별 성과:")
            for sector, perf in sorted(report.sector_performance.items(), 
                                     key=lambda x: x[1].get('mean_return', 0), reverse=True):
                summary.append(f"  • {sector}: {perf.get('mean_return', 0):.2f}% (승률: {perf.get('win_rate', 0):.1f}%)")
        
        # 리스크 메트릭
        if report.risk_metrics:
            summary.append(f"\n⚠️ 리스크 메트릭:")
            summary.append(f"  • 변동성: {report.risk_metrics.get('volatility', 0):.2f}%")
            summary.append(f"  • 최대 낙폭: {report.risk_metrics.get('max_drawdown', 0):.2f}%")
            summary.append(f"  • 95% VaR: {report.risk_metrics.get('var_95', 0):.2f}%")
        
        # 권장사항
        if report.recommendations:
            summary.append(f"\n💡 권장사항:")
            for i, rec in enumerate(report.recommendations, 1):
                summary.append(f"  {i}. {rec}")
        
        return "\n".join(summary)


# 사용 예시
if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)
    
    automation = CalibrationReportAutomation()
    
    # 주간 리포트 생성
    report = automation.generate_weekly_report(days_back=7)
    
    # 리포트 요약 출력
    summary = automation.generate_report_summary(report)
    print(summary)
