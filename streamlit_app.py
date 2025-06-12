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

def send_feedback(consultation_context, ai_suggestion, rating, key_prefix):
    """피드백을 백엔드 서버로 전송하는 함수"""
    try:
        payload = { "user_id": st.session_state.get("user_id"), "consultation_summary": consultation_context[:1000], "ai_suggestion": ai_suggestion, "rating": rating }
        response = requests.post(f"{BACKEND_API_URL}/feedback", json=payload, timeout=10)
        if response.status_code == 201:
            st.toast("소중한 피드백 감사합니다!", icon="✅")
            st.session_state.feedback_status[key_prefix] = True
            st.rerun()
        else:
            st.toast(f"피드백 저장 실패: {response.json().get('error')}", icon="🔥")
    except Exception as e:
        st.toast(f"피드백 전송 중 오류 발생: {e}", icon="🔥")

def login_user(username, password):
    """백엔드에 로그인 요청을 보내는 함수"""
    try:
        payload = {"username": username, "password": password}
        response = requests.post(f"{BACKEND_API_URL}/login", json=payload, timeout=60)
        if response.status_code == 200 and response.json().get("success"):
            user_data = response.json().get("user", {})
            st.session_state.logged_in = True
            st.session_state.username = user_data.get("username")
            st.session_state.role = user_data.get("role")
            st.session_state.user_id = user_data.get("id")
            st.rerun()
        else:
            st.error(f"로그인 실패: {response.json().get('error', '아이디 또는 비밀번호가 일치하지 않습니다.')}")
    except requests.exceptions.RequestException:
        st.error("서버에 연결할 수 없습니다. 백엔드 서버가 실행 중인지 확인해주세요.")

def register_user(payload):
    """백엔드에 회원가입 요청을 보내는 함수"""
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
    """로그인과 아이디 생성 요청 탭이 있는 페이지"""
    st.header("🔐 AI 코칭 플랫폼")
    st.write("팀원의 아이디와 비밀번호로 로그인해주세요.")
    tab1, tab2 = st.tabs(["로그인", "아이디 생성 요청"])
    with tab1:
        with st.form("login_form"):
            username = st.text_input("아이디")
            password = st.text_input("비밀번호", type="password")
            if st.form_submit_button("로그인"):
                if username and password: login_user(username, password)
                else: st.error("아이디와 비밀번호를 모두 입력해주세요.")
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
                if not all([new_username, full_name, branch_name, gaia_code, new_password, confirm_password]): st.error("모든 항목을 입력해주세요.")
                elif new_password != confirm_password: st.error("비밀번호가 일치하지 않습니다.")
                else:
                    payload = {"username": new_username, "password": new_password, "full_name": full_name, "branch_name": branch_name, "gaia_code": gaia_code}
                    register_user(payload)

def display_coaching_result(result):
    """[수정됨] AI 분석 결과를 더 명확하게 구분하여 보여주는 함수"""
    st.subheader("2. AI 코칭 결과 확인하기")
    if not result:
        st.info("상담 내용을 입력하고 'AI 코칭 시작하기' 버튼을 누르면 여기에 분석 결과가 표시됩니다.")
        return

    # 피드백 전송에 필요한 상담 내용 원본을 가져옵니다.
    consultation_context = st.session_state.get('last_consultation_text', '')

    # [수정됨] 탭 구조를 2개로 단순화하여 가독성을 높입니다.
    with st.container(border=True):
        st.markdown("##### 💡 종합 분석 및 전략")
        st.info(f"**고객 핵심 니즈:** {result.get('customer_intent', '분석 정보 없음')}")
        st.info(f"**고객 감정 상태:** {result.get('customer_sentiment', '분석 정보 없음')}")
        st.info(f"**추정 고객 성향:** {result.get('customer_profile_guess', '분석 정보 없음')}")
        st.success(f"**다음 추천 진행 방향:** {result.get('next_step_strategy', '분석 정보 없음')}")

    st.markdown("---")
    
    st.markdown("##### 🛡️ 고객 반론 예측 및 추천 대응 멘트")
    st.caption("AI의 제안이 도움이 되셨다면 👍를, 그렇지 않다면 👎를 눌러주세요!")
    strategy_data = result.get('objection_handling_strategy', {})
    example_script = strategy_data.get('example_script', '추천 멘트 없음')
    
    with st.container(border=True):
        st.warning(f"**예상 반론:** {strategy_data.get('predicted_objection', '분석된 반론 없음')}")
        st.write(example_script)
        if example_script != '추천 멘트 없음':
            feedback_key_strategy = f"feedback_for_strategy_{example_script[:30]}"
            is_disabled_strategy = st.session_state.feedback_status.get(feedback_key_strategy, False)
            feedback_cols = st.columns(10)
            if feedback_cols[0].button("👍", key="helpful_strategy", disabled=is_disabled_strategy):
                send_feedback(consultation_context, example_script, "helpful", feedback_key_strategy)
            if feedback_cols[1].button("👎", key="unhelpful_strategy", disabled=is_disabled_strategy):
                send_feedback(consultation_context, example_script, "not_helpful", feedback_key_strategy)

    st.markdown("##### 💬 추가 추천 멘트 옵션")
    for i, action in enumerate(result.get('recommended_actions', [])):
        with st.expander(f"**옵션 {i+1}: {action.get('style', '')}**"):
            script_text = action.get('script', '')
            st.write(script_text)
            feedback_key_action = f"feedback_for_action_{i}"
            is_disabled_action = st.session_state.feedback_status.get(feedback_key_action, False)
            feedback_cols_actions = st.columns(10)
            if feedback_cols_actions[0].button("👍", key=f"helpful_{i}", disabled=is_disabled_action):
                send_feedback(consultation_context, script_text, "helpful", feedback_key_action)
            if feedback_cols_actions[1].button("👎", key=f"unhelpful_{i}", disabled=is_disabled_action):
                send_feedback(consultation_context, script_text, "not_helpful", feedback_key_action)


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

