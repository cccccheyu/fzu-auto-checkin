# fzu-auto-checkin · 福州大学晚点名自动签到

![License](https://img.shields.io/github/license/cccccheyu/fzu-auto-checkin) ![Python](https://img.shields.io/badge/python-3.11+-blue) ![GitHub Actions](https://img.shields.io/badge/cron-21%3A35%20%2F%2021%3A50-green)

福州大学「智汇福大」晚点名（21:30–23:59）的自动签到工具：**每晚定时自动打卡，结果微信推送**。手机零安装，iOS / 安卓都能用。

> ⚠️ **使用须知**
>
> 晚点名是学校的安全确认制度。本项目仅用于**本人确实在校时防止漏签**，禁止用于向学校隐瞒真实在/离校状态，禁止付费代挂。违规后果由使用者自行承担。

## 功能

- ⏰ 定时自动签到（默认每晚 21:35 / 21:50 两次，错过一次还有一次）
- 📲 签到结果微信推送（Server酱 / PushPlus / Bark / 企业微信）
- 🔑 支持学号密码全自动登录，token 过期自动换新，无需手工维护
- 📍 定位校验预检：坐标不在校区内会明确报错，不会乱点

## 快速开始（3 步）

### 第 1 步 · 拿到代码

```bash
git clone https://github.com/cccccheyu/fzu-auto-checkin.git
cd fzu-auto-checkin
pip install -r requirements.txt
```

### 第 2 步 · 填配置

复制模板为 `config.yaml`（此文件已被 .gitignore 忽略，不会被提交）：

```bash
cp config.example.yaml config.yaml
```

逐项填写（每项怎么填都写在模板注释里）：

| 配置项 | 填什么 | 怎么获取 |
|--------|--------|----------|
| `user.username` / `user.password` | **登录智汇福大 App 的学号和密码**（推荐，全自动免维护） | 你平时登 App 用的那套 |
| `user.token` | 免登 token（可选项，与账密二选一即可） | 见 [docs/protocol.md](docs/protocol.md) §4 |
| `checkin.longitude` / `latitude` | 你在校区内宿舍楼的坐标 | 打开[高德坐标拾取器](https://lbs.amap.com/tools/picker) → 搜索你的宿舍楼 → 复制"经度,纬度" |
| `checkin.actual_location` | 打卡上报的地址文案 | 如「福州大学旗山校区生活区X号楼」 |
| `notify.*` | 推送渠道（填一种即可） | [Server酱](https://sct.ftqq.com) / [PushPlus](https://www.pushplus.plus) 注册即得 key |

### 第 3 步 · 跑起来

**先本地试一次**（确认配置没问题）：

```bash
python main.py
```

输出「已签到 / 无需操作」或「签到成功」即为配置正确。

**然后挂到 GitHub Actions 云端自动跑**（推荐）：

1. 在 GitHub 上 Fork 本仓库，或新建一个 **私有仓库** 推送这份代码
2. 仓库 `Settings → Secrets and variables → Actions → New repository secret`，名称填 `CONFIG_YAML`，值 = 你本地的 `config.yaml` 全文
3. 完成。每天北京时间 21:35 / 21:50 自动执行，结果推送到微信

> 💡 为什么推荐私有仓库：你的凭据只通过 Secret 注入，不进代码库；Actions 免费额度对私有库也够用（每天跑一次绰绰有余）。

## 常见问题

<details>
<summary><b>token 是什么？会过期吗？</b></summary>

登录态凭证。**推荐直接填学号密码**：脚本会自动登录换 token 并回写配置，全程无感。只有不想存密码的人才需要手动获取 token（过期后重新取一次即可）。
</details>

<details>
<summary><b>迟到线是几点？</b></summary>

**22:30**。21:30–22:30 打卡为正常，22:30–23:59 打卡记迟到。定时任务设在 21:35/21:50，正常情况下不会迟到。
</details>

<details>
<summary><b>运行报「服务器暂未返回今日计划」？</b></summary>

跨午夜时段（约 0:00–1:00）服务器尚未发布当日计划，会返回 500，属正常现象，稍后再试即可。定时任务设在签到窗口内，不受影响。
</details>

<details>
<summary><b>寒暑假怎么办？学期中间有不用签到的时段呢？</b></summary>

配置里的 `vacation.skip_ranges` 是**通用的**，任何人都可以按需插入自己的免签时间段（模板已预填官方校历的寒假 1.23–2.21、暑假 7.3–8.29，出处《福州大学 2026—2027 学年校历》）。学期中间加一条即可，比如离校参加比赛一周：

```yaml
vacation:
  notify: false
  skip_ranges:
    # ...已有的区间不动，往下追加：
    - name: 比赛离校
      start: "2026-11-02"
      end: "2026-11-08"
```

区间内脚本**不签、不推、不留记录**，Actions 照常跑但等于空转；区间结束自动恢复签到。新学年校历发布后更新已有区间的日期即可。注意：用 CONFIG_YAML secret 的用户直接改 secret 内容，改完无需提交任何代码。
</details>

<details>
<summary><b>人不在学校会怎样？</b></summary>

脚本不做真实定位——这是特性也是红线：**请在本人确实在校时使用**。长期离校（实习、交换等）请走辅导员报备请假，名正言顺。
</details>

<details>
<summary><b>iOS 用户能用吗？</b></summary>

能，而且是最省事的用法：脚本跑在 GitHub Actions 云端，iPhone 只收微信推送，什么都不用装。
</details>

## 工作原理

晚点名页是一个 H5 页面，认证只靠一个免登 token。本项目通过静态分析其前端代码逆向出完整协议：4 个接口（查状态 / 校时 / 定位校验 / 打卡）+ AES-CBC 参数加密，无需 Frida、无需抓包工具。完整逆向笔记见 [docs/protocol.md](docs/protocol.md)。

另附 v0.1 Android 无障碍脚本（`scripts/autojs_wandianming.js`）：模拟点击方案，不碰接口，供参考。

## 参与贡献

欢迎提 Issue / PR 适配其他学校或系统。提交内容请**脱敏**（密码、学号、token 一律打码）。本项目不接受、不鼓励任何形式的代挂与有偿使用。

## License

MIT
