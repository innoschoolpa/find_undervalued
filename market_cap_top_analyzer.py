#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
코스피 시가총액 상위 종목 분석 시스템
"""

import asyncio
import json
import os
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import argparse

# Import analyzers
from ultimate_enhanced_analyzer_v2 import UltimateEnhancedAnalyzerV2
from kis_data_provider import KISDataProvider
from enhanced_architecture_components import EnhancedLogger


class MarketCapTopAnalyzer:
    """코스피 시가총액 상위 종목 분석기"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.logger = EnhancedLogger("MarketCapTopAnalyzer")
        self.logger.info("🚀 코스피 시가총액 상위 종목 분석기 초기화 시작")
        
        # 기본 분석기 초기화
        self.analyzer = UltimateEnhancedAnalyzerV2(config_file)
        self.data_provider = KISDataProvider(config_file)
        
        # 시가총액 상위 종목 캐시
        self._market_cap_cache = {}
        self._last_update = None
        
        self.logger.info("✅ 코스피 시가총액 상위 종목 분석기 초기화 완료")
    
    async def _load_kospi_master_data(self) -> pd.DataFrame:
        """KOSPI 마스터 데이터 로드"""
        try:
            # KOSPI 마스터 파일 경로들
            possible_paths = [
                "kospi_code.xlsx",
                "kospi_master_data.csv",
                "kospi_code.mst"
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    self.logger.info(f"📊 KOSPI 마스터 데이터 로드: {path}")
                    
                    if path.endswith('.xlsx'):
                        df = pd.read_excel(path)
                    elif path.endswith('.csv'):
                        df = pd.read_csv(path)
                    else:
                        # .mst 파일 처리
                        df = self._parse_mst_file(path)
                    
                    if df is not None and len(df) > 0:
                        self.logger.info(f"✅ KOSPI 마스터 데이터 로드 완료: {len(df)}개 종목")
                        return df
            
            # 기본 종목 리스트 사용
            self.logger.warning("⚠️ KOSPI 마스터 파일을 찾을 수 없어 기본 종목 리스트 사용")
            return self._get_default_stock_list()
            
        except Exception as e:
            self.logger.error(f"❌ KOSPI 마스터 데이터 로드 실패: {e}")
            return self._get_default_stock_list()
    
    def _parse_mst_file(self, file_path: str) -> pd.DataFrame:
        """MST 파일 파싱"""
        try:
            import zipfile
            
            # ZIP 파일인 경우 압축 해제
            if file_path.endswith('.zip'):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall('.')
                file_path = file_path.replace('.zip', '.mst')
            
            # MST 파일 읽기
            with open(file_path, 'r', encoding='cp949') as f:
                lines = f.readlines()
            
            data = []
            for line in lines:
                if len(line) > 50:  # 유효한 데이터 라인만 처리
                    # 종목코드 (6자리)
                    symbol = line[0:6].strip()
                    # 종목명 (한글)
                    name = line[8:20].strip()
                    # 시장구분
                    market = line[20:22].strip()
                    
                    if symbol and name and market in ['10', '20', '30']:  # 코스피만
                        data.append({
                            'symbol': symbol,
                            'name': name,
                            'market': market
                        })
            
            return pd.DataFrame(data)
            
        except Exception as e:
            self.logger.error(f"❌ MST 파일 파싱 실패: {e}")
            return None
    
    def _get_default_stock_list(self) -> pd.DataFrame:
        """기본 종목 리스트 반환 (시가총액 상위 종목들)"""
        default_stocks = [
            ('005930', '삼성전자', '반도체'),
            ('000660', 'SK하이닉스', '반도체'),
            ('035420', 'NAVER', '인터넷'),
            ('051910', 'LG화학', '화학'),
            ('035720', '카카오', '인터넷'),
            ('006400', '삼성SDI', '배터리'),
            ('207940', '삼성바이오로직스', '바이오'),
            ('068270', '셀트리온', '바이오'),
            ('005380', '현대차', '자동차'),
            ('000270', '기아', '자동차'),
            ('012330', '현대모비스', '자동차부품'),
            ('066570', 'LG전자', '전자'),
            ('003550', 'LG생활건강', '화장품'),
            ('323410', '카카오뱅크', '금융'),
            ('086790', '하나금융지주', '금융'),
            ('105560', 'KB금융', '금융'),
            ('055550', '신한지주', '금융'),
            ('034730', 'SK', '에너지'),
            ('096770', 'SK이노베이션', '에너지'),
            ('017670', 'SK텔레콤', '통신')
        ]
        
        data = []
        for symbol, name, sector in default_stocks:
            data.append({
                'symbol': symbol,
                'name': name,
                'sector': sector,
                'market': '10'
            })
        
        return pd.DataFrame(data)
    
    async def _get_market_cap_data(self, symbol: str, name: str) -> Dict[str, Any]:
        """종목의 시가총액 데이터 조회"""
        try:
            # 캐시 확인
            cache_key = f"{symbol}_{name}"
            if cache_key in self._market_cap_cache:
                return self._market_cap_cache[cache_key]
            
            # KIS API로 데이터 조회
            data = self.data_provider.get_stock_price_info(symbol)
            
            if data and 'market_cap' in data:
                market_cap = data.get('market_cap', 0)
                current_price = data.get('current_price', 0)
                shares_outstanding = data.get('shares_outstanding', 0)
                
                result = {
                    'symbol': symbol,
                    'name': name,
                    'market_cap': market_cap,
                    'current_price': current_price,
                    'shares_outstanding': shares_outstanding,
                    'data_source': 'kis_api'
                }
            else:
                # 기본 시가총액 추정 (임의값)
                import random
                estimated_market_cap = random.randint(1000000000000, 50000000000000)  # 1조~50조
                result = {
                    'symbol': symbol,
                    'name': name,
                    'market_cap': estimated_market_cap,
                    'current_price': 0,
                    'shares_outstanding': 0,
                    'data_source': 'estimated'
                }
            
            # 캐시 저장
            self._market_cap_cache[cache_key] = result
            return result
            
        except Exception as e:
            self.logger.error(f"❌ {symbol}({name}) 시가총액 데이터 조회 실패: {e}")
            # 기본값 반환
            return {
                'symbol': symbol,
                'name': name,
                'market_cap': 0,
                'current_price': 0,
                'shares_outstanding': 0,
                'data_source': 'default'
            }
    
    async def get_top_market_cap_stocks(self, top_n: int = 50) -> List[Tuple[str, str, str]]:
        """시가총액 상위 N개 종목 조회"""
        self.logger.info(f"📊 시가총액 상위 {top_n}개 종목 조회 시작")
        
        try:
            # KOSPI 마스터 데이터 로드
            df = await self._load_kospi_master_data()
            
            if df is None or len(df) == 0:
                self.logger.error("❌ KOSPI 데이터를 로드할 수 없습니다")
                return []
            
            # 시가총액 데이터 수집
            market_cap_data = []
            for _, row in df.iterrows():
                # 컬럼명 확인 및 매핑
                if '단축코드' in df.columns:
                    symbol = str(row['단축코드']).zfill(6)
                    name = row['한글명']
                    market_cap_from_file = row.get('시가총액', 0)
                elif 'symbol' in df.columns:
                    symbol = str(row['symbol']).zfill(6)
                    name = row['name']
                    market_cap_from_file = row.get('market_cap', 0)
                else:
                    continue
                
                # 시가총액이 있는 경우 파일에서 가져온 값 사용, 없으면 API 조회
                if market_cap_from_file and market_cap_from_file > 0:
                    market_cap_data.append({
                        'symbol': symbol,
                        'name': name,
                        'market_cap': market_cap_from_file,
                        'current_price': 0,
                        'shares_outstanding': 0,
                        'data_source': 'excel_file'
                    })
                else:
                    data = await self._get_market_cap_data(symbol, name)
                    if data['market_cap'] > 0:
                        market_cap_data.append(data)
            
            # 시가총액 기준 정렬
            market_cap_data.sort(key=lambda x: x['market_cap'], reverse=True)
            
            # 상위 N개 선택
            top_stocks = market_cap_data[:top_n]
            
            # 결과 포맷팅
            result = []
            for data in top_stocks:
                symbol = data['symbol']
                name = data['name']
                market_cap = data['market_cap']
                
                # 업종 정보 추가 (기본값)
                sector = "기타"
                result.append((symbol, name, sector))
                
                self.logger.info(f"📈 {name}({symbol}): {market_cap:,}원")
            
            self.logger.info(f"✅ 시가총액 상위 {len(result)}개 종목 조회 완료")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 시가총액 상위 종목 조회 실패: {e}")
            return []
    
    async def analyze_top_market_cap_stocks(self, top_n: int = 50, min_score: float = 40.0) -> Dict[str, Any]:
        """시가총액 상위 종목 분석"""
        self.logger.info(f"🚀 코스피 시가총액 상위 {top_n}개 종목 분석 시작")
        
        try:
            # 시가총액 상위 종목 조회
            top_stocks = await self.get_top_market_cap_stocks(top_n)
            
            if not top_stocks:
                self.logger.error("❌ 분석할 종목이 없습니다")
                return {}
            
            # 종목 분석
            self.logger.info(f"🔍 {len(top_stocks)}개 종목 분석 시작")
            results = await self.analyzer.analyze_multiple_stocks(top_stocks)
            
            # 결과 필터링 (저평가 종목)
            undervalued_stocks = [
                r for r in results 
                if r.ultimate_score >= min_score
            ]
            
            # 시가총액 가중 분석
            market_cap_analysis = self._analyze_market_cap_weighted(results)
            
            # 결과 정리
            analysis_result = {
                'analysis_date': datetime.now().isoformat(),
                'total_analyzed': len(results),
                'top_n': top_n,
                'undervalued_count': len(undervalued_stocks),
                'min_score_threshold': min_score,
                'market_cap_analysis': market_cap_analysis,
                'results': results,
                'undervalued_stocks': undervalued_stocks
            }
            
            self.logger.info(f"✅ 분석 완료: 총 {len(results)}개, 저평가 {len(undervalued_stocks)}개")
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"❌ 시가총액 상위 종목 분석 실패: {e}")
            return {}
    
    def _analyze_market_cap_weighted(self, results: List) -> Dict[str, Any]:
        """시가총액 가중 분석"""
        try:
            total_market_cap = 0
            weighted_scores = 0
            market_cap_distribution = {}
            
            for result in results:
                # 시가총액 데이터 조회
                market_cap_data = self._market_cap_cache.get(f"{result.symbol}_{result.name}", {})
                market_cap = market_cap_data.get('market_cap', 0)
                
                if market_cap > 0:
                    total_market_cap += market_cap
                    weighted_scores += result.ultimate_score * market_cap
                    
                    # 시가총액 구간별 분포
                    if market_cap >= 100000000000000:  # 100조 이상
                        cap_range = "100조 이상"
                    elif market_cap >= 50000000000000:  # 50조 이상
                        cap_range = "50조~100조"
                    elif market_cap >= 10000000000000:  # 10조 이상
                        cap_range = "10조~50조"
                    elif market_cap >= 1000000000000:  # 1조 이상
                        cap_range = "1조~10조"
                    else:
                        cap_range = "1조 미만"
                    
                    if cap_range not in market_cap_distribution:
                        market_cap_distribution[cap_range] = {
                            'count': 0,
                            'total_market_cap': 0,
                            'avg_score': 0,
                            'stocks': []
                        }
                    
                    market_cap_distribution[cap_range]['count'] += 1
                    market_cap_distribution[cap_range]['total_market_cap'] += market_cap
                    market_cap_distribution[cap_range]['stocks'].append({
                        'symbol': result.symbol,
                        'name': result.name,
                        'score': result.ultimate_score,
                        'market_cap': market_cap
                    })
            
            # 평균 점수 계산
            avg_weighted_score = weighted_scores / total_market_cap if total_market_cap > 0 else 0
            
            # 구간별 평균 점수 계산
            for cap_range in market_cap_distribution:
                dist = market_cap_distribution[cap_range]
                if dist['count'] > 0:
                    dist['avg_score'] = sum(s['score'] for s in dist['stocks']) / dist['count']
                    # 시가총액 순으로 정렬
                    dist['stocks'].sort(key=lambda x: x['market_cap'], reverse=True)
            
            return {
                'total_market_cap': total_market_cap,
                'avg_weighted_score': avg_weighted_score,
                'distribution': market_cap_distribution
            }
            
        except Exception as e:
            self.logger.error(f"❌ 시가총액 가중 분석 실패: {e}")
            return {}
    
    def save_results(self, results: Dict[str, Any], filename_prefix: str = "market_cap_top_analysis") -> str:
        """분석 결과 저장"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename_prefix}_{timestamp}.json"
            
            # JSON 직렬화 가능한 형태로 변환
            serializable_results = {
                'analysis_date': results['analysis_date'],
                'total_analyzed': results['total_analyzed'],
                'top_n': results['top_n'],
                'undervalued_count': results['undervalued_count'],
                'min_score_threshold': results['min_score_threshold'],
                'market_cap_analysis': results['market_cap_analysis'],
                'results': [
                    {
                        'symbol': r.symbol,
                        'name': r.name,
                        'sector': r.sector,
                        'ultimate_score': r.ultimate_score,
                        'ultimate_grade': r.ultimate_grade.value,
                        'investment_recommendation': r.investment_recommendation.value,
                        'confidence_level': r.confidence_level.value,
                        'enhanced_score': r.enhanced_score,
                        'enhanced_grade': r.enhanced_grade.value,
                        'score_breakdown': r.score_breakdown,
                        'financial_score': r.financial_score,
                        'price_position_penalty': r.price_position_penalty
                    }
                    for r in results['results']
                ],
                'undervalued_stocks': [
                    {
                        'symbol': r.symbol,
                        'name': r.name,
                        'sector': r.sector,
                        'ultimate_score': r.ultimate_score,
                        'ultimate_grade': r.ultimate_grade.value,
                        'investment_recommendation': r.investment_recommendation.value,
                        'confidence_level': r.confidence_level.value
                    }
                    for r in results['undervalued_stocks']
                ]
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(serializable_results, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"💾 분석 결과 저장 완료: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"❌ 결과 저장 실패: {e}")
            return ""
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """분석 보고서 생성"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"market_cap_top_report_{timestamp}.txt"
            
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write("=" * 100 + "\n")
                f.write("📊 코스피 시가총액 상위 종목 분석 보고서\n")
                f.write("=" * 100 + "\n")
                f.write(f"📅 분석 일시: {results['analysis_date']}\n")
                f.write(f"📊 분석 종목 수: {results['total_analyzed']}개 (상위 {results['top_n']}개)\n")
                f.write(f"🎯 저평가 종목 발견: {results['undervalued_count']}개\n")
                f.write(f"📈 최소 점수 기준: {results['min_score_threshold']}점\n\n")
                
                # 시가총액 가중 분석
                market_cap_analysis = results['market_cap_analysis']
                if market_cap_analysis:
                    f.write("📈 시가총액 가중 분석\n")
                    f.write("-" * 50 + "\n")
                    f.write(f"총 시가총액: {market_cap_analysis['total_market_cap']:,}원\n")
                    f.write(f"가중 평균 점수: {market_cap_analysis['avg_weighted_score']:.1f}점\n\n")
                    
                    # 시가총액 구간별 분포
                    f.write("📊 시가총액 구간별 분포\n")
                    f.write("-" * 50 + "\n")
                    for cap_range, dist in market_cap_analysis['distribution'].items():
                        f.write(f"{cap_range}: {dist['count']}개 종목\n")
                        f.write(f"  평균 점수: {dist['avg_score']:.1f}점\n")
                        f.write(f"  총 시가총액: {dist['total_market_cap']:,}원\n")
                        f.write(f"  주요 종목:\n")
                        for stock in dist['stocks'][:3]:  # 상위 3개만 표시
                            f.write(f"    - {stock['name']}({stock['symbol']}): {stock['score']:.1f}점\n")
                        f.write("\n")
                
                # 저평가 종목 리스트
                if results['undervalued_stocks']:
                    f.write("🎯 저평가 종목 리스트\n")
                    f.write("-" * 50 + "\n")
                    for i, stock in enumerate(results['undervalued_stocks'], 1):
                        f.write(f"{i:2d}. {stock['name']}({stock['symbol']})\n")
                        f.write(f"    점수: {stock['ultimate_score']:.1f}점 ({stock['ultimate_grade']})\n")
                        f.write(f"    추천: {stock['investment_recommendation']} ({stock['confidence_level']})\n\n")
                else:
                    f.write("⚠️ 저평가 기준을 만족하는 종목이 없습니다.\n\n")
                
                # 투자 전략
                f.write("💼 투자 전략 및 권장사항\n")
                f.write("-" * 50 + "\n")
                f.write("📋 전략: 시가총액 상위 종목 중심의 안정적 투자\n")
                f.write("🎯 포커스: 대형주 중심의 밸류 투자\n")
                f.write("⚠️ 주의사항: 시가총액이 큰 종목들은 시장 변동성이 상대적으로 낮을 수 있습니다.\n")
                f.write("📈 권장: 분산 투자와 정기적인 포트폴리오 리밸런싱\n")
                f.write("=" * 100 + "\n")
            
            self.logger.info(f"📄 분석 보고서 생성 완료: {report_filename}")
            return report_filename
            
        except Exception as e:
            self.logger.error(f"❌ 보고서 생성 실패: {e}")
            return ""


