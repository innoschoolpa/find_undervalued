"""
인터페이스 및 추상 클래스 모듈

데이터 제공자와 점수 계산기의 추상 클래스를 제공합니다.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class DataProvider(ABC):
    """데이터 제공자 추상 클래스"""
    
    @abstractmethod
    def get_financial_data(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        금융 데이터 조회
        
        Args:
            symbol: 종목 코드
            **kwargs: 추가 파라미터
        
        Returns:
            Dict: 금융 데이터
        """
        pass
    
    @abstractmethod
    def get_price_data(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        가격 데이터 조회
        
        Args:
            symbol: 종목 코드
            **kwargs: 추가 파라미터
        
        Returns:
            Dict: 가격 데이터
        """
        pass


class ScoreCalculator(ABC):
    """점수 계산기 추상 클래스"""
    
    @abstractmethod
    def calculate_score(self, data: Dict[str, Any]) -> float:
        """
        점수 계산
        
        Args:
            data: 분석 데이터 딕셔너리
        
        Returns:
            float: 계산된 점수
        """
        pass













