# -*- mode: python; indent-tabs-mode: nil; py-indent-offset: 4; coding: utf-8 -*-
import json
import urllib.request
import utils.util as util
from PyQt5 import QtNetwork, QtCore
try:
    import requests
except ImportError:
    requests = None

global LOG
import logging
LOG = logging.getLogger('app.'+__name__)

class ToxDns:

    def __init__(self, settings, log=None):
        self._settings = settings
        self._log = log

    @staticmethod
    def _send_request(url, data):
        if requests:
            LOG.info('send_request loading with requests: ' + str(url))
            headers = dict()
            headers['Content-Type'] = 'application/json'
            req = requests.get(url, headers=headers)
            if req.status_code < 300:
                retval = req.content
            else:
                raise LookupError(str(req.status_code))
        else:
            req = urllib.request.Request(url)
            req.add_header('Content-Type', 'application/json')
            response = urllib.request.urlopen(req, bytes(json.dumps(data), 'utf-8'))
            retval = response.read()
        res = json.loads(str(retval, 'utf-8'))
        if not res['c']:
            return res['tox_id']
        else:
            raise LookupError()

    def lookup(self, email):
        """
        TOX DNS 4
        :param email: data like 'groupbot@toxme.io'
        :return: tox id on success else None
        """
        site = email.split('@')[1]
        data = {"action": 3, "name": "{}".format(email)}
        urls = ('https://{}/api'.format(site), 'http://{}/api'.format(site))
        if requests:
            for url in urls:
                LOG.info('TOX nodes loading with requests: ' + str(url))
                try:
                    headers = dict()
                    headers['Content-Type'] = 'application/json'
                    req = requests.get(url, headers=headers)
                    if req.status_code < 300:
                        result = req.content
                        return result
                except Exception as ex:
                    LOG.error('ERROR: TOX DNS loading error with requests: ' + str(ex))

        elif not self._settings['proxy_type']:  # no proxy
            for url in urls:
                try:
                    return self._send_request(url, data)
                except Exception as ex:
                    LOG.error('ERROR: TOX DNS ' + str(ex))
        else:  # proxy
            netman = QtNetwork.QNetworkAccessManager()
            proxy = QtNetwork.QNetworkProxy()
            if self._settings['proxy_type'] == 2:
                proxy.setType(QtNetwork.QNetworkProxy.Socks5Proxy)
            else:
                proxy.setType(QtNetwork.QNetworkProxy.HttpProxy)
            proxy.setHostName(self._settings['proxy_host'])
            proxy.setPort(self._settings['proxy_port'])
            netman.setProxy(proxy)
            for url in urls:
                try:
                    request = QtNetwork.QNetworkRequest()
                    request.setUrl(QtCore.QUrl(url))
                    request.setHeader(QtNetwork.QNetworkRequest.ContentTypeHeader, "application/json")
                    reply = netman.post(request, bytes(json.dumps(data), 'utf-8'))

                    while not reply.isFinished():
                        QtCore.QThread.msleep(1)
                        QtCore.QCoreApplication.processEvents()
                    data = bytes(reply.readAll().data())
                    result = json.loads(str(data, 'utf-8'))
                    if not result['c']:
                        return result['tox_id']
                except Exception as ex:
                    LOG.error('ERROR: TOX DNS ' + str(ex))

        return None  # error
