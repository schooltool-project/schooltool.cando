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
Evolve database to generation 2.

Fix the mess made by evolution 1.
"""

from zope.annotation.interfaces import IAnnotations
from zope.app.generations.utility import findObjectsProviding, getRootFolder
from zope.component.hooks import getSite, setSite
from zope.keyreference.interfaces import IKeyReference

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.cando.course import getSectionSkills
from schooltool.cando.course import SectionSkill
from schooltool.cando.generations.evolve1 import pick_section

EVALUATIONS_KEY = "schooltool.evaluations"


def findSkill(score, section):
    section_worksheets = getSectionSkills(section)
    skill_name = score.requirement.__name__
    skillset_name = score.requirement.__parent__.__name__
    for section_skill_set in section_worksheets.values():
        for skill_key in section_skill_set.all_keys():
            skill = section_skill_set[skill_key]
            if (skill_name == skill.source_skill_name and
                skillset_name == skill.source_skillset_name):
                return skill
    return None


def findCandidateSection(score):
    courses = list(score.requirement.section.courses)

    evaluator_sections = []
    sections_attended = []
    for course in courses:
        for section in course.sections:
            instructors = [i.__name__ for i in section.instructors]
            if (score.evaluator in instructors and
                section not in evaluator_sections):
                evaluator_sections.append(section)
            if (score.evaluatee in section.members and
                section not in sections_attended):
                sections_attended.append(section)
    likely_sections = [section for section in sections_attended
                       if section in evaluator_sections]
    target_section = pick_section(score, likely_sections)
    if target_section is None:
        # Maybe evaulator has changed. Try picking sections
        # of this course attended by evaluatee
        target_section = pick_section(score, sections_attended)
    if target_section is None:
        # Try picking sections of this course taught by evaluator
        target_section = pick_section(score, evaluator_sections)
    if target_section is not None:
        return target_section
    return score.requirement.section


def isOlder(older_score, newer_score):
    if not older_score or not newer_score:
        return None
    return older_score.time <= newer_score.time


def replayScore(evaluations, score, skill):
    score.requirement = skill
    skill_ref = IKeyReference(skill)
    history = None

    if (evaluations._history is not None):
        history = evaluations._history.get(skill_ref)

    if (skill_ref not in evaluations._btree and
        not history):
        # No scores yet, so simply add it
        evaluations[skill] = score
        return

    # Our score is newer, so just set it
    latest_score = evaluations._btree.get(skill_ref)
    if isOlder(latest_score, score):
        evaluations[skill] = score
        return

    if not history:
        if not latest_score:
            evaluations[skill] = score
        else:
            # There is a newer score, but no other scores.  Just keep it.
            evaluations.appendToHistory(skill, score)
        return

    insert_before = None

    for index, historical_score in enumerate(history):
        if (historical_score is not None and
            not isOlder(historical_score, score)):
            # The score in history is newer than our misplaced score
            insert_before = index
            break

    # Score may want to be on top of history
    if insert_before is None:
        if not latest_score:
            evaluations[skill] = score
        else:
            evaluations.appendToHistory(skill, score)
    evaluations._history[skill_ref].insert(insert_before, score)


def fixSkillScores(app, person):
    annotations = IAnnotations(person)
    if EVALUATIONS_KEY not in annotations:
        return
    evaluations = annotations[EVALUATIONS_KEY]

    misplaced_scores = []
    refs = set(evaluations._history or []).union(set(evaluations._btree or []))

    for ref in refs:
        skill = ref()
        if not isinstance(skill, SectionSkill):
            continue
        if ref in evaluations._history:
            for n, score in enumerate(evaluations._history[ref]):
                if (score is None or
                    not isinstance(score.requirement, SectionSkill)):
                    continue
                section = findCandidateSection(score)
                if section is score.requirement.section:
                    continue
                skill = findSkill(score, section)
                if skill is None:
                    continue
                misplaced_scores.append((score, skill))
                evaluations._history.pop(n)
        if ref in evaluations._btree:
            score = evaluations._btree[ref]
            if (score is not None and
                isinstance(score.requirement, SectionSkill)):
                section = findCandidateSection(score)
                if section is not score.requirement.section:
                    skill = findSkill(score, section)
                    if skill is not None:
                        misplaced_scores.append((score, skill))
                        del evaluations._btree[ref]
                        if (ref in evaluations._history and
                            evaluations._history[ref]):
                            evaluations._btree[ref] = evaluations._history.pop()

    for score, skill in misplaced_scores:
        replayScore(evaluations, score, skill)


def evolve(context):
    root = getRootFolder(context)

    old_site = getSite()
    apps = findObjectsProviding(root, ISchoolToolApplication)
    for app in apps:
        setSite(app)

        for person in app['persons'].values():
            fixSkillScores(app, person)

    setSite(old_site)
