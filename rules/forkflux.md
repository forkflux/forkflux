# ForkFlux Coordination Rules

You are connected to the ForkFlux Coordination Bus via MCP.

### WHEN TO USE FORKFLUX (Triggers)
Do NOT invoke ForkFlux tools during your normal local coding iterations or intermediate debugging. You operate locally until the job is fully ready for the next stage.

Initiate a ForkFlux Handoff ONLY when:
1. **Explicit Command:** The user explicitly types something like "Hand off to QA", "Create a ForkFlux job", or "Send this to the next agent".
2. **Task Completion:** When you believe you have fully completed the requested feature/fix, generate your final summary and ALWAYS ask the user: *"I have finished the local changes. Should I package this context and hand it off via ForkFlux to another role (e.g., QA, Reviewer)?"* Do not create the job until the user says yes.

---

**When acting as a SOURCE AGENT (Handing off work):**
1. First, call the `forkflux_list_roles` tool to find the correct `target_role_key` for the next agent (e.g., QA, Backend, Frontend).
2. Gather all necessary context, relevant code snippets, file paths, and logs required for the next agent to succeed. Do not just link files; pack the actual required context.
3. Call the `forkflux_create_job` tool. You MUST place the gathered information into the `context_payload` and define strict acceptance criteria in the `constraints` field.

**When acting as a TARGET AGENT (Receiving work):**
1. Call the `forkflux_list_jobs` tool to check for available 'published' jobs assigned to your role.
2. Call `forkflux_claim_job` using the job ID.
   - **CRITICAL:** This tool automatically locks the job, changes its status to 'in_progress', and returns the FULL task card (including `context_payload`, `artifacts`, and `constraints`). You do NOT need to request job details separately.
3. Carefully read the full context returned by the claim tool and IMMEDIATELY begin executing the required work locally.
4. Upon completion or failure, call `forkflux_change_job_status` to update the task lifecycle to either 'completed' or 'failed'.
   - **CRITICAL:** If the task fails, or if you lack the necessary context from the Source Agent to even begin, you MUST transition the status to 'failed' and provide a detailed `failure_reason` (e.g., actual tracebacks, compilation errors, or explicitly state what context is missing).
