# -*- coding: utf-8 -*-

import atexit
import glob
import os
import queue
import threading

from pysp.sbasic import SSingleton
from pysp.serror import SCDebug

from core.config import BillConfig
from core.finance import DataCollection


@atexit.register
def _exit_manager():
    if Collector in SSingleton._instances:
        Collector("NONE").quit()


class Manager(SCDebug):

    def __init__(self, *args, **kwargs):
        super(Manager, self).__init__()
        self.lock = threading.Lock()


class _State:
    def __init__(self, thread):
        self.loop = True
        self.thread = thread
        self.work_code = None

    def quit(self):
        self.loop = False

    def is_run(self):
        return self.loop

    def set_work_code(self, code):
        self.work_code = code

    def is_working(self, code):
        if code is None:
            return True if self.work_code is None else False
        if code == self.work_code:
            return True
        return False


class Collector(Manager, metaclass=SSingleton):
    DEBUG = True
    CMD_QUIT = 'quit'
    QUEUE_SIZE = 100
    State = _State

    def __init__(self, *args, **kwargs):
        super(Collector, self).__init__(*args, **kwargs)
        self.stock_folder = BillConfig().get_value('_config.db.stock_folder')
        self._q = queue.Queue()
        self.state = self.State(threading.Thread(target=self.worker, args=()))
        self.state.thread.start()
        if 'NONE' not in args:
            self.collect(None)

    def collect(self, code):
        if code is None:
            for file in glob.glob(self.stock_folder+'/*.sqlite3'):
                code = os.path.basename(file).split('.')[0]
                self.dprint(f'PUT: {code}')
                self._q.put(code)
            return
        self.dprint(f'PUT: "{code}"')
        self._q.put(code)

    def quit(self):
        self.collect(self.CMD_QUIT)
        self.state.quit()

    def is_working(self, code):
        return self.state.is_working(code)

    def worker(self, *args):
        self.dprint("<Collector::worker(begin)>")
        while self.state.is_run():
            try:
                item = self._q.get(timeout=3)
            except queue.Empty:
                item = ''
            if item:
                self.dprint(f'GET: "{item}"')
            if self.state.is_run() is False or item == self.CMD_QUIT:
                break
            if item:
                self.state.set_work_code(item)
                DataCollection.collect(item, wstate=self.state)
                self.state.set_work_code(None)
            # TODO: others
        self.dprint("<Collector::worker(end)>")
