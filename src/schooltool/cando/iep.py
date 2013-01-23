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
"""Student Individualized Education Plan (IEP)"""

from persistent import Persistent
from persistent.dict import PersistentDict

from zope.annotation.interfaces import IAnnotations
from zope.component import adapter, getUtility
from zope.intid.interfaces import IIntIds
from zope.interface import implementer

from schooltool.basicperson.interfaces import IBasicPerson

from schooltool.cando.interfaces import ISectionSkills
from schooltool.cando.interfaces import IStudentIEP


STUDENT_IEP_KEY = 'schooltool.cando.iep'


class StudentIEP(Persistent):

    active = False
    description = None

    def __init__(self):
        super(StudentIEP, self).__init__()
        self.iep_skills = PersistentDict({})

    def getIEPSkills(self, section):
        result = {}
        int_ids = getUtility(IIntIds)
        section_id = int_ids.getId(section)
        section_iep_skills = self.iep_skills.get(section_id)
        if section_iep_skills is not None:
            section_skills = ISectionSkills(section)
            for skillset_id, skill_ids in section_iep_skills.items():
                skillset = section_skills.get(skillset_id)
                if skillset is not None:
                    result[skillset] = []
                    for skill_id in skill_ids:
                        skill = skillset.get(skill_id)
                        if skill is not None:
                            result[skillset].append(skill)
        return result

    def addSkill(self, section, skill):
        int_ids = getUtility(IIntIds)
        section_id = int_ids.getId(section)
        section_skills = ISectionSkills(section)
        skillset = skill.__parent__
        skillset_id = skillset.__name__
        if skillset_id in section_skills:            
            if section_id not in self.iep_skills:
                self.iep_skills[section_id] = {}
            section_iep_skills = self.iep_skills.get(section_id)
            if skillset_id not in section_iep_skills:
                section_iep_skills[skillset_id] = set()
            section_iep_skills[skillset_id].add(skill.__name__)

    def removeSkill(self, section, skill):
        int_ids = getUtility(IIntIds)
        section_id = int_ids.getId(section)
        section_iep_skills = self.iep_skills.get(section_id)
        if section_iep_skills is not None:
            skill_id = skill.__name__
            skillset = skill.__parent__
            skillset_id = skillset.__name__
            if skillset_id in section_iep_skills and \
               skill_id in section_iep_skills[skillset_id]:
                section_iep_skills[skillset_id].remove(skill_id)
        


@implementer(IStudentIEP)
@adapter(IBasicPerson)
def getStudentIEP(person):
    annotations = IAnnotations(person)
    try:
        return annotations[STUDENT_IEP_KEY]
    except KeyError:
        iep = StudentIEP()
        iep.__parent__ = person
        annotations[STUDENT_IEP_KEY] = iep
        return iep
