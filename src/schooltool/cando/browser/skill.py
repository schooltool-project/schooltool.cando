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
Skill views.
"""

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import adapts
from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.browser import BrowserView
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.traversing.browser.interfaces import IAbsoluteURL

from schooltool.skin import flourish
from schooltool import table
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.cando.interfaces import ISkillSetContainer
from schooltool.common.inlinept import InlineViewPageTemplate

from schooltool.common import SchoolToolMessage as _


class SkillSetContainerView(flourish.page.Page):

    content_template = InlineViewPageTemplate('''
      <div tal:content="structure context/schooltool:content/ajax/table" />
    ''')


class SkillSetTable(table.ajax.Table):
    pass


class SkillSetContainerAbsoluteURLAdapter(BrowserView):
    adapts(ISkillSetContainer, IBrowserRequest)
    implements(IAbsoluteURL)

    def __str__(self):
        app = ISchoolToolApplication(None)
        url = absoluteURL(app, self.request)
        return url + '/skills'

    __call__ = __str__


class ManageSkillsOverview(flourish.page.Content):

    body_template = ViewPageTemplateFile(
        'templates/manage_skills_overview.pt')

    @property
    def skillsets(self):
        app = ISchoolToolApplication(None)
        contacts = ISkillSetContainer(app)
        return contacts

    @property
    def total_skillsets(self):
        return len(self.skillsets)
