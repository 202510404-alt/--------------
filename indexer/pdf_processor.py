import os
import pypdf  # 📦 로컬 텍스트 추출용 라이브러리
from typing import List, Dict, Any
from google import genai
import config

class TextbookIndexer:
    """교과서 PDF를 로컬 자원으로 페이지별 파싱하고, 
    오직 순수 마크다운(.md) 텍스트 데이터셋만 초고속으로 파티셔닝 보존하는 최적화 클래스."""

    def __init__(self, textbook_name: str, output_dir: str = None):
        """
        Args:
            textbook_name (str): 데이터 분리 보관을 위한 교과서 식별 디렉토리명.
            output_dir (str): 물리적 파일이 저장될 루트 디렉토리 경로.
        """
        self.client = genai.Client()
        self.textbook_name = textbook_name
        self.output_root = output_dir or config.DATA_STORAGE_DIR
        
        # 실제 데이터가 저장될 물리 폴더 생성
        self.textbook_dir = os.path.join(self.output_root, self.textbook_name)
        os.makedirs(self.textbook_dir, exist_ok=True)

        # 🔍 [수정] 무겁고 에러가 잦던 임베딩 모델 동적 탐색을 완전히 제거하고 문제 생성용 생성 모델만 동적 매핑
        print("🔍 [시스템 체크] 구글 서버에서 실시간 가용 생성 모델 목록 매핑 중...")
        self.generation_model = self._discover_model(keyword="flash", action="generateContent")
        
        print(f"🤖 매핑된 최신 생성 모델: [{self.generation_model}] (임베딩 엔진 비활성화 완료)")

    def _discover_model(self, keyword: str, action: str) -> str:
        """구글 공식 라이브러리 목록을 실시간으로 긁어와 조건에 맞는 최신 가용 모델을 탐색합니다."""
        try:
            model_list = self.client.models.list()
            for m in model_list:
                if action in m.supported_actions:
                    clean_name = m.name.replace("models/", "")
                    if keyword.lower() in clean_name.lower():
                        return clean_name
            return "gemini-2.5-flash"
        except Exception as e:
            print(f"⚠️ 모델 동적 탐색 중 오류 발생, 기본값 전환: {e}")
            return "gemini-2.5-flash"

    def extract_page_contents(self, pdf_path: str) -> List[Dict[str, Any]]:
        """pypdf를 활용하여 로컬에서 페이지 단위로 텍스트를 안전하게 추출합니다. (100% 로컬 오프라인 작동)"""
        if not os.path.exists(pdf_path):
            print(f"❌ 원본 PDF 파일을 찾을 수 없습니다: {pdf_path}")
            return []

        reader = pypdf.PdfReader(pdf_path)
        parsed_pages = []

        for idx, page in enumerate(reader.pages):
            page_num = idx + 1
            try:
                raw_text = page.extract_text()
            except Exception as e:
                print(f"⚠️ {page_num}p 로컬 텍스트 추출 실패 우회: {e}")
                raw_text = ""

            if not raw_text or not raw_text.strip():
                raw_text = f"High School Textbook Data - Page {page_num}\n[이 페이지는 이미지 위주의 구간입니다.]"

            parsed_pages.append({
                "page_num": page_num,
                "raw_text": raw_text.strip()
            })
        
        return parsed_pages

    # ✂️ [수정] 기존 generate_page_embedding 함수 통째로 삭제 처리 완료

    def save_partitioned_data(self, page_num: int, text: str) -> None:
        """[수정] 인자에서 embedding 벡터를 제거하고, 오직 웹 컨텍스트 소스인 .md 파일만 1:1 저장합니다. (json 관련 로직 전면 제거)"""
        md_path = os.path.join(self.textbook_dir, f"page_{page_num:03d}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"--- PAGE_{page_num} ---\n{text}")

    def execute_full_indexing(self, pdf_path: str) -> None:
        """[수정] API 비용 및 타임아웃 걱정 없는 100% 로컬 초고속 전처리 파이프라인 가동"""
        # 🧹 기존 생성된 파일들이 있다면 인덱싱 시작 전에 깨끗하게 비우기
        if os.path.exists(self.textbook_dir) and os.listdir(self.textbook_dir):
            print(f"🧹 [{self.textbook_name}] 폴더에 기존 데이터가 감지되어 폴더를 초기화(비우기)합니다...")
            for file_name in os.listdir(self.textbook_dir):
                file_path = os.path.join(self.textbook_dir, file_name)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f"⚠️ 파일 삭제 중 오류 발생 ({file_name}): {e}")
            print("✨ 기존 파일 삭제 완료! 새로 인덱싱을 시작합니다.")
        else:
            print(f"📁 [{self.textbook_name}] 새로운 저장 공간을 준비했습니다.")

        print(f"⚙️ [초고속 로컬 전처리] 외부 API 프리 모드로 전 과정 오프라인 인덱싱 가동 중...")
        
        # 1. 로컬 파싱 단계 (pypdf 이용)
        pages_content = self.extract_page_contents(pdf_path)
        total_pages = len(pages_content)
        print(f"📄 총 {total_pages} 페이지 로컬 파싱 완료. 대기 없이 즉시 마크다운 데이터셋 생성을 시작합니다.")

        generated_count = 0

        # 2. 루프를 돌며 외부 통신 단계 없이 다이렉트로 로컬 저장 처리
        for item in pages_content:
            page_num = item["page_num"]
            text_data = item["raw_text"]

            # [수정] 무겁던 외부 통신 단계를 삭제하고 즉시 로컬 디스크에 마크다운 파일로 정렬
            self.save_partitioned_data(page_num, text_data)
            
            generated_count += 1

            if page_num % 50 == 0 or page_num == total_pages:
                print(f"⏳ 데이터베이스 마크다운 정렬 중... ({page_num}/{total_pages} 페이지 완료)")

        print(f"✅ [{self.textbook_name}] 마크다운 데이터베이스 빌드 100% 완료! (총 {generated_count}개 텍스트 소스 확보)")