# Claude Code Configuration

This directory contains Claude Code configuration for the continuous-wave project, including hooks, agents, and commands that enhance the development workflow.

## Structure

```
.claude/
├── SessionStart          # Runs when starting a Claude Code session
├── agents/               # Custom subagents for specialized tasks
│   └── pr-review.md     # PR review agent for critical code analysis
├── commands/             # Slash commands for quick workflows
│   ├── pr-review.md     # Comprehensive PR review command
│   └── pre-pr.md        # Quick pre-PR checklist and workflow
└── plans/                # Documentation and planning documents
```

## Available Commands

### `/pr-review` - Comprehensive PR Review

Runs a thorough review of your changes before creating a pull request.

**Usage:**
```
/pr-review
```

**What it does:**
1. Shows summary of changed files and commits
2. Runs all quality checks (black, ruff, mypy, pytest, build)
3. Critically analyzes code for:
   - Pythonic patterns and idioms
   - Type safety and correctness
   - Architecture and design
   - File organization
   - Test coverage and quality
   - Contributor-friendliness
4. Provides prioritized action items for any issues found
5. Approves PR creation when all standards are met

**When to use:** After completing any task, before creating a PR

### `/pre-pr` - Quick Pre-PR Checklist

Streamlined workflow that runs quality checks and invokes the review agent.

**Usage:**
```
/pre-pr
```

**What it does:**
1. Runs all CI checks (formatting, linting, type checking, tests, build)
2. Helps fix any failures
3. Invokes the PR review agent for critical analysis
4. Guides you through addressing issues
5. Confirms readiness for PR creation

**When to use:** After completing your task, as part of your PR workflow

## Available Agents

### `pr-review` - PR Review Agent

A specialized subagent that performs critical code review with a focus on:

- **Code Quality**: Pythonic patterns, type hints, naming, structure
- **Architecture**: Separation of concerns, dependency injection, immutability
- **File Organization**: Correct locations, appropriate module structure
- **Test Quality**: Coverage, structure, edge cases, isolation
- **Contributor Experience**: Documentation, learning curve, consistency
- **Best Practices**: Security, performance, resource management

The agent enforces the project's high standards:
- 90% minimum test coverage
- Strict mypy type checking
- Black code formatting
- Ruff linting
- Successful package builds

**Invoked by:** `/pr-review` and `/pre-pr` commands

## Workflow

### Recommended Development Workflow

1. **Start a new task**
   - Claude Code automatically runs `.claude/SessionStart`
   - Verifies environment setup and dependencies
   - Shows git status and recent commits

2. **Complete your task**
   - Write code following project standards
   - Add comprehensive tests
   - Update documentation if needed

3. **Run pre-PR review** (IMPORTANT!)
   ```
   /pre-pr
   ```
   - This runs all CI checks locally
   - Catches issues before pushing to GitHub
   - Provides critical feedback on code quality

4. **Address any issues**
   - Fix blocking issues immediately
   - Consider important suggestions
   - Decide on nice-to-have improvements

5. **Create the PR**
   - Once review passes, create the pull request
   - PR will pass CI checks since they match local checks
   - Reviewers will see high-quality, well-tested code

### Why This Matters

Running `/pre-pr` or `/pr-review` before creating PRs:

- ✅ Ensures all CI checks pass (no failed builds)
- ✅ Catches code quality issues early
- ✅ Maintains high code standards across the project
- ✅ Makes code review faster and more focused
- ✅ Keeps the codebase maintainable and contributor-friendly
- ✅ Enforces Pythonic patterns and best practices

## SessionStart Hook

The `SessionStart` hook runs automatically when you start a Claude Code session. It:

1. Verifies Python 3.11+ is installed
2. Confirms git repository status
3. Installs dependencies if needed
4. Checks development tools (pytest, mypy, ruff)
5. Runs sanity checks (test discovery, type checking, linting)
6. Shows git status and recent commits
7. Displays available make commands

This ensures your development environment is always ready to work.

## Integration with CI

The PR review agent runs the **exact same checks** as GitHub Actions CI:

| Check | Local (pr-review) | CI (GitHub Actions) |
|-------|-------------------|---------------------|
| Black formatting | ✅ | ✅ |
| Ruff linting | ✅ | ✅ |
| MyPy type checking | ✅ | ✅ |
| Pytest + coverage | ✅ | ✅ |
| Package build | ✅ | ✅ |

This means:
- **No surprises**: If local checks pass, CI will pass
- **Fast feedback**: Catch issues in seconds, not minutes
- **Consistent standards**: Same checks everywhere

## Contributing

When contributing to this project:

1. **Always run `/pre-pr` before creating a PR** - This is non-negotiable for maintaining code quality
2. **Address all blocking issues** identified by the review agent
3. **Consider important suggestions** - They improve code quality
4. **Keep PRs focused** - One feature or fix per PR

The PR review agent is your ally in creating high-quality PRs that will be quickly approved and merged!

## Customization

### Adding New Commands

Create a new `.md` file in `.claude/commands/`:

```bash
echo "Your command prompt here" > .claude/commands/my-command.md
```

Add frontmatter for configuration:

```markdown
---
description: What this command does
allowed-tools: Read, Bash
---

Your command instructions here
```

### Adding New Agents

Create a new `.md` file in `.claude/agents/`:

```bash
touch .claude/agents/my-agent.md
```

Add frontmatter and instructions:

```markdown
---
name: my-agent
description: When to use this agent
model: sonnet
tools: Read, Grep, Bash
---

Agent instructions and behavior here
```

## Questions?

- See [CONTRIBUTING.md](../docs/CONTRIBUTING.md) for contribution guidelines
- See [DESIGN.md](../docs/DESIGN.md) for architecture documentation
- Open an issue if you have questions about the Claude Code setup

## Summary

The `.claude/` directory provides automated code review and quality checking that ensures all contributions maintain the project's high standards. Use `/pre-pr` before every PR to catch issues early and maintain code quality!
