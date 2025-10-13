#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
섹터 통계 캐시 매니저 v1.0

목적:
- 앱 시작 시 섹터별 통계 프리컴퓨팅
- n=0 문제 해결 (섹터 표본 부족)
- 섹터 중립 평가 정확도 향상

기능:
1. 전체 종목 수집 (1000~2000개)
2. 섹터별 분리 및 통계 계산
3. 퍼센타일 캐싱 (24시간)
4. 자동 갱신
"""

import os
import pickle
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)

class SectorCacheManager:
    """섹터 통계 캐시 매니저"""
    
    def __init__(self, cache_dir: str = 'cache', ttl_hours: int = 24):
        """
        Args:
            cache_dir: 캐시 디렉토리
            ttl_hours: 캐시 유효 시간 (시간)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / 'sector_stats.pkl'
        self.ttl_seconds = ttl_hours * 3600
        
        logger.info(f"✅ SectorCacheManager 초기화 (TTL: {ttl_hours}시간)")
    
    def is_cache_valid(self) -> bool:
        """캐시가 유효한지 확인"""
        if not self.cache_file.exists():
            return False
        
        mtime = self.cache_file.stat().st_mtime
        age = time.time() - mtime
        
        if age < self.ttl_seconds:
            logger.info(f"✅ 캐시 유효 (생성: {datetime.fromtimestamp(mtime)}, 남은 시간: {(self.ttl_seconds - age)/3600:.1f}시간)")
            return True
        else:
            logger.info(f"⏰ 캐시 만료 (생성: {datetime.fromtimestamp(mtime)}, 경과: {age/3600:.1f}시간)")
            return False
    
    def load_cache(self) -> Optional[Dict[str, Dict[str, Any]]]:
        """캐시 로드"""
        try:
            with open(self.cache_file, 'rb') as f:
                sector_stats = pickle.load(f)
            
            logger.info(f"✅ 섹터 캐시 로드: {len(sector_stats)}개 섹터")
            
            # 요약 출력
            for sector, stats in sector_stats.items():
                n = stats.get('sample_size', 0)
                logger.debug(f"  {sector}: n={n}")
            
            return sector_stats
        
        except Exception as e:
            logger.error(f"❌ 캐시 로드 실패: {e}")
            return None
    
    def save_cache(self, sector_stats: Dict[str, Dict[str, Any]]):
        """캐시 저장"""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(sector_stats, f)
            
            logger.info(f"✅ 섹터 캐시 저장: {len(sector_stats)}개 섹터 → {self.cache_file}")
        
        except Exception as e:
            logger.error(f"❌ 캐시 저장 실패: {e}")
    
    def calculate_percentiles(self, values: List[float]) -> Dict[str, float]:
        """퍼센타일 계산"""
        if not values:
            return {}
        
        # 유효한 값만 필터링
        valid_values = [v for v in values if v is not None and not np.isnan(v) and v != 0]
        
        if len(valid_values) < 3:
            return {}
        
        try:
            percentiles = {
                'p10': float(np.percentile(valid_values, 10)),
                'p25': float(np.percentile(valid_values, 25)),
                'p50': float(np.percentile(valid_values, 50)),
                'p75': float(np.percentile(valid_values, 75)),
                'p90': float(np.percentile(valid_values, 90)),
                'mean': float(np.mean(valid_values)),
                'std': float(np.std(valid_values)),
                'min': float(np.min(valid_values)),
                'max': float(np.max(valid_values)),
            }
            return percentiles
        
        except Exception as e:
            logger.warning(f"퍼센타일 계산 실패: {e}")
            return {}
    
    def compute_sector_stats(self, stock_provider) -> Dict[str, Dict[str, Any]]:
        """
        섹터 통계 계산
        
        Args:
            stock_provider: KIS API 또는 기타 데이터 제공자
        
        Returns:
            섹터별 통계 딕셔너리
        """
        logger.info("🔄 섹터 통계 프리컴퓨팅 시작...")
        logger.info("="*60)
        logger.info("⚠️ 알림: 섹터별 퍼센타일 계산을 위해 전체 시장 데이터를 수집합니다.")
        logger.info("         (사용자가 선택한 종목 수와 무관하게 ~1000개 수집)")
        logger.info("="*60)
        
        try:
            # 1. 전체 종목 수집 (빠른 모드)
            logger.info("  📊 1단계: 전체 시장 데이터 수집 중... (목표: 1000개)")
            
            # ValueStockFinder를 통해 종목 수집 (max_count=1000)
            all_stocks = stock_provider.get_stock_universe(max_count=1000)
            
            if not all_stocks or len(all_stocks) < 100:
                logger.warning(f"⚠️ 종목 수집 부족: {len(all_stocks) if all_stocks else 0}개")
                return {}
            
            logger.info(f"  ✅ 1단계 완료: {len(all_stocks)}개 종목 수집 (섹터 통계용)")
            
            # 2. 섹터별 분리
            logger.info("  2단계: 섹터별 분리 중...")
            sector_groups = {}
            
            # ✅ v2.2.3: 섹터명 정규화 필요 - ValueStockFinder의 정규화 사용
            for stock_code, stock_data in all_stocks.items():
                raw_sector = stock_data.get('sector', '기타')
                
                # ValueStockFinder가 아닌 경우 간단한 정규화
                if hasattr(stock_provider, '_normalize_sector_name'):
                    sector = stock_provider._normalize_sector_name(raw_sector)
                else:
                    sector = raw_sector  # 정규화 없이 원본 사용
                
                if sector not in sector_groups:
                    sector_groups[sector] = []
                
                sector_groups[sector].append(stock_data)
            
            logger.info(f"  ✅ {len(sector_groups)}개 섹터 발견")
            
            # 3. 섹터별 통계 계산
            logger.info("  3단계: 섹터별 통계 계산 중...")
            sector_stats = {}
            
            for sector, stocks in sector_groups.items():
                n = len(stocks)
                
                # 최소 표본 크기 확인 (30개 이상)
                if n < 30:
                    logger.debug(f"  ⚠️ {sector}: 표본 부족 (n={n}) → 제외")
                    continue
                
                # PER, PBR, ROE 추출
                per_values = [s.get('per') for s in stocks if s.get('per')]
                pbr_values = [s.get('pbr') for s in stocks if s.get('pbr')]
                roe_values = [s.get('roe') for s in stocks if s.get('roe')]
                
                # 퍼센타일 계산
                per_percentiles = self.calculate_percentiles(per_values)
                pbr_percentiles = self.calculate_percentiles(pbr_values)
                roe_percentiles = self.calculate_percentiles(roe_values)
                
                # 통계 저장
                sector_stats[sector] = {
                    'sample_size': n,
                    'per_percentiles': per_percentiles,
                    'pbr_percentiles': pbr_percentiles,
                    'roe_percentiles': roe_percentiles,
                    'timestamp': datetime.now().isoformat(),
                }
                
                logger.info(f"  ✅ {sector}: n={n}")
            
            logger.info(f"✅ 섹터 통계 계산 완료: {len(sector_stats)}개 섹터")
            
            return sector_stats
        
        except Exception as e:
            logger.error(f"❌ 섹터 통계 계산 실패: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def get_or_compute(self, stock_provider) -> Dict[str, Dict[str, Any]]:
        """
        캐시 로드 또는 계산
        
        Args:
            stock_provider: 데이터 제공자
        
        Returns:
            섹터 통계 딕셔너리
        """
        # 캐시 확인
        if self.is_cache_valid():
            sector_stats = self.load_cache()
            if sector_stats:
                return sector_stats
        
        # 캐시 없거나 만료 → 재계산
        logger.info("🔄 섹터 통계 재계산 시작...")
        sector_stats = self.compute_sector_stats(stock_provider)
        
        if sector_stats:
            self.save_cache(sector_stats)
        
        return sector_stats
    
    def force_refresh(self, stock_provider) -> Dict[str, Dict[str, Any]]:
        """강제 갱신"""
        logger.info("🔄 섹터 통계 강제 갱신...")
        
        # 기존 캐시 삭제
        if self.cache_file.exists():
            self.cache_file.unlink()
            logger.info("  🗑️ 기존 캐시 삭제")
        
        # 재계산
        sector_stats = self.compute_sector_stats(stock_provider)
        
        if sector_stats:
            self.save_cache(sector_stats)
        
        return sector_stats
    
    def get_sector_stat(self, sector: str) -> Optional[Dict[str, Any]]:
        """특정 섹터 통계 조회"""
        if not self.is_cache_valid():
            return None
        
        sector_stats = self.load_cache()
        return sector_stats.get(sector) if sector_stats else None


# ============================================
# 전역 인스턴스 (싱글톤)
# ============================================
_global_cache_manager: Optional[SectorCacheManager] = None

def get_cache_manager() -> SectorCacheManager:
    """전역 캐시 매니저 반환 (싱글톤)"""
    global _global_cache_manager
    
    if _global_cache_manager is None:
        _global_cache_manager = SectorCacheManager()
    
    return _global_cache_manager


# ============================================
# 편의 함수
# ============================================
def initialize_sector_cache(stock_provider, force: bool = False) -> Dict[str, Dict[str, Any]]:
    """
    섹터 캐시 초기화 (앱 시작 시 호출)
    
    Args:
        stock_provider: 데이터 제공자
        force: 강제 갱신 여부
    
    Returns:
        섹터 통계 딕셔너리
    """
    manager = get_cache_manager()
    
    if force:
        return manager.force_refresh(stock_provider)
    else:
        return manager.get_or_compute(stock_provider)


if __name__ == "__main__":
    # 테스트
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*60)
    print("섹터 캐시 매니저 테스트")
    print("="*60)
    
    # 더미 데이터 생성
    class DummyProvider:
        def get_stock_universe(self, limit):
            import random
            sectors = ['전기전자', '운송장비', '금융', '제조업', 'IT', '화학']
            stocks = {}
            
            for i in range(limit):
                sector = random.choice(sectors)
                stocks[f"{i:06d}"] = {
                    'name': f'종목{i}',
                    'sector': sector,
                    'per': random.uniform(5, 30),
                    'pbr': random.uniform(0.5, 3.0),
                    'roe': random.uniform(3, 20),
                }
            
            return stocks
    
    provider = DummyProvider()
    
    # 초기화
    stats = initialize_sector_cache(provider, force=True)
    
    print("\n✅ 섹터 통계:")
    for sector, data in stats.items():
        n = data['sample_size']
        per_p50 = data['per_percentiles'].get('p50', 0)
        print(f"  {sector}: n={n}, PER 중앙값={per_p50:.1f}")
    
    print("\n" + "="*60)
    print("테스트 완료!")
    print("="*60)

