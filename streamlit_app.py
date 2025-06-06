# 파일명: streamlit_app.py (최종 완성본 - 오류 수정 완료)

# --- 1. 필요한 라이브러리들을 가져옵니다 ---
import streamlit as st
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv
from pypdf import PdfReader 

# --------------------------------------------------------------------------
# 2. AI 코칭 서비스 클래스 
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
        history_str = "\n".join(history) if history else "없음"
        # 3단계 보장 분석 지침이 포함된 프롬프트
        return f"""
        
        [역활 및 페르소나]
        당신은 대한민국 최고의 보험 세일즈 전문가이자, 비대면 채팅으로 보험상담을 하는 설계사님을 전문으로 지원하기 위해 개발된 고객 상담 및 학습 전문 AI입니다.
        고객과의 대화 내용을 실시간으로 분석하여 고객의 보험 니즈를 정확하게 파악하고, 설계사님께 최적의 응답을 제안합니다.
        특히, 초보설계사들을 위한 맞춤형 피드백을 제공하여 상담 실력 향상 및 성과 증대에 기여하는 것을 목표로 합니다.
        또한, 심리학에 기반하여 고객의 마음을 얻는 것을 중요하게 생각합니다.
        
        [반드시 지켜야 할 규칙]
        - 상담 내용에 명시적으로 언급되지 않은 정보는 절대 추측하거나 만들어내지 마세요.
        - 모든 추천 멘트는 한 번에 2~3 문장 이내로, 간결하고 명확하게 작성하세요.
        - 고객의 말을 긍정적으로 재진술하며(예: "아, OOO에 대해 궁금하시군요!") 신뢰를 쌓는 화법을 사용하세요.
        - 법적 또는 규제상 민감할 수 있는 내용은 단정적으로 표현하지 말고, "일반적으로" 또는 "예를 들어"와 같은 표현을 사용하세요.
        - 분석이 불가능할 경우, 각 JSON 값에 '정보가 부족하여 분석할 수 없습니다'라고 명확히 응답하세요.
        - 고객이 명시적으로 표현한 니즈는 물론, 대화의 맥락과 감정선, 언급된 상황 등을 통해 암시되는 잠재적/근원적 니즈까지 정확히 포착합니다. 또한, 파악된 니즈들의 우선순위를 추론하여 가장 시급하거나 중요한 포인트를 강조합니다.


        [분석 절차]
        먼저, '이전 상담 맥락'과 '현재 상담 내용'을 바탕으로 단계별로 신중하게 생각한 후, 그 최종 결론을 아래 JSON 형식에 맞춰 제공해주세요.

    [출력 JSON 형식 및 지침]
    {{
      "customer_intent": "고객의 가장 핵심적인 질문 의도나 니즈를 한 문장으로 요약",
      "customer_sentiment": "현재 고객의 감정 상태 (예: 궁금함, 우려함, 긍정적, 부정적, 신중함)",
      "customer_profile_guess": "지금까지의 대화를 바탕으로 추정한 고객 성향 (예: 분석형, 관계중시형, 신중형)",
      "three_stage_coverage_analysis": {{
          "stage_1_actual_cost_insurance": "실손의료보험에 대한 분석 (언급 시)",
          "stage_2_diagnosis_fund": "주요 진단비(암, 뇌, 심장)에 대한 분석 (언급 시)",
          "stage_3_surgery_fund": "수술비 보장에 대한 분석 (언급 시)"
      }},
      "recommended_actions": [
        {{"style": "공감 및 관계 형성", "script": "신뢰를 쌓기 위한 구체적인 멘트"}},
        {{"style": "논리적 설득 및 정보 제공", "script": "고객을 설득하기 위한 구체적인 멘트"}},
        {{"style": "다음 단계 유도 및 질문", "script": "상담을 다음 단계로 이끌기 위한 구체적인 질문 멘트"}}
      ],
      "next_step_strategy": "현재 상황에서 가장 효과적인 다음 상담 진행 방향 및 전략에 대한 간략한 조언"
    }}

    <모범 예시>
    [이전 상담 맥락]
    없음
    [현재 상담 내용]
    고객: 안녕하세요, 실비보험 가입하고 싶은데, 보험료가 얼마나 나올까요?
    [AI 코칭 결과]
    {{
      "customer_intent": "실손의료보험의 예상 보험료에 대한 직접적인 문의",
      "customer_sentiment": "궁금함",
      "customer_profile_guess": "정보 탐색형",
      "three_stage_coverage_analysis": {{"stage_1_actual_cost_insurance": "고객이 가입을 원하는 핵심 보장. 아직 가입 전 상태.", "stage_2_diagnosis_fund": "언급된 정보 없음", "stage_3_surgery_fund": "언급된 정보 없음"}},
      "recommended_actions": [
        {{"style": "깊은 공감 및 부담감 해소", "script": "네, 고객님! 실손 보험에 관심 있으시군요. 가장 기본적인 보험이라 정말 잘 알아보시는 겁니다. 보험료는 고객님의 연령이나 성별 등에 따라 달라져서요, 혹시 실례가 안 된다면 여쭤봐도 될까요?"}},
        {{"style": "관점 전환 및 긍정적 재해석", "script": "보험료도 물론 중요하죠! 그전에 혹시 실손 보험을 통해 어떤 보장을 가장 받고 싶으신지 먼저 여쭤봐도 될까요? 고객님께 꼭 맞는 플랜을 찾아드리고 싶어서요."}},
        {{"style": "구체적인 대안 제시 및 질문", "script": "네, 고객님. 바로 안내 도와드리겠습니다. 정확한 보험료 확인을 위해 몇 가지만 확인하고 바로 맞춤 설계안을 보내드릴게요."}}
      ],
      "next_step_strategy": "고객의 부담감을 먼저 깊이 공감하여 심리적 장벽을 낮추는 것이 최우선입니다. 그 후, '늦었다'는 인식을 '지금이 적기'라는 긍정적 프레임으로 전환하고, '조절 가능하다'는 대안을 제시하여 고객이 다음 단계의 설명을 편안하게 들을 수 있도록 유도해야 합니다."
    }}
        ---
        [이전 상담 맥락]
        {history_str}
        ---
        [현재 상담 내용]
        {consultation_text}
        ---
        """

    def analyze_consultation(self, consultation_text, history):
        if not consultation_text.strip(): return None, history
        prompt = self._build_prompt(consultation_text, history)
        try:
            response = self.model.generate_content(prompt)
            coaching_result = json.loads(response.text)
            new_history = history + [
                f"---고객/설계사 대화---\n{consultation_text}",
                f"---AI 코칭 요약---\n고객 의도: {coaching_result.get('customer_intent')}, 감정: {coaching_result.get('customer_sentiment')}"
            ]
            return coaching_result, new_history
        except Exception as e:
            st.error(f"🔥 AI 분석 중 오류가 발생했습니다: {e}")
            return None, history

