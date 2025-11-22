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

# 전체 지역 리스트 (형식: (저장용 전체명, Google API 검색용 짧은 이름))
TARGET_REGIONS = []

# 서울특별시
SEOUL_DISTRICTS = [
    '강남구', '강동구', '강북구', '강서구', '관악구', '광진구', '구로구', '금천구',
    '노원구', '도봉구', '동대문구', '동작구', '마포구', '서대문구', '서초구',
    '성동구', '성북구', '송파구', '양천구', '영등포구', '용산구', '은평구',
    '종로구', '중구', '중랑구'
]
TARGET_REGIONS.extend([(f'서울특별시 {d}', d) for d in SEOUL_DISTRICTS])

# 경기도 주요 도시
GYEONGGI_CITIES = [
    '고양시', '과천시', '광명시', '광주시', '구리시', '군포시', '김포시',
    '남양주시', '동두천시', '부천시', '성남시', '수원시', '시흥시', '안산시',
    '안성시', '안양시', '양주시', '여주시', '오산시', '용인시', '의왕시',
    '의정부시', '이천시', '파주시', '평택시', '포천시', '하남시', '화성시'
]
TARGET_REGIONS.extend([(f'경기도 {c}', c) for c in GYEONGGI_CITIES])

# 인천광역시
INCHEON_DISTRICTS = ['계양구', '남동구', '동구', '부평구', '서구', '연수구', '중구']
TARGET_REGIONS.extend([(f'인천광역시 {d}', d) for d in INCHEON_DISTRICTS])

# 부산광역시
BUSAN_DISTRICTS = [
    '강서구', '금정구', '남구', '동구', '동래구', '부산진구', '북구',
    '사상구', '사하구', '서구', '수영구', '연제구', '영도구', '중구', '해운대구'
]
TARGET_REGIONS.extend([(f'부산광역시 {d}', d) for d in BUSAN_DISTRICTS])

# 대구광역시
DAEGU_DISTRICTS = ['남구', '달서구', '동구', '북구', '서구', '수성구', '중구']
TARGET_REGIONS.extend([(f'대구광역시 {d}', d) for d in DAEGU_DISTRICTS])

# 대전광역시
DAEJEON_DISTRICTS = ['대덕구', '동구', '서구', '유성구', '중구']
TARGET_REGIONS.extend([(f'대전광역시 {d}', d) for d in DAEJEON_DISTRICTS])

# 광주광역시
GWANGJU_DISTRICTS = ['광산구', '남구', '동구', '북구', '서구']
TARGET_REGIONS.extend([(f'광주광역시 {d}', d) for d in GWANGJU_DISTRICTS])

# 울산광역시
ULSAN_DISTRICTS = ['남구', '동구', '북구', '중구']
TARGET_REGIONS.extend([(f'울산광역시 {d}', d) for d in ULSAN_DISTRICTS])

# 세종특별자치시
TARGET_REGIONS.append(('세종특별자치시', '세종시'))

# 강원특별자치도 주요 시/군
GANGWON_CITIES = [
    '춘천시', '원주시', '강릉시', '동해시', '태백시', '속초시', '삼척시',
    '홍천군', '횡성군', '영월군', '평창군', '정선군', '철원군', '화천군',
    '양구군', '인제군', '고성군', '양양군'
]
TARGET_REGIONS.extend([(f'강원특별자치도 {c}', c) for c in GANGWON_CITIES])

# 충청북도 주요 시/군
CHUNGBUK_CITIES = [
    '청주시', '충주시', '제천시', '보은군', '옥천군', '영동군', '증평군',
    '진천군', '괴산군', '음성군', '단양군'
]
TARGET_REGIONS.extend([(f'충청북도 {c}', c) for c in CHUNGBUK_CITIES])

# 충청남도 주요 시/군
CHUNGNAM_CITIES = [
    '천안시', '공주시', '보령시', '아산시', '서산시', '논산시', '계룡시',
    '당진시', '금산군', '부여군', '서천군', '청양군', '홍성군', '예산군', '태안군'
]
TARGET_REGIONS.extend([(f'충청남도 {c}', c) for c in CHUNGNAM_CITIES])

