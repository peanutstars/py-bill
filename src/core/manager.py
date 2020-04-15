# -*- coding: utf-8 -*-

import atexit
import datetime
import glob
import traceback
import multiprocessing
import os
import sys
import signal
import time
import queue
import threading

from dateutil.relativedelta import relativedelta
from collections import namedtuple

from pysp.sbasic import SSingleton, Dict
from pysp.serror import SCDebug

from web.report import computealgo, Notice

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

    def get_work_codes(self):
        return list(self.wcode)


class _Scheduler(SCDebug):
    DEBUG = True

    class Event(Dict):
        def __init__(self, event, stamp, offset, time):
            self.event = event
            self.stamp = stamp
            self.offset = offset
            self.time = time

    Time = namedtuple('Time', 'hour min')

    EVENT_HOUR        = "EvtHour"
    EVENT_NOTIFY      = "EvtNotify"
    EVENT_COLLECT     = "EvtCollect"

    event = Dict()
    event.EvtHour =    [Time(9,  5), Time(10,  5), Time(11,  5), Time(12,  5), Time(13, 5),
                        Time(14, 5), Time(15,  5), Time(16,  5), Time(17,  5), Time(18, 5)]
    event.EvtNotify =  [Time(9, 30), Time(11, 30), Time(13, 30), Time(16, 45)]
    event.EvtCollect = [Time(4, 30), Time(18, 55)]

    @classmethod
    def skip_timestamp(cls, nowstamp, edt):
        '''
        Get timestamp to skip holidays
        
        Args
            :nowstamp int/float:  Value of now.timestamp()
            :edt      datetime:   datetime object for event

        Return
            :int/float: timestamp to have skipped holidays
        '''
        evtstamp = edt.timestamp()
        while (evtstamp - nowstamp) < 0 or edt.weekday() in [5, 6]:
            edt = edt + datetime.timedelta(days=1)
            evtstamp = edt.timestamp()
        return edt.timestamp()

    @classmethod
    def next(cls, now):
        '''
        Get the event which has an event name and a timestamp.

        Args
            :now datetime:      object datetime.now()
        
        Return
            :Event:             return cls.Event
        '''
        nstamp = now.timestamp()
        nexti = cls.Event(None, None, sys.maxsize, None)
        for evt, items in cls.event.items():
            for t in items:
                edt = datetime.datetime(now.year, now.month, now.day, t.hour, t.min)
                tstamp = cls.skip_timestamp(nstamp, edt)               
                if not nexti.stamp:
                    nexti.event = evt
                    nexti.stamp = tstamp
                    logmsg = "{} {} {} {} {} : {}".format(nexti.offset, nstamp, nexti.stamp, tstamp, t, tstamp - nstamp)
                    cls.dprint(logmsg)
                    continue
                if (tstamp - nstamp) < nexti.offset:
                    nexti.stamp = tstamp
                    nexti.event = evt
                    nexti.offset = tstamp - nstamp
                    nexti.time = t
                logmsg = "{} {} {} {} {} : {}".format(nexti.offset, nstamp, nexti.stamp, tstamp, t, tstamp - nstamp)
                cls.dprint(logmsg)
        cls.dprint("--------->>>", str(nexti))
        return nexti


