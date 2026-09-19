from dotenv import load_dotenv
import os

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage

load_dotenv()


def cached_system(text: str) -> SystemMessage:
    """시스템 프롬프트 메시지를 만든다.

    ※ 이름이 'cached_'인 것은 프롬프트 캐시를 거는 자리로 뒀기 때문이다. Ollama에는
      프롬프트 캐시를 명시적으로 제어하는 API가 없어 지금은 일반 SystemMessage를 만든다.
      모든 역할이 이 함수 하나만 거치므로, 캐시를 지원하는 백엔드로 바꿀 때 여기만 고치면 된다.
    """
    return SystemMessage(content=text)

# ---------------------------------------------------------------------------
# 역할별 LLM 함수
# 역할마다 따로 함수를 둔다. 각 함수는 자기 몫의 모델·온도를 .env에서 읽고,
# 필요하면 도구(tools)를 바인딩해서 돌려준다.
# 편집/검증 = 저온(결정적), 서브 서술 = 중온(자연스러움).
#
# .env 키 규칙 (없으면 OLLAMA_GENERATION_MODEL·아래 기본 온도로 폴백):
#   LLM_EDIT_MODEL   / LLM_EDIT_TEMP
#   LLM_VERIFY_MODEL / LLM_VERIFY_TEMP
#   LLM_WORKER_MODEL / LLM_WORKER_TEMP
#   OLLAMA_BASE_URL  (기본 http://localhost:11434, Docker Desktop이 호스트로 포트를 열어줌)
#   OLLAMA_GENERATION_MODEL (역할별 모델을 따로 안 정했을 때의 공통 기본값)
#   LLM_{role}_NUM_CTX / OLLAMA_NUM_CTX (컨텍스트 길이, 기본 16384 — 메모리 부족 시 낮출 것)
#   LLM_{role}_REPEAT_PENALTY / OLLAMA_REPEAT_PENALTY (반복 페널티, 기본 1.1 — 반복 루프 방지)
#   LLM_{role}_THINK / OLLAMA_THINK (thinking 모델 사고 과정, 기본 false — auto면 모델 기본)
#
# ※ 모델/URL을 모듈 임포트 시점에 상수로 캐싱하지 않고, _build() 호출 시점마다 os.getenv로
#   다시 읽는다. .env만 고쳐서 서버 재시작 없이 바로 반영하려면 override=True로 재로드까지 한다.
# ---------------------------------------------------------------------------


def _build(role: str, default_temp: float, tools=None):
    """역할 이름으로 .env에서 모델·온도를 읽어 ChatOllama를 만든다.

    tools가 주어지면 bind_tools로 묶어서 돌려준다.
    """
    load_dotenv(override=True)  # .env 수정 후 서버 재시작 없이도 다음 호출부터 반영되게

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv(f"LLM_{role}_MODEL") or os.getenv("OLLAMA_GENERATION_MODEL", "llama3.1")
    temp = os.getenv(f"LLM_{role}_TEMP")
    temperature = float(temp) if temp is not None else default_temp
    # 출력 토큰 상한(num_predict). 없으면 Ollama가 컨텍스트 길이(4096)까지 무한정 생성을
    # 시도할 수 있어 소형/양자화 모델이 반복 루프에 빠지면 요청이 사실상 멈춘 것처럼 보인다.
    num_predict = int(os.getenv(f"LLM_{role}_MAX_TOKENS") or os.getenv("OLLAMA_NUM_PREDICT", "768"))
    # 컨텍스트 길이(num_ctx). 미설정 시 Ollama 기본 4096이 적용되는데, worker 프롬프트
    # (시스템 규칙 + facts + ISO 근거 12청크)가 이를 넘으면 Ollama가 프롬프트 '앞부분'
    # (= 시스템 규칙)부터 조용히 잘라내 규칙 위반 서술이 새어 나온다. 근거 증량과 세트로 확장.
    # 메모리가 부족하면 OLLAMA_NUM_CTX(또는 LLM_{role}_NUM_CTX)로 낮춰 조정.
    num_ctx = int(os.getenv(f"LLM_{role}_NUM_CTX") or os.getenv("OLLAMA_NUM_CTX", "16384"))
    # 반복 페널티. langchain-ollama는 미설정 시 null을 보내 Ollama 기본 페널티(1.1)가 꺼진다 →
    # 소형/양자화 모델(예: gemma4:12b-it-qat)이 structured output(JSON) 생성 중 같은 어절을
    # 무한 반복하다 num_predict를 소진해 필수 필드가 잘리는 실패를 확인(2026-07-12). 명시 설정으로 차단.
    repeat_penalty = float(os.getenv(f"LLM_{role}_REPEAT_PENALTY") or os.getenv("OLLAMA_REPEAT_PENALTY", "1.1"))
    # thinking(사고 과정) 끄기. thinking 모델(gemma4:12b-it-qat 등)은 기본으로 사고를 먼저
    # 생성해 message.thinking으로 보내는데, 복잡한 프롬프트에선 사고가 num_predict를 다 소진해
    # content가 빈 문자열로 와 structured output 파싱이 실패한다(2026-07-12 파이프라인 전멸 원인).
    # 값: true/false = think 명시 전송, 빈 값·auto = 미전송(모델 기본) — 예: OLLAMA_THINK=auto.
    think_env = (os.getenv(f"LLM_{role}_THINK") or os.getenv("OLLAMA_THINK", "false")).strip().lower()
    reasoning = None if think_env in ("", "auto", "none") else think_env in ("1", "true", "yes", "on")

    # 요청 시점에 실제로 어떤 모델·URL로 나가는지 백엔드 터미널에서 바로 확인할 수 있게 로그.
    print(f"[llm_model] role={role} model={model} base_url={base_url} temperature={temperature} num_predict={num_predict} num_ctx={num_ctx} repeat_penalty={repeat_penalty} reasoning={reasoning}")

    llm = ChatOllama(model=model, base_url=base_url, temperature=temperature, num_predict=num_predict, num_ctx=num_ctx, repeat_penalty=repeat_penalty, reasoning=reasoning)
    if tools:
        return llm.bind_tools(tools)
    return llm


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
