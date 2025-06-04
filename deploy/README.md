# Website Deployment

This directory contains the production-ready website files for Netlify deployment.

## Structure

- `public/` - Contains all website files ready for serving
  - `index.html` - Homepage (LawyersInc landing page)
  - `about.html` - About page
  - `happy.html` - Happy page with smiley emoji
  - `lawyer-incorporated.html` - Lawyer Incorporated page
  - `lawyer-now.html` - Finding a Lawyer NOW page
  - `color-test.html` - Color test page
  - `test.html` - Test page

- `netlify.toml` - Netlify configuration file

## Deployment Process

1. **Manual**: Drag the `public/` folder contents to Netlify
2. **Automated**: Git push triggers auto-deployment
3. **Agent**: AI agent copies files here and commits changes

## Local Development

To test locally:
```bash
cd public
python3 -m http.server 8000
# Visit http://localhost:8000
```

## Agent Integration

The web design agent will:
1. Update files in `wordpress_clone/pages/`
2. Copy changes to `deploy/public/`
3. Commit and push to trigger deployment 