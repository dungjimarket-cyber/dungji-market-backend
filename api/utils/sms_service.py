import logging
from typing import Tuple, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

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
        
    def send_verification_code(self, phone_number: str, code: str) -> Tuple[bool, Optional[str]]:
        """인증 코드 SMS 발송
        
        Args:
            phone_number: 수신자 전화번호
            code: 6자리 인증 코드
            
        Returns:
            (성공여부, 에러메시지)
        """
        message = f"[둥지마켓] 인증번호는 {code}입니다. 3분 이내에 입력해주세요."
        
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
    
    def _send_mock_sms(self, phone_number: str, message: str) -> Tuple[bool, Optional[str]]:
        """개발용 Mock SMS 발송"""
        logger.info(f"[MOCK SMS] To: {phone_number}, Message: {message}")
        return True, None
    
    def _send_aligo_sms(self, phone_number: str, message: str) -> Tuple[bool, Optional[str]]:
        """알리고 SMS API 구현 예시"""
        # TODO: 실제 알리고 API 구현
        # import requests
        # 
        # url = "https://apis.aligo.in/send/"
        # data = {
        #     'key': self.api_key,
        #     'user_id': self.api_secret,
        #     'sender': self.sender_number,
        #     'receiver': phone_number,
        #     'msg': message,
        #     'msg_type': 'SMS'
        # }
        # 
        # response = requests.post(url, data=data)
        # result = response.json()
        # 
        # if result.get('result_code') == '1':
        #     return True, None
        # else:
        #     return False, result.get('message', 'SMS 발송 실패')
        
        return self._send_mock_sms(phone_number, message)
    
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