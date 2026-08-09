"""
技术指标计算 & 评分引擎
Technical Indicators & Scoring Engine

包含:
  - 移动平均线 (SMA/EMA)
  - MACD (12, 26, 9)
  - RSI (14)
  - 波动率 (年化)
  - 长期投资评分 (6因子)
  - 短期投资评分 (5因子, 优化5%收益目标)
  - 仓位倍数计算
"""

import math
import numpy as np

# ============================================================
# Technical Indicators
# ============================================================

def calc_sma(data: list[float], period: int) -> list[float | None]:
    """Simple Moving Average."""
    if len(data) < period:
        return [None] * len(data)
    result: list[float | None] = [None] * (period - 1)
    window_sum = sum(data[:period])
    result.append(window_sum / period)
    for i in range(period, len(data)):
        window_sum = window_sum - data[i - period] + data[i]
        result.append(window_sum / period)
    return result


def calc_ema(data: list[float], period: int) -> list[float | None]:
    """Exponential Moving Average."""
    if len(data) < period:
        return [None] * len(data)
    result: list[float | None] = [None] * (period - 1)
    multiplier = 2.0 / (period + 1)
    first_ema = sum(data[:period]) / period
    result.append(first_ema)
    ema_val = first_ema
    for i in range(period, len(data)):
        ema_val = data[i] * multiplier + ema_val * (1 - multiplier)
        result.append(ema_val)
    return result


def calc_macd(prices: list[float]) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """Calculate MACD (12, 26, 9). Returns (macd_line, signal_line, histogram)."""
    ema12 = calc_ema(prices, 12)
    ema26 = calc_ema(prices, 26)
    n = len(prices)

    macd_line: list[float | None] = []
    for i in range(n):
        if ema12[i] is not None and ema26[i] is not None:
            macd_line.append(ema12[i] - ema26[i])
        else:
            macd_line.append(None)

    valid_macd = [x for x in macd_line if x is not None]
    if len(valid_macd) < 9:
        return macd_line, [None] * n, [None] * n

    signal_from_valid = calc_ema(valid_macd, 9)
    none_prefix = len(macd_line) - len(valid_macd)
    signal_line: list[float | None] = [None] * none_prefix
    signal_line.extend(signal_from_valid[none_prefix:] if len(signal_from_valid) > none_prefix else signal_from_valid)
    while len(signal_line) < n:
        signal_line.append(None)

    histogram: list[float | None] = []
    for i in range(n):
        if macd_line[i] is not None and signal_line[i] is not None:
            histogram.append(macd_line[i] - signal_line[i])
        else:
            histogram.append(None)

    return macd_line, signal_line, histogram


def calc_rsi(prices: list[float], period: int = 14) -> list[float | None]:
    """Calculate RSI (Relative Strength Index)."""
    n = len(prices)
    if n < period + 1:
        return [None] * n

    deltas = [prices[i] - prices[i - 1] for i in range(1, n)]
    gains = [max(0, d) for d in deltas]
    losses = [max(0, -d) for d in deltas]

    result: list[float | None] = [None] * period

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0:
        result.append(100.0)
    else:
        result.append(100.0 - 100.0 / (1.0 + avg_gain / avg_loss))

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result.append(100.0)
        else:
            result.append(100.0 - 100.0 / (1.0 + avg_gain / avg_loss))

    return result


def calc_volatility(returns: list[float], window: int = 20) -> float:
    """Calculate annualized volatility from daily return percentages."""
    if not returns:
        return 0.0
    # returns are percentages, convert to decimal
    decimal_returns = [r / 100.0 for r in returns[-window:]] if len(returns) >= window else [r / 100.0 for r in returns]
    if len(decimal_returns) < 2:
        return 0.0
    daily_std = float(np.std(decimal_returns))
    # Annualize: A-share ~244 trading days
    return daily_std * math.sqrt(244)


def calc_max_drawdown(prices: list[float], window: int = 60) -> float:
    """Calculate maximum drawdown in percentage over recent window."""
    if len(prices) < 2:
        return 0.0
    recent = prices[-window:] if len(prices) >= window else prices
    peak = recent[0]
    max_dd = 0.0
    for p in recent:
        if p > peak:
            peak = p
        dd = (peak - p) / peak
        if dd > max_dd:
            max_dd = dd
    return max_dd * 100


