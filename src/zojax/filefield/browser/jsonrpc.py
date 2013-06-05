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

from z3c.jsonrpc import publisher

from zope.component import getUtility
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent

from zojax.filefield.interfaces import IPreviewsCatalog


class FileFieldAPI(publisher.MethodPublisher):

    def generatePreview(self, oid):
        """ method gets object by oid,
            then calls generateFunction() method for this object.
            result equals preview size.

            {"jsonrpc":"2.0","result":{"msg":1024,"err":""},"id":"jsonrpc"}
        """
        result = dict(msg=0, err='')

        if not oid:
            result['err'] = "not oid"
            return result

        # NOTE: get object from oid
        object = getUtility(IPreviewsCatalog).getObject(int(oid))

        if not object:
            result['err'] = "not object"
            return result

        # NOTE: starts generating preview for this object
        newsize = object.generateFunction()
        if newsize:
            result['msg'] = newsize
            # NOTE: write newsize to object
            object.previewSize = newsize
            notify(ObjectModifiedEvent(object))

        return result
