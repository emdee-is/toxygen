# -*- mode: python; indent-tabs-mode: nil; py-indent-offset: 4; coding: utf-8 -*-
import pyaudio
import time
import threading
import itertools

from wrapper.toxav_enums import *
from av import screen_sharing
from av.call import Call
import common.tox_save

from utils import ui as util_ui
import wrapper_tests.support_testing as ts
from middleware.threads import invoke_in_main_thread
from main import sleep
from middleware.threads import BaseThread

global LOG
import logging
LOG = logging.getLogger('app.'+__name__)
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

TIMER_TIMEOUT = 30.0
bSTREAM_CALLBACK = False
iFPS = 25

class AV(common.tox_save.ToxAvSave):

    def __init__(self, toxav, settings):
        super().__init__(toxav)
        self._toxav = toxav
        self._settings = settings
        self._running = True
        s = settings
        if 'video' not in s:
            LOG.warn("AV.__init__ 'video' not in s" )
            LOG.debug(f"AV.__init__ {s!r}" )
        elif 'device' not in s['video']:
            LOG.warn("AV.__init__ 'device' not in s.video" )
            LOG.debug(f"AV.__init__ {s['video']!r}" )

        self._calls = {}  # dict: key - friend number, value - Call instance

        self._audio = None
        self._audio_stream = None
        self._audio_thread = None
        self._audio_running = False
        self._out_stream = None

        self._audio_channels = 1
        self._audio_duration = 60
        self._audio_rate_pa = 48000
        self._audio_rate_tox = 48000
        self._audio_rate_pa = 48000
        self._audio_krate_tox_audio = self._audio_rate_tox // 1000
        self._audio_krate_tox_video = 5000
        self._audio_sample_count_pa = self._audio_rate_pa * self._audio_channels * self._audio_duration // 1000
        self._audio_sample_count_tox = self._audio_rate_tox * self._audio_channels * self._audio_duration // 1000

        self._video = None
        self._video_thread = None
        self._video_running = None

        self._video_width = 320
        self._video_height = 240

        # was iOutput = self._settings._args.audio['output']
        iInput = self._settings['audio']['input']
        self.lPaSampleratesI = ts.lSdSamplerates(iInput)
        iOutput = self._settings['audio']['output']
        self.lPaSampleratesO = ts.lSdSamplerates(iOutput)
        global oPYA
        oPYA = self._audio = pyaudio.PyAudio()

    def stop(self):
        self._running = False
        self.stop_audio_thread()
        self.stop_video_thread()

    def __contains__(self, friend_number):
        return friend_number in self._calls

    # Calls

    def __call__(self, friend_number, audio, video):
        """Call friend with specified number"""
        if friend_number in self._calls:
            LOG.warn(f"__call__ already has {friend_number}")
            return
        if self._audio_krate_tox_audio not in ts.lToxSampleratesK:
            LOG.warn(f"__call__ {self._audio_krate_tox_audio} not in {ts.lToxSampleratesK}")

        try:
            self._toxav.call(friend_number,
                             self._audio_krate_tox_audio if audio else 0,
                             self._audio_krate_tox_video if video else 0)
        except Exception as e:
            LOG.warn(f"_toxav.call already has {friend_number}")
            return
        self._calls[friend_number] = Call(audio, video)
        threading.Timer(TIMER_TIMEOUT,
                        lambda: self.finish_not_started_call(friend_number)).start()

    def accept_call(self, friend_number, audio_enabled, video_enabled):
        # obsolete
        return self.call_accept_call(friend_number, audio_enabled, video_enabled)

    def call_accept_call(self, friend_number, audio_enabled, video_enabled):
        LOG.debug(f"call_accept_call from {friend_number} {self._running}" +
                  f"{audio_enabled} {video_enabled}")
        # import pdb; pdb.set_trace() - gets into q Qt exec_ problem
        # ts.trepan_handler()

        if self._audio_krate_tox_audio not in ts.lToxSampleratesK:
            LOG.warn(f"__call__ {self._audio_krate_tox_audio} not in {ts.lToxSampleratesK}")
        if self._running:
            self._calls[friend_number] = Call(audio_enabled, video_enabled)
            # audio_bit_rate: Audio bit rate in Kb/sec. Set this to 0 to disable audio sending.
            # video_bit_rate: Video bit rate in Kb/sec. Set this to 0 to disable video sending.
            try:
                self._toxav.answer(friend_number,
                                   self._audio_krate_tox_audio if audio_enabled else 0,
                                   self._audio_krate_tox_video if video_enabled else 0)
            except ArgumentError as e:
                LOG.debug(f"AV accept_call error from {friend_number} {self._running}" +
                          f"{e}")
                raise
            if audio_enabled:
                # may raise
                self.start_audio_thread()
            if video_enabled:
                # may raise
                self.start_video_thread()

    def finish_call(self, friend_number, by_friend=False):
        LOG.debug(f"finish_call  {friend_number}")
        if not by_friend:
            self._toxav.call_control(friend_number, TOXAV_CALL_CONTROL['CANCEL'])
        if friend_number in self._calls:
            del self._calls[friend_number]
        try:
            # AttributeError: 'int' object has no attribute 'out_audio'
            if not len(list(filter(lambda c: c.out_audio, self._calls))):
                self.stop_audio_thread()
            if not len(list(filter(lambda c: c.out_video, self._calls))):
                self.stop_video_thread()
        except Exception as e:
            LOG.error(f"finish_call FixMe:   {e}")
            # dunno
            self.stop_audio_thread()
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
        LOG.debug(f"toxav_call_state_cb {friend_number}")
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

    # Threads

    def start_audio_thread(self):
        """
        Start audio sending
        from a callback
        """
        global oPYA
        # was iInput = self._settings._args.audio['input']
        iInput = self._settings['audio']['input']
        if self._audio_thread is not None:
            LOG_WARN(f"start_audio_thread device={iInput}")
            return
        LOG_DEBUG(f"start_audio_thread device={iInput}")
        lPaSamplerates = ts.lSdSamplerates(iInput)
        if not(len(lPaSamplerates)):
            e = f"No supported sample rates for device: audio[input]={iInput!r}"
            LOG_ERROR(f"start_audio_thread {e}")
            #?? dunno - cancel call?
            return
        if not self._audio_rate_pa in lPaSamplerates:
            LOG_WARN(f"{self._audio_rate_pa} not in {lPaSamplerates!r}")
            if False:
                self._audio_rate_pa = oPYA.get_device_info_by_index(iInput)['defaultSampleRate']
            else:
                LOG_WARN(f"Setting audio_rate to: {lPaSamplerates[0]}")
                self._audio_rate_pa = lPaSamplerates[0]

        try:
            LOG_DEBUG( f"start_audio_thread framerate: {self._audio_rate_pa}" \
                     +f" device: {iInput}"
                     +f" supported: {lPaSamplerates!r}")
            if self._audio_rate_pa not in lPaSamplerates:
                LOG_WARN(f"PAudio sampling rate was {self._audio_rate_pa} changed to {lPaSamplerates[0]}")
                self._audio_rate_pa = lPaSamplerates[0]

            if bSTREAM_CALLBACK:
                self._audio_stream = oPYA.open(format=pyaudio.paInt16,
                                               rate=self._audio_rate_pa,
                                               channels=self._audio_channels,
                                               input=True,
                                               input_device_index=iInput,
                                               frames_per_buffer=self._audio_sample_count_pa * 10,
                                               stream_callback=self.send_audio_data)
                self._audio_running = True
                self._audio_stream.start_stream()
                while self._audio_stream.is_active():
                    sleep(0.1)
                self._audio_stream.stop_stream()
                self._audio_stream.close()

            else:
                self._audio_stream = oPYA.open(format=pyaudio.paInt16,
                                               rate=self._audio_rate_pa,
                                               channels=self._audio_channels,
                                               input=True,
                                               input_device_index=iInput,
                                               frames_per_buffer=self._audio_sample_count_pa * 10)
                self._audio_running = True
                self._audio_thread = BaseThread(target=self.send_audio,
                                                      name='_audio_thread')
                self._audio_thread.start()

        except Exception as e:
            LOG.error(f"Starting self._audio.open {e}")
            LOG.debug(repr(dict(format=pyaudio.paInt16,
                                rate=self._audio_rate_pa,
                                channels=self._audio_channels,
                                input=True,
                                input_device_index=iInput,
                                frames_per_buffer=self._audio_sample_count_pa * 10)))
            # catcher in place in calls_manager? not if from a callback
            # calls_manager._call.toxav_call_state_cb(friend_number, mask)
            # raise RuntimeError(e)
            return
        else:
            LOG_DEBUG(f"start_audio_thread {self._audio_stream!r}")

    def stop_audio_thread(self):

        if self._audio_thread is None:
            return
        self._audio_running = False

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
        s = self._settings
        if 'video' not in s:
            LOG.warn("AV.__init__ 'video' not in s" )
            LOG.debug(f"start_video_thread {s!r}" )
            raise RuntimeError("start_video_thread not 'video' in s)" )
        elif 'device' not in s['video']:
            LOG.error("start_video_thread not 'device' in s['video']" )
            LOG.debug(f"start_video_thread {s['video']!r}" )
            raise RuntimeError("start_video_thread not 'device' ins s['video']" )
        self._video_width = s['video']['width']
        self._video_height = s['video']['height']

        # dunno
        if True or s['video']['device'] == -1:
            self._video = screen_sharing.DesktopGrabber(s['video']['x'],
                                                        s['video']['y'],
                                                        s['video']['width'],
                                                        s['video']['height'])
        else:
            with ts.ignoreStdout():
                import cv2
            if s['video']['device'] == 0:
                # webcam
                self._video = cv2.VideoCapture(s['video']['device'], cv2.DSHOW)
            else:
                self._video = cv2.VideoCapture(s['video']['device'])
            self._video.set(cv2.CAP_PROP_FPS, iFPS)
            self._video.set(cv2.CAP_PROP_FRAME_WIDTH, self._video_width)
            self._video.set(cv2.CAP_PROP_FRAME_HEIGHT, self._video_height)
