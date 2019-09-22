# AutoRegister
## A python script to automatically sign up for classes for UW

### Features
* completely automated sign up
* indistinguishable from a real user
* only registers once when spot opens up, does not spam register page
* does not spam registration on failure to register for spot
* uses backend json database for faster scraping without login
* checks time conflicts
* records restricted sections and prevents signing up for them
* stops searching when over credit limit or when no classes left to sign up for
* handles classes with lecture and a quiz section or lecture, quiz, and lab sections (hello PHYS 121)
* stores settings in config file so user only has to set up once
* customizable section blacklist

### Dependencies
* selenium (download Chrome webdriver at http://chromedriver.chromium.org/downloads)
* configparser
```
pip install selenium
pip install configparser
```
