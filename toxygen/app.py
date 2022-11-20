# -*- mode: python; indent-tabs-mode: nil; py-indent-offset: 4; coding: utf-8 -*-
import os
import sys
import traceback
from random import shuffle
import threading
from time import sleep

from gevent import monkey; monkey.patch_all(); del monkey   # noqa
import gevent

from PyQt5 import QtWidgets, QtGui, QtCore
from qtpy.QtCore import QTimer
from qtpy.QtWidgets import QApplication

try:
    import coloredlogs
    if 'COLOREDLOGS_LEVEL_STYLES' not in os.environ:
        os.environ['COLOREDLOGS_LEVEL_STYLES'] = 'spam=22;debug=28;verbose=34;notice=220;warning=202;success=118,bold;error=124;critical=background=red'
    # https://pypi.org/project/coloredlogs/
except ImportError as e:
    coloredlogs = False

# install https://github.com/weechat/qweechat
# if you want IRC and jabber

from middleware import threads
import middleware.callbacks as callbacks
import updater.updater as updater
from middleware.tox_factory import tox_factory
import wrapper.toxencryptsave as tox_encrypt_save
import user_data.toxes
from user_data import settings
from user_data.settings import get_user_config_path, merge_args_into_settings
from user_data.settings import Settings
from user_data.profile_manager import ProfileManager

from plugin_support.plugin_support import PluginLoader

import ui.password_screen as password_screen
from ui.login_screen import LoginScreen
from ui.main_screen import MainWindow
from ui import tray

import utils.ui as util_ui
import utils.util as util
from av.calls_manager import CallsManager
from common.provider import Provider
from contacts.contact_provider import ContactProvider
from contacts.contacts_manager import ContactsManager
from contacts.friend_factory import FriendFactory
from contacts.group_factory import GroupFactory
from contacts.group_peer_factory import GroupPeerFactory
from contacts.profile import Profile
from file_transfers.file_transfers_handler import FileTransfersHandler
from file_transfers.file_transfers_messages_service import FileTransfersMessagesService
from groups.groups_service import GroupsService
from history.database import Database
from history.history import History
from messenger.messenger import Messenger
from network.tox_dns import ToxDns
from smileys.smileys import SmileyLoader
from ui.create_profile_screen import CreateProfileScreen
from ui.items_factories import MessagesItemsFactory, ContactItemsFactory
from ui.widgets_factory import WidgetsFactory
from user_data.backup_service import BackupService
import styles.style  # TODO: dynamic loading

import wrapper_tests.support_testing as ts

global LOG
import logging
LOG = logging.getLogger('app')

IDLE_PERIOD = 0.10
iNODES=8

def setup_logging(oArgs):
    global LOG
    logging._defaultFormatter = logging.Formatter(datefmt='%m-%d %H:%M:%S',
                                                  fmt='%(levelname)s:%(name)s %(message)s')
    logging._defaultFormatter.default_time_format = '%m-%d %H:%M:%S'
    logging._defaultFormatter.default_msec_format = ''

    if coloredlogs:
        aKw = dict(level=oArgs.loglevel,
                   logger=LOG,
                   fmt='%(name)s %(levelname)s %(message)s')
        aKw['stream'] = sys.stdout
        coloredlogs.install(**aKw)

    else:
        aKw = dict(level=oArgs.loglevel,
                   format='%(name)s %(levelname)-4s %(message)s')
        aKw['stream'] = sys.stdout
        logging.basicConfig(**aKw)

    if oArgs.logfile:
        oFd = open(oArgs.logfile, 'wt')
        setattr(oArgs, 'log_oFd', oFd)
        oHandler = logging.StreamHandler(stream=oFd)
        LOG.addHandler(oHandler)

    LOG.setLevel(oArgs.loglevel)
    LOG.trace = lambda l: LOG.log(0, repr(l))
    LOG.info(f"Setting loglevel to {oArgs.loglevel!s}")

    if oArgs.loglevel < 20:
        # opencv debug
        sys.OpenCV_LOADER_DEBUG = True

#? with ignoreStderr(): for png
# silence logging PyQt5.uic.uiparser
logging.getLogger('PyQt5.uic').setLevel(logging.ERROR)
logging.getLogger('PyQt5.uic.uiparser').setLevel(logging.ERROR)
logging.getLogger('PyQt5.uic.properties').setLevel(logging.ERROR)

global iI
iI = 0

