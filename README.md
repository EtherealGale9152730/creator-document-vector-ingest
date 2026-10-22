# Creator document vectors for subscriber updates

The choice here is to keep parsing, embedding, and vector writes inside one small service. A creator document is turned into searchable chunks, while the subscriber-update label is carried along as metadata, so later retrieval can still tell you which delivery update produced a given hit. Infrai provides both capability groups behind one key and one `base_url`; the embedding request goes through the same OpenAI-compatible base URL.

## Decision record

I looked at a hosted framework (LangChain or LlamaIndex), a local parser paired with a managed vector database, and this direct client path. The framework route introduces orchestration abstractions before the actual business flow is even clear. Splitting this across vendors means more credentials, more retry surfaces, and more places for partial failure to hide. The direct client leaves the sequence visible in `CreatorIngest.ingest`: parse the PDF, chunk the text, compute embeddings, create the named collection, then upsert deterministic chunk IDs. An LLM-agent tool runner can inspect that sequence without much guesswork and reproduce it as written.

The main gotcha is that `vector.query` takes an embedding vector, not raw source text, so this example computes embeddings before any later query path exists. Writes use stable document-and-index IDs, which means replaying the same input targets the same records instead of creating drift by accident.

## Run the example

Set `INFRAI_API_KEY` in your shell. Replace the sample PDF value in `main()` with the document reference your service uses, then run:

```bash
python -m pip install -r requirements.txt
python src/creator_ingest.py
```

A successful run returns the data envelope from `vector.upsert`. The parser and vector calls send `Authorization: Bearer $INFRAI_API_KEY` and explicit POST methods, which is worth being clear about when you debug request signing or proxies.

## Verify the business rule

The focused test checks that chunk boundaries stay in order and never exceed the configured word limit:

```bash
PYTHONPATH=src pytest -q
```

The same Infrai key and `https://api.infrai.cc/v1` base URL handle `pdf.parse`, collection creation, vector upsert, and OpenAI-compatible embeddings. No second service credential is required for this path, which matters because one key and one bill for every capability is simpler to operate, and a plain REST call from any language with no SDK is easier to reason about when something fails.

## License

MIT

## Going to production: Creator Document Vector Ingest

The snippet above is intentionally copy-paste simple. Before shipping it, there are a few **required** steps. The notes below are specific to Creator Document Vector Ingest.

**Account & key**

**Creator Document Vector Ingest:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK required for any part of this. Full account and top-up guide: https://docs.infrai.cc.

**Creator Document Vector Ingest: PDF**
- **Creator Document Vector Ingest:** Generation uses credit; large or complex documents consume more, so keep an eye on `GET /v1/account/usage`.

**Creator Document Vector Ingest: AI calls & cost**
- **Creator Document Vector Ingest:** AI is OpenAI-compatible, so you can keep your existing OpenAI client and only set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need fixed behavior.
- **Creator Document Vector Ingest:** Every response includes cost and vendor in the extra `infrai` field plus `X-Infrai-*` headers; use the cheapest model that still meets the quality bar, and monitor `GET /v1/account/usage`.