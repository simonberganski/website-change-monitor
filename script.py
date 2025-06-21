import os
import yagmail
import dns.resolver 
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from selenium.webdriver.chrome.options import Options


# Load environment variables
load_dotenv()
EMAIL = os.getenv('EMAIL')  # Email username
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')  # Email password
LOGIN_USERNAME = os.getenv('LOGIN_USERNAME') 
LOGIN_PASSWORD = os.getenv('LOGIN_PASSWORD') 

# Configuration
WEBSITE_NAME = 'HSBI' # for user email, has no semantic value
LOGIN_URL = 'https://www.hsbi.de/qisserver/rds?state=wlogin&login=in&breadCrumbSource=portal'
XPATH_LOGIN_USERNAME = '//*[@id="asdf"]'
XPATH_LOGIN_PASSWORD = '//*[@id="fdsa"]'
XPATH_LOGIN_BUTTON = '//*[@id="loginForm:login"]'
XPATH_BUTTON_STEP_2 = '//*[@id="wrapper"]/div[5]/div/ul/li[1]/a'
XPATH_BUTTON_STEP_3 = '//*[@id="makronavigation"]/ul/li[2]/a'
XPATH_BUTTON_STEP_4 = '//*[@id="wrapper"]/div[5]/table/tbody/tr/td/div/div[2]/div/form/div/ul/li[3]/a'
XPATH_BUTTON_STEP_5 = '//*[@id="wrapper"]/div[5]/table/tbody/tr/td/div/div[2]/form/ul/li/a[2]'

XPATH_TRACK_AREA = '//*[@id="wrapper"]/div[5]/table/tbody/tr/td/div/div[2]/form/table[2]/tbody'

CONTENT_FILE = 'content_file.txt'
TO_EMAIL = EMAIL

SMTP_PROVIDERS = {
    "gmail.com": {"host": "smtp.gmail.com", "port": 587, "use_ssl": False, "use_tls": True},
    "outlook.com": {"host": "smtp.office365.com", "port": 587, "use_ssl": False, "use_tls": True},
    "hotmail.com": {"host": "smtp.office365.com", "port": 587, "use_ssl": False, "use_tls": True},
    "icloud.com": {"host": "smtp.mail.me.com", "port": 587, "use_ssl": False, "use_tls": True},
    "yahoo.com": {"host": "smtp.mail.yahoo.com", "port": 465, "use_ssl": True, "use_tls": False},
    "aol.com": {"host": "smtp.aol.com", "port": 465, "use_ssl": True, "use_tls": False},
    "zoho.com": {"host": "smtp.zoho.com", "port": 587, "use_ssl": False, "use_tls": True},
    "protonmail.com": {"host": "smtp.protonmail.com", "port": 465, "use_ssl": True, "use_tls": False},
    "hsbi.de": {"host": "smtp.hsbi.de", "port": 587, "use_ssl": False, "use_tls": True},

}


def get_website_content():
    options = Options()
    options.add_argument("--headless")  # Enable headless mode
    options.add_argument("--disable-gpu")  # Disable GPU hardware acceleration (not strictly necessary but can improve performance)
    options.add_argument("--no-sandbox")  # Avoid issues in certain environments (e.g., Docker)

    # Initialize Selenium WebDriver with the specified options
    driver = webdriver.Chrome(options=options)

    try:
        # Step 1: Open the login page
        driver.get(LOGIN_URL)
        time.sleep(1)

        # Step 2: Enter username
        username_field = driver.find_element(By.XPATH, XPATH_LOGIN_USERNAME)
        username_field.send_keys(LOGIN_USERNAME)

        # Step 3: Enter password
        password_field = driver.find_element(By.XPATH, XPATH_LOGIN_PASSWORD)
        password_field.send_keys(LOGIN_PASSWORD)

        # Step 4: Click the login button
        login_button = driver.find_element(By.XPATH, XPATH_LOGIN_BUTTON)
        login_button.click()
        
        button_step_2 = driver.find_element(By.XPATH, XPATH_BUTTON_STEP_2)
        button_step_2.click()

        button_step_3 = driver.find_element(By.XPATH, XPATH_BUTTON_STEP_3)
        button_step_3.click()

        button_step_4 = driver.find_element(By.XPATH, XPATH_BUTTON_STEP_4)
        button_step_4.click()

        button_step_5 = driver.find_element(By.XPATH, XPATH_BUTTON_STEP_5)
        button_step_5.click()

        # Step 5: Wait for the login process to complete
        time.sleep(1)  # Adjust based on website behavior

        common_parent_element = driver.find_element(By.XPATH, XPATH_TRACK_AREA)
        page_content = common_parent_element.get_attribute('outerHTML')  # Gets the HTML of the parent element and its content

        return page_content
    finally:
        # Ensure the driver is closed
        driver.quit()

def load_previous_content():
    """Load the previously stored content from file."""
    if os.path.exists(CONTENT_FILE):
        with open(CONTENT_FILE, 'r') as f:
            return f.read().strip()
    return None

def save_current_content(content):
    """Save the current content to a file."""
    with open(CONTENT_FILE, 'w') as f:
        f.write(content)

def get_smtp_settings(email):
    """Determines the SMTP settings based on email domain."""
    domain = email.split('@')[-1]

    if domain in SMTP_PROVIDERS:
        return SMTP_PROVIDERS[domain]

    # If the domain is unknown, perform an MX record lookup
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        mx_host = str(mx_records[0].exchange).rstrip('.')

        # Basic provider detection using MX host
        if "google" in mx_host:
            return SMTP_PROVIDERS["gmail.com"]
        elif "outlook" in mx_host or "office365" in mx_host:
            return SMTP_PROVIDERS["outlook.com"]
        elif "yahoo" in mx_host:
            return SMTP_PROVIDERS["yahoo.com"]
        elif "icloud" in mx_host:
            return SMTP_PROVIDERS["icloud.com"]

    except Exception as e:
        print(f"MX Lookup Failed: {e}")

    # Default to Gmail if nothing is found
    print("Unknown email provider. Using default Gmail settings.")
    return SMTP_PROVIDERS["gmail.com"]
        

def send_email(subject, body):
    """Send an email notification."""
    smtp_settings = get_smtp_settings(EMAIL)

    yag = yagmail.SMTP(
        user=EMAIL,
        password=EMAIL_PASSWORD,
        host=smtp_settings["host"],
        port=smtp_settings["port"],
        smtp_ssl=smtp_settings["use_ssl"],
        smtp_starttls=smtp_settings["use_tls"]
    )

    yag.send(to=TO_EMAIL, subject=subject, contents=body)


def main():
    
    try:
        # Fetch the website content
        content = get_website_content()

        # Compare with the previous content
        previous_content = load_previous_content()
        if previous_content != content:
            # Content has changed
            send_email("Website Updated", f"The website {WEBSITE_NAME} has been updated.")
            print("Website updated. Email sent.")
        else:
            print("No changes detected.")

        save_current_content(content)

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()

# Use this as ENCRYPTION_KEY
# from cryptography.fernet import Fernet
#
# key = Fernet.generate_key()
# print(key.decode())
