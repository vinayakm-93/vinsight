#!/bin/bash
# Auto-setup script for VinSight MCP

CONFIG_DIR="$HOME/Library/Application Support/Claude"
CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"
MCP_SCRIPT="$(pwd)/backend/mcp_server.py"
PYTHON_EXEC="python3"

echo "🔌 Setting up VinSight MCP Server..."

# 1. Check if config dir exists
if [ ! -d "$CONFIG_DIR" ]; then
    echo "⚠️  Claude Desktop config directory not found at $CONFIG_DIR"
    echo "   Please install and run Claude Desktop at least once."
    exit 1
fi

# 2. Prepare Config JSON
# We use a temporary python script to safely merge JSON
cat <<EOF > merge_config.py
import json
import os
import sys

config_path = "$CONFIG_FILE"
mcp_script = "$MCP_SCRIPT"

try:
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            content = f.read().strip()
            data = json.loads(content) if content else {}
    else:
        data = {}

    if "mcpServers" not in data:
        data["mcpServers"] = {}

    data["mcpServers"]["vinsight"] = {
        "command": "$PYTHON_EXEC",
        "args": [mcp_script]
    }

    with open(config_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print("✅ Successfully updated " + config_path)
except Exception as e:
    print("❌ Error updating config: " + str(e))
    sys.exit(1)
EOF

# 3. Run Merger
python3 merge_config.py
rm merge_config.py

echo "🎉 Setup Complete!"
echo "   1. Restart Claude Desktop."
echo "   2. Look for the 🔌 icon."
echo "   3. Ask Claude: 'Check sentiment for AAPL'"
