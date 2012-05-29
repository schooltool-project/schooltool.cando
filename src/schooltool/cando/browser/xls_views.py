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

from schooltool.course.interfaces import ICourseContainer
from schooltool.export import export
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.skin import flourish

from schooltool.cando.interfaces import ILayerContainer, INodeContainer
from schooltool.cando.interfaces import ISkillSetContainer
from schooltool.cando.interfaces import ICourseSkills


class ExportGlobalSkillsView(export.ExcelExportView, flourish.page.Page):
    """A view for exporting global skill data to an XLS file"""

    def export_skillsets(self, wb):
        ws = wb.add_sheet('SkillSets')

        headers = ['ID', 'Title', 'External ID', 'Label']
        for index, header in enumerate(headers):
            self.write_header(ws, 0, index, header)

        skillsets = ISkillSetContainer(self.context)
        for index, skillset in enumerate(skillsets.values()):
            self.write(ws, index + 1, 0, skillset.__name__)
            self.write(ws, index + 1, 1, skillset.title)
            self.write(ws, index + 1, 2, skillset.external_id)
            self.write(ws, index + 1, 3, skillset.label)

    def export_skills(self, wb):
        ws = wb.add_sheet('Skills')

        headers = ['SkillSet ID', 'Skill ID', 'Title', 'Equivalent',
                   'Description', 'External ID', 'Label', 'Required', 'Retired']
        for index, header in enumerate(headers):
            self.write_header(ws, 0, index, header)

        row = 1
        skillsets = ISkillSetContainer(self.context)
        for skillset in skillsets.values():
            for skill in skillset.values():
                self.write(ws, row, 0, skillset.__name__)
                self.write(ws, row, 1, skill.__name__)
                self.write(ws, row, 2, skill.title)
                equivalent = ', '.join([s.__name__ for s in skill.equivalent])
                self.write(ws, row, 3, equivalent)
                self.write(ws, row, 4, skill.description)
                self.write(ws, row, 5, skill.external_id)
                self.write(ws, row, 6, skill.label)
                self.write(ws, row, 7, skill.required)
                self.write(ws, row, 8, skill.retired)
                row += 1

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

    def export_course_skills(self, wb):
        ws = wb.add_sheet('CourseSkills')

        headers = ['Year ID', 'Course ID', 'SkillSets']
        for index, header in enumerate(headers):
            self.write_header(ws, 0, index, header)

        skillsets = ISkillSetContainer(self.context)
        schoolyears = ISchoolYearContainer(self.context)
        row = 1
        for year in schoolyears.values():
            courses = ICourseContainer(year)
            if not len(courses):
                continue
            self.write(ws, row, 0, year.__name__)
            for course in courses.values():
                self.write(ws, row, 1, course.__name__)
                course_skills = ICourseSkills(course)
                skillsets = ', '.join(course_skills.keys())
                self.write(ws, row, 2, skillsets)
                row += 1

    def getFileName(self):
        return 'global_skill_data.xls'

    def __call__(self):
        wb = xlwt.Workbook()
        self.export_skillsets(wb)
        self.export_skills(wb)
        self.export_layers(wb)
        self.export_nodes(wb)
        self.export_course_skills(wb)

        datafile = StringIO()
        wb.save(datafile)
        data = datafile.getvalue()
        self.setUpHeaders(data)
        disposition = 'filename="%s"' % self.getFileName()
        self.request.response.setHeader('Content-Disposition', disposition)
        return data

