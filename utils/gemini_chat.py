import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
_model = genai.GenerativeModel("gemini-2.0-flash-lite")


def build_context(search_result):
    """DB 검색 결과를 Gemini에 넘길 텍스트로 변환"""
    lines = []

    if search_result.get("products"):
        lines.append("【관련 상품】")
        for p in search_result["products"]:
            lines.append(
                f"- {p['상품코드']} | {p['상품판매명']}"
                f" | 갱신: {p.get('자동갱신가능여부','?')}"
                f" | 최대가입연령: {p.get('상품최대가입연령','?')}"
                f" | 보험기간: {p.get('보험기간기본값','?')}"
            )

    if search_result.get("coverages"):
        lines.append("\n【관련 담보】")
        for c in search_result["coverages"]:
            구분 = "기본" if c.get("담보기본특약구분코드") == "01" else "특약"
            lines.append(
                f"- [{구분}] {c['담보코드']} {c['담보대표명']}"
                f" (상품: {c['상품코드']} {c['상품판매명']})"
            )

    if not lines:
        return "관련 데이터를 찾지 못했습니다."

    return "\n".join(lines)


def ask(user_question, db_context_text):
    """Gemini에 질의하고 답변 텍스트 반환"""
    prompt = f"""당신은 보험회사 상품 관리팀의 AI 어시스턴트입니다.
아래 DB 조회 결과를 바탕으로 팀원의 질문에 한국어로 친절하고 정확하게 답변하세요.
DB에 없는 정보는 "데이터가 없습니다"라고 솔직하게 말하세요.

[DB 조회 결과]
{db_context_text}

[팀원 질문]
{user_question}

[답변]"""

    try:
        response = _model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 응답 생성 중 오류가 발생했습니다: {e}"
