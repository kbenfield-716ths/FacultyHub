# IRPA Moonlighter Deployment Guide

## Initial Setup (One Time)

### 1. Create Persistent Volume

Run this command in your terminal:

```bash
fly volumes create moonlighter_data --region iad --size 1
```

This creates a 1GB volume for your SQLite database. Cost: **$0.15/month**

### 2. Deploy the Application

```bash
fly deploy
```

This will:
- Build the Docker container
- Deploy to Fly.io
- Seed the provider list from faculty.csv
- Start the application

## URLs

- **Signup Page**: https://moonlighter-web.fly.dev/signup.html
- **Admin Dashboard**: https://moonlighter-web.fly.dev/Admin.html
- **API Health Check**: https://moonlighter-web.fly.dev/

## Cost Breakdown

With `min_machines_running = 0` (auto-stop when idle):

- **Active usage** (when faculty are signing up): ~$0.20/day
- **Idle** (rest of the month): ~$0.005/day
- **Storage** (always): $0.15/month
- **Estimated monthly cost**: $2-3
- **Estimated annual cost**: $24-36

## Auto-Stop Feature

The application automatically:
- **Stops** after 5 minutes of no requests
- **Starts** automatically when someone visits the URL
- **Cold start time**: 2-3 seconds (acceptable for monthly signup)

## Managing the Application

### View Logs

```bash
fly logs
```

### Check Status

```bash
fly status
```

### Manually Stop/Start

```bash
# Stop
fly machine stop <machine-id>

# Start
fly machine start <machine-id>

# Get machine ID
fly status
```

### Or Use the Fly.io Mobile App

1. Download: [iOS](https://apps.apple.com/app/fly-io/id1540857389) | [Android](https://play.google.com/store/apps/details?id=io.fly.flyctl)
2. Log in with your Fly.io account
3. Select "moonlighter-web"
4. Tap to stop/start machines

## Monthly Workflow

### Week 1: Send Signup Link

1. Email faculty: https://moonlighter-web.fly.dev/signup.html
2. Deadline: 10 days before month starts

### Week 3: Generate Schedule

1. Open: https://moonlighter-web.fly.dev/Admin.html
2. Select month
3. Click "Refresh signups" - verify everyone has signed up
4. Click "Run optimizer for month" - generates assignments
5. Click "Download signups CSV" if you want a backup

### Week 4: Distribute Schedule

1. Review the generated schedule in admin view
2. Export if needed
3. Email schedule to faculty

## Updating Faculty List

### Method 1: Edit faculty.csv and Redeploy

1. Edit `faculty.csv` in the repository
2. Commit and push
3. Run `fly deploy`
4. Providers will be added on next startup (existing providers won't be duplicated)

### Method 2: Direct Database Access (Advanced)

```bash
# SSH into the machine
fly ssh console

# Open SQLite
sqlite3 /data/moonlighter.db

# Add a provider
INSERT INTO providers (id, name, email) VALUES ('smith_j', 'Dr. Jane Smith', 'smith@virginia.edu');

# Exit
.quit
exit
```

## Troubleshooting

### "Application not found" Error

The machine is stopped. Just visit the URL and it will start automatically.

### Signups Not Showing Up

Check logs:

```bash
fly logs
```

Look for database errors or API errors.

### Optimizer Not Running

Check that pandas is installed:

```bash
fly ssh console
python -c "import pandas; print(pandas.__version__)"
```

If not found, redeploy:

```bash
fly deploy
```

### Database Corruption

**Backup the volume first:**

```bash
fly ssh console
cp /data/moonlighter.db /tmp/moonlighter_backup.db
exit
```

**Then recreate the database:**

```bash
fly ssh console
rm /data/moonlighter.db
exit
fly deploy
```

## Backup Strategy

### Manual Backup

```bash
# Download the database
fly ssh console
cat /data/moonlighter.db | base64
# Copy output, paste into local file, decode:
base64 -d > moonlighter_backup.db
```

### Automated Backup (Optional)

Create a GitHub Action (see `.github/workflows/backup.yml.example`)

## Handoff to Successor

### What They Need

1. **Fly.io account** - Add them as a collaborator:
   ```bash
   fly apps list
   # Go to dashboard and add collaborator
   ```

2. **This documentation** - Point them to this file

3. **URLs**:
   - Signup: https://moonlighter-web.fly.dev/signup.html
   - Admin: https://moonlighter-web.fly.dev/Admin.html

4. **Mobile App** - Install Fly.io app for remote control

### What They Need to Know

- Click "Run optimizer" once faculty have signed up
- Download CSV for records
- Cost is ~$2-3/month
- Machine auto-stops when idle (saves money)

### Emergency Fallback

If the system breaks:

1. Download CSV of signups
2. Manually assign faculty to shifts in Excel
3. Email results
4. Contact original developer (Dr. Benfield) for help

## Security Notes

### Current Setup

- **No authentication** - Anyone with the URL can sign up
- **Admin page** - No password protection
- **Acceptable for** - Internal use within trusted faculty group

### Adding Authentication (Future)

If you need to add authentication:

1. Add basic auth to FastAPI
2. Use environment variables for credentials:
   ```bash
   fly secrets set ADMIN_PASSWORD=your_password_here
   ```

## Monitoring

### Check if Running

```bash
fly status
```

### View Metrics

```bash
fly dashboard
```

Or visit: https://fly.io/apps/moonlighter-web

## Support

- **Fly.io Docs**: https://fly.io/docs/
- **Fly.io Community**: https://community.fly.io/
- **This Project**: https://github.com/kbenfield-716ths/moonlighter-web
