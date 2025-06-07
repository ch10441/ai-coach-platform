# 파일명: build_database.py

import google.generativeai as genai
import os
import chromadb
from dotenv import load_dotenv

# .env 파일에서 API 키 로드
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("API 키를 찾을 수 없습니다. .env 파일을 확인하세요.")
genai.configure(api_key=GOOGLE_API_KEY)

def build_chroma_db(knowledge_base_path="knowledge_base.txt", collection_name="insurance_coach"):
    """
    텍스트 파일로부터 지식 베이스를 읽어 ChromaDB 컬렉션을 생성하고 데이터를 저장합니다.
    """
    print("ChromaDB 클라이언트를 초기화합니다...")
    # ChromaDB 클라이언트를 초기화합니다. 데이터는 'chroma_db' 폴더에 저장됩니다.
    client = chromadb.PersistentClient(path="/data/chroma_db")

    # 기존에 같은 이름의 컬렉션이 있다면 삭제하고 새로 만듭니다.
    if collection_name in [c.name for c in client.list_collections()]:
        client.delete_collection(name=collection_name)
        print(f"기존 컬렉션 '{collection_name}'을(를) 삭제했습니다.")

    collection = client.create_collection(name=collection_name)
    print(f"새로운 컬렉션 '{collection_name}'을(를) 생성했습니다.")

    # knowledge_base.txt 파일 읽기
    try:
        with open(knowledge_base_path, "r", encoding="utf-8") as f:
            content = f.read()
        chunks = [chunk.strip() for chunk in content.split("---") if chunk.strip()]
        print(f"지식 베이스 파일에서 {len(chunks)}개의 정보 조각을 로드했습니다.")
    except FileNotFoundError:
        print(f"오류: '{knowledge_base_path}' 파일을 찾을 수 없습니다.")
        return

    # 텍스트 조각들을 Embedding 모델을 사용해 벡터로 변환
    print("정보 조각들을 벡터로 변환 중입니다...")
    embedding_model = 'models/text-embedding-004'
    embeddings = genai.embed_content(model=embedding_model, content=chunks)['embedding']
    print("벡터 변환 완료.")

    # ChromaDB에 데이터 추가
    print("벡터 데이터베이스에 데이터를 저장 중입니다...")
    collection.add(
        embeddings=embeddings,
        documents=chunks,
        ids=[f"chunk_{i}" for i in range(len(chunks))]
    )
    print(f"✅ 성공! {len(chunks)}개의 정보가 벡터 데이터베이스에 저장되었습니다.")
    print(f"이제 'streamlit_app.py'를 실행하여 RAG 시스템을 사용할 수 있습니다.")

if __name__ == "__main__":
    build_chroma_db()