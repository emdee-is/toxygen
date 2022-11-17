# -*- mode: python; indent-tabs-mode: nil; py-indent-offset: 4; coding: utf-8 -*-
import datetime
import os
import platform
import re
import shutil
import sys
import time


def cached(func):
    saved_result = None

    def wrapped_func():
        nonlocal saved_result
        if saved_result is None:
            saved_result = func()

        return saved_result

    return wrapped_func

oFD=None
def log(data=None):
    global oFD
    if not oFD:
        if 'TMPDIR' in os.environ:
            logdir = os.environ['TMPDIR']
        else:
            logdir = '/tmp'
        try:
            oFD = open(join_path(logdir, 'toxygen.log'), 'a')
        except Exception as ex:
            oFD = None
            print(f"ERROR: opening toxygen.log:  {ex}")
            return
    if data is None: return oFD
    try:
        oFD.write(str(data) +'\n')
    except Exception as ex:
        print(f"ERROR: writing to toxygen.log:  {ex}")
    return data

def curr_directory(current_file=None):
    return os.path.dirname(os.path.realpath(current_file or __file__))


def get_base_directory(current_file=None):
    return os.path.dirname(curr_directory(current_file or __file__))


@cached
def get_images_directory():
    return get_app_directory('images')


@cached
def get_styles_directory():
    return get_app_directory('styles')


@cached
def get_sounds_directory():
    return get_app_directory('sounds')


@cached
def get_stickers_directory():
    return get_app_directory('stickers')


@cached
def get_smileys_directory():
    return get_app_directory('smileys')


@cached
def get_translations_directory():
    return get_app_directory('translations')


@cached
def get_plugins_directory():
    return get_app_directory('plugins')


@cached
def get_libs_directory():
    return get_app_directory('libs')


def get_app_directory(directory_name):
    return os.path.join(get_base_directory(), directory_name)


def get_profile_name_from_path(path):
    return os.path.basename(path)[:-4]


def get_views_path(view_name):
    ui_folder = os.path.join(get_base_directory(), 'ui')
    views_folder = os.path.join(ui_folder, 'views')

    return os.path.join(views_folder, view_name + '.ui')


def curr_time():
    return time.strftime('%H:%M')


def get_unix_time():
    return int(time.time())


def join_path(a, b):
    return os.path.join(a, b)


def file_exists(file_path):
    return os.path.exists(file_path)


def copy(src, dest):
    if not os.path.exists(dest):
        os.makedirs(dest)
    src_files = os.listdir(src)
    for file_name in src_files:
        full_file_name = os.path.join(src, file_name)
        if os.path.isfile(full_file_name):
            shutil.copy(full_file_name, dest)
        else:
            copy(full_file_name, os.path.join(dest, file_name))


def remove(folder):
    if os.path.isdir(folder):
        shutil.rmtree(folder)


def convert_time(t):
    offset = time.timezone + time_offset() * 60
    sec = int(t) - offset
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    return '%02d:%02d' % (h, m)


@cached
def time_offset():
    hours = int(time.strftime('%H'))
    minutes = int(time.strftime('%M'))
    sec = int(time.time()) - time.timezone
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    result = hours * 60 + minutes - h * 60 - m
    return result

def unix_time_to_long_str(unix_time):
    date_time = datetime.datetime.utcfromtimestamp(unix_time)

    return date_time.strftime('%Y-%m-%d %H:%M:%S')


@cached
def is_64_bit():
    return sys.maxsize > 2 ** 32


def is_re_valid(regex):
    try:
        re.compile(regex)
    except re.error:
        return False
    else:
        return True


@cached
def get_platform():
    return platform.system()

def get_user_config_path():
    if get_platform() == 'Windows':
        return os.getenv('APPDATA') + '/Tox/'
    elif get_platform() == 'Darwin':
        return os.getenv('HOME') + '/Library/Application Support/Tox/'
    else:
        return os.getenv('HOME') + '/.config/tox/'
