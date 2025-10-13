#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
점수 캘리브레이션 및 드리프트 모니터링 모듈
월별 점수 분포, 등급 비율, 섹터별 평균점수 추적
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import Counter
import statistics

logger = logging.getLogger(__name__)


class ScoreCalibrationMonitor:
    """점수 캘리브레이션 및 드리프트 모니터"""
    
    def __init__(self, log_dir: str = 'logs/calibration'):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 월별 통계 캐시
        self.monthly_stats = {}
        
        # 목표 등급 분포 (%)
        self.target_distribution = {
            'STRONG_BUY': 10,  # 상위 10%
            'BUY': 20,         # 상위 20~30%
            'HOLD': 40,        # 중간 40%
            'SELL': 30         # 하위 30%
        }
    
    def record_scores(self, results: List[Dict], month: Optional[str] = None):
        """
        분석 결과 점수 기록
        
        Args:
            results: 종목 분석 결과 리스트
            month: 월 식별자 (기본값: 현재 월)
        """
        if not results:
            logger.warning("기록할 결과 없음")
            return
        
        if month is None:
            month = datetime.now().strftime('%Y-%m')
        
        try:
            # 점수 추출
            scores = [r['value_score'] for r in results if 'value_score' in r]
            recommendations = [r['recommendation'] for r in results if 'recommendation' in r]
            sectors = [r.get('sector', '기타') for r in results]
            
            # 통계 계산
            stats = {
                'month': month,
                'timestamp': datetime.now().isoformat(),
                'sample_size': len(results),
                'score_distribution': self._calculate_score_distribution(scores),
                'recommendation_distribution': dict(Counter(recommendations)),
                'sector_distribution': dict(Counter(sectors)),
                'sector_avg_scores': self._calculate_sector_avg_scores(results),
                'quantiles': self._calculate_quantiles(scores),
                'drift_indicators': self._calculate_drift(scores, month)
            }
            
            # 캐시 저장
            self.monthly_stats[month] = stats
            
            # 파일 저장
            log_file = os.path.join(self.log_dir, f'calibration_{month}.json')
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 캘리브레이션 통계 저장: {log_file}")
            
            # 경고 체크
            self._check_alerts(stats)
            
        except Exception as e:
            logger.error(f"점수 기록 실패: {e}")
    
    def _calculate_score_distribution(self, scores: List[float]) -> Dict:
        """점수 분포 계산"""
        if not scores:
            return {}
        
        return {
            'mean': statistics.mean(scores),
            'median': statistics.median(scores),
            'stdev': statistics.stdev(scores) if len(scores) > 1 else 0,
            'min': min(scores),
            'max': max(scores),
            'count': len(scores)
        }
    
    def _calculate_quantiles(self, scores: List[float]) -> Dict:
        """분위수 계산 (10%, 25%, 50%, 75%, 90%)"""
        if not scores:
            return {}
        
        sorted_scores = sorted(scores)
        n = len(sorted_scores)
        
        def quantile(p):
            k = (n - 1) * p
            f = int(k)
            c = k - f
            if f + 1 < n:
                return sorted_scores[f] * (1 - c) + sorted_scores[f + 1] * c
            else:
                return sorted_scores[f]
        
        return {
            'p10': quantile(0.10),
            'p25': quantile(0.25),
            'p50': quantile(0.50),
            'p75': quantile(0.75),
            'p90': quantile(0.90)
        }
    
    def _calculate_sector_avg_scores(self, results: List[Dict]) -> Dict:
        """섹터별 평균 점수"""
        sector_scores = {}
        
        for r in results:
            sector = r.get('sector', '기타')
            score = r.get('value_score', 0)
            
            if sector not in sector_scores:
                sector_scores[sector] = []
            sector_scores[sector].append(score)
        
        return {
            sector: {
                'count': len(scores),
                'mean': statistics.mean(scores),
                'median': statistics.median(scores)
            }
            for sector, scores in sector_scores.items()
        }
    
    def _calculate_drift(self, scores: List[float], current_month: str) -> Dict:
        """드리프트 지표 계산 (전월 대비 변화)"""
        if not scores:
            return {}
        
        current_mean = statistics.mean(scores)
        current_stdev = statistics.stdev(scores) if len(scores) > 1 else 0
        
        # 전월 통계 조회
        prev_stats = self._get_previous_month_stats(current_month)
        
        if not prev_stats:
            return {
                'drift_detected': False,
                'reason': '전월 데이터 없음'
            }
        
        prev_mean = prev_stats.get('score_distribution', {}).get('mean', current_mean)
        prev_stdev = prev_stats.get('score_distribution', {}).get('stdev', current_stdev)
        
        # 드리프트 체크
        mean_drift = abs(current_mean - prev_mean)
        stdev_drift = abs(current_stdev - prev_stdev)
        
        # 임계값: 평균 5점 이상 변화, 표준편차 3점 이상 변화
        drift_detected = mean_drift > 5.0 or stdev_drift > 3.0
        
        return {
            'drift_detected': drift_detected,
            'mean_drift': mean_drift,
            'stdev_drift': stdev_drift,
            'current_mean': current_mean,
            'prev_mean': prev_mean,
            'current_stdev': current_stdev,
            'prev_stdev': prev_stdev
        }
    
    def _get_previous_month_stats(self, current_month: str) -> Optional[Dict]:
        """전월 통계 조회"""
        try:
            # 전월 계산
            year, month = map(int, current_month.split('-'))
            if month == 1:
                prev_year = year - 1
                prev_month = 12
            else:
                prev_year = year
                prev_month = month - 1
            
            prev_month_str = f"{prev_year:04d}-{prev_month:02d}"
            
            # 캐시에서 조회
            if prev_month_str in self.monthly_stats:
                return self.monthly_stats[prev_month_str]
            
            # 파일에서 로드
            log_file = os.path.join(self.log_dir, f'calibration_{prev_month_str}.json')
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            return None
            
        except Exception as e:
            logger.debug(f"전월 통계 조회 실패: {e}")
            return None
    
    def _check_alerts(self, stats: Dict):
        """경고 체크 및 로깅"""
        alerts = []
        
        # 1. 등급 분포 체크
        rec_dist = stats.get('recommendation_distribution', {})
        total = sum(rec_dist.values())
        
        if total > 0:
            for grade, target_pct in self.target_distribution.items():
                actual_count = rec_dist.get(grade, 0)
                actual_pct = (actual_count / total) * 100
                
                # 목표 대비 20% 이상 차이
                if abs(actual_pct - target_pct) > 20:
                    alerts.append(
                        f"등급 {grade} 분포 이상: 목표 {target_pct}%, 실제 {actual_pct:.1f}%"
                    )
        
        # 2. 드리프트 체크
        drift = stats.get('drift_indicators', {})
        if drift.get('drift_detected', False):
            alerts.append(
                f"점수 드리프트 감지: 평균 {drift.get('mean_drift', 0):.1f}점 변화"
            )
        
        # 3. 섹터 편향 체크
        sector_dist = stats.get('sector_distribution', {})
        total_sectors = sum(sector_dist.values())
        
        if total_sectors > 0:
            for sector, count in sector_dist.items():
                pct = (count / total_sectors) * 100
                # 특정 섹터가 50% 이상
                if pct > 50:
                    alerts.append(
                        f"섹터 편향: {sector}가 {pct:.1f}% 차지"
                    )
        
        # 경고 로깅
        if alerts:
            logger.warning("⚠️ 캘리브레이션 경고:")
            for alert in alerts:
                logger.warning(f"  - {alert}")
    
    def get_score_statistics(self, month: Optional[str] = None) -> Optional[Dict]:
        """
        ✅ v2.2.2: 점수 통계 조회 (UI 피드백용)
        
        Args:
            month: 월 식별자 (기본값: 현재 월)
        
        Returns:
            점수 통계 딕셔너리 (분포, 퍼센타일 등)
        """
        if month is None:
            month = datetime.now().strftime('%Y-%m')
        
        # 캐시에서 조회
        stats = self.monthly_stats.get(month)
        
        # 캐시에 없으면 파일에서 로드
        if not stats:
            log_file = os.path.join(self.log_dir, f'calibration_{month}.json')
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        stats = json.load(f)
                        self.monthly_stats[month] = stats
                except Exception as e:
                    logger.debug(f"캘리브레이션 파일 로드 실패: {e}")
                    return None
            else:
                return None
        
        # quantiles를 percentiles 형식으로 변환
        # quantiles: 하위 x% 지점 (예: p75 = 하위 75% 지점)
        # percentiles: 상위 x% 컷오프 (예: p80 = 상위 20% 컷오프, 즉 하위 80% 지점)
        quantiles = stats.get('quantiles', {})
        percentiles = {}
        
        if quantiles:
            # 직접 매핑 (하위 x% = 상위 (100-x)% 컷오프)
            percentiles['p10'] = quantiles.get('p90', 0)  # 상위 10% 컷오프 = 하위 90%
            percentiles['p25'] = quantiles.get('p75', 0)  # 상위 25% 컷오프 = 하위 75%
            percentiles['p50'] = quantiles.get('p50', 0)  # 상위 50% 컷오프 = 하위 50% (중앙값)
            percentiles['p75'] = quantiles.get('p25', 0)  # 상위 75% 컷오프 = 하위 25%
            percentiles['p90'] = quantiles.get('p10', 0)  # 상위 90% 컷오프 = 하위 10%
            
            # 상위 20% 컷오프 = 하위 80% 지점 (p75와 p90 사이 보간)
            q75 = quantiles.get('p75', 0)
            q90 = quantiles.get('p90', 0)
            # p80 = p75 + (p90 - p75) * (80-75)/(90-75)
            percentiles['p80'] = q75 + (q90 - q75) * (80 - 75) / (90 - 75)
            
            # 상위 80% 컷오프 = 하위 20% 지점 (p10과 p25 사이 보간)
            q10 = quantiles.get('p10', 0)
            q25 = quantiles.get('p25', 0)
            percentiles['p20'] = q10 + (q25 - q10) * (20 - 10) / (25 - 10)
        
        return {
            'distribution': stats.get('score_distribution', {}),
            'percentiles': percentiles,
            'quantiles': quantiles,
            'sample_size': stats.get('sample_size', 0),
            'month': month
        }
    
    def suggest_grade_cutoffs(self, scores: List[float], target_dist: Optional[Dict] = None) -> Dict:
        """
        목표 등급 분포에 맞는 점수 컷오프 제안
        
        Args:
            scores: 점수 리스트
            target_dist: 목표 등급 분포 (기본값: self.target_distribution)
        
        Returns:
            {'STRONG_BUY': 120, 'BUY': 105, 'HOLD': 90, 'SELL': 0}
        """
        if not scores:
            return {}
        
        if target_dist is None:
            target_dist = self.target_distribution
        
        sorted_scores = sorted(scores, reverse=True)
        n = len(sorted_scores)
        
        # 누적 비율로 컷오프 계산
        cutoffs = {}
        cumulative = 0
        
        # STRONG_BUY: 상위 10%
        strong_buy_pct = target_dist.get('STRONG_BUY', 10)
        strong_buy_idx = int(n * strong_buy_pct / 100)
        cutoffs['STRONG_BUY'] = sorted_scores[strong_buy_idx] if strong_buy_idx < n else sorted_scores[-1]
        cumulative += strong_buy_pct
        
        # BUY: 상위 10~30%
        buy_pct = target_dist.get('BUY', 20)
        buy_idx = int(n * (cumulative + buy_pct) / 100)
        cutoffs['BUY'] = sorted_scores[buy_idx] if buy_idx < n else sorted_scores[-1]
        cumulative += buy_pct
        
        # HOLD: 상위 30~70%
        hold_pct = target_dist.get('HOLD', 40)
        hold_idx = int(n * (cumulative + hold_pct) / 100)
        cutoffs['HOLD'] = sorted_scores[hold_idx] if hold_idx < n else sorted_scores[-1]
        
        # SELL: 하위 30%
        cutoffs['SELL'] = 0
        
        logger.info(f"✅ 제안된 점수 컷오프: {cutoffs}")
        return cutoffs
    
    def generate_monthly_report(self, month: Optional[str] = None) -> str:
        """
        월별 캘리브레이션 리포트 생성
        
        Args:
            month: 월 식별자 (기본값: 현재 월)
        
        Returns:
            마크다운 형식 리포트
        """
        if month is None:
            month = datetime.now().strftime('%Y-%m')
        
        stats = self.monthly_stats.get(month)
        if not stats:
            # 파일에서 로드 시도
            log_file = os.path.join(self.log_dir, f'calibration_{month}.json')
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
            else:
                return f"# {month} 캘리브레이션 리포트\n\n데이터 없음"
        
        # 리포트 생성
        report = f"""# {month} 캘리브레이션 리포트

## 📊 점수 분포

- **샘플 크기**: {stats['sample_size']}
- **평균**: {stats['score_distribution']['mean']:.1f}
- **중앙값**: {stats['score_distribution']['median']:.1f}
- **표준편차**: {stats['score_distribution']['stdev']:.1f}
- **범위**: {stats['score_distribution']['min']:.1f} ~ {stats['score_distribution']['max']:.1f}

## 🎯 등급 분포

"""
        
        rec_dist = stats.get('recommendation_distribution', {})
        total = sum(rec_dist.values())
        
        for grade in ['STRONG_BUY', 'BUY', 'HOLD', 'SELL']:
            count = rec_dist.get(grade, 0)
            pct = (count / total * 100) if total > 0 else 0
            target_pct = self.target_distribution.get(grade, 0)
            
            report += f"- **{grade}**: {count}개 ({pct:.1f}%) - 목표: {target_pct}%\n"
        
        # 드리프트
        drift = stats.get('drift_indicators', {})
        if drift.get('drift_detected', False):
            report += f"\n## ⚠️ 드리프트 감지\n\n"
            report += f"- 평균 변화: {drift.get('mean_drift', 0):.1f}점\n"
            report += f"- 표준편차 변화: {drift.get('stdev_drift', 0):.1f}점\n"
        
        # 섹터별 평균
        sector_avg = stats.get('sector_avg_scores', {})
        if sector_avg:
            report += f"\n## 🏢 섹터별 평균 점수\n\n"
            for sector, info in sorted(sector_avg.items(), key=lambda x: x[1]['mean'], reverse=True):
                report += f"- **{sector}**: {info['mean']:.1f}점 (중앙값: {info['median']:.1f}, {info['count']}개)\n"
        
        return report


# ===== 사용 예시 =====
if __name__ == "__main__":
    # 모니터 초기화
    monitor = ScoreCalibrationMonitor()
    
    # 가상 결과 생성
    import random
    results = [
        {
            'symbol': f'{i:06d}',
            'name': f'종목{i}',
            'value_score': random.gauss(75, 15),  # 평균 75, 표준편차 15
            'recommendation': random.choice(['STRONG_BUY'] * 1 + ['BUY'] * 2 + ['HOLD'] * 4 + ['SELL'] * 3),
            'sector': random.choice(['제조업', '금융', 'IT', '소비재', '건설'])
        }
        for i in range(100)
    ]
    
    # 점수 기록
    monitor.record_scores(results)
    
    # 컷오프 제안
    scores = [r['value_score'] for r in results]
    cutoffs = monitor.suggest_grade_cutoffs(scores)
    print(f"제안된 컷오프: {cutoffs}")
    
    # 리포트 생성
    report = monitor.generate_monthly_report()
    print(report)

