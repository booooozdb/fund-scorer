"""
基金投资评分系统 v2.0 - Web API
"""

import asyncio
import re
import time
from datetime import datetime, time as dt_time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from scoring import (
    calc_sma, calc_ema, calc_macd, calc_rsi, calc_volatility,
    compute_long_score, compute_short_score,
    get_recommendation, get_position_multiplier, estimate_profit_probability,
)
from fund_lists import (
    BROAD_BASED_FUNDS, STRATEGY_FUNDS, SECTOR_FUNDS,
    get_funds_by_category, all_funds_in_category, get_recommend_code,
)

app = FastAPI(title="基金投资评分系统", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = {"realtime": 60, "history": 3600, "category": 300}

def cache_get(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry is None: return None
    ts, value = entry
    ttl = next((v for k, v in CACHE_TTL.items() if k in key), 3600)
    if time.time() - ts > ttl:
        del _cache[key]; return None
    return value

def cache_set(key: str, value: Any) -> None:
    _cache[key] = (time.time(), value)

_client: httpx.AsyncClient | None = None

async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None: _client = httpx.AsyncClient(timeout=httpx.Timeout(15.0))
    return _client

@app.on_event("shutdown")
async def shutdown():
    global _client
    if _client: await _client.aclose(); _client = None

def is_trading_time() -> tuple[bool, str]:
    now = datetime.now()
    ct = now.time()
    if now.weekday() >= 5: return False, "closed_weekend"
    if dt_time(9,30) <= ct <= dt_time(11,30): return True, "trading_morning"
    if dt_time(13,0) <= ct <= dt_time(15,0): return True, "trading_afternoon"
    if ct < dt_time(9,30): return False, "pre_market"
    if ct < dt_time(13,0): return False, "lunch_break"
    return False, "after_market"

async def fetch_realtime_estimate(code: str) -> dict:
    cache_key = f"realtime:{code}"
    cached = cache_get(cache_key)
    if cached: return cached
    url = f"https://hq.sinajs.cn/list=f_{code}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": "https://finance.sina.com.cn/"}
    client = await get_client()
    try:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        text = resp.text
        match = re.search(r'"([^"]*)"', text)
        if not match: raise ValueError("无法解析新浪基金数据")
        parts = match.group(1).split(",")
        if len(parts) < 5 or not parts[0]: raise ValueError(f"未找到基金代码({code})")
        fund_name = parts[0].strip()
        current_nav = float(parts[1]) if parts[1] else 0.0
        prev_nav = float(parts[3]) if len(parts) > 3 and parts[3] else 0.0
        nav_date = parts[4].strip() if len(parts) > 4 else ""
        change_pct = round((current_nav - prev_nav) / prev_nav * 100, 2) if prev_nav > 0 else 0.0
        result = {"fund_code": code, "fund_name": fund_name, "current_nav": current_nav,
                  "estimated_nav": current_nav, "estimated_change_pct": change_pct,
                  "nav_date": nav_date, "estimate_time": nav_date, "source": "sina"}
        cache_set(cache_key, result)
        return result
    except httpx.TimeoutException: raise HTTPException(504, "数据源连接超时")
    except ValueError as e: raise HTTPException(400, str(e))
    except httpx.HTTPStatusError: raise HTTPException(400, f"未找到基金代码({code})")

async def fetch_historical_nav(code: str, target_records: int = 120) -> list[dict]:
    """Fetch historical NAV with proper pagination. API caps at ~20 records/page."""
    cache_key = f"history:{code}"
    cached = cache_get(cache_key)
    if cached: return cached
    url = "http://api.fund.eastmoney.com/f10/lsjz"
    headers = {"Referer": "http://fund.eastmoney.com/", "User-Agent": "Mozilla/5.0"}
    client = await get_client()
    try:
        all_records = []
        pages_needed = max(1, target_records // 20 + 1)
        for page in range(1, pages_needed + 1):
            resp = await client.get(url, params={"fundCode": code, "pageIndex": page, "pageSize": 100}, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if data.get("ErrCode") != 0:
                break
            records = data.get("Data", {}).get("LSJZList", [])
            if not records:
                break
            for r in records:
                try:
                    all_records.append({
                        "date": r["FSRQ"], "nav": float(r["DWJZ"]),
                        "cumulative_nav": float(r.get("LJJZ", r["DWJZ"])),
                        "daily_return": float(r.get("JZZZL", "0") or "0"),
                    })
                except (KeyError, ValueError):
                    continue
            if len(records) < 20:  # last page
                break
        if not all_records: raise ValueError("该基金无历史数据")
        all_records.sort(key=lambda x: x["date"])
        cache_set(cache_key, all_records)
        return all_records
    except httpx.TimeoutException: raise HTTPException(504, "数据源连接超时")
    except ValueError as e: raise HTTPException(400, str(e))


# ============================================================
# Core Scoring Endpoint
# ============================================================

async def build_score_response(fund_code: str, invest_type: str) -> dict:
    """Build complete scoring response for a fund."""
    if not re.match(r'^\d{6}$', fund_code):
        raise HTTPException(400, "基金代码格式错误，请输入6位数字代码")

    try:
        realtime, history = await asyncio.gather(
            fetch_realtime_estimate(fund_code),
            fetch_historical_nav(fund_code),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"数据获取失败: {str(e)}")

    nav_list = [h["nav"] for h in history]
    returns_pct = [h["daily_return"] for h in history]

    if len(nav_list) < 20:
        raise HTTPException(400, f"历史数据不足（仅{len(nav_list)}个交易日），无法计算有效评分")

    # Compute scores based on investment type
    if invest_type == "short":
        result = compute_short_score(nav_list, returns_pct)
    else:
        result = compute_long_score(nav_list, returns_pct)

    total = result["total_score"]
    recommendation = get_recommendation(total)
    position = get_position_multiplier(total)

    # Calculate chart data
    ma20 = calc_sma(nav_list, 20)
    ma60 = calc_sma(nav_list, 60)
    macd_line, signal_line, histogram = calc_macd(nav_list)
    rsi_values = calc_rsi(nav_list, 14)

    # Market status
    is_trading, market_status = is_trading_time()
    status_labels = {
        "trading_morning": "交易中", "trading_afternoon": "交易中",
        "pre_market": "盘前", "lunch_break": "午间休市",
        "after_market": "已收盘", "closed_weekend": "休市",
    }

    data_warning = None
    if len(nav_list) < 60:
        data_warning = f"历史数据仅{len(nav_list)}个交易日，MA60和部分长期指标仅供参考"

    # Short-term specific: estimated profit probability
    short_info = {}
    if invest_type == "short":
        annual_vol = result.get("volatility_annualized", 0) / 100
        prob = estimate_profit_probability(total, annual_vol)
        short_info = {
            "profit_probability": round(prob * 100),
            "target_profit": "5%",
            "timeframe": "1~2周内",
        }

    response = {
        "fund_code": fund_code,
        "fund_name": realtime["fund_name"],
        "current_nav": realtime["current_nav"],
        "estimated_nav": realtime["estimated_nav"],
        "estimated_change_pct": realtime["estimated_change_pct"],
        "nav_date": realtime["nav_date"],
        "estimate_time": realtime["estimate_time"],
        "market_status": market_status,
        "market_status_label": status_labels.get(market_status, "未知"),
        "invest_type": invest_type,
        "data_warning": data_warning,
        "data_days": len(nav_list),
        "total_score": total,
        "recommendation": recommendation,
        "position": position,
        "short_info": short_info if short_info else None,
        "scores": result["scores"],
        "indicators": {
            "current_rsi": result.get("current_rsi"),
            "volatility_annualized": result.get("volatility_annualized"),
        },
        "chart_data": {
            "dates": [h["date"] for h in history],
            "prices": nav_list,
            "ma20": [round(x, 4) if x is not None else None for x in ma20],
            "ma60": [round(x, 4) if x is not None else None for x in ma60],
            "macd_line": [round(x, 6) if x is not None else None for x in macd_line],
            "signal_line": [round(x, 6) if x is not None else None for x in signal_line],
            "histogram": [round(x, 6) if x is not None else None for x in histogram],
            "rsi_values": [round(x, 1) if x is not None else None for x in rsi_values],
        },
    }
    return response


@app.get("/api/score/{fund_code}")
async def get_fund_score(fund_code: str, type: str = Query("long", pattern="^(long|short)$")):
    """Get comprehensive fund scoring. type=long for long-term, type=short for short-term (5% target)."""
    return await build_score_response(fund_code, type)


# ============================================================
# Category Batch Scoring Endpoint
# ============================================================

@app.get("/api/category/{category_name}")
async def get_category_scores(category_name: str, type: str = Query("long", pattern="^(long|short)$")):
    """Batch score all funds in a predefined category. Returns sorted by score descending."""
    funds = all_funds_in_category(category_name)
    if not funds:
        categories = ["宽基", "策略", "行业"]
        raise HTTPException(400, f"不支持该分类: '{category_name}'。支持: {', '.join(categories)}")

    cache_key = f"category:{category_name}:{type}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    async def score_one(fund: dict) -> dict | None:
        try:
            code = fund["code"]
            realtime, history = await asyncio.gather(
                fetch_realtime_estimate(code),
                fetch_historical_nav(code),
            )
            nav_list = [h["nav"] for h in history]
            returns_pct = [h["daily_return"] for h in history]
            if len(nav_list) < 20:
                return None

            if type == "short":
                result = compute_short_score(nav_list, returns_pct)
            else:
                result = compute_long_score(nav_list, returns_pct)

            total = result["total_score"]
            rec = get_recommendation(total)
            pos = get_position_multiplier(total)

            recommend_code = fund.get("recommend", fund["code"])

            return {
                "sector": fund["sector"],
                "code": code,
                "name": fund["name"],
                "desc": fund.get("desc", ""),
                "recommend": recommend_code,
                "total_score": total,
                "recommendation_text": rec["text"],
                "recommendation_color": rec["color"],
                "position_action": pos["action"],
                "position_multiplier": pos["multiplier"],
                "indicators": {
                    "rsi": result.get("current_rsi"),
                    "volatility": result.get("volatility_annualized"),
                },
            }
        except Exception:
            return None

    # Score all funds in parallel with concurrency limit
    sem = asyncio.Semaphore(5)

    async def limited_score(fund):
        async with sem:
            return await score_one(fund)

    results = await asyncio.gather(*[limited_score(f) for f in funds])
    valid_results = [r for r in results if r is not None]

    # Sort by score descending
    valid_results.sort(key=lambda x: x["total_score"], reverse=True)

    is_trading, market_status = is_trading_time()
    response = {
        "category": category_name,
        "invest_type": type,
        "market_status": market_status,
        "total_funds": len(funds),
        "scored_funds": len(valid_results),
        "results": valid_results,
    }
    cache_set(cache_key, response)
    return response


# ============================================================
# Quick Check Endpoint (for validation)
# ============================================================

@app.get("/api/quick-check/{fund_code}")
async def quick_check(fund_code: str):
    """Lightweight endpoint: returns just fund name + scores for both long and short."""
    if not re.match(r'^\d{6}$', fund_code):
        raise HTTPException(400, "基金代码格式错误")

    try:
        realtime, history = await asyncio.gather(
            fetch_realtime_estimate(fund_code),
            fetch_historical_nav(fund_code),
        )
    except Exception as e:
        return {"fund_code": fund_code, "error": str(e)}

    nav_list = [h["nav"] for h in history]
    returns_pct = [h["daily_return"] for h in history]

    if len(nav_list) < 20:
        return {"fund_code": fund_code, "error": "数据不足"}

    long_result = compute_long_score(nav_list, returns_pct)
    short_result = compute_short_score(nav_list, returns_pct)

    return {
        "fund_code": fund_code,
        "fund_name": realtime["fund_name"],
        "current_nav": realtime["current_nav"],
        "nav_date": realtime["nav_date"],
        "data_days": len(nav_list),
        "long_score": long_result["total_score"],
        "short_score": short_result["total_score"],
        "long_rec": get_recommendation(long_result["total_score"])["text"],
        "short_rec": get_recommendation(short_result["total_score"])["text"],
    }


# ============================================================
# Category List Endpoint
# ============================================================

@app.get("/api/categories")
async def list_categories():
    """Return all available categories with fund counts."""
    return {
        "categories": {
            "宽基": {"count": len(BROAD_BASED_FUNDS), "funds": list(BROAD_BASED_FUNDS.keys())},
            "策略": {"count": len(STRATEGY_FUNDS), "funds": list(STRATEGY_FUNDS.keys())},
            "行业": {"count": len(SECTOR_FUNDS), "funds": list(SECTOR_FUNDS.keys())},
        }
    }


# ============================================================
# Static Files & Frontend
# ============================================================

@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")

app.mount("/static", StaticFiles(directory="static"), name="static")


# ============================================================
# Health Check (for cloud deployment monitoring)
# ============================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint for cloud deployment monitoring."""
    is_trading, market_status = is_trading_time()
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "market_status": market_status,
        "version": "2.0.0",
    }


# ============================================================
# Main Entry Point
# ============================================================

if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    # Auto-reload only in development (when PORT not set = running locally)
    is_dev = os.environ.get("PORT") is None
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=is_dev)
