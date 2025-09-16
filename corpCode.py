#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DART API 기업 고유번호 조회 모듈 (개선된 버전)
- 캐싱 시스템
- 향상된 매칭 알고리즘
- 에러 처리 강화
- 성능 최적화
"""

import requests
import io
import zipfile
import xml.etree.ElementTree as ET
import pandas as pd
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from difflib import SequenceMatcher
import time

logger = logging.getLogger(__name__)

class DARTCorpCodeManager:
    """DART 기업 고유번호 관리 클래스"""
    
    def __init__(self, api_key: str, cache_dir: str = "cache"):
        self.api_key = api_key
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "dart_corp_codes.json")
        self.cache_expiry_hours = 24  # 24시간 캐시 유지
        
        # 캐시 디렉토리 생성
        os.makedirs(cache_dir, exist_ok=True)
        
        # 메모리 캐시
        self._corp_codes_df = None
        self._corp_codes_dict = None
        self._last_update = None
    
    def _is_cache_valid(self) -> bool:
        """캐시가 유효한지 확인합니다."""
        if not os.path.exists(self.cache_file):
            return False
        
        try:
            cache_time = datetime.fromtimestamp(os.path.getmtime(self.cache_file))
            return datetime.now() - cache_time < timedelta(hours=self.cache_expiry_hours)
        except Exception:
            return False
    
    def _load_from_cache(self) -> Optional[pd.DataFrame]:
        """캐시에서 데이터를 로드합니다."""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            df = pd.DataFrame(cache_data['corp_codes'])
            logger.info(f"✅ 캐시에서 {len(df):,}개 기업 데이터 로드 완료")
            return df
        except Exception as e:
            logger.warning(f"⚠️ 캐시 로드 실패: {e}")
            return None
    
    def _save_to_cache(self, df: pd.DataFrame) -> None:
        """데이터를 캐시에 저장합니다."""
        try:
            cache_data = {
                'corp_codes': df.to_dict('records'),
                'last_update': datetime.now().isoformat(),
                'total_count': len(df)
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ {len(df):,}개 기업 데이터 캐시 저장 완료")
        except Exception as e:
            logger.error(f"❌ 캐시 저장 실패: {e}")
    
    def get_dart_corp_codes(self, force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """
        DART API를 통해 모든 기업의 고유번호를 받아와 DataFrame으로 반환합니다.
        
        Args:
            force_refresh: 캐시를 무시하고 강제로 새로고침
            
        Returns:
            기업 고유번호 DataFrame
        """
        # 캐시가 유효하고 강제 새로고침이 아닌 경우
        if not force_refresh and self._is_cache_valid():
            cached_df = self._load_from_cache()
            if cached_df is not None:
                self._corp_codes_df = cached_df
                self._last_update = datetime.now()
                return cached_df
        
        # API에서 새로 다운로드
        logger.info("🚀 DART에 기업 고유번호 데이터 요청 중...")
        
        try:
            url = "https://opendart.fss.or.kr/api/corpCode.xml"
            params = {'crtfc_key': self.api_key}
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            # 응답이 실제 Zip 파일인지 확인
            if 'application/zip' not in response.headers.get('Content-Type', ''):
                logger.error("❌ API 오류: DART로부터 유효한 Zip 파일을 받지 못했습니다.")
                logger.error(f"   응답 내용: {response.text[:200]}")
                return None

            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                xml_filename = zf.namelist()[0]
                logger.info(f"✅ Zip 파일 수신 완료, '{xml_filename}' 압축 해제 중...")
                
                with zf.open(xml_filename) as f:
                    tree = ET.parse(f)
                    root = tree.getroot()

                    corp_list = []
                    for item in root.findall('.//list'):
                        corp_code = item.findtext('corp_code')
                        corp_name = item.findtext('corp_name')
                        stock_code = item.findtext('stock_code', '').strip()
                        modify_date = item.findtext('modify_date')
                        
                        # 유효한 데이터만 추가
                        if corp_code and corp_name:
                            corp_list.append({
                                'corp_code': corp_code,
                                'corp_name': corp_name,
                                'stock_code': stock_code,
                                'modify_date': modify_date,
                                'is_listed': bool(stock_code)  # 상장 여부
                            })
                    
                    df = pd.DataFrame(corp_list)
                    logger.info(f"✅ 데이터 파싱 완료. 총 {len(df):,}개의 기업 정보를 변환합니다.")
                    
                    # 캐시에 저장
                    self._save_to_cache(df)
                    
                    self._corp_codes_df = df
                    self._last_update = datetime.now()
                    return df

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ API 요청 중 오류 발생: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ 처리 중 예외 발생: {e}")
            return None
    
    def get_corp_codes_dict(self, force_refresh: bool = False) -> Dict[str, str]:
        """
        기업명 -> 기업고유번호 매핑 딕셔너리를 반환합니다.
        
        Returns:
            {기업명: 기업고유번호} 딕셔너리
        """
        if self._corp_codes_dict is None or force_refresh:
            df = self.get_dart_corp_codes(force_refresh)
            if df is not None:
                self._corp_codes_dict = dict(zip(df['corp_name'], df['corp_code']))
            else:
                self._corp_codes_dict = {}
        
        return self._corp_codes_dict
    
    def find_corp_code_by_name(self, company_name: str, threshold: float = 0.8) -> Optional[str]:
        """
        기업명으로 기업고유번호를 찾습니다. (유사도 기반 매칭)
        
        Args:
            company_name: 찾을 기업명
            threshold: 유사도 임계값 (0.0 ~ 1.0)
            
        Returns:
            기업고유번호 또는 None
        """
        corp_codes_dict = self.get_corp_codes_dict()
        
        # 정확한 매칭 먼저 시도
        if company_name in corp_codes_dict:
            return corp_codes_dict[company_name]
        
        # 유사도 기반 매칭
        best_match = None
        best_score = 0.0
        
        for corp_name in corp_codes_dict.keys():
            # 정규화된 기업명으로 비교
            normalized_name = self._normalize_company_name(company_name)
            normalized_corp_name = self._normalize_company_name(corp_name)
            
            # 유사도 계산
            similarity = SequenceMatcher(None, normalized_name, normalized_corp_name).ratio()
            
            if similarity > best_score and similarity >= threshold:
                best_score = similarity
                best_match = corp_name
        
        if best_match:
            logger.info(f"🔍 '{company_name}' -> '{best_match}' (유사도: {best_score:.2f})")
            return corp_codes_dict[best_match]
        
        logger.warning(f"⚠️ '{company_name}'에 대한 매칭을 찾을 수 없습니다.")
        return None
    
    def _normalize_company_name(self, name: str) -> str:
        """기업명을 정규화합니다."""
        if not name:
            return ""
        
        # 공백 제거 및 소문자 변환
        normalized = name.strip().lower()
        
        # 일반적인 기업명 접미사 제거
        suffixes = ['주식회사', '㈜', '(주)', '㈜', 'co.', 'ltd.', 'inc.', 'corp.']
        for suffix in suffixes:
            if normalized.endswith(suffix.lower()):
                normalized = normalized[:-len(suffix)].strip()
        
        return normalized
    
    def get_listed_companies(self, force_refresh: bool = False) -> pd.DataFrame:
        """상장 기업만 필터링하여 반환합니다."""
        df = self.get_dart_corp_codes(force_refresh)
        if df is not None:
            return df[df['is_listed'] == True].copy()
        return pd.DataFrame()
    
    def search_companies(self, keyword: str, limit: int = 10) -> List[Dict[str, str]]:
        """키워드로 기업을 검색합니다."""
        df = self.get_dart_corp_codes()
        if df is None:
            return []
        
        # 키워드가 포함된 기업들 필터링
        mask = df['corp_name'].str.contains(keyword, case=False, na=False)
        results = df[mask].head(limit)
        
        return results[['corp_name', 'corp_code', 'stock_code']].to_dict('records')
    
    def get_cache_info(self) -> Dict[str, Any]:
        """캐시 정보를 반환합니다."""
        if not os.path.exists(self.cache_file):
            return {"status": "no_cache"}
        
        try:
            cache_time = datetime.fromtimestamp(os.path.getmtime(self.cache_file))
            age_hours = (datetime.now() - cache_time).total_seconds() / 3600
            
            return {
                "status": "cached",
                "last_update": cache_time.isoformat(),
                "age_hours": round(age_hours, 2),
                "is_valid": age_hours < self.cache_expiry_hours
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

# 기존 함수와의 호환성을 위한 래퍼 함수
def get_dart_corp_codes(api_key: str, force_refresh: bool = False) -> Optional[pd.DataFrame]:
    """
    기존 함수와의 호환성을 위한 래퍼 함수
    
    Args:
        api_key: DART API 키
        force_refresh: 캐시를 무시하고 강제로 새로고침
        
    Returns:
        기업 고유번호 DataFrame
    """
    manager = DARTCorpCodeManager(api_key)
    return manager.get_dart_corp_codes(force_refresh)

if __name__ == "__main__":
    # 테스트
    api_key = "881d7d29ca6d553ce02e78d22a1129c15a62ac47"
    df = get_dart_corp_codes(api_key)
    if df is not None:
        print(f"총 {len(df)}개 기업 데이터 로드 완료")
        print(df.head())

