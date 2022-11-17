# -*- mode: python; indent-tabs-mode: nil; py-indent-offset: 4; coding: utf-8 -*-
import os

import utils.util as util
from common.event import Event
from user_data.settings import Settings, get_user_config_path

global LOG
import logging

LOG = logging.getLogger('app.'+__name__)


def LOG_ERROR(l): print('ERROR_: '+l)
def LOG_WARN(l): print('WARN_: '+l)
def LOG_INFO(l): print('INFO_: '+l)
def LOG_DEBUG(l): print('DEBUG_: '+l)
def LOG_TRACE(l): pass # print('TRACE+ '+l)

class ProfileManager:
    """
    Class with methods for search, load and save profiles
    """
    def __init__(self, toxes, path):
        assert path
        self._toxes = toxes
        self._path = path
        assert path
        self._directory = os.path.dirname(path)
        self._profile_saved_event = Event()
        # create /avatars if not exists:
        avatars_directory = util.join_path(self._directory, 'avatars')
        if not os.path.exists(avatars_directory):
            os.makedirs(avatars_directory)

    # -----------------------------------------------------------------------------------------------------------------
    # Properties
    # -----------------------------------------------------------------------------------------------------------------

    def get_profile_saved_event(self):
        return self._profile_saved_event

    profile_saved_event = property(get_profile_saved_event)

    # -----------------------------------------------------------------------------------------------------------------
    # Public methods
    # -----------------------------------------------------------------------------------------------------------------

    def open_profile(self):
        with open(self._path, 'rb') as fl:
            data = fl.read()
        if data:
            return data
        else:
            raise IOError('Save file has zero size!')

    def get_dir(self):
        return self._directory

    def get_path(self):
        return self._path

    def save_profile(self, data):
        if self._toxes.has_password():
            data = self._toxes.pass_encrypt(data)
        try:
            suf = f"{os.getpid()}"
            with open(self._path+suf, 'wb') as fl:
                fl.write(data)
            stat = os.stat(self._path+suf)
            if hasattr(stat, 'st_blocks'):
                assert stat.st_blocks > 0, f"Zero length file {self._path+suf}"
            os.rename(self._path+suf,self._path)
            LOG_INFO('Profile saved successfully to' +self._path)
        except Exception as e:
            LOG_WARN(f"Profile save failed to {self._path}\n{e}")

        self._profile_saved_event(data)

    def export_profile(self, settings, new_path, use_new_path):
        with open(self._path, 'rb') as fin:
            data = fin.read()
        path = new_path + os.path.basename(self._path)
        with open(path, 'wb') as fout:
            fout.write(data)
        LOG.info('Profile exported successfully to ' +path)
        util.copy(os.path.join(self._directory, 'avatars'),
                  os.path.join(new_path, 'avatars'))
        if use_new_path:
            self._path = os.path.join(new_path, os.path.basename(self._path))
            self._directory = new_path
            settings.update_path(new_path)

    @staticmethod
    def find_profiles():
        """
        Find available tox profiles
        """
        path = get_user_config_path()
        result = []
        # check default path
        if not os.path.exists(path):
            os.makedirs(path)
        for fl in os.listdir(path):
            if fl.endswith('.tox'):
                name = fl[:-4]
                result.append((path, name))
        path = util.get_base_directory(__file__)
        # check current directory
        for fl in os.listdir(path):
            if fl.endswith('.tox'):
                name = fl[:-4]
                result.append((path + '/', name))
        return result
