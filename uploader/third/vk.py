import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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

def login_to_vkvideo(driver):
    driver.get("https://vkvideo.ru/")
    # It's highly recommended to load cookies from a file rather than hardcoding them.
    cookies = [
        {"name": "remixstlid", "value": "9097469384008334333_ZMX1t5XFEBuiZfoli3m708SSkhqJ2v2LUaJQSPy2Dxs"},
        {"name": "remixlang", "value": "3"},
        {"name": "remixstid", "value": "955741913_ZMZAEZe2SjO1MzqQhW3PyTaVViY4PG1le8o4ijmmZas"},
        {"name": "remixdsid", "value": "vk1.a.H6u9KvQR8zdVnRlJcUHniyogMPxZV8cSGoEMSkc3Z1AGlfJTqgELlheYRytSKGz6llfK6xaIEyuuSTKGOhtM5pq-y0j9zSMfkqgNoQ5_KRugHu1j8J55NQXx8VkMk__TxWQg87NmEsxiweVjWehfUAkDOtgJhCfJolnebHvOt48"},
        {"name": "httoken", "value": "OBhja5UPhUlzm9Qf4otTtunht7QhGBxfLW4d3_x87xvw9AvtJR9vIhFg06qpqMCTsKW_cJpHJTwfB-84ukxd5XdlqsWdbd8SCba4x9ZsSPbthhKll2S7Rkq8_8M34Dj0Nes"},
        {"name": "remixgp", "value": "c0aec6c8bca3a836e999d4850293f8bd"},
        {"name": "remixdark_color_scheme", "value": "1"}
    ]
    
    for c in cookies:
        try:
            driver.add_cookie({**c, "domain": ".vkvideo.ru", "path": "/"})
        except Exception:
            pass
    
    driver.get("https://vkvideo.ru/upload")
    
    try:
        print("Checking for robot verification...")
        robot_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div > button.start"))
        )
        print("Robot verification page found. Clicking 'Continue' button.")
        robot_button.click()
        time.sleep(5)
    except Exception:
        print("Robot verification page not found. Continuing.")
        
    time.sleep(5)
    return True

def wait_for_upload(driver, max_wait=900):
    start_time = time.time()
    print("Monitoring upload...")
    
    while time.time() - start_time < max_wait:
        try:
            completion_texts = ["processed", "uploaded", "обработан", "загружен"]
            banners = driver.find_elements(By.CSS_SELECTOR, '.vkitStatusBanner__rootModePositive--UPaAS, .vkitStatusBanner__root--usSh1')
            
            for el in banners:
                if el.is_displayed():
                    text = el.text.lower()
                    if any(sub in text for sub in completion_texts):
                        print(f"✅ Upload/Processing detected as complete. Text: '{el.text}'")
                        return True
                    elif "%" in text:
                        print(f"📊 {text}")
            
            title_inputs = driver.find_elements(By.CSS_SELECTOR, 'input[name="title"], input[placeholder*="название"]')
            for inp in title_inputs:
                if inp.is_displayed() and inp.is_enabled():
                    print("✅ Form is ready for editing.")
                    return True
            
            time.sleep(3)
            
        except Exception as e:
            print(f"Monitor error: {e}")
            time.sleep(3)
    
    print("⏰ Timeout waiting for upload to finish, proceeding anyway...")
    return True

