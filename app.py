import os
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from models import db, bcrypt, User, Feedback
from services import AICoachingService

# 1. Flask 앱 및 DB 설정
app = Flask(__name__)
CORS(app)
load_dotenv()
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
bcrypt.init_app(app)


# 2. 앱 시작 시 사용자 DB 테이블 생성 확인
with app.app_context():
    db.create_all()
    print("✅ 사용자 DB 테이블이 준비되었습니다.") 

# 3. AI 서비스 초기화 실행
ai_service = None
try:
    # 이 한 줄만으로 services.py 안에서 모든 초기화(API키, Pinecone, RAG DB)가 진행됩니다.
    ai_service = AICoachingService()
except Exception as e:
    print(f"🔥 시스템 전체 초기화 과정에서 오류가 발생했습니다: {e}")

# --- 4. API 엔드포인트들 ---
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    required_fields = ['username', 'password', 'full_name', 'branch_name', 'gaia_code']
    if not all(field in data and data[field] for field in required_fields):
        return jsonify({"success": False, "error": "모든 항목을 입력해야 합니다."}), 400
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"success": False, "error": "이미 존재하는 아이디입니다."}), 409
    
    # 비밀번호 규칙 검사 로직 (이전 답변에서 누락된 부분을 복원)
    password = data['password']
    if len(password) < 8 or not re.search(r"[a-zA-Z]", password) or not re.search(r"\d", password) or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return jsonify({"success": False, "error": "비밀번호는 8자리 이상, 영문, 숫자, 특수문자를 모두 포함해야 합니다."}), 400

    new_user = User(username=data['username'], full_name=data['full_name'], branch_name=data['branch_name'], gaia_code=data['gaia_code'])
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"success": True, "message": f"'{data['full_name']}' 님의 계정 등록이 요청되었습니다. 관리자 승인 후 사용 가능합니다."}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"success": False, "error": "아이디와 비밀번호가 필요합니다."}), 400
    user = User.query.filter_by(username=data['username']).first()
    if user and user.check_password(data['password']):
        if not user.is_approved:
            return jsonify({"success": False, "error": "계정이 아직 관리자의 승인을 기다리고 있습니다."}), 403
        return jsonify({"success": True, "message": "로그인 성공!", "user": {"username": user.username, "role": user.role}})
    else:
        return jsonify({"success": False, "error": "아이디 또는 비밀번호가 일치하지 않습니다."}), 401

@app.route('/admin/users', methods=['GET'])
def get_all_users():
    """DB에 있는 모든 사용자 목록을 반환합니다."""
    try:
        users = User.query.all()
        user_list = [
            {"id": u.id, "username": u.username, "full_name": u.full_name, 
             "branch_name": u.branch_name, "gaia_code": u.gaia_code, 
             "is_approved": u.is_approved, "role": u.role}
            for u in users
        ]
        return jsonify({"success": True, "users": user_list})
    except Exception as e:
        print(f"🔥 /admin/users API 오류: {e}")
        return jsonify({"success": False, "error": "사용자 목록을 불러오는 중 서버 오류 발생"}), 500

@app.route('/admin/approve/<int:user_id>', methods=['POST'])
def approve_user(user_id):
    """특정 사용자의 is_approved 상태를 True로 변경합니다."""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"success": False, "error": "사용자를 찾을 수 없습니다."}), 404
        user.is_approved = True
        db.session.commit()
        return jsonify({"success": True, "message": f"사용자 '{user.username}'이(가) 승인되었습니다."})
    except Exception as e:
        print(f"🔥 /admin/approve API 오류: {e}")
        return jsonify({"success": False, "error": "계정 승인 중 서버 오류 발생"}), 500

@app.route('/admin/delete/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """특정 사용자를 DB에서 삭제합니다."""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"success": False, "error": "사용자를 찾을 수 없습니다."}), 404
        
        if user.role == 'admin':
            return jsonify({"success": False, "error": "관리자 계정은 삭제할 수 없습니다."}), 403

        db.session.delete(user)
        db.session.commit()
        return jsonify({"success": True, "message": f"사용자 '{user.username}'이(가) 삭제되었습니다."})
    except Exception as e:
        print(f"🔥 /admin/delete API 오류: {e}")
        return jsonify({"success": False, "error": "계정 삭제 중 서버 오류 발생"}), 500
    
def handle_feedback():
    """프론트엔드에서 받은 피드백을 데이터베이스에 저장합니다."""
    data = request.get_json()
    required_fields = ['user_id', 'consultation_summary', 'ai_suggestion', 'rating']
    if not all(field in data for field in required_fields):
        return jsonify({"success": False, "error": "피드백 데이터가 부족합니다."}), 400

    try:
        with app.app_context():
            # User.query.get()은 기본 키(id)로 사용자를 찾는 더 효율적인 방법입니다.
            user = db.session.get(User, data['user_id'])
            if not user:
                return jsonify({"success": False, "error": "사용자를 찾을 수 없습니다."}), 404

            new_feedback = Feedback(
                user_id=user.id,
                consultation_summary=data['consultation_summary'],
                ai_suggestion=data['ai_suggestion'],
                rating=data['rating']
            )
            db.session.add(new_feedback)
            db.session.commit()

        return jsonify({"success": True, "message": "피드백이 성공적으로 기록되었습니다."}), 201

    except Exception as e:
        print(f"🔥 /feedback API 오류: {e}")
        return jsonify({"success": False, "error": "피드백 저장 중 서버 오류 발생"}), 500
# ▲▲▲▲▲ 여기까지 추가 ▲▲▲▲▲

@app.route('/analyze', methods=['POST'])
def analyze():
    if not ai_service:
        return jsonify({"success": False, "error": "AI 서비스가 초기화되지 않았습니다."}), 500
    try:
        data = request.get_json()
        if not data or 'consultation_text' not in data:
            return jsonify({"success": False, "error": "분석할 상담 내용(consultation_text)이 없습니다."}), 400
        consultation_text = data['consultation_text']
        history = data.get('history', [])
        coaching_result, new_history = ai_service.analyze_consultation(consultation_text, history)
        if coaching_result:
            return jsonify({"success": True, "analysis": coaching_result, "history": new_history})
        else:
            return jsonify({"success": False, "error": "AI가 분석 결과를 생성하는데 실패했습니다."}), 500
    except Exception as e:
        print(f"🔥 /analyze API 처리 중 심각한 오류 발생: {e}")
        return jsonify({"success": False, "error": "서버 내부 오류가 발생했습니다. 관리자에게 문의하세요."}), 500


# --- 5. Flask 개발 서버 실행 (로컬 테스트용) ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)