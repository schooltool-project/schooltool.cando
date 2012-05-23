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
Document views.
"""

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.cachedescriptors.property import Lazy
from zope.component import adapts, getUtility, getMultiAdapter
from zope.container.interfaces import INameChooser
from zope.interface import implements, directlyProvides
from zope.intid.interfaces import IIntIds
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.security.proxy import removeSecurityProxy
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
from schooltool.common.inlinept import InlineViewPageTemplate, InheritTemplate
from schooltool.schoolyear.interfaces import ISchoolYearContainer

from schooltool.cando.browser.model import LayersTable, LayerView, LayerEditView
from schooltool.cando.browser.model import EditParentLayersView
from schooltool.cando.browser.skill import SkillAddView, SkillView
from schooltool.cando.browser.skill import SkillSetEditView, SkillEditView
from schooltool.cando.interfaces import ILayerContainer, ILayer
from schooltool.cando.interfaces import INodeContainer, INode
from schooltool.cando.interfaces import IDocumentContainer, IDocument
from schooltool.cando.interfaces import ISkillSetContainer, ISkillSet
from schooltool.cando.model import Layer, LayerLink
from schooltool.cando.model import Node, NodeLink
from schooltool.cando.model import Document
from schooltool.cando.skill import SkillSet, Skill

from schooltool.cando import CanDoMessage as _



class DocumentContainerAbsoluteURLAdapter(BrowserView):
    adapts(IDocumentContainer, IBrowserRequest)
    implements(IAbsoluteURL)

    def __str__(self):
        app = ISchoolToolApplication(None)
        url = absoluteURL(app, self.request)
        return url + '/documents'

    __call__ = __str__


class DocumentsView(flourish.page.Page):

    content_template = InlineViewPageTemplate('''
      <div tal:content="structure context/schooltool:content/ajax/view/container/table" />
    ''')

    @Lazy
    def container(self):
        return IDocumentContainer(ISchoolToolApplication(None))


class DocumentsTable(table.ajax.Table):

    def columns(self):
        default = table.ajax.Table.columns(self)
        return default

    def updateFormatter(self):
        if self._table_formatter is None:
            self.setUp(table_formatter=self.table_formatter,
                       batch_size=self.batch_size,
                       prefix=self.__name__,
                       css_classes={'table': 'data'})


class DocumentsAddLinks(flourish.page.RefineLinksViewlet):
    """Manager for Add links in DocumentsView"""


class DocumentAddView(flourish.form.AddForm):

    template = InheritTemplate(flourish.page.Page.template)
    label = None
    legend = _('Document Information')
    fields = z3c.form.field.Fields(IDocument).select('title', 'description')

    def updateActions(self):
        super(DocumentAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @z3c.form.button.buttonAndHandler(_('Submit'), name='add')
    def handleAdd(self, action):
        super(DocumentAddView, self).handleAdd.func(self, action)

    @z3c.form.button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        app = ISchoolToolApplication(None)
        url = '%s/documents' % absoluteURL(app, self.request)
        self.request.response.redirect(url)

    def create(self, data):
        document = Document(data['title'])
        z3c.form.form.applyChanges(self, document, data)
        return document

    def add(self, document):
        chooser = INameChooser(self.context)
        name = chooser.chooseName(u'', document)
        self.context[name] = document
        self._document = document
        return document

    def nextURL(self):
        return absoluteURL(self._document, self.request)


class DocumentMixin(object):

    def is_document(self):
        return IDocument(self.context, None) is not None

    def get_document(self):
        return self.context

    def get_node(self):
        return None

    def get_layer_hierarchy(self):
        document = self.get_document()
        if document is None:
            return []
        return document.getOrderedHierarchy()

    def get_layer(self):
        layer_id = self.request.get('layer', '')
        app = ISchoolToolApplication(None)
        return ILayerContainer(app).get(layer_id, None)

    def is_skillset_layer(self):
        return len(self.get_layer_hierarchy()) < 3

    def get_next_layer(self):
        hierarchy = self.get_layer_hierarchy()
        if not hierarchy:
            return None
        return hierarchy[0]

    def get_previous_layer(self):
        return None

    def get_children(self):
        if INode(self.context, None) is not None:
            return sorted(NodeLink.query(parent=self.context),
                          key=lambda l: l.__name__)
        return []

    @property
    def layer_title(self):
        layer = self.get_layer()
        if layer is None:
            return _('SkillSet')
        return layer.title

    @property
    def next_layer_title(self):
        layer = self.get_next_layer()
        if layer is None:
            return _('SkillSet')
        return layer.title

    def build_query_string(self, **kw):
        query_string_dict = {}
        document = self.get_document()
        if document is not None:
            query_string_dict['document'] = document.__name__
        layer = kw.get('layer', None)
        if layer is not None:
            query_string_dict['layer'] = layer.__name__
        node = kw.get('node', None)
        if node is not None:
            query_string_dict['node'] = node.__name__

        query_string = ''
        for index, (k, v) in enumerate(query_string_dict.items()):
            query_string += index and '&' or '?'
            query_string += '%s=%s' % (k, v)
        return query_string

    def make_node_item(self, node):
        query_string = self.build_query_string(layer=self.get_next_layer())
        return {
            'url': '%s/document.html%s' % (absoluteURL(node, self.request),
                                           query_string),
            'obj': node,
            }

    def make_skillset_item(self, skillset):
        query_string = self.build_query_string(layer=self.get_next_layer(),
                                               node=self.get_node())
        return {
            'url': '%s/document.html%s' % (absoluteURL(skillset, self.request),
                                           query_string),
            'obj': skillset,
            }

    @property
    def items(self):
        result = []
        if self.is_skillset_layer():
            for skillset in self.context.skillsets:
                result.append(self.make_skillset_item(skillset))
        else:
            for node in self.get_children():
                result.append(self.make_node_item(node))
        return result

    @property
    def add_url(self):
        if self.is_skillset_layer():
            url = 'add_document_skillset.html'
            query_string = self.build_query_string(layer=self.get_next_layer(),
                                                   node=self.get_node())
        else:
            url = 'add_document_node.html'
            query_string = self.build_query_string(layer=self.get_next_layer())
        return '%s%s' % (url, query_string)


class DocumentNodeMixin(DocumentMixin):

    def get_document(self):
        document_id = self.request.get('document', '')
        app = ISchoolToolApplication(None)
        return IDocumentContainer(app).get(document_id, None)

    def get_node(self):
        if INode(self.context, None) is not None:
            return self.context
        node_id = self.request.get('node', '')
        app = ISchoolToolApplication(None)
        return INodeContainer(app).get(node_id, None)

    def is_skillset_layer(self):
        hierarchy = self.get_layer_hierarchy()
        if len(hierarchy) < 3:
            return True
        current_layer = self.get_next_layer()
        if current_layer is None:
            return True
        for index, layer in enumerate(hierarchy):
            if layer is current_layer and index < len(hierarchy) - 2:
                return False
        return True

    def get_next_layer(self):
        hierarchy = self.get_layer_hierarchy()
        if hierarchy:
            current_layer = self.get_layer()
            if current_layer is None:
                return None
            for index, layer in enumerate(hierarchy):
                if layer is current_layer and index < len(hierarchy) - 1:
                    return hierarchy[index + 1]
        return None

    def get_previous_layer(self):
        hierarchy = self.get_layer_hierarchy()
        if hierarchy:
            current_layer = self.get_layer()
            if current_layer is None:
                return None
            for index, layer in enumerate(hierarchy):
                if layer is current_layer and index > 0:
                    return hierarchy[index - 1]
        return None


class DocumentSkillSetMixin(DocumentNodeMixin):

    @property
    def next_layer_title(self):
        hierarchy = self.get_layer_hierarchy()
        if len(hierarchy) > 1:
            return hierarchy[-1].title
        return _('Skill')


class DocumentSkillMixin(DocumentSkillSetMixin):

    @property
    def layer_title(self):
        layer = self.get_layer()
        if layer is None:
            return _('Skill')
        return layer.title


class DocumentAddLinks(flourish.page.RefineLinksViewlet):
    """Manager for Add links in DocumentView"""


class DocumentAddNodeLink(flourish.page.LinkViewlet, DocumentMixin):

    @property
    def title(self):
        return self.next_layer_title

    @property
    def url(self):
        return self.add_url


class DocumentView(flourish.form.DisplayForm, DocumentMixin):

    template = InheritTemplate(flourish.page.Page.template)
    label = None

    fields = z3c.form.field.Fields(IDocument).select('title', 'description')

    @property
    def legend(self):
        return _('${layer} list',
                 mapping={'layer': self.next_layer_title})

    @property
    def can_edit(self):
        return flourish.canEdit(self.context)

    @property
    def edit_url(self):
        return absoluteURL(self.context, self.request) + '/edit.html'

    @property
    def done_link(self):
        app = ISchoolToolApplication(None)
        return '%s/documents' % absoluteURL(app, self.request)


class DocumentEditView(flourish.form.Form, z3c.form.form.EditForm):
    fields = z3c.form.field.Fields(IDocument)
    fields = fields.select('title', 'description')

    legend = _('Document')

    def applyChanges(self, data):
        if data['description'] is None:
            data['description'] = u''
        super(DocumentEditView, self).applyChanges(data)

    @z3c.form.button.buttonAndHandler(_('Submit'), name='apply')
    def handleApply(self, action):
        super(DocumentEditView, self).handleApply.func(self, action)
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            url = absoluteURL(self.context, self.request)
            self.request.response.redirect(url)

    @z3c.form.button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def updateActions(self):
        super(DocumentEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')


class EditDocumentHierarchyView(EditRelationships):
    current_title = _("Current document hierarchy layers")
    available_title = _("Available layers")

    def getCollection(self):
        return self.context.hierarchy

    def getAvailableItemsContainer(self):
        return ILayerContainer(ISchoolToolApplication(None))

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


class AvailableLayersTable(LayerContainerSourceMixin,
                           RelationshipAddTableMixin,
                           LayersTable):
    pass


class RemoveLayersTable(LayerContainerSourceMixin,
                        RelationshipRemoveTableMixin,
                        LayersTable):
    pass


class DocumentLayerView(LayerView, DocumentNodeMixin):

    @property
    def edit_url(self):
        url = absoluteURL(self.context, self.request)
        query_string = self.build_query_string()
        return '%s/edit_document_layer.html%s' % (url, query_string)

    @property
    def edit_parents_url(self):
        url = absoluteURL(self.context, self.request)
        query_string = self.build_query_string()
        return '%s/edit_document_layer_parents.html%s' % (url, query_string)

    @property
    def done_link(self):
        document = self.get_document()
        if document is None:
            app = ISchoolToolApplication(None)
            return '%s/documents' % absoluteURL(app, self.request)
        return absoluteURL(document, self.request)


class DocumentLayerEditView(LayerEditView, DocumentNodeMixin):

    def nextURL(self):
        url = absoluteURL(self.context, self.request)
        query_string = self.build_query_string()
        return '%s/document.html%s' % (url, query_string)


class EditDocumntLayerParentsView(EditParentLayersView, DocumentNodeMixin):

    def nextURL(self):
        url = absoluteURL(self.context, self.request)
        query_string = self.build_query_string()
        return '%s/document.html%s' % (url, query_string)


class DocumentNodeView(flourish.form.DisplayForm, DocumentNodeMixin):
    """Same as DocumentView but for a particular node"""

    template = InheritTemplate(flourish.page.Page.template)
    label = None

    fields = z3c.form.field.Fields(INode).select('title', 'description')

    @property
    def subtitle(self):
        return _('View ${layer}',
                 mapping={'layer': self.layer_title})

    @property
    def legend(self):
        return _('${layer} list',
                 mapping={'layer': self.next_layer_title})

    @property
    def can_edit(self):
        return flourish.canEdit(self.context)

    @property
    def edit_url(self):
        url = absoluteURL(self.context, self.request)
        query_string = self.build_query_string(layer=self.get_layer())
        return '%s/edit_document_node.html%s' % (url, query_string)

    @property
    def done_link(self):
        document = self.get_document()
        if document is None:
            app = ISchoolToolApplication(None)
            return '%s/documents' % absoluteURL(app, self.request)
        layer = self.get_previous_layer()
        if layer is not None:
            for parent in self.context.parents:
                if layer in parent.layers:
                    url = absoluteURL(parent, self.request)
                    query_string = self.build_query_string(layer=layer)
                    return '%s/document.html%s' % (url, query_string)
        return absoluteURL(document, self.request)


class DocumentNodeAddLinks(flourish.page.RefineLinksViewlet):
    """Manager for Add links in DocumentView"""


class DocumentNodeAddNodeLink(flourish.page.LinkViewlet, DocumentNodeMixin):

    @property
    def title(self):
        return self.next_layer_title

    @property
    def url(self):
        return self.add_url


class DocumentAddNodeBase(flourish.form.AddForm):

    template = InheritTemplate(flourish.page.Page.template)
    label = None
    fields = z3c.form.field.Fields(INode).select('title', 'description')

    @property
    def subtitle(self):
        return _('Add ${layer}',
                 mapping={'layer': self.layer_title})

    @property
    def legend(self):
        return _('${layer} Information',
                 mapping={'layer': self.layer_title})

    def updateActions(self):
        super(DocumentAddNodeBase, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @z3c.form.button.buttonAndHandler(_('Submit'), name='add')
    def handleAdd(self, action):
        super(DocumentAddNodeBase, self).handleAdd.func(self, action)

    @z3c.form.button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        self.request.response.redirect(self.nextURL())

    def create(self, data):
        if data['description'] is None:
            data['description'] = u''
        node = Node(data['title'])
        z3c.form.form.applyChanges(self, node, data)
        node.parents.add(removeSecurityProxy(self.context))
        layer = self.get_layer()
        if layer is not None:
            node.layers.add(removeSecurityProxy(layer))
        return node

    def add(self, node):
        nodes = INodeContainer(ISchoolToolApplication(None))
        chooser = INameChooser(nodes)
        name = chooser.chooseName(u'', node)
        nodes[name] = node
        return node


class DocumentAddNodeView(DocumentAddNodeBase, DocumentMixin):
    """Add Node from DocumentView"""

    @property
    def title(self):
        return _('Skills Document')

    def nextURL(self):
        return absoluteURL(self.context, self.request)


class DocumentNodeAddNodeView(DocumentAddNodeBase, DocumentNodeMixin):
    """Add Node from DocumentNodeView"""

    @property
    def title(self):
        return self.context.title

    def nextURL(self):
        return absoluteURL(self.context, self.request) + '/document.html'


class DocumentNodeEditView(flourish.form.Form, z3c.form.form.EditForm,
                           DocumentNodeMixin):
    fields = z3c.form.field.Fields(INode)
    fields = fields.select('title', 'description')

    legend = _('Change information')

    def applyChanges(self, data):
        if data['description'] is None:
            data['description'] = u''
        super(DocumentNodeEditView, self).applyChanges(data)

    @z3c.form.button.buttonAndHandler(_('Submit'), name='apply')
    def handleApply(self, action):
        super(DocumentNodeEditView, self).handleApply.func(self, action)
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            self.request.response.redirect(self.nextURL())

    @z3c.form.button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        self.request.response.redirect(self.nextURL())

    def updateActions(self):
        super(DocumentNodeEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def nextURL(self):
        return absoluteURL(self.context, self.request) + '/document.html'

    def nextURL(self):
        url = absoluteURL(self.context, self.request)
        query_string = self.build_query_string(layer=self.get_layer())
        return '%s/document.html%s' % (url, query_string)


class DocumentAddSkillSetBase(flourish.form.AddForm):

    _skillset = None
    label = None
    fields = z3c.form.field.Fields(ISkillSet)
    fields = fields.select('title', 'label', 'external_id')

    @property
    def legend(self):
        return self.layer_title

    @property
    def subtitle(self):
        return _('Add ${layer}',
                 mapping={'layer': self.layer_title})

    def updateActions(self):
        super(DocumentAddSkillSetBase, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def create(self, data):
        if not data['label']:
            title = unicode(data['title'])
            if len(title) < 10:
                data['label'] = title
            else:
                data['label'] = title[:7]+'...'
        skillset = SkillSet(data['title'])
        z3c.form.form.applyChanges(self, skillset, data)
        self._skillset = skillset
        return skillset

    def add(self, skillset):
        skillsets = ISkillSetContainer(ISchoolToolApplication(None))
        chooser = INameChooser(skillsets)
        name = unicode(skillset.title).encode('punycode')
        name = name[:8]+str(len(skillsets)+1)
        name = chooser.chooseName(name, skillset)
        skillsets[name] = skillset
        removeSecurityProxy(self.context.skillsets).add(
            removeSecurityProxy(skillset))
        return skillset

    def nextURL(self):
        if self._skillset is not None:
            url = absoluteURL(self._skillset, self.request) + '/document.html'
            layer = self.get_layer()
        else:
            url = self.contextURL()
            layer = self.get_previous_layer()
        query_string = self.build_query_string(layer=layer,
                                               node=self.get_node())
        return '%s%s' % (url, query_string)


class DocumentAddSkillSetView(DocumentAddSkillSetBase, DocumentMixin):
    """Add SkillSet from DocumentView"""

    def contextURL(self):
        return absoluteURL(self.context, self.request)


class DocumentNodeAddSkillSetView(DocumentAddSkillSetBase, DocumentNodeMixin):
    """Add SkillSet from DocumentNodeView"""

    def contextURL(self):
        return absoluteURL(self.context, self.request) + '/document.html'


class DocumentSkillSetView(flourish.form.DisplayForm, DocumentSkillSetMixin):
    template = InheritTemplate(flourish.page.Page.template)
    fields = z3c.form.field.Fields(ISkillSet)
    fields = fields.select('label', 'external_id')

    @property
    def subtitle(self):
        return _('View ${layer}',
                 mapping={'layer': self.layer_title})

    @property
    def legend(self):
        layer = self.get_next_layer()
        if layer is None:
            return _('Skills')
        return _('${layer} list',
                 mapping={'layer': layer.title})

    @property
    def can_edit(self):
        return flourish.canEdit(self.context)

    @property
    def edit_url(self):
        url = absoluteURL(self.context, self.request)
        query_string = self.build_query_string(layer=self.get_layer(),
                                               node=self.get_node())
        return '%s/edit_document_skillset.html%s' % (url, query_string)

    @property
    def done_link(self):
        app = ISchoolToolApplication(None)
        document = self.get_document()
        if document is None:
            return '%s/skills' % absoluteURL(app, self.request)
        node_id = self.request.get('node', '')
        node = INodeContainer(app).get(node_id, None)
        if node is not None:
            previous_layer = self.get_previous_layer()
            query_string = self.build_query_string(layer=previous_layer)
            return '%s/document.html%s' % (absoluteURL(node, self.request),
                                           query_string)
        else:
            return '%s/index.html' % absoluteURL(document, self.request)


class DocumentSkillSetSkillTable(table.ajax.Table, DocumentSkillSetMixin):

    def updateFormatter(self):
        if self._table_formatter is None:
            self.setUp(table_formatter=self.table_formatter,
                       batch_size=self.batch_size,
                       prefix=self.__name__,
                       css_classes={'table': 'data'})

    def sortOn(self):
        return (("required", True), ("title", False))

    def title_url_formatter(self, value, item, formatter):
        query_string = self.build_query_string(layer=self.get_next_layer(),
                                               node=self.get_node())
        url = '%s/document.html%s' % (absoluteURL(item, formatter.request),
                                      query_string)
        return '<a href="%s">%s</a>' % (url, value)

    def columns(self):
        title = zc.table.column.GetterColumn(
            name='title',
            title=_(u"Title"),
            cell_formatter=lambda v, i, f: self.title_url_formatter(v, i, f),
            getter=lambda i, f: i.title)
        directlyProvides(title, zc.table.interfaces.ISortableColumn)
        required = zc.table.column.GetterColumn(
            name='required',
            title=_(u'Required'),
            getter=lambda i, f: i.required and _('required') or _('optional'))
        directlyProvides(required, zc.table.interfaces.ISortableColumn)
        label = zc.table.column.GetterColumn(
            name='label',
            title=_(u'Label'),
            getter=lambda i, f: i.label or '')
        return [required, label, title]


class DocumentSkillSetEditView(SkillSetEditView, DocumentSkillSetMixin):

    def nextURL(self):
        url = absoluteURL(self.context, self.request)
        query_string = self.build_query_string(layer=self.get_layer(),
                                               node=self.get_node())
        return '%s/document.html%s' % (url, query_string)


class DocumentSkillSetLinks(flourish.page.RefineLinksViewlet):
    pass


class DocumentAddSkillLink(flourish.page.LinkViewlet, DocumentSkillSetMixin):

    @property
    def title(self):
        return self.next_layer_title

    @property
    def url(self):
        url = 'add_document_skill.html'
        query_string = self.build_query_string(layer=self.get_next_layer(),
                                               node=self.get_node())
        return '%s%s' % (url, query_string)


class DocumentAddSkillView(SkillAddView, DocumentSkillSetMixin):

    @property
    def legend(self):
        return _('${layer} Information',
                 mapping={'layer': self.next_layer_title})

    @property
    def subtitle(self):
        return _('Add ${layer}',
                 mapping={'layer': self.next_layer_title})

    def create(self, data):
        skill = Skill(data['title'])
        z3c.form.form.applyChanges(self, skill, data)
        self._skill = skill
        return skill

    def add(self, skill):
        skillset = self.context
        if not skill.label:
            skill.label = u'%02d' % (len(skillset) + 1)
        chooser = INameChooser(skillset)
        if skill.external_id:
            name = skill.external_id
        else:
            name = unicode(skill.title).encode('punycode')
            name = name[:8]+str(len(skillset)+1)
        name = chooser.chooseName(name, skill)
        skillset[name] = skill
        return skill

    def nextURL(self):
        url = absoluteURL(self.context, self.request)
        if self.add_next:
            query_string = self.build_query_string(layer=self.get_layer(),
                                                   node=self.get_node())
            return '%s/add_document_skill.html%s' % (url, query_string)
        else:
            previous_layer = self.get_previous_layer()
            query_string = self.build_query_string(layer=previous_layer,
                                                   node=self.get_node())
            return '%s/document.html%s' % (url, query_string)


class DocumentSkillView(SkillView, DocumentSkillMixin):

    @property
    def subtitle(self):
        return _('View ${layer}',
                 mapping={'layer': self.layer_title})

    @property
    def can_edit(self):
        return flourish.canEdit(self.context)

    @property
    def edit_url(self):
        url = absoluteURL(self.context, self.request)
        query_string = self.build_query_string(layer=self.get_layer(),
                                               node=self.get_node())
        return '%s/edit_document_skill.html%s' % (url, query_string)

    @property
    def done_link(self):
        url = absoluteURL(self.context.__parent__, self.request)
        query_string = self.build_query_string(layer=self.get_previous_layer(),
                                               node=self.get_node())
        return '%s/document.html%s' % (url, query_string)


class DocumentSkillEditView(SkillEditView, DocumentSkillMixin):

    def nextURL(self):
        url = absoluteURL(self.context, self.request)
        query_string = self.build_query_string(layer=self.get_layer(),
                                               node=self.get_node())
        return '%s/document.html%s' % (url, query_string)

