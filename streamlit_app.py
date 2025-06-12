# 파일명: streamlit_app.py (PDF 기능 포함된 최종 완성본)

import streamlit as st
import requests
import json
import os
from dotenv import load_dotenv
from pypdf import PdfReader

# --- 기본 설정 ---
BACKEND_API_URL = "https://ai-coach-platform-tz4n.onrender.com"

# --------------------------------------------------------------------------
# 1. 기능별 함수 정의
# --------------------------------------------------------------------------

def send_feedback(consultation_context, ai_suggestion, rating):
    """피드백을 백엔드 서버로 전송하는 함수"""
    try:
        # st.session_state에서 user_id를 가져옵니다.
        user_id = st.session_state.get("user_id")
        if not user_id:
            st.toast("오류: 사용자 정보가 없어 피드백을 보낼 수 없습니다.", icon="🔥")
            return

        payload = {
            "user_id": user_id,
            "consultation_summary": consultation_context[:1000], # 너무 길지 않게 요약본만 저장
            "ai_suggestion": ai_suggestion,
            "rating": rating
        }
        # 백엔드의 /feedback API를 호출합니다.
        response = requests.post(f"{BACKEND_API_URL}/feedback", json=payload, timeout=10)

        if response.status_code == 201:
            st.toast(f"소중한 피드백 감사합니다!", icon="✅")
        else:
            st.toast(f"피드백 저장에 실패했습니다: {response.json().get('error')}", icon="🔥")
    except Exception as e:
        st.toast(f"피드백 전송 중 오류 발생: {e}", icon="🔥")

def login_user(username, password):
    """백엔드에 로그인 요청을 보내고 성공 시 user_id를 포함한 세션 상태를 업데이트합니다."""
    try:
        payload = {"username": username, "password": password}
        response = requests.post(f"{BACKEND_API_URL}/login", json=payload, timeout=60)
        if response.status_code == 200 and response.json().get("success"):
            st.session_state["logged_in"] = True
            user_data = response.json().get("user", {})
            st.session_state["username"] = user_data.get("username")
            st.session_state["role"] = user_data.get("role")
            # [추가됨] 피드백 저장을 위해 user_id를 세션에 저장합니다.
            st.session_state["user_id"] = user_data.get("id")
            st.rerun()
        else:
            st.error(f"로그인 실패: {response.json().get('error', '아이디 또는 비밀번호가 일치하지 않습니다.')}")
    except requests.exceptions.RequestException as e:
        st.error(f"서버에 연결할 수 없습니다: {e}")

def register_user(payload):
    """백엔드에 회원가입 요청을 보냅니다."""
    try:
        response = requests.post(f"{BACKEND_API_URL}/register", json=payload)
        if response.status_code == 201 and response.json().get("success"):
            st.success(response.json().get("message"))
            st.info("관리자 승인 후 로그인이 가능합니다.")
        else:
            st.error(f"등록 실패: {response.json().get('error', '알 수 없는 오류')}")
    except requests.exceptions.RequestException as e:
        st.error(f"서버에 연결할 수 없습니다: {e}")

def display_login_page():
    """로그인과 아이디 생성 탭이 있는 페이지를 구성합니다."""
    st.header("🔐 AI 코칭 플랫폼")
    st.write("팀원의 아이디와 비밀번호로 로그인해주세요.")
    
    tab1, tab2 = st.tabs(["로그인", "아이디 생성 요청"])
    with tab1:
        with st.form("login_form"):
            username = st.text_input("아이디")
            password = st.text_input("비밀번호", type="password")
            if st.form_submit_button("로그인"):
                if username and password:
                    login_user(username, password)
                else:
                    st.error("아이디와 비밀번호를 모두 입력해주세요.")
    with tab2:
        with st.form("register_form"):
            st.info("모든 항목은 필수 입력이며, 등록 후 관리자의 승인이 필요합니다.")
            new_username = st.text_input("사용할 아이디")
            full_name = st.text_input("이름")
            branch_name = st.text_input("지점명")
            gaia_code = st.text_input("가이아 코드번호")
            new_password = st.text_input("비밀번호", type="password")
            confirm_password = st.text_input("비밀번호 확인", type="password")
            st.caption("비밀번호는 8자리 이상, 영문, 숫자, 특수문자를 모두 포함해야 합니다.")
            if st.form_submit_button("등록 요청하기"):
                if not all([new_username, full_name, branch_name, gaia_code, new_password, confirm_password]):
                    st.error("모든 항목을 입력해주세요.")
                elif new_password != confirm_password:
                    st.error("비밀번호가 일치하지 않습니다.")
                else:
                    payload = {"username": new_username, "password": new_password, "full_name": full_name, "branch_name": branch_name, "gaia_code": gaia_code}
                    register_user(payload)

