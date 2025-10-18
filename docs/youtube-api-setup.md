# YouTube API Setup Guide

**Story 1.2 - YouTube Data API v3 Configuration**

This guide walks you through setting up a YouTube Data API v3 key for the Safe YouTube Viewer application.

---

## Prerequisites

- Google account
- Access to [Google Cloud Console](https://console.cloud.google.com/)
- Basic understanding of API keys and environment variables

**Time Required:** 10-15 minutes

---

## 1. Creating a Google Cloud Project

1. **Navigate to Google Cloud Console:**
   - Visit https://console.cloud.google.com/
   - Sign in with your Google account

2. **Create a New Project** (or select existing):
   - Click the project dropdown at the top of the page
   - Click "**NEW PROJECT**"
   - Enter project name: `barne-tv` (or your preferred name)
   - Click "**CREATE**"
   - Wait for project creation (takes ~30 seconds)

3. **Select Your Project:**
   - Once created, ensure your new project is selected in the project dropdown

---

## 2. Enabling YouTube Data API v3

1. **Navigate to APIs & Services:**
   - In the left sidebar, click "**APIs & Services**" → "**Library**"
   - Or use the search bar: "APIs & Services"

2. **Search for YouTube Data API v3:**
   - In the API Library search box, type: `YouTube Data API v3`
   - Click on "**YouTube Data API v3**" in the results

3. **Enable the API:**
   - Click the blue "**ENABLE**" button
   - Wait for enablement (takes ~10 seconds)
   - You'll be redirected to the API dashboard

---

## 3. Generating an API Key

1. **Navigate to Credentials:**
   - In the left sidebar, click "**APIs & Services**" → "**Credentials**"

2. **Create Credentials:**
   - Click "**+ CREATE CREDENTIALS**" at the top
   - Select "**API key**" from the dropdown

3. **Copy Your API Key:**
   - A dialog will appear with your new API key
   - **IMPORTANT:** Copy this key immediately
   - Example format: `AIzaSyC...` (39 characters)

4. **Save the Key Securely:**
   - Store the key in a password manager or secure note
   - **NEVER commit this key to version control**
   - You'll add it to your `.env` file in step 5

---

## 4. Setting API Key Restrictions

**Critical for security:** Restrict your API key to prevent unauthorized use.

### Option A: For Local Development (Recommended)

1. **Click "Edit API key"** (or click the key name in credentials list)

2. **Set Application Restrictions:**
   - Select "**HTTP referrers (web sites)**"
   - Click "**+ ADD AN ITEM**"
   - Add these referrers:
     - `http://localhost:8000/*`
     - `http://localhost:5173/*`
     - `http://127.0.0.1:8000/*`
     - `http://127.0.0.1:5173/*`

3. **Set API Restrictions:**
   - Under "API restrictions", select "**Restrict key**"
   - Click "**Select APIs**"
   - Check only: **YouTube Data API v3**
   - Click "**OK**"

4. **Save:**
   - Click "**SAVE**" at the bottom

### Option B: For Production Deployment

1. **Click "Edit API key"**

2. **Set Application Restrictions:**
   - Select "**IP addresses (web servers, cron jobs, etc.)**"
   - Click "**+ ADD AN ITEM**"
   - Add your Hetzner VPS IP address (e.g., `195.201.123.45`)

3. **Set API Restrictions:**
   - Under "API restrictions", select "**Restrict key**"
   - Check only: **YouTube Data API v3**

4. **Save**

### Option C: No Restrictions (Not Recommended)

- **Only for testing:** You can leave restrictions as "None"
- **Security Risk:** If key is leaked, anyone can use it
- **Recommended:** Add restrictions as soon as possible

---

## 5. Adding API Key to .env File

1. **Navigate to your project directory:**
   ```bash
   cd /path/to/barne-tv
   ```

2. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Edit the .env file:**
   ```bash
   nano .env
   # or use your preferred editor: code .env, vim .env, etc.
   ```

4. **Add your API key:**
   ```env
   # YouTube Data API v3 key from Google Cloud Console
   YOUTUBE_API_KEY=AIzaSyC_your_actual_key_here
   ```

5. **Verify other settings:**
   ```env
   DATABASE_PATH=./data/app.db
   ALLOWED_HOSTS=localhost,127.0.0.1
   ENVIRONMENT=development
   ```

6. **Save and close** the file

7. **IMPORTANT: Verify .env is gitignored:**
   ```bash
   git check-ignore .env
   # Should output: .env
   ```

   If not output, add to `.gitignore`:
   ```bash
   echo ".env" >> .gitignore
   ```

---

## 6. Testing Your API Key

1. **Ensure dependencies are installed:**
   ```bash
   uv sync --extra dev
   ```

2. **Initialize the database:**
   ```bash
   mkdir -p data
   DATABASE_PATH=./data/app.db uv run python backend/db/init_db.py admin123
   ```

3. **Start the application:**
   ```bash
   uv run uvicorn backend.main:app --reload
   ```

4. **Check the startup logs:**
   ```
   INFO:     Validating YouTube API key...
   INFO:     YouTube API key validated successfully
   INFO:     Application startup complete.
   ```

   **If you see errors:**
   ```
   ERROR:    Invalid YouTube API key: <HttpError 403...>
   ```
   - Double-check your API key in `.env`
   - Verify API is enabled in Google Cloud Console
   - Check API key restrictions (try removing temporarily)

5. **Verify health endpoint:**
   ```bash
   curl http://127.0.0.1:8000/health
   # Should return: {"status":"ok"}
   ```

6. **Check database for validation log:**
   ```bash
   sqlite3 data/app.db "SELECT * FROM api_usage_log ORDER BY id DESC LIMIT 1;"
   ```

   Should show a validation entry with `success=1`

---

## 7. Understanding Quota Limits

### Daily Quota

- **Default:** 10,000 units per day
- **Resets:** Midnight Pacific Time (not UTC!)
- **Buffer:** Application uses 9,500 as threshold (500 unit safety margin)

### Quota Costs by Operation

| Operation | Quota Cost | Description |
|-----------|------------|-------------|
| `search().list()` | 100 units | Search for videos |
| `videos().list()` | 1 unit | Get video details |
| `channels().list()` | 1 unit | Get channel info |
| `playlistItems().list()` | 1 unit | List playlist videos |

### Example Usage Calculations

- **Fetch 50 videos from channel:**
  - 1 × search (100 units) + 50 × video details (50 units) = **150 units**

- **Fetch 200-video playlist:**
  - 200 × playlist items (200 units) + 200 × video details (200 units) = **400 units**

- **Add 5 channels with 50 videos each:**
  - 5 channels × 150 units = **750 units**

- **Daily capacity:**
  - ~66 channels with 50 videos each (9,900 units)
  - Or ~24 playlists with 200 videos each (9,600 units)

### Requesting Quota Increase

If 10,000 units/day is insufficient:

1. Navigate to: https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas
2. Select your project
3. Click "**EDIT QUOTAS**"
4. Request increase (up to 1,000,000 units/day with justification)
5. Google typically responds within 1-2 business days

---

## 8. Monitoring Quota Usage

### Real-Time Quota Check

```bash
# Check today's quota usage
sqlite3 data/app.db "SELECT SUM(quota_cost) FROM api_usage_log WHERE DATE(timestamp) = DATE('now');"
```

### Daily Usage Breakdown

```bash
# See all API calls today
sqlite3 data/app.db "
SELECT api_name, COUNT(*) as calls, SUM(quota_cost) as total_cost
FROM api_usage_log
WHERE DATE(timestamp) = DATE('now')
GROUP BY api_name;
"
```

### Historical Usage

```bash
# Last 7 days quota usage
sqlite3 data/app.db "
SELECT DATE(timestamp) as date, SUM(quota_cost) as total_quota
FROM api_usage_log
GROUP BY DATE(timestamp)
ORDER BY date DESC
LIMIT 7;
"
```

### Google Cloud Console

- Navigate to: https://console.cloud.google.com/apis/dashboard
- Select your project
- View usage graphs and metrics

---

## 9. Troubleshooting

### Issue: "CRITICAL: Invalid YouTube API key"

**Symptoms:**
```
ERROR:    CRITICAL: Invalid YouTube API key
ERROR:    Application will not function correctly without valid API key
```

**Solutions:**
1. **Verify API key in .env:**
   ```bash
   cat .env | grep YOUTUBE_API_KEY
   # Should show: YOUTUBE_API_KEY=AIzaSyC...
   ```

2. **Check YouTube API is enabled:**
   - Visit: https://console.cloud.google.com/apis/library
   - Search: "YouTube Data API v3"
   - Should show "**ENABLED**"

3. **Temporarily remove restrictions:**
   - Edit API key in Google Cloud Console
   - Set Application restrictions to "**None**"
   - Test again
   - Re-apply restrictions after confirming key works

4. **Verify no extra spaces/characters:**
   ```bash
   # API key should be exactly 39 characters
   python3 -c "import os; print(len(os.getenv('YOUTUBE_API_KEY', '')))"
   ```

5. **Check for typos:**
   - API keys always start with `AIza`
   - Copy-paste directly from Google Cloud Console

---

### Issue: "HTTP 403: quotaExceeded"

**Symptoms:**
```
ERROR:    HTTP 403: quotaExceeded - The request cannot be completed because you have exceeded your quota.
```

**Solutions:**
1. **Check current quota usage:**
   ```bash
   sqlite3 data/app.db "SELECT SUM(quota_cost) FROM api_usage_log WHERE DATE(timestamp) = DATE('now');"
   ```

2. **Wait for quota reset:**
   - Quota resets at midnight Pacific Time
   - Convert to your timezone:
     - Pacific (UTC-8): 00:00
     - CET (UTC+1): 09:00
     - UTC: 08:00

3. **Request quota increase:** (See section 7)

4. **Optimize API usage:**
   - Reduce refresh frequency
   - Cache video metadata
   - Remove unused channels/playlists

---

### Issue: Application starts but API calls fail

**Symptoms:**
- Startup validation succeeds
- But actual API calls return 403/400

**Solutions:**
1. **Check API restrictions:**
   - Restrictions might be too strict
   - For development, use HTTP referrer restrictions
   - For production, use IP restrictions

2. **Verify project selection:**
   - Make sure API is enabled in correct project
   - Check project dropdown in Google Cloud Console

3. **Check billing:**
   - Some Google Cloud features require billing enabled
   - Visit: https://console.cloud.google.com/billing

---

### Issue: ".env file not found"

**Symptoms:**
```
ERROR:    YOUTUBE_API_KEY environment variable is required
```

**Solutions:**
1. **Create .env from template:**
   ```bash
   cp .env.example .env
   ```

2. **Verify file location:**
   ```bash
   ls -la .env
   # Should show: .env file in project root
   ```

3. **Check file permissions:**
   ```bash
   chmod 600 .env  # Read/write for owner only
   ```

---

## 10. Security Best Practices

### DO:
- ✅ Keep API keys in `.env` file (gitignored)
- ✅ Use API restrictions (HTTP referrer or IP)
- ✅ Restrict to YouTube Data API v3 only
- ✅ Monitor quota usage regularly
- ✅ Rotate keys if compromised
- ✅ Use separate keys for dev/staging/production

### DON'T:
- ❌ Commit API keys to version control
- ❌ Share API keys in chat/email
- ❌ Use unrestricted keys in production
- ❌ Hardcode API keys in source code
- ❌ Expose keys in client-side JavaScript
- ❌ Leave keys in screenshots/documentation

### If API Key Compromised:

1. **Immediately revoke the key:**
   - Go to Google Cloud Console → Credentials
   - Click the trash icon next to compromised key
   - Click "**DELETE**"

2. **Generate a new key:**
   - Follow steps 3-4 above

3. **Update .env file:**
   - Replace old key with new key

4. **Restart application:**
   ```bash
   uv run uvicorn backend.main:app --reload
   ```

5. **Investigate usage:**
   - Check Google Cloud Console for unexpected API calls
   - Review quota usage for anomalies

---

## Next Steps

Now that your YouTube API is set up:

1. **Verify application works:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Check API validation succeeded:**
   ```bash
   sqlite3 data/app.db "SELECT * FROM api_usage_log WHERE api_name = 'youtube_search_validation' ORDER BY id DESC LIMIT 1;"
   ```

3. **Continue with development:**
   - Story 1.3: Content source management
   - Add YouTube channels and playlists
   - Fetch video metadata

4. **Monitor quota usage:**
   - Set up daily quota checks
   - Plan refresh schedules to stay under limit
   - Consider requesting increase if needed

---

## Additional Resources

- [YouTube Data API v3 Documentation](https://developers.google.com/youtube/v3)
- [Quota Calculator](https://developers.google.com/youtube/v3/determine_quota_cost)
- [Google Cloud Console](https://console.cloud.google.com/)
- [API Key Best Practices](https://cloud.google.com/docs/authentication/api-keys)

---

## Support

- **Application issues:** See project README.md
- **API key issues:** Review this guide's troubleshooting section
- **Google Cloud issues:** [Google Cloud Support](https://cloud.google.com/support)

---

**Last Updated:** 2025-10-18 (Story 1.2)
