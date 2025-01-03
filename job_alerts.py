from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, jsonify
import time
import smtplib
from collections import defaultdict
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException, StaleElementReferenceException
import traceback  # To print detailed stack trace
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import hashlib
import json
import threading

app = Flask(__name__)

# Configuration

EMAIL_NOTIFICATIONS = "anuragrawal2023@gmail.com"
EMAIL_PASSWORD = ""
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
PREVIOUS_JOBS_FILE = "prev_jobs.json"

COMPANIES = [{"COMPANY_NAME": "Google",
              "URL": "https://www.google.com/about/careers/applications/jobs/results",
              "JOB_TITLE_DIV": "div[class='ObfsIf-eEDwDf ObfsIf-eEDwDf-PvhD9-purZT-OiUrBf ObfsIf-eEDwDf-hJDwNd-Clt0zb']",
              "JOB_LINK_DIV": "div[jsname='hOZ7Ge']",
              "JOB_TITLE_TAG": "h3",
              "JOB_LINK_TAG": "a"},
              {"COMPANY_NAME": "C3 AI",
              "URL": "https://c3.ai/careers/",
              "JOB_TITLE_DIV": "div[class='cell large-12 medium-12 small-12 job_card'], div[class='cell large-12 medium-12 small-12 job_card more-item']",
              "JOB_LINK_DIV": "div[class='cell large-12 medium-12 small-12 job_card'], div[class='cell large-12 medium-12 small-12 job_card more-item']",
              "JOB_TITLE_TAG": "h4",
              "JOB_LINK_TAG": "a"},
              {"COMPANY_NAME": "Meta",
              "URL": "https://www.metacareers.com/jobs", #?page=1000
              "JOB_TITLE_DIV": "div[class='_6g3g x8y0a91 xriwhlb xngnso2 xeqmlgx xeqr9p9 x1e096f4']",
              "JOB_LINK_DIV": "div[class='cell large-12 medium-12 small-12 job_card'], div[class='cell large-12 medium-12 small-12 job_card more-item']",
              "JOB_TITLE_TAG": "h4",
              "JOB_LINK_TAG": "a"},
              {"COMPANY_NAME": "Apple",
              "URL": "https://jobs.apple.com/en-us/search?location=united-states-USA", #?page=1000
              "JOB_TITLE_DIV": "a[class='table--advanced-search__title']",
              "JOB_LINK_DIV": "a[class='table--advanced-search__title']",
              "JOB_TITLE_TAG": "h4",#NA
              "JOB_LINK_TAG": "a"},]#NA

# [{"COMPANY_NAME": "Netflix",
#               "URL": "https://explore.jobs.netflix.net/careers", #?page=1000
#               "JOB_TITLE_DIV": "div[class='position-title line-clamp line-clamp-2 line-clamp-done']",
#               "JOB_LINK_DIV": "div[class='cell large-12 medium-12 small-12 job_card'], div[class='cell large-12 medium-12 small-12 job_card more-item']",
#               "JOB_TITLE_TAG": "h4",
#               "JOB_LINK_TAG": "a"},]


# List of companies for the dropdown
COMPANIES_DROPDOWN_OPTIONS = [
    {"COMPANY_NAME": "Google"},
    {"COMPANY_NAME": "C3 AI"},
    {"COMPANY_NAME": "Meta"},
    {"COMPANY_NAME": "Apple"},
]

# KEYWORDS = ["scientist", "engineer"]

# Load previously seen job hashes
def load_previous_hashes(company_name):
    try:
        with open(PREVIOUS_JOBS_FILE, "r") as f:
            return set(json.load(f)[company_name])
    except FileNotFoundError:
        return set()
    except KeyError:
        return set()
    
# Save current job hashes
def save_hashes(updated_hashes, company_name):
    # Load existing hashes if the file exists
    try:
        with open(PREVIOUS_JOBS_FILE, "r") as f:
            hashes = json.load(f)
    except FileNotFoundError:
        hashes = {}  # Initialize an empty dictionary if the file doesn't exist

    # Update the hashes for the given company
    hashes[company_name] = list(set(updated_hashes))  # Ensure uniqueness of hashes

    # Save back to the file
    with open(PREVIOUS_JOBS_FILE, "w") as f:
        json.dump(hashes, f, indent=4)