# --------------------------------------------------------------------------
# 3. Streamlit 인터페이스 및 로그인/메인 앱 로직
# --------------------------------------------------------------------------

def check_password():
    """비밀번호를 확인하여 로그인 상태를 관리하는 함수 (오류 방지 로직 강화)"""
    if st.session_state.get("password_correct", False):
        return True

    correct_password = os.getenv("APP_PASSWORD")
    if not correct_password:
        st.warning("⚠️ 경고: .env 파일에 APP_PASSWORD가 설정되어 있지 않습니다. 개발 모드로 로그인 없이 진행합니다.")
        return True

    st.header("🔐 AI 코칭 플랫폼 로그인")
    password = st.text_input("비밀번호를 입력하세요.", type="password")
    if st.button("로그인"):
        if password == correct_password:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("비밀번호가 일치하지 않습니다.")
    return False

# ▼▼▼▼▼ [수정됨] 누락되었던 이 함수가 다시 추가되었습니다! ▼▼▼▼▼
def _display_coaching_result(result):
    """구조화된 분석 결과를 사용자가 보기 좋게 출력하는 함수"""
    st.subheader("2. AI 코칭 결과 확인하기")
    if not result:
        st.info("상담 내용을 입력하고 'AI 코칭 시작하기' 버튼을 누르면 여기에 분석 결과가 표시됩니다.")
        return

    tab1, tab2, tab3 = st.tabs(["💡 종합 분석", "📊 보장 분석", "💬 추천 멘트"])

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
        st.markdown("##### 📊 3단계 보장 기준 분석 (언급된 내용 기반)")
        analysis_data = result.get('three_stage_coverage_analysis')
        if analysis_data:
            st.markdown(f"**1️⃣ 실손의료보험:** {analysis_data.get('stage_1_actual_cost_insurance', '분석 정보 없음')}")
            st.markdown(f"**2️⃣ 주요 진단비:** {analysis_data.get('stage_2_diagnosis_fund', '분석 정보 없음')}")
            st.markdown(f"**3️⃣ 수술비 보장:** {analysis_data.get('stage_3_surgery_fund', '분석 정보 없음')}")
        else:
            st.info("분석된 보장 기준 정보가 없습니다.")

    with tab3:
        st.markdown("##### 💬 AI 추천 멘트 옵션")
        for i, action in enumerate(result.get('recommended_actions', [])):
            with st.expander(f"**옵션 {i+1}: {action.get('style', '')}**"):
                st.write(action.get('script', ''))