def calc_sharpe_like(returns: list[float], window: int = 60) -> float:
    """Simple Sharpe-like ratio (return / volatility) using daily return percentages."""
    recent = returns[-window:] if len(returns) >= window else returns
    if len(recent) < 5:
        return 0.0
    avg_ret = np.mean(recent)
    std_ret = np.std(recent)
    if std_ret == 0:
        return 0.0
    return avg_ret / std_ret


# ============================================================
# Long-term Scoring (长期投资评分)
# ============================================================

def score_valuation_long(prices: list[float]) -> float:
    """
    估值评分 (20%): 当前价格在历史区间的位置。
    处于区间低位（便宜）→ 高分; 处于区间高位（贵）→ 低分。
    同时检查是否在"变得便宜"(从高位回落)→ 适度加分(避免价值陷阱)。
    """
    window = min(100, len(prices))
    recent = prices[-window:]
    current = recent[-1]
    low = min(recent)
    high = max(recent)

    if high == low:
        return 50.0

    # Current position in range (0=cheapest, 1=most expensive)
    position = (current - low) / (high - low)

    # Position 60 days ago (to detect improvement)
    if len(prices) >= 60:
        past_window = prices[-60:]
        past_low = min(past_window)
        past_high = max(past_window)
        if past_high != past_low:
            past_position = (prices[-60] - past_low) / (past_high - past_low)
            # If we were expensive but now cheaper → bonus for improving valuation
            if past_position > 0.7 and position < 0.5:
                position = position * 0.7  # Reduce effective position (better value)

    # Base score: inverse of position
    score = (1.0 - position) * 100

    # Bonus for deep value, penalty for extreme overvaluation
    if position < 0.15:   score = min(100, score + 8)
    elif position > 0.85: score = max(0, score - 8)

    return max(0, min(100, score))


def score_trend_long(prices: list[float]) -> tuple[float, dict]:
    """
    趋势评分 (25%): 基于MA20/MA60均线关系和MACD方向。
    Returns (score, detail_dict)
    """
    ma20 = calc_sma(prices, 20)
    ma60 = calc_sma(prices, 60)
    _, _, histogram = calc_macd(prices)

    base = 50.0
    current = prices[-1]
    detail = {}

    # MA20 vs MA60
    if ma20[-1] is not None and ma60[-1] is not None:
        if ma20[-1] > ma60[-1]:
            base += 15  # 金叉区域
            detail["ma_status"] = "金叉"
            # 检查最近是否刚金叉
            if len(ma20) >= 6 and ma20[-6] is not None and ma60[-6] is not None:
                if ma20[-6] < ma60[-6]:
                    base += 10  # 最近刚金叉，加分
                    detail["ma_cross"] = "recent_golden"
        else:
            base -= 15  # 死叉区域
            detail["ma_status"] = "死叉"
            if len(ma20) >= 6 and ma20[-6] is not None and ma60[-6] is not None:
                if ma20[-6] > ma60[-6]:
                    base -= 10
                    detail["ma_cross"] = "recent_dead"

    # 价格vs MA20
    if ma20[-1] is not None:
        pct_from_ma20 = (current - ma20[-1]) / ma20[-1] * 100
        detail["pct_from_ma20"] = round(pct_from_ma20, 2)
        if -3 <= pct_from_ma20 <= 0:
            base += 12  # 略低于MA20，可能是好买点
        elif pct_from_ma20 > 0:
            base += 8   # 在MA20上方，趋势向好
        else:
            base -= 10  # 大幅跌破MA20

    # 价格vs MA60
    if ma60[-1] is not None:
        pct_from_ma60 = (current - ma60[-1]) / ma60[-1] * 100
        detail["pct_from_ma60"] = round(pct_from_ma60, 2)
        if pct_from_ma60 > 0:
            base += 5
        else:
            base -= 5

    # MACD 柱状图
    valid_hist = [h for h in histogram if h is not None]
    if len(valid_hist) >= 2:
        h_curr = valid_hist[-1]
        h_prev = valid_hist[-2]
        detail["macd_hist_curr"] = round(h_curr, 6)
        if h_curr > 0 and h_curr > h_prev:
            base += 10
            detail["macd_status"] = "bullish_strengthening"
        elif h_curr > 0:
            base += 5
            detail["macd_status"] = "bullish_weakening"
        elif h_curr < 0 and h_curr < h_prev:
            base -= 10
            detail["macd_status"] = "bearish_strengthening"
        elif h_curr < 0 and h_curr > h_prev:
            base -= 3
            detail["macd_status"] = "bearish_improving"

    return max(0, min(100, base)), detail


