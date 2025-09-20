#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
간단한 최적 종목 수 찾기 시스템
- 기존 통합 분석 시스템 활용
- 다양한 종목 수별 성과 비교
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel

# 프로젝트 모듈 임포트
from enhanced_integrated_analyzer import EnhancedIntegratedAnalyzer

app = typer.Typer()
console = Console()

class SimpleCountOptimizer:
    """간단한 최적 종목 수 찾기 클래스"""
    
    def __init__(self):
        self.analyzer = EnhancedIntegratedAnalyzer()
        self.results = []
    
    def run_count_analysis(self, 
                          count_range: List[int] = [5, 10, 15, 20, 25, 30, 35, 40, 45],
                          min_market_cap: float = 1000,
                          min_score: float = 50) -> List[Dict]:
        """다양한 종목 수별 분석 수행"""
        
        console.print("🔍 [bold green]최적 종목 수 찾기 분석 시작[/bold green]")
        console.print("=" * 60)
        
        console.print(f"🎯 테스트할 종목 수: {count_range}")
        console.print(f"💰 최소 시가총액: {min_market_cap:,}억원")
        console.print(f"📊 최소 점수: {min_score}점")
        console.print()
        
        # 시가총액 상위 종목 조회 (최대 개수만큼)
        max_count = max(count_range)
        top_stocks = self.analyzer.get_top_market_cap_stocks(
            count=max_count * 2,
            min_market_cap=min_market_cap
        )
        
        if not top_stocks:
            console.print("[red]❌ 조건에 맞는 종목을 찾을 수 없습니다.[/red]")
            return []
        
        console.print(f"✅ 분석 대상 종목 {len(top_stocks)}개 확보")
        console.print()
        
        # 각 종목 수별 분석 수행
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("종목 수별 분석 진행", total=len(count_range))
            
            for i, count in enumerate(count_range):
                progress.update(task, description=f"종목 수 {count}개 분석 중...")
                
                try:
                    # 상위 count개 종목 선택
                    symbols = [stock['symbol'] for stock in top_stocks[:count]]
                    
                    # 통합 분석 수행
                    result = self._run_single_analysis(symbols, min_score)
                    
                    if result:
                        result['count'] = count
                        result['symbols_count'] = len(symbols)
                        self.results.append(result)
                        
                        console.print(f"✅ 종목 수 {count}개: 평균 점수 {result['avg_score']:.1f}, 상위 종목 {result['high_score_count']}개")
                    else:
                        console.print(f"❌ 종목 수 {count}개: 분석 실패")
                    
                except Exception as e:
                    console.print(f"❌ 종목 수 {count}개: 오류 - {e}")
                
                progress.advance(task)
                time.sleep(2)  # API 제한 고려
        
        return self.results
    
    def _run_single_analysis(self, symbols: List[str], min_score: float) -> Optional[Dict]:
        """단일 분석 수행"""
        
        try:
            # 통합 분석 수행
            analysis_results = []
            
            for symbol in symbols:
                try:
                    # 종목 정보 조회
                    stock_info = self.analyzer.get_stock_info(symbol)
                    if not stock_info:
                        continue
                    
                    # 통합 분석 수행
                    result = self.analyzer.analyze_single_stock_safe_enhanced(
                        symbol=symbol,
                        name=stock_info.get('name', ''),
                        analyzer=self.analyzer,
                        days_back=30
                    )
                    
                    if result and result.get('enhanced_score', 0) >= min_score:
                        analysis_results.append(result)
                        
                except Exception as e:
                    continue
            
            if not analysis_results:
                return None
            
            # 결과 집계
            scores = [r.get('enhanced_score', 0) for r in analysis_results]
            high_score_count = len([s for s in scores if s >= 70])
            
            return {
                'total_analyzed': len(analysis_results),
                'avg_score': sum(scores) / len(scores) if scores else 0,
                'max_score': max(scores) if scores else 0,
                'min_score': min(scores) if scores else 0,
                'high_score_count': high_score_count,
                'high_score_ratio': high_score_count / len(analysis_results) if analysis_results else 0,
                'analysis_results': analysis_results
            }
            
        except Exception as e:
            console.print(f"분석 오류: {e}")
        
        return None
    
    def analyze_results(self) -> Dict[str, Any]:
        """분석 결과 분석"""
        
        if not self.results:
            return {}
        
        # 최적 지점 찾기
        analysis = {
            'total_tests': len(self.results),
            'count_range': [r['count'] for r in self.results],
            'max_avg_score_count': max(self.results, key=lambda x: x['avg_score'])['count'],
            'max_avg_score': max(r['avg_score'] for r in self.results),
            'max_high_score_count': max(self.results, key=lambda x: x['high_score_count'])['count'],
            'max_high_score_count_value': max(r['high_score_count'] for r in self.results),
            'max_high_score_ratio_count': max(self.results, key=lambda x: x['high_score_ratio'])['count'],
            'max_high_score_ratio': max(r['high_score_ratio'] for r in self.results),
            'results': self.results
        }
        
        return analysis
    
    def display_results(self, analysis: Dict[str, Any]):
        """결과 표시"""
        
        if not analysis:
            console.print("[red]❌ 분석할 결과가 없습니다.[/red]")
            return
        
        console.print("\n🎯 [bold green]최적 종목 수 분석 결과[/bold green]")
        console.print("=" * 60)
        
        # 요약 테이블
        summary_table = Table(title="종목 수별 성과 요약")
        summary_table.add_column("종목 수", style="cyan", justify="center")
        summary_table.add_column("분석 종목", style="blue", justify="center")
        summary_table.add_column("평균 점수", style="green", justify="right")
        summary_table.add_column("최고 점수", style="yellow", justify="right")
        summary_table.add_column("고점수 종목", style="magenta", justify="center")
        summary_table.add_column("고점수 비율", style="red", justify="right")
        
        for result in analysis['results']:
            summary_table.add_row(
                str(result['count']),
                str(result['total_analyzed']),
                f"{result['avg_score']:.1f}",
                f"{result['max_score']:.1f}",
                f"{result['high_score_count']}개",
                f"{result['high_score_ratio']:.1%}"
            )
        
        console.print(summary_table)
        
        # 최적 지점 분석
        console.print("\n🏆 [bold yellow]최적 지점 분석[/bold yellow]")
        
        optimal_panel = Panel(
            f"""📊 최고 평균 점수: {analysis['max_avg_score_count']}종목 ({analysis['max_avg_score']:.1f}점)
🎯 최다 고점수 종목: {analysis['max_high_score_count']}종목 ({analysis['max_high_score_count_value']}개)
📈 최고 고점수 비율: {analysis['max_high_score_ratio_count']}종목 ({analysis['max_high_score_ratio']:.1%})

💡 권장 종목 수: {analysis['max_avg_score_count']}개 (최고 평균 점수 달성)""",
            title="최적화 결과",
            border_style="green"
        )
        
        console.print(optimal_panel)
    
    def save_results(self, analysis: Dict[str, Any], filename: str = None):
        """결과 저장"""
        
        if not filename:
            timestamp = int(time.time())
            filename = f"simple_count_analysis_{timestamp}.json"
        
        # 결과 저장
        save_data = {
            'timestamp': datetime.now().isoformat(),
            'analysis': analysis,
            'method': 'simple_count_optimizer'
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        console.print(f"💾 결과가 {filename}에 저장되었습니다.")
        return filename

@app.command()
def find_optimal_count(
    count_range: str = typer.Option("5,10,15,20,25,30,35,40,45", "--counts", "-c", 
                                   help="테스트할 종목 수 범위 (쉼표로 구분)"),
    min_market_cap: float = typer.Option(1000, "--min-market-cap", 
                                        help="최소 시가총액 (억원)"),
    min_score: float = typer.Option(50, "--min-score", 
                                   help="최소 점수 임계값"),
    save_results: bool = typer.Option(True, "--save", help="결과 저장 여부")
):
    """최적 종목 수 찾기 (간단 버전)"""
    
    # 종목 수 범위 파싱
    try:
        count_list = [int(x.strip()) for x in count_range.split(',')]
        count_list = sorted(count_list)
    except ValueError:
        console.print("[red]❌ 잘못된 종목 수 범위 형식입니다.[/red]")
        return
    
    # 최적화 실행
    optimizer = SimpleCountOptimizer()
    
    # 분석 수행
    results = optimizer.run_count_analysis(
        count_range=count_list,
        min_market_cap=min_market_cap,
        min_score=min_score
    )
    
    if not results:
        console.print("[red]❌ 분석 결과가 없습니다.[/red]")
        return
    
    # 결과 분석
    analysis = optimizer.analyze_results()
    
    # 결과 표시
    optimizer.display_results(analysis)
    
    # 결과 저장
    if save_results:
        optimizer.save_results(analysis)

if __name__ == "__main__":
    app()


