# Deployment Guide - Get Your Public API URL

## Prerequisites

Before deploying, ensure you have:
- [x] Code working locally (test with `python scripts/test_api.py`)
- [x] Catalog scraped (`data/catalog/shl_catalog.json` exists)
- [x] API key ready (OpenAI, Groq, or Gemini)
- [ ] GitHub account (for Render deployment)

## Method 1: Render (Easiest - 10 minutes)

### Step 1: Push to GitHub

```bash
cd "/Users/seshasaitunuguntla/Desktop/SHL Assignment"

# Initialize git (if not already)
git init

# Add all files
git add .

# Commit
git commit -m "SHL Assessment Recommender - Complete Implementation"

# Create GitHub repo (if you have GitHub CLI)
gh repo create shl-assessment-recommender --public --source=. --push

# OR manually:
# 1. Go to https://github.com/new
# 2. Create repo named "shl-assessment-recommender"
# 3. Follow instructions to push existing repository
```

### Step 2: Deploy on Render

1. **Sign up**: Go to https://render.com and create account

2. **Create Web Service**:
   - Click "New +" → "Web Service"
   - Connect your GitHub account
   - Select your `shl-assessment-recommender` repository
   - Click "Connect"

3. **Configure Service**:
   - **Name**: `shl-recommender` (or any name)
   - **Environment**: `Python 3`
   - **Region**: Choose closest to you
   - **Branch**: `main` or `master`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`

4. **Add Environment Variables**:
   Click "Environment" → "Add Environment Variable":
   
   ```
   Key: OPENAI_API_KEY
   Value: your-actual-api-key-here
   
   Key: CATALOG_PATH
   Value: data/catalog/shl_catalog.json
   
   Key: LLM_PROVIDER
   Value: openai
   
   Key: LLM_MODEL
   Value: gpt-4-turbo-preview
   ```

5. **Create Web Service**:
   - Click "Create Web Service"
   - Wait 5-10 minutes for deployment
   - You'll see build logs in real-time

6. **Get Your URL**:
   - Once deployed, you'll see: `https://shl-recommender-xxxxx.onrender.com`
   - **This is your public API URL!**

### Step 3: Test Deployed API

```bash
# Test health endpoint
curl https://your-render-url.onrender.com/health

# Should return: {"status":"ok"}

# Test chat endpoint
curl -X POST https://your-render-url.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "I need a senior Java developer assessment"}
    ]
  }'
```

### Step 4: Submit

Your public base URL is: `https://your-app-name.onrender.com`

Both endpoints are accessible:
- `GET /health` - Health check
- `POST /chat` - Conversational interface

---

## Method 2: Railway (Alternative - 5 minutes)

### Requirements
- Node.js installed (for Railway CLI)

### Steps

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
cd "/Users/seshasaitunuguntla/Desktop/SHL Assignment"
railway init

# Deploy
railway up

# Add environment variables
railway variables set OPENAI_API_KEY=your-key-here
railway variables set CATALOG_PATH=data/catalog/shl_catalog.json
railway variables set LLM_PROVIDER=openai
railway variables set LLM_MODEL=gpt-4-turbo-preview

# Get your URL
railway domain
```

Your URL will be: `https://your-project.up.railway.app`

---

## Method 3: Fly.io (Alternative - 8 minutes)

### Requirements
- Fly CLI installed

### Steps

```bash
# Install Fly CLI (macOS)
brew install flyctl

# Login
fly auth login

# Navigate to project
cd "/Users/seshasaitunuguntla/Desktop/SHL Assignment"

# Create Procfile
echo "web: uvicorn src.api.main:app --host 0.0.0.0 --port \$PORT" > Procfile

# Launch (interactive setup)
fly launch
# Choose app name, region, don't setup Postgres

# Set secrets
fly secrets set OPENAI_API_KEY=your-key-here
fly secrets set CATALOG_PATH=data/catalog/shl_catalog.json
fly secrets set LLM_PROVIDER=openai

# Deploy
fly deploy

# Get URL
fly status
```

Your URL will be: `https://your-app-name.fly.dev`

---

## Method 4: Hugging Face Spaces (Free, but slower)

### Steps

1. Go to https://huggingface.co/spaces
2. Click "Create new Space"
3. Name: `shl-assessment-recommender`
4. SDK: `Gradio` or `Streamlit`
5. Upload your code
6. Add secrets in Settings

