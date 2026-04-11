# Product Requirements Document (PRD): HoneyHex

## 1. Product Overview
HoneyHex is a Distributed Ledger of Intelligence for multi-agent systems. It moves away from linear LLM wrappers into an Agentic Version Control paradigm. In this system, each agent operates as a repository (a "Cell"), every thought/action is a commit, and multiple agents coordinate through a global mesh (the "Hivemind") using Git-like distributed consensus.

## 2. Core Concepts
* Agent-as-a-Repository: The System Prompt is the README.md, the Agent's Memory is the virtual file system, and its Reasoning Trace is the git log stored in a .honeyhex/ directory.
* Thought-Commits: A Think-to-Act cycle. The commit message is the LLM's internal monologue explaining why it took an action.
* The Hivemind (Global Mesh): Agents do not work in isolation. They constantly push, pull, and merge thoughts to maintain a synchronized collective consciousness.

## 3. Core Features & System Commands

### 3.1 Individual Agent Operations (Micro-Level)
* `hex commit`: Snapshots the current prompt, retrieved RAG context, scratchpad, and tool outputs at the end of a Think-to-Act cycle. 
* `hex checkout -b <hypothesis>`: Forks the agent's execution. Runs two versions of a task in parallel. The branch that reaches the success condition first merges back to main.
* `hex rebase --interactive`: Rewinds the agent's state, deletes hallucinated/bad commits, and re-applies logic with a new fix prompt to prevent hallucination debt.
* `hex cherry-pick <commit-hash>`: Extracts a specific successful thought-pattern from a side-branch or another agent and applies it to the current agent's context.

### 3.2 Swarm Operations (Macro-Level)
* The Hive-Registry: A central discovery layer tracking the HEAD commit of every agent.
  * Command: `hex status` (Visualizes the entire swarm's thought tree and branch operations).
* Distributed Consensus: Reaching a single conclusion via Weighted Voting.
  * Command: `hex merge --quorum` (A proposed solution is tested via background CI/CD for thoughts. If 51% of the validator agents approve, it merges into the Global State).
* Cross-Agent Rebase: Instant propagation of fundamental truths.
  * Command: `hex rebase --global` (All agents pause, pull the new truth commit, and rebase their current work on top of it).
* Inter-Agent Pull Requests: Agent A pushes data to a shared branch and requests review. 
  * Command: `hex push --target=<AgentB>` (Agent B runs a validation check. If malformed, the PR is rejected with an LLM-generated Code Review comment).