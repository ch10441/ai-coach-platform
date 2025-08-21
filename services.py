# 파일명: services.py (self 오류 해결된 최종 버전)

import os
import json
import pinecone
import google.generativeai as genai
from dotenv import load_dotenv
from pypdf import PdfReader
from docx import Document

# [수정됨] _chunk_text 함수를 클래스 바깥의 독립적인 '도우미 함수'로 만듭니다.
# 이제 이 함수는 'self'를 필요로 하지 않습니다.
def _chunk_text(text, chunk_size=2000, chunk_overlap=200):
    if not isinstance(text, str): return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - chunk_overlap
    return chunks

class AICoachingService:
    def __init__(self):
        load_dotenv()
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_env = os.getenv("PINECONE_ENVIRONMENT")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        if not all([self.pinecone_api_key, self.pinecone_env, self.google_api_key]):
            raise ValueError("API 키 또는 환경 변수가 설정되지 않았습니다.")
        genai.configure(api_key=self.google_api_key)
        self.pinecone = pinecone.Pinecone(api_key=self.pinecone_api_key)
        self.index_name = "insurance-coach"
        self.embedding_model = 'models/text-embedding-004'
        self._initialize_pinecone_index()
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite', generation_config={"response_mime_type": "application/json"})
        print("✅ AI 코칭 서비스가 (Pinecone과 함께) 성공적으로 초기화되었습니다.")

    def _initialize_pinecone_index(self):
        if self.index_name not in self.pinecone.list_indexes().names():
             raise ValueError(f"Pinecone에 '{self.index_name}' 인덱스가 없습니다. Pinecone 대시보드에서 먼저 생성해주세요.")
        self.index = self.pinecone.Index(self.index_name)
        stats = self.index.describe_index_stats()
        if stats['total_vector_count'] == 0:
            print(f"Pinecone 인덱스가 비어있어, 지식 베이스로 채웁니다...")
            KNOWLEDGE_DIR = "knowledge_files"
            all_chunks_with_source = []
            if os.path.exists(KNOWLEDGE_DIR):
                for filename in os.listdir(KNOWLEDGE_DIR):
                    filepath = os.path.join(KNOWLEDGE_DIR, filename)
                    full_text = ""
                    if filename.endswith(".pdf"):
                        try:
                            reader = PdfReader(filepath)
                            full_text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
                        except Exception as e: print(f"🔥 PDF 파일 '{filename}' 처리 중 오류: {e}")
                    elif filename.endswith(".docx"):
                        try:
                            doc = Document(filepath)
                            full_text = "\n".join([para.text for para in doc.paragraphs])
                        except Exception as e: print(f"🔥 DOCX 파일 '{filename}' 처리 중 오류: {e}")
                    if full_text.strip():
                        chunks_from_file = _chunk_text(full_text)
                        for chunk in chunks_from_file:
                            all_chunks_with_source.append({"text": chunk, "source": filename})
                        print(f"  - '{filename}' 파일에서 {len(chunks_from_file)}개의 정보 조각 생성 완료.")
            if all_chunks_with_source:
                print(f"총 {len(all_chunks_with_source)}개의 정보 조각을 벡터로 변환하여 저장합니다...")
                just_texts = [item['text'] for item in all_chunks_with_source]
                embeddings = genai.embed_content(model=self.embedding_model, content=just_texts)['embedding']
                vectors_to_upsert = []
                for i, (embedding, item) in enumerate(zip(embeddings, all_chunks_with_source)):
                    metadata = {"text": item['text'], "source_file": item['source']}
                    vectors_to_upsert.append(pinecone.Vector(id=f"doc_chunk_{i}", values=embedding, metadata=metadata))
                batch_size = 100
                for i in range(0, len(vectors_to_upsert), batch_size):
                    self.index.upsert(vectors=vectors_to_upsert[i:i + batch_size])
                print(f"✅ Pinecone 인덱스에 {len(vectors_to_upsert)}개의 정보 조각 저장 완료.")
        else:
            print(f"✅ RAG DB '{self.index_name}'에 이미 {stats['total_vector_count']}개의 데이터가 존재합니다.")

    def retrieve_relevant_knowledge(self, query, top_k=3):
        """사용자의 질문과 가장 관련성 높은 지식을 Pinecone에서 찾아 반환합니다."""
        if not query.strip(): return []
        try:
            query_embedding = genai.embed_content(model=self.embedding_model, content=[query])['embedding'][0]
            results = self.index.query(vector=query_embedding, top_k=top_k, include_metadata=True)
            return [match['metadata']['text'] for match in results['matches']]
        except Exception as e:
            print(f"🔥 Pinecone 검색 중 오류 발생: {e}")
            return []        
            

    def _summarize_if_needed(self, text, max_length=8000):
        if len(text) <= max_length: return text
        print(f"⚠️ 텍스트가 너무 길어({len(text)}자) 요약을 먼저 실행합니다...")
        summarizer_model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = f"다음은 매우 긴 보험 상담 내용입니다. 이 내용의 핵심적인 맥락, 고객의 주요 질문, 그리고 중요한 감정 변화를 놓치지 않으면서, 전체 내용을 5~7개의 핵심 문단으로 요약해주세요. 이 요약본은 다른 AI가 후속 분석을 하는 데 사용될 것입니다.\n---\n원본 텍스트:\n{text}\n---\n핵심 요약본:"
        try:
            response = summarizer_model.generate_content(prompt)
            summary = response.text
            print(f"✅ 요약 완료 (원래 길이: {len(text)}, 요약 길이: {len(summary)})")
            return summary
        except Exception as e:
            print(f"🔥 텍스트 요약 중 오류 발생: {e}")
            return text

    def _build_prompt(self, consultation_text, history, relevant_knowledge):
        # 프롬프트 내용은 이전 최종본과 동일합니다.
        history_str = "\n".join(history) if history else "없음"
        knowledge_str = "\n---\n".join(relevant_knowledge) if relevant_knowledge else "참고할 만한 전문가 지식 없음"
        return f"""
        [역할 및 페르소나]
        당신은 대한민국 최고의 보험 세일즈 전문가이자, 신입 설계사의 성장을 돕는 'AI 코칭 프로'입니다. 당신의 코칭 스타일은 심리학에 기반하여 고객의 마음을 얻는 것을 중요하게 생각하며, 항상 긍정적이고 전략적인 관점에서 조언합니다. 당신의 조언은 절대 딱딱하거나 사무적이지 않고, 실제 대화처럼 자연스럽고 따뜻해야 합니다.

        [반드시 지켜야 할 규칙]
        - 상담 내용에 명시적으로 언급되지 않은 정보는 절대 추측하거나 만들어내지 마세요.
        - [❗ 중요] `recommended_actions` 배열 안의 각 항목의 `style` 값은 반드시 서로 달라야 하며, '공감', '정보제공', '질문'의 세 가지 핵심 카테고리를 각각 대표해야 합니다.
        - [❗ 중요] 모든 추천 멘트("script")는 고객의 마음을 움직일 수 있도록, 최소 3줄에서 5줄 사이의 풍부하고 상세하며 진심이 담긴 내용으로 작성해주세요.
        - 법적 또는 규제상 민감할 수 있는 내용은 단정적으로 표현하지 말고, "일반적으로" 또는 "예를 들어"와 같은 표현을 사용하세요.
        - 분석이 불가능할 경우, 각 JSON 값에 '정보가 부족하여 분석할 수 없습니다'라고 명확히 응답하세요.
        - 멘트 스타일을 중복해서 만들지 마세요.

        [분석 절차 (매우 중요)]
        당신은 다음의 4단계 사고 과정을 반드시 순서대로 거쳐야 합니다.

        **1단계: 고객 심층 분석 (Deeper Customer Analysis)**
        - 고객의 현재 발언을 사실 그대로 분석합니다. 어떤 단어를 사용했는가? 무엇을 직접적으로 질문했는가?
        - 그 발언에 담긴 고객의 진짜 '감정(Sentiment)'과 '숨겨진 의도(Intent)'는 무엇인가?
        - 이전 대화 내용을 포함한 전체 맥락을 통해 고객의 '성향(Profile)'을 추론합니다. (예: 꼼꼼하게 따지는 분석형, 관계를 중시하는 우호형 등)

        **2단계: 맥락 및 데이터 연결 (Context & Data Connection)**
        - 1단계 분석 결과를, 제공된 '[분석에 참고할 전문가 지식 (RAG 결과)]'와 연결합니다.
        - "이 고객의 상황이 우리 회사의 성공/실패 사례 중 어떤 것과 유사한가?"
        - "이 고객의 질문에 답하기 위해, 우리 '비법 노트'에서 어떤 내용을 참고해야 하는가?"

        **3단계: 핵심 문제(반론) 정의 및 전략 수립 (Problem Definition & Strategy Formulation)**
        - 1, 2단계 분석을 종합하여, 현재 상담을 다음 단계로 진전시키기 위해 해결해야 할 '가장 중요한 핵심 문제' 또는 '예상되는 고객의 핵심 반론'을 한 문장으로 정의합니다.
        - 이 문제를 해결하기 위한 '대응 전략'을 수립합니다. (예: '비용 저항이므로, 가치에 초점을 맞춰 설명하는 전략', '결정장애를 보이므로, 선택지를 2개로 좁혀주는 전략' 등)

        **4단계: 최종 코칭 생성 (Generate Final Coaching)**
        - 위 3단계에서 수립된 전략을 바탕으로, 아래 [출력 JSON 형식]의 모든 항목을 구체적이고 실행 가능한 내용으로 채웁니다. 모든 내용은 지금까지의 단계별 사고 과정과 완벽하게 일치해야 합니다.
        ---

        [출력 JSON 형식 및 지침]
        {{
          "customer_intent": "고객의 가장 핵심적인 질문 의도나 니즈를 한 문장으로 요약",
          "customer_sentiment": "현재 고객의 감정 상태 (예: 궁금함, 우려함, 긍정적, 부정적, 신중함)",
          "customer_profile_guess": "지금까지의 대화를 바탕으로 추정한 고객 성향 (예: 분석형, 관계중시형, 신중형)",
          "objection_handling_strategy": {{
              "predicted_objection": "AI가 예측하는 고객의 다음 반론이나 망설임 포인트",
              "counter_strategy": "예측된 반론에 대한 대응 전략 요약",
              "example_script": "그 전략을 현장에서 바로 실행할 수 있는, 3~5줄의 설득력 있는 추천 멘트"
          }},
          "recommended_actions": [
            {{"style": "공감 및 관계 형성", "script": "최소 3~5줄의 풍부하고 상세하며, 진심이 담긴 구체적인 멘트"}},
            {{"style": "핵심 니즈 확인 질문", "script": "고객의 니즈를 더 명확히 하거나, 숨겨진 니즈를 발견하기 위한 구체적인 질문 멘트"}},
            {{"style": "논리적 설득 및 정보 제공", "script": "최소 3~5줄의 풍부하고 상세하며, 고객이 이해하기 쉬운 구체적인 멘트"}},
            {{"style": "다음 단계 유도 및 질문", "script": "최소 3~5줄의 풍부하고 상세하며, 자연스럽게 다음 대화를 이끌어내는 구체적인 질문 멘트"}}
          ],
          "next_step_strategy": "현재 상황에서 가장 효과적인 다음 상담 진행 방향 및 전략에 대한 조언"
        }}

        ---
        [분석에 참고할 전문가 지식 (RAG 결과)]
        {knowledge_str}
        ---
        [이전 상담 맥락]
        {history_str}
        ---
        [현재 상담 내용]
        {consultation_text}
        ---
        """

    def analyze_consultation(self, consultation_text, history):
        """상담 내용을 분석하고 최종 코칭 결과를 반환합니다."""
        error_message = None
        try:
            # RAG 검색
            relevant_knowledge = self.retrieve_relevant_knowledge(consultation_text)
            # 프롬프트 구성
            prompt = self._build_prompt(consultation_text, history, relevant_knowledge)
            # Gemini API 호출
            response = self.model.generate_content(prompt)
            
            if not response.parts:
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                    error_message = f"AI 답변이 안전 문제로 차단되었습니다: {response.prompt_feedback.block_reason.name}"
                else: error_message = "AI로부터 비어있는 응답을 받았습니다."
                raise ValueError(error_message)
            
            coaching_result = json.loads(response.text)
            new_history = history + [f"---고객/설계사 대화---\n{consultation_text}", f"---AI 코칭 요약---\n{coaching_result.get('customer_intent')}"]
            return coaching_result, new_history, None

        except Exception as e:
            final_error_message = error_message or f"AI 분석 중 알 수 없는 오류 발생: {e}"
            print(f"🔥 {final_error_message}")
            return None, history, final_error_message