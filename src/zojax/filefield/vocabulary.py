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
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary


tp1 = SimpleTerm(u'upload', 'upload', 'On Upload (Best Performance)')
tp1.description = u'This creates preview when you add or modify file.'

tp2 = SimpleTerm(u'check', 'check', 'Always if doesn\'t exist')
tp2.description = u'This checks that preview is available and creates it in opposite case.'

tp3 = SimpleTerm(u'always', 'always', 'Always')
tp3.description = u'This generates preview every time when it\'s requested.'

creationTypes = SimpleVocabulary((tp1, tp2, tp3))
