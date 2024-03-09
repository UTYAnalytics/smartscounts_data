# Remember to close the browser
import tempfile
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import hashlib
import os
import time
import pandas as pd
import psycopg2
import glob
from supabase import create_client, Client
from datetime import date
import re
import unicodedata
from selenium.common.exceptions import TimeoutException
import imaplib
import email
import re
import chromedriver_autoinstaller
from selenium.common.exceptions import NoSuchElementException
from datetime import datetime, timezone, timedelta
import numpy as np
from pyvirtualdisplay import Display
from selenium.webdriver.support.ui import Select
from urllib.parse import urlparse


SUPABASE_URL = "https://sxoqzllwkjfluhskqlfl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN4b3F6bGx3a2pmbHVoc2txbGZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MDIyODE1MTcsImV4cCI6MjAxNzg1NzUxN30.FInynnvuqN8JeonrHa9pTXuQXMp9tE4LO0g5gj0adYE"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Replace these with your Keepa username and password
username = "nguyen.quang.tung85@gmail.com"
password = "D8RLPA7$kxG!9zh"

# Gmail App Password
server = "imap.gmail.com"
email_address = "uty.tra@thebargainvillage.com"
email_password = "kwuh xdki tstu vyct"
subject_filter = "Keepa.com Account Security Alert and One-Time Login Code"

# display = Display(visible=0, size=(800, 800))
# display.start()

# chromedriver_autoinstaller.install()  # Check if the current version of chromedriver exists

# Create a temporary directory for downloads
with tempfile.TemporaryDirectory() as download_dir:
    # and if it doesn't exist, download it automatically,
    # then add chromedriver to path
    chrome_options = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    options = [
        # Define window size here
        "--ignore-certificate-errors",
        # "--headless",
        "--disable-gpu",
        "--disable-extensions",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--remote-debugging-port=9222",
    ]
    chrome_options.add_experimental_option("prefs", prefs)
    for option in options:
        chrome_options.add_argument(option)


# Your connection string
connection_string = "postgres://postgres.sxoqzllwkjfluhskqlfl:5giE*5Y5Uexi3P2@aws-0-us-west-1.pooler.supabase.com:6543/postgres"

# Parse the connection string
result = urlparse(connection_string)
user = result.username
passdata = result.password
database = result.path[1:]  # remove the leading '/'
hostname = result.hostname
port = result.port

conn = psycopg2.connect(
    dbname=database, user=user, password=passdata, host=hostname, port=port
)
# Create a cursor
cursor = conn.cursor()

# Execute the SQL query to retrieve distinct seller_id from the "best_seller_keepa" table
query = """
SELECT distinct a.sys_run_date,a.asin
    FROM products_smartscount a left join 
    (select distinct sys_run_date,asin from products_relevant_smartscounts) b on a.asin=b.asin and a.sys_run_date=b.sys_run_date
    where a.sys_run_date=(select max(sys_run_date) from products_smartscount)
"""

cursor.execute(query)


# Fetch all the rows as a list
brand_product_list = cursor.fetchall()


def get_otp_from_email(server, email_address, email_password, subject_filter):
    mail = imaplib.IMAP4_SSL(server)
    mail.login(email_address, email_password)
    mail.select("inbox")

    status, data = mail.search(None, '(SUBJECT "{}")'.format(subject_filter))
    mail_ids = data[0].split()

    latest_email_id = mail_ids[-1]
    status, data = mail.fetch(latest_email_id, "(RFC822)")

    raw_email = data[0][1].decode("utf-8")
    email_message = email.message_from_bytes(data[0][1])

    otp_pattern = re.compile(r"\b\d{6}\b")

    if email_message.is_multipart():
        for part in email_message.walk():
            content_type = part.get_content_type()
            if "text/plain" in content_type or "text/html" in content_type:
                email_content = part.get_payload(decode=True).decode()
                match = otp_pattern.search(email_content)
                if match:
                    return match.group(0)
    else:
        email_content = email_message.get_payload(decode=True).decode()
        match = otp_pattern.search(email_content)
        if match:
            return match.group(0)
    return None


def get_estimated_sales(asin):
    # Specify the path to your webdriver executable (e.g., chromedriver.exe)
    chrome_options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=chrome_options)
    try:
        # Navigate to the ProfitGuru website
        driver.get("https://www.profitguru.com/calculator/sales")
        # Input ASIN value
        asin_input = driver.find_element(By.ID, "calc_asin_input")
        asin_input.send_keys(asin)
        asin_input.send_keys(Keys.ENTER)
        time.sleep(8)
        # Get text from the element
        wait = WebDriverWait(driver, 10)
        estimated_sales_element = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "tr:nth-of-type(6) .pr-2 div")
            )
        )
        estimated_sales_text = estimated_sales_element.text.strip()
        # Check if the text is a number
        try:
            estimated_sales = float(estimated_sales_text.replace(",", ""))
        except ValueError:
            estimated_sales = 0
        return estimated_sales

    finally:
        # Close the browser window
        driver.quit()


