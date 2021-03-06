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
import logging
import md5
import os
import os.path
import rfc822
import struct
import transaction
# import pytz, random, subprocess, tempfile, stat, string, shlex, time

from datetime import datetime
from StringIO import StringIO
from persistent import Persistent
from rwproperty import setproperty, getproperty

from ZODB.blob import Blob
from ZODB.interfaces import BlobError
from ZODB.POSException import POSKeyError

import zope.datetime
from zope import interface, component
from zope.component import getMultiAdapter, getUtility
from zope.cachedescriptors.property import Lazy
from zope.lifecycleevent.interfaces import IObjectModifiedEvent
from zope.proxy import removeAllProxies
from zope.publisher.interfaces.http import IResult
from zope.publisher.interfaces import IPublishTraverse
from zope.size import byteDisplay
from zope.size.interfaces import ISized

from zojax.content.type.interfaces import IDraftedContent
from zojax.converter import api
# from zojax.converter.interfaces import ConverterException
from zojax.resourcepackage import library

from configlet import exclude_types
from interfaces import IFile, IImage, IFileData, IPreviewsCatalog
from interfaces import IFileDataClear, IFileDataNoValue
# OO_CONVERTER_EXECUTABLE, PREVIEWED_TYPES, OO_CONVERTED_TYPES


logger = logging.getLogger('zojax.filefield')


