# Remember to close the browser
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import gspread

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
from selenium.webdriver.chrome.service import Service
import traceback


def get_credential(credentials_file="cred.json"):
    scopes = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets",
    ]
    credentials = Credentials.from_service_account_file(credentials_file, scopes=scopes)
    return credentials


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


def login(driver):
    # Open smartscout
    driver.get("https://app.smartscout.com/sessions/signin")
    print("login")
    # Login process
    wait = WebDriverWait(driver, 30)
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


def get_relative_products(asin_list):
    # Initialize the Chrome driver with the options
    # driver = webdriver.Chrome(options=chrome_options)
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    login(driver)
    # Iterate over each subset
    for subset in asin_list:
        if "asin" in subset.lower():
            print("Asin name contain 'asin', skip...")
            continue

        asin = subset.strip()
        print("Asin: ", asin)

        wait = WebDriverWait(driver, 30)

        print("searchterm")
        # Navigate to the seller
        try:
            print("scroll")
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="navSearchTerms"]')
                )  # Replace "element_id" with the actual ID of the element
            )
            driver.execute_script("arguments[0].scrollIntoView();", element)
            print("searchtermbutton")
            searchterm_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="navSearchTerms"]'))
            )
            print("searchtermbutton_click")
            searchterm_button.click()
            time.sleep(2)
            print("asininput")
            asin_input = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        '.mat-form-field-infix input[formcontrolname="asin"]',
                    )
                )
            )
            # You can also set the maximum value if needed
            asin_input.clear()
            asin_input.send_keys(asin)
            time.sleep(2)
            print("searchbutton")
            search_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="btnSearchProducts"]'))
            )
            search_button.click()
            time.sleep(5)
            # Find the "Products" element using CSS Selector
            print("relevant_products_button")
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
            time.sleep(20)
            # Wait for the button to be clickable
            wait = WebDriverWait(driver, 10)
            print("excel_button")
            excel_button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//span[text()='Excel']/ancestor::button")
                )
            )
            time.sleep(2)

            # Click the "Excel" button
            excel_button.click()
            print("image")
            image = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'img[mattooltip="Export as CSV"]')
                )
            )

            # Click the image
            image.click()
            time.sleep(5)
            # driver.quit()

            def get_newest_file(directory):
                files = glob.glob(os.path.join(directory, "*"))
                if not files:  # Check if the files list is empty
                    return None
                newest_file = max(files, key=os.path.getmtime)
                return newest_file

            file_path = download_dir

            newest_file_path = get_newest_file(file_path)
            print("newest_file ", newest_file_path)
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
                continue
            print(data.shape)

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
            data.insert(0, "asin", str(asin))

            for col in integer_columns:
                data[format_header(col)] = (
                    data[format_header(col)].astype(float).fillna(0.00)
                )

            if len(data) == 0:
                data = pd.DataFrame(
                    [[asin, "", sys_run_date]],
                    columns=["asin", "asin_relevant", "sys_run_date"],
                )
                print(data)
            try:
                # Convert rows to list of dictionaries and handle NaN values
                rows_list = data.replace({np.nan: None}).to_dict(orient="records")

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
        except Exception as e:
            print(e)
            traceback.print_exc()
            driver.quit()

            # Initialize the Chrome driver with the options
            # driver = webdriver.Chrome(options=chrome_options)
            driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
            login(driver)
            continue


def get_relevant_asin_data(sys_run_date, relevancy_score):
    # Create a cursor
    cursor = conn.cursor()

    # Execute the SQL query to retrieve distinct seller_id from the "best_seller_keepa" table
    query = f"""
    SELECT * 
    FROM products_relevant_smartscounts
    where sys_run_date = '{sys_run_date}'
        and relevancy_score >= {relevancy_score}
    """

    cursor.execute(query)

    # Fetch all the rows as a list
    data_list = cursor.fetchall()
    data = pd.DataFrame(
        data_list,
        columns=[
            "amazon_image",
            "asin",
            "asin_relevant",
            "title",
            "brand",
            "common_search_terms",
            "relevancy_score",
            "sys_run_date",
        ],
        dtype=str,
    )
    return data


