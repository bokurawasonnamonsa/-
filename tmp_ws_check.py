import asyncio
import json
import websockets

URL = "ws://127.0.0.1:9011/ws?mode=drill&aln=0&room=default"


async def drain(ws, sec=0.6):
    end = asyncio.get_event_loop().time() + sec
    msgs = []
    while asyncio.get_event_loop().time() < end:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=0.1)
            msgs.append(json.loads(raw))
        except Exception:
            pass
    return msgs


async def main():
    async with websockets.connect(URL) as staff, websockets.connect(URL) as leader:
        await drain(staff, 0.5)
        await drain(leader, 0.5)
        await staff.send(json.dumps({"cmd": "set_mode", "val": {"mode": "drill", "alliance_id": 0, "room_key": "default"}}))
        await leader.send(json.dumps({"cmd": "set_mode", "val": {"mode": "drill", "alliance_id": 0, "room_key": "default"}}))
        await drain(staff, 0.5)
        await drain(leader, 0.5)
        await staff.send(json.dumps({"cmd": "set_staff_mode", "val": {"enabled": True, "alliance_id": 0}}))
        await asyncio.sleep(0.1)
        await staff.send(json.dumps({"cmd": "register_player", "val": {"role": "leader1", "alliance_id": 0, "name": "staffA", "march_min": 0, "march_sec": 30, "device_mode": "2device"}}))
        await leader.send(json.dumps({"cmd": "register_player", "val": {"role": "leader1", "alliance_id": 0, "name": "leadB", "march_min": 0, "march_sec": 20, "device_mode": "2device"}}))
        await asyncio.sleep(0.7)
        await staff.send(json.dumps({"cmd": "fire_gorei", "idx": 0}))
        await asyncio.sleep(1.5)
        msgs = await drain(leader, 0.7)
        types = [m.get("type") for m in msgs if isinstance(m, dict)]
        print(json.dumps({"leader_recv_types": types[-20:]}))


if __name__ == "__main__":
    asyncio.run(main())