class File(Persistent):
    """ inspired by zope.file package implementation """
    interface.implements(IFile)

    filename = u'file'
    mimeType = u''
    modified = None
    disablePreview = False
    disablePrint = False

    def __init__(self):
        self._blob = Blob()
        self.data = u''

    @setproperty
    def data(self, data):
        self.size = len(data)
        self.hash = md5.md5(data).hexdigest()
        self.modified = zope.datetime.parseDatetimetz(str(datetime.now()))
        fp = self.open('w')
        fp.write(data)
        fp.close()

    @getproperty
    def data(self):
        try:
            fp = self._blob.open('r')
            data = fp.read()
            fp.close()
            return data
        except POSKeyError:
            print "Found damaged FileField: %s" % (self.filename)
            return False

    @getproperty
    def previewIsAvailable(self):
        """ check record in previewsCatalog,
            returns True or False
        """
        return getUtility(IPreviewsCatalog).check(self)

    @getproperty
    def size(self):
        if 'size' in self.__dict__:
            return self.__dict__['size']
        else:
            reader = self.open()
            if not reader:
                return 0
            try:
                reader.seek(0, 2)
                size = int(reader.tell())
            finally:
                reader.close()
            self.__dict__['size'] = size
            return size

    @setproperty
    def size(self, value):
        self.__dict__['size'] = value

    @Lazy
    def hash(self):
        fp = self._blob.open('r')
        data = fp.read()
        fp.close()
        self.hash = md5.md5(data).hexdigest()
        self._p_changed = True
        return self.hash

    def __len__(self):
        return self.size

    def __nonzero__(self):
        return self.size > 0

    def clear(self):
        self.filename = u''
        self.mimeType = u''
        self.data = u''
        self.disablePreview = u''
        self.disablePrint = u''

        # NOTE: remove record from previewsCatalog
        getUtility(IPreviewsCatalog).remove(self)

    def open(self, mode="r"):
        try:
            if 'w' in mode:
                if 'size' in self.__dict__:
                    del self.__dict__['size']
                self.modified = zope.datetime.parseDatetimetz(
                    str(datetime.now()))
            return self._blob.open(mode)
        except POSKeyError:
            print "Found damaged FileField: %s" % (self.filename)
            return False

    def openPreview(self, mode="r"):
        """ returns openPreview for preview
        """

        # NOTE: workaround for excluded types
        if self.mimeType in exclude_types:
            return self.open()

        preview = getUtility(IPreviewsCatalog).getPreview(self)
        return preview.openPreview(mode)

    def openDetached(self, n=0):
        try:
            return file(self._blob.committed(), 'rb')
        except BlobError:
            if n < 2:
                transaction.commit()
                return self.openDetached(n + 1)

    def openPreviewDetached(self):
        """ returns openPreviewDetached for preview
        """

        # NOTE: workaround for excluded types
        if self.mimeType in exclude_types:
            return self.openDetached()

        preview = getUtility(IPreviewsCatalog).getPreview(self)
        return preview.openPreviewDetached()

    def _show(self, request, filename=None, contentDisposition="inline"):
        response = request.response

        if not self.mimeType:
            response.setHeader('Content-Type', 'application/octet-stream')
        else:
            response.setHeader('Content-Type', self.mimeType)

        response.setHeader('Content-Length', self.size)

        modified = self.modified

        header = request.getHeader('If-Modified-Since', None)

        lmt = long(zope.datetime.time(modified.isoformat()))

        if header is not None:
            header = header.split(';')[0]
            try:
                mod_since = long(zope.datetime.time(header))
            except:
                mod_since = None
            if mod_since is not None:
                if lmt <= mod_since:
                    response.setStatus(304)
                    return ''
        response.setHeader('Last-Modified', zope.datetime.rfc1123_date(lmt))

        if filename is None:
            filename = self.filename

        response.setHeader(
            'Content-Disposition', '%s; filename="%s"' % (
                contentDisposition, filename.encode('utf-8')))

        if not self.size:
            response.setHeader('Content-Type', 'text/plain')
            return ''
        else:
            return self

    def show(self, *kv, **kw):
        res = self._show(*kv, **kw)
        if res != '':
            return DownloadResult(self)
        return res

    def showFly(self, *kv, **kw):
        res = self._show(*kv, **kw)
        if res != '':
            return DownloadResultFly(self)
        return res

    def _showPreview(self, request, filename=None, contentDisposition="inline"):

        # NOTE: previewSize for preview from previewsCatalog
        previewSize = getUtility(IPreviewsCatalog).getPreviewSize(self)

        response = request.response

        response.setHeader('Content-Type', 'application/pdf')

        response.setHeader('Content-Length', previewSize)

        modified = self.modified

        header = request.getHeader('If-Modified-Since', None)

        lmt = long(rfc822.mktime_tz(modified.utctimetuple() + (0,)))

        if header is not None:
            header = header.split(';')[0]
            try:
                mod_since = long(zope.datetime.time(header))
            except:
                mod_since = None
            if mod_since is not None:
                if lmt <= mod_since:
                    response.setStatus(304)
                    return ''
        response.setHeader('Last-Modified', zope.datetime.rfc1123_date(lmt))

        if filename is None:
            filename = self.filename

        response.setHeader(
            'Content-Disposition', '%s; filename="%s"' % (
                contentDisposition, filename.encode('utf-8')))

        if not previewSize:
            response.setHeader('Content-Type', 'text/plain')
            return ''
        else:
            return self

    def showPreview(self, *kv, **kw):
        res = self._showPreview(*kv, **kw)
        if res != '':
            return DownloadPreviewResult(self)
        return res

    def showPreviewFly(self, *kv, **kw):
        res = self._showPreview(*kv, **kw)
        if res != '':
            return DownloadPreviewResultFly(self)
        return res

    def generatePreview(self):
        """ add record to previewsCatalog, generate preview
        """
        getUtility(IPreviewsCatalog).add(self)

    def __deepcopy__(self, memo):
        new = File()
        new.data = self.data
        new.filename = self.filename
        new.mimeType = self.mimeType
        new.disablePreview = self.disablePreview
        new.disablePrint = self.disablePrint
        new.generatePreview()
        return new


class Image(File):
    interface.implements(IImage)

    width = -1
    height = -1

    @setproperty
    def data(self, data):
        self.size = len(data)
        self.modified = zope.datetime.parseDatetimetz(str(datetime.now()))
        self.width, self.height = getImageSize(data)
        fp = self.open('w')
        fp.write(data)
        fp.close()

    @getproperty
    def data(self):
        try:
            fp = self._blob.open('r')
            data = fp.read()
            fp.close()
            return data
        except POSKeyError:
            print "Found damaged Image %s" % (self.filename)
            return False

    def scale(self, width, height, quality=88):
        self.data = api.convert(
            self.data, self.mimeType, self.mimeType,
            width=width, height=height, quality=quality)

    def updateDimension(self):
        reader = self.open()
        self.width, self.height = getImageSize(reader)
        reader.close()


class FileSized(object):
    component.adapts(IFile)
    interface.implements(ISized)

    def __init__(self, context):
        self.context = context

        self.size = self.context.size

    def sizeForSorting(self):
        return "byte", self.size

    def sizeForDisplay(self):
        return byteDisplay(self.size)


