#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║     Switch GitHub from HTTPS to SSH                   ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${GREEN}Step 1: Add SSH Key to GitHub${NC}"
echo "A browser window should open to: https://github.com/settings/ssh/new"
echo ""
echo "On that page:"
echo "  1. Title: 'VinSight MacBook' (or any name)"
echo "  2. Key: Paste from clipboard (already copied)"
echo "  3. Click 'Add SSH key'"
echo ""
echo -e "${YELLOW}Press ENTER when you've added the key to GitHub...${NC}"
read -r

echo ""
echo -e "${GREEN}Step 2: Test SSH Connection${NC}"
ssh -T git@github.com 2>&1 | head -5 || true

echo ""
echo -e "${GREEN}Step 3: Switch Git Remote from HTTPS to SSH${NC}"

# Get current remote
CURRENT_REMOTE=$(git remote get-url origin)
echo "Current remote: $CURRENT_REMOTE"

# Switch to SSH
NEW_REMOTE="git@github.com:vinayakm-93/vinsight.git"
git remote set-url origin "$NEW_REMOTE"

echo "New remote: $(git remote get-url origin)"
echo ""

echo -e "${GREEN}Step 4: Verify Connection${NC}"
if ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
    echo -e "${GREEN}✓ SSH connection successful!${NC}"
else
    echo -e "${YELLOW}Testing git fetch...${NC}"
    if git fetch --dry-run 2>&1; then
        echo -e "${GREEN}✓ Git SSH working!${NC}"
    else
        echo -e "${RED}⚠ SSH may not be working. Check your key on GitHub.${NC}"
    fi
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     ✓ GitHub now uses SSH instead of HTTPS!          ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Your GitHub token has been removed from the remote URL."
echo "All git push/pull operations now use SSH keys."
