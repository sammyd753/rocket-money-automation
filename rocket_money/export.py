"""Export functions for Rocket Money transactions."""

import time
import undetected_chromedriver as uc
from config import ROCKET_DATE_RANGE_MAP, ROCKET_DATE_SELECT
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from rocket_money.driver import get_chrome_options
from rocket_money.auth import handle_login_form, handle_2fa
from utils.logger import log
from utils.selenium_helpers import wait_and_click


def navigate_and_export_transactions(driver, wait):
    """Navigate to transactions page and export filtered data.
    
    Args:
        driver: Selenium WebDriver instance
        wait: WebDriverWait instance
    """
    # Wait for login and navigate to transactions
    log("Waiting for login to complete...")
    time.sleep(2.5)  # Increased wait time for login
    
    log("Navigating to transactions page...")
    driver.get("https://app.rocketmoney.com/transactions")
    time.sleep(2.5)  # Increased wait time for page load
    
    # DEBUG: Print all button texts on the page
    log('--- DEBUG: Listing all button texts on the page ---')
    buttons = driver.find_elements(By.TAG_NAME, 'button')
    for idx, b in enumerate(buttons):
        log(f'Button {idx}: {repr(b.text)}')
    log('--- END DEBUG BUTTON LIST ---')
    
    # 1. Click All dates button
    log("Clicking All dates button...")
    wait_and_click(
        driver, 
        wait, 
        "//button[contains(normalize-space(.), 'All dates')]",
        "/html/body/div[1]/main/div/div/div[1]/div/div[1]/header/div/div/div[2]/div/div[1]/div/button",
        "Failed to click All dates button"
    )
    
    time.sleep(0.5)  # Wait for dropdown
    
    # 2. Select date range based on config
    date_range_index, date_range_text = ROCKET_DATE_RANGE_MAP[ROCKET_DATE_SELECT]
    log(f"Selecting {date_range_text}...")
    wait_and_click(
        driver,
        wait,
        f"//li[contains(normalize-space(.), '{date_range_text}')]",
        f"/html/body/div[1]/main/div/div/div[3]/div/div/div/div/li[3]",
        f"Failed to select {date_range_text}"
    )
    
    time.sleep(0.5)  # Wait for filter to apply
    
    # 3. Click All Categories button
    log("Clicking All Categories button...")
    wait_and_click(
        driver,
        wait,
        "//button[contains(normalize-space(.), 'All categories')]",
        "/html/body/div[1]/main/div/div/div[1]/div/div[1]/header/div/div/div[2]/div/div[2]/div/button",
        "Failed to click All Categories button"
    )
    
    time.sleep(0.5)  # Wait for dropdown
    
    # 4. Select Piano Income category
    log("Selecting Piano Income category...")
    wait_and_click(
        driver,
        wait,
        "//li[contains(normalize-space(.), 'Piano Income')]",
        "/html/body/div[1]/main/div/div/div[4]/div/div/div/ul/li[4]",
        "Failed to select Piano Income category"
    )
    
    time.sleep(0.5)  # Wait for filter to apply
    
    # 5. Click "Export selected transactions" button (first button with icon)
    log("Clicking 'Export selected transactions' button...")
    try:
        # Try to find button by aria-label first
        export_selected_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Export selected transactions']"))
        )
        export_selected_button.click()
        log("Clicked 'Export selected transactions' button")
        time.sleep(1.5)  # Wait for the export modal to appear
    except Exception as e:
        log(f"Error clicking 'Export selected transactions' button: {str(e)}", "error")
        driver.save_screenshot("export_selected_error.png")
        raise
    
    # 6. Click CSV format option in the modal
    log("Looking for CSV format option...")
    try:
        # The CSV button has aria-label="Export selected transactions" and contains an SVG with CSV icon
        # We need to find it in the modal (not the original button we just clicked)
        # Look for button with CSV icon SVG (the path contains "M20 13V8.41421" which is unique to CSV icon)
        csv_selectors = [
            # Look for button with CSV icon SVG path in modal/dialog context
            "//div[contains(@role, 'dialog')]//button[@aria-label='Export selected transactions' and .//svg//path[contains(@d, 'M20 13V8.41421')]]",
            # Alternative: look for button with the CSV icon in modal context (any modal structure)
            "//div[contains(@role, 'dialog')]//button[@aria-label='Export selected transactions']",
            # Fallback: look for any button with CSV icon SVG (should be in modal after we clicked export)
            "//button[.//svg//path[contains(@d, 'M20 13V8.41421')]]",
            # Last resort: any button with aria-label in a dialog/modal
            "(//div[contains(@role, 'dialog')] | //div[contains(@class, 'modal')] | //div[contains(@class, 'dialog')])//button[@aria-label='Export selected transactions']",
        ]
        
        csv_clicked = False
        for selector in csv_selectors:
            try:
                log(f"Trying CSV selector: {selector}")
                csv_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                csv_button.click()
                log("Clicked CSV format option")
                csv_clicked = True
                time.sleep(0.5)  # Wait for CSV selection to register
                break
            except Exception as e:
                log(f"CSV selector failed: {selector} - {str(e)}")
                continue
        
        if not csv_clicked:
            log("WARNING: Could not find CSV button. Taking screenshot for debugging...", "error")
            driver.save_screenshot("csv_button_not_found.png")
            # Continue anyway - maybe CSV is default or the modal structure changed
    except Exception as e:
        log(f"Error clicking CSV format option: {str(e)}", "error")
        driver.save_screenshot("csv_selection_error.png")
        # Don't raise - continue to try export button anyway
    
    # 7. Wait for and click the actual export confirmation button
    log("Waiting for export confirmation button...")
    try:
        # The export button has aria-label like "Export 12 transactions" (number varies)
        # It contains "Export" and "transactions" but NOT "selected"
        export_selectors = [
            # Button with aria-label starting with "Export" and containing "transactions" but not "selected"
            "//button[starts-with(@aria-label, 'Export') and contains(@aria-label, 'transactions') and not(contains(@aria-label, 'selected'))]",
            # Alternative: button with text starting with "Export" and containing "transactions"
            "//button[starts-with(text(), 'Export') and contains(text(), 'transactions')]",
        ]
        
        export_clicked = False
        for selector in export_selectors:
            try:
                log(f"Trying export button selector: {selector}")
                # Use shorter timeout for each attempt since we're trying multiple
                confirm_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                time.sleep(0.5)  # Short wait to ensure button is ready
                log("Clicking export confirmation button...")
                confirm_button.click()
                log("Export confirmation clicked")
                export_clicked = True
                break
            except Exception as e:
                log(f"Export selector failed: {selector} - {str(e)}")
                continue
        
        if not export_clicked:
            # Try fallback xpath
            try:
                log("Trying fallback xpath for export confirmation button...")
                confirm_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "/html/body/div[5]/div/div/div/div[2]/button"))
                )
                confirm_button.click()
                log("Export confirmation clicked (fallback)")
            except Exception as e2:
                log(f"Fallback also failed: {str(e2)}", "error")
                driver.save_screenshot("export_confirm_error.png")
                raise
    except Exception as e:
        log(f"Error clicking export confirmation: {str(e)}", "error")
        driver.save_screenshot("export_confirm_error.png")
        raise
    
    log(f"Export request submitted for Piano Income transactions from {date_range_text}.")
    time.sleep(0.1)  # Wait for export to initiate