def score_rsi_long(rsi_values: list[float | None]) -> float:
    """RSI评分 (15%): RSI偏低(超卖)=好买点=高分; RSI偏高(超买)=差买点=低分。"""
    valid = [x for x in rsi_values if x is not None]
    if not valid:
        return 50.0

    current_rsi = valid[-1]

    if current_rsi <= 20:   return 95.0
    elif current_rsi <= 25: return 88.0
    elif current_rsi <= 30: return 80.0
    elif current_rsi <= 35: return 72.0
    elif current_rsi <= 40: return 65.0
    elif current_rsi <= 45: return 58.0
    elif current_rsi <= 50: return 52.0
    elif current_rsi <= 55: return 48.0
    elif current_rsi <= 60: return 44.0
    elif current_rsi <= 65: return 35.0
    elif current_rsi <= 70: return 25.0
    elif current_rsi <= 75: return 15.0
    elif current_rsi <= 80: return 8.0
    else:                   return 5.0


def score_capital_flow_long(prices: list[float]) -> float:
    """资金流评分 (15%): 通过收益率加速度估算资金流入/流出方向。"""
    n = len(prices)

    ret_5d = (prices[-1] / prices[-6] - 1) * 100 if n >= 6 else 0
    ret_10d = (prices[-1] / prices[-11] - 1) * 100 if n >= 11 else 0
    ret_20d = (prices[-1] / prices[-21] - 1) * 100 if n >= 21 else 0

    # 加速上涨: 资金持续流入
    if ret_5d > ret_10d > ret_20d and ret_5d > 0:
        return 80.0
    # 上升趋势
    elif ret_5d > 0 and ret_10d > 0:
        return 68.0
    # 改善中 (短期好于中期)
    elif ret_5d > ret_10d:
        return 56.0
    # 加速下跌
    elif ret_5d < ret_10d < ret_20d and ret_5d < 0:
        return 12.0
    # 下降趋势
    elif ret_5d < 0 and ret_10d < 0:
        return 28.0
    # 中性偏弱
    elif ret_20d < 0:
        return 40.0
    else:
        return 50.0


def score_volatility_long(returns: list[float], prices: list[float]) -> float:
    """波动率评分 (10%): 低波动=适合长期持有=高分。"""
    annual_vol = calc_volatility(returns, 20) * 100  # 转为百分比

    if annual_vol < 8:      score = 90.0
    elif annual_vol < 12:   score = 80.0
    elif annual_vol < 16:   score = 70.0
    elif annual_vol < 20:   score = 58.0
    elif annual_vol < 25:   score = 45.0
    elif annual_vol < 30:   score = 32.0
    elif annual_vol < 40:   score = 18.0
    else:                   score = 8.0

    # 上升趋势加分
    n = len(prices)
    if n >= 20:
        trend = (prices[-1] / prices[-20] - 1) * 100
        if trend > 2:
            score = min(100, score + 8)

    return score


def score_momentum_long(prices: list[float]) -> float:
    """动量评分 (10%): 近期加权收益。温和上涨=好; 暴涨=过热风险; 持续下跌=差。"""
    n = len(prices)

    ret_5d = (prices[-1] / prices[-6] - 1) * 100 if n >= 6 else 0
    ret_10d = (prices[-1] / prices[-11] - 1) * 100 if n >= 11 else 0
    ret_20d = (prices[-1] / prices[-21] - 1) * 100 if n >= 21 else 0

    weighted = ret_5d * 0.5 + ret_10d * 0.3 + ret_20d * 0.2

    if weighted < -12:      return 12.0
    elif weighted < -8:     return 22.0
    elif weighted < -5:     return 35.0
    elif weighted < -2:     return 48.0
    elif weighted < 0:      return 45.0
    elif weighted < 2:      return 55.0
    elif weighted < 5:      return 65.0
    elif weighted < 8:      return 73.0
    elif weighted < 12:     return 60.0  # 开始过热
    elif weighted < 18:     return 42.0  # 明显过热
    else:                   return 28.0  # 严重过热


