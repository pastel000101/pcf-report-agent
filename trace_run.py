"""
trace_run.py — 파이프라인 전 구간 타임라인 트레이서 [디버깅/검사용, LLM ✗ 오케스트레이션]

graph를 스트리밍 실행하면서 (1) 각 노드의 출력 (2) 모든 LLM 호출의 SYSTEM/HUMAN 입력과
AI 응답(텍스트·구조화 출력) (3) RAG 검색 문서를 시간순으로 잡아 하나의 md로 떨군다.

실행: .venv/Scripts/python.exe trace_run.py [report_id]
출력: output/run_trace_YYYYmmdd_HHMMSS.md
"""

import json
import sys
import time
import datetime

from langchain_core.callbacks import BaseCallbackHandler

from graph import build_graph

events = []      # 타임라인 이벤트(노드 완료 + LLM 호출)
_pending = {}    # run_id → LLM 시작정보(종료 시 합침)


def _content_str(m):
    c = getattr(m, "content", m)
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        out = []
        for b in c:
            if isinstance(b, dict):
                out.append(b.get("text") or json.dumps(b, ensure_ascii=False))
            else:
                out.append(str(b))
        return "\n".join(out)
    return str(c)


class Trace(BaseCallbackHandler):
    """모든 chat model 호출의 입력 메시지와 응답을 노드 이름과 함께 잡는다."""

    def on_chat_model_start(self, serialized, messages, *, run_id,
                            parent_run_id=None, tags=None, metadata=None, **kw):
        node = (metadata or {}).get("langgraph_node", "?")
        msgs = messages[0] if messages else []
        _pending[str(run_id)] = {
            "t": time.time(), "kind": "llm", "node": node,
            "input": [{"role": getattr(m, "type", "?"), "content": _content_str(m)} for m in msgs],
        }

    def on_llm_end(self, response, *, run_id, **kw):
        rec = _pending.pop(str(run_id), {"t": time.time(), "kind": "llm", "node": "?", "input": []})
        try:
            gen = response.generations[0][0]
            msg = getattr(gen, "message", None)
            rec["output_text"] = gen.text or ""
            rec["output_tools"] = list(getattr(msg, "tool_calls", None) or [])
        except Exception as e:
            rec["output_text"] = f"<응답 파싱 실패: {e}>"
            rec["output_tools"] = []
        try:
            rec["usage"] = (response.llm_output or {}).get("usage")
        except Exception:
            rec["usage"] = None
        events.append(rec)

    def on_llm_error(self, error, *, run_id, **kw):
        rec = _pending.pop(str(run_id), {"t": time.time(), "kind": "llm", "node": "?", "input": []})
        rec["error"] = str(error)
        events.append(rec)


def _summarize(delta: dict):
    """노드가 반환한 상태 변경분(delta)을 사람이 읽을 요약 줄로."""
    lines = []
    for k, v in delta.items():
        try:
            if k == "data_pack":
                r = v.result
                lines.append(f"data_pack(DataPack): final_pcf={r.final_pcf}, total={r.total_tco2eq}, "
                             f"scope12/3={r.scope12_ratio}/{r.scope3_ratio}, boundary='{v.meta.system_boundary}'")
                lines.append(f"  materials={len(v.materials)}, emission_lines={len(v.emission_lines)}, "
                             f"logistics={len(v.logistics)}, breakdown={len(v.breakdown)}, audit_log={len(v.audit_log)}, "
                             f"sensitivity={len(v.sensitivity)}")
            elif k == "outline":
                lines.append("outline(Outline): " + " | ".join(f"{s.id}:{s.title}" for s in v.sections))
            elif k == "evidence":
                lines.append("evidence(RAG 검색 문서):")
                for sid, docs in v.items():
                    lines.append(f"  [{sid}] {len(docs)}건")
                    for d in docs:
                        lines.append(f"    - {d}")
            elif k == "packages":
                lines.append("packages(WorkerPackage ×N): " + ", ".join(p.section_id for p in v))
                for p in v:
                    lines.append(f"  [{p.section_id}] facts {len(p.facts)}건, 근거 {len(p.evidence_slice)}건")
                    for fct in p.facts:
                        lines.append(f"    - {fct}")
            elif k == "drafts":
                for d in v:
                    lines.append(f"draft[{d.id}] '{d.title}' numbers_used={d.numbers_used}")
                    lines.append(f"  citations={d.citations}")
                    lines.append(f"  narrative: {d.narrative}")
            elif k == "draft_md":
                lines.append(f"draft_md(Markdown): {len(v)}자")
            elif k == "verification":
                lines.append(f"verification: passed={v.passed}, failed_sections={v.failed_sections}, rewrite")
                for i in v.issues:
                    lines.append(f"  issue[{i.section_id}] {i.kind}: {i.detail}")
            elif k == "editorial":
                lines.append(f"editorial: passed={v.passed}")
                for i in getattr(v, "issues", []):
                    lines.append(f"  issue[{i.section_id}] {i.kind}: {i.detail}")
            elif k in ("rewrite_count", "editorial_rounds", "approved", "output_path"):
                lines.append(f"{k}: {v}")
            else:
                s = str(v)
                lines.append(f"{k}: {s[:400]}{'…' if len(s) > 400 else ''}")
        except Exception as e:
            lines.append(f"{k}: <{type(v).__name__}> (요약 실패: {e})")
    return lines


