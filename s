import config  # 중앙 통제실 설정 로드
from indexer.pdf_processor import TextbookIndexer
from generator.vector_searcher import PartitionedVectorSearcher
from generator.exam_agent import ExamGenerationAgent
from dotenv import load_dotenv

def main():
    # 0. 환경 변수 초기화 (.env의 API_KEY 로드)
    load_dotenv()
    
    print("=== [1단계] 데이터 전처리 및 물리적 인덱싱 파이프라인 가동 ===")
    # config.py에 정의된 타깃 교과서 이름 사용
    indexer = TextbookIndexer(textbook_name=config.TARGET_TEXTBOOK_NAME)
    
    # [자동 탐색 경로 반영] config.INPUT_PDF_PATH를 넘겨주어 파일 탐색 에러 원천 차단
    indexer.execute_full_indexing(pdf_path=config.INPUT_PDF_PATH)
    print("📂 페이지별 물리적 파티셔닝 데이터베이스 구축 상태 확인 완료.\n")
    
    print("=== [2단계] 사용자 범위 제한 검색/출제 파이프라인 가동 ===")
    # 사용자 입력 모사 (나중에 웹 UI와 연동될 변수들)
    user_start_page = 12
    user_end_page = 25
    user_query = "정보 과학의 '추상화' 개념과 '지하철 노선도' 사례를 연계한 변별력 높은 객관식 문제 출제해줘"
    
    print(f"📥 사용자 설정 범위: {user_start_page}p ~ {user_end_page}p")
    print(f"💡 요구사항: '{user_query}'")
    
    # 2.1 범위 제한 검색 엔진 가동
    searcher = PartitionedVectorSearcher(textbook_name=config.TARGET_TEXTBOOK_NAME)
    
    # 지정된 범위 내의 파일만 읽어 로컬 벡터 코사인 유사도 연산 진행 (NoneType 에러 해결)
    top_ranked_pages = searcher.search_top_k_pages(
        query=user_query, 
        start_page=user_start_page, 
        end_page=user_end_page, 
        top_k=config.SEARCH_TOP_K
    )
    
    # 로컬 검색 엔진이 반환한 결과 검증
    if not top_ranked_pages:
        print("❌ 지정된 범위 내에 파싱된 페이지 데이터가 없거나 유사도 계산에 실패했습니다.")
        return
        
    # 검색 결과에서 최적 페이지 번호 추출
    target_page_numbers = [item["page_num"] for item in top_ranked_pages]
    print(f"🎯 범위 내 로컬 벡터 검색 완료. 최적의 참조 페이지 선정: {target_page_numbers}p")
    
    # 2.2 출제 에이전트 가동 및 최소 토큰 기반 콘텍스트 주입
    agent = ExamGenerationAgent()
    
    # 선정된 최적 페이지의 마크다운 파일 내용만 쏙 골라서 로드
    compact_context = agent.read_context_from_markdown(
        textbook_name=config.TARGET_TEXTBOOK_NAME, 
        target_pages=target_page_numbers
    )
    
    # 압축된 콘텍스트를 기반으로 동적 모델 탐색 후 최종 시험지 생성
    final_exam_sheet = agent.generate_quiz_from_context(
        context=compact_context, 
        query=user_query
    )
    
    print("\n=== ✨ 에이전트 시스템 최종 생성 시험지 ===")
    print(final_exam_sheet)

if __name__ == "__main__":
    main()