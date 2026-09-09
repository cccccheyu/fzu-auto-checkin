"""入口：登录 → 查询任务 → 签到 → 推送结果。"""
from src.config import load_config
from src.login import login
from src.checkin import query_today_task, do_checkin
from src.notify import notify


def main():
    cfg = load_config()
    session = login(cfg)

    status = query_today_task(session, cfg)

    if not status.get("need_checkin"):
        title = "智汇福大晚点名：已签到 / 无需操作"
        print(title)
        notify(cfg, title, "今日晚点名已处理，无需重复签到。")
        return

    ok = do_checkin(session, cfg)
    if ok:
        title = "智汇福大晚点名：签到成功 ✅"
        print(title)
        notify(cfg, title, "今日晚点名已自动签到成功。")
    else:
        title = "智汇福大晚点名：签到失败 ❌"
        print(title)
        notify(cfg, title, "自动签到失败，请手动打开 App 签到。")


if __name__ == "__main__":
    main()
