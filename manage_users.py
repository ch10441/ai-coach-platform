# 파일명: manage_users.py (메뉴 기능이 포함된 최종 완성본)

import getpass
from app import app, db, User

def add_user():
    """새로운 사용자를 데이터베이스에 추가하는 함수"""
    username = input("추가할 팀원의 아이디를 입력하세요: ")
    # 사용자가 이미 존재하는지 확인
    with app.app_context():
        if User.query.filter_by(username=username).first():
            print(f"🔥 오류: 아이디 '{username}'은(는) 이미 존재합니다.")
            return

    full_name = input(f"'{username}' 님의 전체 이름을 입력하세요: ")
    branch_name = input(f"'{username}' 님의 지점명을 입력하세요: ")
    gaia_code = input(f"'{username}' 님의 가이아 코드번호를 입력하세요: ")
    password = getpass.getpass("팀원의 초기 비밀번호를 입력하세요: ")
    password2 = getpass.getpass("비밀번호를 다시 한번 입력하세요: ")

    if password != password2:
        print("🔥 오류: 비밀번호가 일치하지 않습니다.")
        return

    with app.app_context():
        # is_approved는 기본값 False로 생성됨
        new_user = User(
            username=username,
            full_name=full_name,
            branch_name=branch_name,
            gaia_code=gaia_code
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        print(f"✅ 성공! 사용자 '{username}' 님이 등록 요청되었습니다. (승인 대기 상태)")

def list_users():
    """등록된 모든 사용자 목록을 보여주는 함수"""
    print("\n--- [등록된 사용자 목록] ---")
    with app.app_context():
        users = User.query.all()
        if not users:
            print("등록된 사용자가 없습니다.")
        for user in users:
            approved_status = "승인됨" if user.is_approved else "승인 대기중"
            print(f"- 아이디: {user.username}, 이름: {user.full_name}, 역할: {user.role}, 상태: {approved_status}")
    print("--------------------------")

def set_user_as_admin():
    """특정 사용자를 'admin' 역할로 지정하고 즉시 승인 처리하는 함수"""
    username = input("관리자로 지정할 사용자의 아이디를 입력하세요: ")
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            user.role = 'admin'
            user.is_approved = True # 관리자는 바로 승인 상태로 변경
            db.session.commit()
            print(f"✅ 성공! 사용자 '{username}' 님을 'admin' 역할로 지정하고 계정을 활성화했습니다.")
        else:
            print(f"🔥 오류: 사용자 '{username}' 님을 찾을 수 없습니다. 먼저 1번 메뉴에서 해당 계정을 생성했는지 확인해주세요.")

def main():
    """사용자 관리 메뉴를 보여주고 입력을 받는 메인 함수"""
    while True:
        print("\n[사용자 관리 메뉴 (서버 직접 제어)]")
        print("1. 팀원 추가하기")
        print("2. 등록된 팀원 목록 보기")
        print("3. 특정 팀원을 관리자로 지정하기")
        print("4. 종료")
        choice = input("원하시는 기능의 번호를 입력하세요: ")

        if choice == '1':
            add_user()
        elif choice == '2':
            list_users()
        elif choice == '3':
            set_user_as_admin()
        elif choice == '4':
            break
        else:
            print("🔥 잘못된 입력입니다. 1, 2, 3, 4 중 하나를 입력해주세요.")

if __name__ == "__main__":
    main()
