# -*- mode: python; indent-tabs-mode: nil; py-indent-offset: 4; coding: utf-8 -*-
import random
import urllib.request
from utils.util import *
from PyQt5 import QtNetwork
from PyQt5 import QtCore
try:
    import certifi
    from io import BytesIO
except ImportError:
    certifi = None

from user_data.settings import get_user_config_path
from wrapper_tests.support_testing import _get_nodes_path
from wrapper_tests.support_http import download_url

global LOG
import logging
LOG = logging.getLogger('app.'+'bootstrap')

def download_nodes_list(settings, oArgs):
    if not settings['download_nodes_list']:
        return ''
    url = settings['download_nodes_url']
    path = _get_nodes_path(oArgs=oArgs)
    # dont download blindly so we can edit the file and not block on startup
    if os.path.isfile(path):
        with open(path, 'rt') as fl:
            result = fl.read()
            return result
    LOG.debug("downloading list of nodes")
    result = download_url(url, settings._app._settings)
    if not result:
        LOG.warn("failed downloading list of nodes")
        return ''
    LOG.info("downloaded list of nodes")
    _save_nodes(result, settings._app)
    return result

def _save_nodes(nodes, app):
    if not nodes:
        return
    with open(_get_nodes_path(oArgs=app._args), 'wb') as fl:
        LOG.info("Saving nodes to " +_get_nodes_path())
        fl.write(nodes)
