# -*- mode: python; indent-tabs-mode: nil; py-indent-offset: 4; coding: utf-8 -*-

import common.tox_save as tox_save

global LOG
import logging
LOG = logging.getLogger(__name__)


class ContactProvider(tox_save.ToxSave):

    def __init__(self, tox, friend_factory, group_factory, group_peer_factory):
        super().__init__(tox)
        self._friend_factory = friend_factory
        self._group_factory = group_factory
        self._group_peer_factory = group_peer_factory
        self._cache = {}  # key - contact's public key, value - contact instance

    # -----------------------------------------------------------------------------------------------------------------
    # Friends
    # -----------------------------------------------------------------------------------------------------------------

    def get_friend_by_number(self, friend_number):
        try:
            public_key = self._tox.friend_get_public_key(friend_number)
        except Exception as e:
            return None
        return self.get_friend_by_public_key(public_key)

    def get_friend_by_public_key(self, public_key):
        friend = self._get_contact_from_cache(public_key)
        if friend is not None:
            return friend
        friend = self._friend_factory.create_friend_by_public_key(public_key)
        self._add_to_cache(public_key, friend)

        return friend

    def get_all_friends(self):
        try:
            friend_numbers = self._tox.self_get_friend_list()
        except Exception as e:
            return None
        friends = map(lambda n: self.get_friend_by_number(n), friend_numbers)

        return list(friends)

    # -----------------------------------------------------------------------------------------------------------------
    # Groups
    # -----------------------------------------------------------------------------------------------------------------

    def get_all_groups(self):
        try:
            group_numbers = range(self._tox.group_get_number_groups())
        except Exception as e:
            return None
        groups = map(lambda n: self.get_group_by_number(n), group_numbers)

        return list(groups)

    def get_group_by_number(self, group_number):
        try:
            if True:
                # original code
                public_key = self._tox.group_get_chat_id(group_number)
                LOG.info(f"group_get_chat_id {group_number} {public_key}")
                return self.get_group_by_public_key(public_key)
            else:
                # guessing
                chat_id = self._tox.group_get_chat_id(group_number)
                LOG.info(f"group_get_chat_id {group_number} {chat_id}")
                group = self.get_contact_by_tox_id(chat_id)
                return group
        except Exception as e:
            LOG.warn(f"group_get_chat_id {group_number} {e}")
            return None


    def get_group_by_public_key(self, public_key):
        group = self._get_contact_from_cache(public_key)
        if group is not None:
            return group
        group = self._group_factory.create_group_by_public_key(public_key)
        self._add_to_cache(public_key, group)

        return group

    # -----------------------------------------------------------------------------------------------------------------
    # Group peers
    # -----------------------------------------------------------------------------------------------------------------

    def get_all_group_peers(self):
        return list()

    def get_group_peer_by_id(self, group, peer_id):
        peer = group.get_peer_by_id(peer_id)
        if peer:
            return self._get_group_peer(group, peer)

    def get_group_peer_by_public_key(self, group, public_key):
        peer = group.get_peer_by_public_key(public_key)

        return self._get_group_peer(group, peer)

    # -----------------------------------------------------------------------------------------------------------------
    # All contacts
    # -----------------------------------------------------------------------------------------------------------------

    def get_all(self):
        return self.get_all_friends() + self.get_all_groups() + self.get_all_group_peers()

    # -----------------------------------------------------------------------------------------------------------------
    # Caching
    # -----------------------------------------------------------------------------------------------------------------

    def clear_cache(self):
        self._cache.clear()

    def remove_contact_from_cache(self, contact_public_key):
        if contact_public_key in self._cache:
            del self._cache[contact_public_key]

    # -----------------------------------------------------------------------------------------------------------------
    # Private methods
    # -----------------------------------------------------------------------------------------------------------------

    def _get_contact_from_cache(self, public_key):
        return self._cache[public_key] if public_key in self._cache else None

    def _add_to_cache(self, public_key, contact):
        self._cache[public_key] = contact

    def _get_group_peer(self, group, peer):
        return self._group_peer_factory.create_group_peer(group, peer)
