"""
금융결제원(KFTC) 오픈뱅킹 API 서비스
계좌 실명인증 기능 구현
"""

import logging
import requests
import hashlib
import base64
from datetime import datetime
from django.conf import settings
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class KFTCService:
    """금융결제원 오픈뱅킹 API 서비스"""
    
    # API 엔드포인트
    BASE_URL = "https://testapi.openbanking.or.kr"  # 테스트 환경
    # BASE_URL = "https://openapi.openbanking.or.kr"  # 운영 환경
    
    # API 경로
    TOKEN_PATH = "/oauth/2.0/token"
    INQUIRY_REAL_NAME_PATH = "/v2.0/inquiry/real_name"
    
    def __init__(self):
        """KFTC 서비스 초기화"""
        self.client_id = getattr(settings, 'KFTC_CLIENT_ID', '14d022c3-0039-4df9-bb3a-dc8391beb4a9')
        self.client_secret = getattr(settings, 'KFTC_CLIENT_SECRET', '9ff0b139-8d1b-4e6f-ae20-d7fd7493ec90')
        self.use_test_mode = getattr(settings, 'KFTC_TEST_MODE', True)
        
        if self.use_test_mode:
            self.base_url = "https://testapi.openbanking.or.kr"
        else:
            self.base_url = "https://openapi.openbanking.or.kr"
    
    def _get_access_token(self) -> Optional[str]:
        """
        액세스 토큰 발급
        """
        try:
            url = f"{self.base_url}{self.TOKEN_PATH}"
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'oob',
                'grant_type': 'client_credentials'
            }
            
            response = requests.post(url, headers=headers, data=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            if 'access_token' in result:
                logger.info("KFTC 액세스 토큰 발급 성공")
                return result['access_token']
            else:
                logger.error(f"KFTC 액세스 토큰 발급 실패: {result}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"KFTC 토큰 발급 중 네트워크 오류: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"KFTC 토큰 발급 중 예외 발생: {str(e)}")
            return None
    
    def _generate_bank_tran_id(self) -> str:
        """
        은행거래고유번호 생성
        형식: 이용기관코드(10자리) + 생성주체구분코드(1자리) + 생성일자(9자리) + 일련번호(9자리)
        """
        # 테스트 환경에서는 고정된 이용기관코드 사용
        org_code = "T991666190"  # 테스트 이용기관코드
        subject_code = "U"  # 이용기관 생성
        date_str = datetime.now().strftime("%Y%m%d%H")  # YYYYMMDDHH
        
        # 일련번호는 시간 기반으로 생성 (마이크로초 활용)
        seq = str(int(datetime.now().timestamp() * 1000000))[-9:]
        
        return f"{org_code}{subject_code}{date_str}{seq}"
    
    def verify_account(
        self,
        bank_code: str,
        account_num: str,
        account_holder_info: str,
        tran_dtime: Optional[str] = None
    ) -> Tuple[bool, Dict]:
        """
        계좌 실명 조회
        
        Args:
            bank_code: 은행 코드
            account_num: 계좌 번호
            account_holder_info: 생년월일(YYMMDD) 또는 사업자등록번호
            tran_dtime: 거래일시 (없으면 현재시각 사용)
        
        Returns:
            (성공여부, 결과 딕셔너리)
        """
        try:
            # 액세스 토큰 발급
            access_token = self._get_access_token()
            if not access_token:
                return False, {'error': '액세스 토큰 발급 실패'}
            
            # 거래일시 생성
            if not tran_dtime:
                tran_dtime = datetime.now().strftime("%Y%m%d%H%M%S")
            
            # 은행거래고유번호 생성
            bank_tran_id = self._generate_bank_tran_id()
            
            # API 호출
            url = f"{self.base_url}{self.INQUIRY_REAL_NAME_PATH}"
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
            
            # 요청 파라미터
            params = {
                'bank_tran_id': bank_tran_id,
                'bank_code_std': bank_code,
                'account_num': account_num.replace('-', ''),  # 하이픈 제거
                'account_holder_info': account_holder_info,
                'tran_dtime': tran_dtime
            }
            
            logger.info(f"KFTC 계좌 실명 조회 요청: 은행코드={bank_code}, 계좌번호={account_num[:4]}****")
            
            response = requests.post(url, headers=headers, json=params, timeout=10)
            
            # 응답 처리
            result = response.json()
            
            # 응답 코드 확인
            if result.get('rsp_code') == 'A0000':
                # 성공
                account_holder_name = result.get('account_holder_name', '')
                
                logger.info(f"KFTC 계좌 실명 조회 성공: 예금주명={account_holder_name}")
                
                return True, {
                    'success': True,
                    'account_holder_name': account_holder_name,
                    'bank_code': bank_code,
                    'account_num': account_num,
                    'bank_tran_id': bank_tran_id,
                    'message': '계좌 실명 인증이 완료되었습니다.'
                }
            else:
                # 실패
                error_msg = result.get('rsp_message', '알 수 없는 오류')
                logger.warning(f"KFTC 계좌 실명 조회 실패: {error_msg}")
                
                return False, {
                    'success': False,
                    'error': error_msg,
                    'error_code': result.get('rsp_code'),
                    'message': f'계좌 실명 인증 실패: {error_msg}'
                }
                
        except requests.RequestException as e:
            logger.error(f"KFTC API 호출 중 네트워크 오류: {str(e)}")
            return False, {
                'success': False,
                'error': '네트워크 오류가 발생했습니다.',
                'message': 'API 서버와의 통신 중 오류가 발생했습니다.'
            }
        except Exception as e:
            logger.error(f"KFTC 계좌 실명 조회 중 예외 발생: {str(e)}")
            return False, {
                'success': False,
                'error': str(e),
                'message': '계좌 인증 중 오류가 발생했습니다.'
            }
    
    def verify_account_with_name(
        self,
        bank_code: str,
        account_num: str,
        account_holder_name: str,
        account_holder_info: str
    ) -> Tuple[bool, Dict]:
        """
        계좌 실명 조회 및 예금주명 검증
        
        Args:
            bank_code: 은행 코드
            account_num: 계좌 번호
            account_holder_name: 예금주명 (검증용)
            account_holder_info: 생년월일(YYMMDD) 또는 사업자등록번호
        
        Returns:
            (성공여부, 결과 딕셔너리)
        """
        # 계좌 실명 조회
        success, result = self.verify_account(bank_code, account_num, account_holder_info)
        
        if not success:
            return False, result
        
        # 예금주명 일치 여부 확인
        verified_name = result.get('account_holder_name', '')
        
        # 공백 제거 후 비교
        if verified_name.replace(' ', '') != account_holder_name.replace(' ', ''):
            logger.warning(f"예금주명 불일치: 입력={account_holder_name}, 조회={verified_name}")
            return False, {
                'success': False,
                'error': '예금주명이 일치하지 않습니다.',
                'message': '입력하신 예금주명과 계좌의 예금주명이 일치하지 않습니다.',
                'input_name': account_holder_name,
                'verified_name': verified_name
            }
        
        return True, result


# 싱글톤 인스턴스
kftc_service = KFTCService()