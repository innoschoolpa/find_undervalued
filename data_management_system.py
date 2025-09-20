#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
데이터 관리 시스템
- 데이터 영속성 및 재사용
- 캐시 관리 및 최적화
- 데이터 무결성 보장
"""

import os
import json
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)

class DataManagementSystem:
    """데이터 관리 시스템"""
    
    def __init__(self, data_dir: str = "data", cache_dir: str = "cache"):
        self.data_dir = Path(data_dir)
        self.cache_dir = Path(cache_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        
        # 데이터베이스 파일들
        self.stock_db = self.cache_dir / "stock_data.db"
        self.analysis_db = self.data_dir / "analysis_results.db"
        self.metadata_file = self.data_dir / "metadata.json"
        
        self.init_databases()
        self.load_metadata()
    
    def init_databases(self):
        """데이터베이스 초기화"""
        try:
            # 주가 데이터베이스
            with sqlite3.connect(self.stock_db) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS stock_prices (
                        symbol TEXT,
                        date TEXT,
                        open_price REAL,
                        high_price REAL,
                        low_price REAL,
                        close_price REAL,
                        volume INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        data_hash TEXT,
                        PRIMARY KEY (symbol, date)
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS stock_metadata (
                        symbol TEXT PRIMARY KEY,
                        company_name TEXT,
                        market_cap REAL,
                        sector TEXT,
                        last_updated TIMESTAMP,
                        data_quality_score REAL,
                        record_count INTEGER
                    )
                ''')
                
                conn.commit()
            
            # 분석 결과 데이터베이스
            with sqlite3.connect(self.analysis_db) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS analysis_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        analysis_type TEXT,
                        symbols TEXT,
                        parameters TEXT,
                        results TEXT,
                        performance_metrics TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        analysis_hash TEXT
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS backtest_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbols TEXT,
                        start_date TEXT,
                        end_date TEXT,
                        parameters TEXT,
                        total_return REAL,
                        sharpe_ratio REAL,
                        max_drawdown REAL,
                        win_rate REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        result_hash TEXT
                    )
                ''')
                
                conn.commit()
            
            logger.info("데이터베이스 초기화 완료")
            
        except Exception as e:
            logger.error(f"데이터베이스 초기화 실패: {e}")
            raise
    
    def load_metadata(self):
        """메타데이터 로드"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            else:
                self.metadata = {
                    'last_cleanup': None,
                    'total_analyses': 0,
                    'cache_hit_rate': 0.0,
                    'data_quality_scores': {}
                }
        except Exception as e:
            logger.error(f"메타데이터 로드 실패: {e}")
            self.metadata = {}
    
    def save_metadata(self):
        """메타데이터 저장"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"메타데이터 저장 실패: {e}")
    
    def calculate_data_hash(self, data: pd.DataFrame) -> str:
        """데이터 해시 계산"""
        try:
            data_str = data.to_string()
            return hashlib.md5(data_str.encode()).hexdigest()
        except Exception as e:
            logger.error(f"해시 계산 실패: {e}")
            return ""
    
    def store_stock_data(self, symbol: str, data: pd.DataFrame, 
                        company_name: str = None, market_cap: float = None, 
                        sector: str = None) -> bool:
        """주가 데이터 저장"""
        try:
            if data.empty:
                return False
            
            data_hash = self.calculate_data_hash(data)
            
            with sqlite3.connect(self.stock_db) as conn:
                cursor = conn.cursor()
                
                # 기존 데이터 삭제
                cursor.execute('DELETE FROM stock_prices WHERE symbol = ?', [symbol])
                
                # 새 데이터 삽입
                for _, row in data.iterrows():
                    cursor.execute('''
                        INSERT INTO stock_prices 
                        (symbol, date, open_price, high_price, low_price, close_price, volume, data_hash)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', [
                        symbol,
                        row['date'].strftime('%Y-%m-%d'),
                        row.get('open', 0),
                        row.get('high', 0),
                        row.get('low', 0),
                        row.get('close', 0),
                        row.get('volume', 0),
                        data_hash
                    ])
                
                # 메타데이터 업데이트
                data_quality = self.calculate_data_quality(data)
                cursor.execute('''
                    INSERT OR REPLACE INTO stock_metadata
                    (symbol, company_name, market_cap, sector, last_updated, data_quality_score, record_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', [symbol, company_name, market_cap, sector, datetime.now(), data_quality, len(data)])
                
                conn.commit()
                logger.info(f"주가 데이터 저장 완료: {symbol} ({len(data)}건)")
                return True
                
        except Exception as e:
            logger.error(f"주가 데이터 저장 실패 {symbol}: {e}")
            return False
    
    def get_stock_data(self, symbol: str, start_date: str = None, 
                      end_date: str = None) -> Optional[pd.DataFrame]:
        """주가 데이터 조회"""
        try:
            with sqlite3.connect(self.stock_db) as conn:
                query = '''
                    SELECT date, open_price, high_price, low_price, close_price, volume
                    FROM stock_prices
                    WHERE symbol = ?
                '''
                params = [symbol]
                
                if start_date:
                    query += ' AND date >= ?'
                    params.append(start_date)
                
                if end_date:
                    query += ' AND date <= ?'
                    params.append(end_date)
                
                query += ' ORDER BY date'
                
                df = pd.read_sql_query(query, conn, params=params)
                
                if not df.empty:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.rename(columns={
                        'open_price': 'open',
                        'high_price': 'high',
                        'low_price': 'low',
                        'close_price': 'close',
                        'volume': 'volume'
                    })
                    logger.info(f"주가 데이터 조회 성공: {symbol} ({len(df)}건)")
                    return df
                else:
                    logger.info(f"주가 데이터 없음: {symbol}")
                    return None
                    
        except Exception as e:
            logger.error(f"주가 데이터 조회 실패 {symbol}: {e}")
            return None
    
    def calculate_data_quality(self, data: pd.DataFrame) -> float:
        """데이터 품질 점수 계산"""
        try:
            if data.empty:
                return 0.0
            
            score = 1.0
            
            # 누락 데이터 체크
            missing_ratio = data.isnull().sum().sum() / (len(data) * len(data.columns))
            score -= missing_ratio * 0.3
            
            # 중복 데이터 체크
            duplicate_ratio = data.duplicated().sum() / len(data)
            score -= duplicate_ratio * 0.2
            
            # 데이터 일관성 체크
            if 'close' in data.columns:
                negative_prices = (data['close'] <= 0).sum()
                score -= (negative_prices / len(data)) * 0.3
            
            # 시간 연속성 체크
            if 'date' in data.columns and len(data) > 1:
                data_sorted = data.sort_values('date')
                date_diff = data_sorted['date'].diff().dt.days
                gaps = (date_diff > 7).sum()  # 7일 이상 간격
                score -= (gaps / len(data)) * 0.2
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"데이터 품질 계산 실패: {e}")
            return 0.0
    
    def store_analysis_result(self, analysis_type: str, symbols: List[str], 
                            parameters: Dict, results: Dict, 
                            performance_metrics: Dict = None) -> str:
        """분석 결과 저장"""
        try:
            analysis_hash = self.calculate_data_hash(
                pd.DataFrame({'symbols': symbols, 'parameters': [str(parameters)]})
            )
            
            with sqlite3.connect(self.analysis_db) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO analysis_results
                    (analysis_type, symbols, parameters, results, performance_metrics, analysis_hash)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', [
                    analysis_type,
                    json.dumps(symbols),
                    json.dumps(parameters),
                    json.dumps(results),
                    json.dumps(performance_metrics or {}),
                    analysis_hash
                ])
                
                conn.commit()
                result_id = cursor.lastrowid
                
                # 메타데이터 업데이트
                self.metadata['total_analyses'] += 1
                self.save_metadata()
                
                logger.info(f"분석 결과 저장 완료: {analysis_type} (ID: {result_id})")
                return str(result_id)
                
        except Exception as e:
            logger.error(f"분석 결과 저장 실패: {e}")
            return ""
    
    def store_backtest_result(self, symbols: List[str], start_date: str, 
                            end_date: str, parameters: Dict, 
                            total_return: float, sharpe_ratio: float, 
                            max_drawdown: float, win_rate: float) -> str:
        """백테스트 결과 저장"""
        try:
            result_hash = self.calculate_data_hash(
                pd.DataFrame({'symbols': symbols, 'start_date': [start_date], 'end_date': [end_date]})
            )
            
            with sqlite3.connect(self.analysis_db) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO backtest_results
                    (symbols, start_date, end_date, parameters, total_return, sharpe_ratio, max_drawdown, win_rate, result_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', [
                    json.dumps(symbols),
                    start_date,
                    end_date,
                    json.dumps(parameters),
                    total_return,
                    sharpe_ratio,
                    max_drawdown,
                    win_rate,
                    result_hash
                ])
                
                conn.commit()
                result_id = cursor.lastrowid
                
                logger.info(f"백테스트 결과 저장 완료: {symbols} (ID: {result_id})")
                return str(result_id)
                
        except Exception as e:
            logger.error(f"백테스트 결과 저장 실패: {e}")
            return ""
    
    def get_analysis_history(self, analysis_type: str = None, 
                           limit: int = 10) -> List[Dict]:
        """분석 이력 조회"""
        try:
            with sqlite3.connect(self.analysis_db) as conn:
                query = '''
                    SELECT id, analysis_type, symbols, parameters, results, performance_metrics, created_at
                    FROM analysis_results
                '''
                params = []
                
                if analysis_type:
                    query += ' WHERE analysis_type = ?'
                    params.append(analysis_type)
                
                query += ' ORDER BY created_at DESC LIMIT ?'
                params.append(limit)
                
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'id': row[0],
                        'analysis_type': row[1],
                        'symbols': json.loads(row[2]),
                        'parameters': json.loads(row[3]),
                        'results': json.loads(row[4]),
                        'performance_metrics': json.loads(row[5]),
                        'created_at': row[6]
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"분석 이력 조회 실패: {e}")
            return []
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """오래된 데이터 정리"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with sqlite3.connect(self.stock_db) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM stock_prices 
                    WHERE created_at < ?
                ''', [cutoff_date])
                deleted_stocks = cursor.rowcount
                conn.commit()
            
            with sqlite3.connect(self.analysis_db) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM analysis_results 
                    WHERE created_at < ?
                ''', [cutoff_date])
                deleted_analyses = cursor.rowcount
                conn.commit()
            
            # 메타데이터 업데이트
            self.metadata['last_cleanup'] = datetime.now().isoformat()
            self.save_metadata()
            
            logger.info(f"데이터 정리 완료: 주가 {deleted_stocks}건, 분석 {deleted_analyses}건")
            return deleted_stocks + deleted_analyses
            
        except Exception as e:
            logger.error(f"데이터 정리 실패: {e}")
            return 0
    
    def get_system_stats(self) -> Dict[str, Any]:
        """시스템 통계 조회"""
        try:
            stats = {}
            
            # 주가 데이터 통계
            with sqlite3.connect(self.stock_db) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(DISTINCT symbol) FROM stock_prices')
                stats['total_symbols'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM stock_prices')
                stats['total_price_records'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT AVG(data_quality_score) FROM stock_metadata')
                stats['avg_data_quality'] = cursor.fetchone()[0] or 0.0
            
            # 분석 데이터 통계
            with sqlite3.connect(self.analysis_db) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM analysis_results')
                stats['total_analyses'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM backtest_results')
                stats['total_backtests'] = cursor.fetchone()[0]
            
            # 메타데이터
            stats.update(self.metadata)
            
            return stats
            
        except Exception as e:
            logger.error(f"시스템 통계 조회 실패: {e}")
            return {}

def main():
    """테스트 함수"""
    dms = DataManagementSystem()
    
    # 테스트 데이터 생성
    test_data = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=30),
        'open': [100 + i for i in range(30)],
        'high': [105 + i for i in range(30)],
        'low': [95 + i for i in range(30)],
        'close': [102 + i for i in range(30)],
        'volume': [1000000 + i * 10000 for i in range(30)]
    })
    
    # 데이터 저장
    dms.store_stock_data('TEST001', test_data, '테스트회사', 1000000, 'IT')
    
    # 데이터 조회
    retrieved_data = dms.get_stock_data('TEST001')
    print(f"조회된 데이터: {len(retrieved_data)}건")
    print(retrieved_data.head())
    
    # 시스템 통계
    stats = dms.get_system_stats()
    print(f"\n시스템 통계: {stats}")

if __name__ == "__main__":
    main()


