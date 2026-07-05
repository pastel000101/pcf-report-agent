"""
retriever.py — Chroma 검색 + 링크된 표/그림 fetch [그룹 4 / LLM ✗ 임베딩 검색]

ingest가 만든 Chroma(bge-m3)에 연결해:
  1) 질의로 본문 청크를 유사도 검색
  2) 검색된 청크의 refs(가리키는 표/그림 id)를 모아 에셋을 '결정론적으로' fetch
  3) id로 dedup(이미 검색된 에셋은 중복 추가 안 함)
→ 본문 근거 + 링크된 표/그림 설명을 함께 반환.

node/retrieve.py(메인)가 이걸 호출한다. 서브(worker)는 직접 호출하지 않는다.
"""

from langchain_chroma import Chroma

from rag.ingest_iso_14067 import get_embeddings, PERSIST_DIR, COLLECTION

_store = None


def get_store():
    global _store
    if _store is None:
        _store = Chroma(collection_name=COLLECTION, persist_directory=PERSIST_DIR,
                        embedding_function=get_embeddings())
    return _store


def _parse_refs(meta: dict) -> list:
    s = meta.get("refs", "")
    return [x for x in s.split(",") if x] if s else []


def _item(cid, text, meta, linked=False) -> dict:
    return {
        "id": cid,
        "text": text,
        "source": meta.get("source", ""),
        "clause_no": meta.get("clause_no", ""),
        "type": meta.get("type", ""),     # table/figure면 에셋
        "linked": linked,                 # refs로 끌어온 표/그림인가
        "refs": _parse_refs(meta),        # 이 청크가 가리키는 표/그림 id(선별 후 에셋 재결합용)
    }


def search(query: str, k: int = 8) -> list:
    """질의 → 본문 청크 k개 + 링크된 표/그림. id로 dedup."""
    store = get_store()
    docs = store.similarity_search(query, k=k)

    out, seen, ref_ids = [], set(), []
    for d in docs:
        cid = d.metadata.get("chunk_id")
        seen.add(cid)
        out.append(_item(cid, d.page_content, d.metadata))
        ref_ids += _parse_refs(d.metadata)

    # refs로 표/그림 에셋 fetch (이미 검색된 것 제외)
    ref_ids = [r for r in dict.fromkeys(ref_ids) if r and r not in seen]
    if ref_ids:
        got = store.get(ids=ref_ids)
        for cid, text, meta in zip(got["ids"], got["documents"], got["metadatas"]):
            out.append(_item(cid, text, meta, linked=True))
    return out
