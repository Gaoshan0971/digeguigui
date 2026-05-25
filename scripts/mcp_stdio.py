#!/usr/bin/env python3
"""
stdio MCP entry point for Glama quality checks.
Imports the HTTP MCP server's tool registry and handlers,
but communicates over stdin/stdout JSON-RPC (no HTTP, no auth).
"""
import sys, json, os, sqlite3

# ── Paths (env overridable) ──
DB_PATH = os.environ.get('DB_PATH', '/home/ubuntu/digeguigui/data/digeguigui.db')
GENECALC_PATH = os.environ.get('GENECALC_PATH', '/home/ubuntu/digeguigui/scripts/genecalc.py')

# ── Monkey-patch the HTTP server's globals before importing ──
# The HTTP module uses these globals; set them first.
import __main__
__main__.DB_PATH = DB_PATH
__main__.GENECALC_PATH = GENECALC_PATH

# Now import the HTTP server module to get TOOLS and handlers
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcp_server

# ── Stdio JSON-RPC loop ──
def send(data):
    sys.stdout.write(json.dumps(data, ensure_ascii=False) + '\n')
    sys.stdout.flush()

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        rid = req.get('id')
        method = req.get('method', '')
        params = req.get('params', {})

        if method == 'initialize':
            send({
                'jsonrpc': '2.0', 'id': rid,
                'result': {
                    'protocolVersion': '2024-11-05',
                    'serverInfo': {'name': 'digeguigui', 'version': '1.0.0'},
                    'capabilities': {'tools': {}},
                }
            })
        elif method == 'notifications/initialized':
            pass  # no response needed
        elif method == 'tools/list':
            tools_list = [
                {'name': t['name'], 'description': t['description'], 'inputSchema': t['inputSchema']}
                for t in mcp_server.TOOLS.values()
            ]
            send({'jsonrpc': '2.0', 'id': rid, 'result': {'tools': tools_list}})
        elif method == 'tools/call':
            tool_name = params.get('name', '')
            tool_args = params.get('arguments', {})
            tool = mcp_server.TOOLS.get(tool_name)
            if not tool:
                send({'jsonrpc': '2.0', 'id': rid, 'error': {'code': -32601, 'message': f'Unknown tool: {tool_name}'}})
                continue
            try:
                result = tool['handler'](tool_args)
                send({
                    'jsonrpc': '2.0', 'id': rid,
                    'result': {
                        'content': [{'type': 'text', 'text': json.dumps(result, ensure_ascii=False)}],
                        'isError': 'error' in result,
                    }
                })
            except Exception as e:
                send({'jsonrpc': '2.0', 'id': rid, 'error': {'code': -32000, 'message': str(e)}})
        elif method == 'resources/list':
            send({'jsonrpc': '2.0', 'id': rid, 'result': {'resources': []}})
        elif method == 'prompts/list':
            send({'jsonrpc': '2.0', 'id': rid, 'result': {'prompts': []}})
        else:
            send({'jsonrpc': '2.0', 'id': rid, 'error': {'code': -32601, 'message': f'Unknown method: {method}'}})

if __name__ == '__main__':
    main()
