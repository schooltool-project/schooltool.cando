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
from zope.interface import implements
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

from schooltool.cando.browser.skill import SkillAddView, SkillView
from schooltool.cando.browser.skill import SkillEditView
from schooltool.cando.interfaces import ILayerContainer, ILayer
from schooltool.cando.interfaces import INodeContainer, INode
from schooltool.cando.interfaces import IDocumentContainer, IDocument
from schooltool.cando.interfaces import ISkillSetContainer
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

    def get_document(self):
        return self.context

    def get_children(self):
        return sorted(NodeLink.query(parent=self.context),
                      key=lambda l: l.__name__)

    @property
    def layer_heirarchy(self):
        document = self.get_document()
        if document is None:
            return []
        return document.getOrderedHierarchy()

    @property
    def layer_title(self):
        heirarchy = self.layer_heirarchy
        if not heirarchy:
            return _('SkillSet')
        return heirarchy[0].title

    @property
    def legend(self):
        return _('${layer} list',
                 mapping={'layer': self.layer_title})

    @property
    def query_string(self):
        query_string_dict = {}
        document = self.get_document()
        if document is not None:
            query_string_dict['document'] = document.__name__
        heirarchy = self.layer_heirarchy
        if heirarchy:
            query_string_dict['layer'] = heirarchy[0].__name__

        query_string = ''
        for index, (k, v) in enumerate(query_string_dict.items()):
            query_string += index and '&' or '?'
            query_string += '%s=%s' % (k, v)
        return query_string

    def make_item(self, obj):
        return {
            'url': '%s/document.html' % absoluteURL(obj, self.request),
            'obj': obj,
            }

    @property
    def items(self):
        result = []
        if len(self.layer_heirarchy) < 3:
            for skillset in self.context.skillsets:
                result.append(self.make_item(skillset))
        else:
            for node in self.get_children():
                result.append(self.make_item(node))
        return result


class DocumentNodeMixin(DocumentMixin):

    def get_document(self):
        document_id = self.request.get('document', '')
        app = ISchoolToolApplication(None)
        return IDocumentContainer(app).get(document_id, None)


class DocumentAddLinks(flourish.page.RefineLinksViewlet):
    """Manager for Add links in DocumentView"""


class DocumentAddNodeLink(flourish.page.LinkViewlet, DocumentMixin):

    @property
    def title(self):
        return self.layer_title

    @property
    def url(self):
        if len(self.layer_heirarchy) < 3:
            url = 'add_document_skillset.html'
        else:
            url = 'add_document_node.html'
        return '%s%s' % (url, self.query_string)


class DocumentView(flourish.form.DisplayForm, DocumentMixin):

    template = InheritTemplate(flourish.page.Page.template)
    label = None

    fields = z3c.form.field.Fields(IDocument).select('title', 'description')

    @property
    def can_edit(self):
        return flourish.canEdit(self.context)

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


class DocumentNodeView(flourish.page.Page, DocumentNodeMixin):
    """Same as DocumentView but for a particular node"""

    @property
    def title(self):
        return self.context.title

    @property
    def legend(self):
        layer = self.add_layer
        if layer is None:
            return _('Skill list')
        return _('${layer} list',
                 mapping={'layer': layer.title})

    @property
    def rows(self):
        rows = []
        for attr in ['title', 'description']:
            rows.append({
                'label': INode[attr].title,
                'value': getattr(self.context, attr),
                })
        return rows

    @property
    def done_link(self):
        parents = list(self.context.parents)
        if parents:
            parent = parents[0]
            return '%s/document.html' % absoluteURL(parent, self.request)
        else:
            app = ISchoolToolApplication(None)
            return '%s/document.html' % absoluteURL(app, self.request)


class DocumentNodeAddLinks(flourish.page.RefineLinksViewlet):
    """Manager for Add links in DocumentView"""