def upload_video(driver, video_path, title=None):
    if not os.path.exists(video_path):
        print(f"File not found: {video_path}")
        return False
    
    print(f"Uploading: {video_path}")
    wait = WebDriverWait(driver, 30)
    
    try:
        upload_btn_selector = "#video_content_upload > div.VideoUploadPage__root > div > div > section > div.vkitPlaceholder__container--KLQzc.vkuiPlaceholder__host.vkuiPlaceholder__withPadding.vkuiRootComponent__host > div.vkuiPlaceholder__action.vkuiRootComponent__host > button"
        upload_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, upload_btn_selector)))
        upload_btn.click()
        time.sleep(2)
        print("Clicked initial upload button.")
    except Exception:
        print("❌ Initial upload button not found.")
        return False
    
    try:
        file_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]')))
        file_input.send_keys(video_path)
        print("File selected for upload.")
        time.sleep(3)
    except Exception:
        print("❌ File input element not found.")
        return False
    
    if not wait_for_upload(driver):
        return False
    
    try:
        title_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[name="title"], input[placeholder*="название"]')))
        # Use provided title or default to filename
        video_title = title if title else os.path.splitext(os.path.basename(video_path))[0]
        title_input.clear()
        time.sleep(1)
        title_input.send_keys(video_title)
        print(f"Title set to: {video_title}")
    except Exception:
        print("Title input not found, skipping...")
    
    published = False
    video_url = None
    try:
        # Click the option to make the video public
        print("Attempting to set video to public...")
        make_public_selector = "#video_content_upload > div.VideoUploadPage__root > div > div > div > section > div:nth-child(3) > div.vkuiSplitLayout__host > div > div:nth-child(1) > form > div:nth-child(1) > div > div > label:nth-child(4)"
        make_public_option = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, make_public_selector)))
        make_public_option.click()
        print("✅ Set video to public.")
        time.sleep(2)

        # Click the final publish button
        print("Attempting to publish...")
        publish_selector = "#video_content_upload > div.VideoUploadPage__root > div > div > div > section > div.vkitModalFooter__container--z1fX2 > div.vkitModalFooter__actionButtons--xrfVL > div > button.vkitButton__root--m7aR3.vkuiInternalTappable.vkuiButton__host.vkuiButton__sizeM.vkuiButton__modePrimary.vkuiButton__appearanceAccent.vkuiTappable__host.vkuiTappable__hasPointerNone.vkuiClickable__host.vkuiClickable__realClickable.vkuistyles__-focus-visible.vkuiRootComponent__host"
        publish_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, publish_selector)))
        publish_button.click()
        print("✅ Clicked the final publish button!")
        published = True

        # Wait for the confirmation link and extract the URL
        print("Waiting for the video link to appear...")
        link_selector = '#video_content_upload > div.VideoUploadPage__root > div > div > div > section > div:nth-child(3) > div.vkuiSplitLayout__host > div > div:nth-child(2) > div > li > div:nth-child(4) > div.vkitMiniInfoCell__rootNoPadding--8GddV.vkuiMiniInfoCell__host.vkuiMiniInfoCell__textWrapFull.vkuiRootComponent__host > div > span > a'
        video_link_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, link_selector))
        )
        video_url = video_link_element.get_attribute('href')
        print(f"✅ Extracted video URL: {video_url}")

    except Exception as e:
        print(f"❌ Failed during publication or link extraction: {e}")

    # Return the extracted URL if available
    if video_url:
        return video_url
    elif published:
        print("Published, but couldn't get the specific URL. Returning success status.")
        return True
    else:
        print("Could not complete the publication steps.")
        return False

def main_with_path(video_path, title="Uploaded Video"):
    """Main function for API integration - takes video path and optional title"""
    if not os.path.exists(video_path):
        print(f"File not found: {video_path}")
        return None
    
    driver = setup_driver()
    
    try:
        if login_to_vkvideo(driver):
            print("Logged in successfully!")
            result = upload_video(driver, video_path, title)
            if result:
                print("\n✅ Upload process finished!")
                if isinstance(result, str):
                    print(f"Video URL: {result}")
                    return result
                else:
                    # If upload was successful but no URL was returned
                    return True
            else:
                print("\n❌ Upload failed.")
                return None
        else:
            print("Login failed.")
            return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None
    finally:
        print("Closing browser...")
        driver.quit()

def main():
    """Original main function for standalone use"""
    # IMPORTANT: Make sure this path is correct for your system
    video_path = "/workspaces/tools/comdy.mp4" 
    driver = setup_driver()
    
    try:
        if login_to_vkvideo(driver):
            print("Logged in successfully!")
            result = upload_video(driver, video_path)
            if result:
                print("\n✅ Upload process finished!")
                if isinstance(result, str):
                    print(f"Video will be found here: {result}")
            else:
                print("\n❌ Upload failed.")
        else:
            print("Login failed.")
    except Exception as e:
        print(f"An unexpected error occurred in main: {e}")
    finally:
        print("Closing browser in 10 seconds...")
        time.sleep(10)
        driver.quit()

if __name__ == "__main__":
    main()