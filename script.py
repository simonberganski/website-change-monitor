import os
import yagmail
import dns.resolver
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
import time
import html
from cryptography.fernet import Fernet

# Load environment variables
load_dotenv()

def validate_env_vars():
    """Validiert alle erforderlichen Umgebungsvariablen"""
    required_vars = ['EMAIL', 'EMAIL_PASSWORD', 'LOGIN_USERNAME', 'LOGIN_PASSWORD', 'ENCRYPTION_KEY']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"Fehler: Folgende Umgebungsvariablen fehlen: {', '.join(missing_vars)}")
        print("Bitte überprüfen Sie Ihre .env-Datei.")
        return False
    
    return True

def setup_encryption():
    """Richtet die Verschlüsselung ein und generiert bei Bedarf einen neuen Key"""
    encryption_key = os.getenv('ENCRYPTION_KEY')
    
    if not encryption_key:
        print("ENCRYPTION_KEY nicht gefunden. Generiere neuen Key...")
        new_key = Fernet.generate_key()
        print(f"Neuer Encryption Key generiert: {new_key.decode()}")
        print("Bitte fügen Sie diesen Key zu Ihrer .env-Datei hinzu:")
        print(f"ENCRYPTION_KEY={new_key.decode()}")
        return None
    
    try:
        return Fernet(encryption_key.encode())
    except Exception as e:
        print(f"Fehler beim Initialisieren der Verschlüsselung: {e}")
        print("Möglicherweise ist der ENCRYPTION_KEY ungültig.")
        return None

# Umgebungsvariablen validieren
if not validate_env_vars():
    exit(1)

# Verschlüsselung einrichten
fernet = setup_encryption()
if not fernet:
    exit(1)

# Umgebungsvariablen laden
EMAIL = os.getenv('EMAIL')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
LOGIN_USERNAME = os.getenv('LOGIN_USERNAME')
LOGIN_PASSWORD = os.getenv('LOGIN_PASSWORD')

# Configuration
WEBSITE_NAME = 'HSBI'
LOGIN_URL = 'https://www.hsbi.de/qisserver/rds?state=wlogin&login=in&breadCrumbSource=portal'
XPATH_LOGIN_USERNAME = '//*[@id="asdf"]'
XPATH_LOGIN_PASSWORD = '//*[@id="fdsa"]'
XPATH_LOGIN_BUTTON = '//*[@id="loginForm:login"]'
XPATH_BUTTON_STEP_2 = '//*[@id="wrapper"]/div[5]/div/ul/li[1]/a'
XPATH_BUTTON_STEP_3 = '//*[@id="makronavigation"]/ul/li[2]/a'
XPATH_BUTTON_STEP_4 = '//*[@id="wrapper"]/div[5]/table/tbody/tr/td/div/div[2]/div/form/div/ul/li[3]/a'
XPATH_BUTTON_STEP_5 = '//*[@id="wrapper"]/div[5]/table/tbody/tr/td/div/div[2]/form/ul/li/a[2]'
XPATH_TRACK_AREA = '//*[@id="wrapper"]/div[5]/table/tbody/tr/td/div/div[2]/form/table[2]/tbody'

CONTENT_FILE = 'content_file.txt.encrypted'
TO_EMAIL = EMAIL

SMTP_PROVIDERS = {
    "gmail.com": {"host": "smtp.gmail.com", "port": 587, "use_ssl": False, "use_tls": True},
    "outlook.com": {"host": "smtp.office365.com", "port": 587, "use_ssl": False, "use_tls": True},
    "hsbi.de": {"host": "smtp.hsbi.de", "port": 587, "use_ssl": False, "use_tls": True},
}

