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


def polish_consultation_content(category_name: str, selections: list, additional_content: str = "") -> dict:
    """
    탭 선택 결과를 자연스러운 문장으로 다듬기

    Args:
        category_name: 업종명 (예: "세무사", "변호사")
        selections: 선택된 내용 목록 [{"step": 1, "question": "...", "answer": "..."}, ...]
        additional_content: 추가 입력 내용

    Returns:
        {
            "polished_content": "다듬어진 상담 내용",
            "raw_summary": "선택 내용 요약"
        }
    """
    # 선택 내용을 요약
    raw_parts = []
    for sel in selections:
        question = sel.get('question', '')
        answer = sel.get('answer', '')
        if answer:
            raw_parts.append(f"{question}: {answer}")

    raw_summary = " / ".join(raw_parts)
    if additional_content:
        raw_summary += f" / 추가사항: {additional_content}"

    # API 키가 없으면 원본 반환
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not configured, returning raw summary")
        return {
            "polished_content": raw_summary,
            "raw_summary": raw_summary
        }

    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        # 선택 내용을 구조화
        selection_text = "\n".join([
            f"- {sel.get('question', '')}: {sel.get('answer', '')}"
            for sel in selections
            if sel.get('answer')
        ])

        prompt = f"""당신은 전문 상담 접수 담당자입니다.

**업종**: {category_name}

**고객이 선택한 내용**:
{selection_text}

**추가 입력 내용**:
{additional_content if additional_content else "(없음)"}

**작업**:
위 선택 내용을 바탕으로 전문가에게 전달할 상담 요청 문장을 작성해주세요.
- 2-4문장으로 자연스럽게 작성
- 선택한 내용을 모두 포함
- 존댓말 사용
- 구체적이고 명확하게

**예시** (세무사):
"개인사업자로 연매출 3천만원~1억 규모의 사업을 운영하고 있습니다. 종합소득세 신고 대행을 신규로 의뢰하고자 합니다. 기존 세무사 없이 처음 맡기는 것이며, 빠른 처리가 필요합니다."

**응답 형식**:
다듬어진 문장만 작성하세요. 다른 설명 없이 문장만 응답합니다."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 고객의 상담 요청을 정리하는 전문가입니다. 간결하고 명확한 문장으로 작성합니다."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.4,
            max_tokens=200,
            timeout=15
        )

        polished = response.choices[0].message.content.strip()

        # 따옴표로 감싸져 있으면 제거
        if polished.startswith('"') and polished.endswith('"'):
            polished = polished[1:-1]

        logger.info(f"AI 문장 다듬기 완료: {category_name}")

        return {
            "polished_content": polished,
            "raw_summary": raw_summary
        }

    except openai.APIError as e:
        logger.error(f"OpenAI API 오류: {e}")
        return {
            "polished_content": raw_summary,
            "raw_summary": raw_summary
        }
    except openai.APITimeoutError:
        logger.error("OpenAI API 타임아웃")
        return {
            "polished_content": raw_summary,
            "raw_summary": raw_summary
        }
    except Exception as e:
        logger.error(f"AI 문장 다듬기 오류: {e}")
        return {
            "polished_content": raw_summary,
            "raw_summary": raw_summary
        }


def generate_consultation_flow(category_name: str, keywords: str = "", reference_text: str = "") -> dict:
    """
    AI로 상담 질문 플로우 생성

    Args:
        category_name: 업종명 (예: "세무사", "변호사")
        keywords: 참고할 키워드 (예: "종소세, 법인세, 부가세")
        reference_text: 참고할 기존 플로우나 텍스트

    Returns:
        {
            "success": True/False,
            "flows": [
                {
                    "step_number": 1,
                    "question": "질문 텍스트",
                    "is_required": True,
                    "depends_on_step": null,
                    "depends_on_options": [],
                    "options": [
                        {"key": "option_key", "label": "표시 텍스트", "icon": "🔹", "description": "설명"}
                    ]
                }
            ],
            "error": "에러 메시지" (실패 시)
        }
    """
    if not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not configured")
        return {
            "success": False,
            "error": "API 키가 설정되지 않았습니다."
        }

    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        prompt = f"""당신은 상담 접수 시스템 설계 전문가입니다.

