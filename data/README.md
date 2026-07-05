# data/ — RAG 코퍼스 준비 안내

이 폴더에는 원래 ISO 표준 문서(Markdown 변환본)가 들어갑니다.
**ISO 표준은 저작권 보호 대상 유료 문서라 이 저장소에는 포함하지 않습니다.**

## 실행에 필요한 파일

| 파일 | 내용 |
|---|---|
| `ISO14067.md` | ISO 14067:2018 전문 Markdown 변환본 |
| `ISO-14044-2006.md` | ISO 14044:2006 전문 Markdown 변환본 |

정식 구매처(ISO Store, 한국표준협회 등)에서 문서를 확보한 뒤 Markdown으로 변환해 위 파일명으로 배치하세요.

## 인덱스 구축

파일 배치 후 임베딩 인덱스(ChromaDB)를 생성합니다 (Ollama + `bge-m3` 모델 필요):

```bash
python rag/ingest_iso_14067.py
python rag/ingest_iso14044.py
```

생성된 `rag/chroma_db/`는 커밋하지 않습니다(.gitignore 처리).
