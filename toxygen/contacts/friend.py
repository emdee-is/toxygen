from contacts import contact, common
from messenger.messages import *
import os
from contacts.contact_menu import *


class Friend(contact.Contact):
    """
    Friend in list of friends.
    """

    def __init__(self, profile_manager, message_getter, number, name, status_message, widget, tox_id):
        super().__init__(profile_manager, message_getter, number, name, status_message, widget, tox_id)
        self._receipts = 0
        self._typing_notification_handler = common.FriendTypingNotificationHandler(number)

    # -----------------------------------------------------------------------------------------------------------------
    # File transfers support
    # -----------------------------------------------------------------------------------------------------------------

    def insert_inline(self, before_message_id, inline):
        """
        Update status of active transfer and load inline if needed
        """
        try:
            tr = list(filter(lambda m: m.message_id == before_message_id, self._corr))[0]
            i = self._corr.index(tr)
            if inline:  # inline was loaded
                self._corr.insert(i, inline)
            return i - len(self._corr)
        except:
            pass

    def get_unsent_files(self):
        messages = filter(lambda m: type(m) is UnsentFileMessage, self._corr)
        return list(messages)

    def clear_unsent_files(self):
        self._corr = list(filter(lambda m: type(m) is not UnsentFileMessage, self._corr))

    def remove_invalid_unsent_files(self):
        def is_valid(message):
            if type(message) is not UnsentFileMessage:
                return True
            if message.data is not None:
                return True
            return os.path.exists(message.path)

        self._corr = list(filter(is_valid, self._corr))

    def delete_one_unsent_file(self, message_id):
        self._corr = list(filter(lambda m: not (type(m) is UnsentFileMessage and m.message_id == message_id),
                                 self._corr))

    # -----------------------------------------------------------------------------------------------------------------
    # Full status
    # -----------------------------------------------------------------------------------------------------------------

    def get_full_status(self):
        return self._status_message

    # -----------------------------------------------------------------------------------------------------------------
    # Typing notifications
    # -----------------------------------------------------------------------------------------------------------------

    def get_typing_notification_handler(self):
        return self._typing_notification_handler

    # -----------------------------------------------------------------------------------------------------------------
    # Context menu support
    # -----------------------------------------------------------------------------------------------------------------

    def get_context_menu_generator(self):
        return FriendMenuGenerator(self)
