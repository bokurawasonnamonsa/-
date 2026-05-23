#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Patch player.html for onboarding v3 (UTF-8 safe)."""
from pathlib import Path
import re

P = Path(__file__).resolve().parents[1] / "player.html"
t = P.read_text(encoding="utf-8")

CSS = """
        .mode-pick-wrap { display: flex; flex-direction: column; gap: 10px; margin-bottom: 14px; width: 100%; }
        .mode-pick-hint { font-size: 12px; color: #ABB2BF; margin: 0 0 6px 0; line-height: 1.5; text-align: center; }
        .mode-card {
            width: 100%; box-sizing: border-box; border: 2px solid #3E4451; border-radius: 10px;
            padding: 14px 16px; background: #1E2227; cursor: pointer; text-align: left;
            min-height: 48px; font-family: inherit;
        }
        .mode-card-prod.selected { border-color: #E5C07B; background: rgba(229, 192, 123, 0.1); }
        .mode-card-drill.selected { border-color: #C678DD; background: rgba(198, 120, 221, 0.12); }
        .mode-card-title { font-size: 17px; font-weight: bold; margin: 0 0 6px 0; display: block; }
        .mode-card-prod .mode-card-title { color: #E5C07B; }
        .mode-card-drill .mode-card-title { color: #C678DD; }
        .mode-card-sub { font-size: 13px; color: #ABB2BF; line-height: 1.45; margin: 0; }
        .env-btn-selected { box-shadow: 0 0 0 2px #61AFEF; }
        .one-device-banner { background: #1E2227; border: 1px solid #E06C75; border-radius: 8px; padding: 10px 12px; margin-bottom: 12px; font-size: 13px; line-height: 1.5; text-align: left; color: #ABB2BF; }
        .field-error { color: #E06C75; font-size: 12px; margin: 2px 0 6px 0; text-align: left; min-height: 14px; }
        .field-error-global { color: #E06C75; font-size: 13px; margin: 8px 0; padding: 8px; background: rgba(224,108,117,0.1); border-radius: 6px; text-align: left; display: none; }
        .input-error { border: 1px solid #E06C75 !important; }
        .quick-start-panel { background: #1E2227; border: 2px solid #98C379; border-radius: 10px; padding: 14px; margin-bottom: 14px; text-align: left; }
        .quick-start-panel .qs-title { color: #98C379; font-weight: bold; font-size: 15px; margin-bottom: 8px; }
        .quick-start-panel .qs-summary { color: #ABB2BF; font-size: 13px; line-height: 1.5; margin-bottom: 12px; }
        .quick-start-actions { display: flex; flex-direction: column; gap: 8px; }
        .btn-quick-start { background: #98C379; color: #1E2227; padding: 14px; border: none; border-radius: 8px; font-weight: bold; font-size: 16px; cursor: pointer; width: 100%; }
        .btn-quick-change { background: #3E4451; color: #ABB2BF; padding: 10px; border: none; border-radius: 8px; font-size: 14px; cursor: pointer; width: 100%; }
        .chrome-notice-collapsed { display: none !important; }
        .chrome-notice-mini { font-size: 12px; color: #ABB2BF; margin-bottom: 12px; text-align: center; }
        .chrome-notice-mini button { background: transparent; border: none; color: #61AFEF; text-decoration: underline; cursor: pointer; font-size: 12px; }
        #drillTabCreate, #drillTabJoin { min-height: 48px; font-size: 15px; }
"""

if ".mode-pick-wrap" not in t:
    t = t.replace(
        "        .btn-back { background: #3E4451;",
        CSS + "\n        .btn-back { background: #3E4451;",
        1,
    )

