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
CanDo view components.
"""

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.container.interfaces import INameChooser
from zope.i18n import translate
from zope.location.location import LocationProxy
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.security import proxy

from z3c.form import form, field, button

from schooltool.course.interfaces import ISection
from schooltool.common.inlinept import InheritTemplate
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.gradebook.browser.gradebook import FlourishGradebookOverview
from schooltool.gradebook.browser.gradebook import FlourishGradebookStartup
from schooltool.gradebook.browser.gradebook import GradebookStartupNavLink
from schooltool.gradebook.browser.gradebook import FlourishActivityPopupMenuView
from schooltool.gradebook.browser.gradebook import GradebookTertiaryNavigationManager
from schooltool.gradebook.browser.gradebook import FlourishGradebookYearNavigationViewlet
from schooltool.gradebook.browser.gradebook import FlourishGradebookTermNavigationViewlet
from schooltool.gradebook.browser.gradebook import FlourishGradebookSectionNavigationViewlet
from schooltool.person.interfaces import IPerson
from schooltool.skin import flourish

from schooltool.cando.interfaces import IProject
from schooltool.cando.interfaces import IProjects
from schooltool.cando.interfaces import ISectionSkills
from schooltool.cando.interfaces import IProjectsGradebook
from schooltool.cando.interfaces import ISkillsGradebook
from schooltool.cando.interfaces import ISkill
from schooltool.cando.gradebook import ensureAtLeastOneProject
from schooltool.cando.gradebook import getCurrentSectionTaught
from schooltool.cando.gradebook import getCurrentSectionAttended
from schooltool.cando.project import Project
from schooltool.cando.skill import querySkillScoreSystem
from schooltool.cando.browser.skill import SkillAddView
from schooltool.cando import CanDoMessage as _


class CanDoStartupNavLink(GradebookStartupNavLink):

    startup_view_name = 'cando.html'


class CanDoStartupView(FlourishGradebookStartup):

    teacher_gradebook_view_name = 'gradebook-projects'
    student_gradebook_view_name = 'mygrades-projects'

    def update(self):
        self.person = IPerson(self.request.principal)
        if not self.sectionsTaught and not self.sectionsAttended:
            self.noSections = True
        if self.sectionsTaught:
            section = getCurrentSectionTaught(self.person)
            if section is None or section.__parent__ is None:
                section = self.sectionsTaught[0]
            self.gradebookURL = '%s/%s' % (absoluteURL(section, self.request),
                                           self.teacher_gradebook_view_name)
            if not self.sectionsAttended:
                self.request.response.redirect(self.gradebookURL)
        if self.sectionsAttended:
            section = getCurrentSectionAttended(self.person)
            if section is None or section.__parent__ is None:
                section = self.sectionsAttended[0]
            self.mygradesURL = '%s/%s' % (absoluteURL(section, self.request),
                                          self.student_gradebook_view_name)
            if not self.sectionsTaught:
                self.request.response.redirect(self.mygradesURL)


class SectionProjectsCanDoRedirectView(flourish.page.Page):

    teacher_worksheet_view_name = 'gradebook'
    student_worksheet_view_name = 'mygrades'

    # XXX: merge this with SectionGradebookRedirectView
    def __call__(self):
        person = IPerson(self.request.principal)
        worksheets = IProjects(self.context)
        ensureAtLeastOneProject(worksheets)
        current_worksheet = worksheets.getCurrentWorksheet(person)
        url = absoluteURL(worksheets, self.request)
        if current_worksheet is not None:
            url = absoluteURL(current_worksheet, self.request)
            if person in self.context.members:
                url += '/%s' % self.student_worksheet_view_name
            else:
                url += '/%s' % self.teacher_worksheet_view_name
        self.request.response.redirect(url)
        return "Redirecting..."


class SectionSkillsCanDoRedirectView(flourish.page.Page):

    teacher_worksheet_view_name = 'gradebook'
    student_worksheet_view_name = 'mygrades'

    # XXX: merge this with SectionGradebookRedirectView
    def __call__(self):
        person = IPerson(self.request.principal)
        worksheets = ISectionSkills(self.context)
        # XXX: get Location proxy here
        current_worksheet = worksheets.getCurrentWorksheet(person)
        url = absoluteURL(worksheets, self.request)
        if current_worksheet is not None:
            container = ISectionSkills(self.context)
            current_worksheet = LocationProxy(
                current_worksheet,
                container=container,
                name=current_worksheet.__name__)
            url = absoluteURL(current_worksheet, self.request)
            if person in self.context.members:
                url += '/%s' % self.student_worksheet_view_name
            else:
                url += '/%s' % self.teacher_worksheet_view_name
        self.request.response.redirect(url)
        return "Redirecting..."


class ProjectsGradebookOverview(FlourishGradebookOverview):

    labels_row_header = _('Skill')
    teacher_gradebook_view_name = 'gradebook-projects'
    student_gradebook_view_name = 'mygrades-projects'

    @property
    def title(self):
        if self.all_hidden:
            return _('No Visible Projects')
        else:
            return _('Enter Skills')

    def getActivityInfo(self, activity):
        result = super(ProjectsGradebookOverview, self).getActivityInfo(
            activity)
        if not activity.required:
            cssClass = ' '.join(filter(None, [result['cssClass'], 'optional']))
            result['cssClass'] = cssClass
        return result

    def processColumnPreferences(self):
        self.average_hide = True
        self.total_hide = True
        self.tardies_hide = True
        self.absences_hide = True
        self.due_date_hide = True
        self.average_scoresystem = None

    def getActivityAttrs(self, activity):
        shortTitle, longTitle, bestScore = super(
            ProjectsGradebookOverview, self).getActivityAttrs(activity)
        longTitle = activity.label + ': ' + longTitle
        return shortTitle, longTitle, bestScore



class SkillsGradebookOverview(FlourishGradebookOverview):

    labels_row_header = _('Skill')
    teacher_gradebook_view_name = 'gradebook-skills'
    student_gradebook_view_name = 'mygrades-skills'

    @property
    def title(self):
        if self.all_hidden:
            return _('No Visible Skill Sets')
        else:
            return _('Enter Skills')

    def getActivityInfo(self, activity):
        result = super(SkillsGradebookOverview, self).getActivityInfo(
            activity)
        if not activity.required:
            cssClass = ' '.join(filter(None, [result['cssClass'], 'optional']))
            result['cssClass'] = cssClass
        return result

    def processColumnPreferences(self):
        self.average_hide = True
        self.total_hide = True
        self.tardies_hide = True
        self.absences_hide = True
        self.due_date_hide = True
        self.average_scoresystem = None

    def getActivityAttrs(self, activity):
        shortTitle, longTitle, bestScore = super(
            SkillsGradebookOverview, self).getActivityAttrs(activity)
        longTitle = activity.label + ': ' + longTitle
        return shortTitle, longTitle, bestScore


class ProjectsBreadcrumbs(flourish.breadcrumbs.Breadcrumbs):

    @property
    def link(self):
        return '../gradebook-projects'


class SkillsBreadcrumbs(flourish.breadcrumbs.Breadcrumbs):

    @property
    def link(self):
        return '../gradebook-skills'


class CanDoProjectsAddLinks(flourish.page.RefineLinksViewlet):

    pass


class CanDoProjectsSettingsLinks(flourish.page.RefineLinksViewlet):

    pass


class CanDoModes(flourish.page.RefineLinksViewlet):

    pass


class CanDoModesViewlet(flourish.viewlet.Viewlet):

    list_class = 'filter'

    template = InlineViewPageTemplate('''
        <ul tal:attributes="class view/list_class"
            tal:condition="view/items">
          <li tal:repeat="item view/items">
            <input type="radio"
                   onclick="ST.redirect($(this).context.value)"
                   tal:attributes="value item/url;
                                   id item/id;
                                   checked item/selected;" />
            <label tal:content="item/label"
                   tal:attributes="for item/id" />
          </li>
        </ul>
    ''')

    def items(self):
        section = ISection(proxy.removeSecurityProxy(self.context))
        section_url = absoluteURL(section, self.request)
        result = []
        if ISectionSkills(section):
            result.append({
                    'id': 'skills',
                    'label': _('Skills'),
                    'url': section_url + '/gradebook-skills',
                    'selected': ISkillsGradebook.providedBy(self.context),
                    })
        result.append({
                'id': 'projects',
                'label': _('Projects'),
                'url': section_url + '/gradebook-projects',
                'selected': IProjectsGradebook.providedBy(self.context),
                })
        return result

    def render(self, *args, **kw):
        return self.template(*args, **kw)


class SkillAddLink(flourish.page.LinkViewlet):

    @property
    def title(self):
        worksheet = proxy.removeSecurityProxy(self.context).context
        if worksheet.deployed:
            return ''
        return _("Skill")


class ProjectSkillAddView(SkillAddView):

    def nextURL(self):
        url = absoluteURL(self.context, self.request)
        if self.add_next:
            return url + '/addSkill.html'
        return url + '/gradebook'


class ProjectAddView(flourish.form.AddForm):

    fields = field.Fields(IProject).select('title')
    template = InheritTemplate(flourish.page.Page.template)
    label = None
    legend = _('Project Details')

    @button.buttonAndHandler(_('Submit'), name='add')
    def handleAdd(self, action):
        super(ProjectAddView, self).handleAdd.func(self, action)

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        person = IPerson(self.request.principal, None)
        if person is None:
            worksheet = self.context._getDefaultWorksheet()
        else:
            worksheet = self.context.getCurrentWorksheet(person)
        if worksheet is None:
            url = absoluteURL(self.context.__parent__, self.request)
        else:
            url = absoluteURL(worksheet, self.request) + '/gradebook'
        self.request.response.redirect(url)

    def create(self, data):
        self.worksheet = Project(data['title'])
        return self.worksheet

    def add(self, worksheet):
        chooser = INameChooser(self.context)
        name = chooser.chooseName(worksheet.title, worksheet)
        self.context[name] = worksheet
        return worksheet

    def nextURL(self):
        return absoluteURL(self.worksheet, self.request)

    def updateActions(self):
        super(ProjectAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')


class SkillPopupMenuView(FlourishActivityPopupMenuView):

    def getActivityAttrs(self, activity):
        shortTitle, longTitle, bestScore = super(
            SkillPopupMenuView, self).getActivityAttrs(activity)
        longTitle = activity.label + ': ' + longTitle
        return shortTitle, longTitle, bestScore


class SkillEditView(flourish.form.Form, form.EditForm):

    template = InheritTemplate(flourish.page.Page.template)
    label = None
    legend = _('Skill Details')

    fields = field.Fields(ISkill).select('title',
                                         'label',
                                         'description',
                                         'required',
                                         'external_id')

    def updateActions(self):
        super(SkillEditView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @button.buttonAndHandler(_('Submit'), name='add')
    def handleApply(self, action):
        super(SkillEditView, self).handleApply.func(self, action)
        # XXX: hacky sucessful submit check
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            self.request.response.redirect(self.nextURL())

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        self.request.response.redirect(self.nextURL())

    def nextURL(self):
        next = self.request.get('nexturl')
        if next:
            return next
        worksheet = self.context.__parent__
        return absoluteURL(worksheet, self.request) + '/gradebook'


class ProjectsGradebookTertiaryNavigationManager(
    GradebookTertiaryNavigationManager):

    template = ViewPageTemplateFile('templates/cando_third_nav.pt')


class CanDoProjectsNavigationViewletBase(object):

    teacher_gradebook_view_name = 'gradebook-projects'
    student_gradebook_view_name = 'mygrades-projects'


class CanDoProjectsYearNavigationViewlet(
    CanDoProjectsNavigationViewletBase,
    FlourishGradebookYearNavigationViewlet): pass


class CanDoProjectsTermNavigationViewlet(
    CanDoProjectsNavigationViewletBase,
    FlourishGradebookTermNavigationViewlet): pass


class CanDoProjectsSectionNavigationViewlet(
    CanDoProjectsNavigationViewletBase,
    FlourishGradebookSectionNavigationViewlet): pass


class CanDoSkillsNavigationViewletBase(object):

    teacher_gradebook_view_name = 'gradebook-skills'
    student_gradebook_view_name = 'mygrades-skills'


class CanDoSkillsYearNavigationViewlet(
    CanDoSkillsNavigationViewletBase,
    FlourishGradebookYearNavigationViewlet): pass


class CanDoSkillsTermNavigationViewlet(
    CanDoSkillsNavigationViewletBase,
    FlourishGradebookTermNavigationViewlet): pass


class CanDoSkillsSectionNavigationViewlet(
    CanDoSkillsNavigationViewletBase,
    FlourishGradebookSectionNavigationViewlet): pass


class GradebookHelpLinks(flourish.page.RefineLinksViewlet):
    pass


class ScoreSystemHelpViewlet(flourish.page.ModalFormLinkViewlet):

    @property
    def dialog_title(self):
        title = _(u'Score System Help')
        return translate(title, context=self.request)


class ScoreSystemHelpView(flourish.form.Dialog):

    def updateDialog(self):
        # XXX: fix the width of dialog content in css
        if self.ajax_settings['dialog'] != 'close':
            self.ajax_settings['dialog']['width'] = 144 + 16

    def initDialog(self):
        self.ajax_settings['dialog'] = {
            'autoOpen': True,
            'modal': False,
            'resizable': False,
            'draggable': True,
            'position': ['center','middle'],
            'width': 'auto',
            }

    def items(self):
        result = []
        scoresystem = querySkillScoreSystem()
        for score in scoresystem.scores:
            result.append({
                    'score': score[0],
                    'rating': score[1],
                    })
        return result
