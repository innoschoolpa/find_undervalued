#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DART API 데이터 제공자
금융감독원 전자공시 시스템 연동

작성: 2025-10-12
버전: v2.2.2
"""

import logging
import requests
import json
import yaml
import os
import zipfile
import io
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class DartDataProvider:
    """
    DART (Data Analysis, Retrieval and Transfer System) API 데이터 제공자
    
    기능:
    - 재무제표 조회
    - 기업 정보 조회
    - 종목코드 → DART 고유번호 매핑
    - 재무비율 계산
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        초기화
        
        Args:
            api_key: DART API 키 (없으면 config.yaml에서 로드)
        """
        # config.yaml에서 설정 로드
        if api_key is None:
            api_key = self._load_config()
        
        self.api_key = api_key
        self.base_url = "https://opendart.fss.or.kr/api"
        self.timeout = 12
        
        # 캐시
        self.corp_code_cache = {}  # 종목코드 → 고유번호 매핑
        self.company_info_cache = {}  # 기업 정보
        
        # 캐시 디렉토리
        self.cache_dir = 'cache/dart'
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 고유번호 매핑 파일 로드 시도
        self._load_corp_code_cache()
        
        logger.info("✅ DartDataProvider 초기화 완료")
    
    def _load_config(self) -> Optional[str]:
        """config.yaml에서 DART API 키 로드"""
        try:
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                dart_config = config.get('api', {}).get('dart', {})
                return dart_config.get('api_key')
        except Exception as e:
            logger.warning(f"config.yaml 로드 실패: {e}")
            return None
    
    def _load_corp_code_cache(self):
        """고유번호 캐시 파일 로드"""
        cache_file = os.path.join(self.cache_dir, 'corp_code_mapping.json')
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.corp_code_cache = json.load(f)
                    logger.info(f"✅ DART 고유번호 캐시 로드: {len(self.corp_code_cache)}개")
            except Exception as e:
                logger.warning(f"캐시 파일 로드 실패: {e}")
    
    def _save_corp_code_cache(self):
        """고유번호 캐시 저장"""
        cache_file = os.path.join(self.cache_dir, 'corp_code_mapping.json')
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.corp_code_cache, f, ensure_ascii=False, indent=2)
                logger.info(f"✅ DART 고유번호 캐시 저장: {len(self.corp_code_cache)}개")
        except Exception as e:
            logger.error(f"캐시 저장 실패: {e}")
    
    def get_corp_code(self, stock_code: str) -> Optional[str]:
        """
        종목코드로 DART 고유번호 조회
        
        Args:
            stock_code: 종목코드 (예: '005930')
        
        Returns:
            DART 고유번호 (예: '00126380') 또는 None
        """
        # 캐시 확인
        if stock_code in self.corp_code_cache:
            return self.corp_code_cache[stock_code]
        
        # 수동 매핑 (주요 종목)
        known_mappings = {
            '005930': '00126380',  # 삼성전자
            '000660': '00164779',  # SK하이닉스
            '035420': '00401731',  # NAVER
            '051910': '00164742',  # LG화학
            '005380': '00164031',  # 현대차
            '000270': '00164457',  # 기아
            '006400': '00164742',  # 삼성SDI
            '051900': '00164779',  # LG생활건강
        }
        
        if stock_code in known_mappings:
            corp_code = known_mappings[stock_code]
            self.corp_code_cache[stock_code] = corp_code
            return corp_code
        
        logger.warning(f"DART 고유번호 미등록: {stock_code}")
        return None
    
    def get_company_info(self, stock_code: str) -> Optional[Dict]:
        """
        기업 기본정보 조회
        
        Args:
            stock_code: 종목코드
        
        Returns:
            기업 정보 딕셔너리
        """
        if not self.api_key:
            logger.error("DART API 키가 없습니다")
            return None
        
        # 캐시 확인
        if stock_code in self.company_info_cache:
            return self.company_info_cache[stock_code]
        
        # 고유번호 조회
        corp_code = self.get_corp_code(stock_code)
        if not corp_code:
            return None
        
        try:
            url = f"{self.base_url}/company.json"
            params = {
                'crtfc_key': self.api_key,
                'corp_code': corp_code
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == '000':
                    # 캐시 저장
                    self.company_info_cache[stock_code] = data
                    
                    logger.info(f"✅ DART 기업정보 조회: {data.get('corp_name', 'N/A')}")
                    return data
                else:
                    logger.warning(f"DART API 오류: {data.get('message')}")
                    return None
            else:
                logger.error(f"DART API 호출 실패: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"기업정보 조회 실패: {e}")
            return None
    
    def get_financial_statement(self, stock_code: str, year: str = None, 
                                 reprt_code: str = '11011') -> Optional[Dict]:
        """
        재무제표 조회
        
        Args:
            stock_code: 종목코드
            year: 회계연도 (기본값: 전년도)
            reprt_code: 보고서 코드 (11011: 사업보고서, 11012: 반기보고서, 11013: 1분기, 11014: 3분기)
        
        Returns:
            재무제표 데이터
        """
        if not self.api_key:
            logger.error("DART API 키가 없습니다")
            return None
        
        # 고유번호 조회
        corp_code = self.get_corp_code(stock_code)
        if not corp_code:
            return None
        
        # 기본값: 전년도
        if year is None:
            year = str(datetime.now().year - 1)
        
        try:
            url = f"{self.base_url}/fnlttSinglAcntAll.json"
            params = {
                'crtfc_key': self.api_key,
                'corp_code': corp_code,
                'bsns_year': year,
                'reprt_code': reprt_code,
                'fs_div': 'CFS'  # 연결재무제표
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == '000':
                    logger.info(f"✅ DART 재무제표 조회: {stock_code} ({year})")
                    return data
                else:
                    logger.warning(f"DART 재무제표 오류: {data.get('message')}")
                    return None
            else:
                logger.error(f"DART API 호출 실패: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"재무제표 조회 실패: {e}")
            return None
    
    def extract_financial_ratios(self, financial_data: Dict) -> Optional[Dict]:
        """
        재무제표에서 주요 비율 추출
        
        Args:
            financial_data: get_financial_statement 결과
        
        Returns:
            {'roe': 15.0, 'debt_ratio': 120.0, ...}
        """
        if not financial_data or financial_data.get('status') != '000':
            return None
        
        items = financial_data.get('list', [])
        
        # 주요 계정 추출 (유연한 매칭)
        accounts = {}
        for item in items:
            account_nm = item.get('account_nm', '')
            thstrm_amount = item.get('thstrm_amount', '0')
            
            try:
                amount = int(str(thstrm_amount).replace(',', ''))
                
                # 계정과목명 정규화 (공백 제거, 괄호 제거 등)
                account_key = account_nm.replace(' ', '').replace('(', '').replace(')', '')
                accounts[account_key] = amount
                
                # 원본도 저장
                accounts[account_nm] = amount
            except:
                pass
        
        # 재무비율 계산 (유연한 매칭)
        ratios = {}
        
        try:
            # 자산, 부채, 자본 (여러 패턴 시도)
            total_assets = (accounts.get('자산총계', 0) or 
                           accounts.get('자산총계당기말', 0) or
                           accounts.get('총자산', 0))
            
            total_liabilities = (accounts.get('부채총계', 0) or
                                accounts.get('부채총계당기말', 0) or
                                accounts.get('총부채', 0))
            
            total_equity = (accounts.get('자본총계', 0) or
                           accounts.get('자본총계당기말', 0) or
                           accounts.get('총자본', 0) or
                           accounts.get('자본금', 0))
            
            # 손익 (여러 패턴 시도)
            revenue = (accounts.get('매출액', 0) or
                      accounts.get('수익매출액', 0) or
                      accounts.get('영업수익', 0) or
                      accounts.get('매출', 0))
            
            operating_income = (accounts.get('영업이익', 0) or
                               accounts.get('영업이익손실', 0))
            
            net_income = (accounts.get('당기순이익', 0) or
                         accounts.get('당기순이익손실', 0) or
                         accounts.get('순이익', 0))
            
            # ROE 계산
            if total_equity > 0 and net_income != 0:
                ratios['roe'] = (net_income / total_equity) * 100
            
            # 부채비율
            if total_equity > 0:
                ratios['debt_ratio'] = (total_liabilities / total_equity) * 100
            
            # 영업이익률
            if revenue > 0:
                ratios['operating_margin'] = (operating_income / revenue) * 100
            
            # 순이익률
            if revenue > 0:
                ratios['net_margin'] = (net_income / revenue) * 100
            
            # 원본 데이터도 포함
            ratios['_raw_data'] = {
                'total_assets': total_assets,
                'total_liabilities': total_liabilities,
                'total_equity': total_equity,
                'revenue': revenue,
                'operating_income': operating_income,
                'net_income': net_income
            }
            
            return ratios
            
        except Exception as e:
            logger.error(f"재무비율 계산 실패: {e}")
            return None
    
    def cross_check_with_kis(self, stock_code: str, kis_data: Dict) -> Dict:
        """
        KIS 데이터와 DART 데이터 크로스체크
        
        Args:
            stock_code: 종목코드
            kis_data: KIS API에서 가져온 데이터
        
        Returns:
            크로스체크 결과 및 통합 데이터
        """
        result = {
            'stock_code': stock_code,
            'kis_available': bool(kis_data),
            'dart_available': False,
            'cross_check_passed': False,
            'discrepancies': [],
            'merged_data': kis_data.copy() if kis_data else {}
        }
        
        try:
            # DART 데이터 조회
            dart_financial = self.get_financial_statement(stock_code)
            
            if not dart_financial:
                logger.warning(f"DART 데이터 없음: {stock_code}")
                return result
            
            result['dart_available'] = True
            
            # 재무비율 추출
            dart_ratios = self.extract_financial_ratios(dart_financial)
            
            if not dart_ratios:
                logger.warning(f"DART 재무비율 계산 실패: {stock_code}")
                return result
            
            # KIS와 비교
            if kis_data:
                kis_roe = kis_data.get('roe', 0)
                dart_roe = dart_ratios.get('roe', 0)
                
                # ROE 비교 (±5% 이내면 정상)
                if kis_roe > 0 and dart_roe > 0:
                    diff = abs(kis_roe - dart_roe)
                    diff_pct = (diff / kis_roe) * 100
                    
                    if diff_pct > 5:
                        result['discrepancies'].append({
                            'metric': 'ROE',
                            'kis': kis_roe,
                            'dart': dart_roe,
                            'diff': diff,
                            'diff_pct': diff_pct
                        })
                        logger.warning(f"⚠️ ROE 불일치: KIS {kis_roe:.1f}% vs DART {dart_roe:.1f}% (차이 {diff_pct:.1f}%)")
                    else:
                        result['cross_check_passed'] = True
                        logger.info(f"✅ ROE 일치: {kis_roe:.1f}% ≈ {dart_roe:.1f}%")
                
                # DART 데이터로 보강
                result['merged_data']['roe_dart'] = dart_roe
                result['merged_data']['debt_ratio_dart'] = dart_ratios.get('debt_ratio', 0)
                result['merged_data']['operating_margin'] = dart_ratios.get('operating_margin', 0)
                result['merged_data']['net_margin'] = dart_ratios.get('net_margin', 0)
                result['merged_data']['dart_raw'] = dart_ratios.get('_raw_data', {})
            
            return result
            
        except Exception as e:
            logger.error(f"크로스체크 실패: {e}")
            return result
    
    def download_corp_codes(self) -> bool:
        """
        전체 기업 고유번호 다운로드 및 캐싱
        
        Returns:
            성공 여부
        """
        if not self.api_key:
            logger.error("DART API 키가 없습니다")
            return False
        
        try:
            url = f"{self.base_url}/corpCode.xml"
            params = {'crtfc_key': self.api_key}
            
            logger.info("📥 DART 기업 고유번호 다운로드 중...")
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"다운로드 실패: {response.status_code}")
                return False
            
            # ZIP 파일 압축 해제
            zip_file = zipfile.ZipFile(io.BytesIO(response.content))
            xml_data = zip_file.read('CORPCODE.xml')
            
            # XML 파싱
            root = ET.fromstring(xml_data)
            
            mapping = {}
            for corp in root.findall('list'):
                corp_code = corp.find('corp_code').text
                stock_code = corp.find('stock_code').text
                corp_name = corp.find('corp_name').text
                
                # 상장사만 (종목코드 있는 경우)
                if stock_code and stock_code.strip():
                    mapping[stock_code] = corp_code
                    logger.debug(f"매핑 추가: {stock_code} → {corp_code} ({corp_name})")
            
            self.corp_code_cache = mapping
            self._save_corp_code_cache()
            
            logger.info(f"✅ DART 기업 고유번호 다운로드 완료: {len(mapping)}개")
            return True
            
        except Exception as e:
            logger.error(f"기업 고유번호 다운로드 실패: {e}")
            return False


# ===== 사용 예시 =====
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    print("\n" + "="*60)
    print("🧪 DartDataProvider 테스트")
    print("="*60)
    
    # 초기화
    provider = DartDataProvider()
    
    # 1. 고유번호 조회
    print("\n1️⃣ 종목코드 → DART 고유번호 조회")
    stock_code = '005930'
    corp_code = provider.get_corp_code(stock_code)
    print(f"   {stock_code} → {corp_code}")
    
    # 2. 기업 정보 조회
    print("\n2️⃣ 기업 정보 조회")
    company_info = provider.get_company_info(stock_code)
    if company_info:
        print(f"   회사명: {company_info.get('corp_name')}")
        print(f"   종목코드: {company_info.get('stock_code')}")
        print(f"   대표자: {company_info.get('ceo_nm')}")
    
    # 3. 재무제표 조회
    print("\n3️⃣ 재무제표 조회")
    financial = provider.get_financial_statement(stock_code, '2023')
    if financial:
        print(f"   상태: {financial.get('status')} - {financial.get('message')}")
        items = financial.get('list', [])
        print(f"   항목 수: {len(items)}개")
        
        # 재무비율 계산
        ratios = provider.extract_financial_ratios(financial)
        if ratios:
            print(f"\n   📊 주요 재무비율:")
            print(f"      ROE: {ratios.get('roe', 0):.2f}%")
            print(f"      부채비율: {ratios.get('debt_ratio', 0):.1f}%")
            print(f"      영업이익률: {ratios.get('operating_margin', 0):.2f}%")
            print(f"      순이익률: {ratios.get('net_margin', 0):.2f}%")
    
    # 4. 크로스체크 테스트
    print("\n4️⃣ KIS 데이터 크로스체크 테스트")
    kis_mock_data = {
        'symbol': '005930',
        'name': '삼성전자',
        'per': 15.0,
        'pbr': 1.5,
        'roe': 12.0
    }
    
    cross_check_result = provider.cross_check_with_kis(stock_code, kis_mock_data)
    print(f"   KIS 가용: {cross_check_result['kis_available']}")
    print(f"   DART 가용: {cross_check_result['dart_available']}")
    print(f"   크로스체크: {'✅ 통과' if cross_check_result['cross_check_passed'] else '⚠️ 불일치'}")
    
    if cross_check_result['discrepancies']:
        print(f"\n   ⚠️ 불일치 항목:")
        for disc in cross_check_result['discrepancies']:
            print(f"      {disc['metric']}: KIS {disc['kis']:.1f} vs DART {disc['dart']:.1f} (차이 {disc['diff_pct']:.1f}%)")
    
    print("\n✅ DartDataProvider 테스트 완료!")

