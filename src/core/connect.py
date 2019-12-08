# -*- coding: utf-8 -*-

import datetime
import html2text
import requests

from pysp.serror import SCDebug
from pysp.sjson import SJson

from core.helper import Helper
from core.model import StockDayShort, StockDayInvestor, StockDay
from core.cache import FCache
# from core.finance import BillConfig


class Http(SCDebug):
    DEBUG = True

    class Error(Exception):
        pass

    @classmethod
    def do_method(cls, method, url, **kwargs):
        text = kwargs.get('text', False)
        json = kwargs.get('json', False)
        params = kwargs.get('params', {})
        headers = kwargs.get('headers', {})
        try:
            r = method(url, params=params, headers=headers)
        except requests.exceptions.ConnectionError as e:
            raise cls.Error('Failed To Connect: {err}'.format(err=str(e)))

        if r.status_code == 200:
            if text:
                h = html2text.HTML2Text()
                h.ignore_links = True
                return h.handle(r.text)
            if json:
                return SJson.to_deserial(r.text)
            return r.text

        raise cls.Error('Unknown HTTP Status: {err}'.format(err=r.status_code))

    @classmethod
    def get(cls, url, **kwargs):
        cls.dprint(f'Http.get: {url} {kwargs}')
        return cls.do_method(requests.get, url, **kwargs)

    @classmethod
    def post(cls, url, **kwargs):
        cls.dprint(f'Http.post: {url}')
        return cls.do_method(requests.post, url, **kwargs)

    @classmethod
    def _proxy_key(cls, method, url, **kwargs):
        str_params = str(kwargs.get('params', 'none'))
        return '.'.join(['proxy', method, url, str_params])

    @classmethod
    def proxy(cls, method, url, **kwargs):
        '''
        :param method (string): method is GET or POST
        :param url (string):
        :param params (dict):   parameters of http's request
        :param headers (dict):  Request http to append headers
        :param json (bool):     Return a json objeect.
        :param text (bool):     Return a text.
        :param duration (int):  It is the cache's duration time. Unit is msec.
        '''
        def gathering():
            return _method_func.get(method)(url, **kwargs)

        _method_func = {
            'GET':  cls.get,
            'POST': cls.post,
        }
        duration = kwargs.get('duration', None)
        cachekey = cls._proxy_key(method, url, **kwargs)
        params = {}
        if duration:
            params['duration'] = duration
        params.update()
        return FCache().caching(cachekey, gathering, **params)


class FSpHelper(SCDebug):
    class Error(Exception):
        pass

    # DEBUG = True
    URL = {}

    @classmethod
    def stamp_yy_to_yyyy(cls, stamp):
        arr = stamp.split('.')
        yy = '19' if int(arr[0]) >= 60 else '20'
        return yy + stamp

    @classmethod
    def get_chunk(cls, key, **kwargs):
        raise NotImplementedError('Verify Implemented Function: get_chunk()')


class FDaum(FSpHelper):
    BASE_URL = 'http://finance-service.daum.net/item'
    URL = {
        'day': BASE_URL+'/quote_yyyymmdd.daum?code={code}&page={page}',
    }

    @classmethod
    def get_url(cls, key, **kwargs):
        code = kwargs.get('code')
        page = kwargs.get('page', 0)
        if page > 0:
            return cls.URL.get(key).format(code=code, page=page)
        raise cls.Error('Invalied page Range is 0 over.')

    @classmethod
    def get_chunk(cls, key, **kwargs):
        GET_CHUNK = {
            'day': cls._get_chunk_day,
        }
        return GET_CHUNK.get(key)(**kwargs)

    @classmethod
    def _get_chunk_day(cls, **kwargs):
        chunk = Http.get(cls.get_url('day', **kwargs), text=True)
        return cls._parse_day(chunk)

    @classmethod
    def _parse_day(cls, chunk):
        class ColIdx:
            SEPERATOR = '|'
            COL_LENGTH = 8
            IDX_STAMP = 0
            IDX_START = 1
            IDX_END = 4
            IDX_HIGH = 2
            IDX_LOW = 3
            IDX_VOLUME = 7

        days = []
        day = []
        p = Helper.LineParser.DaumDay()
        for line in chunk.split('\n'):
            _l = line.strip().replace(',', '')
            if not _l:
                continue
            if p.input(_l):
                day = [x.strip() for x in p.get_columns()]
                cls.dprint(day)
                days.append(StockDay(
                    finance='Daum',
                    stamp=cls.stamp_yy_to_yyyy(day[ColIdx.IDX_STAMP]),
                    start=int(day[ColIdx.IDX_START]),
                    end=int(day[ColIdx.IDX_END]),
                    high=int(day[ColIdx.IDX_HIGH]),
                    low=int(day[ColIdx.IDX_LOW]),
                    volume=int(day[ColIdx.IDX_VOLUME])))
                day = []
        for day in days:
            cls.dprint(day)
        return days


