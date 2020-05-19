# user input

import os
import sys
import codecs
import argparse
from fake_useragent import UserAgent


if sys.version_info[0] >= 3:
    import urllib
    import urllib.request as request
    import urllib.error as urlerror
else:
    import urllib2 as request
    import urllib2 as urlerror
import socket
from contextlib import closing
from time import sleep
import re

from my_parser import parse_page
from image import download_img

import pandas as pd

def download_page(url, referer, maxretries, timeout, pause):
    tries = 0
    htmlpage = None
    while tries < maxretries and htmlpage is None:
        try:
            code = 404
            req = request.Request(url)
            req.add_header('Referer', referer)
            ua=UserAgent()
            req.add_header('User-agent',ua.random)
            
            with closing(request.urlopen(req, timeout=timeout)) as f:
                code = f.getcode()
                htmlpage = f.read()
                sleep(pause)
        except (urlerror.URLError, socket.timeout, socket.error):
            tries += 1
    if htmlpage:
        return htmlpage.decode('utf-8'), code
    else:
        return None, code


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--domain', help='Domain from which to download the reviews. Default: com',
                        required=False,
                        type=str, default='com')
    parser.add_argument('-f', '--force', help='Force download even if already successfully downloaded', required=False,
                        action='store_true')
    parser.add_argument(
        '-r', '--maxretries', help='Max retries to download a file. Default: 3',
        required=False, type=int, default=3)
    parser.add_argument(
        '-t', '--timeout', help='Timeout in seconds for http connections. Default: 180',
        required=False, type=int, default=180)
    parser.add_argument(
        '-p', '--pause', help='Seconds to wait between http requests. Default: 1', required=False, default=1,
        type=float)
    parser.add_argument(
        '-m', '--maxreviews', help='Maximum number of reviews per item to download. Default:unlimited',
        required=False,
        type=int, default=-1)
    parser.add_argument('--id', type=str, default= 'B071CV8CG2', choices=['B071CV8CG2','B019U00D7K'],
                        help='Product IDs for which to download reviews', required=False)
    args = parser.parse_args()

    print(args.id)
    # ASID = args.id
    id_ = args.id
    

    urlPart1 = "http://www.amazon.com/product-reviews/"
    urlPart2 = "/?ie=UTF8&showViewpoints=0&pageNumber="
    urlPart3 = "&sortBy=bySubmissionDateDescending"

    counterre = re.compile('cm_cr_arp_d_paging_btm_([0-9]+)')
    robotre = re.compile('images-amazon\.com/captcha/')

    referer = urlPart1 + str(id_) + urlPart2 + "1" + urlPart3

    page = 1
    lastPage = 1

    total_review_row = []
    total_df = None
    download_img(id_)
    while page <= lastPage:
        # if not page == 1 and not args.force and os.path.exists(basepath + os.sep + id_ + os.sep + id_ + '_' + str(
        #         page) + '.html'):
        #     print('Already got page ' + str(page) + ' for product ' + id_)
        #     page += 1
        #     continue
        url = urlPart1 + str(id_) + urlPart2 + str(page) + urlPart3
        print(url)
        htmlpage, code = download_page(url, referer, args.maxretries, args.timeout, args.pause)

        if htmlpage is None or code != 200:
            if code == 503:
                page -= 1
                args.pause += 2
                print('(' + str(code) + ') Retrying downloading the URL: ' + url)
            else:
                print('(' + str(code) + ') Done downloading the URL: ' + url)
                break
        else:
            print('Got page ' + str(page) + ' out of ' + str(lastPage) + ' for product ' + id_ + ' timeout=' + str(
                args.pause))
            if robotre.search(htmlpage):
                print('ROBOT! timeout=' + str(args.pause))
                if args.captcha or page == 1:
                    args.pause *= 2
                    continue
                else:
                    args.pause += 2
            for match in counterre.findall(htmlpage):
                try:
                    value = int(match)
                    if value > lastPage:
                        lastPage = value
                except:
                    pass
            
        df = parse_page(htmlpage)
        if page == 1:
            total_df = df
        else:
            total_df = pd.concat([total_df, df])

        if len(total_df[total_df["binaryrating"] == "negative"]) >= 5:
            posit_df = total_df[total_df["binaryrating"] == "positive"]
            negat_df = total_df[total_df["binaryrating"] == "negative"]

            posit_df = posit_df.sort_values(by=['date'], ascending = False)
            negat_df = negat_df.sort_values(by=['date'], ascending = False)

            posit_df = posit_df[:5]
            negat_df = negat_df[:5]
            list(negat_df['reviewtext']); list(negat_df['lemm_reviewtext'])

            break   
        page += 1  

    print(posit_df[['date','rating']].head())
    print(negat_df[['date','rating']].head())
