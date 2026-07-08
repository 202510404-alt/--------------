import os
import streamlit as st
from dotenv import load_dotenv

import config
from indexer.pdf_processor import TextbookIndexer
from generator.exam_agent import ExamGenerationAgent
from generator.quiz_player import QuizPlayer

load_dotenv()

st.set_page_config(
    page_title="AI 시험 생성기",
    page_icon="📚",
    layout="wide"
)

st.title("📚 AI 시험 생성기")

# -------------------------------------------------
# 세션 상태
# -------------------------------------------------

if "quiz_started" not in st.session_state:
    st.session_state.quiz_started = False

# -------------------------------------------------
# 문제 풀이 화면
# -------------------------------------------------

if st.session_state.quiz_started:
    QuizPlayer().run()
    st.stop()

# -------------------------------------------------
# 최초 실행 시 인덱싱
# -------------------------------------------------

indexer = TextbookIndexer(
    textbook_name=config.TARGET_TEXTBOOK_NAME
)

if not (
    os.path.exists(indexer.textbook_dir)
    and os.listdir(indexer.textbook_dir)
):

    with st.spinner("PDF를 분석하고 있습니다..."):

        indexer.execute_full_indexing(
            pdf_path=config.INPUT_PDF_PATH
        )

# -------------------------------------------------
# 시험 생성 UI
# -------------------------------------------------

st.subheader("시험 설정")

col1, col2 = st.columns(2)

with col1:

    start_page = st.number_input(
        "시작 페이지",
        min_value=1,
        value=1
    )

    question_count = st.number_input(
        "문항 수",
        min_value=1,
        value=5
    )

with col2:

    end_page = st.number_input(
        "끝 페이지",
        min_value=1,
        value=5
    )

    difficulty = st.selectbox(
        "난이도",
        ["상", "중", "하"]
    )

user_query = st.text_area(
    "추가 요구사항",
    placeholder="예) 단어퀴즈 위주, 쉬운 문제만..."
)

st.divider()

if st.button(
    "🚀 시험 생성",
    use_container_width=True
):

    if start_page > end_page:

        st.error("시작 페이지는 끝 페이지보다 클 수 없습니다.")

        st.stop()

    with st.spinner("AI가 시험을 생성하고 있습니다..."):

        discovered_keyword = getattr(
            indexer,
            "generation_model",
            "flash"
        )

        agent = ExamGenerationAgent(
            model_keyword=discovered_keyword
        )

        success = agent.generate_quiz_pipeline(

            textbook_name=config.TARGET_TEXTBOOK_NAME,

            start_page=start_page,

            end_page=end_page,

            q_count=question_count,

            q_difficulty=difficulty,

            user_query=user_query

        )

    if success:

        st.success("시험 생성 완료!")

        st.session_state.quiz_started = True

        st.rerun()

    else:

        st.error("시험 생성 실패")