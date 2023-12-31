import threading

from PyQt5 import QtCore, QtGui, QtWidgets
import pyaudio
import wave

from ui import widgets
import utils.util as util
import wrapper_tests.support_testing as ts

global LOG
import logging
LOG = logging.getLogger('app.'+__name__)

class IncomingCallWidget(widgets.CenteredWidget):

    def __init__(self, settings, calls_manager, friend_number, text, name):
        super().__init__()
        self._settings = settings
        self._calls_manager = calls_manager
        self.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint) #  | QtCore.Qt.WindowStaysOnTopHint
        self.resize(QtCore.QSize(500, 270))
        self.avatar_label = QtWidgets.QLabel(self)
        self.avatar_label.setGeometry(QtCore.QRect(10, 20, 64, 64))
        self.avatar_label.setScaledContents(False)
        self.name = widgets.DataLabel(self)
        self.name.setGeometry(QtCore.QRect(90, 20, 300, 25))
        self._friend_number = friend_number
        font = QtGui.QFont()
        font.setFamily(settings['font'])
        font.setPointSize(16)
        font.setBold(True)
        self.name.setFont(font)
        self.call_type = widgets.DataLabel(self)
        self.call_type.setGeometry(QtCore.QRect(90, 55, 300, 25))
        self.call_type.setFont(font)
        self.accept_audio = QtWidgets.QPushButton(self)
        self.accept_audio.setGeometry(QtCore.QRect(20, 100, 150, 150))
        self.accept_video = QtWidgets.QPushButton(self)
        self.accept_video.setGeometry(QtCore.QRect(170, 100, 150, 150))
        self.decline = QtWidgets.QPushButton(self)
        self.decline.setGeometry(QtCore.QRect(320, 100, 150, 150))
        pixmap = QtGui.QPixmap(util.join_path(util.get_images_directory(), 'accept_audio.png'))
        icon = QtGui.QIcon(pixmap)
        self.accept_audio.setIcon(icon)
        pixmap = QtGui.QPixmap(util.join_path(util.get_images_directory(), 'accept_video.png'))
        icon = QtGui.QIcon(pixmap)
        self.accept_video.setIcon(icon)
        pixmap = QtGui.QPixmap(util.join_path(util.get_images_directory(), 'decline_call.png'))
        icon = QtGui.QIcon(pixmap)
        self.decline.setIcon(icon)
        self.accept_audio.setIconSize(QtCore.QSize(150, 150))
        self.accept_video.setIconSize(QtCore.QSize(140, 140))
        self.decline.setIconSize(QtCore.QSize(140, 140))
        #self.accept_audio.setStyleSheet("QPushButton { border: none }")
        #self.accept_video.setStyleSheet("QPushButton { border: none }")
        #self.decline.setStyleSheet("QPushButton { border: none }")
        self.setWindowTitle(text)
        self.name.setText(name)
        self.call_type.setText(text)
        self._processing = False
        self.accept_audio.clicked.connect(self.accept_call_with_audio)
        self.accept_video.clicked.connect(self.accept_call_with_video)
        self.decline.clicked.connect(self.decline_call)

        output_device_index = self._settings._oArgs.audio['output']

        if False and self._settings['calls_sound']:
            class SoundPlay(QtCore.QThread):

                def __init__(self):
                    QtCore.QThread.__init__(self)
                    self.a = None

                def run(self):
                    class AudioFile:
                        chunk = 1024

                        def __init__(self, fl):
                            self.stop = False
                            self.fl = fl
                            self.wf = wave.open(self.fl, 'rb')
                            self.p = pyaudio.PyAudio()
                            self.stream = self.p.open(
                                format=self.p.get_format_from_width(self.wf.getsampwidth()),
                                channels=self.wf.getnchannels(),
                                rate=self.wf.getframerate(),
                                # why no device?
                                output_device_index=output_device_index,
                                output=True)

                        def play(self):
                            while not self.stop:
                                data = self.wf.readframes(self.chunk)
                                # dunno
                                if not data: break
                                while data and not self.stop:
                                    self.stream.write(data)
                                    data = self.wf.readframes(self.chunk)
                                self.wf = wave.open(self.fl, 'rb')

                        def close(self):
                            try:
                                self.stream.close()
                                self.p.terminate()
                            except Exception as e:
                                # malloc_consolidate(): unaligned fastbin chunk detected
                                LOG.warn("SoundPlay close exception {e}")

                    self.a = AudioFile(util.join_path(util.get_sounds_directory(), 'call.wav'))
                    self.a.play()
                    self.a.close()

            self.thread = SoundPlay()
            self.thread.start()
        else:
            self.thread = None

    def stop(self):
        if self._processing:
            self.close()
        if self.thread is not None:
            self.thread.a.stop = True
            i = 0
            while i < ts.iTHREAD_JOINS:
                self.thread.wait(ts.iTHREAD_TIMEOUT)
                if not self.thread.isRunning(): break
                i = i + 1
            else:
                LOG.warn(f"SoundPlay {self.thread.a} BLOCKED")
                # Fatal Python error: Segmentation fault
                self.thread.a.stream.close()
                self.thread.a.p.terminate()
                self.thread.a.close()
            # dunno -failsafe
            self.thread.terminate()
        #? dunno
        self._processing = False

    def accept_call_with_audio(self):
        if self._processing:
            LOG.warn(f" accept_call_with_audio  from {self._friend_number}")
            return
        LOG.debug(f" accept_call_with_audio  from {self._friend_number}")
        self._processing = True
        try:
            self._calls_manager.accept_call(self._friend_number, True, False)
        finally:
            self.stop()

    def accept_call_with_video(self):
        # ts.trepan_handler()

        if self._processing:
            LOG.warn(__name__+f" accept_call_with_video from {self._friend_number}")
            return
        self.setWindowTitle('Answering video call')
        self._processing = True
        LOG.debug(f" accept_call_with_video from {self._friend_number}")
        try:
            self._calls_manager.accept_call(self._friend_number, True, True)
        finally:
            self.stop()

    def decline_call(self):
        if self._processing:
            return
        self._processing = True
        try:
            self._calls_manager.stop_call(self._friend_number, False)
        finally:
            self.stop()

    def set_pixmap(self, pixmap):
        self.avatar_label.setPixmap(pixmap)
