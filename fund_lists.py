"""
基金分类预设列表 - 宽基/策略/行业 基金代码映射
Fund Category Presets - Broad-based / Strategy / Sector fund code mappings

每个分类包含基金代码和对应的推荐基金(用于批量展示时的推荐)
"""

# ============================================================
# 宽基指数基金 (Broad-based Index Funds)
# ============================================================
BROAD_BASED_FUNDS = {
    "恒生指数": {"code": "513660", "name": "华夏恒生ETF", "desc": "跟踪香港恒生指数"},
    "上证50": {"code": "510050", "name": "华夏上证50ETF", "desc": "跟踪上证50指数"},
    "中证全指": {"code": "563800", "name": "中证全指ETF", "desc": "跟踪中证全指"},
    "沪深300": {"code": "510300", "name": "华泰柏瑞沪深300ETF", "desc": "跟踪沪深300指数"},
    "中证500": {"code": "510500", "name": "南方中证500ETF", "desc": "跟踪中证500指数"},
    "创业板指数": {"code": "159915", "name": "易方达创业板ETF", "desc": "跟踪创业板指数"},
    "上证180": {"code": "510180", "name": "华安上证180ETF", "desc": "跟踪上证180指数"},
    "科创50": {"code": "588000", "name": "华夏科创50ETF", "desc": "跟踪科创50指数"},
    "纳斯达克100": {"code": "513100", "name": "国泰纳斯达克100ETF", "desc": "跟踪纳斯达克100指数"},
    "标普500": {"code": "513500", "name": "博时标普500ETF", "desc": "跟踪标普500指数"},
}

# ============================================================
# 策略指数基金 (Strategy Index Funds)
# ============================================================
STRATEGY_FUNDS = {
    "中证红利低波动": {"code": "512890", "name": "华泰柏瑞红利低波ETF", "desc": "跟踪中证红利低波动指数"},
    "中证A50": {"code": "560050", "name": "华泰柏瑞中证A50ETF", "desc": "跟踪中证A50指数"},
    "中证红利": {"code": "510880", "name": "华泰柏瑞红利ETF", "desc": "跟踪中证红利指数"},
    "中证500质量成长": {"code": "560500", "name": "中证500质量成长ETF", "desc": "跟踪中证500质量成长指数"},
    "深证红利": {"code": "159905", "name": "深证红利ETF", "desc": "跟踪深证红利指数"},
    "中证国企红利": {"code": "561580", "name": "国企红利ETF", "desc": "跟踪中证国有企业红利指数"},
}