# Generate a unique hash for a job
def generate_job_hash(job):
    job_string = f"{job['title']}|{job['link']}|{job.get('company', '')}"
    return hashlib.sha256(job_string.encode("utf-8")).hexdigest()

# Function to set up Selenium WebDriver
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    service = Service("/home/anurag/personal/Hourly_job_alerts/chromedriver-linux64/chromedriver")  # Update with your chromedriver path
    #Mac - "/Users/anuragagrawal/Downloads/chromedriver-mac-arm64/chromedriver"
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def fetch_meta_jobs(company_dict, keywords):
    jobs = []
    driver = get_driver() # Ensure the correct driver path is set
    try:
        driver.get(company_dict["URL"])
        time.sleep(30)  # Allow time for the page to load fully

        # Load previously seen hashes
        previous_hashes = load_previous_hashes(company_dict["COMPANY_NAME"])
        new_hashes = set()

        # Find all job elements
        job_elements = driver.find_elements(By.CSS_SELECTOR, company_dict["JOB_TITLE_DIV"])
        # job_elements = driver.find_elements(By.CSS_SELECTOR, "a.card position-card pointer")
        
        print(job_elements)
        print(f"Found {len(job_elements)} job elements.")

        for index, job in enumerate(job_elements):
            try:
                # Scroll to the job element for visibility
                driver.execute_script("arguments[0].scrollIntoView(true);", job)
                time.sleep(1)

                # Extract the job title
                title = job.text.strip()
                # print(f"Job {index + 1} Title: {title}")

                # Extract link from data attributes (if available)
                job_link = job.get_attribute("data-href") or job.get_attribute("data-url") or None

                if not job_link:
                    # Fallback: Simulate CTRL+Click to open in a new tab
                    ActionChains(driver).key_down(Keys.CONTROL).click(job).key_up(Keys.CONTROL).perform()
                    time.sleep(3)

                    if company_dict["COMPANY_NAME"] == "Meta":
                        # Switch to the new tab and capture the URL
                        driver.switch_to.window(driver.window_handles[1])
                        job_link = driver.current_url
                        # print(f"Job {index + 1} Link: {job_link}")

                        # Close the new tab and switch back
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                    elif company_dict["COMPANY_NAME"] == "Netflix":
                        job_link = driver.current_url
                
                else:
                    pass
                
                # print(f"Job {index + 1} Link (from attributes): {job_link}")
                job_entry = {"title": title, "link": job_link, "company": company_dict["COMPANY_NAME"]}
                job_hash = generate_job_hash(job_entry)
                # Skip if job is already seen
                if job_hash in previous_hashes:
                    print(f"Encountered previously seen job: {job_entry}. Skipping remaining/older jobs.")
                    return jobs

                if any(keyword.lower() in title.lower() for keyword in keywords):
                    jobs.append(job_entry)
                    new_hashes.add(job_hash)

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
        # Update stored hashes with new ones
        previous_hashes.update(new_hashes)
        save_hashes(previous_hashes, company_dict["COMPANY_NAME"])
        return jobs

