"""晚点名签到客户端（v1.0 · 接口版）。

协议逆向自智汇福大 App 晚点名 H5（yzsxg.fzu.edu.cn），完整协议见 docs/protocol.md。

要点：
- 认证：H5 页面 URL 的 `?token=xxx`（App 免登下发）→ 请求头 `token: <token>`
- 加密：AES-128-CBC，KEY = IV = "apexinfoapexinfo"，PKCS7，输出 Base64
- check / clockIn / currentTimestamp 为 GET，密文放查询参数 `param=<urlencode(密文)>`
- init 为 POST，明文 JSON
"""

import base64
import json
import urllib.parse

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

BASE_URL = "https://yzsxg.fzu.edu.cn"
API_PREFIX = "/livecloud/project/fzu/attn"
AES_KEY = b"apexinfoapexinfo"  # KEY == IV（前端源码硬编码）

UA = (
    "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
    "Chrome/120 Mobile Safari/537.36"
)


# ============ 加解密 ============

def encrypt(obj) -> str:
    """AES-128-CBC(key=iv) PKCS7 → Base64，与前端 Encrypt() 一致。"""
    data = obj if isinstance(obj, str) else json.dumps(obj, separators=(",", ":"))
    cipher = AES.new(AES_KEY, AES.MODE_CBC, iv=AES_KEY)
    return base64.b64encode(cipher.encrypt(pad(data.encode(), AES.block_size))).decode()


def decrypt(b64text: str) -> str:
    """与前端 Decrypt() 一致：Base64 → AES-128-CBC 解密。"""
    cipher = AES.new(AES_KEY, AES.MODE_CBC, iv=AES_KEY)
    return unpad(cipher.decrypt(base64.b64decode(b64text)), AES.block_size).decode()


# ============ 客户端 ============

class AttnClient:
    """晚点名接口客户端，token 来自 App 免登 URL（获取方式见 docs/protocol.md）。"""

    def __init__(self, token: str):
        self.token = token
        self.http = requests.Session()
        self.http.headers.update({"User-Agent": UA, "token": token})

    def _enc_get(self, path: str, payload: dict):
        """GET，密文放 param 查询参数（对应前端 createEncryptApi）。"""
        param = urllib.parse.quote(encrypt(payload), safe="")
        url = f"{BASE_URL}{API_PREFIX}/{path}?param={param}"
        resp = self.http.get(url, timeout=15)
        resp.raise_for_status()
        body = resp.json()
        if not (body.get("success") and body.get("code") == 1):
            raise RuntimeError(f"{path} 失败: {body.get('msg') or body}")
        return body.get("data")

    def init(self) -> dict:
        """查询今日晚点名计划与状态（POST，明文，对应前端 createCommonApi）。"""
        url = f"{BASE_URL}{API_PREFIX}/init.action"
        resp = self.http.post(url, json={}, timeout=15)
        resp.raise_for_status()
        body = resp.json()
        if not (body.get("success") and body.get("code") == 1):
            raise RuntimeError(f"init 失败: {body.get('msg') or body}")
        return body.get("data") or {}

    def server_time(self):
        """服务器时间戳（毫秒），用于迟到判定与本地时间校准。"""
        try:
            data = self._enc_get("currentTimestamp.action", {})
            return (data or {}).get("timestamp")
        except Exception:
            return None

    def check(self, longitude: float, latitude: float, school_position) -> list:
        """校验定位是否在签到范围，返回命中的校区/网格列表（取[0]用于打卡参数）。"""
        payload = {
            "mapType": "amap",
            "longitude": longitude,
            "latitude": latitude,
            "range": json.dumps(school_position, separators=(",", ":")),
        }
        data = self._enc_get("check.action", payload)
        return data if isinstance(data, list) else []

    def clock_in(self, *, campus_id, longitude, latitude, start_time, end_time,
                 actual_location, coll_unit, way, is_late) -> dict:
        """提交打卡（GET + 加密 param），返回 {attn: {...}}。"""
        payload = {
            "campus": campus_id or "",
            "lon": longitude,
            "lat": latitude,
            "startTime": start_time,
            "endTime": end_time,
            "actualLocation": actual_location,
            "caIsNo": "0",
            "collUnit": coll_unit,
            "way": way,
            "isLate": 1 if is_late else 0,
        }
        return self._enc_get("clockIn.action", payload) or {}


# ============ 对 main.py 的两个适配入口 ============

def query_today_task(client: AttnClient, cfg: dict) -> dict:
    """查询当天状态。返回 {"need_checkin": bool, "init": init响应}。"""
    data = client.init()
    return {"need_checkin": not data.get("clockSuccess"), "init": data}


def do_checkin(client: AttnClient, cfg: dict, init_data: dict) -> bool:
    """按 init 数据 + 配置定位完成 check → clockIn 全链路。"""
    import datetime

    longitude = float(cfg["checkin"]["longitude"])
    latitude = float(cfg["checkin"]["latitude"])

    # 1. 定位校验
    matched = client.check(longitude, latitude, init_data.get("schoolPosition"))
    if not matched:
        return False
    campus = matched[0] or {}

    # 2. 迟到判定（以服务器时间为准，无则退回本机时间）
    ts = client.server_time()
    now = datetime.datetime.fromtimestamp(ts / 1000) if ts else datetime.datetime.now()
    try:
        h, m = map(int, (init_data.get("clockEndTime") or "23:59").split(":")[:2])
        is_late = now.hour * 60 + now.minute > h * 60 + m
    except Exception:
        is_late = False

    # 3. 提交打卡
    client.clock_in(
        campus_id=campus.get("id"),
        longitude=longitude,
        latitude=latitude,
        start_time=init_data.get("clockStartTime"),
        end_time=init_data.get("clockEndTime"),
        actual_location=cfg["checkin"].get("actual_location", ""),
        coll_unit=campus,
        way=init_data.get("clockWay"),
        is_late=is_late,
    )
    return True
