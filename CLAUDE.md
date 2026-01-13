# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

For comprehensive guidance on:
- Project architecture and structure
- Contribution guidelines and workflow
- Creating new tools
- Coding standards and best practices
- Git workflow

**Please refer to [AGENTS.md](AGENTS.md)** - this file contains all essential information for working in this repository.

## Essential Commands

### Local Development
```bash
# Start local web server from repository root
python -m http.server

# Access at http://localhost:8000
# Navigate to tools at http://localhost:8000/tools/<tool-name>/
```

### Testing
```bash
# Run pytest suite
pytest tests/

# Verify docstring parsing
python -c "from pycalcs import utils, <module>; print(utils.get_documentation('<module>', '<function>'))"
```

### Netlify Deployment & Site Management

**Live URLs:**
- Production: https://transparent.tools
- Legacy: https://amarschn.github.io (GitHub Pages, still active)

**Netlify CLI:**
```bash
# Install (one-time)
npm install -g netlify-cli

# Authenticate (one-time)
netlify login

# Link repo to Netlify site (one-time, from repo root)
netlify link

# Open admin dashboard
netlify open:admin

# Manual production deploy
netlify deploy --prod

# Preview deploy (generates preview URL)
netlify deploy
```

**Build Configuration:**
- Config file: `netlify.toml` (in repo root)
- No build step required (pure static HTML/JS)
- Publish directory: `.` (root)

**Support/Monetization:**
- Ko-fi: https://ko-fi.com/transparent_tools
