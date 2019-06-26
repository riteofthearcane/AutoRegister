import requests
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import configparser
import os
import sys
import re


def main():
    print(getNow(), "Initializing AutoRegister...")
    fileName = getFileName()
    config = initializeConfig(fileName)
    if config:
        browser = webdriver.Chrome(config['setup']['driverPath'])
        login(browser, config['setup']['username'],
              config['setup']['password'])
        if not checkLogin(browser):
            term = getTerm(browser)
            enrolled = getEnrolledClass(browser)
            times = getEnrolledTime(enrolled, term)
            credits = getTotalCredits(browser)
            courses = initializeCourses(config, enrolled)
            writeCoursesToConfig(config, courses, fileName)
            timeBlacklist = generateTimeBlacklist(courses, times, term)
            restrictedBlacklist = initializeBlacklist(config, courses)
            writeBlacklistToConfig(config, restrictedBlacklist, fileName)
            goal = int(config['class']['goal'])
            print("Checking for availability for:")
            for course in courses:
                print(course)
            print("Please do not manually drop or sign up classes. \n")
            last = []
            interval = 3600 * 3  # 3 hours
            nextRefresh = time.time() + interval
            while len(courses) > 0 and credits < goal:
                if time.time() >= nextRefresh:
                    addClass(browser, {})
                    print(getNow(), "Refreshing page.")
                    if checkLogin(browser):
                        login(browser, config['setup']['username'],
                              config['setup']['password'])
                        print("Logged out. Logging back in.")
                    nextRefresh = time.time() + interval
                openList = getClassStatus(
                    courses, term, timeBlacklist, restrictedBlacklist)
                if len(openList) > 0 and last != openList:
                    addClass(browser, openList)
                    enrolled = getEnrolledClass(browser)
                    credits = getTotalCredits(browser)
                    deleteList = set()
                    for course in courses:
                        if course in enrolled:
                            print("Enrolled in", course)
                            deleteList.add(course)
                            writeCoursesToConfig(config, courses, fileName)
                            times = getEnrolledTime(enrolled, term)
                            timeBlacklist = generateTimeBlacklist(
                                courses, times, term)
                    for delete in deleteList:
                        courses.remove(delete)
                    getMessage(browser, restrictedBlacklist, config)
                    writeBlacklistToConfig(
                        config, restrictedBlacklist, fileName)
                last = openList
                time.sleep(5)
            if len(courses) == 0:
                print('All classes added.')
            elif credits >= goal:
                print('Credit minimum reached.')
        else:
            print("Login failed.")
    input("Press Enter to continue...")


def getFileName():
    if getattr(sys, 'frozen', False):
        path = os.path.dirname(sys.executable)
    elif __file__:
        path = os.path.dirname(__file__)
    return os.path.join(path, "config.ini")


def initializeConfig(fileName):
    config = configparser.ConfigParser()
    if not os.path.exists(fileName):
        config['setup'] = {
            'username': 'Enter your UW NetID here',
            'password': 'Enter your password here',
            'driverPath': 'Enter the path of the Chrome driver or download at http://chromedriver.chromium.org/'
        }
        config['class'] = {
            'class': 'Enter the classes you want to sign up, separated by a comma',
            'goal': 'Enter the minimum number of credits you wish to take',
            'blacklist': ''
        }
        config.write(open(fileName, 'w'))
        print('Config file created at ', fileName)
        return
    else:
        print("Config found at", fileName)
        config.read(fileName)
        return config


def login(browser, id, pw):
    browser.get("https://sdb.admin.uw.edu/students/uwnetid/register.asp")
    username = browser.find_element_by_id("weblogin_netid")
    password = browser.find_element_by_id("weblogin_password")
    username.send_keys(id)
    password.send_keys(pw)
    browser.find_element_by_name("_eventId_proceed").click()


def checkLogin(browser):
    return len(browser.find_elements_by_name("_eventId_proceed")) > 0


