# -*- mode: python; indent-tabs-mode: nil; py-indent-offset: 4; coding: utf-8 -*-

import os
from platform import system
import json
from pprint import pprint

from utils.util import *
from utils.util import log, join_path
from common.event import Event
import utils.ui as util_ui
import utils.util as util_utils
import user_data
import wrapper_tests.support_testing as ts

global LOG
import logging
LOG = logging.getLogger('settings')

def merge_args_into_settings(args, settings):
    if args:
        print(repr(args.__dict__.keys()))
        if not hasattr(args, 'audio'):
            LOG.warn('No audio ' +repr(args))
        settings['audio'] = getattr(args, 'audio')
        if not hasattr(args, 'video'):
            LOG.warn('No video ' +repr(args))
        settings['video'] = getattr(args, 'video')
        for key in settings.keys():
            # proxy_type proxy_port proxy_host
            not_key = 'not_' +key
            if hasattr(args, key):
                val = getattr(args, key)
                if type(val) == bytes:
                    # proxy_host - ascii?
                    # filenames - ascii?
                    val = str(val, 'UTF-8')
                settings[key] = val
            elif hasattr(args, not_key):
                val = not getattr(args, not_key)
                settings[key] = val
    clean_settings(settings)
    return

def clean_settings(self):
    # failsafe to ensure C tox is bytes and Py settings is str

    # overrides
    self['mirror_mode'] = False
    # REQUIRED!!
    if not os.path.exists('/proc/sys/net/ipv6'):
        LOG.warn('Disabling IPV6 because /proc/sys/net/ipv6 does not exist')
        self['ipv6_enabled'] = False

    if 'proxy_type' in self and self['proxy_type'] == 0:
        self['proxy_host'] = ''
        self['proxy_port'] = 0

    if 'proxy_type' in self and self['proxy_type'] != 0 and \
        'proxy_host' in self and self['proxy_host'] != '' and \
        'proxy_port' in self and self['proxy_port'] != 0:
        if 'udp_enabled' in self and self['udp_enabled']:
            # We don't currently support UDP over proxy.
            LOG.info("UDP enabled and proxy set: disabling UDP")
        self['udp_enabled'] = False
        if 'local_discovery_enabled' in self and self['local_discovery_enabled']:
            LOG.info("local_discovery_enabled enabled and proxy set: disabling local_discovery_enabled")
        self['local_discovery_enabled'] = False
        if 'dht_announcements_enabled' in self and self['dht_announcements_enabled']:
            LOG.info("dht_announcements_enabled enabled and proxy set: disabling dht_announcements_enabled")
        self['dht_announcements_enabled'] = False

    if 'auto_accept_path' in self and \
       type(self['auto_accept_path']) == bytes:
        self['auto_accept_path'] = str(self['auto_accept_path'], 'UTF-8')

    for key in Settings.get_default_settings():
        if key not in self: continue
        if type(self[key]) == bytes:
            LOG.warn('bytes setting in: ' +key \
                     +' ' + repr(self[key]))
            # ascii?
            # self[key] = str(self[key], 'utf-8')
    LOG.debug("Cleaned settings")

def get_user_config_path():
    system = util_utils.get_platform()
    if system == 'Windows':
        return os.path.join(os.getenv('APPDATA'), 'Tox/')
    elif system == 'Darwin':
        return os.path.join(os.getenv('HOME'), 'Library/Application Support/Tox/')
    else:
        return os.path.join(os.getenv('HOME'), '.config/tox/')

def supported_languages():
    return {
        'English': 'en_EN',
        'French': 'fr_FR',
        'Russian': 'ru_RU',
        'Ukrainian': 'uk_UA'
    }

def built_in_themes():
    return {
        'dark': 'dark_style.qss',
        'default': 'style.qss'
    }

def get_global_settings_path():
    return os.path.join(get_base_directory(), 'toxygen.json')

def is_active_profile(profile_path):
    sFile = profile_path + '.lock'
    if not os.path.isfile(sFile):
        return False
    try:
        import psutil
    except Exception as e:
        return True
    with open(sFile, 'rb') as iFd:
        sPid = iFd.read()
    if sPid and int(sPid.strip()) in psutil.pids():
        return True
    LOG.debug('Unlinking stale lock file ' +sFile)
    try:
        os.unlink(sFile)
    except:
        pass
    return False

