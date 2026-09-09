/**
 * fzu-auto-checkin v0.1 · 智汇福大晚点名自动签到（Auto.js / Hamibot 无障碍脚本）
 *
 * 控件文案基于 MuMu 模拟器 + uiautomator dump 实测（2026-09-09，v1.17.3）：
 *   - 导航：底部 tab「业务」→ 顶部 tab「晚点名签到」
 *   - 页面状态：`未签到` / `已签到`；按钮：`晚点打卡`
 *   - 不在范围：出现 `无法签到` + `不在签到范围内`（可签到校区：旗山校区）
 *   - 签到时段：21:30 - 23:59
 *
 * 用法：
 *   1. Android 手机安装 Auto.js（或 Hamibot），开启无障碍服务。
 *   2. 安装智汇福大 App 并保持已登录状态（登录态长期有效）。
 *   3. 定时在 21:30-23:59 时段内运行本脚本；脚本不伪造 GPS，
 *      需要人真的在旗山校区范围内（定位由系统真实上报）。
 */

// ============ 可配置区 ============
const CONFIG = {
    appPackage: "cn.edu.fzu.fdxypa",   // 智汇福大包名
    homeTabDesc: "业务",               // 首页底部第 4 个 tab（desc 前缀）
    entryDesc: "晚点名签到",           // 业务页顶部 tab
    pageReadyText: "签到时段",         // 晚点名页加载完成标志（页面含"签到时段：21:30 -23:59"）
    checkinBtnText: "晚点打卡",        // 签到按钮
    outOfRangeText: "无法签到",        // 不在签到范围时的状态文案
    doneText: "已签到",                // 已完成状态
    waitTimeout: 20000,                // 各步骤最长等待（毫秒）
};

// ============ 工具函数 ============
function waitFor(selectorFactory, timeout) {
    const end = Date.now() + timeout;
    while (Date.now() < end) {
        const w = selectorFactory();
        if (w) return w;
        sleep(500);
    }
    return null;
}

function clickCenter(w) {
    const b = w.bounds();
    return click(b.centerX(), b.centerY());
}

function findFirst(factories) {
    for (let i = 0; i < factories.length; i++) {
        const w = factories[i]();
        if (w) return { widget: w, index: i };
    }
    return null;
}

// ============ 主流程 ============
function main() {
    if (!launch(CONFIG.appPackage)) {
        throw new Error("无法启动智汇福大，请确认已安装并登录");
    }
    sleep(4000); // 等首页加载

    // 1. 切到底部「业务」tab
    const bizTab = waitFor(
        () => descStartsWith(CONFIG.homeTabDesc).findOnce(),
        CONFIG.waitTimeout
    );
    if (!bizTab) throw new Error("未找到底部「业务」tab");
    clickCenter(bizTab);
    sleep(2000);

    // 2. 进入顶部「晚点名签到」tab（若已在晚点名页会直接命中 pageReady，跳过）
    if (!textContains(CONFIG.pageReadyText).findOnce()) {
        const entry = waitFor(
            () => descContains(CONFIG.entryDesc).findOnce(),
            CONFIG.waitTimeout
        );
        if (!entry) throw new Error("未找到「晚点名签到」入口");
        clickCenter(entry);

        // 3. 等晚点名 H5 页面加载完成
        const ready = waitFor(
            () => textContains(CONFIG.pageReadyText).findOnce(),
            CONFIG.waitTimeout
        );
        if (!ready) throw new Error("晚点名页面加载超时");
    }

    // 4. 判断当前状态并执行
    if (text(CONFIG.doneText).findOnce()) {
        toastLog("今日已签到，无需操作 ✅");
        return;
    }
    if (text(CONFIG.outOfRangeText).findOnce()) {
        const loc = textStartsWith("当前定位").findOnce();
        throw new Error(
            "不在签到范围内（" + (loc ? loc.text() : "定位未知") + "），脚本不伪造 GPS"
        );
    }

    const btn = waitFor(
        () => {
            const w = text(CONFIG.checkinBtnText).findOnce();
            return w && w.enabled() ? w : null;
        },
        CONFIG.waitTimeout
    );
    if (!btn) throw new Error("未找到可点击的「" + CONFIG.checkinBtnText + "」按钮");

    clickCenter(btn);
    sleep(3000);

    // 5. 结果确认
    const done = waitFor(
        () => text(CONFIG.doneText).findOnce(),
        CONFIG.waitTimeout
    );
    if (done) {
        toastLog("晚点名签到成功 ✅");
    } else {
        toastLog("已点击打卡，但结果未确认，请手动检查 ❌");
    }
}

try {
    // 无障碍服务就绪检查
    if (!auto.service) {
        auto.waitFor();
    }
    main();
} catch (e) {
    toastLog("执行失败：" + e.message);
}
