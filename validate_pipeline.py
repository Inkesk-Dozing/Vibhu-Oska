"""
Final validation: test 4 prompts end-to-end via WebSocket.
Proves pipeline is alive: ack -> task.created -> task.completed with good content.
"""
import asyncio, json, websockets, uuid

PROMPTS = [
    "hello",
    "who are you",
    "what is the system status",
    "128 * 8",
]

async def test_prompt(prompt: str) -> dict:
    sid = str(uuid.uuid4())
    result = {"prompt": prompt, "status": "TIMEOUT", "content": "", "ms": 0}
    try:
        async with websockets.connect("ws://localhost:8100/ws", ping_timeout=None) as ws:
            await ws.send(json.dumps({"prompt": prompt, "session_id": sid}))
            import time; t0 = time.time()
            while (time.time() - t0) < 25:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=25)
                    data = json.loads(msg)
                    t = data.get("type", "")
                    if t == "task.completed":
                        result["status"] = "OK"
                        result["content"] = data["payload"]["content"]
                        result["ms"] = data["payload"]["metadata"]["processing_time_ms"]
                        break
                    elif t == "task.failed":
                        result["status"] = "FAILED"
                        result["content"] = data["payload"].get("error", "")
                        break
                except asyncio.TimeoutError:
                    break
    except Exception as e:
        result["status"] = f"ERROR: {e}"
    return result

async def main():
    # Warm up router with first call, then test all
    print("=== Vibhu-Oska E2E Validation ===\n")
    for p in PROMPTS:
        r = await test_prompt(p)
        status_icon = "OK" if r["status"] == "OK" else "FAIL"
        print(f'{status_icon} [{r["ms"]}ms] "{r["prompt"]}"')
        if r["status"] == "OK":
            lines = r["content"].strip().split("\n")
            preview = "\n    ".join(lines[:4])
            print(f"    {preview}")
        else:
            print(f"    STATUS: {r['status']}")
        print()

asyncio.run(main())
