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
"""CanDo Gradebook."""

from zope.annotation.interfaces import IAnnotations
from zope.component import adapts, adapter, queryMultiAdapter
from zope.component import getMultiAdapter
from zope.interface import implements, implementer
from zope.location.location import LocationProxy
from zope.publisher.interfaces import IPublishTraverse
from zope.security import proxy

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.basicperson.interfaces import IBasicPerson
from schooltool.course.interfaces import ISection
from schooltool.gradebook.activity import ensureAtLeastOneWorksheet
from schooltool.gradebook.gradebook import Gradebook
from schooltool.gradebook.gradebook import StudentGradebook
from schooltool.gradebook.gradebook import getActivityScore
from schooltool.gradebook.gradebook import CURRENT_SECTION_TAUGHT_KEY
from schooltool.gradebook.gradebook import CURRENT_SECTION_ATTENDED_KEY
from schooltool.requirement.interfaces import IHaveEvaluations
from schooltool.requirement.interfaces import IScore

from schooltool.cando.interfaces import ICanDoGradebook
from schooltool.cando.interfaces import IMySkillsGrades
from schooltool.cando.interfaces import IProject
from schooltool.cando.interfaces import IProjects
from schooltool.cando.interfaces import IProjectsGradebook
from schooltool.cando.interfaces import ISectionSkills
from schooltool.cando.interfaces import ISkillsGradebook
from schooltool.cando.interfaces import ISectionSkillSet
from schooltool.cando.interfaces import ISkill
from schooltool.cando.interfaces import ICanDoStudentGradebook
from schooltool.cando.project import Project
from schooltool.cando import CanDoMessage as _


def ensureAtLeastOneProject(worksheets):
    ensureAtLeastOneWorksheet(worksheets, Project, _('Project1'))


def getCurrentSectionTaught(person):
    person = proxy.removeSecurityProxy(person)
    ann = IAnnotations(person)
    if CURRENT_SECTION_TAUGHT_KEY not in ann:
        ann[CURRENT_SECTION_TAUGHT_KEY] = None
    else:
        section = ann[CURRENT_SECTION_TAUGHT_KEY]
        try:
            IProjects(section)
        except:
            ann[CURRENT_SECTION_TAUGHT_KEY] = None
    return ann[CURRENT_SECTION_TAUGHT_KEY]


def getCurrentSectionAttended(person):
    person = proxy.removeSecurityProxy(person)
    ann = IAnnotations(person)
    if CURRENT_SECTION_ATTENDED_KEY not in ann:
        ann[CURRENT_SECTION_ATTENDED_KEY] = None
    else:
        section = ann[CURRENT_SECTION_ATTENDED_KEY]
        try:
            IProjects(section)
        except:
            ann[CURRENT_SECTION_ATTENDED_KEY] = None
    return ann[CURRENT_SECTION_ATTENDED_KEY]


class ProjectsGradebook(Gradebook):

    implements(IProjectsGradebook)
    adapts(IProject)

    # XXX: Merge with Gradebook and GradebookBase
    def __init__(self, context):
        self.context = context
        # To make URL creation happy
        self.__parent__ = context
        self.section = self.context.__parent__.__parent__
        # Establish worksheets and all activities
        worksheets = IProjects(self.section)
        ensureAtLeastOneProject(worksheets)
        self.worksheets = list(worksheets.values())
        self.activities = []
        for activity in context.values():
            self.activities.append(activity)
        self.students = list(self.section.members)
        self.__name__ = 'gradebook-projects'

    def getCurrentWorksheet(self, person):
        section = self.section
        worksheets = IProjects(section)
        current = worksheets.getCurrentWorksheet(person)
        return current

    def setCurrentWorksheet(self, person, worksheet):
        section = self.section
        worksheets = IProjects(section)
        worksheet = proxy.removeSecurityProxy(worksheet)
        worksheets.setCurrentWorksheet(person, worksheet)

    def filterEquivalent(self, equivalent):
        # select only equivalent skills that belong to this section
        return filter(
            lambda e: ISection(e.__parent__, None) is self.section,
            equivalent)

    def evaluate(self, student, activity, score, evaluator=None):
        super(ProjectsGradebook, self).evaluate(
            student, activity, score, evaluator)
        equivalent = self.filterEquivalent(activity.findAllEquivalent())
        for skill in equivalent:
            worksheet = skill.__parent__
            gradebook = ISkillsGradebook(worksheet, None)
            if gradebook is not None:
                gradebook.evaluate(student, skill, score, evaluator)

    def removeEvaluation(self, student, activity, evaluator=None):
        super(ProjectsGradebook, self).removeEvaluation(
            student, activity, evaluator)
        equivalent = self.filterEquivalent(activity.findAllEquivalent())
        for skill in equivalent:
            worksheet = skill.__parent__
            gradebook = ISkillsGradebook(worksheet, None)
            if gradebook is not None:
                gradebook.removeEvaluation(student, skill, evaluator)


