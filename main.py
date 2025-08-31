"""
Main application file with browser selection moved here.
"""
import time
import os
import json
from src.browser import FirefoxBrowser, ChromeBrowser
from src.moodle import Moodle


BROWSER_CONFIG = "config.json"


def main():
    """
    Main function with browser choice handling.
    """
    
    print("Moodle Downloader")
    print("-" * 20)

    browser_choice = None

    if os.path.exists(BROWSER_CONFIG):
        with open(BROWSER_CONFIG, "r") as f:
            config = json.load(f)
            browser_choice = config.get("browser", None)

    if browser_choice is None:
        while True:
            choice = input("Select browser (1 for Firefox, 2 for Chrome): ").strip()
            if choice == "1":
                browser_choice = "firefox"
                break
            elif choice == "2":
                browser_choice = "chrome"
                break
            else:
                print("Invalid choice. Please enter 1 or 2.")

    if browser_choice == "firefox":
        browser = FirefoxBrowser()
    elif browser_choice == "chrome":
        browser = ChromeBrowser()

    if not os.path.exists(BROWSER_CONFIG):
        config = browser.setup()
        config["browser"] = browser_choice
        with open(BROWSER_CONFIG, "w") as f:
            json.dump(config, f, indent=4)

    t1 = time.perf_counter()
    
    try:
        with browser:
            print("Browser created successfully.")
            moodle = Moodle(6)
            moodle.getCourses(browser)
            moodle.downloadAll()
            
        print("Download completed successfully.")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        t2 = time.perf_counter()
        print(f"Total time: {t2 - t1:.2f} seconds")


if __name__ == "__main__":
    main()