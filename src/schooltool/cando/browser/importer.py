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

from schooltool.export.importer import ImporterBase
from schooltool.export.importer import FlourishMegaImporter


class SkillsImporter(ImporterBase):

    sheet_name = 'Skills'

    def process(self):
        raise NotImplemented()


class ModelImporter(ImporterBase):

    sheet_name = 'Skill Model'

    def process(self):
        raise NotImplemented()


class SkillsMegaImporter(FlourishMegaImporter):

    def nextURL(self):
        url = absoluteURL(self.context, self.request)
        return url

    @property
    def importers(self):
        return [
            SkillsImporter,
            ModelImporter,
            ]
