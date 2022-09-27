from PyQt5 import QtGui
from wrapper.toxcore_enums_and_consts import *
from wrapper.toxav_enums import *
from wrapper.tox import bin_to_string
import utils.ui as util_ui
import utils.util as util
import cv2
import numpy as np
from middleware.threads import invoke_in_main_thread, execute
from notifications.tray import tray_notification
from notifications.sound import *
import threading

# TODO: refactoring. Use contact provider instead of manager

# -----------------------------------------------------------------------------------------------------------------
# Callbacks - current user
# -----------------------------------------------------------------------------------------------------------------


def self_connection_status(tox, profile):
    """
    Current user changed connection status (offline, TCP, UDP)
    """
    def wrapped(tox_link, connection, user_data):
        print('Connection status: ', str(connection))
        status = tox.self_get_status() if connection != TOX_CONNECTION['NONE'] else None
        invoke_in_main_thread(profile.set_status, status)

    return wrapped


# -----------------------------------------------------------------------------------------------------------------
# Callbacks - friends
# -----------------------------------------------------------------------------------------------------------------


def friend_status(contacts_manager, file_transfer_handler, profile, settings):
    def wrapped(tox, friend_number, new_status, user_data):
        """
        Check friend's status (none, busy, away)
        """
        print("Friend's #{} status changed!".format(friend_number))
        friend = contacts_manager.get_friend_by_number(friend_number)
        if friend.status is None and settings['sound_notifications'] and profile.status != TOX_USER_STATUS['BUSY']:
            sound_notification(SOUND_NOTIFICATION['FRIEND_CONNECTION_STATUS'])
        invoke_in_main_thread(friend.set_status, new_status)

        def set_timer():
            t = threading.Timer(5, lambda: file_transfer_handler.send_files(friend_number))
            t.start()
        invoke_in_main_thread(set_timer)
        invoke_in_main_thread(contacts_manager.update_filtration)

    return wrapped


def friend_connection_status(contacts_manager, profile, settings, plugin_loader, file_transfer_handler,
                             messenger, calls_manager):
    def wrapped(tox, friend_number, new_status, user_data):
        """
        Check friend's connection status (offline, udp, tcp)
        """
        print("Friend #{} connection status: {}".format(friend_number, new_status))
        friend = contacts_manager.get_friend_by_number(friend_number)
        if new_status == TOX_CONNECTION['NONE']:
            invoke_in_main_thread(friend.set_status, None)
            invoke_in_main_thread(file_transfer_handler.friend_exit, friend_number)
            invoke_in_main_thread(contacts_manager.update_filtration)
            invoke_in_main_thread(messenger.friend_typing, friend_number, False)
            invoke_in_main_thread(calls_manager.friend_exit, friend_number)
            if settings['sound_notifications'] and profile.status != TOX_USER_STATUS['BUSY']:
                sound_notification(SOUND_NOTIFICATION['FRIEND_CONNECTION_STATUS'])
        elif friend.status is None:
            invoke_in_main_thread(file_transfer_handler.send_avatar, friend_number)
            invoke_in_main_thread(plugin_loader.friend_online, friend_number)

    return wrapped


def friend_name(contacts_provider, messenger):
    def wrapped(tox, friend_number, name, size, user_data):
        """
        Friend changed his name
        """
        print('New name friend #' + str(friend_number))
        friend = contacts_provider.get_friend_by_number(friend_number)
        old_name = friend.name
        new_name = str(name, 'utf-8')
        invoke_in_main_thread(friend.set_name, new_name)
        invoke_in_main_thread(messenger.new_friend_name, friend, old_name, new_name)

    return wrapped


def friend_status_message(contacts_manager, messenger):
    def wrapped(tox, friend_number, status_message, size, user_data):
        """
        :return: function for callback friend_status_message. It updates friend's status message
        and calls window repaint
        """
        friend = contacts_manager.get_friend_by_number(friend_number)
        invoke_in_main_thread(friend.set_status_message, str(status_message, 'utf-8'))
        print('User #{} has new status message'.format(friend_number))
        invoke_in_main_thread(messenger.send_messages, friend_number)

    return wrapped


