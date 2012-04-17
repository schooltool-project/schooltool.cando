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
from zope.container.interfaces import INameChooser
from zope.interface import implements, directlyProvides
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.browser import BrowserView
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.traversing.browser.interfaces import IAbsoluteURL
import z3c.form.field
import z3c.form.form
import z3c.form.button
import zc.table.column
import zc.table.interfaces

from schooltool.skin import flourish
from schooltool import table
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.cando.interfaces import ISkillSetContainer
from schooltool.cando.interfaces import ISkillSet, ISkill
from schooltool.cando.skill import SkillSet, Skill
from schooltool.common.inlinept import InlineViewPageTemplate

from schooltool.common import SchoolToolMessage as _


class SkillSetContainerView(flourish.page.Page):

    content_template = InlineViewPageTemplate('''
      <div tal:content="structure context/schooltool:content/ajax/table" />
    ''')


class SkillSetTable(table.ajax.Table):

    def columns(self):
        default = table.ajax.Table.columns(self)
        skills = zc.table.column.GetterColumn(
            name='skills',
            title=_(u'Skills'),
            getter=lambda i, f: str(len(i)))
        return default + [skills]


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


class SkillSetContainerLinks(flourish.page.RefineLinksViewlet):
    pass


class SkillSetAddView(flourish.form.AddForm):

    label = None
    legend = _('Skill set')

    fields = z3c.form.field.Fields(ISkillSet)
    fields = fields.select('title', 'description', 'external_id')

    def updateActions(self):
        super(SkillSetAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def nextURL(self):
        return absoluteURL(self.context, self.request)

    def create(self, data):
        skillset = SkillSet(data['title'])
        z3c.form.form.applyChanges(self, skillset, data)
        self._skillset = skillset
        return skillset

    def add(self, skillset):
        chooser = INameChooser(self.context)
        name = unicode(skillset.title).encode('punycode')
        name = name[:8]+str(len(self.context)+1)
        name = chooser.chooseName(name, skillset)
        self.context[name] = skillset
        return skillset


class SkillSetView(flourish.form.DisplayForm):
    fields = z3c.form.field.Fields(ISkillSet)
    fields = fields.select('description', 'external_id')


class SkillSetEditView(flourish.form.Form, z3c.form.form.EditForm):
    fields = z3c.form.field.Fields(ISkillSet)
    fields = fields.select('title', 'description', 'external_id')

    legend = _('Skill set')

    @z3c.form.button.buttonAndHandler(_('Submit'), name='apply')
    def handleApply(self, action):
        super(SkillSetEditView, self).handleApply.func(self, action)
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            url = absoluteURL(self.context, self.request)
            self.request.response.redirect(url)

    @z3c.form.button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def updateActions(self):
        super(SkillSetEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')


class SkillSetSkillTable(table.ajax.Table):

    def updateFormatter(self):
        if self._table_formatter is None:
            self.setUp(table_formatter=self.table_formatter,
                       batch_size=self.batch_size,
                       prefix=self.__name__,
                       css_classes={'table': 'data'})

    def sortOn(self):
        return (("required", True), ("title", False))

    def columns(self):
        default = table.ajax.Table.columns(self)
        required = zc.table.column.GetterColumn(
            name='required',
            title=_(u'Required'),
            getter=lambda i, f: i.required and _('required') or _('optional'))
        directlyProvides(required, zc.table.interfaces.ISortableColumn)
        external_id = zc.table.column.GetterColumn(
            name='external_id',
            title=_(u'External ID'),
            getter=lambda i, f: i.external_id or '')
        return [required, external_id] + default


class SkillSetLinks(flourish.page.RefineLinksViewlet):
    pass


class SkillAddView(flourish.form.AddForm):

    label = None
    legend = _('Skill')

    fields = z3c.form.field.Fields(ISkill)
    fields = fields.select('title', 'description', 'label',
                           'required', 'external_id')

    def updateActions(self):
        super(SkillAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def nextURL(self):
        return absoluteURL(self.context, self.request)

    def create(self, data):
        skill = Skill(data['title'])
        z3c.form.form.applyChanges(self, skill, data)
        self._skill = skill
        return skill

    def add(self, skill):
        chooser = INameChooser(self.context)
        if skill.external_id:
            name = skill.external_id
        else:
            name = unicode(skill.title).encode('punycode')
            name = name[:8]+str(len(self.context)+1)
        name = chooser.chooseName(name, skill)
        self.context[name] = skill
        return skill


class SkillView(flourish.form.DisplayForm):

    label = None
    legend = _('Skill')

    fields = z3c.form.field.Fields(ISkill)
    fields = fields.select('description', 'label',
                           'required', 'external_id')

    @property
    def title(self):
        return self.context.__parent__.title


class SkillEditView(flourish.form.Form, z3c.form.form.EditForm):
    fields = z3c.form.field.Fields(ISkill)
    fields = fields.select('title', 'description', 'label',
                           'required', 'external_id')

    legend = _('Skill')

    @z3c.form.button.buttonAndHandler(_('Submit'), name='apply')
    def handleApply(self, action):
        super(SkillEditView, self).handleApply.func(self, action)
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            url = absoluteURL(self.context, self.request)
            self.request.response.redirect(url)

    @z3c.form.button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def updateActions(self):
        super(SkillEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

