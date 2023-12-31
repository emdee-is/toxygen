#!/var/local/bin/python3.bash
#
""" echo.py features
 - accept friend request
 - echo back friend message
 - accept and answer friend call request
 - send back friend audio/video data
 - send back files friend sent
"""

from __future__ import print_function

import sys
import os
import traceback
import random
from ctypes import *
import argparse

import time
from os.path import exists

# LOG=util.log
global LOG
import logging
# log = lambda x: LOG.info(x)
LOG = logging.getLogger('app')
def LOG_error(a): print('EROR_ '+a)
def LOG_warn(a):  print('WARN_ '+a)
def LOG_info(a):  print('INFO_ '+a)
def LOG_debug(a): print('DBUG_ '+a)
def LOG_trace(a): pass # print('TRAC_ '+a)

from middleware.tox_factory import tox_factory
import wrapper
import wrapper.toxcore_enums_and_consts as enums
from wrapper.toxcore_enums_and_consts import TOX_CONNECTION, TOX_USER_STATUS, \
    TOX_MESSAGE_TYPE, TOX_PUBLIC_KEY_SIZE, TOX_FILE_CONTROL
import user_data
from wrapper.libtox import LibToxCore
import wrapper_tests.support_testing as ts
from wrapper_tests.support_testing import oMainArgparser
from wrapper_tests.support_testing import logging_toxygen_echo

def sleep(fSec):
    if 'QtCore' in globals():
        if fSec > .000001: globals['QtCore'].QThread.msleep(fSec)
        globals['QtCore'].QCoreApplication.processEvents()
    else:
        time.sleep(fSec)

try:
    import coloredlogs
    if 'COLOREDLOGS_LEVEL_STYLES' not in os.environ:
        os.environ['COLOREDLOGS_LEVEL_STYLES'] = 'spam=22;debug=28;verbose=34;notice=220;warning=202;success=118,bold;error=124;critical=background=red'
except ImportError as e:
    # logging.log(logging.DEBUG, f"coloredlogs not available:  {e}")
    coloredlogs = None

import wrapper_tests.support_testing as ts
if 'USER' in os.environ:
    sDATA_FILE = '/tmp/logging_toxygen_' +os.environ['USER'] +'.tox'
elif 'USERNAME' in os.environ:
    sDATA_FILE = '/tmp/logging_toxygen_' +os.environ['USERNAME'] +'.tox'
else:
    sDATA_FILE = '/tmp/logging_toxygen_' +'data' +'.tox'

bHAVE_AV = True
iDHT_TRIES = 100
iDHT_TRY = 0

#?SERVER = lLOCAL[-1]

class AV(wrapper.tox.ToxAV):
    def __init__(self, core):
        super(AV, self).__init__(core)
        self.core = self.get_tox()

    def on_call(self, fid, audio_enabled, video_enabled):
        LOG.info("Incoming %s call from %d:%s ..." % (
            "video" if video_enabled else "audio", fid,
            self.core.friend_get_name(fid)))
        bret = self.answer(fid, 48, 64)
        LOG.info(f"Answered, in call... {bret!s}")

    def on_call_state(self, fid, state):
        LOG.info('call state:fn=%d, state=%d' % (fid, state))

    def on_audio_bit_rate(self, fid, audio_bit_rate):
        LOG.info('audio bit rate status: fn=%d, abr=%d' %
              (fid, audio_bit_rate))

    def on_video_bit_rate(self, fid, video_bit_rate):
        LOG.info('video bit rate status: fn=%d, vbr=%d' %
              (fid, video_bit_rate))

    def on_audio_receive_frame(self, fid, pcm, sample_count,
                               channels, sampling_rate):
        # LOG.info('audio frame: %d, %d, %d, %d' %
        #      (fid, sample_count, channels, sampling_rate))
        # LOG.info('pcm len:%d, %s' % (len(pcm), str(type(pcm))))
        sys.stdout.write('.')
        sys.stdout.flush()
        bret = self.audio_send_frame(fid, pcm, sample_count,
                                     channels, sampling_rate)
        if bret is False:
            LOG.error('on_audio_receive_frame error.')

    def on_video_receive_frame(self, fid, width, height, frame, u, v):
        LOG.info('video frame: %d, %d, %d, ' % (fid, width, height))
        sys.stdout.write('*')
        sys.stdout.flush()
        bret = self.video_send_frame(fid, width, height, frame, u, v)
        if bret is False:
            LOG.error('on_video_receive_frame error.')

    def witerate(self):
        self.iterate()


