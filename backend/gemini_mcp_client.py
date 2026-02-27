import os
import sys
import json
import subprocess
import google.generativeai as genai
import google.generativeai.types as genai_types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
MCP_SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "mcp_server.py")
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    # Try looking in project root .env if not found
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(project_root, ".env"))
    API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("❌ Error: GEMINI_API_KEY environment variable not set.")
    sys.exit(1)

genai.configure(api_key=API_KEY)

# --- MCP CLIENT HELPER ---
class MCPClient:
    def __init__(self):
        self.process = subprocess.Popen(
            [sys.executable, MCP_SERVER_SCRIPT],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            text=True,
            bufsize=0
        )
        self._initialize()

    def _send(self, req):
        json_req = json.dumps(req)
        self.process.stdin.write(json_req + "\n")
        self.process.stdin.flush()

    def _read(self):
        return json.loads(self.process.stdout.readline())

    def _initialize(self):
        self._send({
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1,
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "gemini-cli", "version": "1.0"}
            }
        })
        self._read() # Result
        
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def call_tool(self, tool_name: str, args: dict):
        print(f"\n⚡ Executing Tool: {tool_name}({args})...")
        self._send({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 2,
            "params": {
                "name": tool_name,
                "arguments": args
            }
        })
        
        while True:
            resp = self._read()
            if resp.get("id") == 2:
                if "error" in resp:
                    return f"Error: {resp['error']['message']}"
                
                content = resp.get("result", {}).get("content", [])
                if content:
                    return content[0].get("text", "")
                return "No output."

    def close(self):
        self.process.terminate()

# --- GEMINI TOOLS DEFINITION ---
mcp_tools = [
     {"function_declarations": [
    {
        "name": "analyze_sentiment",
        "description": "Get AI-driven sentiment analysis for a stock ticker based on recent news.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock Symbol (e.g. AAPL)"}
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "run_monte_carlo",
        "description": "Run a Monte Carlo simulation to project future price risk (P10/P50/P90).",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock Symbol (e.g. TSLA)"}
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "analyze_earnings",
        "description": "Analyze the latest earnings call transcript for management confidence and guidance.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock Symbol (e.g. NVDA)"}
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "get_portfolio_summary",
        "description": "Generate a comprehensive Wealth Manager Report for the user's portfolio.",
        "parameters": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "description": "User Email (e.g. vinayak@example.com)"}
            },
            "required": ["email"]
        }
    }
     ]}
]

# --- MAIN CHAT LOOP ---
def main():
    print("🚀 Connecting to VinSight MCP Server...")
    client = MCPClient()
    print("✅ Connected.")

    print("🧠 Initializing Gemini 2.0 Flash...")
    model = genai.GenerativeModel(
        model_name='gemini-2.0-flash', 
        tools=mcp_tools
    )
    # Start chat (auto-function calling is tricky with manual execution, using low-level generate_content loop for control)
    # chat = model.start_chat(enable_automatic_function_calling=True) 

    print("\n💬 Gemini CLI Ready! (Type 'exit' to quit)")
    
    # Check for CLI args for single-shot mode
    if len(sys.argv) > 1:
        initial_prompt = " ".join(sys.argv[1:])
        print(f"👤 Auto-Input: {initial_prompt}")
        run_turn(model, client, initial_prompt, [])
        client.close()
        return

    history = []
    while True:
        try:
            user_input = input("\n👤 You: ").strip()
            if user_input.lower() in ["exit", "quit"]:
                break
            if not user_input:
                continue
            
            history = run_turn(model, client, user_input, history)

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

    client.close()
    print("👋 Bye!")

def run_turn(model, client, user_input, history):
    # Construct message list from history + new input
    messages = history + [{"role": "user", "parts": [user_input]}]
    
    # 1. Send Message to Gemini
    response = model.generate_content(messages)
    
    # 2. Check for Function Call
    # Gemini 2.0 returns function calls in parts
    try:
        part = response.candidates[0].content.parts[0]
    except:
        print(f"🤖 Gemini: {response.text}")
        history.append({"role": "model", "parts": [response.text]})
        return history

    if part.function_call:
        fc = part.function_call
        tool_name = fc.name
        plugin_args = dict(fc.args)

        # 3. Execute with MCP
        result_text = client.call_tool(tool_name, plugin_args)
        
        # 4. Feed Result back to Gemini
        # Construct function response
        function_response_part = genai_types.Part(
            function_response=genai_types.FunctionResponse(
                name=tool_name,
                response={'result': result_text}
            )
        )
        
        # Add the model's function call and our response to history/messages
        messages.append({"role": "model", "parts": [part]})
        messages.append({"role": "function", "parts": [function_response_part]})
        
        # Generate final answer from Gemini
        final_response = model.generate_content(messages)
        print(f"🤖 Gemini: {final_response.text}")
        
        # Update history (simplified: just append user and final answer for next turn context)
        # Note: maintaining full function call history in simpler list is tricky, 
        # so for this CLI we might just keep the final text for context or reset.
        # For a robust CLI we'd keep the whole chain.
        history.append({"role": "model", "parts": [final_response.text]})
        
    else:
        print(f"🤖 Gemini: {response.text}")
        history.append({"role": "model", "parts": [response.text]})
        
    return history

if __name__ == "__main__":
    main()