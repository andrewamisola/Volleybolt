# Handoff Command

This command should be run before ending a session or when context is getting full. It ensures all project documentation is updated for the next session.

## Instructions

When this command is invoked, perform the following steps:

### 1. Update DevLog.md
- Add a new entry for the current session if not already present
- Mark any completed items with [x]
- Add any new items that were worked on
- Include timestamp and session summary

### 2. Update Tasks.md
- Update status of any tasks worked on ([ ] -> [x] for completed, [~] for in progress)
- Add any new bugs discovered
- Add any new feature ideas mentioned
- Move completed tasks to the "Completed Tasks" section with today's date

### 3. Update Architecture.md (if needed)
- Document any new systems or mechanics added
- Update constants table if values changed
- Add implementation notes for complex features

### 4. Update Debug.md (if needed)
- Add any new test scenarios discovered
- Document any debugging techniques used

### 5. Update ai.context.md
- Update "Last Updated" date
- Update "Current State" section with game status
- Note any critical information for next session

### 6. Final Summary
After updating documentation, provide a brief summary:
- What was accomplished this session
- What's pending or blocked
- Any important notes for next session

## Output
After completing the handoff, confirm all files were updated and provide the summary.
