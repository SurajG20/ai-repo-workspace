# Structural chunking only

Embedding quality collapses when chunks split symbols mid-body. We chunk strictly by code structure — function, class, module, service — using AST boundaries from the parser, and we do not offer naive fixed-token splitting as a fallback.

## Considered Options

- **Fixed-size token windows with overlap** (the default in most RAG stacks): rejected — splits functions across chunks, breaks signature-to-body cohesion, and produces citations like `file.ts lines 210–260` that mean nothing to a reader.
- **Recursive character splitting**: rejected for the same reasons, plus language-blindness.
- **Structural chunking**: chosen — every chunk maps 1:1 to a symbol that also exists in the Neo4j graph, so vector hits join to graph context for free.

## Consequences

- Very large functions may exceed embedding-model input limits; they are embedded whole or truncated by policy, never split arbitrarily.
- Chunk identity inherits symbol identity (`repository:file:name`), making citations precise (`file:line`) and deduplication trivial.
- Languages supported by embeddings are exactly those supported by the parser.
