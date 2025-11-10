# Quick Start: Deploy to Vercel

## Summary of Changes Made

All the code has been set up for Vercel deployment. Here's what was added/modified:

### New Files Created:
- `vercel.json` - Vercel configuration
- `api/index.py` - Serverless function entry point
- `DEPLOYMENT.md` - Detailed deployment guide
- `convert-service-account.ps1` - Helper script to prepare credentials
- `QUICK_START.md` - This file

### Modified Files:
- `backend/app/sheets.py` - Now reads credentials from environment variable
- `requirements.txt` - Added flask-cors dependency
- `.gitignore` - Added service-account.json and token.json

## Quick Deployment Steps

### 1. Disconnect from Current Repo & Push to Your Own

```powershell
# Remove current remote
git remote remove origin

# Create a new repository on GitHub (via web interface)
# Then connect to it:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Push your code
git add .
git commit -m "Setup for Vercel deployment"
git push -u origin main
```

### 2. Prepare Service Account Credentials

Run the helper script:
```powershell
.\convert-service-account.ps1
```

This creates `service-account-oneline.txt` with your credentials in the right format.

### 3. Deploy to Vercel

1. Go to [vercel.com](https://vercel.com) and sign in
2. Click "Add New..." → "Project"
3. Import your GitHub repository
4. **Before deploying**, click "Environment Variables" and add:
   - `SPREADSHEET_ID` = Your Google Sheet ID
   - `SHEET_RANGE` = `A:Q` (or your range)
   - `GOOGLE_SERVICE_ACCOUNT` = Paste entire contents of `service-account-oneline.txt`
5. Click "Deploy"
6. Wait 2-3 minutes for deployment

### 4. Get Your URL

After deployment, you'll get a URL like: `https://your-app-name.vercel.app`

### 5. Embed in WordPress

Add this to your WordPress page (Custom HTML block):

```html
<iframe 
  src="https://your-app-name.vercel.app" 
  width="100%" 
  height="700" 
  frameborder="0"
  style="border: none;"
  title="Rec Center Live Occupancy">
</iframe>
```

Replace `https://your-app-name.vercel.app` with your actual Vercel URL.

## That's It!

Your app should now be live and embeddable in WordPress. See `DEPLOYMENT.md` for detailed troubleshooting and advanced options.

