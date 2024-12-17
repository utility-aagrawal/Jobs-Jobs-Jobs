from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    NoSuchElementException,
)
import time
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template
import time
import smtplib
from collections import defaultdict
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException
import traceback  # To print detailed stack trace


# Function to set up Selenium WebDriver
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    service = Service("/home/anurag/personal/Hourly_job_alerts/chromedriver-linux64/chromedriver")  # Update with your chromedriver path
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def fetch_meta_jobs():
    jobs = []
    driver = get_driver() # Ensure the correct driver path is set
    try:
        driver.get("https://www.metacareers.com/jobs")
        time.sleep(5)  # Allow time for the page to load fully

        # Scroll the page to load all job elements dynamically
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        print("Finished scrolling the page.")

        # Find all job elements
        job_elements = driver.find_elements(By.CSS_SELECTOR, "div[role='link']")
        print(f"Found {len(job_elements)} job elements.")

        for index, job in enumerate(job_elements):
            try:
                # Scroll to the job element for visibility
                driver.execute_script("arguments[0].scrollIntoView(true);", job)
                time.sleep(1)

                # Extract the job title
                title = job.text.strip()
                print(f"Job {index + 1} Title: {title}")

                # Extract link from data attributes (if available)
                job_link = job.get_attribute("data-href") or job.get_attribute("data-url") or None

                if not job_link:
                    # Fallback: Simulate CTRL+Click to open in a new tab
                    ActionChains(driver).key_down(Keys.CONTROL).click(job).key_up(Keys.CONTROL).perform()
                    time.sleep(3)

                    # Switch to the new tab and capture the URL
                    driver.switch_to.window(driver.window_handles[1])
                    job_link = driver.current_url
                    print(f"Job {index + 1} Link: {job_link}")

                    # Close the new tab and switch back
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                else:
                    print(f"Job {index + 1} Link (from attributes): {job_link}")

                # Save the job details
                jobs.append({"title": title, "link": job_link})

            except StaleElementReferenceException:
                print(f"Stale element for job {index + 1}. Skipping...")
                continue
            except Exception as e:
                print(f"Error processing job {index + 1}: {e}")
                print(traceback.format_exc())
                continue

    finally:
        print("Closing the browser...")
        driver.quit()
        print(f"Total jobs fetched: {len(jobs)}")
        return jobs

# Run the function
meta_jobs = fetch_meta_jobs()
print(meta_jobs)
