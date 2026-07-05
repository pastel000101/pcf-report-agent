from dotenv import load_dotenv
import os

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage

load_dotenv()


def cached_system(text: str) -> SystemMessage:
    """시스템 프롬프트에 Anthropic prompt cache(ephemeral, 5분 TTL)를 건다.

    worker가 같은 시스템 프롬프트로 13회+ 호출되므로, 캐시가 붙으면 입력 토큰
    비용이 크게 준다(캐시 읽기 ≈ 0.1배). 확인은 트레이스의 usage에서
    cache_read_input_tokens > 0 인지로 한다.
    ※ 모델별 '최소 캐시 길이' 미만이면 조용히 캐시가 안 된다(에러 없음) —
      Haiku 4.5는 4096토큰이라 짧은 프롬프트는 캐시가 안 붙을 수 있고,
      Sonnet 계열(1024~2048토큰)로 바꾸면 그대로 활성화된다.
    ※ 실측(2026-07, count_tokens): WORKER≈2.5K / EDIT≈0.8K / VERIFY≈1.5K / EDITORIAL≈2.4K
      → 현재 Haiku 4.5에선 전 역할 캐시 미적용(비용 소액이라 수용). 살리려면
      (a) 섹션별 Few-shot을 시스템 프롬프트 뒤에 붙여 4096을 넘기거나 (b) Sonnet 계열로 전환.
    """
    return SystemMessage(content=[
        {"type": "text", "text": text, "cache_control": {"type": "ephemeral"}},
    ])

# ---------------------------------------------------------------------------
# 역할별 LLM 함수
# 역할마다 따로 함수를 둔다. 각 함수는 자기 몫의 모델·온도를 .env에서 읽고,
# 필요하면 도구(tools)를 바인딩해서 돌려준다.
# 편집/검증 = 저온(결정적), 서브 서술 = 중온(자연스러움).
#
# .env 키 규칙 (없으면 기본 모델(Haiku)·아래 기본 온도로 폴백):
#   LLM_EDIT_MODEL   / LLM_EDIT_TEMP
#   LLM_VERIFY_MODEL / LLM_VERIFY_TEMP
#   LLM_WORKER_MODEL / LLM_WORKER_TEMP
# ---------------------------------------------------------------------------


def _build(role: str, default_temp: float, tools=None):
    """역할 이름으로 .env에서 모델·온도를 읽어 ChatAnthropic을 만든다.

    tools가 주어지면 bind_tools로 묶어서 돌려준다.
    """
    model =os.getenv(f"LLM_{role}_MODEL") or "claude-haiku-4-5-20251001"
    temp = os.getenv(f"LLM_{role}_TEMP")
    temperature = float(temp) if temp is not None else default_temp

    if tools:
        return ChatAnthropic(model_name=model, temperature=temperature).bind_tools(tools)
    return ChatAnthropic(model_name=model, temperature=temperature)


def edit_llm():
    """편집(assemble 조립·편집) — 저온."""
    tools = []
    return _build("EDIT", 0.2, tools)


def verify_llm():
    """검증 grader — 결정성 위해 온도 0."""
    tools = []
    return _build("VERIFY", 0.0, tools)


def worker_llm():
    """서브 서술(단락 작성) — 중온."""
    tools = []
    return _build("WORKER", 0.4, tools)