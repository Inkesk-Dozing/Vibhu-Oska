"""
Vibhu-Oska AI-OS — Pytest Configuration
Ensures that the WindowsSelectorEventLoopPolicy is applied on Windows systems
to support asynchronous ZeroMQ socket communications.
"""

import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
