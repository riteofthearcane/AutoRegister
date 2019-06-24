# AutoRegister
## A python script to automatically sign up for classes for UW

### Features
* completely automated sign up
* indistinguishable from a real user
* only registers once when spot opens up, does not spam register page
* uses backend json database for faster scraping without login
* checks time conflicts
* records restricted sections and prevents signing up for them
* stops searching when over credit limit or when no classes left to sign up for

### Dependencies
* selenium (download Chrome webdriver at http://chromedriver.chromium.org/downloads)
* configparser