**Note**: Requires adapting the code for Gradio/Streamlit interface.

---

## Troubleshooting

### Issue: "Application failed to start"

**Check logs**:
- Render: Click "Logs" tab
- Railway: `railway logs`
- Fly.io: `fly logs`

**Common causes**:
1. Missing `OPENAI_API_KEY` environment variable
2. Wrong start command
3. Missing dependencies in `requirements.txt`
4. Catalog file not found

**Solutions**:
1. Verify all environment variables are set
2. Ensure start command is: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`
3. Check `requirements.txt` is complete
4. Make sure `data/catalog/shl_catalog.json` is committed to git

### Issue: "502 Bad Gateway"

**Cause**: App is still starting (cold start)

**Solution**: Wait 1-2 minutes, then retry

### Issue: "Health check failed"

**Cause**: App initialization takes time

**Solution**: 
- `/health` endpoint allows 2-minute grace period
- Wait and retry
- Check logs for errors

### Issue: Catalog not found

**Cause**: `data/catalog/shl_catalog.json` not in repository

**Solution**:
```bash
# Make sure catalog is committed
git add data/catalog/shl_catalog.json
git commit -m "Add catalog"
git push

# Or use mock catalog
cat > data/catalog/shl_catalog.json << 'EOF'
[
  {
    "name": "Java 8 (New)",
    "url": "https://www.shl.com/solutions/products/java-8/",
    "description": "Technical assessment for Java 8",
    "test_type": "K",
    "category": "Programming"
  }
]
EOF
```

### Issue: Slow responses

**Cause**: Free tier has limited resources

**Solutions**:
1. Use Groq instead of OpenAI (faster, free)
2. Reduce embedding model size
3. Upgrade to paid tier

---

## Verification Checklist

Before submitting, verify:

- [ ] `/health` returns `{"status":"ok"}` with 200 status
- [ ] `/chat` accepts POST requests with messages
- [ ] Vague query triggers clarification
- [ ] Specific query returns recommendations
- [ ] Recommendations include name, URL, test_type
- [ ] No fake assessments (all from catalog)
- [ ] Response time < 30 seconds
- [ ] API docs accessible at `/docs`

### Test Commands

```bash
# Set your URL
API_URL="https://your-app.onrender.com"

# Test 1: Health
curl $API_URL/health

# Test 2: Clarification
curl -X POST $API_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"I need an assessment"}]}'

# Test 3: Recommendation
curl -X POST $API_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Senior Java developer with team lead responsibilities"}]}'

# Test 4: Comparison
curl -X POST $API_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"What is the difference between OPQ32r and Verify G+?"}]}'
```

---

## What to Submit

### Required:
1. **Public API URL**: `https://your-app-name.onrender.com` (or Railway/Fly.io)
2. **APPROACH.md**: 2-page technical document (already created)

### Optional but Recommended:
3. **GitHub Repository**: Link to your code
4. **API Documentation**: Link to `/docs` endpoint

### Submission Format

**Base URL**: `https://shl-recommender-xxxxx.onrender.com`

**Endpoints**:
- `GET /health` - Returns `{"status":"ok"}`
- `POST /chat` - Conversational interface

**Documentation**: Included in repository

---

## Estimated Timings

| Method | Time | Cost | Difficulty |
|--------|------|------|------------|
| Render | 10 min | Free | Easy |
| Railway | 5 min | Free $5 credit | Easy |
| Fly.io | 8 min | Free tier | Medium |
| HF Spaces | 15 min | Free | Hard (needs adaptation) |

**Recommended**: Start with Render (easiest, most reliable)

---

## Need Help?

1. **Deployment Issues**: Check platform-specific docs
   - Render: https://render.com/docs
   - Railway: https://docs.railway.app
   - Fly.io: https://fly.io/docs

2. **API Issues**: Check logs and verify environment variables

3. **Testing Issues**: Use interactive docs at `/docs` endpoint

---

## Success!

Once deployed and tested, you have:
- ✅ Public API accessible via HTTPS
- ✅ Both /health and /chat endpoints working
- ✅ All assignment requirements met
- ✅ Ready to submit!

**Your submission**:
- Public Base URL: `https://your-app.onrender.com`
- Approach Document: `APPROACH.md` (2 pages)
- GitHub Repo (optional): `https://github.com/yourusername/shl-assessment-recommender`

Good luck! 🚀
