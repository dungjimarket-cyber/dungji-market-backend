"""
파트너 은행계좌 관리 API
"""

import logging
from django.utils import timezone
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models_partner import Partner, PartnerBankAccount
from api.utils.kftc_service import kftc_service

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_bank_account(request):
    """
    파트너 은행계좌 등록 및 실명인증
    """
    try:
        # 파트너 확인
        try:
            partner = Partner.objects.get(user=request.user)
        except Partner.DoesNotExist:
            return Response({
                'error': '파트너 정보를 찾을 수 없습니다.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # 요청 데이터 추출
        bank_code = request.data.get('bank_code', '').strip()
        account_number = request.data.get('account_number', '').strip()
        account_holder_name = request.data.get('account_holder_name', '').strip()
        account_holder_info = request.data.get('account_holder_info', '').strip()  # 생년월일 또는 사업자번호
        is_business = request.data.get('is_business', False)
        
        # 필수 필드 검증
        if not all([bank_code, account_number, account_holder_name]):
            return Response({
                'error': '필수 정보를 모두 입력해주세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 은행명 매핑
        bank_names = {
            '002': '산업은행',
            '003': '기업은행',
            '004': 'KB국민은행',
            '005': '수협은행',
            '007': '수협중앙회',
            '011': 'NH농협은행',
            '012': '농협중앙회',
            '020': '우리은행',
            '023': 'SC제일은행',
            '027': '한국씨티은행',
            '031': '대구은행',
            '032': '부산은행',
            '034': '광주은행',
            '035': '제주은행',
            '037': '전북은행',
            '039': '경남은행',
            '045': '새마을금고',
            '048': '신협',
            '050': '저축은행',
            '064': '산림조합',
            '071': '우체국',
            '081': '하나은행',
            '088': '신한은행',
            '089': '케이뱅크',
            '090': '카카오뱅크',
            '092': '토스뱅크',
        }
        
        bank_name = bank_names.get(bank_code, '기타')
        
        # 기존 계좌 확인
        existing_account = PartnerBankAccount.objects.filter(partner=partner).first()
        
        # KFTC API를 통한 계좌 실명인증
        logger.info(f"계좌 실명인증 시작: 파트너={partner.company_name}, 은행={bank_name}, 계좌={account_number[:4]}****")
        
        # 실명인증 수행
        if account_holder_info:
            # 예금주 정보가 있는 경우 실명인증 수행
            success, verification_result = kftc_service.verify_account_with_name(
                bank_code=bank_code,
                account_num=account_number,
                account_holder_name=account_holder_name,
                account_holder_info=account_holder_info
            )
        else:
            # 예금주 정보가 없는 경우 기본 검증만
            success = False
            verification_result = {
                'error': '실명인증을 위한 정보가 부족합니다.',
                'message': '생년월일(YYMMDD) 또는 사업자등록번호를 입력해주세요.'
            }
        
        if success:
            # 인증 성공 - 계좌 정보 저장
            if existing_account:
                # 기존 계좌 업데이트
                existing_account.bank_code = bank_code
                existing_account.bank_name = bank_name
                existing_account.account_number = account_number
                existing_account.account_holder_name = account_holder_name
                existing_account.account_holder_info = account_holder_info
                existing_account.is_business = is_business
                existing_account.verification_status = 'verified'
                existing_account.verification_date = timezone.now()
                existing_account.verification_result = str(verification_result)
                existing_account.save()
                
                logger.info(f"계좌 정보 업데이트 완료: 파트너={partner.company_name}")
            else:
                # 새 계좌 생성
                existing_account = PartnerBankAccount.objects.create(
                    partner=partner,
                    bank_code=bank_code,
                    bank_name=bank_name,
                    account_number=account_number,
                    account_holder_name=account_holder_name,
                    account_holder_info=account_holder_info,
                    is_business=is_business,
                    verification_status='verified',
                    verification_date=timezone.now(),
                    verification_result=str(verification_result)
                )
                
                logger.info(f"새 계좌 등록 완료: 파트너={partner.company_name}")
            
            return Response({
                'success': True,
                'message': '계좌 실명인증이 완료되었습니다.',
                'account': {
                    'id': existing_account.id,
                    'bank_code': existing_account.bank_code,
                    'bank_name': existing_account.bank_name,
                    'account_number': existing_account.account_number,
                    'account_holder_name': existing_account.account_holder_name,
                    'verification_status': existing_account.verification_status,
                    'verification_date': existing_account.verification_date.isoformat() if existing_account.verification_date else None
                }
            })
        else:
            # 인증 실패 - 계좌 정보는 저장하되 인증 실패 상태로
            if existing_account:
                existing_account.bank_code = bank_code
                existing_account.bank_name = bank_name
                existing_account.account_number = account_number
                existing_account.account_holder_name = account_holder_name
                existing_account.account_holder_info = account_holder_info
                existing_account.is_business = is_business
                existing_account.verification_status = 'failed'
                existing_account.verification_date = timezone.now()
                existing_account.verification_result = str(verification_result)
                existing_account.save()
            else:
                existing_account = PartnerBankAccount.objects.create(
                    partner=partner,
                    bank_code=bank_code,
                    bank_name=bank_name,
                    account_number=account_number,
                    account_holder_name=account_holder_name,
                    account_holder_info=account_holder_info,
                    is_business=is_business,
                    verification_status='failed',
                    verification_date=timezone.now(),
                    verification_result=str(verification_result)
                )
            
            logger.warning(f"계좌 실명인증 실패: 파트너={partner.company_name}, 사유={verification_result.get('error', '알 수 없음')}")
            
            return Response({
                'success': False,
                'error': verification_result.get('error', '실명인증에 실패했습니다.'),
                'message': verification_result.get('message', '입력하신 정보를 다시 확인해주세요.'),
                'account': {
                    'id': existing_account.id,
                    'bank_code': existing_account.bank_code,
                    'bank_name': existing_account.bank_name,
                    'account_number': existing_account.account_number,
                    'account_holder_name': existing_account.account_holder_name,
                    'verification_status': existing_account.verification_status
                }
            }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"은행계좌 등록 중 오류: {str(e)}")
        return Response({
            'error': '계좌 등록 중 오류가 발생했습니다.',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_bank_account(request):
    """
    파트너 은행계좌 실명인증 (저장하지 않고 인증만)
    """
    try:
        # 파트너 확인
        try:
            partner = Partner.objects.get(user=request.user)
        except Partner.DoesNotExist:
            return Response({
                'error': '파트너 정보를 찾을 수 없습니다.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # 요청 데이터 추출
        bank_code = request.data.get('bank_code', '').strip()
        account_num = request.data.get('account_num', '').strip()
        account_holder_name = request.data.get('account_holder_name', '').strip()  # 예금주명 
        account_holder_info = request.data.get('account_holder_info', '').strip()  # 생년월일 (YYMMDD)
        
        # 필수 필드 검증
        if not all([bank_code, account_num, account_holder_info]):
            return Response({
                'error': '필수 정보를 모두 입력해주세요.',
                'verified': False
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # KFTC API를 통한 계좌 실명인증
        logger.info(f"계좌 실명인증 요청: 파트너={partner.partner_name}, 은행={bank_code}, 계좌={account_num[:4]}****")
        logger.info(f"KFTC_TEST_MODE: {getattr(settings, 'KFTC_TEST_MODE', True)}")
        
        # 테스트 모드 확인
        if getattr(settings, 'KFTC_TEST_MODE', True):
            logger.info(f"테스트 모드에서 계좌 검증: 은행={bank_code}, 계좌={account_num}, 예금주={account_holder_name}, 생년월일={account_holder_info}")
            
            # 테스트 모드에서는 KFTC 테스트 계좌만 성공 처리
            # 금융결제원 테스트 계좌 예시
            test_accounts = [
                {'bank': '004', 'account': '9876543210', 'name': '홍길동', 'birth': '901225'},
                {'bank': '088', 'account': '110354055057', 'name': '홍길동', 'birth': '901225'},
                {'bank': '020', 'account': '1002123456789', 'name': '김철수', 'birth': '880315'},
            ]
            
            # 테스트 계좌 매칭 확인
            for test in test_accounts:
                if (bank_code == test['bank'] and 
                    account_num.replace('-', '') == test['account'] and
                    account_holder_name == test['name'] and
                    account_holder_info == test['birth']):
                    return Response({
                        'verified': True,
                        'message': '계좌 인증이 완료되었습니다. (테스트)',
                        'account_holder': account_holder_name
                    })
            
            # 매칭되지 않으면 실패
            return Response({
                'verified': False,
                'error': '테스트 계좌 정보가 일치하지 않습니다.',
                'message': '테스트 모드에서는 금융결제원 테스트 계좌만 사용 가능합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 실제 KFTC API 호출
        # account_holder_name이 있으면 이름까지 검증, 없으면 계좌만 검증
        if account_holder_name:
            success, result = kftc_service.verify_account_with_name(
                bank_code=bank_code,
                account_num=account_num,
                account_holder_name=account_holder_name,
                account_holder_info=account_holder_info
            )
        else:
            success, result = kftc_service.verify_account(
                bank_code=bank_code,
                account_num=account_num,
                account_holder_info=account_holder_info
            )
        
        if success:
            return Response({
                'verified': True,
                'message': '계좌 인증이 완료되었습니다.',
                'account_holder': result.get('account_holder_name', account_holder_info)
            })
        else:
            return Response({
                'verified': False,
                'error': result.get('error', '계좌 인증에 실패했습니다.'),
                'message': result.get('message', '입력하신 정보를 다시 확인해주세요.')
            }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"은행계좌 인증 중 오류: {str(e)}")
        return Response({
            'verified': False,
            'error': '계좌 인증 중 오류가 발생했습니다.',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_bank_account(request):
    """
    파트너 은행계좌 정보 조회
    """
    try:
        # 파트너 확인
        try:
            partner = Partner.objects.get(user=request.user)
        except Partner.DoesNotExist:
            return Response({
                'error': '파트너 정보를 찾을 수 없습니다.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # 계좌 정보 조회
        try:
            account = PartnerBankAccount.objects.get(partner=partner)
            
            return Response({
                'success': True,
                'account': {
                    'id': account.id,
                    'bank_code': account.bank_code,
                    'bank_name': account.bank_name,
                    'account_number': account.account_number,
                    'account_holder_name': account.account_holder_name,
                    'account_holder_info': account.account_holder_info,
                    'is_business': account.is_business,
                    'verification_status': account.verification_status,
                    'verification_date': account.verification_date.isoformat() if account.verification_date else None,
                    'is_primary': account.is_primary,
                    'created_at': account.created_at.isoformat(),
                    'updated_at': account.updated_at.isoformat()
                }
            })
        except PartnerBankAccount.DoesNotExist:
            return Response({
                'success': True,
                'account': None,
                'message': '등록된 계좌가 없습니다.'
            })
    
    except Exception as e:
        logger.error(f"은행계좌 조회 중 오류: {str(e)}")
        return Response({
            'error': '계좌 정보 조회 중 오류가 발생했습니다.',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_bank_account(request):
    """
    파트너 은행계좌 삭제
    """
    try:
        # 파트너 확인
        try:
            partner = Partner.objects.get(user=request.user)
        except Partner.DoesNotExist:
            return Response({
                'error': '파트너 정보를 찾을 수 없습니다.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # 계좌 삭제
        deleted_count, _ = PartnerBankAccount.objects.filter(partner=partner).delete()
        
        if deleted_count > 0:
            logger.info(f"은행계좌 삭제 완료: 파트너={partner.company_name}")
            return Response({
                'success': True,
                'message': '계좌가 삭제되었습니다.'
            })
        else:
            return Response({
                'success': False,
                'message': '삭제할 계좌가 없습니다.'
            })
    
    except Exception as e:
        logger.error(f"은행계좌 삭제 중 오류: {str(e)}")
        return Response({
            'error': '계좌 삭제 중 오류가 발생했습니다.',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)