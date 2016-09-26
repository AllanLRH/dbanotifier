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

urlList = ["http://www.dba.dk/til-boligen/spise-og-dagligstuemoebler/sofaer-og-sofagrupper/produkt-chaiselong/stoerrelse-4-pers/reg-koebenhavn-og-omegn/?soeg=bolia&produkt=hjoernesofa&produkt=sofagruppe&stoerrelse=5-pers&stoerrelse=6-pers&fra=privat",
           "http://www.dba.dk/computer-og-spillekonsoller/hardware-og-software/tastaturer-og-mus/?soeg=cherry+mx&fra=privat",
           "http://www.dba.dk/til-boligen/spise-og-dagligstuemoebler/sofaborde-og-andre-borde/produkt-sofabord/reg-koebenhavn-og-omegn/?soeg=nova&sort=listingdate-desc&iswildcard&fra=privat",
           "http://www.dba.dk/til-boligen/spise-og-dagligstuemoebler/reg-koebenhavn-og-omegn/?soeg=bordstel&fra=privat",
           "http://www.dba.dk/til-boligen/spise-og-dagligstuemoebler/reg-koebenhavn-og-omegn/?soeg=M009&fra=privat",
           "http://www.dba.dk/til-boligen/belysning/reg-koebenhavn-og-omegn/?soeg=tom+rossau&fra=privat",
           "http://www.dba.dk/soeg/reg-koebenhavn-og-omegn/?soeg=cigaren+hans+wegner&fra=privat",
           "http://www.dba.dk/til-boligen/spise-og-dagligstuemoebler/sofaborde-og-andre-borde/reg-koebenhavn-og-omegn/?soeg=st%c3%b8bejern&fra=privat",
           "http://www.dba.dk/soeg/reg-koebenhavn-og-omegn/?soeg=hay+bordbukke&fra=privat",
           "http://www.dba.dk/soeg/reg-koebenhavn-og-omegn/?soeg=hay+loop&fra=privat",
           "http://www.dba.dk/computer-og-spillekonsoller/hardware-og-software/tastaturer-og-mus/reg-koebenhavn-og-omegn/?soeg=deathadder&fra=privat&iswildcard"]
urlList = reversed(urlList)
browserUrl = lambda url: url + '&vis=galleri'


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
        date = datetime.datetime.today().strftime("%d/%m/%Y") if d0 == 'I dag' else d0 + "/" + str(datetime.datetime.today().year)
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
        webbrowser.open_new_tab(el['url'])
        messageList.append("{title}\n({date}), {price}\n{url}".format(**el))
    if messageList:
        pb.push_note("Nyt fra DBA", "\n\n".join(messageList))


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'browse':
        for url in urlList:
            webbrowser.open(browserUrl(url))
    searchResult = list()
    for url in urlList:
        s0 = getSoup(url)
        searchResult += extractInfo(s0)
    updateDatabase(searchResult)