# ▲▲▲▲▲ 여기까지가 누락되었던 함수입니다 ▲▲▲▲▲

def main_app():
    """로그인 성공 후 표시될 메인 애플리케이션 UI 및 로직"""
    with st.sidebar:
        st.header("📋 AI 상담 코치")
        st.write("비대면 보험 상담의 성공률을 높여보세요.")
        if st.button("✨ 새로운 상담 시작하기"):
            st.session_state.history = []
            st.session_state.last_analysis = None
            st.success("새로운 상담 세션을 시작합니다!")

    st.title("🚀 AI 실시간 코칭 보조창")
    st.markdown("고객과의 상담 내용을 입력하거나 PDF 파일을 업로드하면, AI가 실시간으로 분석하고 코칭을 제공합니다.")

    st.subheader("1. 상담 내용 입력하기")
    input_text = st.text_area("여기에 고객과의 대화 내용을 붙여넣어 주세요.", height=200, key="text_input")
    st.markdown("---")
    uploaded_file = st.file_uploader("또는 PDF 파일을 업로드하세요.", type="pdf", key="file_uploader")

    if st.button("🤖 AI 코칭 시작하기", type="primary"):
        consultation_text = ""
        source = ""
        if uploaded_file is not None:
            try:
                reader = PdfReader(uploaded_file)
                pdf_text = "".join(page.extract_text() for page in reader.pages)
                if pdf_text.strip():
                    consultation_text = pdf_text
                    source = f"'{uploaded_file.name}' 파일"
                else: st.error("업로드된 PDF 파일에서 텍스트를 추출하지 못했습니다.")
            except Exception as e: st.error(f"PDF 파일 처리 중 오류가 발생했습니다: {e}")
        elif input_text.strip():
            consultation_text = input_text
            source = "텍스트 입력창"

        if consultation_text:
            with st.spinner(f'{source}의 내용을 AI가 분석 중입니다...'):
                analysis_result, new_history = st.session_state.ai_service.analyze_consultation(consultation_text, st.session_state.history)
            if analysis_result:
                st.session_state.last_analysis = analysis_result
                st.session_state.history = new_history
                st.success("✅ AI 코칭 분석이 완료되었습니다!")
        else:
            st.warning("분석할 상담 내용을 텍스트로 입력하거나 PDF 파일을 업로드해주세요.")
    
    # 분석 결과를 표시하기 위해 _display_coaching_result 함수를 호출합니다.
    _display_coaching_result(st.session_state.last_analysis)

# --- 앱의 상태(State) 관리 및 메인 로직 실행 ---
if 'ai_service' not in st.session_state:
    st.session_state.ai_service = AICoachingService()
if 'history' not in st.session_state:
    st.session_state.history = []
if 'last_analysis' not in st.session_state:
    st.session_state.last_analysis = None

if check_password():
    main_app()
