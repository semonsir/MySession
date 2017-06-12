#!/usr/bin/env python2
# encoding: utf-8

import requests, requests.adapters
import cPickle as p
import sys, os, time, os.path


class MySession(requests.Session):
    '''对requests sess类重写，增加自定义ua、重试3次、启用cookies等，最终程序 需要完善到将print 直接输出到日志里面'''
    def __init__(self, cookiefile=None):
        requests.Session.__init__(self)
        custom_header = {'User-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0'}
        self.headers.update(custom_header)
        self.cookiefile = cookiefile
        if self.cookiefile:
            cookies = self.load_cookies()
            self.cookies.update(cookies)
        self.mount('http://', requests.adapters.HTTPAdapter(max_retries=3))
        self.mount('https://', requests.adapters.HTTPAdapter(max_retries=3))

    def  load_cookies(self):
        cookies = ''
        try:
            if os.path.isfile(self.cookiefile):
                with open(self.cookiefile, 'r') as f:
                    cookies = requests.utils.cookiejar_from_dict(p.load(f))
        except Exception as error:
            print error
        return cookies

    def save_cookies(self):
        try:
            if os.path.isfile(self.cookiefile):
                with open(self.cookiefile, 'w') as f:
                    p.dump(requests.utils.dict_from_cookiejar(self.cookies), f)
                    print 'Cookies saved.'
            else:
                print 'Cookiefile not defined, cookies did not saved.'
        except Exception as error:
            print error
            print 'Save cookies failed', sys.exc_info()[0]

    def gen_downloaddir(self, name):
        download_dir = '/opt/download/'
        download_file_dir = download_dir + name + '/'
        try:
            if not os.path.isdir(download_file_dir):
                os.makedirs(download_file_dir)
                print 'Generate download dir successfully:{DIR}'.format(DIR=download_file_dir)
        except Exception as error:
            print error
        return download_file_dir
    def gen_cookiefile(self, cookieFile):
        cookie_dat_dir = '/opt/config/'
        if not os.path.isdir(cookie_dat_dir):
            try:
                os.makedirs(cookie_dat_dir)
            except Exception as error:
                print error
                print 'Failed to makedir for cookies'
        return cookie_dat_dir
    def download(self, url, savefile):
        try:
            startTime = time.time()
            req = self.get(url, timeout=10, stream=True)
            if req.status_code == 200 and req.headers['Content-Length'] != 0:
                should_down, allready_down = str(req.headers['Content-Length']), 0
                if os.path.isfile(savefile):
                    allready_down = str(os.path.getsize(savefile))
                if allready_down == should_down:
                    print 'Allready download {URL} successfully before.'.format(URL=url)
                else:
                    if allready_down != 0:
                        print 'Has a file with the same name will be covered. Should length:{FILE1} and Local length:{FILE2}'.format(FILE1=should_down, FILE2=allready_down)
                    print 'Downloading url is: {URL}'.format(URL=url)
                    print 'Save to local file is: {FILE}'.format(FILE=savefile)
                    with open(savefile, 'wb') as f:
                        len_downloaded = 0
                        for dat in req.iter_content(chunk_size=5242880): # 10M cache # Could be perfect if the process bar showed.
                            len_downloaded += float(len(dat))
                            print '{PROGRESS:0.2f}%..'.format(PROGRESS=len_downloaded/float(should_down)*100),
                            f.write(dat)
                        endTime = time.time()
                    print 'Download {URL} successfull. Size:{SIZE:0.2f} KB, time:{TIME:0.2f} s, speed: {SPEED:0.2f} KB/s.'.format(SIZE=float(len_downloaded/1024), TIME=endTime-startTime, URL=url, SPEED=float(should_down)/(endTime - startTime)/1024)
                    time.sleep(1)
            else:
                raise Exception('status not 200 or length is 0.')
        except Exception as error:
            print 'Download {URL} failed. exception is: {EXP}'.format(URL=url, EXP=error)

    def download_limit_rate_206(self, url, savefile, limitrate=1024):
        '''这个函数最终没用，所以没用进一步完善'''
        self.limitrate = int(limitrate) * 1024  # exchange units to kbps
        try:
            html = self.head(url)
            contentlength = int(html.headers['Content-Length'])
            last_end = 0
            if contentlength > 0:
                with open(savefile, 'wb') as f:
                    while last_end < contentlength:
                        rangeheader = {'Range':'bytes=' + str(last_end) + '-' + str(last_end + self.limitrate)}
                        self.headers.update(rangeheader)
                        startTime = time.time()
                        html = self.get(url)
                        f.write(html.content)
                        endTime = time.time()
                        if endTime - startTime <1:
                            time.sleep(endTime - startTime)
                        last_end = last_end + self.limitrate
                        print '{PROGRESS:0.2f}%..'.format(PROGRESS=float(last_end)/float(contentlength)*100),
                print 'Download206 successfully.'
            else:
                raise Exception('Content length is not a integer.')
        except Exception as error:
            print error
            print 'Download206 failed.'

    def download_limit_rate_200(self, url, savefile, limitrate=1024):
        '''有bug：最低限速1M，如果再低可能出问题'''
        try:
            starttime = time.time()
            download_length = float(0)
            req = self.get(url, stream=True)
            with open(savefile,'wb') as f:
                for dat in req.iter_content(chunk_size=1024000):
                    f.write(dat)
                    consume_time = time.time() - starttime
                    download_length += len(dat)
                    speed = float('{SPEED:0.2f}'.format(SPEED=download_length/consume_time/1024)) # calc speed, units is KP/s
                    if speed > limitrate:
                        should_time = download_length/limitrate/1024 # 计算按照限速应该耗时多少, 单位 s
                        if should_time - consume_time > 20:
                            time.sleep(20)
                            download_length = float(1)
                        else:
                            time.sleep(should_time - consume_time)
                    consume_time = time.time() - starttime
                    speed = float('{SPEED:0.2f}'.format(SPEED=download_length/consume_time/1024))
                    print 'speed is :' + str(speed) + "KB/s     >>>>" + str(download_length) + '>>' + str(starttime)
            print 'write done'
        except Exception as error:
            print error