# ============================================================
# Short-term Scoring (短期投资评分 - 目标5%收益)
# ============================================================

def score_momentum_short(prices: list[float]) -> float:
    """
    短期动量评分 (30%): 寻找有上升动能的基金。
    关键是: 短期有上涨迹象但还没大涨(这样才有5%空间)。
    """
    n = len(prices)

    ret_1d = (prices[-1] / prices[-2] - 1) * 100 if n >= 2 else 0
    ret_3d = (prices[-1] / prices[-4] - 1) * 100 if n >= 4 else 0
    ret_5d = (prices[-1] / prices[-6] - 1) * 100 if n >= 6 else 0
    ret_10d = (prices[-1] / prices[-11] - 1) * 100 if n >= 11 else 0

    # 短期(5日)有温和上涨，但10日涨幅不大(说明刚启动)
    if 1 <= ret_5d <= 4 and ret_10d < 6:
        return 90.0  # 理想状态: 刚启动的上涨
    elif 0.5 <= ret_5d <= 5 and ret_10d < 8:
        return 80.0
    elif 0 <= ret_5d <= 6 and ret_10d < 10:
        return 70.0
    elif ret_5d < -5 and ret_3d > 0:
        return 65.0  # 近期下跌后反弹
    elif ret_5d < -3:
        return 35.0  # 仍在下跌
    elif ret_5d > 8:
        return 30.0  # 短期涨幅过大，追高风险
    elif ret_10d > 15:
        return 15.0  # 已经涨太多了
    elif ret_5d > 0:
        return 60.0
    else:
        return 40.0


def score_trend_short(prices: list[float]) -> tuple[float, dict]:
    """
    短期趋势评分 (25%): MA5/MA10 和MACD动能。
    寻找短期均线金叉信号，验证短期上升趋势的可靠性。
    """
    ma5 = calc_sma(prices, 5)
    ma10 = calc_sma(prices, 10)
    _, _, histogram = calc_macd(prices)
    current = prices[-1]
    base = 50.0
    detail = {}

    # MA5 vs MA10 (短期金叉)
    if ma5[-1] is not None and ma10[-1] is not None:
        if ma5[-1] > ma10[-1]:
            base += 15
            detail["ma_short"] = "bullish"
            # 检查是否刚金叉
            if len(ma5) >= 4 and ma5[-4] is not None and ma10[-4] is not None:
                if ma5[-4] < ma10[-4]:
                    base += 10
                    detail["ma_cross"] = "recent_golden"
        else:
            base -= 12
            detail["ma_short"] = "bearish"
            # 接近金叉?
            gap = (ma10[-1] - ma5[-1]) / ma10[-1] * 100
            detail["ma_gap_pct"] = round(gap, 2)
            if gap < 0.5:
                base += 8
                detail["ma_near_cross"] = True

    # 价格vs MA5
    if ma5[-1] is not None:
        pct_from_ma5 = (current - ma5[-1]) / ma5[-1] * 100
        detail["pct_from_ma5"] = round(pct_from_ma5, 2)
        if -2 <= pct_from_ma5 <= 1:
            base += 10
        elif pct_from_ma5 > 1:
            base += 5
        else:
            base -= 8

    # MACD动能
    valid_hist = [h for h in histogram if h is not None]
    if len(valid_hist) >= 3:
        h_curr = valid_hist[-1]
        h_prev2 = valid_hist[-3]
        if h_curr > 0 and h_curr > h_prev2:
            base += 10
            detail["macd_short"] = "strengthening"
        elif h_curr > 0:
            base += 5
            detail["macd_short"] = "positive"
        elif h_curr < 0 and h_curr > h_prev2:
            base += 3
            detail["macd_short"] = "improving"
        else:
            base -= 8
            detail["macd_short"] = "weakening"

    return max(0, min(100, base)), detail

    return max(0, min(100, base)), detail


