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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
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

from schooltool.cando.interfaces import (ILayerContainer, INodeContainer,
    ISkillSetContainer, ICourseSkills, IDocumentContainer, IDocument)

from schooltool.cando import CanDoMessage as _


class ExportGlobalSkillsView(export.ExcelExportView, flourish.page.Page):
    """A view for exporting global skill data to an XLS file"""

    overall_line_id = 'overall'
    base_filename = 'skills'

    def export_skillsets(self, wb):
        ws = wb.add_sheet('SkillSets')

        headers = ['ID', 'Title', 'Description', 'Label', 'Deprecated']
        for index, header in enumerate(headers):
            self.write_header(ws, 0, index, header)

        skillsets = list(ISkillSetContainer(self.context).values())
        for index, skillset in enumerate(skillsets):
            self.write(ws, index + 1, 0, skillset.__name__)
            self.write(ws, index + 1, 1, skillset.title)
            self.write(ws, index + 1, 2, skillset.description)
            self.write(ws, index + 1, 3, skillset.label)
            self.write(ws, index + 1, 4, skillset.retired)
            self.progress('skills', export.normalized_progress(
                    0, 2,
                    index, len(skillsets)))

    def export_skills(self, wb):
        ws = wb.add_sheet('Skills')

        headers = ['SkillSet ID', 'Skill ID', 'Title', 'Equivalent',
                   'Description', 'External ID', 'Label', 'Required', 'Deprecated']
        for index, header in enumerate(headers):
            self.write_header(ws, 0, index, header)

        row = 1
        skillsets = ISkillSetContainer(self.context).values()
        for index, skillset in enumerate(skillsets):
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
            self.progress('skills', export.normalized_progress(
                    1, 2,
                    index, len(skillsets)))

    def export_layers(self, wb):
        ws = wb.add_sheet('Layers')

        headers = ['ID', 'Title', 'Parents']
        for index, header in enumerate(headers):
            self.write_header(ws, 0, index, header)

        layers = ILayerContainer(self.context).values()
        for index, layer in enumerate(layers):
            self.write(ws, index + 1, 0, layer.__name__)
            self.write(ws, index + 1, 1, layer.title)
            parents = ', '.join([p.__name__ for p in layer.parents])
            self.write(ws, index + 1, 2, parents)
            self.progress('documents', export.normalized_progress(
                    1, 3,
                    index, len(layers)))

    def export_documents(self, wb):
        ws = wb.add_sheet('Documents')

        headers = ['ID', 'Title', 'Description', 'Hierarchy']
        for index, header in enumerate(headers):
            self.write_header(ws, 0, index, header)

        documents = IDocumentContainer(self.context).values()
        for index, document in enumerate(documents):
            self.write(ws, index + 1, 0, document.__name__)
            self.write(ws, index + 1, 1, document.title)
            self.write(ws, index + 1, 2, document.description)
            hierarchy = ', '.join([l.__name__ for l in document.hierarchy])
            self.write(ws, index + 1, 3, hierarchy)
            self.progress('documents', export.normalized_progress(
                    0, 3,
                    index, len(documents)))


    def export_nodes(self, wb):
        ws = wb.add_sheet('Nodes')

        headers = ['ID', 'Title', 'Description', 'Label', 'Documents', 'Parents', 'Layers', 'SkillSets']
        for index, header in enumerate(headers):
            self.write_header(ws, 0, index, header)

        nodes = INodeContainer(self.context).values()
        for index, node in enumerate(nodes):
            self.write(ws, index + 1, 0, node.__name__)
            self.write(ws, index + 1, 1, node.title)
            self.write(ws, index + 1, 2, node.description)
            self.write(ws, index + 1, 3, node.label)
            documents = ', '.join([p.__name__ for p in node.parents
                                   if IDocument(p, None) is not None])
            self.write(ws, index + 1, 4, documents)
            parents = ', '.join([p.__name__ for p in node.parents
                                 if IDocument(p, None) is None])
            self.write(ws, index + 1, 5, parents)
            layers = ', '.join([p.__name__ for p in node.layers])
            self.write(ws, index + 1, 6, layers)
            skillsets = ', '.join([p.__name__ for p in node.skillsets])
            self.write(ws, index + 1, 7, skillsets)
            self.progress('documents', export.normalized_progress(
                    2, 3,
                    index, len(nodes)))


    def export_course_skills(self, wb):
        ws = wb.add_sheet('CourseSkills')

        headers = ['Year ID', 'Course ID', 'SkillSets']
        for index, header in enumerate(headers):
            self.write_header(ws, 0, index, header)

        skillsets = ISkillSetContainer(self.context)
        schoolyears = ISchoolYearContainer(self.context).values()
        row = 1
        for ny, year in enumerate(schoolyears):
            courses = ICourseContainer(year).values()
            if not len(courses):
                continue
            self.write(ws, row, 0, year.__name__)
            for nc, course in enumerate(courses):
                self.write(ws, row, 1, course.__name__)
                course_skills = ICourseSkills(course)
                skillsets = ', '.join(course_skills.keys())
                self.write(ws, row, 2, skillsets)
                row += 1
            self.progress('course_skills', export.normalized_progress(
                    ny, len(schoolyears),
                    nc, len(courses),
                    ))

    def addImporters(self, progress):
        progress.add(
            'documents', active=False,
            title=_('Documents'), progress=0.0)
        progress.add(
            'skills', active=False,
            title=_('Skill definitions'), progress=0.0)
        progress.add(
            'course_skills', active=False,
            title=_('Course Skills'), progress=0.0)
        progress.add(
            'overall',
            title=_('Skills Export'), progress=0.0)

    def __call__(self):
        self.makeProgress()
        self.task_progress.title = _("Exporting skills")
        self.addImporters(self.task_progress)
        wb = xlwt.Workbook()

        self.task_progress.force('documents', active=True)
        self.export_documents(wb)
        self.export_layers(wb)
        self.export_nodes(wb)
        self.finish('documents')

        self.task_progress.force('skills', active=True)
        self.export_skillsets(wb)
        self.export_skills(wb)
        self.finish('skills')

        self.task_progress.force('course_skills', active=True)
        self.export_course_skills(wb)
        self.finish('course_skills')

        self.task_progress.title = _("Export complete")
        self.task_progress.force('overall', progress=1.0)
        return wb

