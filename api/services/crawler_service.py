"""
협회 사이트 Selenium 크롤러 서비스
- 동적 페이지 처리
- 상세 페이지 접근하여 이메일 수집

필요 패키지:
pip install selenium webdriver-manager pandas openpyxl
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import re
import os
import logging
from io import BytesIO
from datetime import datetime

logger = logging.getLogger(__name__)

# 설정
DELAY = 1.5  # 페이지 로딩 대기


def setup_driver(headless=True):
    """Chrome 드라이버 설정"""
    options = Options()
    if headless:
        options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    # Docker 환경에서는 설치된 ChromeDriver 사용, 로컬에서는 webdriver_manager 사용
    chromedriver_path = '/usr/local/bin/chromedriver'
    if os.path.exists(chromedriver_path):
        service = Service(chromedriver_path)
    else:
        service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=options)
    return driver


def extract_emails(text):
    """이메일 추출"""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(pattern, text)
    return [e for e in emails if not e.endswith(('.png', '.jpg', '.gif'))]


def extract_phones(text):
    """전화번호 추출"""
    pattern = r'0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}'
    return list(set(re.findall(pattern, text)))


# ============== 1. 변호사 - 대한변호사협회 ==============
def crawl_lawyers(max_pages=10, progress_callback=None):
    """변호사협회 크롤링"""
    logger.info("[변호사] 크롤링 시작...")

    driver = setup_driver(headless=True)
    all_data = []

    try:
        driver.get("https://www.koreanbar.or.kr/pages/search/search.asp")
        time.sleep(3)

        for page in range(1, max_pages + 1):
            if progress_callback:
                progress_callback(f"변호사 {page}페이지 처리 중...")

            # 검색 결과 카드들
            cards = driver.find_elements(By.CSS_SELECTOR, ".lawyer-card, .search-item, [class*='lawyer'], table tbody tr")

            for card in cards:
                try:
                    data = {"업종": "변호사"}

                    # 테이블 형식인 경우
                    cols = card.find_elements(By.TAG_NAME, "td")
                    if cols and len(cols) >= 2:
                        data["성명"] = cols[0].text.strip() if len(cols) > 0 else ""
                        data["소속"] = cols[1].text.strip() if len(cols) > 1 else ""
                        data["주소"] = cols[2].text.strip() if len(cols) > 2 else ""
                    else:
                        # 카드 형식
                        name_el = card.find_elements(By.CSS_SELECTOR, ".name, h3, h4, .lawyer-name")
                        data["성명"] = name_el[0].text if name_el else ""

                        office_el = card.find_elements(By.CSS_SELECTOR, ".office, .firm, .law-office")
                        data["소속"] = office_el[0].text if office_el else ""

                    # 전체 텍스트에서 연락처 추출
                    text = card.text
                    emails = extract_emails(text)
                    phones = extract_phones(text)

                    data["전화번호"] = phones[0] if phones else ""
                    data["이메일"] = emails[0] if emails else ""

                    if data["성명"]:
                        all_data.append(data)

                except Exception as e:
                    continue

            # 다음 페이지
            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, ".pagination .next, a[rel='next'], .paging a")
                next_btn.click()
                time.sleep(DELAY)
            except:
                break

        logger.info(f"[변호사] 총 {len(all_data)}명 수집")

    except Exception as e:
        logger.error(f"[변호사] 크롤링 오류: {e}")
    finally:
        driver.quit()

    return all_data


# ============== 2. 법무사 - 대한법무사협회 ==============
def crawl_judicial_scriveners(regions=None, progress_callback=None):
    """법무사협회 검색 크롤링"""
    logger.info("[법무사] 크롤링 시작...")

    driver = setup_driver(headless=True)
    all_data = []

    regions = regions or ["서울", "경기", "부산", "대구", "인천", "광주", "대전", "울산"]

    try:
        driver.get("https://www.kjsa.or.kr/front/member/search.do")
        time.sleep(3)

        for region in regions:
            if progress_callback:
                progress_callback(f"법무사 {region} 지역 검색 중...")

            try:
                # 지역 선택
                region_select = driver.find_elements(By.CSS_SELECTOR, "select[name*='sido'], select[name*='region'], #sido")
                if region_select:
                    Select(region_select[0]).select_by_visible_text(region)
                    time.sleep(1)

                # 검색 버튼 클릭
                search_btn = driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], .btn-search, input[type='submit']")
                if search_btn:
                    search_btn[0].click()
                    time.sleep(2)

                # 결과 파싱
                rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, .result-item, .member-list li")

                for row in rows:
                    try:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        text = row.text
                        emails = extract_emails(text)
                        phones = extract_phones(text)

                        if len(cols) >= 2:
                            all_data.append({
                                "업종": "법무사",
                                "성명": cols[0].text.strip() if len(cols) > 0 else "",
                                "사무소명": cols[1].text.strip() if len(cols) > 1 else "",
                                "주소": cols[2].text.strip() if len(cols) > 2 else "",
                                "전화번호": phones[0] if phones else "",
                                "이메일": emails[0] if emails else "",
                                "지역": region
                            })
                    except:
                        continue

            except Exception as e:
                logger.warning(f"[법무사] {region} 오류: {e}")

            time.sleep(DELAY)

        logger.info(f"[법무사] 총 {len(all_data)}명 수집")

    except Exception as e:
        logger.error(f"[법무사] 크롤링 오류: {e}")
    finally:
        driver.quit()

    return all_data


# ============== 3. 세무사 - 한국세무사회 ==============
def crawl_tax_accountants(regions=None, progress_callback=None):
    """세무사회 지역별 명단 크롤링"""
    logger.info("[세무사] 크롤링 시작...")

    driver = setup_driver(headless=True)
    all_data = []

    regions = regions or ["서울", "경기", "부산", "대구", "인천"]

    try:
        driver.get("https://www.kacpta.or.kr/kacpta_view/kac_search/taxAccountant_n.asp")
        time.sleep(3)

        # 지역 선택 드롭다운 찾기
        try:
            region_select = driver.find_elements(By.CSS_SELECTOR, "select[name*='sido'], select[name*='region']")

            if region_select:
                select = Select(region_select[0])
                available_options = [o.text.strip() for o in select.options if o.text.strip()]

                for region in regions:
                    if progress_callback:
                        progress_callback(f"세무사 {region} 검색 중...")

                    # 매칭되는 옵션 찾기
                    matched = [o for o in available_options if region in o]
                    if not matched:
                        continue

                    try:
                        select = Select(region_select[0])
                        select.select_by_visible_text(matched[0])
                        time.sleep(1)

                        # 검색
                        search_btn = driver.find_elements(By.CSS_SELECTOR, "input[type='submit'], .btn-search, button[type='submit']")
                        if search_btn:
                            search_btn[0].click()
                            time.sleep(2)

                        # 테이블 파싱
                        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                        for row in rows:
                            cols = row.find_elements(By.TAG_NAME, "td")
                            if len(cols) >= 3:
                                text = row.text
                                emails = extract_emails(text)
                                phones = extract_phones(text)

                                all_data.append({
                                    "업종": "세무사",
                                    "성명": cols[0].text.strip(),
                                    "사무소명": cols[1].text.strip() if len(cols) > 1 else "",
                                    "주소": cols[2].text.strip() if len(cols) > 2 else "",
                                    "전화번호": phones[0] if phones else "",
                                    "이메일": emails[0] if emails else "",
                                    "지역": region
                                })

                        time.sleep(DELAY)
                    except Exception as e:
                        logger.warning(f"[세무사] {region} 처리 오류: {e}")

        except Exception as e:
            logger.error(f"[세무사] 드롭다운 오류: {e}")

        logger.info(f"[세무사] 총 {len(all_data)}명 수집")

    except Exception as e:
        logger.error(f"[세무사] 크롤링 오류: {e}")
    finally:
        driver.quit()

    return all_data


# ============== 4. 공인회계사 - 한국공인회계사회 ==============
def crawl_accountants(regions=None, progress_callback=None):
    """공인회계사회 크롤링"""
    logger.info("[공인회계사] 크롤링 시작...")

    driver = setup_driver(headless=True)
    all_data = []

    regions = regions or ["서울", "경기", "부산"]

    try:
        driver.get("https://www.kicpa.or.kr/portal/default/kicpa/search/mem_search.page")
        time.sleep(3)

        for region in regions:
            if progress_callback:
                progress_callback(f"공인회계사 {region} 검색 중...")

            try:
                # 지역 선택
                region_inputs = driver.find_elements(By.CSS_SELECTOR, "select[name*='region'], select[name*='sido']")
                if region_inputs:
                    Select(region_inputs[0]).select_by_visible_text(region)
                    time.sleep(1)

                # 검색
                search_btn = driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], .btn-search")
                if search_btn:
                    search_btn[0].click()
                    time.sleep(2)

                # 결과 파싱
                rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) >= 2:
                        text = row.text
                        emails = extract_emails(text)
                        phones = extract_phones(text)

                        all_data.append({
                            "업종": "공인회계사",
                            "성명": cols[0].text.strip(),
                            "소속": cols[1].text.strip() if len(cols) > 1 else "",
                            "주소": cols[2].text.strip() if len(cols) > 2 else "",
                            "전화번호": phones[0] if phones else "",
                            "이메일": emails[0] if emails else "",
                            "지역": region
                        })

            except Exception as e:
                logger.warning(f"[공인회계사] {region} 오류: {e}")

            time.sleep(DELAY)

        logger.info(f"[공인회계사] 총 {len(all_data)}명 수집")

    except Exception as e:
        logger.error(f"[공인회계사] 크롤링 오류: {e}")
    finally:
        driver.quit()

    return all_data


# ============== 5. 공인중개사 ==============
def crawl_realtors(regions=None, progress_callback=None):
    """공인중개사 크롤링 - 국토교통부 부동산거래관리시스템"""
    logger.info("[공인중개사] 크롤링 시작...")

    driver = setup_driver(headless=True)
    all_data = []

    # 서울시 구 목록 (샘플)
    gu_list = regions or ["강남구", "서초구", "송파구", "마포구", "영등포구"]

    try:
        for gu in gu_list:
            if progress_callback:
                progress_callback(f"공인중개사 {gu} 검색 중...")

            try:
                # 국토부 부동산거래관리시스템 또는 서울시 부동산정보광장
                url = f"https://www.reb.or.kr/member/search"
                driver.get(url)
                time.sleep(2)

                # 검색어 입력
                search_input = driver.find_elements(By.CSS_SELECTOR, "input[name*='keyword'], input[type='text']")
                if search_input:
                    search_input[0].clear()
                    search_input[0].send_keys(gu)
                    time.sleep(0.5)

                # 검색
                search_btn = driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], .btn-search")
                if search_btn:
                    search_btn[0].click()
                    time.sleep(2)

                # 테이블 파싱
                rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

                for row in rows:
                    try:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        if len(cols) >= 3:
                            text = row.text
                            emails = extract_emails(text)
                            phones = extract_phones(text)

                            all_data.append({
                                "업종": "공인중개사",
                                "사무소명": cols[0].text.strip(),
                                "대표자": cols[1].text.strip() if len(cols) > 1 else "",
                                "주소": cols[2].text.strip() if len(cols) > 2 else "",
                                "전화번호": phones[0] if phones else "",
                                "이메일": emails[0] if emails else "",
                                "지역": f"서울시 {gu}"
                            })
                    except:
                        continue

            except Exception as e:
                logger.warning(f"[공인중개사] {gu} 오류: {e}")

            time.sleep(DELAY)

        logger.info(f"[공인중개사] 총 {len(all_data)}건 수집")

    except Exception as e:
        logger.error(f"[공인중개사] 크롤링 오류: {e}")
    finally:
        driver.quit()

    return all_data


# ============== 크롤러 실행 함수 ==============
CRAWLER_MAP = {
    'lawyer': ('변호사', crawl_lawyers),
    'judicial_scrivener': ('법무사', crawl_judicial_scriveners),
    'tax_accountant': ('세무사', crawl_tax_accountants),
    'accountant': ('공인회계사', crawl_accountants),
    'realtor': ('공인중개사', crawl_realtors),
}


def run_crawler(crawler_type, regions=None, max_pages=5, progress_callback=None):
    """
    특정 업종 크롤러 실행

    Args:
        crawler_type: 크롤러 타입 (lawyer, judicial_scrivener, tax_accountant, accountant, realtor)
        regions: 검색할 지역 리스트
        max_pages: 최대 페이지 수
        progress_callback: 진행 상황 콜백 함수

    Returns:
        dict: 수집 결과 (data, count, email_count)
    """
    if crawler_type not in CRAWLER_MAP:
        raise ValueError(f"Unknown crawler type: {crawler_type}")

    name, crawler_func = CRAWLER_MAP[crawler_type]

    try:
        if crawler_type == 'lawyer':
            data = crawler_func(max_pages=max_pages, progress_callback=progress_callback)
        else:
            data = crawler_func(regions=regions, progress_callback=progress_callback)

        email_count = len([d for d in data if d.get("이메일")])

        return {
            'success': True,
            'name': name,
            'data': data,
            'count': len(data),
            'email_count': email_count,
        }
    except Exception as e:
        logger.error(f"크롤러 실행 오류 ({name}): {e}")
        return {
            'success': False,
            'name': name,
            'error': str(e),
            'data': [],
            'count': 0,
            'email_count': 0,
        }


def run_all_crawlers(regions=None, max_pages=5, progress_callback=None):
    """
    모든 크롤러 실행

    Returns:
        dict: 전체 수집 결과
    """
    results = {}
    all_data = []

    for crawler_type in CRAWLER_MAP.keys():
        result = run_crawler(crawler_type, regions, max_pages, progress_callback)
        results[crawler_type] = result
        if result['success']:
            all_data.extend(result['data'])

    total_count = sum(r['count'] for r in results.values())
    total_emails = sum(r['email_count'] for r in results.values())

    return {
        'results': results,
        'all_data': all_data,
        'total_count': total_count,
        'total_emails': total_emails,
    }


def export_to_excel(data, filename=None):
    """
    데이터를 엑셀 파일로 변환

    Returns:
        BytesIO: 엑셀 파일 바이트 스트림
    """
    if not data:
        return None

    df = pd.DataFrame(data)

    # 컬럼 순서 정리
    columns_order = ['업종', '성명', '대표자', '사무소명', '소속', '주소', '지역', '전화번호', '이메일']
    existing_columns = [c for c in columns_order if c in df.columns]
    other_columns = [c for c in df.columns if c not in columns_order]
    df = df[existing_columns + other_columns]

    # BytesIO로 엑셀 저장
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='수집결과')

    output.seek(0)
    return output


def get_emails_from_data(data):
    """데이터에서 이메일 목록 추출"""
    emails = []
    for item in data:
        email = item.get('이메일', '').strip()
        if email and '@' in email:
            emails.append({
                'email': email,
                'name': item.get('성명') or item.get('대표자') or item.get('사무소명', ''),
                'category': item.get('업종', ''),
                'region': item.get('지역', ''),
            })
    return emails
