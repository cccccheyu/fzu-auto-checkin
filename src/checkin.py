"""晚点名签到。

⚠️ 待抓包填充：需按 docs/capture.md 抓取「打开晚点名页面」和「提交签到」两个请求，
确认接口 URL、参数、签名/加密方式后替换。
"""


def query_today_task(session, cfg: dict):
    """查询当天晚点名签到任务状态。

    返回 dict，至少包含：
        {"need_checkin": bool, "raw": 原始响应}
    TODO(抓包): 替换为真实「查询任务」请求。
    """
    raise NotImplementedError(
        "查询接口未填充：请按 docs/capture.md 抓取真实查询请求，替换 src/checkin.py。"
    )


def do_checkin(session, cfg: dict) -> bool:
    """提交签到。

    TODO(抓包): 替换为真实「提交签到」请求（可能含定位经纬度、地址等）。
    """
    raise NotImplementedError(
        "签到接口未填充：请按 docs/capture.md 抓取真实提交请求，替换 src/checkin.py。"
    )
