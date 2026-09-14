"""微信推送：Server酱 Turbo / PushPlus / Bark / 企业微信机器人。"""
import requests


def notify(cfg: dict, title: str, content: str) -> bool:
    n = cfg.get("notify", {})
    ntype = n.get("type", "none")

    try:
        if ntype == "serverchan":
            return _serverchan(n.get("serverchan_key", ""), title, content)
        if ntype == "pushplus":
            return _pushplus(n.get("pushplus_token", ""), title, content)
        if ntype == "bark":
            return _bark(n.get("bark_url", ""), title, content)
        if ntype == "wecom":
            return _wecom(n.get("wecom_webhook", ""), title, content)
    except Exception as e:  # 推送失败不影响签到主流程
        print(f"[notify] 推送异常：{e}")
    return False


def _serverchan(key: str, title: str, content: str) -> bool:
    if not key:
        return False
    r = requests.post(
        f"https://sctapi.ftqq.com/{key}.send",
        data={"title": title, "desp": content},
        timeout=15,
    )
    ok = r.status_code == 200 and r.json().get("code") == 0
    print(f"[notify] serverchan -> {ok}")
    return ok


def _pushplus(token: str, title: str, content: str) -> bool:
    if not token:
        return False
    r = requests.post(
        "https://www.pushplus.plus/send",
        json={"token": token, "title": title, "content": content},
        timeout=15,
    )
    ok = r.status_code == 200 and r.json().get("code") == 200
    print(f"[notify] pushplus -> {ok}")
    return ok


def _bark(url: str, title: str, content: str) -> bool:
    if not url:
        return False
    # level=timeSensitive：iOS 时效性通知，穿透专注模式、要求立即投递。
    # 普通级别推送在夜间（睡眠/勿扰/低电量）会被 iOS 延后投递，这是"几小时后才收到"的常见原因；
    # 手机端还需在「设置 → 通知 → Bark」开启时效性通知，或把 Bark 加进专注模式白名单。
    r = requests.post(
        url, json={"title": title, "body": content, "level": "timeSensitive"}, timeout=15
    )
    print(f"[notify] bark -> {r.status_code}")
    return r.status_code == 200


def _wecom(webhook: str, title: str, content: str) -> bool:
    if not webhook:
        return False
    r = requests.post(
        webhook,
        json={"msgtype": "text", "text": {"content": f"{title}\n{content}"}},
        timeout=15,
    )
    ok = r.status_code == 200 and r.json().get("errcode") == 0
    print(f"[notify] wecom -> {ok}")
    return ok
