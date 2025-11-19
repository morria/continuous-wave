---
description: Quick pre-PR checklist - runs before creating a pull request to ensure quality standards
allowed-tools: Bash, Task
---

# Pre-PR Workflow

Run this command after completing your task and before creating a PR. This ensures all quality checks pass and the code meets project standards.

**Quick Pre-PR Checklist:**

1. **Run all quality checks** (same as CI):
   ```bash
   black --check src/ tests/ && \
   ruff check src/ tests/ && \
   python -m mypy src/continuous_wave --strict && \
   pytest tests/ -v --cov=continuous_wave --cov-fail-under=90 && \
   python -m build
   ```

2. **If any checks fail**, fix them immediately:
   - Black formatting: `black src/ tests/`
   - Ruff issues: `ruff check --fix src/ tests/`
   - MyPy errors: Fix type hints
   - Test failures: Fix the failing tests
   - Coverage below 90%: Add more tests

3. **If all checks pass**, invoke the PR review agent for critical analysis:
   - Use the Task tool with subagent_type="pr-review"
   - The agent will review code quality, architecture, and maintainability

4. **Address any issues** identified by the review agent

5. **Create the PR** once everything is approved

---

**For you (Claude)**: Execute steps 1-5 above. Be thorough and don't skip steps. If checks fail, help the user fix them before proceeding to the review agent.
