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
from zojax.converter.interfaces import ConverterException
"""

$Id$
"""
import pytz, os.path, time, os, stat, struct, rfc822, md5, random, shlex, string, \
        subprocess, tempfile, logging

import transaction
from ZODB.blob import Blob
from datetime import datetime
from StringIO import StringIO
from persistent import Persistent
from rwproperty import setproperty, getproperty

import zope.datetime
from zope import interface, component
from zope.component import getMultiAdapter
from zope.cachedescriptors.property import Lazy
from zope.publisher.interfaces.http import IResult
from zope.publisher.interfaces import IPublishTraverse

from zojax.converter import api
from zojax.resourcepackage import library

from interfaces import IFile, IImage, IFileData
from interfaces import IFileDataClear, IFileDataNoValue, OO_CONVERTER_EXECUTABLE, \
OO_CONVERTED_TYPES, PREVIEWED_TYPES


logger = logging.getLogger('zojax.filefield')


class File(Persistent):
    """ inspired by zope.file package implementation """
    interface.implements(IFile)

    filename = u'file'
    mimeType = u''
    modified = None

    def __init__(self):
        self._blob = Blob()
        self._previewBlob = Blob()
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
        fp = self._blob.open('r')
        data = fp.read()
        fp.close()
        return data

    @getproperty
    def previewData(self):
        fp = self._previewBlob.open('r')
        data = fp.read()
        fp.close()
        return data

    @getproperty
    def previewIsAvailable(self):
        try:
            self.generatePreview()
            return bool(self.previewSize())
        except ConverterException:
            return False

    @getproperty
    def size(self):
        if 'size' in self.__dict__:
            return self.__dict__['size']
        else:
            reader = self.open()
            try:
                reader.seek(0,2)
                size = int(reader.tell())
            finally:
                reader.close()
            self.__dict__['size'] = size
            return size

    @setproperty
    def size(self, value):
        self.__dict__['size'] = value

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
        self.fielname = u''
        self.mimeType = u''
        self.data = u''

    def open(self, mode="r"):
        if 'w' in mode:
            if 'size' in self.__dict__:
                del self.__dict__['size']
            if 'previewSize' in self.__dict__:
                del self.__dict__['previewSize']

        return self._blob.open(mode)

    def openPreview(self, mode="r"):
        if 'w' in mode and 'previewSize' in self.__dict__:
            del self.__dict__['previewSize']
        try:
            return self._previewBlob.open(mode)
        except AttributeError:
            self._previewBlob = Blob()
            return self._previewBlob.open(mode)

    def openDetached(self):
        return file(self._blob.committed(), 'rb')

    def openPreviewDetached(self):
        return file(self._previewBlob.committed(), 'rb')

    def show(self, request, filename=None, contentDisposition="inline"):
        response = request.response

        if not self.mimeType:
            response.setHeader('Content-Type', 'application/octet-stream')
        else:
            response.setHeader('Content-Type', self.mimeType)

        response.setHeader('Content-Length', self.size)

        modified = self.modified

        header = request.getHeader('If-Modified-Since', None)

        lmt = long(rfc822.mktime_tz(modified.utctimetuple() + (0,)))

        if header is not None:
            header = header.split(';')[0]
            try:    mod_since=long(zope.datetime.time(header))
            except: mod_since=None
            if mod_since is not None:
                if lmt <= mod_since:
                    response.setStatus(304)
                    return ''
        response.setHeader('Last-Modified', zope.datetime.rfc1123_date(lmt))

        if filename is None:
            filename = self.filename

        response.setHeader(
            'Content-Disposition','%s; filename="%s"'%(
                contentDisposition, filename.encode('utf-8')))

        if not self.size:
            response.setHeader('Content-Type', 'text/plain')
            return ''
        else:
            return DownloadResult(self)

    def showPreview(self, request, filename=None, contentDisposition="inline"):
        response = request.response

        if self.size and not self.previewSize:
            self.generatePreview()
            transaction.commit()

        response.setHeader('Content-Type', 'application/x-shockwave-flash')

        response.setHeader('Content-Length', self.previewSize)

        modified = self.modified

        header = request.getHeader('If-Modified-Since', None)

        lmt = long(rfc822.mktime_tz(modified.utctimetuple() + (0,)))

        if header is not None:
            header = header.split(';')[0]
            try:    mod_since=long(zope.datetime.time(header))
            except: mod_since=None
            if mod_since is not None:
                if lmt <= mod_since:
                    response.setStatus(304)
                    return ''
        response.setHeader('Last-Modified', zope.datetime.rfc1123_date(lmt))

        if filename is None:
            filename = self.filename

        response.setHeader(
            'Content-Disposition','%s; filename="%s"'%(
                contentDisposition, filename.encode('utf-8')))

        if not self.previewSize:
            response.setHeader('Content-Type', 'text/plain')
            return ''
        else:
            return DownloadPreviewResult(self)

    def generatePreview(self):
        fp = self.openPreview('w')
        ff = self.open()
        try:
            fp.write(api.convert(ff, 'application/x-shockwave-flash', self.mimeType))
        except ConverterException, e:
            logger.warning('Error generating preview: %s', e)
        finally:
            ff.close()
            fp.close()

    def __deepcopy__(self, memo):
        new = File()
        new.data = self.data
        new.filename = self.filename
        new.mimeType = self.mimeType
        new.generatePreview()
        return new


class Image(File):
    interface.implements(IImage)

    width = -1
    height = -1

    @setproperty
    def data(self, data):
        self.size = len(data)
        self.modified = datetime.now(pytz.utc)
        self.width, self.height = getImageSize(data)
        fp = self.open('w')
        fp.write(data)
        fp.close()

    @getproperty
    def data(self):
        fp = self._blob.open('r')
        data = fp.read()
        fp.close()
        return data

    def scale(self, width, height, quality=88):
        self.data = api.convert(
            self.data, self.mimeType, self.mimeType,
            width=width, height=height, quality=quality)

    def updateDimension(self):
        reader = self.open()
        self.width, self.height = getImageSize(reader)
        reader.close()


class FileDataClear(object):
    interface.implements(IFileDataClear)


fileDataClear = FileDataClear()


class FileDataNoValue(object):
    interface.implements(IFileDataNoValue)


fileDataNoValue = FileDataNoValue()


class FileData(object):
    """ widget data """
    interface.implements(IFileData)

    def __init__(self, file=u'', filename=None, mimeType=None):
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

        file.seek(0,2)
        self.size = int(file.tell())

        if mimeType is None:
            mimeType = api.guessMimetype(file, self.filename)[0]

        self.mimeType = mimeType

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
                'Expires', u"Fri, 01 Jan, 2100 01:01:01 GMT")
            request.response.setHeader(
                'Last-Modified', u"Sat, 01 Jan, 2000 01:01:01 GMT")

        return getMultiAdapter((self.context, request), name='index.html')


class DownloadResult(object):
    interface.implements(IResult)

    def __init__(self, context):
        self._iter = bodyIterator(context.openDetached())

    def __iter__(self):
        return self._iter

class DownloadPreviewResult(object):
    interface.implements(IResult)

    def __init__(self, context):
        self._iter = bodyIterator(context.openPreviewDetached())

    def __iter__(self):
        return self._iter


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
            while (ord(b) != 0xFF): b = fp.read(1)
            while (ord(b) == 0xFF): b = fp.read(1)
            if (ord(b) >= 0xC0 and ord(b) <= 0xC3):
                fp.read(3)
                h, w = struct.unpack(">HH", fp.read(4))
                break
            else:
                fp.read(int(struct.unpack(">H", fp.read(2))[0])-2)
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
