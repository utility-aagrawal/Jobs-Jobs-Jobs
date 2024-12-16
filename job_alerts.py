
import requests
from bs4 import BeautifulSoup
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

app = Flask(__name__)

# Configuration

EMAIL_NOTIFICATIONS = "anuragrawal2023@gmail.com"
EMAIL_PASSWORD = "ecjkcytjrtzrfwig"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
NEW_JOBS_FILE = "new_jobs.json"

COMPANIES = [{"COMPANY_NAME": "Google",
              "URL": "https://www.google.com/about/careers/applications/jobs/results",
              "JOB_TITLE_DIV": "div[class='ObfsIf-eEDwDf ObfsIf-eEDwDf-PvhD9-purZT-OiUrBf ObfsIf-eEDwDf-hJDwNd-Clt0zb']",
              "JOB_LINK_DIV": "div[jsname='hOZ7Ge']",
              "JOB_TITLE_TAG": "h3",
              "JOB_LINK_TAG": "a"},
               {"COMPANY_NAME": "C3 AI",
              "URL": "https://c3.ai/careers/",
              "JOB_TITLE_DIV": "div[class='cell large-12 medium-12 small-12 job_card']",
              "JOB_LINK_DIV": "div[class='cell large-12 medium-12 small-12 job_card']",
              "JOB_TITLE_TAG": "h4",
              "JOB_LINK_TAG": "a"}]
KEYWORDS = ["scientist", "AI"]

# Function to set up Selenium WebDriver
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    service = Service("/home/anurag/personal/chromedriver-linux64/chromedriver")  # Update with your chromedriver path
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# Function to fetch job postings from Google's careers page
def fetch_jobs(company_dict):
    jobs = []
    driver = get_driver()
    try:
        driver.get(company_dict["URL"])
        time.sleep(30)  # Allow time for JavaScript to load
        # Debugging: Print the page source

        # Save the HTML to a file for debugging
        with open(f"{company_dict['COMPANY_NAME']}.html", "w", encoding="utf-8") as file:
            file.write(driver.page_source)
        print(f"Saved HTML for {company_dict['COMPANY_NAME']} to {company_dict['COMPANY_NAME']}.html")

        job_elements = driver.find_elements(By.CSS_SELECTOR, company_dict["JOB_TITLE_DIV"])
        job_links = driver.find_elements(By.CSS_SELECTOR, company_dict["JOB_LINK_DIV"])
        print(company_dict["COMPANY_NAME"],job_elements, job_links)
        for job, job_link in zip(job_elements, job_links):
            title_element = job.find_element(By.CSS_SELECTOR, company_dict["JOB_TITLE_TAG"])
            link_element = job_link.find_element(By.CSS_SELECTOR, company_dict["JOB_LINK_TAG"])
            title = title_element.text
            link = link_element.get_attribute("href")
            if any(keyword.lower() in title.lower() for keyword in KEYWORDS):
                jobs.append({"title": title, "link": link})
    finally:
        driver.quit()
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
