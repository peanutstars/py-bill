# -*- coding: utf-8 -*-

import hexdump
import unittest

from pysp.sjson import SJson

from core.connect import Http, FDaum, FNaver, FKrx
from core.model import *


EXAMPLE_TEXT = '''
# Example Domain

This domain is established to be used for illustrative examples in documents.
You may use this domain in examples without prior coordination or asking for
permission.

More information...'''.strip()

LICENSE_HTML = '''
MIT License

Copyright (c) 2018 HyunSuk Lee

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''.strip()


class TestConnect(unittest.TestCase):
    spd = ServiceProvider(name='daum', codename='카카오', code='035720')
    spn = ServiceProvider(name='naver', codename='카카오', code='035720')

    def test_http_get(self):
        text = Http.get('http://example.com', text=True)
        self.assertTrue(text.strip() == EXAMPLE_TEXT)

        text = Http.get('https://raw.githubusercontent.com/peanutstars/py-support-package/master/LICENSE')
        self.assertTrue(text.strip() == LICENSE_HTML)

    def test_fspdaum_day(self):
        # FDaum.DEBUG = True
        page = 1
        chunk = FDaum.get_chunk('day', code=self.spd.code, page=page)
        # data  = FDaum.do_parser('day', chunk)
        self.assertTrue(len(chunk) == 10)

    def test_fspnaver_day(self):
        # FNaver.DEBUG = True
        page = 1
        chunk = FNaver.get_chunk('day', code=self.spd.code, page=page)
        # data  = FNaver.do_parser('day', chunk)
        self.assertTrue(len(chunk) == 10)

    def test_fspnaver_dayinvestor(self):
        # FNaver.DEBUG = True
        page = 1
        chunk = FNaver.get_chunk('dayinvestor', code=self.spn.code, page=page)
        # data  = FNaver.do_parser('dayinvestor', chunk)
        self.assertTrue(len(chunk) == 20)

    def test_fspnaver_current(self):
        # import logging
        # import requests
        # try:
        #     import http.client as http_client
        # except ImportError:
        #     # Python 2
        #     import httplib as http_client
        # http_client.HTTPConnection.debuglevel = 1
        # logging.basicConfig()
        # logging.getLogger().setLevel(logging.DEBUG)
        # requests_log = logging.getLogger("requests.packages.urllib3")
        # requests_log.setLevel(logging.DEBUG)
        # requests_log.propagate = True
        # logging.basicConfig(level=logging.DEBUG)
        FNaver.get_chunk('current', code=self.spn.code)

    def test_krx_list(self):
        # Http.DEBUG = True
        chunk = FKrx.get_chunk('list')
        self.assertTrue(type(chunk) == list)
        # print(SJson.to_serial(chunk, indent=2))
        params = {
            'fcode': 'KR7035720002',
            'scode': 'A035720',
            # 'sdate': '20170101',
            # 'edate': '20190215',
            'page':  1
        }
        chunk = FKrx.get_chunk('shortstock', **params)
        self.assertTrue(type(chunk) == list)
        # print(SJson.to_serial(chunk, indent=2))
