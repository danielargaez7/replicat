# My Approach and Thoughts

## The Core Design Decision

The most important architectural choice: **don't treat this as a "send everything to GPT" problem.** Support bundles contain structured, well-defined data — pod statuses, exit codes, event reasons, resource states. Many failure modes are deterministic and well-documented. Using AI for what regex can do is wasteful and less reliable.

So I built a 4-pass pipeline. Pass 1 is pure heuristic: pattern matching against known Kubernetes failure signatures — CrashLoopBackOff, OOMKilled (exit code 137), ImagePullBackOff, probe failures, node pressure conditions. This is fast, deterministic, and produces high-confidence findings with zero API calls. Pass 2 sends targeted, per-namespace context to GPT-4o — not raw data dumps, but curated windows of pod specs, error-line log excerpts, and correlated events. The prompts include K8s domain knowledge (exit code tables, common failure cascades) so the model doesn't hallucinate about things it can look up. Pass 3 synthesizes across all findings to build a root-cause narrative: what caused what, what to fix first. This separation matters because it means the system produces useful results even when the AI layer is unavailable.

## What Makes This Interesting

The Troubleshoot bundle format is surprisingly well-structured for AI analysis. Pods, events, and logs are organized by namespace with predictable paths. This makes it possible to build precise context windows rather than dumping entire archives into a prompt. The real challenge isn't getting the LLM to say something — it's getting it to say something *grounded*. Every finding in Bundlescope cites specific evidence: the actual exit code, the actual event message, the actual log line. No "there might be issues with your deployment."

The streaming architecture (SSE) isn't just a UI gimmick — it fundamentally changes the user experience from "upload and wait" to "watch the analysis unfold." For large bundles with multiple failing namespaces, this is the difference between feeling broken and feeling intelligent.

## Where I'd Take This Next

The most promising direction is **agentic investigation**: instead of pre-determined analysis passes, give the LLM tools to query the bundle (`get_pod_logs`, `get_events`, `check_resource_limits`) and let it investigate iteratively, following hypotheses like a real support engineer. This would handle edge cases better and scale to larger bundles. For production, I'd add bundle comparison (diff two bundles to see what changed), a pattern library of known failure signatures, and structured report export. The heuristic engine could learn new patterns from resolved support cases over time, gradually reducing dependence on the AI layer for common issues.

The support bundle analysis problem is fundamentally about bridging the gap between raw observability data and actionable insight — and the most interesting part is deciding which parts of that bridge need AI and which don't.
