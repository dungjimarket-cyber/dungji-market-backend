"""
Django Admin SMS 테스트 발송 페이지
"""
from django.contrib import admin
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from api.utils.sms_service import SMSService
import random


class SMSTestAdmin(admin.ModelAdmin):
    """SMS 테스트 발송을 위한 가상 Admin"""

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@require_http_methods(["GET", "POST"])
def sms_test_view(request):
    """SMS 테스트 발송 뷰"""

    if request.method == "POST":
        phone_number = request.POST.get('phone_number', '').strip()
        sms_type = request.POST.get('sms_type', 'groupbuy')
        custom_message = request.POST.get('custom_message', '').strip()

        if not phone_number:
            return JsonResponse({
                'success': False,
                'error': '전화번호를 입력해주세요.'
            })

        # 직접 입력인 경우 메시지 확인
        if sms_type == 'custom' and not custom_message:
            return JsonResponse({
                'success': False,
                'error': '메시지 내용을 입력해주세요.'
            })

        # 전화번호 정규화
        normalized_phone = phone_number.replace('-', '').replace(' ', '')

        sms_service = SMSService()

        try:
            if sms_type == 'verification':
                # 인증번호 발송
                code = str(random.randint(100000, 999999))
                success, error = sms_service.send_verification_code(normalized_phone, code)
                message_preview = f"[둥지마켓] 인증번호는 {code}입니다. 3분 이내에 입력해주세요."

            elif sms_type == 'groupbuy':
                # 공구 마감 알림 발송 (구매자용)
                from django.conf import settings
                test_title = "[테스트] 둥지마켓 공구 테스트"
                frontend_url = getattr(settings, 'FRONTEND_URL', 'https://dungjimarket.com')
                my_deals_url = f"{frontend_url}/custom-deals/my"

                success, error = sms_service.send_custom_groupbuy_completion(
                    phone_number=normalized_phone,
                    title=test_title,
                    user=None,
                    custom_groupbuy=None
                )

                # 실제 발송되는 메시지 계산
                message_content = (
                    f"[둥지마켓] 공구 마감 완료!\n"
                    f"{test_title}\n"
                    f"참여하신 공구가 마감되었어요!\n"
                    f"* 할인혜택과 사용기간을 꼭 확인하세요\n"
                    f"바로가기: {my_deals_url}"
                )
                byte_length = sms_service.calculate_sms_length(message_content)
                msg_type = sms_service.get_message_type(message_content)
                message_preview = f"{message_content}\n\n[발송 정보: {msg_type} / {byte_length}바이트]"

            elif sms_type == 'groupbuy_seller':
                # 공구 마감 알림 발송 (판매자용)
                from django.conf import settings
                test_title = "[테스트] 둥지마켓 공구 테스트"
                test_participants = 5
                test_price = 50000

                success, error = sms_service.send_custom_groupbuy_completion_seller(
                    phone_number=normalized_phone,
                    title=test_title,
                    participants_count=test_participants,
                    final_price=test_price,
                    discount_rate=None,
                    user=None,
                    custom_groupbuy=None
                )
                message_preview = f"[둥지마켓] 공구 마감 알림 (판매자)\n{test_title}\n참여자: {test_participants}명\n최종가: {test_price:,}원\n참여자에게 할인정보가 전달되었습니다.\n관리: {getattr(settings, 'FRONTEND_URL', 'https://dungjimarket.com')}/custom-deals/my"

            else:  # custom
                # 직접 입력 메시지 발송
                from api.utils.sms_service import log_sms

                # Mock SMS 발송 (알리고 API 직접 호출)
                if sms_service.provider == 'mock':
                    success, error = sms_service._send_mock_sms(normalized_phone, custom_message)
                elif sms_service.provider == 'aligo':
                    success, error = sms_service._send_aligo_sms(normalized_phone, custom_message)
                else:
                    success, error = sms_service._send_mock_sms(normalized_phone, custom_message)

                # 로그 저장
                log_sms(
                    phone_number=normalized_phone,
                    message_type='custom',
                    message_content=custom_message,
                    status='success' if success else 'failed',
                    error_message=error,
                    user=None,
                    custom_groupbuy=None
                )

                message_preview = custom_message

            if success:
                return JsonResponse({
                    'success': True,
                    'message': f'SMS가 성공적으로 발송되었습니다.\n수신번호: {phone_number}',
                    'preview': message_preview
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': error or 'SMS 발송에 실패했습니다.'
                })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'오류가 발생했습니다: {str(e)}'
            })

    # GET 요청 - 폼 표시
    context = {
        'title': 'SMS 테스트 발송',
        'site_header': admin.site.site_header,
        'site_title': admin.site.site_title,
        'has_permission': True,
    }

    return render(request, 'admin/sms_test.html', context)
