import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, os, re

def setup_driver():
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    return uc.Chrome(driver_executable_path="/home/kda/ok/chromedriver-linux64/chromedriver", version_main=137, options=options)

def safe_click(driver, element):
    for method in [lambda: element.click(), lambda: driver.execute_script("arguments[0].click();", element)]:
        try: method(); return True
        except: continue
    return False

def find_click(driver, selectors, timeout=10):
    for selector in selectors:
        try:
            element = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            if safe_click(driver, element): return True
        except: continue
    return False

def main_with_path(video_path):
    """Modified main function that accepts video path as parameter"""
    if not os.path.exists(video_path): 
        print(f"❌ Video not found: {video_path}")
        return None
    
    driver = setup_driver()
    try:
        # Login
        driver.get("https://ok.ru")
        for cookie in [{"name": "userIds", "value": "910080290458", "domain": ".ok.ru"}, 
                      {"name": "sAuth910080290458", "value": "W0OalXzzGSTMYE623O2bRNBqEjut_0jldPNDtOsozTMXv7wBsTq1ft3G7bDlvhZCTY6aXfCIVzESNJxKtjIRvZwVJ-V8soWcSUauEMVB8X-BEpPBsHaiHEyicYAYPhtjpQuw0Q4Lknjj7XtZpw_5", "domain": ".ok.ru"},
                      {"name": "AUTHCODE", "value": "d3Zmm2jcUVteEJ72_QfPmPnOOOJ17K9TZiNYFzmMz37-xUPrvBS6U5GGYa8QQjsquBQX1JiMFKSuEp8IBY5ml3sxmPn5qjIbVGVB7uWw2atHhkpZjGGvu7QR9xvmoWbmhKDy6Hm2ZV_7SAdggA_5", "domain": ".ok.ru"},
                      {"name": "JSESSIONID", "value": "b22052da389727beb77cf6274b7b4019c1f42812331b34af.38e859c5", "domain": ".ok.ru"}]:
            driver.add_cookie(cookie)
        
        # Upload
        driver.get("https://ok.ru/video/manager")
        time.sleep(3)
        
        file_input = None
        for selector in ["input[type='file']", "input[accept*='video']", ".js-uploader-input input[type='file']"]:
            try: file_input = driver.find_element(By.CSS_SELECTOR, selector); break
            except: continue
        
        if not file_input:
            find_click(driver, ["button[data-l*='upload']", ".js-uploader-button", "[class*='upload']"], 5)
            time.sleep(1)
            for selector in ["input[type='file']", "input[accept*='video']"]:
                try: file_input = driver.find_element(By.CSS_SELECTOR, selector); break
                except: continue
        
        if not file_input: raise Exception("File input not found")
        
        file_input.send_keys(video_path)
        print("✓ Video uploaded")
        time.sleep(10)
        
        # Publish
        if not find_click(driver, [".js-uploader-publish-link", ".publish-btn", "[data-l*='publish']"], 30):
            try: safe_click(driver, WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Опубликовать')]"))))
            except: raise Exception("Publish button not found")
        
        print("✓ Video published")
        
        # Handle dialog
        try: time.sleep(2); safe_click(driver, driver.find_element(By.XPATH, "//button[contains(text(), 'Нет')]"))
        except: pass
        
        time.sleep(5)
        
        # Get URL
        video_match = re.search(r'/video/(\d{13,})', driver.current_url)
        if video_match: video_url = f"https://ok.ru/video/{video_match.group(1)}"
        else:
            for pattern in [r'"videoId":"(\d{13,})"', r'video/(\d{13,})']:
                matches = re.findall(pattern, driver.page_source)
                if matches: video_url = f"https://ok.ru/video/{matches[0]}"; break
            else:
                try:
                    driver.get("https://ok.ru/profile/910080290458/videos")
                    time.sleep(3)
                    href = driver.find_element(By.CSS_SELECTOR, "a[href*='/video/']").get_attribute("href")
                    video_url = href if href and re.search(r'/video/\d{13,}', href) else None
                except: video_url = None
        
        if video_url: 
            return video_url
        else: 
            print("❌ Failed to get video URL")
            return None
        
    except Exception as e: 
        print(f"Error: {e}")
        return None
    finally: 
        driver.quit()

def main():
    """Original main function for backward compatibility"""
    video_path = "/home/kda/AURORA - The Seed 🌿{#aurora #vocal #live #mashup} [Cj11YXylsi8].mp4"
    return main_with_path(video_path)

if __name__ == "__main__": 
    print(f"Result: {main()}")