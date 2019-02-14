# -*- coding: utf-8 -*-

import hexdump
import unittest

from pysp.sjson import SJson

from core.interface import Http


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


class TestInterface(unittest.TestCase):

    def test_http_get(self):
        text = Http.get('http://example.com', text=True)
        self.assertTrue(text.strip() == EXAMPLE_TEXT)

        text = Http.get('https://raw.githubusercontent.com/peanutstars/py-support-package/master/LICENSE')
        self.assertTrue(text.strip() == LICENSE_HTML)

    def test_krx(self):
        Http.DEBUG = True
        params = {
            'bld':  'COM/finder_srtisu',
            'name': 'form',
        }
        url = 'http://short.krx.co.kr/contents/COM/GenerateOTP.jspx'
        code = Http.get(url, params=params)
        print(f'KRX KEY: {code}')
        self.assertTrue(len(code) == 108)

        params = {
            # 'isuCd':    None,
            'no':       'SRT2',
            'mktsel':   'ALL',
            'pagePath': '/contents/COM/FinderSrtIsu.jsp',
            'code':     code,
            # 'pageFirstCall': 'Y',
        }
        kwargs = {
            'params': params,
            'json': True
        }
        url = 'https://short.krx.co.kr/contents/SRT/99/SRT99000001.jspx'
        jdata = Http.post(url, **kwargs)
        self.assertTrue(type(jdata) is dict)
        # print(SJson.to_serial(jdata, indent=2))
