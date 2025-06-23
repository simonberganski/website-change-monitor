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

# Load environment variables
load_dotenv()

def validate_env_vars():
    """Validiert alle erforderlichen Umgebungsvariablen (ohne ENCRYPTION_KEY)"""
    required_vars = ['EMAIL', 'EMAIL_PASSWORD', 'LOGIN_USERNAME', 'LOGIN_PASSWORD']
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

# Umgebungsvariablen validieren
if not validate_env_vars():
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

CONTENT_FILE = 'content_file.txt'  # Ohne Verschlüsselung
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
            with open(CONTENT_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                return parse_table(content)
        except Exception as e:
            print(f"Fehler beim Laden der vorherigen Daten: {e}")
            return []
    return []

def save_current(content):
    try:
        with open(CONTENT_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        print(f"Fehler beim Speichern der Daten: {e}")

def get_smtp_settings(email):
    domain = email.split('@')[-1]
    return SMTP_PROVIDERS.get(domain, SMTP_PROVIDERS["gmail.com"])

def send_email(subject, message_content):
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
        # message_content als String senden, nicht als Liste
        yag.send(to=TO_EMAIL, subject=subject, contents=message_content)
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

def format_email_content(differences):
    """Formatiert die E-Mail mit allen Details der Änderungen"""
    email_content = f"{WEBSITE_NAME} - Neue Noten oder Änderungen erkannt!\n\n"
    email_content += f"Es wurden {len(differences)} Änderung(en) festgestellt:\n\n"
    
    for i, change in enumerate(differences, 1):
        email_content += f"📚 Änderung {i}:\n"
        email_content += f"   Modul: {change['Text']}\n"
        email_content += f"   Prüfungsnummer: {change['PruefNr']}\n"
        email_content += f"   Note: {change['Note']}\n"
        email_content += f"   Semester: {change['Semester']}\n"
        email_content += f"   Status: {change['Status']}\n"
        email_content += f"   Credits: {change['Credits']}\n"
        email_content += f"   Prüfungsdatum: {change['Datum']}\n"
        email_content += f"   Veröffentlichung: {change['Veroeffentlicht']}\n"
        if change['Vermerk']:
            email_content += f"   Vermerk: {change['Vermerk']}\n"
        email_content += "\n" + "-"*50 + "\n\n"
    
    email_content += f"Überprüft am: {time.strftime('%d.%m.%Y um %H:%M:%S')}\n"
    email_content += "Automatische Benachrichtigung vom HSBI Noten-Monitor"
    
    return email_content

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
            
            # Debug: Zeige die erkannten Änderungen in der Konsole
            for change in differences:
                print(f"Neue/Geänderte Note: {change['Text']} - Note: {change['Note']}")
            
            # Formatiere die E-Mail mit allen Details
            email_content = format_email_content(differences)
            
            # Debug: Zeige E-Mail-Inhalt in der Konsole
            print("E-Mail Inhalt:")
            print(email_content)
            
            send_email(f"{WEBSITE_NAME}: {len(differences)} neue Noten erkannt", email_content)
            print("Änderungen erkannt und detaillierte Mail gesendet.")
        else:
            print("Keine Änderungen festgestellt.")

        save_current(html_content)
        print("Überwachung abgeschlossen.")

    except Exception as e:
        print(f"Fehler im Ablauf: {e}")
        # Optional: Fehler-E-Mail senden
        try:
            error_message = f"Fehler beim Überwachen der HSBI-Noten:\n\nFehlermeldung: {str(e)}\n\nZeitpunkt: {time.strftime('%d.%m.%Y um %H:%M:%S')}"
            send_email(f"{WEBSITE_NAME}: Fehler beim Überwachen", error_message)
        except:
            pass

if __name__ == "__main__":
    main()
