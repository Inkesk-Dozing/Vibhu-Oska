import asyncio, json, websockets, time

async def test():
    uri = 'ws://localhost:8100/ws'
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({'prompt': 'hello', 'session_id': 'test-001'}))
        print('SENT: hello')
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=20)
                data = json.loads(msg)
                t = data.get('type', '')
                p = data.get('payload', {})
                print(f'MSG type={t}')
                if t == 'task.completed':
                    print('CONTENT:', p.get('content', '')[:300])
                    break
                elif t == 'task.failed':
                    print('ERROR:', p.get('error', ''))
                    break
            except asyncio.TimeoutError:
                print('TIMEOUT — no response in 20s')
                break

asyncio.run(test())
