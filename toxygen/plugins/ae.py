# -*- mode: python; indent-tabs-mode: nil; py-indent-offset: 4; coding: utf-8 -*-
import plugin_super_class
import json
from user_data import settings
import os
from bootstrap.bootstrap import get_user_config_path

class AvatarEncryption(plugin_super_class.PluginSuperClass):

    def __init__(self, *args):
        super(AvatarEncryption, self).__init__('AvatarEncryption', 'ae', *args)
        self._path = os.path.join(get_user_config_path(), 'avatars')
        self._app = args[0]
        self._profile = self._app._ms._profile
        self._window = None
        #was self._contacts = self._profile._contacts[:]
        self._contacts = self._profile._contacts_provider.get_all_friends()

    def get_description(self):
        return QApplication.translate("AvatarEncryption", 'Encrypt all avatars using profile password.')

    def close(self):
        if not self._encrypt_save.has_password():
            return
        i, data = 1, {}

        self.save_contact_avatar(data, self._profile, 0)
        for friend in self._contacts:
            self.save_contact_avatar(data, friend, i)
            i += 1
        self.save_settings(json.dumps(data))

    def start(self):
        if not self._encrypt_save.has_password():
            return
        data = json.loads(self.load_settings())

        self.load_contact_avatar(data, self._profile)
        for friend in self._contacts:
            self.load_contact_avatar(data, friend)
        self._profile.update()

    def save_contact_avatar(self, data, contact, i):
        tox_id = contact.tox_id[:64]
        data[str(tox_id)] = str(i)
        path = os.path.join(self._path, tox_id + '.png')
        if os.path.isfile(path):
            with open(path, 'rb') as fl:
                avatar = fl.read()
            encr_avatar = self._encrypt_save.pass_encrypt(avatar)
            with open(os.path.join(self._path, self._settings.name + '_' + str(i) + '.png'), 'wb') as fl:
                fl.write(encr_avatar)
            os.remove(path)

    def load_contact_avatar(self, data, contact):
        tox_id = str(contact.tox_id[:64])
        if tox_id not in data:
            return
        path = os.path.join(self._path, self._settings.name + '_' + data[tox_id] + '.png')
        if os.path.isfile(path):
            with open(path, 'rb') as fl:
                avatar = fl.read()
            decr_avatar = self._encrypt_save.pass_decrypt(avatar)
            with open(os.path.join(self._path, str(tox_id) + '.png'), 'wb') as fl:
                fl.write(decr_avatar)
            os.remove(path)
            contact.load_avatar()

    def load_settings(self):
        try:
            with open(plugin_super_class.path_to_data(self._short_name) + self._settings.name + '.json', 'rb') as fl:
                data = fl.read()
            return str(self._encrypt_save.pass_decrypt(data), 'utf-8') if data else '{}'
        except:
            return '{}'

    def save_settings(self, data):
        try:
            data = self._encrypt_save.pass_encrypt(bytes(data, 'utf-8'))
            with open(plugin_super_class.path_to_data(self._short_name) + self._settings.name + '.json', 'wb') as fl:
                fl.write(data)
        except:
            pass
