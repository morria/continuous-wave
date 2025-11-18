#!/bin/bash
# Script to install git hooks

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GIT_HOOKS_DIR="$(git rev-parse --git-dir)/hooks"

echo "Installing git hooks..."

# Install pre-commit hook
if [ -f "$HOOKS_DIR/pre-commit" ]; then
    cp "$HOOKS_DIR/pre-commit" "$GIT_HOOKS_DIR/pre-commit"
    chmod +x "$GIT_HOOKS_DIR/pre-commit"
    echo "✓ Installed pre-commit hook"
else
    echo "✗ Error: pre-commit hook not found in $HOOKS_DIR"
    exit 1
fi

echo ""
echo "Git hooks installed successfully!"
echo ""
echo "The pre-commit hook will now run the following checks before each commit:"
echo "  1. Black code formatting"
echo "  2. Ruff linting"
echo "  3. Mypy type checking"
echo "  4. Pytest with coverage (90% minimum)"
echo "  5. Package build"
echo ""
echo "To bypass the hook for a specific commit, use: git commit --no-verify"
