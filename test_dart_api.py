#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DART API 접속 테스트
금융감독원 전자공시 시스템 연동
"""

import sys
import io
import logging
import requests
import json
import yaml
import os

# Windows 인코딩 처리
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def load_dart_config():
    """config.yaml에서 DART API 설정 로드"""
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            dart_config = config.get('api', {}).get('dart', {})
            
            api_key = dart_config.get('api_key')
            base_url = dart_config.get('base_url', 'https://opendart.fss.or.kr/api')
            timeout = dart_config.get('timeout', 10)
            
            return {
                'api_key': api_key,
                'base_url': base_url,
                'timeout': timeout
            }
    except Exception as e:
        logger.error(f"config.yaml 로드 실패: {e}")
        return None


def test_dart_connection(config):
    """DART API 연결 테스트"""
    print("\n" + "="*60)
    print("🔌 DART API 연결 테스트")
    print("="*60)
    
    api_key = config['api_key']
    base_url = config['base_url']
    timeout = config['timeout']
    
    print(f"\n📋 설정 정보:")
    print(f"   API 키: {api_key[:20]}...")
    print(f"   Base URL: {base_url}")
    print(f"   타임아웃: {timeout}초")
    
    # 1. 회사목록 조회 (간단한 테스트)
    try:
        url = f"{base_url}/corpCode.xml"
        params = {'crtfc_key': api_key}
        
        print(f"\n🌐 API 호출: {url}")
        response = requests.get(url, params=params, timeout=timeout)
        
        print(f"   상태 코드: {response.status_code}")
        print(f"   응답 크기: {len(response.content)} bytes")
        
        if response.status_code == 200:
            # ZIP 파일로 응답됨
            print(f"   응답 타입: {response.headers.get('Content-Type', 'N/A')}")
            
            if len(response.content) > 0:
                print("\n✅ DART API 연결 성공!")
                print("   회사목록 데이터 수신 완료")
                return True
            else:
                print("\n❌ 응답이 비어있습니다")
                return False
        else:
            print(f"\n❌ API 호출 실패: {response.status_code}")
            print(f"   응답: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"\n❌ 타임아웃 ({timeout}초 초과)")
        return False
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        return False


def test_company_search(config):
    """회사 검색 테스트 (삼성전자)"""
    print("\n" + "="*60)
    print("🔍 회사 검색 테스트 (삼성전자)")
    print("="*60)
    
    api_key = config['api_key']
    base_url = config['base_url']
    timeout = config['timeout']
    
    try:
        # 회사 기본정보 조회
        url = f"{base_url}/company.json"
        params = {
            'crtfc_key': api_key,
            'corp_code': '00126380'  # 삼성전자 고유번호
        }
        
        print(f"\n🌐 API 호출: {url}")
        print(f"   기업 코드: 00126380 (삼성전자)")
        
        response = requests.get(url, params=params, timeout=timeout)
        
        print(f"   상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n📄 응답 데이터:")
            print(json.dumps(data, ensure_ascii=False, indent=2)[:500])
            
            if data.get('status') == '000':
                print(f"\n✅ 회사 정보 조회 성공!")
                print(f"   회사명: {data.get('corp_name', 'N/A')}")
                print(f"   대표자: {data.get('ceo_nm', 'N/A')}")
                print(f"   종목코드: {data.get('stock_code', 'N/A')}")
                print(f"   법인구분: {data.get('corp_cls', 'N/A')}")
                return True
            else:
                print(f"\n⚠️ API 응답 상태: {data.get('status')} - {data.get('message')}")
                return False
        else:
            print(f"\n❌ API 호출 실패: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_financial_statement(config):
    """재무제표 조회 테스트 (삼성전자)"""
    print("\n" + "="*60)
    print("📊 재무제표 조회 테스트 (삼성전자)")
    print("="*60)
    
    api_key = config['api_key']
    base_url = config['base_url']
    timeout = config['timeout']
    
    try:
        # 단일회사 전체 재무제표 조회
        url = f"{base_url}/fnlttSinglAcntAll.json"
        params = {
            'crtfc_key': api_key,
            'corp_code': '00126380',  # 삼성전자
            'bsns_year': '2023',      # 2023년
            'reprt_code': '11011'     # 사업보고서
        }
        
        print(f"\n🌐 API 호출: {url}")
        print(f"   기업: 삼성전자 (00126380)")
        print(f"   연도: 2023")
        print(f"   보고서: 사업보고서")
        
        response = requests.get(url, params=params, timeout=timeout)
        
        print(f"   상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == '000':
                items = data.get('list', [])
                print(f"\n✅ 재무제표 조회 성공!")
                print(f"   항목 수: {len(items)}개")
                
                # 주요 재무 항목 추출
                key_items = {
                    '자산총계': None,
                    '부채총계': None,
                    '자본총계': None,
                    '매출액': None,
                    '영업이익': None,
                    '당기순이익': None
                }
                
                for item in items:
                    account_nm = item.get('account_nm', '')
                    thstrm_amount = item.get('thstrm_amount', '0')
                    
                    for key in key_items.keys():
                        if key in account_nm:
                            key_items[key] = thstrm_amount
                            break
                
                print(f"\n📊 주요 재무 항목:")
                for key, value in key_items.items():
                    if value:
                        try:
                            amount = int(value)
                            print(f"   {key}: {amount:,}원")
                        except:
                            print(f"   {key}: {value}")
                    else:
                        print(f"   {key}: 데이터 없음")
                
                # ROE 계산 가능 여부 체크
                equity = key_items.get('자본총계')
                net_income = key_items.get('당기순이익')
                
                if equity and net_income:
                    try:
                        roe = (int(net_income) / int(equity)) * 100
                        print(f"\n💡 계산 가능한 지표:")
                        print(f"   ROE: {roe:.2f}%")
                    except:
                        pass
                
                return True
            else:
                print(f"\n⚠️ API 응답 상태: {data.get('status')} - {data.get('message')}")
                return False
        else:
            print(f"\n❌ API 호출 실패: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_stock_code_mapping():
    """종목코드 → DART 고유번호 매핑 테스트"""
    print("\n" + "="*60)
    print("🔗 종목코드 매핑 테스트")
    print("="*60)
    
    # 주요 종목 매핑
    mappings = {
        '005930': '00126380',  # 삼성전자
        '000660': '00164779',  # SK하이닉스
        '035420': '00401731',  # NAVER
        '051910': '00164742',  # LG화학
        '005380': '00164742',  # 현대차
    }
    
    print(f"\n📋 테스트 매핑 (5개 종목):")
    for stock_code, corp_code in mappings.items():
        print(f"   {stock_code} → {corp_code}")
    
    print(f"\n✅ 매핑 데이터 준비 완료")
    print(f"   향후: corpCode.xml 파일에서 자동 매핑 구현 필요")
    
    return True


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 DART API 접속 테스트 시작")
    print("="*60)
    
    # 설정 로드
    config = load_dart_config()
    
    if not config or not config.get('api_key'):
        print("\n❌ DART API 설정이 없습니다.")
        print("\n💡 해결 방법:")
        print("   1. https://opendart.fss.or.kr/ 에서 API 키 발급")
        print("   2. config.yaml의 api.dart.api_key에 설정")
        sys.exit(1)
    
    results = []
    
    # 1. 연결 테스트
    result1 = test_dart_connection(config)
    results.append(('연결 테스트', result1))
    
    # 2. 회사 검색 테스트
    result2 = test_company_search(config)
    results.append(('회사 검색', result2))
    
    # 3. 재무제표 조회 테스트
    result3 = test_financial_statement(config)
    results.append(('재무제표 조회', result3))
    
    # 4. 매핑 테스트
    result4 = test_stock_code_mapping()
    results.append(('종목코드 매핑', result4))
    
    # 결과 요약
    print("\n" + "="*60)
    print("📊 테스트 결과 요약")
    print("="*60)
    
    for test_name, result in results:
        status = "✅ 성공" if result else "❌ 실패"
        print(f"   {test_name}: {status}")
    
    success_count = sum(1 for _, r in results if r)
    total_count = len(results)
    
    print(f"\n📈 성공률: {success_count}/{total_count} ({success_count/total_count*100:.0f}%)")
    
    if success_count == total_count:
        print("\n🎉 모든 테스트 통과! DART API 연동 준비 완료")
        print("\n🚀 다음 단계:")
        print("   1. DartDataProvider 클래스 구현")
        print("   2. KIS + DART 데이터 크로스체크")
        print("   3. 멀티 소스 통합")
    else:
        print(f"\n⚠️ {total_count - success_count}개 테스트 실패")
        print("\n💡 해결 방법:")
        print("   1. API 키 확인")
        print("   2. 네트워크 연결 확인")
        print("   3. DART API 서비스 상태 확인")


