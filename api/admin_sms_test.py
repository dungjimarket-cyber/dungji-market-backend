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

        if not phone_number:
            return JsonResponse({
                'success': False,
                'error': '전화번호를 입력해주세요.'
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
            else:
                # 공구 마감 알림 발송
                test_title = "[테스트] 둥지마켓 공구 테스트"
                success, error = sms_service.send_custom_groupbuy_completion(
                    phone_number=normalized_phone,
                    title=test_title,
                    user=None,
                    custom_groupbuy=None
                )
                message_preview = f"[둥지마켓] 공구 마감 완료!\n{test_title}\n참여하신 공구가 마감되었어요!\n✅ 할인혜택과 사용기간을 꼭 확인하세요"

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
