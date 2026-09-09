"""入口：初始化客户端 → 查询状态 → 定位校验 → 打卡 → 推送结果。

v1.0 主路径：直接使用 App 免登 token（获取方式见 docs/protocol.md），
无需在脚本里保存学号密码。CAS 自动登录为可选增强（src/login.py）。
"""
from src.config import load_config
from src.checkin import AttnClient, query_today_task, do_checkin
from src.notify import notify


def main():
    cfg = load_config()
    token = cfg.get("user", {}).get("token", "")
    if not token:
        raise SystemExit("config.yaml 未配置 token，获取方式见 docs/protocol.md")

    client = AttnClient(token)
    status = query_today_task(client, cfg)
    init_data = status["init"]

    if not status["need_checkin"]:
        title = "智汇福大晚点名：已签到 / 无需操作"
        print(title)
        notify(cfg, title, "今日晚点名已处理，无需重复签到。")
        return

    if not init_data.get("schoolPosition"):
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
