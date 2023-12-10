# -*- mode: python; indent-tabs-mode: nil; py-indent-offset: 4; coding: utf-8 -*-
import sys
import os
import app
import argparse
import logging
import signal

import faulthandler
faulthandler.enable()

import warnings
warnings.filterwarnings('ignore')

import wrapper_tests.support_testing as ts
try:
    from trepan.interfaces import server as Mserver
    from trepan.api import debug
except:
    print('trepan3 TCP server NOT enabled.')
else:
    import signal
    try:
        signal.signal(signal.SIGUSR1, ts.trepan_handler)
        print('trepan3 TCP server enabled on port 6666.')
    except: pass

from user_data.settings import *
from user_data.settings import Settings
from user_data import settings
import utils.util as util
with ts.ignoreStderr():
    import pyaudio

__maintainer__ = 'Ingvar'
__version__ = '0.5.0+'

import time
sleep = time.sleep

def reset():
    Settings.reset_auto_profile()

def clean():
    """Removes libs folder"""
    directory = util.get_libs_directory()
    util.remove(directory)

def print_toxygen_version():
    print('Toxygen ' + __version__)

def setup_default_audio():
    # need:
    audio = ts.get_audio()
    # unfinished
    global oPYA
    oPYA = pyaudio.PyAudio()
    audio['output_devices'] = dict()
    i = oPYA.get_device_count()
    while i > 0:
        i -= 1
        if oPYA.get_device_info_by_index(i)['maxOutputChannels'] == 0:
            continue
        audio['output_devices'][i] = oPYA.get_device_info_by_index(i)['name']
    i = oPYA.get_device_count()
    audio['input_devices'] = dict()
    while i > 0:
        i -= 1
        if oPYA.get_device_info_by_index(i)['maxInputChannels'] == 0:
            continue
        audio['input_devices'][i] = oPYA.get_device_info_by_index(i)['name']
    return audio

def setup_video(oArgs):
    video = setup_default_video()
    if oArgs.video_input == '-1':
        video['device'] = video['output_devices'][1]
    else:
        video['device'] = oArgs.video_input
    return video

def setup_audio(oArgs):
    global oPYA
    audio = setup_default_audio()
    for k,v in audio['input_devices'].items():
        if v == 'default' and 'input' not in audio:
            audio['input'] = k
        if v == getattr(oArgs, 'audio_input'):
            audio['input'] = k
            LOG.debug(f"Setting audio['input'] {k} = {v} {k}")
            break
    for k,v in audio['output_devices'].items():
        if v == 'default' and 'output' not in audio:
            audio['output'] = k
        if v == getattr(oArgs, 'audio_output'):
            audio['output'] = k
            LOG.debug(f"Setting audio['output'] {k} = {v} " +str(k))
            break

    if hasattr(oArgs, 'mode') and getattr(oArgs, 'mode') > 1:
        audio['enabled'] = True
        audio['audio_enabled'] = True
        audio['video_enabled'] = True
    elif hasattr(oArgs, 'mode') and getattr(oArgs, 'mode') > 0:
        audio['enabled'] = True
        audio['audio_enabled'] = False
        audio['video_enabled'] = True
    else:
        audio['enabled'] = False
        audio['audio_enabled'] = False
        audio['video_enabled'] = False

    return audio

    i = getattr(oArgs, 'audio_output')
    if i >= 0:
        try:
            elt = oPYA.get_device_info_by_index(i)
            if i >= 0 and ( 'maxOutputChannels' not in elt or \
                            elt['maxOutputChannels'] == 0):
                LOG.warn(f"Audio output device has no output channels:  {i}")
                oArgs.audio_output = -1
        except OSError as e:
            LOG.warn("Audio output device error looking for maxOutputChannels: " \
                      +str(i) +' ' +str(e))
            oArgs.audio_output = -1

    if getattr(oArgs, 'audio_output') < 0:
        LOG.info("Choose an output device:")
        i = oPYA.get_device_count()
        while i > 0:
            i -= 1
            if oPYA.get_device_info_by_index(i)['maxOutputChannels'] == 0:
                continue
            LOG.info(str(i) \
                  +' ' +oPYA.get_device_info_by_index(i)['name'] \
                  +' ' +str(oPYA.get_device_info_by_index(i)['defaultSampleRate'])
                  )
        return 0

    i = getattr(oArgs, 'audio_input')
    if i >= 0:
        try:
            elt = oPYA.get_device_info_by_index(i)
            if i >= 0 and ( 'maxInputChannels' not in elt or \
                            elt['maxInputChannels'] == 0):
                LOG.warn(f"Audio input device has no input channels:  {i}")
                setattr(oArgs, 'audio_input', -1)
        except OSError as e:
            LOG.warn("Audio input device error looking for maxInputChannels: " \
                      +str(i) +' ' +str(e))
            setattr(oArgs, 'audio_input', -1)
    if getattr(oArgs, 'audio_input') < 0:
        LOG.info("Choose an input device:")
        i = oPYA.get_device_count()
        while i > 0:
            i -= 1
            if oPYA.get_device_info_by_index(i)['maxInputChannels'] == 0:
                continue
            LOG.info(str(i) \
                     +' ' +oPYA.get_device_info_by_index(i)['name']
                     +' ' +str(oPYA.get_device_info_by_index(i)['defaultSampleRate'])
                  )
        return 0

