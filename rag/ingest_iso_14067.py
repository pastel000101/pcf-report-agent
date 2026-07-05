"""
ingest.py — 문서 인덱싱(청킹 → 임베딩 → Chroma 적재) [그룹 4 / LLM △ 임베딩]

흐름:
  rag.chunking.build_chunks() → Document 변환 → Ollama bge-m3 임베딩 → ChromaDB 영속화.

전제:
  - Ollama 데몬 실행 중 + 모델 pull:  ollama pull bge-m3
  - bge-m3 = 다국어 임베딩(한/영 혼재 ISO 문서에 적합)

설정(환경변수로 덮어쓰기 가능):
  RAG_PERSIST_DIR · RAG_COLLECTION · RAG_EMBED_MODEL

주의:
  - Chroma 메타데이터 값은 str/int/float/bool만 허용 → refs(list)는 콤마 문자열로 직렬화.
  - chunk id를 Document id로 써서, retriever가 refs로 에셋을 결정론적으로 fetch할 수 있게 한다.
  - 한 번 적재해 두고 재사용. 원문이 갱신될 때만 다시 실행.
"""

import os
from pathlib import Path

from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

from rag.chunking import build_chunks

PERSIST_DIR = os.getenv("RAG_PERSIST_DIR") or str(Path(__file__).resolve().parents[1] / "rag" / "chroma_db")
COLLECTION = os.getenv("RAG_COLLECTION", "iso14067")
EMBED_MODEL = os.getenv("RAG_EMBED_MODEL", "bge-m3")


def get_embeddings():
    return OllamaEmbeddings(model=EMBED_MODEL)


def _clean_meta(meta: dict) -> dict:
    """Chroma 호환 메타로 정리: list→콤마문자열, None 제거, 나머지는 스칼라만."""
    out = {}
    for k, v in meta.items():
        if v is None:
            continue
        if isinstance(v, list):
            out[k] = ",".join(map(str, v))      # refs 등
        elif isinstance(v, (str, int, float, bool)):
            out[k] = v
        else:
            out[k] = str(v)
    return out


def ingest(persist_dir=PERSIST_DIR, collection=COLLECTION):
    """청킹 → 임베딩 → Chroma 적재. 적재된 store를 반환."""
    chunks = build_chunks()
    docs, ids = [], []
    for c in chunks:
        meta = _clean_meta(c["metadata"])
        meta["chunk_id"] = c["id"]          # 검색 결과 dedup·ref fetch용
        docs.append(Document(page_content=c["text"], metadata=meta))
        ids.append(c["id"])

    store = Chroma.from_documents(
        documents=docs,
        embedding=get_embeddings(),
        ids=ids,                      # chunk id = Document id (refs fetch용)
        collection_name=collection,
        persist_directory=persist_dir,
    )
    print(f"적재 완료: {len(docs)}개 청크 → {persist_dir} (collection={collection}, model={EMBED_MODEL})")
    return store


if __name__ == "__main__":
    ingest()
