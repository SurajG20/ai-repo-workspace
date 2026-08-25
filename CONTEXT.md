# AI Repository Workspace

Domain language for the repository-intelligence platform. One shared context: everything here describes how a codebase goes from cloned to queryable.

## Language

### Ingestion

**Repository**:
A GitHub repository registered on the platform. Exists once per full name; soft-deleted repositories leave the platform but keep their history.
_Avoid_: repo, project

**Indexing Pipeline**:
The fixed sequence of stages that takes a Repository from registration to queryable: clone, then parse, then graph sync + embed in parallel. There is exactly one pipeline; its shape is not configurable per run.
_Avoid_: workflow, ingestion chain, DAG

**Stage**:
One step of the Indexing Pipeline: clone, snapshot, parse, graph_sync, or embed. A Stage knows nothing about what precedes or follows it.
_Avoid_: phase, step kind

**Job**:
A queued instance of one Stage for one Repository. The unit that gets claimed, completed, failed, and retried.
_Avoid_: task (that is the executor), work item

**Snapshot**:
A recorded commit state of a Repository captured at index time; parsing works against a Snapshot's checkout.
_Avoid_: revision, version

**Artifact**:
The durable output of a finished Stage (for example parse results), consumed by the following Stage or Stages. An Artifact outlives every consumer; it is cleaned up only when the whole pipeline pass reaches a terminal state.
_Avoid_: payload, data file, temp file

**Claim**:
A worker's exclusive reservation of a queued Job. Two workers can never hold the same Claim; a worker that dies mid-Job loses its Claim back to the queue.
_Avoid_: lock, lease