class FileDataClear(object):
    interface.implements(IFileDataClear)


fileDataClear = FileDataClear()


class FileDataNoValue(object):
    interface.implements(IFileDataNoValue)


fileDataNoValue = FileDataNoValue()


class FileData(object):
    """ widget data """
    interface.implements(IFileData)

    def __init__(self, file=u'', filename=None, mimeType=None, disablePreview=None, disablePrint=None):
        if file is None:
            file = u''

        if isinstance(file, basestring):
            file = StringIO(file)
        elif not hasattr(file, 'seek'):
            raise ValueError("File object is required.")

        self.file = file

        if filename is None:
            filename = os.path.split(getattr(file, 'filename', u''))[-1]

        self.filename = filename

        file.seek(0, 2)
        self.size = int(file.tell())

        if mimeType is None:
            mimeType = api.guessMimetype(file, self.filename)[0]

        self.mimeType = mimeType

        if disablePreview is None:
            disablePreview = False

        self.disablePreview = disablePreview

        if disablePrint is None:
            disablePrint = False

        self.disablePrint = disablePrint

    @property
    def data(self):
        self.file.seek(0)
        return self.file.read()

    def __len__(self):
        return self.size


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


class DownloadResult(object):
    interface.implements(IResult)

    def __init__(self, context):
        self._iter = bodyIterator(context.openDetached())

    def __iter__(self):
        return self._iter


class DownloadResultFly(DownloadResult):

    def __init__(self, context):
        self._iter = bodyIterator(context.open())


class DownloadPreviewResult(object):
    interface.implements(IResult)

    def __init__(self, context):
        self._iter = bodyIterator(context.openPreviewDetached())

    def __iter__(self):
        return self._iter


class DownloadPreviewResultFly(DownloadPreviewResult):

    def __init__(self, context):
        self._iter = bodyIterator(context.openPreview())


CHUNK_SIZE = 64 * 1024


def bodyIterator(f):
    while True:
        chunk = f.read(CHUNK_SIZE)
        if not chunk:
            f.close()
            break
        yield chunk
    f.close()
    raise StopIteration()


def getImageSize(fp):
    if isinstance(fp, basestring):
        fp = StringIO(fp)

    fp.seek(0)
    data = fp.read(24)
    size = len(data)
    width = -1
    height = -1

    # gif
    if (size >= 10) and data[:6] in ('GIF87a', 'GIF89a'):
        # Check to see if content_type is correct
        w, h = struct.unpack("<HH", data[6:10])
        width = int(w)
        height = int(h)
        return width, height

    # png
    # See PNG 2. Edition spec (http://www.w3.org/TR/PNG/)
    # Bytes 0-7 are below, 4-byte chunk length, then 'IHDR'
    # and finally the 4-byte width, height
    if ((size >= 24) and data.startswith('\211PNG\r\n\032\n')
       and (data[12:16] == 'IHDR')):
        w, h = struct.unpack(">LL", data[16:24])
        width = int(w)
        height = int(h)
        return width, height
    # Maybe this is for an older PNG version.
    elif (size >= 16) and data.startswith('\211PNG\r\n\032\n'):
        w, h = struct.unpack(">LL", data[8:16])
        width = int(w)
        height = int(h)
        return width, height

    # jpeg
    fp.seek(2)
    b = fp.read(1)
    try:
        w = -1
        h = -1
        while (b and ord(b) != 0xDA):
            while (ord(b) != 0xFF):
                b = fp.read(1)
            while (ord(b) == 0xFF):
                b = fp.read(1)
            if (ord(b) >= 0xC0 and ord(b) <= 0xC3):
                fp.read(3)
                h, w = struct.unpack(">HH", fp.read(4))
                break
            else:
                fp.read(int(struct.unpack(">H", fp.read(2))[0]) - 2)
            b = fp.read(1)
        width = int(w)
        height = int(h)
    except struct.error:
        pass
    except ValueError:
        pass
    except TypeError:
        pass
    return width, height


@component.adapter(IFile, IObjectModifiedEvent)
def fileModifiedHandler(object, event):
    """ generate preview for File
    """
    if not IDraftedContent.providedBy(object):
        object = removeAllProxies(object)
        object.generatePreview()
