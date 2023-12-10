import plugin_super_class
from PyQt5 import QtCore
import time


class InvokeEvent(QtCore.QEvent):
    EVENT_TYPE = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())

    def __init__(self, fn, *args, **kwargs):
        QtCore.QEvent.__init__(self, InvokeEvent.EVENT_TYPE)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs


class Invoker(QtCore.QObject):

    def event(self, event):
        event.fn(*event.args, **event.kwargs)
        return True

_invoker = Invoker()


def invoke_in_main_thread(fn, *args, **kwargs):
    QtCore.QCoreApplication.postEvent(_invoker, InvokeEvent(fn, *args, **kwargs))


class Bot(plugin_super_class.PluginSuperClass):

    def __init__(self, *args):
        super(Bot, self).__init__('Bot', 'bot', *args)
        self._callback = None
        self._mode = 0
        self._message = "I'm away, will back soon"
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self.initialize)
        self._app = args[0]
        self._profile=self._app._ms._profile
        self._window = None

    def get_description(self):
        return QApplication.translate("Bot", 'Plugin to answer bot to your friends.')

    def start(self):
        self._timer.start(10000)

    def command(self, command):
        if command.startswith('mode '):
            self._mode = int(command.split(' ')[-1])
        elif command.startswith('message '):
            self._message = command[8:]
        else:
            super().command(command)

    def initialize(self):
        self._timer.stop()
        self._callback = self._tox.friend_message_cb

        def incoming_message(tox, friend_number, message_type, message, size, user_data):
            self._callback(tox, friend_number, message_type, message, size, user_data)
            if self._profile.status == 1: # TOX_USER_STATUS['AWAY']
                self.answer(friend_number, str(message, 'utf-8'))

        self._tox.callback_friend_message(incoming_message) # , None

    def stop(self):
        if not self._callback: return
        try:
            # TypeError: argument must be callable or integer function address
            self._tox.callback_friend_message(self._callback) # , None
        except: pass

    def close(self):
        self.stop()

    def answer(self, friend_number, message):
        if not self._mode:
            message = self._message
        invoke_in_main_thread(self._profile.send_message, message, friend_number)