# Iterate over each subset
for subset in brand_product_list:
    (
        sys_run_date,
        asin,
    ) = subset
    # Initialize the Chrome driver with the options
    driver = webdriver.Chrome(options=chrome_options)

    # Open Keepa
    driver.get("https://app.smartscout.com/sessions/signin")

    wait = WebDriverWait(driver, 2000000)

    # Login process
    try:
        username_field = wait.until(
            EC.visibility_of_element_located((By.ID, "username"))
        )
        username_field.send_keys(username)

        password_field = driver.find_element(By.ID, "password")
        password_field.send_keys(password)
        password_field.send_keys(Keys.RETURN)
        time.sleep(2)
    except Exception as e:
        # raise Exception
        print("Error during login:", e)

    # Navigate to the seller
    try:
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.ID, "navSearchTerms")
            )  # Replace "element_id" with the actual ID of the element
        )
        driver.execute_script("arguments[0].scrollIntoView();", element)
        searchterm_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="navSearchTerms"]'))
        )
        searchterm_button.click()
        time.sleep(2)

        asin_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, '.mat-form-field-infix input[formcontrolname="asin"]')
            )
        )
        # You can also set the maximum value if needed
        asin_input.clear()
        asin_input.send_keys(asin)
        time.sleep(2)
        search_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="btnSearchProducts"]'))
        )
        search_button.click()
        time.sleep(5)
        # Find the "Products" element using CSS Selector
        relevant_products_button = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    "//div[contains(@class, 'fixed-tab') and contains(text(), 'Relevant Products')]",
                )
            )
        )
        # Click on the "Products" element
        relevant_products_button.click()
        time.sleep(5)
        # Wait for the button to be clickable
        wait = WebDriverWait(driver, 10)
        excel_button = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//span[text()='Excel']/ancestor::button")
            )
        )

        # Click the "Excel" button
        excel_button.click()

        image = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'img[mattooltip="Export as CSV"]')
            )
        )

        # Click the image
        image.click()
        time.sleep(10)
        driver.quit()

        def get_newest_file(directory):
            files = glob.glob(os.path.join(directory, "*"))
            if not files:  # Check if the files list is empty
                return None
            newest_file = max(files, key=os.path.getmtime)
            return newest_file

        file_path = download_dir

        newest_file_path = get_newest_file(file_path)
        # Get the current UTC time
        current_utc_time = datetime.utcnow()

        # Calculate the time difference for GMT+7
        gmt7_offset = timedelta(hours=7)

        # Get the current date and time in GMT+7
        current_time_gmt7 = current_utc_time + gmt7_offset
        if newest_file_path:
            data = pd.read_csv(newest_file_path)
            # data["sys_run_date"] = current_time_gmt7.strftime("%Y-%m-%d %H:%M:%S")
            data["sys_run_date"] = sys_run_date
            # Proceed with the database insertion
        else:
            print("No files found in the specified directory.")

        def format_header(header):
            # Convert to lowercase
            header = header.lower()
            # Replace spaces with underscores
            header = header.replace(" ", "_")
            # Remove Vietnamese characters by decomposing and keeping only ASCII
            header = (
                unicodedata.normalize("NFKD", header)
                .encode("ASCII", "ignore")
                .decode("ASCII")
            )
            return header

        # Extract the header row
        headers = [
            "amazon_image",
            "asin_relevant",
            "title",
            "brand",
            "common_search_terms",
            "relevancy_score",
            "sys_run_date",
        ]

        integer_columns = [
            "relevancy_score",
        ]
        data = data.drop(data.columns[0], axis=1)
        # Concatenate the URL with the data in the second column
        data.rename(columns={data.columns[0]: "amazon_image"}, inplace=True)
        data[data.columns[0]] = (
            "https://images-na.ssl-images-amazon.com/images/I/"
            + data[data.columns[0]].astype(str)
        )
        data.columns = headers
        data.insert(0, "asin", "")
        for col in integer_columns:
            data[format_header(col)] = (
                data[format_header(col)].astype(float).fillna(0.00)
            )
        try:
            # Convert rows to list of dictionaries and handle NaN values
            rows_list = data.replace({np.nan: None}).to_dict(orient="records")

            # Generate MD5 hash as the primary key for each row
            for row_dict in rows_list:
                row_dict["asin"] = str(asin)

            # Insert the rows into the database using executemany
            response = (
                supabase.table("products_relevant_smartscounts")
                .upsert(rows_list)
                .execute()
            )

            if hasattr(response, "error") and response.error is not None:
                raise Exception(f"Error inserting rows: {response.error}")

            print(f"Rows inserted successfully")

        except Exception as e:
            print(f"Error with rows: {e}")
            # Optionally, break or continue based on your preference
        cursor.execute(query)
        # Fetch all the rows as a list
        brand_product_list = cursor.fetchall()
    except Exception as e:
        print(e)
        driver.quit()
        continue
