"""
OpenAI를 활용한 상담 플로우 자동 생성
"""
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def generate_consultation_flow(category_name: str, additional_prompt: str = '') -> dict:
    """
    OpenAI를 사용하여 상담 플로우 생성

    Args:
        category_name: 업종 이름 (예: "세무사", "변호사")
        additional_prompt: 추가 지시사항

    Returns:
        {
            'success': bool,
            'flows': list,  # 생성된 플로우 데이터
            'error': str,   # 에러 메시지 (실패 시)
        }
    """
    try:
        import openai

        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            return {'success': False, 'error': 'OpenAI API 키가 설정되지 않았습니다.'}

        client = openai.OpenAI(api_key=api_key)

        system_prompt = """당신은 상담 플로우 설계 전문가입니다.
사용자가 지정한 업종에 맞는 상담 질문 플로우를 JSON 형식으로 생성해주세요.

규칙:
1. 목적 중심 설계: 첫 질문은 "어떤 도움이 필요하세요?" 형태로 고객의 니즈를 파악
2. 조건부 질문: 이전 선택에 따라 다른 질문을 표시 (depends_on_step, depends_on_options 사용)
3. 3-5단계 정도의 질문으로 구성
4. 마지막에 직접 입력 옵션 제공 (is_custom_input: true)
5. 적절한 이모지 아이콘 사용

출력 형식 (JSON):
{
  "flows": [
    {
      "step_number": 1,
      "question": "어떤 도움이 필요하세요?",
      "is_required": true,
      "depends_on_step": null,
      "depends_on_options": [],
      "options": [
        {"key": "option_key", "label": "선택지 라벨", "icon": "📋", "description": "설명 (선택)"},
        {"key": "custom", "label": "직접 입력", "icon": "📝", "is_custom_input": true}
      ]
    },
    {
      "step_number": 2,
      "question": "구체적인 상황은?",
      "is_required": true,
      "depends_on_step": 1,
      "depends_on_options": ["option_key"],
      "options": [...]
    }
  ]
}

실제 플랫폼(세무통, 로톡, 짐싸, 집닥 등)의 상담 질문 패턴을 참고하세요."""

        user_prompt = f"""업종: {category_name}

이 업종에 맞는 상담 질문 플로우를 생성해주세요.
고객이 무엇을 원하는지 파악하고, 적절한 세부 질문으로 이어지도록 설계해주세요.

{additional_prompt if additional_prompt else ''}

JSON 형식으로만 응답해주세요."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        flows = result.get('flows', [])

        if not flows:
            return {'success': False, 'error': 'AI가 플로우를 생성하지 못했습니다.'}

        return {
            'success': True,
            'flows': flows,
        }

    except ImportError:
        return {'success': False, 'error': 'openai 패키지가 설치되지 않았습니다.'}
    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 오류: {e}")
        return {'success': False, 'error': 'AI 응답 파싱 실패'}
    except Exception as e:
        logger.exception("AI 플로우 생성 오류")
        return {'success': False, 'error': str(e)}


def improve_consultation_flow(category_name: str, current_flows: list, improvement_prompt: str) -> dict:
    """
    기존 플로우를 개선

    Args:
        category_name: 업종 이름
        current_flows: 현재 플로우 데이터
        improvement_prompt: 개선 지시사항

    Returns:
        {
            'success': bool,
            'flows': list,
            'error': str,
        }
    """
    try:
        import openai

        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            return {'success': False, 'error': 'OpenAI API 키가 설정되지 않았습니다.'}

        client = openai.OpenAI(api_key=api_key)

        system_prompt = """당신은 상담 플로우 개선 전문가입니다.
기존 상담 플로우를 분석하고 사용자의 지시에 따라 개선해주세요.

출력은 반드시 JSON 형식으로 해주세요:
{
  "flows": [...]
}"""

        user_prompt = f"""업종: {category_name}

현재 플로우:
{json.dumps(current_flows, ensure_ascii=False, indent=2)}

개선 요청: {improvement_prompt}

개선된 플로우를 JSON 형식으로 응답해주세요."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        flows = result.get('flows', [])

        return {
            'success': True,
            'flows': flows,
        }

    except Exception as e:
        logger.exception("AI 플로우 개선 오류")
        return {'success': False, 'error': str(e)}
