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
    if not cfg.get("user", {}).get("username") or not cfg.get("user", {}).get("password"):
        sys.exit("config.yaml 中 user.username / user.password 未填写。")
    return cfg