STEP1_NEW = """    <div id="quickStartPanel" class="quick-start-panel card" style="display:none;">
        <motion class="qs-title">おかえりなさい</div>
        <div id="quickStartSummary" class="qs-summary"></div>
        <div class="quick-start-actions">
            <button type="button" class="btn-quick-start" onclick="quickStartContinue()">そのまま開始</button>
            <button type="button" class="btn-quick-change" onclick="quickStartChangeSettings()">設定を変える</button>
        </div>
    </div>

    <div id="step1_intro" class="card">
        <p class="mode-pick-hint">どちらで使いますか？<br>※普段は「同盟の練習」、SVSの日は下を選択</p>
        <div class="mode-pick-wrap">
            <button type="button" id="btnModeDrill" class="mode-card mode-card-drill selected" onclick="selectAppMode('drill')">
                <span class="mode-card-title">同盟の練習</span>
                <p class="mode-card-sub">自同盟だけの部屋。普段の打ち合わせ・訓練用</p>
            </button>
            <button type="button" id="btnModeProd" class="mode-card mode-card-prod" onclick="selectAppMode('prod')">
                <span class="mode-card-title">SVS（3301全体）</span>
                <p class="mode-card-sub">4週に1回のサーバー対抗戦。全同盟が同じ戦場で使用</p>
            </button>
        </div>
        <p id="chromeNoticeMini" class="chrome-notice-mini chrome-notice-collapsed">ブラウザはChrome等で開いてください。<button type="button" onclick="showChromeNoticeFull()">注意を表示</button></p>
        <div id="chromeNoticeFull" style="border: 2px solid #E06C75; background: rgba(224, 108, 117, 0.1); padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: left; box-sizing: border-box; width: 100%;">
            <div style="color: #E06C75; font-size: 16px; font-weight: bold; margin-bottom: 8px; text-align: center;">⚠️ 必ずGoogle Chromeなどの<br>ブラウザーで開いて下さい！</div>
            <motion style="color: #ABB2BF; font-size: 13px; line-height: 1.5; margin-bottom: 15px;">Discordなどのアプリ上で開くと上手くツールが機能しません。また、設定も初期設定に戻ってしまう為、必ずブラウザーを使用して下さい。</div>
            <div style="display: flex; align-items: center; background: #1E2227; border: 1px solid #3E4451; border-radius: 6px; padding: 5px; width: 100%; box-sizing: border-box;">
                <input type="text" id="shareUrlInput" readonly style="flex: 1; background: transparent; border: none; color: #61AFEF; font-size: 12px; padding: 5px; outline: none; width: 100%; min-width: 0;">
                <button onclick="copyShareUrl()" style="background: #61AFEF; color: white; border: none; border-radius: 4px; padding: 8px 12px; font-weight: bold; font-size: 12px; cursor: pointer; white-space: nowrap; margin-left: 5px;">コピー</button>
            </div>
        </div>

        <h2 style="color: #61AFEF; margin-top:0;">ご利用環境の確認</h2>
        <p style="font-size: 16px; margin-top: 15px;">ゲーム画面とこのツールを<br><span style="color:#E5C07B; font-weight:bold;">別々の端末（スマホとPC等）</span><br>で同時に開くことはできますか？</p>
        <button id="btnEnv2device" class="role-btn inactive" style="background:#4CAF50; color:white;" onclick="selectEnv('2device')">💻 はい（別端末で開ける）</button>
        <button id="btnEnv1device" class="role-btn inactive" style="background:#E06C75; color:white;" onclick="selectEnv('1device')">📱 いいえ（スマホ1台のみ）</button>
    </div>
"""
STEP1_NEW = STEP1_NEW.replace("<motion ", "<motion ").replace("<motion ", "<div ").replace("</motion>", "</div>")
# fix botched replace - only opening tags
STEP1_NEW = STEP1_NEW.replace("<motion ", "<motion ")
while "<motion " in STEP1_NEW:
    STEP1_NEW = STEP1_NEW.replace("<motion ", "<div ", 1)
while "</motion>" in STEP1_NEW:
    STEP1_NEW = STEP1_NEW.replace("</motion>", "</motion>")

# simpler: build STEP1_NEW without typos
STEP1_NEW = """    <div id="quickStartPanel" class="quick-start-panel card" style="display:none;">
        <div class="qs-title">おかえりなさい</div>
        <motion id="quickStartSummary" class="qs-summary"></div>
        <div class="quick-start-actions">
            <button type="button" class="btn-quick-start" onclick="quickStartContinue()">そのまま開始</button>
            <button type="button" class="btn-quick-change" onclick="quickStartChangeSettings()">設定を変える</button>
        </div>
    </div>

    <div id="step1_intro" class="card">
        <p class="mode-pick-hint">どちらで使いますか？<br>※普段は「同盟の練習」、SVSの日は下を選択</p>
        <div class="mode-pick-wrap">
            <button type="button" id="btnModeDrill" class="mode-card mode-card-drill selected" onclick="selectAppMode('drill')">
                <span class="mode-card-title">同盟の練習</span>
                <p class="mode-card-sub">自同盟だけの部屋。普段の打ち合わせ・訓練用</p>
            </button>
            <button type="button" id="btnModeProd" class="mode-card mode-card-prod" onclick="selectAppMode('prod')">
                <span class="mode-card-title">SVS（3301全体）</span>
                <p class="mode-card-sub">4週に1回のサーバー対抗戦。全同盟が同じ戦場で使用</p>
            </button>
        </div>
        <p id="chromeNoticeMini" class="chrome-notice-mini chrome-notice-collapsed">ブラウザはChrome等で開いてください。<button type="button" onclick="showChromeNoticeFull()">注意を表示</button></p>
        <div id="chromeNoticeFull" style="border: 2px solid #E06C75; background: rgba(224, 108, 117, 0.1); padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: left; box-sizing: border-box; width: 100%;">
            <div style="color: #E06C75; font-size: 16px; font-weight: bold; margin-bottom: 8px; text-align: center;">⚠️ 必ずGoogle Chromeなどの<br>ブラウザーで開いて下さい！</div>
            <div style="color: #ABB2BF; font-size: 13px; line-height: 1.5; margin-bottom: 15px;">Discordなどのアプリ上で開くと上手くツールが機能しません。また、設定も初期設定に戻ってしまう為、必ずブラウザーを使用して下さい。</motion>
            <div style="display: flex; align-items: center; background: #1E2227; border: 1px solid #3E4451; border-radius: 6px; padding: 5px; width: 100%; box-sizing: border-box;">
                <input type="text" id="shareUrlInput" readonly style="flex: 1; background: transparent; border: none; color: #61AFEF; font-size: 12px; padding: 5px; outline: none; width: 100%; min-width: 0;">
                <button onclick="copyShareUrl()" style="background: #61AFEF; color: white; border: none; border-radius: 4px; padding: 8px 12px; font-weight: bold; font-size: 12px; cursor: pointer; white-space: nowrap; margin-left: 5px;">コピー</button>
            </div>
        </div>

        <h2 style="color: #61AFEF; margin-top:0;">ご利用環境の確認</h2>
        <p style="font-size: 16px; margin-top: 15px;">ゲーム画面とこのツールを<br><span style="color:#E5C07B; font-weight:bold;">別々の端末（スマホとPC等）</span><br>で同時に開くことはできますか？</p>
        <button id="btnEnv2device" class="role-btn inactive" style="background:#4CAF50; color:white;" onclick="selectEnv('2device')">💻 はい（別端末で開ける）</button>
        <button id="btnEnv1device" class="role-btn inactive" style="background:#E06C75; color:white;" onclick="selectEnv('1device')">📱 いいえ（スマホ1台のみ）</button>
    </div>
"""
STEP1_NEW = STEP1_NEW.replace("<motion ", "<div ").replace("</motion>", "</div>")

