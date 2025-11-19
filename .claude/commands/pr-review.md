---
description: Run comprehensive PR review before creating a pull request - checks all quality standards, code patterns, file organization, and contributor-friendliness
allowed-tools: Task, Bash, Read
---

# PR Review Command

Invoke the PR review agent to perform a comprehensive review of all changes in the current branch before creating a pull request.

**Instructions for you (Claude):**

1. First, show the user a summary of what will be reviewed by running these commands in parallel:
   - `git status` to see what files have changed
   - `git diff --stat main...HEAD` to see the scope of changes
   - `git log --oneline main..HEAD` to see the commits

2. Then, use the Task tool to invoke the `pr-review` subagent:
   ```
   Task tool with subagent_type="pr-review"
   ```

3. The pr-review agent will:
   - Run all quality checks (black, ruff, mypy, pytest, build)
   - Critically analyze code changes for Pythonic patterns
   - Verify file organization and architecture
   - Check test coverage and quality
   - Assess contributor-friendliness
   - Provide a prioritized list of issues to fix

4. After the review is complete:
   - If there are **blocking issues**, work with the user to fix them before creating the PR
   - If there are only **suggestions**, ask the user if they want to address them now or create the PR
   - If everything passes, congratulate the user and proceed to PR creation if they want

5. When all issues are resolved, ask the user: "All checks passed! Would you like me to create the pull request now?"

**Note**: This review enforces the same standards as CI, so passing this review means your PR will pass CI checks.
