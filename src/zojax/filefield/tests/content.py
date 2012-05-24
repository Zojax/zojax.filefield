from zope import interface, component, schema

from zojax.filefield.field import FileField
from zojax.content.type.item import PersistentItem
from zojax.content.type.interfaces import IContentType, ISearchableContent
from zojax.content.type.contenttype import ContentType


class IMyContent(ISearchableContent):

     title = schema.TextLine(
         title = u'Title')
     data = FileField(
         title = u'Data',
         required=True)


class MyContent(PersistentItem):
     interface.implements(IMyContent)


class MyContentType(ContentType):
    pass
