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
Skills importer.
"""

from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.cando.interfaces import ILayerContainer, INodeContainer
from schooltool.cando.interfaces import ISkillSetContainer
from schooltool.cando.model import Layer, Node
from schooltool.cando.skill import SkillSet, Skill
from schooltool.export.importer import ImporterBase
from schooltool.export.importer import FlourishMegaImporter

from schooltool.common import SchoolToolMessage as _


ERROR_INVALID_PARENTS = _("has an invalid parent id")
ERROR_INVALID_LAYERS = _("has an invalid layer id")
ERROR_INVALID_SKILLSET = _("has an invalid skillset id")
ERROR_MISSING_SKILLSET_ID = _("is missing a skillset id")
ERROR_INVALID_EQUIVALENT = _("has an invalid equivalent skill id")


def breakupIds(ids):
    return [p.strip() for p in ids.split(',') if p.strip()]


class SkillSetsImporter(ImporterBase):

    sheet_name = 'SkillSets'

    def process(self):
        sh = self.sheet
        skillsets = self.context

        for row in range(1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == '':
                break

            num_errors = len(self.errors)
            name = self.getRequiredTextFromCell(sh, row, 0)
            title = self.getRequiredTextFromCell(sh, row, 1)
            external_id = self.getTextFromCell(sh, row, 2)
            label = self.getTextFromCell(sh, row, 3)
            if num_errors < len(self.errors):
                continue

            if name in skillsets:
                skillset = skillsets[name]
                skillset.title = title
            else:
                skillset = skillsets[name] = SkillSet(title)
            skillset.external_id = external_id
            skillset.label = label


class SkillsImporter(ImporterBase):

    sheet_name = 'Skills'

    def process(self):
        sh = self.sheet
        skillsets = self.context
        skillset = None

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

            if name in skillset:
                skill = skillset[name]
                skill.title = title
            else:
                skill = skillset[name] = Skill(title)
            skill.description = description
            skill.external_id = external_id
            skill.label = label
            skill.required = bool(required)
            skill.retired = bool(retired)

        skillset = None

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
            for eq in list(equiv):
                equiv.remove(eq)
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

            name = self.getRequiredTextFromCell(sh, row, 0)
            parents = self.getTextFromCell(sh, row, 2)

            layer = layers[name]
            for parent in list(layer.parents):
                layer.parents.remove(parent)
            for part in breakupIds(parents):
                if part not in layers:
                    self.error(row, 2, ERROR_INVALID_PARENTS)
                    break
                layer.parents.add(layers[part])


class NodesImporter(ImporterBase):

    sheet_name = 'Nodes'

    def process(self):
        sh = self.sheet
        nodes = INodeContainer(self.context)
        layers = ILayerContainer(self.context)
        skillsets = ISkillSetContainer(ISchoolToolApplication(None))

        for row in range(1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == '':
                break

            num_errors = len(self.errors)
            name = self.getRequiredTextFromCell(sh, row, 0)
            description = self.getRequiredTextFromCell(sh, row, 1)
            if num_errors < len(self.errors):
                continue

            if name in nodes:
                nodes[name].description = description
            else:
                nodes[name] = Node(description)

        for row in range(1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == '':
                break

            name = self.getRequiredTextFromCell(sh, row, 0)
            parents = self.getTextFromCell(sh, row, 2)
            node_layers = self.getTextFromCell(sh, row, 3)
            node_skillsets = self.getTextFromCell(sh, row, 4)

            node = nodes[name]

            for parent in list(node.parents):
                layer.parents.remove(parent)
            for part in breakupIds(parents):
                if part not in nodes:
                    self.error(row, 2, ERROR_INVALID_PARENTS)
                    break
                node.parents.add(nodes[part])

            for layer in list(node.layers):
                node.layers.remove(layer)
            for part in breakupIds(node_layers):
                if part not in layers:
                    self.error(row, 3, ERROR_INVALID_LAYERS)
                    break
                node.layers.add(layers[part])

            for skillset in list(node.skillsets):
                node.skillsets.remove(skillset)
            for part in breakupIds(node_skillsets):
                if part not in skillsets:
                    self.error(row, 4, ERROR_INVALID_SKILLSET)
                    break
                node.skillsets.add(skillsets[part])


class GlobalSkillsMegaImporter(FlourishMegaImporter):

    def nextURL(self):
        url = absoluteURL(self.context, self.request)
        return url

    @property
    def importers(self):
        return [
            SkillSetsImporter,
            SkillsImporter,
            ]


class YearlySkillsMegaImporter(FlourishMegaImporter):

    def nextURL(self):
        url = absoluteURL(self.context, self.request)
        return url

    @property
    def importers(self):
        return [
            LayersImporter,
            NodesImporter,
            ]