def getTerm(browser):
    elem = browser.find_elements_by_xpath(
        "/html/body/div[2]/table[3]/tbody/tr/td[1]/h1[1]")
    return elem[0].text.replace('Registration - ', '')


def getEnrolledClass(browser):
    elems = browser.find_elements_by_xpath(
        "/html/body/div[2]/form[1]/p/table[1]/tbody/tr[position() > 2]/td[3]")
    res = {}
    for e in elems:
        split = e.text.split()
        if len(split) > 0:
            enrolledClass = split[0] + ' ' + split[1]
            if not enrolledClass in res:
                res[enrolledClass] = set()
            res[enrolledClass].add(split[2])
    return res


def getEnrolledTime(enrolled, term):
    res = []
    for course in enrolled:
        parser = getCourseJson(course)
        if parser:
            for n1 in parser['courseOfferingInstitutionList']:
                for n2 in n1['courseOfferingTermList']:
                    if n2['term'] == term:
                        for section in n2['activityOfferingItemList']:
                            if section['code'] in enrolled[course]:
                                for meetingTime in section['meetingDetailsList']:
                                    res.append(meetingTime)
    return res


def getTotalCredits(browser):
    elem = browser.find_element_by_xpath(
        "/html/body/div[2]/form[1]/p/table[1]/tbody/tr[last()]/td[1]")
    split = elem.text.split()
    return int(float(split[len(split)-1]))


def addClass(browser, openList):
    max = getMax(browser)
    courses = list(openList.keys())
    for i in range(8):
        form = browser.find_element_by_name("sln" + str(max + 1 + i))
        if i < len(courses):
            form.send_keys(courses[i])
            print(getNow(), "Attempting to enroll in",
                  openList[courses[i]])
        else:
            form.clear()
    browser.find_element_by_xpath(
        '//input[@value=\' Update Schedule \']').click()


def getMessage(browser, restrictedBlacklist, config):
    elems = browser.find_elements_by_xpath(
        "/html/body/div[2]/form[1]/p[2]/table[1]/tbody/tr[position() > 1]/td[5]")
    for e in elems:
        if len(e.text.strip()) > 0:
            print(e.text)
        if "Restricted section" in e.text:
            restricted = e.text.split(':')[0]
            restrictedBlacklist.add(restricted)
            print(restricted, "added to blacklist")


def getCourseName(parser):
    if parser:
        return parser['courseSummaryDetails']['subjectArea'] + ' ' + parser['courseSummaryDetails']['courseNumber']


def generateTimeBlacklist(courses, times, term):
    res = set()
    for course in courses:
        parser = getCourseJson(course)
        if parser:
            for n1 in parser['courseOfferingInstitutionList']:
                for n2 in n1['courseOfferingTermList']:
                    if n2['term'] == term:
                        for section in n2['activityOfferingItemList']:
                            for meetingTime in section['meetingDetailsList']:
                                if overlaps(meetingTime, times):
                                    res.add(course + " " + section['code'])
    return res


def overlaps(meetingTime, times):
    days1 = [a for a in re.split(r'([A-Z][a-z]*)', meetingTime['days']) if a]
    hours1 = meetingTime['time'].split(' - ')
    st1 = hours1[0]  # 1:30 PM
    et1 = hours1[1]
    for timee in times:
        days2 = [a for a in re.split(r'([A-Z][a-z]*)', timee['days']) if a]
        hours2 = timee['time'].split(' - ')
        st2 = hours2[0]
        et2 = hours2[1]
        if (isEarlier(st1, st2) and isEarlier(st2, et1)) or (isEarlier(st2, st1) and isEarlier(st1, et2)):
            for day in days1:
                if day in days2:
                    return True

# returns true if time1 is earlier than time2


