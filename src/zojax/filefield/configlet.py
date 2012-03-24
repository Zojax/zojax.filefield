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
from persistent import Persistent

from zope import interface, event
from persistent.interfaces import IPersistent
from zope.keyreference.persistent import KeyReferenceToPersistent

from interfaces import IPreviewsCatalog, IPreviewData, IFile


class PreviewsCatalog(object):
    interface.implements(IPreviewsCatalog)

    family = BTrees.family32

    @property
    def records(self):
        data = self.data.get('records')
        if data is None:
            data = self.family.IO.BTree()
            self.data['records'] = data
        return data

    def add(self, object=None):
        if object is None or not IFile.providedBy(object):
            return

        oid = self._getOid(object)
        if oid is None:
            return

        preview = PreviewData()

        preview.id = oid
        preview.parent = object

        # NOTE: do not add if object.mimeType is empty
        if object.mimeType:
            self.records[preview.id] = preview

        #event.notify(PreviewRecordAddedEvent(object, preview))

    def remove(self, object=None):
        if object is None or not IFile.providedBy(object):
            return

        oid = self._getOid(object)
        if oid is None:
            return

        record = self.records[oid]
        #event.notify(PreviewRecordRemovedEvent(object, record))

        del record

    def check(self, object=None):
        if object is None or not IFile.providedBy(object):
            return

        oid = self._getOid(object)
        if oid is None:
            return

        if oid not in self.records:
            preview = PreviewData()

            preview.id = oid
            preview.parent = object

            # NOTE: do not add if object.mimeType is empty
            if object.mimeType:
                self.records[preview.id] = preview

            #event.notify(PreviewRecordAddedEvent(object, preview))

    def getObject(self, id):
        return self.records[id]

    def _getOid(self, object):
        """ returns oid for persistent object """
        if not IPersistent.providedBy(object):
            return

        try:
            return hash(KeyReferenceToPersistent(object))
        except NotYet:
            return


class PreviewData(Persistent):
    interface.implements(IPreviewData)

    id = None
    parent = None

    #def __init__(self, id=None, parent=None, **kw):

        #for attr, value in kw.items():
        #    setattr(self, attr, value)


#@component.adapter(IPreviewDataAware, IIntIdRemovedEvent)
#def objectRemovedHandler(object, ev):
#    removeAllProxies(getUtility(IPreviewsCatalog)).remove(object)
