"""智汇福大统一身份认证登录。

⚠️ 待抓包填充：这里的 URL / 参数 / 加密方式都是占位，需按 docs/capture.md
抓到的真实登录请求替换。登录成功后返回一个带会话（cookie/token）的 requests.Session。
"""
import requests


def login(cfg: dict) -> requests.Session:
    username = cfg["user"]["username"]
    password = cfg["user"]["password"]

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; zhihuifuda) AppleWebKit/537.36",
    })

    # TODO(抓包): 替换为真实登录请求
    # 常见形态（以抓包为准）：
    #   1) 先 GET https://id.fzu.edu.cn/authserver/login 拿 cookie / execution 参数
    #   2) 再 POST 账号密码（密码通常有 RSA 公钥加密 + 时间戳校验）
    #   3) 拿到 ticket 后回调业务系统换取 token
    raise NotImplementedError(
        "登录接口未填充：请按 docs/capture.md 抓取真实登录请求，"
        "替换 src/login.py 中 login() 的实现，并将 token/cookie 存回 session。"
    )
