# Learnings Log

## 2026-03-22

### [workflow] Cron Job Reporting Creates Conversation Noise
**Status**: `recurrence`
**Category**: `workflow_issue`

**Problem**: 
Automated cron job reports (every 10 minutes) create conversation noise when the workflow is running correctly without issues. Each successful run triggers a system message requiring acknowledgment.

**Impact**:
- Clutters conversation with repetitive "NO_REPLY" messages
- Reduces signal-to-noise ratio for important notifications  
- Makes it harder to spot actual issues

**Better Approach**:
Only notify when there are actual issues or blockers, not on every successful run.

```yaml
condition: only_notify_on_issues
rules:
  - Skip notification when all tasks complete and no blockers
  - Only notify when: blockers detected, tests fail, code changes needed
  - Or reduce notification frequency to hourly/daily summaries
  - Or add a "quiet mode" flag to suppress routine success messages
```

**Suggested Fix**:
Update cron job to check for actual work needed before notifying:
```python
# Only report if there are actual tasks or blockers
if has_pending_tasks() or has_blockers():
    notify_user()
else:
    log_silently()  # Just log, don't notify
```

**Priority**: P2 (nice to have)

---

## 2026-03-21

### [bug-fix] Website JS Version Not Synced
**Status**: `resolved`
**Category**: `deployment`

**Problem**: 
Fixed TypeScript code (Grade5Generator.ts) but forgot to sync the JavaScript version (js/questionGenerator.js) that the website actually uses.

**Impact**:
- Users still experienced the bug on the live website
- Fix appeared not to work despite code changes

**Solution**:
- Checked both TypeScript (src/) and JavaScript (js/) versions
- Fixed both files with identical logic
- Added to iteration checklist: "verify both src/ and js/ for website projects"

**Simplified & Hardened Pattern**:
```markdown
## Web Project Deployment Checklist

When fixing bugs in web projects:
- [ ] Check BOTH TypeScript/Vue source AND compiled/bundled output
- [ ] Verify the version users actually see (GitHub Pages, CDN, etc.)
- [ ] Test on actual deployed URL, not just local
- [ ] Check for separate build process that might need manual trigger
```

---

### [bug-fix] Grade6 Variable Undefined Error
**Status**: `resolved`
**Category**: `coding`

**Problem**: 
`generateGrade6()` function declared `let a, b, answer, question, type, tags;` but used `c` and `d` without declaring them, causing "c is not defined" error.

**Root Cause**: 
- Variable declaration incomplete
- No linting/static analysis catching undeclared variables

**Solution**:
```javascript
// Before
let a, b, answer, question, type, tags;

// After  
let a, b, c, d, answer, question, type, tags;
```

**Learning**: 
Always declare ALL variables at function start, even if used conditionally. Consider using linters (ESLint) to catch this automatically.

**Simplified & Hardened Pattern**:
```javascript
// Pattern: Declare all potentially used variables upfront
function generateX() {
    let a, b, c, d, result;  // All possible variables
    
    if (condition) {
        c = computeC();  // Safe to use now
    }
}
```

---

### [tooling] Iteration Script Only Generates Docs
**Status**: `recurrence`
**Category**: `automation`

**Problem**: 
The iteration script (`iterate.py`) generates documentation but doesn't actually modify code or write tests. It only updates STATUS.md and CHANGELOG.md.

**Impact**:
- Sprint 2 tasks remain pending indefinitely
- No actual progress on new features
- Automation is partial - docs update but no code changes

**Better Approach**:
The script should distinguish between "documentation iterations" and "development iterations":
1. Check for pending code tasks in TASK_BACKLOG.md
2. If found AND capable of auto-execution, actually modify the code
3. For complex tasks, spawn a sub-agent or create a ticket
4. Report "no actual work needed" instead of creating noise

**Priority**: P1 (important for real progress)