def isEarlier(time1, time2):
    if time1[0:2] == "12":
        if 'AM' in time1:
            time1 = time1.replace('AM', 'PM')
        else:
            time1 = time1.replace('PM', 'AM')
    if time2[0:2] == "12":
        if 'AM' in time2:
            time2 = time2.replace('AM', 'PM')
        else:
            time2 = time2.replace('PM', 'AM')
    if time1[-2] != time2[-2]:
        if time1[-2] == 'A':
            return True
    else:
        split1 = time1.split(':')
        split2 = time2.split(':')
        hr1 = int(split1[0])
        hr2 = int(split2[0])
        min1 = int(split1[1][:2])
        min2 = int(split2[1][:2])
        if hr1 != hr2:
            if hr1 < hr2:
                return True
        else:
            if min1 <= min2:
                return True


def getClassStatus(courses, term, timeBlacklist, restrictedBlacklist):
    res = {}
    for course in courses:
        parser = getCourseJson(course)
        if parser:
            status = {}
            for n1 in parser['courseOfferingInstitutionList']:
                for n2 in n1['courseOfferingTermList']:
                    if n2['term'] == term:
                        for section in n2['activityOfferingItemList']:
                            fullCourseName = course + ' ' + section['code']
                            if not fullCourseName in timeBlacklist and not fullCourseName in restrictedBlacklist:
                                if len(section['code']) == 1:
                                    if section['enrollStatus'] == 'open' and section['addCodeRequired'] == 'false':
                                        status[section['code']] = {
                                            'registrationCode': section['registrationCode']
                                        }
                                else:
                                    if section['code'][0] in status:
                                        sectionType = section['activityOfferingType']
                                        if not sectionType in status[section['code'][0]]:
                                            status[section['code'][0]
                                                   ][sectionType] = {}
                                        if section['enrollStatus'] == 'open' and section['addCodeRequired'] == 'false':
                                            status[section['code'][0]][sectionType][section['code']] = {
                                                'registrationCode': section['registrationCode']
                                            }
            for lecture in status:
                canEnroll = True
                for sectionType in status[lecture]:
                    if sectionType != 'registrationCode' and len(status[lecture][sectionType]) == 0:
                        canEnroll = False
                if canEnroll:
                    res[status[lecture]['registrationCode']
                        ] = course + ' ' + lecture
                    for sectionType in status[lecture]:
                        if sectionType != 'registrationCode':
                            first = list(status[lecture]
                                         [sectionType].keys())[0]
                            res[status[lecture][sectionType][first]
                                ['registrationCode']] = course + ' ' + first
    return res


def initializeCourses(config, enrolled):
    courses = set(())
    for course in config['class']['class'].split(","):
        course = course.strip()
        page = getCourseJson(course)
        if page and getCourseName(page) and not getCourseName(page) in enrolled:
            courses.add(getCourseName(page))
    return courses


def initializeBlacklist(config, courses):
    res = set()
    for entry in config['class']['blacklist'].split(','):
        split = entry.strip().split(' ')
        if len(split) == 3 and split[0].upper() + ' ' + split[1].upper() in courses:
            res.add(entry)
    return res


def writeCoursesToConfig(config, courses, fileName):
    res = ""
    if len(courses) > 0:
        courseList = list(courses)
        courseList.sort()
        for i in range(len(courseList) - 1):
            res += courseList[i] + ","
        res += courseList[-1]
    config['class']['class'] = res
    config.write(open(fileName, 'w'))


def writeBlacklistToConfig(config, blacklist, fileName):
    res = ""
    parsed = list(blacklist)
    parsed.sort()
    if len(parsed) > 0:
        for i in range(len(parsed) - 1):
            res += parsed[i] + ","
        res += parsed[-1]
    config['class']['blacklist'] = res
    config.write(open(fileName, 'w'))


def getCourseJson(course):
    page = None
    try:
        page = requests.get(getCourseLink(course), timeout=30)
    except:
        print(getNow(), getCourseLink(course),
              "error while attempting to load")
    if page and page.status_code == 200:
        return json.loads(page.content)


def getCourseLink(course):
    return 'https://myplan.uw.edu/course/api/courses/' + course + '/details'


def getMax(browser):
    return int(browser.find_element_by_name("maxdrops").get_attribute('value'))


def getNow():
    return datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')


main()
