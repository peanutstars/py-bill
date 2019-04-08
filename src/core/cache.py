
import atexit
import codecs
import glob
import hashlib
import os
import time

from pysp.sbasic import SSingleton
from pysp.serror import SDebug
from pysp.sjson import SJson

from core.config import BillConfig
from core.model import QueryData


@atexit.register
def _cleanup_exit():
    FCache().cleanup()


class FCache(SDebug, metaclass=SSingleton):
    class ExceptionNoData(Exception):
        pass

    DURATION = 3600
    NO_DATA = None

    def __init__(self):
        self._cache = {}
        self.folder = BillConfig().get_value('folder.cache', '/tmp/cache/')
        os.makedirs(self.folder, exist_ok=True)

    def hash(self, key):
        return hashlib.md5(key.encode('utf-8')).hexdigest()

    def cleanup(self):
        cstamp = time.time()
        for cfpath in glob.glob(self.folder+'/*'):
            req_del = False
            with codecs.open(cfpath, encoding='utf-8') as fd:
                try:
                    cache = SJson.to_deserial(fd.read())
                except Exception:
                    req_del = True
                    self.eprint(f'Cache Read Error file:{cfpath}')
                if req_del is False and cache['stamp'] < cstamp:
                    req_del = True
            if req_del:
                self.iprint(f'Delete {cfpath}')
                os.remove(cfpath)
        self.flush()

    def flush(self):
        for k, v in self._cache.items():
            cfpath = self.get_cache_file(k)
            err = False
            if os.path.exists(cfpath):
                os.remove(cfpath)
            if v['stamp'] < time.time():
                continue
            with codecs.open(cfpath, mode='w', encoding='utf-8') as fd:
                try:
                    fd.write(SJson.to_serial(v, indent=2))
                except Exception:
                    err = True
            if err:
                self.eprint(f'Cache Write Error key:{k} file:{cfpath}')
                os.rename(cfpath, cfpath+'.werr')

    def clear(self):
        self._cache = {}

    def get_cache_file(self, key):
        hash = self.hash(key)
        return f'{self.folder}/{hash}'

    def is_valid(self, key):
        self.remove_expired()
        if key in self._cache:
            if self._cache[key]['stamp'] >= time.time():
                return True
        return False

    def set_cache(self, key, value, **kwargs):
        '''
        :param duration:    duration time, unit is second.
        '''
        self.remove_expired()
        duration = kwargs.get('duration', self.DURATION)
        self._cache[key] = {
            'key': key,
            'duration': duration,
            'stamp': time.time() + duration,
            'value': value
        }

    def get_cache(self, key):
        if self.is_valid(key):
            return self._cache[key]['value']
        cfpath = self.get_cache_file(key)
        if os.path.exists(cfpath):
            with codecs.open(cfpath, encoding='utf-8') as fd:
                try:
                    self._cache[key] = SJson.to_deserial(fd.read())
                except Exception:
                    self.eprint(f'Cache Read Error key:{key} file:{cfpath}')
                    # os.rename(cfpath, cfpath+'.rerr')
                    return self.NO_DATA
            os.remove(cfpath)
            return self.get_cache(key)
        return self.NO_DATA

    def caching(self, key, generate_data, **kwargs):
        '''
        :param duration:    duration time, unit is second.
        :param cast:        a cast function which it call with the cached data.
        '''
        cast = kwargs.get('cast', None)
        noneable = kwargs.get('nonable', False)
        fg_hit = True
        data = self.get_cache(key)
        if data == self.NO_DATA:
            fg_hit = False
            data = generate_data()
            if data is None and noneable is False:
                raise FCache.ExceptionNone(f'key: {key}')
            self.set_cache(key, data, **kwargs)
        if cast and hasattr(cast, '__call__'):
            data = cast(data)
        # Delete Cache, QueryData.fields is 0
        if type(data) is QueryData and len(data.fields) == 0:
            del self._cache[key]
        # self.DEBUG = True
        self.dprint(f'Cache@{fg_hit} "{key}"')
        return data

    def remove_expired(self):
        cstamp = time.time()
        self._cache = \
            {k: v for k, v in self._cache.items() if v['stamp'] >= cstamp}
