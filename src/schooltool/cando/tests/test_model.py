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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Unit tests for groups
"""
import unittest
import doctest

from zope.interface.verify import verifyObject
from zope.app.testing import setup
from zope.component import provideHandler
from zope.interface import implements

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.relationship.tests import setUpRelationships
from schooltool.cando.interfaces import (
    ILayer, ILayerContained, ILayerContainer,
    INode, INodeContained, INodeContainer,
    )
from schooltool.cando.model import (
    Layer, LayerContainer,
    NodeContainer, Node,
    preventLayerCycles,
    nodeLinkDoesntViolateModel,
    )
from schooltool.cando.skill import (
    Skill, SkillSet,
    )


def doctest_Layers():
    """Tests for Layer.

        >>> layers = LayerContainer()

        >>> verifyObject(ILayerContainer, layers)
        True

        >>> layers['craft'] = Layer('Craft')

        >>> verifyObject(ILayerContained, layers['craft'])
        True

        >>> layers['branch'] = Layer('Branch')
        >>> layers['branch'].parents.add(layers['craft'])

        >>> print list(layers['branch'].parents)
        [<Layer 'Craft'>]

        >>> layers['topic'] = Layer('Topic')
        >>> layers['topic'].parents.add(layers['branch'])

        >>> layers['craft'].parents.add(layers['topic'])
        Traceback (most recent call last):
        ...
        CyclicRelationship:
          child <Layer 'Craft'>
          target parent <Layer 'Topic'>
          distant parents <Layer 'Branch'>, <Layer 'Craft'>

    """


def doctest_Nodes():
    """Tests for Layer.

        >>> layers = LayerContainer()
        >>> layers['craft'] = Layer('Craft')
        >>> layers['branch'] = Layer('Branch')
        >>> layers['branch'].parents.add(layers['craft'])
        >>> layers['topic'] = Layer('Topic')
        >>> layers['topic'].parents.add(layers['branch'])

        >>> nodes = NodeContainer()
        >>> verifyObject(INodeContainer, nodes)
        True

        >>> nodes['carpentry'] = Node('Carpentry')
        >>> verifyObject(INodeContained, nodes['carpentry'])
        True

        >>> nodes['carpentry'].layers.add(layers['craft'])

        >>> nodes['creative'] = Node('Creative')
        >>> nodes['creative'].layers.add(layers['branch'])

        >>> nodes['conventional'] = Node('Conventional')
        >>> nodes['conventional'].layers.add(layers['branch'])

        >>> nodes['whacking'] = Node('Whacking')
        >>> nodes['whacking'].layers.add(layers['topic'])
        >>> nodes['whacking'].parents.add(nodes['creative'])

        >>> nodes['hammering'] = Node('Hammering')
        >>> nodes['hammering'].layers.add(layers['topic'])
        >>> nodes['hammering'].parents.add(nodes['conventional'])

        >>> nodes['pounding'] = Node('Pounding')
        >>> nodes['pounding'].layers.add(layers['topic'])
        >>> nodes['pounding'].parents.add(nodes['creative'])
        >>> nodes['pounding'].parents.add(nodes['conventional'])

        >>> nodes['pounding']
        <Node 'Pounding' <Layer 'Topic'>>

        >>> nodes['conventional'].parents.add(nodes['pounding'])
        Traceback (most recent call last):
        ...
        CyclicRelationship:
          child <Node 'Conventional' <Layer 'Branch'>>
          target parent <Node 'Pounding' <Layer 'Topic'>>
          distant parents <Node 'Conventional' <Layer 'Branch'>>,
                          <Node 'Creative' <Layer 'Branch'>>

    """


def setUpModelConstraints(test=None):
    provideHandler(preventLayerCycles)
    provideHandler(nodeLinkDoesntViolateModel)


def setUp(test):
    setup.placefulSetUp()
    setup.setUpTraversal()
    setup.setUpAnnotations()
    setUpRelationships()
    setUpModelConstraints(test)

def tearDown(test):
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