class SkillsGradebook(Gradebook):

    implements(ISkillsGradebook)
    adapts(ISectionSkillSet)

    # XXX: Merge with Gradebook and GradebookBase
    def __init__(self, context):
        self.context = context
        # To make URL creation happy
        self.__parent__ = context
        self.section = self.context.__parent__.__parent__
        # Establish worksheets and all activities
        worksheets = ISectionSkills(self.section)
        self.worksheets = list(worksheets.values())
        self.activities = []
        for activity in context.values():
            self.activities.append(activity)
        self.students = list(self.section.members)
        self.__name__ = 'gradebook-skills'

    def getCurrentWorksheet(self, person):
        section = self.section
        worksheets = ISectionSkills(section)
        current = worksheets.getCurrentWorksheet(person)
        return current

    def setCurrentWorksheet(self, person, worksheet):
        section = self.section
        worksheets = ISectionSkills(section)
        worksheet = proxy.removeSecurityProxy(worksheet)
        worksheets.setCurrentWorksheet(person, worksheet)


class MySkillsGrades(SkillsGradebook):

    implements(IMySkillsGrades)
    adapts(ISectionSkillSet)

    def __init__(self, context):
        super(MySkillsGrades, self).__init__(context)
        # To make URL creation happy
        self.__name__ = 'mygrades-skills'


def getMySkillsGradesSection(gradebook):
    return ISection(gradebook.context)


@adapter(IHaveEvaluations, ISkill)
@implementer(IScore)
def getSkillScore(evaluatee, skill):
    return getActivityScore(evaluatee, skill)


class ProjectGradebookTraverser(object):

    implements(IPublishTraverse)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        context = proxy.removeSecurityProxy(self.context)
        try:
            activity = context[name]
            return activity
        except KeyError:
            if name == 'gradebook':
                gb = IProjectsGradebook(context)
                gb = LocationProxy(gb, self.context, name)
                gb.__setattr__('__parent__', gb.__parent__)
                return gb
            elif name == 'mygrades':
                pass
            else:
                return queryMultiAdapter((self.context, request), name=name)


class SkillsGradebookTraverser(object):

    implements(IPublishTraverse)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        context = proxy.removeSecurityProxy(self.context)
        try:
            activity = context[name]
            return activity
        except KeyError:
            if name == 'gradebook':
                gb = ISkillsGradebook(context)
                gb = LocationProxy(gb, self.context, name)
                gb.__setattr__('__parent__', gb.__parent__)
                return gb
            elif name == 'mygrades':
                gb = IMySkillsGrades(context)
                gb = LocationProxy(gb, self.context, name)
                gb.__setattr__('__parent__', gb.__parent__)
                return gb
            else:
                return queryMultiAdapter((self.context, request), name=name)


def getCourseSkillSetSection(worksheet):
    return worksheet.__parent__.__parent__


class CanDoStudentGradebook(StudentGradebook):

    implements(ICanDoStudentGradebook)
    adapts(IBasicPerson, ICanDoGradebook)

    def __init__(self, *args, **kw):
        super(CanDoStudentGradebook, self).__init__(*args, **kw)
        self.__parent__ = self.gradebook.__parent__


class CanDoStudentGradebookTraverser(object):

    implements(IPublishTraverse)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        app = ISchoolToolApplication(None)
        context = proxy.removeSecurityProxy(self.context)

        try:
            student = app['persons'][name]
        except KeyError:
            return queryMultiAdapter((self.context, request), name=name)

        try:
            gb = getMultiAdapter((student, context), ICanDoStudentGradebook)
        except ValueError:
            return queryMultiAdapter((self.context, request), name=name)

        # location looks like http://host/path/to/gradebook/studentsUsername
        gb = LocationProxy(gb, self.context, name)
        return gb
