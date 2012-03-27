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
"""Skills document model."""

from persistent import Persistent
from zope.container.btree import BTreeContainer
from zope.container.contained import Contained
from zope.component import adapts, adapter
from zope.component import getUtility
from zope.interface import implements, implementer
from zope.intid import addIntIdSubscriber
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent import ObjectAddedEvent
from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from zope.security.proxy import removeSecurityProxy

from schooltool.app.app import StartUpBase
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.cando import interfaces
from schooltool.cando.skill import URISkillSet
from schooltool.relationship import URIObject
from schooltool.relationship import RelationshipSchema, RelationshipProperty
from schooltool.relationship.interfaces import InvalidRelationship
from schooltool.relationship.interfaces import IBeforeRelationshipEvent
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.schoolyear.subscriber import ObjectEventAdapterSubscriber


URILayer = URIObject(
    'http://schooltool.org/ns/cando/model/layer',
    'Layer',
    'A layer of the model.')

URIParentLayer = URIObject(
    'http://schooltool.org/ns/cando/model/parent_layer',
    'Parent layer',
    'A parent layer.')

URILayerLink = URIObject(
    'http://schooltool.org/ns/cando/model/layer_link',
    'Layer link',
    'A link between two layers in the model.')

LayerLink = RelationshipSchema(URILayerLink,
                              parent=URIParentLayer,
                              child=URILayer)


URINodeLink = URIObject(
    'http://schooltool.org/ns/cando/model/node_link',
    'Node link',
    'A link between two nodes in the model.')

URINode = URIObject(
    'http://schooltool.org/ns/cando/model/node',
    'Node',
    'A node.')

URIParentNode = URIObject(
    'http://schooltool.org/ns/cando/model/parent_node',
    'Parent node',
    'A parent node.')

NodeLink = RelationshipSchema(URINodeLink,
                              parent=URIParentNode,
                              child=URINode)

URINodeLayer = URIObject(
    'http://schooltool.org/ns/cando/model/node_layer',
    'Node layer',
    'A model layer the node is in.')

NodeLayer = RelationshipSchema(URINodeLayer,
                               node=URINode,
                               layer=URILayer)


URINodeSkillSets = URIObject(
    'http://schooltool.org/ns/cando/model/node_skillsets',
    'Node skillsets',
    'Skillsets this model node implements.')

NodeSkillSets = RelationshipSchema(
    URINodeSkillSets,
    node=URINode,
    skillset=URISkillSet)
# XXX: order in extra_info if neccessary


class LayerContainerContainer(BTreeContainer):
    """Container of layer containers."""
    implements(interfaces.ILayerContainerContainer)


class LayerContainer(BTreeContainer):
    """Container of layers."""
    implements(interfaces.ILayerContainer)


class Layer(Persistent, Contained):
    implements(interfaces.ILayerContained)

    title = None
    parents = RelationshipProperty(URILayerLink, URILayer, URIParentLayer)

    def __init__(self, title):
        self.title = title

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.title)


@adapter(ISchoolYear)
@implementer(interfaces.ILayerContainer)
def getLayerContainer(sy):
    addIntIdSubscriber(sy, ObjectAddedEvent(sy))
    int_ids = getUtility(IIntIds)
    sy_id = str(int_ids.getId(sy))
    app = ISchoolToolApplication(None)
    gc = app['schooltool.cando.layer'].get(sy_id, None)
    if gc is None:
        gc = app['schooltool.cando.layer'][sy_id] = LayerContainer()
    return gc


@adapter(interfaces.ILayerContainer)
@implementer(ISchoolYear)
def getSchoolYearForLayerContainer(layer_container):
    container_id = int(layer_container.__name__)
    int_ids = getUtility(IIntIds)
    container = int_ids.getObject(container_id)
    return container


@adapter(ISchoolToolApplication)
@implementer(interfaces.ILayerContainer)
def getLayerContainerForApp(app):
    syc = ISchoolYearContainer(app)
    sy = syc.getActiveSchoolYear()
    if sy is None:
        return None
    return interfaces.ILayerContainer(sy)


class LayerStartUp(StartUpBase):

    def __call__(self):
        if 'schooltool.cando.layer' not in self.app:
            self.app['schooltool.cando.layer'] = LayerContainerContainer()


class RemoveLayersWhenSchoolYearIsDeleted(ObjectEventAdapterSubscriber):
    adapts(IObjectRemovedEvent, ISchoolYear)

    def __call__(self):
        layer_container = interfaces.ILayerContainer(self.object)
        for layer_id, layer in list(layer_container.items()):
            del layer_container[layer_id]


class NodeContainerContainer(BTreeContainer):
    """Container of node containers."""
    implements(interfaces.INodeContainerContainer)


class NodeContainer(BTreeContainer):
    """Container of nodes."""
    implements(interfaces.INodeContainer)


