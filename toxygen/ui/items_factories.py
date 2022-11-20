from ui.contact_items import *
from ui.messages_widgets import *


class ContactItemsFactory:

    def __init__(self, settings, main_screen):
        self._settings = settings
        self._friends_list = main_screen.friends_list

    def create_contact_item(self):
        item = ContactItem(self._settings)
        elem = QtWidgets.QListWidgetItem(self._friends_list)
        elem.setSizeHint(QtCore.QSize(250, 40 if self._settings['compact_mode'] else 70))
        self._friends_list.addItem(elem)
        self._friends_list.setItemWidget(elem, item)

        return item


class MessagesItemsFactory:

    def __init__(self, settings, plugin_loader, smiley_loader, main_screen, delete_action):
        self._file_transfers_handler = None
        self._settings, self._plugin_loader = settings, plugin_loader
        self._smiley_loader, self._delete_action = smiley_loader, delete_action
        self._messages = main_screen.messages
        self._message_edit = main_screen.messageEdit

    def set_file_transfers_handler(self, file_transfers_handler):
        self._file_transfers_handler = file_transfers_handler

    def create_message_item(self, message, append=True, pixmap=None):
        item = message.get_widget(self._settings, self._create_message_browser,
                                  self._delete_action, self._messages)
        if pixmap is not None:
            item.set_avatar(pixmap)
        elem = QtWidgets.QListWidgetItem()
        elem.setSizeHint(QtCore.QSize(self._messages.width(), item.height()))
        if append:
            self._messages.addItem(elem)
        else:
            self._messages.insertItem(0, elem)
        self._messages.setItemWidget(elem, item)

        return item

#   File "/var/local/src/toxygen/toxygen/file_transfers/file_transfers_handler.py", line 216, in transfer_finished
#     self._file_transfers_message_service.add_inline_message(transfer, index)
#   File "/var/local/src/toxygen/toxygen/file_transfers/file_transfers_messages_service.py", line 47, in add_inline_message
#     self._create_inline_item(transfer.data, count + index + 1)
#   File "/var/local/src/toxygen/toxygen/file_transfers/file_transfers_messages_service.py", line 75, in _create_inline_item
#     return self._messages_items_factory.create_inline_item(data, False, position)
#   File "/var/local/src/toxygen/toxygen/ui/items_factories.py", line 50, in create_inline_item
#     item = InlineImageItem(message.data, self._messages.width(), elem, self._messages)
# AttributeError: 'bytes' object has no attribute 'data'

    def create_inline_item(self, message, append=True, position=0):
        elem = QtWidgets.QListWidgetItem()
        # AttributeError: 'bytes' object has no attribute 'data'
        if type(message) == bytes:
            data = message
        elif hasattr(message, 'data'):
            data = message.data
        else:
            return
        item = InlineImageItem(data, self._messages.width(), elem, self._messages)
        elem.setSizeHint(QtCore.QSize(self._messages.width(), item.height()))
        if append:
            self._messages.addItem(elem)
        else:
            self._messages.insertItem(position, elem)
        self._messages.setItemWidget(elem, item)

        return item

    def create_unsent_file_item(self, message, append=True):
        item = message.get_widget(self._file_transfers_handler, self._settings, self._messages.width(), self._messages)
        elem = QtWidgets.QListWidgetItem()
        elem.setSizeHint(QtCore.QSize(self._messages.width() - 30, 34))
        if append:
            self._messages.addItem(elem)
        else:
            self._messages.insertItem(0, elem)
        self._messages.setItemWidget(elem, item)

        return item

    def create_file_transfer_item(self, message, append=True):
        item = message.get_widget(self._file_transfers_handler, self._settings, self._messages.width(), self._messages)
        elem = QtWidgets.QListWidgetItem()
        elem.setSizeHint(QtCore.QSize(self._messages.width() - 30, 34))
        if append:
            self._messages.addItem(elem)
        else:
            self._messages.insertItem(0, elem)
        self._messages.setItemWidget(elem, item)

        return item

    # -----------------------------------------------------------------------------------------------------------------
    # Private methods
    # -----------------------------------------------------------------------------------------------------------------

    def _create_message_browser(self, text, width, message_type, parent=None):
        return MessageBrowser(self._settings, self._message_edit, self._smiley_loader, self._plugin_loader,
                              text, width, message_type, parent)
