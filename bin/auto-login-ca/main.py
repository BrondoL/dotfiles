#!/usr/bin/env python3
# ca_login.py - login CyberArk + ambil cookie

import os
import sys
import time
import json
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# -----------------------
# File untuk simpan cookies
# -----------------------
COOKIE_FILE = "/tmp/ca-cookies.json"
AAV_COOKIE_FILE = "/home/brondol/.config/bin/auto-login-ca/aav-cookies.json"
AAV_URL = "https://aav4534.id.cyberark.cloud"


# -----------------------
# Helper notif: kirim ke notify-send (Hyprland/mako). Aman walau notify-send
# tidak ada (mis. dijalankan di luar sesi grafis).
# -----------------------
def notify(title, message, urgency="normal"):
    try:
        subprocess.run(["notify-send", "-u", urgency, title, message], check=False)
    except FileNotFoundError:
        pass


# -----------------------
# Helper debug: dump semua button & input yang ada di halaman saat itu
# -----------------------
def dump_page_elements(label):
    print(f"\n========== DEBUG: {label} ==========")
    print(f"URL saat ini : {driver.current_url}")
    print(f"Judul halaman: {driver.title}")

    buttons = driver.find_elements(By.TAG_NAME, "button")
    print(f"\n[BUTTON] ditemukan {len(buttons)} buah:")
    for i, b in enumerate(buttons):
        print(
            f"  #{i} id={b.get_attribute('id')!r} "
            f"name={b.get_attribute('name')!r} "
            f"type={b.get_attribute('type')!r} "
            f"text={b.text!r} "
            f"displayed={b.is_displayed()} enabled={b.is_enabled()}"
        )

    inputs = driver.find_elements(By.TAG_NAME, "input")
    print(f"\n[INPUT] ditemukan {len(inputs)} buah:")
    for i, inp in enumerate(inputs):
        print(
            f"  #{i} id={inp.get_attribute('id')!r} "
            f"name={inp.get_attribute('name')!r} "
            f"type={inp.get_attribute('type')!r} "
            f"placeholder={inp.get_attribute('placeholder')!r} "
            f"displayed={inp.is_displayed()} enabled={inp.is_enabled()}"
        )
    print(f"========== END DEBUG: {label} ==========\n")


# -----------------------
# Setup Chrome options
# -----------------------
chrome_options = Options()
chrome_options.add_argument("--ignore-certificate-errors")
# chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(
    service=Service("/usr/bin/chromedriver"), options=chrome_options
)

# Status login; menentukan exit code di akhir.
login_ok = False

