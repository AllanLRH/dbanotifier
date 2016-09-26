#!/usr/bin/env python
# -*- coding: utf8 -*-

import requests
from bs4 import BeautifulSoup
import webbrowser
import sys
import datetime
import html
import re
from pushbullet import Pushbullet
from tinydb import TinyDB, Query
User = Query()
db = TinyDB('/Users/allan/src/boliaSofa/searches.tinydb.json')

with open("urlList.txt") as fid:
    urlList = [line.strip() for line in fid if line.strip()]
browserUrl = lambda url: url + '&vis=galleri'


def convertDatestringToDate(inStr):
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
    m = re.match(r'(\d+)\. (\w+)', inStr)
    if m:
        d, m = m.groups()
        return datetime.date(currentYear, monthMap[m], int(d))
    elif inStr == "I dag":
        return datetime.date.today()
    elif inStr == "I går":
        return datetime.date.today() - datetime.timedelta(days=1)
    else:
        return inStr


def getSoup(url):
    r = requests.get(url)
    if r.status_code == 200:
        return BeautifulSoup(r.text, 'lxml')
    print('Error retrieving DBA search\n%s' % url, file=sys.stderr)


def extractInfo(s0):
    s1 = s0.findAll(class_="dbaListing")
    itemList = list()
    for el in s1:
        url = el.find('a', class_="thumbnailContainerInner")['href']
        itemId = url.split('/')[-2].replace('id-', '')
        price = el.find('td', title="Pris").text.strip()
        d0 = el.find('td', title="Dato").text.strip()
        date = convertDatestringToDate(d0)
        # Extract shortened title from <script>
        t0 = el.find("script")
        t1 = t0.contents[0].strip()
        t2 = [ln.strip() for ln in t1.splitlines() if '"name":' in ln]
        t3 = t2[0].replace('"name": ', '')
        t4 = t3.replace('"', '')
        t5 = t4.rstrip(",")
        title = html.unescape(re.sub(r'&amp;(?=\#\d+)', r'&', t5))
        itemList.append({'itemId': itemId, 'url': url, 'date': date, 'price': price, 'title': title})
    return itemList


def updateDatabase(searchResult):
    pb = Pushbullet("o.B8s0B7VUNVgrzU4fNpvTjan4VKPO6qhJ")
    toUpdate = [el for el in searchResult if not db.search(User.itemId == el['itemId'])]
    messageList = list()
    for el in toUpdate:
        db.insert(el)
        messageList.append("{title}\n({date}), {price}\n{url}".format(**el))
    if messageList:
        try:
            pb.push_note("Nyt fra DBA", "\n\n".join(messageList))
        except:
            for el in toUpdate:
                webbrowser.open_new_tab(el["url"])


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'browse':
        for url in urlList:
            webbrowser.open(browserUrl(url))
    searchResult = list()
    for url in urlList:
        s0 = getSoup(url)
        searchResult += extractInfo(s0)
    updateDatabase(searchResult)
