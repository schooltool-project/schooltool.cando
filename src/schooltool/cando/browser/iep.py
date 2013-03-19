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
"""IEP views"""

from xml.sax.saxutils import quoteattr

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.cachedescriptors.property import Lazy
from zope.component import getUtility
from zope.intid.interfaces import IIntIds
from zope.i18n.interfaces.locales import ICollator
from zope.publisher.interfaces import NotFound
from zope.security import proxy
from zope.traversing.browser.absoluteurl import absoluteURL

from z3c.form import field, form, button
from z3c.form.interfaces import DISPLAY_MODE
import zc.table

from schooltool.common.inlinept import InheritTemplate
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.course.interfaces import ILearner
from schooltool.course.browser.course import FlourishCoursesViewlet
from schooltool.skin import flourish
from schooltool import table

from schooltool.cando.interfaces import ISectionSkills
from schooltool.cando.interfaces import IStudentIEP
from schooltool.cando import CanDoMessage as _


class StudentIEPLinkViewlet(flourish.page.LinkViewlet):

    @property
    def enabled(self):
        return bool(list(ILearner(self.context).sections()))


class StudentIEPView(flourish.page.Page):

    @property
    def iep(self):
        return IStudentIEP(self.context)


class StudentIEPViewDetails(flourish.form.FormViewlet):

    template = ViewPageTemplateFile('templates/iep_details.pt')
    mode = DISPLAY_MODE

    @property
    def fields(self):
        return field.Fields(IStudentIEP)

    @property
    def title(self):
        return self.view.subtitle

    def canModify(self):
        return flourish.hasPermission(self.context, 'schooltool.edit')

    def editURL(self):
        person_url = absoluteURL(self.context, self.request)
        return '%s/iep-edit-details.html' % person_url

    def getContent(self):
        return self.context


class StudentIEPViewSectionsViewlet(FlourishCoursesViewlet):

    template = ViewPageTemplateFile('templates/iep_sections.pt')

    def update(self):
        super(StudentIEPViewSectionsViewlet, self).update()
        int_ids = getUtility(IIntIds)
        person_url = absoluteURL(self.context, self.request)
        iep_url = '%s/iep_section.html?section_id=%s'
        for sy_info in self.learnerOf:
            for term_info in sy_info['terms']:
                for section_info in term_info['sections']:
                    int_id = int_ids.getId(section_info['obj'])
                    section_info.update({
                            'iep_url': iep_url % (person_url, int_id),
                            })


class StudentIEPViewDoneLink(flourish.viewlet.Viewlet):

    template = InlineViewPageTemplate('''
      <h3 class="done-link" i18n:domain="schooltool">
        <a tal:attributes="href view/url" i18n:translate="">Done</a>
      </h3>
    ''')

    @property
    def url(self):
        return absoluteURL(self.context, self.request)


