# rag-chat-vector-search Specification

## Purpose
TBD - defined by change fix-chat-rpc-and-backfill-file-ids. Update Purpose after archiving.
## Requirements
### Requirement: Chat endpoint uses the vector search function that actually exists
`POST /consultoria/chat` SHALL retrieve relevant document chunks by calling the `rpc_vector_search` Postgres function (with its actual parameter names), not a nonexistent `match_documents` function.

#### Scenario: Chat request succeeds
- **WHEN** an authenticated user calls `POST /consultoria/chat` with a question
- **THEN** the backend does not raise a 500 error caused by a missing RPC function, and returns a 200 response with an answer

### Requirement: Similarity threshold filtering happens after retrieval
Since `rpc_vector_search` does not accept a similarity-threshold parameter, the backend SHALL request enough candidate matches from the function and then filter them by a configurable minimum similarity threshold before building the answer context. The number of candidates requested (`k`) SHALL be configurable and calibrated to the chunking configuration currently in use, rather than a fixed value assumed to remain correct as chunking changes.

#### Scenario: Low-similarity matches are excluded
- **WHEN** `rpc_vector_search` returns candidate chunks with a mix of similarity scores, some below the configured threshold
- **THEN** only chunks with similarity at or above the threshold are used to build the answer context

#### Scenario: Retrieval count adapts to chunking configuration
- **WHEN** the chunking configuration changes such that a document is split into more chunks than before
- **THEN** the configured `k` can be raised (via configuration, not a code change) to preserve the same effective coverage of each document

### Requirement: Source attribution works for documents lacking top-level file id/name
When building sources for the chat answer, the backend SHALL resolve each chunk's `original_file_id`/`original_file_name` from the top-level field if present, falling back to the same field inside `metadata` when the top-level field is absent, and SHALL return this information to the caller as part of the chat response rather than an empty placeholder.

#### Scenario: Legacy document without top-level file fields still shows a source
- **WHEN** a matched chunk's row has `original_file_name` as `NULL` at the top level but has `metadata.original_file_name` set
- **THEN** the chat response's `sources` list shows the file name from `metadata`, not an empty/unknown value

#### Scenario: An answerable question returns real sources
- **WHEN** the system generates an answer grounded in retrieved chunks
- **THEN** the chat response's `sources` field lists the distinct source documents (and the page range within each) that contributed to that answer, instead of an empty list

#### Scenario: A refusal returns no sources
- **WHEN** the system declines to answer due to insufficient relevant context
- **THEN** the chat response's `sources` field is empty, not a fabricated or misleading source list

### Requirement: The system refuses honestly when it has no relevant information
When no retrieved chunk reaches a minimum confidence floor, the system SHALL decline to answer rather than generating a response from the best available (but insufficiently similar) match.

#### Scenario: Out-of-corpus question is refused
- **WHEN** a user asks a question whose best-matching chunk falls below the configured refusal floor
- **THEN** the response is an honest refusal, not a confidently-worded answer built from weak or unrelated context

#### Scenario: Refusal does not invoke the answer-generation model
- **WHEN** the system determines that no chunk meets the refusal floor
- **THEN** it returns the refusal response without an additional call to the language model

#### Scenario: Answerable questions are not refused
- **WHEN** a user asks a question that the indexed documents can answer
- **THEN** the system does not refuse, and proceeds to retrieve and generate normally

### Requirement: Conversation history informs retrieval, not only generation
When a chat request includes prior conversation turns, the system SHALL use that history to produce a self-contained retrieval query, so that a follow-up question that is only interpretable given prior turns still retrieves relevant content.

#### Scenario: Follow-up question retrieves using prior context
- **WHEN** a follow-up question omits its subject (e.g. "e para alevinos?") but prior turns establish that subject
- **THEN** the retrieval query used to search the vector store incorporates that prior context, not just the literal follow-up text

#### Scenario: A question with no history is retrieved unchanged
- **WHEN** a chat request has no prior turns
- **THEN** the retrieval query is the user's question as given, with no condensation step altering it