class Collector(Manager, metaclass=SSingleton):
    DEBUG = True
    INIT_NO_COLLECT =   "NO_COLLECT"
    CMD_QUIT =          'quit'
    QUEUE_SIZE =        1000
    QUEUE_TIMEOUT_SEC = 1
    HOLIDAYS =          [5, 6]
    NOTIFY_HOURS =      [10, 13, 16]
    WORK_HOURS =        range(9, 20)
    # class
    # State = _State
    Scheduler = _Scheduler

    def __init__(self, *args, **kwargs):
        super(Collector, self).__init__(*args, **kwargs)
        self.stock_folder = BillConfig().get_value('config.db.stock.folder')
        self._q = queue.Queue()
        self.need_notify = False
        self.state = _State()
        self._thread = threading.Thread(target=self.worker)
        self._thread.start()
        if self.INIT_NO_COLLECT not in args:
            if 'DEBUG' not in os.environ:
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

    # def _do_event_hour(self):
    #     def do_notify():
    #         notice = Notice()
    #         try:
    #             self.dprint("### [START] notice")
    #             notice.dispatch()
    #             self.dprint("### [E N D] notice")
    #         except:
    #             self.dprint('---------------------------------------')
    #             self.dprint(traceback.format_exc())
    #         del notice

    #     now = datetime.datetime.now()
    #     self.iprint(f'EVENT HOUR {datetime.datetime.now()} {id(self)}')
    #     if _Scheduler.debug:
    #         # For debugging, run it every 10 minutes
    #         computealgo.compute_all()
    #         do_notify()
    #     elif now.weekday() not in self.HOLIDAYS:
    #         if now.hour in self.NOTIFY_HOURS:
    #             self.need_notify = True
    #         if now.hour in self.WORK_HOURS:
    #             self.dprint("### [START] computalgo")
    #             try:
    #                 computealgo.compute_all()
    #             except Exception as e:
    #                 self.dprint(f'Skip to Compute Algo, Error[{str(e)}]')
    #                 return
    #             self.dprint("### [E N D] computalgo")
    #         if self.need_notify:
    #             # go to do this, even if it has an error previously in computing algo.
    #             do_notify()
    #             self.need_notify = False

    def _do_event_hour(self):
        self.iprint(f'EVENT HOUR {datetime.datetime.now()} {id(self)}')
        self.dprint("### [START] computalgo")
        try:
            computealgo.compute_all()
        except Exception as e:
            self.dprint(f'### [ERROR] Skip to Compute Algo - {str(e)}')
            return
        self.dprint("### [E N D] computalgo")

    def _do_event_notify(self):
        notice = Notice()
        self.dprint("### [START] notice")
        try:
            self.need_notify = True
            notice.dispatch()
        except:
            self.dprint('[ERROR] notice.dispatch')
            self.dprint(traceback.format_exc())
        self.dprint("### [E N D] notice")
        self.need_notify = False
        del notice
        

    def _worker_event(self):
        curtime = time.time()
        # print(self.event.stamp, curtime)
        if self.event.stamp < curtime:
            event = self.Scheduler.next(datetime.datetime.now())
            self.iprint(f'EVENT@{self.event.event}')
            if self.event.event == self.Scheduler.EVENT_COLLECT:
                self._do_event_collect()
            if self.event.event in [self.Scheduler.EVENT_HOUR, self.Scheduler.EVENT_NOTIFY]:
                self._do_event_hour()
            if self.need_notify or self.event.event == self.Scheduler.EVENT_NOTIFY:
                self._do_event_notify()
            self.event = event

    def _worker_item(self, code):
        self.state.set_work_code(code)
        # DataCollection.collect(code, wstate=self.state)
        # self.state.clear_work_code(code)

    def _worker_item_process(self):
        def gen_params():
            for code in wcodes:
                param = Dict()
                param.code = code
                param.kwargs.wstate = self.state
                yield param
            return []

        if self._q.empty() and self.state.wcode:
            wcodes = self.state.get_work_codes()
            cpu = multiprocessing.cpu_count()
            pool = multiprocessing.Pool(processes=cpu)
            for code in pool.imap(DataCollection.multiprocess_collect, gen_params()):
                print('@@ Done', code)
                self.state.clear_work_code(code)
            print("@@ All Done")

    def worker(self, *args):
        self.dprint("<Collector::worker(begin)>")
        self.event = self.Scheduler.next(datetime.datetime.now())

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
            
            try:
                self._worker_event()
                if not item:
                    self._worker_item_process()
                else:
                    self._worker_item(item)
            except Exception:
                os.kill(os.getpid(), signal.SIGHUP)

        self.dprint("<Collector::worker(end)>")