def main():
    report_id = int(sys.argv[1]) if len(sys.argv) > 1 else 101
    # 진입점에서 report_name을 확정(타임스탬프 포함) → render가 이 이름 1벌로 저장, 매 실행 겹침 없음.
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_name = f"{report_id}_{ts}"
    init_state = {"report_id": report_id, "report_name": report_name}

    graph = build_graph()
    cfg = {"callbacks": [Trace()], "recursion_limit": 100}

    for chunk in graph.stream(init_state, stream_mode="updates", config=cfg):
        for node, delta in chunk.items():
            if not isinstance(delta, dict):
                continue
            events.append({"t": time.time(), "kind": "node", "node": node,
                           "delta_lines": _summarize(delta)})

    events.sort(key=lambda e: e["t"])

    ts = datetime.datetime.now()
    out = []
    out.append(f"# 실행 트레이스 (timeline)\n")
    out.append(f"> 생성: {ts:%Y-%m-%d %H:%M:%S} · report_id={report_id} · payload는 없으면 sample_payload.json 폴백\n")
    out.append("> 각 노드의 입력 = 이전 노드들이 누적한 상태. LLM 노드는 HUMAN/SYSTEM(입력)과 AI(응답)를 그대로 담음.\n")
    out.append(f"\n## 초기 입력\n\n```\n{json.dumps(init_state, ensure_ascii=False)}\n```\n")
    out.append("\n## 타임라인\n")

    t0 = events[0]["t"] if events else time.time()
    step = 0
    for e in events:
        step += 1
        rel = e["t"] - t0
        if e["kind"] == "llm":
            out.append(f"\n### [{step:02d}] +{rel:6.1f}s · 🤖 LLM 호출 — 노드 `{e['node']}`\n")
            for m in e["input"]:
                out.append(f"<details><summary><b>{m['role'].upper()} (입력)</b></summary>\n\n```\n{m['content']}\n```\n</details>\n")
            if e.get("error"):
                out.append(f"\n**⚠️ LLM 오류:** {e['error']}\n")
            else:
                if (e.get("output_text") or "").strip():
                    out.append(f"\n**AI 응답 (텍스트):**\n\n```\n{e['output_text']}\n```\n")
                for tc in e.get("output_tools") or []:
                    args = json.dumps(tc.get("args"), ensure_ascii=False, indent=2)
                    out.append(f"\n**AI 응답 (구조화 출력 → `{tc.get('name')}`):**\n\n```json\n{args}\n```\n")
                if e.get("usage"):
                    out.append(f"\n_token usage: {e['usage']}_\n")
        else:
            out.append(f"\n### [{step:02d}] +{rel:6.1f}s · 📦 노드 완료 — `{e['node']}`\n")
            body = "\n".join(e["delta_lines"])
            out.append(f"\n```\n{body}\n```\n")

    # 최종 산출물 경로(있으면)
    final_path = next((e for e in reversed(events)
                       if e["kind"] == "node" and e["node"] == "render"), None)

    import os
    from pathlib import Path
    
    ts_name = ts.strftime("%Y%m%d_%H%M%S")
    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"run_trace_{ts_name}.md"
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("TRACE_WRITTEN:", out_path)
    print("EVENTS:", len(events))


if __name__ == "__main__":
    main()
