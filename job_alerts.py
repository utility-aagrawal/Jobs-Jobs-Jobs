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

app = Flask(__name__)

# Configuration

EMAIL_NOTIFICATIONS = ""
EMAIL_PASSWORD = ""
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
NEW_JOBS_FILE = "new_jobs.json"

COMPANIES = [{"COMPANY_NAME": "Meta",
              "URL": "https://www.metacareers.com/jobs?page=1000",
              "JOB_TITLE_DIV": "div[class='_6g3g x8y0a91 xriwhlb xngnso2 xeqmlgx xeqr9p9 x1e096f4']",
              "JOB_LINK_DIV": "div[class='cell large-12 medium-12 small-12 job_card'], div[class='cell large-12 medium-12 small-12 job_card more-item']",
              "JOB_TITLE_TAG": "h4",
              "JOB_LINK_TAG": "a"}]
# [{"COMPANY_NAME": "Google",
#               "URL": "https://www.google.com/about/careers/applications/jobs/results",
#               "JOB_TITLE_DIV": "div[class='ObfsIf-eEDwDf ObfsIf-eEDwDf-PvhD9-purZT-OiUrBf ObfsIf-eEDwDf-hJDwNd-Clt0zb']",
#               "JOB_LINK_DIV": "div[jsname='hOZ7Ge']",
#               "JOB_TITLE_TAG": "h3",
#               "JOB_LINK_TAG": "a"},
#               {"COMPANY_NAME": "C3 AI",
#               "URL": "https://c3.ai/careers/",
#               "JOB_TITLE_DIV": "div[class='cell large-12 medium-12 small-12 job_card'], div[class='cell large-12 medium-12 small-12 job_card more-item']",
#               "JOB_LINK_DIV": "div[class='cell large-12 medium-12 small-12 job_card'], div[class='cell large-12 medium-12 small-12 job_card more-item']",
#               "JOB_TITLE_TAG": "h4",
#               "JOB_LINK_TAG": "a"},


KEYWORDS = ["scientist", "AI"]

# Function to set up Selenium WebDriver
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    service = Service("/home/anurag/personal/Hourly_job_alerts/chromedriver-linux64/chromedriver")  # Update with your chromedriver path
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def fetch_jobs(company_dict):
    jobs = []
    driver = get_driver()
    try:
        driver.get(company_dict["URL"])
        time.sleep(5)  # Allow time for page to load

        # Handle "View All" button using CSS Selector
        try:
            view_all_buttons = driver.find_elements(By.CSS_SELECTOR, "button")
            view_all_clicked = False

            for button in view_all_buttons:
                print(f"Checking button: '{button.text.strip()}'")
                if "View all" in button.text.strip():
                    print("Found 'View all' button. Attempting to click...")
                    driver.execute_script("arguments[0].scrollIntoView(true);", button)
                    driver.execute_script("arguments[0].click();", button)  # Force click using JS
                    time.sleep(5)
                    view_all_clicked = True
                    print("'View all' button clicked successfully.")
                    break

            if not view_all_clicked:
                print("No 'View all' button found with correct text.")
        except Exception as e:
            print("Error while handling 'View All' button:")
            print(traceback.format_exc())

        # Scroll to the bottom if infinite scroll
        try:
            print("Checking for infinite scroll...")
            last_height = driver.execute_script("return document.body.scrollHeight")
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    print("Reached bottom of the page.")
                    break
                last_height = new_height
        except Exception as e:
            print("Error during infinite scroll:")
            print(traceback.format_exc())

        # Handle Pagination
        while True:
            # Extract jobs
            try:
                job_elements = driver.find_elements(By.CSS_SELECTOR, company_dict["JOB_TITLE_DIV"])
                job_links = driver.find_elements(By.CSS_SELECTOR, company_dict["JOB_LINK_DIV"])

                print(f"Found {len(job_elements)} job elements and {len(job_links)} job links.")

                for job, job_link in zip(job_elements, job_links):
                    try:
                        try:
                            title_element = job.find_element(By.CSS_SELECTOR, company_dict["JOB_TITLE_TAG"])
                            title = title_element.text
                        except NoSuchElementException:
                            title = job.text
                        link_element = job_link.find_element(By.CSS_SELECTOR, company_dict["JOB_LINK_TAG"])
                        link = link_element.get_attribute("href")

                        if any(keyword.lower() in title.lower() for keyword in KEYWORDS):
                            jobs.append({"title": title, "link": link})
                    except Exception as e:
                        print("Error extracting job details:")
                        print(traceback.format_exc())

                # Click the "Next" button if available
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, "a[aria-label='Go to next page']")
                    print("Found 'Next' button. Clicking to go to the next page...")
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    driver.execute_script("arguments[0].click();", next_button)  # Force click
                    time.sleep(5)
                except ElementClickInterceptedException:
                    print("Click intercepted! Attempting to close overlays...")
                    # Example: Hide the interfering element
                    driver.execute_script("document.querySelector('.gb_Ta').style.display='none';")
                    next_button.click()   
                except Exception as e:
                    print("No more pages or error clicking 'Next' button:")
                    print(traceback.format_exc())
                    break
            except Exception as e:
                print("Error while extracting jobs or handling pagination:")
                print(traceback.format_exc())
                break

    finally:
        print("Closing the browser...")
        driver.quit()
    
    print(f"Total jobs collected: {len(jobs)}")
    return jobs

# Fetch and store new jobs
def collect_new_jobs():
    all_jobs = defaultdict(list)
    for company in COMPANIES:
        jobs = fetch_jobs(company)
        all_jobs[company["COMPANY_NAME"]].extend(jobs)
    print(all_jobs)
    return all_jobs

# Send daily email notifications
def send_email(all_jobs):
    try:
        message = MIMEMultipart()
        message["From"] = EMAIL_NOTIFICATIONS
        message["To"] = EMAIL_NOTIFICATIONS
        message["Subject"] = "Daily Job Alerts"

        html_content = "<h2>New Job Postings:</h2><ul>"
        for company_name, jobs in all_jobs.items():
            html_content += f'<li>{company_name}</li><ul>'
            for job in jobs:
                html_content += f'<li><a href="{job["link"]}">{job["title"]}</a></li>'
            html_content += "</ul>"
        html_content += "</ul>"

        message.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_NOTIFICATIONS, EMAIL_PASSWORD)
            server.send_message(message)
            print("Email sent successfully!")  # Add this for logging
    except Exception as e:
        print(f"Error sending email: {e}")  # Catch and print any errors

# Daily task to fetch and send email
def daily_job_alert():
    new_jobs = collect_new_jobs()
    if new_jobs:
        send_email(new_jobs)

# Web interface
@app.route("/")
def home():
    jobs = collect_new_jobs()
    return render_template("index.html", jobs=jobs)

if __name__ == "__main__":
    # daily_job_alert()
    app.run(debug=True)
