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
"""Integration with SchoolTool course"""

from persistent.dict import PersistentDict
from zope.annotation.interfaces import IAnnotations
from zope.event import notify
from zope.interface import implements, implementer
from zope.cachedescriptors.property import Lazy
from zope.component import adapter
from zope.container.contained import containedEvent
from zope.location.location import LocationProxy
from zope.proxy.decorator import SpecificationDecoratorBase
from zope.proxy import getProxiedObject

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.cando.interfaces import ICourseSkills, ICourseSkillSet
from schooltool.cando.interfaces import ICourseSkill
from schooltool.cando.interfaces import ISectionSkills
from schooltool.cando.interfaces import ISkillSetContainer
from schooltool.gradebook.activity import Worksheets, GenericWorksheet
from schooltool.requirement.requirement import Requirement
from schooltool.course.interfaces import ISection, ICourse

from schooltool.cando import CanDoMessage as _


COURSE_SKILLS_KEY = 'schooltool.cando.project.courseskills'
SECTION_SKILLS_KEY = 'schooltool.cando.project.sectionskills'


class CourseSkills(Requirement):
    implements(ICourseSkills)


class ReadOnlyContainer(KeyError):
    pass


class CourseSkillSet(GenericWorksheet):
    implements(ICourseSkillSet)

    required = None
    retired = None

    def __init__(self, skillset):
        super(CourseSkillSet, self).__init__(skillset.title)
        self.required = PersistentDict()
        self.retired = PersistentDict()

    @Lazy
    def skillset(self):
        if self.__name__ is None:
            return None
        app = ISchoolToolApplication(None)
        ssc = ISkillSetContainer(app)
        return ssc.get(self.__name__)

    def keys(self):
        skillset = self.skillset
        return [key for key in skillset.keys()
                if not self.retired.get(key)]

    def __getitem__(self, key):
        skillset = self.skillset
        skill = skillset[key]
        cs = CourseSkill(skill)
        cs.__parent__ = self
        return cs

    def __setitem__(self, key, newobject):
        raise ReadOnlyContainer(key)

    def __delitem__(self, key):
        raise ReadOnlyContainer(key)


class CourseSkill(SpecificationDecoratorBase):
    """A skill proxy that allows overriding of required/retired attributes."""
    implements(ICourseSkill)

    __slots__ = ('__parent__', )

    @property
    def required(self):
        if self.__name__ not in self.__parent__.required:
            unproxied = getProxiedObject(self)
            return unproxied.required
        return self.__parent__.required[self.__name__]

    @required.setter
    def required(self, value):
        self.__parent__.required[self.__name__] = value

    @property
    def retired(self):
        if self.__name__ not in self.__parent__.retired:
            unproxied = getProxiedObject(self)
            return unproxied.retired
        return self.__parent__.retired[self.__name__]

    @retired.setter
    def retired(self, value):
        self.__parent__.retired[self.__name__] = value


@adapter(ICourse)
@implementer(ICourseSkills)
def getCourseSkills(course):
    annotations = IAnnotations(course)
    try:
        return annotations[COURSE_SKILLS_KEY]
    except KeyError:
        skills = CourseSkills(_('Course Skills'))
        annotations[COURSE_SKILLS_KEY] = skills
        # Sigh, this is not good.
        skills, event = containedEvent(skills, course, 'skills')
        notify(event)
        return skills

getCourseSkills.factory = CourseSkills


class SectionSkills(Worksheets):
    implements(ISectionSkills)

    annotations_current_worksheet_key = 'schooltool.cando.project.sectionskills'

    def getDefaultWorksheet(self):
        sheets = self.all_worksheets
        if sheets:
            return sheets[0]
        return None

    @property
    def courses(self):
        section = self.__parent__
        return sorted(section.courses, key=lambda c: c.__name__)

    @property
    def worksheets(self):
        return self.all_worksheets

    @property
    def all_worksheets(self):
        sheets = []
        courses = self.courses
        for course in courses:
            skills = []
            for skill in ICourseSkills(course).values():
                worksheet = LocationProxy(
                    skill,
                    container=self,
                    name=skill.__name__)
                skills.append(worksheet)
            sheets.extend(skills)
        return sheets

    def values(self):
        return self.worksheets

    def __getitem__(self, key):
        items = [(value.__name__, value)
                 for value in self.values()]
        return dict(items)[key]

    def keys(self):
        return [value.__name__ for value in self.values()]


@adapter(ISection)
@implementer(ISectionSkills)
def getSectionSkills(section):
    annotations = IAnnotations(section)
    try:
        return annotations[SECTION_SKILLS_KEY]
    except KeyError:
        skills = SectionSkills(_('Section Skills'))
        annotations[SECTION_SKILLS_KEY] = skills
        # Sigh, this is not good.
        skills, event = containedEvent(skills, section, 'skills')
        notify(event)
        return skills

getSectionSkills.factory = SectionSkills


# XXX: maybe course-skillset relationship views
# XXX: helper: linking of all node skillsets to course
# XXX: helper: copying (with resetting required=False) of skillsets
#              (and linking to course)