def display_ai_coach_content():
    """AI 코칭 보조창의 메인 콘텐츠만 그리는 함수"""
    st.title("🚀 AI 실시간 코칭 보조창")
    st.markdown("고객과의 상담 내용을 입력하면, AI가 실시간으로 분석하고 코칭을 제공합니다.")
    input_text = st.text_area("여기에 고객과의 대화 내용을 붙여넣어 주세요.", height=250, key="text_input_key")
    if st.button("🤖 AI 코칭 시작하기", type="primary"):
        if input_text.strip():
            st.session_state['last_consultation_text'] = input_text
            with st.spinner('AI가 상담 내용을 분석 중입니다...'):
                try:
                    payload = {"consultation_text": input_text, "history": st.session_state.get('history', [])}
                    response = requests.post(f"{BACKEND_API_URL}/analyze", json=payload, timeout=60)
                    response_data = response.json()
                    if response.status_code == 200 and response_data.get("success"):
                        st.session_state.last_analysis = response_data.get("analysis")
                        st.session_state.history = response_data.get("history")
                        st.success("✅ AI 코칭 분석이 완료되었습니다!")
                    else: st.error(f"분석 실패: {response_data.get('error', '알 수 없는 오류')}")
                except Exception as e: st.error(f"분석 요청 중 오류가 발생했습니다: {e}")
        else:
            st.warning("분석할 상담 내용을 입력해주세요.")
    display_coaching_result(st.session_state.get('last_analysis'))

# --- 3. 앱의 메인 실행 로직 ---

# [수정됨] 세션 상태 초기화를 맨 위로 올려서, 스크립트 실행 시 항상 가장 먼저 실행되도록 보장합니다.
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.user_id = None
    st.session_state.history = []
    st.session_state.last_analysis = None
    st.session_state.feedback_status = {}
    st.session_state.last_consultation_text = ""

# [수정됨] 로그인 상태에 따라 보여줄 페이지를 명확하게 결정하는 최종 구조
if not st.session_state.logged_in:
    display_login_page()
else:
    # --- 로그인 후 공통 사이드바 ---
    with st.sidebar:
        st.header("📋 AI 상담 코치")
        st.write(f"**{st.session_state.get('username', '설계사')}**님, 환영합니다!")
        if st.button("✨ 새로운 상담 시작하기"):
            st.session_state.history = []; st.session_state.last_analysis = None
            st.session_state.feedback_status = {}; st.session_state.last_consultation_text = ""
            st.session_state.text_input_key = "" # 텍스트 입력창도 초기화
            st.rerun()
        if st.button("🚪 로그아웃"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    # --- 역할에 따른 메인 콘텐츠 ---
    if st.session_state.get("role") == 'admin':
        main_tab, admin_tab = st.tabs(["🚀 AI 코칭 보조창", "👑 관리자 페이지"])
        with main_tab:
            display_ai_coach_content()
        with admin_tab:
            admin_dashboard()
    else: # 일반 사용자의 경우
        display_ai_coach_content()