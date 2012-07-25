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
from zope.catalog.interfaces import ICatalog
from zope.component import getUtility
from zope.container.interfaces import INameChooser
from zope.i18n import translate
from zope.i18n.interfaces.locales import ICollator
from zope.interface import directlyProvides
from zope.intid.interfaces import IIntIds
from zope.location.location import LocationProxy
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.security import proxy
import zc.table.column
from zc.table.interfaces import ISortableColumn

from z3c.form import form, field, button

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.catalog import buildQueryString
from schooltool.course.interfaces import ISection
from schooltool.common.inlinept import InheritTemplate
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.gradebook.browser.gradebook import FlourishGradebookOverview
from schooltool.gradebook.browser.gradebook import FlourishGradebookStartup
from schooltool.gradebook.browser.gradebook import FlourishGradeStudent
from schooltool.gradebook.browser.gradebook import GradebookStartupNavLink
from schooltool.gradebook.browser.gradebook import FlourishNamePopupMenuView
from schooltool.gradebook.browser.gradebook import FlourishActivityPopupMenuView
from schooltool.gradebook.browser.gradebook import GradebookTertiaryNavigationManager
from schooltool.gradebook.browser.gradebook import MyGradesTertiaryNavigationManager
from schooltool.gradebook.browser.gradebook import FlourishGradebookYearNavigationViewlet
from schooltool.gradebook.browser.gradebook import FlourishGradebookTermNavigationViewlet
from schooltool.gradebook.browser.gradebook import FlourishGradebookSectionNavigationViewlet
from schooltool.gradebook.browser.gradebook import FlourishMyGradesView
from schooltool.person.interfaces import IPerson
from schooltool.skin import flourish
from schooltool import table

