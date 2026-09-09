"""读取 config.yaml 配置。"""
import os
import sys

import yaml

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml")


def load_config(path: str = CONFIG_PATH) -> dict:
    if not os.path.exists(path):
        sys.exit("缺少 config.yaml：请先 `cp config.example.yaml config.yaml` 并填写真实值。")
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    # token 与 学号密码 二选一即可：有 token 直接用；没有则用学号密码走 SSO 登录
    if not (cfg.get("user", {}).get("token") or
            (cfg.get("user", {}).get("username") and cfg.get("user", {}).get("password"))):
        sys.exit(
            "config.yaml 认证信息不全：请至少配置 user.token，"
            "或同时配置 user.username / user.password（智汇福大 App 登录账号）。"
        )
    cfg["_config_path"] = path
    return cfg
