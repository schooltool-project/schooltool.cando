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
from zope.component import provideHandler
from zope.interface import implements, classImplements
from zope.annotation.interfaces import IAttributeAnnotatable

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.relationship.tests import setUpRelationships
from schooltool.cando.interfaces import (
    ILayer, ILayerContained, ILayerContainer,
    INode, INodeContained, INodeContainer,
    IDocument, IDocumentContained, IDocumentContainer,
    )
from schooltool.cando.model import (
    Layer, LayerContainer,
    NodeContainer, Node,
    preventLayerCycles,
    nodeLinkDoesntViolateModel,
    nodeLayerDoesntViolateModel,
    removingLayerDoesntViolateModel,
    NodeSkillSets,
    DocumentContainer, Document,
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


def buildTestModel_crafts():
    layers = LayerContainer()
    layers['craft'] = Layer('Craft')
    layers['branch'] = Layer('Branch')
    layers['branch'].parents.add(layers['craft'])
    layers['topic'] = Layer('Topic')
    layers['topic'].parents.add(layers['branch'])

    nodes = NodeContainer()
    nodes['carpentry'] = Node('Carpentry')
    nodes['carpentry'].layers.add(layers['craft'])
    nodes['creative'] = Node('Creative')
    nodes['creative'].layers.add(layers['branch'])
    nodes['creative'].parents.add(nodes['carpentry'])
    nodes['conventional'] = Node('Conventional')
    nodes['conventional'].layers.add(layers['branch'])
    nodes['conventional'].parents.add(nodes['carpentry'])
    nodes['whacking'] = Node('Whacking')
    nodes['whacking'].layers.add(layers['topic'])
    nodes['whacking'].parents.add(nodes['creative'])
    nodes['hammering'] = Node('Hammering')
    nodes['hammering'].layers.add(layers['topic'])
    nodes['hammering'].parents.add(nodes['conventional'])
    nodes['pounding'] = Node('Pounding')
    nodes['pounding'].layers.add(layers['topic'])
    nodes['pounding'].parents.add(nodes['creative'])
    nodes['pounding'].parents.add(nodes['conventional'])
    return layers, nodes


def buildTestModel_documents():
    layers, nodes = buildTestModel_crafts()
    documents = DocumentContainer()
    main = documents['main'] = Document('Main Document')
    main.hierarchy.add(layers['craft'])
    main.hierarchy.add(layers['branch'])
    main.hierarchy.add(layers['topic'])
    return documents


def doctest_Node():
    """Tests for Layer.

        >>> layers, nodes = buildTestModel_crafts()

        >>> verifyObject(INodeContainer, nodes)
        True

        >>> verifyObject(INodeContained, nodes['carpentry'])
        True

        >>> nodes['pounding']
        <Node 'Pounding' <Layer 'Topic'>>

    """


def doctest_Node_parental_consistency():
    """Test node parent relationship constraints.

        >>> layers, nodes = buildTestModel_crafts()

    Nodes can't have cycles.

        >>> nodes['conventional'].parents.add(nodes['pounding'])
        Traceback (most recent call last):
        ...
        CyclicRelationship:
          child <Node 'Conventional' <Layer 'Branch'>>
          target parent <Node 'Pounding' <Layer 'Topic'>>
          distant parents <Node 'Carpentry' <Layer 'Craft'>>,
                          <Node 'Conventional' <Layer 'Branch'>>,
                          <Node 'Creative' <Layer 'Branch'>>

    Let's try linking nodes that would violate the document model.

        >>> nodes['new_age'] = Node('New age')
        >>> nodes['futuristic'] = Node('Futuristic')

        >>> nodes['futuristic'].layers.add(layers['branch'])
        >>> nodes['futuristic'].parents.add(nodes['new_age'])

    Let's add a futuristic(branch) as a child of a whacking(topic).

        >>> nodes['futuristic'].parents.add(nodes['whacking'])
        Traceback (most recent call last):
        ...
        ViolateLayerModel:
          candidate <Node 'Futuristic' <Layer 'Branch'>>
          acceptable parent layers <Layer 'Craft'>
          violates parent <Node 'Whacking' <Layer 'Topic'>>

    Also, we can't add node that has a child ('branch') to a topic.

        >>> nodes['new_age'].parents.add(nodes['whacking'])
        Traceback (most recent call last):
        ...
        ViolateLayerModel:
          candidate <Node 'Futuristic' <Layer 'Branch'>>
          acceptable parent layers <Layer 'Craft'>
          violates parent <Node 'Whacking' <Layer 'Topic'>>

    But we can add new_age(no layer) to carpentry(craft),
    because it's child futuristic(branch) fits the craft->branch model.

        >>> nodes['new_age'].parents.add(nodes['carpentry'])

        >>> print nodes['whacking'].findPaths()
        [(<Node 'Carpentry' <Layer 'Craft'>>,
          <Node 'Creative' <Layer 'Branch'>>,
          <Node 'Whacking' <Layer 'Topic'>>)]

    Let's consider another example.

        >>> nodes['bashing'] = Node('Bashing')
        >>> nodes['bashing'].layers.add(layers['topic'])

    We can add only direct layer parents.

    That is, we can assign bashing(topic) to conventional(branch):

        >>> nodes['bashing'].parents.add(nodes['conventional'])

    But we can't assign bashing(topic) to carpentry(craft)

        >>> nodes['bashing'].parents.add(nodes['carpentry'])
        Traceback (most recent call last):
        ...
        ViolateLayerModel:
          candidate <Node 'Bashing' <Layer 'Topic'>>
          acceptable parent layers <Layer 'Branch'>
          violates parent <Node 'Carpentry' <Layer 'Craft'>>

    """


def doctest_Node_layer_consistency():
    """Test node layer relationship constraints.

        >>> layers, nodes = buildTestModel_crafts()

        >>> nodes['bashing'] = Node('Bashing')

        >>> nodes['bashing'].layers.add(layers['craft'])

        >>> nodes['bashing'].layers.add(layers['branch'])
        Traceback (most recent call last):
        ...
        InvalidLayerLink:
        setting layer <Layer 'Branch'>
        for node <Node 'Bashing' <Layer 'Craft'>>
        offends node <Node 'Bashing' <Layer 'Craft'>>

        >>> nodes['bashing'].layers.remove(layers['craft'])

        >>> nodes['bashing'].parents.add(nodes['creative'])

        >>> nodes['bashing'].layers.add(layers['craft'])
        Traceback (most recent call last):
        ...
        InvalidLayerLink:
        setting layer <Layer 'Craft'>
        for node <Node 'Bashing' >
        offends node <Node 'Creative' <Layer 'Branch'>>

        >>> nodes['bashing'].layers.add(layers['topic'])

        >>> nodes['bashing'].layers.add(layers['craft'])
        Traceback (most recent call last):
        ...
        InvalidLayerLink:
        setting layer <Layer 'Craft'>
        for node <Node 'Bashing' <Layer 'Topic'>>
        offends node <Node 'Bashing' <Layer 'Topic'>>

        >>> nodes['creative'].layers.remove(layers['branch'])
        Traceback (most recent call last):
        ...
        CannotRemoveLayer: setting layer <Layer 'Branch'>
        for node <Node 'Creative' <Layer 'Branch'>>
        breaks parents <Node 'Carpentry' <Layer 'Craft'>>
        and children <Node 'Bashing' <Layer 'Topic'>>,
                     <Node 'Pounding' <Layer 'Topic'>>,
                     <Node 'Whacking' <Layer 'Topic'>>

    """


def doctest_Node_findPaths():
    r"""Tests for node.findPaths

        >>> layers, nodes = buildTestModel_crafts()

    Say, we also have an alternative, industry:

        >>> layers['industry'] = Layer('Industry')
        >>> layers['job'] = Layer('Job')
        >>> layers['job'].parents.add(layers['industry'])
        >>> layers['topic'].parents.add(layers['job'])

        >>> nodes['transportation'] = Node('Transportation')
        >>> nodes['transportation'].layers.add(layers['industry'])
        >>> nodes['ship_builder'] = Node('Ship builder')
        >>> nodes['ship_builder'].layers.add(layers['job'])
        >>> nodes['ship_builder'].parents.add(nodes['transportation'])

        >>> nodes['construction'] = Node('Construction')
        >>> nodes['construction'].layers.add(layers['industry'])
        >>> nodes['carpenter'] = Node('Carpenter')
        >>> nodes['carpenter'].layers.add(layers['job'])
        >>> nodes['carpenter'].parents.add(nodes['construction'])

        >>> nodes['hammering'].parents.add(nodes['carpenter'])
        >>> nodes['hammering'].parents.add(nodes['ship_builder'])
        >>> nodes['whacking'].parents.add(nodes['carpenter'])
        >>> nodes['pounding'].parents.add(nodes['ship_builder'])

    findPaths will return a list of paths that lead to our node:

        >>> print nodes['pounding'].findPaths()
        [(<Node 'Carpentry' <Layer 'Craft'>>,
          <Node 'Conventional' <Layer 'Branch'>>,
          <Node 'Pounding' <Layer 'Topic'>>),
         (<Node 'Carpentry' <Layer 'Craft'>>,
          <Node 'Creative' <Layer 'Branch'>>,
          <Node 'Pounding' <Layer 'Topic'>>),
         (<Node 'Transportation' <Layer 'Industry'>>,
          <Node 'Ship builder' <Layer 'Job'>>,
          <Node 'Pounding' <Layer 'Topic'>>)]

    Here's another example:

        >>> print ('\n'+'-'*40+'\n').join(
        ...     [str(p) for p in nodes['hammering'].findPaths()])
        (<Node 'Construction' <Layer 'Industry'>>,
         <Node 'Carpenter' <Layer 'Job'>>,
         <Node 'Hammering' <Layer 'Topic'>>)
        ----------------------------------------
        (<Node 'Carpentry' <Layer 'Craft'>>,
         <Node 'Conventional' <Layer 'Branch'>>,
         <Node 'Hammering' <Layer 'Topic'>>)
        ----------------------------------------
        (<Node 'Transportation' <Layer 'Industry'>>,
         <Node 'Ship builder' <Layer 'Job'>>,
         <Node 'Hammering' <Layer 'Topic'>>)

    A lonely node:

        >>> nodes['something'] = Node('Something')
        >>> nodes['something'].findPaths()
        [(<Node 'Something' >,)]

    """


def doctest_Node_skillsets():
    r"""Tests for node.skillsets.

        >>> layers, nodes = buildTestModel_crafts()

    Nodes can have assigned skillsets.

        >>> sc1 = SkillSet('Whacking with a hammer')
        >>> sc2 = SkillSet('Whacking with a shoe')
        >>> sc3 = SkillSet('Work place ethics')

        >>> nodes['whacking'].skillsets.add(sc1)
        >>> nodes['whacking'].skillsets.add(sc2)
        >>> nodes['whacking'].skillsets.add(sc3)

        >>> print sorted(nodes['whacking'].skillsets, key=lambda s: s.title)
        [SkillSet('Whacking with a hammer'),
         SkillSet('Whacking with a shoe'),
         SkillSet('Work place ethics')]

        >>> print list(NodeSkillSets.query(skillset=sc1))
        [<Node 'Whacking' <Layer 'Topic'>>]

    """


def doctest_Document():
    """Tests for Document.

        >>> documents = buildTestModel_documents()

        >>> verifyObject(IDocumentContainer, documents)
        True

        >>> verifyObject(IDocumentContained, documents['main'])
        True

        >>> documents['main']
        <Document 'Main Document' <Layer 'Craft'>, <Layer 'Branch'>, <Layer 'Topic'>>

    """


def setUpModelConstraints(test=None):
    provideHandler(preventLayerCycles)
    provideHandler(nodeLinkDoesntViolateModel)
    provideHandler(nodeLayerDoesntViolateModel)
    provideHandler(removingLayerDoesntViolateModel)


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
