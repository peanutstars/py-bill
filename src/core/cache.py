
import codecs
import hashlib
import os
import time

from pysp.sbasic import SSingleton
from pysp.serror import SDebug
from pysp.sjson import SJson

from core.config import BillConfig


class FileCache(SDebug, metaclass=SSingleton):
    DURATION = 3600

    def __init__(self):
        self._cache = {}
        self.folder = BillConfig().get_value('folder.cache', '/tmp/cache/')
        os.makedirs(self.folder, exist_ok=True)

    def __del__(self):
        self.flush_to_file()

    def hash(self, key):
        return hashlib.md5(key.encode('utf-8')).hexdigest()

    def flush_to_file(self):
        for k, v in self._cache.items():
            cfpath = self.get_cache_file(k)
            err = False
            if os.path.exists(cfpath):
                os.remove(cfpath)
            if v['stamp'] < time.time():
                continue
            with codecs.open(cfpath, mode='w', encoding='utf-8') as fd:
                try:
                    fd.write(SJson.to_serial(v))
                except Exception:
                    err = True
            if err:
                self.eprint(f'Cache Write Error key:{k} file:{cfpath}')
                os.rename(cfpath, cfpath+'.werr')

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
        self.remove_expired()
        duration = kwargs.get('duration', self.DURATION)
        self._cache[key] = {
            'key': key,
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
                    os.rename(cfpath, cfpath+'.rerr')
                    return None
            os.remove(cfpath)
            return self.get_cache(key)
        return None

    def remove_expired(self):
        cstamp = time.time()
        self._cache = \
            {k: v for k, v in self._cache.items() if v['stamp'] >= cstamp}