#            self._video.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        if self._video is None:
            LOG.error("start_video_thread " \
                     +f" device: {s['video']['device']}" \
                     +f" supported: {s['video']['width']} {s['video']['height']}")
            return
        LOG.info("start_video_thread " \
                 +f" device: {s['video']['device']}" \
                 +f" supported: {s['video']['width']} {s['video']['height']}")

        self._video_running = True
        self._video_thread = BaseThread(target=self.send_video,
                                        name='_video_thread')
        self._video_thread.start()

    def stop_video_thread(self):
        if self._video_thread is None:
            return

        self._video_running = False
        i = 0
        while i < ts.iTHREAD_JOINS:
            self._video_thread.join(ts.iTHREAD_TIMEOUT)
            try:
                if not self._video_thread.is_alive(): break
            except:
                # AttributeError: 'NoneType' object has no attribute 'join'
                break
            i = i + 1
        else:
            LOG.warn("self._video_thread.is_alive BLOCKED")
        self._video_thread = None
        self._video = None

    # Incoming chunks

    def audio_chunk(self, samples, channels_count, rate):
        """
        Incoming chunk
        """

        if self._out_stream is None:
            # was iOutput = self._settings._args.audio['output']
            iOutput = self._settings['audio']['output']
            if not rate in self.lPaSampleratesO:
                LOG.warn(f"{rate} not in {self.lPaSampleratesO!r}")
                if False:
                    rate = oPYA.get_device_info_by_index(iOutput)['defaultSampleRate']
                LOG.warn(f"Setting audio_rate to: {self.lPaSampleratesO[0]}")
                rate = self.lPaSampleratesO[0]
            try:
                with ts.ignoreStderr():
                    self._out_stream = oPYA.open(format=pyaudio.paInt16,
                                                 channels=channels_count,
                                                 rate=rate,
                                                 output_device_index=iOutput,
                                                 output=True)
            except Exception as e:
                LOG.error(f"Error playing audio_chunk creating self._out_stream   {e}")
                invoke_in_main_thread(util_ui.message_box,
                                    str(e),
                                    util_ui.tr("Error Chunking audio"))
                # dunno
                self.stop()
                return

        iOutput = self._settings['audio']['output']
        LOG.debug(f"audio_chunk output_device_index={iOutput} rate={rate} channels={channels_count}")
        self._out_stream.write(samples)

    # AV sending

    def send_audio_data(self, data, count, *largs, **kwargs):
        pcm = data
        # :param sampling_rate: Audio sampling rate used in this frame.
        if self._toxav is None:
            raise RuntimeError("_toxav not initialized")
        if self._audio_rate_tox not in ts.lToxSamplerates:
            LOG.warn(f"ToxAudio sampling rate was {self._audio_rate_tox} changed to {ts.lToxSamplerates[0]}")
            self._audio_rate_tox = ts.lToxSamplerates[0]

        for friend_num in self._calls:
            if self._calls[friend_num].out_audio:
                try:
                    # app.av.calls ERROR Error send_audio:   One of the frame parameters was invalid. E.g. the resolution may be too small or too large, or the audio sampling rate may be unsupported
                    # app.av.calls ERROR Error send_audio audio_send_frame: This client is currently not in a call with the friend.
                    self._toxav.audio_send_frame(friend_num,
                                                 pcm,
                                                 count,
                                                 self._audio_channels,
                                                 self._audio_rate_tox)
                except Exception as e:
                   LOG.error(f"Error send_audio audio_send_frame: {e}")
                   LOG.debug(f"send_audio self._audio_rate_tox={self._audio_rate_tox} self._audio_channels={self._audio_channels}")
