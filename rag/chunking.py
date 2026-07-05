"""
chunking.py — ISO 14067 청킹 [그룹 4 / LLM ✗]

data/chunk_iso14067.py의 로직을 rag 패키지로 옮긴 것.
JSON 파일을 쓰지 않고 청크 리스트(dict)를 바로 반환한다 → ingest가 임베딩에 사용.

전략:
  1) 헤더(#~######) 기준 1차 분할 + breadcrumb 메타
  2) 긴 청크만 문단 우선 2차 분할(표/수식/그림 블록은 원자 보존)
  3) [B안] 본문의 그림 설명·Table 1 표는 자리표시로 치환(에셋이 정본) → 중복 제거
  4) 본문 청크에 refs(가리키는 표/그림 id) 부여
  5) 표/그림 에셋(정본)을 합쳐 반환
"""

import re
import json
from pathlib import Path

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CLEAN_MD = DATA_DIR / "ISO14067.md"
TABLE_FIG_JSON = DATA_DIR / "ISO14067_table_figure_chunks.json"

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 100
HEADERS = [
    ("#", "H1"), ("##", "H2"), ("###", "H3"),
    ("####", "H4"), ("#####", "H5"), ("######", "H6"),
]


def extract_clause_no(header_value: str):
    if not header_value:
        return "", ""
    m = re.match(r"^((?:\d+(?:\.\d+)*)|Annex [A-E]|[A-E]\.\d[\w.]*)\s+(.*)$", header_value.strip())
    if m:
        return m.group(1), m.group(2)
    return "", header_value.strip()


def build_breadcrumb(meta: dict) -> str:
    parts = []
    has_deeper = any(meta.get(h) for h in ["H2", "H3", "H4", "H5", "H6"])
    for h in ["H1", "H2", "H3", "H4", "H5", "H6"]:
        if not meta.get(h):
            continue
        if h == "H1" and has_deeper:
            continue
        parts.append(meta[h])
    return " > ".join(parts)


def is_definition(meta: dict) -> bool:
    return bool(re.match(r"^3\.1\.\d+\.\d+\s", meta.get("H5", "")))


def is_normative(meta: dict) -> bool:
    for h in ["H2", "H3"]:
        v = meta.get(h, "")
        if "Annex D" in v or "Annex E" in v or "(informative)" in v or "Bibliography" in v:
            return False
    return True


def detect_annex(meta: dict) -> str:
    m = re.search(r"Annex ([A-E])", meta.get("H2", ""))
    return m.group(1) if m else ""


def build_label_map(tf: list) -> dict:
    """표/그림 청크의 metadata.label → id. 예: {"Table 1": "table_1__p27", ...}"""
    return {c["metadata"]["label"]: c["id"] for c in tf if c.get("metadata", {}).get("label")}


def find_refs(text: str, label_map: dict) -> list:
    refs = []
    for label, aid in label_map.items():
        pat = r"\b" + re.escape(label).replace(r"\ ", r"\s+") + r"\b"
        if re.search(pat, text):
            refs.append(aid)
    return sorted(set(refs))


def strip_asset_blocks(md: str, label_map: dict) -> str:
    """[B안] 그림 설명 블록·Table 1 표를 자리표시로 치환(전체 내용은 에셋에만)."""
    lines = md.split("\n")
    out, i, n = [], 0, len(lines)
    while i < n:
        s = lines[i].strip()
        if s.startswith(">"):
            j, buf = i, []
            while j < n and lines[j].strip().startswith(">"):
                buf.append(lines[j]); j += 1
            block = "\n".join(buf)
            if "[Figure description" in block:
                cap = re.sub(r"^\s*>\s*\*+", "", buf[0]).strip().strip("*").strip()
                m = re.search(r"Figure\s+(\d+)", cap)
                aid = label_map.get(f"Figure {m.group(1)}", "") if m else ""
                out.append(f"> {cap} — [상세 설명은 에셋 {aid} 참조]")
                i = j
                continue
            out.extend(buf); i = j
            continue
        if s.startswith("|"):
            j, buf = i, []
            while j < n and lines[j].strip().startswith("|"):
                buf.append(lines[j]); j += 1
            if "Subclause" in "\n".join(buf) and "Specific GHG emissions" in "\n".join(buf):
                aid = label_map.get("Table 1", "")
                out.append(f"Table 1 — Specific GHG emissions and removals treatment — [상세 표는 에셋 {aid} 참조]")
                i = j
                continue
            out.extend(buf); i = j
            continue
        out.append(lines[i]); i += 1
    return "\n".join(out)


