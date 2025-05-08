import sqlite3
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import urllib3

# 禁用 InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 設定數據庫
def init_db():
    conn = sqlite3.connect('announcements.db')
    c = conn.cursor()
    # 如果資料表不存在，創建一個
    c.execute('''
    CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY,
        title TEXT,
        url TEXT UNIQUE
    )
    ''')
    conn.commit()
    return conn, c

# 檢查公告是否已經在數據庫中
def is_announcement_exist(c, url):
    c.execute('SELECT 1 FROM announcements WHERE url = ?', (url,))
    return c.fetchone() is not None

# 將公告儲存到數據庫
def save_announcement(c, title, url):
    c.execute('INSERT INTO announcements (title, url) VALUES (?, ?)', (title, url))
    c.connection.commit()

def fetch_announcement():
    # 設定要抓取的網址
    url = "https://www.tnssh.tn.edu.tw/category/imp/"

    # 設定 Chrome 瀏覽器選項
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 無頭模式 (不顯示瀏覽器界面)
    chrome_options.add_argument("--disable-gpu")  # 禁用 GPU 加速

    # 設定 ChromeDriver 路徑
    chrome_driver_path =   "./chromedriver.exe"            # "/home/iceiceyan618/driver/chromedriver"   修改為你的 ChromeDriver 路徑

    # 設定 WebDriver
    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # 訪問網頁
    driver.get(url)

    # 等待頁面加載完成，等待公告標題元素出現
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.XPATH, "//article"))
        )
    except TimeoutException:
        print("頁面加載超時，請檢查網絡連接。")
        driver.quit()
        return "頁面加載超時，請檢查網絡連接。"

    # 找到所有公告的 article 元素
    articles = driver.find_elements(By.XPATH, "//article")

    # 要查找的關鍵字，進行不區分大小寫匹配
    keywords = ["高一", "全校", "重要公告", "113學年","114學年","衛生組"]
    results = []

    # 設定數據庫
    conn, c = init_db()

    # 篩選出包含關鍵字的公告標題並點擊查看詳細內容
    for index, article in enumerate(articles, start=1):
        # 找到公告標題
        title_element = article.find_element(By.XPATH, ".//header/h4/a")
        title_text = title_element.text.strip()  # 去除多餘的空白
        url_text = title_element.get_attribute('href')

        # 檢查標題中是否包含任何一個關鍵字，忽略大小寫
        if any(keyword.lower() in title_text.lower() for keyword in keywords):
            # 檢查這個公告是否已經爬取過
            if is_announcement_exist(c, url_text):
                print(f"公告已經爬取過，跳過: {title_text}")
                continue  # 跳過已經爬取過的公告

            result = f"# 📢{title_text}"
            

            try:
                # 模擬點擊標題連結
                title_element.click()

                # 等待新頁面加載，確保公告內容加載完成
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//article/div[1]"))
                )

                # 尋找所有相關的 <p> 和 <a> 標籤
                content_elements = driver.find_elements(By.XPATH, "//article/div[1]/p | //article/div[1]/div/a | //article/div[1]//a")


                # 初始化完整內容的字符串
                full_content = ""

                 # 遍歷所有找到的元素
                for element in content_elements:
                    if element.tag_name == "a":  # 如果是 <a> 標籤
                       link_text = element.text.strip()  # 提取連結的文本
                       link_url = element.get_attribute('href')  # 提取連結的 href 屬性
                       link_title = element.get_attribute('title')  # 提取連結的 title 屬性（如果有）

                       if link_text == "下載":
                          continue
        
                     # 將連結格式化為指定格式
                       if link_text and link_url:
                        full_content += f"[{link_text}]({link_url})\n"
                       elif link_title and link_url:  # 如果沒有連結文本，用 title 替代
                            full_content += f"[{link_title}] ({link_url})\n"
                    else:  # 處理 <p> 標籤
                       full_content += element.text.strip() + "\n"

                    # 去除多餘的空行
                full_content = full_content.strip()

             # 添加到結果中
                result += f"\n公告內容:\n{full_content}"


                # 將這個公告保存到數據庫
                save_announcement(c, title_text, url_text)

                # 返回主頁繼續抓取其他公告
                driver.back()

                # 等待頁面返回主頁，並確保公告標題加載完成
                WebDriverWait(driver, 20).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//article"))
                )
                # 重新獲取所有的 article 元素
                articles = driver.find_elements(By.XPATH, "//article")

            except Exception as e:
                result += f"\n錯誤: {e}"
                driver.back()
                WebDriverWait(driver, 20).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//article"))
                )

            results.append(result)

    # 關閉瀏覽器並關閉數據庫連接
    driver.quit()
    conn.close()

    # 若有多則公告，拆分成兩段訊息發送
    if results:
        # 每則公告作為一條訊息返回
        for idx, result in enumerate(results, start=1):
            print(f"發送公告 {idx}:\n{result}\n\n")  # 你可以將這裡的 print 換成發送訊息的程式碼

    return "\n\n".join(results) if results else None

# 如果要執行爬蟲，可以直接呼叫 fetch_announcement 函數
if __name__ == "__main__":
    print(fetch_announcement())
