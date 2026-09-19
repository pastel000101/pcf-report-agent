"""
retriever.py — Chroma 검색 + 링크된 표/그림 fetch [그룹 4 / LLM ✗ 임베딩 검색]

ingest가 만든 Chroma(bge-m3)에 연결해:
  1) 질의로 두 표준 컬렉션(iso14067·iso14044)을 각각 유사도 검색 → 거리 기준 병합 상위 k
  2) 검색된 청크의 refs(가리키는 표/그림 id)를 모아 에셋을 '결정론적으로' fetch
  3) id로 dedup(이미 검색된 에셋은 중복 추가 안 함)
→ 본문 근거 + 링크된 표/그림 설명을 함께 반환.

id 네임스페이스:
  두 표준 모두 조항 번호로 청크 id를 만들어(예: 3_1__0) 컬렉션 간 id가 겹친다.
  → 반환 id는 '컬렉션:청크id'로 네임스페이스해 node/retrieve.py의 dedup이 오판하지 않게 한다.
  refs 에셋(표/그림)은 iso14067에만 있으므로 그 컬렉션에서만 fetch한다.

node/retrieve.py(메인)가 이걸 호출한다. 서브(worker)는 직접 호출하지 않는다.
"""

from langchain_chroma import Chroma

from rag.ingest_iso_14067 import get_embeddings, PERSIST_DIR, COLLECTION as COLL_14067
from rag.ingest_iso14044 import COLLECTION as COLL_14044

_stores = None


def get_stores() -> dict:
    global _stores
    if _stores is None:
        emb = get_embeddings()
        _stores = {name: Chroma(collection_name=name, persist_directory=PERSIST_DIR,
                                embedding_function=emb)
                   for name in (COLL_14067, COLL_14044)}
    return _stores


def _parse_refs(meta: dict) -> list:
    s = meta.get("refs", "")
    return [x for x in s.split(",") if x] if s else []


def _item(ns, cid, text, meta, linked=False) -> dict:
    return {
        "id": f"{ns}:{cid}",              # 컬렉션 네임스페이스 부여(표준 간 id 충돌 방지)
        "text": text,
        "source": meta.get("source", ""),
        "clause_no": meta.get("clause_no", ""),
        "type": meta.get("type", ""),     # table/figure면 에셋
        "linked": linked,                 # refs로 끌어온 표/그림인가
        "refs": [f"{ns}:{r}" for r in _parse_refs(meta)],  # 이 청크가 가리키는 표/그림 id(선별 후 에셋 재결합용)
    }


def search(query: str, k: int = 8) -> list:
    """질의 → 두 컬렉션 병합 상위 k개 본문 청크 + 링크된 표/그림. id로 dedup."""
    stores = get_stores()
    scored = []                           # (거리, 컬렉션명, Document)
    for name, store in stores.items():
        for d, dist in store.similarity_search_with_score(query, k=k):
            scored.append((dist, name, d))
    scored.sort(key=lambda t: t[0])       # 거리 오름차순 = 유사도 내림차순

    out, seen, ref_ids = [], set(), []
    for _, name, d in scored[:k]:
        it = _item(name, d.metadata.get("chunk_id"), d.page_content, d.metadata)
        if it["id"] in seen:
            continue
        seen.add(it["id"])
        out.append(it)
        ref_ids += _parse_refs(d.metadata)    # 에셋 refs는 iso14067 청크에만 있다

    # refs로 표/그림 에셋 fetch (이미 검색된 것 제외) — 에셋은 iso14067 컬렉션에만 존재
    ref_ids = [r for r in dict.fromkeys(ref_ids) if r and f"{COLL_14067}:{r}" not in seen]
    if ref_ids:
        got = stores[COLL_14067].get(ids=ref_ids)
        for cid, text, meta in zip(got["ids"], got["documents"], got["metadatas"]):
            out.append(_item(COLL_14067, cid, text, meta, linked=True))
    return out
