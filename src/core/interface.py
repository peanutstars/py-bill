# -*- coding: utf-8 -*-

import html2text
import requests


class Http:

    class Error(Exception):
        pass

    @classmethod
    def get(cls, url, **kwargs):
        text = kwargs.get('text', False)
        try:
            r = requests.get(url)
        except requests.exceptions.ConnectionError as e:
            rmsg = 'Failed To Connect: {err}'
            raise cls.Error(rmsg.format(err=str(e)))

        if r.status_code == 200:
            if text:
                h = html2text.HTML2Text()
                h.ignore_links = True
                return h.handle(r.text)
            return r.text

        rmsg = 'Unknown HTTP Status: {err}'
        raise cls.Error(rmsg.format(err=r.status_code))