def setup_default_video():
    default_video = ["-1"]
    default_video.extend(ts.get_video_indexes())
    LOG.info(f"Video input choices: {default_video!r}")
    video = {'device': -1, 'width': 320, 'height': 240, 'x': 0, 'y': 0}
    video['output_devices'] = default_video
    return video

def main_parser(_=None, iMode=2):
    import cv2
    if not os.path.exists('/proc/sys/net/ipv6'):
        bIpV6 = 'False'
    else:
        bIpV6 = 'True'
    lIpV6Choices=[bIpV6, 'False']

    audio = setup_default_audio()
    default_video = setup_default_video()

#    parser = argparse.ArgumentParser()
    parser = ts.oMainArgparser()
    parser.add_argument('--version', action='store_true', help='Prints Toxygen version')
    parser.add_argument('--clean', action='store_true', help='Delete toxcore libs from libs folder')
    parser.add_argument('--reset', action='store_true', help='Reset default profile')
    parser.add_argument('--uri', type=str, default='',
                        help='Add specified Tox ID to friends')
    parser.add_argument('--auto_accept_path', '--auto-accept-path', type=str,
                        default=os.path.join(os.environ['HOME'], 'Downloads'),
                        help="auto_accept_path")
#    parser.add_argument('--mode', type=int, default=iMode,
#                        help='Mode: 0=chat 1=chat+audio 2=chat+audio+video default: 0')
    parser.add_argument('--font', type=str, default="Courier",
                        help='Message font')
    parser.add_argument('--message_font_size', type=int, default=15,
                        help='Font size in pixels')
    parser.add_argument('--local_discovery_enabled',type=str,
                        default='False', choices=['True','False'],
                        help='Look on the local lan')
    parser.add_argument('--compact_mode',type=str,
                        default='True', choices=['True','False'],
                        help='Compact mode')
    parser.add_argument('--allow_inline',type=str,
                        default='False', choices=['True','False'],
                        help='Dis/Enable allow_inline')
    parser.add_argument('--notifications',type=str,
                        default='True', choices=['True','False'],
                        help='Dis/Enable notifications')
    parser.add_argument('--sound_notifications',type=str,
                        default='True', choices=['True','False'],
                        help='Enable sound notifications')
    parser.add_argument('--calls_sound',type=str,
                        default='True', choices=['True','False'],
                        help='Enable calls_sound')
    parser.add_argument('--core_logging',type=str,
                        default='False', choices=['True','False'],
                        help='Dis/Enable Toxcore notifications')
    parser.add_argument('--save_history',type=str,
                        default='True', choices=['True','False'],
                        help='En/Disable save history')
    parser.add_argument('--update', type=int, default=0,
                        choices=[0,0],
                        help='Update program (broken)')
    parser.add_argument('--video_input', type=str,
                        default=-1,
                        choices=default_video['output_devices'],
                        help="Video input device number - /dev/video?")
    parser.add_argument('--audio_input', type=str,
                        default=oPYA.get_default_input_device_info()['name'],
                        choices=audio['input_devices'].values(),
                        help="Audio input device name - aplay -L for help")
    parser.add_argument('--audio_output', type=str,
                        default=oPYA.get_default_output_device_info()['index'],
                        choices=audio['output_devices'].values(),
                        help="Audio output device number - -1 for help")
    parser.add_argument('--theme', type=str, default='default',
                        choices=['dark', 'default'],
                        help='Theme - style of UI')
    parser.add_argument('--sleep', type=str, default='time',
                        # could expand this to tk, gtk, gevent...
                        choices=['qt','gevent','time'],
                        help='Sleep method - one of qt, gevent , time')
    supported_languages = settings.supported_languages()
    parser.add_argument('--language', type=str, default='English',
                        choices=supported_languages,
                        help='Languages')
    parser.add_argument('profile', type=str, nargs='?', default=None,
                        help='Path to Tox profile')
    return parser

