# 파일명: db_setup.py

import os
import chromadb
import google.generativeai as genai

COLLECTION_NAME = "insurance_coach"
DB_PATH = "/data/chroma_db"
KNOWLEDGE_BASE_FILE = "knowledge_base.txt"
EMBEDDING_MODEL = 'models/text-embedding-004'

def setup_database():
    """
    ChromaDB가 설정되어 있는지 확인하고, 없으면 새로 생성하는 함수
    """
    print("데이터베이스 설정 확인을 시작합니다...")
    client = chromadb.PersistentClient(path=DB_PATH)

    # 이미 같은 이름의 컬렉션이 있는지 확인
    if COLLECTION_NAME in [c.name for c in client.list_collections()]:
        print(f"✅ 데이터베이스 '{COLLECTION_NAME}'이(가) 이미 존재합니다. 초기화를 건너뜁니다.")
        return

    print(f"'{COLLECTION_NAME}' 컬렉션이 없습니다. 새로 생성합니다...")
    collection = client.create_collection(name=COLLECTION_NAME)

    try:
        with open(KNOWLEDGE_BASE_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        chunks = [chunk.strip() for chunk in content.split("---") if chunk.strip()]
        print(f"지식 베이스 파일에서 {len(chunks)}개의 정보 조각을 로드했습니다.")
    except FileNotFoundError:
        print(f"🔥 오류: '{KNOWLEDGE_BASE_FILE}' 파일을 찾을 수 없습니다.")
        return

    if not chunks:
        print("지식 베이스에 내용이 없어 데이터베이스를 채우지 않습니다.")
        return

    print("정보 조각들을 벡터로 변환 중입니다...")
    embeddings = genai.embed_content(model=EMBEDDING_MODEL, content=chunks)['embedding']
    print("벡터 변환 완료.")

    print("벡터 데이터베이스에 데이터를 저장 중입니다...")
    collection.add(
        embeddings=embeddings,
        documents=chunks,
        ids=[f"chunk_{i}" for i in range(len(chunks))]
    )
    print(f"✅ 성공! {len(chunks)}개의 정보가 벡터 데이터베이스에 저장되었습니다.")