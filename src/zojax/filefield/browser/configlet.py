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
from zope.proxy import removeAllProxies
from zope.component import getUtility, getUtilitiesFor
from zope.app.intid.interfaces import IIntIds
from zope import interface

from zojax.batching.batch import Batch
from zojax.statusmessage.interfaces import IStatusMessage
from zojax.content.type.interfaces import IContentType
from zojax.wizard.step import WizardStep
from zojax.catalog.interfaces import ICatalog

from ..interfaces import _, IPreviewsCatalog, IFileField, IImageField


class PreviewsCatalogView(WizardStep):

    title = _(u'Previews Catalog')
    label = _(u'You can rebuild Previews')

    def update(self):
        super(PreviewsCatalogView, self).update()

        request = self.request
        context = removeAllProxies(self.context)

        if 'form.button.rebuild' in request:
            for oid, record in context.records.items():
                if not record.parent.mimeType:
                    context.remove(oid)
                    continue

                # NOTE: generate new Preview
                record.parent.generatePreview()

            IStatusMessage(request).add(
                _('Previews catalog has been rebuilded.'))

        elif 'form.button.rebuild_selected' in request:
            for oid in request.get('form.checkbox.record_id', ()):
                try:
                    context.records[int(rid)].parent.generatePreview()
                except KeyError:
                    pass
            IStatusMessage(request).add(
                _('Selected reviews has been rebuilded.'))

        elif 'form.button.remove_selected' in request:
            for oid in request.get('form.checkbox.record_id', ()):
                del context.records[int(oid)]
            IStatusMessage(request).add(
                _('Selected reviews has been removed.'))

        results = context.records.items()

        self.batch = Batch(results, size=20, context=context, request=request)

    def getInfo(self, item):
        id, record = item
        # NOTE: record.parent: mimeType, filename, modified, hash, size, _blob
        return dict(filename=record.parent.filename,
                    mimeType=record.parent.mimeType,
                    modified=record.parent.modified,
                    recordId=id)

class PreviewsCatalogBuildView(WizardStep):

    title = _(u'Create Previews for All Files')
    label = _(u'Build previews')
    
    def __init__(self, *args, **kwargs):
        super(PreviewsCatalogBuildView, self).__init__(*args, **kwargs)
        self.f2c_mapping = self.getFieldNameToContentTypeMapping()
        self.catalog = getUtility(ICatalog)
        self.preview_catalog = getUtility(IPreviewsCatalog)
        self.int_ids = getUtility(IIntIds)

    def update(self):
        super(PreviewsCatalogBuildView, self).update()
        request = self.request
        context = removeAllProxies(self.context)
        
        filefield_objects = self.catalog\
            .searchResults(type={'any_of': self.f2c_mapping.keys()})
        
        if 'form.button.build' in request:
            for obj in filefield_objects:
                self.previewForObject(obj)
            
            IStatusMessage(request).add(
                _('Previews catalog has been builded.'))

        elif 'form.button.build_selected' in request:
            for id in request.get('form.checkbox.id', ()):
                obj = self.int_ids.queryObject(int(id))
                self.previewForObject(obj)

            IStatusMessage(request).add(
                _('Previews for selected files has been builded.'))

        results = [o for o in filefield_objects if self.previewsNotExists(o)]
        self.batch = Batch(results, size=20, context=context, request=request)

    def previewsNotExists(self, obj):
        file_fields = self.f2c_mapping[IContentType(obj).name]
        for f in file_fields:
            file = getattr(obj, f, None)
            if file and file.data:
                #previews can re-build here
                #if mode for preview catalog's mode switched in `check`
                #lets set allow_auto_generate=False flag
                if not self.preview_catalog.check(file,
                                                  allow_auto_generate=False):
                    return True
        return False

    def getInfo(self, obj):
        return dict(id=self.int_ids.getId(obj),
                    title=obj.title,
                    files=[getattr(obj, f)
                           for f in self.f2c_mapping[IContentType(obj).name]])

    def getFieldNameToContentTypeMapping(self):
        mapping = {}

        for n, u in getUtilitiesFor(IContentType):
            for f in u.schema.names():
                ifaces = list(interface.providedBy(u.schema[f]))
                if IFileField in ifaces or IImageField in ifaces :
                    if n not in mapping:
                        mapping[n]=[]
                    mapping[n].append(f)

        return mapping

    def previewForObject(self, obj):
        for f in self.f2c_mapping[IContentType(obj).name]:
            self.preview_catalog.add(getattr(obj, f, None))
