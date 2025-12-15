"""Chrome driver configuration for Rocket Money automation."""

import os
import undetected_chromedriver as uc


def get_chrome_options():
    """Configure Chrome options with user data persistence.
    
    Returns:
        uc.ChromeOptions: Configured Chrome options
    """
    options = uc.ChromeOptions()
    options.add_argument('--start-maximized')
    
    # Set up user data directory for session persistence
    user_data_dir = os.path.join(os.getcwd(), 'chrome_user_data')
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)
    options.add_argument(f'--user-data-dir={user_data_dir}')
    options.add_argument('--profile-directory=Default')
    
    return options

