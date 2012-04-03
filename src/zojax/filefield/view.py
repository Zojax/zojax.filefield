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

from zojax.batching.batch import Batch
from zojax.statusmessage.interfaces import IStatusMessage

from interfaces import _, IPreviewsCatalog

from zojax.layoutform.field import Fields
from zojax.wizard.step import WizardStepForm

class PreviewsCatalogView(WizardStepForm):

    title = _(u'Previews Catalog')
    label = _(u'You can rebuild Previews')
    fields = Fields(IPreviewsCatalog)

    def update(self):
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

        results = context.records.values()

        self.batch = Batch(results, size=20, context=context, request=request)

    def getInfo(self, record):
        # NOTE: record.parent: mimeType, filename, modified, hash, size, _blob
        info = {'filename': record.parent.filename,
                'mimeType': record.parent.mimeType,
                'modified': record.parent.modified}

        return info
