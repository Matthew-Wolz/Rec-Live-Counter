# Deployment Guide: Vercel + WordPress Iframe

This guide will walk you through deploying your Rec Center Traffic Histogram application to Vercel and embedding it in WordPress.

## Prerequisites

- A GitHub account
- A Vercel account (free tier is sufficient)
- Your `service-account.json` file (for Google Sheets authentication)
- Your Google Sheet ID and range

## Step 1: Disconnect from Current GitHub Repo and Push to Your Own

### 1.1 Remove Current Remote
```bash
git remote remove origin
```

### 1.2 Create New GitHub Repository
1. Go to [GitHub](https://github.com) and sign in
2. Click the "+" icon in the top right → "New repository"
3. Name it (e.g., `rec-center-traffic-histogram`)
4. **Do NOT** initialize with README, .gitignore, or license
5. Click "Create repository"

### 1.3 Connect to Your New Repository
```bash
# Replace YOUR_USERNAME and REPO_NAME with your actual values
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git
```

### 1.4 Push Your Code
```bash
git add .
git commit -m "Prepare for Vercel deployment"
git branch -M main  # Ensure you're on main branch
git push -u origin main
```

## Step 2: Prepare Service Account Credentials

You need to convert your `service-account.json` file into a single-line JSON string for Vercel's environment variables.

### Option A: Using PowerShell (Windows)
```powershell
# Read the file and convert to single-line JSON
$content = Get-Content -Path "service-account.json" -Raw
$content = $content -replace "`r`n", "" -replace "`n", "" -replace " ", ""
$content | Set-Content -Path "service-account-oneline.txt"
```

Then copy the contents of `service-account-oneline.txt` (you'll need this in Step 3).

### Option B: Using Python
```python
import json

with open('service-account.json', 'r') as f:
    data = json.load(f)
    
# Convert to single-line string
json_string = json.dumps(data)
print(json_string)
```

Copy the entire output (it will be a long single line).

## Step 3: Deploy to Vercel

### 3.1 Sign Up / Log In to Vercel
1. Go to [vercel.com](https://vercel.com)
2. Sign up or log in (you can use your GitHub account)

### 3.2 Import Your Repository
1. Click "Add New..." → "Project"
2. Import your GitHub repository
3. Vercel should auto-detect it's a Python project

### 3.3 Configure Environment Variables
Before deploying, add these environment variables in Vercel:

1. Click "Environment Variables" in the project settings
2. Add the following variables:

   **SPREADSHEET_ID**
   - Value: Your Google Sheet ID (from the sheet URL)
   - Example: `1abc123def456ghi789jkl012mno345pq`

   **SHEET_RANGE**
   - Value: `A:Q` (or your custom range)
   - This is optional if you're using the default

   **GOOGLE_SERVICE_ACCOUNT**
   - Value: Paste the entire single-line JSON string from Step 2
   - This is the entire contents of your `service-account.json` as one line
   - **Important**: Make sure there are no line breaks in this value

### 3.4 Deploy
1. Click "Deploy"
2. Wait for the build to complete (usually 2-3 minutes)
3. Once deployed, you'll get a URL like: `https://your-app-name.vercel.app`

## Step 4: Test Your Deployment

1. Visit your Vercel URL: `https://your-app-name.vercel.app`
2. You should see your histogram application
3. Check the browser console (F12) for any errors
4. Test the API endpoint: `https://your-app-name.vercel.app/api/hourly_breakdown`

## Step 5: Embed in WordPress

### 5.1 Get Your Deployment URL
Your Vercel deployment URL is: `https://your-app-name.vercel.app`

### 5.2 Add to WordPress
1. Log in to your WordPress admin panel
2. Navigate to the page/post where you want to embed the histogram
3. Add a "Custom HTML" block (or use the HTML editor)
4. Paste this code:

```html
<iframe 
  src="https://your-app-name.vercel.app" 
  width="100%" 
  height="700" 
  frameborder="0"
  style="border: none; min-height: 700px;"
  title="Rec Center Live Occupancy">
</iframe>
```

5. Adjust the `height` value as needed (700px is a good starting point)
6. Save and preview your page

### 5.3 Responsive Iframe (Optional)
For better mobile support, you can use this responsive version:

```html
<div style="position: relative; padding-bottom: 100%; height: 0; overflow: hidden;">
  <iframe 
    src="https://your-app-name.vercel.app" 
    style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none;"
    title="Rec Center Live Occupancy">
  </iframe>
</div>
```

## Troubleshooting

### Issue: "No credentials found" error
- **Solution**: Make sure `GOOGLE_SERVICE_ACCOUNT` environment variable is set correctly in Vercel
- The JSON string must be on a single line with no line breaks
- Verify the JSON is valid by testing it in a JSON validator

### Issue: CORS errors in browser console
- **Solution**: The app already has CORS enabled. If you still see errors, check that the iframe is loading from the correct URL

### Issue: Chart not displaying
- **Solution**: 
  1. Check browser console for JavaScript errors
  2. Verify the API endpoint is working: `https://your-app-name.vercel.app/api/hourly_breakdown`
  3. Check that your Google Sheet ID and range are correct

### Issue: Build fails on Vercel
- **Solution**: 
  1. Check the build logs in Vercel dashboard
  2. Ensure `requirements.txt` has all dependencies
  3. Verify Python version compatibility (Vercel uses Python 3.9+)

## Updating Your Deployment

After making changes to your code:

1. Commit and push to your GitHub repository:
   ```bash
   git add .
   git commit -m "Your commit message"
   git push origin main
   ```

2. Vercel will automatically detect the push and redeploy
3. Your changes will be live in 1-2 minutes

## Vercel Free Tier Limits

- **Bandwidth**: 100 GB/month
- **Serverless Function Execution**: 100 GB-hours/month
- **Builds**: Unlimited
- **Deployments**: Unlimited

These limits are more than sufficient for most applications.

## Support

If you encounter issues:
1. Check Vercel deployment logs
2. Check browser console for errors
3. Verify all environment variables are set correctly
4. Test the API endpoint directly in your browser

