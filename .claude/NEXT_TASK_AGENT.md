# Next Task Agent

The Next Task Agent is an automated system that helps manage and execute tasks from the project's work plan. It intelligently selects the next most important task, creates an execution plan, and guides the implementation through to completion.

## Overview

The agent consists of two main components:

1. **Task Parser** (`scripts/next_task_agent.py`) - Python script that analyzes the `.claude/plans/INDEX.md` file to identify available tasks
2. **Execution Agent** (`.claude/commands/next-task.md`) - Claude Code slash command that executes the selected task

## How It Works

### Task Selection Process

The agent uses the following criteria to select the next task:

1. **Priority Level**: Tasks are organized into 4 priority levels
   - Priority 1: CRITICAL BLOCKERS (must complete first)
   - Priority 2: HIGH IMPACT IMPROVEMENTS
   - Priority 3: INFRASTRUCTURE & QUALITY
   - Priority 4: DOCUMENTATION & POLISH

2. **Status**: Only selects tasks marked as "Not Started"
   - Skips tasks marked as "In Progress" or "Completed"

3. **Selection**: Chooses the highest priority available task

### Execution Workflow

Once a task is selected, the agent follows this workflow:

```
1. Identify Task
   ↓
2. Read Detailed Plan
   ↓
3. Create Execution Plan
   ↓
4. Investigate Code
   ↓
5. Implement Changes
   ↓
6. Run Tests
   ↓
7. Update Documentation
   ↓
8. Create Pull Request
```

## Usage

### Command Line Interface

The `next_task_agent.py` script provides several commands:

#### List All Tasks

See all available tasks with their priorities and status:

```bash
python scripts/next_task_agent.py --list
```

Output example:
```
Available Tasks:
================================================================================
○ [CRITICAL] Decoder Fixes (DECODER_FIXES_NEEDED.md)
   Status: Not Started, Effort: 1-2 days

○ [HIGH] Type Safety (TYPING_ISSUES.md)
   Status: Not Started, Effort: 2-3 weeks
...
```

#### Preview Next Task

See what task would be selected without executing it:

```bash
python scripts/next_task_agent.py --dry-run
```

This displays:
- Task title and priority
- Estimated effort
- What the task is blocking
- Checklist of items to complete
- Key files to modify
- Success criteria
- Detailed execution plan

#### Filter by Priority

Only consider tasks at a specific priority level:

```bash
python scripts/next_task_agent.py --dry-run --priority 1  # Only critical tasks
python scripts/next_task_agent.py --dry-run --priority 2  # Only high priority tasks
```

### Claude Code Integration

#### Using the Slash Command

The easiest way to execute the next task is using the Claude Code slash command:

```
/next-task
```

This will:
1. Identify the next task automatically
2. Create a comprehensive execution plan
3. Execute the plan step-by-step
4. Run all tests and validation
5. Update the INDEX.md file
6. Create a pull request

#### Manual Execution

If you prefer more control, you can manually execute the steps:

1. **Identify the task**:
   ```bash
   python scripts/next_task_agent.py --dry-run
   ```

2. **Read the detailed plan** (if referenced):
   ```bash
   cat .claude/plans/DECODER_FIXES_NEEDED.md
   ```

3. **Execute the work** following the plan

4. **Run tests**:
   ```bash
   make pre-commit  # Runs all checks
   ```

5. **Create PR**:
   ```bash
   git add .
   git commit -m "Fix: Description of changes"
   git push -u origin <branch-name>
   gh pr create --title "..." --body "..."
   ```

## Task Structure

Each task in the INDEX.md follows this structure:

```markdown
### Task Title (PLAN_FILE.md)

**Status:** Not Started | In Progress | Completed
**Estimated Effort:** Time estimate
**Blocking:** What this task is blocking

**Phase/Checklist:**
- [ ] Checklist item 1
- [ ] Checklist item 2
- [ ] Checklist item 3

**Key Files:**
- `path/to/file1.py` - Description
- `path/to/file2.py` - Description

**Success Criteria:**
- Criterion 1
- Criterion 2
- Criterion 3
```

## Agent Capabilities

### What the Agent Can Do

✅ **Parse and understand** the task index structure
✅ **Prioritize tasks** based on importance and dependencies
✅ **Read detailed plans** to understand context and requirements
✅ **Create execution plans** breaking down complex tasks
✅ **Implement changes** across multiple files
✅ **Run tests** and verify functionality
✅ **Fix issues** that arise during implementation
✅ **Update documentation** including the INDEX.md
✅ **Create pull requests** with comprehensive descriptions

### What the Agent Cannot Do

❌ **Make architectural decisions** without guidance
❌ **Skip tests** - all tests must pass before completion
❌ **Ignore type errors** - strict type checking must pass
❌ **Work on multiple tasks** simultaneously
❌ **Create tasks** - only executes existing tasks from INDEX.md

## Quality Standards

The agent enforces these quality standards:

