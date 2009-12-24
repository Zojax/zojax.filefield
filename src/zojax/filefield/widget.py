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
from types import FileType
from zope import schema, component, interface
from zope.component import getMultiAdapter
from zope.publisher.browser import FileUpload
from zope.security.proxy import removeSecurityProxy
from zope.app.pagetemplate import ViewPageTemplateFile

from z3c.form.browser import file
from z3c.form.widget import FieldWidget
from z3c.form import interfaces, converter, validator, datamanager

from data import fileDataClear, fileDataNoValue, FileData
from interfaces import _, IBlobDataField, IFileWidget
from interfaces import IFile, IFileData
from interfaces import IFileDataClear, IFileDataNoValue


@component.adapter(IBlobDataField, interface.Interface)
@interface.implementer(interfaces.IFieldWidget)
def FileFieldWidget(field, request):
    return FieldWidget(field, FileWidget(request))


class FileWidget(file.FileWidget):
    interface.implements(IFileWidget)

    unload_template = ViewPageTemplateFile('widget.pt')

    rows = 10
    klass = 'file-widget'

    unload = False

    def update(self):
        field = self.field

        canUnload = not self.ignoreContext and not field.required

        if canUnload:
            value = getMultiAdapter((self.context, field),
                                    interfaces.IDataManager).query()
            if value is interfaces.NOVALUE:
                self.canUnload = False
            else:
                self.canUnload = bool(value)
        else:
            self.canUnload = False

        if self.canUnload:
            name = '%s_unload'%field.__name__
            self.unload = schema.Bool(
                __name__ = name,
                title = _(u"Remove"),
                default = False,
                required = False)

            setattr(self, name, False)

            self.unload.context = self
            self.unload_widget = getMultiAdapter(
                (self.unload, self.request), interfaces.IFieldWidget)
            self.unload_widget.context = self
            interface.alsoProvides(self.unload_widget, interfaces.IContextAware)
            self.unload_widget.update()

        super(FileWidget, self).update()

    def render(self):
        filewidget = super(FileWidget, self).render()

        if self.canUnload:
            return filewidget + self.unload_template()
        else:
            return filewidget

    def extract(self, default=fileDataNoValue):#interfaces.NOVALUE):
        fileUpload = self.request.get(self.name, default)

        if self.canUnload:
            unload = self.unload_widget.extract(default)

            if fileUpload is default or not fileUpload:
                if unload is default:
                    return default
                else:
                    if unload[0] == u'true':
                        return fileDataClear

                return default
        else:
            if fileUpload is default or not fileUpload:
                return default

        if isinstance(fileUpload, FileUpload) or \
                isinstance(fileUpload, FileType):
            return FileData(fileUpload)
        else:
            return default


class FileFieldDataManager(datamanager.AttributeField):
    component.adapts(interface.Interface, IBlobDataField)

    def set(self, value):
        """See z3c.form.interfaces.IDataManager"""
        if self.field.readonly:
            raise TypeError("Can't set values on read-only fields "
                            "(name=%s, class=%s.%s)"
                            % (self.field.__name__,
                               self.context.__class__.__module__,
                               self.context.__class__.__name__))

        if not (IFile.providedBy(value) or
                IFileData.providedBy(value) or
                IFileDataClear.providedBy(value)):
            return

        # get the right adapter or context
        context = removeSecurityProxy(self.context)
        if self.field.interface is not None:
            context = self.field.interface(context)

        field = self.field.bind(context)
        field.set(context, value)


class FileWidgetDataConverter(converter.BaseDataConverter):
    component.adapts(IBlobDataField, IFileWidget)

    def toFieldValue(self, value):
        if IFileData.providedBy(value) or \
               IFileDataClear.providedBy(value) or \
               IFileDataNoValue.providedBy(value):
            return value

        return FileData(value)


class FileFieldValidator(validator.SimpleFieldValidator):
    component.adapts(
        interface.Interface,
        interface.Interface,
        interface.Interface,
        IBlobDataField,
        interface.Interface)

    def validate(self, value):
        if IFileDataClear.providedBy(value):
            return

        return super(FileFieldValidator, self).validate(value)
