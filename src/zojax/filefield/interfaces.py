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
from zope import interface, schema
from zope.schema.interfaces import IField
from zope.i18nmessageid import MessageFactory

from z3c.form.interfaces import IFileWidget as IFileWidgetBase


_ = MessageFactory('zojax.filefield')

OO_CONVERTER_EXECUTABLE = 'unoconv'
OO_CONVERTED_TYPES = ['application/vnd.oasis.opendocument.database',
                      'application/vnd.oasis.opendocument.formula',
                      'application/vnd.oasis.opendocument.graphics',
                      'application/vnd.oasis.opendocument.graphics-template',
                      'application/vnd.oasis.opendocument.image',
                      'application/vnd.oasis.opendocument.presentation',
                      'application/vnd.oasis.opendocument.presentation-template',
                      'application/vnd.oasis.opendocument.spreadsheet',
                      'application/vnd.oasis.opendocument.spreadsheet-template',
                      'application/vnd.oasis.opendocument.text',
                      'application/vnd.oasis.opendocument.text-master',
                      'application/vnd.oasis.opendocument.text-template',
                      'application/vnd.oasis.opendocument.text-web',
                      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheetv',
                      'application/vnd.openxmlformats-officedocument.spreadsheetml.template',
                      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                      'application/vnd.openxmlformats-officedocument.presentationml.slideshow',
                      'application/vnd.openxmlformats-officedocument.presentationml.template',
                      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                      'application/vnd.openxmlformats-officedocument.wordprocessingml.template']

PREVIEWED_TYPES = OO_CONVERTED_TYPES + ['application/pdf']

class NotAllowedFileType(schema.ValidationError):
    __doc__ = _('Data mime type is not allowed.')


class ImageDimensionExceeded(schema.ValidationError):
    __doc__ = _('Image dimension exceeded.')


class IBlobDataField(interface.Interface):
    """ Blob data field """


class IFileField(IField):
    """ File field """

    mimeTypes = schema.Tuple(
        title = u'Mime types',
        description = u'Allowed mime types',
        default = (),
        required = False)


class IImageField(IField):
    """ image field """

    scale = schema.Bool(
        title = u'Scale',
        description = u'Scale image',
        default = False,
        required = False)

    maxWidth = schema.Int(
        title = u'Max width',
        required = False)

    maxHeight = schema.Int(
        title = u'Max height',
        required = False)


class IFile(interface.Interface):

    mimeType = schema.TextLine(
        title = _(u'Mime type'),
        required = False)

    data = schema.Bytes(
        title = _(u'Data'),
        required = False)

    previewData = schema.Bytes(
        title = _(u'Preview Data'),
        required = False)

    previewIsAvailable = schema.Bool(
        title = _(u'Preview is Available'),
        required = False)

    size = interface.Attribute('File size')

    previewSize = interface.Attribute('File preview size')

    hash = interface.Attribute('Data md5 hash')

    filename = interface.Attribute('File name')

    modified = interface.Attribute('Modified time')



    def open(mode='r'):
        """ Open file and return the file descriptor """

    def openDetached():
        """Return file data disconnected from database connection.

        Read access only.
        """

    def clear():
        """ clear all data """

    def show(request, filename=None):
        """ show file committed"""
    
    def showFly(request, filename=None):
        """ show file """

    def showPreview(request, filename=None):
        """ show preview of the file committed"""
    
    def showPreviewFly(request, filename=None):
        """ show preview of the file """

    def __len__(self):
        """ file size in bytes """

    def __nonzero__(self):
        """ empty file or not """


class IImage(IFile):

    width = schema.Int(
        title = _(u'Width'),
        required = True)

    height = schema.Int(
        title = _(u'Height'),
        required = True)

    def scale(width, height, quality=88):
        """ scale image """

    def updateDimension():
        """ update image dimenion,
        usually called after image.open('wb').write() """


class IFileData(interface.Interface):
    """ file field widget data """

    data = interface.Attribute('Data')

    mimeType = interface.Attribute('MimeType')

    filename = interface.Attribute('Filename')

    def __len__():
        """ data length """


class IFileDataClear(interface.Interface):
    """ file field data clearance """


class IFileDataNoValue(interface.Interface):
    """ no value """


class IFileWidget(IFileWidgetBase):
    """ file field widget """
