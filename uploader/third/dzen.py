import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import os
import re

def setup_driver():
    options = uc.ChromeOptions()
    options.add_experimental_option("prefs", {"profile.default_content_setting_values.notifications": 2})
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    return uc.Chrome(options=options)

def wait_for_upload(driver):
    # Wait for upload completion with dynamic timeout based on file size
    file_size_mb = os.path.getsize("/home/kda/comdy.mp4") / (1024 * 1024) if os.path.exists("/home/kda/comdy.mp4") else 100
    max_wait = max(300, int(file_size_mb * 8))  # 8 seconds per MB, minimum 5 minutes
    
    try:
        WebDriverWait(driver, max_wait).until(
            EC.any_of(
                EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Загрузили видео')]")),
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='publish-btn']:not([disabled])"))
            )
        )
        return True
    except:
        return False

def login_and_upload(driver, video_path, title="Comedy Video"):
    # Login with cookies
    driver.get("https://dzen.ru")
    cookies = [
        {"name": "zencookie", "value": "8297893231744362383"},
        {"name": "yandexuid", "value": "4525498611744362383"},
        {"name": "zen_session_id", "value": "OhYi0aEfWJ4WyVHhBJ0nitiKfdOSDe1FqYd.1751052297362"},
        {"name": "Session_id", "value": "3:1751198729.5.0.1751198729440:hknTnA:ad22.1.0.0:3.1:366200649.3:1749838046|64:10029481.483364.yhJ_JqWAm1v_d9_VrNWAdgGyXPE"}
    ]
    
    for c in cookies:
        try: driver.add_cookie({**c, "domain": ".dzen.ru", "path": "/"})
        except: pass
    
    # Navigate and upload
    driver.get("https://dzen.ru/profile/editor/id/67fe5ca67c0c2872e1590bec/publications?state=published")
    time.sleep(3)
    
    # Close modals
    try:
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        driver.execute_script("document.querySelectorAll('[data-testid=\"modal-overlay\"], .modal__overlay').forEach(el => el.style.display = 'none');")
    except: pass
    
    # Upload process
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='add-publication-button']"))).click()
    time.sleep(2)
    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//label[@aria-label='Загрузить видео']"))).click()
    time.sleep(2)
    
    # Upload file
    file_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
    file_input.send_keys(video_path)
    print("Video uploaded")
    
    # Wait for upload completion - OPTIMIZED PART
    if not wait_for_upload(driver):
        print("Upload timeout")
        return None
    
    time.sleep(5)
    
    try:
        title_textarea = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "textarea.Texteditor-Control:not(.Texteditor-Control_isHidden)")))
        title_textarea.clear()
        title_textarea.send_keys(title)
        print("Title set")
    except: print("Could not set title")
    
    # Publish
    WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='publish-btn']"))).click()
    print("Published")
    
    # Extract video URL with multiple attempts
    for attempt in range(6):
        time.sleep(10)
        try:
            url = driver.current_url
            
            if "videoEditorPublicationId=" in url:
                video_id = url.split("videoEditorPublicationId=")[1].split("&")[0]
                return f"https://dzen.ru/video/watch/{video_id}"
            
            if "/video/watch/" in url:
                return url
            
            match = re.search(r'"videoId":"([^"]+)"', driver.page_source)
            if match:
                return f"https://dzen.ru/video/watch/{match.group(1)}"
            
            try:
                link = driver.find_element(By.CSS_SELECTOR, "a[href*='/video/watch/']")
                return link.get_attribute("href")
            except: pass
            
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
    
    try:
        driver.get("https://dzen.ru/profile/editor/id/67fe5ca67c0c2872e1590bec/publications?state=published")
        time.sleep(5)
        link = driver.find_element(By.CSS_SELECTOR, "a[href*='/video/watch/']")
        return link.get_attribute("href")
    except:
        return None

def main_with_path(video_path, title="Uploaded Video"):
    if not os.path.exists(video_path):
        return None
    
    driver = setup_driver()
    try:
        return login_and_upload(driver, video_path, title)
    except:
        return None
    finally:
        driver.quit()

def main():
    return main_with_path("/workspaces/tools/Kryptic (2024) [1080p] [WEBRip] [5.1] [YTS.MX]/qe.mp4", "Comssedy Video")

if __name__ == "__main__":
    result = main()
    print(f"Result: {result}")