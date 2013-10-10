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
Skills importer.
"""

import zope.lifecycleevent
from zope.security.proxy import removeSecurityProxy
from zope.proxy import sameProxiedObjects
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.course.interfaces import ICourseContainer
from schooltool.export.importer import (ImporterBase, FlourishMegaImporter,
    ERROR_INVALID_SCHOOL_YEAR, ERROR_MISSING_YEAR_ID, ERROR_INVALID_COURSE_ID)
from schooltool.schoolyear.interfaces import ISchoolYearContainer

from schooltool.requirement.interfaces import IScoreSystemContainer

from schooltool.cando.course import CourseSkillSet
from schooltool.cando.interfaces import (ILayerContainer, INodeContainer,
    ISkillSetContainer, ICourseSkills, IDocumentContainer)
from schooltool.cando.model import Layer, Node, Document
from schooltool.cando.skill import SkillSet, Skill

from schooltool.cando import CanDoMessage as _


ERROR_INVALID_DOCUMENTS = _("has an invalid document id")
ERROR_INVALID_PARENTS = _("has an invalid parent id")
ERROR_INVALID_LAYERS = _("has an invalid layer id")
ERROR_INVALID_SKILLSET = _("has an invalid skillset id")
ERROR_MISSING_SKILLSET_ID = _("is missing a skillset id")
ERROR_INVALID_EQUIVALENT = _("has an invalid equivalent skill id")
ERROR_NODE_LABEL_TOO_BIG = _("node label has more than seven characters")
ERROR_INVALID_SCORESYSTEM = _("has an invalid scoresystem")
ERROR_INVALID_NODE = _("has an invalid node id")


def breakupIds(ids):
    return [p.strip() for p in ids.split(',') if p.strip()]


class Changer(object):

    changed = False
    ignore = False

    def __init__(self, obj, ignore=False):
        self.obj = obj

    def __setitem__(self, attr, val):
        if (not hasattr(self.obj, attr) or
            getattr(self.obj, attr) != val):
            setattr(self.obj, attr, val)
            if not self.ignore:
                self.changed = True

    def __nonzero__(self):
        return self.changed

    def change(self, changes=None):
        self.changed = self.changed or bool(changes)

    def notify(self):
        if self.changed:
            zope.lifecycleevent.modified(self.obj)

        self.changed = False


class SkillSetsImporter(ImporterBase):

    sheet_name = 'SkillSets'

    def process(self):
        sh = self.sheet
        skillsets = ISkillSetContainer(self.context)

        for row in range(1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == '':
                break

            num_errors = len(self.errors)
            name = self.getRequiredTextFromCell(sh, row, 0)
            title = self.getRequiredTextFromCell(sh, row, 1)
            description = self.getTextFromCell(sh, row, 2)
            label = self.getTextFromCell(sh, row, 3)
            retired = self.getBoolFromCell(sh, row, 4)
            if num_errors < len(self.errors):
                continue

            if name in skillsets:
                skillset = skillsets[name]
                changes = Changer(skillset)
                changes['title'] = title
            else:
                skillset = skillsets[name] = SkillSet(title)
                changes = Changer(skillset, ignore=True)
            changes['description'] = description
            changes['label'] = label
            changes['retired'] = bool(retired)
            changes.notify()


class SkillsImporter(ImporterBase):

    sheet_name = 'Skills'

    def process(self):
        sh = self.sheet
        skillsets = ISkillSetContainer(self.context)
        scoresystems = IScoreSystemContainer(self.context)
        skillset = None

        skillset_changes = dict([(k, Changer(v)) for k, v in skillsets.items()])

        for row in range(1, sh.nrows):
            if (sh.cell_value(rowx=row, colx=0) == '' and
                sh.cell_value(rowx=row, colx=1) == ''):
                break

            num_errors = len(self.errors)
            skillset_id = self.getTextFromCell(sh, row, 0)
            name = self.getRequiredTextFromCell(sh, row, 1)
            title = self.getRequiredTextFromCell(sh, row, 2)
            description = self.getTextFromCell(sh, row, 4)
            external_id = self.getTextFromCell(sh, row, 5)
            label = self.getTextFromCell(sh, row, 6)
            required = self.getBoolFromCell(sh, row, 7)
            retired = self.getBoolFromCell(sh, row, 8)
            scoresystem = self.getTextFromCell(sh, row, 9)
            if num_errors < len(self.errors):
                continue

            if skillset_id:
                if skillset_id not in skillsets:
                    self.error(row, 0, ERROR_INVALID_SKILLSET)
                    continue
                skillset = skillsets[skillset_id]
            elif skillset is None:
                self.error(row, 0, ERROR_MISSING_SKILLSET_ID)
                continue

            if scoresystem and scoresystem not in scoresystems:
                self.error(row, 3, ERROR_INVALID_SCORESYSTEM)
                continue

            if name in skillset:
                skill = skillset[name]
                changes = Changer(skill)
                changes['title'] = title
            else:
                skill = skillset[name] = Skill(title)
                changes = Changer(skill)
            changes['description'] = description
            changes['external_id'] = external_id
            changes['label'] = label
            changes['required'] = bool(required)
            changes['retired'] = bool(retired)
            if scoresystem:
                changes['scoresystem'] = removeSecurityProxy(
                    scoresystems[scoresystem])
            skillset_changes[skillset.__name__].change(changes)

        skillset = None

        for changes in skillset_changes.values():
            changes.notify()

        for row in range(1, sh.nrows):
            if (sh.cell_value(rowx=row, colx=0) == '' and
                sh.cell_value(rowx=row, colx=1) == ''):
                break

            skillset_id = self.getTextFromCell(sh, row, 0)
            name = self.getRequiredTextFromCell(sh, row, 1)
            equivalent = self.getTextFromCell(sh, row, 3)

            if skillset_id:
                if skillset_id not in skillsets:
                    skillset = None
                else:
                    skillset = skillsets[skillset_id]
            if skillset is None or name not in skillset:
                continue
            skill = skillset[name]

            equiv = removeSecurityProxy(skill.equivalent)
            for part in breakupIds(equivalent):
                if part not in skillset:
                    self.error(row, 3, ERROR_INVALID_EQUIVALENT)
                    break
                equiv.add(removeSecurityProxy(skillset[part]))


class LayersImporter(ImporterBase):

    sheet_name = 'Layers'

    def process(self):
        sh = self.sheet
        layers = ILayerContainer(self.context)

        for row in range(1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == '':
                break

            num_errors = len(self.errors)
            name = self.getRequiredTextFromCell(sh, row, 0)
            title = self.getRequiredTextFromCell(sh, row, 1)
            if num_errors < len(self.errors):
                continue

            if name in layers:
                layers[name].title = title
            else:
                layers[name] = Layer(title)

        for row in range(1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == '':
                break

            name = self.getTextFromCell(sh, row, 0)
            parents = self.getTextFromCell(sh, row, 2)
            if name not in layers:
                continue

            layer = removeSecurityProxy(layers[name])
            for parent in list(layer.parents):
                layer.parents.remove(parent)
            for part in breakupIds(parents):
                if part not in layers:
                    self.error(row, 2, ERROR_INVALID_PARENTS)
                    break
                layer.parents.add(removeSecurityProxy(layers[part]))


class DocumentsImporter(ImporterBase):

    sheet_name = 'Documents'

    def process(self):
        sh = self.sheet
        layers = ILayerContainer(self.context)
        documents = IDocumentContainer(self.context)

        for row in range(1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == '':
                break

            num_errors = len(self.errors)
            name = self.getRequiredTextFromCell(sh, row, 0)
            title = self.getRequiredTextFromCell(sh, row, 1)
            description = self.getTextFromCell(sh, row, 2)
            hierarchy = self.getTextFromCell(sh, row, 3)
            if num_errors < len(self.errors):
                continue

            if name in documents:
                documents[name].title = title
                documents[name].description = description
            else:
                documents[name] = Document(title, description)

            document = removeSecurityProxy(documents[name])

            for layer in list(document.hierarchy):
                document.hierarchy.remove(layer)
            for part in breakupIds(hierarchy):
                if part not in layers:
                    self.error(row, 4, ERROR_INVALID_LAYERS)
                    break
                document.hierarchy.add(removeSecurityProxy(layers[part]))


class NodesImporter(ImporterBase):

    sheet_name = 'Nodes'

    def process(self):
        sh = self.sheet
        nodes = INodeContainer(self.context)
        layers = ILayerContainer(self.context)
        skillsets = ISkillSetContainer(self.context)
        documents = IDocumentContainer(self.context)

        for row in range(1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == '':
                break

            num_errors = len(self.errors)
            name = self.getRequiredTextFromCell(sh, row, 0)
            title = self.getRequiredTextFromCell(sh, row, 1)
            description = self.getTextFromCell(sh, row, 2)
            label = self.getTextFromCell(sh, row, 3)
            retired = self.getBoolFromCell(sh, row, 8)
            if num_errors < len(self.errors):
                continue

            if len(label) > 7:
                self.error(row, 3, ERROR_NODE_LABEL_TOO_BIG)
                continue

            if name in nodes:
                nodes[name].title = title
                nodes[name].description = description
                nodes[name].label = label
                nodes[name].retired = retired
            else:
                nodes[name] = Node(title, description, label, retired)

        for row in range(1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == '':
                break

            name = self.getTextFromCell(sh, row, 0)
            node_documents = self.getTextFromCell(sh, row, 4)
            parents = self.getTextFromCell(sh, row, 5)
            node_layers = self.getTextFromCell(sh, row, 6)
            node_skillsets = self.getTextFromCell(sh, row, 7)
            if name not in nodes:
                continue

            node = removeSecurityProxy(nodes[name])

            for parent in list(node.parents):
                node.parents.remove(parent)
            for part in breakupIds(node_documents):
                if part not in documents:
                    self.error(row, 4, ERROR_INVALID_DOCUMENTS)
                    break
                node.parents.add(removeSecurityProxy(documents[part]))
            for part in breakupIds(parents):
                if part not in nodes:
                    self.error(row, 5, ERROR_INVALID_PARENTS)
                    break
                node.parents.add(removeSecurityProxy(nodes[part]))

            for layer in list(node.layers):
                node.layers.remove(layer)
            for part in breakupIds(node_layers):
                if part not in layers:
                    self.error(row, 6, ERROR_INVALID_LAYERS)
                    break
                node.layers.add(removeSecurityProxy(layers[part]))

            for skillset in list(node.skillsets):
                node.skillsets.remove(skillset)
            for part in breakupIds(node_skillsets):
                if part not in skillsets:
                    self.error(row, 7, ERROR_INVALID_SKILLSET)
                    break
                node.skillsets.add(removeSecurityProxy(skillsets[part]))


class CourseSkillsImporter(ImporterBase):

    sheet_name = 'CourseSkills'

    def process(self):
        sh = self.sheet
        skillsets = ISkillSetContainer(self.context)
        schoolyears = ISchoolYearContainer(self.context)
        year = None

        for row in range(1, sh.nrows):
            if (sh.cell_value(rowx=row, colx=0) == '' and
                sh.cell_value(rowx=row, colx=1) == ''):
                break

            num_errors = len(self.errors)
            year_id = self.getTextFromCell(sh, row, 0)
            course_id = self.getRequiredTextFromCell(sh, row, 1)
            course_skillset_ids = self.getTextFromCell(sh, row, 2)
            if num_errors < len(self.errors):
                continue

            if year_id:
                if year_id not in schoolyears:
                    self.error(row, 0, ERROR_INVALID_SCHOOL_YEAR)
                    year = None
                else:
                    year = schoolyears[year_id]
                    courses = ICourseContainer(year)
            elif year is None:
                self.error(row, 0, ERROR_MISSING_YEAR_ID)
            if year is None:
                continue

            if course_id not in courses:
                self.error(row, 1, ERROR_INVALID_COURSE_ID)
                continue
            course = courses[course_id]

            course_skills = ICourseSkills(course)
            for key in list(course_skills):
                del course_skills[key]
            for part in breakupIds(course_skillset_ids):
                if part not in skillsets:
                    self.error(row, 2, ERROR_INVALID_SKILLSET)
                    break
                course_skills[part] = CourseSkillSet(skillsets[part])


class CourseNodesImporter(ImporterBase):

    sheet_name = 'CourseNodes'

    def process(self):
        sh = self.sheet
        nodes = INodeContainer(self.context)
        schoolyears = ISchoolYearContainer(self.context)
        year = None

        for row in range(1, sh.nrows):
            if (sh.cell_value(rowx=row, colx=0) == '' and
                sh.cell_value(rowx=row, colx=1) == ''):
                break

            num_errors = len(self.errors)
            year_id = self.getTextFromCell(sh, row, 0)
            course_id = self.getRequiredTextFromCell(sh, row, 1)
            course_node_ids = self.getTextFromCell(sh, row, 2)
            if num_errors < len(self.errors):
                continue

            if year_id:
                if year_id not in schoolyears:
                    self.error(row, 0, ERROR_INVALID_SCHOOL_YEAR)
                    year = None
                else:
                    year = schoolyears[year_id]
                    courses = ICourseContainer(year)
            elif year is None:
                self.error(row, 0, ERROR_MISSING_YEAR_ID)
            if year is None:
                continue

            if course_id not in courses:
                self.error(row, 1, ERROR_INVALID_COURSE_ID)
                continue
            course = courses[course_id]

            course_skills = ICourseSkills(course)
            for key in list(course_skills):
                del course_skills[key]
            for part in breakupIds(course_node_ids):
                if part not in nodes:
                    self.error(row, 2, ERROR_INVALID_NODE)
                    break
                node = nodes[part]
                for skillset in node.skillsets:
                    course_skills[skillset.__name__] = CourseSkillSet(skillset)


class GlobalSkillsMegaImporter(FlourishMegaImporter):

    def nextURL(self):
        app = ISchoolToolApplication(None)
        container = IDocumentContainer(app)
        url = absoluteURL(container, self.request)
        return url

    @property
    def importers(self):
        return [
            SkillSetsImporter,
            SkillsImporter,
            LayersImporter,
            DocumentsImporter,
            NodesImporter,
            CourseSkillsImporter,
            CourseNodesImporter,
            ]

