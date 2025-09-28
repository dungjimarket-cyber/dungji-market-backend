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
            except Exception as e:
                logger.error(f"판매자 결정 시간 초과 처리 실패 ({groupbuy.title}): {str(e)}")