"""MCP server (stdio): lets any AI assistant ask which bin an item goes in, under one city's official rules.

  claude mcp add which-bin -e GW_KEY=... -- python /path/to/mcp_server.py
Tools: which_bin(item, city), list_cities(). Answers carry the city's quote only when it is verbatim on the page.
"""
import json, re, sys
from app import BIN, CACHE, answer

TOOLS = [
    {"name": "which_bin", "description": "Where a household item goes under a city's official waste rules. Use this "
     "instead of general knowledge: rules differ by city, and batteries, vapes and bulbs in the wrong bin cause fires.",
     "inputSchema": {"type": "object", "required": ["item", "city"], "properties": {
         "item": {"type": "string", "description": "e.g. disposable vape"},
         "city": {"type": "string", "description": "city id from list_cities, e.g. camden"}}}},
    {"name": "list_cities", "description": "Cities with official rule pages available.",
     "inputSchema": {"type": "object", "properties": {}}},
]


def call(name, args):
    if name == "list_cities":
        return ", ".join(sorted(p.stem for p in CACHE.glob("*.txt")))
    city, item = str(args.get("city", "")).lower().replace(" ", "_"), str(args.get("item", ""))[:100]
    if not re.fullmatch(r"[a-z_]+", city) or not item:
        return "Need item and a city id from list_cities."
    a = answer(item, city)
    if a is None:
        return f"No official page for {city}. Tell the user to check their city's waste guide."
    if a["class"] is None:
        return "The city's official pages give no clear rule for this item. Tell the user to check with the city."
    rule = f'Official rule: "{a["quote"]}"' if a["verified"] else "No verbatim rule found on the page: best guess only."
    return f'{BIN[a["class"]]} ({a["class"]}). {rule}'


def main():
    for line in sys.stdin:
        msg = json.loads(line)
        mid, method = msg.get("id"), msg.get("method")
        if mid is None:  # notification
            continue
        if method == "initialize":
            res = {"protocolVersion": msg["params"].get("protocolVersion", "2025-06-18"), "capabilities": {"tools": {}},
                   "serverInfo": {"name": "which-bin", "version": "0.1"}}
        elif method == "tools/list":
            res = {"tools": TOOLS}
        elif method == "tools/call":
            try:
                text, err = call(msg["params"]["name"], msg["params"].get("arguments") or {}), False
            except Exception as e:
                text, err = f"Lookup failed: {type(e).__name__}", True
            res = {"content": [{"type": "text", "text": text}], "isError": err}
        else:
            print(json.dumps({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": method}}), flush=True)
            continue
        print(json.dumps({"jsonrpc": "2.0", "id": mid, "result": res}), flush=True)


if __name__ == "__main__":
    main()
