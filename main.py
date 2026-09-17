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
import json
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


def _daily_confirm_state_path(cfg):
    """每日完成确认的去重状态文件（记当天日期即可）。

    放在 config.yaml 同级的 state/ 下；拿不到配置目录时退回用户家目录。
    云端（GitHub Actions）每次都是全新容器、磁盘不保留，天然去不了重——
    所以那边靠 _on_github_actions() 直接关掉，否则 16 档会每档都推、刷屏。
    """
    try:
        base = os.path.dirname(os.path.abspath(cfg.get("_config_path") or ""))
        if base and os.path.isdir(base):
            d = os.path.join(base, "state")
            os.makedirs(d, exist_ok=True)
            return os.path.join(d, "daily_confirm.json")
    except Exception:
        pass
    return os.path.join(os.path.expanduser("~"), ".fzu-checkin-daily-confirm.json")


def _on_github_actions() -> bool:
    """是否跑在 GitHub Actions 上（云端无持久磁盘，每日确认必须关闭）。"""
    return os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _daily_confirm(cfg, title: str, content: str) -> bool:
    """每晚至多推一次的「完成确认」（心跳）。

    价值：让你能区分「系统活着、今晚只是没活干」和「系统已经死了三天你不知道」。
    2026-09-16 那次事故就是签到成功却因打印崩溃整晚零消息，用户完全无从判断系统状态。

    规则：
    - 开关：`notify.daily_confirm`（**默认 false**，需显式写 true 才发）。
      2026-09-17 用户拍板：「全关了吧，如果有 bug 再发通知」——
      心跳的价值（探测"程序完全没跑"）被判定为不值每晚这一条的打扰。
      ⚠️ 代价必须清楚：关掉后，「程序崩溃/电脑没开/计划任务被删」这类
      **发不出消息的故障将完全静默**，只能等下次真需要签到那晚才发现。
      签到失败 / 不在范围 / 坐标异常等**异常仍然照推**（那些走 _notify，不受本开关管），
      所以"有 bug 再通知"这条是满足的。
    - 云端强制关闭（见 _on_github_actions）
    - 去重：状态文件记当天日期，当天已推过就静默
    - **只用于「结论已确定」的分支**。像「服务器还没发布计划」这种
      不确定状态不要走这里——它自己有推送逻辑，拿来当心跳会发出假消息。
    - 不硬编码发送时刻：哪档先遇到确定结论就哪档发，因此对任意排档都自适应。
    - **签到成功/失败的分支不再补心跳**：那些分支已经把结论推给你了，
      当晚你已经知道结果，再补一条「今日已完成」就是重复（见 _mark_confirmed）。
    """
    if _on_github_actions():
        print("（GitHub Actions 环境：每日完成确认已关闭，避免每档重复推送）")
        return False
    if not (cfg.get("notify") or {}).get("daily_confirm", False):
        return False

    today = beijing_now().strftime("%Y-%m-%d")
    path = _daily_confirm_state_path(cfg)
    try:
        if os.path.exists(path):
            if (json.load(open(path, encoding="utf-8")) or {}).get("date") == today:
                print(f"每日完成确认：今天（{today}）已推送过，本次静默")
                return False
    except Exception as e:
        print(f"读取确认状态失败（按未推送处理）: {e}")

    if not _notify(cfg, title, content):
        return False

    try:
        json.dump({"date": today}, open(path, "w", encoding="utf-8"))
    except Exception as e:
        print(f"写入确认状态失败（不影响签到结果）: {e}")
    return True


def _mark_confirmed(cfg):
    """把当天标记为「今晚已经推送过结论」，后续档不再补心跳。

    2026-09-17 实测：21:35 那档签到成功、推了「签到成功 ✅」，但它走的是 _notify，
    **不写去重状态**；21:50 那档发现「已签到」→ 走 _daily_confirm → 以为今晚还没推过
    → 又推一条「今日已完成 ✅」，一晚白收两条。

    签到成功 / 签到失败 / 不在签到范围，都是当晚已送达的确定结论，
    心跳的价值（证明系统还活着）已经兑现，不必再来一条。

    ⚠️ **只在推送成功后调用**（调用点见 main 末尾）。推送失败时必须不标记，
    否则「结论没送到 + 心跳也被压掉」= 整晚零消息，正是 2026-09-16 的故障形态。
    """
    if _on_github_actions():
        return
    try:
        json.dump({"date": beijing_now().strftime("%Y-%m-%d")},
                  open(_daily_confirm_state_path(cfg), "w", encoding="utf-8"))
    except Exception as e:
        print(f"写入确认状态失败（不影响签到结果）: {e}")


def main():
    # 启动时间戳：run.log 由计划任务长期追加，没有时间信息就只能靠行序推演，
    # 一次崩溃发生在几点、是哪一次运行都无从判断（2026-09-16 排查的最大障碍）。
    print(f"===== 启动：北京时间 {beijing_now():%Y-%m-%d %H:%M:%S} =====")
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
        # 已签到：每晚至多推一条「今日已完成」当心跳。
        # 以前这里是彻底静默，代价是——首档签到成功但推送丢失时（2026-09-16），
        # 整晚一条消息都没有，你根本分不清「系统正常但没活干」还是「系统已经死了」。
        _daily_confirm(
            cfg,
            "智汇福大晚点名：今日已完成 ✅",
            "今日晚点名已签到，无需任何操作。\n"
            "（每晚一条的完成确认，用来确认自动签到还在正常运行。\n"
            "不想收到：在 config.yaml 的 notify: 下面加一行 daily_confirm: false）",
        )
        return

    if not init_data.get("schoolData"):
        # 今日无考勤计划也是「确定结论」，同样纳入每晚一条的完成确认
        _daily_confirm(
            cfg,
            "智汇福大晚点名：今日无考勤计划",
            "服务器未返回签到范围（可能今日无晚点名），未执行打卡。\n"
            "（每晚一条的完成确认，用来确认自动签到还在正常运行。\n"
            "不想收到：在 config.yaml 的 notify: 下面加一行 daily_confirm: false）",
        )
        return

    try:
        ok = do_checkin(client, cfg, init_data)
    except Exception as e:  # 接口报错（如不在时段/范围）要带原因推送
        if _notify(cfg, "智汇福大晚点名：签到失败 ❌", f"自动签到失败：{e}\n请手动打开 App 签到。"):
            _mark_confirmed(cfg)
        return

    if ok:
        delivered = _notify(cfg, "智汇福大晚点名：签到成功 ✅", "今日晚点名已自动签到成功。")
    else:
        delivered = _notify(cfg, "智汇福大晚点名：不在签到范围 ❌", "定位校验未命中任何校区，请确认配置的经纬度。")

    # 只有「结论确实送到用户手上」才标记当晚已确认。
    # 推送失败时不标记 → 后续档的 _daily_confirm 会补一条心跳当兜底报警，
    # 正好覆盖 2026-09-16 那种「签到成功但推送丢了、整晚零消息」的故障。
    if delivered:
        _mark_confirmed(cfg)


if __name__ == "__main__":
    main()
