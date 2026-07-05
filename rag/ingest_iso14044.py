"""
ingest_iso14044.py — ISO 14044:2006 문서 인덱싱 (표/그림 제외 단순화 버전)

흐름:
  1. data/ISO-14044-2006.md 읽기
  2. Markdown 헤더(#) 단위로 1차 분할
  3. 긴 텍스트는 재귀적 문자열 분할기(RecursiveCharacterTextSplitter)로 2차 분할
  4. Ollama 임베딩(bge-m3)을 통해 ChromaDB에 저장 (collection='iso14044')
"""

import os
import re
from pathlib import Path

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

# 경로 설정
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MD_PATH = DATA_DIR / "ISO-14044-2006.md"
PERSIST_DIR = os.getenv("RAG_PERSIST_DIR") or str(Path(__file__).resolve().parents[1] / "rag" / "chroma_db")

# 크로마 컬렉션 이름과 임베딩 모델
COLLECTION = "iso14044"
EMBED_MODEL = os.getenv("RAG_EMBED_MODEL", "bge-m3")

# 청크 설정
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 100
HEADERS = [
    ("#", "H1"), ("##", "H2"), ("###", "H3"),
    ("####", "H4"), ("#####", "H5"), ("######", "H6"),
]

def extract_clause_no(header_value: str):
    """헤더 텍스트에서 조항 번호와 제목을 분리 (예: '4.2.3 Scope' -> '4.2.3', 'Scope')"""
    if not header_value:
        return "", ""
    m = re.match(r"^((?:\d+(?:\.\d+)*)|Annex [A-E]|[A-E]\.\d[\w.]*)\s+(.*)$", header_value.strip())
    if m:
        return m.group(1), m.group(2)
    return "", header_value.strip()


def build_breadcrumb(meta: dict) -> str:
    """헤더 계층 구조를 브레드크럼(경로) 문자열로 생성"""
    parts = []
    has_deeper = any(meta.get(h) for h in ["H2", "H3", "H4", "H5", "H6"])
    for h in ["H1", "H2", "H3", "H4", "H5", "H6"]:
        if not meta.get(h):
            continue
        # 제일 상위 H1은 하위가 있으면 보통 문서 제목이므로 생략
        if h == "H1" and has_deeper:
            continue
        parts.append(meta[h])
    return " > ".join(parts)


def is_definition(meta: dict) -> bool:
    """용어·정의 항목인가. 14044는 '## 3 Terms and definitions' 아래 '### 3.x 용어'(H3) 구조.
    (14067은 H5의 3.1.x.x였다 — 문서마다 정의 계층이 달라 여기선 H3 기준으로 맞춘다.)"""
    return bool(re.match(r"^3\.\d+\s", meta.get("H3", "")))


def is_normative(meta: dict) -> bool:
    """규범(normative) 조항인가. informative 부속서·참고문헌은 제외.
    (현재 14044 md엔 annex/bibliography가 없어 사실상 전부 True지만, 문서 확장 대비 로직 유지.)"""
    for h in ["H2", "H3"]:
        v = meta.get(h, "")
        if "(informative)" in v or "Bibliography" in v:
            return False
    return True


def detect_annex(meta: dict) -> str:
    """H2에서 부속서 문자(A~E) 추출. 없으면 ''."""
    m = re.search(r"Annex ([A-E])", meta.get("H2", ""))
    return m.group(1) if m else ""


def build_chunks(md_path=MD_PATH) -> list:
    """MD 파일을 읽어서 청크 리스트(dict) 반환"""
    text = open(md_path, encoding="utf-8").read()
    
    # 1. 헤더 기준으로 분할
    md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=HEADERS, strip_headers=False)
    
    # 2. 내용이 길면 글자 기준으로 분할
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, 
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", "; ", " ", ""], 
        keep_separator=True,
    )

    final_chunks = []
    idx = 0
    
    for sec in md_splitter.split_text(text):
        meta = sec.metadata
        clause_no, clause_title = extract_clause_no(
            meta.get("H6") or meta.get("H5") or meta.get("H4")
            or meta.get("H3") or meta.get("H2") or ""
        )
        base_meta = {
            "source": "ISO 14044:2006(E)",
            "doc_type": "standard_original",
            "clause_no": clause_no,
            "clause_title": clause_title,
            "breadcrumb": build_breadcrumb(meta),
            "is_definition": is_definition(meta),
            "is_normative": is_normative(meta),
            "annex": detect_annex(meta),
        }
        body = sec.page_content
        
        # 본문 분할
        pieces = char_splitter.split_text(body) if len(body) > CHUNK_SIZE else [body]
        
        for j, piece in enumerate(pieces):
            if not piece.strip():
                continue
            cid = (clause_no.replace(".", "_").replace(" ", "_") or f"sec{idx}")
            m = dict(base_meta, chunk_index=j, n_chunks=len(pieces))
            final_chunks.append({
                "id": f"{cid}__{j}", 
                "text": piece.strip(), 
                "metadata": m
            })
            idx += 1

    return final_chunks


def get_embeddings():
    return OllamaEmbeddings(model=EMBED_MODEL)


def _clean_meta(meta: dict) -> dict:
    """Chroma 메타데이터 제약(str/int/float/bool만 허용)에 맞춰 정리: list→콤마문자열, None 제거."""
    out = {}
    for k, v in meta.items():
        if v is None:
            continue
        if isinstance(v, list):
            out[k] = ",".join(map(str, v))
        elif isinstance(v, (str, int, float, bool)):
            out[k] = v
        else:
            out[k] = str(v)
    return out


def ingest():
    """청킹 → 임베딩 → ChromaDB 저장"""
    print(f"문서 읽기 및 청킹 시작: {MD_PATH}")
    chunks = build_chunks()
    
    docs = []
    ids = []
    for c in chunks:
        meta = _clean_meta(c["metadata"])
        meta["chunk_id"] = c["id"]
        docs.append(Document(page_content=c["text"], metadata=meta))
        ids.append(c["id"])

    print(f"총 {len(docs)}개의 청크가 생성되었습니다. ChromaDB에 임베딩하여 저장합니다...")
    
    store = Chroma.from_documents(
        documents=docs,
        embedding=get_embeddings(),
        ids=ids,
        collection_name=COLLECTION,
        persist_directory=PERSIST_DIR,
    )
    
    print(f"적재 완료! \n- 저장위치: {PERSIST_DIR} \n- 컬렉션: {COLLECTION} \n- 모델: {EMBED_MODEL}")
    return store


if __name__ == "__main__":
    ingest()
