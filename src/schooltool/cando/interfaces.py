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

import zope.schema
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.container.interfaces import IContainer, IContained
from zope.container.constraints import contains
from zope.interface import Interface, Attribute

from schooltool.requirement.interfaces import IRequirement
from schooltool.gradebook.interfaces import IWorksheets, IWorksheet
from schooltool.cando import CanDoMessage as _


class ISkill(IRequirement, IAttributeAnnotatable):

    external_id = zope.schema.TextLine(title=_("External ID"))
    required = zope.schema.Bool(title=_("Required"))

    equivalent = Attribute("Directly equivalent skills.")

    def findAllEquivalent():
        """Find all (including indirectly) equivalent skills."""

    def copy():
        """Return a copy of this skill."""


class ISkillSetContainer(IContainer):
    pass


class ISkillSet(IRequirement):

    description = zope.schema.TextLine(
        title=_("Description"))


class ILayerContainerContainer(IContainer):
    pass


class ILayerContainer(IContainer):
    pass


class ILayer(Interface):
    title = zope.schema.TextLine(
        title=_("Title"))

    parents = Attribute("Parent layers")


class ILayerContained(ILayer, IContained, IAttributeAnnotatable):
    pass


class INodeContainerContainer(IContainer):
    pass


class INodeContainer(IContainer):
    pass


class INode(Interface):

    description = zope.schema.TextLine(
        title=_("Description"))

    layers = Attribute("Layers within this layer")
    parents = Attribute("Parent nodes")

    def findPaths():
        """
          Return a list of paths (tuples) that lead
          (parent-to-child) to this node.
        """


class INodeContained(INode, IContained, IAttributeAnnotatable):
    pass


class IProject(ISkillSet, IWorksheet):
    pass


class IProjects(IWorksheets):
    contains('.IProject')


class ICourseProject(ISkillSet):
    """A template project."""
    contains('.ISkill')

    deployed = zope.schema.Bool(
        title=_("Project deployed"),
        description=_("Is this project deployed to course sections"),
        readonly=True,
        required=False
        )


class ICourseProjects(IRequirement):
    contains('.ICourseProject')

    def isDeployed(project, section):
        """Is given project deployed to that section?"""

    def deploy(self, key, section):
        """Deploy this project to that section."""