1. **Test Coverage**: Minimum 90% code coverage
2. **Type Safety**: All mypy strict checks must pass
3. **Code Style**: Black formatting and Ruff linting
4. **Tests**: All unit and integration tests must pass
5. **Pre-commit**: All pre-commit hooks must succeed

Before creating a PR, the agent verifies:

```bash
make pre-commit
```

This runs:
- Black code formatting check
- Ruff linting
- MyPy type checking (strict mode)
- Pytest with coverage (90% minimum)
- Package build validation

## Handling Blockers

If the agent encounters blockers during execution:

1. **Test Failures**:
   - Investigates root cause
   - Fixes the issue
   - Re-runs tests
   - Does NOT mark task complete until all tests pass

2. **Type Errors**:
   - Reviews mypy output
   - Fixes type annotations
   - Verifies with `make type-check`

3. **Unexpected Issues**:
   - Documents the blocker
   - Tries alternative approaches
   - Updates task status if truly blocked
   - Moves to next available task if needed

## Progress Tracking

The agent updates the INDEX.md file as work progresses:

- Changes `- [ ]` to `- [x]` for completed checklist items
- Updates section status when all items complete
- Updates the "Last Updated" timestamp
- Maintains the "Overall Status" progress counters

## Example Workflow

Here's a complete example of using the agent:

### 1. Check what tasks are available

```bash
$ python scripts/next_task_agent.py --list
Available Tasks:
================================================================================
○ [CRITICAL] Decoder Fixes (DECODER_FIXES_NEEDED.md)
   Status: Not Started, Effort: 1-2 days
...
```

### 2. Preview the next task

```bash
$ python scripts/next_task_agent.py --dry-run
================================================================================
NEXT TASK: Decoder Fixes (DECODER_FIXES_NEEDED.md)
================================================================================

Priority:     CRITICAL
Status:       Not Started
Effort:       1-2 days
...
```

### 3. Execute the task using Claude Code

In Claude Code:
```
/next-task
```

The agent will:
- Read the task and plan file
- Create an execution plan
- Implement the fixes
- Run all tests
- Update INDEX.md
- Create a PR

### 4. Review the PR

The agent creates a PR with:
- Descriptive title
- Summary of changes
- Testing performed
- Success criteria met

## Configuration

The agent uses these file locations:

- **Task Index**: `.claude/plans/INDEX.md`
- **Plan Files**: `.claude/plans/*.md`
- **Current Task**: `.claude/current_task.md` (temporary)
- **Slash Command**: `.claude/commands/next-task.md`

## Integration with Development Workflow

The agent integrates with the existing development workflow:

```
SessionStart Hook
    ↓
Developer opens Claude Code
    ↓
Run: /next-task
    ↓
Agent selects task
    ↓
Agent implements & tests
    ↓
Agent creates PR
    ↓
Developer reviews PR
    ↓
Merge to main
    ↓
Repeat
```

## Benefits

Using the Next Task Agent provides:

1. **Automatic Prioritization**: Always work on the most important task
2. **Structured Execution**: Follow a proven workflow for each task
3. **Quality Assurance**: All tests and checks run automatically
4. **Documentation**: INDEX.md stays up-to-date automatically
5. **Consistency**: Same high-quality approach for every task
6. **Efficiency**: Reduce context switching and decision fatigue

## Advanced Usage

### Working on Lower Priority Tasks

If you want to work on a specific priority level:

```bash
python scripts/next_task_agent.py --priority 3  # Infrastructure tasks
```

### Custom Execution

For manual control over execution:

1. Generate the execution plan:
   ```bash
   python scripts/next_task_agent.py --dry-run > my_plan.md
   ```

2. Edit the plan as needed

3. Execute manually using Claude Code:
   ```
   Follow the plan in my_plan.md
   ```

## Troubleshooting

### "No tasks available"

All tasks are either completed or in progress. Check:

```bash
python scripts/next_task_agent.py --list
```

### "Error: INDEX.md not found"

Ensure you're running from the repository root or the script can find `.claude/plans/INDEX.md`.

### Slash command not working

Ensure the command file exists:
```bash
ls -la .claude/commands/next-task.md
```

## Future Enhancements

Potential future improvements:

- GitHub integration to automatically create issues
- Metrics tracking (time per task, velocity, etc.)
- Task dependency management
- Automatic task breakdown for large tasks
- Integration with project management tools
- Task estimation accuracy tracking

## Contributing

To improve the Next Task Agent:

1. Update `scripts/next_task_agent.py` for parsing logic
2. Update `.claude/commands/next-task.md` for execution workflow
3. Update this documentation
4. Test with various task types
5. Submit PR with improvements

## Support

For issues or questions:

1. Check this documentation
2. Review `.claude/plans/INDEX.md` for task structure
3. Check example tasks in `.claude/plans/`
4. Open an issue on GitHub

---

**Created**: 2025-11-19
**Version**: 1.0.0
**Maintained by**: Claude Code Automation
