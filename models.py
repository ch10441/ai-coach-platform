# 파일명: models.py (사용자 정보가 확장된 최종 버전)

from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    # [추가됨] 새로운 사용자 정보 필드
    full_name = db.Column(db.String(100), nullable=False)
    branch_name = db.Column(db.String(100), nullable=False)
    gaia_code = db.Column(db.String(50), nullable=False)
    
    # [추가됨] 관리자 승인 여부 (기본값은 False로, 승인 대기 상태)
    is_approved = db.Column(db.Boolean, nullable=False, default=False)
    
    # [추가됨] 사용자 역할 (관리자/일반 사용자 구분)
    role = db.Column(db.String(20), nullable=False, default='user')

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # 어떤 사용자가 피드백을 남겼는지 기록 (User 테이블과 연결)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # 어떤 상담 내용에 대한 피드백인지 기록
    consultation_summary = db.Column(db.Text, nullable=False)
    # AI가 제안했던 어떤 멘트에 대한 피드백인지 기록
    ai_suggestion = db.Column(db.Text, nullable=False)
    # 피드백 내용 (좋아요/별로예요)
    rating = db.Column(db.String(20), nullable=False) # 'helpful' or 'not_helpful'
    # 피드백을 남긴 시간
    timestamp = db.Column(db.DateTime, default=db.func.now())

    # User와의 관계 설정
    user = db.relationship('User', backref=db.backref('feedbacks', lazy=True))
# ▲▲▲▲▲ 여기까지 추가 ▲▲▲▲▲