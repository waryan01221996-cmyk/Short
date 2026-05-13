import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import random
import sys

def log(message):
    timestamp = time.strftime("%H:%M:%S", time.localtime())
    print(f"[{timestamp}] {message}", flush=True)

def run_bot():
    log("=== MEMULAI BOT TRAFFIC (SINGLE RUN) ===")
    
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    driver = None
    try:
        log("Membuka browser...")
        driver = uc.Chrome(options=options)
        
        links = [
            "https://sfl.gl/DBAlFU",
            "https://sfl.gl/6zJpYNM"
        ]
        
        random.shuffle(links)

        for index, link in enumerate(links, 1):
            log(f"--- Memproses Link {index}/{len(links)} ---")
            log(f"Target: {link}")
            
            try:
                driver.get(link)
                log(f"Halaman terbuka: {driver.title}")
                
                # Menunggu loading awal halaman iklan
                time.sleep(15)
                
                # Mencoba klik tombol transisi (Continue/Get Link)
                buttons = driver.find_elements(By.TAG_NAME, "button")
                found_btn = False
                for btn in buttons:
                    text = btn.text.lower()
                    if any(x in text for x in ["continue", "next", "get link", "lanjut"]):
                        log(f"Menemukan tombol: '{btn.text}' - Mencoba klik...")
                        driver.execute_script("arguments[0].click();", btn)
                        found_btn = True
                        break
                
                # Stay di halaman untuk validasi traffic
                wait = random.randint(25, 45)
                log(f"Stay di halaman selama {wait} detik agar traffic valid...")
                time.sleep(wait)
                
                log(f"URL Terakhir: {driver.current_url}")
                log("Selesai memproses link ini.")

            except Exception as e:
                log(f"Gagal memproses link ini: {str(e)}")

    except Exception as e:
        log(f"CRITICAL ERROR: {str(e)}")
    
    finally:
        if driver:
            driver.quit()
            log("Browser ditutup.")
        log("=== PROSES SELESAI (TIDAK ADA RERUN) ===")

if __name__ == "__main__":
    run_bot()
