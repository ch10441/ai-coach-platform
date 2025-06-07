# 파일명: app.py (모든 초기화 로직이 통합된 최종 완성본)

import os
import json
import re
import google.generativeai as genai
import chromadb
from flask import Flask, request, jsonify
from flask_cors import CORS
from models import db, bcrypt, User
from services import AICoachingService
from dotenv import load_dotenv

# --- 1. Flask 앱 설정 ---
app = Flask(__name__)
CORS(app)

# --- 2. 환경변수 및 경로 설정 ---
load_dotenv()
DATA_DIR = "/data"
SQLALCHEMY_DB_PATH = os.path.join(DATA_DIR, 'users.db')
CHROMA_DB_PATH = os.path.join(DATA_DIR, 'chroma_db')
KNOWLEDGE_BASE_FILE = "knowledge_base.txt"
EMBEDDING_MODEL = 'models/text-embedding-004'
COLLECTION_NAME = "insurance_coach"

# --- 3. 데이터베이스 및 확장 기능 설정 ---
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{SQLALCHEMY_DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
bcrypt.init_app(app)

# --- 4. 앱 시작 시 실행될 초기화 함수 ---
def initialize_on_startup():
    """앱이 시작될 때 단 한 번, 모든 시스템을 올바른 순서로 준비합니다."""
    with app.app_context():
        print("--- [시스템 초기화 시작] ---")
        
        # 1. Google API 키 설정
        print("1. Google API 키를 설정합니다...")
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("초기화 실패: GOOGLE_API_KEY 환경 변수를 찾을 수 없습니다.")
        genai.configure(api_key=api_key)
        print("✅ Google API 키 설정 완료.")

        # 2. 사용자 정보 DB 테이블 생성 확인
        print("2. 사용자 DB 테이블을 확인 및 생성합니다...")
        db.create_all()
        print("✅ 사용자 DB 테이블 준비 완료.")

        # 3. RAG 벡터 DB 생성 확인
        print("3. RAG 벡터 DB를 확인 및 생성합니다...")
        try:
            client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
            if COLLECTION_NAME not in [c.name for c in client.list_collections()]:
                print(f"'{COLLECTION_NAME}' 컬렉션이 없어 새로 생성합니다...")
                collection = client.create_collection(name=COLLECTION_NAME)
                with open(KNOWLEDGE_BASE_FILE, "r", encoding="utf-8") as f:
                    chunks = [chunk.strip() for chunk in f.read().split("---") if chunk.strip()]
                if chunks:
                    embeddings = genai.embed_content(model=EMBEDDING_MODEL, content=chunks)['embedding']
                    collection.add(embeddings=embeddings, documents=chunks, ids=[f"chunk_{i}" for i in range(len(chunks))])
                    print(f"✅ RAG DB에 {len(chunks)}개의 정보 저장 완료.")
                else:
                    print("지식 베이스 파일이 비어있습니다.")
            else:
                print("✅ RAG DB가 이미 존재합니다.")
        except Exception as e:
            print(f"🔥 RAG DB 설정 중 오류 발생: {e}")
            # 이 오류는 심각하므로 앱 실행을 중단시킬 수 있습니다.
            # 또는, ai_service 없이 실행되도록 할 수도 있습니다.
            raise e

        print("--- [시스템 초기화 성공] ---")

# --- 5. AI 서비스 인스턴스 생성 ---
ai_service = None
try:
    # 앱 컨텍스트 내에서 초기화 함수를 호출합니다.
    with app.app_context():
        initialize_on_startup()
    # 모든 초기화가 성공한 후에 AI 서비스를 생성합니다.
    ai_service = AICoachingService()
    print("✅ AI 코칭 서비스가 성공적으로 활성화되었습니다.")
except Exception as e:
    print(f"🔥 시스템 초기화 과정에서 심각한 오류가 발생했습니다: {e}")

# --- 6. API 엔드포인트들 ---
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


# --- 7. Flask 서버 실행 ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)