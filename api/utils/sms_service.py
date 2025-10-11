import logging
from typing import Tuple, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


def log_sms(phone_number: str, message_type: str, message_content: str,
            status: str, error_message: Optional[str] = None,
            user=None, custom_groupbuy=None):
    """SMS 발송 내역을 DB에 저장"""
    try:
        from api.models_custom import SMSLog

        SMSLog.objects.create(
            user=user,
            phone_number=phone_number,
            message_type=message_type,
            message_content=message_content,
            status=status,
            error_message=error_message,
            custom_groupbuy=custom_groupbuy
        )
    except Exception as e:
        logger.error(f"SMS 로그 저장 실패: {e}", exc_info=True)


class SMSService:
    """SMS 발송 서비스

    실제 구현 시 다음 서비스 중 하나를 선택하여 구현:
    - AWS SNS
    - Twilio
    - 알리고 (한국)
    - 솔루션박스 (한국)
    - LG U+ SMS API (한국)
    """

    def __init__(self):
        self.provider = getattr(settings, 'SMS_PROVIDER', 'mock')
        self.api_key = getattr(settings, 'SMS_API_KEY', '')
        self.api_secret = getattr(settings, 'SMS_API_SECRET', '')
        self.sender_number = getattr(settings, 'SMS_SENDER_NUMBER', '1234-5678')

    @staticmethod
    def calculate_sms_length(message: str) -> int:
        """SMS 메시지 바이트 길이 계산 (EUC-KR 기준)

        알리고 API는 EUC-KR 인코딩 사용:
        - 한글: 2바이트
        - 영문/숫자/기호: 1바이트
        """
        try:
            # EUC-KR로 인코딩하여 실제 바이트 길이 계산
            return len(message.encode('euc-kr'))
        except UnicodeEncodeError:
            # 인코딩 불가능한 문자가 있으면 UTF-8 길이로 근사치 계산
            return len(message.encode('utf-8'))

    @staticmethod
    def get_message_type(message: str) -> str:
        """메시지 길이에 따라 SMS 타입 자동 선택

        Returns:
            'SMS': 90바이트 이하 (단문)
            'LMS': 90바이트 초과 (장문, 최대 2000바이트)
        """
        byte_length = SMSService.calculate_sms_length(message)
        return 'LMS' if byte_length > 90 else 'SMS'
        
    def send_verification_code(self, phone_number: str, code: str) -> Tuple[bool, Optional[str]]:
        """인증 코드 SMS 발송

        Args:
            phone_number: 수신자 전화번호
            code: 6자리 인증 코드

        Returns:
            (성공여부, 에러메시지)
        """
        # 90바이트 이하로 최적화 (약 30바이트)
        message = f"[둥지마켓] 인증번호: {code}"

        try:
            if self.provider == 'mock':
                return self._send_mock_sms(phone_number, message)
            elif self.provider == 'aligo':
                return self._send_aligo_sms(phone_number, message)
            elif self.provider == 'twilio':
                return self._send_twilio_sms(phone_number, message)
            elif self.provider == 'aws_sns':
                return self._send_aws_sns_sms(phone_number, message)
            else:
                logger.error(f"Unknown SMS provider: {self.provider}")
                return False, "SMS 서비스 설정 오류"

        except Exception as e:
            logger.error(f"SMS 발송 실패: {e}", exc_info=True)
            return False, "SMS 발송 중 오류가 발생했습니다."

    def send_custom_groupbuy_completion(self, phone_number: str, title: str,
                                       user=None, custom_groupbuy=None) -> Tuple[bool, Optional[str]]:
        """커스텀 공구 마감 알림 SMS 발송

        Args:
            phone_number: 수신자 전화번호
            title: 공구 상품명
            user: 수신자 User 객체 (로그용, optional)
            custom_groupbuy: 관련 CustomGroupBuy 객체 (로그용, optional)

        Returns:
            (성공여부, 에러메시지)
        """
        # 90바이트 이하로 최적화 (약 77바이트)
        # 제목이 길 경우 자동으로 잘림
        max_title_length = 20  # 한글 10자 (20바이트)
        short_title = title[:max_title_length] if len(title) > max_title_length else title

        message = (
            f"[둥지마켓] 공구마감!\n"
            f"{short_title}\n"
            f"할인정보: dungjimarket.com/my"
        )

        try:
            if self.provider == 'mock':
                success, error = self._send_mock_sms(phone_number, message)
            elif self.provider == 'aligo':
                success, error = self._send_aligo_sms(phone_number, message)
            elif self.provider == 'twilio':
                success, error = self._send_twilio_sms(phone_number, message)
            elif self.provider == 'aws_sns':
                success, error = self._send_aws_sns_sms(phone_number, message)
            else:
                logger.error(f"Unknown SMS provider: {self.provider}")
                success, error = False, "SMS 서비스 설정 오류"

            # 발송 내역 로그 저장
            log_sms(
                phone_number=phone_number,
                message_type='groupbuy_completion',
                message_content=message,
                status='success' if success else 'failed',
                error_message=error,
                user=user,
                custom_groupbuy=custom_groupbuy
            )

            return success, error

        except Exception as e:
            error_msg = "SMS 발송 중 오류가 발생했습니다."
            logger.error(f"커스텀 공구 마감 알림 SMS 발송 실패: {e}", exc_info=True)

            # 예외 발생 시에도 로그 저장
            log_sms(
                phone_number=phone_number,
                message_type='groupbuy_completion',
                message_content=message,
                status='failed',
                error_message=str(e),
                user=user,
                custom_groupbuy=custom_groupbuy
            )

            return False, error_msg

    def send_custom_groupbuy_completion_seller(self, phone_number: str, title: str,
                                               participants_count: int, final_price: int = None,
                                               discount_rate: int = None,
                                               user=None, custom_groupbuy=None) -> Tuple[bool, Optional[str]]:
        """커스텀 공구 마감 알림 SMS 발송 (판매자용)

        Args:
            phone_number: 판매자 전화번호
            title: 공구 상품명
            participants_count: 참여자 수
            final_price: 최종 가격 (단일상품인 경우)
            discount_rate: 할인율 (전품목 할인인 경우)
            user: 판매자 User 객체 (로그용, optional)
            custom_groupbuy: 관련 CustomGroupBuy 객체 (로그용, optional)

        Returns:
            (성공여부, 에러메시지)
        """
        # 90바이트 이하로 최적화 (약 86바이트)
        # 제목이 길 경우 자동으로 잘림
        max_title_length = 16  # 한글 8자 (16바이트) - 판매자용은 더 짧게
        short_title = title[:max_title_length] if len(title) > max_title_length else title

        message = (
            f"[둥지마켓] 공구마감\n"
            f"{short_title}\n"
            f"참여:{participants_count}명\n"
            f"참여정보: dungjimarket.com/my"
        )

        try:
            if self.provider == 'mock':
                success, error = self._send_mock_sms(phone_number, message)
            elif self.provider == 'aligo':
                success, error = self._send_aligo_sms(phone_number, message)
            elif self.provider == 'twilio':
                success, error = self._send_twilio_sms(phone_number, message)
            elif self.provider == 'aws_sns':
                success, error = self._send_aws_sns_sms(phone_number, message)
            else:
                logger.error(f"Unknown SMS provider: {self.provider}")
                success, error = False, "SMS 서비스 설정 오류"

            # 발송 내역 로그 저장
            log_sms(
                phone_number=phone_number,
                message_type='groupbuy_completion_seller',
                message_content=message,
                status='success' if success else 'failed',
                error_message=error,
                user=user,
                custom_groupbuy=custom_groupbuy
            )

            return success, error

        except Exception as e:
            error_msg = "SMS 발송 중 오류가 발생했습니다."
            logger.error(f"판매자 공구 마감 알림 SMS 발송 실패: {e}", exc_info=True)

            # 예외 발생 시에도 로그 저장
            log_sms(
                phone_number=phone_number,
                message_type='groupbuy_completion_seller',
                message_content=message,
                status='failed',
                error_message=str(e),
                user=user,
                custom_groupbuy=custom_groupbuy
            )

            return False, error_msg

    def _send_mock_sms(self, phone_number: str, message: str) -> Tuple[bool, Optional[str]]:
        """개발용 Mock SMS 발송"""
        logger.info(f"[MOCK SMS] To: {phone_number}, Message: {message}")
        return True, None
    
    def _send_aligo_sms(self, phone_number: str, message: str, title: str = '[둥지마켓]') -> Tuple[bool, Optional[str]]:
        """알리고 SMS API 실제 구현

        Args:
            phone_number: 수신자 전화번호
            message: 메시지 내용
            title: LMS 제목 (LMS인 경우에만 사용)
        """
        import requests

        # 개발 모드에서는 Mock 사용
        if settings.DEBUG and not getattr(settings, 'USE_REAL_SMS', False):
            msg_type = self.get_message_type(message)
            byte_length = self.calculate_sms_length(message)
            logger.info(f"[알리고 개발모드] To: {phone_number}, Type: {msg_type}, Length: {byte_length}bytes")
            logger.info(f"[알리고 개발모드] Message: {message}")
            return True, None

        # 메시지 길이에 따라 SMS/LMS 자동 선택
        msg_type = self.get_message_type(message)
        byte_length = self.calculate_sms_length(message)

        logger.info(f"SMS 발송 시작: Type={msg_type}, Length={byte_length}bytes, To={phone_number}")

        url = "https://apis.aligo.in/send/"
        data = {
            'key': self.api_key,
            'user_id': getattr(settings, 'ALIGO_USER_ID', ''),
            'sender': self.sender_number,
            'receiver': phone_number.replace('-', ''),  # 하이픈 제거
            'msg': message,
            'msg_type': msg_type,  # 자동 선택된 타입 사용
        }

        # LMS인 경우에만 제목 추가
        if msg_type == 'LMS':
            data['title'] = title

        try:
            response = requests.post(url, data=data)
            result = response.json()

            if result.get('result_code') == '1':
                logger.info(f"SMS 발송 성공: {phone_number} (Type: {msg_type}, {byte_length}bytes)")
                return True, None
            else:
                error_msg = result.get('message', 'SMS 발송 실패')
                logger.error(f"알리고 SMS 발송 실패: {error_msg}")
                return False, error_msg
        except Exception as e:
            logger.error(f"알리고 API 오류: {e}", exc_info=True)
            return False, "SMS 발송 중 오류가 발생했습니다."
    
    def _send_twilio_sms(self, phone_number: str, message: str) -> Tuple[bool, Optional[str]]:
        """Twilio SMS API 구현 예시"""
        # TODO: 실제 Twilio API 구현
        # from twilio.rest import Client
        # 
        # client = Client(self.api_key, self.api_secret)
        # 
        # try:
        #     message = client.messages.create(
        #         body=message,
        #         from_=self.sender_number,
        #         to=phone_number
        #     )
        #     return True, None
        # except Exception as e:
        #     return False, str(e)
        
        return self._send_mock_sms(phone_number, message)
    
    def _send_aws_sns_sms(self, phone_number: str, message: str) -> Tuple[bool, Optional[str]]:
        """AWS SNS SMS API 구현 예시"""
        # TODO: 실제 AWS SNS API 구현
        # import boto3
        # 
        # sns_client = boto3.client(
        #     'sns',
        #     aws_access_key_id=self.api_key,
        #     aws_secret_access_key=self.api_secret,
        #     region_name='ap-northeast-2'
        # )
        # 
        # try:
        #     response = sns_client.publish(
        #         PhoneNumber=phone_number,
        #         Message=message,
        #         MessageAttributes={
        #             'AWS.SNS.SMS.SMSType': {
        #                 'DataType': 'String',
        #                 'StringValue': 'Transactional'
        #             }
        #         }
        #     )
        #     return True, None
        # except Exception as e:
        #     return False, str(e)
        
        return self._send_mock_sms(phone_number, message)
    
    @staticmethod
    def normalize_phone_number(phone_number: str) -> str:
        """전화번호 정규화
        
        010-1234-5678 -> 01012345678
        """
        return ''.join(filter(str.isdigit, phone_number))
    
    @staticmethod
    def format_phone_number(phone_number: str) -> str:
        """전화번호 포맷팅
        
        01012345678 -> 010-1234-5678
        """
        phone = SMSService.normalize_phone_number(phone_number)
        
        if len(phone) == 11:
            return f"{phone[:3]}-{phone[3:7]}-{phone[7:]}"
        elif len(phone) == 10:
            return f"{phone[:3]}-{phone[3:6]}-{phone[6:]}"
        else:
            return phone