class FNaver(FSpHelper):
    BASE_URL1 = 'https://finance.naver.com/item'
    BASE_URL2 = 'https://m.stock.naver.com/item'
    URL = {
        'day':         BASE_URL1+'/sise_day.nhn?code={code}&page={page}',
        'dayinvestor': BASE_URL1+'/frgn.nhn?code={code}&page={page}',
        'current':     BASE_URL2+'/main.nhn',
        'hdr_current': BASE_URL2+'/index.nhn?code={code}&groupId=-1&type=total'
    }

    @classmethod
    def get_url(cls, key, **kwargs):
        # code = kwargs.get('code')
        # page = kwargs.get('page', 0)
        params = {'code': kwargs.get('code'), 'page': kwargs.get('page', 1)}
        if key in ['key', 'dayinvestor']:
            if params['page'] < 0:
                raise cls.Error('Invalied page Range is 0 over.')
        return cls.URL.get(key).format(**params)

    @classmethod
    def get_chunk(cls, key, **kwargs):
        GET_CHUNK = {
            'day':          cls._get_chunk_day,
            'dayinvestor':  cls._get_chunk_investor,
            'current':      cls._get_chunk_current,
        }
        return GET_CHUNK.get(key)(**kwargs)

    @classmethod
    def _get_chunk_day(cls, **kwargs):
        def gathering():
            chunk = Http.get(url, text=True)
            return cls._parse_day(chunk)

        url = cls.get_url('day', **kwargs)
        return FCache().caching(url, gathering,
                                duration=600, cast=StockDay.cast)

    @classmethod
    def _get_chunk_investor(cls, **kwargs):
        def gathering():
            chunk = Http.get(url, text=True)
            return cls._parser_investor(chunk)

        url = cls.get_url('dayinvestor', **kwargs)
        return FCache().caching(url, gathering,
                                duration=600, cast=StockDayInvestor.cast)

    @classmethod
    def _get_chunk_current(cls, **kwargs):
        # TODO : To be worked out later
        raise NotImplementedError('Not Support')
        # def gathering():
        #     headers = {'referer': cls.get_url('hdr_current', **kwargs)}
        #     chunk = Http.get(url, headers=headers)
        #     return cls._parser_current(chunk)
        #
        # url = cls.get_url('current', **kwargs)
        # return FCache().caching(url, gathering, duration=0)

    @classmethod
    def _parser_current(cls, chunk):
        print(chunk)
        return ''

    @classmethod
    def _parse_day(cls, chunk):
        class ColIdx:
            SEPERATOR = '|'
            COL_LENGTH = 7
            IDX_STAMP = 0
            IDX_START = 3
            IDX_END = 1
            IDX_HIGH = 4
            IDX_LOW = 5
            IDX_VOLUME = 6

        days = []
        day = []
        p = Helper.LineParser.NaverDay()
        for line in chunk.split('\n'):
            _l = line.strip().replace(',', '')
            if not _l:
                continue
            if p.input(_l):
                day = [x.strip() for x in p.get_columns()]
                cls.dprint(day)
                days.append(StockDay(
                    finance='Naver',
                    stamp=day[ColIdx.IDX_STAMP],
                    start=int(day[ColIdx.IDX_START]),
                    end=int(day[ColIdx.IDX_END]),
                    high=int(day[ColIdx.IDX_HIGH]),
                    low=int(day[ColIdx.IDX_LOW]),
                    volume=int(day[ColIdx.IDX_VOLUME])))
                day = []
        for day in days:
            cls.dprint(day)
        return days

    @classmethod
    def _parser_investor(cls, chunk):
        class ColIdx:
            COL_LENGTH = 9
            IDX_STAMP = 0
            IDX_FOREIGNER = 6
            IDX_FOREIGN_RATE = 8
            IDX_INSTITUTE = 5

        days = []
        day = []
        p = Helper.LineParser.NaverInvestor()
        for line in chunk.split('\n'):
            _l = line.strip().replace(',', '')
            if not _l:
                continue
            if p.input(_l):
                day = [x.strip() for x in p.get_columns()]
                cls.dprint(day)
                foreigner = int(day[ColIdx.IDX_FOREIGNER])
                institute = int(day[ColIdx.IDX_INSTITUTE])
                person = -(foreigner+institute)
                days.append(StockDayInvestor(
                    stamp=day[ColIdx.IDX_STAMP],
                    foreigner=foreigner,
                    frate=float(day[ColIdx.IDX_FOREIGN_RATE][:-1]),
                    institute=institute,
                    person=person))
        for day in days:
            cls.dprint(day)
        return days


