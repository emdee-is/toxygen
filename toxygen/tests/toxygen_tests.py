# -*- mode: python; indent-tabs-mode: nil; py-indent-offset: 4; coding: utf-8 -*-

from notifications import sound
from notifications.sound import SOUND_NOTIFICATION
from time import sleep

if True:
    def test_sound_notification(self):
        """
        Plays sound notification
        :param  type of notification
        """
        sound.sound_notification( SOUND_NOTIFICATION['MESSAGE'] )
        sleep(10)
        sound.sound_notification( SOUND_NOTIFICATION['FILE_TRANSFER'] )
        sleep(10)
        sound.sound_notification( None )
