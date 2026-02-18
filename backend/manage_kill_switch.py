#!/usr/bin/env python3
import os
import sys

LOCK_FILE = "mcp_kill_switch.lock"

def enable_kill_switch():
    if os.path.exists(LOCK_FILE):
        print(f"⚠️  Kill Switch is ALREADY ACTIVE. ({LOCK_FILE} exists)")
        return
    with open(LOCK_FILE, "w") as f:
        f.write("KILL SWITCH ENGAGED")
    print(f"✅ KILL SWITCH ENGAGED. All MCP tools are now DISABLED.")

def disable_kill_switch():
    if not os.path.exists(LOCK_FILE):
        print(f"ℹ️  Kill Switch is not active.")
        return
    os.remove(LOCK_FILE)
    print(f"🟢 KILL SWITCH DISABLED. MCP tools are now ACTIVE.")

def status():
    if os.path.exists(LOCK_FILE):
        print(f"🔴 STATUS: KILL SWITCH ACTIVE (System Disabled)")
    else:
        print(f"🟢 STATUS: OPERATIONAL (System Active)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python manage_kill_switch.py [on|off|status]")
        status()
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    if cmd == "on":
        enable_kill_switch()
    elif cmd == "off":
        disable_kill_switch()
    elif cmd == "status":
        status()
    else:
        print("Unknown command. Use: on, off, status")
