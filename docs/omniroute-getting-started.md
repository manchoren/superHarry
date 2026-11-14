# omniroute - Quick Start Guide

> Historical setup notes: provider routing and generation are not accepted by
> this guide. Follow the current [closure plan](plans/t179-t226-t231-t237-closure.md)
> before using external models or claiming release readiness.

**Updated:** 2026-11-11  
**For:** Target VM validation

---

## 🎯 What is omniroute?

omniroute is the **centralized AI gateway** for superHarry that:

- 🔐 Manages credentials for ALL model providers
- 🔄 Automatically routes to available providers with intelligent fallback
- 📊 Tracks tokens, costs, and quota in real-time
- 🔌 Provides a unified OpenAI-compatible interface

**superHarry does NOT store provider credentials**, only omniroute's API key.

---

## 📋 Prerequisites

### On Target VM

1. **omniroute installed and running**
   ```bash
   # Check service
   systemctl status omniroute
   
   # If not running, start it
   sudo systemctl start omniroute
   ```

2. **Port 20128 accessible**
   ```bash
   # Verify port is open
   netstat -tlnp | grep 20128
   
   # Should show something like:
   # tcp 0 0 127.0.0.1:20128 0.0.0.0:* LISTEN 12345/omniroute
   ```

3. **Ollama installed with qwen3.5:4b model**
   ```bash
   # Check Ollama
   ollama list
   
   # If model is missing, download
   ollama pull qwen3.5:4b
   ```

4. **Providers configured in omniroute**
   - Access: http://localhost:20128 (or VM IP)
   - Login with admin credentials
   - Configure at minimum:
     - **Nous Portal** (primary) - API key
     - **Ollama** (local fallback) - endpoint localhost:11434

---

## 🚀 Configuration in superHarry

### 1. Get API Key from omniroute

In omniroute dashboard:
1. Navigate to **Settings → API Keys**
2. Create new API key named "superharry-production"
3. Copy generated key (only shown once)

### 2. Configure Environment Variables

Edit `.env` in superHarry root:

```bash
# omniroute configuration
OMNIROUTE_ENDPOINT=http://localhost:20128/v1
OMNIROUTE_API_KEY=omr_1234567890abcdefghijklmnopqrstuvwxyz
```

**⚠️ Important:** 
- File permissions: `chmod 600 .env`
- DO NOT commit `.env` to git (already in .gitignore)

### 3. Verify Configuration in `.env.paths`

```bash
# omniroute endpoint
OMNIROUTE_ENDPOINT=http://localhost:20128/v1
OMNIROUTE_DASHBOARD=http://localhost:20128

# Local model (Ollama via omniroute)
LOCAL_MODEL_ENDPOINT=http://localhost:11434
LOCAL_MODEL_NAME=qwen3.5:4b
```

---

## ✅ Quick Validation

### Read-only Python validation

Set `OMNIROUTE_ENDPOINT` to the loopback gateway URL and provide
`OMNIROUTE_API_KEY` through the environment without printing it. Then run:

```bash
python scripts/validate_omniroute.py
```

The script checks only `/api/health` and unauthenticated and authenticated
`/v1/models`. It prints a report to standard output, does not generate text,
and does not establish provider eligibility, accounting, or release acceptance.
It accepts only a loopback HTTP endpoint and does not follow redirects or use
proxy settings. No report file is created automatically.

---

## 📚 Additional Documentation

- **Complete validation plan:** `docs/omniroute-validation-plan.md`
- **Security policies:** `docs/reference/security-policies.md` § 5
- **Product requirements:** `docs/reference/product-requirements.md` § 4.1.2

---

## ✅ Validation Checklist

Before considering omniroute production-ready:

- [ ] omniroute service active and stable for >24h
- [ ] Health endpoint responding
- [ ] Dashboard accessible
- [ ] API key configured and functional
- [ ] External model (Nous Portal) responding
- [ ] Local model (Ollama) responding
- [ ] Automatic fallback working
- [ ] SSE streaming working
- [ ] Token tracking working
- [ ] Usage stats available
- [ ] Audit logs working
- [ ] All automated tests pass
- [ ] superHarry can make successful calls
- [ ] No critical errors in logs for 1h

---

## 🚀 Next Steps

Once omniroute is validated:

1. ✅ Fully integrate with `chat_views.py`
2. ✅ Add omniroute logging to `audit.py`
3. ✅ Create admin panel for omniroute stats
4. ✅ Configure alerts for quota exhaustion
5. ✅ Document API key rotation process
6. ✅ Test with real user load

---

**Questions or problems?**

Review:
- omniroute logs: `journalctl -u omniroute -f`
- superHarry logs: `tail -f logs/django.log`
- Validation plan: `docs/omniroute-validation-plan.md`