from schooltool.cando.interfaces import ICourseSkills
from schooltool.cando.interfaces import IProject
from schooltool.cando.interfaces import IProjects
from schooltool.cando.interfaces import ISectionSkills
from schooltool.cando.interfaces import IProjectsGradebook
from schooltool.cando.interfaces import ISkillSetContainer
from schooltool.cando.interfaces import INodeContainer
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

    teacher_gradebook_view_name = 'gradebook-skills'
    student_gradebook_view_name = 'mygrades-skills'

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
        current_worksheet = worksheets.getCurrentWorksheet(person)
        url = absoluteURL(worksheets, self.request)
        if not worksheets:
            url = absoluteURL(self.context, self.request)
            if person in self.context.members:
                url += '/mygrades-projects'
            else:
                url += '/gradebook-projects'
            self.request.response.redirect(url)
            return
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

    list_class = 'filter gradebook-modes'

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
        return absoluteURL(self.worksheet, self.request) + '/gradebook'

    def updateActions(self):
        super(ProjectAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')


class CanDoNamePopupMenuView(FlourishNamePopupMenuView):

    def options(self, worksheet):
        options = [
            {
                'label': self.translate(_('Sort by')),
                'url': '?sort_by=student',
                },
            ]
        return options

    def processColumnPreferences(self):
        return


class SkillPopupMenuView(FlourishActivityPopupMenuView):

    def result(self):
        result = {}
        activity_id = self.request.get('activity_id')
        worksheet = proxy.removeSecurityProxy(self.context).context
        if activity_id is not None and activity_id in worksheet:
            activity = worksheet[activity_id]
            info = self.getActivityInfo(activity)
            info.update({
                    'canDelete': False,
                    'moveLeft': False,
                    'moveRight': False,
                    })
            result['header'] = info['longTitle']
            result['options'] = self.options(info, worksheet)
        return result

    def getActivityAttrs(self, activity):
        shortTitle, longTitle, bestScore = super(
            SkillPopupMenuView, self).getActivityAttrs(activity)
        if activity.label:
            longTitle = '%s: %s' % (activity.label, longTitle)
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


class CanDoGradebookTertiaryNavigationManager(
    GradebookTertiaryNavigationManager):

    template = ViewPageTemplateFile('templates/cando_third_nav.pt')

    @property
    def items(self):
        result = []
        gradebook = proxy.removeSecurityProxy(self.context)
        current = gradebook.context.__name__
        for worksheet in gradebook.worksheets:
            title = worksheet.title
            if ISkillsGradebook.providedBy(self.context) and \
               worksheet.skillset.label:
                title = '%s: %s' % (worksheet.skillset.label, title)
            url = '%s/gradebook' % absoluteURL(worksheet, self.request)
            classes = worksheet.__name__ == current and ['active'] or []
            if worksheet.deployed:
                classes.append('deployed')
            result.append({
                'class': classes and ' '.join(classes) or None,
                'viewlet': u'<a class="navbar-list-worksheets" title="%s" href="%s">%s</a>' % (title, url, title),
                })
        return result


class CanDoNavigationViewletBase(object):

    teacher_gradebook_view_name = 'gradebook-skills'
    student_gradebook_view_name = 'mygrades-skills'


class CanDoYearNavigationViewlet(
    CanDoNavigationViewletBase,
    FlourishGradebookYearNavigationViewlet): pass


class CanDoTermNavigationViewlet(
    CanDoNavigationViewletBase,
    FlourishGradebookTermNavigationViewlet): pass


class CanDoSectionNavigationViewlet(
    CanDoNavigationViewletBase,
    FlourishGradebookSectionNavigationViewlet): pass


class GradebookHelpLinks(flourish.page.RefineLinksViewlet):
    pass


class CourseSkillsViewlet(flourish.page.ModalFormLinkViewlet):

    @property
    def dialog_title(self):
        section = self.context.__parent__.__parent__.__parent__
        title = _('${section} Skills', mapping={'section': section.title})
        return translate(title, context=self.request)


class ScoreSystemHelpViewlet(flourish.page.ModalFormLinkViewlet):

    @property
    def dialog_title(self):
        title = _(u'Score System Help')
        return translate(title, context=self.request)


class ColorCodesHelpViewlet(flourish.page.ModalFormLinkViewlet):

    @property
    def dialog_title(self):
        title = _(u'Color Codes Help')
        return translate(title, context=self.request)


class CourseSkillsView(flourish.form.Dialog):

    def initDialog(self):
        super(CourseSkillsView, self).initDialog()
        self.ajax_settings['dialog']['modal'] = False
        self.ajax_settings['dialog']['draggable'] = True
        self.ajax_settings['dialog']['maxHeight'] = 640

    def update(self):
        flourish.form.Dialog.update(self)
        skillsets = []
        section = self.context.__parent__.__parent__.__parent__
        for course in section.courses:
            courseskills = ICourseSkills(course)
            for courseskillset in courseskills.values():
                skillset = proxy.removeSecurityProxy(courseskillset.skillset)
                skills = []
                for skill in courseskillset.values():
                    title = skill.title
                    if skill.label:
                        title = '%s: %s' % (skill.label, title)
                    skills.append(title)
                skillsets.append({
                        'label': skillset.label,
                        'title': skillset.title,
                        'skills': skills,
                        'id': skillset.__name__,
                        })
        self.skillsets = skillsets


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


class ColorCodesHelpView(flourish.form.Dialog):

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


class ProjectSkillBrowseView(flourish.page.Page):

    content_template = InlineViewPageTemplate('''
      <div tal:content="structure context/schooltool:content/ajax/table" />
    ''')


class SkillAddTertiaryNavigationManager(
    flourish.page.TertiaryNavigationManager):

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
        path = self.request['PATH_INFO']
        current = path[path.rfind('/')+1:]
        actions = [
            ('addSkillBrowse.html', _('XXX Browse and Select Skill XXX')),
            ('addSkillCreate.html', _('XXX Create New Skill XXX')),
            ]
        for action, title in actions:
            url = '%s/%s' % (absoluteURL(self.context, self.request), action)
            title = translate(title, context=self.request)
            result.append({
                'class': action == current and 'active' or None,
                'viewlet': u'<a href="%s">%s</a>' % (url, title),
                })
        return result


class SkillsTable(table.ajax.IndexedTable):

    @property
    def source(self):
        app = ISchoolToolApplication(None)
        return ISkillSetContainer(app)

    def columns(self):
        default = table.ajax.Table.columns(self)
        label = zc.table.column.GetterColumn(
            name='label',
            title=_(u'Label'),
            getter=lambda i, f: i.label or '')
        directlyProvides(label, ISortableColumn)
        return [label] + default

    def sortOn(self):
        return (('label', False), ("title", False),)


class SkillsTableFilter(table.ajax.IndexedTableFilter):

    template = ViewPageTemplateFile('templates/project_skill_table_filter.pt')
    title = _('Skill title, label, external ID and/or description')

    @property
    def search_title_id(self):
        return self.manager.html_id+"-title"

    @property
    def search_group_id(self):
        return self.manager.html_id+"-group"

    @property
    def parameters(self):
        return (self.search_title_id, self.search_group_id)

    def filter(self, items):
        if self.ignoreRequest:
            return items
        if self.search_group_id in self.request:
            group = self.groupContainer().get(self.request[self.search_group_id])
            if group:
                int_ids = getUtility(IIntIds)
                keys = set()
                for skillset in group.skillsets:
                    for skill in skillset.values():
                        keys.add(int_ids.queryId(skill))
                items = [item for item in items
                         if item['id'] in keys]
        if self.search_title_id in self.request:
            searchstr = self.request[self.search_title_id]
            query = buildQueryString(searchstr)
            if query:
                app = ISchoolToolApplication(None)
                container = ISkillSetContainer(app)
                catalog = ICatalog(container)
                result = catalog['text'].apply(query)
                items = [item for item in items
                         if item['id'] in result]
        return items

    def groupContainer(self):
        # XXX must know which group container to pick
        app = ISchoolToolApplication(None)
        return INodeContainer(app, {})

    def groups(self):
        groups = []
        container = self.groupContainer()
        collator = ICollator(self.request.locale)
        group_items = sorted(container.items(),
                             cmp=collator.cmp,
                             key=lambda (gid, g): g.title)
        for id, group in group_items:
            skills = []
            for skillset in group.skillsets:
                for skill in skillset.values():
                    skills.append(skill)
            if len(skills) > 0:
                groups.append({'id': id,
                               'title': "%s (%s)" % (group.title, len(skills))})
        return groups


class MySkillsGradesView(FlourishMyGradesView):

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


class MySkillsGradesYearNavigationViewlet(
    CanDoYearNavigationViewlet):

    isTeacher = False


class MySkillsGradesTermNavigationViewlet(
    CanDoTermNavigationViewlet):

    isTeacher = False


class MySkillsGradesSectionNavigationViewlet(
    CanDoSectionNavigationViewlet):

    isTeacher = False


class MySkillsGradesTertiaryNavigationManager(
    MyGradesTertiaryNavigationManager):

    template = ViewPageTemplateFile('templates/cando_third_nav.pt')

    @property
    def items(self):
        result = []
        gradebook = proxy.removeSecurityProxy(self.context)
        current = gradebook.context.__name__
        for worksheet in gradebook.worksheets:
            title = worksheet.title
            if ISkillsGradebook.providedBy(self.context) and \
               worksheet.skillset.label:
                title = '%s: %s' % (worksheet.skillset.label, title)
            url = '%s/mygrades' % absoluteURL(worksheet, self.request)
            classes = worksheet.__name__ == current and ['active'] or []
            if worksheet.deployed:
                classes.append('deployed')
            result.append({
                'class': classes and ' '.join(classes) or None,
                'viewlet': u'<a class="navbar-list-worksheets" title="%s" href="%s">%s</a>' % (title, url, title),
                })
        return result


class CanDoGradeStudent(FlourishGradeStudent):

    def updateWidgets(self, *args, **kw):
        super(CanDoGradeStudent, self).updateWidgets(*args, **kw)
        for widget in self.widgets.values():
            widget.field.description = None
