import asyncio
import websockets


async def main():
    url = "wss://3301-svs.jp/ws?mode=drill&aln=0&room=default"
    async with websockets.connect(url, open_timeout=10) as ws:
        msg = await asyncio.wait_for(ws.recv(), timeout=10)
        print("ok", len(msg))


asyncio.run(main())