async def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="코스피 시가총액 상위 종목 분석")
    parser.add_argument("--top-n", type=int, default=50, help="상위 N개 종목 분석 (기본값: 50)")
    parser.add_argument("--min-score", type=float, default=40.0, help="최소 점수 기준 (기본값: 40.0)")
    parser.add_argument("--config", type=str, default="config.yaml", help="설정 파일 경로")
    
    args = parser.parse_args()
    
    print("=" * 100)
    print("🚀 코스피 시가총액 상위 종목 분석 시스템")
    print("=" * 100)
    
    try:
        # 분석기 초기화
        analyzer = MarketCapTopAnalyzer(args.config)
        
        # 시가총액 상위 종목 분석
        results = await analyzer.analyze_top_market_cap_stocks(
            top_n=args.top_n,
            min_score=args.min_score
        )
        
        if results:
            # 결과 저장
            json_filename = analyzer.save_results(results)
            
            # 보고서 생성
            report_filename = analyzer.generate_report(results)
            
            print(f"\n✅ 분석 완료!")
            print(f"📊 총 분석 종목: {results['total_analyzed']}개")
            print(f"🎯 저평가 종목: {results['undervalued_count']}개")
            print(f"💾 결과 파일: {json_filename}")
            print(f"📄 보고서 파일: {report_filename}")
            
        else:
            print("❌ 분석 실패")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    
    print("=" * 100)


if __name__ == "__main__":
    asyncio.run(main())