#                   invoke_in_main_thread(util_ui.message_box,
#                                    str(e),
#                                    util_ui.tr("Error send_audio audio_send_frame"))
                   pass

    def send_audio(self):
        """
        This method sends audio to friends
        """
        i=0
        count = self._audio_sample_count_tox
        LOG.debug(f"send_audio stream={self._audio_stream}")
        while self._audio_running:
            try:
                pcm = self._audio_stream.read(count, exception_on_overflow=False)
                if not pcm:
                    sleep(0.1)
                else:
                    self.send_audio_data(pcm, count)
            except:
                LOG_DEBUG(f"error send_audio {i}")
            else:
                LOG_TRACE(f"send_audio {i}")
            i += 1
            sleep(0.01)

    def send_video(self):
        """
        This method sends video to friends
        """
        LOG.debug(f"send_video thread={threading.current_thread().name}"
                  +f" self._video_running={self._video_running}"
                  +f" device: {self._settings['video']['device']}" )
        while self._video_running:
            try:
                result, frame = self._video.read()
                if not result:
                    LOG.warn(f"send_video video_send_frame _video.read result={result}")
                    break
                if frame is None:
                    LOG.warn(f"send_video video_send_frame _video.read result={result} frame={frame}")
                    continue
                else:
                    LOG_TRACE(f"send_video video_send_frame _video.read result={result}")
                    height, width, channels = frame.shape
                    friends = []
                    for friend_num in self._calls:
                        if self._calls[friend_num].out_video:
                            friends.append(friend_num)
                    if len(friends) == 0:
                        LOG.warn(f"send_video video_send_frame no friends")
                    else:
                        LOG_TRACE(f"send_video video_send_frame {friends}")
                        friend_num = friends[0]
                        try:
                            y, u, v = self.convert_bgr_to_yuv(frame)
                            self._toxav.video_send_frame(friend_num, width, height, y, u, v)
                        except Exception as e:
                            LOG.debug(f"send_video video_send_frame ERROR {e}")
                            pass

            except Exception as e:
                LOG.error(f"send_video video_send_frame {e}")
                pass

            sleep( 1.0/iFPS)

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
        with ts.ignoreStdout():
            import cv2
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV_I420)

        y = frame[:self._video_height, :]
        y = list(itertools.chain.from_iterable(y))

        import numpy as np
        u = np.zeros((self._video_height // 2, self._video_width // 2), dtype=np.int)
        u[::2, :] = frame[self._video_height:self._video_height * 5 // 4, :self._video_width // 2]
        u[1::2, :] = frame[self._video_height:self._video_height * 5 // 4, self._video_width // 2:]
        u = list(itertools.chain.from_iterable(u))
        v = np.zeros((self._video_height // 2, self._video_width // 2), dtype=np.int)
        v[::2, :] = frame[self._video_height * 5 // 4:, :self._video_width // 2]
        v[1::2, :] = frame[self._video_height * 5 // 4:, self._video_width // 2:]
        v = list(itertools.chain.from_iterable(v))

        return bytes(y), bytes(u), bytes(v)
