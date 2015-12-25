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
from zope.component import getMultiAdapter  # , queryMultiAdapter
from zope.component.interfaces import ComponentLookupError
from zope.publisher.browser import FileUpload
from zope.security.proxy import removeSecurityProxy
# from zope.app.pagetemplate import ViewPageTemplateFile

from z3c.form.browser import file
from z3c.form.widget import FieldWidget
from z3c.form import interfaces, converter, validator, datamanager

from data import fileDataClear, FileData  # , fileDataNoValue
from interfaces import _, IBlobDataField, IFileWidget
from interfaces import IFile, IFileData
from interfaces import IFileDataClear, IFileDataNoValue


def str2bool(val):
    return val.lower() in ("true", "yes", "1")


@component.adapter(IBlobDataField, interface.Interface)
@interface.implementer(interfaces.IFieldWidget)
def FileFieldWidget(field, request):
    return FieldWidget(field, FileWidget(request))


class FileWidget(file.FileWidget):
    interface.implements(IFileWidget)

    rows = 10
    klass = 'file-widget'

    unload = False
    disable_preview = False
    disable_print = False

    def update(self):
        field = self.field

        canUnload = not self.ignoreContext and not field.required

        if canUnload:
            try:
                value = getMultiAdapter((self.context, field),
                                        interfaces.IDataManager).query()
                if value is interfaces.NOVALUE:
                    self.canUnload = False
                else:
                    self.canUnload = bool(value)
            except ComponentLookupError:
                self.canUnload = False
        else:
            self.canUnload = False

        if self.canUnload:
            name = '%s_unload' % self.name
            self.unload = schema.Bool(
                __name__=name,
                title=_(u"Remove"),
                default=False,
                required=False)

            setattr(self, name, False)

            self.unload.context = self
            self.unload_widget = getMultiAdapter(
                (self.unload, self.request), interfaces.IFieldWidget)
            self.unload_widget.context = self
            interface.alsoProvides(
                self.unload_widget, interfaces.IContextAware)
            self.unload_widget.update()

        # NOTE: disable preview generation widget
        name = '%s_disable_preview' % self.name
        self.disable_preview = schema.Bool(
            __name__=name,
            title=_(u"Disable Preview generation?"),
            default=False,
            required=False)
        # disablePreview = getattr(
        #     removeSecurityProxy(self.context), 'disablePreview', False)
        try:
            value = getMultiAdapter(
                (removeSecurityProxy(self.context), field),
                interfaces.IDataManager).query()
            setattr(self, name, value.disablePreview)
        except:  # (ComponentLookupError, AttributeError):
            setattr(self, name, False)

        self.disable_preview.context = self
        self.disable_preview_widget = getMultiAdapter(
            (self.disable_preview, self.request), interfaces.IFieldWidget)
        self.disable_preview_widget.context = self
        interface.alsoProvides(
            self.disable_preview_widget, interfaces.IContextAware)
        self.disable_preview_widget.update()

        # NOTE: disable print button widget
        name = '%s_disable_print' % self.name
        self.disable_print = schema.Bool(
            __name__=name,
            title=_(u"Disable Print button?"),
            default=False,
            required=False)
        try:
            value = getMultiAdapter(
                (removeSecurityProxy(self.context), field),
                interfaces.IDataManager).query()
            setattr(self, name, value.disablePrint)
        except:
            setattr(self, name, False)

        self.disable_print.context = self
        self.disable_print_widget = getMultiAdapter(
            (self.disable_print, self.request), interfaces.IFieldWidget)
        self.disable_print_widget.context = self
        interface.alsoProvides(
            self.disable_print_widget, interfaces.IContextAware)
        self.disable_print_widget.update()

        super(FileWidget, self).update()

    def extract(self, default=interfaces.NOVALUE):
        context = self.context
        if hasattr(context, 'data') and IFile.providedBy(context.data):
            # NOTE: change disablePreview, even if no new file is uploaded
            file_data = removeSecurityProxy(context).data
            file_data.disablePreview = str2bool(
                self.disable_preview_widget.value[0])
            file_data.disablePrint = str2bool(
                self.disable_print_widget.value[0])

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
        value.disablePreview = False
        value.disablePrint = False
        if getattr(self.widget, 'disable_preview', None) is not None:
            if 'true' in self.widget.disable_preview_widget.value:
                value.disablePreview = True
        if getattr(self.widget, 'disable_print', None) is not None:
            if 'true' in self.widget.disable_print_widget.value:
                value.disablePrint = True

        if IFileData.providedBy(value) or IFileDataClear.providedBy(value) or \
           IFileDataNoValue.providedBy(value) or IFile:
            return value

        if value is None or value == '':
            # When no new file is uploaded, send a signal that we do not want
            # to do anything special.
            return interfaces.NOT_CHANGED

        return FileData(value)

    def toWidgetValue(self, value):
        """See interfaces.IDataConverter"""
        # raise Exception(value)
        return value


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
