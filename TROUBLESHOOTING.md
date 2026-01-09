# 🔧 ENVY Troubleshooting Guide

## InvalidURL Error (https://envy-api.onrender.com/)

### Symptom
Server shows: `raise InvalidURL(error) https://envy-api.onrender.com/`

### Cause
A configuration contains an invalid or non-existent URL. This specific URL (`envy-api.onrender.com`) doesn't exist.

### Solution

**On Render:**
1. Go to your service dashboard → Settings → Environment
2. Look for any variables containing `envy-api.onrender.com`
3. Delete those variables (they're not needed)
4. Save changes (service will auto-restart)

**Locally:**
```bash
# Check for env file
cat .env | grep -i "url"

# Remove any lines with envy-api.onrender.com
# Your service URL should match your actual Render service name
```

**Common mistake:**
- Someone may have set `ENVY_API_URL` or `API_BASE_URL` to a placeholder value
- Remove ALL custom URL environment variables unless you know what they do
- The system automatically uses the correct URLs based on your API keys

---

## Chat Not Responding

### Symptom
You can type messages but the AI doesn't respond, or you see error messages.

### Common Causes & Solutions

#### 1. **Missing API Key** ⚠️
**Error:** "No LLM API key configured"

**Solution:**
```bash
# Get a free key from groq.com
export GROQ_API_KEY="gsk_..."

# Or use OpenRouter
export OPENROUTER_API_KEY="sk-or-..."

# Then restart
python server.py
```

#### 2. **Invalid API Key** ⚠️
**Error:** "401 Unauthorized" or "403 Forbidden"

**Solution:**
- Key may be expired or invalid
- Generate a new key at groq.com or openrouter.ai
- Make sure you copied the entire key (no spaces/line breaks)

#### 3. **Network Error** ⚠️
**Error:** "[Errno -5] No address associated with hostname"

**Causes:**
- No internet connection
- Firewall blocking API calls
- DNS resolution issues

**Solution:**
```bash
# Test internet connectivity
curl https://api.groq.com/openai/v1/models

# If that fails, check network/firewall
```

#### 4. **Server Not Running** ⚠️
**Error:** "Failed to fetch" or "Connection refused"

**Solution:**
```bash
# Start the server
cd /path/to/LOVE-WINS
python server.py

# Should see: "Uvicorn running on http://0.0.0.0:8000"
```

#### 5. **Dependencies Missing** ⚠️
**Error:** "ModuleNotFoundError: No module named 'fastapi'"

**Solution:**
```bash
pip install -r requirements.txt
```

## On Render (Production)

### Setting API Keys

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Select your service
3. Click **Environment** in left sidebar
4. Click **Add Environment Variable**
5. Set:
   - **Key:** `GROQ_API_KEY` (or `OPENROUTER_API_KEY`)
   - **Value:** Your API key
6. Click **Save Changes** (auto-restarts service)

### Checking Logs

1. In Render Dashboard → Your Service
2. Click **Logs** tab
3. Look for:
   - ✅ "ENVY System: ONLINE"
   - ✅ "Multi-Agent Orchestrator: ONLINE"
   - ⚠️ "No LLM API key configured"

## Testing Locally

### 1. Check Server Status
```bash
curl http://localhost:8000/health
# Should return: {"status": "healthy"}
```

### 2. Check API Configuration
```bash
curl http://localhost:8000/api/status
# Should show: {"ready": true, ...}
```

### 3. Test Chat Endpoint
```bash
curl -X POST http://localhost:8000/v1/chat/completions/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello"}], "stream": true}'
  
# Should return streaming data chunks
```

## Getting API Keys

### Groq (Free, Recommended)
1. Go to [groq.com](https://groq.com)
2. Sign up for free account
3. Navigate to API Keys
4. Create new key
5. Copy the key (starts with `gsk_...`)

**Features:**
- ✅ Free tier included
- ✅ Llama-3, Mixtral models
- ✅ Very fast inference

### OpenRouter (Paid, More Models)
1. Go to [openrouter.ai](https://openrouter.ai)
2. Sign up
3. Add credits ($5 minimum)
4. Generate API key
5. Copy the key (starts with `sk-or-...`)

**Features:**
- ✅ 100+ models (Claude, GPT-4, etc.)
- ✅ Pay-per-use pricing
- ✅ Model fallbacks

## Still Having Issues?

1. **Check the server logs** - errors are usually shown there
2. **Verify API key format** - copy entire key with no spaces
3. **Test API key directly**:
   ```bash
   curl https://api.groq.com/openai/v1/models \
     -H "Authorization: Bearer $GROQ_API_KEY"
   ```
4. **Try a different model** - some keys have restricted model access
5. **Check Render build logs** - may show deployment errors

## Quick Validation Script

Save this as `test_envy.py`:

```python
import os
import sys

print("🔍 ENVY Configuration Test\n")

# Check API keys
groq_key = os.getenv("GROQ_API_KEY")
or_key = os.getenv("OPENROUTER_API_KEY")

print(f"GROQ_API_KEY: {'✅ Set' if groq_key else '❌ Not set'}")
print(f"OPENROUTER_API_KEY: {'✅ Set' if or_key else '❌ Not set'}")

if not groq_key and not or_key:
    print("\n❌ No API keys configured!")
    print("Set one of: GROQ_API_KEY, OPENROUTER_API_KEY")
    sys.exit(1)

# Try importing key modules
try:
    import fastapi
    print("✅ FastAPI installed")
except ImportError:
    print("❌ FastAPI missing - run: pip install fastapi")

try:
    import uvicorn
    print("✅ Uvicorn installed")
except ImportError:
    print("❌ Uvicorn missing - run: pip install uvicorn")

try:
    import groq
    print("✅ Groq SDK installed")
except ImportError:
    print("⚠️  Groq SDK missing (optional)")

print("\n✅ Basic configuration looks good!")
print("Try starting server: python server.py")
```

Run with: `python test_envy.py`
