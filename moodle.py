import requests
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
import time
import json
import os
import re


class Browser:
    def __new__(self, config: dict, name: str):
        """
        Returns the browser object created using browser config file.

        Args:
            config (dict): Config for browsers.
            name (str): Name of the browser to use

        Returns:
            (webdriver): webdriver object of required browser.
        """
        if name.lower() == 'firefox' or name.lower() == 'f':
            options = webdriver.FirefoxOptions()
            options.add_argument('-profile')
            options.add_argument(config['firefox']['profile'])
            options.add_argument('-headless')
            service=FirefoxService(GeckoDriverManager().install(),log_output='browser.log')
            browser = webdriver.Firefox(options=options,service=service)
            return browser


class Moodle:
    def __init__(self, semNo: int, browser: str = 'firefox') -> None:
        """
        Initializes the class and creates the necessary files/folders.
        Args:
            semNo (int): Sem
            profileLink (_type_, optional): Location of brower profile with saved login details.
        """
        self.sem = semNo
        self.path = f'./Sem{self.sem}'
        with open('config.json') as f:
            self.config=json.loads(f.read())
        self.browser=browser
        self.header=self.config['browsers'][self.browser]['header']
        if not os.path.exists(self.path):
            os.makedirs(self.path)
            with open(self.path+'/available.json', 'w') as f:
                f.write(json.dumps({}, indent=4))
        with open(self.path+'/available.json', 'rb+') as f:
            self.availableDocs = json.loads(f.read())
        self.header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0',
                       'Connection': 'keep-alive'}
        self.CourseURL = 'https://moodle.iitb.ac.in/my/courses.php'
        self.PDF_URL = 'https://moodle.iitb.ac.in/course/view.php?id='
        self.cookies = self.Login()

    def __del__(self) -> None:
        """
        Rewrites the available.json file to update changes. 
        """
        with open(self.path+'/available.json', 'w') as f:
            f.write(json.dumps(self.availableDocs, indent=4))

    def Login(self) -> dict:
        """
        Logs In to moodle account and return cookies.
        Also creates folders for new courses.

        Returns:
            dict: cookies
        """
        browser = Browser(self.config['browsers'],self.browser)
        browser.get(self.CourseURL)
        button = browser.find_element(value='sso-widget')
        button.click()
        time.sleep(2)
        cookie = browser.get_cookies()
        cookie = {i['name']: i['value'] for i in cookie}
        listElem = browser.find_element(
            'xpath', '/html/body/div[3]/div[3]/div/div/div[2]/div/section/div/aside/section/div/div[2]/div[1]/div[1]/div[2]/div[2]/div/ul/li[2]')
        listElem.click()
        page = browser.page_source
        soup = bs(page, 'html5lib')
        Courses = soup.find_all('li', attrs={'class': 'course-listitem'})
        self.createCourse(Courses)
        browser.close()
        return cookie

    def createCourse(self, Courses: list) -> None:
        """
        Creates a folder for new courses

        Args:
            Courses (list): list of course cards in homepage.
        """
        for i in Courses:
            name = '_'.join(i.find_all(
                'div', attrs={'class': 'text-muted'})[1].find_all('div')[1].text.split())
            id = i['data-course-id']
            if name not in self.availableDocs:
                self.availableDocs[name] = {'id': id, 'docs': [], 'posts': []}
                os.makedirs(self.path+'/'+name)
                f = open(self.path+'/'+name+'/posts.txt', 'w')
                f.write(name+'\n'+'--'*50)
                f.close()

    def DownloadLinks(self, course: str) -> dict:
        """
        Gets all the links for downloadable files in a course which are not already downloaded.
        Return dict of file ID and link

        Args:
            course (str): Name of the course.

        Returns:
            dict: {file_id: link}
        """
        res = requests.get(
            self.PDF_URL+self.availableDocs[course]['id'], cookies=self.cookies, headers=self.header)
        soup = bs(res.content, 'html5lib')
        Doc = soup.find_all('a', attrs={'class': 'aalink'})
        if 'forum' not in self.availableDocs[course]:
            self.availableDocs[course]['forum'] = [i['href']
                                                   for i in Doc if 'forum' in i['href']][0]
        Doc = {i['href'].split('=')[1]: i['href']
               for i in Doc if 'resource' in i['href']}
        return {i: Doc[i] for i in Doc if i not in self.availableDocs[course]['docs']}

    def Download(self, url: str, path: str) -> None:
        """
        Download and write files to corresponding course folder.

        Args:
            url (str): url of file to be downloaded.
            path (str): location where the file needs to be stored.
        """
        res = requests.get(url, cookies=self.cookies)
        try:
            name = re.search(r'filename="(.*)"',
                             res.headers['Content-Disposition']).group(1)
        except KeyError:
            print('Not Downloadable file.')
            return
        with open(path+name, 'wb') as f:
            f.write(res.content)

    def Post(self, url: str, course: str) -> tuple[dict, dict]:
        """
        Scrapes the post and replies and returns new Post Content and undownloaded attachments

        Args:
            url (str): url of post
            course (str): name of course

        Returns:
            tuple[dict, dict]: Post Content and Attachments dict with their IDs.
        """
        res = requests.get(url, cookies=self.cookies, headers=self.header)
        soup = bs(res.content, 'html5lib')
        articles = soup.find_all('div', attrs={'data-content': 'forum-post'})
        PostContents = {}
        Attachments = {}
        for article in articles:
            id = article['data-post-id']
            if id not in self.availableDocs[course]['posts']:
                head = article.find('h3').text
                date = article.find('time').text
                content = '\n'.join([i.text for i in article.find_all(
                    'p')]+[i.text for i in article.find_all('div', attrs={'class': 'text_to_html'})])
                links = article.find_all(
                    'a', attrs={'aria-label': re.compile(r"Attachment.*")})
                Data = f'{head}\t{date}\n{content}\n'
                for link in links:
                    Data += f'{link["aria-label"]}\n'
                Data += '--'*40+'\n'
                print(Data)
                Attachments.update(
                    {'_'.join(link["aria-label"].split()[1:]): link['href'] for link in links})
                PostContents[id] = Data
                self.availableDocs[course]['posts'].append(id)
        return PostContents, Attachments

    def Forum(self, course: str) -> None:
        """
        Scrapes the forum of a course to get posts.
        Writes the Post Content and downloads attachments.

        Args:
            course (str): course
        """
        res = requests.get(
            self.availableDocs[course]['forum'], cookies=self.cookies, headers=self.header)
        soup = bs(res.content, 'html5lib')
        tBody = soup.find('tbody')
        if tBody is None:
            return
        posts = tBody.find_all('th')
        for post in posts:
            link = post.find('a')['href']
            PostContents, Attachments = self.Post(link, course)
            with open(self.path+'/'+course+'/'+'posts.txt', 'r') as f:
                prevPosts = f.read()
            with open(self.path+'/'+course+'/'+'posts.txt', 'w') as f:
                f.write('\n'.join(list(PostContents.values()))+prevPosts)
            for attachment in Attachments:
                if attachment not in self.availableDocs[course]['docs']:
                    print(f'Downloading {course}/{attachment}')
                    self.availableDocs[course]['docs'].append(attachment)
                    self.Download(
                        Attachments[attachment], self.path+'/'+course+'/')

    def DownloadAll(self) -> None:
        """
        Runs the file downloading and forum scraping functions on all the available courses.
        """
        for i in self.availableDocs:
            print(f"Looking into {i}")
            docs = self.DownloadLinks(i)
            for doc in docs:
                print(f'Downloading {i}/{doc}')
                self.availableDocs[i]['docs'].append(doc)
                self.Download(docs[doc], self.path+'/'+i+'/')
            self.Forum(i)


t1 = time.time()
md = Moodle(5)
md.DownloadAll()
t2 = time.time()
del md
print(f'Completed Update in {t2-t1}s.')
