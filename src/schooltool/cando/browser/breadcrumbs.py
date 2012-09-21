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
Breadcrumbs.
"""

from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.skin import flourish

from schooltool.cando.browser import document
from schooltool.cando.interfaces import IDocumentContainer

from schooltool.cando import CanDoMessage as _


class LabelBreadcrumb(flourish.breadcrumbs.Breadcrumbs):

    @property
    def title(self):
        return self.context.label or self.context.title


class CourseSkillSetBreadcrumb(flourish.breadcrumbs.Breadcrumbs):

    @property
    def title(self):
        ss = self.context.skillset
        return ss.label or ss.title


class DocumentNavBreadcrumb(flourish.breadcrumbs.Breadcrumbs):

    @property
    def crumb_parent(self):
        return IDocumentContainer(ISchoolToolApplication(None))

    @property
    def url(self):
        if not self.checkPermission():
            return False
        app = ISchoolToolApplication(None)
        app_url = absoluteURL(app, self.request)
        link = '%s/%s' % (app_url, self.traversal_name)
        return link


class DocumentLayerBreadcrumb(flourish.breadcrumbs.Breadcrumbs,
                              document.DocumentNodeMixin):

    @property
    def crumb_parent(self):
        return self.get_document()

    @property
    def url(self):
        if not self.checkPermission():
            return False
        layer_url = absoluteURL(self.context, self.request)
        query_string = self.build_query_string()
        link = '%s/document.html%s' % (layer_url, query_string)
        return link


class DocumentNodeBreadcrumb(flourish.breadcrumbs.Breadcrumbs,
                             document.DocumentNodeMixin):

    @property
    def crumb_parent(self):
        parents = tuple(self.context.parents)
        if not parents:
            return None
        return parents[0]

    @property
    def url(self):
        if not self.checkPermission():
            return False
        node_url = absoluteURL(self.context, self.request)
        layers = tuple(self.context.layers)
        if not layers:
            return False
        query_string = self.build_query_string(layer=layers[0])
        link = '%s/document.html%s' % (node_url, query_string)
        return link


class DocumentSkillSetBreadcrumb(flourish.breadcrumbs.Breadcrumbs,
                                 document.DocumentSkillSetMixin):

    @property
    def crumb_parent(self):
        return self.get_node()

    @property
    def url(self):
        if not self.checkPermission():
            return False
        skillset_url = absoluteURL(self.context, self.request)
        query_string = self.build_query_string(layer=self.get_previous_layer(),
                                               node=self.get_node())
        link = '%s/document.html%s' % (skillset_url, query_string)
        return link


class DocumentSkillBreadcrumb(flourish.breadcrumbs.Breadcrumbs,
                              document.DocumentSkillMixin):

    @property
    def url(self):
        if not self.checkPermission():
            return False
        skill_url = absoluteURL(self.context, self.request)
        query_string = self.build_query_string(layer=self.get_previous_layer(),
                                               node=self.get_node())
        link = '%s/document.html%s' % (skill_url, query_string)
        return link

