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
"""Gradebook projects."""
from persistent.dict import PersistentDict

from zope.annotation.interfaces import IAnnotations
from zope.interface import implements, implementer
from zope.event import notify
from zope.component import adapter
from zope.container.contained import containedEvent
from zope.container.interfaces import INameChooser
from zope.keyreference.interfaces import IKeyReference
from zope.proxy import sameProxiedObjects

from schooltool.requirement.requirement import Requirement
from schooltool.gradebook.activity import Worksheets, Worksheet
from schooltool.cando.interfaces import IProjects, IProject
from schooltool.cando.interfaces import ICourseProjects, ICourseProject
from schooltool.cando.skill import SkillSet
from schooltool.course.interfaces import ISection, ICourse

from schooltool.cando import CanDoMessage as _

SECTION_PROJECTS_KEY = 'schooltool.cando.project.sectionprojects'
COURSE_PROJECTS_KEY = 'schooltool.cando.project.courseprojects'


class Projects(Worksheets):
    implements(IProjects)

    annotations_current_worksheet_key = 'schooltool.cando.project.currentworksheet'


class Project(SkillSet, Worksheet):
    implements(IProject)


class CourseProjects(Requirement):
    implements(ICourseProjects)

    deployed_projects = None

    def __init__(self, *args, **kw):
        self.deployed_projects = PersistentDict()

    def isDeployed(self, project, section):
        if (project.__name__ not in self or
            not sameProxiedObjects(project.__parent__, self)):
            raise KeyError(project.__name__)
        project_hash = hash(IKeyReference(project))
        section_hash = hash(IKeyReference(section))
        if project_hash not in self.deployed_projects:
            return False
        if section_hash not in self.deployed_projects[project_hash]:
            return False
        return True

    def markDeployed(self, project, deployed_project):
        if (project.__name__ not in self or
            not sameProxiedObjects(project.__parent__, self)):
            raise KeyError(project.__name__)
        project_hash = hash(IKeyReference(project))
        section = ISection(deployed_project.__parent__)
        section_hash = hash(IKeyReference(section))
        if project_hash not in self.deployed_projects:
            self.deployed_projects[project_hash] = PersistentDict()
        deployed_hash = hash(IKeyReference(deployed_project))
        self.deployed_projects[project_hash][section_hash] = deployed_hash
        deployed_project.deployed = True

    def deploy(self, project, section):
        if (project.__name__ not in self or
            not sameProxiedObjects(project.__parent__, self)):
            raise KeyError(project.__name__)
        if self.isDeployed(project, section):
            return

        section_projects = IProjects(section)
        deployed_project = Project(title=project.title,
                                   description=project.description)
        chooser = INameChooser(section_projects)
        name = chooser.chooseName(project.__name__, deployed_project)
        section_projects[name] = deployed_project

        for skill in project.values():
            new_skill = deployed_project.add(skill)
            skill.equivalent.add(new_skill)

        self.markDeployed(project, deployed_project)


class CourseProject(SkillSet):
    implements(ICourseProject)

    @property
    def deployed(self):
        course_projects = self.__parent__
        course = ICourse(course_projects)
        for section in course.sections:
            if not course_projects.isDeployed(self, section):
                return False
        return True


@adapter(ICourse)
@implementer(ICourseProjects)
def getCourseProjects(course):
    annotations = IAnnotations(course)
    try:
        return annotations[COURSE_PROJECTS_KEY]
    except KeyError:
        projects = CourseProjects(_('Course Projects'))
        annotations[COURSE_PROJECTS_KEY] = projects
        # Sigh, this is not good.
        projects, event = containedEvent(projects, course, 'projects')
        notify(event)
        return projects

# Convention to make adapter introspectable
getCourseProjects.factory = CourseProjects


@adapter(ICourseProjects)
@implementer(ICourse)
def getCourseFromProjects(projects):
    annotations = projects.__parent__
    course = annotations.__parent__
    return course


@adapter(ISection)
@implementer(IProjects)
def getSectionProjects(section):
    annotations = IAnnotations(section)
    try:
        return annotations[SECTION_PROJECTS_KEY]
    except KeyError:
        projects = Projects(_('Projects'))
        annotations[SECTION_PROJECTS_KEY] = projects
        # Sigh, this is not good.
        projects, event = containedEvent(projects, section, 'projects')
        notify(event)
        return projects

getSectionProjects.factory = Projects


@adapter(IProjects)
@implementer(ISection)
def getSectionFromProjects(projects):
    annotations = projects.__parent__
    section = annotations.__parent__
    return section