**업종**: {category_name}

**참고 키워드** (있는 경우):
{keywords if keywords else "(없음)"}

**참고 텍스트** (있는 경우):
{reference_text if reference_text else "(없음)"}

**작업**:
"{category_name}" 업종의 무료 상담 신청을 위한 질문 플로우를 설계해주세요.

**요구사항**:
1. 3~5개의 질문 단계로 구성
2. 첫 번째 질문은 "어떤 도움이 필요하세요?" 형태의 핵심 니즈 파악
3. 각 질문에는 3~6개의 선택지 제공
4. 마지막 선택지는 "직접 입력" 옵션 (is_custom_input: true)
5. 필요한 경우 조건부 질문 설정 (이전 답변에 따라 표시)

**응답 형식 (JSON)**:
{{
    "flows": [
        {{
            "step_number": 1,
            "question": "어떤 도움이 필요하세요?",
            "is_required": true,
            "depends_on_step": null,
            "depends_on_options": [],
            "options": [
                {{"key": "option_1", "label": "옵션1", "icon": "📋", "description": "설명"}},
                {{"key": "custom", "label": "직접 입력", "icon": "✏️", "description": "", "is_custom_input": true}}
            ]
        }},
        {{
            "step_number": 2,
            "question": "후속 질문",
            "is_required": true,
            "depends_on_step": 1,
            "depends_on_options": ["option_1"],
            "options": [...]
        }}
    ]
}}

**규칙**:
- key는 영문 소문자와 언더스코어만 사용 (예: tax_return, legal_advice)
- icon은 관련 이모지 하나 사용
- 각 질문의 선택지는 상호 배타적이어야 함
- JSON 형식으로만 응답하세요"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 상담 접수 시스템 설계 전문가입니다. 항상 유효한 JSON 형식으로만 응답합니다."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.4,
            max_tokens=2000,
            timeout=30
        )

        result_text = response.choices[0].message.content.strip()

        # JSON 파싱
        try:
            # 코드 블록 제거
            if result_text.startswith('```'):
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
            result_text = result_text.strip()

            result = json.loads(result_text)
        except json.JSONDecodeError as e:
            logger.warning(f"AI 응답 JSON 파싱 실패: {e}, 원본: {result_text[:500]}")
            return {
                "success": False,
                "error": "AI 응답을 파싱할 수 없습니다."
            }

        flows = result.get('flows', [])

        # 플로우 검증 및 정리
        validated_flows = []
        for idx, flow in enumerate(flows):
            validated_flow = {
                "step_number": flow.get('step_number', idx + 1),
                "question": flow.get('question', ''),
                "is_required": flow.get('is_required', True),
                "depends_on_step": flow.get('depends_on_step'),
                "depends_on_options": flow.get('depends_on_options', []),
                "options": []
            }

            for opt_idx, opt in enumerate(flow.get('options', [])):
                validated_flow["options"].append({
                    "key": opt.get('key', f'option_{opt_idx}'),
                    "label": opt.get('label', ''),
                    "icon": opt.get('icon', ''),
                    "logo": opt.get('logo', ''),
                    "description": opt.get('description', ''),
                    "is_custom_input": opt.get('is_custom_input', False),
                    "order_index": opt_idx
                })

            validated_flows.append(validated_flow)

        logger.info(f"AI 플로우 생성 완료: {category_name} - {len(validated_flows)}개")

        return {
            "success": True,
            "flows": validated_flows
        }

    except openai.APIError as e:
        logger.error(f"OpenAI API 오류: {e}")
        return {
            "success": False,
            "error": f"API 오류: {str(e)}"
        }
    except openai.APITimeoutError:
        logger.error("OpenAI API 타임아웃")
        return {
            "success": False,
            "error": "API 응답 시간 초과"
        }
    except Exception as e:
        logger.error(f"AI 플로우 생성 오류: {e}")
        return {
            "success": False,
            "error": str(e)
        }
