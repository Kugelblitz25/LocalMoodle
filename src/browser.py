"""
Contains browser classes for Firefox and Chrome with proper inheritance structure.
"""
import os
import re
import shutil
import time
import requests
from abc import ABC, abstractmethod
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager


class BaseBrowser(ABC):
    """
    Abstract base class for browser implementations.
    """
    
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0",
        "Connection": "keep-alive",
    }
    
    def __init__(self):
        self.browser = None
        self.tempProfile = None
        self.header = self.DEFAULT_HEADERS.copy()
        self.cookie: dict[str, str] = {}

    @abstractmethod
    def setup(self) -> dict[str, str]:
        """Setup configuration for the browser."""
        pass
    
    @abstractmethod
    def create_browser(self, config: dict[str, str]) -> None:
        """Create and return browser instance."""
        pass
    
    def login(self, url: str) -> str:
        """
        Login to moodle, save relevant cookies and return moodle home page.
        """
        print("Logging in to Moodle.")
        self.browser.get(url)
        button = self.browser.find_element(value="sso-widget")
        button.click()
        time.sleep(2)
        cookie = self.browser.get_cookies()
        self.cookie = {i["name"]: i["value"] for i in cookie}
        page = self.browser.page_source
        return page
    
    def get(self, url: str) -> bytes:
        """
        Load the url with parsed cookies and header and return page content
        """
        res = requests.get(url, cookies=self.cookie, headers=self.header, timeout=12)
        return res.content
    
    def download(self, url: str, loc: str) -> bool:
        """
        Download the content of url to specified location
        """
        try:
            if not os.path.exists(loc):
                os.makedirs(loc, exist_ok=True)
                
            res = requests.get(
                url, 
                cookies=self.cookie, 
                headers=self.header, 
                timeout=30,
                stream=True
            )
            res.raise_for_status()
            
            try:
                filename = re.search(
                    r'filename="(.*)"', res.headers["Content-Disposition"]
                ).group(1)
            except (KeyError, AttributeError):
                filename = "downloaded_file"
            
            filepath = os.path.join(loc, filename)
            with open(filepath, "wb") as f:
                for chunk in res.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"Downloaded: {filename}")
            return True
            
        except requests.RequestException as e:
            print(f"Download failed: {e}")
            return False
        
        except OSError as e:
            print(f"File system error: {e}")
            return False
    
    def __enter__(self):
        return self

    def __exit__(self, *_):
        """
        Close the browser and delete temp profile
        """
        try:
            if self.browser:
                print("Closing the browser.")
                self.browser.quit()
        except Exception as e:
            print(f"Error closing browser: {e}")
        
        try:
            if self.tempProfile and os.path.exists(self.tempProfile):
                shutil.rmtree(self.tempProfile)
                print("Temporary profile cleaned up.")
        except Exception as e:
            print(f"Error cleaning up temp profile: {e}")


class FirefoxBrowser(BaseBrowser):
    """
    Firefox browser implementation.
    """

    def setup(self) -> dict[str, str]:
        """
        Setup configuration for Firefox by user input.
        """
        while True:
            profileDir = input("Enter the Firefox profile directory: ").strip()
            if os.path.exists(profileDir) and os.path.isdir(profileDir):
                break
            print("Invalid directory. Please enter a valid path.")
        
        return {"browser": "Firefox", "profile": profileDir}

    def create_browser(self, config: dict[str, str]):
        """
        Creates a Firefox browser with temp profile.
        """
        try:
            print("Creating a temporary Firefox profile.")
            profile = config["profile"]
            
            if not os.path.exists(profile):
                raise FileNotFoundError(f"Profile directory not found: {profile}")
            
            profileDir = os.path.dirname(profile)
            self.tempProfile = os.path.join(profileDir, "temp")
            
            if os.path.exists(self.tempProfile):
                shutil.rmtree(self.tempProfile)
            os.makedirs(self.tempProfile, exist_ok=True)
            
            cookies_path = os.path.join(profile, "cookies.sqlite")
            if os.path.exists(cookies_path):
                shutil.copy(cookies_path, self.tempProfile)
            
            print("Opening Firefox browser.")
            options = webdriver.FirefoxOptions()
            options.add_argument("-profile")
            options.add_argument(self.tempProfile)
            options.add_argument("-headless")
            
            service = FirefoxService(
                GeckoDriverManager().install(), 
                log_output=os.devnull
            )
            self.browser = webdriver.Firefox(options=options, service=service)
            
        except Exception as e:
            print(f"Failed to create Firefox browser: {e}")
            if self.tempProfile and os.path.exists(self.tempProfile):
                shutil.rmtree(self.tempProfile)
            raise


class ChromeBrowser(BaseBrowser):
    """
    Chrome browser implementation.
    """
    
    def setup(self) -> dict[str, str]:
        """
        Setup configuration for Chrome by user input.
        """
        while True:
            userDataDir = input("Enter the Chrome user data directory: ").strip()
            if os.path.exists(userDataDir) and os.path.isdir(userDataDir):
                break
            print("Invalid directory. Please enter a valid path.")
        
        profileName = input("Enter the profile name: ").strip()
        
        return {
            "browser": "Chrome",
            "user-data-dir": userDataDir,
            "profile": profileName,
        }

    def create_browser(self, config: dict[str, str]) -> None:
        """
        Creates a Chrome browser with temp profile.
        """
        try:
            print("Creating a temporary Chrome profile.")
            userDataDir = config["user-data-dir"]
            profile = os.path.join(userDataDir, config["profile"])
            self.tempProfile = os.path.join(userDataDir, "temp")
            
            if os.path.exists(self.tempProfile):
                shutil.rmtree(self.tempProfile)
            os.makedirs(self.tempProfile, exist_ok=True)
            
            cookies_path = os.path.join(profile, "cookies.sqlite")
            if os.path.exists(cookies_path):
                shutil.copy(cookies_path, self.tempProfile)
            
            print("Opening Chrome browser.")
            options = webdriver.ChromeOptions()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_experimental_option("excludeSwitches", ["enable-logging"])
            options.add_argument(f"--user-data-dir={userDataDir}")
            options.add_argument("--profile-directory=temp")
            
            service = ChromeService(
                ChromeDriverManager().install(), 
                log_output=os.devnull
            )
            self.browser = webdriver.Chrome(service=service, options=options)
            
        except Exception as e:
            print(f"Failed to create Chrome browser: {e}")
            if self.tempProfile and os.path.exists(self.tempProfile):
                shutil.rmtree(self.tempProfile)
            raise
