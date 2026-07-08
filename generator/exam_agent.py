import os
import json
import time
from typing import List, Dict, Any
from google import genai
from google.genai import types
import config  # 중앙 통제실 설정 파일 로드

class ExamGenerationAgent:
    """지정된 범위의 마크다운 컨텍스트를 연속으로 수집하여 맥락 유실을 차단하고,
    구조화된 JSON 스키마를 강제하여 문제지와 정답지를 물리적으로 분리 저장하는 전문 출제 에이전트."""

    def __init__(self, model_keyword: str = None):
        """
        Args:
            model_keyword (str): 실시간 가용 모델 검색 알고리즘에 활용할 키워드. 
                                 None일 경우 config.MODEL_SEARCH_KEYWORD를 사용.
        """
        self.client = genai.Client()
        self.model_keyword = model_keyword or config.MODEL_SEARCH_KEYWORD
        self.system_prompt = config.EXAM_AGENT_SYSTEM_PROMPT

    def _discover_active_model(self) -> str:
        """구글 라이브러리로 모델 목록을 실시간으로 불러와 최신 가용 생성 모델명을 동적으로 반환합니다."""
        try:
            model_list = self.client.models.list()
            for m in model_list:
                if "generateContent" in m.supported_actions:
                    clean_name = m.name.replace("models/", "")
                    if self.model_keyword.lower() in clean_name.lower():
                        return clean_name
            return "gemini-2.5-flash"
        except Exception as e:
            print(f"⚠️ 에이전트 모델 탐색 중 오류 발생, 기본값 전환: {e}")
            return "gemini-2.5-flash"

    def read_context_range_from_markdown(self, textbook_name: str, start_page: int, end_page: int) -> str:
        """지정된 범위의 마크다운 소스를 안전하게 스트리밍 통합 빌드합니다."""
        textbook_dir = os.path.join(config.DATA_STORAGE_DIR, textbook_name)
        combined_context = []

        print(f"📂 [컨텍스트 빌더] {start_page}p부터 {end_page}p까지의 마크다운 소스 정밀 스캔 중...")
        
        for page in range(start_page, end_page + 1):
            file_path = os.path.join(textbook_dir, f"page_{page:03d}.md")
            
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        combined_context.append(content)
                except Exception as e:
                    print(f"⚠️ [경고] {page}p 파일 로드 실패 (공백 우회): {e}")
            else:
                combined_context.append(f"\n--- PAGE_{page} EMPTY DATA ---\n")

        full_context_str = "\n\n".join(combined_context)
        print(f"✨ 컨텍스트 조립 완료! (총 {len(full_context_str)} 자의 교과서 지문 확보)")
        return full_context_str

    def _get_strict_response_schema(self) -> types.Schema:
        """웹 UI 호환 규격을 위한 엄격한 JSON 스키마를 강제 정의합니다."""
        return types.Schema(
            type=types.Type.OBJECT,
            properties={
                "meta": types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "textbook_name": types.Schema(type=types.Type.STRING),
                        "page_range": types.Schema(type=types.Type.STRING),
                        "total_questions": types.Schema(type=types.Type.INTEGER),
                        "difficulty": types.Schema(type=types.Type.STRING),
                    },
                    required=["textbook_name", "page_range", "total_questions", "difficulty"]
                ),
                "quiz_exam": types.Schema(
                    type=types.Type.ARRAY,
                    description="학생들이 보는 순수 문제지 데이터 (정답 힌트 원천 격리)",
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "id": types.Schema(type=types.Type.INTEGER, description="문제 번호 (1부터 시작)"),
                            "type": types.Schema(type=types.Type.STRING, description="문제 유형 (multiple_choice 고정)"),
                            "question_text": types.Schema(type=types.Type.STRING, description="발문 및 문제 조건 문장"),
                            "options": types.Schema(
                                type=types.Type.ARRAY,
                                items=types.Schema(type=types.Type.STRING),
                                description="4지선다형 보기 리스트"
                            )
                        },
                        required=["id", "type", "question_text", "options"]
                    )
                ),
                "quiz_answer": types.Schema(
                    type=types.Type.ARRAY,
                    description="채점 엔진 및 해설 창에서 사용하는 정답/해설 데이터",
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "id": types.Schema(type=types.Type.INTEGER, description="문제 번호"),
                            "correct_option": types.Schema(type=types.Type.STRING, description="정답 기호"),
                            "correct_text": types.Schema(type=types.Type.STRING, description="정답 보기 텍스트"),
                            "explanation": types.Schema(type=types.Type.STRING, description="상세 해설 문장")
                        },
                        required=["id", "correct_option", "correct_text", "explanation"]
                    )
                )
            },
            required=["meta", "quiz_exam", "quiz_answer"]
        )

    def generate_quiz_pipeline(
        self, 
        textbook_name: str, 
        start_page: int, 
        end_page: int, 
        q_count: int, 
        q_difficulty: str, 
        user_query: str = ""
    ) -> bool:
        """지문 조립, AI 출제 요청, 전용 출력 폴더 분리 저장을 원스톱으로 처리합니다."""
        # 1. 가용 최신 생성 모델 확보
        active_model = self._discover_active_model()
        
        # 2. 마크다운 데이터 연속 수집
        context_data = self.read_context_range_from_markdown(textbook_name, start_page, end_page)
        if not context_data.strip() or len(context_data.replace(f"\n--- PAGE_", "").strip()) < 10:
            print("❌ 지정된 범위 내에 유효한 텍스트 소스가 전무하여 출제를 중단합니다.")
            return False

        # 3. 프롬프트 정밀 빌드
        user_instruction = (
            f"주어진 교과서 본문 콘텍스트만을 근거로 삼아, 외부 지식을 배제한 출제를 수행해라.\n\n"
            f"[출제 조건]\n"
            f"- 대상 단원/범위: {start_page}페이지 ~ {end_page}페이지\n"
            f"- 출제 문제 수: {q_count}문항 (반드시 4지선다형 객관식)\n"
            f"- 난이도 제어 가이드라인: {q_difficulty}\n"
        )
        if user_query and user_query.strip():
            user_instruction += f"- 사용자 추가 맞춤 요구사항: {user_query}\n"
        user_instruction += "\n요청된 JSON 구조 명세(Schema)에 맞추어 완벽한 객체를 반환해라."

        print(f"🤖 [{active_model}] 엔진에게 출제 위임장을 송신 중입니다. 잠시만 기다려주세요...")
        time.sleep(0.4)

        try:
            # 4. Gemini API 호출
            response = self.client.models.generate_content(
                model=active_model,
                contents=[
                    f"[Context]\n{context_data}\n\n",
                    f"[Instruction]\n{user_instruction}"
                ],
                config=types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
                    response_mime_type="application/json",
                    response_schema=self._get_strict_response_schema(),
                    temperature=0.3,
                ),
            )

            # 5. JSON 파싱 및 메타 보완
            raw_json_text = response.text
            full_data = json.loads(raw_json_text)

            full_data["meta"]["textbook_name"] = textbook_name
            full_data["meta"]["page_range"] = f"{start_page}-{end_page}"
            full_data["meta"]["total_questions"] = q_count
            full_data["meta"]["difficulty"] = q_difficulty

           # ⚙️ 6. 문제지 / 답안지 저장 폴더 생성
            exam_dir = os.path.join("questions", textbook_name)
            answer_dir = os.path.join("answers", textbook_name)

            # 폴더가 없으면 자동 생성
            os.makedirs(exam_dir, exist_ok=True)
            os.makedirs(answer_dir, exist_ok=True)

            # 저장 파일 경로
            exam_file_path = os.path.join(exam_dir, "quiz_exam.json")
            answer_file_path = os.path.join(answer_dir, "quiz_answer.json")

            # ① 순수 문제지만 따로 묶어서 output_exam 폴더 아래로 격리 저장
            exam_package = {
                "meta": full_data["meta"],
                "questions": full_data["quiz_exam"]
            }
            with open(exam_file_path, "w", encoding="utf-8") as f:
                json.dump(exam_package, f, ensure_ascii=False, indent=2)

            # ② 정답/해설지만 따로 묶어서 output_answer 폴더 아래로 격리 저장
            answer_package = {
                "meta": full_data["meta"],
                "answers": full_data["quiz_answer"]
            }
            with open(answer_file_path, "w", encoding="utf-8") as f:
                json.dump(answer_package, f, ensure_ascii=False, indent=2)

            print("\n" + "="*50)
            print("🎉 [출제 격리 성공] 원본 폴더 유실 없이 깨끗하게 저장을 완료했습니다!")
            print(f"📝 [학생용 문제지 전용 폴더] 저장 ──> {exam_file_path}")
            print(f"🔑 [채점용 정답지 전용 폴더] 저장 ──> {answer_file_path}")
            print("="*50 + "\n")
            
            return True

        except Exception as e:
            print(f"❌ [에러] AI 문제 생성 파이프라인 가동 중 치명적 오류 발생: {e}")
            return False