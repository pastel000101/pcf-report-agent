"""
graph.py — 그래프 빌더 [그룹 5 / LLM ✗ 배선만]

역할:
  node 함수들을 엣지로 연결해 실행 가능한 파이프라인으로 컴파일한다.

노드는 딕셔너리(nodes)로 관리하고 루프로 add_node 한다.
팬아웃(Send)·재작성 루프·편집장 자기수정 루프는 조건부 엣지로 배선돼 있다.

주의:
  - 사람 검토(review) 직전 interrupt + checkpointer는 HITL 단계에서 추가.
"""

from langgraph.graph import StateGraph, START, END

from state.state import ReportState
from support.routes import fan_out_workers, route_after_verify, route_after_editorial, route_after_assemble
from node.collect import collect
from node.plan import plan
from node.retrieve import retrieve
from node.dispatch import dispatch
from node.worker import worker
from node.assemble import assemble
from node.verify import verify
from node.editorial import editorial_review
from node.review import review
from node.render import render

def build_graph(checkpointer=None):
  # 노드 정의를 딕셔너리로 관리 (이름 → 함수)
  nodes = {
      "collect": collect,      # payload → DataPack (숫자의 출처)
      "plan": plan,            # DataPack+요청 → Outline (LLM)
      "retrieve": retrieve,    # Outline → 주제별 근거 (RAG, 메인만)
      "dispatch": dispatch,    # DataPack+근거 → WorkerPackage ×N
      "worker": worker,        # WorkerPackage → SectionDraft (LLM, Send 팬아웃)
      "assemble": assemble,    # drafts+DataPack → Markdown 초안 (편집 LLM + 슬롯 코드)
      "verify": verify,        # 숫자대조(코드)+grader(LLM) → Verification
      "editorial": editorial_review,  # 편집장 AI: 완결성·흐름·가독성 (verify와 다른 층)
      "review": review,        # 얇은 최종 승인(설정형, 기본 자동)
      "render": render,        # Markdown 파일 저장
  }
  
  builder = StateGraph(ReportState)

  # 노드 추가
  for node_name, node_func in nodes.items():
      builder.add_node(node_name, node_func)

  # --- 엣지 배선 ---
  builder.add_edge(START, "collect")
  builder.add_edge("collect", "plan")
  builder.add_edge("plan", "retrieve")
  builder.add_edge("retrieve", "dispatch")
  # ★ 팬아웃: dispatch가 만든 packages 수만큼 worker를 병렬 실행 (Send)
  builder.add_conditional_edges("dispatch", fan_out_workers, ["worker"])
  # 순서: worker → verify → assemble → editorial
  #   조립(무거운 edit_llm) '전에' 숫자 검증 → worker↔verify로 가볍게 숫자를 다 맞춘 뒤
  #   assemble을 마지막에 1회만 실행(재작성마다 재조립하던 토큰 낭비 제거).
  #   ※ verify는 어느 순서든 같은 drafts를 보므로 검증 정확도엔 영향 없음(순수 효율 개선).
  builder.add_edge("worker", "verify")        # 모든 worker 완료 후 verify로 합류
  # ★ 숫자 재작성 루프: 통과/상한→assemble / 실패→실패 섹션만 worker 재작성
  builder.add_conditional_edges("verify", route_after_verify, ["worker", "assemble"])
  # ★ 조립 후: 평가 라운드가 남았으면 editorial, 상한 소진이면 review 직행
  #   (상한 도달 후의 editorial은 결과가 라우팅을 못 바꾸는 죽은 호출 — ~21s/17K토큰 낭비 제거)
  builder.add_conditional_edges("assemble", route_after_assemble, ["editorial", "review"])
  # ★ 편집장 자기수정: 통과/상한→review / content→worker 재작성 / flow→assemble 재편집
  builder.add_conditional_edges("editorial", route_after_editorial, ["worker", "assemble", "review"])
  builder.add_edge("review", "render")        # TODO: 반려 시 plan으로 되돌리는 분기
  builder.add_edge("render", END)

  # TODO: HITL 단계에서 → compile(checkpointer=..., interrupt_before=["review"])
  return builder.compile(checkpointer=checkpointer)


if __name__ == "__main__":
  graph = build_graph()
  result = graph.invoke({"report_id": 101})   # payload 없으면 collect가 샘플 폴백
  print("최종 상태 키:", list(result.keys()))
  print("final_pcf  :", result["data_pack"].result.final_pcf)
