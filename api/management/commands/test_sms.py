"""
SMS 발송 테스트 명령어

사용법:
    # 공구 마감 알림 테스트
    python manage.py test_sms --type groupbuy --phone 010-1234-5678

    # 인증번호 테스트
    python manage.py test_sms --type verification --phone 010-1234-5678

    # 최근 SMS 로그 확인
    python manage.py test_sms --show-logs
"""

from django.core.management.base import BaseCommand
from api.utils.sms_service import SMSService
from api.models_custom import SMSLog
import random


class Command(BaseCommand):
    help = 'SMS 발송 테스트 및 로그 확인'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['groupbuy', 'verification'],
            help='SMS 유형 (groupbuy: 공구마감, verification: 인증번호)'
        )
        parser.add_argument(
            '--phone',
            type=str,
            help='수신자 전화번호 (예: 010-1234-5678)'
        )
        parser.add_argument(
            '--show-logs',
            action='store_true',
            help='최근 SMS 로그 10개 표시'
        )

    def handle(self, *args, **options):
        sms_type = options.get('type')
        phone = options.get('phone')
        show_logs = options.get('show_logs')

        # 로그 확인
        if show_logs:
            self.show_recent_logs()
            return

        # 발송 테스트
        if not sms_type or not phone:
            self.stdout.write(
                self.style.ERROR('--type과 --phone 옵션이 필요합니다.')
            )
            self.stdout.write('\n사용법:')
            self.stdout.write('  python manage.py test_sms --type groupbuy --phone 010-1234-5678')
            self.stdout.write('  python manage.py test_sms --show-logs')
            return

        # 전화번호 정규화
        normalized_phone = phone.replace('-', '').replace(' ', '')

        self.stdout.write(f'\n{"="*60}')
        self.stdout.write(f'SMS 발송 테스트')
        self.stdout.write(f'{"="*60}\n')

        sms_service = SMSService()

        if sms_type == 'verification':
            # 인증번호 테스트
            code = str(random.randint(100000, 999999))
            self.stdout.write(f'📱 수신자: {phone}')
            self.stdout.write(f'🔢 인증번호: {code}')
            self.stdout.write(f'📤 발송 중...\n')

            success, error = sms_service.send_verification_code(normalized_phone, code)

            if success:
                self.stdout.write(self.style.SUCCESS('✅ 발송 성공!'))
            else:
                self.stdout.write(self.style.ERROR(f'❌ 발송 실패: {error}'))

        elif sms_type == 'groupbuy':
            # 공구 마감 알림 테스트
            test_title = "[테스트] 둥지마켓 공구 테스트"
            self.stdout.write(f'📱 수신자: {phone}')
            self.stdout.write(f'📦 공구명: {test_title}')
            self.stdout.write(f'📤 발송 중...\n')

            success, error = sms_service.send_custom_groupbuy_completion(
                phone_number=normalized_phone,
                title=test_title,
                user=None,  # 테스트용이므로 None
                custom_groupbuy=None  # 테스트용이므로 None
            )

            if success:
                self.stdout.write(self.style.SUCCESS('✅ 발송 성공!'))
            else:
                self.stdout.write(self.style.ERROR(f'❌ 발송 실패: {error}'))

        self.stdout.write(f'\n{"="*60}\n')

        # 방금 발송한 로그 확인
        self.stdout.write('📋 최근 발송 로그:')
        self.show_recent_logs(limit=1)

    def show_recent_logs(self, limit=10):
        """최근 SMS 로그 표시"""
        logs = SMSLog.objects.all().order_by('-sent_at')[:limit]

        if not logs:
            self.stdout.write(self.style.WARNING('발송 내역이 없습니다.'))
            return

        self.stdout.write(f'\n{"="*80}')
        self.stdout.write(f'최근 SMS 발송 내역 (최근 {limit}개)')
        self.stdout.write(f'{"="*80}\n')

        for i, log in enumerate(logs, 1):
            status_icon = '✅' if log.status == 'success' else '❌'
            status_color = self.style.SUCCESS if log.status == 'success' else self.style.ERROR

            self.stdout.write(f'\n[{i}] {status_icon} {log.sent_at.strftime("%Y-%m-%d %H:%M:%S")}')
            self.stdout.write(f'    전화번호: {log.phone_number}')
            self.stdout.write(f'    유형: {log.get_message_type_display()}')
            self.stdout.write(status_color(f'    상태: {log.get_status_display()}'))

            if log.user:
                self.stdout.write(f'    수신자: {log.user.username}')

            if log.custom_groupbuy:
                self.stdout.write(f'    관련 공구: {log.custom_groupbuy.title}')

            if log.error_message:
                self.stdout.write(self.style.ERROR(f'    오류: {log.error_message}'))

            # 메시지 미리보기 (첫 50자)
            preview = log.message_content[:50]
            if len(log.message_content) > 50:
                preview += '...'
            self.stdout.write(f'    내용: {preview}')

        self.stdout.write(f'\n{"="*80}\n')
        self.stdout.write(f'총 {logs.count()}개의 로그')
