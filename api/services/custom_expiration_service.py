from django.utils import timezone
from api.models_custom import CustomGroupBuy
import logging

logger = logging.getLogger(__name__)


class CustomExpirationService:

    @staticmethod
    def check_expired_groupbuys():
        now = timezone.now()
        recruiting_groupbuys = CustomGroupBuy.objects.filter(
            status='recruiting',
            expired_at__lte=now
        )

        for groupbuy in recruiting_groupbuys:
            try:
                groupbuy.check_expiration()
                logger.info(f"만료 체크 완료: {groupbuy.title}")
            except Exception as e:
                logger.error(f"만료 체크 실패 ({groupbuy.title}): {str(e)}")

    @staticmethod
    def check_seller_decision_deadline():
        from django.db import transaction

        now = timezone.now()
        pending_groupbuys = CustomGroupBuy.objects.filter(
            status='pending_seller',
            seller_decision_deadline__lte=now
        )

        for groupbuy in pending_groupbuys:
            try:
                with transaction.atomic():
                    # 참여자 정보 먼저 가져오기 (업데이트 전)
                    from api.models_custom import CustomParticipant
                    participants = list(CustomParticipant.objects.filter(
                        custom_groupbuy=groupbuy,
                        status='confirmed'
                    ).select_related('user'))

                    cancelled_count = groupbuy.participants.filter(
                        status='confirmed'
                    ).update(status='cancelled')

                    groupbuy.status = 'cancelled'
                    groupbuy.current_participants = 0
                    groupbuy.save()

                    logger.info(
                        f"판매자 결정 시간 초과로 취소: {groupbuy.title} - "
                        f"{cancelled_count}명 참여자 영향"
                    )

                    # SMS 발송
                    from api.utils.sms_service import SMSService
                    sms_service = SMSService()

                    # 판매자에게 SMS 발송
                    if hasattr(groupbuy.seller, 'phone_number') and groupbuy.seller.phone_number:
                        try:
                            short_title = groupbuy.title[:20] if len(groupbuy.title) > 20 else groupbuy.title
                            sms_message = f"[둥지마켓] {short_title} 공구가 판매결정시간 초과로 취소되었습니다({cancelled_count}명 참여)"
                            sms_service._send_aligo_sms(groupbuy.seller.phone_number, sms_message)
                            logger.info(f"판매자 SMS 발송 완료 (판매결정시간 초과): {groupbuy.seller.username}")
                        except Exception as sms_error:
                            logger.error(f"판매자 SMS 발송 실패 (판매결정시간 초과): {sms_error}")

                    # 참여자들에게 SMS 발송 (대량)
                    phone_numbers = []
                    for participant in participants:
                        if hasattr(participant.user, 'phone_number') and participant.user.phone_number:
                            phone_numbers.append(participant.user.phone_number)

                    if phone_numbers:
                        try:
                            short_title = groupbuy.title[:20] if len(groupbuy.title) > 20 else groupbuy.title
                            sms_message = f"[둥지마켓] {short_title} 공구가 판매결정시간 초과로 취소되었습니다"
                            sms_success_count, sms_fail_count = sms_service.send_bulk_sms(phone_numbers, sms_message)
                            logger.info(f"참여자 SMS 발송 완료 (판매결정시간 초과): 성공 {sms_success_count}건, 실패 {sms_fail_count}건")
                        except Exception as sms_error:
                            logger.error(f"참여자 SMS 발송 실패 (판매결정시간 초과): {sms_error}")

            except Exception as e:
                logger.error(f"판매자 결정 시간 초과 처리 실패 ({groupbuy.title}): {str(e)}")