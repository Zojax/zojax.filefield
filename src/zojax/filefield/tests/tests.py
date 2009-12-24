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
import os.path
import unittest, doctest
from copy import deepcopy
from zope.app.testing import setup
from zojax.filefield import testing

FileFieldLayer = testing.ZCMLLayer(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "ftesting.zcml"), __name__, "FileFieldLayer")

def fromDocFile(path):
    suite = testing.FunctionalDocFileSuite(path)
    suite.layer = FileFieldLayer
    return suite

def setUp(test):
    site = setup.placefulSetUp(True)
    setup.setUpTestAsModule(test, name='zojax.filefield.TESTS')
    test.globs['deepcopy'] = deepcopy

def tearDown(test):
    setup.placefulTearDown()
    setup.tearDownTestAsModule(test)

def test_suite():
    return unittest.TestSuite((
        doctest.DocFileSuite(
            'data.txt', setUp=setUp, tearDown=tearDown,
            optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS),
        doctest.DocFileSuite(
            'file.txt', setUp=setUp, tearDown=tearDown,
            optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS),
        doctest.DocFileSuite(
            'image.txt', setUp=setUp, tearDown=tearDown,
            optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS),
        fromDocFile('widget.txt'),
        fromDocFile('download.txt'),
        ))
