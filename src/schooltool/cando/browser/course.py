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
Course skill views.
"""
from zope.cachedescriptors.property import Lazy
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.traversing.browser.absoluteurl import absoluteURL
import z3c.form.form
import z3c.form.field
import z3c.form.button
import zc.table.column

from schooltool.app.browser.app import RelationshipAddTableMixin
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.cando.course import CourseSkillSet
from schooltool.cando.interfaces import ICourseSkills
from schooltool.cando.interfaces import ICourseSkillSet
from schooltool.cando.interfaces import ISkillSetContainer
from schooltool.cando.browser.skill import SkillSetTable, SkillSetSkillTable
from schooltool.cando.browser.skill import SkillView
from schooltool.course.interfaces import ICourse
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.skin import flourish
from schooltool import table

from schooltool.common import SchoolToolMessage as _


class CourseSkillsOverview(flourish.page.Content):
    body_template = ViewPageTemplateFile(
        'templates/course_skills_overview.pt')

    @Lazy
    def skills(self):
        return ICourseSkills(self.context)


class UseCourseTitleMixin(object):

    @property
    def title(self):
        obj = self.context
        while obj is not None:
            if ICourse.providedBy(obj):
                return obj.title
            obj = obj.__parent__
        return ''


class CourseSkillsView(UseCourseTitleMixin, flourish.page.Page):

    content_template = InlineViewPageTemplate('''
      <div tal:content="structure context/schooltool:content/ajax/table" />
      <h3>
        <a tal:attributes="href context/__parent__/@@absolute_url"
           i18n:translate="">Done</a>
      </h3>
    ''')

    @property
    def title(self):
        return self.context.__parent__.title


class CourseSkillsTable(table.ajax.Table):

    def updateFormatter(self):
        if self._table_formatter is None:
            self.setUp(table_formatter=self.table_formatter,
                       batch_size=self.batch_size,
                       prefix=self.__name__,
                       css_classes={'table': 'data'})

    def columns(self):
        default = table.ajax.Table.columns(self)
        skills = zc.table.column.GetterColumn(
            name='skills',
            title=_(u'Skills'),
            getter=lambda i, f: str(len(i)))
        label = zc.table.column.GetterColumn(
            name='label',
            title=_(u'Label'),
            getter=lambda i, f: i.skillset.label or '')
        return [label] + default + [skills]


class CourseSkillsLinks(flourish.page.RefineLinksViewlet):
    pass


# XXX: done link in course skills view.

class CourseAssignSkillSetView(flourish.page.Page):

    content_template = InlineViewPageTemplate('''
      <div tal:content="structure context/schooltool:content/ajax/available_table" />
    ''')

    def getKey(self, skillset):
        return skillset.__name__

    def getOmmitedItems(self):
        app = ISchoolToolApplication(None)
        skillsets = ISkillSetContainer(app)
        ommit = [skillsets.get(i) for i in self.context]
        return [o for o in ommit if o is not None]


class AvailableSkillSetTable(RelationshipAddTableMixin,
                             SkillSetTable):

    @property
    def source(self):
        app = ISchoolToolApplication(None)
        return ISkillSetContainer(app)

    def submitItems(self):
        prefix = self.button_prefix + '.'
        for key in self.request:
            if not key.startswith(prefix):
                continue
            name = key[len(prefix):]
            self.context[name] = CourseSkillSet(self.source[name])


class CourseSkillSetView(UseCourseTitleMixin, flourish.page.Page):
    pass


class CourseSkillSetEditView(UseCourseTitleMixin, flourish.page.Page):
    pass


class CourseEditSkillSetSkillsTable(table.ajax.Table):

    def updateFormatter(self):
        if self._table_formatter is None:
            self.setUp(table_formatter=self.table_formatter,
                       batch_size=self.batch_size,
                       prefix=self.__name__,
                       css_classes={'table': 'data'})

    def columns(self):
        title = zc.table.column.GetterColumn(name='title',
                             title=_(u"Title"),
                             getter=lambda i, f: i.title,
                             subsort=True)
        label = zc.table.column.GetterColumn(
            name='label',
            title=_(u'Label'),
            getter=lambda i, f: i.label or '')
        required = table.column.CheckboxColumn(
            self.prefix+'.required',
            name='required',
            title=_(u"Required"),
            id_getter=lambda i: i.__name__,
            value_getter=lambda i: i.required)
        hidden = table.column.CheckboxColumn(
            self.prefix+'.hidden',
            name='hidden',
            title=_(u"Hidden"),
            id_getter=lambda i: i.__name__,
            value_getter=lambda i: i.retired)
        return [label, title, required, hidden]

    def items(self):
        source = self.source
        skillset = source.skillset
        return [source.get(k) for k in skillset]

    def nextURL(self):
        return absoluteURL(self.context, self.request)

    def applyChanges(self):
        for v in self.items():
            k = v.__name__
            required = bool(self.request.get(self.prefix + '.required.' + k))
            hidden = bool(self.request.get(self.prefix + '.hidden.' + k))
            if v.required != required:
                v.required = required
            if v.retired != hidden:
                v.retired = hidden

    def update(self):
        super(CourseEditSkillSetSkillsTable, self).update()
        if 'SUBMIT_BUTTON' in self.request:
            self.applyChanges()
            self.request.response.redirect(self.nextURL())
            return
        if 'CANCEL_BUTTON' in self.request:
            self.request.response.redirect(self.nextURL())
            return


class CourseSkillSetBreadcrumb(flourish.breadcrumbs.Breadcrumbs):

    @property
    def title(self):
        ss = self.context.skillset
        return ss.label or ss.title


class CourseSkillSetSkillTable(SkillSetSkillTable):
    pass


class CourseSkillView(SkillView):

    can_edit = False
