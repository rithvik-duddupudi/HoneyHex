3. CODE_PATTERNS (Architectural Paradigms)
Markdown
# CODE_PATTERNS

## 1. The Thought-Commit Pattern (Snapshotting)
Every LLM execution must pass through a CommitManager. 

```python
class ThoughtCommit(BaseModel):
    commit_hash: str
    parent_hash: str
    internal_monologue: str
    diff: StateDiff
    timestamp: datetime
2. The CRDT Blackboard (State Sync)
For the Global Mesh, use Conflict-Free Replicated Data Types for shared variables. If Agent A and Agent B append to a shared array simultaneously, the system must deterministically resolve the order without locking the entire swarm.

3. The Shadow-Branch (Hypothesis Testing)
When implementing hex checkout -b, use Python's multiprocessing or asyncio.gather.

Pattern: Clone the agent's current state object. Spawn two asynchronous worker tasks. The first task to yield a positive validation boolean triggers a cancellation Event on the sibling task.

4. The Consensus Strategy (LLM-Raft)
For hex merge --quorum:

Implement a Proposer class and a Validator class.

Proposer: Submits a CommitProposal.

Validator: A lightweight LLM call that returns {"approved": bool, "reason": str}.

Quorum Logic: if sum(v.approved) / len(validators) >= 0.51: execute_merge()