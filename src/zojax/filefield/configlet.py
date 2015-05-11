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
import BTrees
import logging
import sys
import transaction

from ZODB.blob import Blob
from ZODB.interfaces import BlobError
from persistent import Persistent
from persistent.interfaces import IPersistent
from rwproperty import setproperty, getproperty

from zope import interface  # , event
from zope.component import getUtility
from zope.keyreference.interfaces import NotYet
from zope.keyreference.persistent import KeyReferenceToPersistent

from zojax.converter import api
from zojax.converter.interfaces import ConverterException

from interfaces import IPreviewsCatalog, IPreviewRecord, IFile

logger = logging.getLogger('zojax.filefield (configlet)')


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

        # event.notify(PreviewRecordAddedEvent(object, preview))

    def remove(self, object=None):
        if object is None or not IFile.providedBy(object):
            return

        oid = self._getOid(object)
        if oid is None:
            return

        record = self.records.get(oid, None)
        if record:
            # event.notify(PreviewRecordRemovedEvent(object, record))
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
                if self.records.has_key(oid) and \
                   self.records[oid].previewSize > 0:
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
            # NOTE: records[oid]:parent, previewSize, _previewBlob, previewData
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
                return self.openPreviewDetached(n + 1)

    def generatePreview(self):
        MAX_VALUE = getUtility(IPreviewsCatalog).maxValue * 1024 * 1024
        size = 0

        if self.parent.size < MAX_VALUE and not self.parent.disablePreview:
            logger.info(
                "Start generating preview for: %s" % self.parent.filename)
            fp = self.openPreview('w')
            ff = self.parent.open()
            try:
                fp.write(api.convert(
                    ff, 'application/x-shockwave-flash', self.parent.mimeType,
                    filename=self.parent.filename))
                size = int(fp.tell())
            except (ConverterException, OSError), e:
                logger.warning(
                    'Error generating preview for %s: %s',
                    self.parent.filename, e)
            except:
                logger.warning(
                    '2 - Error generating preview for %s: %s',
                    self.parent.filename, sys.exc_info()[0])
            finally:
                ff.close()
                fp.close()
            logger.info(
                "Finish generating preview for: %s" % self.parent.filename)

        self.previewSize = size
        return size


# @component.adapter(IPreviewDataAware, IIntIdRemovedEvent)
# def objectRemovedHandler(object, ev):
#     removeAllProxies(getUtility(IPreviewsCatalog)).remove(object)
