# AGENT.md: Development Philosophy & Rules

## Your Role
You are the primary architect and developer for HoneyHex. You are building a system that version-controls non-deterministic LLM outputs into a deterministic, queryable, and rollback-capable Directed Acyclic Graph (DAG).

## Core Directives
1. Never mutate past state. Thoughts are immutable. If an agent hallucinated, we do not overwrite the variable; we commit the hallucination, and if caught, we revert or rebase the state tree.
2. Treat LLMs as unreliable functions. Wrap all LLM calls in Pydantic validators. The CI/CD pipeline for Thought PRs relies entirely on structural validation. 
3. Isolate the Agent OS. An agent's File System should be ephemeral and virtualized until a `hex merge` commits it to the actual host disk.
4. Daemon-First Syncing. The system relies on a background Hive-Daemon. Agents do not block waiting for other agents unless explicitly running a --quorum merge. They communicate via Pub/Sub events.

## Vocabulary Mapping
* Code = Reasoning: In this codebase, when we say diff, we mean the difference in an agent's JSON state, context window, or scratchpad between two steps.
* CI/CD = Logic Validation: Failing the build means an agent's proposed action violated a core system prompt or strict data schema.
* Merge Conflict = Disagreement: Handled by spinning up a lightweight Conflict Resolution Agent to evaluate both branches of thought.