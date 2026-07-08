import os
from pathlib import Path
from typing import Dict, Any

# =====================================================================
# [1] 시스템 기본 경로 설정 (Path Configuration)
# =====================================================================
BASE_DIR: Path = Path(__file__).resolve().parent

# 1. data 폴더 경로 지정
DATA_DIR: str = os.path.join(str(BASE_DIR), "data")

# 2. [자동 검색 알고리즘] data 폴더 내에서 첫 번째로 발견되는 PDF 파일 자동 바인딩
INPUT_PDF_PATH: str = None
if os.path.exists(DATA_DIR):
    pdf_files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith('.pdf')]
    if pdf_files:
        # 가장 첫 번째 PDF 파일의 절대 경로를 자동으로 완성
        INPUT_PDF_PATH = os.path.join(DATA_DIR, pdf_files[0])

# 만약 PDF가 발견되지 않았다면 기본값 지정 (안전장치)
if not INPUT_PDF_PATH:
    INPUT_PDF_PATH = os.path.join(DATA_DIR, "information_textbook.pdf")

# 물리적 파티셔닝 데이터가 저장될 루트 폴더 경로
DATA_STORAGE_DIR: str = os.path.join(str(BASE_DIR), "textbook_data")

# 이 교과서를 파싱해서 저장할 타깃 디렉토리 이름
TARGET_TEXTBOOK_NAME: str = "high_school_information"


# =====================================================================
# [2] 동적 모델 탐색 하이퍼파라미터 (이하 생략 - 기존 코드 그대로 유지)
# =====================================================================
MODEL_SEARCH_KEYWORD: str = "flash"
EMBEDDING_SEARCH_KEYWORD: str = "embedding"
FALLBACK_KEYWORD_PRIORITY: list[str] = ["pro", "flash", "1.5-flash"]
SEARCH_TOP_K: int = 2
EXAM_AGENT_SYSTEM_PROMPT: str = (
    "너는 고등학교 정보 과목의 공정한 평가를 담당하는 출제위원 교사이다...\n"
)