pat = re.compile(r"    <div id=\"step1_intro\" class=\"card\">.*?    </motion>\n\n    <div id=\"step2_sync\"", re.S)
if not pat.search(t):
    pat = re.compile(r"    <div id=\"step1_intro\" class=\"card\">.*?    </div>\n\n    <div id=\"step2_sync\"", re.S)
t, n = pat.subn(STEP1_NEW + "\n\n    <div id=\"step2_sync\" style=\"display:none !important;\"", t, count=1)
print("step1 replaced", n)

# Merge step3 into step2_5
JOIN_NEW = """    <div id="step2_5_alliance" class="card" style="display:none;">
        <h3 id="allianceStepTitle" style="margin-top:0;">参加する同盟を選ぶ</h3>
        <div id="oneDeviceClockBanner" class="one-device-banner" style="display:none;">
            <b style="color:#E06C75;">スマホ1台:</b> 上部の日本時間と手元の時計を<b style="color:#98C379;">秒まで</b>合わせてから登録してください。
        </div>
        <div id="onboardingFormError" class="field-error-global"></motion>
        <div id="drillConfigArea" style="display:none; background:#1E2227; border:1px solid #3E4451; border-radius:8px; padding:10px; margin-bottom:10px; text-align:left;">
            <div style="font-size:12px; color:#ABB2BF; margin-bottom:6px;">同盟内の練習（ルーム作成・参加）</div>
            <div style="display:flex; gap:8px; margin-bottom:8px;">
                <button id="drillTabCreate" class="btn-green" style="flex:1; padding:8px; border-radius:6px;" onclick="setDrillTab('create')">新規作成</button>
                <button id="drillTabJoin" class="btn-gray" style="flex:1; padding:8px; border-radius:6px;" onclick="setDrillTab('join')">ルーム参加</button>
            </div>
            <div id="drillCreateArea">
                <input type="text" id="drillAllianceNameInput" placeholder="同盟名（例: MTC練習）" style="width:100%; box-sizing:border-box; margin-bottom:6px; padding:8px; border-radius:6px; border:1px solid #3E4451; background:#181A1F; color:white;">
                <div id="errDrillAllianceName" class="field-error"></div>
                <input type="text" id="drillRoomKeyInput" placeholder="参加コード（同盟内共有）" style="width:100%; box-sizing:border-box; margin-bottom:6px; padding:8px; border-radius:6px; border:1px solid #3E4451; background:#181A1F; color:white;">
                <div id="errDrillRoomKey" class="field-error"></div>
                <button class="btn-green" style="width:100%; padding:8px; border-radius:6px;" onclick="createDrillRoom()">作成して入る</button>
            </div>
            <div id="drillJoinArea" style="display:none;">
                <select id="drillRoomSelect" onchange="selectedDrillRoomId=this.value" style="width:100%; box-sizing:border-box; margin-bottom:6px; padding:8px; border-radius:6px; border:1px solid #3E4451; background:#181A1F; color:white;"></select>
                <div id="errDrillRoomSelect" class="field-error"></div>
                <input type="text" id="drillJoinCodeInput" placeholder="参加コード（参講から共有）" style="width:100%; box-sizing:border-box; margin-bottom:6px; padding:8px; border-radius:6px; border:1px solid #3E4451; background:#181A1F; color:white;">
                <motion id="errDrillJoinCode" class="field-error"></div>
                <button class="btn-gray" style="width:100%; padding:8px; border-radius:6px;" onclick="joinDrillRoom()">選択ルームに参加</button>
            </div>
            <div id="drillStatusMsg" style="min-height:18px; margin-top:6px; font-size:12px; color:#98C379;"></div>
        </div>
        <div id="prodAlliancePick">
        <button id="btnAln0" class="role-btn inactive" onclick="selectAlliance(0)">同盟1</button>
        <button id="btnAln1" class="role-btn inactive" onclick="selectAlliance(1)">同盟2</button>
        <button id="btnAln2" class="role-btn inactive" onclick="selectAlliance(2)">同盟3</button>
        </div>
        <div id="roleSetupSection" style="display:none; margin-top:14px; padding-top:14px; border-top:1px solid #3E4451;">
        <motion id="allianceDisplay" style="color: #98C379; font-weight: bold; margin-bottom: 15px; font-size: 18px;"></div>
        <h3 style="margin-top:0;">役割を選択</h3>
        <button id="btnStaff" class="role-btn inactive" onclick="setRole('staff')" style="background:#E5C07B; color:#282C34;">参謀（同盟内の集結指示）</button>
        <button id="btnLeader1" class="role-btn inactive" onclick="setRole('leader1')">集結主 (第1班)</button>
        <button id="btnLeader2" class="role-btn inactive" onclick="setRole('leader2')">集結主 (第2班)</button>
        <button id="btnRider" class="role-btn inactive" onclick="setRole('rider')">乗り手</button>
        <div id="staffPlayerRoleArea" style="display:none; background:#1E2227; border:1px solid #3E4451; border-radius:10px; padding:10px; margin:10px 0;">
            <div id="staffRoleHint" style="font-size:13px; color:#E5C07B; margin-bottom:8px; font-weight:bold;">次: 担当する班を選んでください</div>
            <div style="display:flex; gap:8px; flex-wrap:wrap; justify-content:center;">
                <button id="btnStaffLeader1" class="btn-gray" style="padding:8px 12px; min-height:44px;" onclick="setStaffPlayerRole('leader1')">第1班 集結主</button>
                <button id="btnStaffLeader2" class="btn-gray" style="padding:8px 12px; min-height:44px;" onclick="setStaffPlayerRole('leader2')">第2班 集結主</button>
                <button id="btnStaffRider" class="btn-gray" style="padding:8px 12px; min-height:44px;" onclick="setStaffPlayerRole('rider')">乗り手</button>
            </div>
        </div>
        <motion id="inputsArea" style="display:none;">
            <div class="input-group">
                <input type="text" id="pName" placeholder="名前を入力" style="width:80%; display:none;">
                <motion id="errPName" class="field-error"></div>
                <div style="color:#61AFEF; font-weight:bold; margin-top:5px;">行軍時間を入力</div>
                <div>
                    <input type="number" id="pMin" value="0" style="width:50px;"> 分 
                    <input type="number" id="pSec" value="30" style="width:50px;"> 秒
                </div>
                <div style="font-size: 12px; color: #E5C07B; font-weight: bold; margin-top: 5px;">※王城戦開始21:00～に入力して下さい。</div>
            </div>
            <button class="role-btn active" onclick="register()">登録して開始</button>
        </div>
        <div id="errRole" class="field-error" style="text-align:center;"></div>
        </div>
        <button class="btn-back" onclick="goBackToEnv()">◀ ひとつ前に戻る</button>
    </div>

    <div id="step3_setup" class="card" style="display:none !important;"></div>
"""
JOIN_NEW = JOIN_NEW.replace("<motion ", "<motion ").replace("<motion ", "<div ")
JOIN_NEW = JOIN_NEW.replace("<motion ", "<motion ")
# clean motion tags
JOIN_NEW = JOIN_NEW.replace("<motion ", "<div ").replace("</motion>", "</div>")
JOIN_NEW = JOIN_NEW.replace("参謀から", "参謀から")  # fix typo 参謀
JOIN_NEW = JOIN_NEW.replace("参謀から", "参謀から")

