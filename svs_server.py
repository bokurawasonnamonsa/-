import asyncio
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import uuid
import json
import urllib.request
import ssl
import os

# =====================================================================
# Gemini API: set GEMINI_API_KEY in the environment (never commit keys)
# =====================================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
# =====================================================================

# =====================================================================
# 🌐 HTMLデータ（全部乗せ）
# ※ファイル読み込みエラーを無くすため、すべてここに埋め込んでいます
# =====================================================================

HTML_PLAYER = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>3301みんなで戦う為のツール</title>
    <style>
        body { background-color: #1e1e1e; color: #ABB2BF; font-family: sans-serif; text-align: center; margin: 0; padding: 10px; overflow-x: hidden; }
        
        button { touch-action: manipulation; user-select: none; -webkit-user-select: none; }
        
        .utc-main-wrapper { display: flex; flex-direction: column; align-items: center; margin-bottom: 10px; background: #21252B; padding: 10px; border-radius: 8px; border: 1px solid #3E4451; width: 100%; box-sizing: border-box;}
        .utc-main { font-size: 28px; color: white; font-weight: bold; margin-bottom: 5px; font-family: 'Arial Black', 'Verdana', sans-serif; letter-spacing: 2px;}
        .sync-info { display: flex; flex-direction: column; align-items: center; gap: 5px; width: 100%;}
        .sync-row { display: flex; align-items: flex-end; justify-content: center; gap: 10px; width: 100%; }
        
        .card { background: #282C34; border: 1px solid #3E4451; border-radius: 12px; padding: 20px; margin-bottom: 15px; width: 100%; box-sizing: border-box; }
        .role-btn { padding: 12px; font-size: 16px; width: 80%; margin: 5px auto; border-radius: 8px; border:none; font-weight:bold; cursor: pointer; display:block;}
        .active { background: #61AFEF; color: white; } .inactive { background: #3E4451; color: #ABB2BF; }
        
        .clock-container { display: flex; flex-direction: column; align-items: center; gap: 10px; margin-bottom: 15px; background: #21252B; padding: 10px; border-radius: 12px; }
        #analogClock { background: transparent; border-radius: 50%; }
        .digital-jst { font-size: 34px; color: #98C379; font-weight: 900; font-family: 'Arial Black', 'Verdana', sans-serif; font-variant-numeric: tabular-nums; letter-spacing: 2px; }
        
        .departure-info { background: #E06C75; color: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 2px solid white; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
        .departure-time { font-size: 38px; font-weight: 900; font-family: 'Arial Black', 'Verdana', sans-serif; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); font-variant-numeric: tabular-nums; letter-spacing: 2px; }

        .input-group { display: flex; flex-direction: column; align-items: center; gap: 10px; margin: 15px 0;}
        input[type="text"], input[type="number"] { padding: 12px; font-size: 18px; border-radius: 6px; border:none; text-align:center;}
        
        .countdown { font-size: 52px; color: #E5C07B; font-weight: 900; font-family: 'Arial Black', 'Verdana', sans-serif; font-variant-numeric: tabular-nums; letter-spacing: 3px; margin: 10px 0; }
        
        .btn-audio { padding: 10px 20px; border-radius: 30px; font-size: 16px; font-weight: bold; border: none; cursor: pointer; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .audio-off { background: #3E4451; color: #ABB2BF; } .audio-on { background: #98C379; color: #282C34; }
        .btn-gray { background: #3E4451; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer;}
        
        .squad-badge { font-size: 11px; padding: 2px 6px; border-radius: 4px; font-weight: bold; margin-bottom: 5px; display: inline-block;}
        .badge-1 { background: #C678DD; color: white; }
        .badge-2 { background: #56B6C2; color: #282C34; }

        .btn-back { background: #3E4451; color: #ABB2BF; padding: 10px; border-radius: 8px; font-size: 14px; font-weight: bold; border: none; cursor: pointer; margin-top: 10px; width: 80%; display:block; margin: 10px auto 0 auto; }
        .btn-edit { background: #E5C07B; color: #282C34; padding: 8px 15px; border-radius: 6px; font-size: 14px; font-weight: bold; border: none; cursor: pointer; margin-top: 20px; width: 100%; box-sizing: border-box; }
        
        /* ★ サポートチャット関連のスタイル */
        .btn-support { background: #181A1F; border: 2px solid #61AFEF; color: #61AFEF; padding: 12px; border-radius: 8px; font-size: 15px; font-weight: bold; width: 100%; margin-top: 15px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        
        .chat-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #1e1e1e; z-index: 9999; display: none; flex-direction: column; }
        .chat-header { background: #282C34; padding: 15px; border-bottom: 2px solid #61AFEF; display: flex; justify-content: space-between; align-items: center; }
        .chat-close-btn { background: transparent; color: white; border: none; font-size: 20px; cursor: pointer; }
        .chat-body { flex: 1; padding: 15px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
        .chat-input-wrapper { background: #282C34; padding: 10px; display: flex; gap: 10px; border-top: 1px solid #3E4451; }
        .chat-input { flex: 1; padding: 10px; border-radius: 20px; border: 1px solid #3E4451; background: #181A1F; color: white; font-size: 14px; outline: none; }
        .chat-send-btn { background: #61AFEF; color: white; border: none; border-radius: 50%; width: 40px; height: 40px; display: flex; justify-content: center; align-items: center; cursor: pointer; }
        
        .msg-bubble { max-width: 80%; padding: 10px 15px; border-radius: 15px; font-size: 14px; line-height: 1.4; position: relative; }
        .msg-time { font-size: 10px; color: #ABB2BF; margin-top: 5px; }
        .msg-user { align-self: flex-end; background: #61AFEF; color: white; border-bottom-right-radius: 2px; }
        .msg-admin { align-self: flex-start; background: #3E4451; color: white; border-bottom-left-radius: 2px; }
        .msg-ai { align-self: flex-start; background: #181A1F; border: 1px solid #98C379; color: #98C379; border-bottom-left-radius: 2px; }
        .ai-label { font-size: 11px; font-weight: bold; margin-bottom: 4px; display: block; }
    </style>
</head>
<body>

    <div class="utc-main-wrapper">
        <div class="utc-main" id="utc">UTC --:--:--</div>
        <div class="sync-info">
            <div style="font-size: 11px; color: #98C379; margin-bottom: 5px;" id="offsetDisp">(ネットの通信遅延は自動補正しています: --秒)</div>
            <div class="sync-row">
                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                    <span style="font-size: 11px; color: #ABB2BF; font-weight: bold;">遅めたい</span>
                    <button onclick="changeManualOffset(-100)" style="background-color: #3A8DCC; color: white; width: 55px; height: 55px; font-size: 30px; font-weight: bold; border: 2px solid #82C5FF; border-bottom: 4px solid #1B5D8F; border-radius: 10px; cursor: pointer; display: flex; justify-content: center; align-items: center; padding-bottom: 4px; box-sizing: border-box; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">－</button>
                    <span style="font-size: 11px; color: #ABB2BF; font-weight: bold;">-0.1秒</span>
                </div>
                
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin: 0 5px;">
                    <div style="font-size: 11px; color: #ABB2BF; font-weight: bold; margin-bottom: 8px;">ゲーム内UTC時間補正</div>
                    <div id="manualOffsetDisp" style="font-size: 20px; color: #E5C07B; font-weight:bold; background:#1E2227; border: 1px solid #56B6C2; border-radius: 6px; padding: 6px 12px; font-family: monospace; min-width: 90px; text-align: center; box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);">±0.0秒</div>
                </div>
                
                <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                    <span style="font-size: 11px; color: #ABB2BF; font-weight: bold;">速めたい</span>
                    <button onclick="changeManualOffset(100)" style="background-color: #3A8DCC; color: white; width: 55px; height: 55px; font-size: 30px; font-weight: bold; border: 2px solid #82C5FF; border-bottom: 4px solid #1B5D8F; border-radius: 10px; cursor: pointer; display: flex; justify-content: center; align-items: center; padding-bottom: 4px; box-sizing: border-box; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">＋</button>
                    <span style="font-size: 11px; color: #ABB2BF; font-weight: bold;">+0.1秒</span>
                </div>
            </div>
            <div style="font-size: 10px; color: #ABB2BF; margin-top:10px;">※ゲーム内のUTC時間と合うように調整して下さい！</div>
        </div>
    </div>

    <div id="topClockArea"></div>

    <div id="multiDeviceWarning" style="display:none; color: #E06C75; font-size: 14px; margin-bottom: 15px; border: 1px dashed #E06C75; padding: 10px; border-radius: 8px; background: rgba(224, 108, 117, 0.1); text-align: left;">
        ⚠️ <b>【重要: 複数端末の方へ】</b><br>
        カウントダウンを正確に聞くため、<b>この画面は、常にゲームで使用する端末とは別の端末で開いたまま</b> にしておいて下さい。
    </div>

    <div id="audioControlsArea" style="display:none; justify-content: center; align-items: center; gap: 15px; margin-bottom: 15px; width: 100%;">
        <button id="audioBtn" class="btn-audio audio-on" onclick="toggleAudio()" style="margin-bottom: 0;">🔊 音声モード ON</button>
        <button class="btn-audio" style="background: #56B6C2; color: #282C34; margin-bottom: 0;" onclick="playTestAudio()">📢 音声テスト</button>
    </div>

    <div id="step1_intro" class="card">
        <div style="border: 2px solid #E06C75; background: rgba(224, 108, 117, 0.1); padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: left; box-sizing: border-box; width: 100%;">
            <div style="color: #E06C75; font-size: 16px; font-weight: bold; margin-bottom: 8px; text-align: center;">⚠️ 必ずGoogle Chromeなどの<br>ブラウザーで開いて下さい！</div>
            <div style="color: #ABB2BF; font-size: 13px; line-height: 1.5; margin-bottom: 15px;">Discordなどのアプリ上で開くと上手くツールが機能しません。また、設定も初期設定に戻ってしまう為、必ずブラウザーを使用して下さい。</div>
            <div style="display: flex; align-items: center; background: #1E2227; border: 1px solid #3E4451; border-radius: 6px; padding: 5px; width: 100%; box-sizing: border-box;">
                <input type="text" id="shareUrlInput" readonly style="flex: 1; background: transparent; border: none; color: #61AFEF; font-size: 12px; padding: 5px; outline: none; width: 100%; min-width: 0;">
                <button onclick="copyShareUrl()" style="background: #61AFEF; color: white; border: none; border-radius: 4px; padding: 8px 12px; font-weight: bold; font-size: 12px; cursor: pointer; white-space: nowrap; margin-left: 5px;">コピー</button>
            </div>
        </div>

        <h2 style="color: #61AFEF; margin-top:0;">ご利用環境の確認</h2>
        <p style="font-size: 16px; margin-top: 15px;">ゲーム画面とこのツールを<br><span style="color:#E5C07B; font-weight:bold;">別々の端末（スマホとPC等）</span><br>で同時に開くことはできますか？</p>
        <button class="role-btn inactive" style="background:#4CAF50; color:white;" onclick="selectEnv('2device')">💻 はい（別端末で開ける）</button>
        <button class="role-btn inactive" style="background:#E06C75; color:white;" onclick="selectEnv('1device')">📱 いいえ（スマホ1台のみ）</button>
    </div>

    <div id="step2_sync" class="card" style="display:none;">
        <h2 style="color: #E06C75; margin-top:0;">【重要】時計の準備</h2>
        <p style="font-size: 14px; text-align: left;">ゲームを開くとツールの音声が聞こえなくなるため、お手元に<b style="color:#98C379;">秒まで分かる時計</b>をご用意ください。<br>上部の「日本時間」と、お手元の時計の秒数をピッタリ合わせてから次へ進んでください。</p>
        <button class="role-btn active" onclick="confirmSync()">⏱️ 時間合わせOK！</button>
        <button class="btn-back" onclick="goBackTo('step1_intro')">◀ ひとつ前に戻る</button>
    </div>

    <div id="step2_5_alliance" class="card" style="display:none;">
        <h3 style="margin-top:0;">SVS参加する同盟の選択</h3>
        <button id="btnAln0" class="role-btn inactive" onclick="selectAlliance(0)">同盟1</button>
        <button id="btnAln1" class="role-btn inactive" onclick="selectAlliance(1)">同盟2</button>
        <button id="btnAln2" class="role-btn inactive" onclick="selectAlliance(2)">同盟3</button>
        <button class="btn-back" onclick="goBackToEnv()">◀ ひとつ前に戻る</button>
    </div>

    <div id="step3_setup" class="card" style="display:none;">
        <div id="allianceDisplay" style="color: #98C379; font-weight: bold; margin-bottom: 15px; font-size: 18px;"></div>
        <h3 style="margin-top:0;">役割を選択</h3>
        <button id="btnLeader1" class="role-btn inactive" onclick="setRole('leader1')">集結主 (第1班)</button>
        <button id="btnLeader2" class="role-btn inactive" onclick="setRole('leader2')">集結主 (第2班)</button>
        <button id="btnRider" class="role-btn inactive" onclick="setRole('rider')">乗り手</button>
        
        <div id="inputsArea" style="display:none;">
            <div class="input-group">
                <input type="text" id="pName" placeholder="名前を入力" style="width:80%; display:none;">
                <div style="color:#61AFEF; font-weight:bold; margin-top:5px;">行軍時間を入力</div>
                <div>
                    <input type="number" id="pMin" value="0" style="width:50px;"> 分 
                    <input type="number" id="pSec" value="30" style="width:50px;"> 秒
                </div>
                <div style="font-size: 12px; color: #E5C07B; font-weight: bold; margin-top: 5px;">※王城戦開始21:00～に入力して下さい。</div>
            </div>
            <button class="role-btn active" onclick="register()">登録して開始</button>
        </div>
        <button class="btn-back" onclick="goBackTo('step2_5_alliance')">◀ 同盟の選択に戻る</button>
    </div>

    <div id="clockContainer" class="clock-container" style="display:none;">
        <canvas id="analogClock" width="160" height="160"></canvas>
        <div class="digital-jst" id="jstClock">00:00:00</div>
        <div style="font-size: 12px;">現在の日本時間 (Synced)</div>
    </div>

    <div id="display" style="display:none;">
        <div style="display: flex; justify-content: center; align-items: center; gap: 15px; margin-bottom: 10px; border-bottom: 2px solid #3E4451; padding-bottom: 10px;">
            <div id="displayAllianceName" style="font-size: 24px; font-weight: bold; color: #98C379;"></div>
            <button onclick="toggleMap()" style="background: #E5C07B; color: #282C34; border: none; border-radius: 6px; padding: 6px 15px; font-weight: bold; font-size: 14px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">🗺️ 今回の配置図</button>
        </div>
        
        <div id="mapContainer" style="max-height: 0px; overflow: hidden; transition: max-height 0.3s ease-in-out, margin-bottom 0.3s ease-in-out; margin-bottom: 0px;">
            <img src="/map.jpg" style="width: 100%; max-width: 600px; border-radius: 8px; border: 2px solid #E5C07B; box-sizing: border-box; display: block; margin: 0 auto;">
        </div>

        <div id="departureBox"></div>
        <div id="cardsArea"></div>
        
        <button class="btn-edit" onclick="openEditMode()">⚙️ 設定を変更する</button>
        
        <!-- ★ チャット画面を開くボタン -->
        <button class="btn-support" onclick="openSupportChat()">✉️ 質問・SOS窓口（総指揮・AI副官）</button>
    </div>

    <!-- ★ サポートチャット専用画面（オーバーレイ） -->
    <div id="chatOverlay" class="chat-overlay">
        <div class="chat-header">
            <div style="color:white; font-weight:bold; font-size:18px;">✉️ サポートセンター</div>
            <button class="chat-close-btn" onclick="closeSupportChat()">✖</button>
        </div>
        <div style="background:#1E2227; padding:10px; font-size:12px; color:#98C379; text-align:left; border-bottom:1px solid #3E4451;">
            ※設定や行軍時間の相談はこちらへ。<br>まずはAI副官が自動返信し、後ほど総指揮（天津飯）が確認します。
        </div>
        <div class="chat-body" id="chatBody">
            <!-- チャット履歴 -->
        </div>
        <div class="chat-input-wrapper">
            <input type="text" id="chatInputText" class="chat-input" placeholder="質問・SOSを入力..." onkeydown="if(event.key==='Enter') sendSupportChat()">
            <button class="chat-send-btn" onclick="sendSupportChat()">➤</button>
        </div>
    </div>

<script>
    // ★ ID記憶システム
    let myClientId = localStorage.getItem("utc_client_id");
    if (!myClientId) {
        myClientId = "user_" + Math.random().toString(36).substr(2, 9);
        localStorage.setItem("utc_client_id", myClientId);
    }

    let deviceMode = null; 
    let myAllianceIdx = -1; 
    let audioEnabled = true;
    let audioCtx = null; 
    let ws, myRole=null, myName="", myMarchSec=0, timeOffset=0;
    let localState = null; 
    let lastActionState = ""; 
    let registeredIdx = -1; 
    let manualTimeOffset = 0;
    
    let lastCancelTrigger = 0;
    let cachedArrTimes = {};
    let cachedInsTime = null;
    
    const voiceBufferCache = {};
    let globalVoiceLockTime = 0;
    let currentAudioSource = null;
    let lastVoiceKeys = {};

    function toggleMap() {
        let mapDiv = document.getElementById('mapContainer');
        if (mapDiv.style.maxHeight === "0px" || mapDiv.style.maxHeight === "") {
            mapDiv.style.maxHeight = "1000px"; 
            mapDiv.style.marginBottom = "15px";
        } else {
            mapDiv.style.maxHeight = "0px";
            mapDiv.style.marginBottom = "0px";
        }
    }

    function getSyncedNow() { return new Date(Date.now() + timeOffset + manualTimeOffset); }

    function changeManualOffset(val) {
        manualTimeOffset += val;
        let displaySec = Math.abs(manualTimeOffset / 1000).toFixed(1);
        if(displaySec === "0.0") {
            document.getElementById('manualOffsetDisp').innerText = `±0.0秒`;
        } else {
            let signStr = manualTimeOffset > 0 ? "+" : "-";
            document.getElementById('manualOffsetDisp').innerText = `${signStr}${displaySec}秒`;
        }
    }

    function copyShareUrl() {
        let url = window.location.href;
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(url).then(() => { alert("URLをコピーしました！"); }).catch(err => { fallbackCopyTextToClipboard(url); });
        } else { fallbackCopyTextToClipboard(url); }
    }

    function fallbackCopyTextToClipboard(text) {
        let urlInput = document.getElementById('shareUrlInput');
        urlInput.select();
        try { document.execCommand("copy"); alert("URLをコピーしました！"); } 
        catch (err) { alert("コピーに失敗しました。"); }
    }

    function hideAllSteps() {
        document.getElementById('step1_intro').style.display = 'none';
        document.getElementById('step2_sync').style.display = 'none';
        document.getElementById('step2_5_alliance').style.display = 'none';
        document.getElementById('step3_setup').style.display = 'none';
        document.getElementById('display').style.display = 'none';
    }

    function goBackTo(targetId) { hideAllSteps(); document.getElementById(targetId).style.display = 'block'; }
    function goBackToEnv() { hideAllSteps(); if (deviceMode === '1device') document.getElementById('step2_sync').style.display = 'block'; else document.getElementById('step1_intro').style.display = 'block'; }
    function openEditMode() { hideAllSteps(); document.getElementById('step3_setup').style.display = 'block'; }

    // ★ チャット画面の開閉
    function openSupportChat() { document.getElementById('chatOverlay').style.display = 'flex'; renderChatBody(); }
    function closeSupportChat() { document.getElementById('chatOverlay').style.display = 'none'; }

    function selectEnv(mode) {
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

    function confirmSync() { hideAllSteps(); document.getElementById('step2_5_alliance').style.display = 'block'; }

    function selectAlliance(idx) {
        myAllianceIdx = idx;
        hideAllSteps();
        document.getElementById('step3_setup').style.display = 'block';
        let alnName = (localState && localState.alliance_names[idx]) ? localState.alliance_names[idx] : `同盟 ${idx+1}`;
        document.getElementById('allianceDisplay').innerText = `【 ${alnName} 】`;
        document.getElementById('displayAllianceName').innerText = `【 ${alnName} 】`;
        for(let i=0; i<3; i++) {
            document.getElementById(`btnAln${i}`).className = (i === idx) ? 'role-btn active' : 'role-btn inactive';
        }
    }

    function clearRegistrationAndReset() {
        if (!confirm("設定を最初からやり直しますか？")) return;
        if (myRole && myRole.startsWith('leader') && myName !== "") {
            if (registeredIdx !== -1) ws.send(JSON.stringify({cmd: "clear_player", idx: registeredIdx}));
        }
        location.reload();
    }

    function drawClock() {
        const canvas = document.getElementById('analogClock');
        const ctx = canvas.getContext('2d');
        const radius = canvas.height / 2;
        const faceRadius = radius * 0.95;
        
        const d = getSyncedNow();
        const h = (d.getUTCHours() + 9) % 12;
        const m = d.getUTCMinutes();
        const s = d.getUTCSeconds();

        ctx.clearRect(0,0,canvas.width,canvas.height);
        ctx.save(); ctx.translate(radius, radius);
        ctx.beginPath(); ctx.arc(0, 0, faceRadius, 0, 2*Math.PI); 
        ctx.fillStyle = '#ffffff'; ctx.fill();
        ctx.strokeStyle = '#222222'; ctx.lineWidth = 6; ctx.stroke();

        for(let i = 0; i < 60; i++) {
            let ang = i * Math.PI / 30;
            ctx.rotate(ang); ctx.beginPath();
            if(i % 5 === 0) { ctx.moveTo(0, -faceRadius * 0.95); ctx.lineTo(0, -faceRadius * 0.85); ctx.lineWidth = 3; } 
            else { ctx.moveTo(0, -faceRadius * 0.95); ctx.lineTo(0, -faceRadius * 0.90); ctx.lineWidth = 1; }
            ctx.strokeStyle = '#666666'; ctx.stroke(); ctx.rotate(-ang);
        }
        ctx.font = "bold " + (radius * 0.28) + "px Arial";
        ctx.textBaseline = "middle"; ctx.textAlign = "center"; ctx.fillStyle = '#333333';
        for(let num = 1; num <= 12; num++) {
            let ang = num * Math.PI / 6;
            ctx.rotate(ang); ctx.translate(0, -faceRadius * 0.68); ctx.rotate(-ang);
            ctx.fillText(num.toString(), 0, 0);
            ctx.rotate(ang); ctx.translate(0, faceRadius * 0.68); ctx.rotate(-ang);
        }
        drawHand(ctx, (h*Math.PI/6)+(m*Math.PI/360), faceRadius*0.5, 6, '#222222');
        drawHand(ctx, (m*Math.PI/30)+(s*Math.PI/1800), faceRadius*0.75, 4, '#222222');
        drawHand(ctx, s*Math.PI/30, faceRadius*0.85, 2, '#E06C75');
        ctx.beginPath(); ctx.arc(0, 0, 5, 0, 2*Math.PI); ctx.fillStyle = '#222222'; ctx.fill();
        ctx.restore();
        const hhStr = String((d.getUTCHours() + 9) % 24).padStart(2, '0');
        document.getElementById('jstClock').innerText = `${hhStr}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
        requestAnimationFrame(drawClock);
    }
    function drawHand(ctx, pos, length, width, color) { ctx.beginPath(); ctx.lineWidth = width; ctx.lineCap = "round"; ctx.strokeStyle = color; ctx.moveTo(0,0); ctx.rotate(pos); ctx.lineTo(0, -length); ctx.stroke(); ctx.rotate(-pos); }
    drawClock();

    function drawStaticClock(canvasId, d) {
        const canvas = document.getElementById(canvasId);
        if(!canvas) return;
        const ctx = canvas.getContext('2d');
        const radius = canvas.height / 2;
        const faceRadius = radius * 0.95;
        const h = d.getUTCHours() % 12; const m = d.getUTCMinutes(); const s = d.getUTCSeconds();
        ctx.clearRect(0,0,canvas.width,canvas.height);
        ctx.save(); ctx.translate(radius, radius);
        for(let i = 0; i < 60; i++) {
            let ang = i * Math.PI / 30; ctx.rotate(ang); ctx.beginPath();
            if(i % 5 === 0) { ctx.moveTo(0, -faceRadius * 0.9); ctx.lineTo(0, -faceRadius * 0.75); ctx.lineWidth = 2.5; }
            else { ctx.moveTo(0, -faceRadius * 0.9); ctx.lineTo(0, -faceRadius * 0.85); ctx.lineWidth = 1; }
            ctx.strokeStyle = '#666'; ctx.stroke(); ctx.rotate(-ang);
        }
        ctx.font = "bold " + (radius * 0.35) + "px Arial"; ctx.textBaseline = "middle"; ctx.textAlign = "center"; ctx.fillStyle = '#333';
        for(let num = 1; num <= 12; num++) {
            let ang = num * Math.PI / 6; ctx.rotate(ang); ctx.translate(0, -faceRadius * 0.58); ctx.rotate(-ang);
            ctx.fillText(num.toString(), 0, 0); ctx.rotate(ang); ctx.translate(0, faceRadius * 0.58); ctx.rotate(-ang);
        }
        drawHand(ctx, (h*Math.PI/6)+(m*Math.PI/360), faceRadius*0.5, 4, '#222');
        drawHand(ctx, (m*Math.PI/30)+(s*Math.PI/1800), faceRadius*0.75, 3, '#222');
        drawHand(ctx, s*Math.PI/30, faceRadius*0.85, 1.5, '#E06C75');
        ctx.beginPath(); ctx.arc(0, 0, 4, 0, 2*Math.PI); ctx.fillStyle = '#222'; ctx.fill();
        ctx.restore();
    }

    function playVoiceDynamic(text) {
        if (!audioEnabled) return;
        
        if (voiceBufferCache[text]) {
            if (currentAudioSource) {
                try { currentAudioSource.stop(); } catch(e) {}
            }
            let source = audioCtx.createBufferSource();
            source.buffer = voiceBufferCache[text];
            source.connect(audioCtx.destination);
            currentAudioSource = source;
            source.start(0);
        } else {
            fallbackTTS(text);
            fetchAndCacheVoice(text);
        }
    }

    async function fetchAndCacheVoice(text) {
        if (voiceBufferCache[text]) return;
        try {
            let url = window.location.protocol + "//" + window.location.host + "/api/voice?text=" + encodeURIComponent(text);
            let res = await fetch(url);
            if (res.ok) {
                let arrayBuffer = await res.arrayBuffer();
                audioCtx.decodeAudioData(arrayBuffer, (buffer) => {
                    voiceBufferCache[text] = buffer;
                });
            }
        } catch(e) {
            console.warn("音声の取得に失敗しました:", text);
        }
    }

    function fallbackTTS(text) {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            let ut = new SpeechSynthesisUtterance(text);
            ut.lang = 'ja-JP';
            ut.rate = 1.35; 
            window.speechSynthesis.speak(ut);
        }
    }

    async function preloadCommonVoices() {
        const texts = [
            "音声テストです",
            "10", "9", "8", "7", "6", "5", "4", "3", "2", "1", 
            "スタート", "抜いてください",
            "集結開始の準備をお願いします", 
            "差込の準備をお願いします", 
            "占領入替の準備をお願いします", 
            "占領から抜く準備をして下さい"
        ];
        for (let t of texts) {
            await fetchAndCacheVoice(t);
        }
    }

    function playTestAudio() {
        if(audioCtx === null) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            preloadCommonVoices();
        }
        if(audioCtx.state === 'suspended') audioCtx.resume();
        if (!audioEnabled) {
            alert("音声モードがOFFになっています。ONにしてからお試しください。");
            return;
        }
        playVoiceDynamic("音声テストです");
    }

    // ★ チャット送信処理
    function sendSupportChat() {
        let inputEl = document.getElementById('chatInputText');
        let msg = inputEl.value.trim();
        if (msg === "") return;
        
        let senderName = myName;
        if (!senderName || senderName === "") {
            let alnName = (localState && localState.alliance_names[myAllianceIdx]) ? localState.alliance_names[myAllianceIdx] : "不明な同盟";
            senderName = `${alnName}の乗り手`;
        }

        ws.send(JSON.stringify({cmd: "send_support_chat", val: {client_id: myClientId, name: senderName, msg: msg}}));
        inputEl.value = ""; 
    }

    // ★ チャット履歴の描画
    function renderChatBody() {
        if (!localState || !localState.support_chats || !localState.support_chats[myClientId]) return;
        let chatData = localState.support_chats[myClientId].messages;
        let html = "";
        
        chatData.forEach(msg => {
            if (msg.sender === "user") {
                html += `
                <div class="msg-bubble msg-user">
                    <div>${msg.text.replace(/\\n/g, '<br>')}</div>
                    <div class="msg-time" style="color:#E5E5E5; text-align:right;">${msg.time}</div>
                </div>`;
            } else if (msg.sender === "ai") {
                html += `
                <div class="msg-bubble msg-ai">
                    <span class="ai-label">🤖 AI副官</span>
                    <div>${msg.text.replace(/\\n/g, '<br>')}</div>
                    <div class="msg-time">${msg.time}</div>
                </div>`;
            } else if (msg.sender === "admin") {
                html += `
                <div class="msg-bubble msg-admin">
                    <span class="ai-label" style="color:#61AFEF;">👑 総指揮（天津飯）</span>
                    <div>${msg.text.replace(/\\n/g, '<br>')}</div>
                    <div class="msg-time">${msg.time}</div>
                </div>`;
            }
        });
        
        let chatBody = document.getElementById('chatBody');
        chatBody.innerHTML = html;
        chatBody.scrollTop = chatBody.scrollHeight; // 一番下にスクロール
    }

    document.addEventListener('touchstart', function() {
        if (audioCtx && audioCtx.state === 'suspended') audioCtx.resume();
        if ('speechSynthesis' in window) {
            let silent = new SpeechSynthesisUtterance("");
            silent.volume = 0;
            window.speechSynthesis.speak(silent);
        }
    }, {passive: true});

    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") {
            if (!ws || ws.readyState !== WebSocket.OPEN) {
                connect();
            }
        }
    });

    window.onload = () => {
        let savedName = localStorage.getItem("utc_my_name");
        let savedMin = localStorage.getItem("utc_my_min");
        let savedSec = localStorage.getItem("utc_my_sec");
        if (savedName) document.getElementById('pName').value = savedName;
        if (savedMin) document.getElementById('pMin').value = savedMin;
        if (savedSec) document.getElementById('pSec').value = savedSec;
        
        let urlInput = document.getElementById('shareUrlInput');
        if(urlInput) urlInput.value = window.location.href;
    };

    function setRole(r) { 
        myRole = r; document.getElementById('inputsArea').style.display = 'block';
        document.getElementById('pName').style.display = r.startsWith('leader') ? 'block' : 'none';
        
        document.getElementById('btnLeader1').className = (r === 'leader1') ? 'role-btn active' : 'role-btn inactive';
        document.getElementById('btnLeader2').className = (r === 'leader2') ? 'role-btn active' : 'role-btn inactive';
        document.getElementById('btnRider').className = (r === 'rider') ? 'role-btn active' : 'role-btn inactive';
    }

    function register() {
        if(audioCtx === null) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        if(audioCtx.state === 'suspended') audioCtx.resume();
        if ('speechSynthesis' in window) {
            let ut = new SpeechSynthesisUtterance("");
            ut.volume = 0;
            window.speechSynthesis.speak(ut);
        }
        
        setTimeout(() => { preloadCommonVoices(); }, 1000 + Math.random() * 4000);

        myMarchSec = parseInt(document.getElementById('pMin').value)*60 + parseInt(document.getElementById('pSec').value);
        localStorage.setItem("utc_my_min", document.getElementById('pMin').value);
        localStorage.setItem("utc_my_sec", document.getElementById('pSec').value);

        if (registeredIdx !== -1) {
            ws.send(JSON.stringify({cmd: "clear_player", idx: registeredIdx}));
            registeredIdx = -1;
        }

        if(myRole.startsWith('leader')) {
            myName = document.getElementById('pName').value;
            if(!myName) return alert("名前を入力してください");
            localStorage.setItem("utc_my_name", myName);
            ws.send(JSON.stringify({cmd:"register_player", val:{role:myRole, alliance_id:myAllianceIdx, name:myName, march_min:0, march_sec:myMarchSec, device_mode: deviceMode}}));
        } else {
            myName = "乗り手"; 
            ws.send(JSON.stringify({cmd:"register_player", val:{role:"rider", alliance_id:myAllianceIdx, device_mode: deviceMode}}));
        }
        
        hideAllSteps();
        document.getElementById('display').style.display = 'block';
        
        if (deviceMode === '2device') {
            document.getElementById('audioControlsArea').style.display = 'flex';
            document.getElementById('multiDeviceWarning').style.display = 'block'; 
        }
    }

    function connect() {
        if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) return;
        let ws_protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
        ws = new WebSocket(ws_protocol + window.location.host + "/ws");
        ws.onmessage = (e) => {
            try {
                const msg = JSON.parse(e.data);
                
                if (msg.type === "sync") {
                    if(msg.server_timestamp) {
                        timeOffset = msg.server_timestamp - Date.now();
                        let displayD = new Date(Date.now() + timeOffset + manualTimeOffset);
                        let dHH = String(displayD.getUTCHours()).padStart(2, '0');
                        let dMM = String(displayD.getUTCMinutes()).padStart(2, '0');
                        let dSS = String(displayD.getUTCSeconds()).padStart(2, '0');
                        document.getElementById('utc').innerText = `UTC ${dHH}:${dMM}:${dSS}`;
                    }
                    return; 
                }

                if(msg.server_timestamp) timeOffset = msg.server_timestamp - Date.now();
                
                let displayD = new Date(Date.now() + timeOffset + manualTimeOffset);
                let dHH = String(displayD.getUTCHours()).padStart(2, '0');
                let dMM = String(displayD.getUTCMinutes()).padStart(2, '0');
                let dSS = String(displayD.getUTCSeconds()).padStart(2, '0');
                document.getElementById('utc').innerText = `UTC ${dHH}:${dMM}:${dSS}`;
                
                let autoSec = (timeOffset / 1000).toFixed(2);
                let autoSign = autoSec >= 0 ? "+" : "";
                document.getElementById('offsetDisp').innerText = `(ネットの通信遅延は自動補正しています: ${autoSign}${autoSec}秒)`;
                
                localState = msg.data;
                
                for (let a = 0; a < 3; a++) {
                    let btn = document.getElementById(`btnAln${a}`);
                    if (btn && localState.alliance_names[a]) {
                        btn.innerText = localState.alliance_names[a];
                    }
                }
                if (myAllianceIdx !== -1 && localState.alliance_names[myAllianceIdx]) {
                    let alnName = localState.alliance_names[myAllianceIdx];
                    let disp1 = document.getElementById('allianceDisplay');
                    if (disp1) disp1.innerText = `【 ${alnName} 】`;
                    let disp2 = document.getElementById('displayAllianceName');
                    if (disp2) disp2.innerText = `【 ${alnName} 】`;
                }
                
                // チャット画面が開いていれば更新
                if (document.getElementById('chatOverlay').style.display === 'flex') {
                    renderChatBody();
                }

            } catch (err) { console.error(err); }
        };
        ws.onclose = () => setTimeout(connect, 1000 + Math.random() * 3000);
    }

    function buildBoxHTML(b, now) {
        let isActionDone = (b.actionMs <= now);
        let boxBg = isActionDone ? "#3E4451" : "#2A2E37";
        let bdColor = isActionDone ? "#3E4451" : b.color;
        let txtColor = isActionDone ? "#ABB2BF" : b.color;
        let cdText = isActionDone ? "00:00" : formatSec((b.actionMs - now)/1000);
        let actionLabel = isActionDone ? `✅ ${b.actionLabel} 完了` : `⏳ ${b.actionLabel} まで`;

        if (deviceMode === '1device') {
            return `
            <div class="departure-info" style="background:${boxBg}; color:#fff; border:2px solid ${bdColor}; padding: 20px;">
                <div style="font-size: 16px; font-weight: bold; margin-bottom: 12px;">💡 あなたの出発時刻 (日本時間)</div>
                <div style="display:flex; justify-content:center; align-items:center; gap: 25px;">
                    <canvas id="clock_${b.type}" width="110" height="110" style="background:#fff; border-radius:50%; border:4px solid #282C34; box-shadow: 0 2px 5px rgba(0,0,0,0.5);"></canvas>
                    <span class="departure-time" id="jst_${b.type}">--:--:--</span>
                </div>
                <div style="font-size:13px; margin-top:15px; font-weight:bold; background:rgba(0,0,0,0.2); padding:6px; border-radius:4px;">※お手元の時計がこの時間になったらボタンを押す！</div>
                
                <div style="margin-top:20px; padding-top:20px; border-top:1px dashed rgba(255,255,255,0.5);">
                    <div style="font-size: 20px; font-weight: bold; color:${txtColor}; letter-spacing: 1px;">${actionLabel}</div>
                    <div id="cd_${b.type}" style="font-size: 56px; color: ${txtColor}; font-weight: 900; font-family: 'Arial Black', 'Verdana', sans-serif; font-variant-numeric: tabular-nums; letter-spacing: 3px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); margin: 15px 0;">${cdText}</div>
                    <div style="margin-top:15px; background:rgba(0,0,0,0.3); padding:10px; border-radius:6px;">
                        <div style="font-size:15px; color:#ABB2BF;">🎯 ${b.arrLabel}時間 (UTC)</div>
                        <div id="arr_${b.type}" style="font-size:32px; color:#98C379; font-weight:bold; font-family: 'Arial Black', 'Verdana', sans-serif; font-variant-numeric: tabular-nums; letter-spacing: 2px; margin-top: 5px;">--:--:--</div>
                    </div>
                </div>
            </div>`;
        } else {
            return `
            <div class="departure-info" style="background:${boxBg}; color:#61AFEF; border:2px solid ${bdColor}; box-shadow: 0 4px 8px rgba(0,0,0,0.5); margin-bottom: 20px; padding: 25px 15px;">
                <div style="font-size: 24px; font-weight: bold; margin-bottom: 10px; color:${txtColor}; letter-spacing: 1px;">${actionLabel}</div>
                <div id="cd_${b.type}" class="departure-time" style="color:${txtColor}; font-size: 76px; font-weight: 900; font-family: 'Arial Black', 'Verdana', sans-serif; font-variant-numeric: tabular-nums; letter-spacing: 4px; margin: 20px 0;">${cdText}</div>
                <div style="margin-top:20px; background:#1E2227; padding:15px; border-radius:8px; border:1px solid #3E4451;">
                    <div style="font-size:16px; color:#ABB2BF; margin-bottom: 5px;">🎯 ${b.arrLabel}時間 (UTC)</div>
                    <div id="arr_${b.type}" style="font-size:40px; color:#98C379; font-weight:bold; font-family: 'Arial Black', 'Verdana', sans-serif; font-variant-numeric: tabular-nums; letter-spacing: 2px;">--:--:--</div>
                </div>
            </div>`;
        }
    }

    function updateBoxDynamic(b, now) {
        let isActionDone = (b.actionMs <= now);
        let cdEl = document.getElementById(`cd_${b.type}`);
        if (cdEl && !isActionDone) cdEl.innerText = formatSec((b.actionMs - now) / 1000);

        let arrEl = document.getElementById(`arr_${b.type}`);
        if (arrEl) {
            let d = new Date(b.targetMs);
            arrEl.innerText = `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}:${String(d.getUTCSeconds()).padStart(2, '0')}`;
        }

        if (deviceMode === '1device') {
            let jstEl = document.getElementById(`jst_${b.type}`);
            if (jstEl) {
                let d = new Date(b.actionMs + 9 * 3600000); 
                jstEl.innerText = `${String(d.getUTCHours() % 24).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}:${String(d.getUTCSeconds()).padStart(2, '0')}`;
            }
        }
    }

    function getTargetTime(t, now, default_rally) {
        if(t.state === 0) return null;
        let adjUTC = now + t.off;
        if(t.state === 4) {
            let w = Math.max(0, (new Date(t.start_at).getTime() - now) / 1000);
            return adjUTC + (w + default_rally + t.sub_set) * 1000;
        } else if(t.state === 1) { return adjUTC + (t.sec + t.sub_set) * 1000;
        } else if(t.state === 2) { return new Date(t.frozen_target).getTime(); }
        return null;
    }

    function getVirtualArrTime(sqId, data, now, depth=0) {
        if(sqId < 0 || sqId > 5 || depth > 3) return null;
        let start = 6 + sqId * 6;
        let arrs = [];
        let marches = [];
        for(let i=start; i<start+6; i++) {
            let t = data.timers[i];
            if(t.name !== "") marches.push(t.sub_set);
            let tgt = getTargetTime(t, now, data.default_rally);
            if(tgt) arrs.push(tgt);
        }
        
        if (arrs.length > 0) {
            let maxArr = Math.max(...arrs);
            cachedArrTimes[sqId] = { time: maxArr, updated: now };
            return maxArr;
        }
        
        let alnIdx = Math.floor(sqId / 2);
        if (data.alliance_roles[alnIdx] === 'occupy') {
            let tgtSq = data.swap_base_squad;
            if (tgtSq >= 0 && tgtSq !== sqId) {
                let baseArr = getVirtualArrTime(tgtSq, data, now, depth+1);
                if (baseArr !== null) {
                    let maxMarch = marches.length > 0 ? Math.max(...marches) : 0;
                    let calcArr = baseArr + data.swap_extras[alnIdx] * 1000 + maxMarch * 1000;
                    cachedArrTimes[sqId] = { time: calcArr, updated: now };
                    return calcArr;
                }
            }
        }
        if (cachedArrTimes[sqId] && (now - cachedArrTimes[sqId].updated < 300000)) return cachedArrTimes[sqId].time;
        return null;
    }

    function getInsTargetTime(data, now) {
        let idx = data.insert_target_idx;
        let res = null;
        if (idx >= 0 && idx < 6 && data.timers[idx].state !== 0) {
            res = getTargetTime(data.timers[idx], now, data.default_rally);
        } else {
            let arr = [];
            for(let i=0; i<6; i++) { let t = getTargetTime(data.timers[i], now, data.default_rally); if(t) arr.push(t); }
            if(arr.length > 0) res = Math.max(...arr);
        }
        if (res !== null) {
            cachedInsTime = { time: res, updated: now };
            return res;
        }
        if (cachedInsTime && (now - cachedInsTime.updated < 300000)) return cachedInsTime.time;
        return null;
    }

    setInterval(() => {
        if (!localState || myRole === null || myAllianceIdx === -1) return;
        let now = getSyncedNow().getTime();

        if (localState.cancel_trigger !== lastCancelTrigger) {
            lastCancelTrigger = localState.cancel_trigger;
            cachedArrTimes = {};
            cachedInsTime = null;
            lastVoiceKeys = {};
            lastActionState = "";
        }

        let startIdx = 6 + myAllianceIdx * 12;
        let myTimers = localState.timers.slice(startIdx, startIdx + 12);
        let myRoleType = localState.alliance_roles[myAllianceIdx];
        
        let leaderT = null;
        if (myRole.startsWith('leader')) {
            let foundIdx = myTimers.findIndex(x => x.name === myName);
            if (foundIdx !== -1) {
                registeredIdx = startIdx + foundIdx; 
                leaderT = myTimers[foundIdx];
            } else {
                registeredIdx = -1;
            }
        }

        let leaderLeadTime = myRole.startsWith('leader') ? (localState.default_rally + myMarchSec) * 1000 : 0;
        let riderLeadTime = myRole === 'rider' ? myMarchSec * 1000 : 0;
        let finalLeadTime = myRole.startsWith('leader') ? leaderLeadTime : riderLeadTime;

        let displayBlocks = [];

        let insT = getInsTargetTime(localState, now);
        if (insT) {
            let actionTime = insT - 1000 - finalLeadTime;
            let actionLbl = myRole.startsWith('leader') ? "差込(集結)" : "差込";
            displayBlocks.push({
                type: 'ins', actionMs: actionTime, targetMs: insT - 1000,
                actionLabel: actionLbl, arrLabel: "差込", color: "#E06C75"
            });
        }

        if (myRole.startsWith('leader') && leaderT && leaderT.state === 4) {
            let startAt = new Date(leaderT.start_at).getTime();
            displayBlocks.push({
                type: 'gorei', actionMs: startAt, targetMs: startAt + (localState.default_rally + leaderT.sub_set) * 1000,
                actionLabel: "集結開始", arrLabel: "着弾", color: "#E5C07B"
            });
        }

        if (myRoleType === 'occupy') {
            if (localState.manual_swap_trigger_time) {
                let targetMs = localState.manual_swap_trigger_time * 1000;
                let actionTime = targetMs - (myMarchSec * 1000); 
                displayBlocks.push({
                    type: 'swap', actionMs: actionTime, targetMs: targetMs,
                    actionLabel: myRole.startsWith('leader') ? "占領入替" : "入替", arrLabel: "入替着弾", color: "#98C379"
                });
            }
        }

        if (myRoleType === 'attack') {
            if (localState.manual_wd_trigger_time) {
                let targetMs = localState.manual_wd_trigger_time * 1000;
                let actionTime = targetMs - (myMarchSec * 1000); 
                displayBlocks.push({
                    type: 'wd_manual', actionMs: actionTime, targetMs: targetMs, 
                    actionLabel: "占領抜き (一斉撤退)", arrLabel: "撤退完了", color: "#C678DD"
                });
            }
        }

        displayBlocks = displayBlocks.filter(b => {
            if (b.type === 'swap' || b.type === 'wd_manual' || b.type === 'ins') return true;
            return (b.targetMs - now) > -5000;
        });
        
        displayBlocks.sort((a,b) => a.actionMs - b.actionMs);

        let newStateStr = displayBlocks.map(b => `${b.type}_${b.actionMs}`).join('|') || "waiting";

        if (newStateStr !== lastActionState) {
            lastActionState = newStateStr;
            let depBox = document.getElementById('departureBox');
            
            if (newStateStr === "waiting") {
                depBox.innerHTML = `<div style="background:#2A2E37; color:#ABB2BF; padding: 30px; border-radius: 8px; border: 2px dashed #3E4451; font-size: 18px; font-weight: bold; margin-bottom: 15px;">💡 総指揮（天津飯）からの指示を待機中...</div>`;
            } else {
                let html = "";
                displayBlocks.forEach(b => { html += buildBoxHTML(b, now); });
                depBox.innerHTML = html;

                if (deviceMode === '1device') {
                    displayBlocks.forEach(b => {
                        if (b.actionMs > now) {
                            drawStaticClock(`clock_${b.type}`, new Date(b.actionMs + 9*3600000));
                        }
                    });
                }
            }
        }

        if (newStateStr !== "waiting") {
            displayBlocks.forEach(b => { 
                updateBoxDynamic(b, now); 
                if (deviceMode === '2device') {
                    let wait = (b.actionMs - now) / 1000;
                    handleVoice(wait, b.type);
                }
            });
        }

        let html = "";
        myTimers.forEach((t, index) => {
            if(myRole.startsWith('leader') && t.name !== myName) return;
            if(myRole === 'rider' && t.name === "") return;
            
            let rem = 0, status = "待機中";
            let arrStr = "--:--:--";
            let adjUTC = now + t.off;

            if(t.state === 4) { 
                rem = (new Date(t.start_at).getTime() - now)/1000; status = "集結ボタンまで"; 
                let d = new Date(adjUTC + (rem + localState.default_rally + t.sub_set) * 1000);
                arrStr = `${String(d.getUTCHours()).padStart(2,'0')}:${String(d.getUTCMinutes()).padStart(2,'0')}:${String(d.getUTCSeconds()).padStart(2,'0')}`;
            }
            else if(t.state === 1) { 
                rem = (new Date(t.end).getTime() - now)/1000; status = "集結中"; 
                let d = new Date(adjUTC + (t.sec + t.sub_set) * 1000);
                arrStr = `${String(d.getUTCHours()).padStart(2,'0')}:${String(d.getUTCMinutes()).padStart(2,'0')}:${String(d.getUTCSeconds()).padStart(2,'0')}`;
            }
            else if(t.state === 2) { 
                rem = (new Date(t.end).getTime() - now)/1000; status = "行軍中"; 
                let d = new Date(t.frozen_target);
                arrStr = `${String(d.getUTCHours()).padStart(2,'0')}:${String(d.getUTCMinutes()).padStart(2,'0')}:${String(d.getUTCSeconds()).padStart(2,'0')}`;
            }
            
            let badgeHtml = index < 6 ? `<span class="squad-badge badge-1">第1班</span>` : `<span class="squad-badge badge-2">第2班</span>`;
            
            html += `
            <div class="card">
                ${badgeHtml}<h2 style="color:#61AFEF;margin:0; margin-top:5px; font-size:22px;">${t.name}部隊</h2>
                <div style="font-size:18px;margin-top:10px; font-weight:bold;">${status}</div>
                <div class="countdown" style="font-family: 'Arial Black', 'Verdana', sans-serif; font-variant-numeric: tabular-nums; letter-spacing: 2px;">${formatSec(rem)}</div>
                <div style="background:#1E2227; border:1px solid #3E4451; border-radius:6px; padding:10px; margin-top:12px;">
                    <div style="font-size:13px; color:#ABB2BF;">🎯 着弾時間 (UTC)</div>
                    <div style="font-size:26px; color:#98C379; font-weight:bold; font-family: 'Arial Black', 'Verdana', sans-serif; font-variant-numeric: tabular-nums; letter-spacing: 2px; margin-top:5px;">${arrStr}</div>
                </div>
            </div>`;
        });
        document.getElementById('cardsArea').innerHTML = html;
    }, 50); 

    function handleVoice(remSec, fullType) {
        let r = Math.floor(remSec);
        if (r < 0 || r > 20) {
            lastVoiceKeys[fullType] = -1;
            return;
        }

        let lastVar = lastVoiceKeys[fullType] === undefined ? -1 : lastVoiceKeys[fullType];
        if (r === lastVar) return; 

        if (lastVar !== -1 && r > lastVar && (r - lastVar) <= 2) return;

        let baseType = fullType.split('_')[0]; 
        let text = "";
        
        if (r === 18) {
            if (baseType === 'gorei') text = "集結開始の準備をお願いします";
            else if (baseType === 'ins') text = "差込の準備をお願いします";
            else if (baseType === 'swap') text = "占領入替の準備をお願いします";
            else if (baseType === 'wd') text = "占領から抜く準備をして下さい";
        } else if (r <= 10 && r > 0) {
            text = r.toString();
        } else if (r === 0) {
            text = baseType === 'wd' ? "抜いてください" : "スタート";
        }
        
        if (text) {
            let nowTs = Date.now();
            if (nowTs - globalVoiceLockTime < 800) {
                return; 
            }

            globalVoiceLockTime = nowTs;
            lastVoiceKeys[fullType] = r;
            playVoiceDynamic(text);
        }
    }

    function formatSec(s){ if(s<0)s=0; return `${String(Math.floor(s/60)).padStart(2,'0')}:${String(Math.floor(s%60)).padStart(2,'0')}`;}
    function toggleAudio() { 
        audioEnabled = !audioEnabled; 
        let b = document.getElementById('audioBtn'); b.innerText = audioEnabled ? "🔊 音声モード ON" : "🔇 音声ミュート中"; b.className = audioEnabled ? "btn-audio audio-on" : "btn-audio audio-off"; 
        if(audioEnabled && 'speechSynthesis' in window) window.speechSynthesis.speak(new SpeechSynthesisUtterance("")); 
    }
    connect();
</script>
</body>
</html>"""

HTML_ADMIN = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>究極のUTC司令塔 WEB</title>
    <style>
        body { background-color: #1e1e1e; color: #ABB2BF; font-family: 'Consolas', sans-serif; margin: 0; padding: 0; font-size: 13px; overflow-x: hidden; }
        .container { width: 100%; max-width: 1900px; padding: 15px; box-sizing: border-box; margin: auto; }
        .sticky-header { position: sticky; top: 0; left: 0; width: 100%; background: #1e1e1e; z-index: 100; padding: 15px 25px; border-bottom: 2px solid #3E4451; display: flex; align-items: center; justify-content: space-between; box-sizing: border-box;}
        .utc-main { font-size: 32px; color: white; font-weight: bold; display: flex; align-items: baseline; gap: 15px; }
        
        .status-bar { display: flex; align-items: center; background: #1E2227; padding: 6px 15px; border-radius: 6px; border: 1px solid #3E4451; gap: 15px; font-size: 13px; }
        .status-divider { width: 1px; height: 20px; background-color: #3E4451; }
        .status-val { font-size: 16px; font-weight: bold; margin: 0 4px; }
        
        .enemy-card { background: #282C34; border: 1px solid #E06C75; border-radius: 8px; padding: 15px; margin-bottom: 15px; }
        .enemy-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
        
        .pair-panel { background: #2A2E37; padding: 10px 15px; margin-bottom: 15px; border: 2px solid #E5C07B; border-radius: 8px; }
        .pair-cb-box { background: #1E2227; padding: 5px 10px; border-radius: 4px; border: 1px solid #3E4451; }

        .manual-panel { background: #21252B; border: 2px solid #98C379; border-radius: 8px; padding: 15px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; }
        .manual-box { background: #2A2E37; border: 1px solid #3E4451; border-radius: 6px; padding: 10px; flex: 1; margin: 0 10px; display: flex; flex-direction: column; align-items: center; }
        .manual-title { font-size: 14px; font-weight: bold; margin-bottom: 8px; width:100%; text-align:center;}

        .alliances-container { display: flex; gap: 15px; width: 100%; justify-content: space-between; }
        .alliance-col { width: calc(33.333% - 10px); background: #282C34; border: 1px solid #3E4451; border-radius: 8px; padding: 15px; display: flex; flex-direction: column; box-sizing: border-box;}
        .squads-flex { display: flex; flex-direction: column; gap: 15px; flex: 1; }
        
        .header-bar { display: flex; align-items: center; background: #2A2E37; padding: 8px 12px; border-radius: 6px; margin-bottom: 10px; border-left: 6px solid;}
        .header-bar-enemy { border-color: #E06C75; }
        .header-bar-ally { border-color: #61AFEF; justify-content: space-between; flex-wrap: wrap; gap: 10px;}
        
        .inline-calc { display: flex; align-items: center; gap: 15px; }
        .row { display: flex; align-items: center; background: #21252B; margin-bottom: 4px; padding: 6px 8px; border-radius: 6px; gap: 6px; }
        
        .name-wrapper { position: relative; display: inline-block; }
        .online-dot { width: 8px; height: 8px; border-radius: 50%; background-color: #5C6370; position: absolute; top: -3px; left: -3px; border: 2px solid #21252B; z-index: 10; transition: background-color 0.3s; }
        .online-dot.active { background-color: #98C379; box-shadow: 0 0 4px #98C379; } 
        .online-dot.away { background-color: #E5C07B; box-shadow: 0 0 4px #E5C07B; } 
        
        .radio-container { display: flex; flex-direction: column; align-items: center; width: 30px;}
        .radio-label { font-size: 10px; font-weight: bold;}
        
        input.alliance-input { width: 140px; font-size: 18px; background: #181A1F; border: 1px solid #56B6C2; color: #56B6C2; font-weight: bold; padding: 6px 10px; border-radius: 4px;}
        select.alliance-role { font-size: 14px; background: #181A1F; border: 1px solid #C678DD; color: #C678DD; font-weight: bold; padding: 6px; border-radius: 4px; cursor: pointer;}
        input.player-name { width: 110px; background: #1E2227; border: 1px solid #3E4451; font-weight: bold; padding: 6px 6px 6px 12px; border-radius: 4px; font-size: 15px;}
        input.color-enemy { color: #E06C75 !important; } 
        input.color-ally1 { color: #C678DD !important; } 
        input.color-ally2 { color: #56B6C2 !important; }
        
        button { cursor: pointer; border: none; border-radius: 3px; font-weight: bold; color: white; }
        .btn-gray { background: #3E4451; } .btn-red { background: #E06C75; } .btn-green { background: #98C379; color: #282C34; }
        
        .timer-box { background: #1E2227; padding: 3px 5px; display: flex; align-items: center; border: 1px solid #3E4451; border-radius: 4px;}
        .updown-col { display: flex; flex-direction: column; align-items: center; gap: 1px;}
        .updown-btn { width: 16px; height: 12px; font-size: 8px; padding: 0;}
        .val-txt { font-size: 18px; color: #E5C07B; font-weight: bold; margin: 0 2px; width: 14px; text-align: center;}
        .colon { color: #E5C07B; font-size: 16px; font-weight: bold; width: 6px; text-align: center; }
        .st-btn { width: 24px; height: 16px; font-size: 10px; padding:0; margin-bottom: 2px;}
        
        .sub-box { background: #1E2227; padding: 3px 5px; display: flex; align-items: center; border: 1px solid #3E4451; border-left:none; border-radius: 0 4px 4px 0;}
        .sub-updown-btn { width: 12px; height: 10px; font-size: 7px; padding: 0;}
        .sub-val-txt { font-size: 12px; color: #ABB2BF; font-weight: bold; width: 10px; text-align: center;}
        .sub-disp { font-size: 14px; color: #C678DD; font-weight: bold; width: 42px; text-align: right; margin-right:4px;}
        
        .target-box { color: #ABB2BF; font-size: 12px; padding-left: 8px; width: 150px; display: flex; flex-direction: column; line-height: 1.2; }
        
        .gorei-panel { background: #2A2E37; border: 1px solid #56B6C2; padding: 8px 12px; border-radius: 0 4px 4px 4px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; border-top: none;}
        .squad-title { font-size: 14px; font-weight: bold; padding: 6px 12px; border-radius: 4px 4px 0 0; display: inline-block; background: #3E4451; color: white; margin-top: 10px; display: flex; justify-content: space-between; align-items: center;}
    </style>
</head>
<body>

<div class="sticky-header">
    <div class="utc-main">
        <span id="utc">UTC --:--:--</span>
        <span id="offsetDisp" style="font-size: 14px; font-weight: normal; color: #98C379;">(同期中...)</span>
    </div>
    
    <div style="display: flex; align-items: center; gap: 20px;">
        <button style="background: #181A1F; border: 2px solid #61AFEF; color: #61AFEF; padding: 8px 16px; font-size: 13px; border-radius: 6px; font-weight: bold; cursor: pointer; box-shadow: 0 2px 4px rgba(0,0,0,0.5);" onclick="window.open('/support_hq_3301', '_blank')" onmouseover="this.style.background='#61AFEF'; this.style.color='white';" onmouseout="this.style.background='#181A1F'; this.style.color='#61AFEF';">✉️ サポートセンターを別枠で開く</button>
        <button class="btn-gray" style="padding: 8px 16px; font-size: 13px; border-radius: 6px;" onclick="send('toggle_rally')" id="rallyToggleBtn">⏱ 5分(切替)</button>
        <div class="status-bar">
            <div style="color: #ABB2BF; font-weight: bold; display: flex; align-items: center;">
                <span style="color:#ffffff; margin-right:8px;">[全同盟]</span>
                👑集結主:<span class="status-val" style="color:#E5C07B;" id="countLeader_total">0</span> 
                🏇乗り手:<span class="status-val" style="color:#C678DD;" id="countRider_total">0</span>
            </div>
            <div class="status-divider"></div>
            <div style="color: #ABB2BF; font-weight: bold; display: flex; align-items: center;">
                <span id="lbl_count_aln0" style="color:#61AFEF; margin-right:5px; width:30px;">APL</span>
                👑<span class="status-val" style="color:#E5C07B;" id="countLeader_aln0">0</span> 
                🏇<span class="status-val" style="color:#C678DD;" id="countRider_aln0">0</span>
            </div>
            <div class="status-divider"></div>
            <div style="color: #ABB2BF; font-weight: bold; display: flex; align-items: center;">
                <span id="lbl_count_aln1" style="color:#61AFEF; margin-right:5px; width:30px;">PKD</span>
                👑<span class="status-val" style="color:#E5C07B;" id="countLeader_aln1">0</span> 
                🏇<span class="status-val" style="color:#C678DD;" id="countRider_aln1">0</span>
            </div>
            <div class="status-divider"></div>
            <div style="color: #ABB2BF; font-weight: bold; display: flex; align-items: center;">
                <span id="lbl_count_aln2" style="color:#61AFEF; margin-right:5px; width:30px;">MTC</span>
                👑<span class="status-val" style="color:#E5C07B;" id="countLeader_aln2">0</span> 
                🏇<span class="status-val" style="color:#C678DD;" id="countRider_aln2">0</span>
            </div>
        </div>
    </div>
</div>

<div class="container">
    <div class="manual-panel" id="manual_panel_content"></div>
    <div class="pair-panel" id="pairing_panel_content"></div>

    <div class="enemy-card">
        <div class="header-bar header-bar-enemy">
            <div style="color: white; font-weight: bold; font-size: 16px; margin-right: 30px;">◆ 敵国 (ターゲット)</div>
            <div class="inline-calc">
                <div style="color: #C678DD; font-weight: bold; font-size: 14px;">【 マーク (1秒前 UTC) 】</div>
                <div id="insTarget" style="font-size: 20px; color: #E5C07B; font-weight: bold;">--:--:--</div>
                <div id="insRemain" style="font-size: 20px; color: #98C379; font-weight: bold;">--:--</div>
            </div>
        </div>
        <div id="enemy_rows" class="enemy-grid"></div>
    </div>

    <div id="alliances_container" class="alliances-container"></div>
</div>

<script>
    let ws; let isBuilt = false; let timeOffset = 0; 
    let insertTargetIdx = -1; let delayTargetIdxs = [-1,-1,-1,-1,-1,-1];
    let currentRoles = ["", "", ""];
    let cachedArrTimes = {};
    let lastCancelTrigger = 0;
    let globalLocalState = null; 

    function getSyncedNow() { return new Date(Date.now() + timeOffset); }
    function send(cmd, idx=null, val=null) { if(ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({cmd: cmd, idx: idx, val: val})); }

    function syncManBaseToSquad(sqIdStr) {
        let sqId = parseInt(sqIdStr);
        if (sqId === -1 || !globalLocalState) return;
        let arrTime = getVirtualArrTime(sqId, globalLocalState, getSyncedNow().getTime());
        if (arrTime) {
            send('set_manual_base_abs', null, arrTime / 1000);
        }
        document.getElementById('manBaseSyncSelect').value = "-1";
    }

    function buildRow(i, radioType, radioName, colorClass) {
        let label = radioType === 'insert' ? 'ﾏｰｸ' : '抜く';
        let labelColor = radioType === 'insert' ? '#E06C75' : '#C678DD';
        let cmd = radioType === 'insert' ? 'set_insert_target' : 'set_delay_target';
        
        return `
        <div class="row">
            <div class="radio-container">
                <div class="radio-label" style="color:${labelColor}">${label}</div>
                <input type="radio" name="${radioName}" id="radio_${i}" value="${i}" onclick="send('${cmd}', ${i})">
            </div>
            <div class="name-wrapper">
                <div id="dot_${i}" class="online-dot" title="未登録"></div>
                <input class="name player-name ${colorClass}" id="name_${i}" onblur="send('update_name', ${i}, this.value)" onkeydown="if(event.key==='Enter') send('update_name', ${i}, this.value)">
            </div>
            <button class="btn-red" style="padding: 3px 6px; font-size: 11px; height: 24px; border-radius: 4px;" onclick="if(confirm('クリアしますか？')) send('clear_player', ${i})" title="クリア">✖</button>
            <div class="timer-box">
                <div class="updown-col"><button class="btn-gray updown-btn" onclick="send('mod_main', ${i}, 600)">▲</button><div class="val-txt" id="m10_${i}">0</div><button class="btn-gray updown-btn" onclick="send('mod_main', ${i}, -600)">▼</button></div>
                <div class="updown-col"><button class="btn-gray updown-btn" onclick="send('mod_main', ${i}, 60)">▲</button><div class="val-txt" id="m1_${i}">0</div><button class="btn-gray updown-btn" onclick="send('mod_main', ${i}, -60)">▼</button></div>
                <div class="colon">:</div>
                <div class="updown-col"><button class="btn-gray updown-btn" onclick="send('mod_main', ${i}, 10)">▲</button><div class="val-txt" id="s10_${i}">0</div><button class="btn-gray updown-btn" onclick="send('mod_main', ${i}, -10)">▼</button></div>
                <div class="updown-col"><button class="btn-gray updown-btn" onclick="send('mod_main', ${i}, 1)">▲</button><div class="val-txt" id="s1_${i}">0</div><button class="btn-gray updown-btn" onclick="send('mod_main', ${i}, -1)">▼</button></div>
                <div style="display:flex; flex-direction:column; margin-left:6px;">
                    <button class="btn-green st-btn" onclick="send('start', ${i})">▶</button>
                    <button class="btn-red st-btn" onclick="send('stop', ${i})">■</button>
                </div>
            </div>
            <div class="sub-box">
                <div style="display:flex;">
                    <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_sub', ${i}, 60)">▲</button><div class="sub-val-txt" id="sm1_${i}">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_sub', ${i}, -60)">▼</button></div>
                    <div style="color:#ABB2BF;font-size:12px;align-self:center">:</div>
                    <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_sub', ${i}, 10)">▲</button><div class="sub-val-txt" id="ss10_${i}">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_sub', ${i}, -10)">▼</button></div>
                    <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_sub', ${i}, 1)">▲</button><div class="sub-val-txt" id="ss1_${i}">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_sub', ${i}, -1)">▼</button></div>
                </div>
                <div class="sub-disp" id="subdisp_${i}">00:00</div>
            </div>
            <div class="target-box">
                <span id="dispatch_${i}" style="color:#E5C07B; font-weight:bold;"></span>
                <span id="tgt_${i}">▶--:--:--</span>
            </div>
        </div>`;
    }

    function buildGoreiPanel(squadId, color) {
        return `
        <div class="gorei-panel" style="border-color: ${color};">
            <div style="display:flex; flex-direction:column; gap:6px; flex:1;">
                <div style="display:flex; align-items:center; justify-content:space-between;">
                    <div style="display:flex; align-items:center; gap:5px;">
                        <span style="color:#ABB2BF; font-size:11px;">猶予+</span>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei', ${squadId}, 10)">▲</button><div class="sub-val-txt" id="goreiE10_${squadId}" style="color:#E5C07B;">1</div><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei', ${squadId}, -10)">▼</button></div>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei', ${squadId}, 1)">▲</button><div class="sub-val-txt" id="goreiE1_${squadId}" style="color:#E5C07B;">5</div><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei', ${squadId}, -1)">▼</button></div>
                        <span style="color:#ABB2BF; font-size:11px;">秒</span>
                    </div>
                    <button style="background: ${color}; color: white; padding: 4px 10px; font-size:12px; border-radius:4px;" onclick="send('fire_gorei', ${squadId})">即時号令 (今のﾀｲﾐﾝｸﾞ)</button>
                </div>
                <div style="display:flex; align-items:center; justify-content:space-between; background:#1E2227; padding:4px 6px; border-radius:4px; border:1px solid #3E4451;">
                    <span style="color:#ABB2BF; font-size:11px;">着弾:</span>
                    <div style="display:flex; align-items:center;">
                        <span id="goreiTargetHH_${squadId}" style="font-size:16px; color:#61AFEF; font-weight:bold;">00</span><span style="color:#61AFEF; font-weight:bold; margin:0 2px;">:</span>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei_target', ${squadId}, 600)">▲</button><div class="sub-val-txt" id="goreiTargetM10_${squadId}" style="color:#61AFEF; font-size:16px;">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei_target', ${squadId}, -600)">▼</button></div>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei_target', ${squadId}, 60)">▲</button><div class="sub-val-txt" id="goreiTargetM1_${squadId}" style="color:#61AFEF; font-size:16px;">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei_target', ${squadId}, -60)">▼</button></div><span style="color:#61AFEF; font-weight:bold; margin:0 2px;">:</span>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei_target', ${squadId}, 10)">▲</button><div class="sub-val-txt" id="goreiTargetS10_${squadId}" style="color:#61AFEF; font-size:16px;">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei_target', ${squadId}, -10)">▼</button></div>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei_target', ${squadId}, 1)">▲</button><div class="sub-val-txt" id="goreiTargetS1_${squadId}" style="color:#61AFEF; font-size:16px;">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei_target', ${squadId}, -1)">▼</button></div>
                    </div>
                    <button style="background: #98C379; color: #282C34; padding: 4px 6px; font-size:11px; border-radius:4px; font-weight:bold;" onclick="send('fire_gorei_fixed', ${squadId})">着弾指定号令</button>
                </div>
            </div>
            <div style="display:flex; flex-direction:column; gap:8px; margin-left:5px; align-items:center;">
                <button class="btn-red" style="padding: 6px 12px; font-size:12px; border-radius:4px;" onclick="send('cancel_gorei', ${squadId})">解除</button>
                <div id="goreiState_${squadId}" style="color:#E5C07B; font-size:11px; width:45px; text-align:center;"></div>
            </div>
        </div>`;
    }

    function buildManualPanel() {
        let html = `
            <div class="manual-box" style="border-color:#E5C07B;">
                <div class="manual-title" style="color:#E5C07B; display:flex; justify-content:space-between; align-items:center;">
                    <span>⏱️ 3301着弾(基準)</span>
                    <select id="manBaseSyncSelect" style="background:#181A1F; border:1px solid #E5C07B; color:#E5C07B; font-size:11px; padding:2px; border-radius:3px; font-weight:bold;" onchange="syncManBaseToSquad(this.value)">
                        <option value="-1">手動で設定</option>
                        <option value="0">APL-第1班の着弾に合わせる</option>
                        <option value="1">APL-第2班の着弾に合わせる</option>
                        <option value="2">PKD-第1班の着弾に合わせる</option>
                        <option value="3">PKD-第2班の着弾に合わせる</option>
                        <option value="4">MTC-第1班の着弾に合わせる</option>
                        <option value="5">MTC-第2班の着弾に合わせる</option>
                    </select>
                </div>
                <div style="display:flex; align-items:center; margin-top:8px;">
                    <span id="manBaseHH" style="font-size:24px; color:#E5C07B; font-weight:bold;">00</span><span style="color:#E5C07B; font-weight:bold; margin:0 3px;">:</span>
                    <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_manual_base', null, 600)">▲</button><div class="sub-val-txt" id="manBaseM10" style="color:#E5C07B; font-size:20px;">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_manual_base', null, -600)">▼</button></div>
                    <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_manual_base', null, 60)">▲</button><div class="sub-val-txt" id="manBaseM1" style="color:#E5C07B; font-size:20px;">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_manual_base', null, -60)">▼</button></div><span style="color:#E5C07B; font-weight:bold; margin:0 3px;">:</span>
                    <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_manual_base', null, 10)">▲</button><div class="sub-val-txt" id="manBaseS10" style="color:#E5C07B; font-size:20px;">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_manual_base', null, -10)">▼</button></div>
                    <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_manual_base', null, 1)">▲</button><div class="sub-val-txt" id="manBaseS1" style="color:#E5C07B; font-size:20px;">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_manual_base', null, -1)">▼</button></div>
                </div>
            </div>
            
            <div style="font-size:24px; color:#ABB2BF;">▶</div>

            <div class="manual-box" style="border-color:#98C379;">
                <div class="manual-title" style="color:#98C379;">🟢 入替着弾(占領同盟)</div>
                <div style="display:flex; align-items:center; gap:5px; margin-bottom:5px;">
                    <span style="color:#ABB2BF; font-size:11px;">基準から +</span>
                    <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_manual_swap_margin', null, 10)">▲</button><div class="sub-val-txt" id="manSwapE10" style="color:#98C379;">1</div><button class="btn-gray sub-updown-btn" onclick="send('mod_manual_swap_margin', null, -10)">▼</button></div>
                    <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_manual_swap_margin', null, 1)">▲</button><div class="sub-val-txt" id="manSwapE1" style="color:#98C379;">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_manual_swap_margin', null, -1)">▼</button></div>
                    <span style="color:#ABB2BF; font-size:11px;">秒後</span>
                </div>
                <div id="manSwapTarget" style="font-size:24px; color:#98C379; font-weight:bold; font-family:monospace; margin-bottom:8px;">00:00:00</div>
                <div style="display:flex; gap:5px; width:100%;">
                    <button style="background:#98C379; color:#282C34; padding:6px; font-weight:bold; border-radius:4px; flex:1;" onclick="send('fire_manual_swap')">発動</button>
                    <button class="btn-red" style="padding:6px; border-radius:4px;" onclick="send('cancel_manual_swap')">解除</button>
                </div>
                <div id="manSwapState" style="color:#E5C07B; font-size:11px; height:12px; margin-top:3px;"></div>
            </div>
            
            <div style="font-size:24px; color:#ABB2BF;">▶</div>

            <div class="manual-box" style="border-color:#E06C75;">
                <div class="manual-title" style="color:#E06C75;">🔴 占領抜き(攻撃同盟)</div>
                <div style="display:flex; align-items:center; gap:5px; margin-bottom:5px;">
                    <span style="color:#ABB2BF; font-size:11px;">入替着弾から -</span>
                    <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_manual_wd_margin', null, 10)">▲</button><div class="sub-val-txt" id="manWdE10" style="color:#E06C75;">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_manual_wd_margin', null, -10)">▼</button></div>
                    <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_manual_wd_margin', null, 1)">▲</button><div class="sub-val-txt" id="manWdE1" style="color:#E06C75;">1</div><button class="btn-gray sub-updown-btn" onclick="send('mod_manual_wd_margin', null, -1)">▼</button></div>
                    <span style="color:#ABB2BF; font-size:11px;">秒前</span>
                </div>
                <div id="manWdTarget" style="font-size:24px; color:#E06C75; font-weight:bold; font-family:monospace; margin-bottom:8px;">00:00:00</div>
                <div style="display:flex; gap:5px; width:100%;">
                    <button style="background:#E06C75; color:white; padding:6px; font-weight:bold; border-radius:4px; flex:1;" onclick="send('fire_manual_wd')">発動</button>
                    <button class="btn-red" style="padding:6px; border-radius:4px;" onclick="send('cancel_manual_wd')">解除</button>
                </div>
                <div id="manWdState" style="color:#E5C07B; font-size:11px; height:12px; margin-top:3px;"></div>
            </div>
        `;
        document.getElementById('manual_panel_content').innerHTML = html;
    }

    function buildPairingPanel() {
        let cbHtml = "";
        let defaultNames = ["APL", "PKD", "MTC"];
        for(let a=0; a<3; a++) {
            cbHtml += `
                <div class="pair-cb-box">
                    <div style="color:#61AFEF; font-weight:bold; margin-bottom:5px; font-size:12px;" id="pair_aln_label_${a}">${defaultNames[a]}</div>
                    <label style="cursor:pointer; display:block; color:#C678DD;"><input type="checkbox" id="pair_cb_${a*2}" onclick="send('toggle_pair_squad', ${a*2})"> 第1班</label>
                    <label style="cursor:pointer; display:block; color:#56B6C2; margin-top:3px;"><input type="checkbox" id="pair_cb_${a*2+1}" onclick="send('toggle_pair_squad', ${a*2+1})"> 第2班</label>
                </div>
            `;
        }
        let html = `
        <h3 style="color:#E5C07B; margin-top:0; margin-bottom:10px;">🔗 複数班ペアリング号令（同時着弾）</h3>
        <div style="display:flex; align-items:center; gap:20px;">
            <div style="display:flex; gap:10px;">${cbHtml}</div>
            <div style="flex:1; display:flex; flex-direction:column; gap:10px; border-left:1px solid #3E4451; padding-left:20px;">
                <div style="display:flex; align-items:center; justify-content:space-between;">
                    <div style="display:flex; align-items:center; gap:5px;">
                        <span style="color:#ABB2BF; font-size:13px;">猶予+</span>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei', null, 10)">▲</button><div class="sub-val-txt" id="pairGoreiE10" style="color:#E5C07B; font-size:14px;">1</div><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei', null, -10)">▼</button></div>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei', null, 1)">▲</button><div class="sub-val-txt" id="pairGoreiE1" style="color:#E5C07B; font-size:14px;">5</div><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei', null, -1)">▼</button></div>
                        <span style="color:#ABB2BF; font-size:13px;">秒</span>
                    </div>
                    <button style="background: #E5C07B; color: #282C34; padding: 6px 20px; font-size:15px; font-weight:bold; border-radius:4px;" onclick="send('fire_pair_gorei')">即時号令 (今のﾀｲﾐﾝｸﾞ)</button>
                </div>
                <div style="display:flex; align-items:center; justify-content:space-between; background:#1E2227; padding:6px 10px; border-radius:4px; border:1px solid #3E4451;">
                    <span style="color:#ABB2BF; font-size:13px;">ペア着弾(UTC):</span>
                    <div style="display:flex; align-items:center;">
                        <span id="pairGoreiTargetHH" style="font-size:18px; color:#E5C07B; font-weight:bold;">00</span><span style="color:#E5C07B; font-weight:bold; margin:0 3px;">:</span>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei_target', null, 600)">▲</button><div class="sub-val-txt" id="pairGoreiTargetM10" style="color:#E5C07B; font-size:18px; width:12px;">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei_target', null, -600)">▼</button></div>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei_target', null, 60)">▲</button><div class="sub-val-txt" id="pairGoreiTargetM1" style="color:#E5C07B; font-size:18px;">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei_target', null, -60)">▼</button></div><span style="color:#E5C07B; font-weight:bold; margin:0 3px;">:</span>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei_target', null, 10)">▲</button><div class="sub-val-txt" id="pairGoreiTargetS10" style="color:#E5C07B; font-size:18px; width:12px;">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei_target', null, -10)">▼</button></div>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei_target', null, 1)">▲</button><div class="sub-val-txt" id="pairGoreiTargetS1" style="color:#E5C07B; font-size:18px;">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei_target', null, -1)">▼</button></div>
                    </div>
                    <button style="background: #98C379; color: #282C34; padding: 6px 20px; font-size:14px; font-weight:bold; border-radius:4px;" onclick="send('fire_pair_gorei_fixed')">着弾指定号令</button>
                </div>
            </div>
            <div style="display:flex; flex-direction:column; gap:10px; align-items:center; margin-left:15px;">
                <button class="btn-red" style="padding: 10px 20px; font-size:14px; border-radius:4px;" onclick="send('cancel_pair_gorei')">一斉解除</button>
            </div>
        </div>`;
        document.getElementById('pairing_panel_content').innerHTML = html;
    }

    function buildAlliancePanel(a, role, data) {
        let panelHtml = `
            <div class="header-bar header-bar-ally">
                <div style="display:flex; align-items:center; gap:10px;">
                    <input class="alliance-input" id="aln_name_${a}" placeholder="同盟名を入力" onblur="send('update_alliance', ${a}, this.value)">
                    <select class="alliance-role" id="aln_role_${a}" onchange="send('update_alliance_role', ${a}, this.value)">
                        <option value="occupy" ${role==='occupy'?'selected':''}>🟢 占領同盟</option>
                        <option value="attack" ${role==='attack'?'selected':''}>🔴 攻撃同盟</option>
                    </select>
                </div>
            </div>
        `;

        panelHtml += `<div class="squads-flex">`;
        
        let s1Title = `
            <div class="squad-title" style="border-bottom: 2px solid #C678DD; color: #C678DD; width: 100%; box-sizing: border-box; display:flex; justify-content:space-between; align-items:center;">
                第1班 (連撃部隊)
            </div>`;
        panelHtml += `
            <div class="squad-block">
                ${s1Title}
                ${buildGoreiPanel(a*2, '#C678DD')}
                <div id="rows_squad_${a*2}"></div>
            </div>`;

        let s2Title = `
            <div class="squad-title" style="border-bottom: 2px solid #56B6C2; color: #56B6C2; width: 100%; box-sizing: border-box; display:flex; justify-content:space-between; align-items:center;">
                第2班 (連撃部隊)
            </div>`;
        panelHtml += `
            <div class="squad-block">
                ${s2Title}
                ${buildGoreiPanel(a*2+1, '#56B6C2')}
                <div id="rows_squad_${a*2+1}"></div>
            </div>
        </div>`;
        return panelHtml;
    }

    function buildDOM() {
        buildManualPanel();
        buildPairingPanel();
        let enemyHtml = '';
        for(let i=0; i<6; i++) enemyHtml += buildRow(i, 'insert', 'ins_tgt', 'color-enemy');
        document.getElementById('enemy_rows').innerHTML = enemyHtml;

        let alnHtml = '';
        for(let a=0; a<3; a++) {
            let initRole = a === 0 ? 'occupy' : 'attack';
            alnHtml += `<div class="alliance-col" id="alliance_container_${a}">${buildAlliancePanel(a, initRole, null)}</div>`;
        }
        document.getElementById('alliances_container').innerHTML = alnHtml;

        for(let a=0; a<3; a++) {
            let sq1 = '', sq2 = '';
            for(let i=0; i<6; i++) {
                sq1 += buildRow(6 + a*12 + i, 'delay', `del_tgt_${a*2}`, 'color-ally1');
                sq2 += buildRow(12 + a*12 + i, 'delay', `del_tgt_${a*2+1}`, 'color-ally2');
            }
            document.getElementById(`rows_squad_${a*2}`).innerHTML = sq1;
            document.getElementById(`rows_squad_${a*2+1}`).innerHTML = sq2;
        }
    }

    function connect() {
        let ws_protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
        ws = new WebSocket(ws_protocol + window.location.host + "/ws");
        ws.onmessage = (e) => {
            try {
                const msg = JSON.parse(e.data); const data = msg.data;
                globalLocalState = data; 
                if(msg.server_timestamp) {
                    timeOffset = msg.server_timestamp - Date.now();
                    let elOffset = document.getElementById('offsetDisp');
                    if(elOffset) elOffset.innerText = `(補正: ${timeOffset > 0 ? "+" : ""}${(timeOffset/1000).toFixed(2)}秒)`;
                }
                if(msg.type === "init") { buildDOM(); isBuilt = true; }
                if(!isBuilt) return;
                updateUI(data, msg.utc);
            } catch (err) { console.error(err); }
        };
        ws.onclose = () => setTimeout(connect, 1000);
    }
    connect();

    function updateUI(data, utcTime) {
        document.getElementById('utc').innerText = "UTC " + utcTime;
        insertTargetIdx = data.insert_target_idx; delayTargetIdxs = data.delay_target_idxs;
        
        document.getElementById('countLeader_total').innerText = data.online_counts.total.leader;
        document.getElementById('countRider_total').innerText = data.online_counts.total.rider;
        
        for(let i=0; i<3; i++) {
            let lbl = document.getElementById(`lbl_count_aln${i}`);
            if(lbl) lbl.innerText = data.alliance_names[i] || ["APL", "PKD", "MTC"][i];
            
            let lCount = document.getElementById(`countLeader_aln${i}`);
            if(lCount) lCount.innerText = data.online_counts[`aln${i}`].leader;
            
            let rCount = document.getElementById(`countRider_aln${i}`);
            if(rCount) rCount.innerText = data.online_counts[`aln${i}`].rider;
        }

        let now = getSyncedNow().getTime();
        
        if (data.cancel_trigger !== lastCancelTrigger) {
            lastCancelTrigger = data.cancel_trigger;
            cachedArrTimes = {};
        }

        document.getElementById('manSwapE10').innerText = Math.floor(data.manual_swap_margin / 10);
        document.getElementById('manSwapE1').innerText = data.manual_swap_margin % 10;
        document.getElementById('manWdE10').innerText = Math.floor(data.manual_wd_margin / 10);
        document.getElementById('manWdE1').innerText = data.manual_wd_margin % 10;

        let manBaseTs = data.manual_base_target ? data.manual_base_target * 1000 : now;
        let dBase = new Date(manBaseTs);
        document.getElementById('manBaseHH').innerText = String(dBase.getUTCHours()).padStart(2, '0');
        document.getElementById('manBaseM10').innerText = Math.floor(dBase.getUTCMinutes() / 10);
        document.getElementById('manBaseM1').innerText = dBase.getUTCMinutes() % 10;
        document.getElementById('manBaseS10').innerText = Math.floor(dBase.getUTCSeconds() / 10);
        document.getElementById('manBaseS1').innerText = dBase.getUTCSeconds() % 10;
        
        let baseColor = data.manual_base_target ? "#E5C07B" : "#ABB2BF";
        document.getElementById('manBaseHH').style.color = baseColor;
        document.getElementById('manBaseM10').style.color = baseColor;
        document.getElementById('manBaseM1').style.color = baseColor;
        document.getElementById('manBaseS10').style.color = baseColor;
        document.getElementById('manBaseS1').style.color = baseColor;

        let dSwap = new Date(manBaseTs + data.manual_swap_margin * 1000);
        document.getElementById('manSwapTarget').innerText = `${String(dSwap.getUTCHours()).padStart(2, '0')}:${String(dSwap.getUTCMinutes()).padStart(2, '0')}:${String(dSwap.getUTCSeconds()).padStart(2, '0')}`;
        document.getElementById('manSwapState').innerText = data.manual_swap_trigger_time ? "✅ 発動中" : "";

        let dWd = new Date(dSwap.getTime() - data.manual_wd_margin * 1000);
        document.getElementById('manWdTarget').innerText = `${String(dWd.getUTCHours()).padStart(2, '0')}:${String(dWd.getUTCMinutes()).padStart(2, '0')}:${String(dWd.getUTCSeconds()).padStart(2, '0')}`;
        document.getElementById('manWdState').innerText = data.manual_wd_trigger_time ? "✅ 発動中" : "";

        for(let a=0; a<3; a++) {
            if (currentRoles[a] !== data.alliance_roles[a]) {
                currentRoles[a] = data.alliance_roles[a];
                document.getElementById(`alliance_container_${a}`).innerHTML = buildAlliancePanel(a, data.alliance_roles[a], data);
                let sq1 = '', sq2 = '';
                for(let i=0; i<6; i++) {
                    sq1 += buildRow(6 + a*12 + i, 'delay', `del_tgt_${a*2}`, 'color-ally1');
                    sq2 += buildRow(12 + a*12 + i, 'delay', `del_tgt_${a*2+1}`, 'color-ally2');
                }
                document.getElementById(`rows_squad_${a*2}`).innerHTML = sq1;
                document.getElementById(`rows_squad_${a*2+1}`).innerHTML = sq2;
            }

            let elName = document.getElementById(`aln_name_${a}`);
            if(elName && document.activeElement !== elName) elName.value = data.alliance_names[a];

            let alnLabel = document.getElementById(`pair_aln_label_${a}`);
            if(alnLabel) alnLabel.innerText = data.alliance_names[a] || ["APL", "PKD", "MTC"][a];
        }
        
        document.getElementById('pairGoreiE10').innerText = Math.floor(data.pair_gorei_offset / 10);
        document.getElementById('pairGoreiE1').innerText = data.pair_gorei_offset % 10;

        let pairMarches = [];
        for (let s = 0; s < 6; s++) {
            if (data.pair_selected[s]) {
                let startIdx = 6 + s * 6;
                for (let i = startIdx; i < startIdx + 6; i++) {
                    if (data.timers[i].name !== "") pairMarches.push(data.timers[i].sub_set);
                }
            }
        }
        let pairMaxMarch = pairMarches.length > 0 ? Math.max(...pairMarches) : 0;
        let minPairTgtTs = now + (data.pair_gorei_offset + data.default_rally + pairMaxMarch) * 1000;
        let pairDispTs = data.pair_fixed_target ? data.pair_fixed_target * 1000 : minPairTgtTs;
        let pairD = new Date(pairDispTs);
        
        document.getElementById('pairGoreiTargetHH').innerText = String(pairD.getUTCHours()).padStart(2, '0');
        document.getElementById('pairGoreiTargetM10').innerText = Math.floor(pairD.getUTCMinutes() / 10);
        document.getElementById('pairGoreiTargetM1').innerText = pairD.getUTCMinutes() % 10;
        document.getElementById('pairGoreiTargetS10').innerText = Math.floor(pairD.getUTCSeconds() / 10);
        document.getElementById('pairGoreiTargetS1').innerText = pairD.getUTCSeconds() % 10;
        
        let pairColor = data.pair_fixed_target ? "#E5C07B" : "#61AFEF";
        document.getElementById('pairGoreiTargetHH').style.color = pairColor;
        document.getElementById('pairGoreiTargetM10').style.color = pairColor;
        document.getElementById('pairGoreiTargetM1').style.color = pairColor;
        document.getElementById('pairGoreiTargetS10').style.color = pairColor;
        document.getElementById('pairGoreiTargetS1').style.color = pairColor;

        for(let s=0; s<6; s++) {
            document.getElementById(`goreiE10_${s}`).innerText = Math.floor(data.gorei_offsets[s] / 10);
            document.getElementById(`goreiE1_${s}`).innerText = data.gorei_offsets[s] % 10;
            
            let startIdx = 6 + s * 6;
            let marches = [];
            for(let i=startIdx; i<startIdx+6; i++) { if(data.timers[i].name !== "") marches.push(data.timers[i].sub_set); }
            let maxMarch = marches.length > 0 ? Math.max(...marches) : 0;
            
            let minTgtTs = now + (data.gorei_offsets[s] + data.default_rally + maxMarch) * 1000;
            let dispTs = data.gorei_fixed_targets[s] ? data.gorei_fixed_targets[s] * 1000 : minTgtTs;
            let d = new Date(dispTs);
            
            document.getElementById(`goreiTargetHH_${s}`).innerText = String(d.getUTCHours()).padStart(2, '0');
            document.getElementById(`goreiTargetM10_${s}`).innerText = Math.floor(d.getUTCMinutes() / 10);
            document.getElementById(`goreiTargetM1_${s}`).innerText = d.getUTCMinutes() % 10;
            document.getElementById(`goreiTargetS10_${s}`).innerText = Math.floor(d.getUTCSeconds() / 10);
            document.getElementById(`goreiTargetS1_${s}`).innerText = d.getUTCSeconds() % 10;
            
            let color = data.gorei_fixed_targets[s] ? "#E5C07B" : "#61AFEF";
            document.getElementById(`goreiTargetHH_${s}`).style.color = color;
            document.getElementById(`goreiTargetM10_${s}`).style.color = color;
            document.getElementById(`goreiTargetM1_${s}`).style.color = color;
            document.getElementById(`goreiTargetS10_${s}`).style.color = color;
            document.getElementById(`goreiTargetS1_${s}`).style.color = color;

            let isGoreiActive = data.timers.slice(startIdx, startIdx+6).some(t => t.state === 4);
            document.getElementById(`goreiState_${s}`).innerText = isGoreiActive ? "待機中" : "";
        }

        for(let i=0; i<42; i++) {
            let rb = document.getElementById('radio_'+i);
            if(rb) {
                if(i<6) rb.checked = (insertTargetIdx === i);
                else { let squadId = Math.floor((i - 6) / 6); rb.checked = (delayTargetIdxs[squadId] === i); }
            }

            let t = data.timers[i]; 
            let ni = document.getElementById('name_'+i); 
            if(ni && document.activeElement !== ni) ni.value = t.name;
            
            let dot = document.getElementById('dot_'+i);
            if(dot) {
                dot.classList.remove('active', 'away');
                if(t.name !== "") {
                    if (t.online) { dot.classList.add('active'); dot.title = "オンライン"; } 
                    else if (t.device_mode === '1device') { dot.classList.add('away'); dot.title = "1端末(ゲーム中)"; } 
                    else { dot.title = "オフライン"; }
                } else { dot.title = "未登録"; }
            }

            const ms = t.sec;
            document.getElementById('m10_'+i).innerText = Math.floor(ms/600); 
            document.getElementById('m1_'+i).innerText = Math.floor((ms%600)/60);
            document.getElementById('s10_'+i).innerText = Math.floor((ms%60)/10); 
            document.getElementById('s1_'+i).innerText = Math.floor(ms%10);
            
            document.getElementById('sm1_'+i).innerText = Math.floor(t.sub_set/60); 
            document.getElementById('ss10_'+i).innerText = Math.floor((t.sub_set%60)/10); 
            document.getElementById('ss1_'+i).innerText = Math.floor(t.sub_set%10);
            document.getElementById('subdisp_'+i).innerText = t.state === 2 ? formatSec(t.sub_sec) : "00:00";
            
            let tgtStr = "▶--:--:--"; let dispatchStr = ""; let adjUTC = now + t.off;
            
            if(t.state === 4) {
                let waitSec = Math.max(0, (new Date(t.start_at).getTime() - now) / 1000);
                dispatchStr = `🚀出征まで:${formatSec(waitSec)}`;
                let tgtD = new Date(adjUTC + (waitSec + data.default_rally + t.sub_set) * 1000);
                tgtStr = `▶${String(tgtD.getUTCHours()).padStart(2,'0')}:${String(tgtD.getUTCMinutes()).padStart(2,'0')}:${String(tgtD.getUTCSeconds()).padStart(2,'0')}`;
            } else if(t.state === 1) {
                let tgtD = new Date(adjUTC + (t.sec + t.sub_set) * 1000);
                tgtStr = `▶${String(tgtD.getUTCHours()).padStart(2,'0')}:${String(tgtD.getUTCMinutes()).padStart(2,'0')}:${String(tgtD.getUTCSeconds()).padStart(2,'0')}`;
            } else if(t.state === 2) {
                let tgtD = new Date(t.frozen_target);
                tgtStr = `▶${String(tgtD.getUTCHours()).padStart(2,'0')}:${String(tgtD.getUTCMinutes()).padStart(2,'0')}:${String(tgtD.getUTCSeconds()).padStart(2,'0')}`;
            }
            document.getElementById('dispatch_'+i).innerText = dispatchStr;
            document.getElementById('tgt_'+i).innerText = tgtStr;
        }
        calcExtras(data, now);
    }

    function getTargetTime(t, now, default_rally) {
        if(t.state === 0) return null;
        let adjUTC = now + t.off;
        if(t.state === 4) {
            let w = Math.max(0, (new Date(t.start_at).getTime() - now) / 1000);
            return adjUTC + (w + default_rally + t.sub_set) * 1000;
        } else if(t.state === 1) { return adjUTC + (t.sec + t.sub_set) * 1000;
        } else if(t.state === 2) { return new Date(t.frozen_target).getTime(); }
        return null;
    }

    function getVirtualArrTime(sqId, data, now, depth=0) {
        if(sqId < 0 || sqId > 5 || depth > 3) return null;
        let start = 6 + sqId * 6;
        let arrs = [];
        let marches = [];
        for(let i=start; i<start+6; i++) {
            let t = data.timers[i];
            if(t.name !== "") marches.push(t.sub_set);
            let tgt = getTargetTime(t, now, data.default_rally);
            if(tgt) arrs.push(tgt);
        }
        
        if (arrs.length > 0) {
            let maxArr = Math.max(...arrs);
            cachedArrTimes[sqId] = { time: maxArr, updated: now };
            return maxArr;
        }
        
        let alnIdx = Math.floor(sqId / 2);
        if (data.alliance_roles[alnIdx] === 'occupy') {
            let tgtSq = data.swap_base_squad;
            if (tgtSq >= 0 && tgtSq !== sqId) {
                let baseArr = getVirtualArrTime(tgtSq, data, now, depth+1);
                if (baseArr !== null) {
                    let maxMarch = marches.length > 0 ? Math.max(...marches) : 0;
                    let calcArr = baseArr + data.swap_extras[alnIdx] * 1000 + maxMarch * 1000;
                    cachedArrTimes[sqId] = { time: calcArr, updated: now };
                    return calcArr;
                }
            }
        }
        if (cachedArrTimes[sqId] && (now - cachedArrTimes[sqId].updated < 300000)) return cachedArrTimes[sqId].time;
        return null;
    }

    function calcExtras(data, now) {
        let elInsTgt = document.getElementById('insTarget');
        let elInsRem = document.getElementById('insRemain');

        let insTargetTime = null;
        if (insertTargetIdx >= 0 && insertTargetIdx < 6 && data.timers[insertTargetIdx].state !== 0) {
            let tgt = getTargetTime(data.timers[insertTargetIdx], now, data.default_rally);
            if (tgt) insTargetTime = tgt - 1000;
        } else {
            let tArrA = [];
            for(let i=0; i<6; i++) { let t = getTargetTime(data.timers[i], now, data.default_rally); if(t) tArrA.push(t); }
            if(tArrA.length > 0) insTargetTime = Math.max(...tArrA) - 1000; 
        }

        if(insTargetTime) {
            let d = new Date(insTargetTime);
            if(elInsTgt) elInsTgt.innerText = `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}:${String(d.getUTCSeconds()).padStart(2, '0')}`;
            if(elInsRem) elInsRem.innerText = formatSec(Math.max(0, (insTargetTime - now)/1000));
        } else {
            if(elInsTgt) elInsTgt.innerText = "--:--:--"; 
            if(elInsRem) elInsRem.innerText = "--:--";
        }
    }

    function formatSec(s) { 
        if (s < 0) s = 0; const m = Math.floor(s/60), ss = Math.floor(s%60); 
        return `${String(m).padStart(2,'0')}:${String(ss).padStart(2,'0')}`; 
    }
</script>
</body>
</html>"""

HTML_SUPPORT = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>🚨 サポート＆AI報告センター</title>
    <style>
        body { background-color: #1e1e1e; color: #ABB2BF; font-family: 'Consolas', sans-serif; margin: 0; padding: 0; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
        .header { background: #282C34; padding: 15px 25px; border-bottom: 2px solid #E06C75; display: flex; justify-content: space-between; align-items: center; box-sizing: border-box; flex-shrink: 0;}
        .title { font-size: 24px; color: white; font-weight: bold; display: flex; align-items: center; gap: 10px; }
        
        .main-container { display: flex; flex: 1; overflow: hidden; }
        
        /* 左側のリスト */
        .list-panel { width: 350px; background: #21252B; border-right: 1px solid #3E4451; display: flex; flex-direction: column; overflow-y: auto; }
        .list-item { padding: 15px; border-bottom: 1px solid #3E4451; cursor: pointer; transition: background 0.2s; position: relative; }
        .list-item:hover { background: #2A2E37; }
        .list-item.active { background: #3E4451; border-left: 4px solid #61AFEF; }
        .list-name { font-size: 16px; font-weight: bold; color: #E5C07B; margin-bottom: 5px; }
        .list-preview { font-size: 13px; color: #ABB2BF; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .unread-badge { background: #E06C75; color: white; font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 10px; position: absolute; top: 15px; right: 15px; }

        /* 右側のチャット画面 */
        .chat-panel { flex: 1; background: #282C34; display: flex; flex-direction: column; }
        .chat-header { padding: 15px 25px; background: #21252B; border-bottom: 1px solid #3E4451; font-size: 18px; font-weight: bold; color: white; flex-shrink: 0;}
        
        .chat-history { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; }
        
        .msg-row { display: flex; flex-direction: column; max-width: 70%; }
        .msg-row.user { align-self: flex-start; }
        .msg-row.admin { align-self: flex-end; align-items: flex-end; }
        .msg-row.ai { align-self: flex-start; max-width: 85%; }
        
        .msg-info { font-size: 11px; color: #5C6370; margin-bottom: 3px; display: flex; gap: 8px; }
        .msg-bubble { padding: 10px 15px; border-radius: 8px; font-size: 14px; line-height: 1.4; word-wrap: break-word; }
        
        .msg-row.user .msg-bubble { background: #3E4451; color: white; border-top-left-radius: 0; }
        .msg-row.admin .msg-bubble { background: #61AFEF; color: white; border-top-right-radius: 0; }
        .msg-row.ai .msg-bubble { background: #1E2227; border: 1px solid #98C379; color: #98C379; border-top-left-radius: 0; }
        .msg-row.ai .msg-info { color: #98C379; font-weight: bold; }

        .chat-input-area { padding: 20px; background: #21252B; border-top: 1px solid #3E4451; display: flex; gap: 15px; flex-shrink: 0;}
        .chat-input { flex: 1; padding: 12px; border-radius: 6px; border: 1px solid #3E4451; background: #181A1F; color: white; font-size: 15px; outline: none; resize: none; font-family: sans-serif; }
        .send-btn { padding: 0 25px; border-radius: 6px; background: #61AFEF; color: white; border: none; font-weight: bold; font-size: 16px; cursor: pointer; transition: filter 0.2s; }
        .send-btn:hover { filter: brightness(1.1); }
        .send-btn:disabled { background: #5C6370; cursor: not-allowed; }
        
        .empty-state { flex: 1; display: flex; align-items: center; justify-content: center; font-size: 20px; color: #5C6370; font-weight: bold; }
    </style>
</head>
<body>

<div class="header">
    <div class="title">🚨 サポート＆AI報告センター</div>
    <div style="font-size: 14px; color: #98C379;">※AIが一次対応を自動で行います。総指揮殿はここで確認・個別返信が可能です。</div>
</div>

<div class="main-container">
    <div class="list-panel" id="userList">
        <!-- ユーザーリストがここに入ります -->
    </div>
    
    <div class="chat-panel" id="chatPanel" style="display: none;">
        <div class="chat-header" id="chatHeaderName">選択してください</div>
        <div class="chat-history" id="chatHistory">
            <!-- チャット履歴がここに入ります -->
        </div>
        <div class="chat-input-area">
            <textarea id="adminInput" class="chat-input" rows="2" placeholder="総指揮（天津飯）として直接返信する..."></textarea>
            <button id="sendBtn" class="send-btn" onclick="sendAdminChat()">送信</button>
        </div>
    </div>
    <div class="empty-state" id="emptyState">左側のリストから対応するプレイヤーを選択してください</div>
</div>

<script>
    let ws;
    let supportChats = {};
    let activeClientId = null;

    function connect() {
        let ws_protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
        ws = new WebSocket(ws_protocol + window.location.host + "/ws");
        ws.onmessage = (e) => {
            try {
                const msg = JSON.parse(e.data);
                if(msg.type === "init" || msg.type === "tick") {
                    supportChats = msg.data.support_chats || {};
                    renderUserList();
                    if(activeClientId) renderChatHistory(activeClientId);
                }
            } catch (err) { console.error(err); }
        };
        ws.onclose = () => setTimeout(connect, 1000);
    }
    connect();

    function renderUserList() {
        const listEl = document.getElementById('userList');
        let html = '';
        
        // 未読を上に、最新のやり取り順に並び替え
        let chatArray = Object.keys(supportChats).map(id => ({ id: id, ...supportChats[id] }));
        chatArray.sort((a, b) => {
            if (a.unread_admin !== b.unread_admin) return a.unread_admin ? -1 : 1;
            return 0; // 簡易ソート
        });

        if (chatArray.length === 0) {
            listEl.innerHTML = `<div style="padding: 20px; color:#5C6370; text-align:center;">現在、質問やSOSはありません。</div>`;
            return;
        }

        chatArray.forEach(chat => {
            let lastMsg = chat.messages.length > 0 ? chat.messages[chat.messages.length - 1].text : "メッセージなし";
            let activeClass = chat.id === activeClientId ? "active" : "";
            let unreadBadge = chat.unread_admin ? `<div class="unread-badge">新着・AI対応済</div>` : "";
            
            html += `
            <div class="list-item ${activeClass}" onclick="selectUser('${chat.id}')">
                ${unreadBadge}
                <div class="list-name">${chat.name}</div>
                <div class="list-preview">${lastMsg}</div>
            </div>`;
        });
        listEl.innerHTML = html;
    }

    function selectUser(clientId) {
        activeClientId = clientId;
        document.getElementById('emptyState').style.display = 'none';
        document.getElementById('chatPanel').style.display = 'flex';
        
        document.getElementById('chatHeaderName').innerText = supportChats[clientId].name + " 様からのSOS";
        
        // 既読にする
        if (supportChats[clientId].unread_admin) {
            ws.send(JSON.stringify({cmd: "mark_chat_read", val: {client_id: clientId}}));
        }
        
        renderUserList();
        renderChatHistory(clientId);
    }

    function renderChatHistory(clientId) {
        const histEl = document.getElementById('chatHistory');
        const chat = supportChats[clientId];
        if (!chat) return;

        let html = '';
        chat.messages.forEach(msg => {
            let rowClass = msg.sender; // 'user', 'ai', 'admin'
            let senderName = "";
            if(msg.sender === 'user') senderName = chat.name;
            if(msg.sender === 'ai') senderName = "🤖 AI副官の一次回答";
            if(msg.sender === 'admin') senderName = "👑 総指揮（あなた）";

            html += `
            <div class="msg-row ${rowClass}">
                <div class="msg-info"><span>${senderName}</span><span>${msg.time}</span></div>
                <div class="msg-bubble">${msg.text.replace(/\\n/g, '<br>')}</div>
            </div>`;
        });
        
        histEl.innerHTML = html;
        histEl.scrollTop = histEl.scrollHeight; // 自動スクロール
    }

    function sendAdminChat() {
        const inputEl = document.getElementById('adminInput');
        const text = inputEl.value.trim();
        if (!text || !activeClientId) return;

        ws.send(JSON.stringify({
            cmd: "send_support_chat", 
            val: {
                client_id: activeClientId, 
                msg: text, 
                is_admin: true // 総指揮からの直接返信フラグ
            }
        }));
        
        inputEl.value = '';
    }

    document.getElementById('adminInput').addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendAdminChat();
        }
    });
</script>
</body>
</html>"""

HTML_STAFF = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>参謀本部 (集結指示専用)</title>
    <style>
        body { background-color: #1e1e1e; color: #ABB2BF; font-family: 'Consolas', sans-serif; margin: 0; padding: 0; font-size: 13px; overflow-x: hidden; }
        .container { width: 100%; max-width: 1900px; padding: 15px; box-sizing: border-box; margin: auto; }
        .sticky-header { position: sticky; top: 0; left: 0; width: 100%; background: #1e1e1e; z-index: 100; padding: 15px 25px; border-bottom: 2px solid #3E4451; display: flex; align-items: center; justify-content: space-between; box-sizing: border-box;}
        .utc-main { font-size: 32px; color: white; font-weight: bold; display: flex; align-items: baseline; gap: 15px; }
        
        .status-bar { display: flex; align-items: center; background: #1E2227; padding: 6px 15px; border-radius: 6px; border: 1px solid #3E4451; gap: 15px; font-size: 13px; }
        .status-divider { width: 1px; height: 20px; background-color: #3E4451; }
        .status-val { font-size: 16px; font-weight: bold; margin: 0 4px; }

        /* 同盟選択画面のスタイル */
        .selection-card { background: #282C34; border: 2px solid #61AFEF; border-radius: 12px; padding: 40px; margin: 50px auto; width: 50%; max-width: 600px; min-width: 300px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.5);}
        .role-btn { padding: 15px 30px; font-size: 20px; width: 80%; margin: 15px auto; border-radius: 8px; border:none; font-weight:bold; cursor: pointer; display:block; transition: filter 0.2s;}
        .role-btn:hover { filter: brightness(1.1); }
        .btn-aln0 { background: #E5C07B; color: #282C34; }
        .btn-aln1 { background: #C678DD; color: white; }
        .btn-aln2 { background: #56B6C2; color: #282C34; }
        
        .pair-panel { background: #2A2E37; padding: 10px 15px; margin-bottom: 25px; border: 2px solid #E5C07B; border-radius: 8px; max-width: 800px; margin-left: auto; margin-right: auto;}
        .pair-cb-box { background: #1E2227; padding: 5px 10px; border-radius: 4px; border: 1px solid #3E4451; }

        .alliances-container { display: flex; gap: 15px; width: 100%; justify-content: center; }
        .alliance-col { width: 100%; max-width: 800px; background: #282C34; border: 1px solid #3E4451; border-radius: 8px; padding: 15px; display: flex; flex-direction: column; box-sizing: border-box;}
        .squads-flex { display: flex; flex-direction: column; gap: 15px; flex: 1; }
        
        .header-bar { display: flex; align-items: center; background: #2A2E37; padding: 8px 12px; border-radius: 6px; margin-bottom: 10px; border-left: 6px solid #61AFEF;}
        
        .row { display: flex; align-items: center; background: #21252B; margin-bottom: 4px; padding: 6px 8px; border-radius: 6px; gap: 6px; }
        
        .name-wrapper { position: relative; display: inline-block; }
        .online-dot { width: 8px; height: 8px; border-radius: 50%; background-color: #5C6370; position: absolute; top: -3px; left: -3px; border: 2px solid #21252B; z-index: 10; transition: background-color 0.3s; }
        .online-dot.active { background-color: #98C379; box-shadow: 0 0 4px #98C379; } 
        .online-dot.away { background-color: #E5C07B; box-shadow: 0 0 4px #E5C07B; } 
        
        .player-name-disp { width: 130px; background: transparent; border: none; color: #ABB2BF; font-weight: bold; padding: 6px 6px 6px 12px; font-size: 15px; pointer-events: none;}
        
        button { cursor: pointer; border: none; border-radius: 3px; font-weight: bold; color: white; }
        .btn-gray { background: #3E4451; } .btn-red { background: #E06C75; } .btn-green { background: #98C379; color: #282C34; }
        
        .timer-box { background: #1E2227; padding: 3px 5px; display: flex; align-items: center; border: 1px solid #3E4451; border-radius: 4px;}
        .val-txt { font-size: 18px; color: #E5C07B; font-weight: bold; margin: 0 2px; width: 14px; text-align: center;}
        .colon { color: #E5C07B; font-size: 16px; font-weight: bold; width: 6px; text-align: center; }
        
        .sub-box { background: #1E2227; padding: 3px 5px; display: flex; align-items: center; border: 1px solid #3E4451; border-left:none; border-radius: 0 4px 4px 0;}
        .sub-disp { font-size: 14px; color: #C678DD; font-weight: bold; width: 42px; text-align: right; margin-right:4px;}
        .sub-val-txt { font-size: 12px; color: #ABB2BF; font-weight: bold; width: 10px; text-align: center;}
        .updown-col { display: flex; flex-direction: column; align-items: center; gap: 1px;}
        .sub-updown-btn { width: 12px; height: 10px; font-size: 7px; padding: 0;}
        
        .target-box { color: #ABB2BF; font-size: 12px; padding-left: 8px; width: 150px; display: flex; flex-direction: column; line-height: 1.2; }
        
        .gorei-panel { background: #2A2E37; border: 1px solid #56B6C2; padding: 8px 12px; border-radius: 0 4px 4px 4px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; border-top: none;}
        .squad-title { font-size: 14px; font-weight: bold; padding: 6px 12px; border-radius: 4px 4px 0 0; display: inline-block; background: #3E4451; color: white; margin-top: 10px; display: flex; justify-content: space-between; align-items: center;}

        /* ★ チャットトレイのスタイル */
        .chat-tray { position: fixed; bottom: 20px; right: 20px; width: 350px; background: #282C34; border: 2px solid #E06C75; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); display: flex; flex-direction: column; z-index: 1000; }
        .chat-tray-header { background: #E06C75; color: white; padding: 8px 12px; font-weight: bold; border-radius: 5px 5px 0 0; display: flex; justify-content: space-between; align-items: center; font-size: 14px;}
        .chat-tray-body { max-height: 250px; overflow-y: auto; padding: 10px; display: flex; flex-direction: column; gap: 8px; }
        .chat-msg { background: #1E2227; border-left: 3px solid #61AFEF; padding: 8px; border-radius: 4px; font-size: 13px; }
        .chat-msg-time { color: #ABB2BF; font-size: 11px; margin-right: 5px; }
        .chat-msg-name { color: #E5C07B; font-weight: bold; }
        .chat-msg-text { color: white; margin-top: 4px; }
    </style>
</head>
<body>

<div class="sticky-header">
    <div class="utc-main">
        <span id="utc">UTC --:--:--</span>
        <span id="offsetDisp" style="font-size: 14px; font-weight: normal; color: #98C379;">(同期中...)</span>
    </div>
    
    <div style="display: flex; align-items: center; gap: 20px;">
        <button class="btn-gray" style="padding: 8px 16px; font-size: 13px; border-radius: 6px;" onclick="send('toggle_rally')" id="rallyToggleBtn">⏱ 5分(切替)</button>
        <div class="status-bar">
            <div style="color: #ABB2BF; font-weight: bold; display: flex; align-items: center;">
                <span style="color:#ffffff; margin-right:8px;">[全同盟]</span>
                👑集結主:<span class="status-val" style="color:#E5C07B;" id="countLeader_total">0</span> 
                🏇乗り手:<span class="status-val" style="color:#C678DD;" id="countRider_total">0</span>
            </div>
            <div class="status-divider"></div>
            <div style="color: #ABB2BF; font-weight: bold; display: flex; align-items: center;">
                <span id="lbl_count_aln0" style="color:#61AFEF; margin-right:5px; width:30px;">APL</span>
                👑<span class="status-val" style="color:#E5C07B;" id="countLeader_aln0">0</span> 
                🏇<span class="status-val" style="color:#C678DD;" id="countRider_aln0">0</span>
            </div>
            <div class="status-divider"></div>
            <div style="color: #ABB2BF; font-weight: bold; display: flex; align-items: center;">
                <span id="lbl_count_aln1" style="color:#61AFEF; margin-right:5px; width:30px;">PKD</span>
                👑<span class="status-val" style="color:#E5C07B;" id="countLeader_aln1">0</span> 
                🏇<span class="status-val" style="color:#C678DD;" id="countRider_aln1">0</span>
            </div>
            <div class="status-divider"></div>
            <div style="color: #ABB2BF; font-weight: bold; display: flex; align-items: center;">
                <span id="lbl_count_aln2" style="color:#61AFEF; margin-right:5px; width:30px;">MTC</span>
                👑<span class="status-val" style="color:#E5C07B;" id="countLeader_aln2">0</span> 
                🏇<span class="status-val" style="color:#C678DD;" id="countRider_aln2">0</span>
            </div>
        </div>
    </div>
</div>

<!-- 同盟選択画面 -->
<div class="container" id="selection_container">
    <div class="selection-card">
        <h2 style="color: #61AFEF; font-size: 24px; margin-top: 0;">担当する同盟を選択</h2>
        <p style="color: #ABB2BF; font-size: 14px; margin-bottom: 25px;">※選択した同盟の集結指示パネルのみが表示されます。</p>
        <button class="role-btn btn-aln0" onclick="selectStaffAlliance(0)" id="btn_sel_0">APL 参謀</button>
        <button class="role-btn btn-aln1" onclick="selectStaffAlliance(1)" id="btn_sel_1">PKD 参謀</button>
        <button class="role-btn btn-aln2" onclick="selectStaffAlliance(2)" id="btn_sel_2">MTC 参謀</button>
    </div>
</div>

<!-- メイン画面（選択後に表示） -->
<div class="container" id="staff_main" style="display:none;">
    <!-- 参謀用：ペアリングパネル -->
    <div class="pair-panel" id="pairing_panel_content"></div>

    <!-- 参謀用：同盟ごとの号令・状態確認パネル -->
    <div id="alliances_container" class="alliances-container"></div>
</div>

<!-- ★ チャットトレイ -->
<div class="chat-tray" id="chatTray" style="display:none;">
    <div class="chat-tray-header">
        <span>🚨 緊急報告・SOS トレイ</span>
        <button style="background:transparent; color:white; border:none; cursor:pointer; font-size:16px;" onclick="document.getElementById('chatTray').style.display='none'">✖</button>
    </div>
    <div class="chat-tray-body" id="chatTrayBody"></div>
</div>

<script>
    let ws; let isBuilt = false; let timeOffset = 0; 
    let globalLocalState = null; 
    let myStaffAllianceIdx = -1; 
    let lastChatCount = 0; // ★ チャット件数の管理

    function getSyncedNow() { return new Date(Date.now() + timeOffset); }
    function send(cmd, idx=null, val=null) { if(ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({cmd: cmd, idx: idx, val: val})); }

    function selectStaffAlliance(idx) {
        myStaffAllianceIdx = idx;
        document.getElementById('selection_container').style.display = 'none';
        document.getElementById('staff_main').style.display = 'block';
        if(isBuilt && globalLocalState) {
            buildDOM();
            updateUI(globalLocalState, document.getElementById('utc').innerText.replace("UTC ", ""));
        }
    }

    function buildRow(i) {
        return `
        <div class="row">
            <div class="name-wrapper">
                <div id="dot_${i}" class="online-dot" title="未登録"></div>
                <div class="player-name-disp" id="name_disp_${i}">---</div>
            </div>
            
            <div class="timer-box" style="margin-left:auto;">
                <div class="val-txt" id="m10_${i}">0</div><div class="val-txt" id="m1_${i}">0</div>
                <div class="colon">:</div>
                <div class="val-txt" id="s10_${i}">0</div><div class="val-txt" id="s1_${i}">0</div>
            </div>
            <div class="sub-box">
                <div class="sub-disp" id="subdisp_${i}">00:00</div>
            </div>
            <div class="target-box">
                <span id="dispatch_${i}" style="color:#E5C07B; font-weight:bold;"></span>
                <span id="tgt_${i}">▶--:--:--</span>
            </div>
        </div>`;
    }

    function buildGoreiPanel(squadId, color) {
        return `
        <div class="gorei-panel" style="border-color: ${color};">
            <div style="display:flex; flex-direction:column; gap:6px; flex:1;">
                <div style="display:flex; align-items:center; justify-content:space-between;">
                    <div style="display:flex; align-items:center; gap:5px;">
                        <span style="color:#ABB2BF; font-size:11px;">猶予+</span>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei', ${squadId}, 10)">▲</button><div class="sub-val-txt" id="goreiE10_${squadId}" style="color:#E5C07B;">1</div><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei', ${squadId}, -10)">▼</button></div>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei', ${squadId}, 1)">▲</button><div class="sub-val-txt" id="goreiE1_${squadId}" style="color:#E5C07B;">5</div><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei', ${squadId}, -1)">▼</button></div>
                        <span style="color:#ABB2BF; font-size:11px;">秒</span>
                    </div>
                    <button style="background: ${color}; color: white; padding: 4px 10px; font-size:12px; border-radius:4px;" onclick="send('fire_gorei', ${squadId})">即時号令 (今のﾀｲﾐﾝｸﾞ)</button>
                </div>
                <div style="display:flex; align-items:center; justify-content:space-between; background:#1E2227; padding:4px 6px; border-radius:4px; border:1px solid #3E4451;">
                    <span style="color:#ABB2BF; font-size:11px;">着弾:</span>
                    <div style="display:flex; align-items:center;">
                        <span id="goreiTargetHH_${squadId}" style="font-size:16px; color:#61AFEF; font-weight:bold;">00</span><span style="color:#61AFEF; font-weight:bold; margin:0 2px;">:</span>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei_target', ${squadId}, 600)">▲</button><div class="sub-val-txt" id="goreiTargetM10_${squadId}" style="color:#61AFEF; font-size:16px;">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei_target', ${squadId}, -600)">▼</button></div>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei_target', ${squadId}, 60)">▲</button><div class="sub-val-txt" id="goreiTargetM1_${squadId}" style="color:#61AFEF; font-size:16px;">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei_target', ${squadId}, -60)">▼</button></div><span style="color:#61AFEF; font-weight:bold; margin:0 2px;">:</span>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei_target', ${squadId}, 10)">▲</button><div class="sub-val-txt" id="goreiTargetS10_${squadId}" style="color:#61AFEF; font-size:16px;">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei_target', ${squadId}, -10)">▼</button></div>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei_target', ${squadId}, 1)">▲</button><div class="sub-val-txt" id="goreiTargetS1_${squadId}" style="color:#61AFEF; font-size:16px;">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_gorei_target', ${squadId}, -1)">▼</button></div>
                    </div>
                    <button style="background: #98C379; color: #282C34; padding: 4px 6px; font-size:11px; border-radius:4px; font-weight:bold;" onclick="send('fire_gorei_fixed', ${squadId})">着弾指定号令</button>
                </div>
            </div>
            <div style="display:flex; flex-direction:column; gap:8px; margin-left:5px; align-items:center;">
                <button class="btn-red" style="padding: 6px 12px; font-size:12px; border-radius:4px;" onclick="send('cancel_gorei', ${squadId})">解除</button>
                <div id="goreiState_${squadId}" style="color:#E5C07B; font-size:11px; width:45px; text-align:center;"></div>
            </div>
        </div>`;
    }

    function buildPairingPanel(a) {
        let defaultNames = ["APL", "PKD", "MTC"];
        let cbHtml = `
            <div class="pair-cb-box">
                <div style="color:#61AFEF; font-weight:bold; margin-bottom:5px; font-size:12px;" id="pair_aln_label_${a}">${defaultNames[a]}</div>
                <label style="cursor:pointer; display:block; color:#C678DD;"><input type="checkbox" id="pair_cb_${a*2}" onclick="send('toggle_pair_squad', ${a*2})"> 第1班</label>
                <label style="cursor:pointer; display:block; color:#56B6C2; margin-top:3px;"><input type="checkbox" id="pair_cb_${a*2+1}" onclick="send('toggle_pair_squad', ${a*2+1})"> 第2班</label>
            </div>
        `;
        
        let html = `
        <h3 style="color:#E5C07B; margin-top:0; margin-bottom:10px;">🔗 担当同盟ペアリング号令（1班・2班 同時着弾）</h3>
        <div style="display:flex; align-items:center; gap:20px;">
            <div style="display:flex; gap:10px;">${cbHtml}</div>
            <div style="flex:1; display:flex; flex-direction:column; gap:10px; border-left:1px solid #3E4451; padding-left:20px;">
                <div style="display:flex; align-items:center; justify-content:space-between;">
                    <div style="display:flex; align-items:center; gap:5px;">
                        <span style="color:#ABB2BF; font-size:13px;">猶予+</span>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei', null, 10)">▲</button><div class="sub-val-txt" id="pairGoreiE10" style="color:#E5C07B; font-size:14px;">1</div><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei', null, -10)">▼</button></div>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei', null, 1)">▲</button><div class="sub-val-txt" id="pairGoreiE1" style="color:#E5C07B; font-size:14px;">5</div><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei', null, -1)">▼</button></div>
                        <span style="color:#ABB2BF; font-size:13px;">秒</span>
                    </div>
                    <button style="background: #E5C07B; color: #282C34; padding: 6px 20px; font-size:15px; font-weight:bold; border-radius:4px;" onclick="send('fire_pair_gorei')">即時号令 (今のﾀｲﾐﾝｸﾞ)</button>
                </div>
                <div style="display:flex; align-items:center; justify-content:space-between; background:#1E2227; padding:6px 10px; border-radius:4px; border:1px solid #3E4451;">
                    <span style="color:#ABB2BF; font-size:13px;">ペア着弾(UTC):</span>
                    <div style="display:flex; align-items:center;">
                        <span id="pairGoreiTargetHH" style="font-size:18px; color:#E5C07B; font-weight:bold;">00</span><span style="color:#E5C07B; font-weight:bold; margin:0 3px;">:</span>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei_target', null, 600)">▲</button><div class="sub-val-txt" id="pairGoreiTargetM10" style="color:#E5C07B; font-size:18px; width:12px;">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei_target', null, -600)">▼</button></div>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei_target', null, 60)">▲</button><div class="sub-val-txt" id="pairGoreiTargetM1" style="color:#E5C07B; font-size:18px;">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei_target', null, -60)">▼</button></div><span style="color:#E5C07B; font-weight:bold; margin:0 3px;">:</span>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei_target', null, 10)">▲</button><div class="sub-val-txt" id="pairGoreiTargetS10" style="color:#E5C07B; font-size:18px; width:12px;">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei_target', null, -10)">▼</button></div>
                        <div class="updown-col"><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei_target', null, 1)">▲</button><div class="sub-val-txt" id="pairGoreiTargetS1" style="color:#E5C07B; font-size:18px;">0</div><button class="btn-gray sub-updown-btn" onclick="send('mod_pair_gorei_target', null, -1)">▼</button></div>
                    </div>
                    <button style="background: #98C379; color: #282C34; padding: 6px 20px; font-size:14px; font-weight:bold; border-radius:4px;" onclick="send('fire_pair_gorei_fixed')">着弾指定号令</button>
                </div>
            </div>
            <div style="display:flex; flex-direction:column; gap:10px; align-items:center; margin-left:15px;">
                <button class="btn-red" style="padding: 10px 20px; font-size:14px; border-radius:4px;" onclick="send('cancel_pair_gorei')">一斉解除</button>
            </div>
        </div>`;
        document.getElementById('pairing_panel_content').innerHTML = html;
    }

    function buildAlliancePanel(a, role, data) {
        let roleStr = role === 'occupy' ? '<span style="color:#98C379;">🟢 占領同盟</span>' : '<span style="color:#E06C75;">🔴 攻撃同盟</span>';
        let panelHtml = `
            <div class="header-bar">
                <div style="display:flex; align-items:center; gap:10px; font-size:18px; font-weight:bold; color:white;">
                    <span id="aln_name_disp_${a}">同盟名</span> 
                    <span style="font-size:14px;">${roleStr}</span>
                </div>
            </div>
        `;

        panelHtml += `<div class="squads-flex">`;
        
        let s1Title = `
            <div class="squad-title" style="border-bottom: 2px solid #C678DD; color: #C678DD; width: 100%; box-sizing: border-box; display:flex; justify-content:space-between; align-items:center;">
                第1班 (連撃部隊)
            </div>`;
        panelHtml += `
            <div class="squad-block">
                ${s1Title}
                ${buildGoreiPanel(a*2, '#C678DD')}
                <div id="rows_squad_${a*2}"></div>
            </div>`;

        let s2Title = `
            <div class="squad-title" style="border-bottom: 2px solid #56B6C2; color: #56B6C2; width: 100%; box-sizing: border-box; display:flex; justify-content:space-between; align-items:center;">
                第2班 (連撃部隊)
            </div>`;
        panelHtml += `
            <div class="squad-block">
                ${s2Title}
                ${buildGoreiPanel(a*2+1, '#56B6C2')}
                <div id="rows_squad_${a*2+1}"></div>
            </div>
        </div>`;
        return panelHtml;
    }

    function buildDOM() {
        if(myStaffAllianceIdx === -1) return; 

        buildPairingPanel(myStaffAllianceIdx);

        let initRole = globalLocalState ? globalLocalState.alliance_roles[myStaffAllianceIdx] : (myStaffAllianceIdx === 0 ? 'occupy' : 'attack');
        
        let alnHtml = `<div class="alliance-col" style="width: 100%; max-width: 800px; margin: 0 auto;" id="alliance_container_${myStaffAllianceIdx}">${buildAlliancePanel(myStaffAllianceIdx, initRole, globalLocalState)}</div>`;
        document.getElementById('alliances_container').innerHTML = alnHtml;

        let sq1 = '', sq2 = '';
        for(let i=0; i<6; i++) {
            sq1 += buildRow(6 + myStaffAllianceIdx*12 + i);
            sq2 += buildRow(12 + myStaffAllianceIdx*12 + i);
        }
        document.getElementById(`rows_squad_${myStaffAllianceIdx*2}`).innerHTML = sq1;
        document.getElementById(`rows_squad_${myStaffAllianceIdx*2+1}`).innerHTML = sq2;
    }

    function connect() {
        let ws_protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
        ws = new WebSocket(ws_protocol + window.location.host + "/ws");
        ws.onmessage = (e) => {
            try {
                const msg = JSON.parse(e.data); const data = msg.data;
                globalLocalState = data; 
                if(msg.server_timestamp) {
                    timeOffset = msg.server_timestamp - Date.now();
                    let elOffset = document.getElementById('offsetDisp');
                    if(elOffset) elOffset.innerText = `(補正: ${timeOffset > 0 ? "+" : ""}${(timeOffset/1000).toFixed(2)}秒)`;
                }
                if(msg.type === "init") { 
                    isBuilt = true;
                    document.getElementById('btn_sel_0').innerText = (data.alliance_names[0] || "APL") + " 参謀";
                    document.getElementById('btn_sel_1').innerText = (data.alliance_names[1] || "PKD") + " 参謀";
                    document.getElementById('btn_sel_2').innerText = (data.alliance_names[2] || "MTC") + " 参謀";
                    if(myStaffAllianceIdx !== -1) buildDOM();
                }
                if(!isBuilt) return;
                updateUI(data, msg.utc);
            } catch (err) { console.error(err); }
        };
        ws.onclose = () => setTimeout(connect, 1000);
    }
    connect();

    function updateUI(data, utcTime) {
        document.getElementById('utc').innerText = "UTC " + utcTime;
        
        if (myStaffAllianceIdx === -1) {
            document.getElementById('btn_sel_0').innerText = (data.alliance_names[0] || "APL") + " 参謀";
            document.getElementById('btn_sel_1').innerText = (data.alliance_names[1] || "PKD") + " 参謀";
            document.getElementById('btn_sel_2').innerText = (data.alliance_names[2] || "MTC") + " 参謀";
        }
        
        document.getElementById('countLeader_total').innerText = data.online_counts.total.leader;
        document.getElementById('countRider_total').innerText = data.online_counts.total.rider;
        
        for(let i=0; i<3; i++) {
            let lbl = document.getElementById(`lbl_count_aln${i}`);
            if(lbl) lbl.innerText = data.alliance_names[i] || ["APL", "PKD", "MTC"][i];
            
            let lCount = document.getElementById(`countLeader_aln${i}`);
            if(lCount) lCount.innerText = data.online_counts[`aln${i}`].leader;
            
            let rCount = document.getElementById(`countRider_aln${i}`);
            if(rCount) rCount.innerText = data.online_counts[`aln${i}`].rider;
        }

        let now = getSyncedNow().getTime();

        if (myStaffAllianceIdx !== -1) {
            let a = myStaffAllianceIdx;
            let elNameDisp = document.getElementById(`aln_name_disp_${a}`);
            if(elNameDisp) elNameDisp.innerText = data.alliance_names[a];

            let alnLabel = document.getElementById(`pair_aln_label_${a}`);
            if(alnLabel) alnLabel.innerText = data.alliance_names[a] || ["APL", "PKD", "MTC"][a];
            
            let cb = document.getElementById(`pair_cb_${a*2}`);
            if(cb) cb.checked = data.pair_selected[a*2];
            let cb2 = document.getElementById(`pair_cb_${a*2+1}`);
            if(cb2) cb2.checked = data.pair_selected[a*2+1];
            
            document.getElementById('pairGoreiE10').innerText = Math.floor(data.pair_gorei_offset / 10);
            document.getElementById('pairGoreiE1').innerText = data.pair_gorei_offset % 10;

            let pairMarches = [];
            for (let s = 0; s < 6; s++) {
                if (data.pair_selected[s]) {
                    let startIdx = 6 + s * 6;
                    for (let i = startIdx; i < startIdx + 6; i++) {
                        if (data.timers[i].name !== "") pairMarches.push(data.timers[i].sub_set);
                    }
                }
            }
            let pairMaxMarch = pairMarches.length > 0 ? Math.max(...pairMarches) : 0;
            let minPairTgtTs = now + (data.pair_gorei_offset + data.default_rally + pairMaxMarch) * 1000;
            let pairDispTs = data.pair_fixed_target ? data.pair_fixed_target * 1000 : minPairTgtTs;
            let pairD = new Date(pairDispTs);
            
            let pgHH = document.getElementById('pairGoreiTargetHH');
            if(pgHH) {
                pgHH.innerText = String(pairD.getUTCHours()).padStart(2, '0');
                document.getElementById('pairGoreiTargetM10').innerText = Math.floor(pairD.getUTCMinutes() / 10);
                document.getElementById('pairGoreiTargetM1').innerText = pairD.getUTCMinutes() % 10;
                document.getElementById('pairGoreiTargetS10').innerText = Math.floor(pairD.getUTCSeconds() / 10);
                document.getElementById('pairGoreiTargetS1').innerText = pairD.getUTCSeconds() % 10;
                
                let pairColor = data.pair_fixed_target ? "#E5C07B" : "#61AFEF";
                pgHH.style.color = pairColor;
                document.getElementById('pairGoreiTargetM10').style.color = pairColor;
                document.getElementById('pairGoreiTargetM1').style.color = pairColor;
                document.getElementById('pairGoreiTargetS10').style.color = pairColor;
                document.getElementById('pairGoreiTargetS1').style.color = pairColor;
            }

            for(let s = a*2; s <= a*2+1; s++) {
                let gE10 = document.getElementById(`goreiE10_${s}`);
                if(!gE10) continue;
                gE10.innerText = Math.floor(data.gorei_offsets[s] / 10);
                document.getElementById(`goreiE1_${s}`).innerText = data.gorei_offsets[s] % 10;
                
                let startIdx = 6 + s * 6;
                let marches = [];
                for(let i=startIdx; i<startIdx+6; i++) { if(data.timers[i].name !== "") marches.push(data.timers[i].sub_set); }
                let maxMarch = marches.length > 0 ? Math.max(...marches) : 0;
                
                let minTgtTs = now + (data.gorei_offsets[s] + data.default_rally + maxMarch) * 1000;
                let dispTs = data.gorei_fixed_targets[s] ? data.gorei_fixed_targets[s] * 1000 : minTgtTs;
                let d = new Date(dispTs);
                
                document.getElementById(`goreiTargetHH_${s}`).innerText = String(d.getUTCHours()).padStart(2, '0');
                document.getElementById(`goreiTargetM10_${s}`).innerText = Math.floor(d.getUTCMinutes() / 10);
                document.getElementById(`goreiTargetM1_${s}`).innerText = d.getUTCMinutes() % 10;
                document.getElementById(`goreiTargetS10_${s}`).innerText = Math.floor(d.getUTCSeconds() / 10);
                document.getElementById(`goreiTargetS1_${s}`).innerText = d.getUTCSeconds() % 10;
                
                let color = data.gorei_fixed_targets[s] ? "#E5C07B" : "#61AFEF";
                document.getElementById(`goreiTargetHH_${s}`).style.color = color;
                document.getElementById(`goreiTargetM10_${s}`).style.color = color;
                document.getElementById(`goreiTargetM1_${s}`).style.color = color;
                document.getElementById(`goreiTargetS10_${s}`).style.color = color;
                document.getElementById(`goreiTargetS1_${s}`).style.color = color;

                let isGoreiActive = data.timers.slice(startIdx, startIdx+6).some(t => t.state === 4);
                document.getElementById(`goreiState_${s}`).innerText = isGoreiActive ? "待機中" : "";
            }

            for(let i = 6 + a*12; i < 6 + a*12 + 12; i++) {
                let t = data.timers[i]; 
                
                let elNameDisp = document.getElementById('name_disp_'+i);
                if(!elNameDisp) continue;
                elNameDisp.innerText = t.name !== "" ? t.name : "---";
                
                let dot = document.getElementById('dot_'+i);
                if(dot) {
                    dot.classList.remove('active', 'away');
                    if(t.name !== "") {
                        if (t.online) { dot.classList.add('active'); dot.title = "オンライン"; } 
                        else if (t.device_mode === '1device') { dot.classList.add('away'); dot.title = "1端末(ゲーム中)"; } 
                        else { dot.title = "オフライン"; }
                    } else { dot.title = "未登録"; }
                }

                const ms = t.sec;
                document.getElementById('m10_'+i).innerText = Math.floor(ms/600); 
                document.getElementById('m1_'+i).innerText = Math.floor((ms%600)/60);
                document.getElementById('s10_'+i).innerText = Math.floor((ms%60)/10); 
                document.getElementById('s1_'+i).innerText = Math.floor(ms%10);
                
                document.getElementById('subdisp_'+i).innerText = t.state === 2 ? formatSec(t.sub_sec) : "00:00";
                
                let tgtStr = "▶--:--:--"; let dispatchStr = ""; let adjUTC = now + t.off;
                
                if(t.state === 4) {
                    let waitSec = Math.max(0, (new Date(t.start_at).getTime() - now) / 1000);
                    dispatchStr = `🚀出征まで:${formatSec(waitSec)}`;
                    let tgtD = new Date(adjUTC + (waitSec + data.default_rally + t.sub_set) * 1000);
                    tgtStr = `▶${String(tgtD.getUTCHours()).padStart(2,'0')}:${String(tgtD.getUTCMinutes()).padStart(2,'0')}:${String(tgtD.getUTCSeconds()).padStart(2,'0')}`;
                } else if(t.state === 1) {
                    let tgtD = new Date(adjUTC + (t.sec + t.sub_set) * 1000);
                    tgtStr = `▶${String(tgtD.getUTCHours()).padStart(2,'0')}:${String(tgtD.getUTCMinutes()).padStart(2,'0')}:${String(tgtD.getUTCSeconds()).padStart(2,'0')}`;
                } else if(t.state === 2) {
                    let tgtD = new Date(t.frozen_target);
                    tgtStr = `▶${String(tgtD.getUTCHours()).padStart(2,'0')}:${String(tgtD.getUTCMinutes()).padStart(2,'0')}:${String(tgtD.getUTCSeconds()).padStart(2,'0')}`;
                }
                document.getElementById('dispatch_'+i).innerText = dispatchStr;
                document.getElementById('tgt_'+i).innerText = tgtStr;
            }
        }

        // ★ チャットの更新処理
        if (data.chat_messages) {
            let chatTray = document.getElementById('chatTray');
            let chatBody = document.getElementById('chatTrayBody');
            
            if (data.chat_messages.length > 0) {
                // 新着メッセージがあればトレイを表示
                if (data.chat_messages.length > lastChatCount) {
                    chatTray.style.display = 'flex';
                    lastChatCount = data.chat_messages.length;
                }
                
                let chatHtml = "";
                data.chat_messages.forEach(msg => {
                    chatHtml += `
                    <div class="chat-msg">
                        <div>
                            <span class="chat-msg-time">${msg.time}</span>
                            <span class="chat-msg-name">${msg.name}</span>
                        </div>
                        <div class="chat-msg-text">${msg.msg}</div>
                    </div>`;
                });
                
                if (chatBody.innerHTML !== chatHtml) {
                    chatBody.innerHTML = chatHtml;
                    chatBody.scrollTop = chatBody.scrollHeight; // 一番下へスクロール
                }
            }
        }
    }

    function formatSec(s) { 
        if (s < 0) s = 0; const m = Math.floor(s/60), ss = Math.floor(s%60); 
        return `${String(m).padStart(2,'0')}:${String(ss).padStart(2,'0')}`; 
    }
</script>
</body>
</html>"""

# =====================================================================
# 🛠️ サーバー初期状態の設定
# =====================================================================
state = {
    "support_chats": {},
    "timers": [{"name": "", "sec": 300, "state": 0} for i in range(42)]
}
connections = {}

# =====================================================================
# 🧠 AI副官（Gemini）自動返信機能
# =====================================================================
async def generate_ai_reply(client_id, user_msg):
    if not GEMINI_API_KEY:
        ai_text = (
            "【設定不足】環境変数 GEMINI_API_KEY が未設定です。"
            "キーはコードやGitに含めず、PCの環境変数またはローカルのみの設定で渡してください。"
        )
    else:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            prompt = f"あなたはホワサバの有能な副官です。天津飯（総指揮）をサポートしています。短く返信して。客: {user_msg}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            data_bytes = json.dumps(payload).encode('utf-8')

            def call_raw_api():
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                headers = {'Content-Type': 'application/json'}
                req = urllib.request.Request(url, data=data_bytes, headers=headers, method='POST')
                with urllib.request.urlopen(req, context=ctx, timeout=10) as res:
                    res_data = json.loads(res.read().decode('utf-8'))
                    return res_data['candidates'][0]['content']['parts'][0]['text']

            loop = asyncio.get_running_loop()
            ai_text = await loop.run_in_executor(None, call_raw_api)

        except Exception as e:
            ai_text = f"【AI副官 起動待機中】Googleの準備を待っています。数分後に再度お試しください。詳細: {str(e)}"
        
    now_dt = datetime.now(timezone.utc) + timedelta(hours=9)
    time_str = now_dt.strftime("%H:%M")
    if client_id in state["support_chats"]:
        state["support_chats"][client_id]["messages"].append({"sender": "ai", "text": ai_text, "time": time_str})
        state["support_chats"][client_id]["unread_admin"] = True

# =====================================================================
# 📡 リアルタイム通信基盤
# =====================================================================
async def broadcast():
    payload = {"type": "tick", "data": state, "utc": datetime.now(timezone.utc).strftime("%H:%M:%S")}
    for ws in list(connections.keys()):
        try: await ws.send_json(payload)
        except: pass

async def broadcast_loop():
    while True: 
        await broadcast()
        await asyncio.sleep(0.25)

@asynccontextmanager
async def lifespan(app: FastAPI): 
    task = asyncio.create_task(broadcast_loop())
    yield
    task.cancel()

# =====================================================================
# 🚀 FastAPI 本体の設定
# =====================================================================
app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# 📱 1. 一般プレイヤー用画面
@app.get("/")
async def get_player():
    return HTMLResponse(content=HTML_PLAYER)

# 👑 2. 総指揮（天津飯）用画面
@app.get("/admin_hq_777")
async def get_admin():
    return HTMLResponse(content=HTML_ADMIN)

# ✉️ 3. サポート＆AI報告センター画面
@app.get("/support_hq_3301")
async def get_support():
    return HTMLResponse(content=HTML_SUPPORT)

# ⚔️ 4. 参謀本部（集結指示）画面 ← ★今回追加した抜け漏れルート
@app.get("/staff_hq_555")
async def get_staff():
    return HTMLResponse(content=HTML_STAFF)

# ⚡ WebSocket通信の処理
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections[websocket] = {"id": str(uuid.uuid4())}
    try:
        await websocket.send_json({"type": "init", "data": state})
        while True:
            data = await websocket.receive_json()
            cmd = data.get("cmd")
            val = data.get("val")
            if cmd == "send_support_chat":
                cid = val.get("client_id", "unknown")
                name = val.get("name", "名無し")
                msg = val.get("msg", "")
                
                if cid not in state["support_chats"]: 
                    state["support_chats"][cid] = {"name": name, "messages": [], "unread_admin": True}
                
                time_str = (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%H:%M")
                is_admin = val.get("is_admin")
                
                state["support_chats"][cid]["messages"].append({
                    "sender": "admin" if is_admin else "user", 
                    "text": msg, 
                    "time": time_str
                })
                
                if is_admin:
                    state["support_chats"][cid]["unread_admin"] = False
                else:
                    state["support_chats"][cid]["unread_admin"] = True
                    asyncio.create_task(generate_ai_reply(cid, msg))
            
            elif cmd == "mark_chat_read":
                cid = val.get("client_id")
                if cid in state["support_chats"]:
                    state["support_chats"][cid]["unread_admin"] = False
                    
            await broadcast()
            
    except WebSocketDisconnect:
        if websocket in connections: 
            del connections[websocket]

# =====================================================================
# 🔥 サーバー起動用のおまじない
# =====================================================================
if __name__ == "__main__":
    # appを直接指定することで、ファイル名を何に変更しても動くようになります
    uvicorn.run(app, host="127.0.0.1", port=8000)