def friend_message(messenger, contacts_manager, profile, settings, window, tray):
    def wrapped(tox, friend_number, message_type, message, size, user_data):
        """
        New message from friend
        """
        message = str(message, 'utf-8')
        invoke_in_main_thread(messenger.new_message, friend_number, message_type, message)
        if not window.isActiveWindow():
            friend = contacts_manager.get_friend_by_number(friend_number)
            if settings['notifications'] and profile.status != TOX_USER_STATUS['BUSY'] and not settings.locked:
                invoke_in_main_thread(tray_notification, friend.name, message, tray, window)
            if settings['sound_notifications'] and profile.status != TOX_USER_STATUS['BUSY']:
                sound_notification(SOUND_NOTIFICATION['MESSAGE'])
            icon = os.path.join(util.get_images_directory(), 'icon_new_messages.png')
            invoke_in_main_thread(tray.setIcon, QtGui.QIcon(icon))

    return wrapped


def friend_request(contacts_manager):
    def wrapped(tox, public_key, message, message_size, user_data):
        """
        Called when user get new friend request
        """
        print('Friend request')
        key = ''.join(chr(x) for x in public_key[:TOX_PUBLIC_KEY_SIZE])
        tox_id = bin_to_string(key, TOX_PUBLIC_KEY_SIZE)
        invoke_in_main_thread(contacts_manager.process_friend_request, tox_id, str(message, 'utf-8'))

    return wrapped


def friend_typing(messenger):
    def wrapped(tox, friend_number, typing, user_data):
        invoke_in_main_thread(messenger.friend_typing, friend_number, typing)

    return wrapped


def friend_read_receipt(messenger):
    def wrapped(tox, friend_number, message_id, user_data):
        invoke_in_main_thread(messenger.receipt, friend_number, message_id)

    return wrapped


# -----------------------------------------------------------------------------------------------------------------
# Callbacks - file transfers
# -----------------------------------------------------------------------------------------------------------------


def tox_file_recv(window, tray, profile, file_transfer_handler, contacts_manager, settings):
    """
    New incoming file
    """
    def wrapped(tox, friend_number, file_number, file_type, size, file_name, file_name_size, user_data):
        if file_type == TOX_FILE_KIND['DATA']:
            print('File')
            try:
                file_name = str(file_name[:file_name_size], 'utf-8')
            except:
                file_name = 'toxygen_file'
            invoke_in_main_thread(file_transfer_handler.incoming_file_transfer,
                                  friend_number,
                                  file_number,
                                  size,
                                  file_name)
            if not window.isActiveWindow():
                friend = contacts_manager.get_friend_by_number(friend_number)
                if settings['notifications'] and profile.status != TOX_USER_STATUS['BUSY'] and not settings.locked:
                    file_from = util_ui.tr("File from")
                    invoke_in_main_thread(tray_notification, file_from + ' ' + friend.name, file_name, tray, window)
                if settings['sound_notifications'] and profile.status != TOX_USER_STATUS['BUSY']:
                    sound_notification(SOUND_NOTIFICATION['FILE_TRANSFER'])
                icon = util.join_path(util.get_images_directory(), 'icon_new_messages.png')
                invoke_in_main_thread(tray.setIcon, QtGui.QIcon(icon))
        else:  # avatar
            print('Avatar')
            invoke_in_main_thread(file_transfer_handler.incoming_avatar,
                                  friend_number,
                                  file_number,
                                  size)
    return wrapped


def file_recv_chunk(file_transfer_handler):
    """
    Incoming chunk
    """
    def wrapped(tox, friend_number, file_number, position, chunk, length, user_data):
        chunk = chunk[:length] if length else None
        execute(file_transfer_handler.incoming_chunk, friend_number, file_number, position, chunk)

    return wrapped


