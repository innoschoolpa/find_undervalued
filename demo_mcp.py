#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP KIS Integration 데모 스크립트

사용법:
    python demo_mcp.py

필요사항:
    1. config.yaml 파일에 KIS API 키 설정
    2. 또는 환경변수 설정:
       - KIS_APP_KEY
       - KIS_APP_SECRET
"""

import sys
import logging
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def load_config():
    """config.yaml 또는 환경변수에서 KIS API 키 로드"""
    import os
    
    # 1. 환경변수 우선
    app_key = os.environ.get('KIS_APP_KEY')
    app_secret = os.environ.get('KIS_APP_SECRET')
    
    if app_key and app_secret:
        logger.info("✅ 환경변수에서 KIS API 키 로드")
        return app_key, app_secret
    
    # 2. config.yaml 파일
    config_file = Path("config.yaml")
    if not config_file.exists():
        logger.error("❌ config.yaml 파일이 없습니다.")
        logger.info("💡 생성 방법:")
        logger.info("   1. config.yaml 파일 생성")
        logger.info("   2. 아래 내용 입력:")
        logger.info("      appkey: YOUR_APP_KEY")
        logger.info("      appsecret: YOUR_APP_SECRET")
        logger.info("")
        logger.info("   또는 환경변수 설정:")
        logger.info("      set KIS_APP_KEY=YOUR_KEY")
        logger.info("      set KIS_APP_SECRET=YOUR_SECRET")
        return None, None
    
    try:
        import yaml
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 최상위 레벨에서 찾기
        app_key = config.get('appkey') or config.get('app_key')
        app_secret = config.get('appsecret') or config.get('app_secret')
        
        # kis_api 섹션에서도 찾기
        if not app_key or not app_secret:
            kis_config = config.get('kis_api', {})
            if kis_config:
                app_key = app_key or kis_config.get('app_key') or kis_config.get('appkey')
                app_secret = app_secret or kis_config.get('app_secret') or kis_config.get('appsecret')
        
        if app_key and app_secret:
            logger.info("✅ config.yaml에서 KIS API 키 로드")
            return app_key, app_secret
        else:
            logger.error("❌ config.yaml에 appkey/appsecret이 없습니다.")
            return None, None
            
    except ImportError:
        logger.error("❌ PyYAML이 설치되지 않았습니다: pip install pyyaml")
        return None, None
    except Exception as e:
        logger.error(f"❌ config.yaml 로드 실패: {e}")
        return None, None

def demo_basic_queries(mcp):
    """기본 API 조회 데모"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("📊 1. 기본 시세 조회 데모")
    logger.info("=" * 80)
    
    # 삼성전자 현재가
    logger.info("🔍 삼성전자(005930) 현재가 조회...")
    price_data = mcp.get_current_price("005930")
    
    if price_data:
        price = mcp._to_float(price_data.get('stck_prpr'))
        change = mcp._to_float(price_data.get('prdy_ctrt'))
        volume = mcp._to_int(price_data.get('acml_vol'))
        
        logger.info(f"✅ 현재가: {price:,.0f}원")
        logger.info(f"   전일대비: {change:+.2f}%")
        logger.info(f"   거래량: {volume:,}주")
    else:
        logger.warning("⚠️ 시세 조회 실패")
    
    # 시가총액 상위 10개
    logger.info("")
    logger.info("🔍 시가총액 상위 10개 조회...")
    market_cap = mcp.get_market_cap_ranking(limit=10)
    
    if market_cap:
        logger.info(f"✅ {len(market_cap)}개 종목 조회 완료:")
        for i, stock in enumerate(market_cap[:5], 1):
            name = stock.get('hts_kor_isnm', '?')
            cap = mcp._to_float(stock.get('hts_avls'))
            logger.info(f"   {i}. {name}: {cap:,.0f}억원")
        if len(market_cap) > 5:
            logger.info(f"   ... 외 {len(market_cap)-5}개")
    else:
        logger.warning("⚠️ 시가총액 순위 조회 실패")

