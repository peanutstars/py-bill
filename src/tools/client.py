#!/usr/bin/env python3

# import codecs
import json
import logging
import os
import requests

from xml.dom import minidom
from pysp.sbasic import SFile, Dict


ENABLE_LOG = True
_log = logging.getLogger('pbclient')
_log.handlers = []
if ENABLE_LOG:
    formatter = logging.Formatter('[%(asctime)s - %(name)s - %(levelname)s] %(message)s')
    h = logging.StreamHandler()
    h.setFormatter(formatter)
    _log.addHandler(h)
    _log.setLevel(logging.DEBUG)


class PbClient(Dict):
    PATH_LOGIN =    '/account/login'
    PATH_LOGOUT =   '/account/logout'
    PATH_WHOAMI =   '/ajax/account/whoami'
    # PATH_CFGFILE =  '/var/pybill/config/pbclient.json'
    PATH_CFGFILE =  '~/.pybill/config/pbclient.json'
    KEY_SESSION =   'session'

    def __init__(self, **kwargs):
        super(PbClient, self).__init__()
        self.url = kwargs.get('url')
        self.loginURL = self.url_path(self.PATH_LOGIN)
        self.user = kwargs.get('user')
        self.passwd = kwargs.get('passwd')
        self.csrf = ''
        self.headers = kwargs.get('headers', {})
        self.cookies = kwargs.get('cookies', {})
        self.do_login()

    def reset_params(self):
        _log.debug('Reset headers and cookies')
        self.csrf = ''
        self.headers = {}
        self.cookies = {}

    @classmethod
    def handle(cls, **kwargs):
        '''
        @param cfgfile string:  Path of configuration file
        '''
        cfgfile = os.path.expanduser(kwargs.get('cfgfile', cls.PATH_CFGFILE))
        url = kwargs.get('url', None)
        user = kwargs.get('user', None)
        passwd = kwargs.get('passwd', None)
        if os.path.exists(cfgfile):
            # with codecs.open(cfgfile, 'r', encoding='utf-8') as fd:
            cfg = json.loads(SFile.read_all(cfgfile))
            if url:
                cfg['url'] = url
            if user:
                cfg['user'] = user
            if passwd:
                cfg['passwd'] = passwd
            return cls(**cfg)
        return cls(**kwargs)
    
    def url_path(self, path):
        splitter = '' if path[0] == '/' else '/'
        url = f'{self.url}{splitter}{path}'
        _log.debug(f'URL: {url}')
        return url

    def parse_session(self, headers):
        for k, v in headers.items():
            if k == 'Set-Cookie':
                for t in v.split('; '):
                    if t.find(self.KEY_SESSION) >= 0:
                        k, v = t.strip().split('=')
                        self.cookies[k] = v
                        # self.headers['Cookie'] = t

    def _get_session(self, force=False):
        # if force is False and 'session' in self.headers:
        if force is False and 'session' in self.cookies:
            return
        
        try:
            r = requests.get(self.loginURL)
        except requests.exceptions.ConnectionError as e:
            raise Exception(f'Failed To Connect: {e}')

        if r.status_code != 200:
            raise Exception(f'Error Connection: HTTP({r.status_code})')

        self.parse_session(r.headers)
        self._get_csrf_token(r.text)

    def _get_csrf_token(self, content):
        for line in content.splitlines():
            if line.find('csrf_token') >= 0:
                xmlstring = line.strip()+'</input>'
                dom = minidom.parseString(xmlstring)
                node = dom.getElementsByTagName('input')
                for attr in node:
                    name = attr.getAttribute('name')
                    if name == 'csrf_token':
                        self.csrf = attr.getAttribute('value')
                        break

    def login(self, force=False):
        def login_params():
            return {
                'csrf_token':   self.csrf,
                'email':        self.user,
                'password':     self.passwd                
            }
        self._get_session(force=force)
        params = login_params()
        try:
            r = requests.post(self.loginURL, headers=self.headers, 
                              cookies=self.cookies, data=params)
        except requests.exceptions.ConnectionError as e:
            raise Exception(f'Failed To Connect: {e}')
        
        if r.status_code == 200:
            self.parse_session(r.headers)
            return

        raise Exception(f'Error Connection: HTTP({r.status_code})')

    def logout(self):
        try:
            self.query(self.PATH_WHOAMI, tojson=True)
        except:
            _log.info('Already Logged Out')
            return True

        self.query(self.PATH_LOGOUT)

        try:
            self.query(self.PATH_WHOAMI, tojson=True)
        except:
            _log.info('Logged Out')
            self.reset_params()
            SFile.to_file(self.PATH_CFGFILE, json.dumps(self))
            return True
        _log.debug('Failed to Log Out')
        return False


    def is_login(self):
        try:
            o = self.query(self.PATH_WHOAMI, tojson=True)
        except:
            self.reset_params()
            return False

        if o['value']['email'] == self.user:
            _log.info('Logged In')
            SFile.to_file(self.PATH_CFGFILE, json.dumps(self))
            return True
        return False

    def do_login(self):
        if self.is_login():
            _log.debug('Logged In in Step 1')
            return True
        self.login()
        if self.is_login():
            _log.debug('Logged In in Step 2')
            return True
        raise Exception('Failed Login - Not matched USER or PASSWORD.')
        
    
    def query(self, path, method='get', **kwargs):
        '''
        @param path
        @param method
        @param headers
        @param data
        @param tojson
        '''
        reqMethod = {
            'get':      requests.get,
            'post':     requests.post,
            'delete':   requests.delete,
            'patch':    requests.patch,
        }
        path = path.strip()
        data = kwargs.get('data', None)
        headers = kwargs.get('headers', {})
        tojson = kwargs.get('tojson', False)
        url = self.url_path(path)
        headers.update(self.headers)
        try:
            r = reqMethod.get(method)(url, headers=headers, cookies=self.cookies, data=data)
        except requests.exceptions.ConnectionError as e:
            raise Exception(f'Failed To Connect: {e}')

        if r.status_code == 200:
            self.parse_session(r.headers)
            if tojson:
                try:
                    return json.loads(r.text)
                except Exception:
                    raise Exception(f'Error JSON Format: [{r.text}]')
            return r.text

        raise Exception(f'Error Connection: HTTP({r.status_code})')



if __name__ == '__main__':
    from core.finalgo import IterAlgo

    params = Dict()
    params.url = 'http://localhost:8000'
    params.user = 'admin'
    params.passwd = 'admin'

    client = PbClient.handle(**params)
    data = client.query('/bill/stock/010140', method='get')
    print(data)

    client = PbClient.handle(cfgfile=PbClient.PATH_CFGFILE)
    param = {
        'colnames': ['stamp', 'start', 'low', 'high', 'end', 'volume']
    }
    headers = {
        'Content-Type': 'application/json'
    }
    code = '095700'
    qdata = client.query(f'/ajax/stock/item/{code}/columns/72', 
                        headers=headers, method='post', data=json.dumps(param), tojson=True)
    if 'value' in qdata and qdata['value']:
        IterAlgo.compute_qdata(qdata=qdata['value'], code=code)

    client.logout()