def file_chunk_request(file_transfer_handler):
    """
    Outgoing chunk
    """
    def wrapped(tox, friend_number, file_number, position, size, user_data):
        execute(file_transfer_handler.outgoing_chunk, friend_number, file_number, position, size)

    return wrapped


def file_recv_control(file_transfer_handler):
    """
    Friend cancelled, paused or resumed file transfer
    """
    def wrapped(tox, friend_number, file_number, file_control, user_data):
        if file_control == TOX_FILE_CONTROL['CANCEL']:
            file_transfer_handler.cancel_transfer(friend_number, file_number, True)
        elif file_control == TOX_FILE_CONTROL['PAUSE']:
            file_transfer_handler.pause_transfer(friend_number, file_number, True)
        elif file_control == TOX_FILE_CONTROL['RESUME']:
            file_transfer_handler.resume_transfer(friend_number, file_number, True)

    return wrapped

# -----------------------------------------------------------------------------------------------------------------
# Callbacks - custom packets
# -----------------------------------------------------------------------------------------------------------------


def lossless_packet(plugin_loader):
    def wrapped(tox, friend_number, data, length, user_data):
        """
        Incoming lossless packet
        """
        data = data[:length]
        invoke_in_main_thread(plugin_loader.callback_lossless, friend_number, data)

    return wrapped


def lossy_packet(plugin_loader):
    def wrapped(tox, friend_number, data, length, user_data):
        """
        Incoming lossy packet
        """
        data = data[:length]
        invoke_in_main_thread(plugin_loader.callback_lossy, friend_number, data)

    return wrapped


# -----------------------------------------------------------------------------------------------------------------
# Callbacks - audio
# -----------------------------------------------------------------------------------------------------------------

def call_state(calls_manager):
    def wrapped(toxav, friend_number, mask, user_data):
        """
        New call state
        """
        print(friend_number, mask)
        if mask == TOXAV_FRIEND_CALL_STATE['FINISHED'] or mask == TOXAV_FRIEND_CALL_STATE['ERROR']:
            invoke_in_main_thread(calls_manager.stop_call, friend_number, True)
        else:
            calls_manager.toxav_call_state_cb(friend_number, mask)

    return wrapped


def call(calls_manager):
    def wrapped(toxav, friend_number, audio, video, user_data):
        """
        Incoming call from friend
        """
        print(friend_number, audio, video)
        invoke_in_main_thread(calls_manager.incoming_call, audio, video, friend_number)

    return wrapped


def callback_audio(calls_manager):
    def wrapped(toxav, friend_number, samples, audio_samples_per_channel, audio_channels_count, rate, user_data):
        """
        New audio chunk
        """
        calls_manager.call.audio_chunk(
            bytes(samples[:audio_samples_per_channel * 2 * audio_channels_count]),
            audio_channels_count,
            rate)

    return wrapped

# -----------------------------------------------------------------------------------------------------------------
# Callbacks - video
# -----------------------------------------------------------------------------------------------------------------


