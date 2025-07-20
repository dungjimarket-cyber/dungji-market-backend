import json
import logging

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware:
    """개발 환경에서 요청 데이터를 로깅하는 미들웨어"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # GroupBuy 관련 요청만 로깅
        if request.path.startswith('/api/groupbuys/') and request.method in ['POST', 'PUT', 'PATCH']:
            try:
                if request.content_type == 'application/json':
                    body = json.loads(request.body.decode('utf-8'))
                    logger.info(f"\n{'='*50}")
                    logger.info(f"[{request.method}] {request.path}")
                    logger.info(f"요청 데이터:")
                    logger.info(json.dumps(body, indent=2, ensure_ascii=False))
                    
                    # regions 필드 특별 로깅
                    if 'regions' in body:
                        logger.info(f"regions 필드 타입: {type(body['regions'])}")
                        logger.info(f"regions 개수: {len(body['regions']) if isinstance(body['regions'], list) else 'N/A'}")
                    logger.info(f"{'='*50}\n")
            except Exception as e:
                logger.error(f"요청 로깅 중 오류: {str(e)}")
        
        response = self.get_response(request)
        return response