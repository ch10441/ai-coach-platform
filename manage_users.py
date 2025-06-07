# 파일명: manage_users.py (관리자 생성 기능 추가)
from app import app, db, User

def set_user_as_admin():
    username = input("관리자로 지정할 사용자의 아이디를 입력하세요: ")
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            user.role = 'ch10441'
            user.is_approved = True # 관리자는 바로 승인 상태로
            db.session.commit()
            print(f"✅ 성공! 사용자 '{username}'이(가) 관리자로 지정되었습니다.")
        else:
            print(f"🔥 오류: 사용자 '{username}'을(를) 찾을 수 없습니다.")

if __name__ == "__main__":
    # 사용법:
    # 1. 먼저 Streamlit 앱의 '팀원 등록' 탭에서 관리자로 사용할 계정을 하나 만듭니다.
    # 2. 그 다음, 이 스크립트를 실행하여 해당 계정을 관리자로 지정합니다.
    set_user_as_admin()