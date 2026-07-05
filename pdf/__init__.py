"""
pdf — PDF 산출 패키지 (격리된 교체 지점)

외부에는 md_to_pdf() 하나만 노출한다. PDF 엔진/스타일을 바꿔야 하면
이 패키지 안(to_pdf.py + report.css)만 수정하면 되고, node/render.py는 안 건드린다.
"""

from .to_pdf import embed_datapack, md_to_pdf

__all__ = ["md_to_pdf", "embed_datapack"]
