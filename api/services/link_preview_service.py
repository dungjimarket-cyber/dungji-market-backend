import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class LinkPreviewService:
    """링크 미리보기 메타데이터 추출 서비스"""

    @staticmethod
    def extract_metadata(url: str) -> dict:
        """
        URL에서 Open Graph 메타데이터 추출

        Args:
            url: 미리보기를 추출할 URL

        Returns:
            dict: {
                'title': 제목,
                'description': 설명,
                'image': 이미지 URL,
                'url': 원본 URL
            }
        """
        try:
            # User-Agent 설정 (일부 사이트는 봇 차단)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            # 타임아웃 5초
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Open Graph 태그 우선
            og_title = soup.find('meta', property='og:title')
            og_description = soup.find('meta', property='og:description')
            og_image = soup.find('meta', property='og:image')

            # 일반 메타 태그 fallback
            # 제목 추출
            title = ''
            if og_title and og_title.get('content'):
                title = og_title['content']
            elif soup.find('title'):
                title = soup.find('title').text

            # 설명 추출
            description = ''
            if og_description and og_description.get('content'):
                description = og_description['content']
            else:
                desc_tag = soup.find('meta', attrs={'name': 'description'})
                if desc_tag and desc_tag.get('content'):
                    description = desc_tag['content']

            # 이미지 추출
            image = ''
            if og_image and og_image.get('content'):
                image = og_image['content']

            return {
                'title': title[:200] if title else '',  # 최대 200자
                'description': description[:500] if description else '',  # 최대 500자
                'image': image,
                'url': url
            }

        except requests.exceptions.Timeout:
            logger.warning(f'Link preview timeout: {url}')
            return {'error': 'Timeout: 사이트 응답이 없습니다'}

        except requests.exceptions.RequestException as e:
            logger.error(f'Link preview error: {url} - {str(e)}')
            return {'error': '링크를 불러올 수 없습니다'}

        except Exception as e:
            logger.error(f'Unexpected error in link preview: {url} - {str(e)}')
            return {'error': '미리보기 생성 실패'}