# -*- coding: utf-8 -*-

import atexit
import datetime
import glob
import traceback
import multiprocessing
import os
import time
import queue
import threading

from dateutil.relativedelta import relativedelta

from pysp.sbasic import SSingleton
from pysp.serror import SCDebug

from web.report import computealgo, Notice

from core.model import Dict
from core.config import BillConfig
from core.finance import DataCollection


@atexit.register
def _exit_manager():
    if Collector in SSingleton._instances:
        Collector("NO_COLLECT").quit()


class Manager(SCDebug):

    def __init__(self, *args, **kwargs):
        super(Manager, self).__init__()
        self.lock = threading.Lock()


class _State(SCDebug):
    DEBUG = False

    def __init__(self):
        super(_State, self).__init__()
        self.loop = True
        self.wcode = []
        self.dprint(f'------------------- {id(self)} {id(self.wcode)}')

    def quit(self):
        self.loop = False

    def is_run(self):
        return self.loop

    def set_work_code(self, code):
        self.dprint(f'###########B {id(self.wcode)} {self.wcode}=[{code}]')
        self.wcode.append(code)
        self.wcode = list(set(self.wcode))
        self.dprint(f'###########A {id(self.wcode)} {self.wcode}=[{code}]')

    def clear_work_code(self, code):
        self.dprint('## B clear_work_code', code, str(self.wcode))
        if code in self.wcode:
            idx = self.wcode.index(code)
            self.wcode.pop(idx)
        self.dprint('## A clear_work_code', str(self.wcode))


class _Scheduler(SCDebug):
    EVENT_COLLECT = "EvtCollect"
    EVENT_HOUR = "EvtHour"
    collect_hour = 18
    collect_min = 35
    debugging = False

    class Event:
        def __init__(self, event, stamp):
            self.event = event
            self.stamp = stamp

    @classmethod
    def next(cls):
        now = datetime.datetime.now()
        ecollect = cls.next_collect(now)
        ehour = cls.next_hour(now)
        event = ecollect if ecollect.stamp < ehour.stamp else ehour
        stamp = int(now.timestamp() - event.stamp)
        cls.iprint(f'Next Event: {event.event} after {stamp} second')
        return event

    @classmethod
    def next_collect(cls, now=None):
        if now is None:
            now = datetime.datetime.now()
        next = datetime.datetime(now.year, now.month, now.day, cls.collect_hour, cls.collect_min)
        if (next.timestamp() - now.timestamp()) > 0:
            return cls.Event(cls.EVENT_COLLECT, next.timestamp())

        next = next + relativedelta(days=1)
        return cls.Event(cls.EVENT_COLLECT, next.timestamp())

    @classmethod
    def next_hour(cls, now=None):
        if now is None:
            now = datetime.datetime.now()
        # next = now + relativedelta(minutes=1, seconds=(59-now.second))
        if _Scheduler.debugging:
            # For debugging, every 10 minutes.
            minute = 10-(now.minute%10)
            next = now + relativedelta(minutes=minute,seconds=(59-now.second))
        else:
            next = now + relativedelta(minutes=(60-now.minute),seconds=(59-now.second))
        print('@@@', next)
        return cls.Event(cls.EVENT_HOUR, next.timestamp())


class Collector(Manager, metaclass=SSingleton):
    DEBUG = True
    INIT_NO_COLLECT = "NO_COLLECT"
    CMD_QUIT = 'quit'
    QUEUE_SIZE = 1000
    QUEUE_TIMEOUT_SEC = 1
    # class
    # State = _State
    Scheduler = _Scheduler

    def __init__(self, *args, **kwargs):
        super(Collector, self).__init__(*args, **kwargs)
        self.stock_folder = BillConfig().get_value('config.db.stock.folder')
        self._q = queue.Queue()
        self.state = _State()
        self._thread = threading.Thread(target=self.worker)
        self._thread.start()
        if self.INIT_NO_COLLECT not in args:
            if 'DEBUG_PYTHON' not in os.environ:
                self.collect(None)

    def push(self, code):
        if self.is_exist(code) is False:
            if code == self.CMD_QUIT:
                with self._q.mutex:
                    self._q.queue.clear()
            self.dprint(f'PUT: {code}')
            self._q.put(code)

    def pop(self):
        return self._q.get(timeout=self.QUEUE_TIMEOUT_SEC)

    def is_exist(self, code):
        return True if code in self._q.queue else False

    def collect(self, code):
        if code is None:
            for file in glob.glob(self.stock_folder+'/*.sqlite3'):
                code = os.path.basename(file).split('.')[0]
                self.push(code)
            return
        self.push(code)

    def quit(self):
        self.state.quit()
        self.collect(self.CMD_QUIT)

    def is_working(self, code):
        # return self.state.is_working(code)
        self.dprint(f'### {id(self.state.wcode)} {self.state.wcode} {code}')
        if code in self.state.wcode:
            return True
        return False

    def _do_event_collect(self):
        self.dprint("### [START] collect")
        self.collect(None)
        self.dprint("### [E N D] collect")

    def _do_event_hour(self):
        def do_notify():
            notice = Notice()
            try:
                self.dprint("### [START] notice")
                notice.dispatch()
                self.dprint("### [E N D] notice")
            except:
                self.dprint('---------------------------------------')
                self.dprint(traceback.format_exc())
            del notice

        now = datetime.datetime.now()
        self.iprint(f'EVENT HOUR {datetime.datetime.now()} {id(self)}')
        if _Scheduler.debugging:
            # For debugging, run it every 10 minutes
            computealgo.compute_all()
            do_notify()
        elif now.weekday() not in [5, 6]:
            if now.hour in range(9, 20):
                self.dprint("### [START] computalgo")
                computealgo.compute_all()
                self.dprint("### [E N D] computalgo")
            if now.hour in [10, 13, 16]:
                do_notify()

    def _worker_event(self):
        curtime = time.time()
        # print(self.event.stamp, curtime)
        if self.event.stamp < curtime:
            event = self.Scheduler.next()
            self.iprint(f'EVENT@{self.event.event}')
            if self.event.event == self.Scheduler.EVENT_COLLECT:
                self._do_event_collect()
            if self.event.event == self.Scheduler.EVENT_HOUR:
                self._do_event_hour()
            self.event = event

    def _worker_item(self, code):
        self.state.set_work_code(code)
        # DataCollection.collect(code, wstate=self.state)
        # self.state.clear_work_code(code)

    def _worker_item_process(self):
        def gen_params():
            for code in self.state.wcode:
                param = Dict()
                param.code = code
                param.kwargs.wstate = self.state
                yield param
            return []

        if self._q.empty() and self.state.wcode:
            cpu = multiprocessing.cpu_count()
            pool = multiprocessing.Pool(processes=cpu)
            for code in pool.imap(DataCollection.multiprocess_collect, gen_params()):
                print('@@ Done', code)
                self.state.clear_work_code(code)
            print("@@ All Done")

    def worker(self, *args):
        self.dprint("<Collector::worker(begin)>")
        self.event = self.Scheduler.next()

        while self.state.is_run():
            try:
                item = self.pop()
                self.dprint(f'GET: "{item}"')
            except queue.Empty:
                item = ''
            if self.is_exist(self.CMD_QUIT) or \
                    self.state.is_run() is False or \
                    item == self.CMD_QUIT:
                break
            
            self._worker_event()
            if not item:
                self._worker_item_process()
            else:
                self._worker_item(item)

        self.dprint("<Collector::worker(end)>")
