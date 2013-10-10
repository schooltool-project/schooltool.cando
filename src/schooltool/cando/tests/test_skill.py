#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2012 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Unit tests for groups
"""
import unittest
import doctest

from zope.interface.verify import verifyObject
from zope.app.testing import setup
from zope.component import provideHandler, provideAdapter
from zope.interface import implements

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.relationship.tests import setUpRelationships
#from schooltool.testing.catalog import setUpIntIds, tearDownIntIds
#from schooltool.testing.catalog import setUpCatalogs, tearDownCatalogs
from schooltool.requirement.interfaces import IScoreSystemContainer
from schooltool.cando.interfaces import (
    ISkill,
    )
from schooltool.cando.skill import (
    Skill, SkillSet,
    )


def doctest_Skill():
    """Tests for Skill.

        >>> skill = Skill(title=u'Unit testing')

        >>> verifyObject(ISkill, skill)
        True

        >>> skill.title
        u'Unit testing'

        >>> skill.external_id
        u''

        >>> print repr(Skill('very '*15+'long description'))
        <Skill u'very very very ve...ery long description'>

    """


def doctest_Skill_Equivalency():
    """Tests for Skill equivalency.

        >>> def print_skills(iterable):
        ...     print sorted(iterable, key=lambda i:(i.title, i.__name__))

    Say we have three skills.

        >>> sc = SkillSet('Carpentry')
        >>> hammer = sc.add(Skill('Hammering'))
        >>> pound = sc.add(Skill('Pounding'))
        >>> whack = sc.add(Skill('Whacking'))

        >>> print_skills(hammer.equivalent)
        []

    And we decide to make hammering equivalent to pounding.

        >>> hammer.equivalent.add(pound)

        >>> print_skills(hammer.equivalent)
        [<Skill u'Pounding'>]

        >>> print_skills(pound.equivalent)
        [<Skill u'Hammering'>]

    Then, we make whacking equivalent to pounding.

        >>> whack.equivalent.add(pound)

        >>> print_skills(whack.equivalent)
        [<Skill u'Pounding'>]

    Whacking becomes indirectly equivalent to hammering:

        >>> print_skills(whack.findAllEquivalent())
        [<Skill u'Hammering'>, <Skill u'Pounding'>]

    Because of direct dependence to pounding:

        >>> print_skills(whack.equivalent)
        [<Skill u'Pounding'>]

        >>> print_skills(pound.equivalent)
        [<Skill u'Hammering'>, <Skill u'Whacking'>]

    And if we remove the original dependence, indirect
    dependence is removed as well.

        >>> whack.equivalent.remove(pound)

        >>> print_skills(whack.equivalent)
        []

        >>> print_skills(whack.findAllEquivalent())
        []

    """


class AppStub(dict):
    implements(ISchoolToolApplication)


def setUp(test):
    setup.placefulSetUp()
    setup.setUpTraversal()
    setup.setUpAnnotations()
    provideAdapter(lambda n: AppStub(), (None,), ISchoolToolApplication)
    provideAdapter(lambda a: {}, (ISchoolToolApplication,), IScoreSystemContainer)
    # XXX: no int id or catalog usage yet
    #setUpIntIds(test)
    #setUpCatalogs(test)
    setUpRelationships()

def tearDown(test):
    #tearDownCatalogs(test)
    #tearDownIntIds(test)
    setup.placefulTearDown()


def test_suite():
    optionflags = (doctest.NORMALIZE_WHITESPACE |
                   doctest.ELLIPSIS |
                   doctest.REPORT_NDIFF)
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                             optionflags=optionflags),
           ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
