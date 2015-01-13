#!/usr/bin/env python
# pylint: disable=missing-docstring

import hashlib
import logging

import record
from http import HttpException

logger = logging.getLogger('api') # pylint: disable=invalid-name

class Api(object):
    def __init__(self, node):
        self.node = node

    def get(self, tid, key):
        logger.info('Got a GET: tid = %s, key = %s', tid.encode('hex'), key)
        if tid not in self.node.stores:
            raise HttpException(404, "Not Found")
        the_store = self.node.stores[tid]
        khash = hashlib.sha256(key).digest()
        (ctype, data) = the_store.get_data(record.RT_SIGNED, khash)
        if ctype == 'tombstone' and data == 'tombstone':
            raise HttpException(404, "Not Found")
        if ctype == None:
            raise HttpException(404, "Not Found")
        return (ctype, data)

    def put(self, tid, key, ctype, body):
        logger.info('Got a PUT: tid = %s, key = %s', tid.encode('hex'), key)
        if tid not in self.node.stores:
            raise HttpException(404, "Not Found")
        the_store = self.node.stores[tid]
        signer = the_store.signer
        if signer == None:
            raise HttpException(403, "Forbidden")
        (hid, summary, data) = record.make_signed_record(signer, key, ctype, body)
        if not the_store.on_record(record.RT_SIGNED, hid, summary, data):
            raise HttpException(500, "Unable to write record")

    def delete(self, tid, key):
        logger.info('Got a DELETE: tid = %s, key = %s', tid.encode('hex'), key)
        self.put(tid, key, 'tombstone', 'tombstone')

    def __require(self, obj, field):
        _ = self
        if field not in obj:
            raise HttpException(400, "Action requires field: " + field)
        return obj[field]

    def __require_int(self, obj, field):
        val = self.__require(obj, field)
        if type(val) is not int:
            raise HttpException(400, "Field " + field + " not an integer")
        return val

    def __require_str(self, obj, field):
        val = self.__require(obj, field)
        if type(val) is not str:
            raise HttpException(400, "Field " + field + " not a string")
        return val

    def post(self, tid, action, obj):
        logger.info('Got a POST: action=%s, obj=%s', action, obj)
        if type(obj) is not dict:
            raise HttpException(400, "API request requires a json object")
        if hasattr(self, 'gact_' + action):
            if tid is not None:
                raise HttpException(400, "This action is global, no tid allowed")
            return getattr(self, 'gact_' + action)(obj)
        if hasattr(self, 'tact_' + action):
            if tid is None:
                raise HttpException(400, "This action is local, tid required")
            return getattr(self, 'tact_' + action)(tid, obj)
        raise HttpException(400, "Unknown action")

    def gact_create_app(self, obj):
        max_size = self.__require_int(obj, 'max_size')
        if max_size < 0 or max_size > 1*1024*1024*1024:
            raise HttpException(400, "max_size out of range")
        tid = self.node.create_app(max_size)
        return {'success' : True, 'tid' : tid.encode('hex')}

    def tact_join_app(self, tid, obj):
        max_size = self.__require_int(obj, 'max_size')
        if max_size < 0 or max_size > 1*1024*1024*1024:
            raise HttpException(400, "max_size out of range")
        self.node.join_app(tid, max_size)
        return {'success' : True}

    def tact_add_peer(self, tid, obj):
        addr = self.__require_str(obj, 'addr')
        port = self.__require_int(obj, 'port')
        self.node.on_peer(tid, (addr, port))
        return {'success' : True}

    def tact_add_record(self, tid, obj):
        if tid not in self.node.stores:
            return None
        return {'success' : True}

