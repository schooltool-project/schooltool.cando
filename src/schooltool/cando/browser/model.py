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
Model views.
"""

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.cachedescriptors.property import Lazy
from zope.component import adapts, getUtility, getMultiAdapter
from zope.container.interfaces import INameChooser
from zope.i18n.interfaces.locales import ICollator
from zope.interface import implements, directlyProvides
from zope.intid.interfaces import IIntIds
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.traversing.browser.interfaces import IAbsoluteURL

import zc.table.column
from zc.table.interfaces import ISortableColumn
import z3c.form.form
import z3c.form.button
import z3c.form.field

from schooltool.skin import flourish
from schooltool import table
from schooltool.app.browser.app import RelationshipAddTableMixin
from schooltool.app.browser.app import RelationshipRemoveTableMixin
from schooltool.app.browser.app import EditRelationships
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.browser.app import ContentTitle
from schooltool.cando.browser.skill import SkillSetTable
from schooltool.cando.interfaces import ILayerContainer, ILayer
from schooltool.cando.interfaces import INodeContainer, INode
from schooltool.cando.interfaces import ISkillSetContainer
from schooltool.cando.model import Layer, LayerLink
from schooltool.cando.model import Node, NodeLink
from schooltool.common.inlinept import InlineViewPageTemplate, InheritTemplate
from schooltool.schoolyear.interfaces import ISchoolYearContainer

from schooltool.cando import CanDoMessage as _


class LayerContainerAbsoluteURLAdapter(BrowserView):
    adapts(ILayerContainer, IBrowserRequest)
    implements(IAbsoluteURL)

    def __str__(self):
        app = ISchoolToolApplication(None)
        url = absoluteURL(app, self.request)
        return url + '/layers'

    __call__ = __str__


class LayersView(flourish.page.Page):

    content_template = InlineViewPageTemplate('''
      <div tal:content="structure context/schooltool:content/ajax/view/container/table" />
      <h3 tal:condition="python: not len(context)" i18n:domain="schooltool">There are no layers.</h3>
    ''')

    @Lazy
    def container(self):
        return ILayerContainer(ISchoolToolApplication(None))


class LayersAddLinks(flourish.page.RefineLinksViewlet):
    """Manager for Add links in LayersView"""


class FlourishLayerAddView(flourish.form.AddForm):

    template = InheritTemplate(flourish.page.Page.template)
    label = None
    legend = _('Layer Information')
    fields = z3c.form.field.Fields(ILayer).select('title')

    def updateActions(self):
        super(FlourishLayerAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @z3c.form.button.buttonAndHandler(_('Submit'), name='add')
    def handleAdd(self, action):
        super(FlourishLayerAddView, self).handleAdd.func(self, action)

    @z3c.form.button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        if 'camefrom' in self.request:
            url = self.request['camefrom']
            self.request.response.redirect(url)
            return
        app = ISchoolToolApplication(None)
        url = '%s/layers' % absoluteURL(app, self.request)
        self.request.response.redirect(url)

    def create(self, data):
        layer = Layer(data['title'])
        z3c.form.form.applyChanges(self, layer, data)
        return layer

    def add(self, layer):
        chooser = INameChooser(self.context)
        name = chooser.chooseName(u'', layer)
        self.context[name] = layer
        self._layer = layer
        return layer

    def nextURL(self):
        return absoluteURL(self._layer, self.request)


class LayerView(flourish.form.DisplayForm):

    template = InheritTemplate(flourish.page.Page.template)

    label = None
    legend = _('Skill')

    fields = z3c.form.field.Fields(ILayer)
    fields = fields.select('title')

    @property
    def can_edit(self):
        return flourish.canEdit(self.context)

    @property
    def edit_url(self):
        return absoluteURL(self.context, self.request) + '/edit.html'

    @property
    def edit_children_url(self):
        return absoluteURL(self.context, self.request) + '/edit_children.html'

    @property
    def parents(self):
        parents = sorted(LayerLink.query(child=self.context), key=lambda l: l.__name__)
        return parents

    @property
    def children(self):
        children = sorted(LayerLink.query(parent=self.context), key=lambda l: l.__name__)
        return children

    @property
    def done_link(self):
        app = ISchoolToolApplication(None)
        return '%s/layers' % absoluteURL(app, self.request)


class LayerEditView(flourish.form.Form, z3c.form.form.EditForm):
    fields = z3c.form.field.Fields(ILayer)
    fields = fields.select('title')

    legend = _('Layer')

    @z3c.form.button.buttonAndHandler(_('Submit'), name='apply')
    def handleApply(self, action):
        super(LayerEditView, self).handleApply.func(self, action)
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            self.request.response.redirect(self.nextURL())

    @z3c.form.button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        self.request.response.redirect(self.nextURL())

    def updateActions(self):
        super(LayerEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def nextURL(self):
        return absoluteURL(self.context, self.request)


class LayersTable(table.ajax.Table):

    def columns(self):
        default = table.ajax.Table.columns(self)
        def get_parents(layer):
            return sorted(LayerLink.query(child=layer),
                          key=lambda l: l.__name__)
        def get_children(layer):
            return sorted(LayerLink.query(parent=layer),
                          key=lambda l: l.__name__)

        parents = zc.table.column.GetterColumn(
            name='parents',
            title=_(u'Parents'),
            getter=lambda i, f: u', '.join([l.title for l in get_parents(i)])
            )
        children = zc.table.column.GetterColumn(
            name='children',
            title=_(u'Children'),
            getter=lambda i, f: u', '.join([l.title for l in get_children(i)])
            )
        return default + [parents, children]

    def updateFormatter(self):
        if self._table_formatter is None:
            self.setUp(table_formatter=self.table_formatter,
                       batch_size=self.batch_size,
                       prefix=self.__name__,
                       css_classes={'table': 'data'})


class LayerContainerSourceMixin(object):

    @property
    def layers(self):
        layer = self.context
        return ILayerContainer(layer.__parent__)

    @property
    def source(self):
        return self.layers


class AvailableChildLayersTable(LayerContainerSourceMixin,
                                RelationshipAddTableMixin,
                                LayersTable):
    pass


class RemoveChildLayersTable(LayerContainerSourceMixin,
                             RelationshipRemoveTableMixin,
                             LayersTable):
    pass


class EditChildLayersView(EditRelationships):
    current_title = _("Current child layers")
    available_title = _("Available child layers")

    def getCollection(self):
        return self.context.children

    def getAvailableItemsContainer(self):
        layer = self.context
        return ILayerContainer(layer.__parent__)

    def getAvailableItems(self):
        """Return a sequence of items that can be selected."""
        container = self.getAvailableItemsContainer()
        selected_items = set(self.getSelectedItems())
        return [p for p in container.values()
                if p not in selected_items]


class NodeContainerAbsoluteURLAdapter(BrowserView):
    adapts(INodeContainer, IBrowserRequest)
    implements(IAbsoluteURL)

    def __str__(self):
        app = ISchoolToolApplication(None)
        url = absoluteURL(app, self.request)
        return url + '/nodes'

    __call__ = __str__


class NodesView(flourish.page.Page):

    content_template = InlineViewPageTemplate('''
      <div tal:content="structure context/schooltool:content/ajax/view/container/table" />
      <h3 tal:condition="python: not len(context)" i18n:domain="schooltool">There are no nodes.</h3>
    ''')

    @Lazy
    def container(self):
        return INodeContainer(ISchoolToolApplication(None))


class NodesAddLinks(flourish.page.RefineLinksViewlet):
    """Manager for Add links in NodesView"""


class FlourishNodeAddView(flourish.form.AddForm):

    template = InheritTemplate(flourish.page.Page.template)
    label = None
    legend = _('Node Information')
    fields = z3c.form.field.Fields(INode).select('title', 'description',
                                                 'label')

    def updateActions(self):
        super(FlourishNodeAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def updateWidgets(self):
        super(FlourishNodeAddView, self).updateWidgets()
        self.widgets['label'].maxlength = 7

    @z3c.form.button.buttonAndHandler(_('Submit'), name='add')
    def handleAdd(self, action):
        super(FlourishNodeAddView, self).handleAdd.func(self, action)

    @z3c.form.button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        if 'camefrom' in self.request:
            url = self.request['camefrom']
            self.request.response.redirect(url)
            return
        app = ISchoolToolApplication(None)
        url = '%s/nodes' % absoluteURL(app, self.request)
        self.request.response.redirect(url)

    def create(self, data):
        if data['description'] is None:
            data['description'] = u''
        node = Node(data['title'])
        z3c.form.form.applyChanges(self, node, data)
        return node

    def add(self, node):
        chooser = INameChooser(self.context)
        name = chooser.chooseName(u'', node)
        self.context[name] = node
        self._node = node
        return node

    def nextURL(self):
        return absoluteURL(self._node, self.request)


class NodeView(flourish.form.DisplayForm):

    template = InheritTemplate(flourish.page.Page.template)

    label = None
    legend = _('Node')

    fields = z3c.form.field.Fields(INode)
    fields = fields.select('title', 'description', 'label')

    @property
    def can_edit(self):
        return flourish.canEdit(self.context)

    @property
    def parents(self):
        parents = sorted(NodeLink.query(child=self.context), key=lambda l: l.__name__)
        return parents

    @property
    def children(self):
        children = sorted(NodeLink.query(parent=self.context), key=lambda l: l.__name__)
        return children

    @property
    def done_link(self):
        app = ISchoolToolApplication(None)
        return '%s/nodes' % absoluteURL(app, self.request)


class NodeEditView(flourish.form.Form, z3c.form.form.EditForm):
    fields = z3c.form.field.Fields(INode)
    fields = fields.select('title', 'description', 'label')

    legend = _('Node')

    def applyChanges(self, data):
        if data['description'] is None:
            data['description'] = u''
        if data['label'] is None:
            data['label'] = u''
        super(NodeEditView, self).applyChanges(data)

    @z3c.form.button.buttonAndHandler(_('Submit'), name='apply')
    def handleApply(self, action):
        super(NodeEditView, self).handleApply.func(self, action)
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            url = absoluteURL(self.context, self.request)
            self.request.response.redirect(url)

    @z3c.form.button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def updateActions(self):
        super(NodeEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def updateWidgets(self):
        super(NodeEditView, self).updateWidgets()
        self.widgets['label'].maxlength = 7


class NodesTable(table.ajax.Table):

    def columns(self):
        def get_parents(node):
            return sorted(NodeLink.query(child=node),
                          key=lambda n: n.__name__)

        label = zc.table.column.GetterColumn(
            name='label',
            title=_(u"Label"),
            getter=lambda i, f: i.label
            )
        title = zc.table.column.GetterColumn(
            name='title',
            title=_(u"Title"),
            cell_formatter=table.ajax.url_cell_formatter,
            getter=lambda i, f: i.title,
            subsort=True)
        directlyProvides(title, ISortableColumn)
        layers = zc.table.column.GetterColumn(
            name='layers',
            title=_(u'Layers'),
            getter=lambda i, f: u', '.join([l.title for l in i.layers])
            )
        return [label, title, layers]

    def updateFormatter(self):
        if self._table_formatter is None:
            self.setUp(table_formatter=self.table_formatter,
                       batch_size=self.batch_size,
                       prefix=self.__name__,
                       css_classes={'table': 'data'})


class NodesTableFilter(table.ajax.TableFilter):

    search_title = _("ID, title, label or description")
    template = ViewPageTemplateFile('templates/nodes_table_filter.pt')

    @property
    def search_id(self):
        return self.manager.html_id+'-search'

    @property
    def search_title_id(self):
        return self.manager.html_id+'-title'

    @property
    def search_layer_ids(self):
        return self.manager.html_id+"-layers"

    def layerContainer(self):
        app = ISchoolToolApplication(None)
        return ILayerContainer(app)

    def layers(self):
        result = []
        container = self.layerContainer()
        collator = ICollator(self.request.locale)
        items = sorted(container.items(),
                       key=lambda (lid, layer): layer.title,
                       cmp=collator.cmp)
        for id, layer in items:
            checked = not self.manager.fromPublication
            if self.search_layer_ids in self.request:
                layer_ids = self.request[self.search_layer_ids]
                if not isinstance(layer_ids, list):
                    layer_ids = [layer_ids]
                checked = id in layer_ids
            result.append({'id': id,
                           'title': layer.title,
                           'checked': checked})
        return result


    def filter(self, items):
        if self.ignoreRequest:
            return items
        if self.search_layer_ids in self.request:
            layer_ids = self.request[self.search_layer_ids]
            if not isinstance(layer_ids, list):
                layer_ids = [layer_ids]
            layers = set()
            for layer_id in layer_ids:
                layer = self.layerContainer().get(layer_id)
                if layer is not None:
                    layers.add(layer)
            if layers:
                items = [item for item in items
                         if set(list(item.layers)).intersection(layers)]
        else:
            return []
        if self.search_title_id in self.request:
            searchstr = self.request[self.search_title_id].lower()
            items = [item for item in items
                     if searchstr in item.__name__.lower() or
                     searchstr in item.title.lower() or
                     searchstr in getattr(item, 'label', '').lower() or
                     searchstr in getattr(item, 'description', '').lower()]
        return items


class NodeContainerSourceMixin(object):

    @property
    def nodes(self):
        node = self.context
        return INodeContainer(node.__parent__)

    @property
    def source(self):
        return self.nodes


class AvailableChildNodesTable(NodeContainerSourceMixin,
                               RelationshipAddTableMixin,
                               NodesTable):
    pass


class RemoveChildNodesTable(NodeContainerSourceMixin,
                            RelationshipRemoveTableMixin,
                            NodesTable):
    pass


class EditChildNodesView(EditRelationships):
    current_title = _("Current child nodes")
    available_title = _("Available child nodes")

    def getCollection(self):
        return self.context.children

    def getAvailableItemsContainer(self):
        node = self.context
        return INodeContainer(node.__parent__)

    def getAvailableItems(self):
        """Return a sequence of items that can be selected."""
        container = self.getAvailableItemsContainer()
        selected_items = set(self.getSelectedItems())
        return [p for p in container.values()
                if p not in selected_items]


class LayerContainerSourceMixin(object):

    @property
    def source(self):
        return ILayerContainer(ISchoolToolApplication(None))


class AvailableNodeLayersTable(LayerContainerSourceMixin,
                               RelationshipAddTableMixin,
                               LayersTable):
    pass


class RemoveNodeLayersTable(LayerContainerSourceMixin,
                            RelationshipRemoveTableMixin,
                            LayersTable):
    pass


class EditNodeLayersView(EditRelationships):
    current_title = _("Current node layers")
    available_title = _("Available node layers")

    def getCollection(self):
        return self.context.layers

    def getAvailableItemsContainer(self):
        return ILayerContainer(ISchoolToolApplication(None))

    def getAvailableItems(self):
        """Return a sequence of items that can be selected."""
        container = self.getAvailableItemsContainer()
        selected_items = set(self.getSelectedItems())
        return [p for p in container.values()
                if p not in selected_items]


class SkillSetContainerSourceMixin(object):

    @property
    def source(self):
        return ISkillSetContainer(ISchoolToolApplication(None))


class AvailableNodeSkillSetsTable(SkillSetContainerSourceMixin,
                                  RelationshipAddTableMixin,
                                  SkillSetTable):
    pass


class RemoveNodeSkillSetsTable(SkillSetContainerSourceMixin,
                               RelationshipRemoveTableMixin,
                               SkillSetTable):
    pass


class EditNodeSkillSetsView(EditRelationships):
    current_title = _("Current node skillsets")
    available_title = _("Available node skillsets")

    def getCollection(self):
        return self.context.skillsets

    def getAvailableItemsContainer(self):
        return ISkillSetContainer(ISchoolToolApplication(None))

    def getAvailableItems(self):
        """Return a sequence of items that can be selected."""
        container = self.getAvailableItemsContainer()
        selected_items = set(self.getSelectedItems())
        return [p for p in container.values()
                if p not in selected_items]

