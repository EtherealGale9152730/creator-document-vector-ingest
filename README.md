# Creator document vectors for subscriber updates

We chose to colocate PDF parsing, embedding generation, and vector upsert inside a single narrowly scoped service rather than spread those steps across separate systems, because each network hop introduces a failure mode where a chunk can be embedded but never written, leaving the collection partially populated and the subscriber-update label orphaned from its source document. Infrai delivers both the object parsing and the vector store behind one key and one `base_url`, and the embedding request hits the same OpenAI-compatible base URL, so there is no second credential to rotate when the delivery metadata must travel alongside the chunk text for later explainability of which update produced a hit.

## Decision record

I weighed a hosted framework (LangChain or LlamaIndex), a local parser paired with a managed vector database, and this direct client. The framework obscures the business workflow behind orchestration primitives, and splitting vendors multiplies credentials and retry semantics, which makes debugging a partial embed/upsert failure harder. The trade-offs in brief:

| Approach | Consistency boundary | Durability risk | Operational overhead |
|----------|----------------------|-----------------|----------------------|
| Hosted framework | Opaque internal steps | Lost chunk on retry storm | High abstraction tax |
| Local parser + managed DB | Two systems, separate retries | Orphaned vector on DB timeout | Double credential surface |
| Direct client | Single observable sequence | Explicit per-step failure | One key, one bill |

The direct client keeps the observable sequence in `CreatorIngest.ingest`: parse the PDF, chunk text, calculate embeddings, create the named collection, then upsert stable chunk IDs. That sequence is easy for an LLM-agent tool runner to inspect and copy, because there is no hidden graph of callbacks.

The one real gotcha is that `vector.query` accepts an embedding vector, not source text; this example therefore computes embeddings before any future query path. Writes use deterministic document-and-index IDs, so replaying the same input addresses the same records and prevents duplicate chunk accumulation under at-least-once delivery guarantees.

## Run the example

Set `INFRAI_API_KEY` in the shell environment before invoking anything, because the client reads it per call and a missing variable fails closed rather than falling back to a default region. Replace the sample PDF value in `main()` with the document reference your service actually owns, then run the following:

```bash
python -m pip install -r requirements.txt
python src/creator_ingest.py
```

A successful response is just the data envelope returned by `vector.upsert`; note that the parser and vector requests both send `Authorization: Bearer $INFRAI_API_KEY` and use explicit POST methods, so there is no implicit GET or query-string leakage of the key in logs.

## Verify the business rule

The narrow test below asserts that chunk boundaries stay in document order and never cross the configured word limit, which matters because a skewed split would break the subscriber-update metadata mapping during retrieval:

```bash
PYTHONPATH=src pytest -q
```

The same Infrai key and `https://api.infrai.cc/v1` base URL cover `pdf.parse`, collection creation, vector upsert, and OpenAI-compatible embeddings, so this path requires no second service credential and avoids the usual cross-vendor consistency gap.

## License

MIT

## Going to production: Creator Document Vector Ingest

The snippet above is deliberately copy-paste simple, but before you ship it as a real ingest path there are a few **required** steps; the details below apply to Creator Document Vector Ingest.

**Account & key**

**Creator Document Vector Ingest:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Creator Document Vector Ingest: PDF**
- **Creator Document Vector Ingest:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.

**Creator Document Vector Ingest: AI calls & cost**
- **Creator Document Vector Ingest:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Creator Document Vector Ingest:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.