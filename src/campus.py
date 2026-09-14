"""定位签到护栏：每日签前校验坐标必须落在校区范围内。

说明：
- 服务端 check.action 本身会做精确多边形围栏校验，本模块是「软约束 + 快速失败」：
  在发起任何签到请求前，先判断配置的坐标是否落在校区边界盒内，
  明显填错（如填了老家/异地坐标）会直接拦截并推送提醒，不发签到请求。
- 边界盒为宽泛范围（GCJ-02 高德坐标系），用于拦截明显越界的坐标，
  精确判定仍以服务端围栏为准。盒子刻意放宽，避免把正常在校同学误拦。
- 已在 config.yaml 的 campus.bounds 里写出的校区优先；未配置时用下面内置的
  福州大学各校区默认盒。需要新增/收窄校区时，照格式追加一条即可。
"""

# 福州大学各校区边界盒（GCJ-02，含生活区；取宽泛范围防误拦，精确围栏由服务端判定）
DEFAULT_BOUNDS = {
    "旗山校区": {
        "min_lng": 119.16, "max_lng": 119.24,
        "min_lat": 26.02, "max_lat": 26.09,
    },
    "怡山校区": {
        "min_lng": 119.25, "max_lng": 119.31,
        "min_lat": 26.04, "max_lat": 26.10,
    },
    "铜盘校区": {
        "min_lng": 119.23, "max_lng": 119.30,
        "min_lat": 26.08, "max_lat": 26.14,
    },
    "晋江校区": {
        "min_lng": 118.54, "max_lng": 118.64,
        "min_lat": 24.51, "max_lat": 24.61,
    },
    "泉港校区": {
        "min_lng": 118.80, "max_lng": 118.90,
        "min_lat": 25.09, "max_lat": 25.18,
    },
    "厦门集美校区": {
        "min_lng": 118.05, "max_lng": 118.13,
        "min_lat": 24.59, "max_lat": 24.68,
    },
    "厦门鼓浪屿校区": {
        "min_lng": 118.02, "max_lng": 118.10,
        "min_lat": 24.41, "max_lat": 24.48,
    },
}


def get_bounds(cfg: dict) -> dict:
    """读取校区边界盒配置，未配置时用内置默认。"""
    bounds = (cfg.get("campus") or {}).get("bounds")
    if not bounds:
        return DEFAULT_BOUNDS
    return bounds


def match_campus(longitude: float, latitude: float, cfg: dict):
    """返回命中的校区名；坐标不在任何校区范围内返回 None。"""
    for name, box in get_bounds(cfg).items():
        try:
            if (box["min_lng"] <= longitude <= box["max_lng"]
                    and box["min_lat"] <= latitude <= box["max_lat"]):
                return name
        except (KeyError, TypeError):
            continue
    return None