def display_coaching_result(result):
    """AI 분석 결과를 탭 형태로 출력하고, 피드백 버튼을 추가합니다."""
    st.subheader("2. AI 코칭 결과 확인하기")
    if not result:
        st.info("상담 내용을 입력하고 'AI 코칭 시작하기' 버튼을 누르면 여기에 분석 결과가 표시됩니다.")
        return

    # 피드백을 보낼 때, 어떤 상담에 대한 피드백인지 알려주기 위해 원본 상담 내용을 가져옵니다.
    consultation_context = st.session_state.get('last_consultation_text', '')

    tab1, tab2 = st.tabs(["💡 종합 분석 및 전략", "💬 AI 추천 멘트 모음"])

    with tab1:
        st.markdown(f"##### 💡 고객 핵심 니즈")
        st.info(result.get('customer_intent', '분석 정보 없음'))
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"##### 💖 고객 감정 상태")
            st.info(result.get('customer_sentiment', '분석 정보 없음'))
        with col2:
            st.markdown("##### 👤 추정 고객 성향")
            st.info(result.get('customer_profile_guess', '분석 정보 없음'))
        st.markdown("---")
        st.markdown("##### 🧭 다음 추천 진행 방향")
        st.success(result.get('next_step_strategy', '분석 정보 없음'))

    with tab2:
        st.markdown("##### 🛡️ 고객 반론 예측 및 추천 대응 멘트")
        st.caption("AI의 제안이 도움이 되셨다면 👍를, 그렇지 않다면 👎를 눌러주세요!")
        
        strategy_data = result.get('objection_handling_strategy', {})
        example_script = strategy_data.get('example_script', '추천 멘트 없음')
        
        # expander 안에 버튼을 넣기 위해 expander를 먼저 생성합니다.
        strategy_expander = st.expander("**추천 대응 멘트 보기**", expanded=True)
        with strategy_expander:
            st.info(f"**예상 반론:** {strategy_data.get('predicted_objection', '분석된 반론 없음')}")
            st.success(f"**대응 전략:** {strategy_data.get('counter_strategy', '분석된 전략 없음')}")
            st.write(example_script)

            if example_script != '추천 멘트 없음':
                feedback_cols = st.columns([1, 1, 8])
                if feedback_cols[0].button("👍", key="helpful_strategy"):
                    send_feedback(consultation_context, example_script, "helpful")
                if feedback_cols[1].button("👎", key="unhelpful_strategy"):
                    send_feedback(consultation_context, example_script, "not_helpful")
        
        st.markdown("---")
        st.markdown("##### 💬 추가 추천 멘트 옵션")
        for i, action in enumerate(result.get('recommended_actions', [])):
            with st.expander(f"**옵션 {i+1}: {action.get('style', '')}**"):
                script_text = action.get('script', '')
                st.write(script_text)
                
                feedback_cols_actions = st.columns([1, 1, 8])
                if feedback_cols_actions[0].button("👍", key=f"helpful_{i}"):
                    send_feedback(consultation_context, script_text, "helpful")
                if feedback_cols_actions[1].button("👎", key=f"unhelpful_{i}"):
                    send_feedback(consultation_context, script_text, "not_helpful")

