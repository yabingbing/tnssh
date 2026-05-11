import sqlite3
import requests
import os
import shutil
import tempfile
import urllib3

# 關閉未驗證 HTTPS 請求的警告訊息。
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def resolve_chrome_driver_path():
    return os.getenv("CHROMEDRIVER_PATH") or shutil.which("chromedriver")

# 初始化公告資料庫連線與資料表。
def init_db():
    conn = sqlite3.connect('announcements.db')
    c = conn.cursor()
    # 第一次執行時建立公告去重用的資料表。
    c.execute('''
    CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY,
        title TEXT,
        url TEXT UNIQUE
    )
    ''')
    conn.commit()
    return conn, c

# 檢查公告網址是否已經儲存過。
def is_announcement_exist(c, url):
    c.execute('SELECT 1 FROM announcements WHERE url = ?', (url,))
    return c.fetchone() is not None

# 儲存公告標題與網址，供下次爬取時去重。
def save_announcement(c, title, url):
    c.execute('INSERT INTO announcements (title, url) VALUES (?, ?)', (title, url))
    c.connection.commit()

def fetch_announcement():
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException

    # 目標為校網重要公告列表。
    url = "https://www.tnssh.tn.edu.tw/category/imp/"
    driver = None
    conn = None
    chrome_profile_dir = tempfile.mkdtemp(prefix="chrome_profile_tnssh_")

    # 設定無介面的 Chrome 執行環境。
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f"--user-data-dir={chrome_profile_dir}")
    chrome_options.add_argument("--disable-gpu")
# 其他系統相容性選項可依部署環境追加。

    # 取得 ChromeDriver 路徑。
    chrome_driver_path = resolve_chrome_driver_path()
    if not chrome_driver_path:
        shutil.rmtree(chrome_profile_dir, ignore_errors=True)
        raise RuntimeError("找不到 chromedriver，請安裝 chromedriver 或設定 CHROMEDRIVER_PATH。")

    try:
        # 建立 Selenium WebDriver。
        service = Service(chrome_driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # 開啟公告列表頁。
        driver.get(url)

        # 等待公告文章載入完成。
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_all_elements_located((By.XPATH, "//article"))
            )
        except TimeoutException:
            print("頁面加載超時，請檢查網絡連接。")
            return "頁面加載超時，請檢查網絡連接。"

        # 取得目前頁面中的所有公告項目。
        articles = driver.find_elements(By.XPATH, "//article")

        # 只處理標題包含這些關鍵字的公告。
        keywords = ["高一", "全校", "重要公告", "113學年","114學年","衛生組","K館"]
        results = []

        # 開啟資料庫，避免重複發送同一則公告。
        conn, c = init_db()

        # 逐筆檢查公告標題，符合條件才進入內頁。
        for index, article in enumerate(articles, start=1):
            # 取得公告標題與連結。
            title_element = article.find_element(By.XPATH, ".//header/h4/a")
            title_text = title_element.text.strip()  # 移除標題前後空白。
            url_text = title_element.get_attribute('href')

            # 以不分大小寫方式比對關鍵字。
            if any(keyword.lower() in title_text.lower() for keyword in keywords):
                # 已儲存的公告略過，避免重複通知。
                if is_announcement_exist(c, url_text):
                    print(f"公告已經爬取過，跳過: {title_text}")
                    continue  # 略過已處理公告。

                result = f"# 📢{title_text}"

                try:
                    # 點擊標題進入公告內頁。
                    title_element.click()

                    # 等待公告內容區塊載入。
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, "//article/div[1]"))
                    )

                    # 抓取正文段落與相關連結。
                    content_elements = driver.find_elements(By.XPATH, "//article/div[1]/p | //article/div[1]/div/a | //article/div[1]//a")


                    # 累積整理後的公告內容。
                    full_content = ""

                    # 逐一整理段落與連結文字。
                    for element in content_elements:
                        if element.tag_name == "a":  # 連結元素需轉成 Markdown 格式。
                           link_text = element.text.strip()  # 取得連結顯示文字。
                           link_url = element.get_attribute('href')  # 取得連結網址。
                           link_title = element.get_attribute('title')  # 沒有顯示文字時使用 title。

                           if link_text == "下載":
                              continue

                           # 將有效連結轉成 Markdown 連結。
                           if link_text and link_url:
                            full_content += f"[{link_text}]({link_url})\n"
                           elif link_title and link_url:  # 沒有連結文字時改用 title。
                                full_content += f"[{link_title}] ({link_url})\n"
                        else:  # 一般段落直接加入內容。
                           full_content += element.text.strip() + "\n"

                    # 移除首尾多餘空白與空行。
                    full_content = full_content.strip()

                    # 將正文接到公告標題後方。
                    result += f"\n公告內容:\n{full_content}"


                    # 成功處理後寫入資料庫。
                    save_announcement(c, title_text, url_text)

                    # 回到列表頁繼續處理下一則公告。
                    driver.back()

                    # 確認列表頁已重新載入。
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_all_elements_located((By.XPATH, "//article"))
                    )
                    # 返回後元素參照會失效，需重新取得列表。
                    articles = driver.find_elements(By.XPATH, "//article")

                except Exception as e:
                    result += f"\n錯誤: {e}"
                    driver.back()
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_all_elements_located((By.XPATH, "//article"))
                    )

                results.append(result)

        # 有新公告時逐則輸出，方便後續改成 Discord 發送。
        if results:
            # 每則公告獨立輸出。
            for idx, result in enumerate(results, start=1):
                print(f"發送公告 {idx}:\n{result}\n\n")  # 可改成實際訊息發送邏輯。

        return "\n\n".join(results) if results else None
    finally:
        if driver:
            driver.quit()
        if conn:
            conn.close()
        shutil.rmtree(chrome_profile_dir, ignore_errors=True)

# 直接執行此檔案時，單獨測試公告爬蟲。
if __name__ == "__main__":
    print(fetch_announcement())
