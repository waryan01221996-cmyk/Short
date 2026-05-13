import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import random
import sys

def log(message):
    timestamp = time.strftime("%H:%M:%S", time.localtime())
    print(f"[{timestamp}] {message}", flush=True)

def run_bot():
    log("=== MEMULAI BOT TRAFFIC (VERSI PERBAIKAN) ===")
    
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = None
    try:
        log("Mencoba inisialisasi browser (Auto-detecting version)...")
        # undetected-chromedriver akan mencoba mencocokkan versi secara otomatis
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
                
                # Tunggu loading iklan
                time.sleep(15)
                
                # Logika klik tombol otomatis
                buttons = driver.find_elements(By.TAG_NAME, "button")
                found_btn = False
                for btn in buttons:
                    text = btn.text.lower()
                    if any(x in text for x in ["continue", "next", "get link", "lanjut"]):
                        log(f"Menemukan tombol: '{btn.text}' - Mencoba klik...")
                        driver.execute_script("arguments[0].click();", btn)
                        found_btn = True
                        break
                
                # Waktu tunggu agar traffic dianggap valid oleh penyedia shortlink
                wait = random.randint(30, 50)
                log(f"Stay di halaman selama {wait} detik...")
                time.sleep(wait)
                
                log(f"URL Akhir: {driver.current_url}")
                log("Selesai memproses satu link.")

            except Exception as e:
                log(f"Gagal pada link ini: {str(e)}")

    except Exception as e:
        log(f"CRITICAL ERROR: {str(e)}")
        log("Tips: Jika error 'session not created', pastikan versi Chrome di main.yml sudah terbaru.")
    
    finally:
        if driver:
            driver.quit()
            log("Browser ditutup.")
        log("=== PROSES SELESAI ===")

if __name__ == "__main__":
    run_bot()
