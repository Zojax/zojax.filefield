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

from zope.app.testing import functional
from zope.app.component.hooks import setSite

FileFieldLayer = functional.ZCMLLayer(
    os.path.join(os.path.split(__file__)[0], 'ftesting.zcml'),
    __name__, 'FileFieldLayer', allow_teardown=True)

def FunctionalDocFileSuite(*paths, **kw):
    layer = FileFieldLayer

    globs = kw.setdefault('globs', {})
    globs['http'] = functional.HTTPCaller()
    globs['getRootFolder'] = functional.getRootFolder
    globs['sync'] = functional.sync
    globs['deepcopy'] = deepcopy

    kw['package'] = doctest._normalize_module(kw.get('package'))

    kwsetUp = kw.get('setUp')
    def setUp(test):
        functional.FunctionalTestSetup().setUp()

        root = functional.getRootFolder()
        setSite(root)

    kw['setUp'] = setUp

    kwtearDown = kw.get('tearDown')
    def tearDown(test):
        setSite(None)
        functional.FunctionalTestSetup().tearDown()

    kw['tearDown'] = tearDown

    if 'optionflags' not in kw:
        old = doctest.set_unittest_reportflags(0)
        doctest.set_unittest_reportflags(old)
        kw['optionflags'] = (old|doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS)

    suite = doctest.DocFileSuite(*paths, **kw)
    suite.layer = layer
    return suite


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
        FunctionalDocFileSuite("data.txt"),
        FunctionalDocFileSuite("file.txt"),
        FunctionalDocFileSuite("image.txt"),
        fromDocFile('widget.txt'),
        fromDocFile('download.txt'),
        #fromDocFile('configlet.txt'),
        ))
