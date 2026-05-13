import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import random
import os
import sys

def log(message):
    # Log dengan timestamp agar mudah dipantau di GitHub Actions
    timestamp = time.strftime("%H:%M:%S", time.localtime())
    print(f"[{timestamp}] {message}", flush=True)

def get_chrome_main_version():
    # Mendeteksi versi Chrome yang terinstal di runner Ubuntu
    try:
        version_output = os.popen('google-chrome --version').read()
        # Mengambil angka pertama (misal: 147 dari 147.0.7727.0)
        main_version = version_output.split()[2].split('.')[0]
        return int(main_version)
    except Exception as e:
        log(f"Gagal deteksi versi Chrome: {e}")
        return None

def run_bot():
    log("=== MEMULAI BOT TRAFFIC (STABLE VERSION) ===")
    
    version = get_chrome_main_version()
    log(f"Chrome terdeteksi versi: {version}")

    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    driver = None
    try:
        log("Inisialisasi driver...")
        # Memaksa driver menggunakan versi yang sama dengan browser
        driver = uc.Chrome(options=options, version_main=version)
        
        links = [
            "https://sfl.gl/DBAlFU",
            "https://sfl.gl/6zJpYNM"
        ]
        
        random.shuffle(links)

        for index, link in enumerate(links, 1):
            log(f"Memproses [{index}/{len(links)}]: {link}")
            try:
                driver.get(link)
                time.sleep(15) # Tunggu loading
                
                # Cari tombol interaksi secara luas
                potential_buttons = driver.find_elements(By.TAG_NAME, "button")
                for btn in potential_buttons:
                    text = btn.text.lower()
                    if any(x in text for x in ["continue", "get link", "next", "lanjut"]):
                        driver.execute_script("arguments[0].click();", btn)
                        log(f"Klik tombol: {btn.text}")
                        break
                
                # Simulasi waktu baca agar traffic valid
                wait_time = random.randint(30, 45)
                log(f"Menunggu {wait_time} detik...")
                time.sleep(wait_time)
                
                log(f"Status Akhir: {driver.current_url}")
            except Exception as e:
                log(f"Gagal pada link: {e}")

    except Exception as e:
        log(f"CRITICAL ERROR: {e}")
    finally:
        if driver:
            driver.quit()
            log("Browser ditutup.")

if __name__ == "__main__":
    run_bot()
