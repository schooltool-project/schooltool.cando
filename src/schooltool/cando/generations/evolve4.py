#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2013 Shuttleworth Foundation
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
Evolve database to generation 4.

Sets cache for URIObjects.
"""

from zope.app.generations.utility import getRootFolder
from zope.component.hooks import getSite, setSite

from schooltool.app.interfaces import ISchoolToolApplication

from schooltool.cando.model import URIDocument
from schooltool.cando.model import URIDocumentHierarchy
from schooltool.cando.model import URILayer
from schooltool.cando.model import URILayerLink
from schooltool.cando.model import URINode
from schooltool.cando.model import URINodeLayer
from schooltool.cando.model import URINodeLink
from schooltool.cando.model import URINodeSkillSets
from schooltool.cando.model import URIParentLayer
from schooltool.cando.model import URIParentNode
from schooltool.cando.skill import URIEquivalent
from schooltool.cando.skill import URISkill
from schooltool.cando.skill import URISkillSet


def requireURICache(app):
    cache = app['schooltool.relationship.uri']
    standard_uris = [
        URIDocument,
        URIDocumentHierarchy,
        URILayer,
        URILayerLink,
        URINode,
        URINodeLayer,
        URINodeLink,
        URINodeSkillSets,
        URIParentLayer,
        URIParentNode,
        URIEquivalent,
        URISkill,
        URISkillSet,
        ]
    for uri in standard_uris:
        cache.cache(uri)


def evolve(context):
    root = getRootFolder(context)
    old_site = getSite()

    assert ISchoolToolApplication.providedBy(root)
    setSite(root)

    requireURICache(root)
    setSite(old_site)
