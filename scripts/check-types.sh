#!/bin/bash
# Granular type checking script with multiple strictness levels
# Usage: ./scripts/check-types.sh [strict|normal|lenient]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default to normal mode
MODE=${1:-normal}

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   Type Checking Mode: ${MODE}${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

case ${MODE} in
  strict)
    echo -e "${YELLOW}Running STRICT type checking (zero tolerance)${NC}"
    echo -e "${YELLOW}All type errors will cause failure${NC}\n"

    if python -m mypy src/ tests/ --strict --no-error-summary 2>&1; then
      echo -e "\n${GREEN}✓ Strict type checking passed!${NC}"
      echo -e "${GREEN}No type errors found in codebase.${NC}"
      exit 0
    else
      echo -e "\n${RED}✗ Strict type checking failed${NC}"
      echo -e "${RED}Fix all type errors to pass strict mode${NC}"
      exit 1
    fi
    ;;

  normal)
    echo -e "${BLUE}Running NORMAL type checking (current configuration)${NC}"
    echo -e "${BLUE}Checks with existing overrides and configurations${NC}\n"

    if python -m mypy src/continuous_wave --strict 2>&1; then
      echo -e "\n${GREEN}✓ Normal type checking passed!${NC}"
      exit 0
    else
      echo -e "\n${RED}✗ Normal type checking failed${NC}"
      echo -e "${YELLOW}💡 Tip: Run './scripts/check-types.sh lenient' to focus on new code${NC}"
      exit 1
    fi
    ;;

  lenient)
    echo -e "${GREEN}Running LENIENT type checking (focused on critical modules)${NC}"
    echo -e "${GREEN}Only checks core modules without known type issues${NC}\n"

    # List of modules to check (exclude problematic ones)
    MODULES_TO_CHECK=(
      "src/continuous_wave/models.py"
      "src/continuous_wave/protocols.py"
      "src/continuous_wave/config.py"
      "src/continuous_wave/logging.py"
    )

    # Find all Python files in signal/, detection/, timing/ (if they exist)
    if [ -d "src/continuous_wave/signal" ]; then
      MODULES_TO_CHECK+=("src/continuous_wave/signal/")
    fi
    if [ -d "src/continuous_wave/detection" ]; then
      MODULES_TO_CHECK+=("src/continuous_wave/detection/")
    fi
    if [ -d "src/continuous_wave/timing" ]; then
      MODULES_TO_CHECK+=("src/continuous_wave/timing/")
    fi

    # Check if any modules exist
    if [ ${#MODULES_TO_CHECK[@]} -eq 0 ]; then
      echo -e "${YELLOW}⚠ No modules found to check in lenient mode${NC}"
      echo -e "${YELLOW}  This might be a new project setup${NC}"
      exit 0
    fi

    # Filter to only existing files/directories
    EXISTING_MODULES=()
    for module in "${MODULES_TO_CHECK[@]}"; do
      if [ -e "$module" ]; then
        EXISTING_MODULES+=("$module")
      fi
    done

    if [ ${#EXISTING_MODULES[@]} -eq 0 ]; then
      echo -e "${YELLOW}⚠ No existing modules found to check${NC}"
      exit 0
    fi

    echo -e "${BLUE}Checking ${#EXISTING_MODULES[@]} module(s):${NC}"
    for module in "${EXISTING_MODULES[@]}"; do
      echo -e "  - ${module}"
    done
    echo ""

    if python -m mypy "${EXISTING_MODULES[@]}" --strict --no-error-summary 2>&1; then
      echo -e "\n${GREEN}✓ Lenient type checking passed!${NC}"
      echo -e "${GREEN}Core modules are type-safe${NC}"
      exit 0
    else
      echo -e "\n${RED}✗ Lenient type checking failed${NC}"
      echo -e "${YELLOW}💡 Focus on fixing type errors in core modules first${NC}"
      exit 1
    fi
    ;;

  incremental)
    echo -e "${BLUE}Running INCREMENTAL type checking (only changed files)${NC}"
    echo -e "${BLUE}Checks only files modified in git working tree${NC}\n"

    # Get list of modified Python files
    CHANGED_FILES=$(git diff --name-only --cached --diff-filter=ACM | grep '\.py$' || true)

    if [ -z "$CHANGED_FILES" ]; then
      echo -e "${YELLOW}⚠ No Python files changed${NC}"
      echo -e "${GREEN}✓ Nothing to type check${NC}"
      exit 0
    fi

    echo -e "${BLUE}Checking modified files:${NC}"
    echo "$CHANGED_FILES" | while read -r file; do
      echo -e "  - ${file}"
    done
    echo ""

    if echo "$CHANGED_FILES" | xargs python -m mypy --strict --no-error-summary 2>&1; then
      echo -e "\n${GREEN}✓ Incremental type checking passed!${NC}"
      exit 0
    else
      echo -e "\n${RED}✗ Incremental type checking failed${NC}"
      exit 1
    fi
    ;;

  *)
    echo -e "${RED}✗ Invalid mode: ${MODE}${NC}"
    echo -e "${YELLOW}Usage: $0 [strict|normal|lenient|incremental]${NC}"
    echo ""
    echo -e "${BLUE}Modes:${NC}"
    echo -e "  ${GREEN}strict${NC}      - Zero tolerance, checks all files with strict mode"
    echo -e "  ${GREEN}normal${NC}      - Current configuration (default)"
    echo -e "  ${GREEN}lenient${NC}     - Only checks core modules without known issues"
    echo -e "  ${GREEN}incremental${NC} - Only checks files changed in git working tree"
    echo ""
    exit 1
    ;;
esac
