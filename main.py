"""入口：初始化客户端 → 查询状态 → 定位校验 → 打卡 → 推送结果。

v1.0 主路径：直接使用 App 免登 token（获取方式见 docs/protocol.md），
无需在脚本里保存学号密码。CAS 自动登录为可选增强（src/login.py）。
"""
from src.config import load_config
from src.checkin import AttnClient, query_today_task, do_checkin, beijing_now
from src.notify import notify
from src.vacation import matched_range, today_cn
from src.campus import match_campus

import datetime
import os
import re
import sys
import time

import requests

# Windows 计划任务 / run.bat 追加日志时，stdout 默认走 GBK(cp936)，
# 标题里的 ✅ ❌ 编码不了会抛 UnicodeEncodeError 直接终止进程——
# 2026-09-16 晚就因签到成功后 print("…✅") 崩在 notify() 前一行，导致整晚零通知。
# 这里强制 UTF-8 并容错，保证「打印」永远不会中断主流程。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # 非 CPython / 无 reconfigure 能力时忽略
    pass


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


def _notify(cfg, title: str, content: str) -> bool:
    """推送结果。铁律：**先推送，后打印**——打印/编码异常绝不能吞掉通知。

    2026-09-16 教训：GBK 环境下 print("签到成功 ✅") 抛 UnicodeEncodeError，
    进程在 notify() 前一行就死了，签到成功却整晚零消息。
    这里推送失败自动重试一次；仍失败时打印醒目告警（签到结果本身不受影响）。
    """
    ok = False
    for attempt in (1, 2):
        try:
            if notify(cfg, title, content):
                ok = True
                break
        except Exception as e:  # notify 内部已兜底，这里再兜一层
            print(f"[notify] 第 {attempt} 次推送异常：{e}")
        if attempt == 1:
            print("[notify] 推送未成功，重试一次…")
    try:
        print(title)
    except Exception:
        pass
    if not ok:
        print("[notify] 警告：本次结果推送失败，请检查 config.yaml 的 notify 配置（签到结果不受影响）")
    return ok


