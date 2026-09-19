from dotenv import load_dotenv
import os

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage

load_dotenv()


def system_message(text: str) -> SystemMessage:
    """시스템 프롬프트 텍스트를 SystemMessage로 만든다.

    ※ 모든 역할(worker/verify/edit/editorial)이 이 함수 하나만 거친다 — 백엔드별로
      시스템 프롬프트를 다르게 처리해야 하면(예: 프롬프트 캐시 지시) 여기만 고치면 된다.
      Ollama에는 프롬프트 캐시를 명시적으로 제어하는 API가 없어 지금은 평문으로 감싼다.
    """
    return SystemMessage(content=text)

# 역할별 LLM 함수 — 편집/검증은 저온(결정적), 서브 서술은 중온(자연스러움).
# 설정 가능한 .env 키는 .env.example 참조.


def _build(role: str, default_temp: float, tools=None, default_predict: int = 768):
    """역할 이름으로 .env에서 모델·온도를 읽어 ChatOllama를 만든다.

    tools가 주어지면 bind_tools로 묶어서 돌려준다.
    default_predict는 역할별 출력 토큰 상한의 기본값 — 한 번에 내보내는 분량이 역할마다
    다르므로(worker=1개 섹션, edit=6개 섹션 전부) 같은 값을 쓰면 안 된다.
    """
    load_dotenv(override=True)  # .env 수정 후 서버 재시작 없이도 다음 호출부터 반영되게

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv(f"LLM_{role}_MODEL") or os.getenv("OLLAMA_GENERATION_MODEL", "gemma4:12b-it-qat")
    temp = os.getenv(f"LLM_{role}_TEMP")
    temperature = float(temp) if temp is not None else default_temp
    # 출력 토큰 상한. 역할별 기본값이 다르다 — EDIT는 6개 섹션 서술을 한 응답에 담으므로
    # 작게 두면 편집 출력이 잘리고, 그때 생성 중이던 섹션만 문장 중간에서 끊긴 채 남는다.
    num_predict = int(os.getenv(f"LLM_{role}_MAX_TOKENS")
                      or os.getenv(f"OLLAMA_NUM_PREDICT_{role}")
                      or default_predict)
    # 컨텍스트 길이. Ollama 기본 4096으로는 worker 프롬프트(규칙+facts+ISO 근거 12청크)가
    # 넘쳐 '앞부분'인 시스템 규칙부터 조용히 잘리고 규칙 위반 서술이 새어 나온다.
    num_ctx = int(os.getenv(f"LLM_{role}_NUM_CTX") or os.getenv("OLLAMA_NUM_CTX", "16384"))
    # langchain-ollama는 미설정 시 null을 보내 Ollama 기본 페널티가 꺼진다 → 소형 모델이
    # JSON 생성 중 같은 어절을 무한 반복하다 상한을 소진해 필수 필드가 잘린다. 명시 필수.
    repeat_penalty = float(os.getenv(f"LLM_{role}_REPEAT_PENALTY") or os.getenv("OLLAMA_REPEAT_PENALTY", "1.1"))
    # thinking 끄기. 사고 과정이 출력 상한을 다 소진하면 content가 빈 문자열로 와
    # 구조화 출력 파싱이 실패한다. 빈 값·auto면 미전송(모델 기본).
    think_env = (os.getenv(f"LLM_{role}_THINK") or os.getenv("OLLAMA_THINK", "false")).strip().lower()
    reasoning = None if think_env in ("", "auto", "none") else think_env in ("1", "true", "yes", "on")

    # 어떤 모델·설정으로 나가는지 터미널에서 바로 확인할 수 있게 로그.
    print(f"[llm_model] role={role} model={model} base_url={base_url} temperature={temperature} num_predict={num_predict} num_ctx={num_ctx} repeat_penalty={repeat_penalty} reasoning={reasoning}")

    llm = ChatOllama(model=model, base_url=base_url, temperature=temperature, num_predict=num_predict, num_ctx=num_ctx, repeat_penalty=repeat_penalty, reasoning=reasoning)
    if tools:
        return llm.bind_tools(tools)
    return llm


def edit_llm():
    """편집(assemble 조립·편집) — 저온. 6개 섹션 서술을 한 응답에 담으므로 출력 상한을 크게."""
    tools = []
    return _build("EDIT", 0.2, tools, default_predict=6144)


def verify_llm():
    """검증 grader — 결정성 위해 온도 0."""
    tools = []
    return _build("VERIFY", 0.0, tools)


def worker_llm():
    """서브 서술(단락 작성) — 중온."""
    tools = []
    return _build("WORKER", 0.4, tools)
