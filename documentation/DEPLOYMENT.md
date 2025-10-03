# Deployment Guide - Product Adder to Vercel

## Overview

This guide will help you deploy your Product Adder Flask application to Vercel, making it accessible via a public URL.

## Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **Vercel CLI**: Install with `npm i -g vercel`
3. **Git Repository**: Your code should be in a Git repository (GitHub, GitLab, or Bitbucket)

## Deployment Steps

### 1. Prepare Your Environment Variables

Create a `.env.production` file with your production environment variables:

```env
# Shopify Configuration
SHOPIFY_STORE=your-store.myshopify.com
SHOPIFY_API_VERSION=2023-10
SHOPIFY_ACCESS_TOKEN=your_access_token

# JDS API Configuration
EXTERNAL_API_URL=https://api.jdsapp.com/get-product-details-by-skus
EXTERNAL_API_TOKEN=your_jds_token

# Application Configuration
FLASK_ENV=production
DATABASE_URL=sqlite:///product_adder.db
SECRET_KEY=your_production_secret_key
APP_API_KEY=your_production_api_key
```

### 2. Deploy to Vercel

#### Option A: Using Vercel CLI

```bash
# Navigate to your project directory
cd /home/norllr/dev/morganicsPricing/product_adder

# Login to Vercel
vercel login

# Deploy
vercel

# Follow the prompts:
# - Set up and deploy? Y
# - Which scope? (select your account)
# - Link to existing project? N
# - Project name: product-adder (or your preferred name)
# - Directory: ./
# - Override settings? N
```

#### Option B: Using Vercel Dashboard

1. Go to [vercel.com/dashboard](https://vercel.com/dashboard)
2. Click "New Project"
3. Import your Git repository
4. Vercel will automatically detect it's a Python/Flask project
5. Configure environment variables in the dashboard
6. Deploy

### 3. Configure Environment Variables in Vercel

After deployment, add your environment variables in the Vercel dashboard:

1. Go to your project dashboard
2. Click on "Settings" tab
3. Click on "Environment Variables"
4. Add each variable from your `.env.production` file

### 4. Important Notes for Vercel Deployment

#### Database Considerations
- **SQLite Limitation**: Vercel's serverless environment has limitations with SQLite
- **File System**: The file system is read-only except for `/tmp`
- **Recommendation**: Consider using a cloud database like:
  - **PlanetScale** (MySQL)
  - **Supabase** (PostgreSQL)
  - **MongoDB Atlas**
  - **Vercel Postgres**

#### Alternative Database Setup
If you want to keep using SQLite, you'll need to modify the database path:

```python
# In database.py, update the database path for Vercel
import os

if os.environ.get('VERCEL'):
    # Vercel environment - use /tmp directory
    DATABASE_URL = 'sqlite:////tmp/product_adder.db'
else:
    # Local environment
    DATABASE_URL = 'sqlite:///product_adder.db'
```

### 5. Test Your Deployment

After deployment, test your application:

```bash
# Get your deployment URL from Vercel
# It will be something like: https://product-adder-abc123.vercel.app

# Test the health endpoint
curl https://your-app-url.vercel.app/api/health

# Test the main dashboard
# Open https://your-app-url.vercel.app in your browser
```

## Post-Deployment Configuration

### 1. Set Up Custom Domain (Optional)

1. Go to your project settings in Vercel
2. Click on "Domains"
3. Add your custom domain
4. Configure DNS settings as instructed

### 2. Configure Webhooks (If Needed)

If you need to sync data automatically, set up webhooks:

1. In your Vercel dashboard, go to "Functions"
2. Create a new serverless function for webhook handling
3. Configure your external services to call these webhooks

### 3. Monitor Performance

Use Vercel's built-in analytics:

1. Go to your project dashboard
2. Click on "Analytics" tab
3. Monitor performance, errors, and usage

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors
- **Problem**: SQLite database not accessible
- **Solution**: Use a cloud database or modify database path to `/tmp`

#### 2. Environment Variables Not Loading
- **Problem**: App can't access environment variables
- **Solution**: Ensure variables are set in Vercel dashboard and restart deployment

#### 3. Static Files Not Loading
- **Problem**: CSS/JS files not loading
- **Solution**: Check that static files are in the correct directory structure

#### 4. API Timeout Issues
- **Problem**: Long-running operations timing out
- **Solution**: Vercel has a 10-second timeout for serverless functions. Consider:
  - Breaking operations into smaller chunks
  - Using background jobs
  - Implementing async processing

### Debugging

1. **Check Vercel Logs**:
   ```bash
   vercel logs
   ```

2. **View Function Logs**:
   - Go to your project dashboard
   - Click on "Functions" tab
   - View logs for each function

3. **Test Locally with Vercel**:
   ```bash
   vercel dev
   ```

## Production Considerations

### 1. Security
- Use strong, unique API keys
- Enable HTTPS (automatic with Vercel)
- Implement rate limiting
- Validate all inputs

### 2. Performance
- Monitor response times
- Use Vercel's caching features
- Optimize database queries
- Implement proper error handling

### 3. Monitoring
- Set up error tracking (Sentry, etc.)
- Monitor API usage
- Track performance metrics
- Set up alerts for critical issues

## Next Steps

After successful deployment:

1. **Test all functionality** with your production environment
2. **Set up monitoring** and alerting
3. **Configure backups** for your database
4. **Document your deployment** for team members
5. **Set up CI/CD** for automatic deployments

## Support

If you encounter issues:

1. Check Vercel's documentation: [vercel.com/docs](https://vercel.com/docs)
2. Review your application logs
3. Test locally with `vercel dev`
4. Contact Vercel support if needed

---

**Your Product Adder application will be accessible at your Vercel URL once deployed!** 🚀
