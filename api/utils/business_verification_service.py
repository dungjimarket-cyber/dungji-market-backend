"""
사업자번호 검증 서비스
국세청 사업자등록정보 진위확인 API를 사용하여 사업자번호를 검증합니다.
"""

import requests
import json
from django.conf import settings
from django.utils import timezone
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BusinessVerificationService:
    """사업자번호 검증 서비스"""
    
    # 국세청 사업자등록정보 상태조회 API (공공데이터포털)
    API_URL = "https://api.odcloud.kr/api/nts-businessman/v1/status"
    
    def __init__(self):
        # API 키는 Django settings에서 가져옴
        self.api_key = getattr(settings, 'BUSINESS_VERIFICATION_API_KEY', None)
        if not self.api_key:
            logger.warning("BUSINESS_VERIFICATION_API_KEY not set in settings")
    
    def verify_business_number(self, business_number, business_name=None):
        """
        사업자번호 검증 (국세청 상태조회 API 사용)
        
        Args:
            business_number (str): 사업자등록번호 (10자리)
            business_name (str): 상호명 (선택사항, 이 API에서는 사용되지 않음)
        
        Returns:
            dict: 검증 결과
                - success (bool): 검증 성공 여부
                - status (str): 상태 ('valid', 'invalid', 'error')
                - data (dict): 사업자 정보
                - message (str): 결과 메시지
        """
        
        if not self.api_key:
            return {
                'success': False,
                'status': 'error',
                'data': {},
                'message': 'API 키가 설정되지 않았습니다.',
                'api_response': {}
            }
        
        try:
            # 요청 데이터 구성 (공공데이터포털 스펙에 맞게)
            request_data = {
                "b_no": [business_number]  # 사업자등록번호 배열
            }
            
            # API 요청 (serviceKey는 URL 파라미터로)
            response = requests.post(
                self.API_URL,
                params={
                    'serviceKey': self.api_key,
                    'returnType': 'JSON'
                },
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                data=json.dumps(request_data),
                timeout=15
            )
            
            logger.info(f"Business verification API request: {business_number}")
            logger.info(f"API Response status: {response.status_code}")
            logger.info(f"API Response text: {response.text[:500]}")  # 처음 500자만 로그
            
            if response.status_code not in [200, 400]:  # 400도 처리 (데이터가 없는 경우)
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                return {
                    'success': False,
                    'status': 'error',
                    'data': {},
                    'message': f'API 요청 실패 (HTTP {response.status_code})',
                    'api_response': {'status_code': response.status_code, 'text': response.text}
                }
            
            # 응답 파싱
            try:
                api_response = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}, Response: {response.text}")
                return {
                    'success': False,
                    'status': 'error',
                    'data': {},
                    'message': 'API 응답 형식 오류',
                    'api_response': {'error': 'JSON decode failed', 'text': response.text}
                }
            
            logger.info(f"API Response data: {api_response}")
            
            # 에러 응답 처리
            if response.status_code == 400 or 'data' not in api_response:
                error_msg = api_response.get('message', '사업자번호를 찾을 수 없습니다.')
                return {
                    'success': False,
                    'status': 'invalid',
                    'data': {},
                    'message': error_msg,
                    'api_response': api_response
                }
            
            # 응답 데이터 확인
            if not api_response['data']:
                return {
                    'success': False,
                    'status': 'invalid',
                    'data': {},
                    'message': '등록되지 않은 사업자등록번호입니다.',
                    'api_response': api_response
                }
            
            # 첫 번째 사업자 정보 추출
            business_info = api_response['data'][0]
            
            # 사업자 상태 확인 (공공데이터포털 API 응답 구조에 맞게 수정)
            business_status_code = business_info.get('b_stt_cd', '')  # 사업자 상태 코드
            business_status_name = business_info.get('b_stt', '')     # 사업자 상태명
            tax_type = business_info.get('tax_type', '')              # 과세유형 메시지
            
            # 검증 결과 판단
            if business_status_code == '01':  # 계속사업자
                status = 'valid'
                message = '유효한 사업자등록번호입니다. (계속사업자)'
            elif business_status_code == '02':  # 휴업자  
                status = 'valid'
                message = '휴업 중인 사업자입니다.'
            elif business_status_code == '03':  # 폐업자
                status = 'invalid'
                message = '폐업한 사업자등록번호입니다.'
            else:
                # 기타 상태나 오류
                status = 'invalid'
                message = tax_type or '등록되지 않은 사업자등록번호입니다.'
            
            # 사업자 정보 추출 (API 응답에 따라)
            data = {
                'business_number': business_number,
                'business_name': tax_type,  # 과세유형 메시지에 상호명 정보가 포함됨
                'representative_name': '',  # 이 API에서는 제공되지 않음
                'business_status': business_status_name,
                'business_status_code': business_status_code,
                'business_type': business_info.get('utcc_yn', ''),  # 단위과세전환사업자 여부
                'establishment_date': None,  # 이 API에서는 제공되지 않음
                'address': '',  # 이 API에서는 제공되지 않음
                'end_date': business_info.get('end_dt', ''),  # 폐업일
                'tax_type': tax_type,  # 과세유형 메시지
                'tax_type_code': business_info.get('tax_type_cd', ''),  # 과세유형 코드
                'invoice_apply_date': business_info.get('invoice_apply_dt', ''),  # 세금계산서 적용일
            }
            
            return {
                'success': True,
                'status': status,
                'data': data,
                'message': message,
                'api_response': api_response
            }
            
        except requests.exceptions.Timeout:
            logger.error("Business verification API timeout")
            return {
                'success': False,
                'status': 'error',
                'data': {},
                'message': 'API 요청 시간이 초과되었습니다.',
                'api_response': {}
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Business verification API request error: {e}")
            return {
                'success': False,
                'status': 'error',
                'data': {},
                'message': 'API 요청 중 오류가 발생했습니다.',
                'api_response': {'error': str(e)}
            }
        except json.JSONDecodeError as e:
            logger.error(f"Business verification API JSON decode error: {e}")
            return {
                'success': False,
                'status': 'error',
                'data': {},
                'message': 'API 응답 파싱 오류가 발생했습니다.',
                'api_response': {'error': str(e)}
            }
        except Exception as e:
            logger.error(f"Business verification unexpected error: {e}")
            return {
                'success': False,
                'status': 'error',
                'data': {},
                'message': '예상치 못한 오류가 발생했습니다.',
                'api_response': {'error': str(e)}
            }
    
    def verify_and_save(self, user, business_number, business_name=None):
        """
        사업자번호 검증 후 데이터베이스에 저장
        
        Args:
            user: Django User 객체
            business_number (str): 사업자등록번호
            business_name (str): 상호명 (선택사항)
        
        Returns:
            BusinessNumberVerification: 생성된 검증 객체
        """
        from ..models_verification import BusinessNumberVerification
        
        # 형식 검증
        is_valid_format, clean_number_or_message = BusinessNumberVerification.validate_business_number_format(business_number)
        
        if not is_valid_format:
            # 형식이 잘못된 경우
            verification = BusinessNumberVerification.objects.create(
                user=user,
                business_number=business_number,
                status='invalid',
                error_message=clean_number_or_message
            )
            return verification
        
        # 형식이 올바른 경우 실제 검증 수행
        clean_number = clean_number_or_message
        result = self.verify_business_number(clean_number, business_name)
        
        # 검증 결과 저장
        verification_data = {
            'user': user,
            'business_number': clean_number,
            'status': result['status'],
            'api_response': result['api_response'],
        }
        
        if result['success']:
            verification_data.update({
                'verified_at': timezone.now(),
                'business_name': result['data'].get('business_name', ''),
                'representative_name': result['data'].get('representative_name', ''),
                'business_status': result['data'].get('business_status', ''),
                'business_type': result['data'].get('business_type', ''),
                'address': result['data'].get('address', ''),
            })
            
            # 개업일 파싱 (있는 경우)
            if result['data'].get('establishment_date'):
                try:
                    verification_data['establishment_date'] = datetime.strptime(
                        result['data']['establishment_date'], '%Y%m%d'
                    ).date()
                except ValueError:
                    pass
        else:
            verification_data['error_message'] = result['message']
        
        verification = BusinessNumberVerification.objects.create(**verification_data)
        
        # 사용자의 사업자번호 업데이트
        if result['success'] and result['status'] == 'valid':
            user.business_number = clean_number
            user.is_business_verified = True
            user.save()
        
        return verification