try:
    # -----------------------
    # Load cookies aav4534 (jika ada). Harus buka domain-nya dulu supaya
    # add_cookie boleh dipanggil untuk domain itu.
    # -----------------------
    aav_cookies_valid = False
    if os.path.exists(AAV_COOKIE_FILE):
        try:
            # Buka /applogin dulu supaya tidak ke-redirect ke domain lain;
            # add_cookie hanya boleh dipanggil saat sudah di domain aav4534.
            driver.get(f"{AAV_URL}/applogin")
            time.sleep(2)
            with open(AAV_COOKIE_FILE, "r") as f:
                aav_cookies = json.load(f)

            now = time.time()
            loaded = 0
            skipped_expired = 0
            for c in aav_cookies:
                if c.get("expiry") and c["expiry"] < now:
                    skipped_expired += 1
                    continue
                cookie = {
                    k: v
                    for k, v in c.items()
                    if k
                    in (
                        "name",
                        "value",
                        "domain",
                        "path",
                        "expiry",
                        "secure",
                        "httpOnly",
                    )
                }
                try:
                    driver.add_cookie(cookie)
                    loaded += 1
                except Exception as ce:
                    print(f"  skip cookie {c.get('name')}: {type(ce).__name__}: {ce}")
            print(
                f"Cookies aav4534 di-load: {loaded}/{len(aav_cookies)} "
                f"(skip expired: {skipped_expired}) dari {AAV_COOKIE_FILE}"
            )

            # Verifikasi: buka bare domain (tanpa path). /applogin tidak
            # pernah redirect jadi tidak bisa dipakai untuk tes. Kalau
            # cookies valid -> redirect ke pt-brondol.cyberark.cloud. Kalau
            # tidak valid -> stuck di aav4534 (mis. /my?customerId=AAV4534).
            if loaded > 0:
                driver.get(AAV_URL)
                time.sleep(3)
                current_url = driver.current_url
                if "pt-brondol.cyberark.cloud" in current_url.lower():
                    aav_cookies_valid = True
                    print(f"Cookies aav4534 VALID (redirect ke: {current_url})")
                else:
                    print(f"Cookies aav4534 sudah TIDAK valid (URL: {current_url})")
        except Exception as e:
            print(f"Gagal load cookies aav4534: {type(e).__name__}: {e}")
    else:
        print(f"File cookies aav4534 belum ada ({AAV_COOKIE_FILE}), skip load.")

    # -----------------------
    # Buka CyberArk
    # -----------------------
    driver.get("https://cyberark.local.brondol.id/PasswordVault")

    # -----------------------
    # Klik tombol Continue (selalu dijalankan; ini yang men-trigger
    # redirect ke flow login berikutnya).
    # -----------------------
    try:
        continue_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "continue-button"))
        )
        continue_button.click()
        print("Tombol Continue berhasil diklik!")
    except Exception as e:
        print(
            f"Tombol Continue tidak ditemukan/tidak bisa diklik: {type(e).__name__}: {e}"
        )

    # -----------------------
    # Klik tombol IDAFTIVE MFA (selalu dijalankan). Setelah ini, kalau
    # cookies aav4534 valid akan langsung redirect ke /Accounts (SSO),
    # kalau tidak valid akan redirect ke halaman login aav4534.
    # -----------------------
    try:
        mfa_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@id="Idaftive MFA"]'))
        )
        time.sleep(1)
        mfa_button.click()
        print("Tombol IDAFTIVE MFA berhasil diklik!")
    except Exception as e:
        print(
            f"Tombol IDAFTIVE MFA tidak ditemukan/tidak bisa diklik: {type(e).__name__}: {e}"
        )

    # -----------------------
    # SSO probe: kalau cookies aav4534 valid, setelah klik Idaftive MFA
    # halaman akan langsung redirect ke /Accounts tanpa perlu username/
    # password/push. Probe ~15 detik.
    # -----------------------
    sso_ok = False
    if aav_cookies_valid:
        try:
            WebDriverWait(driver, 15).until(
                EC.url_contains("/PasswordVault/v10/Accounts")
            )
            print("SSO sukses lewat cookies aav4534, skip flow username/password/push.")
            sso_ok = True
        except Exception:
            print(
                "SSO tidak auto-login dalam 15 detik, fallback ke flow username/password/push."
            )

    if not sso_ok:
        # -----------------------
        # Isi field username
        # -----------------------
        try:
            username_field = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            username_field.clear()
            username_field.send_keys("aulianabil@brondol.id")
            print("Username berhasil diisi!")
        except Exception as e:
            print(f"Field username tidak ditemukan: {type(e).__name__}: {e}")

        # -----------------------
        # Klik tombol Next setelah username
        # -----------------------
        try:
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="usernameForm"]/div[2]/button')
                )
            )
            next_button.click()
            print("Tombol Next berhasil diklik!")
        except Exception as e:
            print(
                f"Tombol Next tidak ditemukan/tidak bisa diklik: {type(e).__name__}: {e}"
            )

        # -----------------------
        # Isi password
        # -----------------------
        # Debug: lihat komponen apa saja yang ada SEBELUM mencoba isi password
        # dump_page_elements("Sebelum isi password")

        try:
            password_field = WebDriverWait(driver, 20).until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//input[@name='answer' and @placeholder='Password']")
                )
            )
            password_field.clear()
            password_field.send_keys("brondol")
            print("Password berhasil diisi!")
        except Exception as e:
            print(
                f"Field password tidak ditemukan. Error asli: {type(e).__name__}: {e}"
            )
            # Simpan screenshot juga untuk membandingkan headless vs non-headless
            driver.save_screenshot("/tmp/ca-password-fail.png")
            print("Screenshot disimpan di /tmp/ca-password-fail.png")

        # -----------------------
        # Check "Keep me signed in"
        # -----------------------
        try:
            checkboxes = WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.NAME, "rememberMe"))
            )
            if len(checkboxes) >= 2:
                remember_me_checkbox = checkboxes[1]  # ambil yang kedua
                if not remember_me_checkbox.is_selected():
                    remember_me_checkbox.click()
                print("Checkbox 'Keep me signed in' kedua dicentang!")
            else:
                print("Checkbox 'Keep me signed in' kedua tidak ditemukan")
        except Exception as e:
            print(
                f"Checkbox 'Keep me signed in' tidak ditemukan: {type(e).__name__}: {e}"
            )

        # -----------------------
        # Klik tombol "Send me a push"
        # -----------------------
        try:
            send_push_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[text()='Send me a push']")
                )
            )
            send_push_button.click()
            print("Tombol 'Send me a push' diklik!")
            notify("CyberArk", "Cek HP, approve push CyberArk 📲")
        except Exception as e:
            print(
                f"Tombol 'Send me a push' tidak ditemukan/tidak bisa diklik: {type(e).__name__}: {e}"
            )

    # -----------------------
    # Tunggu sampai halaman /Accounts muncul (MFA diterima)
    # Timeout 60 detik supaya cukup waktu approve push di HP.
    # -----------------------
    try:
        WebDriverWait(driver, 60).until(EC.url_contains("/PasswordVault/v10/Accounts"))
        print("Halaman /Accounts sudah terbuka, mengambil cookies...")

        cookies = driver.get_cookies()
        with open(COOKIE_FILE, "w") as f:
            json.dump(cookies, f)
        print(f"Cookies berhasil disimpan di {COOKIE_FILE}")

        # Buat string cookies untuk curl
        cookie_string = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        print("\nString cookies untuk curl:")
        print(cookie_string)

        login_ok = True

        # -----------------------
        # Buka domain aav4534 untuk ambil cookies-nya, lalu simpan.
        # Pakai /applogin supaya tetap di domain aav4534 (bare domain
        # akan redirect ke pt-brondol kalau sudah ter-authenticate).
        # -----------------------
        try:
            driver.get(f"{AAV_URL}/applogin")
            time.sleep(3)
            aav_cookies = driver.get_cookies()
            with open(AAV_COOKIE_FILE, "w") as f:
                json.dump(aav_cookies, f)
            print(
                f"Cookies aav4534 ({len(aav_cookies)} buah) disimpan di {AAV_COOKIE_FILE}"
            )
        except Exception as e:
            print(f"Gagal simpan cookies aav4534: {type(e).__name__}: {e}")

    except Exception as e:
        print(
            f"Timeout: Halaman /Accounts tidak terbuka dalam 60 detik. "
            f"Tidak ada cookie yang diambil. ({type(e).__name__})"
        )

finally:
    driver.quit()

# Exit code: 0 = sukses (cookie tersimpan), 1 = gagal. Dipakai connect-ca
# untuk tahu apakah login berhasil.
sys.exit(0 if login_ok else 1)
