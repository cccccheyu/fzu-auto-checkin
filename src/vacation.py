"""假期跳过：根据校历/自定义日期区间，假期内不执行任何签到操作。

区间来源（config.yaml 的 vacation.skip_ranges）：
- 官方校历：福州大学 2026—2027 学年校历（福大教〔2026〕10号）
  寒假 2027-01-23 ~ 2027-02-21；暑假 2027-07-03 ~ 2027-08-29
- 个人区间：用户可自行添加（如实训、离校等），同样只跳过、不代签
"""
import datetime

# 北京时间（GitHub Actions 跑在 UTC，统一按 UTC+8 判定“今天”）
_TZ_CN = datetime.timezone(datetime.timedelta(hours=8), "Asia/Shanghai")


def today_cn() -> datetime.date:
    return datetime.datetime.now(_TZ_CN).date()


def matched_range(cfg: dict, today: datetime.date | None = None):
    """命中假期则返回区间名（用于提示），否则返回 None。"""
    ranges = ((cfg.get("vacation") or {}).get("skip_ranges")) or []
    today = today or today_cn()
    for r in ranges:
        try:
            start = datetime.date.fromisoformat(str(r["start"]))
            end = datetime.date.fromisoformat(str(r["end"]))
        except (KeyError, ValueError):
            continue  # 区间写错格式直接忽略，不影响正常签到
        if start <= today <= end:
            return r.get("name") or f"{start} ~ {end}"
    return None