def demo_stock_analysis(mcp):
    """종목 분석 데모"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("📈 2. 종목 종합 분석 데모")
    logger.info("=" * 80)
    
    # 종목명으로 조회 (자동 코드 변환)
    stock_name = "삼성전자"
    logger.info(f"🔍 '{stock_name}' 종합 분석 중...")
    
    analysis = mcp.analyze_stock_comprehensive(stock_name)
    
    if analysis:
        logger.info(f"✅ 종합 분석 완료:")
        logger.info(f"   종목: {analysis['name']} ({analysis['symbol']})")
        logger.info(f"   섹터: {analysis['sector']}")
        logger.info(f"   현재가: {analysis['current_price']:,.0f}원")
        
        metrics = analysis.get('valuation_metrics', {})
        logger.info(f"   PER: {metrics.get('per', 0):.2f}")
        logger.info(f"   PBR: {metrics.get('pbr', 0):.2f}")
        logger.info(f"   ROE: {metrics.get('roe', 0):.1f}%")
        
        score = analysis.get('comprehensive_score', {})
        logger.info(f"   종합점수: {score.get('total_score', 0):.1f}점")
        logger.info(f"   등급: {score.get('grade', 'N/A')}")
        logger.info(f"   추천: {score.get('recommendation', 'N/A')}")
    else:
        logger.warning("⚠️ 종목 분석 실패")

def demo_value_stock_finder(mcp):
    """가치주 발굴 데모 (간단 버전)"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("🎯 3. 가치주 발굴 데모 (간단 버전)")
    logger.info("=" * 80)
    logger.info("⚠️  이 데모는 시간이 오래 걸릴 수 있습니다 (5-10분)")
    logger.info("⚠️  실전 사용은 value_stock_finder.py를 권장합니다")
    logger.info("")
    
    # 사용자 확인
    try:
        response = input("계속하시겠습니까? (y/n): ").strip().lower()
        if response != 'y':
            logger.info("⏭️  가치주 발굴 스킵")
            return
    except (KeyboardInterrupt, EOFError):
        logger.info("\n⏭️  가치주 발굴 스킵")
        return
    
    logger.info("🔍 가치주 발굴 시작 (최대 10개)...")
    logger.info("   기준: PER≤18, PBR≤2.0, ROE≥8%")
    
    try:
        value_stocks = mcp.find_real_value_stocks(
            limit=10,  # 빠른 데모를 위해 10개만
            criteria={
                'per_max': 18.0,
                'pbr_max': 2.0,
                'roe_min': 8.0,
            },
            candidate_pool_size=100,  # 후보군 축소 (빠른 실행)
            min_trading_value=5_000_000_000,  # 50억원
            quality_check=True,
            momentum_scoring=False,  # 모멘텀 비활성화 (빠른 실행)
        )
        
        if value_stocks and len(value_stocks) > 0:
            logger.info(f"✅ {len(value_stocks)}개 가치주 발굴 완료:")
            logger.info("")
            logger.info("-" * 80)
            
            for i, stock in enumerate(value_stocks, 1):
                name = stock['name']
                sector = stock['sector']
                score = stock['score']
                per = stock['per']
                pbr = stock['pbr']
                roe = stock['roe']
                weight = stock.get('proposed_weight', 0) * 100
                
                logger.info(f"{i:2d}. {name:12s} [{sector:8s}]")
                logger.info(f"    점수={score:5.1f} | PER={per:5.2f} PBR={pbr:5.2f} ROE={roe:5.1f}% | 비중={weight:4.1f}%")
            
            logger.info("-" * 80)
        else:
            logger.warning("⚠️ 가치주를 찾을 수 없습니다")
            
    except Exception as e:
        logger.error(f"❌ 가치주 발굴 실패: {e}")

