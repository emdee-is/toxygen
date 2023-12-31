from utils import util
import json
import os
from collections import OrderedDict
from PyQt5 import QtCore

# LOG=util.log
global LOG
import logging
LOG = logging.getLogger('app.'+__name__)
log = lambda x: LOG.info(x)

class SmileyLoader:
    """
    Class which loads smileys packs and insert smileys into messages
    """

    def __init__(self, settings):
        super().__init__()
        self._settings = settings
        self._curr_pack = None  # current pack name
        self._smileys = {}  # smileys dict. key - smiley (str), value - path to image (str)
        self._list = []  # smileys list without duplicates
        self.load_pack()

    def load_pack(self):
        """
        Loads smiley pack
        """
        pack_name = self._settings['smiley_pack']
        if self._settings['smileys'] and self._curr_pack != pack_name:
            self._curr_pack = pack_name
            path = util.join_path(self.get_smileys_path(), 'config.json')
            try:
                with open(path, encoding='utf8') as fl:
                    self._smileys = json.loads(fl.read())
                    fl.seek(0)
                    tmp = json.loads(fl.read(), object_pairs_hook=OrderedDict)
                LOG.info('Smiley pack {} loaded'.format(pack_name))
                keys, values, self._list = [], [], []
                for key, value in tmp.items():
                    value = util.join_path(self.get_smileys_path(), value)
                    if value not in values:
                        keys.append(key)
                        values.append(value)
                self._list = list(zip(keys, values))
            except Exception as ex:
                self._smileys = {}
                self._list = []
                LOG.error('Smiley pack {} was not loaded. Error: {}'.format(pack_name, str(ex)))

    def get_smileys_path(self):
        return util.join_path(util.get_smileys_directory(), self._curr_pack) if self._curr_pack is not None else None

    @staticmethod
    def get_packs_list():
        d = util.get_smileys_directory()
        return [x[1] for x in os.walk(d)][0]

    def get_smileys(self):
        return list(self._list)

    def add_smileys_to_text(self, text, edit):
        """
        Adds smileys to text
        :param text: message
        :param edit: MessageEdit instance
        :return text with smileys
        """
        if not self._settings['smileys'] or not len(self._smileys):
            return text
        arr = text.split(' ')
        for i in range(len(arr)):
            if arr[i] in self._smileys:
                file_name = self._smileys[arr[i]]  # image name
                arr[i] = '<img title=\"{}\" src=\"{}\" />'.format(arr[i], file_name)
                if file_name.endswith('.gif'):  # animated smiley
                    edit.addAnimation(QtCore.QUrl(file_name), self.get_smileys_path() + file_name)
        return ' '.join(arr)