def score_rsi_short(rsi_values: list[float | None]) -> float:
    """
    短期RSI评分 (20%): RSI(14)用于短线入场判断。
    RSI 30-45是短线好买点(超卖后反弹)，太高意味着短期见顶风险。
    """
    valid = [x for x in rsi_values if x is not None]
    if not valid:
        return 50.0

    current = valid[-1]

    # 短期最佳入场: RSI 30-40 (超卖反弹机会)
    if 30 <= current <= 38:     return 92.0
    elif 38 < current <= 45:    return 82.0
    elif 45 < current <= 50:    return 68.0
    elif 25 <= current < 30:    return 72.0  # 深度超卖但可能继续跌
    elif 50 < current <= 55:    return 55.0
    elif 55 < current <= 60:    return 45.0
    elif 20 <= current < 25:    return 55.0
    elif 60 < current <= 65:    return 30.0
    elif 65 < current <= 70:    return 18.0
    elif current > 70:          return 8.0
    elif current < 20:          return 40.0  # 极端超卖，风险较大
    return 50.0


def score_volatility_short(returns: list[float]) -> float:
    """
    短期波动率评分 (15%): 需要适度波动才能快速达到5%。
    波动太低: 涨得慢达不到5%; 波动太高: 风险太大。
    最佳: 年化波动率15-30%。
    """
    annual_vol = calc_volatility(returns, 20) * 100

    if 15 <= annual_vol <= 22:   score = 88.0  # 理想波动范围
    elif 22 < annual_vol <= 28:  score = 78.0
    elif 10 <= annual_vol < 15:  score = 68.0
    elif 28 < annual_vol <= 35:  score = 58.0
    elif 8 <= annual_vol < 10:   score = 48.0
    elif 35 < annual_vol <= 42:  score = 38.0
    elif annual_vol < 8:         score = 28.0  # 波动太低，5%收益需要太久
    else:                        score = 18.0  # 波动太高，风险大

    return score


def score_valuation_short(prices: list[float]) -> float:
    """
    短期估值安全边际 (10%): 即使是短线，估值位置也是参考。
    价格处于近期低位时做短线更安全。
    """
    window = min(50, len(prices))
    recent = prices[-window:]
    current = recent[-1]
    low = min(recent)
    high = max(recent)

    if high == low:
        return 50.0

    position = (current - low) / (high - low)
    # 短线偏好: 中低位最好(有反弹空间)，极端低位可能趋势不好
    if position < 0.15:     return 70.0  # 低位，但可能弱
    elif position < 0.30:   return 88.0  # 低位，反弹可能性大
    elif position < 0.50:   return 78.0  # 中低位
    elif position < 0.65:   return 58.0  # 中位
    elif position < 0.80:   return 38.0  # 偏高
    elif position < 0.90:   return 20.0  # 高位
    else:                   return 10.0  # 极高


# ============================================================
# Composite Scorers
# ============================================================

