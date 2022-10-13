# -*- mode: python; indent-tabs-mode: nil; py-indent-offset: 4; coding: utf-8 -*-
import user_data.settings
import wrapper.tox
import wrapper.toxcore_enums_and_consts as enums
import ctypes
import traceback
import os

global LOG
import logging
LOG = logging.getLogger('app.'+'tox_factory')

from ctypes import *
from utils import util
from utils import ui as util_ui

# callbacks can be called in any thread so were being careful
# tox.py can be called by callbacks
def LOG_ERROR(a): print('EROR> '+a)
def LOG_WARN(a): print('WARN> '+a)
def LOG_INFO(a):
    bVERBOSE = hasattr(__builtins__, 'app') and app.oArgs.loglevel <= 20
    if bVERBOSE: print('INFO> '+a)
def LOG_DEBUG(a):
    bVERBOSE = hasattr(__builtins__, 'app') and app.oArgs.loglevel <= 10-1
    if bVERBOSE: print('DBUG> '+a)
def LOG_TRACE(a):
    bVERBOSE = hasattr(__builtins__, 'app') and app.oArgs.loglevel < 10
    if bVERBOSE: print('TRAC> '+a)
def LOG_LOG(a): print('TRAC> '+a)

def tox_log_cb(iTox, level, file, line, func, message, *args):
    """
    * @param level The severity of the log message.
    * @param file The source file from which the message originated.
    * @param line The source line from which the message originated.
    * @param func The function from which the message originated.
    * @param message The log message.
    * @param user_data The user data pointer passed to tox_new in options.
    """
    try:
        if type(file) == bytes:
            file = str(file, 'UTF-8')
        if file == 'network.c' and line in [944, 660]: return
        # root WARNING 3network.c#944:b'send_packet'attempted to send message with network family 10 (probably IPv6) on IPv4 socket
        if type(func) == bytes:
            func = str(func, 'UTF-8')
        if type(message) == bytes:
            message = str(message, 'UTF-8')
        message = f"{file}#{line}:{func} {message}"
        LOG_LOG(message)
    except Exception as e:
        LOG_ERROR("tox_log_cb {e}")
        
def tox_factory(data=None, settings=None, args=None, app=None):
    """
    :param data: user data from .tox file. None = no saved data, create new profile
    :param settings: current profile settings. None = default settings will be used
    :return: new tox instance
    """
    if not settings:
        LOG_WARN("tox_factory using get_default_settings")
        settings = user_data.settings.Settings.get_default_settings()
    else:
        user_data.settings.clean_settings(settings)

    try:
        tox_options = wrapper.tox.Tox.options_new()
        tox_options.contents.ipv6_enabled = settings['ipv6_enabled']
        tox_options.contents.udp_enabled = settings['udp_enabled']
        tox_options.contents.proxy_type = int(settings['proxy_type'])
        if type(settings['proxy_host']) == str:
            tox_options.contents.proxy_host = bytes(settings['proxy_host'],'UTF-8')
        elif type(settings['proxy_host']) == bytes:
            tox_options.contents.proxy_host = settings['proxy_host']
        else:
            tox_options.contents.proxy_host = b''
        tox_options.contents.proxy_port = int(settings['proxy_port'])
        tox_options.contents.start_port = settings['start_port']
        tox_options.contents.end_port = settings['end_port']
        tox_options.contents.tcp_port = settings['tcp_port']
        tox_options.contents.local_discovery_enabled = settings['local_discovery_enabled']
        tox_options.contents.dht_announcements_enabled = settings['dht_announcements_enabled']
        tox_options.contents.hole_punching_enabled = settings['hole_punching_enabled']
        if data:  # load existing profile
            tox_options.contents.savedata_type = enums.TOX_SAVEDATA_TYPE['TOX_SAVE']
            tox_options.contents.savedata_data = ctypes.c_char_p(data)
            tox_options.contents.savedata_length = len(data)
        else:  # create new profile
            tox_options.contents.savedata_type = enums.TOX_SAVEDATA_TYPE['NONE']
            tox_options.contents.savedata_data = None
            tox_options.contents.savedata_length = 0

        # overrides
        tox_options.contents.local_discovery_enabled = False
        tox_options.contents.ipv6_enabled = False
        tox_options.contents.hole_punching_enabled = False

        LOG.debug("wrapper.tox.Tox settings: " +repr(settings))

        if tox_options._options_pointer:
            c_callback = CFUNCTYPE(None, c_void_p, c_int, c_char_p, c_int, c_char_p, c_char_p, c_void_p)
            tox_options.self_logger_cb = c_callback(tox_log_cb)
            wrapper.tox.Tox.libtoxcore.tox_options_set_log_callback(
                tox_options._options_pointer,
                tox_options.self_logger_cb)
        else:
            LOG_WARN("No tox_options._options_pointer to add self_logger_cb" )

        retval = wrapper.tox.Tox(tox_options)
    except Exception as e:
        if app and hasattr(app, '_log'):
            pass
        LOG_ERROR(f"wrapper.tox.Tox failed:  {e}")
        LOG_WARN(traceback.format_exc())
        raise

    if app and hasattr(app, '_log'):
        app._log("DEBUG: wrapper.tox.Tox succeeded")
    return retval