# 전북특별자치도 주요 시/군
JEONBUK_CITIES = [
    '전주시', '군산시', '익산시', '정읍시', '남원시', '김제시',
    '완주군', '진안군', '무주군', '장수군', '임실군', '순창군', '고창군', '부안군'
]
TARGET_REGIONS.extend([(f'전북특별자치도 {c}', c) for c in JEONBUK_CITIES])

# 전라남도 주요 시/군
JEONNAM_CITIES = [
    '목포시', '여수시', '순천시', '나주시', '광양시',
    '담양군', '곡성군', '구례군', '고흥군', '보성군', '화순군', '장흥군',
    '강진군', '해남군', '영암군', '무안군', '함평군', '영광군', '장성군', '완도군', '진도군', '신안군'
]
TARGET_REGIONS.extend([(f'전라남도 {c}', c) for c in JEONNAM_CITIES])

# 경상북도 주요 시/군
GYEONGBUK_CITIES = [
    '포항시', '경주시', '김천시', '안동시', '구미시', '영주시', '영천시', '상주시', '문경시', '경산시',
    '군위군', '의성군', '청송군', '영양군', '영덕군', '청도군', '고령군', '성주군',
    '칠곡군', '예천군', '봉화군', '울진군', '울릉군'
]
TARGET_REGIONS.extend([(f'경상북도 {c}', c) for c in GYEONGBUK_CITIES])

# 경상남도 주요 시/군
GYEONGNAM_CITIES = [
    '창원시', '진주시', '통영시', '사천시', '김해시', '밀양시', '거제시', '양산시',
    '의령군', '함안군', '창녕군', '고성군', '남해군', '하동군', '산청군', '함양군', '거창군', '합천군'
]
TARGET_REGIONS.extend([(f'경상남도 {c}', c) for c in GYEONGNAM_CITIES])

