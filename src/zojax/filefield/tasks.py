##############################################################################
#
# Copyright (c) 2008 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

"""
$Id$
"""

import time
import urllib2
import httplib

from celery.task import task
from datetime import datetime
from urlparse import urlparse

try:
    import simplejson as json
except ImportError:
    import json

import logging
logger = logging.getLogger('zojax.filefield.tasks')


@task()  # (track_started=True)
def start_generating(oid, url):

    startTimer = time.time()
    start_generating.update_state(
        state='STARTED',
        meta={'startat': startTimer})

    # NOTE: delay before generation start
    # to avoid KeyError exception on creating object
    time.sleep(15)

    params = dict(oid=oid)
    res = jsonRpcRequest(
        method='generatePreview',
        params=json.dumps(params),
        jsonRPCUrl=url)

    if res['err']:
        msg = "Generation NOT finished, error: %s" % res['err']
        message(text=msg, type='critical')

    return res['msg']


def message(text=None, type='info'):
    if not text:
        return

    if type == 'info':
        logging.info(text)
    if type == 'debug':
        logging.debug(text)
    if type == 'warn':
        logging.warn(text)
    if type == 'error':
        logging.error(text)
    if type == 'critical':
        logging.critical(text)

    print "%s %s: %s" % (datetime.now(), type, text)


def prepareUrl(url=None):
    if not url:
        return

    jsoRPC = "++skin++JSONRPC.filefield"

    # NOTE: workaround for localhost
    if ":8080" in url:
        o = urlparse(url)
        url = "%s://%s/%s%s" % (o.scheme, o.netloc, jsoRPC, o.path)
    else:
        url = "%s/%s" % (url, jsoRPC)

    return url


def jsonRpcRequest(method=None, params=None, jsonRPCUrl=None):
    if not method or not jsonRPCUrl:
        return

    if params:
        reqParams = "{'method':'%s', 'params': %s}" % (method, params)
    else:
        reqParams = "{'method':'%s', 'params': {}}" % method

    try:
        req = urllib2.Request(
            prepareUrl(jsonRPCUrl),
            headers={"Content-Type": "application/json", },
            data=reqParams
        )

        json = eval(urllib2.urlopen(req).read())

        # NOTE: standart JSON-RPC error
        # {"jsonrpc":"2.0","id":"jsonrpc","error":{"message": \
        # "Invalid JSON-RPC","code":-32603,"data":"error here"}}
        if "error" in json:
            msg = "%s - %s (code: %s)" % (
                json["error"]["message"],
                json["error"]["data"],
                json["error"]["code"])
            msg = "%s \n %s" % (msg, reqParams)
            message(text=msg, type='critical')
            return

        # NOTE: JSON-RPC result
        # json = {'msg': 'result here', 'err': "error here"}
        if "result" in json:
            return json["result"]

        message(
            text="jsonRpcRequest - no error and no result",
            type='critical')
        return

    except urllib2.URLError, e:
        message(text="%s | %s" % (e, reqParams), type='critical')
        return
    except httplib.BadStatusLine, e:
        message(text="%s | %s" % (e, reqParams), type='critical')
        return
    except:
        message(
            text="%s | %s" % ('Unexpected error in jsonRpcRequest', reqParams),
            type='critical')
        return
