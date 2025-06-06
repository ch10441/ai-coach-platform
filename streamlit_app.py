# 파일명: streamlit_app.py

# --- 1. 필요한 라이브러리들을 가져옵니다 ---
import streamlit as st
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv
from pypdf import PdfReader # [추가됨] PDF 처리를 위해 다시 추가

# --------------------------------------------------------------------------
# 2. AI 코칭 서비스 클래스 (이전과 동일, 수정 없음)
# --------------------------------------------------------------------------
class AICoachingService:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            st.error("오류: GOOGLE_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")
            st.stop()
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(
            'gemini-1.5-pro-latest',
            generation_config={"response_mime_type": "application/json"}
        )

    def _build_prompt(self, consultation_text, history):
        # ... (이전과 동일한 프롬프트 내용)
        history_str = "\n".join(history) if history else "없음"
        return f"""
        당신은 보험 설계사를 위한 매우 유능한 AI 상담 코치입니다. ... (이하 프롬프트 생략)
        """

    def analyze_consultation(self, consultation_text, history):
        # ... (이전과 동일한 분석 로직)
        if not consultation_text.strip(): return None, history
        prompt = self._build_prompt(consultation_text, history)
        try:
            response = self.model.generate_content(prompt)
            coaching_result = json.loads(response.text)
            new_history = history + [f"---고객/설계사 대화---\n{consultation_text}", f"---AI 코칭 요약---\n고객 의도: {coaching_result.get('customer_intent')}, 감정: {coaching_result.get('customer_sentiment')}"]
            return coaching_result, new_history
        except Exception as e:
            st.error(f"🔥 AI 분석 중 오류가 발생했습니다: {e}")
            return None, history

# --------------------------------------------------------------------------
# 3. Streamlit으로 인터페이스(화면) 만들기
# --------------------------------------------------------------------------

# --- 앱의 상태(State) 관리 ---
if 'ai_service' not in st.session_state:
    st.session_state.ai_service = AICoachingService()
if 'history' not in st.session_state:
    st.session_state.history = []
if 'last_analysis' not in st.session_state:
    st.session_state.last_analysis = None

# --- 사이드바 화면 구성 (이전과 동일) ---
with st.sidebar:
    st.header("📋 AI 상담 코치")
    st.write("비대면 보험 상담의 성공률을 높여보세요.")
    if st.button("✨ 새로운 상담 시작하기"):
        st.session_state.history = []
        st.session_state.last_analysis = None
        st.success("새로운 상담 세션을 시작합니다!")

# --- 메인 화면 구성 ---
st.title("🚀 AI 실시간 코칭 보조창")
st.markdown("고객과의 상담 내용을 입력하거나 PDF 파일을 업로드하면, AI가 실시간으로 분석하고 코칭을 제공합니다.")

# --- 상담 내용 입력 영역 ---
st.subheader("1. 상담 내용 입력하기")
input_text = st.text_area(
    "여기에 고객과의 대화 내용을 붙여넣어 주세요.", 
    height=200, 
    placeholder="예시) 고객: 안녕하세요, 암보험이 궁금해서요..."
)

# [추가됨] PDF 파일 업로드 기능
st.markdown("---") # 구분선
uploaded_file = st.file_uploader("또는 PDF 파일을 업로드하세요.", type="pdf")


# [수정됨] 버튼 클릭 시 로직 수정
if st.button("🤖 AI 코칭 시작하기", type="primary"):
    
    consultation_text = ""
    source = ""

    # 1. PDF 파일이 업로드되었는지 먼저 확인
    if uploaded_file is not None:
        try:
            reader = PdfReader(uploaded_file)
            pdf_text = "".join(page.extract_text() for page in reader.pages)
            if pdf_text.strip():
                consultation_text = pdf_text
                source = f"'{uploaded_file.name}' 파일"
            else:
                st.error("업로드된 PDF 파일에서 텍스트를 추출하지 못했습니다.")
        except Exception as e:
            st.error(f"PDF 파일 처리 중 오류가 발생했습니다: {e}")
            
    # 2. PDF 파일이 없다면, 텍스트 입력창에 내용이 있는지 확인
    elif input_text.strip():
        consultation_text = input_text
        source = "텍스트 입력창"

    # 분석할 내용이 있을 경우에만 AI 분석 실행
    if consultation_text:
        with st.spinner(f'{source}의 내용을 AI가 분석 중입니다... 잠시만 기다려주세요...'):
            analysis_result, new_history = st.session_state.ai_service.analyze_consultation(
                consultation_text, 
                st.session_state.history
            )
        
        if analysis_result:
            st.session_state.last_analysis = analysis_result
            st.session_state.history = new_history
            st.success("✅ AI 코칭 분석이 완료되었습니다!")
    # 분석할 내용이 아무것도 없는 경우
    else:
        st.warning("분석할 상담 내용을 텍스트로 입력하거나 PDF 파일을 업로드해주세요.")

# --- AI 코칭 결과 표시 영역 (이전과 동일) ---
st.subheader("2. AI 코칭 결과 확인하기")

if st.session_state.last_analysis:
    result = st.session_state.last_analysis
    tab1, tab2 = st.tabs(["💡 종합 분석 및 전략", "💬 추천 멘트"])

    with tab1:
        st.markdown(f"##### 💡 고객 핵심 니즈")
        st.info(result.get('customer_intent', '분석 정보 없음'))
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"##### 💖 고객 감정 상태")
            st.info(result.get('customer_sentiment', '분석 정보 없음'))
        with col2:
            st.markdown(f"##### 👤 추정 고객 성향")
            st.info(result.get('customer_profile_guess', '분석 정보 없음'))
        
        st.markdown("---")
        st.markdown("##### 🧭 다음 추천 진행 방향")
        st.success(result.get('next_step_strategy', '분석 정보 없음'))

    with tab2:
        st.markdown("##### 💬 AI 추천 멘트 옵션")
        for i, action in enumerate(result.get('recommended_actions', [])):
            with st.expander(f"**옵션 {i+1}: {action.get('style', '')}**"):
                st.write(action.get('script', ''))
else:
    st.info("상담 내용을 입력하고 'AI 코칭 시작하기' 버튼을 누르면 여기에 분석 결과가 표시됩니다.")
