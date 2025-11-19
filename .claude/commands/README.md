# Claude Code Commands

This directory contains slash commands for Claude Code to perform specialized tasks in the continuous-wave repository.

## Available Commands

### `/cleanup` - Repository Cleanup Agent

A comprehensive cleanup agent that maintains repository organization, updates plans, and ensures documentation accuracy.

**When to use:**
- After completing major features or fixing bugs
- To update plans and mark completed work
- To ensure documentation is accurate and complete
- To identify new work items (skipped tests, bugs, etc.)
- Before creating releases or major pull requests

**What it does:**
1. **Document Organization**: Checks markdown formatting, heading hierarchy, and link validity
2. **Plan Management**: Marks completed items, updates status, validates file references
3. **Documentation Accuracy**: Verifies code examples, API references, and completeness
4. **Work Identification**: Finds skipped tests, TODO comments, and other work items

**Usage:**
```bash
/cleanup
```

The cleanup agent will:
- Review all plans in `.claude/plans/` and `docs/plans/`
- Update completion status based on git history and codebase state
- Fix documentation formatting issues
- Identify new work items and add them to plans
- Generate a detailed cleanup report

**Example cleanup tasks:**
- Marking decoder fixes as complete when tests pass
- Updating file references when code is refactored
- Finding and documenting skipped tests
- Ensuring plan priorities match current project state
- Fixing typos and formatting in documentation

## Adding New Commands

To add a new slash command:

1. Create a markdown file in this directory: `.claude/commands/your-command.md`
2. Write clear instructions for Claude Code to follow
3. Document the command in this README
4. The command will be available as `/your-command` in Claude Code sessions

## Command Development Guidelines

**Good command practices:**
- Be specific about what the command should do
- Include clear success criteria
- Provide examples and context
- List files and areas to check
- Specify output format
- Include safety guidelines (what NOT to do)

**Structure:**
```markdown
# Command Name

Brief description of the command's purpose.

## Responsibilities
- Specific task 1
- Specific task 2
...

## Workflow
1. Step 1
2. Step 2
...

## Output Format
Describe expected output

## Guidelines
- Important rules
- Safety considerations
```

## See Also

- `.claude/SessionStart` - Session initialization hook
- `.claude/plans/` - Internal development plans
- `docs/plans/` - Public improvement plans
