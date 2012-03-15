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
from persistent.interfaces import IPersistent

from zope import interface, schema
from zope.schema.interfaces import RequiredMissing, WrongType
from zope.security.proxy import removeSecurityProxy
from zope.publisher.browser import FileUpload

from data import File, Image, FileData, getImageSize, fileDataNoValue

from interfaces import NotAllowedFileType, ImageDimensionExceeded

from interfaces import IBlobDataField
from interfaces import IFileField, IImageField
from interfaces import IFile, IImage, IFileData
from interfaces import IFileDataClear, IFileDataNoValue

_marker = object()


class FileField(schema.MinMaxLen, schema.Field):
    interface.implements(IBlobDataField, IFileField)

    mimeTypes = ()

    def __init__(self, mimeTypes=(), **kw):
        super(FileField, self).__init__(**kw)

        try:
            mts = {}
            for mt in mimeTypes:
                mt1, mt2 = mt.split('/')

                sec = mts.setdefault(mt1, [])
                if mt2 not in sec:
                    sec.append(mt2)

            self.mts = mts
            self.mimeTypes = mimeTypes
        except:
            raise ValueError('Mime type format error.', mimeTypes)

    def get(self, object, _getattr=getattr, _setattr=setattr):
        value = _getattr(object, self.__name__, None)

        if IFile.providedBy(value):
            return value
        elif value is None:
            value = u''

        self.set(object, value, _getattr, _setattr)
        return self.get(object, _getattr, _setattr)

        raise AttributeError(self.__name__)

    def set(self, object, value, _getattr=getattr, _setattr=setattr):
        if self.readonly:
            raise TypeError("Can't set values on read-only fields "
                            "(name=%s, class=%s.%s)"
                            % (self.__name__,
                               object.__class__.__module__,
                               object.__class__.__name__))

        if IFile.providedBy(value):
            _setattr(object, self.__name__, value)
        elif IFileData.providedBy(value):
            data = _getattr(object, self.__name__, None)
            if not IFile.providedBy(data):
                data = File()
                data.data = value.data
                data.mimeType = value.mimeType
                data.filename = value.filename
                data.rebuildPreview = True
                _setattr(object, self.__name__, data)
            else:
                data = removeSecurityProxy(data)
                data.data = value.data
                data.mimeType = value.mimeType
                data.filename = value.filename
                data.rebuildPreview = True
                _setattr(object, self.__name__, data)
        elif IFileDataClear.providedBy(value):
            data = _getattr(object, self.__name__, None)
            if IFile.providedBy(data):
                data.clear()
            else:
                _setattr(object, self.__name__, File())
        elif IFileDataNoValue.providedBy(value):
            pass
        else:
            self.set(object, FileData(value), _getattr, _setattr)

    def _validate(self, value):
        if (IFileDataNoValue.providedBy(value) or not value)  and self.required:
            raise RequiredMissing()

        if IFileDataClear.providedBy(value) or IFileDataNoValue.providedBy(value):
            return

        super(FileField, self)._validate(value)

        if not (IFile.providedBy(value) or IFileData.providedBy(value)):
            raise WrongType(value, (IFile, IFileData))

        if self.mimeTypes:
            mt1, mt2 = value.mimeType.split('/')

            sec = self.mts.get(mt1)
            if sec:
                if '*' in sec:
                    return
                elif mt2 in sec:
                    return

            raise NotAllowedFileType(value.mimeType, self.mimeTypes)


