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
from dotenv import load_dotenv
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from flask import Flask, request, jsonify
from flask_cors import CORS 
import base64


# הוסף את זה אחרי ה-imports
def load_cookies_from_env():
    """טוען cookies ממשתני סביבה אם קובץ לא קיים"""
    if os.path.exists("slack_cookies.pkl"):
        logger.info("Using local cookies file")
        return
    
    cookies_b64 = os.environ.get('SLACK_COOKIES_BASE64')
    if cookies_b64:
        try:
            import pickle
            cookies_data = base64.b64decode(cookies_b64)
            with open("slack_cookies.pkl", "wb") as f:
                f.write(cookies_data)
            logger.info("Loaded cookies from environment variable")
        except Exception as e:
            logger.error(f"Failed to load cookies from env: {e}")

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
CORS(app)

# Load saved session cookies (if available)
COOKIES_FILE = "slack_cookies.pkl"

def send_zoho_email(subject, email_body, action_type="general"):
    """
    שולח מייל לזוהו עם פרטי הפעולה
    action_type: "invite", "role_change", "error", "general"
    """
    SENDER_EMAIL = os.environ.get('ZOHO_SENDER_EMAIL')
    SENDER_PASSWORD = os.environ.get('ZOHO_SENDER_PASSWORD')
    RECIPIENT_EMAIL = "kfiram-266@forms.zohocreator.com"

    if not SENDER_EMAIL or not SENDER_PASSWORD:
        logger.error("Sender email or password not found in environment variables.")
        return "Error: Email credentials not configured on the server."

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg.set_content(email_body)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
            logger.info(f"Successfully sent email to Zoho: {subject}")
            return f"Email sent successfully: {subject}"
    except Exception as e:
        logger.error(f"Failed to send email to Zoho. Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error: Failed to send email to Zoho: {e}"

# Function to perform Slack invitation
def invite_emails(emails, channelsNames, isMember, className):
    logger.info(f"Starting invitation process for: {emails}")
    
    load_cookies_from_env()
    
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-images")
    options.add_argument("--disable-extensions")
    options.add_argument("--single-process")
    options.add_argument("--window-size=1920,1080")  
    options.binary_location = "/usr/bin/google-chrome"
    
    driver = uc.Chrome(options=options, version_main=140)  
    driver.maximize_window()
    logger.info(f"className is {className}")
    
    try:
        driver.get("https://iaccollege.slack.com")
        logger.info("Opened Slack login page")

        if os.path.exists(COOKIES_FILE):
            try:
                with open(COOKIES_FILE, "rb") as f:
                    cookies = pickle.load(f)
                    for cookie in cookies:
                        try:
                            driver.add_cookie(cookie)
                        except Exception as e:
                            logger.warning(f"Cookie error: {e}")
                driver.refresh()
                logger.info("Loaded session cookies to bypass login.")
                time.sleep(3)
                debug_url = driver.current_url
                logger.info(f"URL after loading cookies and refreshing is: {debug_url}")
                driver.save_screenshot("debug_after_cookies.png")
                logger.info("Saved screenshot as debug_after_cookies.png")
            except Exception as e:
                logger.error(f"Error loading cookies: {e}")
        else:
            logger.warning("No cookies found. Please log in manually.")

        if not os.path.exists(COOKIES_FILE):
            input("Manually log in, then press Enter to continue...")
            with open(COOKIES_FILE, "wb") as f:
                pickle.dump(driver.get_cookies(), f)
            logger.info("Saved session cookies for future logins.")

        admin_url = "https://iaccollege.slack.com/admin/invites"
        driver.get(admin_url)
        logger.info(f"Attempting to navigate to admin invites page: {admin_url}")
        time.sleep(4)
    
        final_url = driver.current_url
        logger.info(f"URL after navigating to admin page is: {final_url}")
        
        screenshot_path = "admin_page_final_view.png"
        driver.save_screenshot(screenshot_path)
        logger.info(f"CRITICAL EVIDENCE screenshot saved to: {screenshot_path}")

        wait = WebDriverWait(driver, 15)

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

        time.sleep(2)

        email_input_div = None
        multi_select_xpath = '(//div[contains(@class, "c-multi_select_input")])[1]'

        try:
            email_input_div = wait.until(EC.presence_of_element_located((By.XPATH, multi_select_xpath)))
        except TimeoutException:
            raise Exception("Could not find the email input field.")

        email_list = emails.split(",") 
        logger.info(f"Processing {len(email_list)} emails")

        input_element = email_input_div.find_element(By.XPATH, ".//div[@contenteditable='true']")
        wait.until(EC.element_to_be_clickable((By.XPATH, ".//div[@contenteditable='true']")))

        input_element.click()
        for email in email_list: 
            email = email.strip()
            if email:
                logger.info(f"Entering email: {email}")
                for char in email:
                    input_element.send_keys(char)
                time.sleep(0.5)
                input_element.send_keys(Keys.ENTER)
                logger.info(f"Entered email: {email}")
                time.sleep(0.2)
        
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
                channels_inp_div = wait.until(EC.element_to_be_clickable((By.XPATH, channels_selector)))
                channels_inp_div.click()
                channels_inp_span = wait.until(EC.visibility_of_element_located(
                    (By.XPATH, "(//div[@role='combobox']//span[contains(@class,'c-multi_select_input__filter_query')])[2]")
                ))
                driver.execute_script("arguments[0].focus();", channels_inp_span)
                for _name in channels_Names_list:
                    channels_inp_span.send_keys(_name)
                    time.sleep(0.5)
                    channels_inp_span.send_keys(Keys.ENTER)
                logger.info("Entered channel name into the input field.")
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
                channels_inp_div = wait.until(EC.element_to_be_clickable((By.XPATH, channels_selector)))
                channels_inp_div.click()
                channels_inp_span = wait.until(EC.visibility_of_element_located(
                    (By.XPATH, "(//div[@role='combobox']//span[contains(@class,'c-multi_select_input__filter_query')])[2]")
                ))
                driver.execute_script("arguments[0].focus();", channels_inp_span)
                for _name in channels_Names_list:
                    channels_inp_span.send_keys(_name)
                    time.sleep(0.5)
                    channels_inp_span.send_keys(Keys.ENTER)
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

        time.sleep(3)
        logger.info("Invitation process completed successfully")
        
        # ✅ שלח מייל רק אחרי הצלחה מוחלטת!
        send_zoho_email(
            subject=f"Slack Invitation SUCCESS - {className}",
            email_body=f"""
ACTION: Slack Invitation Completed Successfully
Class Name: {className}
Emails Invited: {emails}
Channels: {channelsNames}
User Type: {"Member" if isMember == "true" else "Guest"}
Time: {time.strftime('%Y-%m-%d %H:%M:%S')}
Status: SUCCESS
            """,
            action_type="invite"
        )
        
        return "Emails invited successfully."

    except Exception as e:
        logger.error(f"Error occurred: {e}")
        driver.save_screenshot("error_screenshot.png")
        logger.error("Error screenshot saved as 'error_screenshot.png'")
        with open("error_page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        logger.error("Saved page source for debugging.")
        
        # ❌ שלח מייל שגיאה
        send_zoho_email(
            subject=f"Slack Invitation FAILED - {className}",
            email_body=f"""
ACTION: Slack Invitation Failed
Class Name: {className}
Emails: {emails}
Channels: {channelsNames}
Time: {time.strftime('%Y-%m-%d %H:%M:%S')}
Error: {str(e)}
Status: FAILED
            """,
            action_type="error"
        )
        
        raise e
    finally:
        driver.quit()
        logger.info("Browser closed.")

# ========== פונקציה לשינוי רול ==========

def change_user_role_to_member(user_id, user_email):
    """משנה את הרול של משתמש מ-Guest ל-Regular Member"""
    logger.info(f"Starting role change process for user: {user_email} (ID: {user_id})")
    
    load_cookies_from_env()
    
    options = uc.ChromeOptions()
    
    # בדוק איזו מערכת הפעלה - ללא import platform!
    is_linux = os.name != 'nt'  # אם זה לא Windows, זה Linux
    logger.info(f"Running on {'Linux' if is_linux else 'Windows'}")
    
    if is_linux:
        # רק ב-Linux תוסיף את כל האופציות האלו
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-images")
        options.add_argument("--disable-extensions")
        options.add_argument("--single-process")
        options.binary_location = "/usr/bin/google-chrome"
    else:
        # ב-Windows - אל תוסיף כלום מלבד window size!
        logger.info("Running on Windows - using default Chrome settings")
    
    options.add_argument("--window-size=1920,1080")
    
    driver = uc.Chrome(options=options, version_main=140)
    driver.maximize_window()
    
    try:
        driver.get("https://iaccollege.slack.com")
        logger.info("Opened Slack page")
        
        if os.path.exists(COOKIES_FILE):
            try:
                with open(COOKIES_FILE, "rb") as f:
                    cookies = pickle.load(f)
                    for cookie in cookies:
                        try:
                            driver.add_cookie(cookie)
                        except Exception as e:
                            logger.warning(f"Cookie error: {e}")
                driver.refresh()
                logger.info("Loaded session cookies")
                time.sleep(3)
            except Exception as e:
                logger.error(f"Error loading cookies: {e}")
        else:
            logger.error("No cookies found!")
            return {"ok": False, "error": "No authentication cookies available"}
        
        admin_url = "https://iaccollege.slack.com/admin"
        driver.get(admin_url)
        logger.info(f"Navigated to admin page: {admin_url}")
        time.sleep(4)
        
        driver.save_screenshot("admin_page_role_change.png")
        logger.info("Screenshot saved: admin_page_role_change.png")
        
        wait = WebDriverWait(driver, 15)
        
        # חפש את שדה החיפוש
        search_selectors = [
            '//input[@placeholder="Filter by name, email, or ID..."]',
            '//input[contains(@placeholder, "Filter")]',
            '//input[@type="text" and contains(@class, "c-input")]'
        ]
        
        search_input = None
        for selector in search_selectors:
            try:
                search_input = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                logger.info(f"Found search input with selector: {selector}")
                break
            except Exception as e:
                logger.warning(f"Selector {selector} failed: {e}")
                continue
        
        if not search_input:
            raise Exception("Could not find search input field")
        
        # חפש את המשתמש לפי ID
        logger.info(f"Searching for user ID: {user_id}")
        search_input.click()
        search_input.clear()
        
        for char in user_id:
            search_input.send_keys(char)
            time.sleep(0.05)
        
        time.sleep(3)
        driver.save_screenshot("after_search_role.png")
        logger.info("Screenshot saved: after_search_role.png")
        
        # מצא את כפתור ה-3 נקודות
        three_dots_selectors = [
            f'//div[@data-qa-id="{user_id}"]//button[@data-qa="table_row_actions_button"]',
            '//button[@data-qa="table_row_actions_button"]',
            '//button[contains(@class, "c-action_buttons__button")]',
            '//i[contains(@class, "c-icon--ellipsis")]//parent::button',
            '(//button[@aria-haspopup="menu"])[1]'
        ]
        
        three_dots_button = None
        for selector in three_dots_selectors:
            try:
                three_dots_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                logger.info(f"Found 3-dots button with selector: {selector}")
                break
            except Exception as e:
                logger.warning(f"Selector {selector} failed: {e}")
                continue
        
        if not three_dots_button:
            raise Exception("Could not find 3-dots menu button")
        
        three_dots_button.click()
        logger.info("Clicked 3-dots menu button")
        time.sleep(2)
        
        driver.save_screenshot("menu_opened_role.png")
        logger.info("Screenshot saved: menu_opened_role.png")
        
        # לחץ על "Change account type"
        change_type_selectors = [
            '//button[contains(text(), "Change account type")]',
            '//div[contains(text(), "Change account type")]',
            '//span[contains(text(), "Change account type")]',
            '//button[@role="menuitem"]',
            '(//div[@role="menu"]//button)[1]'
        ]
        
        change_type_button = None
        for selector in change_type_selectors:
            try:
                change_type_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                logger.info(f"Found 'Change account type' with selector: {selector}")
                break
            except Exception as e:
                logger.warning(f"Selector {selector} failed: {e}")
                continue
        
        if not change_type_button:
            raise Exception("Could not find 'Change account type' button")
        
        change_type_button.click()
        logger.info("Clicked 'Change account type' button")
        time.sleep(2)
        
        driver.save_screenshot("change_type_dialog_role.png")
        logger.info("Screenshot saved: change_type_dialog_role.png")
        
        # בחר ב-"Regular Member" - פשוט מאוד לפי ה-HTML!
        member_radio_selectors = [
            '//input[@id="change-account-type-member"]',  # הכי מדויק לפי ה-HTML שלך!
            '//input[@value="MEMBER"]',  # לפי value
            '//label[contains(text(), "Regular Member")]//input',
            '(//input[@type="radio"])[1]'  # Regular Member הוא הראשון
        ]
        
        member_radio = None
        for selector in member_radio_selectors:
            try:
                member_radio = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                logger.info(f"Found 'Regular Member' radio with selector: {selector}")
                break
            except Exception as e:
                logger.warning(f"Selector {selector} failed: {e}")
                continue
        
        if not member_radio:
            raise Exception("Could not find 'Regular Member' radio button")
        
        # לחץ על הרדיו בוטון
        driver.execute_script("arguments[0].click();", member_radio)
        logger.info("Selected 'Regular Member'")
        time.sleep(3)  # ✅ המתנה של 3 שניות אחרי בחירת הרדיו
        
        driver.save_screenshot("member_selected_role.png")
        logger.info("Screenshot saved: member_selected_role.png")
        
        # ✅ לחץ על כפתור "Save" (לא "Next"!)
        save_button_selectors = [
            '//button[@data-qa="change_account_type_save_btn"]',  # ✅ הכי מדויק!
            '//button[@aria-label="Save"]',
            '//button[contains(text(), "Save")]',
            '//button[contains(@class, "c-button--primary") and @type="button"]'
        ]
        
        save_button = None
        for selector in save_button_selectors:
            try:
                save_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                logger.info(f"Found 'Save' button with selector: {selector}")
                break
            except Exception as e:
                logger.warning(f"Selector {selector} failed: {e}")
                continue
        
        if not save_button:
            raise Exception("Could not find 'Save' button")
        
        # ✅ נסה ללחוץ עם JavaScript אם הכפתור חסום
        try:
            save_button.click()
            logger.info("Clicked 'Save' button")
        except Exception as e:
            logger.warning(f"Regular click failed, trying JavaScript click: {e}")
            driver.execute_script("arguments[0].click();", save_button)
            logger.info("Clicked 'Save' button using JavaScript")
        
        time.sleep(4)  # ✅ המתנה לאחר השמירה
        
        driver.save_screenshot("role_changed_success.png")
        logger.info("Screenshot saved: role_changed_success.png")
        
        logger.info(f"Successfully changed role for user: {user_email}")
        
        # ✅ שלח מייל רק אחרי הצלחה מוחלטת!
        send_zoho_email(
            subject=f"Role Change SUCCESS - {user_email}",
            email_body=f"""
ACTION: Role Change Completed Successfully
User Email: {user_email}
User ID: {user_id}
Previous Role: Guest
New Role: Regular Member
Time: {time.strftime('%Y-%m-%d %H:%M:%S')}
Status: SUCCESS
            """,
            action_type="role_change"
        )
        
        return {"ok": True, "message": f"User {user_email} upgraded to Regular Member"}
        
    except Exception as e:
        logger.error(f"Error occurred during role change: {e}")
        
        # נסה לצלם screenshot רק אם הדפדפן עדיין חי
        try:
            driver.save_screenshot("error_role_change.png")
            logger.error("Error screenshot saved")
        except:
            logger.error("Could not save screenshot - browser might be closed")
        
        # נסה לשמור page source רק אם הדפדפן עדיין חי
        try:
            with open("error_page_source_role.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            logger.error("Saved page source for debugging")
        except:
            logger.error("Could not save page source - browser might be closed")
        
        # ❌ שלח מייל שגיאה
        send_zoho_email(
            subject=f"Role Change FAILED - {user_email}",
            email_body=f"""
ACTION: Role Change Failed
User Email: {user_email}
User ID: {user_id}
Target Role: Regular Member
Time: {time.strftime('%Y-%m-%d %H:%M:%S')}
Error: {str(e)}
Status: FAILED
            """,
            action_type="error"
        )
        
        return {"ok": False, "error": str(e)}
    
    finally:
        try:
            driver.quit()
            logger.info("Browser closed")
        except:
            logger.info("Browser was already closed")


# ========== REST ENDPOINTS ==========

@app.route('/invite', methods=['POST'])
def invite():
    logger.info(f"Received invitation request from {request.remote_addr}")
    
    try:
        data = request.get_json()
        logger.info(f"Request data: {data}")
        
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
        
        if not isinstance(emails, str) or not isinstance(className, str):
            logger.warning("Invalid input: 'emails' or 'className' is not a string.")
            return jsonify({"error": "'emails' and 'className' must be strings.", "ok": False}), 400

        logger.info(f"Processing Slack invitation for: {emails}")
        
        slack_result = invite_emails(emails, channelsNames, isMember, className)
        logger.info(f"Slack invitation result: {slack_result}")
        
        zoho_api_res = "Not a single email, Zoho call skipped."
        
        trimmed_emails = emails.strip()
        if not (',' in trimmed_emails or ';' in trimmed_emails or ' ' in trimmed_emails):
            if trimmed_emails:
                logger.info(f"Detected single email '{trimmed_emails}'. Processing additional ZOHO notification.")
                zoho_api_res = send_zoho_email(
                    subject=f"New Single Student Registration - {className}",
                    email_body=f"""
Email: {trimmed_emails}
ClassName: {className}
                    """,
                    action_type="general"
                )
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

@app.route('/change-role', methods=['POST'])
def change_role():
    """
    Endpoint לשינוי רול של משתמש
    Expected JSON: {"user_id": "U123456", "user_email": "user@example.com", "is_member": true}
    """
    logger.info(f"Received role change request from {request.remote_addr}")
    
    try:
        data = request.get_json()
        logger.info(f"Request data: {data}")
        
        if not data:
            return jsonify({"error": "No JSON data provided", "ok": False}), 400
        
        required_fields = ['user_id', 'user_email', 'is_member']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing '{field}' field", "ok": False}), 400
        
        user_id = data['user_id']
        user_email = data['user_email']
        is_member = data['is_member']
        
        # רק אם is_member == true
        if is_member != True:
            logger.info(f"User {user_email} should not be a member (is_member={is_member}). Skipping role change.")
            
            return jsonify({
                "ok": True,
                "message": "User should not be a member. No action taken.",
                "skipped": True
            })
        
        logger.info(f"Processing role change for user: {user_email} (ID: {user_id})")
        
        result = change_user_role_to_member(user_id, user_email)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error processing role change: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e), "ok": False}), 500

@app.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "running", "ok": True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Flask server on 0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)