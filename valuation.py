"""Valuation helper functions extracted from the analyzer."""

from __future__ import annotations

from typing import Dict, Optional


def calculate_metric_score(value: Optional[float], *, min_val: float, max_val: float, reverse: bool = False) -> Optional[float]:
    return score_linear(value, min_val=min_val, max_val=max_val, reverse=reverse)


def score_linear(value: Optional[float], *, min_val: float, max_val: float, reverse: bool = False) -> Optional[float]:
    if value is None:
        return None
    try:
        numerical = float(value)
    except Exception:
        return None
    low, high = (min_val, max_val) if not reverse else (max_val, min_val)
    if high == low:
        return None
    scaled = (numerical - low) / (high - low)
    scaled = max(0.0, min(1.0, scaled))
    return scaled * 100.0


def grade_from_score(score: float) -> str:
    if score >= 85:
        return 'A+'
    if score >= 75:
        return 'A'
    if score >= 70:
        return 'B+'
    if score >= 65:
        return 'B'
    if score >= 60:
        return 'C+'
    if score >= 55:
        return 'C'
    return 'D'


def evaluate_valuation_by_sector(
    symbol: str,
    *,
    per: float,
    pbr: float,
    roe: float,
    get_sector_characteristics_fn,
    get_sector_benchmarks_fn,
) -> Dict[str, any]:
    sector_info = get_sector_characteristics_fn(symbol)
    benchmarks = get_sector_benchmarks_fn(sector_info.get('name', '기타'))
    per_lo, per_hi = benchmarks['per_range']
    pbr_lo, pbr_hi = benchmarks['pbr_range']
    roe_lo, roe_hi = benchmarks['roe_range']

    per_score = calculate_metric_score(per, min_val=per_lo, max_val=per_hi, reverse=True)
    pbr_score = calculate_metric_score(pbr, min_val=pbr_lo, max_val=pbr_hi, reverse=True)
    roe_score = calculate_metric_score(roe, min_val=roe_lo, max_val=roe_hi, reverse=False)

    scores, weights = [], []
    if per_score is not None:
        scores.append(per_score)
        weights.append(0.35)
    if pbr_score is not None:
        scores.append(pbr_score)
        weights.append(0.25)
    if roe_score is not None:
        scores.append(roe_score)
        weights.append(0.40)

    if scores:
        weight_sum = sum(weights) or 1.0
        total = sum(score * (weight / weight_sum) for score, weight in zip(scores, weights))
    else:
        total = 50.0

    breakdown = {
        'PER': 50.0 if per_score is None else float(per_score),
        'PBR': 50.0 if pbr_score is None else float(pbr_score),
        'ROE': 50.0 if roe_score is None else float(roe_score),
    }

    return {
        'total_score': float(max(0.0, min(100.0, total))),
        'grade': grade_from_score(total),
        'breakdown': breakdown,
        'sector_info': sector_info,
    }





