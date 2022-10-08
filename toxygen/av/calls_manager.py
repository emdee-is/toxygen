# -*- mode: python; indent-tabs-mode: nil; py-indent-offset: 4; coding: utf-8 -*-

import sys
import threading

import av.calls
from messenger.messages import *
from ui import av_widgets
import common.event as event
import utils.ui as util_ui

global LOG
import logging
LOG = logging.getLogger('app.'+__name__)

class CallsManager:

    def __init__(self, toxav, settings, main_screen, contacts_manager, app=None):
        self._call = av.calls.AV(toxav, settings)  # object with data about calls
        self._call_widgets = {}  # dict of incoming call widgets
        self._incoming_calls = set()
        self._settings = settings
        self._main_screen = main_screen
        self._contacts_manager = contacts_manager
        self._call_started_event = event.Event()  # friend_number, audio, video, is_outgoing
        self._call_finished_event = event.Event()  # friend_number, is_declined
        self._app = app

    def set_toxav(self, toxav):
        self._call.set_toxav(toxav)

    # -----------------------------------------------------------------------------------------------------------------
    # Events
    # -----------------------------------------------------------------------------------------------------------------

    def get_call_started_event(self):
        return self._call_started_event

    call_started_event = property(get_call_started_event)

    def get_call_finished_event(self):
        return self._call_finished_event

    call_finished_event = property(get_call_finished_event)

    # -----------------------------------------------------------------------------------------------------------------
    # AV support
    # -----------------------------------------------------------------------------------------------------------------

    def call_click(self, audio=True, video=False):
        """User clicked audio button in main window"""
        num = self._contacts_manager.get_active_number()
        if not self._contacts_manager.is_active_a_friend():
            return
        if num not in self._call and self._contacts_manager.is_active_online():  # start call
            if not self._settings['audio']['enabled']:
                return
            self._call(num, audio, video)
            self._main_screen.active_call()
            self._call_started_event(num, audio, video, True)
        elif num in self._call:  # finish or cancel call if you call with active friend
            self.stop_call(num, False)

    def incoming_call(self, audio, video, friend_number):
        """
        Incoming call from friend.
        """
        LOG.debug(__name__ +f" incoming_call  {friend_number}")
        # if not self._settings['audio']['enabled']: return
        friend = self._contacts_manager.get_friend_by_number(friend_number)
        self._call_started_event(friend_number, audio, video, False)
        self._incoming_calls.add(friend_number)
        if friend_number == self._contacts_manager.get_active_number():
            self._main_screen.incoming_call()
        else:
            friend.actions = True
        text = util_ui.tr("Incoming video call") if video else util_ui.tr("Incoming audio call")
        self._call_widgets[friend_number] = self._get_incoming_call_widget(friend_number, text, friend.name)
        self._call_widgets[friend_number].set_pixmap(friend.get_pixmap())
        self._call_widgets[friend_number].show()

    def accept_call(self, friend_number, audio, video):
        """
        Accept incoming call with audio or video
        Called from a thread
        """

        LOG.debug(f"CM accept_call from {friend_number} {audio} {video}")
        sys.stdout.flush()

        try:
            self._call.call_accept_call(friend_number, audio, video)
        except Exception as e:
            LOG.error(f"accept_call _call.accept_call ERROR for {friend_number} {e}")
            self._main_screen.call_finished()
            if hasattr(self._main_screen, '_settings') and \
              'audio' in self._main_screen._settings and \
              'input' in self._main_screen._settings['audio']:
                iInput = self._settings['audio']['input']
                iOutput = self._settings['audio']['output']
                iVideo = self._settings['video']['device']
                LOG.debug(f"iInput={iInput} iOutput={iOutput} iVideo={iVideo}")
            elif hasattr(self._main_screen, '_settings') and \
              hasattr(self._main_screen._settings, 'audio') and \
              'input' not in self._main_screen._settings['audio']:
                LOG.warn(f"'audio' not in {self._main_screen._settings!r}")
            elif hasattr(self._main_screen, '_settings') and \
              hasattr(self._main_screen._settings, 'audio') and \
              'input' not in self._main_screen._settings['audio']:
                LOG.warn(f"'audio' not in {self._main_screen._settings!r}")
            else:
                LOG.warn(f"_settings not in self._main_screen")
            util_ui.message_box(str(e),
                            util_ui.tr('ERROR Accepting call from {friend_number}'))
        else:
            self._main_screen.active_call()

        finally:
            # does not terminate call - just the av_widget
            if friend_number in self._incoming_calls:
                self._incoming_calls.remove(friend_number)
            try:
                self._call_widgets[friend_number].close()
                del self._call_widgets[friend_number]
            except:
                # RuntimeError: wrapped C/C++ object of type IncomingCallWidget has been deleted

                pass
            LOG.debug(f" closed self._call_widgets[{friend_number}]")

    def stop_call(self, friend_number, by_friend):
        """
        Stop call with friend
        """
        LOG.debug(__name__+f" stop_call {friend_number}")
        if friend_number in self._incoming_calls:
            self._incoming_calls.remove(friend_number)
            is_declined = True
        else:
            is_declined = False
        self._main_screen.call_finished()
        self._call.finish_call(friend_number, by_friend)  # finish or decline call
        if friend_number in self._call_widgets:
            self._call_widgets[friend_number].close()
            del self._call_widgets[friend_number]

        def destroy_window():
            #??? FixMed
            is_video = self._call.is_video_call(friend_number)
            if is_video:
                import cv2
                cv2.destroyWindow(str(friend_number))

        threading.Timer(2.0, destroy_window).start()
        self._call_finished_event(friend_number, is_declined)

    def friend_exit(self, friend_number):
        if friend_number in self._call:
            self._call.finish_call(friend_number, True)

    # -----------------------------------------------------------------------------------------------------------------
    # Private methods
    # -----------------------------------------------------------------------------------------------------------------

    def _get_incoming_call_widget(self, friend_number, text, friend_name):
        return av_widgets.IncomingCallWidget(self._settings, self, friend_number, text, friend_name)
