"""
retrieve.py — 메인: RAG 호출 [그룹 2 / LLM △ 검색만]

역할:
  Outline의 각 섹션이 필요로 하는 규제·방법론 근거를 검색해 '주제별로 인덱싱'한다.
  (예: 할당, 영향평가 방법, 데이터 품질 등)

입력 → 출력:
  Outline → 주제 → 근거 청크 묶음(evidence)

의존: rag.retriever (검색기)

주의:
  - RAG는 메인만 호출한다. 서브(worker)가 직접 검색하면 같은 문서를 여러 번 가져와
    비용·비일관이 생긴다.
  - 질의는 '섹션 목적(goal)·포함항목(must_cover) 단위'로 쪼개 여러 번 던진다.
    제목+목표+포함항목 전부를 이어붙인 긴 질의 1건은 임베딩이 평균화되어
    짧고 용어 밀도가 높은 정의 조항(3장)만 잔뜩 맞았다(run_trace 20260703_172241:
    lci/lcia 8건 중 대부분이 3.1.x 정의, 두 섹션 간 중복도 심함).
"""

from rag.retriever import search

K_PER_SECTION = 8     # 섹션당 최종 근거 수
K_PER_QUERY = 5       # 질의당 후보 수(과검색 후 선별)
MAX_DEFINITIONS = 2   # 용어 정의(3장) 조항 상한 — 방법론 조항(5/6/7장 등)에 자리를 내준다
MAX_PER_CLAUSE = 2    # 같은 조항(clause_no)의 청크 상한 — 긴 조항이 여러 청크로 쪼개져 한 섹션을 독점하는 것 방지
MIN_PER_SECTION = 3   # 전 섹션 중복 배제로 이보다 적어지면 중복을 허용해 보충

# ISO 방법론 근거가 '정당히 필요한' 섹션만 RAG 검색한다.
#   결론·요약은 결과 요약이 역할이라 ISO 조항 인용이 불필요하고, 받으면 'ISO 6.3.5 요건이
#   평가되었다' 식 준수단정을 유발한다(프롬프트로 못 막힘 — e2e #5 확인). 줄 ISO가 없으면
#   준수단정 자체가 불가 → 구조적 차단(프롬프트보다 구조 우선).
#   governance는 데이터 품질(6.3.5)·1차 데이터(3.1.6.1)·투명성(5.11) 등 관련 조항이
#   실재하므로 검색 대상에 포함한다(worker 규칙 4가 '요구 설명용' 인용만 허용).
RAG_SECTIONS = {"lci", "lcia", "interpretation", "governance"}


def _queries(sp) -> list[str]:
    """섹션 기획을 '목적 1건 + 포함항목별 1건'의 짧은 질의 여러 개로 쪼갠다.
    bge-m3 다국어라 한글 질의 OK. 짧고 초점 있는 질의가 방법론 조항에 더 잘 맞는다."""
    qs = [f"{sp.title} {sp.goal}"]
    qs += [f"{sp.title} {mc}" for mc in sp.must_cover]
    return qs


def _interleave(result_lists) -> list:
    """질의별 결과를 rank 순서로 번갈아 합친다(각 질의의 상위 결과가 골고루 앞에 오게).
    id로 dedup."""
    out, seen = [], set()
    width = max((len(rl) for rl in result_lists), default=0)
    for rank in range(width):
        for rl in result_lists:
            if rank < len(rl) and rl[rank]["id"] not in seen:
                seen.add(rl[rank]["id"])
                out.append(rl[rank])
    return out


def _is_definition(it: dict) -> bool:
    """3장(용어와 정의) 조항인가 — ISO 14067/14044 모두 3장이 정의부."""
    return str(it.get("clause_no", "")).startswith("3.")


def _select(candidates, used_ids) -> list:
    """후보에서 본문 청크 K개를 선별한다.
      - 앞 섹션이 이미 가져간 청크 배제(섹션 간 중복 → 프롬프트 낭비·근거 편중)
      - 정의 조항은 MAX_DEFINITIONS까지만(정의 재낭독 대신 방법론 조항 우선)
      - 같은 조항의 청크는 MAX_PER_CLAUSE까지만(긴 조항의 섹션 독점 방지)
      - 배제가 과해 MIN_PER_SECTION 미만이면 중복 허용으로 보충(빈 근거 방지)"""
    mains = [it for it in candidates if not it.get("linked")]
    picked, defs, per_clause = [], 0, {}

    def _admit(it, allow_used):
        nonlocal defs
        if it["id"] in {p["id"] for p in picked}:
            return False
        if not allow_used and it["id"] in used_ids:
            return False
        cl = str(it.get("clause_no", ""))
        if cl and per_clause.get(cl, 0) >= MAX_PER_CLAUSE:
            return False
        if _is_definition(it):
            if defs >= MAX_DEFINITIONS:
                return False
            defs += 1
        if cl:
            per_clause[cl] = per_clause.get(cl, 0) + 1
        picked.append(it)
        return True

    for it in mains:
        if len(picked) >= K_PER_SECTION:
            break
        _admit(it, allow_used=False)
    if len(picked) < MIN_PER_SECTION:       # 중복 배제 완화 보충
        for it in mains:
            if len(picked) >= MIN_PER_SECTION:
                break
            _admit(it, allow_used=True)
    return picked


def _attach_assets(picked, candidates) -> list:
    """선별된 청크가 refs로 가리키는 표/그림 에셋만 뒤에 붙인다(선별 수에 미포함)."""
    linked_by_id = {it["id"]: it for it in candidates if it.get("linked")}
    have = {it["id"] for it in picked}
    out = list(picked)
    for it in picked:
        for rid in it.get("refs", []):
            if rid in linked_by_id and rid not in have:
                have.add(rid)
                out.append(linked_by_id[rid])
    return out


def _fmt(it: dict) -> str:
    """근거 1건을 인용하기 좋은 문자열로. (worker가 출처 표기에 사용)"""
    tag = it.get("clause_no") or it.get("type") or ""
    head = f"[{it.get('source','')} {tag}]".strip()
    return f"{head} {it['text']}".strip()


def retrieve(state):
    """메인만 호출. 섹션별로 근거를 검색해 evidence[section_id]에 인덱싱."""
    outline = state["outline"]
    evidence, used_ids = {}, set()
    for sp in outline.sections:
        if sp.id not in RAG_SECTIONS:       # 결론·요약 등은 ISO 조항 안 줌(준수단정 차단)
            evidence[sp.id] = []
            continue
        results = [search(q, k=K_PER_QUERY) for q in _queries(sp)]
        candidates = _interleave(results)
        picked = _select(candidates, used_ids)
        used_ids |= {it["id"] for it in picked}
        evidence[sp.id] = [_fmt(it) for it in _attach_assets(picked, candidates)]
    return {"evidence": evidence}