def save_to_file(tox, fname):
    data = tox.get_savedata()
    with open(fname, 'wb') as f:
        f.write(data)

def load_from_file(fname):
    assert os.path.exists(fname)
    return open(fname, 'rb').read()

class EchoBot():
    def __init__(self, oTox):
        self._tox = oTox
        self._tox.self_set_name("EchoBot")
        LOG.info('ID: %s' % self._tox.self_get_address())

        self.files = {}
        self.av = None
        self.on_connection_status = None

    def start(self):
        self.connect()
        if bHAVE_AV:
            # RuntimeError: Attempted to create a second session for the same Tox instance.

            self.av = True # AV(self._tox_pointer)
        def bobs_on_friend_request(iTox,
                                     public_key,
                                     message_data,
                                     message_data_size,
                                     *largs):
            key = ''.join(chr(x) for x in public_key[:TOX_PUBLIC_KEY_SIZE])
            sPk = wrapper.tox.bin_to_string(key, TOX_PUBLIC_KEY_SIZE)
            sMd = str(message_data, 'UTF-8')
            LOG.debug('on_friend_request ' +sPk +' ' +sMd)
            self.on_friend_request(sPk, sMd)
        LOG.info('setting bobs_on_friend_request')
        self._tox.callback_friend_request(bobs_on_friend_request)

        def bobs_on_friend_message(iTox,
                                   iFriendNum,
                                   iMessageType,
                                   message_data,
                                   message_data_size,
                                   *largs):
            sMd = str(message_data, 'UTF-8')
            LOG_debug(f"on_friend_message  {iFriendNum}" +' ' +sMd)
            self.on_friend_message(iFriendNum, iMessageType, sMd)
        LOG.info('setting bobs_on_friend_message')
        self._tox.callback_friend_message(bobs_on_friend_message)

        def bobs_on_file_chunk_request(iTox, fid, filenumber, position, length, *largs):
            if length == 0:
                return

            data = self.files[(fid, filenumber)]['f'][position:(position + length)]
            self._tox.file_send_chunk(fid, filenumber, position, data)
        self._tox.callback_file_chunk_request(bobs_on_file_chunk_request)

        def bobs_on_file_recv(iTox, fid, filenumber, kind, size, filename, *largs):
            LOG_info(f"on_file_recv {fid!s} {filenumber!s} {kind!s} {size!s} {filename}")
            if size == 0:
                return
            self.files[(fid, filenumber)] = {
                'f': bytes(),
                'filename': filename,
                'size': size
            }
            self._tox.file_control(fid, filenumber, TOX_FILE_CONTROL['RESUME'])


    def connect(self):
        if not self.on_connection_status:
            def on_connection_status(iTox, iCon, *largs):
                LOG_info('ON_CONNECTION_STATUS - CONNECTED ' + repr(iCon))
            self._tox.callback_self_connection_status(on_connection_status)
            LOG.info('setting on_connection_status callback ')
            self.on_connection_status = on_connection_status
        if self._oargs.network in ['newlocal', 'local']:
            LOG.info('connecting on the new network ')
            sNet = 'newlocal'
        elif self._oargs.network == 'new':
            LOG.info('connecting on the new network ')
            sNet = 'new'
        else: # main old
            LOG.info('connecting on the old network ')
            sNet = 'old'
        sFile = self._oargs.nodes_json
        lNodes = generate_nodes_from_file(sFile)
        lElts = lNodes
        random.shuffle(lElts)
        for lElt in lElts[:10]:
            status = self._tox.self_get_connection_status()
            try:
                if self._tox.bootstrap(*lElt):
                    LOG.info('connected to ' + lElt[0]+' '+repr(status))
                else:
                    LOG.warn('failed connecting to ' + lElt[0])
            except Exception as e:
                LOG.warn('error connecting to ' + lElt[0])

        if self._oargs.proxy_type > 0:
            random.shuffle(ts.lRELAYS)
            for lElt in ts.lRELAYS[:10]:
                status = self._tox.self_get_connection_status()
                try:
                    if self._tox.add_tcp_relay(*lElt):
                        LOG.info('relayed to ' + lElt[0] +' '+repr(status))
                    else:
                        LOG.warn('failed relay to ' + lElt[0])
                except Exception as e:
                    LOG.warn('error relay to ' + lElt[0])

    def loop(self):
        if not self.av:
            self.start()
        checked = False
        save_to_file(self._tox, sDATA_FILE)

        LOG.info('Starting loop.')
        while True:

            status = self._tox.self_get_connection_status()
            if not checked and status:
                LOG.info('Connected to DHT.')
                checked = True
            if not checked and not status:
                global iDHT_TRY
                iDHT_TRY += 10
                self.connect()
                self.iterate(100)
                if iDHT_TRY >= iDHT_TRIES:
                    raise RuntimeError("Failed to connect to the DHT.")
                LOG.warn(f"NOT Connected to DHT. {iDHT_TRY}")
                checked = True
            if checked and not status:
                LOG.info('Disconnected from DHT.')
                self.connect()
                checked = False

            if bHAVE_AV:
                True # self.av.witerate()
            self.iterate(100)

        LOG.info('Ending loop.')

    def iterate(self, n=100):
        interval = self._tox.iteration_interval()
        for i in range(n):
            self._tox.iterate()
            sleep(interval / 1000.0)
            self._tox.iterate()

    def on_friend_request(self, pk, message):
        LOG.debug('Friend request from %s: %s' % (pk, message))
        self._tox.friend_add_norequest(pk)
        LOG.info('on_friend_request Accepted.')
        save_to_file(self._tox, sDATA_FILE)

    def on_friend_message(self, friendId, type, message):
        name = self._tox.friend_get_name(friendId)
        LOG.debug('%s: %s' % (name, message))
        yMessage = bytes(message, 'UTF-8')
        self._tox.friend_send_message(friendId, TOX_MESSAGE_TYPE['NORMAL'], yMessage)
        LOG.info('EchoBot sent: %s' % message)

    def on_file_recv_chunk(self, fid, filenumber, position, data):
        filename = self.files[(fid, filenumber)]['filename']
        size = self.files[(fid, filenumber)]['size']
        LOG.debug(f"on_file_recv_chunk {fid!s} {filenumber!s} {filename} {position/float(size)*100!s}")

        if data is None:
            msg = "I got '{}', sending it back right away!".format(filename)
            self._tox.friend_send_message(fid, TOX_MESSAGE_TYPE['NORMAL'], msg)

            self.files[(fid, 0)] = self.files[(fid, filenumber)]

            length = self.files[(fid, filenumber)]['size']
            self.file_send(fid, 0, length, filename, filename)

            del self.files[(fid, filenumber)]
            return

        self.files[(fid, filenumber)]['f'] += data