# ============================================================
# 行业板块基金 (Sector Funds) - 每个板块推荐一只代表性基金
# ============================================================
SECTOR_FUNDS = {
    "银行": {"code": "512800", "name": "华宝银行ETF", "recommend": "512800", "desc": "中证银行指数"},
    "证券": {"code": "512880", "name": "国泰证券ETF", "recommend": "512880", "desc": "中证全指证券公司指数"},
    "医药": {"code": "512010", "name": "华宝医药ETF", "recommend": "512010", "desc": "中证医药卫生指数"},
    "港股通医药": {"code": "513120", "name": "港股通医药ETF", "recommend": "513120", "desc": "中证港股通医药卫生综合指数"},
    "创新药": {"code": "515120", "name": "创新药ETF", "recommend": "515120", "desc": "中证创新药产业指数"},
    "生物科技": {"code": "159837", "name": "生物科技ETF", "recommend": "159837", "desc": "中证生物科技主题指数"},
    "科技50": {"code": "515750", "name": "科技50ETF", "recommend": "515750", "desc": "中证科技50指数"},
    "恒生科技": {"code": "513180", "name": "恒生科技ETF", "recommend": "513180", "desc": "恒生科技指数"},
    "云计算": {"code": "516510", "name": "云计算ETF", "recommend": "516510", "desc": "中证云计算与大数据主题指数"},
    "芯片": {"code": "159995", "name": "芯片ETF", "recommend": "159995", "desc": "国证半导体芯片指数"},
    "半导体材料设备": {"code": "159691", "name": "半导体材料设备ETF", "recommend": "159691", "desc": "中证半导体材料设备主题指数"},
    "软件": {"code": "515230", "name": "软件ETF", "recommend": "515230", "desc": "中证软件服务指数"},
    "消费电子": {"code": "159732", "name": "消费电子ETF", "recommend": "159732", "desc": "中证消费电子主题指数"},
    "电信": {"code": "563010", "name": "电信ETF", "recommend": "563010", "desc": "中证电信主题指数"},
    "消费": {"code": "159928", "name": "消费ETF", "recommend": "159928", "desc": "中证主要消费指数"},
    "军工": {"code": "512660", "name": "军工ETF", "recommend": "512660", "desc": "中证军工指数"},
    "光伏": {"code": "515790", "name": "光伏ETF", "recommend": "515790", "desc": "中证光伏产业指数"},
    "储能电池": {"code": "159689", "name": "储能电池ETF", "recommend": "159689", "desc": "储能电池主题"},
    "稀土": {"code": "516780", "name": "稀土ETF", "recommend": "516780", "desc": "中证稀土产业指数"},
    "绿色电力": {"code": "159611", "name": "绿色电力ETF", "recommend": "159611", "desc": "中证绿色电力指数"},
    "人工智能": {"code": "159819", "name": "人工智能ETF", "recommend": "159819", "desc": "中证人工智能主题指数"},
    "科创人工智能": {"code": "588900", "name": "科创AI ETF", "recommend": "588900", "desc": "上证科创板人工智能指数"},
    "信创": {"code": "159537", "name": "信创ETF", "recommend": "159537", "desc": "中证信息技术应用创新产业指数"},
    "物联网": {"code": "159701", "name": "物联网ETF", "recommend": "159701", "desc": "中证物联网主题指数"},
    "高端制造": {"code": "159638", "name": "高端制造ETF", "recommend": "159638", "desc": "中证高端制造主题指数"},
    "机器人": {"code": "562500", "name": "机器人ETF", "recommend": "562500", "desc": "机器人主题"},
    "智能汽车": {"code": "515250", "name": "智能汽车ETF", "recommend": "515250", "desc": "中证智能汽车主题指数"},
    "碳中和": {"code": "159790", "name": "碳中和ETF", "recommend": "159790", "desc": "中证内地低碳经济主题指数"},
    "新能源": {"code": "516160", "name": "新能源ETF", "recommend": "516160", "desc": "中证新能源指数"},
    "一带一路": {"code": "515110", "name": "一带一路ETF", "recommend": "515110", "desc": "中证国企一带一路指数"},
    "电网设备": {"code": "159611", "name": "绿色电力ETF", "recommend": "159611", "desc": "电网/绿色电力主题"},
    "存储芯片": {"code": "159690", "name": "存储芯片ETF", "recommend": "159690", "desc": "存储芯片主题"},
    "CPO": {"code": "515050", "name": "5GETF", "recommend": "515050", "desc": "CPO/光通信相关"},
    "商业航天": {"code": "563300", "name": "商业航天ETF", "recommend": "563300", "desc": "商业航天主题"},
    "有色金属": {"code": "512400", "name": "有色金属ETF", "recommend": "512400", "desc": "中证申万有色金属指数"},
    "半导体芯片": {"code": "512480", "name": "半导体ETF", "recommend": "512480", "desc": "中证全指半导体产品与设备指数"},
    "锂矿": {"code": "159840", "name": "锂电池ETF", "recommend": "159840", "desc": "锂矿/锂电池主题"},
    "新能源电池": {"code": "159755", "name": "电池ETF", "recommend": "159755", "desc": "中证电池主题指数"},
    "储能": {"code": "159689", "name": "储能电池ETF", "recommend": "159689", "desc": "储能/电池主题"},
    "黄金": {"code": "009505", "name": "博时黄金ETF联接C", "recommend": "009505", "desc": "跟踪国内黄金价格"},
}


def get_funds_by_category(category: str) -> dict[str, dict]:
    """Return fund list for a given category name."""
    cat = category.strip()
    if cat in ("宽基", "指数", "宽基指数", "broad"):
        return BROAD_BASED_FUNDS
    elif cat in ("策略", "strategy"):
        return STRATEGY_FUNDS
    elif cat in ("行业", "板块", "sector"):
        return SECTOR_FUNDS
    return {}


def get_recommend_code(category: str, sector_name: str) -> str | None:
    """Get recommended fund code for a specific sector."""
    if category in ("行业", "板块", "sector"):
        info = SECTOR_FUNDS.get(sector_name, {})
        return info.get("recommend") or info.get("code")
    return None


def all_funds_in_category(category: str) -> list[dict]:
    """Return all funds in a category as list of {name, code, desc, recommend}."""
    funds = get_funds_by_category(category)
    result = []
    for name, info in funds.items():
        result.append({
            "sector": name,
            "code": info["code"],
            "name": info["name"],
            "desc": info.get("desc", ""),
            "recommend": info.get("recommend", info["code"]),
        })
    return result
