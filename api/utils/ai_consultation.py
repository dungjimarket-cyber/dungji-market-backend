"""
상담 내용 AI 정리 및 상담 유형 추천
OpenAI GPT-4o-mini 사용
"""
import json
import logging
import openai
from django.conf import settings

logger = logging.getLogger(__name__)


def get_consultation_assist(category_name: str, content: str, available_types: list) -> dict:
    """
    상담 내용 정리 및 적합한 상담 유형 추천

    Args:
        category_name: 업종명 (예: "세무사", "변호사")
        content: 사용자가 입력한 상담 내용
        available_types: 해당 업종의 상담 유형 리스트 [{"id": 1, "name": "종소세 신고"}, ...]

    Returns:
        {
            "summary": "정리된 상담 내용",
            "recommended_types": [{"id": 1, "name": "유형명", "relevance": 0.9}, ...]
        }
    """
    if not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not configured")
        return {
            "summary": content[:200],
            "recommended_types": available_types[:2] if available_types else []
        }

    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        # 상담 유형 이름만 추출
        type_names = [t['name'] for t in available_types]

        prompt = f"""당신은 전문 상담 접수 담당자입니다.

**업종**: {category_name}

**고객 문의 내용**:
{content}

**가능한 상담 유형**:
{', '.join(type_names)}

**작업**:
1. 고객의 문의 내용을 전문가가 이해하기 쉽게 2-3문장으로 정리해주세요.
2. 위 상담 유형 중 가장 적합한 것을 최대 3개까지 추천해주세요.

**응답 형식 (JSON)**:
{{
    "summary": "정리된 상담 내용 (2-3문장)",
    "recommended_types": ["유형1", "유형2"]
}}

중요: JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 전문 상담 접수 담당자입니다. 항상 유효한 JSON 형식으로만 응답합니다."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=300,
            timeout=15
        )

        result_text = response.choices[0].message.content.strip()

        # JSON 파싱 시도
        try:
            # 코드 블록 제거 (```json ... ``` 형태 대응)
            if result_text.startswith('```'):
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
            result_text = result_text.strip()

            result = json.loads(result_text)
        except json.JSONDecodeError as e:
            logger.warning(f"AI 응답 JSON 파싱 실패: {e}, 원본: {result_text}")
            return {
                "summary": content[:200],
                "recommended_types": []
            }

        # 추천 유형에 ID 매핑
        type_name_to_id = {t['name']: t['id'] for t in available_types}
        recommended = []

        for idx, type_name in enumerate(result.get('recommended_types', [])):
            if type_name in type_name_to_id:
                recommended.append({
                    "id": type_name_to_id[type_name],
                    "name": type_name,
                    "relevance": round(1.0 - (idx * 0.15), 2)  # 순서대로 relevance 감소
                })

        logger.info(f"AI 상담 정리 완료: {category_name}, 추천 {len(recommended)}개")

        return {
            "summary": result.get('summary', content[:200]),
            "recommended_types": recommended
        }

    except openai.APIError as e:
        logger.error(f"OpenAI API 오류: {e}")
        return {
            "summary": content[:200],
            "recommended_types": []
        }
    except openai.APITimeoutError:
        logger.error("OpenAI API 타임아웃")
        return {
            "summary": content[:200],
            "recommended_types": []
        }
    except Exception as e:
        logger.error(f"AI 상담 정리 오류: {e}")
        return {
            "summary": content[:200],
            "recommended_types": []
        }