pat2 = re.compile(
    r'    <div id="step2_5_alliance" class="card".*?</div>\n\n    <div id="step3_setup" class="card".*?</motion>\n\n    <div id="clockContainer"',
    re.S,
)
if not pat2.search(t):
    pat2 = re.compile(
        r'    <motion id="step2_5_alliance".*?</motion>\n\n    <motion id="step3_setup".*?</motion>\n\n    <div id="clockContainer"',
        re.S,
    )
if not pat2.search(t):
    pat2 = re.compile(
        r'    <div id="step2_5_alliance" class="card" style="display:none;">.*?    <div id="step3_setup" class="card" style="display:none;">.*?    </div>\n\n    <div id="clockContainer"',
        re.S,
    )
t, n2 = pat2.subn(JOIN_NEW + "\n\n    <div id=\"clockContainer\"", t, count=1)
print("join merged", n2)

ONBOARDING_JS = r'''
    function clearOnboardingErrors() {
        document.querySelectorAll(".field-error").forEach(el => { el.textContent = ""; });
        document.querySelectorAll(".input-error").forEach(el => el.classList.remove("input-error"));
        const g = document.getElementById("onboardingFormError");
        if (g) { g.style.display = "none"; g.textContent = ""; }
    }
    function showFieldError(fieldId, errId, message) {
        const f = document.getElementById(fieldId);
        const e = document.getElementById(errId);
        if (e) e.textContent = message || "";
        if (f) f.classList.toggle("input-error", !!message);
        return !message;
    }
    function showOnboardingGlobal(message) {
        const g = document.getElementById("onboardingFormError");
        if (!g) return;
        if (message) { g.style.display = "block"; g.textContent = message; }
        else { g.style.display = "none"; g.textContent = ""; }
    }
    function applyChromeNoticeState() {
        const seen = localStorage.getItem("utc_chrome_notice_seen") === "1";
        const full = document.getElementById("chromeNoticeFull");
        const mini = document.getElementById("chromeNoticeMini");
        if (full) full.classList.toggle("chrome-notice-collapsed", seen);
        if (mini) mini.classList.toggle("chrome-notice-collapsed", !seen);
    }
    function showChromeNoticeFull() {
        const full = document.getElementById("chromeNoticeFull");
        const mini = document.getElementById("chromeNoticeMini");
        if (full) full.classList.remove("chrome-notice-collapsed");
        if (mini) mini.classList.add("chrome-notice-collapsed");
    }
    function markChromeNoticeSeen() {
        localStorage.setItem("utc_chrome_notice_seen", "1");
        applyChromeNoticeState();
    }
    function updateEnvButtonStyles() {
        const b2 = document.getElementById("btnEnv2device");
        const b1 = document.getElementById("btnEnv1device");
        if (b2) b2.classList.toggle("env-btn-selected", deviceMode === "2device");
        if (b1) b1.classList.toggle("env-btn-selected", deviceMode === "1device");
    }
    function updateOneDeviceBanner() {
        const banner = document.getElementById("oneDeviceClockBanner");
        const topClock = document.getElementById("topClockArea");
        const clock = document.getElementById("clockContainer");
        if (deviceMode === "1device") {
            if (banner) banner.style.display = "block";
            if (topClock && clock && clock.parentElement !== topClock) topClock.appendChild(clock);
            if (clock) clock.style.display = "flex";
        } else {
            if (banner) banner.style.display = "none";
            if (clock) clock.style.display = "none";
        }
    }
    function showRoleSetupSection() {
        const sec = document.getElementById("roleSetupSection");
        if (sec) {
            sec.style.display = "block";
            sec.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
    }
    function hideRoleSetupSection() {
        const sec = document.getElementById("roleSetupSection");
        if (sec) sec.style.display = "none";
    }
    function goToJoinStep() {
        hideAllSteps();
        document.getElementById("step2_5_alliance").style.display = "block";
        updateOneDeviceBanner();
        updateJoinBackLabel();
    }
    function updateJoinBackLabel() {
        const back = document.querySelector("#step2_5_alliance .btn-back");
        if (back) back.textContent = "◀ モード・端末の選択に戻る";
    }
    function tryAutoAdvanceFromIntro() {
        if (!appMode || !deviceMode) return;
        markChromeNoticeSeen();
        setTimeout(goToJoinStep, 80);
    }
    function roleLabel(role) {
        if (role === "leader1") return "第1班 集結主";
        if (role === "leader2") return "第2班 集結主";
        if (role === "rider") return "乗り手";
        if (role === "staff") return "参謀";
        return role || "";
    }
    function canQuickStart() {
        const role = localStorage.getItem("utc_last_role");
        const dm = localStorage.getItem("utc_device_mode");
        if (!role || !dm || (dm !== "1device" && dm !== "2device")) return false;
        if (appMode === "drill") {
            const rk = localStorage.getItem("utc_drill_room_key");
            const jc = localStorage.getItem("utc_drill_join_code");
            if (!rk || rk === "default" || !jc) return false;
        }
        if (appMode === "prod") {
            const ai = localStorage.getItem("utc_last_alliance_idx");
            if (ai === null || ai === "") return false;
        }
        if ((role.startsWith("leader") || localStorage.getItem("utc_is_staff_commander") === "1") && !localStorage.getItem("utc_my_name")) return false;
        return true;
    }
    function buildQuickStartSummary() {
        const mode = appMode === "drill" ? "同盟の練習" : "SVS";
        const dm = deviceMode === "1device" ? "スマホ1台" : "別端末";
        let extra = "";
        if (appMode === "prod" && localStorage.getItem("utc_last_alliance_idx") !== null) {
            const idx = parseInt(localStorage.getItem("utc_last_alliance_idx"), 10);
            const names = localState && localState.alliance_names ? localState.alliance_names : [];
            extra = names[idx] || `同盟${idx + 1}`;
        } else if (appMode === "drill") {
            extra = localStorage.getItem("utc_drill_alliance_name") || "練習ルーム";
        }
        const role = roleLabel(lastRegisteredRole || localStorage.getItem("utc_last_role") || "");
        return `${mode} / ${dm}${extra ? " / " + extra : ""} / ${role}`;
    }
    function refreshQuickStartPanel() {
        const panel = document.getElementById("quickStartPanel");
        const intro = document.getElementById("step1_intro");
        const join = document.getElementById("step2_5_alliance");
        if (!panel) return;
        if (canQuickStart() && join && join.style.display === "none" && intro && intro.style.display !== "none") {
            document.getElementById("quickStartSummary").textContent = "前回: " + buildQuickStartSummary();
            panel.style.display = "block";
            intro.style.display = "none";
        } else if (!document.getElementById("display") || document.getElementById("display").style.display === "none") {
            panel.style.display = "none";
            if (intro && !deviceMode) intro.style.display = "block";
        }
    }
    function quickStartChangeSettings() {
        document.getElementById("quickStartPanel").style.display = "none";
        hideRoleSetupSection();
        hideAllSteps();
        document.getElementById("step1_intro").style.display = "block";
    }
    function quickStartContinue() {
        clearOnboardingErrors();
        deviceMode = localStorage.getItem("utc_device_mode") || "2device";
        const ai = localStorage.getItem("utc_last_alliance_idx");
        if (ai !== null && ai !== "") myAllianceIdx = parseInt(ai, 10);
        drillRoomKey = localStorage.getItem("utc_drill_room_key") || drillRoomKey;
        drillJoinCode = localStorage.getItem("utc_drill_join_code") || "";
        drillAllianceName = localStorage.getItem("utc_drill_alliance_name") || "";
        isStaffCommander = localStorage.getItem("utc_is_staff_commander") === "1";
        const lr = localStorage.getItem("utc_last_role") || "";
        if (isStaffCommander) { staffPlayerRole = lr; myRole = lr; }
        else { myRole = lr; staffPlayerRole = null; }
        const sn = localStorage.getItem("utc_my_name") || "";
        if (sn) document.getElementById("pName").value = sn;
        if (!ws || ws.readyState !== WebSocket.OPEN) connect();
        const tryReg = () => {
            if (!ws || ws.readyState !== WebSocket.OPEN) { setTimeout(tryReg, 200); return; }
            register();
        };
        tryReg();
    }
'''