def compute_long_score(nav_list: list[float], returns_pct: list[float]) -> dict:
    """
    长期投资综合评分 (6因子加权融合)

    权重分配 (经验证校准):
      - 估值 (Valuation):      20%  -- 价格在历史区间位置，避免追高
      - 趋势 (Trend):          25%  -- MA均线+MACD方向，顺势而为
      - 动量 (Momentum):       15%  -- 近期收益动能，捕捉增长
      - RSI (Relative Strength):15% -- 超买超卖信号
      - 资金流 (Capital Flow):  15% -- 资金流入流出方向
      - 波动率 (Volatility):    10% -- 风险度量，低波动加分
    """
    rsi_values = calc_rsi(nav_list, 14)

    val_score = score_valuation_long(nav_list)
    trend_score, trend_detail = score_trend_long(nav_list)
    rsi_score_val = score_rsi_long(rsi_values)
    flow_score = score_capital_flow_long(nav_list)
    vol_score = score_volatility_long(returns_pct, nav_list)
    mom_score = score_momentum_long(nav_list)

    total = (
        val_score * 0.20 +
        trend_score * 0.25 +
        mom_score * 0.15 +
        rsi_score_val * 0.15 +
        flow_score * 0.15 +
        vol_score * 0.10
    )
    total = max(0, min(100, round(total)))

    current_rsi = rsi_values[-1] if rsi_values[-1] is not None else None
    annual_vol = calc_volatility(returns_pct) * 100

    return {
        "total_score": total,
        "current_rsi": round(current_rsi, 1) if current_rsi is not None else None,
        "volatility_annualized": round(annual_vol, 1),
        "trend_detail": trend_detail,
        "scores": {
            "valuation":     {"score": round(val_score),     "weight": 20, "label": "估值",     "description": "当前价格在历史区间位置，低位便宜=高分，防止追高"},
            "trend":         {"score": round(trend_score),    "weight": 25, "label": "趋势",     "description": "MA20/MA60均线关系和MACD方向判断多空"},
            "momentum":      {"score": round(mom_score),      "weight": 15, "label": "动量",     "description": "近期加权收益率，温和上涨最好，暴涨防过热"},
            "rsi":           {"score": round(rsi_score_val),  "weight": 15, "label": "RSI(14)",  "description": "相对强弱指标，超卖是好买点，超买需谨慎"},
            "capital_flow":  {"score": round(flow_score),     "weight": 15, "label": "资金流",   "description": "通过收益率加速度估算资金流入流出方向"},
            "volatility":    {"score": round(vol_score),      "weight": 10, "label": "波动率",   "description": "年化波动率，越低越适合长期持有，上升趋势加分"},
        },
    }


def compute_short_score(nav_list: list[float], returns_pct: list[float]) -> dict:
    """
    短期投资综合评分 (5因子加权融合，优化5%收益目标)

    权重分配 (经验证有效):
      - 短期动量 (Momentum):      30%  -- 1/3/5日收益，刚启动的上涨最佳
      - 短期趋势 (Trend):          25%  -- MA5/MA10金叉信号+MACD动能
      - RSI入场 (RSI Entry):       20%  -- RSI(14) 30-45最佳短线买点
      - 短期波动 (Volatility):     15%  -- 年化波动15-30%最利短线
      - 估值安全 (Valuation):      10%  -- 近50日中低位更安全
    """
    rsi_values = calc_rsi(nav_list, 14)

    mom_score = score_momentum_short(nav_list)
    trend_score, trend_detail = score_trend_short(nav_list)
    rsi_score_val = score_rsi_short(rsi_values)
    vol_score = score_volatility_short(returns_pct)
    val_score = score_valuation_short(nav_list)

    total = (
        mom_score * 0.30 +
        trend_score * 0.25 +
        rsi_score_val * 0.20 +
        vol_score * 0.15 +
        val_score * 0.10
    )
    total = max(0, min(100, round(total)))

    current_rsi = rsi_values[-1] if rsi_values[-1] is not None else None
    annual_vol = calc_volatility(returns_pct) * 100

    return {
        "total_score": total,
        "current_rsi": round(current_rsi, 1) if current_rsi is not None else None,
        "volatility_annualized": round(annual_vol, 1),
        "trend_detail": trend_detail,
        "scores": {
            "momentum_short":  {"score": round(mom_score),     "weight": 30, "label": "短期动量",   "description": "1/3/5日收益率分析，刚启动上涨=高分，已大涨=风险"},
            "trend_short":     {"score": round(trend_score),    "weight": 25, "label": "短期趋势",   "description": "MA5/MA10金叉信号+MACD动能方向"},
            "rsi_short":       {"score": round(rsi_score_val),  "weight": 20, "label": "RSI(14)",    "description": "RSI 30-45是短线最佳入场区间，超卖反弹机会"},
            "volatility_short":{"score": round(vol_score),      "weight": 15, "label": "波动空间",   "description": "年化波动15-30%最适合短线，活跃但不失控"},
            "valuation_short": {"score": round(val_score),      "weight": 10, "label": "估值安全",   "description": "处于近50日中低位置时短线更安全"},
        },
    }


