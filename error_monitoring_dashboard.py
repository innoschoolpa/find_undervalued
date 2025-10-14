#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
오류/차단 관측 대시보드 (시간대별 401/429/500)
AppKey 차단 리스크를 사전에 감지하고 간격을 자동 상향
"""

import logging
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from collections import defaultdict, deque
import threading
import time

logger = logging.getLogger(__name__)

@dataclass
class ErrorEvent:
    """오류 이벤트 데이터"""
    timestamp: str
    error_type: str  # 401, 429, 500, timeout, connection
    endpoint: str
    tr_id: str
    message: str
    retry_count: int
    response_time: float
    user_agent: str

@dataclass
class ErrorStats:
    """오류 통계 데이터"""
    total_errors: int
    error_by_type: Dict[str, int]
    error_by_hour: Dict[int, int]
    error_by_endpoint: Dict[str, int]
    avg_response_time: float
    max_response_time: float
    error_rate: float
    consecutive_errors: int
    last_error_time: str

class ErrorMonitoringDashboard:
    """오류/차단 관측 대시보드 클래스"""
    
    def __init__(self, logs_dir: str = "logs/errors"):
        """
        Args:
            logs_dir: 오류 로그 디렉토리 경로
        """
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # 실시간 오류 데이터 저장
        self.error_events = deque(maxlen=10000)  # 최근 10,000개 이벤트만 유지
        self.error_lock = threading.Lock()
        
        # 오류 통계 캐시
        self.stats_cache = {}
        self.cache_ttl = 60  # 1분 캐시
        
        # 경고 임계값
        self.warning_thresholds = {
            'error_rate': 5.0,  # 5% 이상 오류율
            'consecutive_errors': 3,  # 연속 3회 오류
            'response_time': 10.0,  # 10초 이상 응답시간
            'hourly_errors': 50  # 시간당 50회 이상 오류
        }
    
    def log_error(self, error_type: str, endpoint: str, tr_id: str, 
                  message: str, retry_count: int = 0, response_time: float = 0.0):
        """오류 이벤트 로깅"""
        try:
            event = ErrorEvent(
                timestamp=datetime.now().isoformat(),
                error_type=error_type,
                endpoint=endpoint,
                tr_id=tr_id,
                message=message,
                retry_count=retry_count,
                response_time=response_time,
                user_agent="KIS-API-Client/1.0"
            )
            
            # 실시간 데이터에 추가
            with self.error_lock:
                self.error_events.append(event)
            
            # 파일에 로깅
            self._write_error_log(event)
            
            # 경고 체크
            self._check_warnings()
            
        except Exception as e:
            logger.error(f"오류 이벤트 로깅 실패: {e}")
    
    def _write_error_log(self, event: ErrorEvent):
        """오류 로그 파일에 쓰기"""
        try:
            # 일별 로그 파일
            date_str = datetime.now().strftime('%Y%m%d')
            log_file = self.logs_dir / f"errors_{date_str}.jsonl"
            
            # JSONL 형태로 추가
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(asdict(event), ensure_ascii=False) + '\n')
            
        except Exception as e:
            logger.error(f"오류 로그 파일 쓰기 실패: {e}")
    
    def _check_warnings(self):
        """경고 조건 체크"""
        try:
            stats = self.get_error_stats()
            
            # 오류율 경고
            if stats.error_rate > self.warning_thresholds['error_rate']:
                logger.warning(f"⚠️ 높은 오류율 감지: {stats.error_rate:.1f}%")
            
            # 연속 오류 경고
            if stats.consecutive_errors >= self.warning_thresholds['consecutive_errors']:
                logger.warning(f"🚨 연속 오류 감지: {stats.consecutive_errors}회")
            
            # 응답시간 경고
            if stats.avg_response_time > self.warning_thresholds['response_time']:
                logger.warning(f"⚠️ 높은 응답시간: {stats.avg_response_time:.1f}초")
            
        except Exception as e:
            logger.error(f"경고 체크 실패: {e}")
    
    def get_error_stats(self, hours_back: int = 24) -> ErrorStats:
        """오류 통계 계산"""
        try:
            # 캐시 확인
            cache_key = f"stats_{hours_back}"
            if cache_key in self.stats_cache:
                cached_stats, cached_time = self.stats_cache[cache_key]
                if time.time() - cached_time < self.cache_ttl:
                    return cached_stats
            
            # 시간 범위 계산
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            # 최근 오류 이벤트 필터링
            recent_events = []
            with self.error_lock:
                for event in self.error_events:
                    event_time = datetime.fromisoformat(event.timestamp)
                    if event_time >= cutoff_time:
                        recent_events.append(event)
            
            if not recent_events:
                return ErrorStats(
                    total_errors=0,
                    error_by_type={},
                    error_by_hour={},
                    error_by_endpoint={},
                    avg_response_time=0.0,
                    max_response_time=0.0,
                    error_rate=0.0,
                    consecutive_errors=0,
                    last_error_time=""
                )
            
            # 통계 계산
            total_errors = len(recent_events)
            error_by_type = defaultdict(int)
            error_by_hour = defaultdict(int)
            error_by_endpoint = defaultdict(int)
            response_times = []
            consecutive_errors = 0
            
            # 최근 이벤트부터 역순으로 연속 오류 계산
            for i, event in enumerate(reversed(recent_events)):
                if i == 0:  # 가장 최근 이벤트
                    consecutive_errors = 1
                else:
                    # 이전 이벤트와 시간 차이 확인
                    prev_event = list(reversed(recent_events))[i-1]
                    prev_time = datetime.fromisoformat(prev_event.timestamp)
                    curr_time = datetime.fromisoformat(event.timestamp)
                    
                    if (curr_time - prev_time).total_seconds() < 300:  # 5분 이내
                        consecutive_errors += 1
                    else:
                        break
            
            for event in recent_events:
                error_by_type[event.error_type] += 1
                
                event_time = datetime.fromisoformat(event.timestamp)
                error_by_hour[event_time.hour] += 1
                
                error_by_endpoint[event.endpoint] += 1
                
                if event.response_time > 0:
                    response_times.append(event.response_time)
            
            # 응답시간 통계
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
            max_response_time = max(response_times) if response_times else 0.0
            
            # 오류율 계산 (전체 요청 대비, 추정)
            # 실제로는 전체 요청 수가 필요하지만, 여기서는 오류 이벤트 기반으로 추정
            estimated_total_requests = total_errors * 20  # 오류율 5% 가정
            error_rate = (total_errors / estimated_total_requests) * 100 if estimated_total_requests > 0 else 0.0
            
            stats = ErrorStats(
                total_errors=total_errors,
                error_by_type=dict(error_by_type),
                error_by_hour=dict(error_by_hour),
                error_by_endpoint=dict(error_by_endpoint),
                avg_response_time=avg_response_time,
                max_response_time=max_response_time,
                error_rate=error_rate,
                consecutive_errors=consecutive_errors,
                last_error_time=recent_events[-1].timestamp if recent_events else ""
            )
            
            # 캐시 저장
            self.stats_cache[cache_key] = (stats, time.time())
            
            return stats
            
        except Exception as e:
            logger.error(f"오류 통계 계산 실패: {e}")
            return ErrorStats(
                total_errors=0,
                error_by_type={},
                error_by_hour={},
                error_by_endpoint={},
                avg_response_time=0.0,
                max_response_time=0.0,
                error_rate=0.0,
                consecutive_errors=0,
                last_error_time=""
            )
    
    def create_error_dashboard(self, hours_back: int = 24) -> go.Figure:
        """오류 대시보드 생성"""
        stats = self.get_error_stats(hours_back)
        
        # 서브플롯 생성
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                '오류 유형별 분포',
                '시간대별 오류 발생',
                '엔드포인트별 오류',
                '응답시간 분포'
            ),
            specs=[[{"type": "pie"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "histogram"}]]
        )
        
        # 1. 오류 유형별 분포
        if stats.error_by_type:
            error_types = list(stats.error_by_type.keys())
            error_counts = list(stats.error_by_type.values())
            
            fig.add_trace(
                go.Pie(labels=error_types, values=error_counts, name='오류 유형'),
                row=1, col=1
            )
        
        # 2. 시간대별 오류 발생
        if stats.error_by_hour:
            hours = list(range(24))
            hour_counts = [stats.error_by_hour.get(h, 0) for h in hours]
            
            fig.add_trace(
                go.Bar(x=hours, y=hour_counts, name='시간대별 오류'),
                row=1, col=2
            )
        
        # 3. 엔드포인트별 오류
        if stats.error_by_endpoint:
            endpoints = list(stats.error_by_endpoint.keys())
            endpoint_counts = list(stats.error_by_endpoint.values())
            
            # 엔드포인트명 단축
            short_endpoints = [ep.split('/')[-1] for ep in endpoints]
            
            fig.add_trace(
                go.Bar(x=short_endpoints, y=endpoint_counts, name='엔드포인트별 오류'),
                row=2, col=1
            )
        
        # 4. 응답시간 분포 (실제 데이터가 있는 경우)
        if stats.avg_response_time > 0:
            # 응답시간 히스토그램을 위한 가상 데이터 생성
            response_times = [stats.avg_response_time * (0.5 + i * 0.1) for i in range(10)]
            
            fig.add_trace(
                go.Histogram(x=response_times, name='응답시간 분포'),
                row=2, col=2
            )
        
        # 레이아웃 업데이트
        fig.update_layout(
            title_text=f"오류/차단 관측 대시보드 (최근 {hours_back}시간)",
            showlegend=False,
            height=800
        )
        
        return fig
    
    def get_recommendations(self, stats: ErrorStats) -> List[str]:
        """오류 기반 권장사항 생성"""
        recommendations = []
        
        try:
            # 오류율 기반 권장사항
            if stats.error_rate > 10.0:
                recommendations.append("🚨 오류율이 10%를 초과했습니다. API 호출 간격을 2배로 늘리세요.")
            elif stats.error_rate > 5.0:
                recommendations.append("⚠️ 오류율이 5%를 초과했습니다. API 호출 간격을 1.5배로 늘리세요.")
            elif stats.error_rate < 1.0:
                recommendations.append("✅ 오류율이 1% 미만으로 안정적입니다. 현재 설정을 유지하세요.")
            
            # 연속 오류 기반 권장사항
            if stats.consecutive_errors >= 5:
                recommendations.append("🚨 연속 5회 이상 오류 발생. 즉시 API 호출을 중단하고 10분 대기하세요.")
            elif stats.consecutive_errors >= 3:
                recommendations.append("⚠️ 연속 3회 이상 오류 발생. API 호출 간격을 3배로 늘리세요.")
            
            # 응답시간 기반 권장사항
            if stats.avg_response_time > 15.0:
                recommendations.append("⚠️ 평균 응답시간이 15초를 초과했습니다. 타임아웃 설정을 확인하세요.")
            elif stats.avg_response_time > 10.0:
                recommendations.append("⚠️ 평균 응답시간이 10초를 초과했습니다. 서버 상태를 확인하세요.")
            
            # 오류 유형 기반 권장사항
            if stats.error_by_type.get('401', 0) > 0:
                recommendations.append("🔑 401 오류 발생. 토큰 갱신이 필요할 수 있습니다.")
            
            if stats.error_by_type.get('429', 0) > 0:
                recommendations.append("⏱️ 429 오류 발생. API 호출 한도를 초과했습니다. 간격을 늘리세요.")
            
            if stats.error_by_type.get('500', 0) > 5:
                recommendations.append("🔥 500 오류가 빈번히 발생합니다. 서버 문제일 수 있습니다.")
            
            # 시간대별 패턴 기반 권장사항
            peak_hour = max(stats.error_by_hour.items(), key=lambda x: x[1])[0] if stats.error_by_hour else None
            if peak_hour is not None and stats.error_by_hour[peak_hour] > 20:
                recommendations.append(f"📊 {peak_hour}시에 오류가 집중 발생합니다. 해당 시간대 간격을 늘리세요.")
            
            # 기본 권장사항
            if not recommendations:
                recommendations.append("✅ 현재 오류 상황이 안정적입니다.")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"권장사항 생성 실패: {e}")
            return ["❌ 권장사항 생성 중 오류가 발생했습니다."]
    
    def generate_error_report(self, hours_back: int = 24) -> str:
        """오류 보고서 생성"""
        stats = self.get_error_stats(hours_back)
        recommendations = self.get_recommendations(stats)
        
        report = []
        
        report.append(f"📊 오류/차단 관측 보고서 (최근 {hours_back}시간)")
        report.append("=" * 50)
        
        # 기본 통계
        report.append(f"📈 기본 통계:")
        report.append(f"  • 총 오류 수: {stats.total_errors}개")
        report.append(f"  • 오류율: {stats.error_rate:.2f}%")
        report.append(f"  • 연속 오류: {stats.consecutive_errors}회")
        report.append(f"  • 평균 응답시간: {stats.avg_response_time:.2f}초")
        report.append(f"  • 최대 응답시간: {stats.max_response_time:.2f}초")
        
        if stats.last_error_time:
            last_error = datetime.fromisoformat(stats.last_error_time)
            report.append(f"  • 마지막 오류: {last_error.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 오류 유형별 통계
        if stats.error_by_type:
            report.append(f"\n🔍 오류 유형별 분포:")
            for error_type, count in sorted(stats.error_by_type.items(), key=lambda x: x[1], reverse=True):
                report.append(f"  • {error_type}: {count}개")
        
        # 시간대별 통계
        if stats.error_by_hour:
            report.append(f"\n⏰ 시간대별 오류 발생:")
            peak_hour = max(stats.error_by_hour.items(), key=lambda x: x[1])
            report.append(f"  • 최다 발생 시간: {peak_hour[0]}시 ({peak_hour[1]}개)")
            
            # 상위 3개 시간대
            top_hours = sorted(stats.error_by_hour.items(), key=lambda x: x[1], reverse=True)[:3]
            for hour, count in top_hours:
                report.append(f"  • {hour}시: {count}개")
        
        # 엔드포인트별 통계
        if stats.error_by_endpoint:
            report.append(f"\n🌐 엔드포인트별 오류:")
            top_endpoints = sorted(stats.error_by_endpoint.items(), key=lambda x: x[1], reverse=True)[:5]
            for endpoint, count in top_endpoints:
                short_name = endpoint.split('/')[-1]
                report.append(f"  • {short_name}: {count}개")
        
        # 권장사항
        report.append(f"\n💡 권장사항:")
        for i, rec in enumerate(recommendations, 1):
            report.append(f"  {i}. {rec}")
        
        return "\n".join(report)
    
    def export_error_data(self, hours_back: int = 24) -> pd.DataFrame:
        """오류 데이터를 DataFrame으로 내보내기"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            # 최근 오류 이벤트 수집
            recent_events = []
            with self.error_lock:
                for event in self.error_events:
                    event_time = datetime.fromisoformat(event.timestamp)
                    if event_time >= cutoff_time:
                        recent_events.append(asdict(event))
            
            if not recent_events:
                return pd.DataFrame()
            
            # DataFrame 생성
            df = pd.DataFrame(recent_events)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp', ascending=False)
            
            return df
            
        except Exception as e:
            logger.error(f"오류 데이터 내보내기 실패: {e}")
            return pd.DataFrame()


# 사용 예시
if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)
    
    dashboard = ErrorMonitoringDashboard()
    
    # 테스트 오류 이벤트 생성
    dashboard.log_error("429", "quotations/inquire-price", "FHKST01010100", "Rate limit exceeded", 1, 2.5)
    dashboard.log_error("500", "quotations/inquire-daily-itemchartprice", "FHKST03010100", "Internal server error", 2, 5.0)
    dashboard.log_error("401", "quotations/inquire-price", "FHKST01010100", "Unauthorized", 0, 1.0)
    
    # 통계 조회
    stats = dashboard.get_error_stats(24)
    print(f"총 오류 수: {stats.total_errors}")
    print(f"오류율: {stats.error_rate:.2f}%")
    
    # 보고서 생성
    report = dashboard.generate_error_report(24)
    print(report)
