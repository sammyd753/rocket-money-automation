"""Authentication functions for Rocket Money."""

import time
from config import ROCKET_USER, ROCKET_PASS
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, InvalidElementStateException
from utils.logger import log


def handle_login_form(driver, wait):
    """Handle the login form submission.
    
    Args:
        driver: Selenium WebDriver instance
        wait: WebDriverWait instance
    """
    log("Waiting for login form...")
    try:
        # Try multiple selectors for the login form
        selectors = [
            # "input[name='username']",
            # "input[name='email']",
            "input[type='email']"
            # "input[placeholder*='email']",
            # "input[placeholder*='Email']",
            # "input[placeholder*='username']",
            # "input[placeholder*='Username']",
            # "input[id*='username']",
            # "input[id*='email']",
            # "input[type='text'][placeholder*='email']",
            # "input[type='text'][placeholder*='Email']"
        ]
        
        username_field = None
        for selector in selectors:
            try:
                log(f"Trying selector: {selector}")
                username_field = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if username_field:
                    log(f"Found username field with selector: {selector}")
                    break
            except:
                continue
        
        if not username_field:
            raise Exception("Could not find username field with any selector")
        
        # Take a screenshot before entering credentials
        driver.save_screenshot("before_login.png")
        log("Screenshot saved as before_login.png")
        
        # Clear fields first
        username_field.clear()
        time.sleep(0.5)
        
        # Type credentials
        for char in ROCKET_USER:
            username_field.send_keys(char)
        time.sleep(0.5)
        
        # Try to find password field
        password_selectors = [
            # "input[name='password']",
            "input[type='password']",
            # "input[placeholder*='password']",
            # "input[placeholder*='Password']",
            # "input[id*='password']"
        ]
        
        password_field = None
        for selector in password_selectors:
            try:
                log(f"Trying password selector: {selector}")
                password_field = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if password_field:
                    log(f"Found password field with selector: {selector}")
                    break
            except:
                continue
        
        if not password_field:
            raise Exception("Could not find password field with any selector")
        
        password_field.clear()
        time.sleep(0.5)
        
        for char in ROCKET_PASS:
            password_field.send_keys(char)
        time.sleep(0.5)
        
        # Try to find login button
        button_selectors = [
            "button[type='submit']",
            "button:contains('Sign in')",
            "button:contains('Log in')",
            "button:contains('Login')",
            "button:contains('Sign In')",
            "button:contains('Log In')",
            "input[type='submit']",
            "button[class*='login']",
            "button[class*='signin']",
            "button[id*='login']",
            "button[id*='signin']"
        ]
        
        login_button = None
        for selector in button_selectors:
            try:
                log(f"Trying button selector: {selector}")
                login_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                if login_button:
                    log(f"Found login button with selector: {selector}")
                    break
            except:
                continue
        
        if not login_button:
            raise Exception("Could not find login button with any selector")
        
        login_button.click()
        
    except Exception as e:
        log(f"Error during login form interaction: {str(e)}", "error")
        # Take screenshot on error
        driver.save_screenshot("login_error.png")
        log("Error screenshot saved as login_error.png")
        raise


def handle_2fa(driver, wait):
    """Handle 2-factor authentication flow.
    
    Args:
        driver: Selenium WebDriver instance
        wait: WebDriverWait instance
    """
    log("Waiting for 2-factor authentication...")
    
    try:
        # Check if we are already logged in by verifying if we have reached the expected logged-in URL
        logged_in_url = "https://app.rocketmoney.com/"  # Replace with your actual logged-in page URL
        if driver.current_url.startswith(logged_in_url):
            log("Already logged in. Skipping 2FA.")
            return  # Exit gracefully
        
        # Wait for the 2FA input field
        twofa_field = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
        )
        log("Found 2FA input field")
        
        # Clear the field first
        twofa_field.clear()
        time.sleep(1)
        
        # Get 2FA code from user
        twofa_code = input("Please enter the 2FA code sent to your device: ")
        
        # Type the code with small delays
        for char in twofa_code:
            twofa_field.send_keys(char)
            time.sleep(0.1)
        time.sleep(0.5)
        
        # Find and click the verify button
        verify_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
        )
        verify_button.click()
        log("2FA code submitted")
        
        # Wait for 2FA verification
        time.sleep(2)
    
    except TimeoutException:
        log("2FA input field not found, assuming already logged in. Skipping 2FA.")
        return  # Gracefully exit if 2FA is not required
    
    except InvalidElementStateException:
        log("2FA field exists but is not interactable. Assuming already logged in.")
        return  # Exit gracefully
    
    except Exception as e:
        log(f"Error during 2FA: {str(e)}", "error")
        driver.save_screenshot("2fa_error.png")
        log("2FA error screenshot saved as 2fa_error.png")
        raise


def authenticate(driver, wait):
    """Orchestrate the complete authentication flow (login + 2FA).
    
    Args:
        driver: Selenium WebDriver instance
        wait: WebDriverWait instance
    """
    handle_login_form(driver, wait)
    handle_2fa(driver, wait)

