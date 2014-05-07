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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Skill views.
"""

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.cachedescriptors.property import Lazy
from zope.component import adapts
from zope.container.interfaces import INameChooser
from zope.interface import implements, Interface
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.browser import BrowserView
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.traversing.browser.interfaces import IAbsoluteURL
import z3c.form.field
import z3c.form.form
import z3c.form.button
from z3c.form.browser.text import TextWidget
from z3c.form.widget import FieldWidget
from z3c.form.term import BoolTerms
from z3c.form.interfaces import IRadioWidget
import zc.table.column
import zc.table.interfaces

from schooltool.skin import flourish
from schooltool import table
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.person.interfaces import IPerson
from schooltool.cando.interfaces import ISkillSetContainer
from schooltool.cando.interfaces import ISkillSet, ISkill
from schooltool.cando.interfaces import ISkillRequiredBool
from schooltool.cando.skill import SkillSet, Skill
from schooltool.common.inlinept import InheritTemplate
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.skin.flourish import IFlourishLayer

from schooltool.cando import CanDoMessage as _
from schooltool.cando.skill import getDefaultSkillScoreSystem
from schooltool.cando.skill import setDefaultSkillScoreSystem

class SkillSetContainerView(flourish.page.Page):

    content_template = InlineViewPageTemplate('''
      <div tal:content="structure context/schooltool:content/ajax/view/container/table" />
      <h3 tal:condition="python: not len(context)" i18n:domain="schooltool">There are no skill sets.</h3>
    ''')

    @Lazy
    def container(self):
        return ISkillSetContainer(ISchoolToolApplication(None))


class SkillSetTable(table.ajax.Table):

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
        label = table.column.LocaleAwareGetterColumn(
            name='label',
            title=_(u'Label'),
            getter=lambda i, f: i.label or '',
            subsort=True)
        return [label] + default + [skills]

    def sortOn(self):
        return (('label', False), ('title', False))


class SkillSetTableFilter(table.ajax.TableFilter, table.table.FilterWidget):

    title = _("Title, description or label")

    def filter(self, results):
        if self.ignoreRequest:
            return results
        if 'SEARCH' in self.request:
            searchstr = self.request['SEARCH'].lower()
            results = [item for item in results
                       if searchstr in item.title.lower() or
                       (item.label and searchstr in item.label.lower()) or
                       (item.description and
                        searchstr in item.description.lower())]
        return results


class SkillSetContainerAbsoluteURLAdapter(BrowserView):
    adapts(ISkillSetContainer, IBrowserRequest)
    implements(IAbsoluteURL)

    def __str__(self):
        app = ISchoolToolApplication(None)
        url = absoluteURL(app, self.request)
        return url + '/skills'

    __call__ = __str__


class SkillSetContainerLinks(flourish.page.RefineLinksViewlet):
    pass


class SkillSetContainerActionLinks(flourish.page.RefineLinksViewlet):
    pass


class SkillSetAddView(flourish.form.AddForm):

    template = InheritTemplate(flourish.page.Page.template)
    label = None
    legend = _('Skill set')
    add_next = False

    fields = z3c.form.field.Fields(ISkillSet)
    fields = fields.select('title', 'description', 'label')

    def updateActions(self):
        super(SkillSetAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['submitadd'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def nextURL(self):
        url = absoluteURL(self.context, self.request)
        if self.add_next:
            return url + '/add.html'
        return url

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

    @z3c.form.button.buttonAndHandler(_('Submit'), name='add')
    def handleSubmit(self, action):
        super(SkillSetAddView, self).handleAdd.func(self, action)

    @z3c.form.button.buttonAndHandler(_('Submit and add'), name='submitadd')
    def handleSubmitAndAdd(self, action):
        super(SkillSetAddView, self).handleAdd.func(self, action)
        if self._finishedAdd:
            self.add_next = True

    @z3c.form.button.buttonAndHandler(_('Cancel'))
    def handleCancel(self, action):
        super(SkillSetAddView, self).handleCancel.func(self, action)


# XXX: after adding skillset, redirect to it's edit view.

class SkillSetView(flourish.form.DisplayForm):
    template = InheritTemplate(flourish.page.Page.template)
    fields = z3c.form.field.Fields(ISkillSet)
    fields = fields.select('description', 'label', 'retired')


class SkillSetEditView(flourish.form.Form, z3c.form.form.EditForm):

    template = InheritTemplate(flourish.page.Page.template)
    fields = z3c.form.field.Fields(ISkillSet)
    fields = fields.select('title', 'description', 'label', 'retired')

    legend = _('Skill set')

    @z3c.form.button.buttonAndHandler(_('Submit'), name='apply')
    def handleApply(self, action):
        super(SkillSetEditView, self).handleApply.func(self, action)
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            self.request.response.redirect(self.nextURL())

    @z3c.form.button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        self.request.response.redirect(self.nextURL())

    def updateActions(self):
        super(SkillSetEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def nextURL(self):
        return absoluteURL(self.context, self.request)


class SkillSetSkillTable(table.ajax.Table):

    def updateFormatter(self):
        if self._table_formatter is None:
            self.setUp(table_formatter=self.table_formatter,
                       batch_size=self.batch_size,
                       prefix=self.__name__,
                       css_classes={'table': 'data'})

    def sortOn(self):
        return (('label', False), ('title', False))

    def columns(self):
        default = table.ajax.Table.columns(self)
        label = table.column.LocaleAwareGetterColumn(
            name='label',
            title=_(u'Label'),
            getter=lambda i, f: i.label or '',
            subsort=True)
        return [label] + default


class SkillSetLinks(flourish.page.RefineLinksViewlet):
    pass


class SkillAddView(flourish.form.AddForm):

    template = InheritTemplate(flourish.page.Page.template)
    label = None
    legend = _('Skill')
    add_next = False

    fields = z3c.form.field.Fields(ISkill)
    fields = fields.select('title', 'scoresystem', 'description', 'label',
                           'required', 'external_id')

    @z3c.form.button.buttonAndHandler(_('Submit'), name='add')
    def handleSubmit(self, action):
        super(SkillAddView, self).handleAdd.func(self, action)

    @z3c.form.button.buttonAndHandler(_('Submit and add'), name='submitadd')
    def handleSubmitAndAdd(self, action):
        super(SkillAddView, self).handleAdd.func(self, action)
        if self._finishedAdd:
            self.add_next = True

    @z3c.form.button.buttonAndHandler(_('Cancel'))
    def handleCancel(self, action):
        super(SkillAddView, self).handleCancel.func(self, action)

    def updateActions(self):
        super(SkillAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['submitadd'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def updateWidgets(self):
        super(SkillAddView, self).updateWidgets()

        scoresystem = self.widgets['scoresystem'].value
        if scoresystem:
            return
        person = IPerson(self.request.principal, None)
        default = getDefaultSkillScoreSystem(person)
        if default is not None:
            self.widgets['scoresystem'].value = default

    def nextURL(self):
        url = absoluteURL(self.context, self.request)
        if self.add_next:
            return url + '/add.html'
        return url

    def create(self, data):
        if not data['label']:
            data['label'] = u'%02d' % (len(self.context) + 1)
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
        scoresystem = self.request.get(self.widgets['scoresystem'].name, '')
        if scoresystem:
            person = IPerson(self.request.principal, None)
            setDefaultSkillScoreSystem(person, scoresystem)
        return skill


class SkillView(flourish.form.DisplayForm):

    template = InheritTemplate(flourish.page.Page.template)

    label = None
    legend = _('Skill')

    fields = z3c.form.field.Fields(ISkill)
    fields = fields.select('scoresystem', 'description', 'label', 'required',
                           'retired', 'external_id')

    @property
    def title(self):
        return self.context.__parent__.title

    @property
    def can_edit(self):
        return flourish.canEdit(self.context)

    @property
    def edit_url(self):
        return absoluteURL(self.context, self.request) + '/edit.html'

    @property
    def done_url(self):
        return absoluteURL(self.context.__parent__, self.request)


class SkillEditView(flourish.form.Form, z3c.form.form.EditForm):

    template = InheritTemplate(flourish.page.Page.template)
    fields = z3c.form.field.Fields(ISkill)
    fields = fields.select('title', 'description', 'label',
                           'required', 'external_id')

    legend = _('Skill')

    @z3c.form.button.buttonAndHandler(_('Submit'), name='apply')
    def handleApply(self, action):
        super(SkillEditView, self).handleApply.func(self, action)
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            self.request.response.redirect(self.nextURL())

    @z3c.form.button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        self.request.response.redirect(self.nextURL())

    def updateActions(self):
        super(SkillEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def nextURL(self):
        return absoluteURL(self.context, self.request)


class LabelTextLineWidget(TextWidget):

    def update(self):
        super(LabelTextLineWidget, self).update()
        self.maxlength = self.field.max_length


def LabelTextLineFieldWidget(field, request):
    return FieldWidget(field, LabelTextLineWidget(request))


class SkillRequiredTerms(BoolTerms):

    adapts(Interface,
           IFlourishLayer,
           Interface,
           ISkillRequiredBool,
           IRadioWidget)

    trueLabel = _('Required')
    falseLabel = _('Optional')
