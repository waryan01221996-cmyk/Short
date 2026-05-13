import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random

def run_bot():
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Menyamarkan bot agar terlihat seperti browser asli
    driver = uc.Chrome(options=options)
    
    links = [
        "https://sfl.gl/DBAlFU",
        "https://sfl.gl/6zJpYNM"
    ]
    
    random.shuffle(links)

    for link in links:
        try:
            print(f"Mengunjungi: {link}")
            driver.get(link)
            
            # Tahap 1: Menunggu dan mencari tombol 'Continue' atau sejenisnya
            # Kita gunakan selector umum yang sering dipakai shortlink
            time.sleep(random.randint(10, 15))
            
            # Mencoba klik tombol yang mungkin ada (Continue/Next)
            try:
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    if "continue" in btn.text.lower() or "next" in btn.text.lower():
                        driver.execute_script("arguments[0].click();", btn)
                        print("Tombol transisi diklik.")
                        break
            except:
                pass

            # Tahap 2: Menunggu link akhir muncul
            time.sleep(15)
            print(f"Posisi saat ini: {driver.current_url}")
            
            # Jika sampai ke link akhir, pundi uang biasanya baru terhitung
            print(f"Berhasil memproses link: {driver.title}")
            
        except Exception as e:
            print(f"Gagal pada {link}: {e}")
            
    driver.quit()

if __name__ == "__main__":
    run_bot()
