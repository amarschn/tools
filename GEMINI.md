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

## Plans Folder Rule

Repository-level plan documents in `/plans/` must use `YYYY-MM-DD_short_slug.md` filenames and include a matching `Date: YYYY-MM-DD` line immediately below the H1 title. Use ISO dates so plans sort chronologically.

## Branch Workflow

- Keep `main` stable and deployable.
- Do non-trivial work on `task/<short-name>` branches.
- Use one task branch per piece of work, and reuse it across computers instead of creating separate machine-specific branches.
- Push task branches frequently and merge back to `main` only after verification.

## Essential Commands

### Local Development
```bash
# Start local web server from repository root
python -m http.server

# Access at http://localhost:8000
# Navigate to tools at http://localhost:8000/tools/<tool-name>/
```

### Parameter JSON Test Cases
Tools may include `test-cases/*.json` files with pre-configured input parameters.
See AGENTS.md "Parameter JSON Test Cases" for the full specification.
### Testing
```bash
# Run pytest suite
pytest tests/

# Verify docstring parsing
python -c "from pycalcs import utils, <module>; print(utils.get_documentation('<module>', '<function>'))"
```