sSTYLE = """
.QWidget {font-family Helvetica;}
.QCheckBox { font-family Helvetica;}
.QComboBox { font-family Helvetica;}
.QGroupBox { font-family Helvetica;}
.QLabel {font-family Helvetica;}
.QLineEdit { font-family Helvetica;}
.QListWidget { font-family Helvetica;}
.QListWidgetItem { font-family Helvetica;}
.QMainWindow {font-family Helvetica;}
.QMenu {font-family Helvetica;}
.QMenuBar {font-family Helvetica;}
.QPlainText {font-family Courier; weight: 75;}
.QPlainTextEdit {font-family Courier;}
.QPushButton {font-family Helvetica;}
.QRadioButton { font-family Helvetica; }
.QText {font-family Courier; weight: 75; }
.QTextBrowser {font-family Courier; weight: 75; }
.QTextSingleLine {font-family Courier; weight: 75; }
.QToolBar { font-weight: bold; }
"""
from copy import deepcopy
class App:

    def __init__(self, version, oArgs):
        global LOG
        self._args = oArgs
        self._oArgs = oArgs
        self._path = path_to_profile = oArgs.profile
        uri = oArgs.uri
        logfile = oArgs.logfile
        loglevel = oArgs.loglevel

        setup_logging(oArgs)
        # sys.stderr.write( 'Command line args: ' +repr(oArgs) +'\n')
        LOG.info("Command line: " +' '.join(sys.argv[1:]))
        LOG.debug(f'oArgs = {oArgs!r}')
        LOG.info("Starting toxygen version " +version)

        self._version = version
        self._tox = None
        self._app = self._settings = self._profile_manager = None
        self._plugin_loader = self._messenger = None
        self._tox = self._ms = self._init = self._main_loop = self._av_loop = None
        self._uri = self._toxes = self._tray = self._file_transfer_handler = self._contacts_provider = None
        self._friend_factory = self._calls_manager = None
        self._contacts_manager = self._smiley_loader = None
        self._group_peer_factory = self._tox_dns = self._backup_service = None
        self._group_factory = self._groups_service = self._profile = None
        if uri is not None and uri.startswith('tox:'):
            self._uri = uri[4:]
        self._history = None

    # -----------------------------------------------------------------------------------------------------------------
    # Public methods
    # -----------------------------------------------------------------------------------------------------------------

    def set_trace(self):
        """unused"""
        LOG.debug('pdb.set_trace ')
        sys.stdin = sys.__stdin__
        sys.stdout = sys.__stdout__
        import pdb; pdb.set_trace()

    def ten(self, i=0):
        """unused"""
        global iI
        iI += 1
        if logging.getLogger('app').getEffectiveLevel() != 10:
            sys.stderr.write('CHANGED '+str(logging.getLogger().level+'\n'))
            LOG.setLevel(10)
            LOG.root.setLevel(10)
            logging.getLogger('app').setLevel(10)
        #sys.stderr.write(f"ten '+str(iI)+'  {i}"+' '+repr(LOG) +'\n')
        #LOG.debug('ten '+str(iI))

    def iMain(self):
        """
        Main function of app. loads login screen if needed and starts main screen
        """
        self._app = QtWidgets.QApplication([])
        self._load_icon()

        if util.get_platform() == 'Linux':
            QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_X11InitThreads)

        self._load_base_style()

        encrypt_save = tox_encrypt_save.ToxEncryptSave()
        self._toxes = user_data.toxes.ToxES(encrypt_save)
        try:
            # this throws everything as errors
            if not self._select_and_load_profile():
                return 2
            if hasattr(self._oArgs, 'update') and self._oArgs.update:
                if self._try_to_update(): return 3

            self._load_app_styles()
            if self._oArgs.language != 'English':
                # > /var/local/src/toxygen/toxygen/app.py(303)_load_app_translations()->None
                # -> self._app.translator = translator
                # (Pdb) Fatal Python error: Segmentation fault
                self._load_app_translations()
            self._create_dependencies()

            self._start_threads(True)

            if self._uri is not None:
                self._ms.add_contact(self._uri)
        except Exception as e:
            LOG.error(f"Error loading profile: {e!s}")
            sys.stderr.write(' iMain(): ' +f"Error loading profile: {e!s}" \
                             +'\n' + traceback.format_exc()+'\n')
            util_ui.message_box(str(e),
                                util_ui.tr('Error loading profile'))
            return 4

        self._app.lastWindowClosed.connect(self._app.quit)
        try:
            self._execute_app()
            self.quit()
            retval = 0
        except KeyboardInterrupt:
            retval = 0
        except Exception:
            retval = 1

        return retval

    # -----------------------------------------------------------------------------------------------------------------
    # App executing
    # -----------------------------------------------------------------------------------------------------------------

    def _execute_app(self):
        LOG.debug("_execute_app")

        while True:
            try:
                self._app.exec_()
            except Exception as ex:
                LOG.error('Unhandled exception: ' + str(ex))
            else:
                break

    def quit(self, retval=0):
        LOG.debug("quit")
        self._stop_app()

        # failsafe: segfaults on exit
        if hasattr(self, '_tox'):
            if self._tox and hasattr(self._tox, 'kill'):
                LOG.debug(f"quit: Killing {self._tox}")
                self._tox.kill()
            del self._tox

        if hasattr(self, '_app'):
            self._app.quit()
            del self._app.quit
            del self._app

        sys.stderr.write('quit raising SystemExit' +'\n')
        # hanging on gevents
        # Thread 1 "python3.9" received signal SIGSEGV, Segmentation fault.
        #44 0x00007ffff7fb2f93 in  () at /usr/lib/python3.9/site-packages/greenlet/_greenlet.cpython-39-x86_64-linux-gnu.so
        #45 0x00007ffff7fb31ef in  () at /usr/lib/python3.9/site-packages/greenlet/_greenlet.cpython-39-x86_64-linux-gnu.so
        #46 0x00007ffff452165c in hb_shape_plan_create_cached2 () at /usr/lib64/libharfbuzz.so.0

        raise SystemExit(retval)

    def _stop_app(self):
        LOG.debug("_stop_app")
        self._save_profile()
        #? self._history.save_history()

        self._plugin_loader.stop()
        try:
            self._stop_threads(is_app_closing=True)
        except (Exception, RuntimeError):
            # RuntimeError: cannot join current thread
            pass
        if hasattr(self, '_tray') and self._tray:
            self._tray.hide()
        self._settings.close()

        LOG.debug(f"stop_app: Killing {self._tox}")
        self._kill_toxav()
        self._kill_tox()
        del self._tox

        oArgs = self._oArgs
        if hasattr(oArgs, 'log_oFd'):
            LOG.debug(f"Closing {oArgs.log_oFd}")
            oArgs.log_oFd.close()
            delattr(oArgs, 'log_oFd')

    # -----------------------------------------------------------------------------------------------------------------
    # App loading
    # -----------------------------------------------------------------------------------------------------------------

    def _load_base_style(self):
        if self._oArgs.theme in ['', 'default']: return

        if qdarkstyle:
            LOG.debug("_load_base_style qdarkstyle " +self._oArgs.theme)
            # QDarkStyleSheet
            if self._oArgs.theme == 'light':
                from qdarkstyle.light.palette import LightPalette
                style = qdarkstyle.load_stylesheet(palette=LightPalette)
            else:
                from qdarkstyle.dark.palette import DarkPalette
                style = qdarkstyle.load_stylesheet(palette=DarkPalette)
        else:
            LOG.debug("_load_base_style qss " +self._oArgs.theme)
            name = self._oArgs.theme + '.qss'
            with open(util.join_path(util.get_styles_directory(), name)) as fl:
                style = fl.read()
        style += '\n' +sSTYLE
        self._app.setStyleSheet(style)

    def _load_app_styles(self):
        LOG.debug(f"_load_app_styles {list(settings.built_in_themes().keys())!r}")
        # application color scheme
        if self._settings['theme'] in ['', 'default']: return
        for theme in settings.built_in_themes().keys():
            if self._settings['theme'] != theme:
                continue
            if qdarkstyle:
                LOG.debug("_load_base_style qdarkstyle " +self._oArgs.theme)
                # QDarkStyleSheet
                if self._oArgs.theme == 'light':
                    from qdarkstyle.light.palette import LightPalette
                    style = qdarkstyle.load_stylesheet(palette=LightPalette)
                else:
                    from qdarkstyle.dark.palette import DarkPalette
                    style = qdarkstyle.load_stylesheet(palette=DarkPalette)
            else:
                theme_path = settings.built_in_themes()[theme]
                file_path = util.join_path(util.get_styles_directory(), theme_path)
                if not os.path.isfile(file_path):
                    LOG.warn('_load_app_styles: no theme file ' + file_path)
                    continue
                with open(file_path) as fl:
                    style = fl.read()
                LOG.debug('_load_app_styles: loading theme file ' + file_path)
            style += '\n' +sSTYLE
            self._app.setStyleSheet(style)
            LOG.info('_load_app_styles: loaded theme ' +self._oArgs.theme)
            break

    def _load_login_screen_translations(self):
        LOG.debug("_load_login_screen_translations")
        current_language, supported_languages = self._get_languages()
        if current_language not in supported_languages:
            return
        lang_path = supported_languages[current_language]
        translator = QtCore.QTranslator()
        translator.load(util.get_translations_directory() + lang_path)
        self._app.installTranslator(translator)
        self._app.translator = translator

    def _load_icon(self):
        LOG.debug("_load_icon")
        icon_file = os.path.join(util.get_images_directory(), 'icon.png')
        self._app.setWindowIcon(QtGui.QIcon(icon_file))

    @staticmethod
    def _get_languages():
        LOG.debug("_get_languages")
        current_locale = QtCore.QLocale()
        curr_language = current_locale.languageToString(current_locale.language())
        supported_languages = settings.supported_languages()

        return curr_language, supported_languages

    def _load_app_translations(self):
        LOG.debug("_load_app_translations")
        lang = settings.supported_languages()[self._settings['language']]
        translator = QtCore.QTranslator()
        translator.load(os.path.join(util.get_translations_directory(), lang))
        self._app.installTranslator(translator)
        self._app.translator = translator

    def _select_and_load_profile(self):
        LOG.debug("_select_and_load_profile: " +repr(self._path))

        if self._path is not None:
            # toxygen was started with path to profile
            try:
                assert os.path.exists(self._path), self._path
                self._load_existing_profile(self._path)
            except Exception as e:
                LOG.error('_load_existing_profile failed: ' + str(e))
                title = 'Loading the profile failed '
                if self._path:
                    title += os.path.basename(self._path)
                text = 'Loading the profile failed - \n' +str(e)
                if 'Dis' == 'Abled':
                    text += '\nLoading the profile failed - \n' \
                      +str(e) +'\nContinue with a default profile?'
                    reply = util_ui.question(text, title)
                    if not reply:
                        LOG.debug('_load_existing_profile not continuing ')
                        raise
                    LOG.debug('_load_existing_profile continuing ')
                    # drop through
                else:
                    util_ui.message_box(text, title)
                    raise
        else:
            auto_profile = Settings.get_auto_profile()
            if auto_profile is None:  # no default profile
                LOG.debug('_select_and_load_profile no default profile ')
                result = self._select_profile()
                if result is None:
                    LOG.debug('no selected profile ')
                    return False
                if result.is_new_profile():  # create new profile
                    if not self._create_new_profile(result.profile_path):
                        LOG.warn('no new profile ')
                        return False
                    LOG.debug('created new profile ')
                else:  # load existing profile
                    self._load_existing_profile(result.profile_path)
                    # drop through
                self._path = result.profile_path
            else:  # default profile
                LOG.debug('loading default profile ')
                self._path = auto_profile
                self._load_existing_profile(auto_profile)

        if settings.is_active_profile(self._path):  # profile is in use
            LOG.warn(f"_select_and_load_profile active: {self._path}")
            profile_name = util.get_profile_name_from_path(self._path)
            title = util_ui.tr('Profile {}').format(profile_name)
            text = util_ui.tr(
                'Other instance of Toxygen uses this profile or profile was not properly closed. Continue?')
            reply = util_ui.question(text, title)
            if not reply:
                return False

        self._settings.set_active_profile()

        return True

    # -----------------------------------------------------------------------------------------------------------------
    # Threads
    # -----------------------------------------------------------------------------------------------------------------

    def _start_threads(self, initial_start=True):
        LOG.debug(f"_start_threads before: {threading.enumerate()!r}")
        # init thread
        self._init = threads.InitThread(self._tox,
                                        self._plugin_loader,
                                        self._settings,
                                        self,
                                        initial_start)
        self._init.start()
        def te(): return [t.name for t in threading.enumerate()]
        LOG.debug(f"_start_threads init: {te()!r}")

        # starting threads for tox iterate and toxav iterate
        self._main_loop = threads.ToxIterateThread(self._tox)
        self._main_loop.start()

        self._av_loop = threads.ToxAVIterateThread(self._tox.AV)
        self._av_loop.start()

        if initial_start:
            threads.start_file_transfer_thread()
        LOG.debug(f"_start_threads after: {[t.name for t in threading.enumerate()]!r}")

    def _stop_threads(self, is_app_closing=True):
        LOG.debug("_stop_threads")
        self._init.stop_thread(1.0)

        self._av_loop.stop_thread()
        self._main_loop.stop_thread()

        if is_app_closing:
            threads.stop_file_transfer_thread()

    def iterate(self, n=100):
        interval = self._tox.iteration_interval()
        for i in range(n):
            self._tox.iterate()
            gevent.sleep(interval / 1000.0)

    # -----------------------------------------------------------------------------------------------------------------
    # Profiles
    # -----------------------------------------------------------------------------------------------------------------

    def _select_profile(self):
        LOG.debug("_select_profile")
        if self._oArgs.language != 'English':
            self._load_login_screen_translations()
        ls = LoginScreen()
        profiles = ProfileManager.find_profiles()
        ls.update_select(profiles)
        ls.show()
        self._app.exec_()
        return ls.result

    def _load_existing_profile(self, profile_path):
        LOG.info("_load_existing_profile " +repr(profile_path))
        assert os.path.exists(profile_path), profile_path
        self._profile_manager = ProfileManager(self._toxes, profile_path)
        data = self._profile_manager.open_profile()
        if self._toxes.is_data_encrypted(data):
            LOG.debug("_entering password")
            data = self._enter_password(data)
            LOG.debug("_entered password")
        json_file = profile_path.replace('.tox', '.json')
        assert os.path.exists(json_file), json_file
        LOG.debug("creating _settings from: " +json_file)
        self._settings = Settings(self._toxes, json_file, self)
        self._tox = self._create_tox(data, self._settings)
        LOG.debug("created _tox")

    def _create_new_profile(self, profile_name):
        LOG.info("_create_new_profile " + profile_name)
        result = self._get_create_profile_screen_result()
        if result is None:
            return False
        if result.save_into_default_folder:
            profile_path = util.join_path(get_user_config_path(), profile_name + '.tox')
        else:
            profile_path = util.join_path(util.curr_directory(__file__), profile_name + '.tox')
        if os.path.isfile(profile_path):
            util_ui.message_box(util_ui.tr('Profile with this name already exists'),
                                util_ui.tr('Error'))
            return False
        name = profile_name or 'toxygen_user'
        assert self._oArgs
        self._path = profile_path
        if result.password:
            self._toxes.set_password(result.password)
        self._settings = Settings(self._toxes,
                                  self._path.replace('.tox', '.json'),
                                  app=self)
        self._tox = self._create_tox(None,
                                     self._settings)
        self._tox.self_set_name(name if name else 'Toxygen User')
        self._tox.self_set_status_message('Toxing on Toxygen')

        self._profile_manager = ProfileManager(self._toxes, profile_path)
        try:
            self._save_profile()
        except Exception as ex:
            #? print(ex)
            LOG.error('Profile creation exception: ' + str(ex))
            text = util_ui.tr('Profile saving error! Does Toxygen have permission to write to this directory?')
            util_ui.message_box(text, util_ui.tr('Error'))

            return False
        current_language, supported_languages = self._get_languages()
        if current_language in supported_languages:
            self._settings['language'] = current_language
        self._settings.save()

        return True

    def _get_create_profile_screen_result(self):
        LOG.debug("_get_create_profile_screen_result")
        cps = CreateProfileScreen()
        cps.show()
        self._app.exec_()

        return cps.result

    def _save_profile(self, data=None):
        LOG.debug("_save_profile")
        data = data or self._tox.get_savedata()
        self._profile_manager.save_profile(data)

    # -----------------------------------------------------------------------------------------------------------------
    # Other private methods
    # -----------------------------------------------------------------------------------------------------------------

    def _enter_password(self, data):
        """
        Show password screen
        """
        LOG.debug("_enter_password")
        p = password_screen.PasswordScreen(self._toxes, data)
        p.show()
        self._app.lastWindowClosed.connect(self._app.quit)
        self._app.exec_()
        if p.result is not None:
            return p.result
        self._force_exit(0)
        return None

    def _reset(self):
        LOG.debug("_reset")
        """
        Create new tox instance (new network settings)
        :return: tox instance
        """
        self._contacts_manager.reset_contacts_statuses()
        self._stop_threads(False)
        data = self._tox.get_savedata()
        self._save_profile(data)
        self._kill_toxav()
        self._kill_tox()
        try:
            # create new tox instance
            self._tox = self._create_tox(data, self._settings)
            assert self._tox
            self._start_threads(False)

            tox_savers = [self._friend_factory, self._group_factory,
                          self._plugin_loader, self._contacts_manager,
                          self._contacts_provider, self._messenger,
                          self._file_transfer_handler,
                          self._groups_service, self._profile]
            for tox_saver in tox_savers:
                tox_saver.set_tox(self._tox)

            self._calls_manager.set_toxav(self._tox.AV)
            self._contacts_manager.update_friends_numbers()
            self._contacts_manager.update_groups_lists()
            self._contacts_manager.update_groups_numbers()

            self._init_callbacks()
        except BaseException as e:
            LOG.error(f"_reset :  {e}")
            LOG.debug('_reset: ' \
                     +'\n' + traceback.format_exc())
            title = util_ui.tr('Reset Error')
            text = util_ui.tr('Error:') + str(e)
            util_ui.message_box(text, title)

    def _create_dependencies(self):
        LOG.info(f"_create_dependencies toxygen version {self._version}")
        if hasattr(self._oArgs, 'update') and self._oArgs.update:
            self._backup_service = BackupService(self._settings,
                                                 self._profile_manager)
        self._smiley_loader = SmileyLoader(self._settings)
        self._tox_dns = ToxDns(self._settings)
        self._ms = MainWindow(self._settings, self._tray, self)

        db_path = self._path.replace('.tox', '.db')
        db = Database(db_path, self._toxes)
        if os.path.exists(db_path) and hasattr(db, 'open'):
            db.open()

        assert self._tox

        contact_items_factory = ContactItemsFactory(self._settings, self._ms)
        self._friend_factory = FriendFactory(self._profile_manager,
                                             self._settings,
                                             self._tox,
                                             db,
                                             contact_items_factory)
        self._group_factory = GroupFactory(self._profile_manager,
                                           self._settings,
                                           self._tox,
                                           db,
                                           contact_items_factory)
        self._group_peer_factory = GroupPeerFactory(self._tox,
                                                    self._profile_manager,
                                                    db,
                                                    contact_items_factory)
        self._contacts_provider = ContactProvider(self._tox,
                                                  self._friend_factory,
                                                  self._group_factory,
                                                  self._group_peer_factory)
        self._profile = Profile(self._profile_manager,
                                self._tox,
                                self._ms,
                                self._contacts_provider,
                                self._reset)
        self._init_profile()
        self._plugin_loader = PluginLoader(self._settings, self)
        history = None
        messages_items_factory = MessagesItemsFactory(self._settings,
                                                      self._plugin_loader,
                                                      self._smiley_loader,
                                                      self._ms,
                                                      lambda m: history.delete_message(m))
        history = History(self._contacts_provider, db,
                          self._settings, self._ms, messages_items_factory)
        self._contacts_manager = ContactsManager(self._tox,
                                                 self._settings,
                                                 self._ms,
                                                 self._profile_manager,
                                                 self._contacts_provider,
                                                 history,
                                                 self._tox_dns,
                                                 messages_items_factory)
        history.set_contacts_manager(self._contacts_manager)
        self._history = history
        self._calls_manager = CallsManager(self._tox.AV,
                                           self._settings,
                                           self._ms,
                                           self._contacts_manager,
                                           self)
        self._messenger = Messenger(self._tox,
                                    self._plugin_loader, self._ms, self._contacts_manager,
                                    self._contacts_provider, messages_items_factory, self._profile,
                                    self._calls_manager)
        file_transfers_message_service = FileTransfersMessagesService(self._contacts_manager, messages_items_factory,
                                                                      self._profile, self._ms)
        self._file_transfer_handler = FileTransfersHandler(self._tox, self._settings, self._contacts_provider,
                                                           file_transfers_message_service, self._profile)
        messages_items_factory.set_file_transfers_handler(self._file_transfer_handler)
        widgets_factory = None
        widgets_factory_provider = Provider(lambda: widgets_factory)
        self._groups_service = GroupsService(self._tox,
                                             self._contacts_manager,
                                             self._contacts_provider,
                                             self._ms,
                                             widgets_factory_provider)
        widgets_factory = WidgetsFactory(self._settings,
                                         self._profile,
                                         self._profile_manager,
                                         self._contacts_manager,
                                         self._file_transfer_handler,
                                         self._smiley_loader,
                                         self._plugin_loader,
                                         self._toxes,
                                         self._version,
                                         self._groups_service,
                                         history,
                                         self._contacts_provider)
        if False:
            self._tray = tray.init_tray(self._profile,
                                        self._settings,
                                        self._ms, self._toxes)
        self._ms.set_dependencies(widgets_factory,
                                  self._tray,
                                  self._contacts_manager,
                                  self._messenger,
                                  self._profile,
                                  self._plugin_loader,
                                  self._file_transfer_handler,
                                  history,
                                  self._calls_manager,
                                  self._groups_service, self._toxes, self)

        if False:
            # the tray icon does not die with the app
            self._tray.show()
        self._ms.show()

        # FixMe:
        self._log = lambda line: LOG.log(self._oArgs.loglevel,
                                         self._ms.status(line))
        # self._ms._log = self._log # was used in callbacks.py

        if False:
            self.status_handler = logging.Handler()
            self.status_handler.setLevel(logging.INFO) # self._oArgs.loglevel
            self.status_handler.handle = self._ms.status

        self._init_callbacks()
        LOG.info("_create_dependencies toxygen version " +self._version)

    def _try_to_update(self):
        LOG.debug("_try_to_update")
        updating = updater.start_update_if_needed(self._version, self._settings)
        if updating:
            LOG.info("Updating toxygen version " +self._version)
            self._save_profile()
            self._settings.close()
            self._kill_toxav()
            self._kill_tox()
        return updating

    def _create_tox(self, data, settings_):
        LOG.info("_create_tox calling tox_factory")
        assert self._oArgs
        retval = tox_factory(data=data, settings=settings_,
                             args=self._oArgs, app=self)
        LOG.debug("_create_tox succeeded")
        self._tox = retval
        return retval

    def _force_exit(self, retval=0):
        LOG.debug("_force_exit")
        sys.exit(0)

    def _init_callbacks(self, ms=None):
        LOG.debug("_init_callbacks")
        # this will block if you are not connected
        callbacks.init_callbacks(self._tox, self._profile, self._settings,
                                 self._plugin_loader, self._contacts_manager,
                                 self._calls_manager,
                                 self._file_transfer_handler, self._ms,
                                 self._tray,
                                 self._messenger, self._groups_service,
                                 self._contacts_provider, self._ms)

    def _init_profile(self):
        LOG.debug("_init_profile")
        if not self._profile.has_avatar():
            self._profile.reset_avatar(self._settings['identicons'])

    def _kill_toxav(self):
