#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2013 Shuttleworth Foundation
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
Evolve database to generation 3.

Sets equivalent course skill for section skills.

Fixes a bug caused by the old skills importer (before rev 154) where
equivalent were removed for global skills, affecting also course
skills and breaking projects.
"""

from zope.annotation.interfaces import IAnnotations
from zope.app.generations.utility import findObjectsProviding, getRootFolder
from zope.component.hooks import getSite, setSite

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.relationships import CourseSections
from schooltool.relationship.relationship import relate

from schooltool.cando.course import COURSE_SKILLS_KEY
from schooltool.cando.course import SECTION_SKILLS_KEY
from schooltool.cando.skill import EquivalentSkills
from schooltool.cando.skill import URIEquivalent
from schooltool.cando.skill import URISkill


def getCourseSkillSets(course):
    course_annotations = IAnnotations(course)
    return course_annotations.get(COURSE_SKILLS_KEY, {})


def getSectionSkillSets(section):
    section_annotations = IAnnotations(section)
    return section_annotations.get(SECTION_SKILLS_KEY, {})


def evolveSectionSkills(section, course_skillsets):
    section_skillsets = getSectionSkillSets(section)
    for section_skillset in section_skillsets.values():
        course_skillset = course_skillsets[section_skillset.__name__]
        for section_skill in section_skillset.values():
            equivalent = list(EquivalentSkills.query(skill=section_skill))
            course_skill = course_skillset[section_skill.__name__]
            if course_skill not in equivalent:
                relate(URIEquivalent,
                       (section_skill, URISkill),
                       (course_skill, URISkill))


def evolve(context):
    root = getRootFolder(context)
    old_site = getSite()
    apps = findObjectsProviding(root, ISchoolToolApplication)
    for app in apps:
        setSite(app)
        for cc in app['schooltool.course.course'].values():
            for course in cc.values():
                course_skillsets = getCourseSkillSets(course)
                if course_skillsets:
                    course_sections = list(CourseSections.query(course=course))
                    for section in course_sections:
                        evolveSectionSkills(section, course_skillsets)
    setSite(old_site)
