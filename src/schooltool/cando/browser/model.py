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
from zope.interface import implements
from zope.intid.interfaces import IIntIds
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.traversing.browser.interfaces import IAbsoluteURL

import zc.table.column
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
from schooltool.cando.interfaces import ILayerContainer, ILayer
from schooltool.cando.interfaces import INodeContainer, INode
from schooltool.cando.model import Layer, LayerLink
from schooltool.cando.model import Node, NodeLink
from schooltool.common.inlinept import InlineViewPageTemplate, InheritTemplate
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.schoolyear.interfaces import ISchoolYear

from schooltool.cando import CanDoMessage as _



class LayerContainerAbsoluteURLAdapter(BrowserView):
    adapts(ILayerContainer, IBrowserRequest)
    implements(IAbsoluteURL)

    def __str__(self):
        container_id = int(self.context.__name__)
        int_ids = getUtility(IIntIds)
        container = int_ids.getObject(container_id)
        url = str(getMultiAdapter((container, self.request), name='absolute_url'))
        return url + '/layers'

    __call__ = __str__


class LayersActiveTabMixin(object):

    @property
    def schoolyear(self):
        schoolyears = ISchoolYearContainer(self.context)
        result = schoolyears.getActiveSchoolYear()
        if 'schoolyear_id' in self.request:
            schoolyear_id = self.request['schoolyear_id']
            result = schoolyears.get(schoolyear_id, result)
        return result


class LayerContainerTitle(ContentTitle):

    @property
    def title(self):
        schoolyear = ISchoolYear(self.context)
        return _('Layers for ${schoolyear}',
                 mapping={'schoolyear': schoolyear.title})


class LayersView(flourish.page.Page, LayersActiveTabMixin):

    content_template = InlineViewPageTemplate('''
      <div tal:content="structure context/schooltool:content/ajax/view/container/table" />
    ''')

    @property
    def title(self):
        schoolyear = self.schoolyear
        return _('Layers for ${schoolyear}',
                 mapping={'schoolyear': schoolyear.title})

    @Lazy
    def container(self):
        schoolyear = self.schoolyear
        return ILayerContainer(schoolyear)


class LayersTertiaryNavigationManager(flourish.page.TertiaryNavigationManager):

    template = InlineViewPageTemplate("""
        <ul tal:attributes="class view/list_class">
          <li tal:repeat="item view/items"
              tal:attributes="class item/class"
              tal:content="structure item/viewlet">
          </li>
        </ul>
    """)

    @property
    def items(self):
        result = []
        schoolyears = ISchoolYearContainer(self.context)
        active = schoolyears.getActiveSchoolYear()
        if 'schoolyear_id' in self.request:
            schoolyear_id = self.request['schoolyear_id']
            active = schoolyears.get(schoolyear_id, active)
        for schoolyear in schoolyears.values():
            url = '%s/%s?schoolyear_id=%s' % (
                absoluteURL(self.context, self.request),
                'layers',
                schoolyear.__name__)
            result.append({
                    'class': schoolyear.first == active.first and 'active' or None,
                    'viewlet': u'<a href="%s">%s</a>' % (url, schoolyear.title),
                    })
        return result


class ManageLayersOverview(flourish.page.Content):

    body_template = ViewPageTemplateFile(
        'templates/manage_layers_overview.pt')

    @property
    def schoolyear(self):
        schoolyears = ISchoolYearContainer(self.context)
        result = schoolyears.getActiveSchoolYear()
        if 'schoolyear_id' in self.request:
            schoolyear_id = self.request['schoolyear_id']
            result = schoolyears.get(schoolyear_id, result)
        return result

    @property
    def has_schoolyear(self):
        return self.schoolyear is not None

    @property
    def layers(self):
        return ILayerContainer(self.schoolyear, None)


class LayersAddLinks(flourish.page.RefineLinksViewlet):
    """Manager for Add links in LayersView"""


class LayersSchoolyearLink(flourish.page.LinkViewlet):
    @property
    def url(self):
        link = self.link
        if not link:
            return None
        schoolyear = self.view.schoolyear
        layers = ILayerContainer(schoolyear)
        return "%s/%s" % (absoluteURL(layers, self.request),
                                self.link)


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
        schoolyear = ISchoolYear(self.context)
        url = '%s/%s?schoolyear_id=%s' % (
            absoluteURL(ISchoolToolApplication(None), self.request),
            'layers',
            schoolyear.__name__)
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

    @property
    def title(self):
        schoolyear = ISchoolYear(self.context)
        return _('Layers for ${schoolyear}',
                 mapping={'schoolyear': schoolyear.title})


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
    def parents(self):
        parents = sorted(LayerLink.query(child=self.context), key=lambda l: l.__name__)
        return parents

    @property
    def children(self):
        children = sorted(LayerLink.query(parent=self.context), key=lambda l: l.__name__)
        return children

    @property
    def done_link(self):
        schoolyear = ISchoolYear(self.context.__parent__)
        return '%s/%s?schoolyear_id=%s' % (
            absoluteURL(ISchoolToolApplication(None), self.request),
            'layers',
            schoolyear.__name__)


