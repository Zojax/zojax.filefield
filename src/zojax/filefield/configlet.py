##############################################################################
#
# Copyright (c) 2009 Zope Foundation and Contributors.
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
import BTrees, transaction, logging, time

from celery.result import AsyncResult

from datetime import datetime, timedelta
from persistent import Persistent
from persistent.interfaces import IPersistent
from rwproperty import setproperty, getproperty
from ZODB.blob import Blob
from ZODB.interfaces import BlobError

from zope import interface, event
from zope.app.component.hooks import getSite
from zope.component import getUtility
from zope.keyreference.interfaces import NotYet
from zope.keyreference.persistent import KeyReferenceToPersistent
from zope.traversing.browser import absoluteURL

from zojax.catalog.utils import getRequest
from zojax.converter import api
from zojax.converter.interfaces import ConverterException
from zojax.statusmessage.interfaces import IStatusMessage

from zojax.filefield import tasks
from interfaces import IPreviewsCatalog, IPreviewRecord, IFile

logger = logging.getLogger('zojax.filefield (configlet)')

try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5



class PreviewsCatalog(object):
    interface.implements(IPreviewsCatalog)

    family = BTrees.family32

    @property
    def records(self):
        data = self.data.get('records')
        if data is None:
            data = self.family.OO.BTree()
            self.data['records'] = data
        return data

    def add(self, object=None):

        if object is None or not IFile.providedBy(object):
            return

        oid = self._getOid(object)
        if oid is None:
            return

        preview = PreviewRecord()

        preview.parent = object
        preview.generatePreview()

        # NOTE: do not add if object.mimeType is empty
        if object.mimeType:
            self.records[oid] = preview

        #event.notify(PreviewRecordAddedEvent(object, preview))

    def remove(self, object=None):
        if object is None or not IFile.providedBy(object):
            return

        oid = self._getOid(object)
        if oid is None:
            return

        record = self.records.get(oid, None)
        if record:
            #event.notify(PreviewRecordRemovedEvent(object, record))
            del self.records[oid]

    def check(self, object=None, allow_auto_generate=True):

        if object is None or not IFile.providedBy(object):
            return

        oid = self._getOid(object)
        if oid is None:
            return

        if oid in self.records and self.records[oid].previewSize > 0:
            return True
        else:
            if allow_auto_generate and ('check' in self.generateMethod):
                self.add(object)
                # NOTE: there is no oid in self.records if file is missing
                if self.records.has_key(oid) and self.records[oid].previewSize > 0:
                    return True

            return False

    def getPreview(self, object=None):
        """ returns preview from records """
        if object is None or not IFile.providedBy(object):
            return

        oid = self._getOid(object)
        if oid is None:
            return

        if 'always' in self.generateMethod:
            self.add(object)

        if oid in self.records:
            # NOTE: records[oid]: parent, previewSize, _previewBlob, previewData
            return self.records[oid]

    def getPreviewSize(self, object=None):
        if object is None or not IFile.providedBy(object):
            return

        oid = self._getOid(object)
        if oid is None:
            return

        if oid in self.records:
            return self.records[oid].previewSize

    def getObject(self, id):
        return self.records[id]

    def _getOid(self, object):
        """ returns oid for persistent object """
        if not IPersistent.providedBy(object):
            return

        try:
            return hash(KeyReferenceToPersistent(object))
            #oid = hash(KeyReferenceToPersistent(object))

            ## negative hash means file was not uploaded
            #if oid <= 0:
            #    return

            #return oid
        except NotYet:
            return


class PreviewRecord(Persistent):
    interface.implements(IPreviewRecord)

    def __init__(self, parent=None):
        self.parent = parent
        self.previewSize = 0
        self._previewBlob = Blob()

    @getproperty
    def previewData(self):
        """ returns preview data """
        fp = self._previewBlob.open('r')
        data = fp.read()
        fp.close()
        return data

    @getproperty
    def previewSize(self):
        if 'previewSize' in self.__dict__:
            return self.__dict__['previewSize']
        else:
            reader = self.openPreview()
            try:
                reader.seek(0,2)
                size = int(reader.tell())
            finally:
                reader.close()
            self.__dict__['previewSize'] = size
            return size

    @setproperty
    def previewSize(self, value):
        self.__dict__['previewSize'] = value

    def openPreview(self, mode="r"):
        try:
            return self._previewBlob.open(mode)
        except AttributeError:
            self._previewBlob = Blob()
            return self._previewBlob.open(mode)

    def openPreviewDetached(self, n=0):
        try:
            return file(self._previewBlob.committed(), 'rb')
        except BlobError:
            if n < 2:
                transaction.commit()
                return self.openPreviewDetached(n+1)

    def generateFunction(self):
        size = 0
        fp = self.openPreview('w')
        ff = self.parent.open()
        try:
            fp.write(api.convert(ff, 'application/x-shockwave-flash', self.parent.mimeType, filename=self.parent.filename))
            size = int(fp.tell())
        except ConverterException, e:
            logger.warning('Error generating preview: %s', e)
        finally:
            ff.close()
            fp.close()
        return size

    def generatePreview(self):
        catalog = getUtility(IPreviewsCatalog)
        MAX_VALUE = catalog.maxValue * 1024 * 1024
        size = 0

        if self.parent.size < MAX_VALUE:

            if catalog.generateWith=='default':
                size = self.generateFunction()

            elif catalog.generateWith=='celery':
                msg = msgType = ''
                portalURL = absoluteURL(getSite(), getRequest())

                # NOTE: unique task id for current file
                oid = str(hash(KeyReferenceToPersistent(self.parent)))
                lock_id = "preview.generating-lock-%s" % md5(oid).hexdigest()

                try:
                    check = AsyncResult(lock_id).state
                except:
                    check = "None"
                print "before - %s" % check
                # STARTED - has been started
                # RETRY - is being retried
                # REVOKED - has been revoked
                # PENDING - is waiting for execution or unknown
                # SUCCESS - has been successfully executed
                # FAILURE - execution resulted in failure
                if check not in ["STARTED", "RETRY"]:

                    # NOTE: set expire
                    expires = datetime.now() + timedelta(minutes=30)
                    tasks.start_generating.apply_async(
                        args=[oid,portalURL],
                        expires=expires,
                        task_id=lock_id,
                        queue="images",
                        routing_key="media.image")

                    # NOTE: delay before set StatusMessage
                    time.sleep(3)

                    if AsyncResult(lock_id).state in ["STARTED", "RETRY"]:
                        msg = 'Preview will be generated in 1-5 minutes. Thanks for your patience.'
                        msgType = 'info'
                    elif AsyncResult(lock_id).state in ["SUCCESS",]:
                        msg = 'Preview was generated successfully'
                        msgType = 'info'
                    else:
                        msg = 'Preview generation is NOT running'
                        msgType = 'warning'
                    print "after - %s" % AsyncResult(lock_id).state

                #else:
                #    msg = 'Preview generation is already running'
                #    msgType = 'warning'

                if msg and msgType:
                    IStatusMessage(getRequest()).add(msg, type=msgType)

        self.previewSize = size
        return size


#@component.adapter(IPreviewDataAware, IIntIdRemovedEvent)
#def objectRemovedHandler(object, ev):
#    removeAllProxies(getUtility(IPreviewsCatalog)).remove(object)