def fetch_jobs(company_dict, keywords):
    if company_dict["COMPANY_NAME"] in ["Meta", "Netflix"]: return fetch_meta_jobs(company_dict, keywords)
    jobs = []
    driver = get_driver()
    try:
        driver.get(company_dict["URL"])
        time.sleep(5)  # Allow time for page to load

        # Load previously seen hashes
        previous_hashes = load_previous_hashes(company_dict["COMPANY_NAME"])
        new_hashes = set()

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
        print(f"URL after clicking/checking for buttons: {driver.current_url}")

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
        
        print(f"URL after infinite scroll: {driver.current_url}")

        # Handle Pagination
        while True:
            # Extract jobs
            try:
                job_elements = driver.find_elements(By.CSS_SELECTOR, company_dict["JOB_TITLE_DIV"])
                job_links = driver.find_elements(By.CSS_SELECTOR, company_dict["JOB_LINK_DIV"])

                print(f"Found {len(job_elements)} job elements and {len(job_links)} job links.")

                for job, job_link in zip(job_elements, job_links):
                    print(job.text, job_link.get_attribute("href"))
                    try:
                        if company_dict["COMPANY_NAME"] != "Apple":
                            title_element = job.find_element(By.CSS_SELECTOR, company_dict["JOB_TITLE_TAG"])
                            title = title_element.text.strip()
                            link_element = job_link.find_element(By.CSS_SELECTOR, company_dict["JOB_LINK_TAG"])
                            link = link_element.get_attribute("href")
                        else:
                            title = job.text.strip()
                            link = job_link.get_attribute("href")

                        job_entry = {"title": title, "link": link, "company": company_dict["COMPANY_NAME"]}
                        job_hash = generate_job_hash(job_entry)
                        # Skip if job is already seen
                        if job_hash in previous_hashes:
                            print(f"Encountered previously seen job: {job_entry}. Skipping remaining/older jobs.")
                            return jobs

                        if any(keyword.lower() in title.lower() for keyword in keywords):
                            jobs.append(job_entry)
                            new_hashes.add(job_hash)
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
                except NoSuchElementException:
                    break
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
    
    # Update stored hashes with new ones
    previous_hashes.update(new_hashes)
    save_hashes(previous_hashes, company_dict["COMPANY_NAME"])
    
    print(f"Total jobs collected: {len(jobs)}")
    return jobs

# Fetch and store new jobs
def collect_new_jobs(temp, keywords):
    all_jobs = defaultdict(list)
    for company in temp:
        jobs = fetch_jobs(company, keywords)
        all_jobs[company["COMPANY_NAME"]].extend(jobs)
    print(all_jobs)
    return all_jobs

# Send daily email notifications
def send_email(all_jobs, toEmailID):
    try:
        message = MIMEMultipart()
        message["From"] = EMAIL_NOTIFICATIONS
        message["To"] = toEmailID
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
def daily_job_alert(new_jobs):
    # new_jobs = collect_new_jobs()
    if new_jobs:
        send_email(new_jobs)

# # Web interface
# @app.route("/")
# def home():
#     jobs = collect_new_jobs()
#     return render_template("index.html", jobs=jobs)

# Placeholder for results
results = []

def background_task(selected_companies):
    """Simulate a long-running job fetching task."""
    global results
    results = []  # Reset results
    for company in selected_companies:
        time.sleep(2)  # Simulate a delay
        results.append(f"Fetched jobs for {company}")

@app.route("/", methods=["GET", "POST"])
def home():
    available_companies = [company["COMPANY_NAME"] for company in COMPANIES_DROPDOWN_OPTIONS]  # Update the variable name
    jobs = {}

    if request.method == "POST":
        # Get selected companies from the form
        selected_companies = request.form.getlist("companies")
        print(selected_companies)
        temp = [COMPANY for COMPANY in COMPANIES if COMPANY["COMPANY_NAME"] in selected_companies]


        # Get keywords and split into a list
        raw_keywords = request.form.get("keywords", "")
        keywords = [keyword.strip().lower() for keyword in raw_keywords.split(",") if keyword.strip()]

        toEmailID = request.form.get("email") or "anuragrawal2023@gmail.com"

        print(toEmailID)
        # Run the job fetching logic for the selected companies
        jobs = collect_new_jobs(temp, keywords)
        send_email(jobs, toEmailID)
        return  jsonify(jobs)
    
    return render_template("index.html", available_companies=available_companies)


@app.route("/results", methods=["GET"])
def get_results():
    """Return the results to the client."""
    global results
    if not results:
        return jsonify({"status": "Processing", "data": []})
    return jsonify({"status": "Completed", "data": results})

if __name__ == "__main__":
    # daily_job_alert()
    app.run(debug=True, port=5004)