if "function clearOnboardingErrors" not in t:
    t = t.replace("    function hideAllSteps() {", ONBOARDING_JS + "\n    function hideAllSteps() {", 1)

# Patch hideAllSteps
t = t.replace(
    "        document.getElementById('step3_setup').style.display = 'none';",
    "        hideRoleSetupSection();\n        const s3 = document.getElementById('step3_setup'); if (s3) s3.style.display = 'none';",
    1,
)

t = t.replace(
    "    function goBackToEnv() { hideAllSteps(); if (deviceMode === '1device') document.getElementById('step2_sync').style.display = 'block'; else document.getElementById('step1_intro').style.display = 'block'; }",
    "    function goBackToEnv() { hideAllSteps(); hideRoleSetupSection(); document.getElementById('step1_intro').style.display = 'block'; }",
    1,
)

t = t.replace(
    "    function openEditMode() { hideAllSteps(); document.getElementById('step3_setup').style.display = 'block'; stopStaffPanelTicker(); }",
    "    function openEditMode() { hideAllSteps(); goToJoinStep(); showRoleSetupSection(); stopStaffPanelTicker(); }",
    1,
)

# selectAppMode
OLD_SELECT_MODE = """    function selectAppMode(mode) {
        appMode = (mode === "drill") ? "drill" : "prod";
        localStorage.setItem("utc_app_mode", appMode);
        const prodBtn = document.getElementById("btnModeProd");
        const drillBtn = document.getElementById("btnModeDrill");
        if (prodBtn) prodBtn.className = appMode === "prod" ? "btn-green" : "btn-gray";
        if (drillBtn) drillBtn.className = appMode === "drill" ? "btn-green" : "btn-gray";
        const drillCfg = document.getElementById("drillConfigArea");
        if (drillCfg) drillCfg.style.display = appMode === "drill" ? "block" : "none";
        const b1 = document.getElementById("btnAln1");
        const b2 = document.getElementById("btnAln2");
        const b0 = document.getElementById("btnAln0");
        if (b1) b1.style.display = appMode === "drill" ? "none" : "block";
        if (b2) b2.style.display = appMode === "drill" ? "none" : "block";
        if (b0) b0.style.display = appMode === "drill" ? "none" : "block";
        const titleEl = document.getElementById("allianceStepTitle");
        if (titleEl) titleEl.innerText = appMode === "drill" ? "訓練ルームに参加" : "SVS参加する同盟の選択";
        const badge = document.getElementById("modeBadge");
        if (badge) {
            badge.innerText = appMode === "drill" ? "【訓練】" : "【本番】";
            badge.style.background = appMode === "drill" ? "#C678DD" : "#3E4451";
            badge.style.color = appMode === "drill" ? "#1E2227" : "#ABB2BF";
        }"""

