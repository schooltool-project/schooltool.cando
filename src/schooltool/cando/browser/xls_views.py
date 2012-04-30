#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
XLS Views
"""

import xlwt
from StringIO import StringIO

from schooltool.export import export
from schooltool.skin import flourish

from schooltool.cando.interfaces import ILayerContainer, INodeContainer


class ExportYearlySkillsView(export.ExcelExportView, flourish.page.Page):
    """A view for exporting yearly skill data to an XLS file"""

    def export_layers(self, wb):
        ws = wb.add_sheet('Layers')

        headers = ['ID', 'Title', 'Parents']
        for index, header in enumerate(headers):
            self.write_header(ws, 0, index, header)

        layers = ILayerContainer(self.context)
        for index, layer in enumerate(layers.values()):
            self.write(ws, index + 1, 0, layer.__name__)
            self.write(ws, index + 1, 1, layer.title)
            parents = ', '.join([p.__name__ for p in layer.parents])
            self.write(ws, index + 1, 2, parents)

    def export_nodes(self, wb):
        ws = wb.add_sheet('Nodes')

        headers = ['ID', 'Description', 'Parents', 'Layers', 'SkillSets']
        for index, header in enumerate(headers):
            self.write_header(ws, 0, index, header)

        nodes = INodeContainer(self.context)
        for index, node in enumerate(nodes.values()):
            self.write(ws, index + 1, 0, node.__name__)
            self.write(ws, index + 1, 1, node.description)
            parents = ', '.join([p.__name__ for p in node.parents])
            self.write(ws, index + 1, 2, parents)
            layers = ', '.join([p.__name__ for p in node.layers])
            self.write(ws, index + 1, 3, layers)
            skillsets = ', '.join([p.__name__ for p in node.skillsets])
            self.write(ws, index + 1, 4, skillsets)

    def getFileName(self):
        return 'yearly_skill_data_%s.xls' % self.context.__name__

    def __call__(self):
        wb = xlwt.Workbook()
        self.export_layers(wb)
        self.export_nodes(wb)

        datafile = StringIO()
        wb.save(datafile)
        data = datafile.getvalue()
        self.setUpHeaders(data)
        disposition = 'filename="%s"' % self.getFileName()
        self.request.response.setHeader('Content-Disposition', disposition)
        return data