class StudentIEPEditView(flourish.form.Form, form.EditForm):

    template = InheritTemplate(flourish.page.Page.template)
    content_template = ViewPageTemplateFile('templates/form.pt')
    label = None
    legend = _('IEP Details')

    fields = field.Fields(IStudentIEP)

    def updateActions(self):
        super(StudentIEPEditView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @button.buttonAndHandler(_('Submit'), name='add')
    def handleApply(self, action):
        super(StudentIEPEditView, self).handleApply.func(self, action)
        # XXX: hacky sucessful submit check
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            self.request.response.redirect(self.nextURL())

    @button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        self.request.response.redirect(self.nextURL())

    def nextURL(self):
        person_url = absoluteURL(self.context, self.request)
        return '%s/iep.html' % person_url


class IEPSectionSkillsMixing(flourish.page.Page):

    container_class = 'container widecontainer'

    @property
    def iep(self):
        return IStudentIEP(self.context)

    def isIEPSkill(self, iep_skills, skill):
        skillset = skill.__parent__
        return skillset in iep_skills and skill in iep_skills[skillset]

    @Lazy
    def section(self):
        try:
            section_id = int(self.request.get('section_id'))
        except (TypeError, ValueError):
            section_id = None
        if section_id is not None:
            int_ids = getUtility(IIntIds)
            return int_ids.queryObject(section_id)
        raise NotFound(self.context, self.__name__, self.request)


class StudentIEPSectionView(IEPSectionSkillsMixing):

    @property
    def subtitle(self):
        return _('IEP Skills for ${section}',
                 mapping={'section': self.section.title})


class StudentIEPSectionSkillsViewlet(flourish.viewlet.Viewlet):

    template = InlineViewPageTemplate('''
      <h3 i18n:domain="schooltool.cando">
        <tal:block i18n:translate="">
          IEP Skills
        </tal:block>
        <a class="modify" href=""
           title="Edit student's IEP skills"
           tal:attributes="href view/editURL"
           i18n:attributes="title"
           tal:condition="view/canModify">
          <img tal:attributes="src context/++resource++schooltool.skin.flourish/edit-icon.png"
               i18n:domain="schooltool"
               alt="Edit"
               i18n:attributes="alt" />
        </a>
      </h3>
      <div tal:content="structure view/view/providers/ajax/view/context/iep_section_skills" />
    ''')

    def canModify(self):
        return flourish.hasPermission(self.context, 'schooltool.edit')

    def editURL(self):
        person_url = absoluteURL(self.context, self.request)
        int_ids = getUtility(IIntIds)
        section_id = int_ids.getId(self.view.section)
        return '%s/iep_edit_section_skills.html?section_id=%s' % (
            person_url, section_id)


class SkillSetColumn(zc.table.column.GetterColumn):

    def getSortKey(self, item, formatter):
        collator = ICollator(formatter.request.locale)
        skillset = item['skillset']
        skillset_label = item['skillset_label']
        skill = item['skill']
        return (collator.key(skillset_label or ''),
                collator.key(skillset.title),
                collator.key(skill.label or ''),
                collator.key(skill.title))


def label_title_formatter(obj, item, formatter):
    title = obj.title
    label = getattr(obj, 'label')
    if label is not None:
        title = '%s: %s' % (label, title)
    return title


class StudentIEPSectionSkillsTableFormatter(table.ajax.AJAXFormSortFormatter):

    def renderCell(self, item, column):
        klass = self.cssClasses.get('td', '')
        if column.name == 'skill' and not item['skill'].required:
            if klass:
                klass += ' '
            klass += 'optional'
        if column.name == 'skill' and item['is_iep_skill']:
            if klass:
                klass += ' '
            klass += 'iep'
        klass = klass and ' class=%s' % quoteattr(klass) or ''
        return '<td%s>%s</td>' % (klass, self.getCell(item, column),)

    def renderRow(self, item):
        klass = self.cssClasses.get('tr', '')
        if klass:
            klass += ' '
        klass += '%s/gradebook' % absoluteURL(item['skillset'], self.request)
        klass = klass and ' class=%s' % quoteattr(klass) or ''
        return '<tr%s>%s</tr>' % (
            klass, self.renderCells(item))


class StudentIEPSectionSkillsTable(table.ajax.Table):

    batch_size = 0
    table_formatter = StudentIEPSectionSkillsTableFormatter
    visible_column_names = ['label', 'skill']

    def columns(self):
        skillset = SkillSetColumn(
            name='skillset',
            title=_('Skill Set'))
        label = zc.table.column.GetterColumn(
            name='label',
            title='',
            getter=lambda item, formatter: item['skill'].label or '')
        skill = zc.table.column.GetterColumn(
            name='skill',
            title=_('Skill'),
            getter=lambda item, formatter: item['skill'].title)
        return [skillset, label, skill]

    def items(self):
        result = []
        iep = IStudentIEP(self.context)
        iep_skills = iep.getIEPSkills(self.view.section)
        worksheets = ISectionSkills(self.view.section)
        for worksheet in worksheets.values():
            skillset_label = worksheet.label
            for skill in worksheet.values():
                is_iep_skill =self.view.isIEPSkill(iep_skills, skill)
                result.append({
                        'skillset': proxy.removeSecurityProxy(worksheet),
                        'skillset_label': skillset_label,
                        'skill': skill,
                        'skill_id': self.getSkillId(skill),
                        'is_iep_skill': is_iep_skill,
                        })
        return result

    def sortOn(self):
        return (('skillset', False),)

    def getSkillId(self, skill):
        skillset = skill.__parent__
        return '%s.%s' % (skillset.__name__, skill.__name__)

    def updateFormatter(self):
        if self._table_formatter is None:
            self.setUp(table_formatter=self.table_formatter,
                       batch_size=self.batch_size,
                       prefix=self.__name__,
                       css_classes={'table': 'data color-codes'})


class StudentIEPSectionViewDoneLink(StudentIEPViewDoneLink):

    @property
    def url(self):
        return '%s/iep.html' % absoluteURL(self.context, self.request)


class StudentIEPEditSectionSkillsView(IEPSectionSkillsMixing):

    @property
    def subtitle(self):
        return _('Edit IEP Skills for ${section}',
                 mapping={'section': self.section.title})


class StudentIEPEditSectionSkillsViewlet(flourish.viewlet.Viewlet):

    template = InlineViewPageTemplate('''
      <div tal:content="structure view/view/providers/ajax/view/context/iep_section_skills" />
    ''')


def iep_value_getter(item):
    return False


class StudentIEPEditSectionSkillsTable(StudentIEPSectionSkillsTable):

    visible_column_names = ['optional-iep', 'label', 'skill']
    buttons = (
        {'name': 'SAVE', 'label': _('Save'), 'klass': 'button-ok'},
        {'name': 'CANCEL', 'label': _('Cancel'), 'klass': 'button-cancel'},
        )

    @property
    def checkbox_prefix(self):
        return '%s.iep' % self.prefix

    def columns(self):
        default = super(StudentIEPEditSectionSkillsTable, self).columns()
        iep = table.column.CheckboxColumn(
            self.checkbox_prefix,
            name='optional-iep',
            title=_('Optional IEP'),
            isDisabled=lambda i: not i['skill'].required,
            id_getter=lambda i: i['skill_id'],
            value_getter=lambda i: i['is_iep_skill'])
        return [iep] + default

    def update(self):
        super(StudentIEPEditSectionSkillsTable, self).update()
        saved = False
        if 'SAVE' in self.request:
            self.updateIEPSkills()
            saved = True
        if 'CANCEL' in self.request or saved:
            person_url = absoluteURL(self.context, self.request)
            section_id = self.request.get('section_id')
            url = '%s/iep_section.html?section_id=%s' % (
                person_url, section_id)
            self.request.response.redirect(url)

    def updateIEPSkills(self):
        for item in self._items:
            skill = item['skill']
            cell_name = '%s.%s' % (self.checkbox_prefix, item['skill_id'])
            if cell_name in self.request:
                if not item['is_iep_skill']:
                    self.view.iep.addSkill(self.view.section, skill)
            else:
                if item['is_iep_skill']:
                    self.view.iep.removeSkill(self.view.section, skill)


class StudentIEPEditSectionSkillsButtons(flourish.viewlet.Viewlet):

    template = InlineViewPageTemplate('''
      <input type="hidden" name="section_id"
             tal:define="section_id request/section_id|nothing"
             tal:condition="section_id"
             tal:attributes="value section_id;" />
      <div class="buttons" i18n:domain="schooltool">
        <tal:loop repeat="action view/manager/buttons">
          <input type="submit"
                 tal:attributes="name action/name;
                                 value action/label;
                                 class action/klass;"
                 />
        </tal:loop>
      </div>
    ''')


class GradebookIEPStudents(flourish.viewlet.Viewlet):

    template = ViewPageTemplateFile('templates/gradebook_iep_students.pt')

    def students(self):
        result = []
        for student in self.view.students:
            if IStudentIEP(student).active:
                result.append(student.username)
        return result


class GradeStudentIEPDescriptionViewlet(StudentIEPViewDetails):

    @property
    def fields(self):
        return field.Fields(IStudentIEP).select('description')

    @property
    def title(self):
        return _('IEP Information')

    def canModify(self):
        return False

    def getContent(self):
        return self.view.student

    @property
    def enabled(self):
        iep = IStudentIEP(self.view.student)
        return iep.active and iep.description

    def render(self, *args, **kw):
        if not self.enabled:
            return ''
        return super(GradeStudentIEPDescriptionViewlet, self).render(
            *args, **kw)
