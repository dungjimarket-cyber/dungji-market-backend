"""
AI 기반 리뷰 요약 유틸리티
OpenAI GPT-4o-mini를 사용하여 Google 리뷰를 요약
"""
import openai
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def generate_business_summary(reviews_data: list, business_name: str) -> tuple:
    """
    Google 리뷰를 기반으로 AI 요약 생성

    Args:
        reviews_data: 리뷰 객체 리스트 [{"text": "...", "rating": 5}, ...]
        business_name: 업체명

    Returns:
        (summary, error_message) 튜플
        - success: (summary_text, None)
        - failure: (None, error_message)
    """
    if not reviews_data or len(reviews_data) == 0:
        logger.info(f"No reviews for {business_name}, skipping AI summary")
        return (None, "리뷰 데이터 없음")

    if not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not configured")
        return (None, "OpenAI API 키 미설정")

    try:
        # OpenAI 클라이언트 초기화
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        # 최대 5개 리뷰만 사용 (토큰 절약)
        reviews_to_use = reviews_data[:5]

        # 리뷰 텍스트 포맷팅
        reviews_text = '\n\n'.join([
            f"- (평점 {review.get('rating', 0)}/5) {review.get('text', '')[:200]}"  # 각 리뷰 최대 200자
            for review in reviews_to_use
            if review.get('text')  # 텍스트가 있는 리뷰만
        ])

        if not reviews_text.strip():
            logger.info(f"No text reviews for {business_name}, skipping AI summary")
            return (None, "텍스트 리뷰 없음 (평점만 존재)")

        # 프롬프트 구성
        prompt = f"""다음은 "{business_name}"에 대한 고객 리뷰입니다.
이 리뷰들을 바탕으로 이 업체의 특징과 장점을 요약해주세요.

**요구사항:**
- 최대 50-60자 이내 (2줄 분량)
- 핵심 장점 1-2가지만 간결하게
- 긍정적이고 객관적인 톤
- 과장 금지

리뷰:
{reviews_text}

요약 (50-60자):"""

        # OpenAI API 호출 (GPT-4o-mini: 가장 저렴한 최신 모델)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 비즈니스 리뷰를 분석하고 요약하는 전문가입니다. 50-60자 이내로 핵심만 간결하게 요약합니다."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=80,  # 50-60자면 충분 (한글은 토큰당 1-2자)
            temperature=0.7,  # 적당한 창의성
            timeout=15  # 15초 타임아웃 (대량 처리 시 여유)
        )

        summary = response.choices[0].message.content.strip()

        # 로그 기록
        logger.info(f"✅ AI summary generated for {business_name}: {summary[:50]}...")

        return (summary, None)

    except openai.APIError as e:
        error_msg = f"OpenAI API 오류: {str(e)}"
        logger.error(f"{error_msg} for {business_name}")
        return (None, error_msg)
    except openai.APITimeoutError as e:
        error_msg = f"OpenAI 타임아웃 (15초 초과)"
        logger.error(f"{error_msg} for {business_name}")
        return (None, error_msg)
    except Exception as e:
        error_msg = f"예상치 못한 오류: {str(e)}"
        logger.error(f"{error_msg} for {business_name}")
        return (None, error_msg)
