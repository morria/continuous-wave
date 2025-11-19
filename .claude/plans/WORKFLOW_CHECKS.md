# GitHub Workflow Checks Reference

This document lists every check run in the GitHub CI workflow and the exact local commands to reproduce them. The pre-commit hook at `.git/hooks/pre-commit` runs these exact checks automatically.

## Complete Check List

### 1. Black Formatting Check
**Purpose:** Ensures code is formatted consistently according to Black's style

**GitHub Workflow:**
```bash
black --check src/ tests/
```

**Local Command:**
```bash
black --check src/ tests/
```

**Auto-fix:**
```bash
black src/ tests/
# or
make format
```

**Configuration:** `pyproject.toml:117-119` (line-length=100, target-version=py311)

---

### 2. Ruff Linting
**Purpose:** Catches code quality issues, unused imports, potential bugs

**GitHub Workflow:**
```bash
ruff check src/ tests/
```

**Local Command:**
```bash
ruff check src/ tests/
```

**Auto-fix:**
```bash
ruff check src/ tests/ --fix
# or
make lint-fix
```

**Configuration:** `pyproject.toml:121-140` (line-length=100, various rules enabled)

---

### 3. MyPy Type Checking
**Purpose:** Ensures strict type safety across the codebase

**GitHub Workflow:**
```bash
python -m mypy src/continuous_wave --strict
```

**Local Command:**
```bash
python -m mypy src/continuous_wave --strict
```

**Configuration:** `pyproject.toml:82-115` (strict mode with overrides for specific modules)

**Note:** Some modules have `ignore_errors = true` as documented in the config

---

### 4. Pytest with Coverage
**Purpose:** Runs all tests and enforces 90% code coverage

**GitHub Workflow:**
```bash
pytest tests/ -v --cov=continuous_wave --cov-report=term-missing --cov-report=xml --cov-fail-under=90
```

**Local Command:**
```bash
pytest tests/ -v --cov=continuous_wave --cov-report=term-missing --cov-report=xml --cov-fail-under=90
# or
make test
```

**Configuration:** `pyproject.toml:66-80` (pytest settings)
**Coverage Config:** `pyproject.toml:142-167` (branch coverage, exclusions)

**Requirements:**
- Minimum 90% coverage
- Must test on both Python 3.11 and 3.12 (GitHub runs matrix)

---

### 5. Package Build
**Purpose:** Ensures the package can be built successfully for distribution

**GitHub Workflow:**
```bash
python -m build
```

**Local Command:**
```bash
python -m build
# or
make build
```

**Output:** Creates `dist/` directory with wheel and source distribution

---

## Pre-Commit Hook Enforcement

### Status: ✅ ACTIVE

The git pre-commit hook at `.git/hooks/pre-commit` automatically runs all 5 checks before allowing any commit.

### How It Works

1. You run `git commit -m "your message"`
2. Git triggers `.git/hooks/pre-commit`
3. Hook runs all 5 checks in sequence
4. **If all pass:** Commit succeeds ✅
5. **If any fail:** Commit is blocked ❌

### Hook Output

The hook provides clear, colorized output showing:
- Which check is running
- Pass/fail status for each check
- Quick fix suggestions if checks fail
- Overall verdict

### Bypassing (Not Recommended)

```bash
git commit --no-verify -m "bypass hook"
```

**WARNING:** This will cause CI to fail and your PR cannot be merged.

---

## Claude Code Integration

### Automatic Enforcement

Claude Code will **always** trigger the pre-commit hook when making commits. This means:
- ✅ Claude Code cannot commit code that will fail CI
- ✅ All checks must pass before commit
- ✅ You get immediate feedback locally
- ✅ No surprise CI failures

### Setup Verification

When a Claude Code session starts (`.claude/SessionStart`), it:
1. Verifies Python version (3.11+)
2. Installs development dependencies if needed
3. Runs sanity checks on tools
4. Shows available commands

The pre-commit hook is **always active** because it's in `.git/hooks/pre-commit`.

---

## Quick Reference Commands

```bash
# Run all checks manually (same as pre-commit hook)
make pre-commit

# Run individual checks
make format-check    # Black check only
make lint            # Ruff check only
make type-check      # MyPy check only
make test            # Pytest with coverage only
make build           # Package build only

# Auto-fix issues
make format          # Auto-format with Black
make lint-fix        # Auto-fix Ruff issues

# Run all checks that can auto-fix, then verify
make pre-commit
```

---

## GitHub CI Matrix Testing

While the pre-commit hook runs checks on your local Python version, the GitHub CI workflow runs tests on **both Python 3.11 and 3.12** in a matrix.

This means your local tests might pass on Python 3.11, but could fail on 3.12 in CI if there are version-specific issues.

**Recommendation:** If you're making changes that might be Python-version-sensitive, test locally with both versions before pushing.

---

## Differences: Pre-Commit Hook vs .pre-commit-config.yaml

The repository has two pre-commit systems:

### 1. Git Hook (`.git/hooks/pre-commit`) - **ACTIVE**
- ✅ Automatically runs on every commit
- ✅ Matches GitHub CI exactly
- ✅ No additional installation needed
- ✅ Works with Claude Code automatically

### 2. Pre-commit Framework (`.pre-commit-config.yaml`) - **OPTIONAL**
- Requires `pip install pre-commit && pre-commit install`
- Provides additional hooks (trailing whitespace, etc.)
- Can be used instead of git hook
- Both are configured to match CI exactly

**You only need one.** The git hook is already active.

---

## Troubleshooting

### Hook doesn't run
```bash
# Check if hook exists and is executable
ls -la .git/hooks/pre-commit
# Should show: -rwxr-xr-x (x = executable)

# Make it executable if needed
chmod +x .git/hooks/pre-commit
```

### Checks fail locally but you think they're correct
```bash
# Ensure you have latest dependencies
pip install -r requirements-dev.txt
pip install -e .

# Clean cached files
make clean

# Try again
make pre-commit
```

### Need to commit despite failures (emergency only)
```bash
git commit --no-verify -m "emergency commit"
```
**Then immediately fix the issues and create a new commit.**

---

## Summary

| Check | Command | Auto-fix Available | Required | Enforced By |
|-------|---------|-------------------|----------|-------------|
| Black | `black --check src/ tests/` | Yes (`make format`) | ✅ | Pre-commit hook |
| Ruff | `ruff check src/ tests/` | Yes (`make lint-fix`) | ✅ | Pre-commit hook |
| MyPy | `python -m mypy src/continuous_wave --strict` | No | ✅ | Pre-commit hook |
| Pytest | `pytest tests/ -v --cov=... --cov-fail-under=90` | No | ✅ | Pre-commit hook |
| Build | `python -m build` | No | ✅ | Pre-commit hook |

**All checks must pass for commit to succeed. All checks match GitHub CI exactly.**
