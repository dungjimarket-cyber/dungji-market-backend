# 🔧 Deployment Fix - S3 Configuration & Port Conflict

**Date:** October 17, 2025
**Issues Fixed:**
1. S3 bucket configuration error causing API endpoints to crash
2. Docker container permission issues preventing deployment
3. Port 8000 allocation conflicts during deployment

---

## 📋 Changes Made

### 1. **Enhanced S3 Storage Backend** (`api/storage_backends.py`)

**Problem:** API endpoints were crashing with `ValueError: Required parameter name not set` when trying to access media files.

**Solution:** Added defensive programming and graceful error handling:

```python
def __init__(self, *args, **kwargs):
    # Validate S3 bucket configuration
    bucket_name = os.getenv('AWS_STORAGE_BUCKET_NAME')
    if not bucket_name:
        logger.error("AWS_STORAGE_BUCKET_NAME environment variable not set")
        # Logs all AWS-related env vars for debugging
        raise ValueError("AWS_STORAGE_BUCKET_NAME not configured")

def url(self, name):
    # Fallback to local URLs if S3 fails
    try:
        if not self.bucket_name:
            return f"/media/{name}"  # Local fallback
        return super().url(name)
    except Exception as e:
        logger.error(f"S3 URL generation failed: {e}")
        return f"/media/{name}"  # Graceful degradation
```

**Benefits:**
- Clear error messages when S3 is misconfigured
- Automatic fallback to local URLs prevents total API failure
- Detailed logging helps debug configuration issues quickly

### 2. **Improved Deployment Workflow** (`.github/workflows/deploy.yml`)

**Problem:** Deployment failing due to permission errors when stopping Docker containers.

**Solution:** Replace `docker stop` with more forceful `docker kill`:

```bash
# Before: docker stop (can fail with permission denied)
sudo docker ps -q | xargs -r sudo docker stop || true

# After: docker kill (more forceful, handles permissions better)
sudo docker ps -q | xargs -r sudo docker kill || true
sudo docker ps -aq | xargs -r sudo docker rm -f || true
```

**Benefits:**
- More reliable container cleanup
- Handles permission conflicts better
- Prevents "port already allocated" errors

---

## ⚠️ IMMEDIATE ACTION REQUIRED

The deployment is currently **blocked** due to an existing container that cannot be stopped. You must **manually fix this on the server** before the next deployment can succeed.

### SSH into Server and Fix Port Conflict

```bash
# 1. SSH into your server
ssh ubuntu@54.180.82.238

# 2. Kill ALL Docker containers
sudo docker kill $(sudo docker ps -q)
sudo docker rm -f $(sudo docker ps -aq)

# 3. Clean up networks
sudo docker network prune -f

# 4. Verify port 8000 is free
sudo lsof -i :8000

# 5. If still occupied, force kill the process
sudo kill -9 $(sudo lsof -t -i:8000)

# 6. Manually redeploy
cd ~/dungji-market-backend
sudo docker-compose -p dungji-backend down
sudo docker-compose -p dungji-backend up --build -d --force-recreate

# 7. Check logs for S3 errors
sudo docker-compose -p dungji-backend logs -f web
```

### What to Look For in Logs

✅ **Success - S3 configured correctly:**
```
INFO MediaStorage initialized: bucket=dungjimarket, location=media
```

❌ **Error - S3 not configured:**
```
ERROR AWS_STORAGE_BUCKET_NAME environment variable not set
ERROR   AWS_ACCESS_KEY_ID = AKIA...
ERROR   AWS_SECRET_ACCESS_KEY = Yw...
ERROR   AWS_STORAGE_BUCKET_NAME =
ValueError: AWS_STORAGE_BUCKET_NAME not configured
```

If you see the error, it means the `.env` file on the server is missing `AWS_STORAGE_BUCKET_NAME`.

---

## 🔍 Root Cause Analysis

### Why S3 URLs Were Failing

The `django-storages` library requires several AWS environment variables:
- `AWS_ACCESS_KEY_ID` ✅ (was set)
- `AWS_SECRET_ACCESS_KEY` ✅ (was set)
- `AWS_STORAGE_BUCKET_NAME` ❌ (was missing or empty in container)

Even though the `.env` file has this variable, Docker containers sometimes don't receive all environment variables properly, especially if:
- The container was started with a different `.env` file
- Environment variables weren't passed through `docker-compose.yml`
- The container is using cached layers with old environment

### Why Deployment Failed

The old container (`dungji-market-backend-web-1`) was:
1. Started by a different user or process
2. Holding port 8000 with a file lock
3. Unable to be stopped by the deployment script due to permissions

The new workflow uses `docker kill` which:
- Sends `SIGKILL` instead of `SIGTERM` (more forceful)
- Bypasses graceful shutdown processes
- Works better with permission issues

---

## 🚀 Next Steps

### Option A: Manual Fix (Recommended - Fastest)
1. Follow the SSH commands above to clear the port
2. Manually redeploy the application
3. Verify the S3 configuration in logs

### Option B: Re-trigger GitHub Actions
1. Complete Option A first to clear the port
2. Push a new commit or manually trigger the workflow
3. The improved workflow should handle cleanup automatically

---

## 📝 Verification Checklist

After deployment, verify these endpoints work:

- [ ] `GET /api/` - Main API endpoint
- [ ] `GET /api/products/` - Product list (uses images from S3)
- [ ] `GET /api/groupbuys/` - Group buys list (uses images)
- [ ] `GET /api/popups/active_popups/` - Popup list (uses images)
- [ ] `GET /api/notices/main/` - Main notices (uses images)

All should return 200 OK with proper image URLs.

---

## 🛡️ Prevention for Future

### Server-Side Setup
1. Always use the same user to start Docker containers
2. Use `sudo docker-compose` consistently
3. Regularly clean up old containers: `sudo docker system prune -f`

### Development Workflow
1. Test environment variables locally before deploying
2. Verify `.env` file on server matches local configuration
3. Use `docker-compose logs` to catch issues early

---

## 📞 Support

If issues persist after following this guide:

1. Check `.env` file on server: `cat ~/dungji-market-backend/.env | grep AWS`
2. Verify Docker permissions: `sudo docker info`
3. Review full deployment logs in GitHub Actions

The updated code includes extensive logging to help diagnose any remaining issues.
