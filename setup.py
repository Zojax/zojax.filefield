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
""" Setup for zojax.filefield package

$Id$
"""
import sys, os
from setuptools import setup, find_packages

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

version='0'


setup(name = 'zojax.filefield',
      version = version,
      author = 'Nikolay Kim',
      author_email = 'fafhrd91@gmail.com',
      description ="File/image schema field",
      long_description = (
          'Detailed Documentation\n' +
          '======================\n'
          + '\n\n' +
          read('CHANGES.txt')
          ),
      classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Zope Public License',
        'Programming Language :: Python',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP',
        'Framework :: Zope3'],
      url='http://zojax.net/',
      license='ZPL 2.1',
      packages=find_packages('src'),
      package_dir = {'':'src'},
      namespace_packages=['zojax'],
      install_requires = ['setuptools', 'ZODB3', 'rwproperty',
                          'zope.schema',
                          'zope.component',
                          'zope.interface',
                          'zope.security',
                          'zope.publisher',
                          'zope.datetime',
                          'zope.i18nmessageid',
                          'zope.cachedescriptors',
                          'zope.app.security',
                          'zc.copy',
                          'z3c.form',
                          'zojax.converter',
                          'zojax.catalog',
                          'zojax.content.type',
                          'zojax.formatter',
                          'zojax.layout',
                          'zojax.resource',
                          'zojax.resourcepackage',
                          'zojax.jquery.media',
                          'zojax.batching',
                          'zojax.wizard'
                          ],
      extras_require = dict(test=['zope.app.testing',
                                  'zope.testing',
                                  'zope.testbrowser',
                                  'zope.viewlet',
                                  'zope.securitypolicy',
                                  'zope.app.zcmlfiles',
                                  'zojax.autoinclude',
                                  'zojax.formatter [test]'
                                  ]),
      include_package_data = True,
      zip_safe = False
      )