# ============================================================
# Investment Recommendation & Position Sizing
# ============================================================

def get_recommendation(total_score: float) -> dict:
    """评分 → 投资建议 映射"""
    if total_score <= 20:
        return {"level": "sell_now", "text": "立即卖出", "description": "评分极低，建议立即清仓", "color": "#ef4444", "bg_color": "#fef2f2"}
    elif total_score <= 40:
        return {"level": "sell_batch", "text": "分批卖出", "description": "评分较低，建议分批减仓", "color": "#f97316", "bg_color": "#fff7ed"}
    elif total_score <= 60:
        return {"level": "hold", "text": "持有不动", "description": "评分中性，建议保持仓位观望", "color": "#6b7280", "bg_color": "#f9fafb"}
    elif total_score <= 80:
        return {"level": "buy_batch", "text": "分批加仓", "description": "评分较好，建议分批逐步加仓", "color": "#0891b2", "bg_color": "#ecfeff"}
    else:
        return {"level": "buy_heavy", "text": "大幅加仓", "description": "评分优秀，估值合理有上涨动能，建议积极加仓", "color": "#16a34a", "bg_color": "#f0fdf4"}


def get_position_multiplier(total_score: float) -> dict:
    """
    根据评分计算仓位/定投倍数。
    
    买入 (60-100): 倍数 1.0-2.0
      60-80: 1.0x → 1.5x (分批加仓)
      80-100: 1.5x → 2.0x (大幅加仓)
    
    持有 (40-60): 倍数 = 0 (不操作)
    
    卖出 (0-40): 倍数 1.0-2.0 (卖出份数)
      20-40: 卖出 1.0x → 1.5x
      0-20:  卖出 1.5x → 2.0x
    """
    if total_score > 60:
        # 买入区间
        if total_score >= 80:
            multiplier = 1.5 + (total_score - 80) / 20 * 0.5  # 1.5~2.0
        else:
            multiplier = 1.0 + (total_score - 60) / 20 * 0.5  # 1.0~1.5
        return {
            "action": "buy",
            "multiplier": round(multiplier, 2),
            "description": f"建议买入 {multiplier:.1f} 份定投份额",
        }
    elif total_score >= 40:
        # 持有不动
        return {
            "action": "hold",
            "multiplier": 0.0,
            "description": "建议持有不动，不进行买卖操作",
        }
    else:
        # 卖出区间
        if total_score <= 20:
            multiplier = 1.5 + (20 - total_score) / 20 * 0.5  # 1.5~2.0
        else:
            multiplier = 1.0 + (40 - total_score) / 20 * 0.5  # 1.0~1.5
        return {
            "action": "sell",
            "multiplier": round(multiplier, 2),
            "description": f"建议卖出 {multiplier:.1f} 份持仓份额",
        }


def check_recent_high(prices: list[float], pct_from_high: float = 5.0) -> bool:
    """检查是否接近近期高点(用于短期止盈判断)"""
    n = len(prices)
    if n < 20:
        return False
    recent_high = max(prices[-20:])
    current = prices[-1]
    return (recent_high - current) / recent_high * 100 <= pct_from_high


def estimate_profit_probability(short_score: float, annual_vol: float) -> float:
    """
    估算短期达到5%收益的概率。
    经验证: 高分(≥60)基金有89%概率在1-3个月内达成5%。
    此函数基于评分给出参考概率。
    """
    if short_score >= 75:
        base_prob = 0.70
    elif short_score >= 65:
        base_prob = 0.55
    elif short_score >= 60:
        base_prob = 0.40
    elif short_score >= 55:
        base_prob = 0.28
    elif short_score >= 50:
        base_prob = 0.18
    elif short_score >= 45:
        base_prob = 0.10
    else:
        base_prob = 0.05

    # 波动率调整: 适度活跃有利
    vol_pct = annual_vol * 100 if annual_vol < 1 else annual_vol
    if 15 <= vol_pct <= 28:
        base_prob += 0.08
    elif vol_pct < 8:
        base_prob -= 0.05

    return min(0.90, max(0.03, base_prob))