def iMain(oArgs):
    global sDATA_FILE
    # oTOX_OPTIONS = ToxOptions()
    global oTOX_OPTIONS
    oTOX_OPTIONS = oToxygenToxOptions(oArgs)
    opts = oTOX_OPTIONS
    if coloredlogs:
        coloredlogs.install(
                            level=oArgs.loglevel,
                            logger=LOG,
                            # %(asctime)s,%(msecs)03d %(hostname)s [%(process)d]
                            fmt='%(name)s %(levelname)s %(message)s'
                        )
    else:
        if 'logfile' in oArgs:
            logging.basicConfig(filename=oArgs.logfile,
                                level=oArgs.loglevel,
                                format='%(levelname)-8s %(message)s')
        else:
            logging.basicConfig(level=oArgs.loglevel,
                                format='%(levelname)-8s %(message)s')

    iRet = 0
    if hasattr(oArgs,'profile') and oArgs.profile and os.path.isfile(oArgs.profile):
        sDATA_FILE = oArgs.profile
        LOG.info(f"loading from  {sDATA_FILE}")
        opts.savedata_data = load_from_file(sDATA_FILE)
        opts.savedata_length = len(opts.savedata_data)
        opts.savedata_type = enums.TOX_SAVEDATA_TYPE['TOX_SAVE']
    else:
        opts.savedata_data = None

    try:
        if False:
            oTox = tox_factory(data=opts.savedata_data,
                        settings=opts, args=oArgs, app=None)
        else:
            oTox = wrapper.tox.Tox(opts)
        t = EchoBot(oTox)
        t._oargs = oArgs
        t.start()
        t.loop()
        save_to_file(t._tox, sDATA_FILE)
    except KeyboardInterrupt:
        save_to_file(t._tox, sDATA_FILE)
    except RuntimeError as e:
        LOG.error(f"exiting with  {e}")
        iRet = 1
    except Exception as e:
        LOG.error(f"exiting with  {e}")
        LOG.warn(' iMain(): ' \
                     +'\n' + traceback.format_exc())
        iRet = 1
    return iRet