def export_rocket_money_data():
    """Main function to export Rocket Money data.
    
    Handles authentication, navigation, and export of transactions.
    """
    log("Starting Rocket Money export...")
    
    driver = None
    try:
        log("Initializing Chrome driver...")
        options = get_chrome_options()
        driver = uc.Chrome(options=options)
        wait = WebDriverWait(driver, 20)
        
        # Login to Rocket Money
        log("Navigating to Rocket Money app...")
        driver.get("https://app.rocketmoney.com")
        time.sleep(2)  # Wait for initial page load and redirect
        
        # Log the current URL to verify we're on the right page
        current_url = driver.current_url
        log(f"Current URL: {current_url}")

        # Check if we are already logged in by verifying if we have reached the expected logged-in URL
        logged_in_url = "https://app.rocketmoney.com/"  # Replace with your actual logged-in page URL
        if driver.current_url.startswith(logged_in_url):
            log("Already logged in. Skipping 2FA.")
            return navigate_and_export_transactions(driver, wait)

        # Check if we need to log in
        try:
            # More robust login detection - try multiple selectors that indicate login is needed
            login_indicators = [
                # "input[name='username']",
                # "input[name='email']", 
                "input[type='email']",
                # "input[placeholder*='email']",
                # "input[placeholder*='Email']",
                # "input[placeholder*='username']",
                # "input[placeholder*='Username']",
                # "input[id*='username']",
                # "input[id*='email']",
                # "input[type='text'][placeholder*='email']",
                # "input[type='text'][placeholder*='Email']"
            ]
            
            login_required = False
            for selector in login_indicators:
                try:
                    log(f"Checking for login field with selector: {selector}")
                    username_field = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if username_field:
                        log(f"Found login field with selector: {selector}")
                        login_required = True
                        break
                except TimeoutException:
                    continue
            
            if login_required:
                log("Login required, proceeding with authentication...")
                handle_login_form(driver, wait)
                handle_2fa(driver, wait)
            else:
                # Additional check: look for common logged-in page indicators
                logged_in_indicators = [
                    "//a[contains(text(), 'Transactions')]",
                    "//a[contains(text(), 'Dashboard')]",
                    "//button[contains(text(), 'Export')]",
                    "//div[contains(@class, 'dashboard')]",
                    "//div[contains(@class, 'transactions')]"
                ]
                
                logged_in = False
                for xpath in logged_in_indicators:
                    try:
                        element = driver.find_element(By.XPATH, xpath)
                        if element:
                            log(f"Found logged-in indicator: {xpath}")
                            logged_in = True
                            break
                    except:
                        continue
                
                if logged_in:
                    log("Already logged in, skipping authentication...")
                else:
                    log("Could not determine login status, taking debug screenshot...")
                    driver.save_screenshot("login_status_unknown.png")
                    log("Debug screenshot saved as login_status_unknown.png")
                    
                    # Log some page information for debugging
                    try:
                        page_title = driver.title
                        current_url = driver.current_url
                        log(f"Page title: {page_title}")
                        log(f"Current URL: {current_url}")
                        
                        # Look for any input fields on the page
                        input_fields = driver.find_elements(By.TAG_NAME, "input")
                        log(f"Found {len(input_fields)} input fields on the page")
                        for i, field in enumerate(input_fields[:5]):  # Log first 5 fields
                            try:
                                field_type = field.get_attribute("type")
                                field_name = field.get_attribute("name")
                                field_id = field.get_attribute("id")
                                field_placeholder = field.get_attribute("placeholder")
                                log(f"Input field {i}: type={field_type}, name={field_name}, id={field_id}, placeholder={field_placeholder}")
                            except:
                                log(f"Input field {i}: could not get attributes")
                    except Exception as e:
                        log(f"Error getting page debug info: {str(e)}")
                    
                    log("Attempting login anyway...")
                    handle_login_form(driver, wait)
                    handle_2fa(driver, wait)
                    
        except Exception as e:
            log(f"Error during login detection: {str(e)}", "error")
            # Take screenshot for debugging
            driver.save_screenshot("login_detection_error.png")
            log("Login detection error screenshot saved as login_detection_error.png")
            # Attempt login anyway as fallback
            log("Attempting login as fallback...")
            handle_login_form(driver, wait)
            handle_2fa(driver, wait)

        # Navigate to transactions page and export data
        navigate_and_export_transactions(driver, wait)
        
    except Exception as e:
        log(f"Error during Rocket Money export: {str(e)}", "error")
        if driver:
            try:
                screenshot_path = "error_screenshot.png"
                driver.save_screenshot(screenshot_path)
                log(f"Error screenshot saved to {screenshot_path}")
            except:
                pass
        raise
    finally:
        log(f"Quitting driver...")
        if driver:
            driver.quit()

