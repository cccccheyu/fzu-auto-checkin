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
    r = requests.post(url, json={"title": title, "body": content}, timeout=15)
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
