# performance_monitor.py
"""
성능 모니터링 및 통계 수집 모듈
- 실시간 성능 모니터링
- 메트릭 수집 및 분석
- 성능 리포트 생성
- 알림 시스템
"""

import time
import threading
import logging
from typing import Dict, List, Any, Optional, Callable
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """성능 메트릭 데이터 클래스"""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceAlert:
    """성능 알림 데이터 클래스"""
    metric_name: str
    threshold: float
    current_value: float
    severity: str
    timestamp: float = field(default_factory=time.time)
    message: str = ""

class PerformanceMonitor:
    """성능 모니터링 클래스"""
    
    def __init__(self, max_metrics: int = 10000, alert_thresholds: Dict[str, float] = None):
        self.max_metrics = max_metrics
        self.alert_thresholds = alert_thresholds or {
            'response_time': 5.0,  # 5초
            'memory_usage': 1000.0,  # 1GB
            'error_rate': 0.1,  # 10%
            'cpu_usage': 80.0  # 80%
        }
        
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_metrics))
        self._alerts: List[PerformanceAlert] = []
        self._lock = threading.RLock()
        self._start_time = time.time()
        
        # 통계 수집
        self._stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_response_time': 0.0,
            'peak_memory_usage': 0.0,
            'peak_cpu_usage': 0.0
        }
    
    def record_metric(self, name: str, value: float, metadata: Dict[str, Any] = None):
        """메트릭 기록"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            metadata=metadata or {}
        )
        
        with self._lock:
            self._metrics[name].append(metric)
            
            # 통계 업데이트
            if name == 'response_time':
                self._stats['total_response_time'] += value
            elif name == 'memory_usage':
                self._stats['peak_memory_usage'] = max(self._stats['peak_memory_usage'], value)
            elif name == 'cpu_usage':
                self._stats['peak_cpu_usage'] = max(self._stats['peak_cpu_usage'], value)
            
            # 알림 체크
            self._check_alerts(name, value)
    
    def record_request(self, success: bool, response_time: float = None):
        """요청 기록"""
        with self._lock:
            self._stats['total_requests'] += 1
            if success:
                self._stats['successful_requests'] += 1
            else:
                self._stats['failed_requests'] += 1
            
            if response_time is not None:
                self.record_metric('response_time', response_time)
    
    def _check_alerts(self, metric_name: str, value: float):
        """알림 체크"""
        if metric_name in self.alert_thresholds:
            threshold = self.alert_thresholds[metric_name]
            if value > threshold:
                severity = 'critical' if value > threshold * 2 else 'warning'
                alert = PerformanceAlert(
                    metric_name=metric_name,
                    threshold=threshold,
                    current_value=value,
                    severity=severity,
                    message=f"{metric_name} exceeded threshold: {value:.2f} > {threshold:.2f}"
                )
                self._alerts.append(alert)
                logger.warning(f"Performance alert: {alert.message}")
    
    def get_metrics(self, name: str, time_window: float = None) -> List[PerformanceMetric]:
        """메트릭 조회"""
        with self._lock:
            metrics = list(self._metrics[name])
            
            if time_window:
                cutoff_time = time.time() - time_window
                metrics = [m for m in metrics if m.timestamp >= cutoff_time]
            
            return metrics
    
    def get_statistics(self, name: str, time_window: float = None) -> Dict[str, float]:
        """통계 조회"""
        metrics = self.get_metrics(name, time_window)
        
        if not metrics:
            return {}
        
        values = [m.value for m in metrics]
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'median': sorted(values)[len(values) // 2],
            'p95': sorted(values)[int(len(values) * 0.95)],
            'p99': sorted(values)[int(len(values) * 0.99)]
        }
    
    def get_overall_stats(self) -> Dict[str, Any]:
        """전체 통계 조회"""
        with self._lock:
            uptime = time.time() - self._start_time
            
            success_rate = 0.0
            if self._stats['total_requests'] > 0:
                success_rate = self._stats['successful_requests'] / self._stats['total_requests']
            
            avg_response_time = 0.0
            if self._stats['successful_requests'] > 0:
                avg_response_time = self._stats['total_response_time'] / self._stats['successful_requests']
            
            return {
                'uptime': uptime,
                'total_requests': self._stats['total_requests'],
                'successful_requests': self._stats['successful_requests'],
                'failed_requests': self._stats['failed_requests'],
                'success_rate': success_rate,
                'avg_response_time': avg_response_time,
                'peak_memory_usage': self._stats['peak_memory_usage'],
                'peak_cpu_usage': self._stats['peak_cpu_usage'],
                'active_alerts': len([a for a in self._alerts if a.timestamp > time.time() - 3600])  # 1시간 내 알림
            }
    
    def get_alerts(self, severity: str = None, time_window: float = 3600) -> List[PerformanceAlert]:
        """알림 조회"""
        with self._lock:
            cutoff_time = time.time() - time_window
            alerts = [a for a in self._alerts if a.timestamp >= cutoff_time]
            
            if severity:
                alerts = [a for a in alerts if a.severity == severity]
            
            return alerts
    
    def clear_old_data(self, max_age: float = 86400):  # 24시간
        """오래된 데이터 정리"""
        with self._lock:
            cutoff_time = time.time() - max_age
            
            for name in list(self._metrics.keys()):
                metrics = self._metrics[name]
                # deque는 자동으로 오래된 항목을 제거하므로 별도 정리 불필요
                pass
            
            # 오래된 알림 제거
            self._alerts = [a for a in self._alerts if a.timestamp >= cutoff_time]
    
    def export_report(self, filepath: str = None) -> str:
        """성능 리포트 생성"""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"performance_report_{timestamp}.json"
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_stats': self.get_overall_stats(),
            'metrics': {},
            'alerts': [
                {
                    'metric_name': a.metric_name,
                    'threshold': a.threshold,
                    'current_value': a.current_value,
                    'severity': a.severity,
                    'timestamp': a.timestamp,
                    'message': a.message
                }
                for a in self.get_alerts()
            ]
        }
        
        # 주요 메트릭들의 통계 추가
        for metric_name in ['response_time', 'memory_usage', 'cpu_usage', 'error_rate']:
            if metric_name in self._metrics:
                report['metrics'][metric_name] = self.get_statistics(metric_name)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Performance report exported to {filepath}")
        return filepath

class PerformanceProfiler:
    """성능 프로파일러"""
    
    def __init__(self, monitor: PerformanceMonitor = None):
        self.monitor = monitor or PerformanceMonitor()
        self._active_profiles = {}
    
    def start_profile(self, name: str) -> str:
        """프로파일 시작"""
        profile_id = f"{name}_{int(time.time() * 1000)}"
        self._active_profiles[profile_id] = {
            'name': name,
            'start_time': time.time(),
            'start_memory': self._get_memory_usage()
        }
        return profile_id
    
    def end_profile(self, profile_id: str, metadata: Dict[str, Any] = None):
        """프로파일 종료"""
        if profile_id not in self._active_profiles:
            logger.warning(f"Profile {profile_id} not found")
            return
        
        profile = self._active_profiles.pop(profile_id)
        duration = time.time() - profile['start_time']
        end_memory = self._get_memory_usage()
        memory_delta = end_memory - profile['start_memory']
        
        # 메트릭 기록
        self.monitor.record_metric('profile_duration', duration, {
            'profile_name': profile['name'],
            'memory_delta': memory_delta,
            **(metadata or {})
        })
        
        if memory_delta > 0:
            self.monitor.record_metric('profile_memory_usage', memory_delta, {
                'profile_name': profile['name']
            })
    
    def _get_memory_usage(self) -> float:
        """메모리 사용량 조회 (MB)"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
    
    def profile_function(self, name: str = None):
        """함수 프로파일링 데코레이터"""
        def decorator(func: Callable) -> Callable:
            profile_name = name or f"{func.__module__}.{func.__name__}"
            
            def wrapper(*args, **kwargs):
                profile_id = self.start_profile(profile_name)
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    self.end_profile(profile_id)
            
            return wrapper
        return decorator

# 전역 인스턴스
global_monitor = PerformanceMonitor()
global_profiler = PerformanceProfiler(global_monitor)

# 편의 함수들
def record_metric(name: str, value: float, metadata: Dict[str, Any] = None):
    """메트릭 기록"""
    global_monitor.record_metric(name, value, metadata)

def record_request(success: bool, response_time: float = None):
    """요청 기록"""
    global_monitor.record_request(success, response_time)

def get_performance_stats(metric_name: str = None, time_window: float = None) -> Dict[str, Any]:
    """성능 통계 조회"""
    if metric_name:
        return global_monitor.get_statistics(metric_name, time_window)
    else:
        return global_monitor.get_overall_stats()

def get_alerts(severity: str = None, time_window: float = 3600) -> List[PerformanceAlert]:
    """알림 조회"""
    return global_monitor.get_alerts(severity, time_window)

def export_performance_report(filepath: str = None) -> str:
    """성능 리포트 생성"""
    return global_monitor.export_report(filepath)

def profile_function(name: str = None):
    """함수 프로파일링 데코레이터"""
    return global_profiler.profile_function(name)

