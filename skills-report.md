# Skills Audit Report

Date: 2026-06-14

## Installation Summary

Installed and verified with `npx skills list`.

- Total active project skills: 56
- Install location: `.agents/skills/`
- Lock file: `skills-lock.json`
- Duplicate directory check: no duplicate skill directories found

Source counts:

- `am-will/codex-skills`: 20
- `obra/superpowers`: 14
- `nextlevelbuilder/ui-ux-pro-max-skill`: 7
- `vercel-labs/agent-skills`: 8
- `pbakaus/impeccable`: 1
- `specstoryai/agent-skills`: 6

Latest requested installation results:

- `nextlevelbuilder/ui-ux-pro-max-skill`: installed 7 skills.
- `pbakaus/impeccable`: installed 1 skill.
- `DavidHDev/react-bits`: not installed; repository cloned but no valid `SKILL.md` files with required metadata were found.
- `multicai-ai/andrej-karpathy-skills`: not installed; GitHub HTTPS clone failed with authentication/access error.

## Installed Skills

| Skill | Source |
| --- | --- |
| Agent Browser | `am-will/codex-skills` |
| brainstorming | `obra/superpowers` |
| ckm:banner-design | `nextlevelbuilder/ui-ux-pro-max-skill` |
| ckm:brand | `nextlevelbuilder/ui-ux-pro-max-skill` |
| ckm:design | `nextlevelbuilder/ui-ux-pro-max-skill` |
| ckm:design-system | `nextlevelbuilder/ui-ux-pro-max-skill` |
| ckm:slides | `nextlevelbuilder/ui-ux-pro-max-skill` |
| ckm:ui-styling | `nextlevelbuilder/ui-ux-pro-max-skill` |
| create-hook | `am-will/codex-skills` |
| deploy-to-vercel | `vercel-labs/agent-skills` |
| dispatching-parallel-agents | `obra/superpowers` |
| executing-plans | `obra/superpowers` |
| finishing-a-development-branch | `obra/superpowers` |
| Frontend Responsive Design Standards | `am-will/codex-skills` |
| frontend-design | `am-will/codex-skills` |
| gemini-computer-use | `am-will/codex-skills` |
| img-to-frontend | `am-will/codex-skills` |
| impeccable | `pbakaus/impeccable` |
| llm-council | `am-will/codex-skills` |
| markdown-url | `am-will/codex-skills` |
| openai-docs-skill | `am-will/codex-skills` |
| parallel | `am-will/codex-skills` |
| parallel-task | `am-will/codex-skills` |
| parallel-task-spark | `am-will/codex-skills` |
| plan-harder | `am-will/codex-skills` |
| planner | `am-will/codex-skills` |
| pluginstaller | `am-will/codex-skills` |
| read-github | `am-will/codex-skills` |
| receiving-code-review | `obra/superpowers` |
| requesting-code-review | `obra/superpowers` |
| role-creator | `am-will/codex-skills` |
| specstory-guard | `specstoryai/agent-skills` |
| specstory-link-trail | `specstoryai/agent-skills` |
| specstory-organize | `specstoryai/agent-skills` |
| specstory-project-stats | `specstoryai/agent-skills` |
| specstory-session-summary | `specstoryai/agent-skills` |
| specstory-yak | `specstoryai/agent-skills` |
| subagent-driven-development | `obra/superpowers` |
| super-swarm-spark | `am-will/codex-skills` |
| swarm-planner | `am-will/codex-skills` |
| systematic-debugging | `obra/superpowers` |
| test-driven-development | `obra/superpowers` |
| ui-ux-pro-max | `nextlevelbuilder/ui-ux-pro-max-skill` |
| using-git-worktrees | `obra/superpowers` |
| using-superpowers | `obra/superpowers` |
| vercel-cli-with-tokens | `vercel-labs/agent-skills` |
| vercel-composition-patterns | `vercel-labs/agent-skills` |
| vercel-optimize | `vercel-labs/agent-skills` |
| vercel-react-best-practices | `am-will/codex-skills` |
| vercel-react-native-skills | `vercel-labs/agent-skills` |
| vercel-react-view-transitions | `vercel-labs/agent-skills` |
| verification-before-completion | `obra/superpowers` |
| web-design-guidelines | `vercel-labs/agent-skills` |
| writing-guidelines | `vercel-labs/agent-skills` |
| writing-plans | `obra/superpowers` |
| writing-skills | `obra/superpowers` |

## Available Commands

Verified commands:

- `npx skills add <owner>/<repo>` installs all skills from a GitHub repository.
- `npx skills list` lists installed project skills and their install paths.

Commands executed:

- `npx skills add obra/superpowers`
- `npx skills add vercel-labs/agent-skills`
- `npx skills add am-will/codex-skills`
- `npx skills add specstoryai/agent-skills`
- `npx skills list`

Note: `npx skills --help` did not return usable output in this environment, so only verified commands are listed above.

## Overlapping Skills

No duplicate skill directories remain after installation.

Observed overlap:

- `vercel-react-best-practices` was installed by `vercel-labs/agent-skills` and then overwritten by `am-will/codex-skills`. The active version is from `am-will/codex-skills`.

Functional overlap to manage during use:

- Planning: `planner`, `plan-harder`, `writing-plans`, `executing-plans`, `swarm-planner`
- Parallel/multi-agent work: `parallel`, `parallel-task`, `parallel-task-spark`, `dispatching-parallel-agents`, `subagent-driven-development`, `super-swarm-spark`
- Frontend/UI: `frontend-design`, `Frontend Responsive Design Standards`, `web-design-guidelines`, `img-to-frontend`, `vercel-react-best-practices`
- Review/quality: `receiving-code-review`, `requesting-code-review`, `verification-before-completion`, `systematic-debugging`, `test-driven-development`
- Documentation/session history: `specstory-session-summary`, `specstory-organize`, `specstory-project-stats`, `writing-guidelines`

## Recommended Skills By Use Case

Streamlit:

- `frontend-design`
- `Frontend Responsive Design Standards`
- `web-design-guidelines`
- `systematic-debugging`
- `verification-before-completion`

SaaS:

- `frontend-design`
- `web-design-guidelines`
- `vercel-composition-patterns`
- `writing-guidelines`
- `verification-before-completion`

Multi-Agent:

- `subagent-driven-development`
- `dispatching-parallel-agents`
- `parallel-task`
- `parallel-task-spark`
- `super-swarm-spark`
- `swarm-planner`

RAG:

- `planner`
- `systematic-debugging`
- `test-driven-development`
- `verification-before-completion`
- `llm-council`

UI/UX:

- `frontend-design`
- `Frontend Responsive Design Standards`
- `web-design-guidelines`
- `img-to-frontend`
- `vercel-react-best-practices`

## Additional Recommended Skills To Create

Construction Compliance:

- `construction-compliance-review`
- Purpose: review construction documents for compliance workflow, risk categories, evidence extraction, and escalation.

NCC 2025:

- `ncc-2025-compliance`
- Purpose: encode NCC 2025 clause lookup, building class handling, state variations, citation requirements, and uncertainty rules.

Business Analytics:

- `business-analytics-dashboard`
- Purpose: guide metric definitions, KPI modeling, executive dashboards, spreadsheet ingestion, and structured insight generation.

CrewAI:

- `crewai-agent-architecture`
- Purpose: standardize CrewAI agent/task/crew design, tool wiring, testing patterns, and production deployment checks.

## Cleanup Result

- Duplicate active skill directories: none.
- Duplicate functional coverage: documented above for routing discipline.
- Application code modified: no.