def admin_dashboard():
    """관리자 전용 대시보드 UI 및 기능"""
    st.subheader("👑 관리자 페이지: 팀원 계정 관리")
    if st.button("🔄 사용자 목록 새로고침"): st.rerun()
    try:
        response = requests.get(f"{BACKEND_API_URL}/admin/users")
        if response.status_code == 200 and response.json().get("success"):
            users = response.json().get("users", [])
            st.markdown("---")
            cols = st.columns([1.5, 1.5, 1.5, 1.5, 1, 1, 1]); cols[0].write("**아이디**"); cols[1].write("**이름**"); cols[2].write("**지점명**"); cols[3].write("**가이아 코드**"); cols[4].write("**승인 상태**"); cols[5].write("**역할**"); cols[6].write("**계정 관리**")
            for user in users:
                cols = st.columns([1.5, 1.5, 1.5, 1.5, 1, 1, 1])
                cols[0].text(user['username']); cols[1].text(user['full_name']); cols[2].text(user['branch_name']); cols[3].text(user['gaia_code'])
                if user['is_approved']: cols[4].success("승인")
                else:
                    if cols[4].button("승인하기", key=f"approve_{user['id']}", type="primary"):
                        requests.post(f"{BACKEND_API_URL}/admin/approve/{user['id']}"); st.success(f"'{user['username']}'님을 승인했습니다."); st.rerun()
                cols[5].text(user['role'])
                if user['role'] != 'admin':
                    if cols[6].button("삭제", key=f"delete_{user['id']}"):
                        requests.delete(f"{BACKEND_API_URL}/admin/delete/{user['id']}"); st.warning(f"'{user['username']}'님을 삭제했습니다."); st.rerun()
        else: st.error("사용자 목록을 불러오는 데 실패했습니다.")
    except requests.exceptions.RequestException as e: st.error(f"서버에 연결할 수 없습니다: {e}")

def display_ai_coach_ui():
    """AI 코칭 보조창의 메인 UI를 그리는 함수"""
    with st.sidebar:
        st.header("📋 AI 상담 코치")
        st.write(f"**{st.session_state.get('username', '설계사')}**님, 환영합니다!")
        if st.button("✨ 새로운 상담 시작하기"):
            keys_to_clear = ['history', 'last_analysis', 'text_input']
            for key in keys_to_clear:
                if key in st.session_state:
                    st.session_state[key] = "" if key == 'text_input' else None
            st.success("새로운 상담 세션을 시작합니다!")
            st.rerun()
        if st.button("🚪 로그아웃"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    st.title("🚀 AI 실시간 코칭 보조창")
    st.markdown("고객과의 상담 내용을 입력하거나 PDF 파일을 업로드하면, AI가 실시간으로 분석하고 코칭을 제공합니다.")

    # --- [복원됨] 상담 내용 입력 영역 (텍스트 + PDF) ---
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
            st.session_state['last_consultation_text'] = consultation_text
            with st.spinner(f'{source}의 내용을 AI가 분석 중입니다...'):
                payload = {"consultation_text": consultation_text, "history": st.session_state.get('history', [])}
                response = requests.post(f"{BACKEND_API_URL}/analyze", json=payload)
                if response.status_code == 200 and response.json().get("success"):
                    response_data = response.json()
                    st.session_state.last_analysis = response_data.get("analysis")
                    st.session_state.history = response_data.get("history")
                    st.success("✅ AI 코칭 분석이 완료되었습니다!")
                else:
                    st.error(f"분석 실패: {response.json().get('error', '알 수 없는 오류')}")
                    pass
        else:
            st.warning("분석할 상담 내용을 텍스트로 입력하거나 PDF 파일을 업로드해주세요.")

    # 분석 결과를 표시하기 위해 display_coaching_result 함수를 호출합니다.
    display_coaching_result(st.session_state.get('last_analysis'))

def main_app():
    """로그인 성공 후 표시될 화면을 역할에 따라 분기"""
    user_role = st.session_state.get("role", "user")
    if user_role == 'admin':
        main_tab, admin_tab = st.tabs(["🚀 AI 코칭 보조창", "👑 관리자 페이지"])
        with main_tab:
            display_ai_coach_ui()
        with admin_tab:
            admin_dashboard()
    else:
        display_ai_coach_ui()

# --------------------------------------------------------------------------
# 4. 앱의 메인 실행 로직
# --------------------------------------------------------------------------

# 세션 상태 초기화
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if 'history' not in st.session_state: st.session_state.history = []
if 'last_analysis' not in st.session_state: st.session_state.last_analysis = None

# 로그인 상태에 따라 다른 페이지(함수)를 보여줌
if st.session_state.logged_in:
    main_app()
else:
    display_login_page()
