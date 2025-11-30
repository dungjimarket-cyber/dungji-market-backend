"""
전문가 매칭 유틸리티
- 상담 요청 생성 시 매칭 전문가 찾기
- ConsultationMatch 생성
- 알림 발송
"""
import logging
from django.conf import settings
from django.db import transaction

from ..models_expert import ExpertProfile, ConsultationMatch

logger = logging.getLogger(__name__)

# 지역 매칭 활성화 여부 (기본값: 비활성화)
ENABLE_REGION_MATCHING = getattr(settings, 'ENABLE_REGION_MATCHING', False)


def get_matching_experts(consultation):
    """
    상담 요청에 맞는 전문가 목록 조회

    매칭 조건:
    1. 같은 카테고리
    2. 상태가 verified (승인됨)
    3. 상담 수신 활성화 상태
    4. (선택) 지역 매칭 - ENABLE_REGION_MATCHING 설정에 따라

    Args:
        consultation: ConsultationRequest 인스턴스

    Returns:
        QuerySet[ExpertProfile]: 매칭된 전문가 목록
    """
    queryset = ExpertProfile.objects.filter(
        status='verified',
        is_receiving_requests=True,
        category=consultation.category
    ).select_related('user')

    # 지역 매칭 (설정에 따라)
    if ENABLE_REGION_MATCHING and consultation.region:
        # 지역명에 포함되는 전문가 필터링
        # 예: "서울 강남구" → 서울 또는 강남구가 포함된 지역 담당 전문가
        region_parts = consultation.region.split()
        from django.db.models import Q
        region_filter = Q()
        for part in region_parts:
            if part:
                region_filter |= Q(regions__name__icontains=part)
                region_filter |= Q(regions__full_name__icontains=part)

        if region_filter:
            queryset = queryset.filter(region_filter).distinct()

    return queryset


def create_expert_matches(consultation):
    """
    상담 요청에 대한 전문가 매칭 생성

    Args:
        consultation: ConsultationRequest 인스턴스

    Returns:
        int: 생성된 매칭 수
    """
    # 매칭 전문가 조회
    experts = get_matching_experts(consultation)

    if not experts.exists():
        logger.info(f"상담 {consultation.id}: 매칭 전문가 없음 (카테고리: {consultation.category.name})")
        return 0

    # 매칭 생성
    matches_created = 0
    with transaction.atomic():
        for expert in experts:
            # 중복 매칭 방지
            match, created = ConsultationMatch.objects.get_or_create(
                consultation=consultation,
                expert=expert,
                defaults={
                    'status': 'pending'
                }
            )
            if created:
                matches_created += 1
                logger.debug(f"상담 {consultation.id}: 전문가 {expert.id} 매칭 생성")

    # 알림 발송 (별도 처리)
    if matches_created > 0:
        try:
            send_new_consultation_notifications(consultation, experts)
        except Exception as e:
            logger.error(f"상담 {consultation.id} 알림 발송 오류: {e}")
            # 알림 실패해도 매칭은 유지

    return matches_created


def send_new_consultation_notifications(consultation, experts):
    """
    새 상담 요청 알림 발송

    Args:
        consultation: ConsultationRequest 인스턴스
        experts: 전문가 목록
    """
    from ..models import Notification
    from .sms_service import SMSService

    sms_service = SMSService()

    for expert in experts:
        try:
            # 알림 메시지 생성
            message = f"새 {consultation.category.name} 상담 요청이 있습니다."
            if consultation.region:
                message += f" ({consultation.region})"

            # 인앱 알림 생성
            Notification.objects.create(
                user=expert.user,
                notification_type='consultation_new',
                message=message,
                item_type='consultation',
                item_id=consultation.id
            )

            # SMS 발송 - User.phone_number 우선 사용, 없으면 contact_phone
            phone_number = expert.user.phone_number or expert.contact_phone
            if phone_number:
                sms_service.send_consultation_new_expert(
                    phone_number,
                    consultation.category.name
                )

            logger.debug(f"전문가 {expert.id}에게 상담 알림 발송")

        except Exception as e:
            logger.error(f"전문가 {expert.id} 알림 발송 오류: {e}")
            continue


def send_consultation_replied_notification(match):
    """
    전문가 답변 알림 발송 (고객에게)

    Args:
        match: ConsultationMatch 인스턴스
    """
    from ..models import Notification, User
    from .sms_service import SMSService

    consultation = match.consultation
    expert = match.expert
    expert_name = expert.business_name or expert.representative_name

    sms_service = SMSService()

    try:
        # 고객 유저 찾기 (전화번호로)
        customer = User.objects.filter(phone_number=consultation.phone).first()

        if customer:
            message = f"{expert_name} 전문가가 상담에 답변했습니다."

            Notification.objects.create(
                user=customer,
                notification_type='consultation_replied',
                message=message,
                item_type='consultation',
                item_id=consultation.id
            )

            logger.info(f"고객 {customer.id}에게 답변 알림 발송")

        # SMS 발송 (회원/비회원 모두)
        sms_service.send_consultation_replied_customer(
            consultation.phone,
            expert_name
        )

    except Exception as e:
        logger.error(f"답변 알림 발송 오류: {e}")


def send_consultation_connected_notification(match):
    """
    상담 연결 알림 발송 (전문가에게)

    Args:
        match: ConsultationMatch 인스턴스
    """
    from ..models import Notification

    consultation = match.consultation
    expert = match.expert

    try:
        # 고객 이름 마스킹
        customer_name = consultation.name
        if len(customer_name) > 1:
            masked_name = customer_name[0] + '*' * (len(customer_name) - 1)
        else:
            masked_name = customer_name

        message = f"{masked_name}님과 상담이 연결되었습니다. 연락처를 확인하세요."

        Notification.objects.create(
            user=expert.user,
            notification_type='consultation_connected',
            message=message,
            item_type='consultation',
            item_id=consultation.id
        )

        logger.info(f"전문가 {expert.id}에게 연결 알림 발송")

    except Exception as e:
        logger.error(f"연결 알림 발송 오류: {e}")
