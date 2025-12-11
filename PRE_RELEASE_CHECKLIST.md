# 🔒 Pre-Release Security Checklist

Before pushing this repository to GitHub or making it public, **complete this checklist** to ensure no sensitive data is exposed.

---

## ✅ Step 1: Verify .gitignore is Working

The `.gitignore` file has been created. Now verify it's protecting sensitive files:

```bash
# Check what files are currently tracked by Git
git ls-files

# Check for any sensitive files that might be staged
git status
```

**Expected Result**: You should NOT see any of these files in the output:
- `.env`
- `credentials.json`
- `service_account.json`
- `activity.log`
- `__pycache__/` directories

---

## ⚠️ Step 2: Remove Sensitive Files from Git History (If Already Committed)

If you've previously committed sensitive files, they exist in Git history even if deleted now.

### Check if sensitive files are in history:
```bash
git log --all --full-history -- backend/credentials.json
git log --all --full-history -- backend/.env
git log --all --full-history -- backend/service_account.json
```

### If found, remove them from history:

**Option A: Using git filter-repo (Recommended)**
```bash
# Install git-filter-repo first
pip install git-filter-repo

# Remove specific files from entire history
git filter-repo --path backend/credentials.json --invert-paths
git filter-repo --path backend/service_account.json --invert-paths
git filter-repo --path backend/.env --invert-paths
```

**Option B: Using BFG Repo-Cleaner**
```bash
# Download BFG from https://rtyley.github.io/bfg-repo-cleaner/
java -jar bfg.jar --delete-files credentials.json
java -jar bfg.jar --delete-files service_account.json
java -jar bfg.jar --delete-files .env

git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

**⚠️ WARNING**: After cleaning history, you'll need to force-push:
```bash
git push origin --force --all
```

---

## 📝 Step 3: Create Example Configuration Files

Create template files to help users set up their own credentials:

### Create `backend/.env.example`:
```bash
# Copy your .env but remove actual values
GEMINI_API_KEY="your_gemini_api_key_here"
GOOGLE_CREDENTIALS_PATH="service_account.json"
SPREADSHEET_ID="your_google_sheet_id_here"
```

### Create `backend/README.md` (if not exists):
Add instructions on how to obtain:
- Gemini API Key
- Google Cloud Service Account
- Google Sheet setup

---

## 🔍 Step 4: Scan for Hardcoded Secrets

Search your codebase for accidentally hardcoded credentials:

```bash
# Search for common patterns
git grep -i "api.key"
git grep -i "password"
git grep -i "secret"
git grep -i "AIza"  # Google API keys often start with this
```

**Action**: If found, replace with environment variables.

---

## 🧪 Step 5: Test with Fresh Clone

Simulate a new user experience:

```bash
# Clone to a temporary directory
cd /tmp
git clone https://github.com/Amitro123/LinkedIn-KnowledgeBase.git test-clone
cd test-clone

# Verify sensitive files are NOT present
ls backend/credentials.json  # Should fail
ls backend/.env              # Should fail
```

---

## 📦 Step 6: Final Git Commands

Once everything is verified:

```bash
# Add the new files
git add .gitignore
git add ROADMAP.md
git add PRE_RELEASE_CHECKLIST.md
git add README.md

# Commit
git commit -m "docs: Add security .gitignore, roadmap, and pre-release checklist"

# Push to GitHub
git push origin main
```

---

## 🎯 Step 7: GitHub Repository Settings

After pushing, configure your GitHub repository:

1. **Add Repository Description**:
   - "Turn your LinkedIn saved posts into an AI-powered knowledge base using Gemini 2.5 Flash and Google Sheets"

2. **Add Topics/Tags**:
   - `linkedin`, `ai`, `gemini`, `rag`, `knowledge-base`, `chrome-extension`, `fastapi`

3. **Enable Issues** (for community contributions)

4. **Add a LICENSE file** (MIT is already mentioned in README)

5. **Create a GitHub Release** (v1.0.0)

---

## ✅ Security Checklist Summary

- [ ] `.gitignore` file created and tested
- [ ] Sensitive files removed from Git history (if applicable)
- [ ] `.env.example` created for user guidance
- [ ] No hardcoded secrets in codebase
- [ ] Fresh clone test passed
- [ ] Repository pushed to GitHub
- [ ] GitHub repository configured with description and topics
- [ ] LICENSE file added

---

## 🆘 Emergency: Leaked Credentials

If you accidentally pushed credentials to GitHub:

1. **Immediately revoke/regenerate**:
   - Gemini API Key: Go to Google AI Studio → Delete old key → Create new one
   - Google Service Account: Go to Google Cloud Console → Delete old account → Create new one

2. **Clean Git history** (see Step 2 above)

3. **Force push** to overwrite remote history

4. **Never reuse** the leaked credentials

---

**Last Updated**: December 2025  
**Status**: Ready for review
