"""
둥지마켓 크롤러 GUI 프로그램
- 업체 웹사이트에서 이메일 수집
- 협회 사이트 크롤링
- 결과 엑셀 저장
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import sys
import re
from datetime import datetime

# Selenium 관련
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# 엑셀 관련
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# HTTP 요청
try:
    import urllib.request
    import urllib.parse
    import json
    URLLIB_AVAILABLE = True
except ImportError:
    URLLIB_AVAILABLE = False

# 서버 설정
SERVER_URL = "https://api.dungji.co.kr"  # 실제 서버 URL로 변경


class CrawlerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("둥지마켓 크롤러")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # 크롤링 중단 플래그
        self.stop_flag = False
        self.is_running = False

        # 수집된 데이터
        self.collected_data = []

        self.setup_ui()
        self.check_dependencies()

    def check_dependencies(self):
        """필수 패키지 확인"""
        missing = []
        if not SELENIUM_AVAILABLE:
            missing.append("selenium, webdriver-manager")
        if not PANDAS_AVAILABLE:
            missing.append("pandas, openpyxl")

        if missing:
            self.log(f"[경고] 다음 패키지가 필요합니다: {', '.join(missing)}")
            self.log("pip install selenium webdriver-manager pandas openpyxl")

    def setup_ui(self):
        """UI 구성"""
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # === 설정 영역 ===
        settings_frame = ttk.LabelFrame(main_frame, text="크롤링 설정", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        # 크롤러 유형
        type_frame = ttk.Frame(settings_frame)
        type_frame.pack(fill=tk.X, pady=5)

        ttk.Label(type_frame, text="크롤러 유형:").pack(side=tk.LEFT)
        self.crawler_type = tk.StringVar(value="website")
        type_combo = ttk.Combobox(type_frame, textvariable=self.crawler_type, state="readonly", width=30)
        type_combo['values'] = [
            "website - 웹사이트 URL에서 이메일 수집",
            "lawyer - 변호사협회",
            "tax_accountant - 세무사회",
            "judicial_scrivener - 법무사협회",
            "accountant - 공인회계사회",
        ]
        type_combo.current(0)
        type_combo.pack(side=tk.LEFT, padx=(10, 0))
        type_combo.bind("<<ComboboxSelected>>", self.on_type_change)

        # URL 입력 영역 (웹사이트 크롤링용)
        self.url_frame = ttk.LabelFrame(settings_frame, text="웹사이트 URL 목록", padding="5")
        self.url_frame.pack(fill=tk.X, pady=5)

        url_input_frame = ttk.Frame(self.url_frame)
        url_input_frame.pack(fill=tk.X)

        self.url_text = tk.Text(url_input_frame, height=5, width=70)
        self.url_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.url_text.insert("1.0", "# 한 줄에 하나씩 URL 입력\n# 예: https://example.com\n")

        url_scroll = ttk.Scrollbar(url_input_frame, orient=tk.VERTICAL, command=self.url_text.yview)
        url_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.url_text.configure(yscrollcommand=url_scroll.set)

        url_btn_frame = ttk.Frame(self.url_frame)
        url_btn_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(url_btn_frame, text="서버에서 가져오기", command=self.show_server_dialog).pack(side=tk.LEFT)
        ttk.Button(url_btn_frame, text="파일에서 불러오기", command=self.load_urls_from_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(url_btn_frame, text="URL 지우기", command=lambda: self.url_text.delete("1.0", tk.END)).pack(side=tk.LEFT, padx=5)

        # 지역 설정 (협회 크롤링용)
        self.region_frame = ttk.LabelFrame(settings_frame, text="지역 선택", padding="5")

        self.region_vars = {}
        regions = ['서울', '경기', '부산', '대구', '인천', '광주', '대전', '울산', '세종',
                   '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주']

        region_inner = ttk.Frame(self.region_frame)
        region_inner.pack(fill=tk.X)

        for i, region in enumerate(regions):
            var = tk.BooleanVar(value=(region in ['서울', '경기']))
            self.region_vars[region] = var
            cb = ttk.Checkbutton(region_inner, text=region, variable=var)
            cb.grid(row=i//6, column=i%6, sticky=tk.W, padx=5)

        # 기타 설정
        other_frame = ttk.Frame(settings_frame)
        other_frame.pack(fill=tk.X, pady=5)

        ttk.Label(other_frame, text="최대 크롤링 수:").pack(side=tk.LEFT)
        self.max_count = tk.StringVar(value="50")
        ttk.Entry(other_frame, textvariable=self.max_count, width=10).pack(side=tk.LEFT, padx=(5, 20))

        self.headless_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(other_frame, text="백그라운드 실행 (창 숨김)", variable=self.headless_var).pack(side=tk.LEFT)

        # === 버튼 영역 ===
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        self.start_btn = ttk.Button(btn_frame, text="크롤링 시작", command=self.start_crawling)
        self.start_btn.pack(side=tk.LEFT)

        self.stop_btn = ttk.Button(btn_frame, text="중단", command=self.stop_crawling, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="결과 저장 (엑셀)", command=self.save_to_excel).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="결과 지우기", command=self.clear_results).pack(side=tk.LEFT)

        # 통계
        self.stats_label = ttk.Label(btn_frame, text="수집: 0건 | 이메일: 0개")
        self.stats_label.pack(side=tk.RIGHT)

        # === 로그 영역 ===
        log_frame = ttk.LabelFrame(main_frame, text="진행 상황", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, height=15, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=log_scroll.set)

        # === 결과 테이블 ===
        result_frame = ttk.LabelFrame(main_frame, text="수집 결과", padding="5")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        columns = ('업체명', '이메일', '전화번호', '주소', '웹사이트')
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show='headings', height=8)

        for col in columns:
            self.result_tree.heading(col, text=col)
            self.result_tree.column(col, width=120)

        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        result_scroll = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        result_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_tree.configure(yscrollcommand=result_scroll.set)

    def on_type_change(self, event=None):
        """크롤러 유형 변경 시"""
        crawler_type = self.crawler_type.get().split(" - ")[0]

        if crawler_type == "website":
            self.url_frame.pack(fill=tk.X, pady=5, after=self.url_frame.master.winfo_children()[1])
            self.region_frame.pack_forget()
        else:
            self.url_frame.pack_forget()
            self.region_frame.pack(fill=tk.X, pady=5)

    def load_urls_from_file(self):
        """파일에서 URL 목록 불러오기"""
        filepath = filedialog.askopenfilename(
            title="URL 파일 선택",
            filetypes=[("텍스트 파일", "*.txt"), ("CSV 파일", "*.csv"), ("모든 파일", "*.*")]
        )
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.url_text.delete("1.0", tk.END)
                self.url_text.insert("1.0", content)
                self.log(f"[정보] URL 파일 불러옴: {filepath}")
            except Exception as e:
                messagebox.showerror("오류", f"파일 읽기 실패: {e}")

    def log(self, message):
        """로그 출력"""
        self.log_text.configure(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)
        self.root.update_idletasks()

    def update_stats(self):
        """통계 업데이트"""
        total = len(self.collected_data)
        emails = len([d for d in self.collected_data if d.get('이메일')])
        self.stats_label.config(text=f"수집: {total}건 | 이메일: {emails}개")

    def add_result(self, data):
        """결과 테이블에 추가"""
        self.collected_data.append(data)
        self.result_tree.insert('', tk.END, values=(
            data.get('업체명', ''),
            data.get('이메일', ''),
            data.get('전화번호', ''),
            data.get('주소', ''),
            data.get('웹사이트', '')
        ))
        self.update_stats()

    def clear_results(self):
        """결과 지우기"""
        if self.collected_data and not messagebox.askyesno("확인", "수집된 결과를 모두 지우시겠습니까?"):
            return
        self.collected_data = []
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        self.update_stats()
        self.log("[정보] 결과가 지워졌습니다.")

    def setup_driver(self):
        """Chrome 드라이버 설정"""
        options = Options()
        if self.headless_var.get():
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver

    def extract_emails(self, text):
        """이메일 추출"""
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(pattern, text)
        # 이미지 파일 등 제외
        return [e for e in emails if not e.endswith(('.png', '.jpg', '.gif', '.js', '.css'))]

    def extract_phones(self, text):
        """전화번호 추출"""
        pattern = r'0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}'
        return list(set(re.findall(pattern, text)))

    def crawl_website(self, url, driver):
        """단일 웹사이트 크롤링"""
        import time

        found_emails = set()
        found_phones = set()

        try:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            driver.set_page_load_timeout(15)
            driver.get(url)
            time.sleep(2)

            # 페이지 소스에서 추출
            page_source = driver.page_source
            emails = self.extract_emails(page_source)
            phones = self.extract_phones(page_source)
            found_emails.update(emails)
            found_phones.update(phones)

            # mailto 링크
            try:
                mailto_links = driver.find_elements(By.CSS_SELECTOR, "a[href^='mailto:']")
                for link in mailto_links:
                    href = link.get_attribute('href')
                    if href:
                        email = href.replace('mailto:', '').split('?')[0].strip()
                        if '@' in email:
                            found_emails.add(email)
            except:
                pass

            # 연락처 페이지 탐색
            if not found_emails:
                contact_keywords = ['contact', 'about', '연락', '문의', '회사소개']
                try:
                    links = driver.find_elements(By.TAG_NAME, "a")
                    for link in links[:30]:
                        try:
                            href = link.get_attribute('href') or ''
                            text = link.text.lower()
                            for keyword in contact_keywords:
                                if keyword in href.lower() or keyword in text:
                                    if href.startswith('http'):
                                        driver.get(href)
                                        time.sleep(1.5)
                                        emails = self.extract_emails(driver.page_source)
                                        found_emails.update(emails)
                                        if found_emails:
                                            break
                        except:
                            continue
                        if found_emails:
                            break
                except:
                    pass

        except Exception as e:
            self.log(f"  [오류] {url}: {str(e)[:50]}")

        return list(found_emails), list(found_phones)

    def start_crawling(self):
        """크롤링 시작"""
        if not SELENIUM_AVAILABLE:
            messagebox.showerror("오류", "selenium 패키지가 설치되지 않았습니다.\npip install selenium webdriver-manager")
            return

        if self.is_running:
            return

        self.is_running = True
        self.stop_flag = False
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        # 백그라운드 스레드에서 실행
        thread = threading.Thread(target=self.run_crawling, daemon=True)
        thread.start()

    def run_crawling(self):
        """실제 크롤링 실행"""
        import time

        crawler_type = self.crawler_type.get().split(" - ")[0]
        max_count = int(self.max_count.get())

        self.log(f"[시작] 크롤링 시작 - 유형: {crawler_type}, 최대: {max_count}개")

        driver = None
        try:
            self.log("[정보] Chrome 드라이버 초기화 중...")
            driver = self.setup_driver()
            self.log("[정보] Chrome 드라이버 준비 완료")

            if crawler_type == "website":
                # URL 목록 파싱
                url_text = self.url_text.get("1.0", tk.END)
                urls = []
                for line in url_text.strip().split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        urls.append(line)

                if not urls:
                    self.log("[오류] 크롤링할 URL이 없습니다.")
                    return

                urls = urls[:max_count]
                total = len(urls)

                for idx, url in enumerate(urls, 1):
                    if self.stop_flag:
                        self.log("[중단] 사용자에 의해 중단됨")
                        break

                    self.log(f"[{idx}/{total}] {url}")
                    emails, phones = self.crawl_website(url, driver)

                    if emails:
                        for email in emails:
                            self.root.after(0, lambda e=email, u=url, p=phones: self.add_result({
                                '업체명': '',
                                '이메일': e,
                                '전화번호': p[0] if p else '',
                                '주소': '',
                                '웹사이트': u
                            }))
                        self.log(f"  -> 이메일 발견: {emails}")
                    else:
                        self.log(f"  -> 이메일 없음")

                    time.sleep(1)
            else:
                # 협회 크롤링 (기존 로직)
                self.log("[정보] 협회 크롤링은 아직 구현 중입니다.")

            self.log("[완료] 크롤링 완료!")

        except Exception as e:
            self.log(f"[오류] 크롤링 실패: {e}")
        finally:
            if driver:
                driver.quit()
            self.is_running = False
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))

    def stop_crawling(self):
        """크롤링 중단"""
        self.stop_flag = True
        self.log("[정보] 중단 요청됨... 현재 작업 완료 후 중단됩니다.")

    def save_to_excel(self):
        """엑셀로 저장"""
        if not self.collected_data:
            messagebox.showwarning("경고", "저장할 데이터가 없습니다.")
            return

        if not PANDAS_AVAILABLE:
            messagebox.showerror("오류", "pandas 패키지가 설치되지 않았습니다.\npip install pandas openpyxl")
            return

        filepath = filedialog.asksaveasfilename(
            title="엑셀 파일 저장",
            defaultextension=".xlsx",
            initialfilename=f"크롤링결과_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            filetypes=[("Excel 파일", "*.xlsx")]
        )

        if filepath:
            try:
                df = pd.DataFrame(self.collected_data)
                df.to_excel(filepath, index=False, sheet_name='크롤링결과')
                self.log(f"[저장] 엑셀 파일 저장 완료: {filepath}")
                messagebox.showinfo("완료", f"저장 완료!\n{filepath}")
            except Exception as e:
                messagebox.showerror("오류", f"저장 실패: {e}")

    def show_server_dialog(self):
        """서버에서 URL 가져오기 다이얼로그"""
        dialog = tk.Toplevel(self.root)
        dialog.title("서버에서 URL 가져오기")
        dialog.geometry("400x350")
        dialog.transient(self.root)
        dialog.grab_set()

        # 메인 프레임
        main_frame = ttk.Frame(dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 서버 URL 설정
        server_frame = ttk.LabelFrame(main_frame, text="서버 설정", padding="10")
        server_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(server_frame, text="서버 URL:").pack(anchor=tk.W)
        self.server_url_var = tk.StringVar(value=SERVER_URL)
        ttk.Entry(server_frame, textvariable=self.server_url_var, width=50).pack(fill=tk.X, pady=(5, 0))

        # 필터 설정
        filter_frame = ttk.LabelFrame(main_frame, text="필터", padding="10")
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        # 카테고리
        ttk.Label(filter_frame, text="카테고리:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.filter_category_var = tk.StringVar(value="")
        category_combo = ttk.Combobox(filter_frame, textvariable=self.filter_category_var, width=30)
        category_combo['values'] = ["(전체)", "변호사", "법무사", "세무사", "공인회계사", "변리사", "노무사"]
        category_combo.current(0)
        category_combo.grid(row=0, column=1, padx=(10, 0), pady=2)

        # 지역
        ttk.Label(filter_frame, text="지역:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.filter_region_var = tk.StringVar(value="")
        region_combo = ttk.Combobox(filter_frame, textvariable=self.filter_region_var, width=30)
        region_combo['values'] = ["(전체)", "서울", "경기", "부산", "대구", "인천", "광주", "대전", "울산",
                                   "세종", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
        region_combo.current(0)
        region_combo.grid(row=1, column=1, padx=(10, 0), pady=2)

        # 가져올 개수
        ttk.Label(filter_frame, text="최대 개수:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.filter_limit_var = tk.StringVar(value="100")
        ttk.Entry(filter_frame, textvariable=self.filter_limit_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        # 이메일 없는것만
        self.filter_no_email_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(filter_frame, text="이메일이 없는 업체만", variable=self.filter_no_email_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        # 상태 표시
        self.server_status_var = tk.StringVar(value="")
        ttk.Label(main_frame, textvariable=self.server_status_var, foreground="blue").pack(pady=5)

        # 버튼
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_frame, text="URL 가져오기", command=lambda: self.fetch_urls_from_server(dialog)).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="닫기", command=dialog.destroy).pack(side=tk.RIGHT)

    def fetch_urls_from_server(self, dialog):
        """서버에서 URL 목록 가져오기"""
        if not URLLIB_AVAILABLE:
            messagebox.showerror("오류", "urllib 모듈을 사용할 수 없습니다.")
            return

        try:
            self.server_status_var.set("서버에서 데이터를 가져오는 중...")
            dialog.update()

            # 요청 URL 구성
            base_url = self.server_url_var.get().rstrip('/')
            params = []

            category = self.filter_category_var.get()
            if category and category != "(전체)":
                params.append(f"category={urllib.parse.quote(category)}")

            region = self.filter_region_var.get()
            if region and region != "(전체)":
                params.append(f"region={urllib.parse.quote(region)}")

            limit = self.filter_limit_var.get()
            if limit:
                params.append(f"limit={limit}")

            if self.filter_no_email_var.get():
                params.append("no_email=true")

            params.append("format=json")

            url = f"{base_url}/api/local-businesses/crawler-urls/"
            if params:
                url += "?" + "&".join(params)

            self.log(f"[서버] 요청 URL: {url}")

            # HTTP 요청
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'DungjiCrawler/1.0')

            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))

            # 결과 처리
            if 'businesses' in data:
                businesses = data['businesses']
                count = len(businesses)

                # URL 텍스트에 추가
                urls = []
                for biz in businesses:
                    url_val = biz.get('website_url', '')
                    name = biz.get('name', '')
                    if url_val:
                        urls.append(f"# {name}")
                        urls.append(url_val)

                if urls:
                    self.url_text.delete("1.0", tk.END)
                    self.url_text.insert("1.0", "\n".join(urls))

                self.server_status_var.set(f"✓ {count}개의 URL을 가져왔습니다!")
                self.log(f"[서버] {count}개의 URL을 가져왔습니다.")
                messagebox.showinfo("완료", f"{count}개의 URL을 가져왔습니다!")
            else:
                self.server_status_var.set("데이터가 없습니다.")
                self.log("[서버] 데이터가 없습니다.")

        except urllib.error.HTTPError as e:
            error_msg = f"HTTP 오류: {e.code} - {e.reason}"
            self.server_status_var.set(error_msg)
            self.log(f"[서버 오류] {error_msg}")
            messagebox.showerror("서버 오류", error_msg)
        except urllib.error.URLError as e:
            error_msg = f"연결 오류: {e.reason}"
            self.server_status_var.set(error_msg)
            self.log(f"[서버 오류] {error_msg}")
            messagebox.showerror("연결 오류", f"서버에 연결할 수 없습니다.\n{error_msg}")
        except Exception as e:
            error_msg = str(e)
            self.server_status_var.set(f"오류: {error_msg}")
            self.log(f"[서버 오류] {error_msg}")
            messagebox.showerror("오류", error_msg)


def main():
    root = tk.Tk()
    app = CrawlerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
