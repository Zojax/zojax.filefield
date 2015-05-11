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
from zope import component, interface
from zc.copy.interfaces import ICopyHook

from data import File, Image
from interfaces import IFile, IImage


@component.adapter(IFile)
@interface.implementer(ICopyHook)
def fileCopyFactory(original):
    def factory(location, register):
        file = File()
        file.filename = original.filename
        file.mimeType = original.mimeType
        file.disablePreview = original.disablePreview

        def afterCopy(translate):
            file.data = original.data

        register(afterCopy)
        return file
    return factory


@component.adapter(IImage)
@interface.implementer(ICopyHook)
def imageCopyFactory(original):
    def factory(location, register):
        image = Image()
        image.filename = original.filename
        image.mimeType = original.mimeType

        def afterCopy(translate):
            image.data = original.data

        register(afterCopy)
        return image
    return factory
