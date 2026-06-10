---
description: Retrieve the full handoff context, acceptance criteria, and artifacts for a specific job using the forkflux_job_details MCP tool.
---

# ff-job-details

## Description

Fetches the detailed card for a specific ForkFlux job. This tool unpacks the complete execution context left by the Source Agent so the Target Agent can understand exactly what needs to be done before or after claiming the job.

## Required MCP tool

`forkflux_job_details`

## Agent instructions

1. Before calling the tool, verify that the user has provided a valid `job_id`. If the `job_id` is missing, stop and ask the user to provide it (or suggest running `/ff-list-jobs` first).
2. Call the `forkflux_job_details` tool using the provided `job_id`.
3. If the tool call fails (e.g., Job Not Found or Network Error), output the exact error message and stop. Do not hallucinate job details.
4. **Context Ingestion:** Once you receive the response, you MUST silently absorb the `context_payload` into your working memory. This payload contains the crucial architectural context, previous steps, and implicit knowledge from the prior agent.
5. **User Presentation:** Do NOT dump the raw JSON `context_payload` into the chat. Instead, process the data and present a human-readable executive summary to the user.
6. Conclude your response by asking if the user would like you to claim this job to begin execution.

## Output

Generate a clean, structured Markdown summary containing:

* 📄 **Job ID & Status**: The current state of the job.
* 🎯 **Acceptance Criteria**: A clear list of the `constraints` that must be met to complete the work.
* 🧠 **Context Summary**: A 2-3 sentence human-readable interpretation of the core details found inside the `context_payload`.
* 📎 **Artifacts**: A bulleted list of attached files or logs (if any).

**Strict Rule:** Keep the output concise and readable. The heavy lifting of the `context_payload` is for your internal reasoning, not for the user's chat window.
