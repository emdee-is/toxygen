import utils.util as util
import os
from user_data.settings import Settings
from common.event import Event


class ProfileManager:
    """
    Class with methods for search, load and save profiles
    """
    def __init__(self, toxes, path):
        self._toxes = toxes
        self._path = path
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
        with open(self._path, 'wb') as fl:
            fl.write(data)
        print('Profile saved successfully')

        self._profile_saved_event(data)

    def export_profile(self, settings, new_path, use_new_path):
        path = new_path + os.path.basename(self._path)
        with open(self._path, 'rb') as fin:
            data = fin.read()
        with open(path, 'wb') as fout:
            fout.write(data)
        print('Profile exported successfully')
        util.copy(self._directory + 'avatars', new_path + 'avatars')
        if use_new_path:
            self._path = new_path + os.path.basename(self._path)
            self._directory = new_path
            settings.update_path(new_path)

    @staticmethod
    def find_profiles():
        """
        Find available tox profiles
        """
        path = Settings.get_default_path()
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
