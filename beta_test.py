"""
Beta user simulation — tests the full conversation loop like a real user.
Sends 10 messages in sequence, verifying each response.
"""
import asyncio, json, uuid, time

try:
    import websockets
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets", "-q"])
    import websockets

MESSAGES = [
    "hello",
    "what are you?",
    "what is the system status",
    "how much ram is being used",
    "128 * 8",
    "what is 2 to the power of 10",
    "how does the pipeline work",
    "who built you",
    "what is chromadb",
    "help",
]

async def chat(prompt: str, session_id: str) -> dict:
    t0 = time.time()
    result = {"prompt": prompt[:40], "status": "TIMEOUT", "ms": 0, "content": ""}
    try:
        async with websockets.connect("ws://localhost:8100/ws", ping_timeout=None) as ws:
            await ws.send(json.dumps({"prompt": prompt, "session_id": session_id}))
            deadline = time.time() + 25
            while time.time() < deadline:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=25)
                    data = json.loads(msg)
                    t = data.get("type", "")
                    if t == "task.completed":
                        result["status"] = "OK"
                        result["content"] = data["payload"]["content"]
                        result["ms"] = int((time.time() - t0) * 1000)
                        break
                    elif t == "task.failed":
                        result["status"] = "FAILED"
                        result["content"] = data["payload"].get("error", "")
                        result["ms"] = int((time.time() - t0) * 1000)
                        break
                except asyncio.TimeoutError:
                    break
    except Exception as e:
        result["status"] = f"ERR:{e}"
    return result

async def main():
    sid = str(uuid.uuid4())
    print("=== Beta User Simulation — Vibhu-Oska AI-OS ===")
    print(f"Session: {sid[:8]}")
    print("=" * 52)
    total_ok = 0
    for msg in MESSAGES:
        r = await chat(msg, sid)
        icon = "[OK]  " if r["status"] == "OK" else "[FAIL]"
        print(f"\n{icon} [{r['ms']}ms] User: {r['prompt']}")
        if r["status"] == "OK":
            # Print first 3 lines of response
            lines = r["content"].strip().split("\n")[:3]
            for ln in lines:
                print(f"       AI: {ln}")
            total_ok += 1
        else:
            print(f"       STATUS: {r['status']}")
    print(f"\n{'='*52}")
    print(f"Result: {total_ok}/{len(MESSAGES)} responses OK")

asyncio.run(main())
