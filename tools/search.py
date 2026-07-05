"""
search.py — Chroma 문서 검색 '도구'(tool) [tools/ : bind_tools 대상]

역할:
  rag/retriever.py의 검색을 LLM이 직접 호출할 수 있는 도구로 노출한다.
  (llm_model.py의 tools 인자 → bind_tools로 전달)
  여기는 얇은 래퍼일 뿐, 실제 검색 로직은 rag.retriever에 있다.

입력 → 출력:
  query(str) → 관련 근거 텍스트(LLM이 읽기 좋은 형태로 직렬화)

의존: rag.retriever.search

구현 메모:
  - LangChain @tool 데코레이터로 정의하면 bind_tools에 바로 넘길 수 있다.
  - docstring이 곧 LLM에게 보이는 '도구 설명'이 되므로 명확히 적는다.

주의(설계):
  - 원칙상 RAG는 메인(node/retrieve.py)이 호출한다. 이 도구를 worker 등 서브 LLM에
    bind하면 '서브가 직접 검색'하게 되어 비용·중복이 생길 수 있다.
    → 어느 역할 LLM에 bind할지(기획만? 검증만?) 의식적으로 정할 것.
"""

# from langchain_core.tools import tool
# from rag.retriever import search as _search


# @tool
# def doc_search(query: str) -> str:
#     """ISO 14044/14067 등 규제·방법론 문서에서 질의와 관련된 근거를 찾는다."""
#     ...  # TODO: _search(query) 호출 → 결과를 문자열로 정리해 반환