class ImageField(schema.MinMaxLen, schema.Field):
    interface.implements(IBlobDataField, IImageField)

    mimeTypes = ('image/jpeg', 'image/gif', 'image/png')

    def __init__(self, scale=False, maxWidth=0, maxHeight=0, **kw):
        super(ImageField, self).__init__(**kw)

        self.scale = scale
        self.maxWidth = maxWidth
        self.maxHeight = maxHeight

    def get(self, object, _getattr=getattr, _setattr=setattr):
        value = _getattr(object, self.__name__, None)
        if IImage.providedBy(value):
            return value
        elif IFile.providedBy(value):
            self.set(object, value.data, _getattr, _setattr)
            return self.get(object, _getattr, _setattr)
        elif value is None:
            value = u''

        self.set(object, value, _getattr, _setattr)
        return self.get(object, _getattr, _setattr)

    def set(self, object, value, _getattr=getattr, _setattr=setattr):
        if self.readonly:
            raise TypeError("Can't set values on read-only fields "
                            "(name=%s, class=%s.%s)"
                            % (self.__name__,
                               object.__class__.__module__,
                               object.__class__.__name__))

        if IImage.providedBy(value):
            _setattr(object, self.__name__, value)
        elif IFileData.providedBy(value):
            data = _getattr(object, self.__name__, None)
            if not IImage.providedBy(data):
                data = Image()
                data.data = value.data
                data.mimeType = value.mimeType
                data.filename = value.filename
                _setattr(object, self.__name__, data)
            else:
                data = removeSecurityProxy(data)
                data.data = value.data
                data.mimeType = value.mimeType
                data.filename = value.filename
                _setattr(object, self.__name__, data)

            if self.scale and \
                    (self.maxWidth < data.width or self.maxHeight < data.height):
                data.scale(self.maxWidth, self.maxHeight)

        elif IFileDataClear.providedBy(value):
            data = _getattr(object, self.__name__, None)
            if IImage.providedBy(data):
                data.clear()
            else:
                _setattr(object, self.__name__, Image())
        elif IFileDataNoValue.providedBy(value):
            pass
        else:
            self.set(object, FileData(value), _getattr, _setattr)

    def _validate(self, value):
        if (IFileDataNoValue.providedBy(value) or not value) and self.required:
            raise RequiredMissing()

        if IFileDataClear.providedBy(value) or \
                IFileDataNoValue.providedBy(value):
            return

        super(ImageField, self)._validate(value)

        if not (IImage.providedBy(value) or IFileData.providedBy(value)):
            raise WrongType(value, (IImage, IFileData))

        if self.mimeTypes:
            if value.mimeType not in self.mimeTypes:
                raise NotAllowedFileType(value.mimeType, self.mimeTypes)

        if not self.scale and (self.maxWidth > 0 or self.maxHeight > 0):
            if IImage.providedBy(value):
                width, height = value.width, value.height
            else:
                width, height = getImageSize(value.data)

            if self.maxWidth > 0 and width > self.maxWidth:
                raise ImageDimensionExceeded(width, ('width', self.maxWidth))

            if self.maxHeight > 0 and height > self.maxHeight:
                raise ImageDimensionExceeded(height, ('height', self.maxHeight))


class FileFieldProperty(object):

    def __init__(self, field, name=None):
        if name is None:
            name = field.__name__

        self.__field = field
        self.__name = name

    def __get__(self, inst, klass):
        if inst is None:
            return self

        try:
            value = self.__field.get(inst, self.__getattr, self.__setattr)
        except AttributeError:
            value = _marker

        if value is _marker:
            field = self.__field.bind(inst)
            value = getattr(field, 'default', _marker)
            if value is _marker:
                raise AttributeError(self.__name)

        return value

    def __set__(self, inst, value):
        field = self.__field.bind(inst)
        field.validate(value)
        if field.readonly and inst.__dict__.has_key(self.__name):
            raise ValueError(self.__name, 'field is readonly')
        self.__field.set(inst, value, self.__getattr, self.__setattr)

    def __delete__(self, inst):
        if self.__name in inst.__dict__:
            del inst.__dict__[self.__name]

    def __getattr(self, object, name, default=None):
        return removeSecurityProxy(object).__dict__.get(name, default)

    def __setattr(self, object, name, value):
        removeSecurityProxy(object).__dict__[name] = value

        if IPersistent.providedBy(object):
            object._p_changed = True