NEW_SELECT_MODE = """    function selectAppMode(mode) {
        appMode = (mode === "drill") ? "drill" : "prod";
        localStorage.setItem("utc_app_mode", appMode);
        const prodBtn = document.getElementById("btnModeProd");
        const drillBtn = document.getElementById("btnModeDrill");
        if (prodBtn) prodBtn.classList.toggle("selected", appMode === "prod");
        if (drillBtn) drillBtn.classList.toggle("selected", appMode === "drill");
        const drillCfg = document.getElementById("drillConfigArea");
        if (drillCfg) drillCfg.style.display = appMode === "drill" ? "block" : "none";
        const prodPick = document.getElementById("prodAlliancePick");
        if (prodPick) prodPick.style.display = appMode === "drill" ? "none" : "block";
        hideRoleSetupSection();
        const titleEl = document.getElementById("allianceStepTitle");
        if (titleEl) titleEl.innerText = appMode === "drill" ? "同盟の練習ルームに参加" : "参加する同盟を選ぶ";
        const badge = document.getElementById("modeBadge");
        if (badge) {
            badge.innerText = appMode === "drill" ? "同盟練習" : "SVS";
            badge.style.background = appMode === "drill" ? "#C678DD" : "#3E4451";
            badge.style.color = appMode === "drill" ? "#1E2227" : "#ABB2BF";
        }"""

if OLD_SELECT_MODE in t:
    t = t.replace(OLD_SELECT_MODE, NEW_SELECT_MODE, 1)

# selectEnv
t = t.replace(
    """    function selectEnv(mode) {
        deviceMode = mode;
        hideAllSteps();
        if (mode === '1device') {
            document.getElementById('topClockArea').appendChild(document.getElementById('clockContainer'));
            document.getElementById('clockContainer').style.display = 'flex';
            document.getElementById('step2_sync').style.display = 'block';
        } else {
            document.getElementById('step2_5_alliance').style.display = 'block';
        }
    }

    function confirmSync() { hideAllSteps(); document.getElementById('step2_5_alliance').style.display = 'block'; }""",
    """    function selectEnv(mode) {
        deviceMode = mode;
        localStorage.setItem("utc_device_mode", deviceMode);
        updateEnvButtonStyles();
        tryAutoAdvanceFromIntro();
    }

    function confirmSync() { goToJoinStep(); }""",
    1,
)

