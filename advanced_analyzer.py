#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KOSPI 마스터 데이터를 활용한 고급 저평가 가치주 분석 시스템
"""

import typer
import pandas as pd
import numpy as np
import logging
import time
import os
import yaml

# 로거 설정
logger = logging.getLogger(__name__)
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import queue
from rich.console import Console
from rich.progress import Progress
from rich.table import Table
from rich.panel import Panel
from kis_data_provider import KISDataProvider
from enhanced_price_provider import EnhancedPriceProvider
from dart_financial_analyzer import DARTFinancialAnalyzer
from dart_comprehensive_analyzer import DARTComprehensiveAnalyzer
from sector_analyzer import SectorAnalyzer
from stock_info_analyzer import StockInfoAnalyzer
from balance_sheet_analyzer import BalanceSheetAnalyzer
from income_statement_analyzer import IncomeStatementAnalyzer
from financial_ratio_analyzer import FinancialRatioAnalyzer
from profit_ratio_analyzer import ProfitRatioAnalyzer
from stability_ratio_analyzer import StabilityRatioAnalyzer
from growth_ratio_analyzer import GrowthRatioAnalyzer
from estimate_performance_analyzer import EstimatePerformanceAnalyzer
from corpCode import get_dart_corp_codes, DARTCorpCodeManager
from typing import List, Dict, Any, Optional

# TPS 제한을 고려한 레이트리미터 클래스
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

def load_config():
    """config.yaml 파일을 로드합니다."""
    try:
        with open('config.yaml', 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        console.print("⚠️ config.yaml 파일을 찾을 수 없습니다.")
        return {}
    except Exception as e:
        console.print(f"⚠️ config.yaml 로드 실패: {e}")
        return {}

def get_dart_api_key_from_config():
    """config.yaml에서 DART API 키를 가져옵니다."""
    config = load_config()
    dart_key = config.get('api', {}).get('dart', {}).get('api_key')
    if dart_key:
        console.print("✅ config.yaml에서 DART API 키를 로드했습니다.")
        return dart_key
    else:
        console.print("⚠️ config.yaml에서 DART API 키를 찾을 수 없습니다.")
        return None

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
# 분석 모듈들의 로깅 레벨을 WARNING으로 설정하여 불필요한 경고 메시지 줄이기
logging.getLogger('profit_ratio_analyzer').setLevel(logging.WARNING)
logging.getLogger('financial_ratio_analyzer').setLevel(logging.WARNING)
logging.getLogger('stability_ratio_analyzer').setLevel(logging.WARNING)
logging.getLogger('growth_ratio_analyzer').setLevel(logging.WARNING)
logging.getLogger('estimate_performance_analyzer').setLevel(logging.WARNING)

# Rich Console 초기화
console = Console()

# Typer CLI 앱 생성
app = typer.Typer(help="KOSPI 마스터 데이터 기반 고급 저평가 가치주 분석 시스템")

class AdvancedStockAnalyzer:
    """고급 주식 분석 클래스"""
    
    def __init__(self, dart_api_key: str = None):
        self.provider = KISDataProvider()
        self.price_provider = EnhancedPriceProvider()
        self.kospi_data = None
        self.dart_analyzer = None
        self.dart_comprehensive_analyzer = None
        self.sector_analyzer = SectorAnalyzer(self.provider)
        self.stock_info_analyzer = StockInfoAnalyzer(self.provider)
        self.balance_sheet_analyzer = BalanceSheetAnalyzer(self.provider)
        self.income_statement_analyzer = IncomeStatementAnalyzer(self.provider)
        self.financial_ratio_analyzer = FinancialRatioAnalyzer(self.provider)
        self.profit_ratio_analyzer = ProfitRatioAnalyzer(self.provider)
        self.stability_ratio_analyzer = StabilityRatioAnalyzer(self.provider)
        self.growth_ratio_analyzer = GrowthRatioAnalyzer(self.provider)
        self.estimate_performance_analyzer = EstimatePerformanceAnalyzer(self.provider)
        self.corp_code_mapping = {}  # 종목코드 -> 기업고유번호 매핑
        self.dart_corp_manager = None  # DART 기업 고유번호 관리자
        self._load_kospi_data()
        
        # DART API 키 자동 로드 (config.yaml에서)
        if not dart_api_key:
            dart_api_key = get_dart_api_key_from_config()
        
        # DART API 키를 인스턴스 변수로 저장
        self.dart_api_key = dart_api_key
        
        # DART 기업코드 매핑 테이블 자동 로드
        if dart_api_key:
            # 설정 파일에서 DART 설정 로드
            dart_config = self._load_dart_config()
            self.dart_corp_manager = DARTCorpCodeManager(
                dart_api_key, 
                cache_dir=dart_config.get('cache_dir', 'cache')
            )
            # 설정 적용
            self._apply_dart_config(dart_config)
        self._load_dart_corp_mapping()
        
        # DART API 키가 제공된 경우 재무 분석기 초기화
        if dart_api_key:
            self.dart_analyzer = DARTFinancialAnalyzer(dart_api_key)
            self.dart_comprehensive_analyzer = DARTComprehensiveAnalyzer(dart_api_key)
            console.print("✅ DART 포괄적 재무 분석기 초기화 완료")
        else:
            console.print("⚠️ DART API 키 없음 - 기본 매핑만 사용")
    
    def _load_kospi_data(self):
        """KOSPI 마스터 데이터를 로드합니다."""
        try:
            # 파일 존재 확인
            if not os.path.exists('kospi_code.xlsx'):
                console.print("❌ kospi_code.xlsx 파일을 찾을 수 없습니다.")
                console.print("📋 복구 가이드:")
                console.print("   1. python kospi_master_download.py 실행")
                console.print("   2. 또는 수동으로 KOSPI 마스터 데이터 다운로드")
                console.print("   3. 파일명을 'kospi_code.xlsx'로 저장")
                self.kospi_data = pd.DataFrame()
                return
            
            # 데이터 로드
            self.kospi_data = pd.read_excel('kospi_code.xlsx')
            
            # 필수 컬럼 검증
            required_columns = ['단축코드', '한글명', '시가총액']
            missing_columns = [col for col in required_columns if col not in self.kospi_data.columns]
            
            if missing_columns:
                console.print(f"❌ 필수 컬럼이 누락되었습니다: {missing_columns}")
                console.print("📋 복구 가이드: kospi_master_download.py를 다시 실행하세요.")
                self.kospi_data = pd.DataFrame()
                return
            
            # 데이터 신선도 확인 (파일 수정일 기준)
            file_mtime = os.path.getmtime('kospi_code.xlsx')
            file_age_days = (time.time() - file_mtime) / (24 * 3600)
            
            if file_age_days > 30:
                console.print(f"⚠️ 마스터 데이터가 오래되었습니다 ({file_age_days:.0f}일 전)")
                console.print("📋 권장사항: python kospi_master_download.py 실행")
            
            console.print(f"✅ KOSPI 마스터 데이터 로드 완료: {len(self.kospi_data)}개 종목")
            
        except Exception as e:
            console.print(f"❌ KOSPI 마스터 데이터 로드 실패: {e}")
            console.print("📋 복구 가이드:")
            console.print("   1. python kospi_master_download.py 실행")
            console.print("   2. 파일 권한 확인")
            console.print("   3. Excel 파일 손상 여부 확인")
            self.kospi_data = pd.DataFrame()
    
    def _load_dart_corp_mapping(self):
        """DART 기업코드 매핑을 건너뛰고 동적 검색을 사용합니다."""
        console.print("⚡ DART 기업코드 매핑을 건너뛰고 동적 검색을 사용합니다.")
        self.corp_code_mapping = {}
    
    def _load_corp_code_mapping(self, dart_api_key: str):
        """DART 기업고유번호 매핑을 로드합니다. (레거시 - 자동 매핑으로 대체됨)"""
        # 이 메서드는 이제 _load_dart_corp_mapping으로 대체됨
        pass
    
    def refresh_dart_corp_codes(self, force_refresh: bool = True):
        """DART 기업 고유번호 데이터를 새로고침합니다."""
        if not self.dart_corp_manager:
            console.print("❌ DART 관리자가 초기화되지 않았습니다.")
            return False
        
        try:
            console.print("🔄 DART 기업 고유번호 데이터 새로고침 중...")
            df = self.dart_corp_manager.get_dart_corp_codes(force_refresh=force_refresh)
            
            if df is not None and not df.empty:
                console.print(f"✅ DART 기업 고유번호 새로고침 완료: {len(df):,}개 기업")
                # 매핑 테이블 재구축
                self._load_dart_corp_mapping()
                return True
            else:
                console.print("❌ DART 기업 고유번호 새로고침 실패")
                return False
                
        except Exception as e:
            console.print(f"❌ DART 기업 고유번호 새로고침 중 오류: {e}")
            return False
    
    def get_dart_corp_code_info(self) -> Dict[str, Any]:
        """DART 기업 고유번호 관리 상태 정보를 반환합니다."""
        if not self.dart_corp_manager:
            return {"status": "not_initialized"}
        
        cache_info = self.dart_corp_manager.get_cache_info()
        mapping_count = len(self.corp_code_mapping)
        kospi_count = len(self.kospi_data) if self.kospi_data is not None else 0
        
        return {
            "status": "initialized",
            "cache_info": cache_info,
            "mapping_count": mapping_count,
            "kospi_count": kospi_count,
            "mapping_rate": f"{mapping_count/kospi_count*100:.1f}%" if kospi_count > 0 else "0%"
        }
    
    def search_dart_company(self, keyword: str, limit: int = 10) -> List[Dict[str, str]]:
        """DART 기업을 검색합니다."""
        if not self.dart_corp_manager:
            console.print("❌ DART 관리자가 초기화되지 않았습니다.")
            return []
        
        try:
            results = self.dart_corp_manager.search_companies(keyword, limit)
            return results
        except Exception as e:
            console.print(f"❌ 기업 검색 중 오류: {e}")
            return []
    
    def _load_dart_config(self) -> Dict[str, Any]:
        """설정 파일에서 DART 관련 설정을 로드합니다."""
        try:
            config_path = "config.yaml"
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                dart_config = config.get('api', {}).get('dart', {}).get('corp_code_management', {})
                return dart_config
            else:
                logger.warning("설정 파일을 찾을 수 없습니다. 기본 설정을 사용합니다.")
                return {}
        except Exception as e:
            logger.error(f"DART 설정 로드 실패: {e}")
            return {}
    
    def _apply_dart_config(self, config: Dict[str, Any]) -> None:
        """DART 설정을 적용합니다."""
        if not self.dart_corp_manager or not config:
            return
        
        try:
            # 캐시 만료 시간 설정
            if 'cache_expiry_hours' in config:
                self.dart_corp_manager.cache_expiry_hours = config['cache_expiry_hours']
            
            # 매칭 설정 적용
            matching_config = config.get('matching', {})
            if 'fuzzy_threshold' in matching_config:
                self.dart_corp_manager.fuzzy_threshold = matching_config['fuzzy_threshold']
            
            logger.info("DART 설정이 성공적으로 적용되었습니다.")
        except Exception as e:
            logger.error(f"DART 설정 적용 실패: {e}")
    
    def get_top_stocks_by_market_cap(self, n: int = 100) -> List[str]:
        """시가총액 상위 N개 종목을 반환합니다."""
        if self.kospi_data.empty:
            return []
        
        # KOSPI 종목만 필터링하고 시가총액 순으로 정렬
        kospi_stocks = self.kospi_data[
            (self.kospi_data['KOSPI'] == 'Y') & 
            (self.kospi_data['시가총액'] > 0)
        ].copy()
        
        kospi_stocks = kospi_stocks.sort_values('시가총액', ascending=False)
        return kospi_stocks['단축코드'].head(n).tolist()
    
    def get_sector_stocks(self, sector: str) -> List[str]:
        """특정 섹터의 종목들을 반환합니다."""
        if self.kospi_data.empty:
            return []
        
        sector_mapping = {
            '반도체': 'KRX반도체',
            '바이오': 'KRX바이오', 
            '자동차': 'KRX자동차',
            '은행': 'KRX은행',
            '에너지화학': 'KRX에너지화학',
            '철강': 'KRX철강',
            '미디어통신': 'KRX미디어통신',
            '건설': 'KRX건설',
            '증권': 'KRX증권',
            '선박': 'KRX선박'
        }
        
        if sector not in sector_mapping:
            console.print(f"❌ 지원하지 않는 섹터입니다: {sector}")
            return []
        
        sector_col = sector_mapping[sector]
        sector_stocks = self.kospi_data[
            (self.kospi_data['KOSPI'] == 'Y') & 
            (self.kospi_data[sector_col] == 'Y')
        ]
        
        return sector_stocks['단축코드'].tolist()
    
    def calculate_advanced_valuation_score(self, stock_info: Dict[str, Any], kospi_info: Optional[Dict] = None, dart_financial: Optional[Dict] = None) -> Dict[str, float]:
        """고급 가치 평가 점수를 계산합니다."""
        pbr = stock_info.get('pbr', 0)
        per = stock_info.get('per', 0)
        market_cap = stock_info.get('market_cap', 0)
        
        scores = {
            'pbr_score': 0,
            'per_score': 0,
            'size_score': 0,
            'roe_score': 0,
            'debt_ratio_score': 0,
            'profitability_score': 0,
            'growth_score': 0,
            'total_score': 0
        }
        
        # PBR 점수 (낮을수록 높음)
        if pbr and 0 < pbr < 1:
            scores['pbr_score'] = (1 - pbr) * 50
        elif pbr and 1 <= pbr < 2:
            scores['pbr_score'] = (2 - pbr) * 25
        
        # PER 점수 (낮을수록 높음)
        if per and 0 < per < 10:
            scores['per_score'] = (10 - per) * 5
        elif per and 10 <= per < 20:
            scores['per_score'] = (20 - per) * 2.5
        
        # 시가총액 점수 (클수록 안정성 높음)
        if market_cap > 100000:  # 10조원 이상
            scores['size_score'] = 20
        elif market_cap > 50000:  # 5조원 이상
            scores['size_score'] = 15
        elif market_cap > 10000:  # 1조원 이상
            scores['size_score'] = 10
        elif market_cap > 1000:   # 1000억원 이상
            scores['size_score'] = 5
        
        # DART 재무 데이터 활용 점수 (우선순위 높음)
        if dart_financial:
            # ROE 점수 (DART 데이터 우선)
            roe = dart_financial.get('roe', 0)
            if roe and roe > 0:
                if roe > 20:
                    scores['roe_score'] = 25
                elif roe > 15:
                    scores['roe_score'] = 20
                elif roe > 10:
                    scores['roe_score'] = 15
                elif roe > 5:
                    scores['roe_score'] = 10
                else:
                    scores['roe_score'] = 5
            else:
                scores['roe_score'] = 0
            
            # 부채비율 점수 (낮을수록 높음)
            debt_ratio = dart_financial.get('debt_ratio', 0)
            if debt_ratio > 0:
                if debt_ratio < 30:
                    scores['debt_ratio_score'] = 15
                elif debt_ratio < 50:
                    scores['debt_ratio_score'] = 10
                elif debt_ratio < 70:
                    scores['debt_ratio_score'] = 5
                else:
                    scores['debt_ratio_score'] = 0
            
            # 수익성 점수 (영업이익률 + 순이익률)
            operating_margin = dart_financial.get('operating_margin', 0)
            net_margin = dart_financial.get('net_margin', 0)
            if operating_margin > 0:
                if operating_margin > 15:
                    scores['profitability_score'] += 10
                elif operating_margin > 10:
                    scores['profitability_score'] += 8
                elif operating_margin > 5:
                    scores['profitability_score'] += 5
                else:
                    scores['profitability_score'] += 2
            
            if net_margin > 0:
                if net_margin > 10:
                    scores['profitability_score'] += 10
                elif net_margin > 5:
                    scores['profitability_score'] += 8
                elif net_margin > 2:
                    scores['profitability_score'] += 5
                else:
                    scores['profitability_score'] += 2
            
            # 성장성 점수
            revenue_growth = dart_financial.get('revenue_growth', 0)
            net_income_growth = dart_financial.get('net_income_growth', 0)
            if revenue_growth > 0:
                if revenue_growth > 20:
                    scores['growth_score'] += 10
                elif revenue_growth > 10:
                    scores['growth_score'] += 8
                elif revenue_growth > 5:
                    scores['growth_score'] += 5
                else:
                    scores['growth_score'] += 2
            
            if net_income_growth > 0:
                if net_income_growth > 20:
                    scores['growth_score'] += 10
                elif net_income_growth > 10:
                    scores['growth_score'] += 8
                elif net_income_growth > 5:
                    scores['growth_score'] += 5
                else:
                    scores['growth_score'] += 2
        
        # KOSPI 마스터 데이터 활용 점수 (DART 데이터가 없을 때만)
        elif kospi_info:
            # ROE 점수
            roe = kospi_info.get('ROE', 0)
            if roe and roe > 0:
                if roe > 15:
                    scores['roe_score'] = 20
                elif roe > 10:
                    scores['roe_score'] = 15
                elif roe > 5:
                    scores['roe_score'] = 10
                else:
                    scores['roe_score'] = 5
            else:
                scores['roe_score'] = 0
            
            # 시가총액 규모 점수
            market_cap_scale = kospi_info.get('시가총액규모', '0')
            if market_cap_scale == '1':  # 대형주
                scores['scale_score'] = 15
            elif market_cap_scale == '2':  # 중형주
                scores['scale_score'] = 10
            elif market_cap_scale == '3':  # 소형주
                scores['scale_score'] = 5
            else:
                scores['scale_score'] = 0
        
        # 총점 계산
        scores['total_score'] = sum([
            scores['pbr_score'],
            scores['per_score'], 
            scores['size_score'],
            scores.get('roe_score', 0),
            scores.get('debt_ratio_score', 0),
            scores.get('profitability_score', 0),
            scores.get('growth_score', 0),
            scores.get('scale_score', 0)
        ])
        
        # DART 재무 데이터를 결과에 포함
        if dart_financial:
            scores.update({
                'roe': dart_financial.get('roe', 0),
                'roa': dart_financial.get('roa', 0),
                'debt_ratio': dart_financial.get('debt_ratio', 0),
                'operating_margin': dart_financial.get('operating_margin', 0),
                'net_margin': dart_financial.get('net_margin', 0),
                'revenue_growth': dart_financial.get('revenue_growth', 0),
                'net_income_growth': dart_financial.get('net_income_growth', 0)
            })
        
        return scores
    
    def get_kospi_info(self, symbol: str) -> Optional[Dict]:
        """종목 코드에 해당하는 KOSPI 마스터 정보를 반환합니다."""
        if self.kospi_data.empty:
            return None
        
        stock_info = self.kospi_data[self.kospi_data['단축코드'] == symbol]
        if not stock_info.empty:
            return stock_info.iloc[0].to_dict()
        return None
    
    def analyze_stocks(self, symbols: List[str]) -> pd.DataFrame:
        """종목들을 분석합니다."""
        all_stock_info = []
        
        with Progress(console=console) as progress:
            task = progress.add_task("[cyan]고급 분석 중...", total=len(symbols))
            
            for symbol in symbols:
                # KIS API에서 데이터 수집
                price_info = self.provider.get_stock_price_info(symbol)
                if price_info:
                    # KOSPI 마스터 데이터에서 추가 정보 수집
                    kospi_info = self.get_kospi_info(symbol)
                    
                    # DART 포괄적 재무 데이터 수집 (가능한 경우)
                    dart_financial = None
                    if self.dart_comprehensive_analyzer and self.corp_code_mapping:
                        # 종목코드로 기업 고유번호 찾기
                        corp_code = self.corp_code_mapping.get(symbol)
                        if corp_code:
                            # 2024년 데이터로 시도, 실패하면 2023년으로 fallback
                            dart_financial = self.dart_comprehensive_analyzer.get_comprehensive_financial_data(corp_code, 2024)
                            if not dart_financial:
                                dart_financial = self.dart_comprehensive_analyzer.get_comprehensive_financial_data(corp_code, 2023)
                    
                    # 고급 점수 계산
                    scores = self.calculate_advanced_valuation_score(price_info, kospi_info, dart_financial)
                    
                    # 종목명 추가 (KIS API에서 가져온 이름 우선, KOSPI 마스터 데이터는 보조)
                    stock_name = price_info.get('name', kospi_info.get('한글명', f'종목코드: {symbol}')) if kospi_info else price_info.get('name', f'종목코드: {symbol}')
                    
                    # 결과 통합
                    result = {
                        **price_info,
                        'stock_name': stock_name,
                        'sector': kospi_info.get('지수업종대분류', '') if kospi_info else '',
                        'market_cap_scale': kospi_info.get('시가총액규모', '') if kospi_info else '',
                        'roe_master': kospi_info.get('ROE', 0) if kospi_info else 0,
                        **scores
                    }
                    
                    # DART 재무 데이터 추가
                    if dart_financial:
                        result.update({
                            'roe_dart': dart_financial.get('roe', 0),
                            'debt_ratio': dart_financial.get('debt_ratio', 0),
                            'operating_margin': dart_financial.get('operating_margin', 0),
                            'net_margin': dart_financial.get('net_margin', 0),
                            'revenue_growth': dart_financial.get('revenue_growth', 0),
                            'net_income_growth': dart_financial.get('net_income_growth', 0),
                            'roa': dart_financial.get('roa', 0),
                            'asset_turnover': dart_financial.get('asset_turnover', 0)
                        })
                    
                    all_stock_info.append(result)
                    progress.update(task, advance=1, description=f"[cyan]분석 중... {stock_name} 완료")
                else:
                    progress.update(task, advance=1, description=f"[red]분석 중... {symbol} 실패")
        
        if not all_stock_info:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_stock_info)
        return df.sort_values('total_score', ascending=False).reset_index(drop=True)
    
    def display_results(self, df: pd.DataFrame, top_n: int = 10):
        """결과를 표시합니다."""
        if df.empty:
            console.print("[bold red]❌ 분석할 데이터가 없습니다.[/bold red]")
            return
        
        # 상위 N개만 표시
        top_df = df.head(top_n)
        
        console.print(f"\n📊 [bold yellow]고급 저평가 가치주 분석 결과 (상위 {top_n}개)[/bold yellow]")
        
        # 테이블 생성
        table = Table(title=f"🏆 저평가 가치주 TOP {top_n}")
        table.add_column("순위", justify="center", style="bold")
        table.add_column("종목명", justify="left", style="cyan")
        table.add_column("종목코드", justify="center")
        table.add_column("현재가", justify="right", style="green")
        table.add_column("등락률", justify="right", style="dim")
        table.add_column("PBR", justify="right")
        table.add_column("PER", justify="right")
        table.add_column("총점", justify="right", style="bold yellow")
        table.add_column("ROE", justify="right", style="blue")
        table.add_column("ROA", justify="right", style="blue")
        table.add_column("부채비율", justify="right", style="blue")
        table.add_column("영업이익률", justify="right", style="blue")
        table.add_column("순이익률", justify="right", style="blue")
        table.add_column("거래량", justify="right", style="dim")
        table.add_column("상태", justify="center")
        
        for i, (_, row) in enumerate(top_df.iterrows(), 1):
                # 등락률 표시
                change_rate = row.get('change_rate', 0)
                change_rate_str = f"{change_rate:+.2f}%" if change_rate != 0 else "0.00%"
                
                # 거래량 표시 (천 단위)
                volume = row.get('volume', 0)
                volume_str = f"{volume:,.0f}K" if volume > 0 else "0"
                
                # 종목 상태 표시
                status = ""
                if row.get('management_stock') == 'Y':
                    status = "관리"
                elif row.get('investment_caution') == 'Y':
                    status = "투자유의"
                elif row.get('short_overheating') == 'Y':
                    status = "단기과열"
                elif row.get('market_warning'):
                    status = "경고"
                else:
                    status = "정상"
                
                # DART 포괄적 재무 데이터 표시
                roe_value = row.get('roe', 0)
                roe_str = f"{roe_value:.1f}%" if roe_value and roe_value > 0 else "N/A"
                
                roa_value = row.get('roa', 0)
                roa_str = f"{roa_value:.1f}%" if roa_value and roa_value > 0 else "N/A"
                
                debt_ratio = row.get('debt_ratio', 0)
                debt_ratio_str = f"{debt_ratio:.1f}%" if debt_ratio and debt_ratio > 0 else "N/A"
                
                operating_margin = row.get('operating_margin', 0)
                operating_margin_str = f"{operating_margin:.1f}%" if operating_margin and operating_margin > 0 else "N/A"
                
                net_margin = row.get('net_margin', 0)
                net_margin_str = f"{net_margin:.1f}%" if net_margin and net_margin > 0 else "N/A"
                
                table.add_row(
                str(i),
                row['stock_name'],
                row['symbol'],
                f"{row['current_price']:,.0f}원",
                change_rate_str,
                f"{row['pbr']:.2f}",
                f"{row['per']:.2f}",
                f"{row['total_score']:.1f}",
                roe_str,
                roa_str,
                debt_ratio_str,
                operating_margin_str,
                net_margin_str,
                volume_str,
                status
            )
        
        console.print(table)
        
        # 요약 통계
        console.print(f"\n📈 [bold]분석 요약[/bold]")
        console.print(f"• 분석 종목 수: {len(df)}개")
        console.print(f"• 평균 총점: {df['total_score'].mean():.1f}점")
        console.print(f"• 최고 점수: {df['total_score'].max():.1f}점")
        console.print(f"• 평균 PBR: {df['pbr'].mean():.2f}")
        console.print(f"• 평균 PER: {df['per'].mean():.2f}")

@app.command(name="analyze-top")
def analyze_top_stocks(
    n: int = typer.Option(50, "--count", "-n", help="분석할 상위 종목 수"),
    top_display: int = typer.Option(10, "--display", "-d", help="표시할 상위 종목 수"),
    dart_key: str = typer.Option(None, "--dart-key", "-k", help="DART API 키 (재무 분석용)")
):
    """시가총액 상위 종목들을 분석합니다."""
    analyzer = AdvancedStockAnalyzer(dart_key)
    
    console.print(f"🚀 [bold green]시가총액 상위 {n}개[/bold green] 종목에 대한 고급 분석을 시작합니다...")
    
    symbols = analyzer.get_top_stocks_by_market_cap(n)
    if not symbols:
        console.print("[bold red]❌ 분석할 종목을 찾을 수 없습니다.[/bold red]")
        return
    
    df = analyzer.analyze_stocks(symbols)
    analyzer.display_results(df, top_display)

@app.command(name="analyze-sector")
def analyze_sector_stocks(
    sector: str = typer.Option("반도체", "--sector", "-s", help="분석할 섹터"),
    top_display: int = typer.Option(10, "--display", "-d", help="표시할 상위 종목 수"),
    dart_key: str = typer.Option(None, "--dart-key", "-k", help="DART API 키 (재무 분석용)")
):
    """특정 섹터의 종목들을 분석합니다."""
    analyzer = AdvancedStockAnalyzer(dart_key)
    
    console.print(f"🚀 [bold green]{sector} 섹터[/bold green] 종목들에 대한 고급 분석을 시작합니다...")
    
    symbols = analyzer.get_sector_stocks(sector)
    if not symbols:
        console.print(f"[bold red]❌ {sector} 섹터 종목을 찾을 수 없습니다.[/bold red]")
        return
    
    df = analyzer.analyze_stocks(symbols)
    analyzer.display_results(df, top_display)

@app.command(name="analyze-custom")
def analyze_custom_stocks(
    symbols_str: str = typer.Option("005930,000660,035420,005380,051910", "--symbols", "-s", help="분석할 종목 코드 (쉼표로 구분)"),
    top_display: int = typer.Option(10, "--display", "-d", help="표시할 상위 종목 수"),
    dart_key: str = typer.Option(None, "--dart-key", "-k", help="DART API 키 (재무 분석용)")
):
    """사용자 지정 종목들을 분석합니다."""
    analyzer = AdvancedStockAnalyzer(dart_key)
    
    symbols = [s.strip() for s in symbols_str.split(',')]
    console.print(f"🚀 [bold green]{len(symbols)}개[/bold green] 사용자 지정 종목에 대한 고급 분석을 시작합니다...")
    
    df = analyzer.analyze_stocks(symbols)
    analyzer.display_results(df, top_display)

@app.command()
def analyze_sector_market(
    dart_key: str = typer.Option(None, help="DART API 키")
):
    """업종별 시장 분석을 수행합니다."""
    analyzer = AdvancedStockAnalyzer(dart_key)
    
    console.print("📊 업종별 시장 분석을 시작합니다...")
    
    # 모든 시장의 업종 지수 데이터 조회
    all_sector_data = analyzer.sector_analyzer.get_all_sector_data()
    
    if not all_sector_data:
        console.print("❌ 업종 지수 데이터를 조회할 수 없습니다.")
        return
    
    # 결과 테이블 생성
    table = Table(title="🏢 업종별 시장 분석")
    table.add_column("시장", justify="center", style="cyan")
    table.add_column("현재가", justify="right", style="green")
    table.add_column("등락률", justify="right", style="dim")
    table.add_column("거래량", justify="right", style="blue")
    table.add_column("상승종목", justify="right", style="green")
    table.add_column("하락종목", justify="right", style="red")
    table.add_column("시장심리", justify="center", style="yellow")
    table.add_column("종합점수", justify="right", style="bold")
    table.add_column("투자추천", justify="center", style="bold")
    
    for market_code, data in all_sector_data.items():
        # 성과 분석
        analysis = analyzer.sector_analyzer.analyze_sector_performance(data)
        
        # 등락률 표시
        change_rate = data.get('change_rate', 0)
        change_rate_str = f"{change_rate:+.2f}%" if change_rate != 0 else "0.00%"
        
        # 거래량 표시 (천 단위)
        volume = data.get('volume', 0)
        volume_str = f"{volume:,.0f}K" if volume > 0 else "0"
        
        # 시장심리 색상
        sentiment = data.get('market_sentiment', '중립')
        sentiment_color = "green" if "강세" in sentiment else "red" if "약세" in sentiment else "yellow"
        
        # 투자추천 색상
        recommendation = analysis.get('recommendation', '중립')
        rec_color = "green" if "추천" in recommendation else "red" if "비추천" in recommendation else "yellow"
        
        table.add_row(
            data['market_name'],
            f"{data['current_price']:,.2f}",
            change_rate_str,
            volume_str,
            str(data['ascending_count']),
            str(data['declining_count']),
            f"[{sentiment_color}]{sentiment}[/{sentiment_color}]",
            f"{analysis['total_score']:.1f}",
            f"[{rec_color}]{recommendation}[/{rec_color}]"
        )
    
    console.print(table)
    
    # 요약 통계
    total_scores = [analyzer.sector_analyzer.analyze_sector_performance(data)['total_score'] 
                   for data in all_sector_data.values()]
    
    console.print(f"\n📈 [bold]시장 분석 요약[/bold]")
    console.print(f"• 분석 시장 수: {len(all_sector_data)}개")
    console.print(f"• 평균 종합점수: {sum(total_scores) / len(total_scores):.1f}점")
    console.print(f"• 최고 점수: {max(total_scores):.1f}점")
    console.print(f"• 최저 점수: {min(total_scores):.1f}점")
    
    # 상세 분석 결과
    console.print(f"\n🔍 [bold]상세 분석 결과[/bold]")
    for market_code, data in all_sector_data.items():
        analysis = analyzer.sector_analyzer.analyze_sector_performance(data)
        console.print(f"\n📊 [bold]{data['market_name']}[/bold]")
        console.print(f"  • 성과점수: {analysis['performance_score']:.1f}점")
        console.print(f"  • 변동성점수: {analysis['volatility_score']:.1f}점")
        console.print(f"  • 유동성점수: {analysis['liquidity_score']:.1f}점")
        console.print(f"  • 심리점수: {analysis['sentiment_score']:.1f}점")
        console.print(f"  • 연중최고가: {data['year_high']:,.2f} ({data['year_high_date']})")
        console.print(f"  • 연중최저가: {data['year_low']:,.2f} ({data['year_low_date']})")

@app.command()
def analyze_stock_detail(
    symbol: str = typer.Option(..., help="분석할 종목코드"),
    dart_key: str = typer.Option(None, help="DART API 키")
):
    """종목의 상세 정보를 분석합니다."""
    analyzer = AdvancedStockAnalyzer(dart_key)
    
    console.print(f"🔍 {symbol} 종목 상세 정보 분석을 시작합니다...")
    
    # 종목 기본 정보 조회
    basic_info = analyzer.stock_info_analyzer.get_stock_basic_info(symbol)
    if not basic_info:
        console.print(f"❌ {symbol} 종목 기본 정보를 조회할 수 없습니다.")
        return
    
    # 종목 특성 분석
    characteristics = analyzer.stock_info_analyzer.analyze_stock_characteristics(basic_info)
    
    # 기본 정보 테이블
    console.print(f"\n📊 [bold]{basic_info['product_name']}[/bold] ({symbol}) 상세 정보")
    
    # 기본 정보
    basic_table = Table(title="기본 정보")
    basic_table.add_column("항목", justify="left", style="cyan")
    basic_table.add_column("값", justify="right", style="white")
    
    basic_table.add_row("종목명", basic_info['product_name'])
    basic_table.add_row("영문명", basic_info.get('product_eng_name', 'N/A'))
    basic_table.add_row("시장", basic_info['market_name'])
    basic_table.add_row("증권그룹", basic_info['security_group_name'])
    basic_table.add_row("주식종류", basic_info['stock_type_name'])
    basic_table.add_row("상장상태", basic_info['listing_status'])
    basic_table.add_row("투자등급", basic_info['investment_grade'])
    
    console.print(basic_table)
    
    # 시장 정보
    market_table = Table(title="시장 정보")
    market_table.add_column("항목", justify="left", style="cyan")
    market_table.add_column("값", justify="right", style="white")
    
    market_table.add_row("상장주수", f"{basic_info['listed_shares']:,}주")
    market_table.add_row("시가총액", f"{basic_info['market_cap']:,.0f}원")
    market_table.add_row("액면가", f"{basic_info['face_value']:,.0f}원")
    market_table.add_row("발행가격", f"{basic_info['issue_price']:,.0f}원")
    market_table.add_row("결산월일", basic_info['settlement_date'])
    market_table.add_row("코스피200", "포함" if basic_info['kospi200_item'] else "미포함")
    
    console.print(market_table)
    
    # 업종 정보
    industry_table = Table(title="업종 정보")
    industry_table.add_column("분류", justify="left", style="cyan")
    industry_table.add_column("코드", justify="center", style="dim")
    industry_table.add_column("명칭", justify="left", style="white")
    
    industry_table.add_row("대분류", basic_info['industry_large_code'], basic_info['industry_large_name'])
    industry_table.add_row("중분류", basic_info['industry_medium_code'], basic_info['industry_medium_name'])
    industry_table.add_row("소분류", basic_info['industry_small_code'], basic_info['industry_small_name'])
    industry_table.add_row("표준산업", basic_info['standard_industry_code'], basic_info['standard_industry_name'])
    
    console.print(industry_table)
    
    # 거래 정보
    trading_table = Table(title="거래 정보")
    trading_table.add_column("항목", justify="left", style="cyan")
    trading_table.add_column("값", justify="right", style="white")
    
    trading_table.add_row("현재가", f"{basic_info['current_price']:,.0f}원")
    trading_table.add_row("전일종가", f"{basic_info['prev_price']:,.0f}원")
    trading_table.add_row("거래정지", "정지" if basic_info['trading_stop'] else "정상")
    trading_table.add_row("관리종목", "관리" if basic_info['admin_item'] else "정상")
    trading_table.add_row("대용가격", f"{basic_info['substitute_price']:,.0f}원")
    trading_table.add_row("외국인한도", f"{basic_info['foreign_personal_limit_rate']:.1f}%")
    
    console.print(trading_table)
    
    # 상장 일자 정보
    listing_table = Table(title="상장 일자 정보")
    listing_table.add_column("시장", justify="left", style="cyan")
    listing_table.add_column("상장일자", justify="center", style="green")
    listing_table.add_column("상장폐지일자", justify="center", style="red")
    
    if basic_info['kospi_listing_date']:
        listing_table.add_row("코스피", basic_info['kospi_listing_date'], basic_info['kospi_delisting_date'] or "-")
    if basic_info['kosdaq_listing_date']:
        listing_table.add_row("코스닥", basic_info['kosdaq_listing_date'], basic_info['kosdaq_delisting_date'] or "-")
    if basic_info['freeboard_listing_date']:
        listing_table.add_row("프리보드", basic_info['freeboard_listing_date'], basic_info['freeboard_delisting_date'] or "-")
    
    console.print(listing_table)
    
    # 특성 분석
    console.print(f"\n🔍 [bold]종목 특성 분석[/bold]")
    console.print(f"• 규모: {characteristics['size_category']}")
    console.print(f"• 시장특성: {characteristics['market_characteristics']}")
    console.print(f"• 업종특성: {characteristics['industry_characteristics']}")
    console.print(f"• 투자특성: {characteristics['investment_characteristics']}")
    console.print(f"• 거래특성: {characteristics['trading_characteristics']}")
    
    # ETF/ETN 정보 (해당하는 경우)
    if basic_info['security_group_id'] in ['EF', 'EN']:
        etf_table = Table(title="ETF/ETN 정보")
        etf_table.add_column("항목", justify="left", style="cyan")
        etf_table.add_column("값", justify="right", style="white")
        
        etf_table.add_row("ETF구분코드", basic_info['etf_division_code'])
        etf_table.add_row("ETF유형코드", basic_info['etf_type_code'])
        etf_table.add_row("ETFCU수량", f"{basic_info['etf_cu_quantity']:,}")
        etf_table.add_row("추적수익률배수", f"{basic_info['etf_tracking_rate']:.2f}")
        etf_table.add_row("투자유의종목", "유의" if basic_info['etf_etn_investment_warning'] else "정상")
        
        console.print(etf_table)

@app.command()
def analyze_balance_sheet(
    symbol: str = typer.Option(..., help="분석할 종목코드"),
    period_type: str = typer.Option("0", help="분류 구분 코드 (0: 년, 1: 분기)"),
    dart_key: str = typer.Option(None, help="DART API 키")
):
    """종목의 대차대조표를 분석합니다."""
    analyzer = AdvancedStockAnalyzer(dart_key)
    
    console.print(f"📊 {symbol} 대차대조표 분석을 시작합니다...")
    
    # 대차대조표 조회
    balance_sheet_data = analyzer.balance_sheet_analyzer.get_balance_sheet(symbol, period_type)
    if not balance_sheet_data:
        console.print(f"❌ {symbol} 대차대조표를 조회할 수 없습니다.")
        return
    
    # 최신 5개 기간 표시
    display_data = balance_sheet_data[:5]
    
    # 대차대조표 테이블
    console.print(f"\n📊 [bold]{symbol}[/bold] 대차대조표 (최신 {len(display_data)}개 기간)")
    
    # 자산 정보 테이블
    assets_table = Table(title="자산 정보")
    assets_table.add_column("기간", justify="center", style="cyan")
    assets_table.add_column("자산총계", justify="right", style="green")
    assets_table.add_column("유동자산", justify="right", style="blue")
    assets_table.add_column("고정자산", justify="right", style="yellow")
    assets_table.add_column("유동자산비율", justify="right", style="dim")
    assets_table.add_column("고정자산비율", justify="right", style="dim")
    
    for data in display_data:
        assets_table.add_row(
            data['period'],
            f"{data['total_assets']:,.0f}",
            f"{data['current_assets']:,.0f}",
            f"{data['fixed_assets']:,.0f}",
            f"{data['current_assets_ratio']:.1f}%",
            f"{data['fixed_assets_ratio']:.1f}%"
        )
    
    console.print(assets_table)
    
    # 부채 및 자본 정보 테이블
    liabilities_table = Table(title="부채 및 자본 정보")
    liabilities_table.add_column("기간", justify="center", style="cyan")
    liabilities_table.add_column("부채총계", justify="right", style="red")
    liabilities_table.add_column("자본총계", justify="right", style="green")
    liabilities_table.add_column("부채비율", justify="right", style="yellow")
    liabilities_table.add_column("자기자본비율", justify="right", style="blue")
    liabilities_table.add_column("유동비율", justify="right", style="purple")
    
    for data in display_data:
        liabilities_table.add_row(
            data['period'],
            f"{data['total_liabilities']:,.0f}",
            f"{data['total_equity']:,.0f}",
            f"{data['debt_ratio']:.1f}%",
            f"{data['equity_ratio']:.1f}%",
            f"{data['current_ratio']:.1f}%"
        )
    
    console.print(liabilities_table)
    
    # 추세 분석
    trend_analysis = analyzer.balance_sheet_analyzer.analyze_balance_sheet_trend(balance_sheet_data)
    
    console.print(f"\n📈 [bold]재무 추세 분석[/bold]")
    
    # 자산 추세
    console.print(f"\n💰 [bold]자산 추세[/bold]")
    console.print(f"• 자산총계 변화: {trend_analysis['assets_trend']['total_assets_change']:+.1f}%")
    console.print(f"• 유동자산 변화: {trend_analysis['assets_trend']['current_assets_change']:+.1f}%")
    console.print(f"• 고정자산 변화: {trend_analysis['assets_trend']['fixed_assets_change']:+.1f}%")
    
    # 부채 추세
    console.print(f"\n💳 [bold]부채 추세[/bold]")
    console.print(f"• 부채총계 변화: {trend_analysis['liabilities_trend']['total_liabilities_change']:+.1f}%")
    console.print(f"• 유동부채 변화: {trend_analysis['liabilities_trend']['current_liabilities_change']:+.1f}%")
    console.print(f"• 고정부채 변화: {trend_analysis['liabilities_trend']['fixed_liabilities_change']:+.1f}%")
    
    # 자본 추세
    console.print(f"\n🏦 [bold]자본 추세[/bold]")
    console.print(f"• 자본총계 변화: {trend_analysis['equity_trend']['total_equity_change']:+.1f}%")
    console.print(f"• 자본금 변화: {trend_analysis['equity_trend']['capital_change']:+.1f}%")
    console.print(f"• 이익잉여금 변화: {trend_analysis['equity_trend']['retained_earnings_change']:+.1f}%")
    
    # 재무 안정성 평가
    stability = trend_analysis['financial_stability']
    console.print(f"\n🛡️ [bold]재무 안정성 평가[/bold]")
    console.print(f"• 부채비율 등급: {stability['debt_ratio_grade']}")
    console.print(f"• 자기자본비율 등급: {stability['equity_ratio_grade']}")
    console.print(f"• 유동비율 등급: {stability['current_ratio_grade']}")
    console.print(f"• 종합 등급: [bold]{stability['overall_grade']}[/bold]")

@app.command()
def compare_balance_sheets(
    symbols: str = typer.Option(..., help="비교할 종목코드들 (쉼표로 구분)"),
    period_type: str = typer.Option("0", help="분류 구분 코드 (0: 년, 1: 분기)"),
    dart_key: str = typer.Option(None, help="DART API 키")
):
    """여러 종목의 대차대조표를 비교합니다."""
    analyzer = AdvancedStockAnalyzer(dart_key)
    symbol_list = [s.strip() for s in symbols.split(',')]
    
    console.print(f"📊 {len(symbol_list)}개 종목의 대차대조표 비교 분석을 시작합니다...")
    
    # 여러 종목의 대차대조표 조회
    balance_sheets = analyzer.balance_sheet_analyzer.get_multiple_balance_sheets(symbol_list, period_type)
    
    if not balance_sheets:
        console.print("❌ 대차대조표를 조회할 수 있는 종목이 없습니다.")
        return
    
    # 비교 테이블 생성
    comparison_df = analyzer.balance_sheet_analyzer.compare_balance_sheets(balance_sheets)
    
    if comparison_df.empty:
        console.print("❌ 비교할 데이터가 없습니다.")
        return
    
    # 비교 결과 테이블
    console.print(f"\n📊 [bold]대차대조표 비교 (최신 기간)[/bold]")
    
    comparison_table = Table(title="종목별 대차대조표 비교")
    comparison_table.add_column("종목코드", justify="center", style="cyan")
    comparison_table.add_column("기간", justify="center", style="dim")
    comparison_table.add_column("자산총계", justify="right", style="green")
    comparison_table.add_column("부채총계", justify="right", style="red")
    comparison_table.add_column("자본총계", justify="right", style="blue")
    comparison_table.add_column("부채비율", justify="right", style="yellow")
    comparison_table.add_column("자기자본비율", justify="right", style="purple")
    comparison_table.add_column("유동비율", justify="right", style="magenta")
    
    for _, row in comparison_df.iterrows():
        comparison_table.add_row(
            row['symbol'],
            row['period'],
            f"{row['total_assets']:,.0f}",
            f"{row['total_liabilities']:,.0f}",
            f"{row['total_equity']:,.0f}",
            f"{row['debt_ratio']:.1f}%",
            f"{row['equity_ratio']:.1f}%",
            f"{row['current_ratio']:.1f}%"
        )
    
    console.print(comparison_table)
    
    # 순위 분석
    console.print(f"\n🏆 [bold]재무 지표 순위[/bold]")
    
    # 부채비율 순위 (낮을수록 좋음)
    debt_ratio_rank = comparison_df.sort_values('debt_ratio').reset_index(drop=True)
    console.print(f"\n💳 부채비율 순위 (낮을수록 우수):")
    for i, (_, row) in enumerate(debt_ratio_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['debt_ratio']:.1f}%")
    
    # 자기자본비율 순위 (높을수록 좋음)
    equity_ratio_rank = comparison_df.sort_values('equity_ratio', ascending=False).reset_index(drop=True)
    console.print(f"\n🏦 자기자본비율 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(equity_ratio_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['equity_ratio']:.1f}%")
    
    # 유동비율 순위 (높을수록 좋음)
    current_ratio_rank = comparison_df.sort_values('current_ratio', ascending=False).reset_index(drop=True)
    console.print(f"\n💧 유동비율 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(current_ratio_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['current_ratio']:.1f}%")

@app.command()
def analyze_income_statement(
    symbol: str = typer.Option(..., help="분석할 종목코드"),
    period_type: str = typer.Option("0", help="분류 구분 코드 (0: 년, 1: 분기)"),
    dart_key: str = typer.Option(None, help="DART API 키")
):
    """종목의 손익계산서를 분석합니다."""
    analyzer = AdvancedStockAnalyzer(dart_key)
    
    console.print(f"📊 {symbol} 손익계산서 분석을 시작합니다...")
    
    # 손익계산서 조회
    income_data = analyzer.income_statement_analyzer.get_income_statement(symbol, period_type)
    if not income_data:
        console.print(f"❌ {symbol} 손익계산서를 조회할 수 없습니다.")
        return
    
    # 최신 5개 기간 표시
    display_data = income_data[:5]
    
    # 손익계산서 테이블
    console.print(f"\n📊 [bold]{symbol}[/bold] 손익계산서 (최신 {len(display_data)}개 기간)")
    
    # 매출 및 수익성 테이블
    revenue_table = Table(title="매출 및 수익성")
    revenue_table.add_column("기간", justify="center", style="cyan")
    revenue_table.add_column("매출액", justify="right", style="green")
    revenue_table.add_column("매출총이익", justify="right", style="blue")
    revenue_table.add_column("영업이익", justify="right", style="yellow")
    revenue_table.add_column("당기순이익", justify="right", style="purple")
    revenue_table.add_column("매출총이익률", justify="right", style="dim")
    revenue_table.add_column("영업이익률", justify="right", style="dim")
    revenue_table.add_column("순이익률", justify="right", style="dim")
    
    for data in display_data:
        revenue_table.add_row(
            data['period'],
            f"{data['revenue']:,.0f}",
            f"{data['gross_profit']:,.0f}",
            f"{data['operating_income']:,.0f}",
            f"{data['net_income']:,.0f}",
            f"{data['gross_profit_margin']:.1f}%",
            f"{data['operating_margin']:.1f}%",
            f"{data['net_margin']:.1f}%"
        )
    
    console.print(revenue_table)
    
    # 상세 손익구조 테이블
    detail_table = Table(title="상세 손익구조")
    detail_table.add_column("기간", justify="center", style="cyan")
    detail_table.add_column("매출원가", justify="right", style="red")
    detail_table.add_column("영업외수익", justify="right", style="blue")
    detail_table.add_column("영업외비용", justify="right", style="red")
    detail_table.add_column("경상이익", justify="right", style="green")
    detail_table.add_column("특별이익", justify="right", style="yellow")
    detail_table.add_column("특별손실", justify="right", style="red")
    
    for data in display_data:
        detail_table.add_row(
            data['period'],
            f"{data['cost_of_sales']:,.0f}",
            f"{data['non_operating_income']:,.0f}",
            f"{data['non_operating_expenses']:,.0f}",
            f"{data['ordinary_income']:,.0f}",
            f"{data['special_income']:,.0f}",
            f"{data['special_loss']:,.0f}"
        )
    
    console.print(detail_table)
    
    # 추세 분석
    trend_analysis = analyzer.income_statement_analyzer.analyze_income_statement_trend(income_data)
    
    console.print(f"\n📈 [bold]수익성 추세 분석[/bold]")
    
    # 매출 추세
    console.print(f"\n💰 [bold]매출 추세[/bold]")
    console.print(f"• 매출 변화: {trend_analysis['revenue_trend']['revenue_change']:+.1f}%")
    console.print(f"• 매출총이익 변화: {trend_analysis['revenue_trend']['gross_profit_change']:+.1f}%")
    console.print(f"• 영업이익 변화: {trend_analysis['revenue_trend']['operating_income_change']:+.1f}%")
    console.print(f"• 순이익 변화: {trend_analysis['revenue_trend']['net_income_change']:+.1f}%")
    
    # 수익성 추세
    console.print(f"\n📊 [bold]수익성 추세[/bold]")
    console.print(f"• 매출총이익률 변화: {trend_analysis['profitability_trend']['gross_margin_change']:+.1f}%p")
    console.print(f"• 영업이익률 변화: {trend_analysis['profitability_trend']['operating_margin_change']:+.1f}%p")
    console.print(f"• 순이익률 변화: {trend_analysis['profitability_trend']['net_margin_change']:+.1f}%p")
    
    # 수익성 평가
    profitability = trend_analysis['profitability_assessment']
    console.print(f"\n🏆 [bold]수익성 평가[/bold]")
    console.print(f"• 매출총이익률 등급: {profitability['gross_margin_grade']}")
    console.print(f"• 영업이익률 등급: {profitability['operating_margin_grade']}")
    console.print(f"• 순이익률 등급: {profitability['net_margin_grade']}")
    console.print(f"• 종합 등급: [bold]{profitability['overall_grade']}[/bold]")
    
    # 성장 품질 분석
    growth_analysis = analyzer.income_statement_analyzer.analyze_growth_quality(income_data)
    
    console.print(f"\n🚀 [bold]성장 품질 분석[/bold]")
    console.print(f"• 매출 성장률: {growth_analysis['revenue_growth']['average_growth']:+.1f}%")
    console.print(f"• 영업이익 성장률: {growth_analysis['operating_growth']['average_growth']:+.1f}%")
    console.print(f"• 순이익 성장률: {growth_analysis['net_growth']['average_growth']:+.1f}%")
    console.print(f"• 성장 일관성: {growth_analysis['revenue_growth']['growth_consistency']}")
    console.print(f"• 성장 품질: [bold]{growth_analysis['growth_quality']}[/bold]")

@app.command()
def compare_income_statements(
    symbols: str = typer.Option(..., help="비교할 종목코드들 (쉼표로 구분)"),
    period_type: str = typer.Option("0", help="분류 구분 코드 (0: 년, 1: 분기)"),
    dart_key: str = typer.Option(None, help="DART API 키")
):
    """여러 종목의 손익계산서를 비교합니다."""
    analyzer = AdvancedStockAnalyzer(dart_key)
    symbol_list = [s.strip() for s in symbols.split(',')]
    
    console.print(f"📊 {len(symbol_list)}개 종목의 손익계산서 비교 분석을 시작합니다...")
    
    # 여러 종목의 손익계산서 조회
    income_statements = analyzer.income_statement_analyzer.get_multiple_income_statements(symbol_list, period_type)
    
    if not income_statements:
        console.print("❌ 손익계산서를 조회할 수 있는 종목이 없습니다.")
        return
    
    # 비교 테이블 생성
    comparison_df = analyzer.income_statement_analyzer.compare_income_statements(income_statements)
    
    if comparison_df.empty:
        console.print("❌ 비교할 데이터가 없습니다.")
        return
    
    # 비교 결과 테이블
    console.print(f"\n📊 [bold]손익계산서 비교 (최신 기간)[/bold]")
    
    comparison_table = Table(title="종목별 손익계산서 비교")
    comparison_table.add_column("종목코드", justify="center", style="cyan")
    comparison_table.add_column("기간", justify="center", style="dim")
    comparison_table.add_column("매출액", justify="right", style="green")
    comparison_table.add_column("영업이익", justify="right", style="yellow")
    comparison_table.add_column("당기순이익", justify="right", style="purple")
    comparison_table.add_column("매출총이익률", justify="right", style="blue")
    comparison_table.add_column("영업이익률", justify="right", style="yellow")
    comparison_table.add_column("순이익률", justify="right", style="purple")
    
    for _, row in comparison_df.iterrows():
        comparison_table.add_row(
            row['symbol'],
            row['period'],
            f"{row['revenue']:,.0f}",
            f"{row['operating_income']:,.0f}",
            f"{row['net_income']:,.0f}",
            f"{row['gross_profit_margin']:.1f}%",
            f"{row['operating_margin']:.1f}%",
            f"{row['net_margin']:.1f}%"
        )
    
    console.print(comparison_table)
    
    # 순위 분석
    console.print(f"\n🏆 [bold]수익성 지표 순위[/bold]")
    
    # 매출액 순위 (높을수록 좋음)
    revenue_rank = comparison_df.sort_values('revenue', ascending=False).reset_index(drop=True)
    console.print(f"\n💰 매출액 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(revenue_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['revenue']:,.0f}원")
    
    # 영업이익률 순위 (높을수록 좋음)
    operating_margin_rank = comparison_df.sort_values('operating_margin', ascending=False).reset_index(drop=True)
    console.print(f"\n📊 영업이익률 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(operating_margin_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['operating_margin']:.1f}%")
    
    # 순이익률 순위 (높을수록 좋음)
    net_margin_rank = comparison_df.sort_values('net_margin', ascending=False).reset_index(drop=True)
    console.print(f"\n💎 순이익률 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(net_margin_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['net_margin']:.1f}%")

@app.command()
def analyze_financial_ratios(
    symbol: str = typer.Option(..., help="분석할 종목코드"),
    period_type: str = typer.Option("0", help="분류 구분 코드 (0: 년, 1: 분기)"),
    dart_key: str = typer.Option(None, help="DART API 키")
):
    """종목의 재무비율을 분석합니다."""
    analyzer = AdvancedStockAnalyzer(dart_key)
    
    console.print(f"📊 {symbol} 재무비율 분석을 시작합니다...")
    
    # 재무비율 조회
    ratio_data = analyzer.financial_ratio_analyzer.get_financial_ratios(symbol, period_type)
    if not ratio_data:
        console.print(f"❌ {symbol} 재무비율을 조회할 수 없습니다.")
        return
    
    # 최신 5개 기간 표시
    display_data = ratio_data[:5]
    
    # 재무비율 테이블
    console.print(f"\n📊 [bold]{symbol}[/bold] 재무비율 (최신 {len(display_data)}개 기간)")
    
    # 수익성 지표 테이블
    profitability_table = Table(title="수익성 지표")
    profitability_table.add_column("기간", justify="center", style="cyan")
    profitability_table.add_column("ROE", justify="right", style="green")
    profitability_table.add_column("ROA", justify="right", style="blue")
    profitability_table.add_column("EPS", justify="right", style="yellow")
    profitability_table.add_column("BPS", justify="right", style="purple")
    profitability_table.add_column("SPS", justify="right", style="magenta")
    
    for data in display_data:
        profitability_table.add_row(
            data['period'],
            f"{data['roe']:.2f}%",
            f"{data['roa']:.2f}%",
            f"{data['eps']:,.0f}원",
            f"{data['bps']:,.0f}원",
            f"{data['sps']:,.0f}원"
        )
    
    console.print(profitability_table)
    
    # 성장성 지표 테이블
    growth_table = Table(title="성장성 지표")
    growth_table.add_column("기간", justify="center", style="cyan")
    growth_table.add_column("매출증가율", justify="right", style="green")
    growth_table.add_column("영업이익증가율", justify="right", style="blue")
    growth_table.add_column("순이익증가율", justify="right", style="yellow")
    growth_table.add_column("성장점수", justify="right", style="purple")
    
    for data in display_data:
        growth_table.add_row(
            data['period'],
            f"{data['revenue_growth_rate']:+.1f}%",
            f"{data['operating_income_growth_rate']:+.1f}%",
            f"{data['net_income_growth_rate']:+.1f}%",
            f"{data['growth_score']:.1f}점"
        )
    
    console.print(growth_table)
    
    # 안정성 지표 테이블
    stability_table = Table(title="안정성 지표")
    stability_table.add_column("기간", justify="center", style="cyan")
    stability_table.add_column("부채비율", justify="right", style="red")
    stability_table.add_column("자기자본비율", justify="right", style="green")
    stability_table.add_column("유보비율", justify="right", style="blue")
    stability_table.add_column("안정성점수", justify="right", style="purple")
    
    for data in display_data:
        stability_table.add_row(
            data['period'],
            f"{data['debt_ratio']:.1f}%",
            f"{data['equity_ratio']:.1f}%",
            f"{data['retained_earnings_ratio']:.1f}%",
            f"{data['stability_score']:.1f}점"
        )
    
    console.print(stability_table)
    
    # 종합 점수 테이블
    total_table = Table(title="종합 점수")
    total_table.add_column("기간", justify="center", style="cyan")
    total_table.add_column("성장성점수", justify="right", style="green")
    total_table.add_column("수익성점수", justify="right", style="blue")
    total_table.add_column("안정성점수", justify="right", style="purple")
    total_table.add_column("종합점수", justify="right", style="bold")
    
    for data in display_data:
        total_table.add_row(
            data['period'],
            f"{data['growth_score']:.1f}점",
            f"{data['profitability_score']:.1f}점",
            f"{data['stability_score']:.1f}점",
            f"{data['total_score']:.1f}점"
        )
    
    console.print(total_table)
    
    # 추세 분석
    trend_analysis = analyzer.financial_ratio_analyzer.analyze_financial_ratio_trend(ratio_data)
    
    console.print(f"\n📈 [bold]재무비율 추세 분석[/bold]")
    
    # 성장률 추세
    console.print(f"\n🚀 [bold]성장률 추세[/bold]")
    console.print(f"• 매출증가율 변화: {trend_analysis['growth_trend']['revenue_growth_change']:+.1f}%p")
    console.print(f"• 영업이익증가율 변화: {trend_analysis['growth_trend']['operating_growth_change']:+.1f}%p")
    console.print(f"• 순이익증가율 변화: {trend_analysis['growth_trend']['net_growth_change']:+.1f}%p")
    
    # 수익성 추세
    console.print(f"\n💰 [bold]수익성 추세[/bold]")
    console.print(f"• ROE 변화: {trend_analysis['profitability_trend']['roe_change']:+.2f}%p")
    console.print(f"• ROA 변화: {trend_analysis['profitability_trend']['roa_change']:+.2f}%p")
    console.print(f"• EPS 변화: {trend_analysis['profitability_trend']['eps_change']:+.0f}원")
    
    # 안정성 추세
    console.print(f"\n🛡️ [bold]안정성 추세[/bold]")
    console.print(f"• 부채비율 변화: {trend_analysis['stability_trend']['debt_ratio_change']:+.1f}%p")
    console.print(f"• 자기자본비율 변화: {trend_analysis['stability_trend']['equity_ratio_change']:+.1f}%p")
    
    # 종합 평가
    overall_assessment = trend_analysis['overall_assessment']
    console.print(f"\n🏆 [bold]종합 재무 평가[/bold]")
    console.print(f"• ROE 등급: {overall_assessment['roe_grade']}")
    console.print(f"• ROA 등급: {overall_assessment['roa_grade']}")
    console.print(f"• 부채비율 등급: {overall_assessment['debt_grade']}")
    console.print(f"• 성장성 등급: {overall_assessment['growth_grade']}")
    console.print(f"• 종합 등급: [bold]{overall_assessment['overall_grade']}[/bold]")
    
    # 투자 매력도 분석
    attractiveness = analyzer.financial_ratio_analyzer.analyze_investment_attractiveness(ratio_data)
    
    console.print(f"\n💎 [bold]투자 매력도 분석[/bold]")
    console.print(f"• 가치 평가: {attractiveness['value_assessment']}")
    console.print(f"• 성장성 평가: {attractiveness['growth_assessment']}")
    console.print(f"• 수익성 평가: {attractiveness['profitability_assessment']}")
    console.print(f"• 안정성 평가: {attractiveness['stability_assessment']}")
    console.print(f"• 종합 매력도: [bold]{attractiveness['overall_attractiveness']}[/bold]")

@app.command()
def compare_financial_ratios(
    symbols: str = typer.Option(..., help="비교할 종목코드들 (쉼표로 구분)"),
    period_type: str = typer.Option("0", help="분류 구분 코드 (0: 년, 1: 분기)"),
    dart_key: str = typer.Option(None, help="DART API 키")
):
    """여러 종목의 재무비율을 비교합니다."""
    analyzer = AdvancedStockAnalyzer(dart_key)
    symbol_list = [s.strip() for s in symbols.split(',')]
    
    console.print(f"📊 {len(symbol_list)}개 종목의 재무비율 비교 분석을 시작합니다...")
    
    # 여러 종목의 재무비율 조회
    financial_ratios = analyzer.financial_ratio_analyzer.get_multiple_financial_ratios(symbol_list, period_type)
    
    if not financial_ratios:
        console.print("❌ 재무비율을 조회할 수 있는 종목이 없습니다.")
        return
    
    # 비교 테이블 생성
    comparison_df = analyzer.financial_ratio_analyzer.compare_financial_ratios(financial_ratios)
    
    if comparison_df.empty:
        console.print("❌ 비교할 데이터가 없습니다.")
        return
    
    # 비교 결과 테이블
    console.print(f"\n📊 [bold]재무비율 비교 (최신 기간)[/bold]")
    
    # 수익성 비교 테이블
    profitability_comparison = Table(title="수익성 지표 비교")
    profitability_comparison.add_column("종목코드", justify="center", style="cyan")
    profitability_comparison.add_column("기간", justify="center", style="dim")
    profitability_comparison.add_column("ROE", justify="right", style="green")
    profitability_comparison.add_column("ROA", justify="right", style="blue")
    profitability_comparison.add_column("EPS", justify="right", style="yellow")
    profitability_comparison.add_column("BPS", justify="right", style="purple")
    profitability_comparison.add_column("수익성점수", justify="right", style="bold")
    
    for _, row in comparison_df.iterrows():
        profitability_comparison.add_row(
            row['symbol'],
            row['period'],
            f"{row['roe']:.2f}%",
            f"{row['roa']:.2f}%",
            f"{row['eps']:,.0f}원",
            f"{row['bps']:,.0f}원",
            f"{row['profitability_score']:.1f}점"
        )
    
    console.print(profitability_comparison)
    
    # 성장성 비교 테이블
    growth_comparison = Table(title="성장성 지표 비교")
    growth_comparison.add_column("종목코드", justify="center", style="cyan")
    growth_comparison.add_column("기간", justify="center", style="dim")
    growth_comparison.add_column("매출증가율", justify="right", style="green")
    growth_comparison.add_column("영업이익증가율", justify="right", style="blue")
    growth_comparison.add_column("순이익증가율", justify="right", style="yellow")
    growth_comparison.add_column("성장점수", justify="right", style="bold")
    
    for _, row in comparison_df.iterrows():
        growth_comparison.add_row(
            row['symbol'],
            row['period'],
            f"{row['revenue_growth_rate']:+.1f}%",
            f"{row['operating_growth_rate']:+.1f}%",
            f"{row['net_growth_rate']:+.1f}%",
            f"{row['growth_score']:.1f}점"
        )
    
    console.print(growth_comparison)
    
    # 안정성 비교 테이블
    stability_comparison = Table(title="안정성 지표 비교")
    stability_comparison.add_column("종목코드", justify="center", style="cyan")
    stability_comparison.add_column("기간", justify="center", style="dim")
    stability_comparison.add_column("부채비율", justify="right", style="red")
    stability_comparison.add_column("자기자본비율", justify="right", style="green")
    stability_comparison.add_column("유보비율", justify="right", style="blue")
    stability_comparison.add_column("안정성점수", justify="right", style="bold")
    
    for _, row in comparison_df.iterrows():
        stability_comparison.add_row(
            row['symbol'],
            row['period'],
            f"{row['debt_ratio']:.1f}%",
            f"{row['equity_ratio']:.1f}%",
            f"{row['retained_earnings_ratio']:.1f}%",
            f"{row['stability_score']:.1f}점"
        )
    
    console.print(stability_comparison)
    
    # 순위 분석
    console.print(f"\n🏆 [bold]재무비율 순위[/bold]")
    
    # ROE 순위 (높을수록 좋음)
    roe_rank = comparison_df.sort_values('roe', ascending=False).reset_index(drop=True)
    console.print(f"\n💰 ROE 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(roe_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['roe']:.2f}%")
    
    # 성장점수 순위 (높을수록 좋음)
    growth_rank = comparison_df.sort_values('growth_score', ascending=False).reset_index(drop=True)
    console.print(f"\n🚀 성장점수 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(growth_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['growth_score']:.1f}점")
    
    # 안정성점수 순위 (높을수록 좋음)
    stability_rank = comparison_df.sort_values('stability_score', ascending=False).reset_index(drop=True)
    console.print(f"\n🛡️ 안정성점수 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(stability_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['stability_score']:.1f}점")
    
    # 종합점수 순위 (높을수록 좋음)
    total_rank = comparison_df.sort_values('total_score', ascending=False).reset_index(drop=True)
    console.print(f"\n⭐ 종합점수 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(total_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['total_score']:.1f}점")

@app.command()
def analyze_profit_ratios(
    symbol: str = typer.Option(..., help="분석할 종목코드"),
    period_type: str = typer.Option("0", help="분류 구분 코드 (0: 년, 1: 분기)"),
    dart_key: str = typer.Option(None, help="DART API 키")
):
    """종목의 수익성비율을 분석합니다."""
    analyzer = AdvancedStockAnalyzer(dart_key)
    
    console.print(f"📊 {symbol} 수익성비율 분석을 시작합니다...")
    
    # 수익성비율 조회
    ratio_data = analyzer.profit_ratio_analyzer.get_profit_ratios(symbol, period_type)
    if not ratio_data:
        console.print(f"❌ {symbol} 수익성비율을 조회할 수 없습니다.")
        return
    
    # 최신 5개 기간 표시
    display_data = ratio_data[:5]
    
    # 수익성비율 테이블
    console.print(f"\n📊 [bold]{symbol}[/bold] 수익성비율 (최신 {len(display_data)}개 기간)")
    
    # 핵심 수익성 지표 테이블
    core_ratios_table = Table(title="핵심 수익성 지표")
    core_ratios_table.add_column("기간", justify="center", style="cyan")
    core_ratios_table.add_column("ROA", justify="right", style="green")
    core_ratios_table.add_column("ROE", justify="right", style="blue")
    core_ratios_table.add_column("순이익률", justify="right", style="yellow")
    core_ratios_table.add_column("총이익률", justify="right", style="purple")
    core_ratios_table.add_column("수익성점수", justify="right", style="bold")
    
    for data in display_data:
        core_ratios_table.add_row(
            data['period'],
            f"{data['roa']:.2f}%",
            f"{data['roe']:.2f}%",
            f"{data['net_profit_margin']:.2f}%",
            f"{data['gross_profit_margin']:.2f}%",
            f"{data['profitability_score']:.1f}점"
        )
    
    console.print(core_ratios_table)
    
    # 수익성 평가 테이블
    evaluation_table = Table(title="수익성 평가")
    evaluation_table.add_column("기간", justify="center", style="cyan")
    evaluation_table.add_column("수익성등급", justify="center", style="green")
    evaluation_table.add_column("안정성", justify="center", style="blue")
    evaluation_table.add_column("종합점수", justify="right", style="bold")
    
    for data in display_data:
        # 등급에 따른 색상 설정
        grade_color = "green" if data['profitability_grade'] == "우수" else "blue" if data['profitability_grade'] == "양호" else "yellow" if data['profitability_grade'] == "보통" else "red"
        stability_color = "green" if "매우 안정" in data['profitability_stability'] else "blue" if "안정" in data['profitability_stability'] else "yellow" if "불안정" in data['profitability_stability'] else "red"
        
        evaluation_table.add_row(
            data['period'],
            f"[{grade_color}]{data['profitability_grade']}[/{grade_color}]",
            f"[{stability_color}]{data['profitability_stability']}[/{stability_color}]",
            f"{data['total_profitability_score']:.1f}점"
        )
    
    console.print(evaluation_table)
    
    # 추세 분석
    trend_analysis = analyzer.profit_ratio_analyzer.analyze_profit_ratio_trend(ratio_data)
    
    console.print(f"\n📈 [bold]수익성비율 추세 분석[/bold]")
    
    # 수익성비율 변화
    console.print(f"\n💰 [bold]수익성비율 변화[/bold]")
    console.print(f"• ROA 변화: {trend_analysis['profit_trend']['roa_change']:+.2f}%p")
    console.print(f"• ROE 변화: {trend_analysis['profit_trend']['roe_change']:+.2f}%p")
    console.print(f"• 순이익률 변화: {trend_analysis['profit_trend']['net_margin_change']:+.2f}%p")
    console.print(f"• 총이익률 변화: {trend_analysis['profit_trend']['gross_margin_change']:+.2f}%p")
    
    # 개선도 및 일관성 평가
    console.print(f"\n📊 [bold]수익성 평가[/bold]")
    console.print(f"• 개선도: {trend_analysis['improvement_assessment']}")
    console.print(f"• 일관성: {trend_analysis['consistency_assessment']}")
    
    # 투자 매력도 분석
    attractiveness = analyzer.profit_ratio_analyzer.analyze_investment_attractiveness(ratio_data)
    
    console.print(f"\n💎 [bold]투자 매력도 분석[/bold]")
    console.print(f"• 수익성 평가: {attractiveness['profitability_assessment']}")
    console.print(f"• 성장성 평가: {attractiveness['growth_assessment']}")
    console.print(f"• 안정성 평가: {attractiveness['stability_assessment']}")
    console.print(f"• 종합 매력도: [bold]{attractiveness['overall_attractiveness']}[/bold]")

@app.command()
def compare_profit_ratios(
    symbols: str = typer.Option(..., help="비교할 종목코드들 (쉼표로 구분)"),
    period_type: str = typer.Option("0", help="분류 구분 코드 (0: 년, 1: 분기)"),
    dart_key: str = typer.Option(None, help="DART API 키")
):
    """여러 종목의 수익성비율을 비교합니다."""
    analyzer = AdvancedStockAnalyzer(dart_key)
    symbol_list = [s.strip() for s in symbols.split(',')]
    
    console.print(f"📊 {len(symbol_list)}개 종목의 수익성비율 비교 분석을 시작합니다...")
    
    # 여러 종목의 수익성비율 조회
    profit_ratios = analyzer.profit_ratio_analyzer.get_multiple_profit_ratios(symbol_list, period_type)
    
    if not profit_ratios:
        console.print("❌ 수익성비율을 조회할 수 있는 종목이 없습니다.")
        return
    
    # 비교 테이블 생성
    comparison_df = analyzer.profit_ratio_analyzer.compare_profit_ratios(profit_ratios)
    
    if comparison_df.empty:
        console.print("❌ 비교할 데이터가 없습니다.")
        return
    
    # 비교 결과 테이블
    console.print(f"\n📊 [bold]수익성비율 비교 (최신 기간)[/bold]")
    
    # 핵심 수익성비율 비교 테이블
    core_comparison = Table(title="핵심 수익성비율 비교")
    core_comparison.add_column("종목코드", justify="center", style="cyan")
    core_comparison.add_column("기간", justify="center", style="dim")
    core_comparison.add_column("ROA", justify="right", style="green")
    core_comparison.add_column("ROE", justify="right", style="blue")
    core_comparison.add_column("순이익률", justify="right", style="yellow")
    core_comparison.add_column("총이익률", justify="right", style="purple")
    core_comparison.add_column("수익성점수", justify="right", style="bold")
    
    for _, row in comparison_df.iterrows():
        core_comparison.add_row(
            row['symbol'],
            row['period'],
            f"{row['roa']:.2f}%",
            f"{row['roe']:.2f}%",
            f"{row['net_profit_margin']:.2f}%",
            f"{row['gross_profit_margin']:.2f}%",
            f"{row['profitability_score']:.1f}점"
        )
    
    console.print(core_comparison)
    
    # 수익성 평가 비교 테이블
    evaluation_comparison = Table(title="수익성 평가 비교")
    evaluation_comparison.add_column("종목코드", justify="center", style="cyan")
    evaluation_comparison.add_column("기간", justify="center", style="dim")
    evaluation_comparison.add_column("수익성등급", justify="center", style="green")
    evaluation_comparison.add_column("안정성", justify="center", style="blue")
    evaluation_comparison.add_column("종합점수", justify="right", style="bold")
    
    for _, row in comparison_df.iterrows():
        # 등급에 따른 색상 설정
        grade_color = "green" if row['profitability_grade'] == "우수" else "blue" if row['profitability_grade'] == "양호" else "yellow" if row['profitability_grade'] == "보통" else "red"
        stability_color = "green" if "매우 안정" in row['profitability_stability'] else "blue" if "안정" in row['profitability_stability'] else "yellow" if "불안정" in row['profitability_stability'] else "red"
        
        evaluation_comparison.add_row(
            row['symbol'],
            row['period'],
            f"[{grade_color}]{row['profitability_grade']}[/{grade_color}]",
            f"[{stability_color}]{row['profitability_stability']}[/{stability_color}]",
            f"{row['total_profitability_score']:.1f}점"
        )
    
    console.print(evaluation_comparison)
    
    # 순위 분석
    console.print(f"\n🏆 [bold]수익성비율 순위[/bold]")
    
    # ROA 순위 (높을수록 좋음)
    roa_rank = comparison_df.sort_values('roa', ascending=False).reset_index(drop=True)
    console.print(f"\n💰 ROA 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(roa_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['roa']:.2f}%")
    
    # ROE 순위 (높을수록 좋음)
    roe_rank = comparison_df.sort_values('roe', ascending=False).reset_index(drop=True)
    console.print(f"\n📈 ROE 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(roe_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['roe']:.2f}%")
    
    # 순이익률 순위 (높을수록 좋음)
    net_margin_rank = comparison_df.sort_values('net_profit_margin', ascending=False).reset_index(drop=True)
    console.print(f"\n💎 순이익률 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(net_margin_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['net_profit_margin']:.2f}%")
    
    # 수익성점수 순위 (높을수록 좋음)
    profitability_rank = comparison_df.sort_values('profitability_score', ascending=False).reset_index(drop=True)
    console.print(f"\n⭐ 수익성점수 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(profitability_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['profitability_score']:.1f}점")
    
    # 종합점수 순위 (높을수록 좋음)
    total_rank = comparison_df.sort_values('total_profitability_score', ascending=False).reset_index(drop=True)
    console.print(f"\n🏆 종합점수 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(total_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['total_profitability_score']:.1f}점")

@app.command()
def analyze_stability_ratios(
    symbol: str = typer.Option(..., help="분석할 종목코드"),
    period_type: str = typer.Option("0", help="분류 구분 코드 (0: 년, 1: 분기)"),
    dart_key: str = typer.Option(None, help="DART API 키")
):
    """종목의 안정성비율을 분석합니다."""
    analyzer = AdvancedStockAnalyzer(dart_key)
    
    console.print(f"📊 {symbol} 안정성비율 분석을 시작합니다...")
    
    # 안정성비율 조회
    ratio_data = analyzer.stability_ratio_analyzer.get_stability_ratios(symbol, period_type)
    if not ratio_data:
        console.print(f"❌ {symbol} 안정성비율을 조회할 수 없습니다.")
        return
    
    # 최신 5개 기간 표시
    display_data = ratio_data[:5]
    
    # 안정성비율 테이블
    console.print(f"\n📊 [bold]{symbol}[/bold] 안정성비율 (최신 {len(display_data)}개 기간)")
    
    # 핵심 안정성 지표 테이블
    core_ratios_table = Table(title="핵심 안정성 지표")
    core_ratios_table.add_column("기간", justify="center", style="cyan")
    core_ratios_table.add_column("부채비율", justify="right", style="red")
    core_ratios_table.add_column("자기자본비율", justify="right", style="green")
    core_ratios_table.add_column("차입금 의존도", justify="right", style="yellow")
    core_ratios_table.add_column("안정성점수", justify="right", style="bold")
    
    for data in display_data:
        core_ratios_table.add_row(
            data['period'],
            f"{data['debt_ratio']:.1f}%",
            f"{data['equity_ratio']:.1f}%",
            f"{data['borrowing_dependency']:.1f}%",
            f"{data['stability_score']:.1f}점"
        )
    
    console.print(core_ratios_table)
    
    # 유동성 지표 테이블
    liquidity_table = Table(title="유동성 지표")
    liquidity_table.add_column("기간", justify="center", style="cyan")
    liquidity_table.add_column("유동비율", justify="right", style="blue")
    liquidity_table.add_column("당좌비율", justify="right", style="purple")
    liquidity_table.add_column("유동성등급", justify="center", style="green")
    
    for data in display_data:
        # 유동성 등급에 따른 색상 설정
        liquidity_color = "green" if "매우 우수" in data['liquidity_grade'] else "blue" if "우수" in data['liquidity_grade'] else "yellow" if "양호" in data['liquidity_grade'] else "red"
        
        liquidity_table.add_row(
            data['period'],
            f"{data['current_ratio']:.1f}%",
            f"{data['quick_ratio']:.1f}%",
            f"[{liquidity_color}]{data['liquidity_grade']}[/{liquidity_color}]"
        )
    
    console.print(liquidity_table)
    
    # 안정성 평가 테이블
    evaluation_table = Table(title="안정성 평가")
    evaluation_table.add_column("기간", justify="center", style="cyan")
    evaluation_table.add_column("안정성등급", justify="center", style="green")
    evaluation_table.add_column("종합점수", justify="right", style="bold")
    
    for data in display_data:
        # 안정성 등급에 따른 색상 설정
        stability_color = "green" if "매우 안정" in data['stability_grade'] else "blue" if "안정" in data['stability_grade'] else "yellow" if "보통" in data['stability_grade'] else "red"
        
        evaluation_table.add_row(
            data['period'],
            f"[{stability_color}]{data['stability_grade']}[/{stability_color}]",
            f"{data['total_stability_score']:.1f}점"
        )
    
    console.print(evaluation_table)
    
    # 추세 분석
    trend_analysis = analyzer.stability_ratio_analyzer.analyze_stability_ratio_trend(ratio_data)
    
    console.print(f"\n📈 [bold]안정성비율 추세 분석[/bold]")
    
    # 안정성비율 변화
    console.print(f"\n🛡️ [bold]안정성비율 변화[/bold]")
    console.print(f"• 부채비율 변화: {trend_analysis['stability_trend']['debt_ratio_change']:+.1f}%p")
    console.print(f"• 자기자본비율 변화: {trend_analysis['stability_trend']['equity_ratio_change']:+.1f}%p")
    console.print(f"• 유동비율 변화: {trend_analysis['stability_trend']['current_ratio_change']:+.1f}%p")
    console.print(f"• 당좌비율 변화: {trend_analysis['stability_trend']['quick_ratio_change']:+.1f}%p")
    console.print(f"• 차입금 의존도 변화: {trend_analysis['stability_trend']['borrowing_dependency_change']:+.1f}%p")
    
    # 개선도 및 일관성 평가
    console.print(f"\n📊 [bold]안정성 평가[/bold]")
    console.print(f"• 개선도: {trend_analysis['improvement_assessment']}")
    console.print(f"• 일관성: {trend_analysis['consistency_assessment']}")
    
    # 투자 매력도 분석
    attractiveness = analyzer.stability_ratio_analyzer.analyze_investment_attractiveness(ratio_data)
    
    console.print(f"\n💎 [bold]투자 매력도 분석[/bold]")
    console.print(f"• 안정성 평가: {attractiveness['stability_assessment']}")
    console.print(f"• 유동성 평가: {attractiveness['liquidity_assessment']}")
    console.print(f"• 부채구조 평가: {attractiveness['debt_structure_assessment']}")
    console.print(f"• 종합 매력도: [bold]{attractiveness['overall_attractiveness']}[/bold]")

@app.command()
def compare_stability_ratios(
    symbols: str = typer.Option(..., help="비교할 종목코드들 (쉼표로 구분)"),
    period_type: str = typer.Option("0", help="분류 구분 코드 (0: 년, 1: 분기)"),
    dart_key: str = typer.Option(None, help="DART API 키")
):
    """여러 종목의 안정성비율을 비교합니다."""
    analyzer = AdvancedStockAnalyzer(dart_key)
    symbol_list = [s.strip() for s in symbols.split(',')]
    
    console.print(f"📊 {len(symbol_list)}개 종목의 안정성비율 비교 분석을 시작합니다...")
    
    # 여러 종목의 안정성비율 조회
    stability_ratios = analyzer.stability_ratio_analyzer.get_multiple_stability_ratios(symbol_list, period_type)
    
    if not stability_ratios:
        console.print("❌ 안정성비율을 조회할 수 있는 종목이 없습니다.")
        return
    
    # 비교 테이블 생성
    comparison_df = analyzer.stability_ratio_analyzer.compare_stability_ratios(stability_ratios)
    
    if comparison_df.empty:
        console.print("❌ 비교할 데이터가 없습니다.")
        return
    
    # 비교 결과 테이블
    console.print(f"\n📊 [bold]안정성비율 비교 (최신 기간)[/bold]")
    
    # 핵심 안정성비율 비교 테이블
    core_comparison = Table(title="핵심 안정성비율 비교")
    core_comparison.add_column("종목코드", justify="center", style="cyan")
    core_comparison.add_column("기간", justify="center", style="dim")
    core_comparison.add_column("부채비율", justify="right", style="red")
    core_comparison.add_column("자기자본비율", justify="right", style="green")
    core_comparison.add_column("차입금 의존도", justify="right", style="yellow")
    core_comparison.add_column("안정성점수", justify="right", style="bold")
    
    for _, row in comparison_df.iterrows():
        core_comparison.add_row(
            row['symbol'],
            row['period'],
            f"{row['debt_ratio']:.1f}%",
            f"{row['equity_ratio']:.1f}%",
            f"{row['borrowing_dependency']:.1f}%",
            f"{row['stability_score']:.1f}점"
        )
    
    console.print(core_comparison)
    
    # 유동성 비교 테이블
    liquidity_comparison = Table(title="유동성 지표 비교")
    liquidity_comparison.add_column("종목코드", justify="center", style="cyan")
    liquidity_comparison.add_column("기간", justify="center", style="dim")
    liquidity_comparison.add_column("유동비율", justify="right", style="blue")
    liquidity_comparison.add_column("당좌비율", justify="right", style="purple")
    liquidity_comparison.add_column("유동성등급", justify="center", style="green")
    
    for _, row in comparison_df.iterrows():
        # 유동성 등급에 따른 색상 설정
        liquidity_color = "green" if "매우 우수" in row['liquidity_grade'] else "blue" if "우수" in row['liquidity_grade'] else "yellow" if "양호" in row['liquidity_grade'] else "red"
        
        liquidity_comparison.add_row(
            row['symbol'],
            row['period'],
            f"{row['current_ratio']:.1f}%",
            f"{row['quick_ratio']:.1f}%",
            f"[{liquidity_color}]{row['liquidity_grade']}[/{liquidity_color}]"
        )
    
    console.print(liquidity_comparison)
    
    # 안정성 평가 비교 테이블
    evaluation_comparison = Table(title="안정성 평가 비교")
    evaluation_comparison.add_column("종목코드", justify="center", style="cyan")
    evaluation_comparison.add_column("기간", justify="center", style="dim")
    evaluation_comparison.add_column("안정성등급", justify="center", style="green")
    evaluation_comparison.add_column("종합점수", justify="right", style="bold")
    
    for _, row in comparison_df.iterrows():
        # 안정성 등급에 따른 색상 설정
        stability_color = "green" if "매우 안정" in row['stability_grade'] else "blue" if "안정" in row['stability_grade'] else "yellow" if "보통" in row['stability_grade'] else "red"
        
        evaluation_comparison.add_row(
            row['symbol'],
            row['period'],
            f"[{stability_color}]{row['stability_grade']}[/{stability_color}]",
            f"{row['total_stability_score']:.1f}점"
        )
    
    console.print(evaluation_comparison)
    
    # 순위 분석
    console.print(f"\n🏆 [bold]안정성비율 순위[/bold]")
    
    # 부채비율 순위 (낮을수록 좋음)
    debt_ratio_rank = comparison_df.sort_values('debt_ratio').reset_index(drop=True)
    console.print(f"\n💳 부채비율 순위 (낮을수록 우수):")
    for i, (_, row) in enumerate(debt_ratio_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['debt_ratio']:.1f}%")
    
    # 자기자본비율 순위 (높을수록 좋음)
    equity_ratio_rank = comparison_df.sort_values('equity_ratio', ascending=False).reset_index(drop=True)
    console.print(f"\n🏦 자기자본비율 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(equity_ratio_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['equity_ratio']:.1f}%")
    
    # 유동비율 순위 (높을수록 좋음)
    current_ratio_rank = comparison_df.sort_values('current_ratio', ascending=False).reset_index(drop=True)
    console.print(f"\n💧 유동비율 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(current_ratio_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['current_ratio']:.1f}%")
    
    # 안정성점수 순위 (높을수록 좋음)
    stability_rank = comparison_df.sort_values('stability_score', ascending=False).reset_index(drop=True)
    console.print(f"\n🛡️ 안정성점수 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(stability_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['stability_score']:.1f}점")
    
    # 종합점수 순위 (높을수록 좋음)
    total_rank = comparison_df.sort_values('total_stability_score', ascending=False).reset_index(drop=True)
    console.print(f"\n⭐ 종합점수 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(total_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['total_stability_score']:.1f}점")

@app.command()
def analyze_growth_ratios(
    symbol: str = typer.Option(..., help="분석할 종목코드"),
    period_type: str = typer.Option("0", help="분류 구분 코드 (0: 년, 1: 분기)"),
    dart_key: str = typer.Option(None, help="DART API 키")
):
    """종목의 성장성비율을 분석합니다."""
    analyzer = AdvancedStockAnalyzer(dart_key)
    
    console.print(f"📊 {symbol} 성장성비율 분석을 시작합니다...")
    
    # 성장성비율 조회
    ratio_data = analyzer.growth_ratio_analyzer.get_growth_ratios(symbol, period_type)
    if not ratio_data:
        console.print(f"❌ {symbol} 성장성비율을 조회할 수 없습니다.")
        return
    
    # 최신 5개 기간 표시
    display_data = ratio_data[:5]
    
    # 성장성비율 테이블
    console.print(f"\n📊 [bold]{symbol}[/bold] 성장성비율 (최신 {len(display_data)}개 기간)")
    
    # 핵심 성장성 지표 테이블
    core_ratios_table = Table(title="핵심 성장성 지표")
    core_ratios_table.add_column("기간", justify="center", style="cyan")
    core_ratios_table.add_column("매출액 증가율", justify="right", style="green")
    core_ratios_table.add_column("영업이익 증가율", justify="right", style="blue")
    core_ratios_table.add_column("자기자본 증가율", justify="right", style="purple")
    core_ratios_table.add_column("총자산 증가율", justify="right", style="yellow")
    
    for data in display_data:
        core_ratios_table.add_row(
            data['period'],
            f"{data['revenue_growth_rate']:+.1f}%",
            f"{data['operating_income_growth_rate']:+.1f}%",
            f"{data['equity_growth_rate']:+.1f}%",
            f"{data['total_asset_growth_rate']:+.1f}%"
        )
    
    console.print(core_ratios_table)
    
    # 성장성 평가 테이블
    evaluation_table = Table(title="성장성 평가")
    evaluation_table.add_column("기간", justify="center", style="cyan")
    evaluation_table.add_column("성장성점수", justify="right", style="bold")
    evaluation_table.add_column("성장성등급", justify="center", style="green")
    evaluation_table.add_column("성장성안정성", justify="center", style="blue")
    evaluation_table.add_column("성장성품질", justify="center", style="purple")
    
    for data in display_data:
        # 성장성 등급에 따른 색상 설정
        growth_color = "green" if "매우 우수" in data['growth_grade'] else "blue" if "우수" in data['growth_grade'] else "yellow" if "양호" in data['growth_grade'] else "red"
        
        # 성장성 안정성에 따른 색상 설정
        stability_color = "green" if "매우 안정" in data['growth_stability'] else "blue" if "안정" in data['growth_stability'] else "yellow" if "보통" in data['growth_stability'] else "red"
        
        # 성장성 품질에 따른 색상 설정
        quality_color = "green" if "매우 우수" in data['growth_quality'] else "blue" if "우수" in data['growth_quality'] else "yellow" if "양호" in data['growth_quality'] else "red"
        
        evaluation_table.add_row(
            data['period'],
            f"{data['growth_score']:.1f}점",
            f"[{growth_color}]{data['growth_grade']}[/{growth_color}]",
            f"[{stability_color}]{data['growth_stability']}[/{stability_color}]",
            f"[{quality_color}]{data['growth_quality']}[/{quality_color}]"
        )
    
    console.print(evaluation_table)
    
    # 종합 점수 테이블
    total_score_table = Table(title="종합 성장성 점수")
    total_score_table.add_column("기간", justify="center", style="cyan")
    total_score_table.add_column("종합점수", justify="right", style="bold")
    
    for data in display_data:
        total_score_table.add_row(
            data['period'],
            f"{data['total_growth_score']:.1f}점"
        )
    
    console.print(total_score_table)
    
    # 추세 분석
    trend_analysis = analyzer.growth_ratio_analyzer.analyze_growth_ratio_trend(ratio_data)
    
    console.print(f"\n📈 [bold]성장성비율 추세 분석[/bold]")
    
    # 성장성비율 변화
    console.print(f"\n🚀 [bold]성장성비율 변화[/bold]")
    console.print(f"• 매출 증가율 변화: {trend_analysis['growth_trend']['revenue_growth_change']:+.1f}%p")
    console.print(f"• 영업이익 증가율 변화: {trend_analysis['growth_trend']['operating_growth_change']:+.1f}%p")
    console.print(f"• 자기자본 증가율 변화: {trend_analysis['growth_trend']['equity_growth_change']:+.1f}%p")
    console.print(f"• 총자산 증가율 변화: {trend_analysis['growth_trend']['asset_growth_change']:+.1f}%p")
    
    # 개선도, 일관성, 가속도 평가
    console.print(f"\n📊 [bold]성장성 평가[/bold]")
    console.print(f"• 개선도: {trend_analysis['improvement_assessment']}")
    console.print(f"• 일관성: {trend_analysis['consistency_assessment']}")
    console.print(f"• 가속도: {trend_analysis['acceleration_assessment']}")
    
    # 투자 매력도 분석
    attractiveness = analyzer.growth_ratio_analyzer.analyze_investment_attractiveness(ratio_data)
    
    console.print(f"\n💎 [bold]투자 매력도 분석[/bold]")
    console.print(f"• 성장성 평가: {attractiveness['growth_assessment']}")
    console.print(f"• 수익성 성장 평가: {attractiveness['profitability_growth_assessment']}")
    console.print(f"• 자본 효율성 평가: {attractiveness['capital_efficiency_assessment']}")
    console.print(f"• 종합 매력도: [bold]{attractiveness['overall_attractiveness']}[/bold]")

@app.command()
def compare_growth_ratios(
    symbols: str = typer.Option(..., help="비교할 종목코드들 (쉼표로 구분)"),
    period_type: str = typer.Option("0", help="분류 구분 코드 (0: 년, 1: 분기)"),
    dart_key: str = typer.Option(None, help="DART API 키")
):
    """여러 종목의 성장성비율을 비교합니다."""
    analyzer = AdvancedStockAnalyzer(dart_key)
    symbol_list = [s.strip() for s in symbols.split(',')]
    
    console.print(f"📊 {len(symbol_list)}개 종목의 성장성비율 비교 분석을 시작합니다...")
    
    # 여러 종목의 성장성비율 조회
    growth_ratios = analyzer.growth_ratio_analyzer.get_multiple_growth_ratios(symbol_list, period_type)
    
    if not growth_ratios:
        console.print("❌ 성장성비율을 조회할 수 있는 종목이 없습니다.")
        return
    
    # 비교 테이블 생성
    comparison_df = analyzer.growth_ratio_analyzer.compare_growth_ratios(growth_ratios)
    
    if comparison_df.empty:
        console.print("❌ 비교할 데이터가 없습니다.")
        return
    
    # 비교 결과 테이블
    console.print(f"\n📊 [bold]성장성비율 비교 (최신 기간)[/bold]")
    
    # 핵심 성장성비율 비교 테이블
    core_comparison = Table(title="핵심 성장성비율 비교")
    core_comparison.add_column("종목코드", justify="center", style="cyan")
    core_comparison.add_column("기간", justify="center", style="dim")
    core_comparison.add_column("매출액 증가율", justify="right", style="green")
    core_comparison.add_column("영업이익 증가율", justify="right", style="blue")
    core_comparison.add_column("자기자본 증가율", justify="right", style="purple")
    core_comparison.add_column("총자산 증가율", justify="right", style="yellow")
    
    for _, row in comparison_df.iterrows():
        core_comparison.add_row(
            row['symbol'],
            row['period'],
            f"{row['revenue_growth_rate']:+.1f}%",
            f"{row['operating_income_growth_rate']:+.1f}%",
            f"{row['equity_growth_rate']:+.1f}%",
            f"{row['total_asset_growth_rate']:+.1f}%"
        )
    
    console.print(core_comparison)
    
    # 성장성 평가 비교 테이블
    evaluation_comparison = Table(title="성장성 평가 비교")
    evaluation_comparison.add_column("종목코드", justify="center", style="cyan")
    evaluation_comparison.add_column("기간", justify="center", style="dim")
    evaluation_comparison.add_column("성장성점수", justify="right", style="bold")
    evaluation_comparison.add_column("성장성등급", justify="center", style="green")
    evaluation_comparison.add_column("성장성안정성", justify="center", style="blue")
    evaluation_comparison.add_column("성장성품질", justify="center", style="purple")
    
    for _, row in comparison_df.iterrows():
        # 성장성 등급에 따른 색상 설정
        growth_color = "green" if "매우 우수" in row['growth_grade'] else "blue" if "우수" in row['growth_grade'] else "yellow" if "양호" in row['growth_grade'] else "red"
        
        # 성장성 안정성에 따른 색상 설정
        stability_color = "green" if "매우 안정" in row['growth_stability'] else "blue" if "안정" in row['growth_stability'] else "yellow" if "보통" in row['growth_stability'] else "red"
        
        # 성장성 품질에 따른 색상 설정
        quality_color = "green" if "매우 우수" in row['growth_quality'] else "blue" if "우수" in row['growth_quality'] else "yellow" if "양호" in row['growth_quality'] else "red"
        
        evaluation_comparison.add_row(
            row['symbol'],
            row['period'],
            f"{row['growth_score']:.1f}점",
            f"[{growth_color}]{row['growth_grade']}[/{growth_color}]",
            f"[{stability_color}]{row['growth_stability']}[/{stability_color}]",
            f"[{quality_color}]{row['growth_quality']}[/{quality_color}]"
        )
    
    console.print(evaluation_comparison)
    
    # 종합 점수 비교 테이블
    total_score_comparison = Table(title="종합 성장성 점수 비교")
    total_score_comparison.add_column("종목코드", justify="center", style="cyan")
    total_score_comparison.add_column("기간", justify="center", style="dim")
    total_score_comparison.add_column("종합점수", justify="right", style="bold")
    
    for _, row in comparison_df.iterrows():
        total_score_comparison.add_row(
            row['symbol'],
            row['period'],
            f"{row['total_growth_score']:.1f}점"
        )
    
    console.print(total_score_comparison)
    
    # 순위 분석
    console.print(f"\n🏆 [bold]성장성비율 순위[/bold]")
    
    # 매출액 증가율 순위 (높을수록 좋음)
    revenue_rank = comparison_df.sort_values('revenue_growth_rate', ascending=False).reset_index(drop=True)
    console.print(f"\n📈 매출액 증가율 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(revenue_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['revenue_growth_rate']:+.1f}%")
    
    # 영업이익 증가율 순위 (높을수록 좋음)
    operating_rank = comparison_df.sort_values('operating_income_growth_rate', ascending=False).reset_index(drop=True)
    console.print(f"\n💰 영업이익 증가율 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(operating_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['operating_income_growth_rate']:+.1f}%")
    
    # 자기자본 증가율 순위 (높을수록 좋음)
    equity_rank = comparison_df.sort_values('equity_growth_rate', ascending=False).reset_index(drop=True)
    console.print(f"\n🏦 자기자본 증가율 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(equity_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['equity_growth_rate']:+.1f}%")
    
    # 총자산 증가율 순위 (높을수록 좋음)
    asset_rank = comparison_df.sort_values('total_asset_growth_rate', ascending=False).reset_index(drop=True)
    console.print(f"\n📊 총자산 증가율 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(asset_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['total_asset_growth_rate']:+.1f}%")
    
    # 성장성점수 순위 (높을수록 좋음)
    growth_rank = comparison_df.sort_values('growth_score', ascending=False).reset_index(drop=True)
    console.print(f"\n🚀 성장성점수 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(growth_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['growth_score']:.1f}점")
    
    # 종합점수 순위 (높을수록 좋음)
    total_rank = comparison_df.sort_values('total_growth_score', ascending=False).reset_index(drop=True)
    console.print(f"\n⭐ 종합점수 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(total_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']}: {row['total_growth_score']:.1f}점")

@app.command()
def analyze_estimate_performance(
    symbol: str = typer.Option(..., help="분석할 종목코드"),
    dart_key: str = typer.Option(None, help="DART API 키")
):
    """종목의 추정실적을 분석합니다."""
    analyzer = AdvancedStockAnalyzer(dart_key)
    
    console.print(f"📊 {symbol} 추정실적 분석을 시작합니다...")
    
    # 추정실적 조회
    performance_data = analyzer.estimate_performance_analyzer.get_estimate_performance(symbol)
    if not performance_data:
        console.print(f"❌ {symbol} 추정실적을 조회할 수 없습니다.")
        return
    
    # 기본 정보
    if 'basic_info' in performance_data:
        basic = performance_data['basic_info']
        console.print(f"\n📈 [bold]{basic.get('name', '')}[/bold] 기본 정보")
        console.print(f"• 현재가: {basic.get('current_price', 0):,.0f}원")
        console.print(f"• 전일대비: {basic.get('price_change', 0):+,.0f}원 ({basic.get('price_change_rate', 0):+.2f}%)")
        volume = basic.get('volume', 0)
        volume_k = volume / 1000 if volume > 0 else 0
        console.print(f"• 거래량: {volume_k:,.0f}K주 ({volume:,.0f}주)")
    
    # 추정손익계산서
    if 'income_statement' in performance_data:
        income = performance_data['income_statement']
        periods = performance_data.get('periods', [''] * 5)
        
        console.print(f"\n💰 [bold]추정손익계산서 (최신 5개 기간)[/bold]")
        
        # 매출액 테이블
        revenue_table = Table(title="매출액 및 증가율")
        revenue_table.add_column("기간", justify="center", style="cyan")
        revenue_table.add_column("매출액", justify="right", style="green")
        revenue_table.add_column("매출증가율", justify="right", style="blue")
        
        for i in range(5):
            if i < len(periods):
                revenue_table.add_row(
                    periods[i],
                    f"{income.get('revenue', [0])[i]:,.0f}억원",
                    f"{income.get('revenue_growth_rate', [0])[i]:+.1f}%"
                )
        
        console.print(revenue_table)
        
        # 영업이익 테이블
        operating_table = Table(title="영업이익 및 증가율")
        operating_table.add_column("기간", justify="center", style="cyan")
        operating_table.add_column("영업이익", justify="right", style="green")
        operating_table.add_column("영업이익증가율", justify="right", style="blue")
        
        for i in range(5):
            if i < len(periods):
                operating_table.add_row(
                    periods[i],
                    f"{income.get('operating_income', [0])[i]:,.0f}억원",
                    f"{income.get('operating_income_growth_rate', [0])[i]:+.1f}%"
                )
        
        console.print(operating_table)
        
        # 순이익 테이블
        net_table = Table(title="순이익 및 증가율")
        net_table.add_column("기간", justify="center", style="cyan")
        net_table.add_column("순이익", justify="right", style="green")
        net_table.add_column("순이익증가율", justify="right", style="blue")
        
        for i in range(5):
            if i < len(periods):
                net_table.add_row(
                    periods[i],
                    f"{income.get('net_income', [0])[i]:,.0f}억원",
                    f"{income.get('net_income_growth_rate', [0])[i]:+.1f}%"
                )
        
        console.print(net_table)
    
    # 투자지표
    if 'investment_metrics' in performance_data:
        metrics = performance_data['investment_metrics']
        periods = performance_data.get('periods', [''] * 5)
        
        console.print(f"\n📊 [bold]투자지표 (최신 5개 기간)[/bold]")
        
        # 수익성 지표 테이블
        profitability_table = Table(title="수익성 지표")
        profitability_table.add_column("기간", justify="center", style="cyan")
        profitability_table.add_column("EBITDA", justify="right", style="green")
        profitability_table.add_column("EPS", justify="right", style="blue")
        profitability_table.add_column("EPS증가율", justify="right", style="purple")
        profitability_table.add_column("ROE", justify="right", style="yellow")
        
        for i in range(5):
            if i < len(periods):
                profitability_table.add_row(
                    periods[i],
                    f"{metrics.get('ebitda', [0])[i]:,.0f}억원",
                    f"{metrics.get('eps', [0])[i]:,.0f}원",
                    f"{metrics.get('eps_growth_rate', [0])[i]:+.1f}%",
                    f"{metrics.get('roe', [0])[i]:.1f}%"
                )
        
        console.print(profitability_table)
        
        # 가치평가 지표 테이블
        valuation_table = Table(title="가치평가 지표")
        valuation_table.add_column("기간", justify="center", style="cyan")
        valuation_table.add_column("PER", justify="right", style="green")
        valuation_table.add_column("EV/EBITDA", justify="right", style="blue")
        valuation_table.add_column("부채비율", justify="right", style="purple")
        valuation_table.add_column("이자보상배율", justify="right", style="yellow")
        
        for i in range(5):
            if i < len(periods):
                valuation_table.add_row(
                    periods[i],
                    f"{metrics.get('per', [0])[i]:.1f}배",
                    f"{metrics.get('ev_ebitda', [0])[i]:.1f}배",
                    f"{metrics.get('debt_ratio', [0])[i]:.1f}%",
                    f"{metrics.get('interest_coverage_ratio', [0])[i]:.1f}배"
                )
        
        console.print(valuation_table)
    
    # 분석 결과
    if 'analysis' in performance_data:
        analysis = performance_data['analysis']
        
        console.print(f"\n🔍 [bold]분석 결과[/bold]")
        console.print(f"• 종합 투자 매력도: [bold]{analysis.get('overall_attractiveness', '평가불가')}[/bold]")
        
        # 성장성 분석
        if 'growth_analysis' in analysis:
            growth = analysis['growth_analysis']
            console.print(f"\n📈 [bold]성장성 분석[/bold]")
            console.print(f"• 매출 성장률 등급: {growth.get('revenue_growth_grade', '평가불가')}")
            console.print(f"• 영업이익 성장률 등급: {growth.get('operating_growth_grade', '평가불가')}")
            console.print(f"• 순이익 성장률 등급: {growth.get('net_growth_grade', '평가불가')}")
        
        # 수익성 분석
        if 'profitability_analysis' in analysis:
            profit = analysis['profitability_analysis']
            console.print(f"\n💰 [bold]수익성 분석[/bold]")
            console.print(f"• ROE 등급: {profit.get('roe_grade', '평가불가')}")
            console.print(f"• EPS 등급: {profit.get('eps_grade', '평가불가')}")
            console.print(f"• EBITDA 등급: {profit.get('ebitda_grade', '평가불가')}")
        
        # 가치 평가 분석
        if 'valuation_analysis' in analysis:
            valuation = analysis['valuation_analysis']
            console.print(f"\n💎 [bold]가치 평가 분석[/bold]")
            console.print(f"• PER 등급: {valuation.get('per_grade', '평가불가')}")
            console.print(f"• EV/EBITDA 등급: {valuation.get('ev_ebitda_grade', '평가불가')}")
        
        # 안정성 분석
        if 'stability_analysis' in analysis:
            stability = analysis['stability_analysis']
            console.print(f"\n🛡️ [bold]안정성 분석[/bold]")
            console.print(f"• 부채비율 등급: {stability.get('debt_ratio_grade', '평가불가')}")
            console.print(f"• 이자보상배율 등급: {stability.get('interest_coverage_grade', '평가불가')}")

@app.command()
def compare_estimate_performance(
    symbols: str = typer.Option(..., help="비교할 종목코드들 (쉼표로 구분)"),
    dart_key: str = typer.Option(None, help="DART API 키")
):
    """여러 종목의 추정실적을 비교합니다."""
    analyzer = AdvancedStockAnalyzer(dart_key)
    symbol_list = [s.strip() for s in symbols.split(',')]
    
    console.print(f"📊 {len(symbol_list)}개 종목의 추정실적 비교 분석을 시작합니다...")
    
    # 여러 종목의 추정실적 조회
    performance_data = analyzer.estimate_performance_analyzer.get_multiple_estimate_performance(symbol_list)
    
    if not performance_data:
        console.print("❌ 추정실적을 조회할 수 있는 종목이 없습니다.")
        return
    
    # 비교 테이블 생성
    comparison_df = analyzer.estimate_performance_analyzer.compare_estimate_performance(performance_data)
    
    if comparison_df.empty:
        console.print("❌ 비교할 데이터가 없습니다.")
        return
    
    # 비교 결과 테이블
    console.print(f"\n📊 [bold]추정실적 비교 (최신 기간)[/bold]")
    
    # 기본 정보 비교 테이블
    basic_comparison = Table(title="기본 정보 비교")
    basic_comparison.add_column("종목코드", justify="center", style="cyan")
    basic_comparison.add_column("종목명", justify="center", style="green")
    basic_comparison.add_column("현재가", justify="right", style="blue")
    basic_comparison.add_column("전일대비율", justify="right", style="purple")
    
    for _, row in comparison_df.iterrows():
        basic_comparison.add_row(
            row['symbol'],
            row['name'],
            f"{row['current_price']:,.0f}원",
            f"{row['price_change_rate']:+.2f}%"
        )
    
    console.print(basic_comparison)
    
    # 투자지표 비교 테이블
    metrics_comparison = Table(title="투자지표 비교")
    metrics_comparison.add_column("종목코드", justify="center", style="cyan")
    metrics_comparison.add_column("종목명", justify="center", style="green")
    metrics_comparison.add_column("ROE", justify="right", style="blue")
    metrics_comparison.add_column("EPS", justify="right", style="purple")
    metrics_comparison.add_column("PER", justify="right", style="yellow")
    metrics_comparison.add_column("EV/EBITDA", justify="right", style="red")
    metrics_comparison.add_column("부채비율", justify="right", style="orange")
    
    for _, row in comparison_df.iterrows():
        metrics_comparison.add_row(
            row['symbol'],
            row['name'],
            f"{row['latest_roe']:.1f}%",
            f"{row['latest_eps']:,.0f}원",
            f"{row['latest_per']:.1f}배",
            f"{row['latest_ev_ebitda']:.1f}배",
            f"{row['latest_debt_ratio']:.1f}%"
        )
    
    console.print(metrics_comparison)
    
    # 투자 매력도 비교 테이블
    attractiveness_comparison = Table(title="투자 매력도 비교")
    attractiveness_comparison.add_column("종목코드", justify="center", style="cyan")
    attractiveness_comparison.add_column("종목명", justify="center", style="green")
    attractiveness_comparison.add_column("종합 매력도", justify="center", style="bold")
    
    for _, row in comparison_df.iterrows():
        # 매력도에 따른 색상 설정
        attractiveness_color = "green" if "매우 매력적" in row['overall_attractiveness'] else "blue" if "매력적" in row['overall_attractiveness'] else "yellow" if "보통" in row['overall_attractiveness'] else "red"
        
        attractiveness_comparison.add_row(
            row['symbol'],
            row['name'],
            f"[{attractiveness_color}]{row['overall_attractiveness']}[/{attractiveness_color}]"
        )
    
    console.print(attractiveness_comparison)
    
    # 순위 분석
    console.print(f"\n🏆 [bold]추정실적 순위[/bold]")
    
    # ROE 순위 (높을수록 좋음)
    roe_rank = comparison_df.sort_values('latest_roe', ascending=False).reset_index(drop=True)
    console.print(f"\n📈 ROE 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(roe_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']} ({row['name']}): {row['latest_roe']:.1f}%")
    
    # EPS 순위 (높을수록 좋음)
    eps_rank = comparison_df.sort_values('latest_eps', ascending=False).reset_index(drop=True)
    console.print(f"\n💰 EPS 순위 (높을수록 우수):")
    for i, (_, row) in enumerate(eps_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']} ({row['name']}): {row['latest_eps']:,.0f}원")
    
    # PER 순위 (낮을수록 좋음)
    per_rank = comparison_df.sort_values('latest_per').reset_index(drop=True)
    console.print(f"\n💎 PER 순위 (낮을수록 우수):")
    for i, (_, row) in enumerate(per_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']} ({row['name']}): {row['latest_per']:.1f}배")
    
    # EV/EBITDA 순위 (낮을수록 좋음)
    ev_ebitda_rank = comparison_df.sort_values('latest_ev_ebitda').reset_index(drop=True)
    console.print(f"\n📊 EV/EBITDA 순위 (낮을수록 우수):")
    for i, (_, row) in enumerate(ev_ebitda_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']} ({row['name']}): {row['latest_ev_ebitda']:.1f}배")
    
    # 부채비율 순위 (낮을수록 좋음)
    debt_rank = comparison_df.sort_values('latest_debt_ratio').reset_index(drop=True)
    console.print(f"\n🛡️ 부채비율 순위 (낮을수록 우수):")
    for i, (_, row) in enumerate(debt_rank.iterrows(), 1):
        console.print(f"  {i}. {row['symbol']} ({row['name']}): {row['latest_debt_ratio']:.1f}%")

@app.command()
def find_undervalued_stocks(
    count: int = typer.Option(10, help="분석할 종목 수 (기본값: 10개)"),
    display: int = typer.Option(10, help="표시할 결과 수 (기본값: 10개)"),
    dart_key: str = typer.Option(None, help="DART API 키"),
    min_market_cap: float = typer.Option(500, help="최소 시가총액 (억원, 기본값: 500억원)"),
    max_per: float = typer.Option(25, help="최대 PER (기본값: 25배)"),
    min_roe: float = typer.Option(5, help="최소 ROE (%, 기본값: 5%)"),
    max_debt_ratio: float = typer.Option(150, help="최대 부채비율 (%, 기본값: 150%)")
):
    """종합적인 저평가 가치주를 발굴합니다."""
    analyzer = AdvancedStockAnalyzer(dart_key)
    
    console.print(f"🔍 [bold]종합 저평가 가치주 발굴 시스템[/bold]")
    console.print(f"📊 분석 대상: 시가총액 상위 {count}개 종목")
    console.print(f"📈 필터 조건: PER ≤ {max_per}배, ROE ≥ {min_roe}%, 부채비율 ≤ {max_debt_ratio}%")
    console.print(f"💰 최소 시가총액: {min_market_cap:,}억원")
    
    # 1단계: 시가총액 상위 종목 선별
    console.print(f"\n📊 [bold]1단계: 시가총액 상위 종목 선별[/bold]")
    
    if analyzer.kospi_data is None or analyzer.kospi_data.empty:
        console.print("❌ KOSPI 데이터를 로드할 수 없습니다.")
        return
    
    # 시가총액 기준으로 정렬하고 필터링 (우선주 제외)
    filtered_stocks = analyzer.kospi_data[
        (analyzer.kospi_data['시가총액'] >= min_market_cap) &
        (~analyzer.kospi_data['한글명'].str.contains('우$', na=False))  # 우선주 제외
    ].nlargest(count, '시가총액')
    
    console.print(f"✅ {len(filtered_stocks)}개 종목 선별 완료")
    
    # 2단계: 각 종목의 종합 분석 수행 (순차적 조회)
    console.print(f"\n🔍 [bold]2단계: 종합 분석 수행 (순차적 조회)[/bold]")
    
    analysis_results = []
    
    with Progress() as progress:
        task = progress.add_task("분석 진행 중...", total=len(filtered_stocks))
        
        for idx, (_, stock) in enumerate(filtered_stocks.iterrows()):
            symbol = stock['단축코드']
            name = stock['한글명']
            market_cap = stock['시가총액']
            
            progress.update(task, description=f"분석 중: {name} ({symbol})")
            
            # 최소한의 종목 간 대기 (1초) - API 서버 연결 안정성
            if idx > 0:
                time.sleep(1.0)
            
            try:
                # 기본 정보
                stock_info = {
                    'symbol': symbol,
                    'name': name,
                    'market_cap': market_cap,
                    'sector': str(stock.get('지수업종대분류', '')),
                    'score': 0,
                    'analysis_details': {}
                }
                
                # 1. 현재가 및 기본 정보 조회 (향상된 프로바이더 사용)
                try:
                    # 향상된 가격 프로바이더로 종합 데이터 조회
                    price_data = analyzer.price_provider.get_comprehensive_price_data(symbol)
                    
                    if price_data and price_data.get('current_price'):
                        stock_info.update({
                            'current_price': price_data.get('current_price', 0),
                            'price_change': price_data.get('price_change', 0),
                            'price_change_rate': price_data.get('price_change_rate', 0),
                            'per': price_data.get('per', 0),
                            'pbr': price_data.get('pbr', 0),
                            'volume': price_data.get('volume', 0)
                        })
                        console.print(f"✅ {name} ({symbol}) 현재가: {price_data.get('current_price', 0):,}원")
                    else:
                        console.print(f"⚠️ {name} ({symbol}) 현재가 조회 실패 - 데이터 없음")
                        
                except Exception as e:
                    console.print(f"❌ {name} ({symbol}) 현재가 조회 실패: {e}")
                    pass
                
                # 2. 재무비율 분석
                time.sleep(2.5)  # API 호출 간 대기 (연결 안정성 강화)
                try:
                    financial_ratios = analyzer.financial_ratio_analyzer.get_financial_ratios(symbol)
                    if financial_ratios and len(financial_ratios) > 0:
                        latest_ratios = financial_ratios[0]
                        stock_info.update({
                            'roe': latest_ratios.get('roe', 0),
                            'roa': latest_ratios.get('roa', 0),
                            'debt_ratio': latest_ratios.get('debt_ratio', 0),
                            'equity_ratio': latest_ratios.get('equity_ratio', 0),
                            'revenue_growth_rate': latest_ratios.get('revenue_growth_rate', 0),
                            'operating_income_growth_rate': latest_ratios.get('operating_income_growth_rate', 0),
                            'net_income_growth_rate': latest_ratios.get('net_income_growth_rate', 0)
                        })
                except:
                    pass
                
                # 3. 수익성비율 분석
                time.sleep(2.5)  # API 호출 간 대기 (연결 안정성 강화)
                try:
                    profit_ratios = analyzer.profit_ratio_analyzer.get_profit_ratios(symbol)
                    if profit_ratios and len(profit_ratios) > 0:
                        latest_profit = profit_ratios[0]
                        stock_info.update({
                            'net_profit_margin': latest_profit.get('net_profit_margin', 0),
                            'gross_profit_margin': latest_profit.get('gross_profit_margin', 0),
                            'profitability_grade': latest_profit.get('profitability_grade', '평가불가')
                        })
                except:
                    pass
                
                # 4. 안정성비율 분석
                time.sleep(2.5)  # API 호출 간 대기 (연결 안정성 강화)
                try:
                    stability_ratios = analyzer.stability_ratio_analyzer.get_stability_ratios(symbol)
                    if stability_ratios and len(stability_ratios) > 0:
                        latest_stability = stability_ratios[0]
                        stock_info.update({
                            'current_ratio': latest_stability.get('current_ratio', 0),
                            'quick_ratio': latest_stability.get('quick_ratio', 0),
                            'borrowing_dependency': latest_stability.get('borrowing_dependency', 0),
                            'stability_grade': latest_stability.get('stability_grade', '평가불가')
                        })
                except:
                    pass
                
                # 5. 성장성비율 분석
                time.sleep(2.5)  # API 호출 간 대기 (연결 안정성 강화)
                try:
                    growth_ratios = analyzer.growth_ratio_analyzer.get_growth_ratios(symbol)
                    if growth_ratios and len(growth_ratios) > 0:
                        latest_growth = growth_ratios[0]
                        stock_info.update({
                            'revenue_growth_rate_annual': latest_growth.get('revenue_growth_rate', 0),
                            'operating_income_growth_rate_annual': latest_growth.get('operating_income_growth_rate', 0),
                            'equity_growth_rate': latest_growth.get('equity_growth_rate', 0),
                            'total_asset_growth_rate': latest_growth.get('total_asset_growth_rate', 0),
                            'growth_grade': latest_growth.get('growth_grade', '평가불가')
                        })
                except:
                    pass
                
                # 6. 추정실적 분석
                time.sleep(2.5)  # API 호출 간 대기 (연결 안정성 강화)
                try:
                    estimate_performance = analyzer.estimate_performance_analyzer.get_estimate_performance(symbol)
                    if estimate_performance and 'investment_metrics' in estimate_performance:
                        metrics = estimate_performance['investment_metrics']
                        if metrics.get('eps') and len(metrics['eps']) > 0:
                            stock_info.update({
                                'estimated_eps': metrics['eps'][0],
                                'estimated_per': metrics['per'][0] if metrics.get('per') and len(metrics['per']) > 0 else 0,
                                'estimated_roe': metrics['roe'][0] if metrics.get('roe') and len(metrics['roe']) > 0 else 0
                            })
                except:
                    pass
                
                # 7. 종합 점수 계산
                stock_info['score'] = calculate_comprehensive_score(stock_info, max_per, min_roe, max_debt_ratio)
                
                # 8. 필터 조건 미충족 시 점수 감점 적용
                stock_info = apply_filter_penalties(stock_info, max_per, min_roe, max_debt_ratio)
                
                # 모든 종목을 결과에 포함 (점수 감점 적용)
                analysis_results.append(stock_info)
                
                # 감점 사유가 있으면 표시
                penalty_reasons = stock_info.get('penalty_reasons', [])
                warning_flags = stock_info.get('warning_flags', [])
                
                if penalty_reasons:
                    penalty_text = ", ".join(penalty_reasons)
                    console.print(f"⚠️ {name} ({symbol}) 분석 완료 - 점수: {stock_info['score']:.1f}점 (감점: {stock_info['penalty_score']}점, 사유: {penalty_text})")
                elif warning_flags:
                    warning_text = ", ".join(warning_flags)
                    console.print(f"⚠️ {name} ({symbol}) 분석 완료 - 점수: {stock_info['score']:.1f}점 (경고: {warning_text})")
                else:
                    console.print(f"✅ {name} ({symbol}) 분석 완료 - 점수: {stock_info['score']:.1f}점")
                
            except Exception as e:
                console.print(f"❌ {name} ({symbol}) 분석 실패: {e}")
                pass
            
            progress.update(task, advance=1)
            
            # 배치 간 대기 제거 - API 호출 간 대기로 충분
    
    # 3단계: 결과 정렬 및 표시
    console.print(f"\n📊 [bold]3단계: 결과 분석 및 정렬[/bold]")
    
    if not analysis_results:
        console.print("❌ 조건을 만족하는 종목이 없습니다.")
        return
    
    # 점수 기준으로 정렬
    analysis_results.sort(key=lambda x: x['score'], reverse=True)
    
    console.print(f"✅ {len(analysis_results)}개 종목 분석 완료")
    
    # 4단계: 결과 표시
    console.print(f"\n🏆 [bold]종합 저평가 가치주 TOP {min(display, len(analysis_results))}[/bold]")
    
    # 종합 순위 테이블
    ranking_table = Table(title="종합 저평가 가치주 순위")
    ranking_table.add_column("순위", justify="center", style="bold")
    ranking_table.add_column("종목코드", justify="center", style="cyan")
    ranking_table.add_column("종목명", justify="left", style="green")
    ranking_table.add_column("업종", justify="center", style="blue")
    ranking_table.add_column("시가총액", justify="right", style="yellow")
    ranking_table.add_column("현재가", justify="right", style="purple")
    ranking_table.add_column("PER", justify="right", style="red")
    ranking_table.add_column("ROE", justify="right", style="yellow")
    ranking_table.add_column("부채비율", justify="right", style="magenta")
    ranking_table.add_column("종합점수", justify="right", style="bold")
    ranking_table.add_column("감점사유", justify="left", style="red")
    
    for i, stock in enumerate(analysis_results[:display], 1):
        penalty_reasons = stock.get('penalty_reasons', [])
        penalty_text = ", ".join(penalty_reasons) if penalty_reasons else "없음"
        
        ranking_table.add_row(
            str(i),
            stock['symbol'],
            stock['name'],
            stock.get('sector', ''),
            f"{stock.get('market_cap', 0):,.0f}억원",
            f"{stock.get('current_price', 0):,.0f}원",
            f"{stock.get('per', 0):.1f}배",
            f"{stock.get('roe', 0):.1f}%",
            f"{stock.get('debt_ratio', 0):.1f}%",
            f"{stock['score']:.1f}점",
            penalty_text
        )
    
    console.print(ranking_table)
    
    # 5단계: 상세 분석 결과
    console.print(f"\n🔍 [bold]상세 분석 결과[/bold]")
    
    # PER 분포
    per_values = [s.get('per', 0) for s in analysis_results if s.get('per', 0) > 0]
    if per_values:
        console.print(f"• 평균 PER: {sum(per_values) / len(per_values):.1f}배")
        console.print(f"• 최저 PER: {min(per_values):.1f}배")
        console.print(f"• 최고 PER: {max(per_values):.1f}배")
    
    # ROE 분포
    roe_values = [s.get('roe', 0) for s in analysis_results if s.get('roe', 0) > 0]
    if roe_values:
        console.print(f"• 평균 ROE: {sum(roe_values) / len(roe_values):.1f}%")
        console.print(f"• 최저 ROE: {min(roe_values):.1f}%")
        console.print(f"• 최고 ROE: {max(roe_values):.1f}%")
    
    # 부채비율 분포
    debt_values = [s.get('debt_ratio', 0) for s in analysis_results if s.get('debt_ratio', 0) > 0]
    if debt_values:
        console.print(f"• 평균 부채비율: {sum(debt_values) / len(debt_values):.1f}%")
        console.print(f"• 최저 부채비율: {min(debt_values):.1f}%")
        console.print(f"• 최고 부채비율: {max(debt_values):.1f}%")
    
    # 업종별 분포
    sector_distribution = {}
    for stock in analysis_results:
        sector = stock.get('sector', '기타')
        sector_distribution[sector] = sector_distribution.get(sector, 0) + 1
    
    console.print(f"\n📊 [bold]업종별 분포[/bold]")
    for sector, count in sorted(sector_distribution.items(), key=lambda x: x[1], reverse=True):
        console.print(f"• {sector}: {count}개 종목")
    
    # 6단계: 투자 추천
    console.print(f"\n💎 [bold]투자 추천[/bold]")
    
    top_3 = analysis_results[:3]
    for i, stock in enumerate(top_3, 1):
        console.print(f"\n🥇 [bold]{i}위: {stock['name']} ({stock['symbol']})[/bold]")
        console.print(f"   • 시가총액: {stock.get('market_cap', 0):,.0f}억원")
        console.print(f"   • 현재가: {stock.get('current_price', 0):,.0f}원")
        console.print(f"   • PER: {stock.get('per', 0):.1f}배")
        console.print(f"   • ROE: {stock.get('roe', 0):.1f}%")
        console.print(f"   • 부채비율: {stock.get('debt_ratio', 0):.1f}%")
        console.print(f"   • 종합점수: {stock['score']:.1f}점")
        
        # 강점 분석
        strengths = []
        if stock.get('per', 0) < 15:
            strengths.append("저PER")
        if stock.get('roe', 0) > 15:
            strengths.append("고ROE")
        if stock.get('debt_ratio', 0) < 50:
            strengths.append("안정적 부채구조")
        if stock.get('revenue_growth_rate', 0) > 10:
            strengths.append("성장성")
        if stock.get('profitability_grade', '') in ['우수', '매우 우수']:
            strengths.append("수익성 우수")
        
        if strengths:
            console.print(f"   • 강점: {', '.join(strengths)}")

def normalize_market_cap(value: float, from_unit: str = "억원") -> float:
    """시가총액을 표준 단위(억원)로 정규화합니다."""
    if value <= 0:
        return 0
    
    # 단위별 변환 (억원 기준)
    if from_unit == "원":
        return value / 100_000_000  # 원 -> 억원
    elif from_unit == "백만원":
        return value / 100  # 백만원 -> 억원
    elif from_unit == "억원":
        return value  # 이미 억원
    elif from_unit == "조원":
        return value * 10000  # 조원 -> 억원
    else:
        return value  # 기본값

def calculate_comprehensive_score(stock_info: Dict[str, Any], max_per: float, min_roe: float, max_debt_ratio: float) -> float:
    """종합 점수를 계산합니다."""
    score = 0
    
    # 1. 가치 평가 점수 (40%)
    per = stock_info.get('per', 0)
    if per > 0 and per <= max_per:
        if per <= 10:
            score += 40
        elif per <= 15:
            score += 30
        elif per <= 20:
            score += 20
        else:
            score += 10
    
    # 2. 수익성 점수 (30%)
    roe = stock_info.get('roe', 0)
    if roe >= min_roe:
        if roe >= 20:
            score += 30
        elif roe >= 15:
            score += 25
        elif roe >= 10:
            score += 20
        else:
            score += 10
    
    # 3. 안정성 점수 (20%)
    debt_ratio = stock_info.get('debt_ratio', 0)
    if debt_ratio <= max_debt_ratio:
        if debt_ratio <= 30:
            score += 20
        elif debt_ratio <= 50:
            score += 15
        elif debt_ratio <= 70:
            score += 10
        else:
            score += 5
    
    # 4. 성장성 점수 (10%)
    revenue_growth = stock_info.get('revenue_growth_rate', 0)
    if revenue_growth > 0:
        if revenue_growth >= 20:
            score += 10
        elif revenue_growth >= 10:
            score += 8
        elif revenue_growth >= 5:
            score += 5
        else:
            score += 2
    
    # 5. 규모 점수 (10%) - 시가총액 기반
    market_cap = stock_info.get('market_cap', 0)
    normalized_cap = normalize_market_cap(market_cap, "억원")
    
    if normalized_cap >= 100000:  # 10조원 이상
        score += 10
    elif normalized_cap >= 50000:  # 5조원 이상
        score += 8
    elif normalized_cap >= 10000:  # 1조원 이상
        score += 5
    elif normalized_cap >= 5000:   # 5천억원 이상
        score += 2
    
    return score

def analyze_single_stock_safe(symbol: str, name: str, market_cap: float, sector: str, 
                             analyzer: 'AdvancedStockAnalyzer', max_per: float, min_roe: float, max_debt_ratio: float) -> Dict[str, Any]:
    """단일 종목을 안전하게 분석합니다. (병렬 처리용)"""
    try:
        # TPS 제한 적용
        rate_limiter.acquire()
        
        # 기본 정보
        stock_info = {
            'symbol': symbol,
            'name': name,
            'market_cap': market_cap,
            'sector': sector,
            'score': 0,
            'analysis_details': {}
        }
        
        # 1. 현재가 및 기본 정보 조회
        try:
            current_data = analyzer.provider.get_stock_price_info(symbol)
            if current_data and current_data.get('current_price', 0) > 0:
                stock_info.update({
                    'current_price': current_data.get('current_price', 0),
                    'price_change': current_data.get('change_price', 0),
                    'price_change_rate': current_data.get('change_rate', 0),
                    'per': current_data.get('per', 0),
                    'pbr': current_data.get('pbr', 0),
                    'volume': current_data.get('volume', 0)
                })
            else:
                # 현재가가 0이거나 데이터가 없는 경우 재시도
                rate_limiter.acquire()  # 재시도 전에도 TPS 제한 적용
                current_data = analyzer.provider.get_stock_price_info(symbol)
                if current_data:
                    stock_info.update({
                        'current_price': current_data.get('current_price', 0),
                        'price_change': current_data.get('change_price', 0),
                        'price_change_rate': current_data.get('change_rate', 0),
                        'per': current_data.get('per', 0),
                        'pbr': current_data.get('pbr', 0),
                        'volume': current_data.get('volume', 0)
                    })
        except Exception as e:
            pass
        
        # 2. 재무비율 분석
        rate_limiter.acquire()
        try:
            financial_ratios = analyzer.financial_ratio_analyzer.get_financial_ratios(symbol)
            if financial_ratios and len(financial_ratios) > 0:
                latest_ratios = financial_ratios[0]
                stock_info.update({
                    'roe': latest_ratios.get('roe', 0),
                    'roa': latest_ratios.get('roa', 0),
                    'debt_ratio': latest_ratios.get('debt_ratio', 0),
                    'equity_ratio': latest_ratios.get('equity_ratio', 0),
                    'revenue_growth_rate': latest_ratios.get('revenue_growth_rate', 0),
                    'operating_income_growth_rate': latest_ratios.get('operating_income_growth_rate', 0),
                    'net_income_growth_rate': latest_ratios.get('net_income_growth_rate', 0)
                })
        except:
            pass
        
        # 3. 수익성비율 분석
        rate_limiter.acquire()
        try:
            profit_ratios = analyzer.profit_ratio_analyzer.get_profit_ratios(symbol)
            if profit_ratios and len(profit_ratios) > 0:
                latest_profit = profit_ratios[0]
                stock_info.update({
                    'net_profit_margin': latest_profit.get('net_profit_margin', 0),
                    'gross_profit_margin': latest_profit.get('gross_profit_margin', 0),
                    'profitability_grade': latest_profit.get('profitability_grade', '평가불가')
                })
        except:
            pass
        
        # 4. 안정성비율 분석
        rate_limiter.acquire()
        try:
            stability_ratios = analyzer.stability_ratio_analyzer.get_stability_ratios(symbol)
            if stability_ratios and len(stability_ratios) > 0:
                latest_stability = stability_ratios[0]
                stock_info.update({
                    'current_ratio': latest_stability.get('current_ratio', 0),
                    'quick_ratio': latest_stability.get('quick_ratio', 0),
                    'borrowing_dependency': latest_stability.get('borrowing_dependency', 0),
                    'stability_grade': latest_stability.get('stability_grade', '평가불가')
                })
        except:
            pass
        
        # 5. 성장성비율 분석
        rate_limiter.acquire()
        try:
            growth_ratios = analyzer.growth_ratio_analyzer.get_growth_ratios(symbol)
            if growth_ratios and len(growth_ratios) > 0:
                latest_growth = growth_ratios[0]
                stock_info.update({
                    'revenue_growth_rate_annual': latest_growth.get('revenue_growth_rate', 0),
                    'operating_income_growth_rate_annual': latest_growth.get('operating_income_growth_rate', 0),
                    'equity_growth_rate': latest_growth.get('equity_growth_rate', 0),
                    'total_asset_growth_rate': latest_growth.get('total_asset_growth_rate', 0),
                    'growth_grade': latest_growth.get('growth_grade', '평가불가')
                })
        except:
            pass
        
        # 6. 추정실적 분석
        rate_limiter.acquire()
        try:
            estimate_performance = analyzer.estimate_performance_analyzer.get_estimate_performance(symbol)
            if estimate_performance and 'investment_metrics' in estimate_performance:
                metrics = estimate_performance['investment_metrics']
                if metrics.get('eps') and len(metrics['eps']) > 0:
                    stock_info.update({
                        'estimated_eps': metrics['eps'][0],
                        'estimated_per': metrics['per'][0] if metrics.get('per') and len(metrics['per']) > 0 else 0,
                        'estimated_roe': metrics['roe'][0] if metrics.get('roe') and len(metrics['roe']) > 0 else 0
                    })
        except:
            pass
        
        # 7. 종합 점수 계산
        stock_info['score'] = calculate_comprehensive_score(stock_info, max_per, min_roe, max_debt_ratio)
        
        # 8. 필터 조건 미충족 시 점수 감점 적용
        stock_info = apply_filter_penalties(stock_info, max_per, min_roe, max_debt_ratio)
        
        return stock_info
        
    except Exception as e:
        return {
            'symbol': symbol,
            'name': name,
            'market_cap': market_cap,
            'sector': sector,
            'score': -1000,  # 오류 시 매우 낮은 점수
            'error': str(e)
        }

def apply_filter_penalties(stock_info: Dict[str, Any], max_per: float, min_roe: float, max_debt_ratio: float) -> Dict[str, Any]:
    """필터 조건 미충족 시 점수 감점을 적용합니다."""
    per = stock_info.get('per', 0)
    roe = stock_info.get('roe', 0)
    debt_ratio = stock_info.get('debt_ratio', 0)
    pbr = stock_info.get('pbr', 0)
    
    penalty_reasons = []
    penalty_score = 0
    warning_flags = []
    
    # PER 비정상값 처리
    if pd.isna(per) or per <= 0:
        penalty_score -= 30
        penalty_reasons.append("PER 데이터 없음")
        warning_flags.append("PER_NA")
    elif per > max_per:
        penalty_score -= 20
        penalty_reasons.append(f"PER {per:.1f}배 > {max_per}배")
    
    # PBR 비정상값 처리
    if pd.isna(pbr) or pbr <= 0:
        warning_flags.append("PBR_NA")
    elif pbr > 5:  # PBR 5배 이상은 고평가
        warning_flags.append("PBR_HIGH")
    
    # ROE 비정상값 처리
    if pd.isna(roe):
        penalty_score -= 20
        penalty_reasons.append("ROE 데이터 없음")
        warning_flags.append("ROE_NA")
    elif roe < min_roe:
        penalty_score -= 20
        penalty_reasons.append(f"ROE {roe:.1f}% < {min_roe}%")
    
    # 부채비율 비정상값 처리
    if pd.isna(debt_ratio):
        warning_flags.append("DEBT_RATIO_NA")
    elif debt_ratio > max_debt_ratio:
        penalty_score -= 15
        penalty_reasons.append(f"부채비율 {debt_ratio:.1f}% > {max_debt_ratio}%")
    
    # 점수에 감점 적용
    stock_info['score'] += penalty_score
    stock_info['penalty_reasons'] = penalty_reasons
    stock_info['penalty_score'] = penalty_score
    stock_info['warning_flags'] = warning_flags
    
    return stock_info

@app.command()
def test_parallel_processing(
    count: int = typer.Option(10, help="분석할 종목 수 (기본값: 10개)"),
    display: int = typer.Option(10, help="표시할 결과 수 (기본값: 10개)"),
    max_workers: int = typer.Option(3, help="병렬 워커 수 (기본값: 3개, TPS 제한 고려)"),
    dart_key: str = typer.Option(None, help="DART API 키"),
    min_market_cap: float = typer.Option(500, help="최소 시가총액 (억원, 기본값: 500억원)"),
    max_per: float = typer.Option(25, help="최대 PER (기본값: 25배)"),
    min_roe: float = typer.Option(5, help="최소 ROE (%, 기본값: 5%)"),
    max_debt_ratio: float = typer.Option(150, help="최대 부채비율 (%, 기본값: 150%)")
):
    """KIS OpenAPI TPS 제한을 고려한 안전한 병렬 처리 테스트"""
    analyzer = AdvancedStockAnalyzer(dart_key)
    
    console.print(f"🚀 [bold]KIS OpenAPI 병렬 처리 테스트[/bold]")
    console.print(f"📊 분석 대상: 시가총액 상위 {count}개 종목")
    console.print(f"⚡ 병렬 워커: {max_workers}개 (TPS 제한: 초당 8건)")
    console.print(f"📈 필터 조건: PER ≤ {max_per}배, ROE ≥ {min_roe}%, 부채비율 ≤ {max_debt_ratio}%")
    console.print(f"💰 최소 시가총액: {min_market_cap:,}억원")
    
    # 1단계: 시가총액 상위 종목 선별
    console.print(f"\n📊 [bold]1단계: 시가총액 상위 종목 선별[/bold]")
    
    if analyzer.kospi_data is None or analyzer.kospi_data.empty:
        console.print("❌ KOSPI 데이터를 로드할 수 없습니다.")
        return
    
    # 시가총액 기준으로 정렬하고 필터링 (우선주 제외)
    filtered_stocks = analyzer.kospi_data[
        (analyzer.kospi_data['시가총액'] >= min_market_cap) &
        (~analyzer.kospi_data['한글명'].str.contains('우$', na=False))  # 우선주 제외
    ].nlargest(count, '시가총액')
    
    console.print(f"✅ {len(filtered_stocks)}개 종목 선별 완료")
    
    # 2단계: 병렬 분석 수행
    console.print(f"\n⚡ [bold]2단계: 병렬 분석 수행 (TPS 제한 적용)[/bold]")
    
    analysis_results = []
    start_time = time.time()
    
    with Progress() as progress:
        task = progress.add_task("병렬 분석 진행 중...", total=len(filtered_stocks))
        
        # ThreadPoolExecutor를 사용한 병렬 처리
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 각 종목에 대한 Future 생성
            future_to_stock = {}
            for _, stock in filtered_stocks.iterrows():
                symbol = stock['단축코드']
                name = stock['한글명']
                market_cap = stock['시가총액']
                sector = str(stock.get('지수업종대분류', ''))
                
                future = executor.submit(
                    analyze_single_stock_safe,
                    symbol, name, market_cap, sector,
                    analyzer, max_per, min_roe, max_debt_ratio
                )
                future_to_stock[future] = (symbol, name)
            
            # 완료된 작업들을 처리
            for future in as_completed(future_to_stock):
                symbol, name = future_to_stock[future]
                try:
                    result = future.result()
                    analysis_results.append(result)
                    
                    # 결과 표시
                    if 'error' in result:
                        console.print(f"❌ {name} ({symbol}) 분석 실패: {result['error']}")
                    else:
                        penalty_reasons = result.get('penalty_reasons', [])
                        warning_flags = result.get('warning_flags', [])
                        
                        if penalty_reasons:
                            penalty_text = ", ".join(penalty_reasons)
                            console.print(f"⚠️ {name} ({symbol}) 분석 완료 - 점수: {result['score']:.1f}점 (감점: {result['penalty_score']}점, 사유: {penalty_text})")
                        elif warning_flags:
                            warning_text = ", ".join(warning_flags)
                            console.print(f"⚠️ {name} ({symbol}) 분석 완료 - 점수: {result['score']:.1f}점 (경고: {warning_text})")
                        else:
                            console.print(f"✅ {name} ({symbol}) 분석 완료 - 점수: {result['score']:.1f}점")
                    
                    progress.update(task, advance=1)
                    
                except Exception as e:
                    console.print(f"❌ {name} ({symbol}) Future 처리 실패: {e}")
                    progress.update(task, advance=1)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # 3단계: 결과 분석
    console.print(f"\n📊 [bold]3단계: 병렬 처리 결과 분석[/bold]")
    
    if not analysis_results:
        console.print("❌ 분석된 종목이 없습니다.")
        return
    
    # 성공/실패 통계
    success_count = len([r for r in analysis_results if 'error' not in r])
    error_count = len(analysis_results) - success_count
    
    console.print(f"✅ 성공: {success_count}개")
    console.print(f"❌ 실패: {error_count}개")
    console.print(f"⏱️ 총 소요시간: {total_time:.1f}초")
    console.print(f"⚡ 평균 처리속도: {len(analysis_results)/total_time:.2f}종목/초")
    console.print(f"🔒 TPS 준수: 초당 8건 이하 유지")
    
    # 점수 기준으로 정렬
    valid_results = [r for r in analysis_results if 'error' not in r]
    valid_results.sort(key=lambda x: x['score'], reverse=True)
    
    if valid_results:
        console.print(f"\n🏆 [bold]병렬 처리 결과 TOP {min(display, len(valid_results))}[/bold]")
        
        # 결과 테이블
        result_table = Table(title="병렬 처리 분석 결과")
        result_table.add_column("순위", justify="center", style="bold")
        result_table.add_column("종목코드", justify="center", style="cyan")
        result_table.add_column("종목명", justify="left", style="green")
        result_table.add_column("시가총액", justify="right", style="yellow")
        result_table.add_column("현재가", justify="right", style="purple")
        result_table.add_column("PER", justify="right", style="red")
        result_table.add_column("ROE", justify="right", style="yellow")
        result_table.add_column("종합점수", justify="right", style="bold")
        
        for i, stock in enumerate(valid_results[:display], 1):
            result_table.add_row(
                str(i),
                stock['symbol'],
                stock['name'],
                f"{stock.get('market_cap', 0):,.0f}억원",
                f"{stock.get('current_price', 0):,.0f}원",
                f"{stock.get('per', 0):.1f}배",
                f"{stock.get('roe', 0):.1f}%",
                f"{stock['score']:.1f}점"
            )
        
        console.print(result_table)
    
    # 성능 비교 (순차 처리 대비)
    sequential_time_estimate = len(analysis_results) * 16  # 종목당 16초 추정
    speedup = sequential_time_estimate / total_time if total_time > 0 else 0
    
    console.print(f"\n📈 [bold]성능 분석[/bold]")
    console.print(f"• 순차 처리 예상시간: {sequential_time_estimate:.1f}초")
    console.print(f"• 병렬 처리 실제시간: {total_time:.1f}초")
    console.print(f"• 성능 향상: {speedup:.1f}배")
    console.print(f"• 시간 절약: {sequential_time_estimate - total_time:.1f}초")

@app.command()
def test_financial_ratio_parallel(
    symbols: str = typer.Option("005930,000660,035420,005380,000270,105560,012450,207940,373220,329180", help="분석할 종목코드 (쉼표로 구분)"),
    max_workers: int = typer.Option(3, help="병렬 워커 수 (기본값: 3개)"),
    use_retry: bool = typer.Option(True, help="재시도 로직 사용 여부"),
    display: int = typer.Option(10, help="표시할 결과 수 (기본값: 10개)"),
    dart_key: str = typer.Option(None, help="DART API 키")
):
    """재무비율 병렬 분석 테스트"""
    analyzer = AdvancedStockAnalyzer(dart_key)
    
    symbol_list = [s.strip() for s in symbols.split(',')]
    
    console.print(f"🚀 [bold]재무비율 병렬 분석 테스트[/bold]")
    console.print(f"📊 분석 대상: {len(symbol_list)}개 종목")
    console.print(f"⚡ 병렬 워커: {max_workers}개")
    console.print(f"🔄 재시도 로직: {'사용' if use_retry else '미사용'}")
    
    start_time = time.time()
    
    # 병렬 재무비율 분석
    results_df = analyzer.financial_ratio_analyzer.parallel_compare_financial_ratios(
        symbol_list, 
        max_workers=max_workers, 
        use_retry=use_retry
    )
    
    end_time = time.time()
    total_time = end_time - start_time
    
    if results_df is not None and not results_df.empty:
        console.print(f"\n✅ 병렬 분석 완료: {len(results_df)}개 종목")
        console.print(f"⏱️ 총 소요시간: {total_time:.1f}초")
        console.print(f"⚡ 평균 처리속도: {len(results_df)/total_time:.2f}종목/초")
        
        # 결과 테이블
        result_table = Table(title="재무비율 병렬 분석 결과")
        result_table.add_column("순위", justify="center", style="bold")
        result_table.add_column("종목코드", justify="center", style="cyan")
        result_table.add_column("ROE", justify="right", style="green")
        result_table.add_column("ROA", justify="right", style="blue")
        result_table.add_column("부채비율", justify="right", style="red")
        result_table.add_column("매출증가율", justify="right", style="yellow")
        result_table.add_column("종합점수", justify="right", style="bold")
        
        # 점수 기준으로 정렬하여 상위 결과만 표시
        sorted_results = results_df.sort_values('total_score', ascending=False).head(display)
        
        for i, (_, row) in enumerate(sorted_results.iterrows(), 1):
            result_table.add_row(
                f"{i}위",
                row['symbol'],
                f"{row.get('roe', 0):.1f}%",
                f"{row.get('roa', 0):.1f}%",
                f"{row.get('debt_ratio', 0):.1f}%",
                f"{row.get('revenue_growth_rate', 0):+.1f}%",
                f"{row.get('total_score', 0):.1f}점"
            )
        
        console.print(result_table)
    else:
        console.print("❌ 재무비율 병렬 분석 실패")

@app.command()
def test_profit_ratio_parallel(
    symbols: str = typer.Option("005930,000660,035420,005380,000270,105560,012450,207940,373220,329180", help="분석할 종목코드 (쉼표로 구분)"),
    max_workers: int = typer.Option(3, help="병렬 워커 수 (기본값: 3개)"),
    use_retry: bool = typer.Option(True, help="재시도 로직 사용 여부"),
    display: int = typer.Option(10, help="표시할 결과 수 (기본값: 10개)"),
    dart_key: str = typer.Option(None, help="DART API 키")
):
    """수익성비율 병렬 분석 테스트"""
    analyzer = AdvancedStockAnalyzer(dart_key)
    
    symbol_list = [s.strip() for s in symbols.split(',')]
    
    console.print(f"🚀 [bold]수익성비율 병렬 분석 테스트[/bold]")
    console.print(f"📊 분석 대상: {len(symbol_list)}개 종목")
    console.print(f"⚡ 병렬 워커: {max_workers}개")
    console.print(f"🔄 재시도 로직: {'사용' if use_retry else '미사용'}")
    
    start_time = time.time()
    
    # 병렬 수익성비율 분석
    results_df = analyzer.profit_ratio_analyzer.parallel_compare_profit_ratios(
        symbol_list, 
        max_workers=max_workers, 
        use_retry=use_retry
    )
    
    end_time = time.time()
    total_time = end_time - start_time
    
    if results_df is not None and not results_df.empty:
        console.print(f"\n✅ 병렬 분석 완료: {len(results_df)}개 종목")
        console.print(f"⏱️ 총 소요시간: {total_time:.1f}초")
        console.print(f"⚡ 평균 처리속도: {len(results_df)/total_time:.2f}종목/초")
        
        # 결과 테이블
        result_table = Table(title="수익성비율 병렬 분석 결과")
        result_table.add_column("순위", justify="center", style="bold")
        result_table.add_column("종목코드", justify="center", style="cyan")
        result_table.add_column("ROA", justify="right", style="green")
        result_table.add_column("ROE", justify="right", style="blue")
        result_table.add_column("순이익률", justify="right", style="yellow")
        result_table.add_column("총이익률", justify="right", style="purple")
        result_table.add_column("수익성등급", justify="center", style="bold")
        
        # 점수 기준으로 정렬하여 상위 결과만 표시
        sorted_results = results_df.sort_values('total_profitability_score', ascending=False).head(display)
        
        for i, (_, row) in enumerate(sorted_results.iterrows(), 1):
            result_table.add_row(
                f"{i}위",
                row['symbol'],
                f"{row.get('roa', 0):.1f}%",
                f"{row.get('roe', 0):.1f}%",
                f"{row.get('net_profit_margin', 0):.1f}%",
                f"{row.get('gross_profit_margin', 0):.1f}%",
                row.get('profitability_grade', 'N/A')
            )
        
        console.print(result_table)
    else:
        console.print("❌ 수익성비율 병렬 분석 실패")

@app.command()
def test_batch_parallel_analysis(
    count: int = typer.Option(20, help="분석할 종목 수 (기본값: 20개)"),
    batch_size: int = typer.Option(5, help="배치 크기 (기본값: 5개)"),
    max_workers: int = typer.Option(3, help="병렬 워커 수 (기본값: 3개)"),
    dart_key: str = typer.Option(None, help="DART API 키")
):
    """배치 병렬 분석 테스트"""
    analyzer = AdvancedStockAnalyzer(dart_key)
    
    console.print(f"🚀 [bold]배치 병렬 분석 테스트[/bold]")
    console.print(f"📊 분석 대상: 시가총액 상위 {count}개 종목")
    console.print(f"📦 배치 크기: {batch_size}개")
    console.print(f"⚡ 병렬 워커: {max_workers}개")
    
    if analyzer.kospi_data is None or analyzer.kospi_data.empty:
        console.print("❌ KOSPI 데이터를 로드할 수 없습니다.")
        return
    
    # 시가총액 상위 종목 선별
    filtered_stocks = analyzer.kospi_data[
        (analyzer.kospi_data['시가총액'] >= 500) &
        (~analyzer.kospi_data['한글명'].str.contains('우$', na=False))
    ].nlargest(count, '시가총액')
    
    symbol_list = filtered_stocks['단축코드'].tolist()
    console.print(f"✅ {len(symbol_list)}개 종목 선별 완료")
    
    start_time = time.time()
    
    # 배치 병렬 재무비율 분석
    console.print(f"\n📊 [bold]재무비율 배치 병렬 분석[/bold]")
    financial_results = analyzer.financial_ratio_analyzer.batch_compare_financial_ratios(
        symbol_list, 
        batch_size=batch_size, 
        max_workers=max_workers
    )
    
    # 배치 병렬 수익성비율 분석
    console.print(f"\n💰 [bold]수익성비율 배치 병렬 분석[/bold]")
    profit_results = analyzer.profit_ratio_analyzer.batch_compare_profit_ratios(
        symbol_list, 
        batch_size=batch_size, 
        max_workers=max_workers
    )
    
    end_time = time.time()
    total_time = end_time - start_time
    
    console.print(f"\n📈 [bold]배치 병렬 분석 결과[/bold]")
    console.print(f"⏱️ 총 소요시간: {total_time:.1f}초")
    console.print(f"⚡ 평균 처리속도: {len(symbol_list)/total_time:.2f}종목/초")
    
    if financial_results is not None and not financial_results.empty:
        console.print(f"✅ 재무비율 분석: {len(financial_results)}개 종목 성공")
    else:
        console.print("❌ 재무비율 분석 실패")
    
    if profit_results is not None and not profit_results.empty:
        console.print(f"✅ 수익성비율 분석: {len(profit_results)}개 종목 성공")
    else:
        console.print("❌ 수익성비율 분석 실패")

@app.command()
def dart_info():
    """DART 기업 고유번호 관리 상태를 확인합니다."""
    analyzer = AdvancedStockAnalyzer()
    
    info = analyzer.get_dart_corp_code_info()
    
    if info["status"] == "not_initialized":
        console.print("❌ DART 관리자가 초기화되지 않았습니다.")
        return
    
    console.print("📊 DART 기업 고유번호 관리 상태:")
    console.print(f"   매핑된 종목: {info['mapping_count']}개")
    console.print(f"   KOSPI 종목: {info['kospi_count']}개")
    console.print(f"   매칭률: {info['mapping_rate']}")
    
    cache_info = info['cache_info']
    if cache_info['status'] == 'cached':
        console.print(f"   캐시 상태: 유효 (마지막 업데이트: {cache_info['age_hours']:.1f}시간 전)")
    else:
        console.print(f"   캐시 상태: {cache_info['status']}")

@app.command()
def dart_refresh():
    """DART 기업 고유번호 데이터를 새로고침합니다."""
    analyzer = AdvancedStockAnalyzer()
    
    if analyzer.refresh_dart_corp_codes():
        console.print("✅ DART 기업 고유번호 새로고침 완료")
    else:
        console.print("❌ DART 기업 고유번호 새로고침 실패")

@app.command()
def dart_search(
    keyword: str = typer.Argument(..., help="검색할 기업명 키워드"),
    limit: int = typer.Option(10, "--limit", "-l", help="검색 결과 개수 제한")
):
    """DART 기업을 검색합니다."""
    analyzer = AdvancedStockAnalyzer()
    
    results = analyzer.search_dart_company(keyword, limit)
    
    if not results:
        console.print(f"❌ '{keyword}'에 대한 검색 결과가 없습니다.")
        return
    
    console.print(f"🔍 '{keyword}' 검색 결과 ({len(results)}개):")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("기업명", style="cyan")
    table.add_column("기업고유번호", style="green")
    table.add_column("종목코드", style="yellow")
    
    for result in results:
        table.add_row(
            result['corp_name'],
            result['corp_code'],
            result['stock_code'] if result['stock_code'] else "-"
        )
    
    console.print(table)

if __name__ == "__main__":
    app()
