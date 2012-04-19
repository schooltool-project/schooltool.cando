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

from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.cando.interfaces import ILayerContainer, INodeContainer
from schooltool.cando.model import Layer, Node
from schooltool.export.importer import ImporterBase
from schooltool.export.importer import FlourishMegaImporter

from schooltool.common import SchoolToolMessage as _


ERROR_INVALID_PARENTS = _("has an invalid parent id")
ERROR_INVALID_LAYERS = _("has an invalid layer id")


class SkillsImporter(ImporterBase):

    sheet_name = 'Skills'

    def process(self):
        raise NotImplemented()


class ModelImporter(ImporterBase):

    sheet_name = 'Skill Model'

    def process(self):
        raise NotImplemented()


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
            parts = [p.strip() for p in parents.split(',')]
            for part in parts:
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

        for row in range(1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == '':
                break

            num_errors = len(self.errors)
            name = self.getRequiredTextFromCell(sh, row, 0)
            title = self.getRequiredTextFromCell(sh, row, 1)
            if num_errors < len(self.errors):
                continue

            if name in nodes:
                nodes[name].title = title
            else:
                nodes[name] = Node(title)

        for row in range(1, sh.nrows):
            if sh.cell_value(rowx=row, colx=0) == '':
                break

            name = self.getRequiredTextFromCell(sh, row, 0)
            parents = self.getTextFromCell(sh, row, 2)
            node_layers = self.getTextFromCell(sh, row, 3)

            node = nodes[name]
            for parent in list(node.parents):
                layer.parents.remove(parent)
            for layer in list(node.layers):
                node.layers.remove(layer)

            parts = [p.strip() for p in parents.split(',')]
            for part in parts:
                if part not in nodes:
                    self.error(row, 2, ERROR_INVALID_PARENTS)
                    break
                node.parents.add(nodes[part])
            parts = [l.strip() for l in node_layers.split(',')]
            for part in parts:
                if part not in layers:
                    self.error(row, 2, ERROR_INVALID_LAYERS)
                    break
                node.layers.add(layers[part])


class SkillsMegaImporter(FlourishMegaImporter):

    def nextURL(self):
        url = absoluteURL(self.context, self.request)
        return url

    @property
    def importers(self):
        return [
            LayersImporter,
            NodesImporter,
            SkillsImporter,
            ModelImporter,
            ]

