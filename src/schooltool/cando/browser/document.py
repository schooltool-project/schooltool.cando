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


class DocumentMixin(object):

    list_class = ''

    @property
    def schoolyear(self):
        app = ISchoolToolApplication(None)
        schoolyears = ISchoolYearContainer(app)
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
        layers = ILayerContainer(self.schoolyear, None)
        if layers is None:
            return []
        return list(layers.values())

    @property
    def nodes(self):
        nodes = INodeContainer(self.schoolyear, None)
        if nodes is None:
            return []
        return list(nodes.values())

    @property
    def layer_heirarchy(self):
        layers = self.layers
        for layer in layers:
            if not len(layer.parents):
                result = [layer]
                break
        else:
            return None
        while True:
            for layer in layers:
                if result[-1] in layer.parents:
                    result.append(layer)
                    break
            else:
                return result

    @property
    def add_layer(self):
        heirarchy = self.layer_heirarchy
        if heirarchy is None:
            return None
        return heirarchy[0]

    def node_item(self, node):
        return {
            'url': '%s/document.html' % absoluteURL(node, self.request),
            'obj': node,
            }

    def skill_item(self, skill):
        return {
            'url': '%s' % absoluteURL(skill, self.request),
            'obj': skill,
            }

    @property
    def items(self):
        result = []
        add_layer = self.add_layer
        if add_layer is not None:
            for node in self.nodes:
                if add_layer in node.layers:
                    result.append(self.node_item(node))
        return result


class DocumentNodeMixin(DocumentMixin):

    @property
    def schoolyear(self):
        return ISchoolYear(self.context.__parent__)

    @property
    def add_layer(self):
        heirarchy = self.layer_heirarchy
        if heirarchy is None:
            return None
        for index, layer in enumerate(heirarchy[:-1]):
            if layer in self.context.layers:
                return heirarchy[index + 1]
        else:
            return None

    @property
    def items(self):
        result = []
        if self.add_layer is None:
            skillsets = list(self.context.skillsets)
            if skillsets:
                for skill in skillsets[0].values():
                    result.append(self.skill_item(skill))
        else:
            for node in self.nodes:
                if self.context in node.parents:
                    result.append(self.node_item(node))
        return result


class ManageDocumentOverview(flourish.page.Content, DocumentMixin):

    body_template = ViewPageTemplateFile(
        'templates/manage_document_overview.pt')


class DocumentView(flourish.page.Page, DocumentMixin):

    @property
    def title(self):
        schoolyear = self.schoolyear
        return _('Skills Document for ${schoolyear}',
                 mapping={'schoolyear': schoolyear.title})

    @property
    def legend(self):
        layer = self.add_layer
        if layer is None:
            return ''
        return _('${layer} list',
                 mapping={'layer': layer.title})

    @property
    def rows(self):
        return []

    @property
    def done_link(self):
        app = ISchoolToolApplication(None)
        return '%s/manage' % absoluteURL(app, self.request)


class DocumentTertiaryNavigationManager(flourish.page.TertiaryNavigationManager):

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


class DocumentAddLinks(flourish.page.RefineLinksViewlet):
    """Manager for Add links in DocumentView"""


class DocumentAddNodeLink(flourish.page.LinkViewlet, DocumentMixin):

    @property
    def title(self):
        layer = self.add_layer
        if layer is None:
            return None
        return layer.title


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

