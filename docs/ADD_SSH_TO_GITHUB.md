# Adding SSH Key to GitHub - Step by Step Guide

## 📋 Prerequisites (Already Done ✅)

- ✅ SSH key generated: `~/.ssh/id_ed25519`
- ✅ Public key copied to clipboard
- ✅ SSH agent configured

---

## 🎯 Step-by-Step Instructions

### Step 1: Open GitHub SSH Settings

Go to: **https://github.com/settings/ssh/new**

Or manually:
1. Go to https://github.com
2. Click your profile picture (top right)
3. Click **Settings**
4. Click **SSH and GPG keys** (left sidebar)
5. Click **New SSH key** (green button)

---

### Step 2: Fill in the Form

On the "Add new SSH key" page:

#### **Title Field:**
```
VinSight MacBook
```
(or any name you prefer - this is just a label)

#### **Key Type:**
Select: **Authentication Key** (should be default)

#### **Key Field:**
Paste your public key (already in clipboard):

**Just press:** `Cmd + V` or right-click → Paste

The key should look like:
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHrkHkad9+VKG4KL48f7NGRRKOwvLdniIhmw+82ZZrxH vinayakmalhotra11111@gmail.com
```

---

### Step 3: Add the Key

Click the green **"Add SSH key"** button

You may be prompted to:
- Enter your GitHub password
- Complete 2FA if enabled

---

### Step 4: Verify Key Was Added

You should see your new key listed with:
- ✅ Title: "VinSight MacBook"
- ✅ Fingerprint: `SHA256:D6vps8CegGCG8dxp...`
- ✅ Added today: 2026-01-17

---

## ✅ After Adding the Key

### Test SSH Connection

Open your terminal and run:

```bash
ssh -T git@github.com
```

**Expected output:**
```
Hi vinayakm-93! You've successfully authenticated, but GitHub does not provide shell access.
```

If you see this, SSH is working! ✅

---

### Switch Git Remote from HTTPS to SSH

Run the automated script:

```bash
cd "/Users/vinayak/Documents/Antigravity/Project 1"
./switch_to_ssh.sh
```

This script will:
1. ✅ Test SSH connection
2. ✅ Change remote URL from HTTPS to SSH
3. ✅ Verify everything works
4. ✅ Remove GitHub token from URL

---

## 🔍 Visual Guide

### Before (HTTPS with token):
```
https://vinayakm-93:github_pat_XXX@github.com/vinayakm-93/vinsight.git
```
⚠️ Token visible in URL

### After (SSH):
```
git@github.com:vinayakm-93/vinsight.git
```
✅ No credentials in URL, uses SSH key

---

## ❌ Troubleshooting

### If clipboard is empty:

Re-copy the public key:
```bash
cat ~/.ssh/id_ed25519.pub | pbcopy
```

### If you get "Permission denied":

1. Check SSH agent:
   ```bash
   ssh-add -l
   ```
   
2. If empty, add key:
   ```bash
   ssh-add ~/.ssh/id_ed25519
   ```

### If you're not sure what to paste:

Display your public key:
```bash
cat ~/.ssh/id_ed25519.pub
```

Copy the entire output (starts with `ssh-ed25519`)

---

## 🎬 Quick Demo

### Option 1: Web Interface (Manual)
1. **Browser:** Open https://github.com/settings/ssh/new
2. **Title:** Type any name (e.g., "VinSight MacBook")
3. **Key:** Press `Cmd + V` to paste
4. **Click:** "Add SSH key" button
5. **Done!** ✅

### Option 2: GitHub CLI (Advanced)
```bash
# If you have gh CLI installed
gh ssh-key add ~/.ssh/id_ed25519.pub --title "VinSight MacBook"
```

---

## 📱 Your SSH Public Key

If you need to see it again:

```bash
cat ~/.ssh/id_ed25519.pub
```

**Your key:**
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHrkHkad9+VKG4KL48f7NGRRKOwvLdniIhmw+82ZZrxH vinayakmalhotra11111@gmail.com
```

This is safe to share - it's the **public** key, not the private one!

---

## 🔐 Security Notes

### ✅ DO:
- Add the **public** key (`.pub` file) to GitHub
- Keep the **private** key (`id_ed25519`) on your computer only
- Use a descriptive title for your keys

### ❌ DON'T:
- Never share your private key (`~/.ssh/id_ed25519`)
- Don't paste the private key to GitHub
- Don't commit SSH keys to Git

---

## ✅ Checklist

- [ ] Open https://github.com/settings/ssh/new
- [ ] Enter title: "VinSight MacBook"
- [ ] Paste public key (Cmd+V)
- [ ] Click "Add SSH key"
- [ ] Test with: `ssh -T git@github.com`
- [ ] Run: `./switch_to_ssh.sh`

---

**Once completed, your Git operations will use secure SSH instead of HTTPS tokens!** 🚀
