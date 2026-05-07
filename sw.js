let timers = [];
let defaultRally = 300;
let myName = "";
let myRole = null;
let myMarchSec = 0;
let timeOffset = 0;
let delayTargetIdx = -1;
let insertTargetIdx = -1;

function getSyncedNow() {
    return new Date(Date.now() + timeOffset).getTime();
}

function checkTimers() {
    let now = getSyncedNow();
    if (myRole === 'rider') {
        let insT = getInsTargetTime(now);
        if (insT) checkAndTriggerVoice((insT - now) / 1000 - myMarchSec, "ins");
        let swpT = getSwapTargetTime(now);
        if (swpT) checkAndTriggerVoice((swpT - now) / 1000 - myMarchSec, "swap");
    } else if (myRole === 'leader' && myName !== "") {
        timers.slice(3, 6).forEach((t) => {
            if (t.name !== myName) return;
            // ★修正: リーダーは「集結ボタンまで(state 4)」の時のみカウントダウンする
            // 集結中(1)や行軍中(2)はすでにボタンを押しているので鳴らさない
            if (t.state === 4) {
                let wait = (new Date(t.start_at).getTime() - now) / 1000;
                checkAndTriggerVoice(wait, "leader");
            }
        });
    }
}

function checkAndTriggerVoice(remSec, type) {
    let r = Math.floor(remSec);
    if (r === 18 || (r > 0 && r <= 10) || r === 0) {
        clients.matchAll().then(clients => {
            clients.forEach(client => {
                client.postMessage({ type: 'playVoice', remSec: r, roleType: type });
            });
        });
    }
}

function getInsTargetTime(now) {
    let idx = insertTargetIdx;
    if (idx >= 0 && timers[idx] && timers[idx].state !== 0) return getT(timers[idx], now, defaultRally) - 1000;
    let arr = [];
    for(let i=0; i<3; i++) { let t = getT(timers[i], now, defaultRally); if(t) arr.push(t); }
    return arr.length ? Math.max(...arr) - 1000 : null;
}
function getSwapTargetTime(now) {
    let arr = [];
    for(let i=3; i<6; i++) { let t = getT(timers[i], now, defaultRally); if(t) arr.push(t); }
    return arr.length ? Math.max(...arr) + 10000 : null; 
}
function getT(t, now, def) {
    if(!t || t.state === 0) return null;
    if(t.state === 4) return new Date(t.start_at).getTime() + (def + t.sub_set) * 1000;
    if(t.state === 1) return new Date(t.end).getTime();
    if(t.state === 2) return new Date(t.end).getTime();
    return null;
}

self.addEventListener('message', (e) => {
    if (e.data.type === 'updateState') {
        timers = e.data.timers; defaultRally = e.data.defaultRally; myName = e.data.myName;
        myRole = e.data.myRole; myMarchSec = e.data.myMarchSec; timeOffset = e.data.timeOffset;
        insertTargetIdx = e.data.insertTargetIdx; delayTargetIdx = e.data.delayTargetIdx;
    }
});
setInterval(checkTimers, 200);