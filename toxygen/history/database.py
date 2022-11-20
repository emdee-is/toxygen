# -*- mode: python; indent-tabs-mode: nil; py-indent-offset: 4; coding: utf-8 -*-
from sqlite3 import connect
import os.path
import utils.util as util

global LOG
import logging
LOG = logging.getLogger('app.db')

TIMEOUT = 11
SAVE_MESSAGES = 500
MESSAGE_AUTHOR = {
    'ME': 0,
    'FRIEND': 1,
    'NOT_SENT': 2,
    'GC_PEER': 3
}
CONTACT_TYPE = {
    'FRIEND': 0,
    'GC_PEER': 1,
    'GC_PEER_PRIVATE': 2
}


class Database:

    def __init__(self, path, toxes):
        self._path = path
        self._toxes = toxes
        self._name = os.path.basename(path)

    def open(self):
        path = self._path
        toxes = self._toxes
        if not os.path.exists(path):
            LOG.warn('Db not found: ' +path)
            return
        try:
            with open(path, 'rb') as fin:
                data = fin.read()
        except Exception as ex:
            LOG.error('Db reading error: ' +path +' ' +str(ex))
            raise
        try:
            if toxes.is_data_encrypted(data):
                data = toxes.pass_decrypt(data)
                with open(path, 'wb') as fout:
                    fout.write(data)
        except Exception as ex:
            LOG.error('Db writing error: ' +path +' ' + str(ex))
            os.remove(path)
        LOG.info('Db opened: ' +path)

    # -----------------------------------------------------------------------------------------------------------------
    # Public methods
    # -----------------------------------------------------------------------------------------------------------------

    def save(self):
        if self._toxes.has_password():
            with open(self._path, 'rb') as fin:
                data = fin.read()
            data = self._toxes.pass_encrypt(bytes(data))
            with open(self._path, 'wb') as fout:
                fout.write(data)

    def export(self, directory):
        new_path = util.join_path(directory, self._name)
        with open(self._path, 'rb') as fin:
            data = fin.read()
        if self._toxes.has_password():
            data = self._toxes.pass_encrypt(data)
        with open(new_path, 'wb') as fout:
            fout.write(data)
        LOG.info('Db exported: ' +new_path)

    def add_friend_to_db(self, tox_id):
        db = self._connect()
        try:
            cursor = db.cursor()
            cursor.execute('CREATE TABLE IF NOT EXISTS id' + tox_id + '('
                           '    id INTEGER PRIMARY KEY,'
                           '    author_name TEXT,'
                           '    message TEXT,'
                           '    author_type INTEGER,'
                           '    unix_time REAL,'
                           '    message_type INTEGER'
                           ')')
            db.commit()
            return True
        except Exception as e:
            LOG.error("dd_friend_to_db " +self._name +' Database exception! ' +str(e))
            db.rollback()
            return False
        finally:
            db.close()
            LOG.debug(f"add_friend_to_db {tox_id}")

    def delete_friend_from_db(self, tox_id):
        db = self._connect()
        try:
            cursor = db.cursor()
            cursor.execute('DROP TABLE id' + tox_id + ';')
            db.commit()
            return True
        except Exception as e:
            LOG.error("delete_friend_from_db " +self._name +' Database exception! ' +str(e))
            db.rollback()
            return False
        finally:
            db.close()
            LOG.debug(f"delete_friend_from_db {tox_id}")

    def save_messages_to_db(self, tox_id, messages_iter):
        db = self._connect()
        try:
            cursor = db.cursor()
            cursor.executemany('INSERT INTO id' + tox_id +
                               '(message, author_name, author_type, unix_time, message_type) ' +
                               'VALUES (?, ?, ?, ?, ?);', messages_iter)
            db.commit()
            return True
        except Exception as e:
            LOG.error("" +self._name +' Database exception! ' +str(e))
            db.rollback()
            return False
        finally:
            db.close()
            LOG.debug(f"save_messages_to_db {tox_id}")

    def update_messages(self, tox_id, message_id):
        db = self._connect()
        try:
            cursor = db.cursor()
            cursor.execute('UPDATE id' + tox_id + ' SET author = 0 '
                           'WHERE id = ' + str(message_id) + ' AND author = 2;')
            db.commit()
            return True
        except Exception as e:
            LOG.error("" +self._name +' Database exception! ' +str(e))
            db.rollback()
            return False
        finally:
            db.close()
            LOG.debug(f"update_messages {tox_id}")

    def delete_message(self, tox_id, unique_id):
        db = self._connect()
        try:
            cursor = db.cursor()
            cursor.execute('DELETE FROM id' + tox_id + ' WHERE id = ' + str(unique_id) + ';')
            db.commit()
            return True
        except Exception as e:
            LOG.error("" +self._name +' Database exception! ' +str(e))
            db.rollback()
            return False
        finally:
            db.close()
            LOG.debug(f"delete_message {tox_id}")

    def delete_messages(self, tox_id):
        db = self._connect()
        try:
            cursor = db.cursor()
            cursor.execute('DELETE FROM id' + tox_id + ';')
            db.commit()
            return True
        except Exception as e:
            LOG.error("" +self._name +' Database exception! ' +str(e))
            db.rollback()
            return False
        finally:
            db.close()
            LOG.debug(f"delete_messages {tox_id}")

    def messages_getter(self, tox_id):
        self.add_friend_to_db(tox_id)

        return Database.MessageGetter(self._path, tox_id)

    # -----------------------------------------------------------------------------------------------------------------
    # Messages loading
    # -----------------------------------------------------------------------------------------------------------------

    class MessageGetter:

        def __init__(self, path, tox_id):
            self._count = 0
            self._path = path
            self._tox_id = tox_id
            self._db = self._cursor = None

        def get_one(self):
            return self.get(1)

        def get_all(self):
            self._connect()
            data = self._cursor.fetchall()
            self._disconnect()
            self._count = len(data)
            return data

        def get(self, count):
            self._connect()
            self.skip()
            data = self._cursor.fetchmany(count)
            self._disconnect()
            self._count += len(data)
            return data

        def skip(self):
            if self._count:
                self._cursor.fetchmany(self._count)

        def delete_one(self):
            if self._count:
                self._count -= 1

        def _connect(self):
            self._db = connect(self._path, timeout=TIMEOUT)
            self._cursor = self._db.cursor()
            self._cursor.execute('SELECT message, author_type, author_name, unix_time, message_type, id FROM id' +
                                 self._tox_id + ' ORDER BY unix_time DESC;')

        def _disconnect(self):
            self._db.close()

    # -----------------------------------------------------------------------------------------------------------------
    # Private methods
    # -----------------------------------------------------------------------------------------------------------------

    def _connect(self):
        return connect(self._path, timeout=TIMEOUT)
