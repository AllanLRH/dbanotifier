#!/usr/bin/env python
# -*- coding: utf8 -*-

import webbrowser
import sys
import datetime
import html
import os
import re
import logging
import functools
# Rest of the imports not in stdlib
import requests
import yaml
from bs4 import BeautifulSoup
from pushbullet import Pushbullet
from tinydb import TinyDB, Query


browserUrl = lambda url: url + '&vis=galleri'


@functools.lru_cache()  # Note that logging is not activated when a cached result is returned
def convertDatestringToDate(inStr):
    """
    Convert date string to datetime.date-object.
    If not possible, return inStr.
    """
    logging.info("Converting {} to datetime".format(inStr))
    currentYear = datetime.datetime.today().year
    monthMap = {"jan": 1,
                "feb": 2,
                "mar": 3,
                "apr": 4,
                "maj": 5,
                "jun": 6,
                "jul": 7,
                "aug": 8,
                "sep": 9,
                "okt": 10,
                "nov": 11,
                "dec": 12}
    try:
        toReturn = inStr
        m = re.match(r'(\d+)\. (\w+)', inStr)
        if m:
            d, m = m.groups()
            toReturn = datetime.date(currentYear, monthMap[m], int(d))
        elif inStr == "I dag":
            toReturn = datetime.date.today()
        elif inStr == "I går":
            toReturn = datetime.date.today() - datetime.timedelta(days=1)
        if toReturn == inStr:
            logging.critical("Could not convert string '{}' to datetime-object".format(inStr))
        return toReturn
    except Exception as e:
        logging.critical("An error occured when attempting to convert the string '{}' to a datetime-object".format(inStr))
        raise e


def getSoup(url):
    """
    Get webpage specified by url, return result as a BeautifulSoup-object.
    """
    logging.info("Getting soup for url: " + url)
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return BeautifulSoup(r.text, 'lxml')
    except requests.ConnectionError as e:
        logging.critical("Could not get html for url {}, status code {}. Captured error message: {}".format(url, r.status_code, e))
        raise e


def extractInfo(s0):
    """
    Extract relevant info from BeautifulSoup-object (s0).
    Returns results in a dict.
    """
    s1 = s0.findAll(class_="dbaListing")
    logging.info("{} listings found in search".format(len(s1)))
    itemList = list()
    for el in s1:
        url = el.find('a', class_="thumbnailContainerInner")['href']
        logging.debug("Found listing url: {}".format(url))
        itemId = url.split('/')[-2].replace('id-', '')
        logging.debug("Found listing itemId: {}".format(itemId))
        price = el.find('td', title="Pris").text.strip()
        logging.debug("Found listing price: {}".format(price))
        d0 = el.find('td', title="Dato").text.strip()
        logging.debug("Found listing date-string: {}".format(d0))
        date = convertDatestringToDate(d0)
        # Extract shortened title from <script>
        scriptText = el.find("script").text
        scriptTextSearch = re.search(r'\s+"name": "([^"]+)",', scriptText, re.MULTILINE)
        title = html.unescape(re.sub(r'&amp;(?=\#\d+)', r'&', scriptTextSearch.groups()[0]))
        logging.debug("Found listing title: {}".format(title))
        listingDict = {'itemId': itemId, 'url': url, 'date': date, 'price': price, 'title': title}
        itemList.append(listingDict)
        logging.info("Listing dict: {}".format(listingDict))
    return itemList


def updateDatabase(searchResult):
    """
    Update database with new search results, and send a push
    message if there's any new items in the search result.
    """
    logging.debug("The search result is: {}".format(searchResult))
    pb = Pushbullet(cfg["pushBulletId"])
    logging.info("Created pushbullet instance with id {}".format(cfg["pushBulletId"]))
    logging.info("Checking database against {} search results".format(len(searchResult)))
    toUpdate = [el for el in searchResult if not db.search(User.itemId == el['itemId'])]
    logging.info("There was {} new results which will be appended to the database".format(len(toUpdate)))
    logging.debug("The following will be appended to the database: {}".format(toUpdate))
    messageList = list()
    for el in toUpdate:
        db.insert(el)
        messageList.append("{title}\n({date}), {price}\n{url}".format(**el))
    if messageList:
        logging.info("The following message will be sent: {}".format("\n\n".join(messageList)))
        try:
            pb.push_note("{} nye fra DBA".format(len(toUpdate)), "\n\n".join(messageList))
        except:
            for el in toUpdate:
                webbrowser.open_new_tab(el["url"])
    else:
        logging.info("No message will be sent")


if __name__ == '__main__':
    if len(sys.argv) == 1 or not all([(el.endswith("yml") or el.endswith("yaml")) for el in sys.argv[1:]]):
        print("Error, you must provide configuration file(s) as argument(s).")
        sys.exit(1)
    for cfgFile in sys.argv[1:]:

        with open(os.path.join(os.path.dirname(__file__), cfgFile)) as fid:
            cfg = yaml.load(fid)

        User = Query()
        db = TinyDB(cfg["dbPath"])

        logging.basicConfig(filename=cfg["logfilePath"],
                            level=logging.INFO,
                            format="%(filename)s:%(lineno)s :: %(funcName)s()\t :: \t%(message)s")

        searchResult = list()
        for url in cfg["urls"]:
            s0 = getSoup(url)
            searchResult += extractInfo(s0)
        updateDatabase(searchResult)