def main():
    cfg = load_config()

    # GitHub 定时档实测常被延迟 1-4 小时（晚间档可能整批拖到凌晨）：
    # 窗口外到达的运行一律静默跳过（不登录、不推送）；
    # 卡在窗口边缘（21:30-21:34）的运行等满 21:35 再签，避开服务器刚开窗的边界；
    # FZU_CHECKIN_FORCE=1（本地部署脚本试运行用）：绕过窗口限制，只验证连通不真签
    force = bool(os.environ.get("FZU_CHECKIN_FORCE"))
    now = beijing_now()
    if datetime.time(21, 30) <= now.time() < datetime.time(21, 35) and not force:
        wait = (datetime.datetime.combine(now.date(), datetime.time(21, 35)) - now).total_seconds()
        print(f"当前北京时间 {now:%H:%M}，等待 {int(wait) + 1} 秒到 21:35 再执行")
        time.sleep(max(wait, 0) + 1)
        now = beijing_now()
    in_window = datetime.time(21, 35) <= now.time() <= datetime.time(23, 59, 59)
    if not in_window and not force:
        print(f"北京时间 {now:%H:%M} 不在晚点名窗口（21:35-23:59），判定为延迟触发的补跑，静默跳过。")
        return

    # 假期自动跳过：命中校历/自定义区间时什么都不做（默认静默）
    vac = matched_range(cfg)
    if vac:
        if (cfg.get("vacation") or {}).get("notify"):
            _notify(cfg, f"智汇福大晚点名：假期中，已跳过（{vac}）", "假期期间自动签到暂停。")
        else:
            print(f"假期中（{vac}），跳过本次签到。今天是 {today_cn()}。")
        return

    # 定位签到护栏：签前校验配置坐标必须落在任一校区范围内（软约束，防误填/防离校代签）。
    # 服务端 check.action 仍会做精确多边形围栏，这里只是「快速失败」——
    # 明显不对的坐标直接不发签到请求，并把原因推给用户，避免"按了没反应"。
    try:
        lng = float((cfg.get("checkin") or {}).get("longitude"))
        lat = float((cfg.get("checkin") or {}).get("latitude"))
    except (TypeError, ValueError):
        lng = lat = None
    if lng is None or lat is None:
        title = "智汇福大晚点名：坐标未配置 ❌"
        print("未读到有效坐标，本次未签到（请填 config.yaml 的 checkin.longitude / latitude）")
        if not force:
            _notify(cfg, title,
                    "未读到有效坐标，本次未签到。请在 config.yaml 的 checkin.longitude / latitude 填入你的坐标。")
        return
    campus = match_campus(lng, lat, cfg)
    if campus is None:
        title = "智汇福大晚点名：坐标不在校区范围，已拦截 ❌"
        print(f"坐标=({lng}, {lat}) 未命中任何校区")
        if force:
            print("[试运行] 坐标不在任何校区范围内，正式运行会被拦截，请先核对坐标")
        else:
            _notify(cfg, title,
                   "配置的坐标不在任何校区范围内，今日签到已拦截。请核对 config.yaml 的 "
                   "checkin.longitude / latitude；若你在其他校区，可在 campus.bounds 里补上该校区范围。")
        return
    print(f"定位护栏通过：坐标 ({lng}, {lat}) 命中「{campus}」")

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
        # init 返回 500 的两种原因：
        #  a) 跨午夜时段（约 0:00-1:00）服务器尚未发布当日计划（属正常，稍后自愈）
        #  b) token 已失效/过期（服务器对无效 token 也返回 500 而不是 401）
        # token 失效时若还有学号密码，立即重新登录换新 token 重试一次——否则会
        # 「明明有签到计划却报无计划」，白丢一晚。
        username = (cfg.get("user") or {}).get("username", "")
        password = (cfg.get("user") or {}).get("password", "")
        if username and password:
            print(f"init 返回 {e}，尝试重新登录换 token 后重试…")
            status = None
            try:
                from src.login import login as sso_login

                token = sso_login(username, password)
                _save_token(cfg, token)
                client = AttnClient(token)
                status = query_today_task(client, cfg)
                print("重新登录成功，已用新 token 继续。")
            except Exception as e2:
                title = "智汇福大晚点名：服务器暂未返回今日计划"
                if beijing_now().time() < datetime.time(21, 45):
                    _notify(cfg, title, f"服务器未返回今日计划，重新登录也失败：{e2}\n如需请手动打开 App 确认。")
                else:
                    print(f"{title}（重登也失败，兜底跑静默）{e2}")
                return
            if status is None:
                return
        else:
            title = "智汇福大晚点名：服务器暂未返回今日计划"
            # 21:45 前视为首跑，推送提醒一次即可；21:50/22:05 兜底跑静默，避免一晚连推三条
            if beijing_now().time() < datetime.time(21, 45):
                _notify(cfg, title, "服务器暂时无今日计划数据（跨天时段/服务波动），本次跳过。稍后自动重试无需操作。")
            else:
                print(f"{title} {e}（兜底跑：仍无计划数据，静默跳过，不再重复推送）")
            return
    init_data = status["init"]

    if force:
        # 本地部署脚本试运行：只验证配置 / 登录 / 服务器连通，不真签、不推送。
        # 无论是否在签到窗口内都保持只读——避免"试运行"意外产生真实打卡。
        state = "已签到（无需操作）" if not status["need_checkin"] else "待签到（到点会自动执行）"
        print("[试运行] 配置读取 ✅  登录/Token ✅  服务器连通 ✅")
        print(f"[试运行] 今日状态：{state}")
        print("[试运行] 仅验证，不签到、不推送；正式签到由计划任务在 21:35 起自动完成")
        return

    if not status["need_checkin"]:
        # 静默：21:35 首跑成功时已推送过，21:50 兜底跑只需记日志，不再打扰
        print("已签到 / 无需操作（不推送，避免每晚重复通知）")
        return

    if not init_data.get("schoolData"):
        title = "智汇福大晚点名：今日无考勤计划"
        # 首跑（22:00 前）推送提醒一次；后面的兜底跑静默，避免一晚连推多条
        if beijing_now().time() < datetime.time(22, 0):
            _notify(cfg, title, "服务器未返回签到范围（可能今日无晚点名），未执行打卡。")
        else:
            print(f"{title}（晚间兜底跑：无考勤计划，静默跳过，不重复推送）")
        return

    try:
        ok = do_checkin(client, cfg, init_data)
    except Exception as e:  # 接口报错（如不在时段/范围）要带原因推送
        _notify(cfg, "智汇福大晚点名：签到失败 ❌", f"自动签到失败：{e}\n请手动打开 App 签到。")
        return

    if ok:
        _notify(cfg, "智汇福大晚点名：签到成功 ✅", "今日晚点名已自动签到成功。")
    else:
        _notify(cfg, "智汇福大晚点名：不在签到范围 ❌", "定位校验未命中任何校区，请确认配置的经纬度。")


if __name__ == "__main__":
    main()