#        LOG_debug("_kill_toxav")
        self._calls_manager.set_toxav(None)
        self._tox.AV.kill()

    def _kill_tox(self):
#        LOG.debug("_kill_tox")
        self._tox.kill()

    def loop(self, n):
        """
        Im guessings - there are 3 sleeps - time, tox, and Qt
        """
        interval = self._tox.iteration_interval()
        for i in range(n):
            self._tox.iterate()
            QtCore.QThread.msleep(interval)
            # NO QtCore.QCoreApplication.processEvents()
            sleep(interval / 1000.0)

    def _test_tox(self):
        self.test_net()
        self._ms.log_console()

    def test_net(self, lElts=None, oThread=None, iMax=4):

        LOG.debug("test_net " +self._oArgs.network)
        # bootstrap
        LOG.debug('Calling generate_nodes: udp')
        lNodes = ts.generate_nodes(oArgs=self._oArgs,
                                   ipv='ipv4',
                                   udp_not_tcp=True)
        self._settings['current_nodes_udp'] = lNodes
        if not lNodes:
            LOG.warn('empty generate_nodes udp')
        LOG.debug('Calling generate_nodes: tcp')
        lNodes = ts.generate_nodes(oArgs=self._oArgs,
                                   ipv='ipv4',
                                   udp_not_tcp=False)
        self._settings['current_nodes_tcp'] = lNodes
        if not lNodes:
            LOG.warn('empty generate_nodes tcp')

        # if oThread and oThread._stop_thread: return
        LOG.debug("test_net network=" +self._oArgs.network +' iMax=' +str(iMax))
        if self._oArgs.network not in ['local', 'localnew', 'newlocal']:
            b = ts.bAreWeConnected()
            if b is None:
                i = os.system('ip route|grep ^def')
                if i > 0:
                    b = False
                else:
                    b = True
            if not b:
                LOG.warn("No default route for network " +self._oArgs.network)
                text = 'You have no default route - are you connected?'
                reply = util_ui.question(text, "Are you connected?")
                if not reply: return
                iMax = 1
            else:
                LOG.debug("Have default route for network " +self._oArgs.network)

        lUdpElts = self._settings['current_nodes_udp']
        if self._oArgs.proxy_type <= 0 and not lUdpElts:
            title = 'test_net Error'
            text = 'Error: ' + str('No UDP nodes')
            util_ui.message_box(text, title)
            return
        lTcpElts = self._settings['current_nodes_tcp']
        if self._oArgs.proxy_type > 0 and not lTcpElts:
            title = 'test_net Error'
            text = 'Error: ' + str('No TCP nodes')
            util_ui.message_box(text, title)
            return
        LOG.debug(f"test_net {self._oArgs.network} lenU={len(lUdpElts)} lenT={len(lTcpElts)} iMax= {iMax}")
        i = 0
        while i < iMax:
            # if oThread and oThread._stop_thread: return
            i = i + 1
            LOG.debug(f"bootstrapping status proxy={self._oArgs.proxy_type} # {i}")
            if self._oArgs.proxy_type == 0:
                self._test_bootstrap(lUdpElts)
            else:
                self._test_bootstrap([lUdpElts[0]])
                LOG.debug(f"relaying status # {i}")
                self._test_relays(self._settings['current_nodes_tcp'])
            status = self._tox.self_get_connection_status()
            if status > 0:
                LOG.info(f"Connected # {i}" +' : ' +repr(status))
                break
            LOG.trace(f"Connected status #{i}: {status!r}")
            self.loop(2)

    def _test_env(self):
        _settings = self._settings
        if 'proxy_type' not in _settings or _settings['proxy_type'] == 0 or \
          not _settings['proxy_host'] or not _settings['proxy_port']:
            env = dict( prot = 'ipv4')
            lElts = self._settings['current_nodes_udp']
        elif _settings['proxy_type'] == 2:
            env = dict(prot = 'socks5',
                       https_proxy='', \
                       socks_proxy='socks5://' \
                       +_settings['proxy_host'] +':' \
                       +str(_settings['proxy_port']))
            lElts = self._settings['current_nodes_tcp']
        elif _settings['proxy_type'] == 1:
            env = dict(prot = 'https',
                       socks_proxy='', \
                       https_proxy='http://' \
                       +_settings['proxy_host'] +':' \
                       +str(_settings['proxy_port']))
            lElts = _settings['current_nodes_tcp']
