# 파일명: rag_service.py (ChromaDB 연동 버전)

import google.generativeai as genai
import chromadb

class RAGService:
    def __init__(self, collection_name="insurance_coach"):
        """서비스 초기화 시, ChromaDB에 연결하고 컬렉션을 가져옵니다."""
        print("RAG 서비스가 ChromaDB에 연결을 시도합니다...")
        client = chromadb.PersistentClient(path="./chroma_db")
        try:
            self.collection = client.get_collection(name=collection_name)
            print(f"✅ ChromaDB의 '{collection_name}' 컬렉션에 성공적으로 연결되었습니다.")
        except ValueError:
            # 만약 컬렉션이 없다면 오류를 발생시켜 build_database.py를 먼저 실행하도록 유도합니다.
            raise ValueError(f"오류: ChromaDB에서 '{collection_name}' 컬렉션을 찾을 수 없습니다. 'build_database.py'를 먼저 실행하여 데이터베이스를 생성해주세요.")

        self.embedding_model = 'models/text-embedding-004'

    def retrieve_relevant_knowledge(self, query, top_k=3):
        """사용자의 질문(query)과 가장 관련성 높은 지식을 ChromaDB에서 찾아서 반환합니다."""
        if not query.strip():
            return []

        # 1. 사용자의 질문을 벡터로 변환합니다.
        query_embedding = genai.embed_content(
            model=self.embedding_model,
            content=[query]
        )['embedding']

        # 2. ChromaDB에 쿼리하여 가장 유사한 텍스트 조각 top_k개를 검색합니다.
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k
        )

        # 검색된 문서(텍스트 조각)들을 리스트로 반환합니다.
        return results['documents'][0]