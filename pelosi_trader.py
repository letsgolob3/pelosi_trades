import logging
import os
import smtplib
import time
import uuid
from datetime import datetime
from typing import List, Union

import pandas as pd
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# Load environment variables from .env file
load_dotenv()

# Configure logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Function to scrape the website and return data as a pandas DataFrame
def scrape_website(github_action: bool) -> pd.DataFrame:
    """
    Scrapes the stock trade table from the specified website and returns it as a pandas DataFrame.
    
    Returns:
        pd.DataFrame: DataFrame containing the scraped table data.
    """

    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


    if  github_action:

        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")  # Helps in some environments
    
    try:
        url = 'https://valueinvesting.io/nancy-pelosi-stock-trades-tracker'
        driver.get(url)
        time.sleep(5)  # Wait for the table to load
        
        table = driver.find_element(By.XPATH, '//table')
        headers = [header.text for header in table.find_elements(By.XPATH, './/th')]
        
        rows = []
        for row in table.find_elements(By.XPATH, './/tr')[1:]:  # Skip the header row
            cols = row.find_elements(By.XPATH, './/td')
            cols_data = [col.text for col in cols]
            rows.append(cols_data)
        
        df = pd.DataFrame(rows, columns=headers)
        return df
    finally:
        driver.quit()  # Ensure the driver is closed after scraping


def check_for_updates(csv_filename: str,github_action) -> None:
    """
    Checks for new stock trade records and updates the CSV file if changes are detected.
    
    Args:
        csv_filename (str): Path to the CSV file storing previous trade data.
    """
    new_data = scrape_website(github_action)
    new_data['Transaction Date']= pd.to_datetime(new_data['Transaction Date'])

    latest_date_from_new = max(new_data['Transaction Date'])

    logging.info(f"length of new data is {len(new_data)}")
    logging.info(f"{latest_date_from_new}")
    

    if not os.path.exists(csv_filename):
        new_data.to_csv(csv_filename, index=False)
        logger.info('Initial data saved')
    
    old_data = pd.read_csv(csv_filename)

    old_data['Transaction Date']= pd.to_datetime(old_data['Transaction Date'])
    latest_date_from_old = max(old_data['Transaction Date'])

    # new_data.to_csv('new_data.csv',index=False)

    logging.info(f"length of old data is {len(old_data)}")
    logging.info(f"{latest_date_from_old}")
    
    if latest_date_from_new > latest_date_from_old:  # Check if new trades have been added
        # Get all of the new data
        only_new_trades = new_data.loc[new_data['Transaction Date']>latest_date_from_old]

        # only_new_trades.to_csv('latest_trades.csv', index=False)

        new_data.to_csv('trades.csv', index=False)

        logger.info('New data added to trades.csv and new trades saved to latest_trades.csv')

        only_new_trades ['Update Date'] = datetime.now().date().isoformat()

        # Usage example
        recipient_email = ["mark.golob275@gmail.com","tristanpeters303@gmail.com","thatnelson@gmail.com"]
        subject = "Pelosi Trades Update"
        #body = "Attached is the latest updated stock trade data."

        send_email(recipient_email, subject,only_new_trades)


    else:
        logger.info('No new trades found')

def send_email(recipient_email: Union[str, List[str]], 
               subject: str, 
               df: pd.DataFrame,
               body: str="") -> None:
    """
    Send an email with the latest trades from Pelosi's account.

    This function creates and sends an HTML email containing a DataFrame of trade information
    and a link to the Nancy Pelosi Stock Trades Tracker.

    Args:
        recipient_email (Union[str, List[str]]): Email address(es) of the recipient(s).
        subject (str): Subject line of the email.
        body (str): Plain text body of the email.
        df (pd.DataFrame): DataFrame containing the trade information to be included in the email.

    Returns:
        None

    Raises:
        smtplib.SMTPException: If there's an error in sending the email.
        KeyError: If the required environment variables are not set.

    """
    sender_email = os.environ["EMAIL_USER"] or os.getenv("EMAIL_USER")
    app_password = os.environ["EMAIL_PASSWORD"] or os.getenv("EMAIL_PASSWORD")

    # Create message
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = ', '.join(recipient_email) 
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    df_html = df.to_html(index=False)

    # Create HTML content
    html_content = f"""
    <html>
    <body>
        <p>Hi,</p>
        <p>Please see the latest trades from Pelosi's account below. </p>
        <p>For more information, visit: <a href="https://valueinvesting.io/nancy-pelosi-stock-trades-tracker">Nancy Pelosi Stock Trades Tracker</a></p>
        <p>Good luck!<br>Mark</p>
        {df_html}
    </body>
    </html>
    """

    message.attach(MIMEText(html_content, 'html'))

    # Create SMTP session
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender_email, app_password)
        server.send_message(message)

    logger.info("Email sent successfully")


if __name__ == "__main__":
    """
    Ensures the script runs only when executed directly, not when imported as a module.
    """
    
    if os.getenv("EMAIL_USER"):
        github_action = False
    else:
        github_action = True
    

    check_for_updates('trades.csv',github_action)

        
