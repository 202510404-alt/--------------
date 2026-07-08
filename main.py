import os
import config  # 중앙 통제실 설정 파일 로드
from indexer.pdf_processor import TextbookIndexer
from generator.exam_agent import ExamGenerationAgent
from dotenv import load_dotenv

def main():
    # 0. 환경 변수 초기화 (.env의 API_KEY 로드)
    load_dotenv()
    
    print("=== [1단계] 데이터 전처리 및 물리적 인덱싱 파이프라인 점검 ===")
    # config.py에 정의된 타깃 교과서 이름 사용
    indexer = TextbookIndexer(textbook_name=config.TARGET_TEXTBOOK_NAME)
    
    # 💡 [교정 및 복원]: 무조건 새로 인덱싱하는 버그 수정.
    # 해당 교과서 폴더가 존재하고 내부 파일(마크다운)이 이미 존재한다면 전처리를 초고속 스킵합니다.
    if os.path.exists(indexer.textbook_dir) and os.listdir(indexer.textbook_dir):
        print(f"ℹ️ [{config.TARGET_TEXTBOOK_NAME}] 이미 추출된 마크다운 데이터베이스가 감지되었습니다.")
        print("⚡ 중복 파싱을 방지하기 위해 1단계 인덱싱을 스킵하고 즉시 출제 단계로 진입합니다.")
    else:
        print("📂 기존 데이터베이스가 비어있거나 존재하지 않습니다. 로컬 전처리를 시작합니다...")
        # config.INPUT_PDF_PATH를 넘겨주어 파일 탐색 에러 원천 차단
        indexer.execute_full_indexing(pdf_path=config.INPUT_PDF_PATH)
        print("📂 페이지별 물리적 파티셔닝 데이터베이스 구축 완료.\n")
    
    print("\n=== [2단계] 사용자 맞춤형 범위 제한 전체 스캔 출제 파이프라인 가동 ===")
    
    # 💡 [기능 확장]: 하드코딩을 걷어내고, 사용자가 유연하게 시험지를 통제할 수 있는 터미널 UI 구축
    try:
        user_start_page = int(input("📖 출제를 시작할 페이지 번호 입력 (예: 12): "))
        user_end_page = int(input("📖 출제를 마칠 페이지 번호 입력 (예: 25): "))
        q_count = int(input("❓ 출제할 문항 수 입력 (예: 3): "))
        q_difficulty = input("📊 난이도 설정 (상 / 중 / 하): ").strip()
        user_query = input("💡 추가 맞춤 요구사항 입력 (없으면 그냥 엔터): ").strip()
    except ValueError:
        print("❌ [오류] 페이지 번호와 문항 수는 반드시 정수(숫자)로 입력해야 합니다.")
        return

    # 입력 조건 무결성 1차 방어 코드
    if user_start_page <= 0 or user_end_page <= 0:
        print("❌ [오류] 페이지 번호는 0보다 커야 합니다.")
        return
    if user_start_page > user_end_page:
        print("❌ [오류] 시작 페이지 번호가 끝 페이지 번호보다 클 수 없습니다.")
        return
    if q_count <= 0:
        print("❌ [오류] 최소 1문항 이상 출제해야 합니다.")
        return

    print(f"\n📥 사용자 지정 옵션 수신 완료:")
    print(f"  - 범위: {user_start_page}p ~ {user_end_page}p")
    print(f"  - 문항 수: {q_count}문항 / 난이도: {q_difficulty}")
    if user_query:
        print(f"  - 요구사항: '{user_query}'")
    print("-" * 50)

    # 💡 [교정 및 복원]: 인덱서가 서버에서 동적으로 발견한 생성용 모델 가용 키워드를 안전하게 이관 주입
    discovered_keyword = getattr(indexer, 'generation_model', "flash")
    agent = ExamGenerationAgent(model_keyword=discovered_keyword)
    
    # 💡 [새로운 설계 적용]: 지정 범위 마크다운 연속 스캔 및 JSON 분리 저장 원스톱 파이프라인 호출
    print("🚀 연속 지문 병합 및 구글 구조화 JSON 스키마 기반 문제 출제를 가동합니다...")
    success = agent.generate_quiz_pipeline(
        textbook_name=config.TARGET_TEXTBOOK_NAME,
        start_page=user_start_page,
        end_page=user_end_page,
        q_count=q_count,
        q_difficulty=q_difficulty,
        user_query=user_query
    )
    
    if success:
        print("\n✨ [최종 안내] 모든 출제 및 파일 물리적 격리 저장이 완료되었습니다. 시스템을 종료합니다.")
    else:
        print("\n❌ [최종 안내] 파이프라인 연산 중 오류가 발생하여 출제에 실패했습니다.")

if __name__ == "__main__":
    main()