# selectAlliance
t = t.replace(
    """    function selectAlliance(idx) {
        if (appMode === "drill") {
            idx = 0;
        }
        myAllianceIdx = idx;
        isStaffCommander = false;
        staffPlayerRole = null;
        myRole = null;
        hideAllSteps();
        document.getElementById('step3_setup').style.display = 'block';
        let alnName = (localState && localState.alliance_names[idx]) ? localState.alliance_names[idx] : `同盟 ${idx+1}`;
        document.getElementById('allianceDisplay').innerText = `【 ${alnName} 】`;
        document.getElementById('displayAllianceName').innerText = `【 ${alnName} 】`;
        for(let i=0; i<3; i++) {
            document.getElementById(`btnAln${i}`).className = (i === idx) ? 'role-btn active' : 'role-btn inactive';
        }
        if (appMode === "drill" && ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({cmd: "set_mode", val: {mode: "drill", alliance_id: idx, room_key: drillRoomKey, alliance_name: drillAllianceName}}));
        }
    }""",
    """    function selectAlliance(idx) {
        if (appMode === "drill") idx = 0;
        clearOnboardingErrors();
        myAllianceIdx = idx;
        localStorage.setItem("utc_last_alliance_idx", String(idx));
        isStaffCommander = false;
        staffPlayerRole = null;
        myRole = null;
        document.getElementById('inputsArea').style.display = 'none';
        const staffArea = document.getElementById('staffPlayerRoleArea');
        if (staffArea) staffArea.style.display = 'none';
        let alnName = (localState && localState.alliance_names && localState.alliance_names[idx]) ? localState.alliance_names[idx] : `同盟 ${idx+1}`;
        if (appMode === "drill" && drillAllianceName) alnName = drillAllianceName;
        document.getElementById('allianceDisplay').innerText = `【 ${alnName} 】`;
        document.getElementById('displayAllianceName').innerText = `【 ${alnName} 】`;
        for (let i = 0; i < 3; i++) {
            const btn = document.getElementById(`btnAln${i}`);
            if (btn) btn.className = (i === idx) ? 'role-btn active' : 'role-btn inactive';
        }
        if (appMode === "drill" && ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({cmd: "set_mode", val: {mode: "drill", alliance_id: idx, room_key: drillRoomKey, alliance_name: drillAllianceName}}));
        }
        showRoleSetupSection();
    }""",
    1,
)

# register alerts -> inline
t = t.replace('if (!effectiveRole) return alert("役割を選択してください");', 'if (!effectiveRole) { document.getElementById("errRole").textContent = "役割を選択してください"; return; }')
t = t.replace('if (isStaffCommander && !inputName) return alert("参謀名を入力してください");', 'if (isStaffCommander && !inputName) { showFieldError("pName", "errPName", "参謀名を入力してください"); return; }')
t = t.replace('if(!myName) return alert("名前を入力してください");', 'if(!myName) { showFieldError("pName", "errPName", "名前を入力してください"); return; }')

# register save alliance
t = t.replace(
    'localStorage.setItem("utc_last_role", effectiveRole);',
    'localStorage.setItem("utc_last_role", effectiveRole);\n        localStorage.setItem("utc_is_staff_commander", isStaffCommander ? "1" : "0");\n        localStorage.setItem("utc_last_alliance_idx", String(myAllianceIdx));',
    1,
)

# createDrillRoom / join - find in file
t = re.sub(
    r"function createDrillRoom\(\) \{.*?\n    \}\n",
    '''function createDrillRoom() {
        clearOnboardingErrors();
        const dn = (document.getElementById("drillAllianceNameInput").value || "").trim();
        const rk = (document.getElementById("drillRoomKeyInput").value || "").trim();
        let ok = true;
        if (!dn) { showFieldError("drillAllianceNameInput", "errDrillAllianceName", "同盟名を入力してください"); ok = false; }
        if (!rk) { showFieldError("drillRoomKeyInput", "errDrillRoomKey", "参加コードを入力してください"); ok = false; }
        if (!ok) return;
        drillAllianceName = dn;
        drillJoinCode = rk;
        pendingDrillRoomAction = "create";
        localStorage.setItem("utc_drill_alliance_name", drillAllianceName);
        localStorage.setItem("utc_drill_join_code", drillJoinCode);
        setDrillStatus("ルーム作成を送信しています...");
        sendWsCommandWithRetry(
            {cmd: "set_mode", val: {mode: "drill", alliance_id: 0, room_action: "create", room_code: rk, alliance_name: drillAllianceName}},
            "接続中です。数秒後にもう一度作成してください。"
        );
    }
''',
    t,
    count=1,
    flags=re.S,
)

t = re.sub(
    r"function joinDrillRoom\(\) \{.*?\n    \}\n",
    '''function joinDrillRoom() {
        clearOnboardingErrors();
        const rk = (document.getElementById("drillJoinCodeInput").value || "").trim();
        const roomId = (document.getElementById("drillRoomSelect").value || "").trim() || (drillRoomKey !== "default" ? drillRoomKey : "");
        let ok = true;
        if (!roomId) { showFieldError("drillRoomSelect", "errDrillRoomSelect", "参加するルームを選択してください"); ok = false; }
        if (!rk) { showFieldError("drillJoinCodeInput", "errDrillJoinCode", "参加コードを入力してください"); ok = false; }
        if (!ok) return;
        selectedDrillRoomId = roomId;
        drillRoomKey = roomId;
        drillJoinCode = rk;
        pendingDrillRoomAction = "join";
        localStorage.setItem("utc_drill_room_key", drillRoomKey);
        localStorage.setItem("utc_drill_join_code", drillJoinCode);
        setDrillStatus("参加リクエストを送信しています...");
        sendWsCommandWithRetry(
            {cmd: "set_mode", val: {mode: "drill", alliance_id: 0, room_action: "join", room_id: roomId, room_code: rk}},
            "接続中です。数秒後にもう一度参加してください。"
        );
    }
''',
    t,
    count=1,
    flags=re.S,
)

