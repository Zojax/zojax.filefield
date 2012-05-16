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

from zope import interface, component
from zope.component import getMultiAdapter
from zope.publisher.interfaces import IPublishTraverse

from zojax.resourcepackage import library

from ..interfaces import IFile


class FileView(object):

    def __call__(self):
        return self.context.show(self.request)


class FilePreView(object):

    def __call__(self):
        return self.context.showPreview(self.request)


class FilePreViewPage(object):

    def update(self):
        library.include('jquery-plugins')


class FileTraverser(object):
    interface.implements(IPublishTraverse)
    component.adapts(IFile, interface.Interface)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        if name != 'index.html':
            request.response.setHeader(
                'Cache-Control', 'public, max-age=31536000')
            request.response.setHeader(
                'Expires', u"Fri, 01 Jan 2100 01:01:01 GMT")
            request.response.setHeader(
                'Last-Modified', u"Sat, 01 Jan 2000 01:01:01 GMT")

        return getMultiAdapter((self.context, request), name='index.html')
