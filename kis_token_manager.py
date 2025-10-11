import yaml
import requests
import json
import os
import logging
import sys
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class KISTokenManager:
    """
    KIS API 인증 토큰을 관리하고, 파일 캐시를 통해 24시간 재사용하는 클래스.
    싱글턴 패턴을 적용하여 애플리케이션 전체에서 단일 인스턴스를 보장합니다.
    """
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(KISTokenManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_path: str = 'config.yaml', cache_path: str = '.kis_token_cache.json'):
        if self._initialized:
            return

        self.cache_path = cache_path
        self.base_url = "https://openapi.koreainvestment.com:9443"

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            self.app_key = config['kis_api']['app_key']
            self.app_secret = config['kis_api']['app_secret']
        except FileNotFoundError:
            logger.error(f"❌ 설정 파일({config_path})을 찾을 수 없습니다. API 키를 확인해주세요.")
            sys.exit(1)
        except KeyError:
            logger.error(f"❌ 설정 파일에 'kis_api' 또는 'app_key'/'app_secret' 항목이 없습니다.")
            sys.exit(1)

        self.token = None
        self.access_token = None  # 컬렉터들이 사용하는 속성
        self.headers = {}
        self._initialized = True

    def _load_token_from_cache(self) -> bool:
        """파일 캐시에서 토큰을 로드하고 유효성을 검사합니다."""
        if not os.path.exists(self.cache_path):
            logger.info("📝 토큰 캐시 파일이 없습니다. 새 토큰을 발급합니다.")
            return False

        try:
            with open(self.cache_path, 'r') as f:
                cache = json.load(f)

            # 캐시 파일에 필요한 키가 있는지 확인
            if 'token' not in cache or 'expires_at' not in cache:
                logger.warning("⚠️ 캐시 파일에 필요한 정보가 없습니다. 새 토큰을 발급합니다.")
                return False

            # ✅ expires_at 타입 호환 (ISO 문자열 or epoch 숫자)
            expires_at_value = cache['expires_at']
            current_time = datetime.now()
            
            if isinstance(expires_at_value, (int, float)):
                expires_at = datetime.fromtimestamp(expires_at_value)
            elif isinstance(expires_at_value, str):
                expires_at = datetime.fromisoformat(expires_at_value)
            else:
                logger.warning(f"⚠️ 알 수 없는 expires_at 타입: {type(expires_at_value)}")
                return False

            # 토큰이 유효한지 확인 (1시간 여유분 포함)
            if expires_at > current_time + timedelta(hours=1):
                self.token = cache['token']
                self.access_token = self.token  # 컬렉터들이 사용하는 속성
                # 토큰이 비어있지 않은지 확인
                if not self.token or self.token.strip() == "":
                    logger.warning("⚠️ 캐시된 토큰이 비어있습니다. 새 토큰을 발급합니다.")
                    return False

                self._update_headers()
                remaining_time = expires_at - current_time
                logger.info(f"♻️ 캐시된 토큰을 재사용합니다. (만료: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}, 남은 시간: {remaining_time})")
                return True
            else:
                logger.info("⚠️ 캐시된 토큰이 만료되었거나 만료가 임박하여 갱신합니다.")
                return False

        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.warning(f"⚠️ 캐시 파일이 손상되었거나 읽을 수 없습니다: {e}. 새 토큰을 발급합니다.")
            return False

    def _save_token_to_cache(self, token_data: dict):
        """발급받은 토큰 정보와 만료 시간을 파일에 저장합니다."""
        try:
            expires_in = token_data.get('expires_in', 86400)
            expires_at = datetime.now() + timedelta(seconds=expires_in)

            cache = {'token': self.token, 'expires_at': expires_at.isoformat()}
            with open(self.cache_path, 'w') as f:
                json.dump(cache, f)
            logger.info(f"✅ 토큰 정보를 '{self.cache_path}' 파일에 저장했습니다.")
        except OSError as e:
            logger.error(f"❌ 토큰 캐시 파일 저장에 실패했습니다: {e}")

    def _issue_new_token(self):
        """KIS API 서버로부터 새로운 인증 토큰을 발급받습니다."""
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        body = {"grant_type": "client_credentials", "appkey": self.app_key, "appsecret": self.app_secret}

        try:
            response = requests.post(url, headers=headers, data=json.dumps(body), timeout=5)
            response.raise_for_status()
            token_data = response.json()

            self.token = token_data.get('access_token')
            self.access_token = self.token  # 컬렉터들이 사용하는 속성
            if not self.token:
                logger.error("❌ 토큰 발급 응답에 'access_token'이 없습니다.")
                return False

            self._update_headers()
            self._save_token_to_cache(token_data)
            logger.info("✅ KIS API 인증 토큰을 새로 발급받았습니다.")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ KIS API 토큰 발급 요청 실패: {e}")
            return False

    def _update_headers(self):
        """API 요청에 사용할 표준 헤더를 업데이트합니다."""
        self.headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {self.token}",
            "appKey": self.app_key,
            "appSecret": self.app_secret,
            "tr_id": "FHKST01010100"
        }

    def authenticate(self):
        """메인 인증 메서드. 저장된 토큰 확인 후, 필요 시 새로 발급합니다."""
        # 먼저 저장된 토큰의 유효성을 확인
        if self._load_token_from_cache():
            # 캐시에서 유효한 토큰을 로드했다면 인증 완료
            return

        # 저장된 토큰이 없거나 유효하지 않으면 새로 발급
        self._issue_new_token()

    def _is_token_expired(self) -> bool:
        """
        토큰이 만료되었는지 확인합니다.

        Returns:
            bool: 토큰이 만료되었으면 True, 그렇지 않으면 False
        """
        if not os.path.exists(self.cache_path):
            return True

        try:
            with open(self.cache_path, 'r') as f:
                cache = json.load(f)

            if 'expires_at' not in cache:
                return True

            # ✅ expires_at 타입 호환 (ISO 문자열 or epoch 숫자)
            expires_at_value = cache['expires_at']
            current_time = datetime.now()
            
            if isinstance(expires_at_value, (int, float)):
                expires_at = datetime.fromtimestamp(expires_at_value)
            elif isinstance(expires_at_value, str):
                expires_at = datetime.fromisoformat(expires_at_value)
            else:
                return True  # 알 수 없는 타입이면 만료로 간주

            # 1시간 여유분을 두고 만료 확인
            return expires_at <= current_time + timedelta(hours=1)
        except (json.JSONDecodeError, KeyError, OSError):
            return True

    def get_valid_token(self) -> str:
        """
        유효한 토큰을 반환합니다. 토큰이 없거나 만료된 경우 새로 발급합니다.

        Returns:
            str: 유효한 액세스 토큰
        """
        # 토큰이 없거나 만료된 경우 새로 발급
        if not self.access_token or self._is_token_expired():
            self.authenticate()

        return self.access_token

# 전역 함수로 토큰 매니저 인스턴스 반환
def get_token_manager(config_path: str = 'config.yaml') -> KISTokenManager:
    """
    KISTokenManager 싱글턴 인스턴스를 반환하는 전역 함수

    Args:
        config_path (str): 설정 파일 경로

    Returns:
        KISTokenManager: 토큰 매니저 인스턴스
    """
    return KISTokenManager(config_path)

