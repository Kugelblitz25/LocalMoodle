"""
This module contains classes Course and Announcement that
parse courses and announcements forums respectively
"""

import os
import re

from bs4 import BeautifulSoup as bs

from src.browser import Browser


class Announcement:
    """
    Parses Announcements forum
    """

    def __init__(self, url: str, browser: Browser):
        self.url = url
        self.browser = browser
        self.page = browser.get(url)

    def downloadFiles(self, courseLoc: str, courseInfo: dict) -> tuple[list[str]]:
        """Download posts and attachments from forum and write posts.txt"""
        soup = bs(self.page, "html5lib")
        tBody = soup.find("tbody")
        if tBody is None:
            return ([], [])

        conversations = tBody.find_all("th")
        posts, docs = [], []
        for conversation in conversations:
            link = conversation.find("a")["href"]
            newPosts, newDocs = self.parseConversation(link, courseInfo)

            with open(os.path.join(courseLoc, "posts.txt"), "a", encoding="utf-8") as f:
                f.write("\n".join(list(newPosts.values())))

            for doc, url in newDocs.items():
                if doc not in courseInfo["docs"]:
                    self.browser.download(url, courseLoc)
            posts += list(newPosts.keys())
            docs += list(newDocs.keys())
        return posts, docs

    def parseConversation(self, url: str, courseInfo: dict) -> tuple[dict]:
        """Parse each conversation to extract title, date, text and attachments."""
        res = self.browser.get(url)
        soup = bs(res, "html5lib")
        articles = soup.find_all("div", attrs={"data-content": "forum-post"})
        newPosts = {}
        newDocs = {}
        for article in articles:
            code = article["data-post-id"]
            if code not in courseInfo["posts"]:
                links = article.find_all("a", attrs={"aria-label": re.compile(r"Attachment.*")})
                title = f'{article.find("h3").text}\t{article.find("time").text}\n'
                paras = "\n".join([i.text for i in article.find_all("p")])
                paras += "\n".join([i.text for i in article.find_all("div", attrs={"class": "text_to_html"})])
                data = title + paras
                for link in links:
                    data += f'{link["aria-label"]}\n'
                data += "\n" + "--" * 40 + "\n"
                print(data)
                newDocs.update({"_".join(link["aria-label"].split()[1:]): link["href"] for link in links})
                newPosts[code] = data
        return newPosts, newDocs


class Course:
    """
    Parses Course.
    """

    def __init__(self, courseInfo: dict, browser: Browser):
        self.courseLoc = courseInfo["loc"]
        self.courseURL = courseInfo["url"]
        self.courseName = courseInfo["name"]
        self.courseInfo = courseInfo
        self.announcementsURL = ""
        self.browser = browser

    def download(self) -> dict:
        """
        Downloads documents in the given course and
        creates announcements object
        """
        print(f"Looking into {self.courseName}")
        newDocs = self.downloadFiles(self.courseURL)
        self.courseInfo["docs"] += newDocs
        announcemet = Announcement(self.announcementsURL, self.browser)
        newPosts, newDocs = announcemet.downloadFiles(self.courseLoc, self.courseInfo)
        self.courseInfo["posts"] += newPosts
        self.courseInfo["docs"] += newDocs
        return self.courseInfo

    def downloadFiles(self, url: str) -> list[str]:
        """
        Downloads new document.
        """
        res = self.browser.get(url)
        soup = bs(res, "html5lib")
        links = soup.find_all("a", attrs={"class": "aalink"})
        self.announcementsURL = [i["href"] for i in links if "forum" in i["href"]][0]  # use filter
        links = {i["href"].split("=")[1]: i["href"] for i in links if "resource" in i["href"]}
        newDocs = []
        for link in links:
            if link not in self.courseInfo["docs"]:
                self.browser.download(links[link], self.courseLoc)
                newDocs.append(link)
        return newDocs