def get_website_content():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")  # Für CI/CD Umgebungen

    driver = webdriver.Chrome(options=options)

    try:
        print("Lade Website...")
        driver.get(LOGIN_URL)
        time.sleep(2)

        print("Führe Login durch...")
        driver.find_element(By.XPATH, XPATH_LOGIN_USERNAME).send_keys(LOGIN_USERNAME)
        driver.find_element(By.XPATH, XPATH_LOGIN_PASSWORD).send_keys(LOGIN_PASSWORD)
        driver.find_element(By.XPATH, XPATH_LOGIN_BUTTON).click()
        time.sleep(2)

        print("Navigiere durch die Seiten...")
        driver.find_element(By.XPATH, XPATH_BUTTON_STEP_2).click()
        time.sleep(1)
        driver.find_element(By.XPATH, XPATH_BUTTON_STEP_3).click()
        time.sleep(1)
        driver.find_element(By.XPATH, XPATH_BUTTON_STEP_4).click()
        time.sleep(1)
        driver.find_element(By.XPATH, XPATH_BUTTON_STEP_5).click()
        time.sleep(2)

        print("Extrahiere Inhalte...")
        element = driver.find_element(By.XPATH, XPATH_TRACK_AREA)
        html_content = element.get_attribute('outerHTML')
        return html_content
    
    except Exception as e:
        print(f"Fehler beim Abrufen der Website-Inhalte: {e}")
        raise
    finally:
        driver.quit()

def parse_table(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    rows = soup.find_all('tr')
    data = []
    for row in rows:
        cols = [col.get_text(strip=True) for col in row.find_all(['td', 'th'])]
        if len(cols) >= 9 and cols[0].isdigit():
            data.append({
                'PruefNr': cols[0],
                'Text': cols[1],
                'Semester': cols[2],
                'Note': cols[3],
                'Status': cols[4],
                'Credits': cols[5],
                'Vermerk': cols[6],
                'Versuch': cols[7],
                'Datum': cols[8],
                'Veroeffentlicht': cols[9] if len(cols) > 9 else ''
            })
    return data

def load_previous():
    if os.path.exists(CONTENT_FILE):
        try:
            with open(CONTENT_FILE, 'rb') as f:
                encrypted = f.read()
                decrypted = fernet.decrypt(encrypted)
                return parse_table(decrypted.decode())
        except Exception as e:
            print(f"Fehler beim Laden der vorherigen Daten: {e}")
            return []
    return []

def save_current(content):
    try:
        encrypted = fernet.encrypt(content.encode())
        with open(CONTENT_FILE, 'wb') as f:
            f.write(encrypted)
    except Exception as e:
        print(f"Fehler beim Speichern der Daten: {e}")

def get_smtp_settings(email):
    domain = email.split('@')[-1]
    return SMTP_PROVIDERS.get(domain, SMTP_PROVIDERS["gmail.com"])

def send_email(subject, lines):
    try:
        smtp = get_smtp_settings(EMAIL)
        yag = yagmail.SMTP(
            user=EMAIL,
            password=EMAIL_PASSWORD,
            host=smtp["host"],
            port=smtp["port"],
            smtp_ssl=smtp["use_ssl"],
            smtp_starttls=smtp["use_tls"]
        )
        yag.send(to=TO_EMAIL, subject=subject, contents=lines)
        print("E-Mail erfolgreich gesendet.")
    except Exception as e:
        print(f"Fehler beim Senden der E-Mail: {e}")

def diff_entries(old, new):
    changes = []
    old_map = {row['PruefNr']: row for row in old}
    for row in new:
        prev = old_map.get(row['PruefNr'])
        if not prev or row['Note'] != prev['Note'] or row['Veroeffentlicht'] != prev['Veroeffentlicht']:
            changes.append(row)
    return changes

def main():
    try:
        print("Starte Überwachung...")
        html_content = get_website_content()
        current = parse_table(html_content)
        previous = load_previous()

        print(f"Aktuelle Einträge: {len(current)}")
        print(f"Vorherige Einträge: {len(previous)}")

        differences = diff_entries(previous, current)

        if differences:
            print(f"Änderungen erkannt: {len(differences)}")
            lines = [
                f"{WEBSITE_NAME} - Es wurden neue Noten oder Änderungen erkannt:\n"
            ]
            for d in differences:
                lines.append(
                    f"- {d['Text']} | Note: {d['Note']} | Veröffentlichungsdatum: {d['Veroeffentlicht']}"
                )
            send_email(f"{WEBSITE_NAME}: Neue Noten erkannt", lines)
            print("Änderungen erkannt und Mail gesendet.")
        else:
            print("Keine Änderungen festgestellt.")

        save_current(html_content)
        print("Überwachung abgeschlossen.")

    except Exception as e:
        print(f"Fehler im Ablauf: {e}")
        # Optional: Fehler-E-Mail senden
        try:
            send_email(f"{WEBSITE_NAME}: Fehler beim Überwachen", [f"Fehler aufgetreten: {str(e)}"])
        except:
            pass

if __name__ == "__main__":
    main()
