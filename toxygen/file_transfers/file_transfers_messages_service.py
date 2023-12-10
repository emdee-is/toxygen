from messenger.messenger import *
import utils.util as util
from file_transfers.file_transfers import *

global LOG
import logging
LOG = logging.getLogger('app.'+__name__)

def LOG_ERROR(l): print('ERROR_: '+l)
def LOG_WARN(l): print('WARN_: '+l)
def LOG_INFO(l): print('INFO_: '+l)
def LOG_DEBUG(l): print('DEBUG_: '+l)
def LOG_TRACE(l): pass # print('TRACE+ '+l)

class FileTransfersMessagesService:

    def __init__(self, contacts_manager, messages_items_factory, profile, main_screen):
        self._contacts_manager = contacts_manager
        self._messages_items_factory = messages_items_factory
        self._profile = profile
        self._messages = main_screen.messages

    def add_incoming_transfer_message(self, friend, accepted, size, file_name, file_number):
        assert friend
        author = MessageAuthor(friend.name, MESSAGE_AUTHOR['FRIEND'])
        status = FILE_TRANSFER_STATE['RUNNING'] if accepted else FILE_TRANSFER_STATE['INCOMING_NOT_STARTED']
        tm = TransferMessage(author, util.get_unix_time(), status, size, file_name, friend.number, file_number)

        if self._is_friend_active(friend.number):
            self._create_file_transfer_item(tm)
            self._messages.scrollToBottom()
        else:
            friend.actions = True

        friend.append_message(tm)

        return tm

    def add_outgoing_transfer_message(self, friend, size, file_name, file_number):
        assert friend
        author = MessageAuthor(self._profile.name, MESSAGE_AUTHOR['ME'])
        status = FILE_TRANSFER_STATE['OUTGOING_NOT_STARTED']
        tm = TransferMessage(author, util.get_unix_time(), status, size, file_name, friend.number, file_number)

        if self._is_friend_active(friend.number):
            self._create_file_transfer_item(tm)
            self._messages.scrollToBottom()

        friend.append_message(tm)

        return tm

    def add_inline_message(self, transfer, index):
        """callback"""
        if not self._is_friend_active(transfer.friend_number):
            return
        if transfer is None or not hasattr(transfer, 'data') or \
           not transfer.data:
            LOG_ERROR(f"add_inline_message empty data")
            return
        count = self._messages.count()
        if count + index + 1 >= 0:
            self._create_inline_item(transfer.data, count + index + 1)

    def add_unsent_file_message(self, friend, file_path, data):
        assert friend
        author = MessageAuthor(self._profile.name, MESSAGE_AUTHOR['ME'])
        size = os.path.getsize(file_path) if data is None else len(data)
        tm = UnsentFileMessage(file_path, data, util.get_unix_time(), author, size, friend.number)
        friend.append_message(tm)

        if self._is_friend_active(friend.number):
            self._create_unsent_file_item(tm)
            self._messages.scrollToBottom()

        return tm

    # Private methods

    def _is_friend_active(self, friend_number):
        if not self._contacts_manager.is_active_a_friend():
            return False

        return friend_number == self._contacts_manager.get_active_number()

    def _create_file_transfer_item(self, tm):
        return self._messages_items_factory.create_file_transfer_item(tm)

    def _create_inline_item(self, data, position):
        return self._messages_items_factory.create_inline_item(data, False, position)

    def _create_unsent_file_item(self, tm):
        return self._messages_items_factory.create_unsent_file_item(tm)
