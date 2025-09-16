#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
병렬 처리 유틸리티 모듈
KIS OpenAPI TPS 제한을 고려한 안전한 병렬 처리 지원
"""

import time
import queue
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable, Optional
from rich.console import Console
from rich.progress import Progress

console = Console()

class TPSRateLimiter:
    """KIS OpenAPI TPS 제한(초당 10건)을 고려한 레이트리미터"""
    
    def __init__(self, max_tps: int = 8):  # 안전 마진을 위해 8로 설정
        self.max_tps = max_tps
        self.requests = queue.Queue()
        self.lock = Lock()
    
    def acquire(self):
        """요청 허가를 받습니다."""
        with self.lock:
            now = time.time()
            
            # 1초 이전의 요청들을 제거
            while not self.requests.empty():
                try:
                    request_time = self.requests.get_nowait()
                    if now - request_time < 1.0:
                        self.requests.put(request_time)
                        break
                except queue.Empty:
                    break
            
            # TPS 제한 확인
            if self.requests.qsize() >= self.max_tps:
                # 가장 오래된 요청이 1초가 지날 때까지 대기
                oldest_request = self.requests.get()
                sleep_time = 1.0 - (now - oldest_request)
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            # 현재 요청 기록
            self.requests.put(time.time())

# 전역 레이트리미터 인스턴스
rate_limiter = TPSRateLimiter(max_tps=8)

def parallel_analyze_stocks(
    stocks_data: List[Dict[str, Any]], 
    analysis_func: Callable,
    max_workers: int = 3,
    show_progress: bool = True,
    progress_description: str = "병렬 분석 진행 중..."
) -> List[Dict[str, Any]]:
    """
    종목들을 병렬로 분석합니다.
    
    Args:
        stocks_data: 분석할 종목 데이터 리스트
        analysis_func: 분석 함수 (stock_data, *args) -> result
        max_workers: 최대 워커 수
        show_progress: 진행률 표시 여부
        progress_description: 진행률 설명
    
    Returns:
        분석 결과 리스트
    """
    results = []
    start_time = time.time()
    
    if show_progress:
        with Progress() as progress:
            task = progress.add_task(progress_description, total=len(stocks_data))
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 각 종목에 대한 Future 생성
                future_to_stock = {}
                for i, stock_data in enumerate(stocks_data):
                    future = executor.submit(analysis_func, stock_data)
                    future_to_stock[future] = (i, stock_data)
                
                # 완료된 작업들을 처리
                for future in as_completed(future_to_stock):
                    i, stock_data = future_to_stock[future]
                    try:
                        result = future.result()
                        results.append(result)
                        progress.update(task, advance=1)
                    except Exception as e:
                        console.print(f"❌ {stock_data.get('name', 'Unknown')} 분석 실패: {e}")
                        results.append({
                            'error': str(e),
                            'stock_data': stock_data
                        })
                        progress.update(task, advance=1)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 각 종목에 대한 Future 생성
            future_to_stock = {}
            for i, stock_data in enumerate(stocks_data):
                future = executor.submit(analysis_func, stock_data)
                future_to_stock[future] = (i, stock_data)
            
            # 완료된 작업들을 처리
            for future in as_completed(future_to_stock):
                i, stock_data = future_to_stock[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    console.print(f"❌ {stock_data.get('name', 'Unknown')} 분석 실패: {e}")
                    results.append({
                        'error': str(e),
                        'stock_data': stock_data
                    })
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # 성능 통계
    success_count = len([r for r in results if 'error' not in r])
    error_count = len(results) - success_count
    
    console.print(f"✅ 병렬 분석 완료: 성공 {success_count}개, 실패 {error_count}개")
    console.print(f"⏱️ 총 소요시간: {total_time:.1f}초")
    console.print(f"⚡ 평균 처리속도: {len(results)/total_time:.2f}종목/초")
    
    return results

def parallel_analyze_with_retry(
    stocks_data: List[Dict[str, Any]], 
    analysis_func: Callable,
    max_workers: int = 3,
    max_retries: int = 2,
    retry_delay: float = 1.0,
    show_progress: bool = True,
    progress_description: str = "병렬 분석 진행 중..."
) -> List[Dict[str, Any]]:
    """
    재시도 로직이 포함된 병렬 분석을 수행합니다.
    
    Args:
        stocks_data: 분석할 종목 데이터 리스트
        analysis_func: 분석 함수 (stock_data, *args) -> result
        max_workers: 최대 워커 수
        max_retries: 최대 재시도 횟수
        retry_delay: 재시도 간 지연 시간
        show_progress: 진행률 표시 여부
        progress_description: 진행률 설명
    
    Returns:
        분석 결과 리스트
    """
    def analyze_with_retry(stock_data):
        """재시도 로직이 포함된 분석 함수"""
        for attempt in range(max_retries + 1):
            try:
                # TPS 제한 적용
                rate_limiter.acquire()
                result = analysis_func(stock_data)
                return result
            except Exception as e:
                if attempt < max_retries:
                    console.print(f"⚠️ {stock_data.get('name', 'Unknown')} 재시도 중... ({attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    raise e
    
    return parallel_analyze_stocks(
        stocks_data, 
        analyze_with_retry, 
        max_workers, 
        show_progress, 
        progress_description
    )

def batch_parallel_analyze(
    stocks_data: List[Dict[str, Any]], 
    analysis_func: Callable,
    batch_size: int = 10,
    max_workers: int = 3,
    show_progress: bool = True,
    progress_description: str = "배치 병렬 분석 진행 중..."
) -> List[Dict[str, Any]]:
    """
    배치 단위로 병렬 분석을 수행합니다.
    
    Args:
        stocks_data: 분석할 종목 데이터 리스트
        analysis_func: 분석 함수 (stock_data, *args) -> result
        batch_size: 배치 크기
        max_workers: 최대 워커 수
        show_progress: 진행률 표시 여부
        progress_description: 진행률 설명
    
    Returns:
        분석 결과 리스트
    """
    all_results = []
    total_batches = (len(stocks_data) + batch_size - 1) // batch_size
    
    console.print(f"📦 배치 병렬 분석 시작: {total_batches}개 배치, 배치당 {batch_size}개 종목")
    
    for batch_idx in range(0, len(stocks_data), batch_size):
        batch_data = stocks_data[batch_idx:batch_idx + batch_size]
        batch_num = batch_idx // batch_size + 1
        
        console.print(f"\n🔄 배치 {batch_num}/{total_batches} 처리 중... ({len(batch_data)}개 종목)")
        
        batch_results = parallel_analyze_stocks(
            batch_data,
            analysis_func,
            max_workers,
            show_progress,
            f"배치 {batch_num}/{total_batches} - {progress_description}"
        )
        
        all_results.extend(batch_results)
        
        # 배치 간 대기 (API 서버 부하 방지)
        if batch_idx + batch_size < len(stocks_data):
            console.print(f"⏳ 다음 배치까지 대기 중...")
            time.sleep(2.0)
    
    console.print(f"\n✅ 전체 배치 분석 완료: {len(all_results)}개 종목")
    return all_results

def get_optimal_worker_count(total_tasks: int, max_workers: int = 5) -> int:
    """
    작업 수에 따른 최적 워커 수를 계산합니다.
    
    Args:
        total_tasks: 전체 작업 수
        max_workers: 최대 워커 수
    
    Returns:
        최적 워커 수
    """
    # TPS 제한(초당 8건)을 고려한 최적 워커 수 계산
    if total_tasks <= 5:
        return min(2, max_workers)
    elif total_tasks <= 20:
        return min(3, max_workers)
    elif total_tasks <= 50:
        return min(4, max_workers)
    else:
        return min(5, max_workers)

def analyze_performance_metrics(
    results: List[Dict[str, Any]], 
    expected_sequential_time: float = None
) -> Dict[str, Any]:
    """
    병렬 처리 성능 메트릭을 분석합니다.
    
    Args:
        results: 분석 결과 리스트
        expected_sequential_time: 예상 순차 처리 시간
    
    Returns:
        성능 메트릭 딕셔너리
    """
    success_count = len([r for r in results if 'error' not in r])
    error_count = len(results) - success_count
    
    metrics = {
        'total_tasks': len(results),
        'success_count': success_count,
        'error_count': error_count,
        'success_rate': success_count / len(results) if results else 0,
        'error_rate': error_count / len(results) if results else 0
    }
    
    if expected_sequential_time:
        # 실제 처리 시간은 호출하는 쪽에서 측정해야 함
        metrics['expected_sequential_time'] = expected_sequential_time
    
    return metrics
