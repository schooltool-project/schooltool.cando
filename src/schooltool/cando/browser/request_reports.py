#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2009 Shuttleworth Foundation
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
Request Report Views
"""

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.export.export import RequestXLSReportDialog
from schooltool.report.report import ReportLinkViewlet
from schooltool.report.browser.report import RequestReportArchiveDialog


class RequestGlobalSkillsExportView(RequestXLSReportDialog):

    report_builder = 'export_global_skills.xls'

    @property
    def target(self):
        return ISchoolToolApplication(None)


class RequestStudentCompetencyArchive(RequestReportArchiveDialog):

    report_builder = 'student_competency_archive.zip'

    @property
    def target(self):
        return ISchoolToolApplication(None)


class GradebookArchiveLinkViewlet(ReportLinkViewlet):
    pass
