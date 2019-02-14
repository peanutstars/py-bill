# -*- coding: utf-8 -*-

import html2text
import requests

from pysp.serror import SDebug
from pysp.sjson import SJson


class Http(SDebug):
    # DEBUG = True

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
