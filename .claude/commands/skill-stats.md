# Skill Stats — Usage Measurement

Read and report on skill/tool usage from the log file written by the PreToolUse hook.

## Arguments
$ARGUMENTS

Arguments: empty (summary), `all` (full log), `today`, `week`

## Steps

1. **Check for the log file** at `~/.claude/skill-usage.log`. If it doesn't exist, report:
   ```
   No usage data found yet. The PreToolUse hook logs tool invocations to ~/.claude/skill-usage.log.
   Usage data will appear after tools are invoked in sessions with the hook active.
   ```

2. **Parse the log file.** Each line is tab-separated: `{timestamp}\t{session_id}\t{tool_name}`

3. **Filter by time range:**
   - Empty / `summary` → last 7 days
   - `today` → today only
   - `week` → last 7 days
   - `all` → no filter

4. **Generate report:**

   ```
   SKILL USAGE REPORT
   Period: {time range}
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   Tool Invocations:
     Edit          ████████████████  142
     Read          ███████████████   128
     Bash          ██████████        87
     Grep          ████████          65
     Write         ██████            48
     Glob          █████             42
     Skill         ███               24
     Agent         ██                15

   Skills (via Skill tool):
     /commit       ████████          8
     /review       ██████            6
     /deploy       ████              4
     /careful      ███               3
     /aios-patterns ██               2
     /freeze       █                 1

   Sessions: {unique session count}
   Total invocations: {total count}

   Trend (last 7 days):
     Mon: ██████  52
     Tue: ████████  68
     ...

   Most used: {tool_name} ({count})
   Least used: {tool_name} ({count})
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

5. **If `all` is specified**, also show the raw log entries (last 100 lines max).

## Notes
- The log is written by `.claude/hooks/log-tool-usage.sh` — a PreToolUse hook
- If the hook isn't active, no data will be collected
- The log file grows unbounded — suggest periodic cleanup if it exceeds 10MB