def get_new_asin_list(asin_list, sys_run_date):
    asin_list = [item[0] for item in asin_list if "asin" not in item[0].lower()]

    cursor = conn.cursor()

    # Execute the SQL query to retrieve distinct seller_id from the "best_seller_keepa" table
    query = f"""
    SELECT distinct asin 
    FROM products_relevant_smartscounts
    where sys_run_date = '{sys_run_date}'
    """

    cursor.execute(query)

    # Fetch all the rows as a list
    data_list = cursor.fetchall()
    old_asin_list = [item[0] for item in data_list]
    new_asin_list = [asin for asin in asin_list if asin not in old_asin_list]
    return new_asin_list


def load_relative_products_to_gg_sheet(spreadsheet_name, sys_run_date):
    #     asin_list = [item[0] for item in asin_list]
    print("spreadsheet_name :", spreadsheet_name)
    spreadsheet = gg_sheet_client.open(
        spreadsheet_name, folder_id="1SEIJ9XVaBNc2Ovah56fUR4j5Fmgx3Uaq"
    )

    try:
        worksheet = spreadsheet.add_worksheet(
            title=sys_run_date, rows=100, cols=20, index=0
        )
    except Exception:
        # Delete existing sheet
        worksheet = spreadsheet.worksheet(sys_run_date)

        old_df = pd.DataFrame(worksheet.get_all_records(), dtype=str)
        print("Old relative data shape: ", old_df.shape)
        # print(old_df.dtypes)

    data = get_relevant_asin_data(sys_run_date, 9)
    print("Full relative data shape: ", data.shape)
    # print(data)
    # print(data.dtypes)

    data = pd.concat([old_df, data]).drop_duplicates()
    # print(data)
    print("Final relative data shape: ", data.shape)

    worksheet.update([data.columns.values.tolist()] + data.astype(str).values.tolist())
    current_time = datetime.now(timezone(timedelta(hours=7)))

    # Open the spreadsheet by its title
    spreadsheet = gg_sheet_client.open("Asin")
    input_worksheet = spreadsheet.worksheet("asin_input_list")
    input_worksheet.update_cell(
        1, 2, f"Relative Product sheet is updated at {current_time}"
    )


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

chromedriver_autoinstaller.install()  # Check if the current version of chromedriver exists

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
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--window-size=1920,1080",
    ]
    chrome_options.add_experimental_option("prefs", prefs)
    # chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    # chrome_service = Service(os.environ.get("CHROMEDRIVER_PATH"))
    chrome_service = Service()
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
# cursor = conn.cursor()

# Execute the SQL query to retrieve distinct seller_id from the "best_seller_keepa" table
# query = """
# SELECT distinct a.sys_run_date,a.asin
#     FROM products_smartscount a left join
#     (select distinct sys_run_date,asin from products_relevant_smartscounts) b on a.asin=b.asin and a.sys_run_date=b.sys_run_date
#     where a.sys_run_date=(select max(sys_run_date) from products_smartscount)
#     and b.asin is null
# """

# cursor.execute(query)


# Fetch all the rows as a list
# brand_product_list = cursor.fetchall()

# Define the scope
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# Path to your credentials JSON file
credentials = get_credential()

# Authorize the client using the credentials
gg_sheet_client = gspread.authorize(credentials)

# Open the spreadsheet by its title
spreadsheet = gg_sheet_client.open("Asin")


# # Select the worksheet by its title
input_worksheet = spreadsheet.worksheet("asin_input_list")

# Get all values from the worksheet
asin_list_raw = input_worksheet.get_all_values()

sys_run_date = (datetime.now(timezone.utc) + timedelta(hours=7)).strftime("%Y-%m-%d")
print("today: ", sys_run_date)


def main():
    print("Filter asin.................")
    print("Asin list raw len: ", len(asin_list_raw))
    new_asin_list = get_new_asin_list(asin_list_raw, sys_run_date)
    print("new_asin_list len: ", len(new_asin_list))

    if len(new_asin_list) == 0:
        print("There is no new asin. Returning..............................")
        return

    print("Get relative products.........................")
    get_relative_products(new_asin_list)

    print("load to gg sheet.................................")
    load_relative_products_to_gg_sheet("Relative Products", sys_run_date)


if __name__ == "__main__":
    main()
