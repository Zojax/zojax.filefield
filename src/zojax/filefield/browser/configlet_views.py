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
            for rid, record in context.records.items():
                if not record.parent.mimeType:
                    context.remove(rid)
                    continue

                # NOTE: generate new Preview
                record.parent.generatePreview()

            IStatusMessage(request).add(
                _('Previews catalog has been rebuilded.'))

        elif 'form.button.rebuild_selected' in request:
            for rid in request.get('form.checkbox.record_id', ()):
                try:
                    context.records[rid].parent.generatePreview()
                except KeyError:
                    pass
            IStatusMessage(request).add(
                _('Selected reviews has been rebuilded.'))

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
        
        files = catalog.searchResults(type={'any_of': ['contenttype.file']})
        
        if 'form.button.build' in request:

            for r in files:
                preview_catalog.add(r.data)
            
            IStatusMessage(request).add(
                _('Previews catalog has been builded.'))

        elif 'form.button.build_selected' in request:
            for id in request.get('form.checkbox.id', ()):
                print id

        results = [f for f in files if preview_catalog.add(f.data)]#no, my own check here - previews can re-build here, if mode for catalog switched in `check` mode
        self.batch = Batch(results, size=20, context=context, request=request)
