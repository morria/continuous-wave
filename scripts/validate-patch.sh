#!/bin/bash
# Patch validation script that runs all CI checks locally
# Usage: ./scripts/validate-patch.sh [commit-range]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get commit range (default to comparing against main branch)
COMMIT_RANGE="${1:-main...HEAD}"
BASE_BRANCH="${2:-main}"

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}   Patch Validation - Pre-PR Checks${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Helper function to run a check with timing
run_check() {
    local name=$1
    local cmd=$2

    echo -e "${YELLOW}${name}${NC}"
    start=$(date +%s)

    # Create temp file for output
    local tmpfile=$(mktemp)

    if eval "$cmd" > "$tmpfile" 2>&1; then
        end=$(date +%s)
        duration=$((end - start))
        echo -e "${GREEN}✓ Passed${NC} ${BLUE}(${duration}s)${NC}\n"
        rm -f "$tmpfile"
        return 0
    else
        end=$(date +%s)
        duration=$((end - start))
        echo -e "${RED}✗ Failed${NC} ${BLUE}(${duration}s)${NC}"
        cat "$tmpfile"
        echo ""
        rm -f "$tmpfile"
        return 1
    fi
}

# Track results
FAILED_CHECKS=()
TOTAL_START=$(date +%s)

# Show patch information
echo -e "${BLUE}📊 Patch Information${NC}\n"
echo -e "Branch: ${GREEN}$(git rev-parse --abbrev-ref HEAD)${NC}"
echo -e "Comparing: ${CYAN}${COMMIT_RANGE}${NC}"
echo ""

# Show diff stats
if git rev-parse "${BASE_BRANCH}" >/dev/null 2>&1; then
    echo -e "${BLUE}📈 Changes Summary${NC}"
    git diff --stat "${BASE_BRANCH}...HEAD" | head -20
    echo ""
fi

# Check for merge conflicts
echo -e "${BLUE}🔍 Checking for merge conflicts...${NC}"
if git diff --check "${BASE_BRANCH}...HEAD" >/dev/null 2>&1; then
    echo -e "${GREEN}✓ No merge conflicts detected${NC}\n"
else
    echo -e "${RED}✗ Merge conflicts detected${NC}\n"
    FAILED_CHECKS+=("Merge conflicts")
fi

# Check commit message format
echo -e "${BLUE}📝 Validating commit messages...${NC}"
COMMIT_MSG_ISSUES=0
while IFS= read -r commit; do
    msg=$(git log -1 --format=%s "$commit")
    # Check if message is at least 10 characters and doesn't start with lowercase
    if [ ${#msg} -lt 10 ]; then
        echo -e "${YELLOW}⚠ Commit $commit has short message: $msg${NC}"
        COMMIT_MSG_ISSUES=$((COMMIT_MSG_ISSUES + 1))
    fi
done < <(git rev-list "${COMMIT_RANGE}")

if [ $COMMIT_MSG_ISSUES -eq 0 ]; then
    echo -e "${GREEN}✓ All commit messages look good${NC}\n"
else
    echo -e "${YELLOW}⚠ $COMMIT_MSG_ISSUES commit messages could be improved${NC}\n"
fi

# Run CI checks
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}   Running CI Pipeline Checks${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# 1. Format check
if ! run_check "[1/5] Black Format Check" "black --check src/ tests/"; then
    FAILED_CHECKS+=("Black formatting")
    echo -e "${YELLOW}💡 Fix with: make format${NC}\n"
fi

# 2. Lint check
if ! run_check "[2/5] Ruff Linting" "ruff check src/ tests/"; then
    FAILED_CHECKS+=("Ruff linting")
    echo -e "${YELLOW}💡 Fix with: make lint-fix${NC}\n"
fi

# 3. Type check
if ! run_check "[3/5] MyPy Type Check" "python -m mypy src/continuous_wave --strict"; then
    FAILED_CHECKS+=("Type checking")
fi

# 4. Tests
if ! run_check "[4/5] Pytest with Coverage" "python -m pytest tests/ -v --cov=continuous_wave --cov-report=term-missing --cov-fail-under=90"; then
    FAILED_CHECKS+=("Tests/Coverage")
fi

# 5. Build
if ! run_check "[5/5] Package Build" "python -m build >/dev/null 2>&1"; then
    FAILED_CHECKS+=("Package build")
fi

# Clean up build artifacts
rm -rf build/ dist/ *.egg-info

# Calculate total time
TOTAL_END=$(date +%s)
TOTAL_DURATION=$((TOTAL_END - TOTAL_START))

# Summary
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}   Validation Summary${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

if [ ${#FAILED_CHECKS[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC} ${BLUE}(Total: ${TOTAL_DURATION}s)${NC}"
    echo -e "${GREEN}✓ Your patch is ready for PR!${NC}\n"

    # Estimate CI time
    echo -e "${BLUE}ℹ Estimated GitHub Actions CI time: ~$((TOTAL_DURATION + 30))s${NC}"
    echo -e "${BLUE}  (includes setup overhead)${NC}\n"

    exit 0
else
    echo -e "${RED}✗ ${#FAILED_CHECKS[@]} check(s) failed:${NC}"
    for check in "${FAILED_CHECKS[@]}"; do
        echo -e "${RED}  • $check${NC}"
    done
    echo ""
    echo -e "${YELLOW}💡 Fix these issues before creating a PR${NC}"
    echo -e "${YELLOW}   Your PR will fail CI with these issues${NC}\n"
    exit 1
fi
