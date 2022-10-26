# -*- mode: python; indent-tabs-mode: nil; py-indent-offset: 4; coding: utf-8 -*-
import sys
import threading
import queue
from PyQt5 import QtCore

from bootstrap.bootstrap import *
from bootstrap.bootstrap import download_nodes_list
from wrapper.toxcore_enums_and_consts import TOX_USER_STATUS, TOX_CONNECTION
import wrapper_tests.support_testing as ts
from utils import util

import time
sleep = time.sleep

# LOG=util.log
global LOG
import logging
LOG = logging.getLogger('app.'+'threads')
# log = lambda x: LOG.info(x)

def LOG_ERROR(l): print('EROR+ '+l)
def LOG_WARN(l):  print('WARN+ '+l)
def LOG_INFO(l):  print('INFO+ '+l)
def LOG_DEBUG(l): print('DBUG+ '+l)
def LOG_TRACE(l): pass # print('TRACE+ '+l)

iLAST_CONN = 0
iLAST_DELTA = 60

# -----------------------------------------------------------------------------------------------------------------
# Base threads
# -----------------------------------------------------------------------------------------------------------------

class BaseThread(threading.Thread):

    def __init__(self, name=None, target=None):
        self._stop_thread = False
        if name:
            super().__init__(name=name, target=target)
        else:
            super().__init__(target=target)

    def stop_thread(self, timeout=-1):
        self._stop_thread = True
        if timeout < 0:
            timeout = ts.iTHREAD_TIMEOUT
        i = 0
        while i < ts.iTHREAD_JOINS:
            self.join(timeout)
            if not self.is_alive(): break
            i = i + 1
        else:
            LOG_WARN(f"BaseThread {self.name} BLOCKED after {ts.iTHREAD_JOINS}")

class BaseQThread(QtCore.QThread):

    def __init__(self, name=None):
        # NO name=name
        super().__init__()
        self._stop_thread = False
        self.name = str(id(self))

    def stop_thread(self, timeout=-1):
        self._stop_thread = True
        if timeout < 0:
            timeout = ts.iTHREAD_TIMEOUT
        i = 0
        while i < ts.iTHREAD_JOINS:
            self.wait(timeout)
            if not self.isRunning(): break
            i = i + 1
            sleep(ts.iTHREAD_TIMEOUT)
        else:
            LOG_WARN(f"BaseQThread {self.name} BLOCKED")

# -----------------------------------------------------------------------------------------------------------------
# Toxcore threads
# -----------------------------------------------------------------------------------------------------------------

class InitThread(BaseThread):

    def __init__(self, tox, plugin_loader, settings, app, is_first_start):
        super().__init__(name='InitThread')
        self._tox = tox
        self._plugin_loader = plugin_loader
        self._settings = settings
        self._app = app
        self._is_first_start = is_first_start

    def run(self):
        # DBUG+ InitThread run: ERROR name 'ts' is not defined
        import wrapper_tests.support_testing as ts
        LOG_DEBUG('InitThread run: ')
        try:
            if self._is_first_start and ts.bAreWeConnected() and \
              self._settings['download_nodes_list']:
                LOG_INFO(f"downloading list of nodes {self._settings['download_nodes_list']}")
                download_nodes_list(self._settings, oArgs=self._app._args)

            if ts.bAreWeConnected():
                LOG_INFO(f"calling test_net nodes")
                self._app.test_net(oThread=self, iMax=4)

            if self._is_first_start:
                LOG_INFO('starting plugins')
                self._plugin_loader.load()

        except Exception as e:
            LOG_DEBUG(f"InitThread run: ERROR {e}")
            pass

        for _ in range(ts.iTHREAD_JOINS):
            if self._stop_thread:
                return
            sleep(ts.iTHREAD_SLEEP)
        return

class ToxIterateThread(BaseQThread):

    def __init__(self, tox, app=None):
        super().__init__()
        self._tox = tox
        self._app = app
        
    def run(self):
        LOG_DEBUG('ToxIterateThread run: ')
        while not self._stop_thread:
            try:
                iMsec = self._tox.iteration_interval()
                self._tox.iterate()
            except Exception as e:
                # Fatal Python error: Segmentation fault
                LOG_ERROR(f"ToxIterateThread run: {e}")
            else:
                sleep(iMsec / 1000.0)
                
            global iLAST_CONN
            if not iLAST_CONN:
                iLAST_CONN = time.time()
            # TRAC> TCP_common.c#203:read_TCP_packet recv buffer has 0 bytes, but requested 10 bytes

            # and segv
            if \
                time.time() - iLAST_CONN > iLAST_DELTA and \
                ts.bAreWeConnected() and \
                self._tox.self_get_status() == TOX_USER_STATUS['NONE'] and \
                self._tox.self_get_connection_status() == TOX_CONNECTION['NONE']:
                    iLAST_CONN = time.time()
                    LOG_INFO(f"ToxIterateThread calling test_net")
                    invoke_in_main_thread(
                        self._app.test_net, oThread=self, iMax=2)
                

class ToxAVIterateThread(BaseQThread):
    def __init__(self, toxav):
        super().__init__()
        self._toxav = toxav

    def run(self):
        LOG_DEBUG('ToxAVIterateThread run: ')
        while not self._stop_thread:
            self._toxav.iterate()
            sleep(self._toxav.iteration_interval() / 1000)


# -----------------------------------------------------------------------------------------------------------------
# File transfers thread
# -----------------------------------------------------------------------------------------------------------------

class FileTransfersThread(BaseQThread):

    def __init__(self):
        super().__init__('FileTransfers')
        self._queue = queue.Queue()
        self._timeout = 0.01

    def execute(self, func, *args, **kwargs):
        self._queue.put((func, args, kwargs))

    def run(self):
        while not self._stop_thread:
            try:
                func, args, kwargs = self._queue.get(timeout=self._timeout)
                func(*args, **kwargs)
            except queue.Empty:
                pass
            except queue.Full:
                LOG_WARN('Queue is full in _thread')
            except Exception as ex:
                LOG_ERROR('in _thread: ' + str(ex))


_thread = FileTransfersThread()
def start_file_transfer_thread():
    _thread.start()


def stop_file_transfer_thread():
    _thread.stop_thread()


def execute(func, *args, **kwargs):
    _thread.execute(func, *args, **kwargs)


# -----------------------------------------------------------------------------------------------------------------
# Invoking in main thread
# -----------------------------------------------------------------------------------------------------------------

class InvokeEvent(QtCore.QEvent):
    EVENT_TYPE = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())

    def __init__(self, fn, *args, **kwargs):
        QtCore.QEvent.__init__(self, InvokeEvent.EVENT_TYPE)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs


class Invoker(QtCore.QObject):

    def event(self, event):
        event.fn(*event.args, **event.kwargs)
        return True


_invoker = Invoker()


def invoke_in_main_thread(fn, *args, **kwargs):
    QtCore.QCoreApplication.postEvent(_invoker, InvokeEvent(fn, *args, **kwargs))