def split_preserving_blocks(body: str, char_splitter) -> list:
    lines = body.split("\n")
    blocks, i, n = [], 0, len(lines)
    while i < n:
        stripped = lines[i].strip()
        if stripped.startswith("```"):
            buf = [lines[i]]; i += 1
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            if i < n:
                buf.append(lines[i]); i += 1
            while i < n:
                nxt = lines[i].strip()
                if nxt == "":
                    if i + 1 < n and (lines[i + 1].strip().lower().startswith("where")
                                      or lines[i + 1].strip().startswith("-")):
                        buf.append(lines[i]); i += 1; continue
                    break
                if nxt.lower().startswith("where") or nxt.startswith("- "):
                    buf.append(lines[i]); i += 1; continue
                break
            blocks.append(("atomic", "\n".join(buf)))
            continue
        if stripped.startswith("|"):
            buf = [lines[i]]; i += 1
            while i < n and lines[i].strip().startswith("|"):
                buf.append(lines[i]); i += 1
            blocks.append(("atomic", "\n".join(buf)))
            continue
        if stripped.startswith(">"):
            buf = [lines[i]]; i += 1
            while i < n and (lines[i].strip().startswith(">") or lines[i].strip() == ""):
                if lines[i].strip() == "" and not (i + 1 < n and lines[i + 1].strip().startswith(">")):
                    break
                buf.append(lines[i]); i += 1
            blocks.append(("atomic", "\n".join(buf)))
            continue
        blocks.append(("text", lines[i])); i += 1

    pieces, text_run = [], []

    def flush():
        nonlocal text_run
        joined = "\n".join(text_run).strip()
        if joined:
            pieces.extend(char_splitter.split_text(joined) if len(joined) > CHUNK_SIZE else [joined])
        text_run = []

    for kind, txt in blocks:
        if kind == "atomic":
            flush(); pieces.append(txt.strip())
        else:
            text_run.append(txt)
    flush()
    return [p for p in pieces if p.strip()]


def build_chunks(md_path=CLEAN_MD, asset_path=TABLE_FIG_JSON) -> list:
    """최종 청크 리스트 반환: [{"id","text","metadata"}, ...] (본문 + 에셋)."""
    text = open(md_path, encoding="utf-8").read()
    try:
        tf = json.load(open(asset_path, encoding="utf-8"))
    except FileNotFoundError:
        tf = []
    label_map = build_label_map(tf)
    text = strip_asset_blocks(text, label_map)   # [B안]

    md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=HEADERS, strip_headers=False)
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", "; ", " ", ""], keep_separator=True,
    )

    final_chunks, idx = [], 0
    for sec in md_splitter.split_text(text):
        meta = sec.metadata
        clause_no, clause_title = extract_clause_no(
            meta.get("H6") or meta.get("H5") or meta.get("H4")
            or meta.get("H3") or meta.get("H2") or ""
        )
        base_meta = {
            "source": "ISO 14067:2018(E)", "doc_type": "standard_original",
            "clause_no": clause_no, "clause_title": clause_title,
            "breadcrumb": build_breadcrumb(meta),
            "is_definition": is_definition(meta), "is_normative": is_normative(meta),
            "annex": detect_annex(meta),
        }
        body = sec.page_content
        pieces = [body] if len(body) <= CHUNK_SIZE else split_preserving_blocks(body, char_splitter)
        for j, piece in enumerate(pieces):
            cid = (clause_no.replace(".", "_").replace(" ", "_") or f"sec{idx}")
            m = dict(base_meta, chunk_index=j, n_chunks=len(pieces),
                     refs=find_refs(piece, label_map))
            final_chunks.append({"id": f"{cid}__{j}", "text": piece.strip(), "metadata": m})
            idx += 1

    for c in tf:   # 표/그림 에셋(정본) 합치기
        c.setdefault("metadata", {}).setdefault("doc_type", "standard_original")
        final_chunks.append(c)

    return final_chunks


if __name__ == "__main__":
    chunks = build_chunks()
    print(f"총 청크 {len(chunks)} (refs 보유 {sum(1 for c in chunks if c['metadata'].get('refs'))})")