class Node(Persistent, Contained):
    implements(interfaces.INodeContained)

    description = u''
    layers = RelationshipProperty(URINodeLayer, URINode, URILayer)
    parents = RelationshipProperty(URINodeLink, URINode, URIParentNode)

    def __init__(self, description=u''):
        self.description = description

    def __repr__(self):
        return '<%s %r %s>' % (self.__class__.__name__, self.description,
                               ', '.join([str(l) for l in self.layers]))


@adapter(ISchoolYear)
@implementer(interfaces.INodeContainer)
def getNodeContainer(sy):
    addIntIdSubscriber(sy, ObjectAddedEvent(sy))
    int_ids = getUtility(IIntIds)
    sy_id = str(int_ids.getId(sy))
    app = ISchoolToolApplication(None)
    gc = app['schooltool.cando.node'].get(sy_id, None)
    if gc is None:
        gc = app['schooltool.cando.node'][sy_id] = NodeContainer()
    return gc


@adapter(interfaces.INodeContainer)
@implementer(ISchoolYear)
def getSchoolYearForNodeContainer(node_container):
    container_id = int(node_container.__name__)
    int_ids = getUtility(IIntIds)
    container = int_ids.getObject(container_id)
    return container


@adapter(ISchoolToolApplication)
@implementer(interfaces.INodeContainer)
def getNodeContainerForApp(app):
    syc = ISchoolYearContainer(app)
    sy = syc.getActiveSchoolYear()
    if sy is None:
        return None
    return interfaces.INodeContainer(sy)


class NodeStartUp(StartUpBase):

    def __call__(self):
        if 'schooltool.cando.node' not in self.app:
            self.app['schooltool.cando.node'] = NodeContainerContainer()


class RemoveNodesWhenSchoolYearIsDeleted(ObjectEventAdapterSubscriber):
    adapts(IObjectRemovedEvent, ISchoolYear)

    def __call__(self):
        node_container = interfaces.INodeContainer(self.object)
        for node_id, node in list(node_container.items()):
            del node_container[node_id]


class CyclicRelationship(InvalidRelationship):

    def __init__(self, child, parent, parents):
        self.child = child
        self.parent = parent
        self.parents = parents
        InvalidRelationship.__init__(self, child, parent, parents)

    def __str__(self):
        return '%s' % (
            '\n'.join([
                    'child %s' % self.child,
                    'target parent %s' % self.parent,
                    'distant parents %s' % ', '.join(
                        sorted([str(l) for l in self.parents]))
                    ]))


def _expand_nodes(nodes, functor, recursive=True):
    nodes = set(nodes)
    open = set(nodes)
    parents = set()
    while open:
        p = open.pop()
        if p not in parents:
            if recursive:
                open.update(set(functor(p)).difference(parents))
            if p not in nodes:
                parents.add(p)
    return parents


@adapter(IBeforeRelationshipEvent)
def preventLayerCycles(event):
    match = event.match(LayerLink)
    if match is None:
        match = event.match(NodeLink)
    if match is None:
        return
    parent = removeSecurityProxy(match.parent)
    child = removeSecurityProxy(match.child)
    # Explicitly don't handle existing child-parent relationships,
    # only parent loops.  So, check only parents of parent node.
    parents = _expand_nodes(nodes=[parent], functor=lambda n: n.parents)
    if child in parents:
        raise CyclicRelationship(child, parent, parents)


class ViolateLayerModel(InvalidRelationship):
    pass


def validateAgainstNode(candidate, distant_parent, valid_layers):
    open = set([distant_parent])
    while open:
        # Walk up to parents with layers and check if our layers are valid
        with_no_layers = set()
        for model_node in open:
            node_layers = list(model_node.layers)
            if node_layers:
                for layer in node_layers:
                    if layer not in valid_layers:
                        raise ViolateLayerModel('\n'.join([
                            'candidate %s' % candidate,
                            'acceptable parent layers %s' % ', '.join(
                                sorted([str(l) for l in valid_layers])),
                            'violates parent %s' % model_node]))
            else:
                with_no_layers.add(model_node)
        open = _expand_nodes(nodes=with_no_layers,
                             functor=lambda n:n.parents,
                             recursive=False)


@adapter(IBeforeRelationshipEvent)
def nodeLinkDoesntViolateModel(event):
    match = event.match(NodeLink)
    if match is None:
        return
    parent = removeSecurityProxy(match.parent)
    child = removeSecurityProxy(match.child)

    if not child.layers:
        valid_layers = _expand_nodes(set(child.layers),
                                     functor=lambda n: n.parents)
        # XXX: expand only nearest layers
        validateAgainstNode(child, parent, valid_layers)

    def expand_children_if_without_layers(node):
        if node.layers:
            return []
        return NodeLink.query(parent=node)

    check_children = _expand_nodes(nodes=[child],
                                   functor=expand_children_if_without_layers)
    for node in check_children:
        if not node.layers:
            valid_layers = _expand_nodes(set(node.layers),
                                         functor=lambda n: n.parents)
            # XXX: only parent layers
            validateAgainstNode(node, parent, valid_layers)
