"""Sector utility helpers extracted from the monolithic analyzer."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from utils.data_utils import DataValidator


def sanitize_leaders(leaders: List[str], kospi_data: Optional[pd.DataFrame]) -> List[str]:
    """Return only leader codes present in the KOSPI dataset."""

    if kospi_data is None or kospi_data.empty:
        return leaders

    if kospi_data.index.name == '단축코드':
        codes = set(kospi_data.index.astype(str))
    else:
        codes = set(kospi_data['단축코드'].astype(str))
    return [code for code in leaders if code in codes]


def collect_sector_peers(
    sector_name: str,
    kospi_data: Optional[pd.DataFrame],
    data_provider,
    max_count: int = 200,
) -> List[Tuple[Optional[float], Optional[float], Optional[float]]]:
    """Collect PER/PBR/ROE tuples for peers in the same sector."""

    peers: List[Tuple[Optional[float], Optional[float], Optional[float]]] = []
    if kospi_data is None or kospi_data.empty:
        return peers

    try:
        if '섹터' in kospi_data.columns:
            df = kospi_data[kospi_data['섹터'] == sector_name]
        else:
            df = kospi_data[kospi_data['업종명'] == sector_name]

        for _, row in df.head(max_count).iterrows():
            symbol = str(row.get('단축코드') or '').strip()
            if not symbol:
                continue

            price_data = data_provider.get_price_data(symbol)
            financial_data = data_provider.get_financial_data(symbol)

            per = DataValidator.safe_float_optional(price_data.get('per'))
            pbr = DataValidator.safe_float_optional(price_data.get('pbr'))
            roe = DataValidator.safe_float_optional(financial_data.get('roe'))

            if per is None and pbr is None and roe is None:
                continue

            peers.append((per, pbr, roe))
            if len(peers) >= max_count:
                break
    except Exception as exc:  # pragma: no cover
        logging.debug("섹터 동종군 수집 실패: %s (%s)", sector_name, exc)

    return peers


SECTOR_ALIASES = {
    'it': '기술업', '정보기술': '기술업', '소프트웨어': '기술업',
    '바이오': '바이오/제약', '제약': '바이오/제약', '생명과학': '바이오/제약',
    '자동차': '제조업', '전자': '제조업', '화학': '제조업',
    '은행': '금융업', '증권': '금융업', '보험': '금융업',
    '건설': '건설업', '부동산': '건설업',
    '유통': '소비재', '식품': '소비재', '의류': '소비재',
    '에너지': '에너지/화학', '석유': '에너지/화학',
    '통신': '통신업', '미디어': '통신업'
}


def get_sector_benchmarks(
    sector: str,
    kospi_data: Optional[pd.DataFrame],
    sector_stats: Optional[Dict[str, Any]] = None
) -> Dict[str, any]:
    """Return benchmark ranges and leaders for the given sector."""

    normalized_sector = SECTOR_ALIASES.get(str(sector).lower(), str(sector)) if sector else "기타"

    benchmarks = {
        '금융업': {
            'per_range': (5, 15), 'pbr_range': (0.5, 2.0), 'roe_range': (8, 20),
            'description': '안정적 수익성, 낮은 PBR',
            'leaders': ['105560', '055550', '086790']
        },
        '기술업': {
            'per_range': (15, 50), 'pbr_range': (1.5, 8.0), 'roe_range': (10, 30),
            'description': '높은 성장성, 높은 PER',
            'leaders': ['005930', '000660', '035420', '035720']
        },
        '제조업': {
            'per_range': (8, 25), 'pbr_range': (0.8, 3.0), 'roe_range': (8, 20),
            'description': '안정적 수익성, 적정 PER',
            'leaders': ['005380', '000270', '012330', '329180']
        },
        '바이오/제약': {
            'per_range': (20, 100), 'pbr_range': (2.0, 10.0), 'roe_range': (5, 25),
            'description': '높은 불확실성, 높은 PER',
            'leaders': ['207940', '068270', '006280']
        },
        '에너지/화학': {
            'per_range': (5, 20), 'pbr_range': (0.5, 2.5), 'roe_range': (5, 15),
            'description': '사이클 특성, 변동성 큰 수익',
            'leaders': ['034020', '010140']
        },
        '소비재': {
            'per_range': (10, 30), 'pbr_range': (1.0, 4.0), 'roe_range': (8, 18),
            'description': '안정적 수요, 적정 수익성',
            'leaders': []
        },
        '통신업': {
            'per_range': (8, 20), 'pbr_range': (0.8, 3.0), 'roe_range': (6, 15),
            'description': '현금흐름 안정',
            'leaders': ['017670']
        },
        '건설업': {
            'per_range': (5, 15), 'pbr_range': (0.5, 2.0), 'roe_range': (5, 12),
            'description': '사이클 민감, 보수적 밸류에이션',
            'leaders': ['000720', '051600']
        },
        '기타': {
            'per_range': (5, 40), 'pbr_range': (0.5, 6.0), 'roe_range': (5, 20),
            'description': '일반적 기준 (폴백)',
            'leaders': []
        },
    }

    entry = dict(benchmarks.get(normalized_sector, benchmarks['기타']))
    entry['leaders'] = sanitize_leaders(entry.get('leaders', []), kospi_data)
    entry['name'] = normalized_sector

    if sector_stats:
        per_percentiles = sector_stats.get('per_percentiles')
        pbr_percentiles = sector_stats.get('pbr_percentiles')
        roe_percentiles = sector_stats.get('roe_percentiles')

        def _override_range(original: Tuple[float, float], stats: Optional[Dict[str, float]], cushion: float = 0.2) -> Tuple[float, float]:
            if not stats:
                return original
            p25 = stats.get('p25')
            p50 = stats.get('p50')
            p75 = stats.get('p75')
            if p25 is None or p75 is None or p50 is None:
                return original
            low = max(0.0, min(p25, p50 * (1 - cushion)))
            high = max(p75, p50 * (1 + cushion))
            return (float(low), float(high))

        entry['per_range'] = _override_range(entry['per_range'], per_percentiles, cushion=0.15)
        entry['pbr_range'] = _override_range(entry['pbr_range'], pbr_percentiles, cushion=0.15)

        if roe_percentiles:
            p25 = roe_percentiles.get('p25')
            p50 = roe_percentiles.get('p50')
            p75 = roe_percentiles.get('p75')
            if p25 is not None and p75 is not None and p50 is not None:
                low = max(0.0, min(p25, p50 * 0.8))
                high = max(p75, p50 * 1.2)
                entry['roe_range'] = (float(low), float(high))

        entry['sample_size'] = sector_stats.get('sample_size')
        entry['avg_metrics'] = {
            'per': sector_stats.get('avg_pe_ratio'),
            'pbr': sector_stats.get('avg_pb_ratio'),
            'roe': sector_stats.get('avg_roe')
        }

    return entry
"""Sector-related utilities extracted from the analyzer."""


