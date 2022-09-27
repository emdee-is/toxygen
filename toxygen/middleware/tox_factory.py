import user_data.settings
import wrapper.tox
import wrapper.toxcore_enums_and_consts as enums
import ctypes


def tox_factory(data=None, settings=None):
    """
    :param data: user data from .tox file. None = no saved data, create new profile
    :param settings: current profile settings. None = default settings will be used
    :return: new tox instance
    """
    if settings is None:
        settings = user_data.settings.Settings.get_default_settings()

    tox_options = wrapper.tox.Tox.options_new()
    tox_options.contents.udp_enabled = settings['udp_enabled']
    tox_options.contents.proxy_type = settings['proxy_type']
    tox_options.contents.proxy_host = bytes(settings['proxy_host'], 'UTF-8')
    tox_options.contents.proxy_port = settings['proxy_port']
    tox_options.contents.start_port = settings['start_port']
    tox_options.contents.end_port = settings['end_port']
    tox_options.contents.tcp_port = settings['tcp_port']
    tox_options.contents.local_discovery_enabled = settings['lan_discovery']
    if data:  # load existing profile
        tox_options.contents.savedata_type = enums.TOX_SAVEDATA_TYPE['TOX_SAVE']
        tox_options.contents.savedata_data = ctypes.c_char_p(data)
        tox_options.contents.savedata_length = len(data)
    else:  # create new profile
        tox_options.contents.savedata_type = enums.TOX_SAVEDATA_TYPE['NONE']
        tox_options.contents.savedata_data = None
        tox_options.contents.savedata_length = 0

    return wrapper.tox.Tox(tox_options)
