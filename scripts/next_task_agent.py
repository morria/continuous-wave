#!/usr/bin/env python3
"""
Next Task Agent

This agent automatically selects and executes the next most important task
from the .claude/plans/INDEX.md file.

Usage:
    python scripts/next_task_agent.py [--dry-run] [--priority PRIORITY]

Options:
    --dry-run       Show what would be done without executing
    --priority      Only consider tasks at this priority level (1-4)
"""

import argparse
import re
import sys
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Optional


class Priority(IntEnum):
    """Task priority levels."""
    CRITICAL = 1
    HIGH = 2
    INFRASTRUCTURE = 3
    DOCUMENTATION = 4


@dataclass
class Task:
    """Represents a single task from the index."""
    section: str
    description: str
    status: str
    effort: str
    blocking: str
    checklist_items: list[str]
    key_files: list[str]
    success_criteria: list[str]
    priority: Priority
    plan_file: Optional[str] = None


@dataclass
class TaskSection:
    """Represents a section of related tasks."""
    title: str
    plan_file: Optional[str]
    status: str
    effort: str
    blocking: str
    priority: Priority
    checklist_items: list[str]
    key_files: list[str]
    success_criteria: list[str]


class IndexParser:
    """Parses the INDEX.md file to extract tasks."""

    def __init__(self, index_path: Path):
        self.index_path = index_path
        self.content = index_path.read_text()

    def parse(self) -> list[TaskSection]:
        """Parse the index file and return all task sections."""
        sections = []
        current_priority = None

        # Split by priority sections
        priority_pattern = r'## Priority \d+: (.+?)(?=## Priority \d+:|## Reference Documents|## Progress Tracking|$)'
        priority_sections = re.finditer(priority_pattern, self.content, re.DOTALL)

        for match in priority_sections:
            priority_name = match.group(1).strip()
            section_content = match.group(0)

            # Determine priority level
            if "CRITICAL" in priority_name:
                priority = Priority.CRITICAL
            elif "HIGH IMPACT" in priority_name:
                priority = Priority.HIGH
            elif "INFRASTRUCTURE" in priority_name:
                priority = Priority.INFRASTRUCTURE
            elif "DOCUMENTATION" in priority_name:
                priority = Priority.DOCUMENTATION
            else:
                continue

            # Parse subsections within this priority
            subsection_pattern = r'### (.+?)\n\n\*\*Status:\*\* (.+?)\n\*\*Estimated Effort:\*\* (.+?)(?:\n\*\*Blocking:\*\* (.+?))?\n'
            subsections = re.finditer(subsection_pattern, section_content, re.DOTALL)

            for subsection_match in subsections:
                title = subsection_match.group(1).strip()
                status = subsection_match.group(2).strip()
                effort = subsection_match.group(3).strip()
                blocking = subsection_match.group(4).strip() if subsection_match.group(4) else ""

                # Extract plan file if referenced
                plan_file_match = re.search(r'\(([A-Z_]+\.md)\)', title)
                plan_file = plan_file_match.group(1) if plan_file_match else None

                # Extract checklist items
                subsection_start = subsection_match.end()
                subsection_end = section_content.find('### ', subsection_start)
                if subsection_end == -1:
                    next_priority = section_content.find('## Priority', subsection_start)
                    subsection_end = next_priority if next_priority != -1 else len(section_content)

                subsection_text = section_content[subsection_start:subsection_end]

                checklist_items = re.findall(r'- \[ \] (.+)', subsection_text)

                # Extract key files
                key_files = []
                key_files_match = re.search(r'\*\*Key Files:\*\*(.+?)(?:\*\*|$)', subsection_text, re.DOTALL)
                if key_files_match:
                    key_files = re.findall(r'- `(.+?)`', key_files_match.group(1))

                # Extract success criteria
                success_criteria = []
                success_match = re.search(r'\*\*Success Criteria:\*\*(.+?)(?:\*\*|---|$)', subsection_text, re.DOTALL)
                if success_match:
                    success_criteria = re.findall(r'- (.+)', success_match.group(1))

                sections.append(TaskSection(
                    title=title,
                    plan_file=plan_file,
                    status=status,
                    effort=effort,
                    blocking=blocking,
                    priority=priority,
                    checklist_items=checklist_items,
                    key_files=key_files,
                    success_criteria=success_criteria
                ))

        return sections

    def find_next_task(self, priority_filter: Optional[int] = None) -> Optional[TaskSection]:
        """Find the next task to work on (highest priority, not started)."""
        sections = self.parse()

        # Filter by priority if specified
        if priority_filter is not None:
            sections = [s for s in sections if s.priority == priority_filter]

        # Filter to only "Not Started" tasks
        available_sections = [s for s in sections if s.status == "Not Started"]

        if not available_sections:
            return None

        # Sort by priority (lowest number = highest priority)
        available_sections.sort(key=lambda s: s.priority)

        return available_sections[0]


