"""入口：初始化客户端 → 查询状态 → 定位校验 → 打卡 → 推送结果。

v1.0 主路径：直接使用 App 免登 token（获取方式见 docs/protocol.md），
无需在脚本里保存学号密码。CAS 自动登录为可选增强（src/login.py）。
"""
from src.config import load_config
from src.checkin import AttnClient, query_today_task, do_checkin, beijing_now
from src.notify import notify
from src.vacation import matched_range, today_cn

import datetime
import re

import requests


def _save_token(cfg, token: str):
    """把新 token 回写到 config.yaml（避免每次运行都重新登录）。"""
    try:
        path = cfg.get("_config_path")
        if not path:
            return
        text = open(path, encoding="utf-8").read()
        new_text, n = re.subn(
            r'(token:\s*")([^"]*)(")', rf"\g<1>{token}\g<3>", text, count=1
        )
        if n:
            open(path, "w", encoding="utf-8").write(new_text)
            print("新 token 已回写 config.yaml")
    except Exception as e:
        print(f"token 回写失败（不影响本次运行）: {e}")


def main():
    cfg = load_config()

    # 假期自动跳过：命中校历/自定义区间时什么都不做（默认静默）
    vac = matched_range(cfg)
    if vac:
        print(f"假期中（{vac}），跳过本次签到。今天是 {today_cn()}。")
        if (cfg.get("vacation") or {}).get("notify"):
            notify(cfg, f"智汇福大晚点名：假期中，已跳过（{vac}）", "假期期间自动签到暂停。")
        return

    token = (cfg.get("user") or {}).get("token", "")
    if not token:
        username = (cfg.get("user") or {}).get("username", "")
        password = (cfg.get("user") or {}).get("password", "")
        if not (username and password):
            raise SystemExit(
                "config.yaml 未配置 token，且学号/密码不全（学号密码=智汇福大 App 登录账号）"
            )
        from src.login import login as sso_login

        token = sso_login(username, password)
        print("SSO 登录成功，已获取新 token")
        _save_token(cfg, token)

    client = AttnClient(token)
    try:
        status = query_today_task(client, cfg)
    except requests.HTTPError as e:
        # 跨午夜时段（约 0:00-1:00）服务器尚未发布当日计划时会返回 500，
        # 属正常现象；定时任务设在 21:35/21:50/22:05 不受影响。
        title = "智汇福大晚点名：服务器暂未返回今日计划"
        print(title, e)
        # 21:45 前视为首跑，推送提醒一次即可；21:50/22:05 兜底跑静默，避免一晚连推三条
        if beijing_now().time() < datetime.time(21, 45):
            notify(cfg, title, "服务器暂时无今日计划数据（跨天时段/服务波动），本次跳过。稍后自动重试无需操作。")
        else:
            print("（兜底跑：仍无计划数据，静默跳过，不再重复推送）")
        return
    init_data = status["init"]

    if not status["need_checkin"]:
        # 静默：21:35 首跑成功时已推送过，21:50 兜底跑只需记日志，不再打扰
        print("已签到 / 无需操作（不推送，避免每晚重复通知）")
        return

    if not init_data.get("schoolData"):
        title = "智汇福大晚点名：今日无考勤计划"
        print(title)
        notify(cfg, title, "服务器未返回签到范围（可能今日无晚点名），未执行打卡。")
        return

    try:
        ok = do_checkin(client, cfg, init_data)
    except Exception as e:  # 接口报错（如不在时段/范围）要带原因推送
        title = "智汇福大晚点名：签到失败 ❌"
        print(title, e)
        notify(cfg, title, f"自动签到失败：{e}\n请手动打开 App 签到。")
        return

    if ok:
        title = "智汇福大晚点名：签到成功 ✅"
        print(title)
        notify(cfg, title, "今日晚点名已自动签到成功。")
    else:
        title = "智汇福大晚点名：不在签到范围 ❌"
        print(title)
        notify(cfg, title, "定位校验未命中任何校区，请确认配置的经纬度。")


if __name__ == "__main__":
    main()
