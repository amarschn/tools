# GEMINI.md

This file provides guidance to Google Gemini CLI when working with code in this repository.

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