class LayerEditView(flourish.form.Form, z3c.form.form.EditForm):
    fields = z3c.form.field.Fields(ILayer)
    fields = fields.select('title')

    legend = _('Layer')

    @z3c.form.button.buttonAndHandler(_('Submit'), name='apply')
    def handleApply(self, action):
        super(LayerEditView, self).handleApply.func(self, action)
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            url = absoluteURL(self.context, self.request)
            self.request.response.redirect(url)

    @z3c.form.button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def updateActions(self):
        super(LayerEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')


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


class AvailableParentLayersTable(LayerContainerSourceMixin,
                                 RelationshipAddTableMixin,
                                 LayersTable):
    pass


class RemoveParentLayersTable(LayerContainerSourceMixin,
                              RelationshipRemoveTableMixin,
                              LayersTable):
    pass


class EditParentLayersView(EditRelationships):
    current_title = _("Current parent layers")
    available_title = _("Available parent layers")

    def getCollection(self):
        return self.context.parents

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
        container_id = int(self.context.__name__)
        int_ids = getUtility(IIntIds)
        container = int_ids.getObject(container_id)
        url = str(getMultiAdapter((container, self.request), name='absolute_url'))
        return url + '/nodes'

    __call__ = __str__


class NodesActiveTabMixin(object):

    @property
    def schoolyear(self):
        schoolyears = ISchoolYearContainer(self.context)
        result = schoolyears.getActiveSchoolYear()
        if 'schoolyear_id' in self.request:
            schoolyear_id = self.request['schoolyear_id']
            result = schoolyears.get(schoolyear_id, result)
        return result


class NodeContainerTitle(ContentTitle):

    @property
    def title(self):
        schoolyear = ISchoolYear(self.context)
        return _('Nodes for ${schoolyear}',
                 mapping={'schoolyear': schoolyear.title})


class NodesView(flourish.page.Page, NodesActiveTabMixin):

    content_template = InlineViewPageTemplate('''
      <div tal:content="structure context/schooltool:content/ajax/view/container/table" />
    ''')

    @property
    def title(self):
        schoolyear = self.schoolyear
        return _('Nodes for ${schoolyear}',
                 mapping={'schoolyear': schoolyear.title})

    @Lazy
    def container(self):
        schoolyear = self.schoolyear
        return INodeContainer(schoolyear)


class NodesTertiaryNavigationManager(flourish.page.TertiaryNavigationManager):

    template = InlineViewPageTemplate("""
        <ul tal:attributes="class view/list_class">
          <li tal:repeat="item view/items"
              tal:attributes="class item/class"
              tal:content="structure item/viewlet">
          </li>
        </ul>
    """)

    @property
    def items(self):
        result = []
        schoolyears = ISchoolYearContainer(self.context)
        active = schoolyears.getActiveSchoolYear()
        if 'schoolyear_id' in self.request:
            schoolyear_id = self.request['schoolyear_id']
            active = schoolyears.get(schoolyear_id, active)
        for schoolyear in schoolyears.values():
            url = '%s/%s?schoolyear_id=%s' % (
                absoluteURL(self.context, self.request),
                'nodes',
                schoolyear.__name__)
            result.append({
                    'class': schoolyear.first == active.first and 'active' or None,
                    'viewlet': u'<a href="%s">%s</a>' % (url, schoolyear.title),
                    })
        return result


class ManageNodesOverview(flourish.page.Content):

    body_template = ViewPageTemplateFile(
        'templates/manage_nodes_overview.pt')

    @property
    def schoolyear(self):
        schoolyears = ISchoolYearContainer(self.context)
        result = schoolyears.getActiveSchoolYear()
        if 'schoolyear_id' in self.request:
            schoolyear_id = self.request['schoolyear_id']
            result = schoolyears.get(schoolyear_id, result)
        return result

    @property
    def has_schoolyear(self):
        return self.schoolyear is not None

    @property
    def nodes(self):
        return INodeContainer(self.schoolyear, None)


class NodesAddLinks(flourish.page.RefineLinksViewlet):
    """Manager for Add links in NodesView"""


class NodesSchoolyearLink(flourish.page.LinkViewlet):
    @property
    def url(self):
        link = self.link
        if not link:
            return None
        schoolyear = self.view.schoolyear
        nodes = INodeContainer(schoolyear)
        return "%s/%s" % (absoluteURL(nodes, self.request),
                                self.link)


class FlourishNodeAddView(flourish.form.AddForm):

    template = InheritTemplate(flourish.page.Page.template)
    label = None
    legend = _('Node Information')
    fields = z3c.form.field.Fields(INode).select('title', 'description')

    def updateActions(self):
        super(FlourishNodeAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @z3c.form.button.buttonAndHandler(_('Submit'), name='add')
    def handleAdd(self, action):
        super(FlourishNodeAddView, self).handleAdd.func(self, action)

    @z3c.form.button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        if 'camefrom' in self.request:
            url = self.request['camefrom']
            self.request.response.redirect(url)
            return
        schoolyear = ISchoolYear(self.context)
        url = '%s/%s?schoolyear_id=%s' % (
            absoluteURL(ISchoolToolApplication(None), self.request),
            'nodes',
            schoolyear.__name__)
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

    @property
    def title(self):
        schoolyear = ISchoolYear(self.context)
        return _('Nodes for ${schoolyear}',
                 mapping={'schoolyear': schoolyear.title})


class NodeView(flourish.form.DisplayForm):

    template = InheritTemplate(flourish.page.Page.template)

    label = None
    legend = _('Node')

    fields = z3c.form.field.Fields(INode)
    fields = fields.select('title', 'description')

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
        schoolyear = ISchoolYear(self.context.__parent__)
        return '%s/%s?schoolyear_id=%s' % (
            absoluteURL(ISchoolToolApplication(None), self.request),
            'nodes',
            schoolyear.__name__)


class NodeEditView(flourish.form.Form, z3c.form.form.EditForm):
    fields = z3c.form.field.Fields(INode)
    fields = fields.select('title', 'description')

    legend = _('Node')

    def applyChanges(self, data):
        if data['description'] is None:
            data['description'] = u''
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


class NodesTable(table.ajax.Table):

    def columns(self):
        def get_parents(node):
            return sorted(NodeLink.query(child=node),
                          key=lambda n: n.__name__)
        def get_children(node):
            return sorted(NodeLink.query(parent=node),
                          key=lambda n: n.__name__)

        default = table.ajax.Table.columns(self)
        description = zc.table.column.GetterColumn(
            name='description',
            title=_(u"Description"),
            getter=lambda i, f: i.description
            )
        parents = zc.table.column.GetterColumn(
            name='parents',
            title=_(u'Parents'),
            getter=lambda i, f: u', '.join([n.title for n in get_parents(i)])
            )
        children = zc.table.column.GetterColumn(
            name='children',
            title=_(u'Children'),
            getter=lambda i, f: u', '.join([n.title for n in get_children(i)])
            )
        layers = zc.table.column.GetterColumn(
            name='layers',
            title=_(u'Layers'),
            getter=lambda i, f: u', '.join([l.title for l in i.layers])
            )
        return default + [description, parents, children, layers]

    def updateFormatter(self):
        if self._table_formatter is None:
            self.setUp(table_formatter=self.table_formatter,
                       batch_size=self.batch_size,
                       prefix=self.__name__,
                       css_classes={'table': 'data'})


class NodeContainerSourceMixin(object):

    @property
    def nodes(self):
        node = self.context
        return INodeContainer(node.__parent__)

    @property
    def source(self):
        return self.nodes


class AvailableParentNodesTable(NodeContainerSourceMixin,
                                 RelationshipAddTableMixin,
                                 NodesTable):
    pass


class RemoveParentNodesTable(NodeContainerSourceMixin,
                              RelationshipRemoveTableMixin,
                              NodesTable):
    pass


class EditParentNodesView(EditRelationships):
    current_title = _("Current parent nodes")
    available_title = _("Available parent nodes")

    def getCollection(self):
        return self.context.parents

    def getAvailableItemsContainer(self):
        node = self.context
        return INodeContainer(node.__parent__)

    def getAvailableItems(self):
        """Return a sequence of items that can be selected."""
        container = self.getAvailableItemsContainer()
        selected_items = set(self.getSelectedItems())
        return [p for p in container.values()
                if p not in selected_items]