class Settings(dict):
    """
    Settings of current profile + global app settings
    """

    def __init__(self, toxes, path, app):
        self._path = path
        self._profile_path = path.replace('.json', '.tox')
        self._toxes = toxes
        self._app = app
        self._oArgs = app._oArgs
        self._log = lambda l: LOG.log(self._oArgs.loglevel, l)

        self._settings_saved_event = Event()
        if path and os.path.isfile(path):
            try:
                with open(path, 'rb') as fl:
                    data = fl.read()
                if toxes.is_data_encrypted(data):
                    data = toxes.pass_decrypt(data)
                info = json.loads(str(data, 'utf-8'))
                LOG.debug('Parsed settings from: ' + str(path))
            except Exception as ex:
                title = 'Error opening/parsing settings file: '
                text = title + path
                LOG.error(title +str(ex))
                util_ui.message_box(text, title)
                info = Settings.get_default_settings(app._oArgs)
            user_data.settings.clean_settings(info)
        else:
            LOG.debug('get_default_settings for: ' + repr(path))
            info = Settings.get_default_settings(app._oArgs)

        if not os.path.exists(path):
            merge_oArgs_into_settings(app._oArgs, info)
        else:
            aC = self._changed(app._oArgs, info)
            if aC:
                title = 'Override profile with commandline - '
                if path:
                    title += os.path.basename(path)
                text = 'Override profile with command-line settings? \n'
    #            text += '\n'.join([str(key) +'=' +str(val) for
    #                               key,val in self._changed(app._oArgs).items()])
                text += repr(aC)
                reply = util_ui.question(text, title)
                if reply:
                    merge_oArgs_into_settings(app._oArgs, info)
        info['audio'] = getattr(app._oArgs, 'audio')
        info['video'] = getattr(app._oArgs, 'video')
        super().__init__(info)
        self._upgrade()

        LOG.info('Parsed settings from: ' + str(path))
        ex = f"self=id(self) {self!r}"
        LOG.debug(ex)

        self.save()
        self.locked = False
        self.closing = False
        self.unlockScreen = False


    # -----------------------------------------------------------------------------------------------------------------
    # Properties
    # -----------------------------------------------------------------------------------------------------------------

    def get_settings_saved_event(self):
        return self._settings_saved_event

    settings_saved_event = property(get_settings_saved_event)

    # -----------------------------------------------------------------------------------------------------------------
    # Public methods
    # -----------------------------------------------------------------------------------------------------------------

    def save(self):
        text = json.dumps(self)
        if self._toxes.has_password():
            text = bytes(self._toxes.pass_encrypt(bytes(text, 'utf-8')))
        else:
            text = bytes(text, 'utf-8')
        tmp = self._path + str(os.getpid())
        try:
            with open(tmp, 'wb') as fl:
                fl.write(text)
            os.rename(tmp, self._path)
        except Exception as e:
            LOG.warn(f'Error saving to {self._path} ' +str(e))
        else:
            self._settings_saved_event(text)

    def close(self):
        path = self._profile_path + '.lock'
        if os.path.isfile(path):
            os.remove(path)

    def set_active_profile(self):
        """
        Mark current profile as active
        """
        path = self._profile_path + '.lock'
        try:
            import shutil
        except:
            pass
        else:
            shutil.copy2(self._profile_path, path)
            # need to open this with the same perms as _profile_path
            # copy profile_path and then write?
        with open(path, 'wb') as fl:
            fl.write(bytes(str(os.getpid()), 'ascii'))

    def export(self, path):
        text = json.dumps(self)
        name = os.path.basename(self._path)
        with open(join_path(path, str(name)), 'w') as fl:
            fl.write(text)

    def update_path(self, new_path):
        self._path = new_path
        self.save()

    # -----------------------------------------------------------------------------------------------------------------
    # Static methods
    # -----------------------------------------------------------------------------------------------------------------

    @staticmethod
    def get_auto_profile():
        p = get_global_settings_path()
        if not os.path.isfile(p):
            return None
        with open(p) as fl:
            data = fl.read()
        try:
            auto = json.loads(data)
        except Exception as ex:
            LOG.warn(f"json.loads {data}: {ex!s}")
            auto = {}
        if 'profile_path' in auto:
            path = str(auto['profile_path'])
            if not os.path.isabs(path):
                path = join_path(path, curr_directory(__file__))
            if os.path.isfile(path):
                return path

    @staticmethod
    def supported_languages():
        # backwards
        return supported_languages()

    @staticmethod
    def set_auto_profile(path):
        p = get_global_settings_path()
        if os.path.isfile(p):
            with open(p) as fl:
                data = fl.read()
            data = json.loads(data)
        else:
            data = {}
        data['profile_path'] = str(path)
        with open(p, 'w') as fl:
            fl.write(json.dumps(data))

    @staticmethod
    def reset_auto_profile():
        p = get_global_settings_path()
        if os.path.isfile(p):
            with open(p) as fl:
                data = fl.read()
            data = json.loads(data)
        else:
            data = {}
        if 'profile_path' in data:
            del data['profile_path']
        with open(p, 'w') as fl:
            fl.write(json.dumps(data))

    @staticmethod
    def get_default_settings(args=None):
        """
        Default profile settings
        """
        retval = {
            # FixMe: match? /var/local/src/c-toxcore/toxcore/tox.h
            'ipv6_enabled': True,
            'udp_enabled': True,
            'trace_enabled': False,
            'local_discovery_enabled': True,
            'dht_announcements_enabled': True,
            'proxy_type': 0,
            'proxy_host': '',
            'proxy_port': 0,
            'start_port': 0,
            'end_port': 0,
            'tcp_port': 0,
            'local_discovery_enabled': True,
            'hole_punching_enabled': False,
            # tox_log_cb *log_callback;
            'experimental_thread_safety': False,
            # operating_system

            'theme': 'default',
            'notifications': False,
            'sound_notifications': False,
            'language': 'English',
            'calls_sound': False, # was True

            'save_history': True,
            'save_unsent_only': False,
            'allow_inline': True,
            'allow_auto_accept': True,
            'auto_accept_path': None,
            'sorting': 0,
            'auto_accept_from_friends': [],
            'paused_file_transfers': {},
            'resend_files': True,
            'friends_aliases': [],
            'show_avatars': False,
            'typing_notifications': False,
            'blocked': [],
            'plugins': [],
            'notes': {},
            'smileys': True,
            'smiley_pack': 'default',
            'mirror_mode': False,
            'width': 920,
            'height': 500,
            'x': 400,
            'y': 400,
            'message_font_size': 14,
            'unread_color': 'red',
            'compact_mode': False,
            'identicons': True,
            'show_welcome_screen': True,
            'close_app': 0,
            'font': 'Times New Roman',
            'update': 0,
            'group_notifications': True,
            'download_nodes_list': False, #
            'download_nodes_url': 'https://nodes.tox.chat/json',
            'notify_all_gc': False,
            'backup_directory': None,

            'audio': {'input': -1,
                      'output': -1,
                      'enabled': True},
            'video': {'device': -1,
                       'width': 320,
                       'height': 240,
                       'x': 0,
                       'y': 0},
            'current_nodes': None,
            'network': 'new',
            'tray_icon': False,
        }
        return retval

    # -----------------------------------------------------------------------------------------------------------------
    # Private methods
    # -----------------------------------------------------------------------------------------------------------------

    def _upgrade(self):
        default = Settings.get_default_settings()
        for key in default:
            if key not in self:
                print(key)
                self[key] = default[key]

    def _changed(self, aArgs, info):
        aRet = dict()
        default = Settings.get_default_settings()
        for key in default:
            if key in ['audio', 'video']: continue
            if key not in aArgs.__dict__: continue
            val = aArgs.__dict__[key]
            if val in ['0.0.0.0']: continue
            if key in aArgs.__dict__ and key not in info:
                # dunno = network
                continue
            if key in aArgs.__dict__ and info[key] != val:
                aRet[key] = val
        return aRet

