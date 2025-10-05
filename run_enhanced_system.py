#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Integrated Analyzer 통합 실행 스크립트

KIS API 연동, 백테스팅, 포트폴리오 최적화 기능을 통합하여 실행합니다.
"""

import os
import sys
import logging
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional
import json

# 로컬 모듈 import
from enhanced_config_manager import create_enhanced_config_manager
from kis_api_manager import create_kis_api_manager, KISAPIConfig
from backtesting_engine import create_backtesting_engine, BacktestConfig, sample_value_strategy
from portfolio_optimizer import create_portfolio_optimizer, PortfolioConfig
from enhanced_integrated_analyzer_refactored import EnhancedIntegratedAnalyzer

class EnhancedSystemRunner:
    """Enhanced Integrated Analyzer 시스템 실행자"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        
        # 설정 관리자 초기화
        self.config_manager = create_enhanced_config_manager(config_file)
        
        # 시스템 구성 요소 초기화
        self.kis_api_manager = None
        self.backtesting_engine = None
        self.portfolio_optimizer = None
        self.analyzer = None
        
        self.logger.info("Enhanced System Runner 초기화 완료")
    
    def initialize_kis_api(self) -> bool:
        """KIS API 초기화"""
        try:
            # API 설정 확인
            api_key = self.config_manager.get('kis.api_key')
            api_secret = self.config_manager.get('kis.api_secret')
            
            if not api_key or not api_secret:
                self.logger.warning("KIS API 키가 설정되지 않았습니다. Mock 모드로 실행됩니다.")
                return False
            
            # KIS API 설정 생성
            api_config = KISAPIConfig(
                api_key=api_key,
                api_secret=api_secret,
                base_url=self.config_manager.get('kis.base_url', 'https://openapi.koreainvestment.com:9443'),
                max_tps=self.config_manager.get('kis.max_tps', 8),
                cache_ttl_price=self.config_manager.get('kis.cache_ttl_price', 5.0),
                cache_ttl_financial=self.config_manager.get('kis.cache_ttl_financial', 900.0),
                cache_max_keys=self.config_manager.get('kis.cache_max_keys', 2000)
            )
            
            self.kis_api_manager = create_kis_api_manager(api_config)
            
            # API 상태 확인
            status = self.kis_api_manager.get_api_status()
            if status['api_key_configured']:
                self.logger.info("KIS API 초기화 완료")
                return True
            else:
                self.logger.warning("KIS API 초기화 실패")
                return False
                
        except Exception as e:
            self.logger.error(f"KIS API 초기화 중 오류: {e}")
            return False
    
    def initialize_backtesting(self) -> bool:
        """백테스팅 엔진 초기화"""
        try:
            backtest_config = BacktestConfig(
                start_date=self.config_manager.get('backtest.start_date', '2020-01-01'),
                end_date=self.config_manager.get('backtest.end_date', '2024-12-31'),
                initial_capital=self.config_manager.get('backtest.initial_capital', 100000000),
                transaction_cost=self.config_manager.get('backtest.transaction_cost', 0.0015),
                rebalance_frequency=self.config_manager.get('backtest.rebalance_frequency', 'monthly'),
                max_positions=self.config_manager.get('backtest.max_positions', 20),
                min_weight=self.config_manager.get('backtest.min_weight', 0.01),
                max_weight=self.config_manager.get('backtest.max_weight', 0.15)
            )
            
            self.backtesting_engine = create_backtesting_engine(backtest_config)
            self.logger.info("백테스팅 엔진 초기화 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"백테스팅 엔진 초기화 중 오류: {e}")
            return False
    
    def initialize_portfolio_optimizer(self) -> bool:
        """포트폴리오 최적화 엔진 초기화"""
        try:
            portfolio_config = PortfolioConfig(
                max_stocks=self.config_manager.get('portfolio.max_stocks', 20),
                min_weight=self.config_manager.get('portfolio.min_weight', 0.01),
                max_weight=self.config_manager.get('portfolio.max_weight', 0.15),
                rebalance_frequency=self.config_manager.get('portfolio.rebalance_frequency', 'monthly'),
                risk_target=self.config_manager.get('portfolio.risk_target', 0.12),
                risk_free_rate=self.config_manager.get('portfolio.risk_free_rate', 0.03),
                transaction_cost=self.config_manager.get('portfolio.transaction_cost', 0.0015),
                max_turnover=self.config_manager.get('portfolio.max_turnover', 0.30)
            )
            
            self.portfolio_optimizer = create_portfolio_optimizer(portfolio_config)
            self.logger.info("포트폴리오 최적화 엔진 초기화 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"포트폴리오 최적화 엔진 초기화 중 오류: {e}")
            return False
    
    def initialize_analyzer(self) -> bool:
        """Enhanced Analyzer 초기화"""
        try:
            self.analyzer = EnhancedIntegratedAnalyzer()
            self.logger.info("Enhanced Analyzer 초기화 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"Enhanced Analyzer 초기화 중 오류: {e}")
            return False
    
    def run_system_diagnostics(self) -> Dict[str, Any]:
        """시스템 진단 실행"""
        self.logger.info("시스템 진단 시작")
        
        diagnostics = {
            'timestamp': datetime.now().isoformat(),
            'system_info': self.config_manager.get_system_info().__dict__,
            'config_summary': self.config_manager.get_config_summary(),
            'components_status': {}
        }
        
        # KIS API 상태
        if self.kis_api_manager:
            diagnostics['components_status']['kis_api'] = self.kis_api_manager.get_api_status()
        else:
            diagnostics['components_status']['kis_api'] = {'status': 'not_initialized'}
        
        # 백테스팅 엔진 상태
        diagnostics['components_status']['backtesting'] = {
            'status': 'initialized' if self.backtesting_engine else 'not_initialized'
        }
        
        # 포트폴리오 최적화 엔진 상태
        diagnostics['components_status']['portfolio_optimizer'] = {
            'status': 'initialized' if self.portfolio_optimizer else 'not_initialized'
        }
        
        # Enhanced Analyzer 상태
        diagnostics['components_status']['analyzer'] = {
            'status': 'initialized' if self.analyzer else 'not_initialized'
        }
        
        return diagnostics
    
    def run_backtest(self, symbols: List[str], strategy_function=None) -> Optional[Dict[str, Any]]:
        """백테스팅 실행"""
        if not self.backtesting_engine:
            self.logger.error("백테스팅 엔진이 초기화되지 않았습니다")
            return None
        
        if strategy_function is None:
            strategy_function = sample_value_strategy
        
        try:
            self.logger.info(f"백테스팅 실행: {len(symbols)}개 종목")
            result = self.backtesting_engine.run_backtest(strategy_function, symbols)
            
            # 결과를 딕셔너리로 변환
            backtest_result = {
                'total_return': result.total_return,
                'annualized_return': result.annualized_return,
                'volatility': result.volatility,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown': result.max_drawdown,
                'win_rate': result.win_rate,
                'total_trades': result.total_trades,
                'profit_factor': result.profit_factor,
                'equity_curve_length': len(result.equity_curve),
                'trades_count': len(result.trades)
            }
            
            self.logger.info(f"백테스팅 완료: 총 수익률 {result.total_return:.2%}")
            return backtest_result
            
        except Exception as e:
            self.logger.error(f"백테스팅 실행 중 오류: {e}")
            return None
    
    def run_portfolio_optimization(self, symbols: List[str]) -> Optional[Dict[str, Any]]:
        """포트폴리오 최적화 실행"""
        if not self.portfolio_optimizer:
            self.logger.error("포트폴리오 최적화 엔진이 초기화되지 않았습니다")
            return None
        
        try:
            self.logger.info(f"포트폴리오 최적화 실행: {len(symbols)}개 종목")
            results = self.portfolio_optimizer.compare_strategies(symbols)
            
            # 결과를 딕셔너리로 변환
            optimization_results = {}
            for strategy, result in results.items():
                optimization_results[strategy] = {
                    'expected_return': result.expected_return,
                    'expected_volatility': result.expected_volatility,
                    'sharpe_ratio': result.sharpe_ratio,
                    'diversification_ratio': result.diversification_ratio,
                    'concentration_risk': result.concentration_risk,
                    'convergence_achieved': result.convergence_achieved,
                    'top_positions': dict(list(result.optimal_weights.items())[:5])  # 상위 5개
                }
            
            self.logger.info("포트폴리오 최적화 완료")
            return optimization_results
            
        except Exception as e:
            self.logger.error(f"포트폴리오 최적화 실행 중 오류: {e}")
            return None
    
    def get_market_data(self, symbols: List[str]) -> Dict[str, Any]:
        """시장 데이터 조회"""
        if self.kis_api_manager:
            try:
                self.logger.info(f"KIS API를 통한 시장 데이터 조회: {len(symbols)}개 종목")
                return self.kis_api_manager.get_market_data(symbols)
            except Exception as e:
                self.logger.error(f"KIS API 데이터 조회 실패: {e}")
                return {}
        else:
            self.logger.info("KIS API가 초기화되지 않음. Mock 데이터 사용")
            return self._generate_mock_data(symbols)
    
    def _generate_mock_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Mock 데이터 생성"""
        mock_data = {}
        
        for symbol in symbols:
            mock_data[symbol] = {
                'price': {'current_price': 10000 + hash(symbol) % 100000},
                'financial': {'per': 10 + hash(symbol) % 20, 'pbr': 1 + hash(symbol) % 3},
                'timestamp': datetime.now().isoformat()
            }
        
        return mock_data
    
    def save_results(self, results: Dict[str, Any], filename: Optional[str] = None) -> str:
        """결과 저장"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"enhanced_system_results_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"결과 저장 완료: {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"결과 저장 실패: {e}")
            raise

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='Enhanced Integrated Analyzer 통합 실행')
    parser.add_argument('--config', type=str, help='설정 파일 경로')
    parser.add_argument('--symbols', nargs='+', default=['005930', '000270', '035420', '012330', '005380'],
                       help='분석할 종목 코드들')
    parser.add_argument('--mode', choices=['diagnostics', 'backtest', 'optimize', 'full'], default='diagnostics',
                       help='실행 모드')
    parser.add_argument('--output', type=str, help='결과 출력 파일명')
    parser.add_argument('--verbose', action='store_true', help='상세 로그 출력')
    
    args = parser.parse_args()
    
    # 로깅 설정
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Enhanced Integrated Analyzer 시스템 시작")
    
    try:
        # 시스템 실행자 초기화
        runner = EnhancedSystemRunner(args.config)
        
        # 시스템 진단
        diagnostics = runner.run_system_diagnostics()
        logger.info("시스템 진단 완료")
        
        results = {'diagnostics': diagnostics}
        
        if args.mode in ['backtest', 'full']:
            # 백테스팅 엔진 초기화
            runner.initialize_backtesting()
            
            # 백테스팅 실행
            backtest_result = runner.run_backtest(args.symbols)
            if backtest_result:
                results['backtest'] = backtest_result
        
        if args.mode in ['optimize', 'full']:
            # 포트폴리오 최적화 엔진 초기화
            runner.initialize_portfolio_optimizer()
            
            # 포트폴리오 최적화 실행
            optimization_result = runner.run_portfolio_optimization(args.symbols)
            if optimization_result:
                results['portfolio_optimization'] = optimization_result
        
        if args.mode == 'full':
            # KIS API 초기화 (선택적)
            runner.initialize_kis_api()
            
            # Enhanced Analyzer 초기화
            runner.initialize_analyzer()
            
            # 시장 데이터 조회
            market_data = runner.get_market_data(args.symbols)
            results['market_data'] = {
                'symbols_count': len(market_data),
                'data_available': bool(market_data)
            }
        
        # 결과 저장
        output_file = runner.save_results(results, args.output)
        
        # 결과 요약 출력
        print("\n" + "="*60)
        print("Enhanced Integrated Analyzer 실행 결과")
        print("="*60)
        
        print(f"시스템 정보:")
        sys_info = results['diagnostics']['system_info']
        print(f"  CPU 코어 수: {sys_info['cpu_count']}")
        print(f"  메모리: {sys_info['memory_gb']:.1f}GB")
        print(f"  사용 가능 메모리: {sys_info['available_memory_gb']:.1f}GB")
        
        print(f"\n컴포넌트 상태:")
        for component, status in results['diagnostics']['components_status'].items():
            if isinstance(status, dict):
                if 'status' in status:
                    print(f"  {component}: {status['status']}")
                else:
                    print(f"  {component}: 활성")
            else:
                print(f"  {component}: {status}")
        
        if 'backtest' in results:
            bt = results['backtest']
            print(f"\n백테스팅 결과:")
            print(f"  총 수익률: {bt['total_return']:.2%}")
            print(f"  연환산 수익률: {bt['annualized_return']:.2%}")
            print(f"  샤프 비율: {bt['sharpe_ratio']:.2f}")
            print(f"  최대 낙폭: {bt['max_drawdown']:.2%}")
        
        if 'portfolio_optimization' in results:
            po = results['portfolio_optimization']
            print(f"\n포트폴리오 최적화 결과:")
            for strategy, result in po.items():
                print(f"  {strategy}:")
                print(f"    예상 수익률: {result['expected_return']:.2%}")
                print(f"    예상 변동성: {result['expected_volatility']:.2%}")
                print(f"    샤프 비율: {result['sharpe_ratio']:.2f}")
        
        print(f"\n결과 파일: {output_file}")
        print("="*60)
        
    except Exception as e:
        logger.error(f"시스템 실행 중 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()










