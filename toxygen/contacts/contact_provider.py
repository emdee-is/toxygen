# -*- mode: python; indent-tabs-mode: nil; py-indent-offset: 4; coding: utf-8 -*-

import common.tox_save as tox_save

global LOG
import logging
LOG = logging.getLogger(__name__)

# callbacks can be called in any thread so were being careful
def LOG_ERROR(l): print('EROR< '+l)
def LOG_WARN(l):  print('WARN< '+l)
def LOG_INFO(l):
    bIsVerbose = hasattr(__builtins__, 'app') and app.oArgs.loglevel <= 20-1
    if bIsVerbose: print('INFO< '+l)
def LOG_DEBUG(l):
    bIsVerbose = hasattr(__builtins__, 'app') and app.oArgs.loglevel <= 10-1
    if bIsVerbose: print('DBUG< '+l)
def LOG_TRACE(l):
    bIsVerbose = hasattr(__builtins__, 'app') and app.oArgs.loglevel < 10-1
    pass # print('TRACE+ '+l)

class ContactProvider(tox_save.ToxSave):

    def __init__(self, tox, friend_factory, group_factory, group_peer_factory):
        super().__init__(tox)
        self._friend_factory = friend_factory
        self._group_factory = group_factory
        self._group_peer_factory = group_peer_factory
        self._cache = {}  # key - contact's public key, value - contact instance

    # Friends

    def get_friend_by_number(self, friend_number):
        try:
            public_key = self._tox.friend_get_public_key(friend_number)
        except Exception as e:
            LOG_WARN(f"CP.get_friend_by_number NO {friend_number} {e} ")
            return None
        return self.get_friend_by_public_key(public_key)

    def get_friend_by_public_key(self, public_key):
        friend = self._get_contact_from_cache(public_key)
        if friend is not None:
            return friend
        friend = self._friend_factory.create_friend_by_public_key(public_key)
        self._add_to_cache(public_key, friend)
        LOG_INFO(f"CP.get_friend_by_public_key ADDED {friend} ")

        return friend

    def get_all_friends(self):
        try:
            friend_numbers = self._tox.self_get_friend_list()
        except Exception as e:
            LOG_WARN(f"CP.get_all_friends NO {friend_numbers} {e} ")
            return None
        friends = map(lambda n: self.get_friend_by_number(n), friend_numbers)

        return list(friends)

    # Groups

    def get_all_groups(self):
        """from callbacks"""
        try:
            len_groups = self._tox.group_get_number_groups()
            group_numbers = range(len_groups)
        except Exception as e:
            return None
        groups = list(map(lambda n: self.get_group_by_number(n), group_numbers))
        # failsafe in case there are bogus None groups?
        fgroups = list(filter(lambda x: x, groups))
        if len(fgroups) != len_groups:
            LOG_WARN(f"CP.are there are bogus None groups in libtoxcore? {len(fgroups)} != {len_groups}")
            for group_num in group_numbers:
                group = self.get_group_by_number(group_num)
                if group is None:
                    LOG_ERROR(f"There are bogus None groups in libtoxcore {group_num}!")
                    # fixme: do something
            groups = fgroups
        return groups

    def get_group_by_number(self, group_number):
        group = None
        try:
            LOG_INFO(f"CP.CP.group_get_number {group_number} ")
            # original code
            chat_id = self._tox.group_get_chat_id(group_number)
            if chat_id is None:
                LOG_ERROR(f"get_group_by_number NULL chat_id ({group_number})")
            elif chat_id == '-1':
                LOG_ERROR(f"get_group_by_number <0 chat_id ({group_number})")
            else:
                LOG_INFO(f"CP.group_get_number {group_number} {chat_id}")
                group = self.get_group_by_chat_id(chat_id)
                if group is None or group  == '-1':
                    LOG_WARN(f"CP.get_group_by_number leaving {group} ({group_number})")
                    #? iRet = self._tox.group_leave(group_number)
                    # invoke in main thread?
                    # self._contacts_manager.delete_group(group_number)
            return group
        except Exception as e:
            LOG_WARN(f"CP.group_get_number {group_number} {e}")
            return None

    def get_group_by_chat_id(self, chat_id):
        group = self._get_contact_from_cache(chat_id)
        if group is not None:
            return group
        group = self._group_factory.create_group_by_chat_id(chat_id)
        if group is None:
            LOG_ERROR(f"get_group_by_chat_id NULL chat_id={chat_id}")
        else:
            self._add_to_cache(chat_id, group)

        return group

    def get_group_by_public_key(self, public_key):
        group = self._get_contact_from_cache(public_key)
        if group is not None:
            return group
        group = self._group_factory.create_group_by_public_key(public_key)
        if group is None:
            LOG_ERROR(f"get_group_by_public_key NULL group public_key={get_group_by_chat_id}")
        else:
            self._add_to_cache(public_key, group)

        return group

    # Group peers

    def get_all_group_peers(self):
        return list()

    def get_group_peer_by_id(self, group, peer_id):
        peer = group.get_peer_by_id(peer_id)
        if peer:
            return self._get_group_peer(group, peer)

    def get_group_peer_by_public_key(self, group, public_key):
        peer = group.get_peer_by_public_key(public_key)

        return self._get_group_peer(group, peer)

    # All contacts

    def get_all(self):
        return self.get_all_friends() + self.get_all_groups() + self.get_all_group_peers()

    # Caching

    def clear_cache(self):
        self._cache.clear()

    def remove_contact_from_cache(self, contact_public_key):
        if contact_public_key in self._cache:
            del self._cache[contact_public_key]

    # Private methods

    def _get_contact_from_cache(self, public_key):
        return self._cache[public_key] if public_key in self._cache else None

    def _add_to_cache(self, public_key, contact):
        self._cache[public_key] = contact

    def _get_group_peer(self, group, peer):
        return self._group_peer_factory.create_group_peer(group, peer)
