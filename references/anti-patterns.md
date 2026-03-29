# Anti-Patterns | Anti-Patterns List

> When executing Agent framework tasks, the following anti-patterns must be avoided.

## 1. Ignoring heartbeat, starting from scratch

**Wrong**: Each time execution starts from Step 1 without reading heartbeat.md.  
**Right**: First read heartbeat.md and continue from the recorded breakpoint.

## 2. Self-declaring completion

**Wrong**: Declaring "completed" after task execution without running external validation.  
**Right**: Must run harness_eval.py or verify each item according to eval_criteria.md.

## 3. Swallowing exceptions

**Wrong**: Silently skipping errors without recording them in heartbeat.md.  
**Right**: Use harness_heartbeat.py fail to record exceptions, so the next execution knows what happened.

## 4. Infinite retries

**Wrong**: Repeatedly retrying the same step on failure without escalating to humans.  
**Right**: Mark as blocked after 3 consecutive failures and wait for manual intervention.

## 5. Modifying mission.md

**Wrong**: Agent modifies the completion contract in mission.md during execution.  
**Right**: mission.md is the user-defined "constitution"; Agent only reads it and does not write.

## 6. progress.md infinite expansion

**Wrong**: Never cleaning progress.md, letting it grow indefinitely and crowd out context.  
**Right**: Regularly run harness_cleanup.py to compress old records.

## 7. Treating playbook as a one-time prompt

**Wrong**: Reading playbook.md only on the first execution and relying on "memory" afterwards.  
**Right**: Read playbook.md anew each time to ensure the latest version is used.

## 8. Skipping boundary checks

**Wrong**: Not reading the "Boundaries and Constraints" in mission.md and performing prohibited operations.  
**Right**: Check boundary constraints before each execution to ensure no overreach.
