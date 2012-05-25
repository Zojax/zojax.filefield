from zope import interface, component, schema

from persistent import Persistent

from zojax.filefield.field import FileField, FileFieldProperty
from zojax.filefield.interfaces import IFileData
from zojax.content.type.item import PersistentItem
from zojax.content.type.interfaces import IContentType, ISearchableContent, IItem
from zojax.content.type.contenttype import ContentType
from zojax.content.type.container import ContentContainer


class IMyContent(interface.Interface):

     title = schema.TextLine(
         title = u'Title')
     data = FileField(
         title = u'Data',
         required=False)


class MyContent(PersistentItem):
     interface.implements(IMyContent)
     data = FileFieldProperty(IMyContent['data'])

class IMyContentType(interface.Interface):
    pass

class MyContentType(ContentType):
    pass


class IMyContainer(interface.Interface):
    pass


class MyContainer(ContentContainer):
    interface.implements(IMyContainer)


class IMyContainerType(interface.Interface):
    pass


class MyContainerType(ContentType):
    pass