def oToxygenToxOptions(oArgs, data=None):
    tox_options = wrapper.tox.Tox.options_new()

    tox_options.contents.local_discovery_enabled = False
    tox_options.contents.dht_announcements_enabled = False
    tox_options.contents.hole_punching_enabled = False
    tox_options.contents.experimental_thread_safety = False
    tox_options.contents.ipv6_enabled = False
    tox_options.contents.tcp_port = 3390

    if oArgs.proxy_type > 0:
        tox_options.contents.proxy_type = int(oArgs.proxy_type)
        tox_options.contents.proxy_host = bytes(oArgs.proxy_host, 'UTF-8')
        tox_options.contents.proxy_port = int(oArgs.proxy_port)
        tox_options.contents.udp_enabled = False
        LOG.debug('setting oArgs.proxy_host = ' +oArgs.proxy_host)
    else:
        tox_options.contents.udp_enabled = True

    if data:  # load existing profile
        tox_options.contents.savedata_type = enums.TOX_SAVEDATA_TYPE['TOX_SAVE']
        tox_options.contents.savedata_data = c_char_p(data)
        tox_options.contents.savedata_length = len(data)
    else:  # create new profile
        tox_options.contents.savedata_type = enums.TOX_SAVEDATA_TYPE['NONE']
        tox_options.contents.savedata_data = None
        tox_options.contents.savedata_length = 0

    if tox_options._options_pointer:
        ts.vAddLoggerCallback(tox_options, ts.on_log)
    else:
        logging.warn("No tox_options._options_pointer " +repr(tox_options._options_pointer))

    return tox_options

def oArgparse(lArgv):
    parser = ts.oMainArgparser()
    parser.add_argument('profile', type=str, nargs='?',
                        default=sDATA_FILE,
                        help='Path to Tox profile to save')
    oArgs = parser.parse_args(lArgv)
    if hasattr(oArgs, 'sleep') and oArgs.sleep == 'qt':
        pass # broken
    else:
        oArgs.sleep = 'time'
    for key in ts.lBOOLEANS:
        if key not in oArgs: continue
        val = getattr(oArgs, key)
        if val in ['False', 'false', 0]:
            setattr(oArgs, key, False)
        else:
            setattr(oArgs, key, True)
    if not os.path.exists('/proc/sys/net/ipv6') and oArgs.ipv6_enabled:
        LOG.warn('setting oArgs.ipv6_enabled = False')
        oArgs.ipv6_enabled = False
    return oArgs

def main(largs=None):
    if largs is None: largs = []
    oArgs = oArgparse(largs)
    global     oTOX_OARGS
    oTOX_OARGS = oArgs
    print(oArgs)

    if coloredlogs:
        logger = logging.getLogger()
        # https://pypi.org/project/coloredlogs/
        coloredlogs.install(level=oArgs.loglevel,
                        logger=logger,
                        # %(asctime)s,%(msecs)03d %(hostname)s [%(process)d]
                        fmt='%(name)s %(levelname)s %(message)s'
                        )
    else:
        logging.basicConfig(level=oArgs.loglevel) #  logging.INFO

    return iMain(oArgs)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
