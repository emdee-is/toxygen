# -*- mode: python; indent-tabs-mode: nil; py-indent-offset: 4; coding: utf-8 -*-

from contacts import contact
from contacts.contact_menu import GroupMenuGenerator
import utils.util as util
from groups.group_peer import GroupChatPeer
from wrapper import toxcore_enums_and_consts as constants
from common.tox_save import ToxSave
from groups.group_ban import GroupBan

global LOG
import logging
LOG = logging.getLogger(__name__)
def LOG_ERROR(l): print('ERROR_: '+l)
def LOG_WARN(l): print('WARN_: '+l)
def LOG_INFO(l): print('INFO_: '+l)
def LOG_DEBUG(l): print('DEBUG_: '+l)
def LOG_TRACE(l): pass # print('TRACE+ '+l)

class GroupChat(contact.Contact, ToxSave):

    def __init__(self, tox, profile_manager, message_getter, number, name, status_message, widget, tox_id, is_private):
        super().__init__(profile_manager, message_getter, number, name, status_message, widget, tox_id)
        ToxSave.__init__(self, tox)

        self._is_private = is_private
        self._password = str()
        self._peers_limit = 512
        self._peers = []
        self._add_self_to_gc()

    def remove_invalid_unsent_files(self):
        pass

    def get_context_menu_generator(self):
        return GroupMenuGenerator(self)

    # Properties

    def get_is_private(self):
        return self._is_private

    def set_is_private(self, is_private):
        self._is_private = is_private

    is_private = property(get_is_private, set_is_private)

    def get_password(self):
        return self._password

    def set_password(self, password):
        self._password = password

    password = property(get_password, set_password)

    def get_peers_limit(self):
        return self._peers_limit

    def set_peers_limit(self, peers_limit):
        self._peers_limit = peers_limit

    peers_limit = property(get_peers_limit, set_peers_limit)

    # Peers methods

    def get_self_peer(self):
        return self._peers[0]

    def get_self_name(self):
        return self._peers[0].name

    def get_self_role(self):
        return self._peers[0].role

    def is_self_moderator_or_founder(self):
        return self.get_self_role() <= constants.TOX_GROUP_ROLE['MODERATOR']

    def is_self_founder(self):
        return self.get_self_role() == constants.TOX_GROUP_ROLE['FOUNDER']

    def add_peer(self, peer_id, is_current_user=False):
        "called from callbacks"
        if peer_id >  self._peers_limit:
            LOG_WARN(f"add_peer id={peer_id} > {self._peers_limit}")
            return

        LOG_TRACE(f"add_peer id={peer_id}")
        peer = GroupChatPeer(peer_id,
                             self._tox.group_peer_get_name(self._number, peer_id),
                             self._tox.group_peer_get_status(self._number, peer_id),
                             self._tox.group_peer_get_role(self._number, peer_id),
                             self._tox.group_peer_get_public_key(self._number, peer_id),
                             is_current_user)
        self._peers.append(peer)

    def remove_peer(self, peer_id):
        if peer_id == self.get_self_peer().id:  # we were kicked or banned
            self.remove_all_peers_except_self()
        else:
            peer = self.get_peer_by_id(peer_id)
            if peer: # broken
                self._peers.remove(peer)
            else:
                LOG_WARN(f"remove_peer empty peers for {peer_id}")

    def get_peer_by_id(self, peer_id):
        peers = list(filter(lambda p: p.id == peer_id, self._peers))
        if peers:
            return peers[0]
        else:
            LOG_WARN(f"get_peer_by_id empty peers for {peer_id}")
            return []

    def get_peer_by_public_key(self, public_key):
        peers = list(filter(lambda p: p.public_key == public_key, self._peers))
        # DEBUGc: group_moderation #0 mod_id=4294967295 event_type=3
        # WARN_: get_peer_by_id empty peers for 4294967295
        if peers:
            return peers[0]
        else:
            LOG_WARN(f"get_peer_by_public_key empty peers for {public_key}")
            return []

    def remove_all_peers_except_self(self):
        self._peers = self._peers[:1]

    def get_peers_names(self):
        peers_names = map(lambda p: p.name, self._peers)
        if peers_names: # broken
            return list(peers_names)
        else:
            LOG_WARN(f"get_peers_names empty peers")
            #? broken
            return []

    def get_peers(self):
        return self._peers[:]

    peers = property(get_peers)

    def get_bans(self):
        return []
#        ban_ids = self._tox.group_ban_get_list(self._number)
#        bans = []
#        for ban_id in ban_ids:
#            ban = GroupBan(ban_id,
#                           self._tox.group_ban_get_target(self._number, ban_id),
#                           self._tox.group_ban_get_time_set(self._number, ban_id))
#            bans.append(ban)
#
#        return bans
#
    bans = property(get_bans)

    # Private methods

    @staticmethod
    def _get_default_avatar_path():
        return util.join_path(util.get_images_directory(), 'group.png')

    def _add_self_to_gc(self):
        peer_id = self._tox.group_self_get_peer_id(self._number)
        self.add_peer(peer_id, True)
