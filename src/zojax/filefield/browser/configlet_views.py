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
from zope.component import getUtility
from zope.app.intid.interfaces import IIntIds

from zojax.batching.batch import Batch

from zojax.statusmessage.interfaces import IStatusMessage

from ..interfaces import _, IPreviewsCatalog

from zojax.wizard.step import WizardStep

from zojax.catalog.interfaces import ICatalog

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

    def update(self):
        super(PreviewsCatalogBuildView, self).update()
        request = self.request
        context = removeAllProxies(self.context)
        
        catalog = getUtility(ICatalog)
        preview_catalog = getUtility(IPreviewsCatalog)
        int_ids = getUtility(IIntIds)
        
        files = catalog.searchResults(type={'any_of': ['contenttype.file']})
        
        if 'form.button.build' in request:

            for r in files:
                preview_catalog.add(r.data)
            
            IStatusMessage(request).add(
                _('Previews catalog has been builded.'))

        elif 'form.button.build_selected' in request:
            for id in request.get('form.checkbox.id', ()):
                preview_catalog.add(int_ids.queryObject(int(id)).data)

            IStatusMessage(request).add(
                _('Previews for selected files has been builded.'))

        #previews can re-build here
        #if mode for preview catalog's mode switched in `check`
        #lets set allow_auto_generate=False flag
        results = [f for f in files
                   if not preview_catalog.check(f.data,
                                                allow_auto_generate=False)]
        self.batch = Batch(results, size=20, context=context, request=request)

    def getInfo(self, file):
        int_ids = getUtility(IIntIds)
        return dict(id=int_ids.getId(file),
                    name=file.data.filename)
