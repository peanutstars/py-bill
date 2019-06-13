
import atexit
import codecs
import glob
import hashlib
import os
import threading
import time

from pysp.sbasic import SSingleton
from pysp.serror import SDebug
from pysp.sjson import SJson

from core.config import BillConfig
from core.model import QueryData


# @atexit.register
# def _cleanup_exit():
#     FCache().cleanup()


class FCache(SDebug, metaclass=SSingleton):
    class ExceptionNoData(Exception):
        pass

    DURATION = 3600
    NO_DATA = None

    def __init__(self):
        self._cache = {}
        self.lock = threading.Lock()
        # self.folder = BillConfig().get_value('folder.cache', '/tmp/cache/')
        # os.makedirs(self.folder, exist_ok=True)

    def hash(self, key):
        return hashlib.md5(key.encode('utf-8')).hexdigest()

    # def cleanup(self):
    #     cstamp = time.time()
    #     for cfpath in glob.glob(self.folder+'/*'):
    #         req_del = False
    #         with codecs.open(cfpath, encoding='utf-8') as fd:
    #             try:
    #                 cache = SJson.to_deserial(fd.read())
    #             except Exception:
    #                 req_del = True
    #                 self.eprint(f'Cache Read Error file:{cfpath}')
    #             if req_del is False and cache['stamp'] < cstamp:
    #                 req_del = True
    #         if req_del:
    #             self.dprint(f'Delete {cfpath}')
    #             os.remove(cfpath)
    #     self.flush()

    # def flush(self):
    #     with self.lock:
    #         for k, v in self._cache.items():
    #             cfpath = self.get_cache_file(k)
    #             err = False
    #             if os.path.exists(cfpath):
    #                 os.remove(cfpath)
    #             if v['stamp'] < time.time():
    #                 continue
    #             with codecs.open(cfpath, mode='w', encoding='utf-8') as fd:
    #                 try:
    #                     fd.write(SJson.to_serial(v, indent=2))
    #                 except Exception:
    #                     err = True
    #             if err:
    #                 self.eprint(f'Cache Write Error key:{k} file:{cfpath}')
    #                 os.rename(cfpath, cfpath+'.werr')

    def clear(self, hkey=None):
        with self.lock:
            if hkey is None:
                self._cache = {}
                return
            if hkey in self._cache:
                del self._cache[hkey]
                return
        raise KeyError(f'Not Exist HASH Key: {hkey}')

    # def get_cache_file(self, hkey):
    #     return f'{self.folder}/{hkey}'

    def is_valid(self, hkey):
        self.remove_expired()
        with self.lock:
            if hkey in self._cache:
                if self._cache[hkey]['stamp'] >= time.time():
                    return True
        return False

    def set_cache(self, key, value, **kwargs):
        '''
        :param duration:    duration time, unit is second.
        '''
        duration = kwargs.get('duration', self.DURATION)
        hkey = self.hash(key)
        self._cache[hkey] = {
            'key': key,
            'duration': duration,
            'stamp': time.time() + duration,
            'value': value
        }

    def get_cache(self, key):
        hkey = self.hash(key)
        self.dprint(f'Cache key: {hkey}@"{key}"')
        if self.is_valid(hkey):
            with self.lock:
                return self._cache[hkey]['value']
        # cfpath = self.get_cache_file(hkey)
        # if os.path.exists(cfpath):
        #     data = None
        #     with codecs.open(cfpath, encoding='utf-8') as fd:
        #         try:
        #             data = SJson.to_deserial(fd.read())
        #         except Exception:
        #             self.eprint(f'Cache Read Error key:{key} file:{cfpath}')
        #             return self.NO_DATA
        #     with self.lock:
        #         self._cache[hkey] = data
        #     os.remove(cfpath)
        #     return self.get_cache(key)
        return self.NO_DATA

    def caching(self, key, generate_data, **kwargs):
        '''
        :param duration:    duration time, unit is second.
        :param cast:        a cast function which it call with the cached data.
        '''
        # self.DEBUG = True
        cast = kwargs.get('cast', None)
        noneable = kwargs.get('nonable', False)
        fg_hit = True
        data = self.get_cache(key)
        if data == self.NO_DATA:
            fg_hit = False
            data = generate_data()
            if data is None and noneable is False:
                raise FCache.ExceptionNoData(f'key: {key}')
            self.set_cache(key, data, **kwargs)
        if cast and hasattr(cast, '__call__'):
            data = cast(data)
        # Delete Cache, QueryData.fields is 0
        if type(data) is QueryData and len(data.fields) == 0:
            self.clear(self.hash(key))
        self.dprint(f'Cache@{fg_hit} "{key}"')
        return data

    def remove_expired(self):
        cstamp = time.time()
        with self.lock:
            self._cache = \
                {k: v for k, v in self._cache.items() if v['stamp'] >= cstamp}
