# -*- coding: utf-8 -*-

import datetime
import html2text
import requests

from pysp.serror import SDebug
from pysp.sjson import SJson

from core.helper import Helper
from core.model import *



class Http(SDebug):
    DEBUG = True

    class Error(Exception):
        pass

    @classmethod
    def do_method(cls, method, url, **kwargs):
        text = kwargs.get('text', False)
        json = kwargs.get('json', False)
        params = kwargs.get('params', None)
        try:
            r = method(url, params=params)
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
        cls.dprint(f'Http.get: {url}')
        return cls.do_method(requests.get, url, **kwargs)

    @classmethod
    def post(cls, url, **kwargs):
        cls.dprint(f'Http.post: {url}')
        return cls.do_method(requests.post, url, **kwargs)


class FSpHelper(SDebug):
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
    URL = {
        'day': 'http://finance-service.daum.net/item/quote_yyyymmdd.daum?code={code}&page={page}',
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
            SEPERATOR   = '|'
            COL_LENGTH  = 8
            IDX_STAMP   = 0
            IDX_START   = 1
            IDX_END     = 4
            IDX_HIGH    = 2
            IDX_LOW     = 3
            IDX_VOLUME  = 7

        days = []
        day = []
        p = Helper.LineParser.DaumDay()
        for line in chunk.split('\n'):
            l = line.strip().replace(',','')
            if not l:
                continue
            if p.input(l):
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
    BASE_URL = 'https://finance.naver.com/item'
    URL = {
        'day':          BASE_URL+'/sise_day.nhn?code={code}&page={page}',
        'dayinvestor': BASE_URL+'/frgn.nhn?code={code}&page={page}'
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
            'day':          cls._get_chunk_day,
            'dayinvestor':  cls._get_chunk_investor,
        }
        return GET_CHUNK.get(key)(**kwargs)

    @classmethod
    def _get_chunk_day(cls, **kwargs):
        chunk = Http.get(cls.get_url('day', **kwargs), text=True)
        return cls._parse_day(chunk)

    @classmethod
    def _get_chunk_investor(cls, **kwargs):
        chunk = Http.get(cls.get_url('dayinvestor', **kwargs), text=True)
        return cls._parser_investor(chunk)

    @classmethod
    def _parse_day(cls, chunk):
        class ColIdx:
            SEPERATOR   = '|'
            COL_LENGTH  = 7
            IDX_STAMP   = 0
            IDX_START   = 3
            IDX_END     = 1
            IDX_HIGH    = 4
            IDX_LOW     = 5
            IDX_VOLUME  = 6

        days = []
        day = []
        p = Helper.LineParser.NaverDay()
        for line in chunk.split('\n'):
            l = line.strip().replace(',','')
            if not l:
                continue
            if p.input(l):
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
            COL_LENGTH      = 9
            IDX_STAMP       = 0
            IDX_FOREIGNER   = 6
            IDX_FOREIGN_RATE = 8
            IDX_INSTITUTE   = 5

        days = []
        day = []
        p = Helper.LineParser.NaverInvestor()
        for line in chunk.split('\n'):
            l = line.strip().replace(',','')
            if not l:
                continue
            if p.input(l):
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
        for item in pool['block1']:
            if item['short_code'] == short_code:
                return item['full_code']
        if default is None:
            raise cls.Error(f'Unknown Short Code: {code}')
        return default

    @classmethod
    def _get_chunk_list(cls, **kwargs):
        params = {
            'bld':  'COM/finder_srtisu',
            'name': 'form',
        }
        url = cls.URL.get('otp')
        key = Http.get(url, params=params)

        params = {
            'no':       'SRT2',
            'mktsel':   'ALL',
            'pagePath': '/contents/COM/FinderSrtIsu.jsp',
            'code':     key,
        }
        kwargs = {
            'params': params,
            'json': True
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
        return  Http.post(url, **kwargs)

    @classmethod
    def _get_chunk_shortstock(cls, **kwargs):
        params = {
            'bld':  'SRT/02/02010100/srt02010100',
            'name': 'form',
        }
        url = cls.URL.get('otp')
        key = Http.get(url, params=params)

        page = kwargs.get('page', 1)
        now = datetime.datetime.now()
        delta = datetime.timedelta(days=((page-1)*365))
        sdate = (now - delta).strftime('%Y%m%d')
        edate = (now - delta - datetime.timedelta(days=364)).strftime('%Y%m%d')

        cls.dprint(f'####### S:{sdate} E:{edate}')
        params = {
            'isu_cd':       kwargs.get('fcode'),
            'isu_srt_cd':   kwargs.get('scode'),
            'strt_dd':      edate,
            'end_dd':       sdate,
            'pagePath':     '/contents/SRT/02/02010100/SRT02010100.jsp',
            'code':         key,
        }
        kwargs = {
            'params': params,
            'json': True
        }
        url = cls.URL.get('query')
        data = Http.post(url, **kwargs)
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
                amount = item['str_const_val1'].replace(',','')
                days.append(StockDayShort(
                    stamp=item['trd_dd'],
                    short=int(item['cvsrtsell_trdvol'].replace(',','')),
                    shortamount=None if amount == '-' else int(amount)))
        for day in days:
            cls.dprint(day)
        return days


class FUnknown:
    class Error(Exception):
        pass

    @classmethod
    def get_chunk(cls, key, **kwargs):
        return cls.Error('Unknown {key} Function')
