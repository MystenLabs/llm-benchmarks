# Deploying to Vercel

This guide provides steps for deploying the Gymnasuium application to Vercel.

## Prerequisites

1. A [Vercel account](https://vercel.com/signup)
2. [Vercel CLI](https://vercel.com/cli) (optional for command-line deployment)

## Pre-deployment Setup

Before deploying, make sure the `public/test_outputs` directory contains all your report files. These files are required for the application to display reports properly.

```bash
# Copy test output files to the public directory (if not already done)
cp -r test_outputs/* gymnasuium-server/public/test_outputs/
```

## Deployment Steps

### Option 1: Deploy Using the Vercel Dashboard

1. Push your repository to GitHub, GitLab, or Bitbucket
2. Log in to the [Vercel Dashboard](https://vercel.com/dashboard)
3. Click "Add New" > "Project"
4. Import your repository
5. Configure the project:
   - Select the `gymnasuium-server` directory as the root directory
   - Vercel should automatically detect it's a Next.js application
6. Set required environment variables:
   - Copy all values from your `.env` or `.env.local` file
   - Add them to the Environment Variables section in Vercel
7. Click "Deploy"

### Option 2: Deploy Using Vercel CLI

1. Install Vercel CLI if you haven't already: `npm i -g vercel`
2. Navigate to the gymnasuium-server directory: `cd gymnasuium-server`
3. Login to Vercel: `vercel login`
4. Deploy the application:
   - For production: `vercel --prod`
   - For preview/development: `vercel`
5. Follow the CLI prompts to complete the deployment

## Important Notes

- The application is configured to use files in the `public/test_outputs` directory
- If you add new test outputs locally, you'll need to copy them to the public directory and redeploy
- Make sure all required environment variables are set in Vercel
- If you update the code, you can redeploy using `vercel --prod` or through the Vercel dashboard

## Troubleshooting

If you encounter issues with the deployment:

1. Check Vercel deployment logs in the dashboard
2. Ensure all environment variables are correctly set
3. Verify the build command and output directory in `vercel.json` are correct
4. Make sure your project dependencies are correctly listed in `package.json`
5. If reports aren't showing up, verify the test output files were properly copied to `public/test_outputs`

## Additional Resources

- [Vercel Documentation](https://vercel.com/docs)
- [Next.js on Vercel](https://nextjs.org/docs/deployment) 