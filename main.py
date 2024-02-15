import time

from src.browser import Browser
from src.moodle import Moodle


def main():
    """
    Main function
    """
    t1 = time.perf_counter()
    with Browser() as browser:
        moodle = Moodle(6)
        moodle.getCourses(browser)
        moodle.downloadAll()
    t2 = time.perf_counter()
    print(f"Completed in: {t2-t1}")


if __name__ == "__main__":
    main()
