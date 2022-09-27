import pyaudio
import time
import threading
from wrapper.toxav_enums import *
import cv2
import itertools
import numpy as np
from av import screen_sharing
from av.call import Call
import common.tox_save


class AV(common.tox_save.ToxAvSave):

    def __init__(self, toxav, settings):
        super().__init__(toxav)
        self._settings = settings
        self._running = True

        self._calls = {}  # dict: key - friend number, value - Call instance

        self._audio = None
        self._audio_stream = None
        self._audio_thread = None
        self._audio_running = False
        self._out_stream = None

        self._audio_rate = 8000
        self._audio_channels = 1
        self._audio_duration = 60
        self._audio_sample_count = self._audio_rate * self._audio_channels * self._audio_duration // 1000

        self._video = None
        self._video_thread = None
        self._video_running = False

        self._video_width = 640
        self._video_height = 480

    def stop(self):
        self._running = False
        self.stop_audio_thread()
        self.stop_video_thread()

    def __contains__(self, friend_number):
        return friend_number in self._calls

    # -----------------------------------------------------------------------------------------------------------------
    # Calls
    # -----------------------------------------------------------------------------------------------------------------

    def __call__(self, friend_number, audio, video):
        """Call friend with specified number"""
        self._toxav.call(friend_number, 32 if audio else 0, 5000 if video else 0)
        self._calls[friend_number] = Call(audio, video)
        threading.Timer(30.0, lambda: self.finish_not_started_call(friend_number)).start()

    def accept_call(self, friend_number, audio_enabled, video_enabled):
        if self._running:
            self._calls[friend_number] = Call(audio_enabled, video_enabled)
            self._toxav.answer(friend_number, 32 if audio_enabled else 0, 5000 if video_enabled else 0)
            if audio_enabled:
                self.start_audio_thread()
            if video_enabled:
                self.start_video_thread()

    def finish_call(self, friend_number, by_friend=False):
        if not by_friend:
            self._toxav.call_control(friend_number, TOXAV_CALL_CONTROL['CANCEL'])
        if friend_number in self._calls:
            del self._calls[friend_number]
        if not len(list(filter(lambda c: c.out_audio, self._calls))):
            self.stop_audio_thread()
        if not len(list(filter(lambda c: c.out_video, self._calls))):
            self.stop_video_thread()

    def finish_not_started_call(self, friend_number):
        if friend_number in self:
            call = self._calls[friend_number]
            if not call.is_active:
                self.finish_call(friend_number)

    def toxav_call_state_cb(self, friend_number, state):
        """
        New call state
        """
        call = self._calls[friend_number]
        call.is_active = True

        call.in_audio = state | TOXAV_FRIEND_CALL_STATE['SENDING_A'] > 0
        call.in_video = state | TOXAV_FRIEND_CALL_STATE['SENDING_V'] > 0

        if state | TOXAV_FRIEND_CALL_STATE['ACCEPTING_A'] and call.out_audio:
            self.start_audio_thread()

        if state | TOXAV_FRIEND_CALL_STATE['ACCEPTING_V'] and call.out_video:
            self.start_video_thread()

    def is_video_call(self, number):
        return number in self and self._calls[number].in_video

    # -----------------------------------------------------------------------------------------------------------------
    # Threads
    # -----------------------------------------------------------------------------------------------------------------

    def start_audio_thread(self):
        """
        Start audio sending
        """
        if self._audio_thread is not None:
            return

        self._audio_running = True

        self._audio = pyaudio.PyAudio()
        self._audio_stream = self._audio.open(format=pyaudio.paInt16,
                                              rate=self._audio_rate,
                                              channels=self._audio_channels,
                                              input=True,
                                              input_device_index=self._settings.audio['input'],
                                              frames_per_buffer=self._audio_sample_count * 10)

        self._audio_thread = threading.Thread(target=self.send_audio)
        self._audio_thread.start()

    def stop_audio_thread(self):

        if self._audio_thread is None:
            return

        self._audio_running = False

        self._audio_thread.join()

        self._audio_thread = None
        self._audio_stream = None
        self._audio = None

        if self._out_stream is not None:
            self._out_stream.stop_stream()
            self._out_stream.close()
            self._out_stream = None

    def start_video_thread(self):
        if self._video_thread is not None:
            return

        self._video_running = True
        self._video_width = s.video['width']
        self._video_height = s.video['height']

        if s.video['device'] == -1:
            self._video = screen_sharing.DesktopGrabber(self._settings.video['x'], self._settings.video['y'],
                                                        self._settings.video['width'], self._settings.video['height'])
        else:
            self._video = cv2.VideoCapture(self._settings.video['device'])
            self._video.set(cv2.CAP_PROP_FPS, 25)
            self._video.set(cv2.CAP_PROP_FRAME_WIDTH, self._video_width)
            self._video.set(cv2.CAP_PROP_FRAME_HEIGHT, self._video_height)

        self._video_thread = threading.Thread(target=self.send_video)
        self._video_thread.start()

    def stop_video_thread(self):
        if self._video_thread is None:
            return

        self._video_running = False
        self._video_thread.join()
        self._video_thread = None
        self._video = None

    # -----------------------------------------------------------------------------------------------------------------
    # Incoming chunks
    # -----------------------------------------------------------------------------------------------------------------

    def audio_chunk(self, samples, channels_count, rate):
        """
        Incoming chunk
        """

        if self._out_stream is None:
            self._out_stream = self._audio.open(format=pyaudio.paInt16,
                                                channels=channels_count,
                                                rate=rate,
                                                output_device_index=self._settings.audio['output'],
                                                output=True)
        self._out_stream.write(samples)

    # -----------------------------------------------------------------------------------------------------------------
    # AV sending
    # -----------------------------------------------------------------------------------------------------------------

    def send_audio(self):
        """
        This method sends audio to friends
        """

        while self._audio_running:
            try:
                pcm = self._audio_stream.read(self._audio_sample_count)
                if pcm:
                    for friend_num in self._calls:
                        if self._calls[friend_num].out_audio:
                            try:
                                self._toxav.audio_send_frame(friend_num, pcm, self._audio_sample_count,
                                                             self._audio_channels, self._audio_rate)
                            except:
                                pass
            except:
                pass

            time.sleep(0.01)

    def send_video(self):
        """
        This method sends video to friends
        """
        while self._video_running:
            try:
                result, frame = self._video.read()
                if result:
                    height, width, channels = frame.shape
                    for friend_num in self._calls:
                        if self._calls[friend_num].out_video:
                            try:
                                y, u, v = self.convert_bgr_to_yuv(frame)
                                self._toxav.video_send_frame(friend_num, width, height, y, u, v)
                            except:
                                pass
            except:
                pass

            time.sleep(0.01)

    def convert_bgr_to_yuv(self, frame):
        """
        :param frame: input bgr frame
        :return y, u, v: y, u, v values of frame

        How this function works:
        OpenCV creates YUV420 frame from BGR
        This frame has following structure and size:
        width, height - dim of input frame
        width, height * 1.5 - dim of output frame

                  width
        -------------------------
        |                       |
        |          Y            |      height
        |                       |
        -------------------------
        |           |           |
        |  U even   |   U odd   |      height // 4
        |           |           |
        -------------------------
        |           |           |
        |  V even   |   V odd   |      height // 4
        |           |           |
        -------------------------

         width // 2   width // 2

        Y, U, V can be extracted using slices and joined in one list using itertools.chain.from_iterable()
        Function returns bytes(y), bytes(u), bytes(v), because it is required for ctypes
        """
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV_I420)

        y = frame[:self._video_height, :]
        y = list(itertools.chain.from_iterable(y))

        u = np.zeros((self._video_height // 2, self._video_width // 2), dtype=np.int)
        u[::2, :] = frame[self._video_height:self._video_height * 5 // 4, :self._video_width // 2]
        u[1::2, :] = frame[self._video_height:self._video_height * 5 // 4, self._video_width // 2:]
        u = list(itertools.chain.from_iterable(u))
        v = np.zeros((self._video_height // 2, self._video_width // 2), dtype=np.int)
        v[::2, :] = frame[self._video_height * 5 // 4:, :self._video_width // 2]
        v[1::2, :] = frame[self._video_height * 5 // 4:, self._video_width // 2:]
        v = list(itertools.chain.from_iterable(v))

        return bytes(y), bytes(u), bytes(v)
