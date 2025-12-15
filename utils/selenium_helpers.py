"""Selenium helper utilities for web automation."""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from utils.logger import log


def wait_and_click(driver, wait, text_pattern, fallback_xpath, error_msg, retries=3):
    """Helper function to wait for and click elements with retry logic and fallback xpath.
    
    Args:
        driver: Selenium WebDriver instance
        wait: WebDriverWait instance
        text_pattern: Primary XPath pattern to find element
        fallback_xpath: Fallback XPath if primary pattern fails
        error_msg: Error message to log if all attempts fail
        retries: Number of retry attempts (default: 3)
        
    Returns:
        bool: True if click was successful, False otherwise
        
    Raises:
        TimeoutException: If element cannot be found after all retries
        ElementClickInterceptedException: If element cannot be clicked after all retries
    """
    for attempt in range(retries):
        try:
            try:
                # If text_pattern fails, try fallback xpath
                element = wait.until(EC.element_to_be_clickable((By.XPATH, text_pattern)))
                element.click()
                return True
            except:
                # Try fallback xpath first
                log(f"Primary text_pattern failed, trying fallback for: {error_msg}")
                element = wait.until(EC.element_to_be_clickable((By.XPATH, fallback_xpath)))
                element.click()
                return True
        except (TimeoutException, ElementClickInterceptedException) as e:
            if attempt == retries - 1:
                log(f"{error_msg}: {str(e)}", "error")
                raise
            time.sleep(2)
    return False

