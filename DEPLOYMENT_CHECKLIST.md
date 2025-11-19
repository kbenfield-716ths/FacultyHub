# Deployment Checklist - CRITICAL STEPS

## ⚠️ BEFORE YOU DEPLOY

### 1. Check if Volume Exists

```bash
fly volumes list
```

**Expected output:**
```
ID                      NAME                SIZE    REGION  ZONE    ENCRYPTED       ATTACHED VM     CREATED AT
vol_xxxxxxxxxxxxx       moonlighter_data    1GB     iad     xxxx    true            xxxxxxxxxx      2025-xx-xx
```

**If you see nothing:**

```bash
fly volumes create moonlighter_data --region iad --size 1
```

### 2. Verify Volume is in fly.toml

Open `fly.toml` and verify this section exists:

```toml
[mounts]
  source = "moonlighter_data"
  destination = "/data"
```

### 3. Check Current Database Location

Before deploying, SSH in and check:

```bash
fly ssh console
ls -la /data/
ls -la /app/
exit
```

**If you see `moonlighter.db` in `/app/` instead of `/data/`**, your data will be lost on redeploy!

---

## 🚀 DEPLOYMENT STEPS

### Deploy

```bash
fly deploy
```

### Immediately After Deploy - Verify Volume Mount

```bash
# SSH into the container
fly ssh console

# Check if /data exists and is writable
ls -la /data/
touch /data/test.txt
ls -la /data/test.txt

# Check database location
ls -la /data/moonlighter.db

# If database doesn't exist yet, it will be created on first request
exit
```

---

## 🧪 TEST AFTER DEPLOYMENT

### 1. Health Check

```bash
curl https://moonlighter-web.fly.dev/
```

Should return: `{"status":"ok"}`

### 2. Check Logs for Errors

```bash
fly logs
```

Look for:
- ✅ `[seed_providers] Seeding complete`
- ✅ Database path: `/data/moonlighter.db`
- ❌ Any import errors
- ❌ Any permission errors on `/data`

### 3. Test Signup Flow

1. Visit: https://moonlighter-web.fly.dev/signup.html
2. Select a provider
3. Pick some dates
4. Save
5. Visit admin page and verify data is there

### 4. Stop and Restart - Verify Data Persists

```bash
# Get machine ID
fly status

# Stop
fly machine stop <machine-id>

# Start
fly machine start <machine-id>

# Check if data is still there
fly ssh console
ls -la /data/moonlighter.db
sqlite3 /data/moonlighter.db "SELECT COUNT(*) FROM signups;"
exit
```

If count is > 0, data persisted! ✅

---

## 🐛 TROUBLESHOOTING DATA LOSS

### Symptom: Data disappears after restart

**Check 1: Is volume mounted?**

```bash
fly ssh console
df -h | grep data
```

Should show `/data` mounted.

**Check 2: Is database in the right place?**

```bash
fly ssh console
find / -name "moonlighter.db" 2>/dev/null
```

Should ONLY show `/data/moonlighter.db`

If it shows `/app/moonlighter.db`, the volume isn't working!

**Fix:**

```bash
# SSH in
fly ssh console

# Move the database to the volume
cp /app/moonlighter.db /data/moonlighter.db

# Verify
ls -la /data/moonlighter.db
exit

# Redeploy to use the right path
fly deploy
```

### Symptom: Volume exists but not attached

```bash
fly volumes list
```

If `ATTACHED VM` column is empty:

```bash
fly deploy --force
```

### Symptom: Permission denied on /data

```bash
fly ssh console
sudo chown -R 1000:1000 /data
sudo chmod -R 755 /data
exit
```

---

## 📊 VERIFY OPTIMIZER WORKS

### After Some Faculty Have Signed Up:

1. Go to: https://moonlighter-web.fly.dev/Admin.html
2. Select month with signups
3. Click "Run optimizer"
4. Watch the browser console (F12)
5. Check fly logs:

```bash
fly logs
```

Look for:
- ✅ `[optimizer] Found X faculty with signups`
- ✅ `[optimizer] DataFrame shape: (X, 5)`
- ✅ `[optimizer] Generated schedule for X nights`
- ✅ `[optimizer] Created X assignments`
- ❌ Any Python import errors
- ❌ Any optimizer crashes

---

## 🔄 MIGRATION FROM OLD DATABASE

### If you had data before and lost it:

**Option 1: Restore from backup CSV**

1. If you downloaded CSV before, you can re-import
2. Have each faculty re-signup (fastest)

**Option 2: Try to recover old database**

```bash
# SSH in
fly ssh console

# Check if old database exists anywhere
find /app -name "*.db" 2>/dev/null

# If found, copy to volume
cp /app/moonlighter.db /data/moonlighter.db

exit
```

---

## ✅ SUCCESS CHECKLIST

Before considering deployment complete:

- [ ] Volume exists: `fly volumes list`
- [ ] Volume is mounted in fly.toml
- [ ] Database is at `/data/moonlighter.db`
- [ ] Health check passes
- [ ] Can sign up as faculty
- [ ] Data persists after machine stop/start
- [ ] Admin page shows signups
- [ ] Optimizer runs without errors
- [ ] CSV download works
- [ ] Logs show no errors

---

## 💾 BACKUP STRATEGY

Set up a weekly backup:

```bash
#!/bin/bash
# backup_moonlighter.sh

DATE=$(date +%Y%m%d)
fly ssh console -C "cat /data/moonlighter.db" > moonlighter_backup_${DATE}.db
echo "Backup saved: moonlighter_backup_${DATE}.db"
```

Run this every Sunday evening.
