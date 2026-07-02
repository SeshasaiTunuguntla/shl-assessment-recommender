# Quick Start Guide

Get the SHL Assessment Recommender running in 5 minutes.

## Prerequisites

- Python 3.8+ installed
- OpenAI API key (or free alternative: Groq, Gemini)
- Internet connection for scraping

## Steps

### 1. Setup Environment

```bash
# Navigate to project directory
cd "SHL Assignment"

# Run setup script (creates venv, installs dependencies)
bash scripts/setup.sh

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows
```

### 2. Configure API Keys

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your API key
# You can use any of these:
# - OPENAI_API_KEY=sk-...
# - GROQ_API_KEY=gsk_...  (Free!)
# - GEMINI_API_KEY=...    (Free!)
```

**Get free API keys:**
- Groq: https://console.groq.com/ (Fast, free Mixtral/Llama)
- Gemini: https://makersuite.google.com/app/apikey

### 3. Scrape SHL Catalog

```bash
# This creates data/catalog/shl_catalog.json
python src/scraper/scrape_catalog.py
```

**Note:** Scraping may take 2-5 minutes depending on the catalog size. If it fails due to website changes, you can create a mock catalog for testing:

```bash
# Create mock catalog (for testing only)
mkdir -p data/catalog
cat > data/catalog/shl_catalog.json << 'EOF'
[
  {
    "name": "Java 8 (New)",
    "url": "https://www.shl.com/solutions/products/java-8-new/",
    "description": "Technical assessment for Java 8 programming knowledge",
    "test_type": "K",
    "category": "Programming",
    "duration": "45 min"
  },
  {
    "name": "OPQ32r",
    "url": "https://www.shl.com/solutions/products/opq32r/",
    "description": "Occupational personality questionnaire measuring 32 traits",
    "test_type": "P",
    "category": "Personality",
    "duration": "25 min"
  },
  {
    "name": "Verify G+",
    "url": "https://www.shl.com/solutions/products/verify-g-plus/",
    "description": "General cognitive ability assessment",
    "test_type": "A",
    "category": "Cognitive",
    "duration": "30 min"
  }
]
EOF
```

### 4. Start the API Server

```bash
# Start with auto-reload (for development)
uvicorn src.api.main:app --reload

# OR for production
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Wait for:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### 5. Test It!

Open a new terminal and run:

```bash
# Activate venv again
source venv/bin/activate

# Run test script
python scripts/test_api.py
```

Or test manually with curl:

```bash
# Health check
curl http://localhost:8000/health

# Chat request
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "I'\''m hiring a senior Java developer"}
    ]
  }'
```

Or visit the interactive docs:
```
http://localhost:8000/docs
```

## What to Expect

### First Request (Vague Query)
```json
{
  "messages": [
    {"role": "user", "content": "I need an assessment"}
  ]
}
```

**Response:**
```json
{
  "reply": "I'd be happy to help! What role are you hiring for?",
  "recommendations": [],
  "end_of_conversation": false
}
```

### Follow-up (Specific Query)
```json
{
  "messages": [
    {"role": "user", "content": "I need an assessment"},
    {"role": "assistant", "content": "I'd be happy to help! What role are you hiring for?"},
    {"role": "user", "content": "Senior Java developer with team lead responsibilities"}
  ]
}
```

**Response:**
```json
{
  "reply": "Great! Here are 5 assessments for a senior Java developer with leadership duties:\n\n1. **Java 8** - Tests core Java knowledge...",
  "recommendations": [
    {
      "name": "Java 8 (New)",
      "url": "https://www.shl.com/...",
      "test_type": "K"
    },
    {
      "name": "OPQ32r",
      "url": "https://www.shl.com/...",
      "test_type": "P"
    }
  ],
  "end_of_conversation": false
}
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'fastapi'"
**Solution:** Make sure venv is activated and dependencies installed:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: "OPENAI_API_KEY not found"
**Solution:** Create .env file and add your key:
```bash
echo "OPENAI_API_KEY=your-key-here" > .env
```

Or use a free alternative:
```bash
echo "LLM_PROVIDER=groq" >> .env
echo "GROQ_API_KEY=your-groq-key" >> .env
```

### Issue: Scraper fails / no catalog
**Solution:** Use the mock catalog above or check internet connection

### Issue: API returns 503 Service Unavailable
**Solution:** Wait 10-30 seconds for initialization, then retry

### Issue: Slow responses (>30 seconds)
**Solution:** 
- Check your internet connection
- Try switching to Groq (faster than OpenAI):
  ```bash
  echo "LLM_PROVIDER=groq" >> .env
  echo "LLM_MODEL=mixtral-8x7b-32768" >> .env
  ```

## Next Steps

Once it's working:

1. **Explore the API docs:** http://localhost:8000/docs
2. **Run evaluations:** `python src/evaluation/evaluate.py`
3. **Read technical details:** See `APPROACH.md`
4. **Understand the code:** See `EXPLANATION.md`

## Deploy to Cloud (Optional)

### Render (Free tier)

1. Push code to GitHub
2. Go to https://render.com
3. Create new "Web Service"
4. Connect your repo
5. Set build command: `pip install -r requirements.txt`
6. Set start command: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`
7. Add environment variables (OPENAI_API_KEY, etc.)
8. Deploy!

### Railway (Free $5 credit)

1. Install Railway CLI: `npm install -g @railway/cli`
2. Login: `railway login`
3. Initialize: `railway init`
4. Deploy: `railway up`
5. Add env vars: `railway variables set OPENAI_API_KEY=...`

### Fly.io (Free tier)

1. Install flyctl: https://fly.io/docs/hands-on/install-flyctl/
2. Login: `fly auth login`
3. Launch: `fly launch`
4. Set secrets: `fly secrets set OPENAI_API_KEY=...`
5. Deploy: `fly deploy`

## Need Help?

- **API not starting:** Check logs for specific error
- **Wrong responses:** Verify .env has correct API key
- **Evaluation failing:** Make sure you have test traces in data/traces/

---

Happy building! 🚀
