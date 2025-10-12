#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
경고 메시지 최적화
"""

class WarningOptimization:
    """경고 메시지 최적화"""
    
    @staticmethod
    def reduce_api_warnings():
        """API 경고 최소화"""
        return """
        # kis_data_provider.py에서
        # Before: WARNING 레벨
        logger.warning(f"⚠️ 서버 내부 오류 (500) - {delay:.1f}초 후 재시도 ({retry}/{max_retries})")
        
        # After: DEBUG 레벨 (정상적인 재시도)
        logger.debug(f"서버 오류 재시도: {delay:.1f}초 후 ({retry}/{max_retries})")
        """
    
    @staticmethod
    def consolidate_dummy_detection():
        """더미 데이터 감지 통합"""
        return """
        # Before: 여러 경고
        logger.warning(f"더미 데이터 감지 (필드 누락): {symbol} - {missing_count}/5 필드 누락")
        logger.warning(f"더미 데이터 감지 - 평가 제외: {symbol}")
        
        # After: 하나의 요약 경고
        logger.info(f"데이터 품질 관리: {symbol} 제외 ({missing_count}/5 필드 누락)")
        """
    
    @staticmethod
    def improve_negative_per_message():
        """음수 PER 메시지 개선"""
        return """
        # Before: INFO 레벨
        logger.info(f"음수 PER 대체 평가 적용: {symbol} - 대체점수 {score:.1f}점")
        
        # After: DEBUG 레벨 (정상적인 처리)
        logger.debug(f"음수 PER 대체 평가: {symbol} → {score:.1f}점")
        """

if __name__ == '__main__':
    print("=== 경고 메시지 최적화 ===\n")
    
    opt = WarningOptimization()
    
    print("1. API 경고 최소화")
    print(opt.reduce_api_warnings())
    
    print("\n2. 더미 데이터 감지 통합")
    print(opt.consolidate_dummy_detection())
    
    print("\n3. 음수 PER 메시지 개선")
    print(opt.improve_negative_per_message())
    
    print("\n💡 권장사항:")
    print("- 현재 경고들은 모두 정상 작동을 나타냄")
    print("- 시스템 안정성과 데이터 품질 관리를 보여줌")
    print("- 필요시 DEBUG 레벨로 변경하여 로그 노이즈 감소 가능")
