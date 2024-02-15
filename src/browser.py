"""
Contains Browser class that maintains all functions related to browsers.
"""

import json
import os
import re
import shutil
import time

import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager


class Browser:
    """
    Setup and Create a browser with proper cookies.
    Has helper functions for loading webpages and downloading files.
    """

    def __init__(self):
        if not os.path.exists("config.json"):
            browser = input("Enter the browser that you want to use(firefox/chrome):")
            if browser.lower() == "firefox":
                self.setupFirefox()
            if browser.lower() == "chrome":
                self.setupChrome()

        with open("config.json", "r", encoding="utf-8") as f:
            self.config = json.loads(f.read())

        if self.config["browser"] == "Firefox":
            self.browser = self.createFirefox()
        if self.config["browser"] == "Chrome":
            self.browser = self.createChrome()

        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0",
            "Connection": "keep-alive",
        }
        self.cookie = {}

    def setupFirefox(self):
        """
        Setup configuration for Firefox by user input.
        """
        profileDir = input("Enter the profile directory:")
        data = {"browser": "Firefox", "profile": profileDir}
        with open("config.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=4))

    def setupChrome(self):
        """
        Setup configuration for Chrome by user input.
        """
        profileDir = input("Enter the user data directory:")
        profileName = input("Enter the profile name:")
        data = {"browser": "Chrome", "user-data-dir": profileDir, "profile": profileName}
        with open("config.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=4))

    def createFirefox(self):
        """
        Creates a firefox browser with temp profile.
        """
        print("Creating a temperory profile.")
        profile = self.config["profile"]
        profileDir = "/".join(profile.split("/")[:-1])
        self.tempProfile = os.path.join(profileDir, "temp")
        if os.path.exists(self.tempProfile):
            shutil.rmtree(self.tempProfile)
        os.mkdir(self.tempProfile)
        shutil.copy(os.path.join(profile, "cookies.sqlite"), self.tempProfile)

        print("Opening browser.")
        options = webdriver.FirefoxOptions()
        options.add_argument("-profile")
        options.add_argument(self.tempProfile)
        options.add_argument("-headless")
        service = FirefoxService(GeckoDriverManager().install(), log_output="browser.log")
        browser = webdriver.Firefox(options=options, service=service)
        return browser

    def createChrome(self):
        """
        Creates a chrome browser with temp profile.
        """
        print("Creating a temperory profile.")
        userDataDir = self.config["user-data-dir"]
        profile = os.path.join(userDataDir, self.config["profile"])
        self.tempProfile = os.path.join(userDataDir, "temp")
        if os.path.exists(self.tempProfile):
            shutil.rmtree(self.tempProfile)
        os.mkdir(self.tempProfile)
        shutil.copy(os.path.join(profile, "cookies.sqlite"), self.tempProfile)

        print("Opening browser.")
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        options.add_argument(f"--user-data-dir={userDataDir}")
        options.add_argument("--profile-directory=temp")
        service = ChromeService(ChromeDriverManager().install(), log_output="browser.log")
        browser = webdriver.Chrome(service=service, options=options)
        return browser

    def login(self, url: str) -> str:
        """
        Login to moodle, save relavent cookies and return moodle home page.
        """
        print("Loging in to Moodle.")
        self.browser.get(url)
        button = self.browser.find_element(value="sso-widget")
        button.click()
        time.sleep(2)
        cookie = self.browser.get_cookies()
        self.cookie = {i["name"]: i["value"] for i in cookie}
        page = self.browser.page_source
        return page

    def get(self, url: str):
        """
        Load the url with parsed cookies and header and return page content
        """
        res = requests.get(url, cookies=self.cookie, headers=self.header, timeout=12)
        return res.content

    def download(self, url: str, loc: str):
        """
        Download the content of url to specified location
        """
        res = requests.get(url, cookies=self.cookie, headers=self.header, timeout=30)
        try:
            name = re.search(r'filename="(.*)"', res.headers["Content-Disposition"]).group(1)
            with open(os.path.join(loc, name), "wb") as f:
                f.write(res.content)
        except KeyError:
            print("Not Downloadable file.")

    def __enter__(self):
        return self

    def __exit__(self, excType, excValue, excTraceback):
        """
        Close the browser and delete temp profile
        """
        print("Closing the browser.")
        self.browser.close()
        shutil.rmtree(self.tempProfile)