def video_receive_frame(toxav, friend_number, width, height, y, u, v, ystride, ustride, vstride, user_data):
    """
    Creates yuv frame from y, u, v and shows it using OpenCV
    For yuv => bgr we need this YUV420 frame:

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

    It can be created from initial y, u, v using slices
    """
    try:
        y_size = abs(max(width, abs(ystride)))
        u_size = abs(max(width // 2, abs(ustride)))
        v_size = abs(max(width // 2, abs(vstride)))

        y = np.asarray(y[:y_size * height], dtype=np.uint8).reshape(height, y_size)
        u = np.asarray(u[:u_size * height // 2], dtype=np.uint8).reshape(height // 2, u_size)
        v = np.asarray(v[:v_size * height // 2], dtype=np.uint8).reshape(height // 2, v_size)

        width -= width % 4
        height -= height % 4

        frame = np.zeros((int(height * 1.5), width), dtype=np.uint8)

        frame[:height, :] = y[:height, :width]
        frame[height:height * 5 // 4, :width // 2] = u[:height // 2:2, :width // 2]
        frame[height:height * 5 // 4, width // 2:] = u[1:height // 2:2, :width // 2]

        frame[height * 5 // 4:, :width // 2] = v[:height // 2:2, :width // 2]
        frame[height * 5 // 4:, width // 2:] = v[1:height // 2:2, :width // 2]

        frame = cv2.cvtColor(frame, cv2.COLOR_YUV2BGR_I420)

        invoke_in_main_thread(cv2.imshow, str(friend_number), frame)
    except Exception as ex:
        print(ex)

# -----------------------------------------------------------------------------------------------------------------
# Callbacks - groups
# -----------------------------------------------------------------------------------------------------------------


def group_message(window, tray, tox, messenger, settings, profile):
    """
    New message in group chat
    """
    def wrapped(tox_link, group_number, peer_id, message_type, message, length, user_data):
        message = str(message[:length], 'utf-8')
        invoke_in_main_thread(messenger.new_group_message, group_number, message_type, message, peer_id)
        if window.isActiveWindow():
            return
        bl = settings['notify_all_gc'] or profile.name in message
        name = tox.group_peer_get_name(group_number, peer_id)
        if settings['notifications'] and profile.status != TOX_USER_STATUS['BUSY'] and (not settings.locked) and bl:
            invoke_in_main_thread(tray_notification, name, message, tray, window)
        if settings['sound_notifications'] and bl and profile.status != TOX_USER_STATUS['BUSY']:
            sound_notification(SOUND_NOTIFICATION['MESSAGE'])
        icon = util.join_path(util.get_images_directory(), 'icon_new_messages.png')
        invoke_in_main_thread(tray.setIcon, QtGui.QIcon(icon))

    return wrapped


def group_private_message(window, tray, tox, messenger, settings, profile):
    """
    New private message in group chat
    """
    def wrapped(tox_link, group_number, peer_id, message_type, message, length, user_data):
        message = str(message[:length], 'utf-8')
        invoke_in_main_thread(messenger.new_group_private_message, group_number, message_type, message, peer_id)
        if window.isActiveWindow():
            return
        bl = settings['notify_all_gc'] or profile.name in message
        name = tox.group_peer_get_name(group_number, peer_id)
        if settings['notifications'] and profile.status != TOX_USER_STATUS['BUSY'] and (not settings.locked) and bl:
            invoke_in_main_thread(tray_notification, name, message, tray, window)
        if settings['sound_notifications'] and bl and profile.status != TOX_USER_STATUS['BUSY']:
            sound_notification(SOUND_NOTIFICATION['MESSAGE'])
        icon = util.join_path(util.get_images_directory(), 'icon_new_messages.png')
        invoke_in_main_thread(tray.setIcon, QtGui.QIcon(icon))

    return wrapped


def group_invite(window, settings, tray, profile, groups_service, contacts_provider):
    def wrapped(tox, friend_number, invite_data, length, group_name, group_name_length, user_data):
        group_name = str(bytes(group_name[:group_name_length]), 'utf-8')
        invoke_in_main_thread(groups_service.process_group_invite,
                              friend_number, group_name,
                              bytes(invite_data[:length]))
        if window.isActiveWindow():
            return
        if settings['notifications'] and profile.status != TOX_USER_STATUS['BUSY'] and not settings.locked:
            friend = contacts_provider.get_friend_by_number(friend_number)
            title = util_ui.tr('New invite to group chat')
            text = util_ui.tr('{} invites you to group "{}"').format(friend.name, group_name)
            invoke_in_main_thread(tray_notification, title, text, tray, window)
        icon = util.join_path(util.get_images_directory(), 'icon_new_messages.png')
        invoke_in_main_thread(tray.setIcon, QtGui.QIcon(icon))

    return wrapped


def group_self_join(contacts_provider, contacts_manager, groups_service):
    def wrapped(tox, group_number, user_data):
        group = contacts_provider.get_group_by_number(group_number)
        invoke_in_main_thread(group.set_status, TOX_USER_STATUS['NONE'])
        invoke_in_main_thread(groups_service.update_group_info, group)
        invoke_in_main_thread(contacts_manager.update_filtration)

    return wrapped


def group_peer_join(contacts_provider, groups_service):
    def wrapped(tox, group_number, peer_id, user_data):
        group = contacts_provider.get_group_by_number(group_number)
        group.add_peer(peer_id)
        invoke_in_main_thread(groups_service.generate_peers_list)
        invoke_in_main_thread(groups_service.update_group_info, group)

    return wrapped


def group_peer_exit(contacts_provider, groups_service, contacts_manager):
    def wrapped(tox, group_number, peer_id, message, length, user_data):
        group = contacts_provider.get_group_by_number(group_number)
        group.remove_peer(peer_id)
        invoke_in_main_thread(groups_service.generate_peers_list)

    return wrapped


def group_peer_name(contacts_provider, groups_service):
    def wrapped(tox, group_number, peer_id, name, length, user_data):
        group = contacts_provider.get_group_by_number(group_number)
        peer = group.get_peer_by_id(peer_id)
        peer.name = str(name[:length], 'utf-8')
        invoke_in_main_thread(groups_service.generate_peers_list)

    return wrapped


def group_peer_status(contacts_provider, groups_service):
    def wrapped(tox, group_number, peer_id, peer_status, user_data):
        group = contacts_provider.get_group_by_number(group_number)
        peer = group.get_peer_by_id(peer_id)
        peer.status = peer_status
        invoke_in_main_thread(groups_service.generate_peers_list)

    return wrapped


def group_topic(contacts_provider):
    def wrapped(tox, group_number, peer_id, topic, length, user_data):
        group = contacts_provider.get_group_by_number(group_number)
        topic = str(topic[:length], 'utf-8')
        invoke_in_main_thread(group.set_status_message, topic)

    return wrapped


def group_moderation(groups_service, contacts_provider, contacts_manager, messenger):

    def update_peer_role(group, mod_peer_id, peer_id, new_role):
        peer = group.get_peer_by_id(peer_id)
        peer.role = new_role
        # TODO: add info message

    def remove_peer(group, mod_peer_id, peer_id, is_ban):
        contacts_manager.remove_group_peer_by_id(group, peer_id)
        group.remove_peer(peer_id)
        # TODO: add info message

    def wrapped(tox, group_number, mod_peer_id, peer_id, event_type, user_data):
        group = contacts_provider.get_group_by_number(group_number)

        if event_type == TOX_GROUP_MOD_EVENT['KICK']:
            remove_peer(group, mod_peer_id, peer_id, False)
        elif event_type == TOX_GROUP_MOD_EVENT['BAN']:
            remove_peer(group, mod_peer_id, peer_id, True)
        elif event_type == TOX_GROUP_MOD_EVENT['OBSERVER']:
            update_peer_role(group, mod_peer_id, peer_id, TOX_GROUP_ROLE['OBSERVER'])
        elif event_type == TOX_GROUP_MOD_EVENT['USER']:
            update_peer_role(group, mod_peer_id, peer_id, TOX_GROUP_ROLE['USER'])
        elif event_type == TOX_GROUP_MOD_EVENT['MODERATOR']:
            update_peer_role(group, mod_peer_id, peer_id, TOX_GROUP_ROLE['MODERATOR'])

        invoke_in_main_thread(groups_service.generate_peers_list)

    return wrapped


def group_password(contacts_provider):

    def wrapped(tox_link, group_number, password, length, user_data):
        password = str(password[:length], 'utf-8')
        group = contacts_provider.get_group_by_number(group_number)
        group.password = password

    return wrapped


def group_peer_limit(contacts_provider):

    def wrapped(tox_link, group_number, peer_limit, user_data):
        group = contacts_provider.get_group_by_number(group_number)
        group.peer_limit = peer_limit

    return wrapped


def group_privacy_state(contacts_provider):

    def wrapped(tox_link, group_number, privacy_state, user_data):
        group = contacts_provider.get_group_by_number(group_number)
        group.is_private = privacy_state == TOX_GROUP_PRIVACY_STATE['PRIVATE']

    return wrapped

# -----------------------------------------------------------------------------------------------------------------
# Callbacks - initialization
# -----------------------------------------------------------------------------------------------------------------


def init_callbacks(tox, profile, settings, plugin_loader, contacts_manager,
                   calls_manager, file_transfer_handler, main_window, tray, messenger, groups_service,
                   contacts_provider):
    """
    Initialization of all callbacks.
    :param tox: Tox instance
    :param profile: Profile instance
    :param settings: Settings instance
    :param contacts_manager: ContactsManager instance
    :param contacts_manager: ContactsManager instance
    :param calls_manager: CallsManager instance
    :param file_transfer_handler: FileTransferHandler instance
    :param plugin_loader: PluginLoader instance
    :param main_window: MainWindow instance
    :param tray: tray (for notifications)
    :param messenger: Messenger instance
    :param groups_service: GroupsService instance
    :param contacts_provider: ContactsProvider instance
    """
    # self callbacks
    tox.callback_self_connection_status(self_connection_status(tox, profile))

    # friend callbacks
    tox.callback_friend_status(friend_status(contacts_manager, file_transfer_handler, profile, settings))
    tox.callback_friend_message(friend_message(messenger, contacts_manager, profile, settings, main_window, tray))
    tox.callback_friend_connection_status(friend_connection_status(contacts_manager, profile, settings, plugin_loader,
                                                                   file_transfer_handler, messenger, calls_manager))
    tox.callback_friend_name(friend_name(contacts_provider, messenger))
    tox.callback_friend_status_message(friend_status_message(contacts_manager, messenger))
    tox.callback_friend_request(friend_request(contacts_manager))
    tox.callback_friend_typing(friend_typing(messenger))
    tox.callback_friend_read_receipt(friend_read_receipt(messenger))

    # file transfer
    tox.callback_file_recv(tox_file_recv(main_window, tray, profile, file_transfer_handler,
                                         contacts_manager, settings))
    tox.callback_file_recv_chunk(file_recv_chunk(file_transfer_handler))
    tox.callback_file_chunk_request(file_chunk_request(file_transfer_handler))
    tox.callback_file_recv_control(file_recv_control(file_transfer_handler))

    # av
    toxav = tox.AV
    toxav.callback_call_state(call_state(calls_manager), 0)
    toxav.callback_call(call(calls_manager), 0)
    toxav.callback_audio_receive_frame(callback_audio(calls_manager), 0)
    toxav.callback_video_receive_frame(video_receive_frame, 0)

    # custom packets
    tox.callback_friend_lossless_packet(lossless_packet(plugin_loader))
    tox.callback_friend_lossy_packet(lossy_packet(plugin_loader))

    # gc callbacks
    tox.callback_group_message(group_message(main_window, tray, tox, messenger, settings, profile), 0)
    tox.callback_group_private_message(group_private_message(main_window, tray, tox, messenger, settings, profile), 0)
    tox.callback_group_invite(group_invite(main_window, settings, tray, profile, groups_service, contacts_provider), 0)
    tox.callback_group_self_join(group_self_join(contacts_provider, contacts_manager, groups_service), 0)
    tox.callback_group_peer_join(group_peer_join(contacts_provider, groups_service), 0)
    tox.callback_group_peer_exit(group_peer_exit(contacts_provider, groups_service, contacts_manager), 0)
    tox.callback_group_peer_name(group_peer_name(contacts_provider, groups_service), 0)
    tox.callback_group_peer_status(group_peer_status(contacts_provider, groups_service), 0)
    tox.callback_group_topic(group_topic(contacts_provider), 0)
    tox.callback_group_moderation(group_moderation(groups_service, contacts_provider, contacts_manager, messenger), 0)
    tox.callback_group_password(group_password(contacts_provider), 0)
    tox.callback_group_peer_limit(group_peer_limit(contacts_provider), 0)
    tox.callback_group_privacy_state(group_privacy_state(contacts_provider), 0)
