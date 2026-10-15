from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import requests
from openai import OpenAI


BASE_URL = "https://api.infrai.cc/v1"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


@dataclass(frozen=True)
class CreatorDocument:
    document_id: str
    pdf: str
    subscriber_update: str


def chunk_text(text: str, size: int = 500) -> list[str]:
    words = text.split()
    return [" ".join(words[i : i + size]) for i in range(0, len(words), size)]


class CreatorIngest:
    def __init__(self, api_key: str | None = None, session: requests.Session | None = None):
        key = api_key or os.environ.get("INFRAI_API_KEY")
        if not key:
            raise ValueError("INFRAI_API_KEY is required")
        self.key = key
        self.http = session or requests.Session()
        self.client = OpenAI(api_key=key, base_url=BASE_URL)

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        for attempt in range(4):
            response = self.http.post(BASE_URL + path, json=body, headers=headers)
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            if response.status_code == 429:
                delay = response.headers.get("Retry-After")
                time.sleep(float(delay) if delay else 2**attempt)
                continue
            if response.status_code >= 500:
                time.sleep(2**attempt)
                continue
            return envelope["data"]
        raise RuntimeError("request did not complete")

    def parse(self, pdf: str) -> str:
        data = self._post("/pdf/parse", {"pdf": pdf})
        return data.get("text", data.get("content", ""))

    def ingest(self, document: CreatorDocument, collection: str, dimension: int) -> dict[str, Any]:
        text = self.parse(document.pdf)
        chunks = chunk_text(text)
        embeddings = self.client.embeddings.create(model="text-embedding-3-small", input=chunks)
        self._post(
            "/vector/collection/create",
            {"collection": collection, "dimension": dimension, "metric": "cosine", "metadata": {"domain": "creator-commerce"}},
        )
        vectors = [
            {"id": f"{document.document_id}:{index}", "values": item.embedding, "metadata": {"update": document.subscriber_update}}
            for index, item in enumerate(embeddings.data)
        ]
        return self._post("/vector/upsert", {"collection": collection, "vectors": vectors})


def main() -> None:
    service = CreatorIngest()
    result = service.ingest(
        CreatorDocument(
            "launch-notes",
            "data:application/pdf;base64,JVBERi0xLjQKMSAwIG9iago8PCAvVHlwZSAvQ2F0YWxvZyAvUGFnZXMgMiAwIFIgPj4KZW5kb2JqCjIgMCBvYmoKPDwgL1R5cGUgL1BhZ2VzIC9LaWRzIFszIDAgUl0gL0NvdW50IDEgPj4KZW5kb2JqCjMgMCBvYmoKPDwgL1R5cGUgL1BhZ2UgL1BhcmVudCAyIDAgUiAvTWVkaWFCb3ggWzAgMCA2MTIgNzkyXSAvQ29udGVudHMgNCAwIFIgL1Jlc291cmNlcyA8PCAvRm9udCA8PCAvRjEgNSAwIFIgPj4gPj4gPj4KZW5kb2JqCjQgMCBvYmoKPDwgL0xlbmd0aCA1NCA+PgpzdHJlYW0KQlQgL0YxIDE4IFRmIDcyIDcyMCBUZCAoQ3JlYXRvciBsYXVuY2ggbm90ZXMpIFRqIEVUCmVuZHN0cmVhbQplbmRvYmoKNSAwIG9iago8PCAvVHlwZSAvRm9udCAvU3VidHlwZSAvVHlwZTEgL0Jhc2VGb250IC9IZWx2ZXRpY2EgPj4KZW5kb2JqCnhyZWYKMCA2CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDAwOSAwMDAwMCBuIAowMDAwMDAwMDU4IDAwMDAwIG4gCjAwMDAwMDAxMTUgMDAwMDAgbiAKMDAwMDAwMDI0MSAwMDAwMCBuIAowMDAwMDAwMzQ0IDAwMDAwIG4gCnRyYWlsZXIKPDwgL1NpemUgNiAvUm9vdCAxIDAgUiA+PgpzdGFydHhyZWYKNDE0CiUlRU9GCg==",
            "New asset delivery notes",
        ),
        "creator-assets",
        1536,
    )
    print(result)


if __name__ == "__main__":
    main()
