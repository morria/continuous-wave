# Git Hooks

This directory contains git hooks that can be installed to run automated checks before commits.

## Pre-commit Hook

The pre-commit hook runs the same checks as the CI workflow to catch issues before they are pushed to the repository.

### Checks Performed

1. **Black code formatting** - Ensures code follows consistent formatting style
2. **Ruff linting** - Checks for code quality and potential bugs
3. **Mypy type checking** - Verifies type annotations are correct
4. **Pytest with coverage** - Runs all tests and ensures 90% minimum coverage
5. **Package build** - Validates that the package can be built successfully

### Installation

To install the git hooks, run:

```bash
./hooks/install-hooks.sh
```

Or manually:

```bash
cp hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### Usage

Once installed, the pre-commit hook will automatically run every time you execute `git commit`. If any check fails, the commit will be aborted.

### Bypassing the Hook

If you need to bypass the hook for a specific commit (not recommended), use:

```bash
git commit --no-verify
```

### Requirements

Make sure you have all development dependencies installed:

```bash
pip install -r requirements-dev.txt
pip install -e .
```

Additional dependencies for type checking:

```bash
pip install mypy scipy-stubs
```

Build tools:

```bash
pip install build
```

### Troubleshooting

If the hook fails:

1. **Black formatting**: Run `black src/ tests/` to auto-format your code
2. **Ruff linting**: Run `ruff check --fix src/ tests/` to auto-fix some issues
3. **Mypy type checking**: Fix type errors based on mypy output
4. **Test failures**: Run `pytest tests/ -v` to see detailed test failures
5. **Coverage too low**: Add more tests to increase coverage
6. **Build failure**: Check the build output for errors

### Performance

The pre-commit hook runs comprehensive checks and may take 30-60 seconds to complete. This ensures that commits are high quality and reduces CI failures.