# 제주특별자치도
JEJU_CITIES = ['제주시', '서귀포시']
TARGET_REGIONS.extend([(f'제주특별자치도 {c}', c) for c in JEJU_CITIES])


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
            default=20,
            help='지역당 최대 업체 수 (기본: 20개)'
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
            regions = [r for r in TARGET_REGIONS if options['region'] in r[0] or options['region'] in r[1]]

        region_display = ', '.join([r[0] for r in regions])
        self.stdout.write(f"🎯 대상 지역: {len(regions)}개 - {region_display}")
        self.stdout.write(f"🎯 대상 업종: {categories.count()}개")

        if categories.count() == 0:
            self.stdout.write(self.style.ERROR('❌ 활성화된 카테고리가 없습니다!'))
            return

        limit = options['limit']

        total_collected = 0
        for region_full_name, region_short_name in regions:
            for category in categories:
                self.stdout.write(f"\n📍 {region_full_name} - {category.name}")

                try:
                    count = self.collect_businesses(region_full_name, region_short_name, category, limit)
                    total_collected += count
                    self.stdout.write(self.style.SUCCESS(f"  ✅ {count}개 수집"))

                    # API Rate Limiting
                    time.sleep(1)

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ❌ 오류: {str(e)}"))
                    continue

        self.stdout.write(self.style.SUCCESS(f"\n=== 완료: 총 {total_collected}개 업체 수집 ==="))

    def collect_businesses(self, region_full_name, region_short_name, category, limit):
        """특정 지역+업종의 업체 수집"""
        # Google Places API 호출 (한글 카테고리명 사용)
        places = self.fetch_google_places(
            city=region_short_name,
            category=category.name,  # name_en 대신 한글 name 사용
            place_type=category.google_place_type,
            max_results=limit
        )

        if not places:
            return 0

        # DB 저장 (전체 이름 사용)
        count = 0
        for rank, place in enumerate(places[:limit], start=1):
            try:
                with transaction.atomic():
                    # 기존 업체 확인
                    existing_business = LocalBusiness.objects.filter(
                        google_place_id=place['placeId']
                    ).first()

                    if existing_business:
                        # 기존 업체는 카테고리 제외하고 업데이트
                        existing_business.region_name = region_full_name
                        existing_business.name = place['name']
                        existing_business.address = place['address']
                        existing_business.phone_number = place.get('phoneNumber')
                        existing_business.latitude = Decimal(str(place['latitude']))
                        existing_business.longitude = Decimal(str(place['longitude']))
                        existing_business.rating = Decimal(str(place['rating'])) if place.get('rating') else None
                        existing_business.review_count = place.get('userRatingCount', 0)
                        existing_business.google_maps_url = place['googleMapsUrl']
                        existing_business.photo_url = place.get('photoUrl')
                        existing_business.popularity_score = place.get('popularityScore', 0)
                        existing_business.rank_in_region = rank
                        existing_business.is_new = place.get('userRatingCount', 0) < 10
                        existing_business.editorial_summary = place.get('editorialSummary')
                        existing_business.website_url = place.get('websiteUri')
                        existing_business.business_status = place.get('businessStatus', 'OPERATIONAL')
                        existing_business.last_synced_at = timezone.now()
                        existing_business.save()

                        self.stdout.write(f"    ↻ {existing_business.name} (업데이트, 카테고리 유지: {existing_business.category.name})")
                    else:
                        # 신규 업체는 모든 정보 포함하여 생성
                        business = LocalBusiness.objects.create(
                            google_place_id=place['placeId'],
                            category=category,
                            region_name=region_full_name,
                            name=place['name'],
                            address=place['address'],
                            phone_number=place.get('phoneNumber'),
                            latitude=Decimal(str(place['latitude'])),
                            longitude=Decimal(str(place['longitude'])),
                            rating=Decimal(str(place['rating'])) if place.get('rating') else None,
                            review_count=place.get('userRatingCount', 0),
                            google_maps_url=place['googleMapsUrl'],
                            photo_url=place.get('photoUrl'),
                            popularity_score=place.get('popularityScore', 0),
                            rank_in_region=rank,
                            is_new=place.get('userRatingCount', 0) < 10,
                            editorial_summary=place.get('editorialSummary'),
                            website_url=place.get('websiteUri'),
                            business_status=place.get('businessStatus', 'OPERATIONAL'),
                            last_synced_at=timezone.now(),
                        )
                        count += 1
                        self.stdout.write(f"    + {business.name} (신규)")

            except Exception as e:
                error_msg = f"업체 저장 실패: {place.get('name')} - {str(e)}"
                logger.error(error_msg)
                self.stdout.write(self.style.ERROR(f"    ❌ {error_msg}"))
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
            'X-Goog-FieldMask': 'places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.location,places.internationalPhoneNumber,places.photos,places.editorialSummary,places.websiteUri,places.businessStatus'
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
            'minRating': 3.5,
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
                'editorialSummary': place.get('editorialSummary', {}).get('text'),
                'websiteUri': place.get('websiteUri'),
                'businessStatus': place.get('businessStatus', 'OPERATIONAL'),
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
        """지역 좌표 반환"""
        # 전체 지역 좌표
        REGION_COORDINATES = {
            # 서울특별시
            '강남구': {'latitude': 37.5172, 'longitude': 127.0473},
            '강동구': {'latitude': 37.5301, 'longitude': 127.1238},
            '강북구': {'latitude': 37.6396, 'longitude': 127.0257},
            '강서구': {'latitude': 37.5509, 'longitude': 126.8495},
            '관악구': {'latitude': 37.4784, 'longitude': 126.9516},
            '광진구': {'latitude': 37.5384, 'longitude': 127.0822},
            '구로구': {'latitude': 37.4954, 'longitude': 126.8874},
            '금천구': {'latitude': 37.4519, 'longitude': 126.8955},
            '노원구': {'latitude': 37.6542, 'longitude': 127.0568},
            '도봉구': {'latitude': 37.6688, 'longitude': 127.0471},
            '동대문구': {'latitude': 37.5744, 'longitude': 127.0396},
            '동작구': {'latitude': 37.5124, 'longitude': 126.9393},
            '마포구': {'latitude': 37.5663, 'longitude': 126.9019},
            '서대문구': {'latitude': 37.5791, 'longitude': 126.9368},
            '서초구': {'latitude': 37.4837, 'longitude': 127.0324},
            '성동구': {'latitude': 37.5635, 'longitude': 127.0369},
            '성북구': {'latitude': 37.5894, 'longitude': 127.0167},
            '송파구': {'latitude': 37.5145, 'longitude': 127.1059},
            '양천구': {'latitude': 37.5170, 'longitude': 126.8664},
            '영등포구': {'latitude': 37.5264, 'longitude': 126.8962},
            '용산구': {'latitude': 37.5326, 'longitude': 126.9900},
            '은평구': {'latitude': 37.6027, 'longitude': 126.9291},
            '종로구': {'latitude': 37.5735, 'longitude': 126.9788},
            '중구': {'latitude': 37.5641, 'longitude': 126.9979},
            '중랑구': {'latitude': 37.6063, 'longitude': 127.0925},

            # 경기도
            '고양시': {'latitude': 37.6584, 'longitude': 126.8320},
            '과천시': {'latitude': 37.4292, 'longitude': 126.9877},
            '광명시': {'latitude': 37.4785, 'longitude': 126.8644},
            '광주시': {'latitude': 37.4292, 'longitude': 127.2550},
            '구리시': {'latitude': 37.5943, 'longitude': 127.1296},
            '군포시': {'latitude': 37.3617, 'longitude': 126.9352},
            '김포시': {'latitude': 37.6152, 'longitude': 126.7158},
            '남양주시': {'latitude': 37.6360, 'longitude': 127.2165},
            '동두천시': {'latitude': 37.9034, 'longitude': 127.0606},
            '부천시': {'latitude': 37.5035, 'longitude': 126.7660},
            '성남시': {'latitude': 37.4201, 'longitude': 127.1262},
            '수원시': {'latitude': 37.2636, 'longitude': 127.0286},
            '시흥시': {'latitude': 37.3800, 'longitude': 126.8028},
            '안산시': {'latitude': 37.3219, 'longitude': 126.8309},
            '안성시': {'latitude': 37.0079, 'longitude': 127.2797},
            '안양시': {'latitude': 37.3943, 'longitude': 126.9568},
            '양주시': {'latitude': 37.7852, 'longitude': 127.0458},
            '여주시': {'latitude': 37.2982, 'longitude': 127.6377},
            '오산시': {'latitude': 37.1498, 'longitude': 127.0773},
            '용인시': {'latitude': 37.2410, 'longitude': 127.1776},
            '의왕시': {'latitude': 37.3449, 'longitude': 126.9684},
            '의정부시': {'latitude': 37.7381, 'longitude': 127.0338},
            '이천시': {'latitude': 37.2720, 'longitude': 127.4351},
            '파주시': {'latitude': 37.7599, 'longitude': 126.7800},
            '평택시': {'latitude': 36.9921, 'longitude': 127.1127},
            '포천시': {'latitude': 37.8948, 'longitude': 127.2006},
            '하남시': {'latitude': 37.5393, 'longitude': 127.2148},
            '화성시': {'latitude': 37.1990, 'longitude': 126.8312},

            # 인천광역시
            '계양구': {'latitude': 37.5377, 'longitude': 126.7377},
            '남동구': {'latitude': 37.4474, 'longitude': 126.7313},
            '부평구': {'latitude': 37.5070, 'longitude': 126.7219},
            '연수구': {'latitude': 37.4106, 'longitude': 126.6784},

            # 부산/대구/대전/광주/울산 주요 구
            '해운대구': {'latitude': 35.1631, 'longitude': 129.1635},
            '부산진구': {'latitude': 35.1628, 'longitude': 129.0531},
            '동래구': {'latitude': 35.2048, 'longitude': 129.0784},
            '수성구': {'latitude': 35.8581, 'longitude': 128.6311},
            '달서구': {'latitude': 35.8298, 'longitude': 128.5326},
            '유성구': {'latitude': 36.3621, 'longitude': 127.3567},
            '서구': {'latitude': 35.1520, 'longitude': 126.8895},  # 광주
        }

        # 좌표가 없는 경우 강남구 기본값 사용
        return REGION_COORDINATES.get(city, REGION_COORDINATES['강남구'])
