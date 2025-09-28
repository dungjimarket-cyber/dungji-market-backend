import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class URLMetadataService:

    @staticmethod
    def extract_metadata(url, timeout=10):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            metadata = {
                'meta_title': None,
                'meta_image': None,
                'meta_description': None,
                'meta_price': None
            }

            metadata['meta_title'] = (
                URLMetadataService._get_og_tag(soup, 'title') or
                URLMetadataService._get_meta_tag(soup, 'twitter:title') or
                (soup.find('title').text if soup.find('title') else None)
            )

            metadata['meta_image'] = (
                URLMetadataService._get_og_tag(soup, 'image') or
                URLMetadataService._get_meta_tag(soup, 'twitter:image')
            )

            metadata['meta_description'] = (
                URLMetadataService._get_og_tag(soup, 'description') or
                URLMetadataService._get_meta_tag(soup, 'twitter:description') or
                URLMetadataService._get_meta_tag(soup, 'description')
            )

            price_str = (
                URLMetadataService._get_og_tag(soup, 'price:amount') or
                URLMetadataService._get_meta_tag(soup, 'product:price:amount')
            )

            if price_str:
                try:
                    metadata['meta_price'] = int(float(price_str.replace(',', '')))
                except (ValueError, AttributeError):
                    pass

            logger.info(f"메타데이터 추출 성공: {url}")
            return metadata

        except requests.Timeout:
            logger.warning(f"메타데이터 추출 타임아웃: {url}")
            return None
        except requests.RequestException as e:
            logger.warning(f"메타데이터 추출 실패: {url} - {str(e)}")
            return None
        except Exception as e:
            logger.error(f"메타데이터 추출 중 오류: {url} - {str(e)}")
            return None

    @staticmethod
    def _get_og_tag(soup, property_name):
        tag = soup.find('meta', property=f'og:{property_name}')
        return tag.get('content') if tag else None

    @staticmethod
    def _get_meta_tag(soup, name):
        tag = soup.find('meta', attrs={'name': name}) or soup.find('meta', attrs={'property': name})
        return tag.get('content') if tag else None