def demo_search_by_name(mcp):
    """종목명 검색 데모"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("🔍 4. 종목명 검색 데모")
    logger.info("=" * 80)
    
    test_names = ["삼성전자", "시프트업", "KB금융", "카카오"]
    
    for name in test_names:
        code = mcp.search_stock_by_name(name)
        if code:
            logger.info(f"✅ '{name}' → {code}")
        else:
            logger.warning(f"⚠️ '{name}' 검색 실패")

def main():
    """메인 데모 실행"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("🚀 MCP KIS Integration 데모 시작")
    logger.info("=" * 80)
    
    # 1. API 키 로드
    app_key, app_secret = load_config()
    if not app_key or not app_secret:
        logger.error("❌ API 키를 로드할 수 없습니다. 종료합니다.")
        return 1
    
    # 2. OAuth 매니저 생성 (SimpleOAuthManager를 직접 구현)
    try:
        import json
        import time
        import requests
        import os
        
        class SimpleOAuthManager:
            """KIS OAuth 토큰 관리자 (value_stock_finder.py와 동일)"""
            def __init__(self, appkey, appsecret, is_test=False):
                self.appkey = appkey
                self.appsecret = appsecret
                self.app_key = appkey
                self.app_secret = appsecret
                self.is_test = is_test
                self.base_url = ("https://openapivts.koreainvestment.com:29443" if is_test 
                                else "https://openapi.koreainvestment.com:9443")
                self._rest_token = None
            
            def _refresh_rest_token(self):
                """REST 토큰 갱신 (KIS API 호출)"""
                for attempt in range(3):
                    try:
                        url = f"{self.base_url}/oauth2/tokenP"
                        headers = {"content-type": "application/json"}
                        body = {
                            "grant_type": "client_credentials",
                            "appkey": self.appkey,
                            "appsecret": self.appsecret
                        }
                        
                        response = requests.post(url, headers=headers, json=body, timeout=10)
                        if response.status_code == 200:
                            data = response.json()
                            token = data.get('access_token')
                            expires_in = data.get('expires_in', 86400)
                            exp = time.time() + expires_in
                            
                            with open('.kis_token_cache.json', 'w') as f:
                                json.dump({'token': token, 'expires_at': exp}, f)
                            
                            try:
                                os.chmod('.kis_token_cache.json', 0o600)
                            except Exception:
                                pass
                            
                            self._rest_token = token
                            logger.info("✅ OAuth 토큰 발급 성공")
                            return token
                        else:
                            logger.error(f"토큰 발급 실패 (시도 {attempt+1}/3): {response.status_code}")
                    except Exception as e:
                        logger.error(f"토큰 발급 예외 (시도 {attempt+1}/3): {e}")
                    
                    if attempt < 2:
                        time.sleep(0.5 * (2 ** attempt))
                
                logger.error("❌ 토큰 발급 최종 실패 (3회 시도)")
                return None
            
            def get_rest_token(self):
                """토큰 캐시에서 로드 + 만료 시 자동 갱신"""
                try:
                    if os.path.exists('.kis_token_cache.json'):
                        with open('.kis_token_cache.json', 'r') as f:
                            cache = json.load(f)
                        token = cache.get('token')
                        exp = cache.get('expires_at')
                        if token and exp and time.time() < exp - 120:
                            return token
                except Exception as e:
                    logger.debug(f"토큰 캐시 읽기 실패: {e}")
                
                return self._refresh_rest_token()
        
        logger.info("✅ SimpleOAuthManager 초기화")
        oauth = SimpleOAuthManager(appkey=app_key, appsecret=app_secret, is_test=False)
    
    except Exception as e:
        logger.error(f"❌ OAuth 매니저 생성 실패: {e}")
        return 1
    
    # 3. MCP 객체 생성
    try:
        from mcp_kis_integration import MCPKISIntegration
        
        logger.info("✅ MCPKISIntegration 초기화 중...")
        logger.info("   레이트 리밋: 0.5초 간격 (2건/초, AppKey 차단 방지)")
        
        mcp = MCPKISIntegration(
            oauth,
            request_interval=0.5,  # ⚠️ 안전한 간격
            timeout=(10, 30)
        )
        
        logger.info("✅ 초기화 완료!")
        
    except Exception as e:
        logger.error(f"❌ MCP 초기화 실패: {e}")
        return 1
    
    # 4. 데모 실행
    try:
        # 데모 1: 기본 조회
        demo_basic_queries(mcp)
        
        # 데모 2: 종목 분석
        demo_stock_analysis(mcp)
        
        # 데모 3: 종목명 검색
        demo_search_by_name(mcp)
        
        # 데모 4: 가치주 발굴 (선택적)
        demo_value_stock_finder(mcp)
        
    except KeyboardInterrupt:
        logger.info("\n⏸️  사용자가 중단했습니다")
    except Exception as e:
        logger.error(f"❌ 데모 실행 중 오류: {e}", exc_info=True)
        return 1
    finally:
        # 세션 종료
        try:
            mcp.close()
            logger.info("✅ 세션 종료")
        except:
            pass
    
    # 5. 완료
    logger.info("")
    logger.info("=" * 80)
    logger.info("✅ 모든 데모 완료!")
    logger.info("=" * 80)
    logger.info("")
    logger.info("💡 다음 단계:")
    logger.info("   1. value_stock_finder.py로 본격적인 가치주 발굴")
    logger.info("   2. mcp_kis_integration.py를 다른 스크립트에서 임포트")
    logger.info("   3. 자신만의 투자 전략 스크립트 작성")
    logger.info("")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n👋 종료합니다")
        sys.exit(0)

