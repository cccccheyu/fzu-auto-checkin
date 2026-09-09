# fzu-auto-checkin · 智汇福大晚点名自动签到

福州大学「智汇福大」App 晚点名签到的自动化工具。双版本路线：

- **v0.1 · 无障碍版**（Android Auto.js 脚本）：定时打开智汇福大 → 自动进入晚点名 → 自动点签到。不碰接口、不怕改版加密，上手门槛最低。
- **v1.0 · 接口版**（Python + GitHub Actions）：逆向晚点名 H5 接口，云端定时执行，结果微信推送。**手机上什么都不用装，iOS 用户同样适用。**

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
| v0.1 无障碍脚本 | ✅ 控件已 dump 并填充（基于 MuMu 模拟器实测） |
| v1.0 接口协议逆向 | ✅ **完成**（免登 token + AES-CBC + 4 个接口全打通，见 [docs/protocol.md](docs/protocol.md)） |
| v1.0 客户端实现 | ✅ `src/checkin.py`（init → check → clockIn 全链路） |
| CAS 自动换取 token | ⏳ TODO（目前 token 需从 Android logcat 获取，见下） |
| v0.1 / v1.0 真机验证 | ⏳ 待校园内实测 |

**iOS 用户看这里**：iOS 无越狱抓不到 App 内部请求（SSL Pinning），也无法模拟点击——
所以 iOS 的正确姿势是 **v1.0 云端跑**：脚本在 GitHub Actions 上定时执行，你手机只收
微信推送，什么都不用装。获取一次性 token 需要 Android 环境借力（[docs/protocol.md](docs/protocol.md) §4），
CAS 自动登录完成后将不再需要。

## 路线图

- [x] 项目骨架、推送、定时任务
- [x] PC 安装 Android 模拟器（MuMu），安装智汇福大 APK
- [x] v0.1：uiautomator dump 晚点名页面控件 → 完成自动点击脚本
- [x] v1.0：logcat + 前端 JS 静态分析逆向晚点名接口（无需 Frida），AES-CBC 参数加密破解，`src/checkin.py` 全链路实现
- [ ] 真机/真 token 实测一轮完整签到
- [ ] CAS 自动登录换取 token（`src/login.py`），实现全自动免维护
- [ ] 发布 v1.0，支持多账号、结果推送

## 目录结构

```
fzu-auto-checkin/
├── main.py                  # v1.0 入口：init → check → clockIn → 推送
├── config.example.yaml      # 配置模板（复制为 config.yaml 填真实值）
├── requirements.txt
├── src/
│   ├── config.py            # 读取配置
│   ├── login.py             # CAS 自动登录（TODO，可选项）
│   ├── checkin.py           # 晚点名接口客户端（token + AES-CBC，已实现）
│   └── notify.py            # 微信推送
├── scripts/
│   └── autojs_wandianming.js    # v0.1 无障碍脚本（控件已实测填充）
├── docs/
│   ├── protocol.md          # 晚点名接口协议逆向笔记（token/加密/API 全记录）
│   └── capture.md           # 抓包教程
└── .github/workflows/checkin.yml  # v1.0 定时任务
```

## 参与贡献（欢迎各校同学）

1. 有 Android 设备/模拟器的同学：按 [`docs/capture.md`](docs/capture.md) 抓包（或用 Auto.js dump 控件），提 Issue/PR 提交你学校/系统的适配。
2. 提交内容请**脱敏**：密码、学号、token 一律打码，只保留结构。
3. 本项目不接受、不鼓励任何形式的代挂与有偿使用。

## 许可证

MIT