def format_task_summary(task: TaskSection) -> str:
    """Format a task summary for display."""
    lines = [
        "=" * 80,
        f"NEXT TASK: {task.title}",
        "=" * 80,
        "",
        f"Priority:     {task.priority.name}",
        f"Status:       {task.status}",
        f"Effort:       {task.effort}",
    ]

    if task.blocking:
        lines.append(f"Blocking:     {task.blocking}")

    if task.plan_file:
        lines.append(f"Plan File:    .claude/plans/{task.plan_file}")

    lines.extend([
        "",
        "CHECKLIST:",
    ])

    for item in task.checklist_items:
        lines.append(f"  - [ ] {item}")

    if task.key_files:
        lines.extend([
            "",
            "KEY FILES:",
        ])
        for file in task.key_files:
            lines.append(f"  - {file}")

    if task.success_criteria:
        lines.extend([
            "",
            "SUCCESS CRITERIA:",
        ])
        for criterion in task.success_criteria:
            lines.append(f"  - {criterion}")

    lines.append("")
    lines.append("=" * 80)

    return "\n".join(lines)


def generate_execution_plan(task: TaskSection, plans_dir: Path) -> str:
    """Generate a detailed execution plan for Claude Code."""
    plan_parts = [
        f"# Execution Plan: {task.title}",
        "",
        "## Objective",
        f"Complete the task: {task.title}",
        f"Estimated effort: {task.effort}",
        "",
        "## Context",
    ]

    if task.plan_file:
        plan_file_path = plans_dir / task.plan_file
        if plan_file_path.exists():
            plan_parts.append(f"Detailed plan available in: {task.plan_file}")
            plan_parts.append("")
            plan_parts.append("### Key Requirements from Plan File:")
            plan_parts.append("")
            # Read first part of the plan file for context
            content = plan_file_path.read_text()
            # Extract the first few sections
            lines = content.split('\n')[:50]  # First 50 lines for context
            plan_parts.extend(lines)

    plan_parts.extend([
        "",
        "## Tasks to Complete",
        "",
    ])

    for i, item in enumerate(task.checklist_items, 1):
        plan_parts.append(f"{i}. {item}")

    plan_parts.extend([
        "",
        "## Files to Modify",
        "",
    ])

    for file in task.key_files:
        plan_parts.append(f"- {file}")

    plan_parts.extend([
        "",
        "## Verification Steps",
        "",
        "After completing the implementation:",
        "1. Run the full test suite: `make test`",
        "2. Run type checking: `make type-check`",
        "3. Run linting: `make lint`",
        "4. Verify all pre-commit checks pass: `make pre-commit`",
        "",
        "## Success Criteria",
        "",
    ])

    for criterion in task.success_criteria:
        plan_parts.append(f"- {criterion}")

    plan_parts.extend([
        "",
        "## PR Creation",
        "",
        "Once all tests pass:",
        "1. Commit changes with a descriptive message",
        "2. Push to the feature branch",
        "3. Create a pull request with:",
        f"   - Title: {task.title}",
        "   - Body: Summary of changes, testing performed, and success criteria met",
        "",
    ])

    return "\n".join(plan_parts)


def main() -> int:
    """Main entry point for the next task agent."""
    parser = argparse.ArgumentParser(
        description="Next Task Agent - Automatically select and execute the next task"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing"
    )
    parser.add_argument(
        "--priority",
        type=int,
        choices=[1, 2, 3, 4],
        help="Only consider tasks at this priority level"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available tasks and exit"
    )

    args = parser.parse_args()

    # Find the repository root
    repo_root = Path(__file__).parent.parent
    index_path = repo_root / ".claude" / "plans" / "INDEX.md"
    plans_dir = repo_root / ".claude" / "plans"

    if not index_path.exists():
        print(f"Error: INDEX.md not found at {index_path}", file=sys.stderr)
        return 1

    # Parse the index
    index_parser = IndexParser(index_path)

    if args.list:
        # List all tasks
        sections = index_parser.parse()
        print("Available Tasks:")
        print("=" * 80)
        for section in sections:
            status_marker = "✓" if section.status == "Completed" else "○"
            print(f"{status_marker} [{section.priority.name}] {section.title}")
            print(f"   Status: {section.status}, Effort: {section.effort}")
            print()
        return 0

    # Find next task
    next_task = index_parser.find_next_task(args.priority)

    if not next_task:
        priority_msg = f" at priority {args.priority}" if args.priority else ""
        print(f"No tasks available{priority_msg}!")
        print("All tasks are either completed or in progress.")
        return 0

    # Display task summary
    print(format_task_summary(next_task))

    if args.dry_run:
        print("\n[DRY RUN] Would execute this task")
        print("\nExecution plan:")
        print(generate_execution_plan(next_task, plans_dir))
        return 0

    # Generate execution plan
    execution_plan = generate_execution_plan(next_task, plans_dir)

    # Save execution plan to a temporary file for Claude Code
    plan_output = repo_root / ".claude" / "current_task.md"
    plan_output.write_text(execution_plan)

    print(f"\nExecution plan saved to: {plan_output}")
    print("\nTo execute this task with Claude Code:")
    print("  1. Review the execution plan above")
    print("  2. Run: claude-code execute .claude/current_task.md")
    print("  OR")
    print("  3. Use the slash command: /next-task")

    return 0


if __name__ == "__main__":
    sys.exit(main())
