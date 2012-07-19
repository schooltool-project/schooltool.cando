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
Course skill views.
"""
from zope.cachedescriptors.property import Lazy
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.i18n import translate
from zope.i18n.interfaces.locales import ICollator
from zope.interface import directlyProvides
from zope.traversing.browser.absoluteurl import absoluteURL
import z3c.form.form
import z3c.form.field
import z3c.form.button
import zc.table.column
from zc.table.interfaces import ISortableColumn

from schooltool.app.browser.app import RelationshipAddTableMixin
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.cando.course import CourseSkillSet
from schooltool.cando.interfaces import ICourseSkills
from schooltool.cando.interfaces import ILayerContainer
from schooltool.cando.interfaces import INodeContainer
from schooltool.cando.interfaces import ICourseSkillSet
from schooltool.cando.interfaces import ISkillSetContainer
from schooltool.cando.browser.skill import SkillSetTable, SkillSetSkillTable
from schooltool.cando.browser.skill import SkillView
from schooltool.course.interfaces import ICourse
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.skin import flourish
from schooltool.table.column import getResourceURL
from schooltool import table

from schooltool.cando import CanDoMessage as _


class CourseSkillsOverview(flourish.page.Content):
    body_template = ViewPageTemplateFile(
        'templates/course_skills_overview.pt')

    @Lazy
    def skills(self):
        return ICourseSkills(self.context)


class UseCourseTitleMixin(object):

    @property
    def title(self):
        obj = self.context
        while obj is not None:
            if ICourse.providedBy(obj):
                return obj.title
            obj = obj.__parent__
        return ''


class CourseSkillsView(UseCourseTitleMixin, flourish.page.Page):

    content_template = InlineViewPageTemplate('''
      <table class="form-fields" i18n:domain="schooltool">
        <tbody>
          <tr>
            <td class="label" i18n:translate="">Course ID</td>
            <td tal:content="context/__parent__/course_id" />
          </tr>
          <tr>
            <td class="label" i18n:translate="">Alternate ID</td>
            <td tal:content="context/__parent__/government_id" />
          </tr>
        </tbody>
      </table>
      <div tal:content="structure context/schooltool:content/ajax/table" />
      <h3>
        <a tal:attributes="href context/__parent__/@@absolute_url"
           i18n:translate="">Done</a>
      </h3>
    ''')

    @property
    def title(self):
        return self.context.__parent__.title


class CourseSkillsTable(table.ajax.Table):

    def updateFormatter(self):
        if self._table_formatter is None:
            self.setUp(table_formatter=self.table_formatter,
                       batch_size=self.batch_size,
                       prefix=self.__name__,
                       css_classes={'table': 'data'})

    def columns(self):
        default = table.ajax.Table.columns(self)
        skills = zc.table.column.GetterColumn(
            name='skills',
            title=_(u'Skills'),
            getter=lambda i, f: str(len(i)))
        label = zc.table.column.GetterColumn(
            name='label',
            title=_(u'Label'),
            getter=lambda i, f: i.skillset.label or '')
        return [label] + default + [skills]

    def sortOn(self):
        return None


class CourseSkillsLinks(flourish.page.RefineLinksViewlet):
    pass


class RemoveSkillsLinkViewlet(flourish.page.LinkViewlet):

    @property
    def enabled(self):
        return bool(self.context)


# XXX: done link in course skills view.

class CourseAssignSkillSetView(flourish.page.Page):

    content_template = InlineViewPageTemplate('''
      <div tal:content="structure context/schooltool:content/ajax/available_table" />
    ''')

    def getKey(self, skillset):
        return skillset.__name__

    def getOmmitedItems(self):
        app = ISchoolToolApplication(None)
        skillsets = ISkillSetContainer(app)
        ommit = [skillsets.get(i) for i in self.context]
        return [o for o in ommit if o is not None]


def get_node_layers(node, formatter):
    return ', '.join([layer.title for layer in node.layers])


def node_layers_formatter(value, node, formatter):
    return '<br />'.join([layer.title for layer in node.layers])


class DialogButtonColumn(table.column.ImageInputColumn):

    content_template = ViewPageTemplateFile(
        'templates/dialog_button_column.pt')

    def __init__(self, course_url):
        self.course_url = course_url
        kw = {
            'prefix': 'add_item',
            'title': _('Add'),
            'name': 'action',
            'alt': _('Add'),
            'library': 'schooltool.skin.flourish',
            'image': 'add-icon.png',
            'id_getter': lambda x:x.__name__,
            }
        super(DialogButtonColumn, self).__init__(**kw)

    def renderCell(self, item, formatter):
        params = self.params(item, formatter)
        if not params:
            return ''
        # XXX: hack, scriplocal can't be used in inlintemplates?
        self.context = item
        self.request = formatter.request
        return self.content_template(params=params)

    def params(self, item, formatter):
        image_url = getResourceURL(self.library, self.image, formatter.request)
        if not image_url:
            return None
        dialog_url = '%s/assign-skillsets.html?node_id=%s' % (
            self.course_url, item.__name__)
        dialog_id = '%s-container' % item.__name__
        dialog_title = self.dialog_title(item, formatter)
        return {
            'title': translate(self.title, context=formatter.request) or '',
            'alt': translate(self.alt, context=formatter.request) or '',
            'src': image_url,
            'id': item.__name__,
            'dialog_url': dialog_url,
            'dialog_id': dialog_id,
            'dialog_title': dialog_title,
            }

    def dialog_title(self, item, formatter):
        title = _('Select Skill Sets from ${node} (${node_id})',
                  mapping={'node': item.title, 'node_id': item.__name__})
        return translate(title, context=formatter.request)


class SkillsetNodesTable(table.ajax.Table):

    def updateFormatter(self):
        if self._table_formatter is None:
            self.setUp(table_formatter=self.table_formatter,
                       batch_size=self.batch_size,
                       prefix=self.__name__,
                       css_classes={'table': 'data'})

    def columns(self):
        title = table.column.LocaleAwareGetterColumn(
            name='title',
            title=_(u"Title"),
            getter=lambda i, f: i.title,
            subsort=True)
        ID = table.column.LocaleAwareGetterColumn(
            name='ID',
            title=_(u'ID'),
            getter=lambda i, f: i.__name__,
            subsort=True)
        layers = table.column.LocaleAwareGetterColumn(
            name='layers',
            title=_('Layers'),
            getter=get_node_layers,
            cell_formatter=node_layers_formatter)
        skillsets = zc.table.column.GetterColumn(
            name='skillsets',
            title=_(u"Skill Sets"),
            getter=lambda i, f: len(i.skillsets),
            subsort=True)
        course_url = absoluteURL(self.context, self.request)
        action = DialogButtonColumn(course_url)
        directlyProvides(ID, ISortableColumn)
        directlyProvides(layers, ISortableColumn)
        return [ID, title, layers, skillsets, action]

    @property
    def source(self):
        app = ISchoolToolApplication(None)
        nodes = INodeContainer(app)
        result = {}
        for node in nodes.values():
            if node.skillsets:
                result[node.__name__] = node
        return result


class SkillsetNodesTableFilter(table.ajax.TableFilter):

    search_title = _("ID, title, label or description")
    template = ViewPageTemplateFile(
        'templates/course_assign_skills_table_filter.pt')

    @property
    def search_id(self):
        return self.manager.html_id+'-search'

    @property
    def search_title_id(self):
        return self.manager.html_id+'-title'

    @property
    def search_layer_ids(self):
        return self.manager.html_id+"-layers"

    def layerContainer(self):
        app = ISchoolToolApplication(None)
        return ILayerContainer(app)

    def layers(self):
        result = []
        container = self.layerContainer()
        collator = ICollator(self.request.locale)
        items = sorted(container.items(),
                       key=lambda (lid, layer): layer.title,
                       cmp=collator.cmp)
        for id, layer in items:
            checked = not self.manager.fromPublication
            if self.search_layer_ids in self.request:
                layer_ids = self.request[self.search_layer_ids]
                if not isinstance(layer_ids, list):
                    layer_ids = [layer_ids]
                checked = id in layer_ids
            result.append({'id': id,
                           'title': layer.title,
                           'checked': checked})
        return result


    def filter(self, items):
        if self.ignoreRequest:
            return items
        if self.search_layer_ids in self.request:
            layer_ids = self.request[self.search_layer_ids]
            if not isinstance(layer_ids, list):
                layer_ids = [layer_ids]
            layers = set()
            for layer_id in layer_ids:
                layer = self.layerContainer().get(layer_id)
                if layer is not None:
                    layers.add(layer)
            if layers:
                items = [item for item in items
                         if set(list(item.layers)).intersection(layers)]
        else:
            return []
        if self.search_title_id in self.request:
            searchstr = self.request[self.search_title_id].lower()
            items = [item for item in items
                     if searchstr in item.__name__.lower() or
                     searchstr in item.title.lower() or
                     searchstr in getattr(item, 'label', '') or
                     searchstr in getattr(item, 'description', '')]
        return items


class CourseAssignSkillsView(flourish.page.Page):

    container_class = 'container widecontainer'
    content_template = InlineViewPageTemplate('''
      <div tal:content="structure context/schooltool:content/ajax/nodes_table" />
    ''')

    @property
    def title(self):
        return self.context.__parent__.title


class CourseRemoveSkillsView(flourish.page.Page):

    container_class = 'container widecontainer'
    content_template = ViewPageTemplateFile(
        'templates/course_remove_skills.pt')

    @property
    def title(self):
        return self.context.__parent__.title

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())
            return
        selected_skillsets = self.request.get('selected_skillsets', [])
        if not isinstance(selected_skillsets, list):
            selected_skillsets = [selected_skillsets]
        skillsets = []
        for course_skillset in self.context.values():
            skillset = course_skillset.skillset
            skills = []
            for skill in skillset.values():
                title = skill.title
                if skill.label:
                    title = '%s: %s' % (skill.label, title)
                skills.append(title)
            skillsets.append({
                    'label': skillset.label,
                    'title': skillset.title,
                    'skills': skills,
                    'id': skillset.__name__,
                    'checked': skillset.__name__ in selected_skillsets,
                    })
        self.skillsets = skillsets
        if 'SUBMIT_BUTTON' in self.request:
            for course_skillset in self.context.values():
                if course_skillset.skillset.__name__ in selected_skillsets:
                    del self.context[course_skillset.__name__]
            self.request.response.redirect(self.nextURL())

    def nextURL(self):
        return absoluteURL(self.context, self.request)


class CourseAssignSkillSetsDialog(flourish.form.Dialog):

    def initDialog(self):
        super(CourseAssignSkillSetsDialog, self).initDialog()
        self.ajax_settings['dialog']['maxHeight'] = 640
        self.ajax_settings['dialog']['draggable'] = True
        self.ajax_settings['dialog']['dialogClass'] = 'explicit-close-dialog'
        self.ajax_settings['dialog']['closeOnEscape'] = False

    @property
    def error(self):
        return 'SUBMIT_BUTTON' in self.request and \
            'selected_skillsets' not in self.request

    def nextURL(self):
        return absoluteURL(self.context, self.request)

    def nodeContainer(self):
        app = ISchoolToolApplication(None)
        return INodeContainer(app)

    def update(self):
        flourish.form.Dialog.update(self)
        node_id = self.request.get('node_id')
        node = self.nodeContainer().get(node_id)
        selected_skillsets = self.request.get('selected_skillsets', [])
        if not isinstance(selected_skillsets, list):
            selected_skillsets = [selected_skillsets]
        skillsets = []
        if node is not None:
            for skillset in node.skillsets:
                skills = []
                for skill in skillset.values():
                    title = skill.title
                    if skill.label:
                        title = '%s: %s' % (skill.label, title)
                    skills.append(title)
                skillsets.append({
                        'label': skillset.label,
                        'title': skillset.title,
                        'skills': skills,
                        'id': skillset.__name__,
                        'checked': skillset.__name__ in selected_skillsets or 'SUBMIT_BUTTON' not in self.request,
                        })
        self.skillsets = skillsets
        if 'SUBMIT_BUTTON' in self.request:
            if not selected_skillsets:
                return
            for skillset in node.skillsets:
                if skillset.__name__ in selected_skillsets:
                    self.context[skillset.__name__] = CourseSkillSet(skillset)
            self.request.response.redirect(self.nextURL())


class AvailableSkillSetTable(RelationshipAddTableMixin,
                             SkillSetTable):

    @property
    def source(self):
        app = ISchoolToolApplication(None)
        return ISkillSetContainer(app)

    def submitItems(self):
        prefix = self.button_prefix + '.'
        for key in self.request:
            if not key.startswith(prefix):
                continue
            name = key[len(prefix):]
            self.context[name] = CourseSkillSet(self.source[name])


class CourseSkillSetView(UseCourseTitleMixin, flourish.page.Page):
    pass


class CourseSkillSetEditView(UseCourseTitleMixin, flourish.page.Page):
    pass


class SelectAllCheckboxColumn(table.column.CheckboxColumn):

    css_classes = 'select-all'
    script = 'return ST.cando.column_select_all(this);'

    def template(self):
        result = [
            '<span>%(title)s</span>',
            '<input class="%(css_classes)s" type="checkbox" name="%(name)s"',
            '       id="%(id)s" onclick="%(script)s" />',
            ]
        return ''.join(result)

    def renderHeader(self, formatter):
        title = translate(self.title, context=formatter.request,
                          default=self.title)
        name = self.prefix + '-select-all'
        return self.template() % {
            'title': title,
            'css_classes': self.css_classes,
            'name': name,
            'id': name,
            'script': self.script,
            }


class CourseEditSkillSetSkillsTable(table.ajax.Table):

    def updateFormatter(self):
        if self._table_formatter is None:
            self.setUp(table_formatter=self.table_formatter,
                       batch_size=self.batch_size,
                       prefix=self.__name__,
                       css_classes={'table': 'data'})

    def columns(self):
        title = zc.table.column.GetterColumn(name='title',
                             title=_(u"Title"),
                             getter=lambda i, f: i.title,
                             subsort=True)
        label = zc.table.column.GetterColumn(
            name='label',
            title=_(u'Label'),
            getter=lambda i, f: i.label or '')
        required = SelectAllCheckboxColumn(
            self.prefix+'.required',
            name='required',
            title=_(u"Required"),
            id_getter=lambda i: i.__name__,
            value_getter=lambda i: i.required)
        hidden = SelectAllCheckboxColumn(
            self.prefix+'.hidden',
            name='hidden',
            title=_(u"Hidden"),
            id_getter=lambda i: i.__name__,
            value_getter=lambda i: i.retired)
        directlyProvides(title, ISortableColumn)
        directlyProvides(label, ISortableColumn)
        return [label, title, required, hidden]

    def items(self):
        source = self.source
        skillset = source.skillset
        return [source.get(k) for k in skillset]

    def nextURL(self):
        return absoluteURL(self.context, self.request)

    def applyChanges(self):
        for v in self.items():
            k = v.__name__
            required = bool(self.request.get(self.prefix + '.required.' + k))
            hidden = bool(self.request.get(self.prefix + '.hidden.' + k))
            if v.required != required:
                v.required = required
            if v.retired != hidden:
                v.retired = hidden

    def update(self):
        super(CourseEditSkillSetSkillsTable, self).update()
        if 'SUBMIT_BUTTON' in self.request:
            self.applyChanges()
            self.request.response.redirect(self.nextURL())
            return
        if 'CANCEL_BUTTON' in self.request:
            self.request.response.redirect(self.nextURL())
            return

    def sortOn(self):
        return (('label', False),)


class CourseSkillSetSkillTable(SkillSetSkillTable):

    def sortOn(self):
        return (("label", False),)

    def columns(self):
        default = table.ajax.Table.columns(self)
        label = zc.table.column.GetterColumn(
            name='label',
            title=_(u'Label'),
            getter=lambda i, f: i.label or '')
        directlyProvides(label, ISortableColumn)
        return [label] + default


class CourseSkillView(SkillView):

    can_edit = False