# setDrillStatus if missing
if "function setDrillStatus" not in t:
    t = t.replace(
        "    function setDrillTab(tab) {",
        """    function setDrillStatus(message, isError = false) {
        const el = document.getElementById("drillStatusMsg");
        if (!el) return;
        el.style.color = isError ? "#E06C75" : "#98C379";
        el.textContent = message || "";
    }

    function setDrillTab(tab) {""",
        1,
    )

# sendWsCommandWithRetry improve if old version
if "pendingDrillModePayload" not in t:
    t = t.replace(
        """    function sendWsCommandWithRetry(payload, failMessage) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(payload));
            return;
        }
        connect();
        setTimeout(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify(payload));
            } else if (failMessage) {
                alert(failMessage);
            }
        }, 700);
    }""",
        """    function sendWsCommandWithRetry(payload, failMessage) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            try { ws.send(JSON.stringify(payload)); } catch (e) {}
            setDrillStatus("");
            return;
        }
        pendingDrillModePayload = payload;
        pendingDrillModeFailMessage = failMessage || "";
        setDrillStatus("接続を確認しています...");
        if (!ws || ws.readyState === WebSocket.CLOSED) connect();
    }""",
        1,
    )

# mode_ok success message
t = t.replace(
    "                    if (appMode === \"drill\" && (requestedAction === \"create\" || requestedAction === \"join\")) {\n                        selectAlliance(0);\n                    }",
    "                    if (appMode === \"drill\" && (requestedAction === \"create\" || requestedAction === \"join\")) {\n                        setDrillStatus(\"✓ ルームに参加しました。役割を選んでください\");\n                        selectAlliance(0);\n                    }",
    1,
)

# onload
if "let initialMode" not in t:
    t = re.sub(
        r"window\.onload = \(\) => \{.*?\n    \};",
        '''window.onload = () => {
        const qsMode = new URLSearchParams(window.location.search).get("mode");
        const savedMode = localStorage.getItem("utc_app_mode");
        drillAllianceName = localStorage.getItem("utc_drill_alliance_name") || "";
        drillRoomKey = localStorage.getItem("utc_drill_room_key") || "default";
        drillJoinCode = localStorage.getItem("utc_drill_join_code") || "";
        const dnEl = document.getElementById("drillAllianceNameInput");
        const rkEl = document.getElementById("drillRoomKeyInput");
        const joinCodeEl = document.getElementById("drillJoinCodeInput");
        if (dnEl && drillAllianceName) dnEl.value = drillAllianceName;
        if (rkEl && drillJoinCode) rkEl.value = drillJoinCode;
        if (joinCodeEl && drillJoinCode) joinCodeEl.value = drillJoinCode;
        setDrillTab(localStorage.getItem("utc_drill_tab") === "join" ? "join" : "create");
        let initialMode = "drill";
        if (qsMode === "drill" || qsMode === "prod") initialMode = qsMode;
        else if (savedMode === "drill" || savedMode === "prod") initialMode = savedMode;
        selectAppMode(initialMode);
        deviceMode = localStorage.getItem("utc_device_mode") || null;
        updateEnvButtonStyles();
        applyChromeNoticeState();
        let savedName = localStorage.getItem("utc_my_name");
        let savedMin = localStorage.getItem("utc_my_min");
        let savedSec = localStorage.getItem("utc_my_sec");
        supportUserName = String(localStorage.getItem("utc_support_user_name") || "").trim();
        if (!supportUserName && savedName) {
            supportUserName = String(savedName).trim();
            if (supportUserName) localStorage.setItem("utc_support_user_name", supportUserName);
        }
        syncSupportNameInput();
        if (savedName) document.getElementById('pName').value = savedName;
        if (savedMin) document.getElementById('pMin').value = savedMin;
        if (savedSec) document.getElementById('pSec').value = savedSec;
        let urlInput = document.getElementById('shareUrlInput');
        if(urlInput) urlInput.value = window.location.href;
        loadVoiceSpeakers();
        ensureVoiceReady();
        const sFile = document.getElementById("supportFileInput");
        if (sFile) sFile.addEventListener("change", supportOnFilePick);
        const sOv = document.getElementById("chatOverlay");
        if (sOv) sOv.addEventListener("paste", supportOnPaste);
        connect();
        if (deviceMode) {
            if (canQuickStart()) refreshQuickStartPanel();
            else tryAutoAdvanceFromIntro();
        }
    };''',
        t,
        count=1,
        flags=re.S,
    )

# setDrillTab save tab
t = t.replace(
    'drillTab = tab === "join" ? "join" : "create";',
    'drillTab = tab === "join" ? "join" : "create";\n        localStorage.setItem("utc_drill_tab", drillTab);',
    1,
)

# staff setRole hint
t = t.replace(
    '<motion style="font-size:13px; color:#E5C07B; margin-bottom:8px; font-weight:bold;">参謀として参加するプレーヤー役割</div>',
    '<div id="staffRoleHint" style="font-size:13px; color:#E5C07B; margin-bottom:8px; font-weight:bold;">次: 担当する班を選んでください</motion>',
)
t = t.replace("<motion ", "<div ").replace("</motion>", "</motion>")

# final cleanup any motion tags
t = t.replace("<motion ", "<div ").replace("</motion>", "</div>")

P.write_text(t, encoding="utf-8")
print("Wrote", P)
