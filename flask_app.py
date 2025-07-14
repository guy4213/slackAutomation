
import smtplib
from email.message import EmailMessage
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pickle
import os
import logging
from dotenv import load_dotenv # Import load_dotenv
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from flask import Flask, request, jsonify
from flask_cors import CORS 

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("slack_inviter.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

# Load saved session cookies (if available)Q
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_FILE = os.path.join(BASE_DIR, "slack_cookies.pkl")

# Function to perform Slack invitation
def invite_emails(emails,channelsNames,isMember,className):
    logger.info(f"Starting invitation process for: {emails}")
    # Setup Chrome driver (undetected to avoid bot detection)
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")            # Headless mode (Chromium >= 109)
    options.add_argument("--no-sandbox")               # Required in many Linux containers
    options.add_argument("--disable-dev-shm-usage")    # Prevents /dev/shm issues
    options.add_argument("--disable-gpu")              # Disable GPU if any issues
    options.add_argument("--window-size=1920,1080")  
    options.binary_location = "/usr/bin/google-chrome"  # חשוב! עבור Render
  # Optional: set window size
    driver = uc.Chrome(options=options)
    driver.maximize_window()
    logger.info(f"className is {className}")
    try:
        # Open Slack login page
        driver.get("https://iaccollege.slack.com")
        logger.info("Opened Slack login page")

        # Load cookies to avoid re-login
        if os.path.exists(COOKIES_FILE):
            try:
                logger.info(f"Looking for cookies in: {COOKIES_FILE}")
                logger.info(f"File exists? {os.path.exists(COOKIES_FILE)}")
                with open(COOKIES_FILE, "rb") as f:
                    cookies = pickle.load(f)
                    for cookie in cookies:
                        try:
                            driver.add_cookie(cookie)
                        except Exception as e:
                            logger.warning(f"Cookie error: {e}")
                driver.refresh()
                logger.info("Loaded session cookies to bypass login.")
            except Exception as e:
                logger.error(f"Error loading cookies: {e}")
        else:
            logger.warning("No cookies found. Please log in manually.")

        # Wait for user to manually log in (if cookies are not available)
        if not os.path.exists(COOKIES_FILE):
            input("Manually log in, then press Enter to continue...")
            with open(COOKIES_FILE, "wb") as f:
                pickle.dump(driver.get_cookies(), f)
            logger.info("Saved session cookies for future logins.")

        # Navigate to admin page
        driver.get("https://iaccollege.slack.com/admin/invites")
        logger.info("Navigated to admin invites page")

        wait = WebDriverWait(driver, 15)

        # Find and click the Invite People button
        invite_button = None
        invite_buttons = [
            '//button[contains(text(), "Invite People")]',
            '//a[contains(text(), "Invite People")]',
            '//span[contains(text(), "Invite People")]/parent::button',
            '//div[contains(@class, "p-admin_invites")]//button[contains(@class, "c-button")]'
        ]

        for selector in invite_buttons:
            try:
                invite_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                invite_button.click()
                logger.info("Clicked Invite People button")
                break
            except Exception as e:
                logger.warning(f"Selector {selector} failed: {e}")
                continue

        if not invite_button:
            raise Exception("Could not find 'Invite People' button.")

        # Wait for the invitation dialog to appear
        time.sleep(2)

        # Locate the first multi-select input div
        email_input_div = None
        multi_select_xpath = '(//div[contains(@class, "c-multi_select_input")])[1]'

        try:
            email_input_div = wait.until(EC.presence_of_element_located((By.XPATH, multi_select_xpath)))
        except TimeoutException:
            raise Exception("Could not find the email input field.")

        # Split the emails string by commas. This allows for inviting multiple users.
        email_list = emails.split(",") 
        logger.info(f"Processing {len(email_list)} emails")

        # Locate the contenteditable div and click on it
        input_element = email_input_div.find_element(By.XPATH, ".//div[@contenteditable='true']")

        # Wait for the element to be clickable before interacting with it
        wait.until(EC.element_to_be_clickable((By.XPATH, ".//div[@contenteditable='true']")))

        input_element.click()
        # Iterate over each email and enter it
        for email in email_list: 
            email = email.strip()  # Remove any whitespace
            if email: # Only process non-empty email strings
                logger.info(f"Entering email: {email}")
                
                # Send the email character by character with a small delay to prevent skipping
                for char in email:
                    input_element.send_keys(char)
                
                time.sleep(0.5)  # Pause before pressing Enter

                # After entering the email, press ENTER
                input_element.send_keys(Keys.ENTER)
                logger.info(f"Entered email: {email}")
                time.sleep(0.2)  # Wait a moment before entering the next email
        
        time.sleep(0.5)
        
        typeUser_button=None
        typeUser_selector='//div[contains(@class, "c-select_button") and contains(@class, "c-select_button--medium")]'
        guest_button=None
        guest_selector="//div[contains(@class, 'c-select_options_list__option')][2]"
        customizeButton_selector="//button[contains(@class, 'c-button-unstyled') and contains(@class, 'p-customize_button--toggle-button')]"
 
                    
        channels_selector="//div[contains(@class, 'c-multi_select_input c-multi_select_input--initial')]"
        channels_Names_list = channelsNames.split(",")

        if  isMember=="false":
            try:
                typeUser_button = driver.find_element(By.XPATH, typeUser_selector)
                typeUser_button.click()
                logger.info("Clicked typeUser_button button")
            except Exception as e:
                logger.error(f"Error clicking 'typeUser_button': {e}")
                raise

            try:
                guest_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, guest_selector)))
                guest_button.click()
                logger.info("Clicked guest button")
            except Exception as e:
                logger.error(f"Error clicking 'guest_button': {e}")
                raise

            time.sleep(0.5)

            try:
            # Wait until the parent element is visible and clickable (the div itself)
                channels_inp_div = wait.until(EC.element_to_be_clickable((By.XPATH, channels_selector)))
                
                # Click the parent element (div)
                channels_inp_div.click()

                # Wait for the span with contenteditable=true to be present
                channels_inp_span = wait.until(EC.visibility_of_element_located(
                    (By.XPATH, "(//div[@role='combobox']//span[contains(@class,'c-multi_select_input__filter_query')])[2]")
                ))

                # Ensure the element is focused by executing JavaScript to explicitly focus it
                driver.execute_script("arguments[0].focus();", channels_inp_span)

                # Send the input text into the span (contenteditable field)
                for _name in channels_Names_list:
                    channels_inp_span.send_keys(_name)
                    time.sleep(0.5)
                    channels_inp_span.send_keys(Keys.ENTER)

                # Then send the Enter key separately
                    
                # Log success
                logger.info( "Entered channel name into the input field." )

            except Exception as e:
                logger.error(f"Error interacting with 'channels_inp': {e}")
            
        else:
            try:
                    
                customizeButton = driver.find_element(By.XPATH, customizeButton_selector)
                customizeButton.click()
                logger.info("Clicked customizeButton button")
            except Exception as e:
                logger.error(f"Error clicking 'customizeButton': {e}")
                raise
            time.sleep(0.5)
        
            try:
            # Wait until the parent element is visible and clickable (the div itself)
                channels_inp_div = wait.until(EC.element_to_be_clickable((By.XPATH, channels_selector)))
                
                # Click the parent element (div)
                channels_inp_div.click()

                # Wait for the span with contenteditable=true to be present
                channels_inp_span = wait.until(EC.visibility_of_element_located(
                    (By.XPATH, "(//div[@role='combobox']//span[contains(@class,'c-multi_select_input__filter_query')])[2]")
                ))

                # Ensure the element is focused by executing JavaScript to explicitly focus it
                driver.execute_script("arguments[0].focus();", channels_inp_span)

                # Send the input text into the span (contenteditable field)
                for _name in channels_Names_list:
                    channels_inp_span.send_keys(_name)
                    time.sleep(0.5)
                    channels_inp_span.send_keys(Keys.ENTER)

                # Then send the Enter key separately
                    
                # Log success
                logger.info("Entered channel name into the input field.")

            except Exception as e:
                logger.error(f"Error interacting with 'channels_inp_member_Section': {e}")         
                
        time.sleep(1)         

        send_button = None
        send_selector = '//button[contains(@aria-label, "Send")]'

        try:
            send_button = wait.until(EC.element_to_be_clickable((By.XPATH, send_selector)))
            send_button.click()
            logger.info("Clicked Send button")
        except TimeoutException:
            raise Exception("Could not find 'Send' button after waiting.")

        # Wait for confirmation
        time.sleep(3)
        logger.info("Invitation process completed successfully")
        return "Emails invited successfully."

    except Exception as e:
        logger.error(f"Error occurred: {e}")

        # Save error screenshot
        driver.save_screenshot("error_screenshot.png")
        logger.error("Error screenshot saved as 'error_screenshot.png'")

        # Save page source for debugging
        with open("error_page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        logger.error("Saved page source for debugging.")
        
        raise e  # Re-raise to be caught by the route handler
    
    finally:
        # Close browser
        driver.quit()
        logger.info("Browser closed.")
def send_zoho_email(email_address, class_name):
    """
    Sends an email to Zoho Creator with the student's details.
    Uses environment variables for sender credentials for security.
    """
    # --- הגדרות מאובטחות ---
    # מומלץ מאוד להגדיר את המשתנים האלו כמשתני סביבה במערכת שלך
    SENDER_EMAIL = os.environ.get('ZOHO_SENDER_EMAIL')
    SENDER_PASSWORD = os.environ.get('ZOHO_SENDER_PASSWORD') # השתמש בסיסמת אפליקציה של ג'ימייל
    RECIPIENT_EMAIL = "kfiram-266@forms.zohocreator.com"

    if not SENDER_EMAIL or not SENDER_PASSWORD:
        logger.error("Sender email or password not found in environment variables.")
        logger.error("Please set ZOHO_SENDER_EMAIL and ZOHO_SENDER_PASSWORD.")
        return "Error: Email credentials not configured on the server."

    # --- יצירת תוכן המייל ---
    msg = EmailMessage()
    msg['Subject'] = f"New Student Registration for Class: {class_name}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL

    # גוף המייל צריך להיות בפורמט ש-Zoho יוכל לנתח בקלות
    # פורמט פשוט של מפתח: ערך הוא בדרך כלל הטוב ביותר
    email_body = f"""
    Email: {email_address}
    ClassName: {class_name}
    """
    msg.set_content(email_body)

    # --- שליחת המייל ---
    try:
        # התחברות לשרת ה-SMTP של גוגל עם SSL
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
            logger.info(f"Successfully sent email to Zoho for {email_address} in class {class_name}")
            return f"Successfully sent registration for {email_address} to Zoho."

    except Exception as e:
        logger.error(f"Failed to send email to Zoho. Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error: Failed to send email to Zoho: {e}"

# REST endpoint for the POST request with improved error handling
@app.route('/invite', methods=['POST'])
def invite():
    logger.info(f"Received invitation request from {request.remote_addr}")
    
    try:
        # Get JSON data from the request body
        data = request.get_json()
        logger.info(f"Request data: {data}")
        
        # Check for missing required fields
        if not data:
            logger.warning("No data received in request")
            return jsonify({"error": "No JSON data provided in the request body.", "ok": False}), 400

        required_fields = ['emails', 'channelsNames', 'isMember', 'className']
        for field in required_fields:
            if field not in data:
                logger.warning(f"Missing '{field}' field in request")
                return jsonify({"error": f"Missing '{field}' field in the request body.", "ok": False}), 400
        
        emails = data['emails']
        channelsNames = data['channelsNames']
        isMember = data['isMember']
        className = data['className']
        
        # Check if emails and className are strings
        if not isinstance(emails, str) or not isinstance(className, str):
            logger.warning("Invalid input: 'emails' or 'className' is not a string.")
            return jsonify({"error": "'emails' and 'className' must be strings.", "ok": False}), 400

        logger.info(f"Processing Slack invitation for: {emails}")
        
        # Call the function to send Slack invitations
        slack_result = invite_emails(emails, channelsNames, isMember, className)
        logger.info(f"Slack invitation result: {slack_result}")
        
        zoho_api_res = "Not a single email, Zoho call skipped."
        
        # --- כאן מבצעים את הבדיקה והשליחה ל-ZOHO ---
        trimmed_emails = emails.strip()
        # Check if the emails string is a single email (no common delimiters)
        if not (',' in trimmed_emails or ';' in trimmed_emails or ' ' in trimmed_emails):
            if trimmed_emails: # Make sure it's not an empty string
                logger.info(f"Detected single email '{trimmed_emails}'. Processing ZOHO request.")
                # קריאה לפונקציית המייל החדשה
                zoho_api_res = send_zoho_email(email_address=trimmed_emails, class_name=className)
            else:
                zoho_api_res = "Email string was empty, Zoho call skipped."


        return jsonify({
            "slack_message": slack_result,
            "zoho_message": zoho_api_res,
            "ok": True
        })
    
    except Exception as e:
        logger.error(f"Error processing invitation: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e), "ok": False}), 500


        
# Status endpoint to check if server is running
@app.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "running", "ok": True})

# Start the Flask application
if __name__ == '__main__':
    logger.info("Starting Flask server on 0.0.0.0:5000")
    print("Server is running at http://0.0.0.0:5000")
    print("Your local IP addresses:")
    
    # Show available IP addresses to help with configuration
    import socket
    hostname = socket.gethostname()
    ip_list = socket.gethostbyname_ex(hostname)[2]
    for ip in ip_list:
        print(f"  http://{ip}:5000")
    
    app.run(host='0.0.0.0', port=5000)
