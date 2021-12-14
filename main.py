import urllib3
from bs4 import BeautifulSoup
import re

import sys
import argparse

argparser = argparse.ArgumentParser()
#argparser.add_argument('-dom', dest='domain', required=True)
argparser.add_argument('domain', help='adress or domain')
argparser.add_argument('--deep', dest='deepness', default=-1, type=int)
argparser.add_argument('--link', action='store_true')
argparser.add_argument('--script', action='store_true')
argparser.add_argument('--img', action='store_true')

rootDomain = ''
rootLink = ''
maxDeepness = 0

args = argparser.parse_args()

rootDomain = args.domain
if args.deepness >= 0:
    maxDeepness = args.deepness
else:
    maxDeepness = 2**32


rootLink = rootDomain

poolManager = urllib3.PoolManager()

error_log = ''

visited_links = {}
invalid_links = {}
extern_links = {}

protocols_re = '(https?)|(mailto)'

#rootDomain = 'cs.mipt.ru/advanced_python'
#rootLink = 'http://cs.mipt.ru/advanced_python'

num_of_links = 0

class Link(object):
    def __init__(self, link, parents, children):
        global num_of_links
        num_of_links += 1
        #print(link)
        self.parents = parents
        self.children = children
        self.link = link
        self.isVisited = False
        self.isInvalid = False
        #self.isExtern = False
    def getPage(self):
        page = None
        try:
            return poolManager.request('GET', self.link)
        except:
            #print('pizdec1: ', self.link)
            global invalid_links
            global error_log
            if self.link not in invalid_links:
                self.isInvalid = True
                invalid_links.update({self.link : self})
            error_log += 'unable to get request from: ' + self.link + '\n'
            return
    def getHtml(self):
        global error_log
        try:
            bf = BeautifulSoup(((self.getPage()).data).decode('utf-8'), 'html.parser')
            if bf:
                return bf
            else:
                error_log += 'unable to get parse html from: ' + self.link + '\n'
                return
        except:
            #print('pizdec2: ', self.link)
            error_log += 'unable to get parse html from: ' + self.link + '\n'
    def formatLink(self, lnk):
        
        global visited_links
        global invalid_links
        global extern_links

        link = None
        if lnk in visited_links:
            link = visited_links[lnk]
        if lnk in invalid_links:
            link = invalid_links[lnk]
        if lnk in extern_links:
            link = extern_links[lnk]
        if link is None:
            link = Link(lnk, {}, {})

        if link.link not in self.children:
            self.children.update({link.link : link})
        if self.link not in link.parents:
            link.parents.update({self.link : self})

        return link

class LocalLink(Link):
    def navigate(self, deepness):
        if deepness > maxDeepness:
            return
        #print(self.link)
        global visited_links
        #global invalid_links
        global extern_links


        self.isVisited = True
        visited_links.update({self.link : self})
        html = self.getHtml()
        if not html:
            return

        links_link = []
        links_script = []
        links_img = []

        links_href = [lnk.get('href') for lnk in html.find_all('a')]
        if args.link:
            links_link = [lnk.get('href') for lnk in html.find_all('link')]
        if args.script:
            links_script = [lnk.get('src') for lnk in html.find_all('script')]
        if args.img:
            links_img = [lnk.get('src') for lnk in html.find_all('img')]
        links = links_href + links_link + links_script
        for lnk in links:
            if lnk and len(lnk):
                if lnk[0] == '/':
                    link = self.formatLink(rootLink + lnk)
                    link.__class__ = LocalLink

                    if not link.isVisited and not link.isInvalid:
                        link.navigate(deepness + 1)
                            #visited_links.update({link.link : link})
                        
                else:
                    global rootDomain
                    #if re.search('^(' + protocols_re + ':(//)?' + rootDomain + ')?', lnk) is not None:
                    if re.search(rootDomain, lnk) is not None:
                        link = self.formatLink(lnk)
                        link.__class__ = LocalLink

                        if not link.isVisited and not link.isInvalid:
                            link.navigate(deepness + 1)
                                #visited_links.update({link.link : link})
                    else:
                        if re.search('^' + protocols_re, lnk) is not None:
                            link = self.formatLink(lnk)
                            link.__class__ = ExternalLink

                            if lnk not in extern_links:
                                extern_links.update({link.link : link})
class ExternalLink(Link):
    def dummy(self):
        return ':('


RootLink = LocalLink(rootLink, {}, {})
RootLink.navigate(0)

print('==========SUMMARY==========')
print()
print('Links analysed: ', num_of_links)
print()
print('External links found: ', len(extern_links), ':')
for link in extern_links:
    print('\t', link)
print()
print('Invalid links found: ', len(invalid_links), ':')
for link in invalid_links:
    print('\t', link)

with open('error_log.out', 'w') as errlog:
    errlog.write(error_log)