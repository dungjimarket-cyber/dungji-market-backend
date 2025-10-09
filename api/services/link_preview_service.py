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
            # User-Agent 설정 (더 실제 브라우저처럼)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }

            # 타임아웃 10초로 증가 (네이버 스마트스토어는 느림)
            response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
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
            # 타임아웃 시에도 기본 정보 반환
            return {
                'title': '',
                'description': '',
                'image': '',
                'url': url,
                'warning': '사이트 응답이 느립니다. 링크는 정상적으로 작동합니다.'
            }

        except requests.exceptions.HTTPError as e:
            logger.error(f'Link preview HTTP error: {url} - {e.response.status_code}')
            # HTTP 에러도 기본 정보 반환 (링크 자체는 유효함)
            return {
                'title': '',
                'description': '',
                'image': '',
                'url': url,
                'warning': '미리보기를 가져올 수 없지만 링크는 유효합니다.'
            }

        except requests.exceptions.RequestException as e:
            logger.error(f'Link preview error: {url} - {str(e)}')
            return {
                'title': '',
                'description': '',
                'image': '',
                'url': url,
                'warning': '미리보기를 가져올 수 없지만 링크는 저장됩니다.'
            }

        except Exception as e:
            logger.error(f'Unexpected error in link preview: {url} - {str(e)}')
            return {
                'title': '',
                'description': '',
                'image': '',
                'url': url,
                'warning': '미리보기 생성 실패'
            }