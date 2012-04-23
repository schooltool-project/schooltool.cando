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
from decimal import Decimal

from zope.interface import implements, implementer
from zope.component import adapter
from zope.container.btree import BTreeContainer
from zope.container.interfaces import INameChooser

from schooltool.app.app import InitBase, StartUpBase
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.cando import interfaces
from schooltool.relationship import URIObject
from schooltool.relationship import RelationshipSchema, RelationshipProperty
from schooltool.requirement.interfaces import IScoreSystemContainer
from schooltool.requirement.requirement import Requirement
from schooltool.requirement.scoresystem import CustomScoreSystem
from schooltool.requirement.scoresystem import GlobalDiscreteValuesScoreSystem


URISkill = URIObject(
    'http://schooltool.org/ns/cando/skill',
    'Skill',
    'A single skill.')

URISkillSet = URIObject(
    'http://schooltool.org/ns/cando/skillset',
    'Skillset',
    'A set of skills.')

URIEquivalent = URIObject(
    'http://schooltool.org/ns/cando/skill/equivalent',
    'Equivalent',
    'All equivalend skills.')

EquivalentSkills = RelationshipSchema(
    URIEquivalent,
    skill=URISkill,
    equivalent=URISkill)


class Skill(Requirement):
    implements(interfaces.ISkill)

    external_id = u''
    label = u''
    description = u''
    required = False
    retired = False

    equivalent = RelationshipProperty(URIEquivalent, URISkill, URISkill)

    def __init__(self, title, required=False, external_id=u'', label=u''):
        Requirement.__init__(self, title)
        self.required = required
        self.external_id = external_id
        self.label = label

    def findAllEquivalent(self):
        """Find indirectly equivalent skills."""
        visited = set()
        result = list()
        open = set(self.equivalent)
        while open:
            skill = open.pop()
            # XXX: proxies!
            if (skill not in visited and
                skill is not self):
                visited.add(skill)
                result.append(skill)
            open.update(set(skill.equivalent).difference(set(visited)))
        return result

    def copy(self):
        return Skill(title=self.title,
                     required=self.required,
                     external_id=self.external_id)

    def __repr__(self):
        desc = unicode(self.title)
        if len(desc) > 40:
            desc = desc[:17]+'...'+desc[-20:]
        return '<Skill %r>' % unicode(desc)


class SkillSetContainer(BTreeContainer):
    """Container of skill sets."""
    implements(interfaces.ISkillSetContainer)


class SkillSet(Requirement):
    implements(interfaces.ISkillSet)

    external_id = u''
    label = u''

    def __init__(self, title, external_id=u'', label=u''):
        Requirement.__init__(self, title)
        self.external_id = external_id
        self.label = label

    def add(self, skill):
        skill_copy = skill.copy()
        chooser = INameChooser(self)
        name = chooser.chooseName(skill.__name__, skill_copy)
        self[name] = skill_copy
        return skill_copy


class SkillInit(InitBase):

    def __call__(self):
        self.app['schooltool.cando.skillset'] = SkillSetContainer()


class SkillAppStartup(StartUpBase):
    def __call__(self):
        if 'schooltool.cando.skillset' not in self.app:
            self.app['schooltool.cando.skillset'] = SkillSetContainer()


@implementer(interfaces.ISkillSetContainer)
@adapter(ISchoolToolApplication)
def getSkillSetContainer(app):
    return app['schooltool.cando.skillset']


SkillScoreSystem = GlobalDiscreteValuesScoreSystem(
    'SkillScoreSystem',
    u'Competency', u'Skill Competency Score',
    [('4', u'Expert', Decimal(4), Decimal(90)),
     ('3', u'Competent', Decimal(3), Decimal(70)),
     ('2', u'Practicing', Decimal(2), Decimal(50)),
     ('1', u'Exposed', Decimal(1), Decimal(30)),
     ('0', u'No evidence', Decimal(0), Decimal(0))],
     '4', '3')


class ScoreSystemAppStartup(StartUpBase):
    after = ('schooltool.requirement.scoresystem', )

    def __call__(self):
        ssc = IScoreSystemContainer(self.app)
        if SkillScoreSystem.__name__ in ssc:
            return
        ssc[SkillScoreSystem.__name__] = CustomScoreSystem(
            SkillScoreSystem.title, SkillScoreSystem.description,
            SkillScoreSystem.scores,
            SkillScoreSystem._bestScore, SkillScoreSystem._minPassingScore)


def querySkillScoreSystem():
    """Get default skill score system for evaluations."""
    app = ISchoolToolApplication(None)
    ssc = IScoreSystemContainer(app)
    ss = ssc.get(SkillScoreSystem.__name__, None)
    return ss


# XXX: skill catalog
#
# + directly equivalent
# + all equivalent