class DocumentNodeAddNodeLink(flourish.page.LinkViewlet, DocumentNodeMixin):

    @property
    def title(self):
        layer = self.add_layer
        if layer is None:
            return 'Skill'
        return layer.title

    @property
    def url(self):
        if self.add_layer is None:
            return 'add_document_skill.html'
        return 'add_document_node.html'


class DocumentAddNodeBase(flourish.form.AddForm):

    template = InheritTemplate(flourish.page.Page.template)
    label = None
    fields = z3c.form.field.Fields(INode).select('title', 'description')

    @property
    def subtitle(self):
        layer = self.add_layer
        if layer is None:
            return ''
        return _('Add ${layer}',
                 mapping={'layer': layer.title})

    @property
    def legend(self):
        layer = self.add_layer
        if layer is None:
            return ''
        return _('${layer} Information',
                 mapping={'layer': layer.title})

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
        context = self.node_context
        if context is not None:
            node.parents.add(removeSecurityProxy(context))
        layer = self.add_layer
        if layer is not None:
            node.layers.add(removeSecurityProxy(layer))
        return node

    def add(self, node):
        nodes = INodeContainer(ISchoolToolApplication(None))
        chooser = INameChooser(nodes)
        name = chooser.chooseName(u'', node)
        nodes[name] = node
        return node

    def nextURL(self):
        return absoluteURL(self.context, self.request) + '/document.html'


class DocumentAddNodeView(DocumentAddNodeBase, DocumentMixin):
    """Add Node from DocumentView"""

    @property
    def title(self):
        return _('Skills Document')


class DocumentNodeAddNodeView(DocumentAddNodeBase, DocumentNodeMixin):
    """Add Node from DocumentNodeView"""

    @property
    def title(self):
        return self.context.title


class DocumentNodeEditView(flourish.form.Form, z3c.form.form.EditForm):
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


class DocumentNodeAddSkillView(SkillAddView):

    def create(self, data):
        skill = Skill(data['title'])
        z3c.form.form.applyChanges(self, skill, data)
        self._skill = skill
        return skill

    def add(self, skill):
        skillsets = list(self.context.skillsets)
        if skillsets:
            skillset = skillsets[0]
        else:
            skillset = SkillSet(self.context.title)
            skillsets = ISkillSetContainer(ISchoolToolApplication(None))
            chooser = INameChooser(skillsets)
            name = unicode(skillset.title).encode('punycode')
            name = name[:8]+str(len(skillsets)+1)
            name = chooser.chooseName(name, skillset)
            skillsets[name] = skillset
            removeSecurityProxy(self.context.skillsets).add(
                removeSecurityProxy(skillset))

        if not skill.label:
            skill.label = u'%02d' % (len(skillset) + 1)
        chooser = INameChooser(skillset)
        if skill.external_id:
            name = skill.external_id
        else:
            name = unicode(skill.title).encode('punycode')
            name = name[:8]+str(len(skillsets)+1)
        name = chooser.chooseName(name, skill)
        skillset[name] = skill
        return skill

    def nextURL(self):
        url = absoluteURL(self.context, self.request)
        if self.add_next:
            return url + '/add_document_skill.html'
        return url + '/document.html'


class DocumentNodeSkillView(SkillView):

    @property
    def edit_url(self):
        next_url = self.request.get('next_url', '')
        if next_url:
            next_url = '?next_url=' + next_url
        url = absoluteURL(self.context, self.request)
        return '%s/edit_document_skill.html%s' % (url, next_url)

    @property
    def done_url(self):
        next_url = self.request.get('next_url')
        if next_url:
            return next_url + '/document.html'
        return absoluteURL(self.context.__parent__, self.request)


class DocumentNodeSkillEditView(SkillEditView):

    def nextURL(self):
        next_url = self.request.get('next_url', '')
        if next_url:
            next_url = '?next_url=' + next_url
        url = absoluteURL(self.context, self.request)
        return '%s/document_skill.html%s' % (url, next_url)

