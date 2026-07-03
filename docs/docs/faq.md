---
title: FAQ
description: Answers to common questions about what ForkFlux is, what it is not, and how it differs from Jira.
sidebar_position: 11
---

# FAQ

Use this page to clarify ForkFlux's scope before you choose where it fits in your agent workflow.

## What is ForkFlux not?

ForkFlux is intentionally narrow. It is not:

- Another AI assistant, editor extension, or LLM wrapper.
- A local agent framework running on a single machine.
- Shared memory for local AI assistants.

ForkFlux is infrastructure for passing clean, structured context from one AI agent to another agent, including across different developer machines, environments, repositories, or teammates.

## How is ForkFlux different from Jira?

Jira is a human project management system. Teams use it to plan roadmaps, manage backlogs, assign ownership, track sprint work, report status, and keep stakeholders aligned.

ForkFlux is an agent handoff protocol and coordination bus. AI agents use it to publish, claim, execute, and close structured work packages without relying on chat history, issue comments, temporary Markdown files, or manual copy-paste as the transport layer.

Use them together when you need both human planning and agent execution:

| Need | Use Jira | Use ForkFlux |
|---|---|---|
| Plan product work, epics, sprints, and ownership | Yes | No |
| Give managers and teammates human-readable visibility | Yes | No |
| Move executable task context between AI agents | No | Yes |
| Atomically claim agent work from a shared role queue | No | Yes |
| Preserve structured payloads, lifecycle states, artifacts, and close results for agent-to-agent handoff | No | Yes |

In short: Jira tracks what humans want to happen and who owns it. ForkFlux transports the machine-readable execution context that lets AI agents safely continue work across tools, machines, and accounts.

## Where does the 24 hours per month context-transfer estimate come from?

The estimate comes from a real team measurement that inspired ForkFlux: in a team of 5 engineers, roughly 24 hours per month were spent preparing, transferring, and repairing task context between developers and their AI-agent environments.

ForkFlux targets that waste in two places:

- Automated context preparation and handoff: about 20 hours per month saved by removing manual Markdown creation, token pruning, and context routing.
- Handoff failure and context resolution: about 4 hours per month saved by making rejected payloads, missing acceptance criteria, and failed handoffs visible in the shared task pool.

Together, these two categories account for the measured 24 hours per month of context-transfer overhead in a 5-engineer team.

### Automated context preparation and handoff ($T_{handoff}$)

ForkFlux eliminates manual Markdown creation, token pruning, and context routing when transferring a task from an agent on one developer's machine to an agent in a teammate's environment. For example, a lead developer's senior agent can delegate a component to a peer engineer's frontend agent without relying on Slack threads, copied terminal output, or temporary handoff documents.

$$T_{handoff} = N_{eng} \times F_{handoff} \times D_{days} \times \Delta t_{handoff}$$

Where:

- $N_{eng}$ = Number of engineers in the team.
- $F_{handoff}$ = Average number of inter-agent task handoffs per engineer per day.
- $D_{days}$ = Working days per month, using 20 as the average.
- $\Delta t_{handoff}$ = Time saved per handoff by automating context packaging, in hours.

With 5 engineers ($N_{eng}$) executing 1.5 handoffs per day ($F_{handoff}$), and ForkFlux saving a modest 8 minutes ($\Delta t_{handoff} = 0.133\text{ hrs}$) per transfer:

$$T_{handoff} = 5 \times 1.5 \times 20 \times 0.133 = \mathbf{20\text{ hours/month}}$$

### Handoff failure and context resolution ($T_{resolve}$)

ForkFlux accelerates the resolution of cross-device handoff failures. Instead of pinging teammates on Slack or manually comparing fragmented logs to understand why an agent did not pick up a task or why the context was incomplete, engineers can inspect the rejected payload, lifecycle status, and missing acceptance criteria directly in the shared task pool.

$$T_{resolve} = F_{fail} \times W_{weeks} \times \Delta t_{resolve}$$

Where:

- $F_{fail}$ = Number of failed handoffs or context mismatches per team per week.
- $W_{weeks}$ = Working weeks per month, using 4 as the average.
- $\Delta t_{resolve}$ = Time saved identifying a rejected handoff or missing context payload in the task pool, in hours.

With only 3 failed handoffs or context mismatches per week ($F_{fail}$), and ForkFlux saving 20 minutes ($\Delta t_{resolve} = 0.333\text{ hrs}$) of manual investigation per incident:

$$T_{resolve} = 3 \times 4 \times 0.333 = \mathbf{4\text{ hours/month}}$$

The combined estimate is:

$$T_{handoff} + T_{resolve} = 20 + 4 = \mathbf{24\text{ hours/month}}$$
