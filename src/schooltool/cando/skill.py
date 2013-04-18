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

from zope.annotation.interfaces import IAnnotations
import zc.catalog.extentcatalog
from zope.catalog.text import TextIndex
from zope.index.text.interfaces import ISearchableText
from zope.interface import implements, implementer
from zope.component import adapter, adapts
from zope.container.btree import BTreeContainer
from zope.container.interfaces import INameChooser
from zope.security.proxy import removeSecurityProxy

from schooltool.app.app import InitBase, StartUpBase
from schooltool.app.catalog import AttributeCatalog
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.cando import interfaces
from schooltool.relationship import URIObject
from schooltool.relationship import RelationshipSchema, RelationshipProperty
from schooltool.requirement.interfaces import IScoreSystemContainer
from schooltool.requirement.requirement import Requirement
from schooltool.requirement.scoresystem import CustomScoreSystem
from schooltool.requirement.scoresystem import GlobalDiscreteValuesScoreSystem

DEFAULT_SCORESYSTEM_KEY = 'schooltool.cando.defaultscoresystem'


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
    custom_scoresystem = None

    equivalent = RelationshipProperty(URIEquivalent, URISkill, URISkill)

    def __init__(self, title, required=False, external_id=u'', label=u'',
                 scoresystem=None):
        Requirement.__init__(self, title)
        self.required = required
        self.external_id = external_id
        self.label = label
        self.custom_scoresystem = scoresystem

    @property
    def scoresystem(self):
        if self.custom_scoresystem is not None:
            return self.custom_scoresystem
        return querySkillScoreSystem()

    @scoresystem.setter
    def scoresystem(self, new_scoresystem):
        self.custom_scoresystem = new_scoresystem

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
                     external_id=self.external_id,
                     label=self.label)

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

    description = u''
    label = u''

    def __init__(self, title, description=u'', label=u''):
        Requirement.__init__(self, title)
        self.description = description
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
     ('1', u'Beginning', Decimal(1), Decimal(30)),
     ('0', u'Uninformed', Decimal(0), Decimal(0))],
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
    if ss is not None:
        return ss
    ssc = IScoreSystemContainer(ISchoolToolApplication(None))
    if len(ssc) > 0:
        return ssc.values()[0]
    return None


def getDefaultSkillScoreSystem(person):
    default_ss = querySkillScoreSystem()
    if default_ss is None:
        return None

    default = default_ss.__name__.encode('punycode')
    if person is None:
        return default
    ann = IAnnotations(removeSecurityProxy(person))
    if DEFAULT_SCORESYSTEM_KEY not in ann:
        return default
    return ann[DEFAULT_SCORESYSTEM_KEY]


def setDefaultSkillScoreSystem(person, scoresystem):
    if person is None:
        return
    person = removeSecurityProxy(person)
    ann = IAnnotations(person)
    ann[DEFAULT_SCORESYSTEM_KEY] = scoresystem


def is_global_skillset(index, docid, item):
    if (not interfaces.ISkillSet.providedBy(item) or
        not interfaces.ISkillSetContainer.providedBy(item.__parent__) or
        not ISchoolToolApplication.providedBy(item.__parent__.__parent__)):
        return False
    return True


def is_global_skill(index, docid, item):
    if (not interfaces.ISkill.providedBy(item) or
        not interfaces.ISkillSet.providedBy(item.__parent__) or
        not interfaces.ISkillSetContainer.providedBy(item.__parent__.__parent__) or
        not ISchoolToolApplication.providedBy(item.__parent__.__parent__.__parent__)):
        return False
    return True


class SkillCatalog(AttributeCatalog):

    version = '1.1 - index only global skills'
    interface = interfaces.ISkill
    attributes = ('title', 'external_id', 'label', 'description',
                  'required', 'retired')

    def createCatalog(self):
        return zc.catalog.extentcatalog.Catalog(
            zc.catalog.extentcatalog.FilterExtent(is_global_skill))

    def setIndexes(self, catalog):
        super(SkillCatalog, self).setIndexes(catalog)
        catalog['text'] = TextIndex('getSearchableText', ISearchableText, True)


getSkillCatalog = SkillCatalog.get


class SearchableTextSkill(object):

    adapts(interfaces.ISkill)
    implements(ISearchableText)

    def __init__(self, context):
        self.context = context

    def getSearchableText(self):
        result = [
            self.context.title,
            self.context.external_id or '',
            self.context.label or '',
            self.context.description or '',
            ]
        return ' '.join(result)


class SkillSetCatalog(AttributeCatalog):

    version = '1 - attributes and text indexes'
    interface = interfaces.ISkillSet
    attributes = ('title', 'label', 'description',)

    def createCatalog(self):
        return zc.catalog.extentcatalog.Catalog(
            zc.catalog.extentcatalog.FilterExtent(is_global_skillset))

    def setIndexes(self, catalog):
        super(SkillSetCatalog, self).setIndexes(catalog)
        catalog['text'] = TextIndex('getSearchableText', ISearchableText, True)


getSkillSetCatalog = SkillSetCatalog.get


class SearchableTextSkillSet(object):

    adapts(interfaces.ISkillSet)
    implements(ISearchableText)

    def __init__(self, context):
        self.context = context

    def getSearchableText(self):
        result = [
            self.context.title,
            self.context.label or '',
            self.context.description or '',
            ]
        return ' '.join(result)


# + directly equivalent
# + all equivalent
