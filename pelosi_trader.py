from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import pandas as pd
import time
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Function to scrape the website and return data as a pandas DataFrame
def scrape_website() -> pd.DataFrame:
    """
    Scrapes the stock trade table from the specified website and returns it as a pandas DataFrame.
    
    Returns:
        pd.DataFrame: DataFrame containing the scraped table data.
    """
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
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


def check_for_updates(csv_filename: str) -> None:
    """
    Checks for new stock trade records and updates the CSV file if changes are detected.
    
    Args:
        csv_filename (str): Path to the CSV file storing previous trade data.
    """
    new_data = scrape_website()
    
    if not os.path.exists(csv_filename):
        new_data.to_csv(csv_filename, index=False)
        logger.info('Initial data saved')
        return False
    
    old_data = pd.read_csv(csv_filename)
    
    if len(new_data) > len(old_data):  # Check if new trades have been added
        new_data.to_csv(csv_filename, index=False)
        logger.info('Data updated and saved')
        return True
    else:
        logger.info('No changes')
        return False


def send_email(recipient_email, subject, body,df):
    # Get credentials from environment variables
    sender_email = os.environ["EMAIL_USER"] or os.getenv("EMAIL_USER")
    app_password = os.environ["EMAIL_PASS"] or os.getenv("EMAIL_PASSWORD")

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
        <p>Please find below the latest trades from Pelosi's account:</p>
        {df_html}
        <p> Good luck!,<br>Mark</p>
    </body>
    </html>
    """

    message.attach(MIMEText(html_content, 'html'))

    # Create SMTP session
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender_email, app_password)
        server.send_message(message)

    print("Email sent successfully")




if __name__ == "__main__":
    """
    Ensures the script runs only when executed directly, not when imported as a module.
    """
        
    #is_update = check_for_updates('trades.csv')

    is_update = True

    if is_update:

        updated_df = pd.read_csv('trades.csv')

        updated_df ['Update Date'] = datetime.now().date().isoformat()

        # Usage example
        recipient_email = ["mark.golob275@gmail.com"]
        subject = "Pelosi Trades Update"
        body = "Attached is the latest updated stock trade data."

        send_email(recipient_email, subject, body,updated_df)