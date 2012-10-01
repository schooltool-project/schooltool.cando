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
Evolve database to generation 1.

Sections get copies of skils instead of proxies.
"""

from zope.annotation.interfaces import IAnnotations
from zope.app.generations.utility import findObjectsProviding, getRootFolder
from zope.component import getUtility
from zope.component.hooks import getSite, setSite
from zope.intid.interfaces import IIntIds

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.relationships import CourseSections
from schooltool.cando.course import getSectionSkills
from schooltool.cando.course import SectionSkillSet, SectionSkill

COURSE_SKILLS_KEY = 'schooltool.cando.project.courseskills'
EVALUATIONS_KEY = "schooltool.evaluations"


def deploySkillSet(skillset, sections):
    int_ids = getUtility(IIntIds)
    for section in sections:
        worksheets = getSectionSkills(section)
        section_intid = int_ids.getId(section)
        worksheet = worksheets[skillset.__name__] = SectionSkillSet(skillset)
        for skill_name in skillset.all_keys():
            skill = skillset[skill_name]
            if skill_name not in worksheet.all_keys():
                target_skill = worksheet[skill_name] = SectionSkill(skill.title)
                target_skill.equivalent.add(skill)
            for attr in ('external_id', 'label', 'description',
                         'required', 'retired'):
                val = getattr(skill, attr, None)
                setattr(target_skill, attr, val)
            target_skill.section_intid = section_intid
            target_skill.source_skill_name = skill.__name__
            target_skill.source_skillset_name = skill.__parent__.__name__


def reassignScoreSkill(section_worksheets, evaluations, score):
    skill_name = score.requirement.__name__
    skillset_name = score.requirement.__parent__.__name__
    for section_skill_set in section_worksheets.values():
        for skill_key in section_skill_set.all_keys():
            skill = section_skill_set[skill_key]
            if (skill_name == skill.source_skill_name and
                skillset_name == skill.source_skillset_name):
                del evaluations[score.requirement]
                score.requirement = skill
                evaluations.addEvaluation(score)
                return


def evolveCourse(app, course):
    annotations = IAnnotations(course)
    if COURSE_SKILLS_KEY not in annotations:
        return
    courseskills = annotations[COURSE_SKILLS_KEY]
    if not courseskills:
        return
    course_sections = list(CourseSections.query(course=course))
    if not course_sections:
        return

    instructor_sections = {}
    students = {}
    evaluations = {}
    for section in course_sections:
        for student in section.members:
            if student not in students:
                students[student.__name__] = students
            annotations = IAnnotations(student)
            if EVALUATIONS_KEY in annotations:
                evaluations[student.__name__] = annotations[EVALUATIONS_KEY]
        for instructor in section.instructors:
            instructor_sections[instructor.__name__] = section

    for course_skillset in courseskills.values():
        deploySkillSet(course_skillset, course_sections)

    worksheet_cache = {}

    for course_skillset in courseskills.values():
        for skill_name in course_skillset.all_keys():
            skill = course_skillset[skill_name]
            for student_id, student_evaluations in evaluations.items():
                scores = student_evaluations.getEvaluationsForRequirement(skill)
                if not scores:
                    continue
                for score in scores.values():
                    target_section = instructor_sections.get(score.evaluator)
                    if target_section is None:
                        continue
                    if id(target_section) not in worksheet_cache:
                        worksheet_cache[id(target_section)] = getSectionSkills(section)
                    reassignScoreSkill(worksheet_cache[id(target_section)],
                                       student_evaluations, score)


def evolve(context):
    root = getRootFolder(context)

    old_site = getSite()
    apps = findObjectsProviding(root, ISchoolToolApplication)
    for app in apps:
        setSite(app)

        for cc in app['schooltool.course.course'].values():
            for course in cc.values():
                evolveCourse(app, course)

    setSite(old_site)

