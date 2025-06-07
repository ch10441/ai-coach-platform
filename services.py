# 파일명: services.py (Pinecone RAG 적용 최종 버전)
import os
import json
import pinecone
import google.generativeai as genai
from dotenv import load_dotenv

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

        self.model = genai.GenerativeModel('gemini-1.5-pro-latest', generation_config={"response_mime_type": "application/json"})
        print("✅ AI 코칭 서비스가 (Pinecone과 함께) 성공적으로 초기화되었습니다.")

    def _initialize_pinecone_index(self):
        if self.index_name not in self.pinecone.list_indexes().names():
             raise ValueError(f"Pinecone에 '{self.index_name}' 인덱스가 없습니다. Pinecone 대시보드에서 먼저 생성해주세요.")
        
        self.index = self.pinecone.Index(self.index_name)
        stats = self.index.describe_index_stats()
        
        if stats['total_vector_count'] == 0:
            print(f"Pinecone 인덱스 '{self.index_name}'이 비어있어, 지식 베이스로 채웁니다...")
            try:
                with open("knowledge_base.txt", "r", encoding="utf-8") as f:
                    chunks = [c.strip() for c in f.read().split("---") if c.strip()]
                if chunks:
                    print(f"{len(chunks)}개의 정보 조각을 벡터로 변환하여 저장합니다...")
                    embeddings = genai.embed_content(model=self.embedding_model, content=chunks)['embedding']
                    self.index.upsert(vectors=[(f"chunk_{i}", emb, {"text": chunk}) for i, (emb, chunk) in enumerate(zip(embeddings, chunks))])
                    print("✅ Pinecone 인덱스에 데이터 저장 완료.")
            except FileNotFoundError:
                print("⚠️ 경고: knowledge_base.txt 파일을 찾을 수 없어 Pinecone을 초기화하지 못했습니다.")
            except Exception as e:
                print(f"🔥 Pinecone 초기화 중 오류: {e}")

    def retrieve_relevant_knowledge(self, query, top_k=3):
        if not query.strip(): return []
        query_embedding = genai.embed_content(model=self.embedding_model, content=[query])['embedding'][0]
        results = self.index.query(vector=query_embedding, top_k=top_k, include_metadata=True)
        return [match['metadata']['text'] for match in results['matches']]

    def _build_prompt(self, consultation_text, history, relevant_knowledge):
        # 프롬프트 내용은 이전 최종본과 동일합니다.
        history_str = "\n".join(history) if history else "없음"
        knowledge_str = "\n---\n".join(relevant_knowledge) if relevant_knowledge else "참고할 만한 전문가 지식 없음"
        return f"""
        [역할 및 페르소나]
        당신은 대한민국 최고의 보험 세일즈 전문가이자, 신입 설계사의 성장을 돕는 'AI 코칭 프로'입니다. 당신의 코칭 스타일은 심리학에 기반하여 고객의 마음을 얻는 것을 중요하게 생각하며, 항상 긍정적이고 전략적인 관점에서 조언합니다. 당신의 조언은 절대 딱딱하거나 사무적이지 않고, 실제 대화처럼 자연스럽고 따뜻해야 합니다.

        [반드시 지켜야 할 규칙]
        - 상담 내용에 명시적으로 언급되지 않은 정보는 절대 추측하거나 만들어내지 마세요.
        - [❗ 중요] 모든 추천 멘트("script")는 고객의 마음을 움직일 수 있도록, 최소 3줄에서 5줄 사이의 풍부하고 상세하며 진심이 담긴 내용으로 작성해주세요.
        - 고객의 말을 긍정적으로 재진술하며(예: "아, OOO에 대해 궁금하시군요!") 신뢰를 쌓는 화법을 사용하세요.
        - 법적 또는 규제상 민감할 수 있는 내용은 단정적으로 표현하지 말고, "일반적으로" 또는 "예를 들어"와 같은 표현을 사용하세요.
        - 분석이 불가능할 경우, 각 JSON 값에 '정보가 부족하여 분석할 수 없습니다'라고 명확히 응답하세요.

        [분석 절차]
        먼저, '이전 상담 맥락'과 '현재 상담 내용', 그리고 '분석에 참고할 전문가 지식'을 바탕으로 단계별로 신중하게 생각한 후, 그 최종 결론을 아래 JSON 형식에 맞춰 제공해주세요. 아래 제공된 '<모범 예시>'를 참고하여 답변의 스타일과 깊이를 학습하세요.

        [출력 JSON 형식 및 지침]
        {{
          "customer_intent": "고객의 가장 핵심적인 질문 의도나 니즈를 한 문장으로 요약",
          "customer_sentiment": "현재 고객의 감정 상태 (예: 궁금함, 우려함, 긍정적, 부정적, 신중함)",
          "customer_profile_guess": "지금까지의 대화를 바탕으로 추정한 고객 성향 (예: 분석형, 관계중시형, 신중형)",
          "three_stage_coverage_analysis": {{
              "stage_1_actual_cost_insurance": "실손의료보험에 대한 분석 (언급 시)",
              "stage_2_diagnosis_fund": "주요 진단비(암, 뇌, 심장)에 대한 분석 (언급 시)",
              "stage_3_surgery_fund": "수술비 보장에 대한 분석 (언급 시)"
          }},
          "recommended_actions": [
            {{"style": "공감 및 관계 형성", "script": "최소 3~5줄의 풍부하고 상세하며, 진심이 담긴 구체적인 멘트"}},
            {{"style": "논리적 설득 및 정보 제공", "script": "최소 3~5줄의 풍부하고 상세하며, 고객이 이해하기 쉬운 구체적인 멘트"}},
            {{"style": "다음 단계 유도 및 질문", "script": "최소 3~5줄의 풍부하고 상세하며, 자연스럽게 다음 대화를 이끌어내는 구체적인 질문 멘트"}}
          ],
          "next_step_strategy": "현재 상황에서 가장 효과적인 다음 상담 진행 방향 및 전략에 대한 간략한 조언"
        }}

        <모범 예시>
        [이전 상담 맥락]
        없음
        [현재 상담 내용]
        고객: 안녕하세요, 연금보험을 좀 알아보고 있는데요. 제가 지금부터 준비하기엔 너무 늦은 것 같기도 하고, 20년 넘게 돈을 내야 한다고 생각하니 솔직히 좀 부담스럽네요.
        [AI 코칭 결과]
        {{
          "customer_intent": "연금보험 가입의 필요성은 인지하고 있으나, 늦은 시작 시점과 장기 납입에 대한 부담감 및 두려움을 느끼고 있음.",
          "customer_sentiment": "부담감, 불안함",
          "customer_profile_guess": "신중형, 안정성 중시형",
          "three_stage_coverage_analysis": {{"stage_1_actual_cost_insurance": "언급된 정보 없음", "stage_2_diagnosis_fund": "언급된 정보 없음", "stage_3_surgery_fund": "언급된 정보 없음"}},
          "recommended_actions": [
            {{"style": "깊은 공감 및 부담감 해소", "script": "고객님, 그럼요. 20년이라는 시간이 길게 느껴지고 미래에 대한 큰 결정을 하시는 만큼, 부담감을 느끼시는 건 정말 당연한 마음입니다. 오히려 이렇게 신중하게 고민하시는 모습이 정말 멋져 보이세요. 그만큼 고객님의 미래를 소중하게 생각하고 계시다는 의미니까요."}},
            {{"style": "관점 전환 및 긍정적 재해석", "script": "사실 많은 분들이 고객님과 비슷한 시기에 비슷한 고민을 시작하세요. 반대로 생각해보면, 지금 관심을 가지신 덕분에 앞으로의 30년, 40년을 훨씬 더 안정적이고 풍요롭게 만드실 수 있는 가장 좋은 기회를 잡으신 거라고 생각합니다. '가장 빠를 때'는 바로 '지금'이니까요. ^^"}},
            {{"style": "구체적인 대안 제시 및 질문", "script": "물론 20년이라는 기간이 부담되실 수 있죠. 하지만 이건 어디까지나 예시일 뿐, 납입 기간이나 금액은 고객님의 계획과 상황에 맞춰 얼마든지 더 짧게, 또는 더 유연하게 조절할 수 있는 방법들이 있습니다. 혹시 괜찮으시다면, 고객님의 부담을 덜어드릴 수 있는 몇 가지 현실적인 방법에 대해 먼저 설명해 드려도 될까요?"}}
          ],
          "next_step_strategy": "고객의 부담감을 먼저 깊이 공감하여 심리적 장벽을 낮추는 것이 최우선입니다. 그 후, '늦었다'는 인식을 '지금이 적기'라는 긍정적 프레임으로 전환하고, '조절 가능하다'는 대안을 제시하여 고객이 다음 단계의 설명을 편안하게 들을 수 있도록 유도해야 합니다."
        }}
        </모범 예시>

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
        relevant_knowledge = self.retrieve_relevant_knowledge(consultation_text)
        prompt = self._build_prompt(consultation_text, history, relevant_knowledge)
        try:
            response = self.model.generate_content(prompt)
            coaching_result = json.loads(response.text)
            new_history = history + [f"---고객/설계사 대화---\n{consultation_text}", f"---AI 코칭 요약---\n고객 의도: {coaching_result.get('customer_intent')}"]
            return coaching_result, new_history
        except Exception as e:
            print(f"🔥 AI 분석 중 오류 발생 (services.py): {e}")
            return None, history