"""
This module contains the Moodle class that parse moodle.iitb.ac.in to
download all the documents and posts
"""

import concurrent.futures
import json
import os
import shutil

from bs4 import BeautifulSoup as bs

from src.browser import Browser
from src.objects import Course

MOODLE = "https://moodle.iitb.ac.in/my/courses.php"
COURSE_URL = "https://moodle.iitb.ac.in/course/view.php?id="


class Moodle:
    """
    Download all the documents and posts from Moodle to Device.
    """

    def __init__(self, sem: int):
        self.semLoc = f"Sem{sem}/"
        self.avail = os.path.join(self.semLoc, "available.json")
        if not os.path.exists(self.semLoc):
            self.createSem()
        with open(self.avail, "r", encoding="utf-8") as f:
            self.availableDocs = json.loads(f.read())
        self.courses = []

    def createSem(self):
        """Creates sem folder"""
        os.mkdir(self.semLoc)
        with open(self.avail, "w", encoding="utf-8") as f:
            f.write(json.dumps({}, indent=4))

    def createCourse(self, name: str, code: str):
        """
        Create a course directory.
        """
        courseLoc = os.path.join(self.semLoc, name)
        url = COURSE_URL + code
        courseInfo = {"name": name, "url": url, "loc": courseLoc, "docs": [], "posts": []}
        if os.path.exists(courseLoc):
            shutil.rmtree(courseLoc)
        os.makedirs(courseLoc)
        with open(os.path.join(courseLoc, "posts.txt"), "w", encoding="utf-8") as f:
            f.write(name + "\n" + "--" * 50)
        self.availableDocs[name] = courseInfo

    def getCourses(self, browser: Browser):
        """
        Get a list of available courses.
        """
        page = browser.login(MOODLE)
        soup = bs(page, "html5lib")
        courses = soup.find_all("li", attrs={"class": "course-listitem"})

        for course in courses:
            name = "_".join(course.find_all("div", attrs={"class": "text-muted"})[1].find_all("div")[1].text.split())
            code = course["data-course-id"]
            if name not in self.availableDocs:
                self.createCourse(name, code)
            courseInfo = self.availableDocs[name]
            self.courses.append(Course(courseInfo, browser))

    def downloadAll(self):
        """
        Download posts and documents from courses.
        """
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(course.download): course.courseInfo["name"] for course in self.courses}

            for future in concurrent.futures.as_completed(futures):
                self.availableDocs[futures[future]] = future.result()

        with open(self.avail, "w", encoding="utf-8") as f:
            f.write(json.dumps(self.availableDocs, indent=4))
