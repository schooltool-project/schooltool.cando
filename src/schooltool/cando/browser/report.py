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
CanDo report views.
"""

import math
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.cachedescriptors.property import Lazy
from zope.component import getUtility
from zope.i18n.interfaces.locales import ICollator
from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser.absoluteurl import absoluteURL
from zc.table.column import GetterColumn
import zc.resourcelibrary

from schooltool import table
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.basicperson.interfaces import IDemographics
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.course.interfaces import ISection, ISectionContainer
from schooltool.course.interfaces import ICourseContainer
from schooltool.person.interfaces import IPersonFactory
from schooltool.report.report import ReportLinkViewlet
from schooltool.requirement.scoresystem import UNSCORED
from schooltool.resource.interfaces import ILocation
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.skin import flourish

from schooltool.cando.interfaces import ISectionSkills
from schooltool.cando.interfaces import ISkillsGradebook
from schooltool.cando.skill import querySkillScoreSystem
from schooltool.cando import CanDoMessage as _


placeholder = object()


class SkillsGradebookReportLink(ReportLinkViewlet):

    @property
    def report_link(self):
        skills = ISectionSkills(self.context)
        if skills:
            skillset = skills.values()[0]
            return '%s/gradebook/%s' % (absoluteURL(skillset, self.request),
                                        self.link)

    def render(self, *args, **kw):
        if not self.report_link:
            return ''
        return super(SkillsGradebookReportLink, self).render(*args, **kw)


class SectionReportViewBase(flourish.page.Page):

    passing_score_filter_id = 'passing-score-filter'

    @property
    def subtitle(self):
        return self.section.title

    @Lazy
    def gradebook(self):
        return removeSecurityProxy(self.context)

    @Lazy
    def section(self):
        return ISection(self.gradebook)

    @Lazy
    def scoresystem(self):
        return querySkillScoreSystem()

    @Lazy
    def default_passing_score(self):
        scores = self.scoresystem.scoresDict()
        return scores[self.scoresystem._minPassingScore]

    @Lazy
    def passing_scores(self):
        result = []
        for score in self.scoresystem.scores:
            label, abbr, value, percent = score
            result.append({
                    'value': value,
                    'submit_value': label,
                    'label': abbr,
                    'default': value == self.default_passing_score,
                    })
        return result

    @property
    def passing_score(self):
        passing_score_filter_id = self.passing_score_filter_id
        submitted_passing_score = self.request.get(passing_score_filter_id)
        if submitted_passing_score is not None:
            for score in self.passing_scores:
                if submitted_passing_score == score['submit_value']:
                    return score['value']
        return self.default_passing_score

    def render(self, *args, **kw):
        zc.resourcelibrary.need('schooltool.skin.flourish-report')
        return super(SectionReportViewBase, self).render(*args, **kw)


class SectionReportDetailsViewletBase(flourish.viewlet.Viewlet):

    @property
    def course(self):
        course_titles = []
        course_government_ids = []
        section = self.view.section
        for course in section.courses:
            course_titles.append(course.title)
            course_government_ids.append(course.government_id or '')
        return {
            'title': ', '.join(course_titles),
            'government_id': ', '.join(course_government_ids),
            }

    @property
    def instructors(self):
        instructors = []
        section = self.view.section
        for person in section.instructors:
            instructors.append(person.title)
        return '<br />'.join(instructors)


class SectionReportView(SectionReportViewBase):

    form_container_id = 'section-report-form-container'
    passing_target_filter_id = 'passing-target-filter'
    skill_type_filter_id = 'skill-type-filter'
    score_colors_container_id = 'score-colors-container'
    default_skill_type = 'all'
    default_passing_target = 80
    colors = {'passing': {'start': '#6B3A89', 'end': '#D1C4DA'},
              'not_passing': {'start': '#F68E4D', 'end': '#FCD6C5'}}

    @Lazy
    def skills(self):
        result = []
        for worksheet in ISectionSkills(self.section).values():
            gradebook = ISkillsGradebook(worksheet)
            for skill in worksheet.values():
                result.append((skill, gradebook))
        return self.filter_skills(result)

    def filter_skills(self, skills):
        if self.skill_type == 'required':
            condition = lambda (skill, gradebook): skill.required
        else:
            condition = None
        return filter(condition, skills)

    @Lazy
    def passing_targets(self):
        result = []
        start = 10
        end = 100
        step = 10
        for value in range(start, end, step):
            result.append({
                    'value': value,
                    'submit_value': str(value),
                    'default': value == self.default_passing_target,
                    })
        return result

    @property
    def passing_target(self):
        passing_target_filter_id = self.passing_target_filter_id
        submitted_passing_target = self.request.get(passing_target_filter_id)
        if submitted_passing_target is not None:
            for target in self.passing_targets:
                if submitted_passing_target == target['submit_value']:
                    return target['value']
        return self.default_passing_target

    @Lazy
    def skill_types(self):
        result = []
        labels = [_('All'), _('Required'), _('Evaluated')]
        for label in labels:
            value = str(label).lower()
            result.append({
                    'value': value,
                    'submit_value': value,
                    'label': label,
                    'default': value == self.default_skill_type,
                    })
        return result

    @property
    def skill_type(self):
        skill_type_filter_id = self.skill_type_filter_id
        submitted_skill_type = self.request.get(skill_type_filter_id)
        if submitted_skill_type is not None:
            for skill_type in self.skill_types:
                if submitted_skill_type == skill_type['submit_value']:
                    return skill_type['value']
        return self.default_skill_type

    def studentSkillsData(self, student):
        grouped_by_score = {}
        count = 0
        evaluated = 0
        for skill, gradebook in self.skills:
            count += 1
            score = gradebook.getScore(student, skill)
            if score is not None and score.value is not UNSCORED:
                evaluated += 1
                if score.value not in grouped_by_score:
                    grouped_by_score[score.value] = 0
                grouped_by_score[score.value] += 1
        return grouped_by_score, evaluated, count

    def getChartData(self, student):
        result = {
            'student': student,
            'container_id': flourish.page.sanitize_id(
                'skills-data-%s' % student.username),
            }
        grouped_by_score, evaluated, total = self.studentSkillsData(student)
        if self.skill_type == 'evaluated':
            skills_count = evaluated
        else:
            skills_count = total
        result['skills_count'] = skills_count
        result['chart_scores'] = self.getChartScores(grouped_by_score,
                                                     skills_count)
        return result

    def getChartScores(self, student_data, skills_count):
        passing = []
        not_passing = []
        for passing_score in reversed(self.passing_scores):
            is_passing = passing_score['value'] >= self.passing_score
            if is_passing:
                score_list = passing
            else:
                score_list = not_passing
            count = student_data.get(passing_score['submit_value'], 0)
            score_list.append({
                    'count': count,
                    'is_passing': is_passing,
                    'label': passing_score['label'],
                    'submit_value': passing_score['submit_value'],
                    'value': float(passing_score['value']),
                    })
        not_passing_length = len(not_passing)
        passing_length = len(passing)
        for index, score_info in enumerate(not_passing):
            x = sum([info['count'] for info in not_passing[index:]])
            try:
                count = student_data.get(score_info['submit_value'], 0)
                percentage = (count * 100.0) / skills_count
            except (ZeroDivisionError,):
                percentage = 0
            if not_passing_length > 1:
                color_weight = float(index) / (not_passing_length - 1)
            else:
                color_weight = float(index) / not_passing_length
            score_info.update({
                    'x': -x,
                    'color_weight': color_weight,
                    'above_passing_target': False,
                    'percentage': '%.1f%%' % percentage,
                    })
        for index, score_info in enumerate(passing):
            x = sum([info['count'] for info in passing[:index+1]])
            try:
                count = student_data.get(score_info['submit_value'], 0)
                percentage = (count * 100.0) / skills_count
            except (ZeroDivisionError,):
                percentage = 0
            try:
                above_passing_target = (x * 100.0 / skills_count) >= self.passing_target
            except (ZeroDivisionError,):
                above_passing_target = False
            if passing_length > 1:
                color_weight = 1 - (float(index) / (passing_length - 1))
            else:
                color_weight = 1 - (float(index) / passing_length)
            score_info.update({
                    'x': x,
                    'color_weight': color_weight,
                    'above_passing_target': above_passing_target,
                    'percentage': '%.1f%%' % percentage,
                    })
        passing.reverse()
        result = not_passing + passing
        return result


class SectionReportByStudentView(SectionReportView):

    pass


class ReportDetailsViewlet(SectionReportDetailsViewletBase):

    template = ViewPageTemplateFile(
        'templates/section_report_details.pt')


class SectionReportByStudentDescriptionViewlet(flourish.page.Related):

    template = InlineViewPageTemplate('''
      <tal:block i18n:domain="schooltool.virginia">
        <div class="header" i18n:translate="">
          Note:
        </div>
        <div class="body">
          <p i18n:domain="" i18n:translate="">
            Students are expected to achieve a satisfactory rating
            (one of the three highest marks) on the Student Competency
            Record (SCR) rating scale on at least 80% of the required
            (essential) competencies.
          </p>
        </div>
      </tal:block>
    ''')


class SectionReportTableViewlet(flourish.viewlet.Viewlet):

    template = InlineViewPageTemplate('''
      <div tal:content="structure view/view/providers/ajax/view/section/charts_table"/>
    ''')


def student_id_getter(item, formatter):
    student = item['student']
    demographics = IDemographics(student)
    return demographics.get('ID') or ''


class SectionReportChartsColumn(GetterColumn):

    template = ViewPageTemplateFile(
        'templates/section_report_charts_column.pt')


class SkillsColumn(SectionReportChartsColumn):

    svg = {'width': 220, 'height': 12}

    @Lazy
    def chart(self):
        margins = {'top': 0, 'bottom': 0, 'left': 10, 'right': 10}
        w = self.svg['width'] - (margins['left'] + margins['right'])
        h = self.svg['height'] - (margins['top'] + margins['bottom'])
        return {'width': w, 'height': h, 'margins': margins}

    @property
    def passing_target_size(self):
        w = self.chart['width'] * ((self.passing_target/200.0)+0.5)
        return {'width': w, 'height': self.svg['height']}

    def __init__(self, passing_target, colors):
        self.passing_target = passing_target
        self.colors = colors
        title = _('% of Skills Below and Above Passing')
        name = 'skills'
        super(SkillsColumn, self).__init__(title, name=name)

    def renderCell(self, item, formatter):
        container_id = item['container_id']
        skills_count = item['skills_count']
        chart_scores = item['chart_scores']
        # XXX: hack to make the ViewPageTemplateFile to work
        self.context = item
        self.request = formatter.request
        return self.template(container_id=container_id,
                             svg_size=self.svg,
                             container_size=self.chart,
                             container_margins=self.chart['margins'],
                             skills_count=skills_count,
                             passing_target_size=self.passing_target_size,
                             scores=chart_scores,
                             colors=self.colors)


class StudentsColumn(SectionReportChartsColumn):

    def __init__(self, view):
        self.view = view
        self.total = len(view.section.members)
        title = _('Students (${count})',
                  mapping={'count': self.total})
        name = 'students'
        super(StudentsColumn, self).__init__(title, name=name)

    def renderCell(self, item, formatter):
        skill, gradebook = item
        container_id = 'skills-data-%s' % skill.__name__
        skill_data = self.skillScoresData(skill, gradebook)
        data = []
        passing_index = None
        scores = reversed(self.view.scoresystem.scores)
        score_labels = []
        for i, score in enumerate(scores):
            score_labels.append(score[1])
            data.append(skill_data[score[0]])
            if score[2] == self.view.passing_score:
                passing_index = i
        # XXX: hack to make the ViewPageTemplateFile to work
        self.context = item
        self.request = formatter.request
        return self.template(total=self.total,
                             passing_index=passing_index,
                             data=data,
                             container_id=container_id,
                             score_labels = score_labels,
                             passing_target=self.view.passing_target)

    def skillScoresData(self, skill, gradebook):
        result = {}
        for score in self.view.scoresystem.scores:
            result[score[0]] = 0
        for student in self.view.section.members:
            score = gradebook.getScore(student, skill)
            if score is not None and score.value is not UNSCORED:
                result[score.value] += 1
        return result


class SectionReportSortFormatter(table.ajax.AJAXFormSortFormatter):

    script_name = 'ST.report.on_section_report_sort'


class SectionReportChartsTable(table.ajax.Table):

    batch_size = 0
    table_formatter = SectionReportSortFormatter
    css_classes = ''

    @property
    def html_id(self):
        return self.view.form_container_id

    def updateFormatter(self):
        if self._table_formatter is None:
            self.setUp(table_formatter=self.table_formatter,
                       batch_size=self.batch_size,
                       prefix=self.__name__,
                       css_classes={'table': self.css_classes})


class ByStudentChartsTable(SectionReportChartsTable):

    css_classes = 'section-report section-report-by-student'
    visible_column_names = ['title', 'ID', 'skills']

    def columns(self):
        first_name = table.column.LocaleAwareGetterColumn(
            name='first_name',
            title=_(u'First Name'),
            getter=lambda i, f: i['student'].first_name,
            subsort=True)
        last_name = table.column.LocaleAwareGetterColumn(
            name='last_name',
            title=_(u'Last Name'),
            getter=lambda i, f: i['student'].last_name,
            subsort=True)
        title = table.column.LocaleAwareGetterColumn(
            name='title',
            title=_(u'Student'),
            getter=lambda i, f: i['student'].title,
            subsort=True)
        ID = table.column.LocaleAwareGetterColumn(
            name='ID',
            title=_(u'Student ID #'),
            getter=student_id_getter,
            subsort=True)
        skills = SkillsColumn(self.view.passing_target, self.view.colors)
        return [first_name, last_name, title, ID, skills]

    def sortOn(self):
        return getUtility(IPersonFactory).sortOn()

    def items(self):
        result = []
        for student in self.context.members:
            result.append(self.view.getChartData(student))
        return result


class PassingScoreFilterViewlet(flourish.page.RefineLinksViewlet): pass


class PassingScoreFilterMenuViewlet(flourish.viewlet.Viewlet):

    template = InlineViewPageTemplate('''
      <select tal:attributes="id view/view/passing_score_filter_id;
                              name view/view/passing_score_filter_id;"
              class="select-widget report-filter">
        <option tal:repeat="option view/options"
                tal:content="option/title"
                tal:attributes="value option/value;
                                selected option/selected;"
                />
      </select>
    ''')

    def options(self):
        result = []
        for passing_score in self.view.passing_scores:
            selected = passing_score['value'] == self.view.passing_score
            result.append({
                    'value': passing_score['submit_value'],
                    'title': passing_score['label'],
                    'selected': selected,
                    })
        return result


class SkillTypeFilterViewlet(flourish.page.RefineLinksViewlet): pass


class SkillTypeFilterOptionsViewlet(flourish.viewlet.Viewlet):

    template = InlineViewPageTemplate('''
      <ul class="filter">
        <li tal:repeat="option view/options">
          <input type="radio" class="report-filter"
                 tal:attributes="id option/id;
                                 name view/view/skill_type_filter_id;
                                 value option/value;
                                 checked option/selected;"
                 />
          <label tal:attributes="for option/id"
                 tal:content="option/title" />
        </li>
      </ul>
    ''')

    def options(self):
        result = []
        skill_type_filter_id = self.view.skill_type_filter_id
        for skill_type in self.view.skill_types:
            option_id = '%s.%s' % (skill_type['submit_value'],
                                   skill_type_filter_id)
            selected = skill_type['value'] == self.view.skill_type
            result.append({
                    'id': option_id,
                    'value': skill_type['submit_value'],
                    'title': skill_type['label'],
                    'selected': selected,
                    })
        return result


class PassingTargetFilterViewlet(flourish.page.RefineLinksViewlet): pass


class PassingTargetFilterMenuViewlet(flourish.viewlet.Viewlet):

    template = InlineViewPageTemplate('''
      <select tal:attributes="id view/view/passing_target_filter_id;
                              name view/view/passing_target_filter_id;"
              class="select-widget report-filter">
        <option tal:repeat="option view/options"
                tal:content="option/title"
                tal:attributes="value option/value;
                                selected option/selected;"
                />
      </select>
    ''')

    def options(self):
        result = []
        for passing_target in self.view.passing_targets:
            selected = passing_target['value'] == self.view.passing_target
            result.append({
                    'value': passing_target['submit_value'],
                    'title': '%d%%' % passing_target['value'],
                    'selected': selected,
                    })
        return result


class SectionReportDoneButtonViewlet(flourish.viewlet.Viewlet):

    template = InlineViewPageTemplate('''
      <h3 i18n:domain="schooltool" class="done-link">
        <a tal:attributes="href view/nextURL" i18n:translate="">
          Done
        </a>
      </h3>
    ''')

    def nextURL(self):
        return absoluteURL(self.context, self.request)


class ScoreColorsViewlet(flourish.page.Related):

    template = ViewPageTemplateFile(
        'templates/section_report_score_colors.pt')


class ScoreColorColumn(GetterColumn):

    template = ViewPageTemplateFile(
        'templates/section_report_score_colors_column.pt')

    def __init__(self, *args, **kw):
        self.colors = kw.pop('colors')
        super(ScoreColorColumn, self).__init__(*args, **kw)

    def renderCell(self, item, formatter):
        container_id = 'score-color-%s' % item['submit_value']
        # XXX: hack to make the ViewPageTemplateFile to work
        self.context = item
        self.request = formatter.request
        return self.template(container_id=container_id,
                             score=item,
                             colors=self.colors)


class ScoreColorsTable(table.ajax.Table):

    batch_size = 0

    @property
    def html_id(self):
        return self.view.score_colors_container_id

    def columns(self):
        color = ScoreColorColumn(
            name='color',
            title=_(u'Score Colors'),
            colors=self.view.colors)
        return [color]

    def items(self):
        passing = []
        not_passing = []
        for passing_score in self.view.passing_scores:
            is_passing = passing_score['value'] >= self.view.passing_score
            if is_passing:
                score_list = passing
            else:
                score_list = not_passing
            score_list.append({
                    'submit_value': passing_score['submit_value'],
                    'is_passing': is_passing,
                    'label': passing_score['label'],
                    })
        not_passing_length = len(not_passing)
        passing_length = len(passing)
        for index, score in enumerate(passing):
            if passing_length > 1:
                score['color_weight'] = float(index) / (len(passing)-1)
            else:
                score['color_weight'] = float(index) / len(passing)              
        for index, score in enumerate(reversed(not_passing)):
            if not_passing_length > 1:
                score['color_weight'] = float(index) / (len(not_passing)-1)
            else:
                score['color_weight'] = float(index) / len(not_passing)
        return passing + not_passing

    def sortOn(self):
        return None

    def updateFormatter(self):
        if self._table_formatter is None:
            self.setUp(table_formatter=self.table_formatter,
                       batch_size=self.batch_size,
                       prefix=self.__name__,
                       css_classes={'table': 'score-colors-table'})


class SkillsCompletionReportViewBase(SectionReportView):

    container_class = 'container widecontainer'
    location_filter_id = 'location-filter'
    course_filter_id = 'course-filter'
    default_location = None
    default_course = None

    @property
    def subtitle(self):
        return self.context.title

    @Lazy
    def locations(self):
        result = []
        app = ISchoolToolApplication(None)
        collator = ICollator(self.request.locale)
        locations = filter(ILocation.providedBy, app['resources'].values())
        for location in sorted(locations,
                               key=lambda x:x.title,
                               cmp=collator.cmp):
            result.append({
                    'value': location,
                    'submit_value': location.__name__,
                    'label': location.title,
                    'default': location.__name__ == self.default_location,
                    })
        return result

    @property
    def location(self):
        location_filter_id = self.location_filter_id
        submitted_location = self.request.get(location_filter_id)
        if submitted_location is not None:
            for location in self.locations:
                if submitted_location == location['submit_value']:
                    return location['value']
        return self.default_location

    @Lazy
    def courses(self):
        result = []
        schoolyear = ISchoolYear(self.context)
        courses = ICourseContainer(schoolyear).values()
        collator = ICollator(self.request.locale)
        for course in sorted(courses,
                             key=lambda x:x.title,
                             cmp=collator.cmp):
            result.append({
                    'value': course,
                    'submit_value': course.__name__,
                    'label': course.title,
                    'default': course.__name__ == self.default_location,
                    })
        return result

    @property
    def course(self):
        course_filter_id = self.course_filter_id
        submitted_course = self.request.get(course_filter_id)
        if submitted_course is not None:
            for course in self.courses:
                if submitted_course == course['submit_value']:
                    return course['value']
        return self.default_course

    def getSkills(self, section):
        result = []
        for worksheet in ISectionSkills(section).values():
            gradebook = ISkillsGradebook(worksheet)
            for skill in worksheet.values():
                result.append((skill, gradebook))
        return self.filter_skills(result)


class SkillsCompletionReportView(SkillsCompletionReportViewBase):

    def sectionSkillsData(self, section):
        grouped_by_score = {}
        count = 0
        evaluated = {}
        student_count = len(list(section.members))
        for skill, gradebook in self.getSkills(section):
            count += 1
            for student in section.members:
                score = gradebook.getScore(student, skill)
                if score is not None and score.value is not UNSCORED:
                    if skill not in evaluated:
                        evaluated[skill] = skill
                    if score.value not in grouped_by_score:
                        grouped_by_score[score.value] = 0
                    grouped_by_score[score.value] += 1
        result = {}
        for key in grouped_by_score:
            result[key] = int(math.floor(grouped_by_score[key] /
                                         float(student_count)))
        return result, len(evaluated), count

    def getChartData(self, section):
        result = {
            'section': section,
            'container_id': flourish.page.sanitize_id(
                'skills-data-%s' % section.__name__),
            'courses': set(list(section.courses)),
            }
        grouped_by_score, evaluated, total = self.sectionSkillsData(section)
        if self.skill_type == 'evaluated':
            skills_count = evaluated
        else:
            skills_count = total
        result['skills_count'] = skills_count
        result['chart_scores'] = self.getChartScores(grouped_by_score,
                                                     skills_count)
        return result


class SkillsCompletionReportTableViewlet(flourish.viewlet.Viewlet):

    template = InlineViewPageTemplate('''
      <div tal:content="structure view/view/providers/ajax/view/context/skills_completion_report_table"/>
    ''')


class SkillsCompletionReportTableFormatter(SectionReportSortFormatter):

    pass


def get_section_title(item, formatter):
    section = item['section']
    if section is placeholder:
        return _('Totals')
    return section.title


def get_section_courses(item, formatter):
    if item['section'] is placeholder:
        return ''
    collator = ICollator(formatter.request.locale)
    courses = [course.title for course in item['courses']]
    return ', '.join(sorted(courses, cmp=collator.cmp))


def get_section_instructors(item, formatter):
    section = item['section']
    if section is placeholder:
        return ''
    collator = ICollator(formatter.request.locale)
    factory = getUtility(IPersonFactory)
    sorting_key = lambda x: factory.getSortingKey(x, collator)
    sorted_instructors = sorted(section.instructors, key=sorting_key)
    instructors = [person.title for person in sorted_instructors]
    return ', '.join(instructors)


def section_instructors_formatter(value, item, formatter):
    section = item['section']
    if section is placeholder:
        return ''
    collator = ICollator(formatter.request.locale)
    factory = getUtility(IPersonFactory)
    sorting_key = lambda x: factory.getSortingKey(x, collator)
    sorted_instructors = sorted(section.instructors, key=sorting_key)
    instructors = [person.title for person in sorted_instructors]
    return '<br />'.join(instructors)


class SkillsCompletionReportTable(SectionReportChartsTable):

    batch_size = 0
    css_classes = 'section-report skills-completion-report'
    table_formatter = SkillsCompletionReportTableFormatter
    group_by_column = 'course'
    visible_column_names = ['section', 'instructors', 'skills']

    def items(self):
        result = []
        sections = ISectionContainer(self.context).values()
        location = self.view.location
        if location is not None:
            sections = filter(lambda section: location in section.resources,
                              sections)
        for section in sections:
            result.append(self.view.getChartData(section))
        return result

    def columns(self):
        course = table.column.LocaleAwareGetterColumn(
            name='course',
            title=_('Course'),
            getter=get_section_courses)
        section = GetterColumn(
            name='section',
            title=_('Section'),
            getter=get_section_title)
        instructors = GetterColumn(
            name='instructors',
            title=_('Teachers'),
            getter=get_section_instructors,
            cell_formatter=section_instructors_formatter)
        skills = SkillsColumn(self.view.passing_target, self.view.colors)
        return [course, section, instructors, skills]

    def sortOn(self):
        return (('course', False), ('section', False))


class LocationFilterViewlet(flourish.page.RefineLinksViewlet): pass


class LocationFilterMenuViewlet(flourish.viewlet.Viewlet):

    template = InlineViewPageTemplate('''
      <select tal:attributes="id view/view/location_filter_id;
                              name view/view/location_filter_id;"
              class="select-widget report-filter">
        <option value="" i18n:domain="schooltool.virginia"
                i18n:translate="">All</option>
        <option tal:repeat="option view/options"
                tal:content="option/title"
                tal:attributes="value option/value;
                                selected option/selected;"
                />
      </select>
    ''')

    def options(self):
        result = []
        for location in self.view.locations:
            selected = location['value'] == self.view.location
            result.append({
                    'value': location['submit_value'],
                    'title': location['label'],
                    'selected': selected,
                    })
        return result