#        LOG.debug(f"test_env {len(lElts)}")
        return env

    def _test_bootstrap(self, lElts=None):
        if lElts is None:
            lElts = self._settings['current_nodes_udp']
        LOG.debug(f"_test_bootstrap #Elts={len(lElts)}")
        if not lElts:
            return
        shuffle(lElts)
        ts.bootstrap_udp(lElts[:iNODES], [self._tox])
        LOG.info("Connected status: " +repr(self._tox.self_get_connection_status()))

    def _test_relays(self, lElts=None):
        if lElts is None:
            lElts = self._settings['current_nodes_tcp']
        shuffle(lElts)
        LOG.debug(f"_test_relays {len(lElts)}")
        ts.bootstrap_tcp(lElts[:iNODES], [self._tox])

    def _test_nmap(self, lElts=None):
        LOG.debug("_test_nmap")
        if not self._tox: return
        title = 'Extended Test Suite'
        text = 'Run the Extended Test Suite?\nThe program may freeze for 1-10 minutes.'
        i = os.system('ip route|grep ^def >/dev/null')
        if i > 0:
            text += '\nYou have no default route - are you connected?'
        reply = util_ui.question(text, title)
        if not reply: return

        if lElts is None:
            if self._oArgs.proxy_type == 0:
                sProt = "udp4"
                lElts = self._settings['current_nodes_tcp']
            else:
                sProt = "tcp4"
                lElts = self._settings['current_nodes_tcp']
        shuffle(lElts)
        try:
            ts.bootstrap_iNmapInfo(lElts, self._oArgs, sProt)
            self._ms.log_console()
        except Exception as e:
            LOG.error(f"test_nmap ' +' :  {e}")
            LOG.error('_test_nmap(): ' \
                         +'\n' + traceback.format_exc())
            title = 'Test Suite Error'
            text = 'Error: ' + str(e)
            util_ui.message_box(text, title)

        # LOG.info("Connected status: " +repr(self._tox.self_get_connection_status()))
        self._ms.log_console()

    def _test_main(self):
        from tests.tests_socks import main as tests_main
        LOG.debug("_test_main")
        if not self._tox: return
        title = 'Extended Test Suite'
        text = 'Run the Extended Test Suite?\nThe program may freeze for 20-60 minutes.'
        reply = util_ui.question(text, title)
        if reply:
            if hasattr(self._oArgs, 'proxy_type') and self._oArgs.proxy_type:
                lArgs = ['--proxy_host', self._oArgs.proxy_host,
                         '--proxy_port', str(self._oArgs.proxy_port),
                         '--proxy_type', str(self._oArgs.proxy_type), ]
            else:
                lArgs = list()
            try:
                tests_main(lArgs)
            except Exception as e:
                LOG.error(f"_test_socks():  {e}")
                LOG.error('_test_socks(): ' \
                         +'\n' + traceback.format_exc())
                title = 'Extended Test Suite Error'
                text = 'Error:' + str(e)
                util_ui.message_box(text, title)
            self._ms.log_console()

class GEventProcessing:
    """Interoperability class between Qt/gevent that allows processing gevent
    tasks during Qt idle periods."""
    def __init__(self, idle_period=IDLE_PERIOD):
        # Limit the IDLE handler's frequency while still allow for gevent
        # to trigger a microthread anytime
        self._idle_period = idle_period
        # IDLE timer: on_idle is called whenever no Qt events left for
        # processing
        self._timer = QTimer()
        self._timer.timeout.connect(self.process_events)
        self._timer.start(0)
    def __enter__(self):
        pass
    def __exit__(self, *exc_info):
        self._timer.stop()
    def process_events(self, idle_period=None):
        if idle_period is None:
            idle_period = self._idle_period
        # Cooperative yield, allow gevent to monitor file handles via libevent
        gevent.sleep(idle_period)
