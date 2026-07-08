import json
import os
import streamlit as st
import config


class QuizPlayer:
    def __init__(self):
        self.textbook_name = config.TARGET_TEXTBOOK_NAME

        self.question_path = os.path.join(
            "questions",
            self.textbook_name,
            "quiz_exam.json"
        )

        self.answer_path = os.path.join(
            "answers",
            self.textbook_name,
            "quiz_answer.json"
        )

    def load_data(self):
        if not os.path.exists(self.question_path):
            st.error(f"문제 파일이 없습니다.\n{self.question_path}")
            st.stop()

        if not os.path.exists(self.answer_path):
            st.error(f"답안 파일이 없습니다.\n{self.answer_path}")
            st.stop()

        with open(self.question_path, "r", encoding="utf-8") as f:
            exam = json.load(f)

        with open(self.answer_path, "r", encoding="utf-8") as f:
            answer = json.load(f)

        return exam, answer

    def run(self):

        exam, answer = self.load_data()

        questions = exam["questions"]
        answers = answer["answers"]

        if "current" not in st.session_state:
            st.session_state.current = 0

        if "score" not in st.session_state:
            st.session_state.score = 0

        if "submitted" not in st.session_state:
            st.session_state.submitted = False

        if "selected" not in st.session_state:
            st.session_state.selected = None
        
        if "answered" not in st.session_state:
            st.session_state.answered = {}

        if st.session_state.current >= len(questions):

            st.success(
                f"시험 종료!\n\n점수 : {st.session_state.score}/{len(questions)}"
            )

            if st.button("처음부터 다시"):
                st.session_state.current = 0
                st.session_state.score = 0
                st.session_state.submitted = False
                st.session_state.selected = None
                st.session_state.answered = {}
                st.rerun()

            return

        q = questions[st.session_state.current]
        a = answers[st.session_state.current]

        st.title("📖 AI 시험")

        st.subheader(
            f"문제 {st.session_state.current+1} / {len(questions)}"
        )

        st.write(q["question_text"])

        choice = st.radio(
            "정답을 선택하세요.",
            q["options"],
            key=f"radio_{st.session_state.current}"
        )

        if st.button("제출"):

            st.session_state.submitted = True
            st.session_state.selected = choice

            current_id = q["id"]

            # 이미 채점한 문제인지 확인
            if current_id not in st.session_state.answered:

                # 선택한 보기 번호 추출
                selected_number = choice.split(".")[0].strip()

                # 정답 비교
                if selected_number == str(a["correct_option"]):
                    st.success("⭕ 정답입니다.")
                    st.session_state.score += 1
                    st.session_state.answered[current_id] = True
                else:
                    st.error("❌ 오답입니다.")
                    st.session_state.answered[current_id] = False

            else:
                # 이미 채점된 문제면 결과만 출력
                if st.session_state.answered[current_id]:
                    st.success("⭕ 정답입니다.")
                else:
                    st.error("❌ 오답입니다.")

        if st.session_state.submitted:

            with st.expander("답지 보기"):

                st.write(f"**정답 :** {a['correct_option']}")
                st.write(f"**정답 내용 :** {a['correct_text']}")
                st.write("---")
                st.write(a["explanation"])

            if st.button("다음 문제"):

                st.session_state.current += 1
                st.session_state.submitted = False
                st.session_state.selected = None

                st.rerun()


if __name__ == "__main__":
    QuizPlayer().run()