# clean out the unchanged settings so these can override the profile
lKEEP_SETTINGS = ['uri',
                  'profile',
                  'loglevel',
                  'logfile',
                  'mode',

                  # dunno
                  'audio_input',
                  'audio_output',
                  'audio',
                  'video',

                  'ipv6_enabled',
                  'udp_enabled',
                  'local_discovery_enabled',
                  'theme',
                  'network',
                  'message_font_size',
                  'font',
                  'save_history',
                  'language',
                  'update',
                  'proxy_host',
                  'proxy_type',
                  'proxy_port',
                  'core_logging',
                  'audio',
                  'video'
                  ] # , 'nodes_json'

class A(): pass

def main(lArgs):
    global oPYA
    from argparse import Namespace
    parser = main_parser()
    default_ns = parser.parse_args([])
    oArgs = parser.parse_args(lArgs)

    if oArgs.version:
        print_toxygen_version()
        return 0

    if oArgs.clean:
        clean()
        return 0

    if oArgs.reset:
        reset()
        return 0

    # if getattr(oArgs, 'network') in ['newlocal', 'localnew']: oArgs.network = 'new'

    # clean out the unchanged settings so these can override the profile
    for key in default_ns.__dict__.keys():
        if key in lKEEP_SETTINGS: continue
        if not hasattr(oArgs, key): continue
        if getattr(default_ns, key) == getattr(oArgs, key):
            delattr(oArgs, key)

    ts.clean_booleans(oArgs)

    aArgs = A()
    for key in oArgs.__dict__.keys():
        setattr(aArgs, key, getattr(oArgs, key))
    #setattr(aArgs, 'video', setup_video(oArgs))
    aArgs.video = setup_video(oArgs)
    assert 'video' in aArgs.__dict__

    #setattr(aArgs, 'audio', setup_audio(oArgs))
    aArgs.audio = setup_audio(oArgs)
    assert 'audio' in aArgs.__dict__
    oArgs = aArgs

    toxygen = app.App(__version__, oArgs)
    # for pyqtconsole
    __builtins__.app = toxygen
    i = toxygen.iMain()
    return i

if __name__ == '__main__':
    iRet = 0
    try:
        iRet = main(sys.argv[1:])
    except KeyboardInterrupt:
        iRet = 0
    except SystemExit as e:
        iRet = e
    except Exception as e:
        import traceback
        sys.stderr.write(f"Exception from main  {e}" \
                         +'\n' + traceback.format_exc() +'\n' )
        iRet = 1

    # Exception ignored in: <module 'threading' from '/usr/lib/python3.9/threading.py'>
    # File "/usr/lib/python3.9/threading.py", line 1428, in _shutdown
    # lock.acquire()
    # gevent.exceptions.LoopExit as e:
    # This operation would block forever
    sys.stderr.write('Calling sys.exit' +'\n')
    with ts.ignoreStdout():
        sys.exit(iRet)
