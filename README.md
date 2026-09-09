# fzu-auto-checkin · 智汇福大晚点名自动签到

福州大学「智汇福大」App 晚点名签到的自动化工具。规划双版本路线：

- **v0.1 · 无障碍版**（Android Auto.js 脚本）：定时打开智汇福大 → 自动进入晚点名 → 自动点签到。不碰接口、不怕改版加密，上手门槛最低。
- **v1.0 · 接口版**（Python + GitHub Actions）：逆向登录/签到接口，云端定时执行，结果微信推送。

> ⚠️ **免责声明**
>
> 1. 本项目仅供学习自动化、Android 无障碍开发与接口逆向技术交流使用。
> 2. 晚点名是学校的安全确认制度，请仅在**本人确实在校**时用于防止漏签，切勿用于向学校隐瞒真实在/离校状态。
> 3. **禁止任何人使用本项目提供付费代挂服务。**
> 4. 因使用本项目违反校规或造成的一切后果，由使用者自行承担。
> 5. 请勿在本项目 Issue/PR 中提交真实密码、token 等凭据。

## 当前状态

| 模块 | 状态 |
|------|------|
| 项目骨架 / 配置模板 | ✅ 已完成 |
| 微信推送（Server酱/PushPlus/Bark/企业微信） | ✅ 已完成 |
| GitHub Actions 定时任务 | ✅ 已完成 |
| v1.0 登录/签到接口逆向 | ⏳ 待 Android 环境（模拟器 + Frida）抓包 |
| v0.1 无障碍脚本 | ✅ 控件已 dump 并填充（基于 MuMu 模拟器实测） |

**关键进展**：智汇福大 App 登录走统一身份认证（`sso.fzu.edu.cn`），晚点名业务在学工系统（`yzsxg.fzu.edu.cn`），但 App 端做了 SSL Pinning（iOS 无越狱抓不到），PC 端学工系统无学生自签入口——所以需要 **Android 模拟器**环境继续。

## 路线图

- [x] 项目骨架、推送、定时任务
- [x] PC 安装 Android 模拟器（MuMu），安装智汇福大 APK
- [x] v0.1：uiautomator dump 晚点名页面控件 → 完成自动点击脚本（晚点名为 H5 页但无障碍可用；状态 `未签到`/`已签到`，按钮 `晚点打卡`，仅旗山校区 21:30-23:59 可签）
- [ ] v0.1 真机验证：Auto.js 在真实手机上跑通一次完整签到
- [ ] v1.0：模拟器 + Frida 绕过证书校验 → 抓登录/查询/签到 3 个接口 → 填充 `src/login.py`、`src/checkin.py`
- [ ] 发布 v1.0，支持多账号、结果推送

## 目录结构

```
fzu-auto-checkin/
├── main.py                  # v1.0 入口：登录 → 查任务 → 签到 → 推送
├── config.example.yaml      # 配置模板（复制为 config.yaml 填真实值）
├── requirements.txt
├── src/
│   ├── config.py            # 读取配置
│   ├── login.py             # 登录（待抓包填充）
│   ├── checkin.py           # 签到（待抓包填充）
│   └── notify.py            # 微信推送
├── scripts/
│   └── autojs_wandianming.js    # v0.1 无障碍脚本（控件已实测填充）
├── docs/
│   └── capture.md           # 抓包教程
└── .github/workflows/checkin.yml  # v1.0 定时任务
```

## 参与贡献（欢迎各校同学）

1. 有 Android 设备/模拟器的同学：按 [`docs/capture.md`](docs/capture.md) 抓包（或用 Auto.js dump 控件），提 Issue/PR 提交你学校/系统的适配。
2. 提交内容请**脱敏**：密码、学号、token 一律打码，只保留结构。
3. 本项目不接受、不鼓励任何形式的代挂与有偿使用。

## 许可证

MIT
