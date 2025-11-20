"""
지역 업체 정보 수집 (Google Places API 사용)
기존 rankings 시스템의 fetchPlaceRankings 로직 재사용
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from api.models import LocalBusinessCategory, LocalBusiness
import requests
import time
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

# 하드코딩된 지역 리스트 (Region 테이블 불필요)
TARGET_REGIONS = [
    '강남구', '서초구', '송파구', '강동구', '마포구',  # 서울 5개구
    '성남시', '수원시', '고양시', '용인시', '화성시'   # 수도권 5개시
]


class Command(BaseCommand):
    help = '구글 Places API로 지역 업체 정보 수집'

    def add_arguments(self, parser):
        parser.add_argument(
            '--region',
            type=str,
            help='특정 지역만 수집 (예: 강남구)'
        )
        parser.add_argument(
            '--category',
            type=str,
            help='특정 업종만 수집 (예: 세무사)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=5,
            help='지역당 최대 업체 수 (기본: 5개)'
        )

    def handle(self, *args, **options):
        """메인 실행 로직"""
        self.stdout.write(self.style.SUCCESS('=== 지역 업체 정보 수집 시작 ==='))

        # 카테고리 필터링
        categories = LocalBusinessCategory.objects.filter(is_active=True)
        if options['category']:
            categories = categories.filter(name=options['category'])

        # 지역 필터링 (하드코딩된 리스트 사용)
        regions = TARGET_REGIONS
        if options['region']:
            regions = [r for r in TARGET_REGIONS if options['region'] in r]

        self.stdout.write(f"🎯 대상 지역: {len(regions)}개 - {', '.join(regions)}")
        self.stdout.write(f"🎯 대상 업종: {categories.count()}개")

        if categories.count() == 0:
            self.stdout.write(self.style.ERROR('❌ 활성화된 카테고리가 없습니다!'))
            return

        limit = options['limit']

        total_collected = 0
        for region_name in regions:
            for category in categories:
                self.stdout.write(f"\n📍 {region_name} - {category.name}")

                try:
                    count = self.collect_businesses(region_name, category, limit)
                    total_collected += count
                    self.stdout.write(self.style.SUCCESS(f"  ✅ {count}개 수집"))

                    # API Rate Limiting
                    time.sleep(1)

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ❌ 오류: {str(e)}"))
                    continue

        self.stdout.write(self.style.SUCCESS(f"\n=== 완료: 총 {total_collected}개 업체 수집 ==="))

    def collect_businesses(self, region_name, category, limit):
        """특정 지역+업종의 업체 수집"""
        # Google Places API 호출
        places = self.fetch_google_places(
            city=region_name,
            category=category.name_en,
            place_type=category.google_place_type,
            max_results=limit
        )

        if not places:
            return 0

        # DB 저장
        count = 0
        for rank, place in enumerate(places[:limit], start=1):
            try:
                with transaction.atomic():
                    business, created = LocalBusiness.objects.update_or_create(
                        google_place_id=place['placeId'],
                        defaults={
                            'category': category,
                            'region_name': region_name,
                            'name': place['name'],
                            'address': place['address'],
                            'phone_number': place.get('phoneNumber'),
                            'latitude': Decimal(str(place['latitude'])),
                            'longitude': Decimal(str(place['longitude'])),
                            'rating': Decimal(str(place['rating'])) if place.get('rating') else None,
                            'review_count': place.get('userRatingCount', 0),
                            'google_maps_url': place['googleMapsUrl'],
                            'photo_url': place.get('photoUrl'),
                            'popularity_score': place.get('popularityScore', 0),
                            'rank_in_region': rank,
                            'is_new': place.get('userRatingCount', 0) < 10,
                            'last_synced_at': timezone.now(),
                        }
                    )

                    if created:
                        count += 1
                        self.stdout.write(f"    + {business.name}")
                    else:
                        self.stdout.write(f"    ↻ {business.name} (업데이트)")

            except Exception as e:
                logger.error(f"업체 저장 실패: {place.get('name')} - {str(e)}")
                continue

        return count

    def fetch_google_places(self, city, category, place_type, max_results=5):
        """Google Places API 호출 (rankings 로직 재사용)"""
        from django.conf import settings

        api_key = settings.GOOGLE_PLACES_API_KEY
        if not api_key:
            raise ValueError("GOOGLE_PLACES_API_KEY not configured")

        # 지역 좌표 (rankings의 REGION_COORDINATES 사용)
        coordinates = self.get_region_coordinates(city)

        # 검색 쿼리
        search_query = f"{city} {category}"

        # API 요청
        url = 'https://places.googleapis.com/v1/places:searchText'
        headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': api_key,
            'X-Goog-FieldMask': 'places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.location,places.internationalPhoneNumber,places.photos'
        }

        body = {
            'textQuery': search_query,
            'languageCode': 'ko',
            'locationBias': {
                'circle': {
                    'center': {
                        'latitude': coordinates['latitude'],
                        'longitude': coordinates['longitude']
                    },
                    'radius': 5000.0
                }
            },
            'minRating': 4.0,
            'maxResultCount': max_results
        }

        response = requests.post(url, json=body, headers=headers)

        if not response.ok:
            logger.error(f"Google API 오류: {response.status_code} - {response.text}")
            return []

        data = response.json()
        places = data.get('places', [])

        # 결과 변환
        results = []
        for place in places:
            # 인기도 점수 계산 (베이지안 평균)
            rating = place.get('rating', 0)
            review_count = place.get('userRatingCount', 0)
            popularity_score = self.calculate_popularity_score(rating, review_count)

            # 사진 URL
            photo_url = None
            if place.get('photos'):
                photo_name = place['photos'][0]['name']
                photo_url = f"https://places.googleapis.com/v1/{photo_name}/media?maxWidthPx=400&key={api_key}"

            # 구글 지도 URL
            google_maps_url = f"https://www.google.com/maps/place/?q=place_id:{place['id']}"

            results.append({
                'placeId': place['id'],
                'name': place['displayName']['text'],
                'address': place['formattedAddress'],
                'phoneNumber': place.get('internationalPhoneNumber'),
                'latitude': place['location']['latitude'],
                'longitude': place['location']['longitude'],
                'rating': rating,
                'userRatingCount': review_count,
                'googleMapsUrl': google_maps_url,
                'photoUrl': photo_url,
                'popularityScore': popularity_score,
            })

        return results

    def calculate_popularity_score(self, rating, user_rating_count):
        """인기도 점수 계산 (베이지안 평균)"""
        import math

        C = 10  # 신뢰도 기준
        m = 4.0  # 평균 평점 기준값

        # 베이지안 평균
        adjusted_rating = (C * m + user_rating_count * rating) / (C + user_rating_count)

        # 최종 점수
        return adjusted_rating * math.log10(user_rating_count + 1)

    def get_region_coordinates(self, city):
        """지역 좌표 반환 (rankings의 REGION_COORDINATES)"""
        # 주요 지역 좌표 (확장 가능)
        REGION_COORDINATES = {
            '강남구': {'latitude': 37.5172, 'longitude': 127.0473},
            '서초구': {'latitude': 37.4837, 'longitude': 127.0324},
            '송파구': {'latitude': 37.5145, 'longitude': 127.1059},
            '강동구': {'latitude': 37.5301, 'longitude': 127.1238},
            '마포구': {'latitude': 37.5663, 'longitude': 126.9019},
            '성남시': {'latitude': 37.4201, 'longitude': 127.1262},
            '수원시': {'latitude': 37.2636, 'longitude': 127.0286},
            '고양시': {'latitude': 37.6584, 'longitude': 126.8320},
            '용인시': {'latitude': 37.2410, 'longitude': 127.1776},
            '화성시': {'latitude': 37.1990, 'longitude': 126.8312},
        }

        return REGION_COORDINATES.get(city, REGION_COORDINATES['강남구'])