class FKrx(FSpHelper):
    # DEBUG = True
    BASE_URL = 'https://short.krx.co.kr'
    URL = {
        'otp':      BASE_URL + '/contents/COM/GenerateOTP.jspx',
        # 'otp':      'https://short.krx.co.kr' + '/contents/COM/GenerateOTP.jspx',
        'query':    BASE_URL + '/contents/SRT/99/SRT99000001.jspx'
    }

    @classmethod
    def get_chunk(cls, key, **kwargs):
        GET_CHUNK = {
            'list':         cls._get_chunk_list,
            'shortstock':   cls._get_chunk_shortstock,
        }
        return GET_CHUNK.get(key)(**kwargs)

    @classmethod
    def get_fullcode(cls, pool, code, default=None):
        short_code = code if code[0] == 'A' else ('A'+code)
        # for item in pool['block1']:
        for item in pool:
            if item['short_code'] == short_code:
                return item['full_code']
        if default is None:
            raise cls.Error(f'Unknown Short Code: {code}')
        return default

    @classmethod
    def _get_chunk_list(cls, **kwargs):
        '''Get the stock items all from KRX.'''
        def gathering():
            # 2019.12.08 : Changed Format  bld=SRT/02/02010100/srt02010100&name=form
            params = {
                'bld':  'COM/finder_srtisu',
                # 'bld': 'SRT/02/02010100/srt02010100',
                'name': 'form',
            }
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36',
            }
            url = cls.URL.get('otp')
            key = Http.get(url, params=params, headers=headers)
            if not key:
                raise cls.Error('No KEY of KRX')

            params = {
                'no':       'SRT2',
                'mktsel':   'ALL',
                'pagePath': '/contents/COM/FinderSrtIsu.jsp',
                'code':     key,
            }
            pkwargs = {
                'params': params,
                'headers': headers,
                'json': True,
            }
            url = cls.URL.get('query')
            # {
            #   "block1": [
            #     {
            #       "full_code": "KR7060310000",
            #       "short_code": "A060310",
            #       "codeName": "3S",
            #       "marketName": "KOSDAQ"
            #     },
            #  }
            krxlist = Http.post(url, **pkwargs)
            return krxlist['block1']

        return FCache().caching(cls.URL['query'], gathering, duration=21600)

    @classmethod
    def _get_chunk_shortstock(cls, **kwargs):
        '''
        :param page     page index number, start from 0
        :param fcode    full code of stock item in Korea Exchange
        :param scode    short code of stock item in Korea Exchange

        :return         list of list or list of StockDayShort
        '''
        page = kwargs.get('page', 1)
        now = datetime.datetime.now()
        delta = datetime.timedelta(days=((page-1)*365))
        sdate = (now - delta).strftime('%Y%m%d')
        edate = (now - delta - datetime.timedelta(days=364)).strftime('%Y%m%d')

        fullcode = kwargs.get('fcode')
        shortcode = kwargs.get('scode')
        keywords = ['krx.short.stock', fullcode, shortcode, sdate, edate]

        def gathering():
            params = {
                'bld':  'SRT/02/02010100/srt02010100',
                'name': 'form',
            }
            url = cls.URL.get('otp')
            key = Http.get(url, params=params)

            cls.dprint(f'####### S:{sdate} E:{edate}')
            params = {
                'isu_cd':       fullcode,
                'isu_srt_cd':   shortcode,
                'strt_dd':      edate,
                'end_dd':       sdate,
                'pagePath':     '/contents/SRT/02/02010100/SRT02010100.jsp',
                'code':         key,
            }
            pkwargs = {
                'params': params,
                'json': True
            }
            url = cls.URL.get('query')
            data = Http.post(url, **pkwargs)
            days = []
            # {
            #   "block1": [
            #     {
            #       "totCnt": "241",
            #       "rn": "1",
            #       "trd_dd": "2019/02/14",
            #       "isu_cd": "KR7035720002",
            #       "isu_abbrv": "\uce74\uce74\uc624",
            #       "cvsrtsell_trdvol": "75,749",
            #       "str_const_val1": "-",
            #       "cvsrtsell_trdval": "7,475,106,600",
            #       "str_const_val2": "-"
            #     },
            # }
            if type(data) is dict and 'block1' in data:
                for item in data['block1']:
                    amount = item['str_const_val1'].replace(',', '')
                    days.append(StockDayShort(
                        stamp=item['trd_dd'],
                        short=int(item['cvsrtsell_trdvol'].replace(',', '')),
                        shortamount=None if amount == '-' else int(amount)))
            for day in days:
                cls.dprint(day)
            return days

        return FCache().caching(','.join(keywords), gathering,
                                duration=600, cast=StockDayShort.cast)


class FUnknown:
    class Error(Exception):
        pass

    @classmethod
    def get_chunk(cls, key, **kwargs):
        return cls.Error('Unknown {key} Function')


# if __name__ == '__main__':
#     import logging
#     import requests
#     try:
#         import http.client as http_client
#     except ImportError:
#         # Python 2
#         import httplib as http_client
#     http_client.HTTPConnection.debuglevel = 1
#     logging.basicConfig()
#     logging.getLogger().setLevel(logging.DEBUG)
#     requests_log = logging.getLogger("requests.packages.urllib3")
#     requests_log.setLevel(logging.DEBUG)
#     requests_log.propagate = True
#
#     data = Http.get('https://m.stock.naver.com/item/main.nhn',
#                     # text=True,
#                     headers={'referer': 'https://m.stock.naver.com/item/index.nhn?code=035720&groupId=-1&type=total',
#                              'User-Agent': 'curl/7.58.0'})
#     print(data)
