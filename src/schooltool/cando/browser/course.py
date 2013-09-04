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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Course skill views.
"""
import zope.lifecycleevent
from zope.cachedescriptors.property import Lazy
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.i18n import translate
from zope.i18n.interfaces.locales import ICollator
from zope.interface import directlyProvides
from zope.traversing.browser.absoluteurl import absoluteURL
import zc.table.column
from zc.table.interfaces import ISortableColumn

from schooltool.app.browser.app import RelationshipAddTableMixin
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.course.interfaces import ICourseContainer
from schooltool.cando.course import CourseSkillSet
from schooltool.cando.interfaces import ICourseSkills
from schooltool.cando.interfaces import ILayerContainer
from schooltool.cando.interfaces import INodeContainer
from schooltool.cando.interfaces import INode
from schooltool.cando.interfaces import ISkillSetContainer
from schooltool.cando.browser.skill import SkillSetTable, SkillSetSkillTable
from schooltool.cando.browser.skill import SkillView
from schooltool.cando.model import URINode, URINodeLayer
from schooltool.course.interfaces import ICourse
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.relationship import getRelatedObjects
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.schoolyear.interfaces import ISchoolYear
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
      <script type="text/javascript">
        $(document).ready(function() {
            // accordion setup
            $( "table.courseskills-table" ).accordion({
                header: 'h2',
                active: false,
                collapsible: true,
                autoHeight: false
            });
        });
      </script>
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
      <div class="skillsets-selection skillsets-selection-courseskills">
        <div tal:content="structure context/schooltool:content/ajax/table" />
      </div>
      <h3 i18n:domain="schooltool" class="done-link">
        <a tal:attributes="href context/__parent__/@@absolute_url"
           i18n:translate="">Done</a>
      </h3>
    ''')

    @property
    def title(self):
        return self.context.__parent__.title


def skillset_accordion_formatter(value, item, formatter):
    collator = ICollator(formatter.request.locale)
    skillset = item.skillset
    cell_template = [
        '<h2>%s</h2>',
        '<div>',
        '<ul class="skills">',
        '%s',
        '</ul>',
        '</div>',
        ]
    title = skillset.title
    if skillset.label:
        title = '%s: %s' % (skillset.label, skillset.title)
    skills = []
    for skill in sorted(item.values(),
                        key=lambda x:(collator.key(x.label or ''),
                                      collator.key(x.title))):
        skill_title = skill.title
        if skill.label:
            skill_title = '%s: %s' % (skill.label, skill.title)
        skills.append('<li%s>%s</li>' % (not skill.required and ' class="optional"' or '', skill_title))
    return ''.join(cell_template) % (title, ''.join(skills))


class CourseSkillsTable(table.ajax.Table):

    batch_size = 0
    visible_column_names = ['title', 'skills']

    def updateFormatter(self):
        if self._table_formatter is None:
            self.setUp(table_formatter=self.table_formatter,
                       batch_size=self.batch_size,
                       prefix=self.__name__,
                       css_classes={'table': 'courseskills-table'})

    def columns(self):
        label = table.column.LocaleAwareGetterColumn(
            name='label',
            title=u'Label',
            getter=lambda i, f: i.skillset.label or '',
            subsort=True)
        raw_title = table.column.LocaleAwareGetterColumn(
            name='raw_title',
            title=u'Raw Title',
            getter=lambda i, f: i.title,
            subsort=True)
        title = zc.table.column.GetterColumn(
            name='title',
            title=_('Title'),
            cell_formatter=skillset_accordion_formatter,
            getter=lambda i, f: i.title,
            subsort=True)
        skills = zc.table.column.GetterColumn(
            name='skills',
            title=_(u'Skills'),
            getter=lambda i, f: str(len(i)))
        return [label, raw_title, title, skills]

    def sortOn(self):
        return (('label', False), ('raw_title', False))


class CourseSkillsLinks(flourish.page.RefineLinksViewlet):
    pass


class RemoveSkillsLinkViewlet(flourish.page.LinkViewlet):

    @property
    def enabled(self):
        return bool(self.context)


class EditSkillsLinkViewlet(flourish.page.LinkViewlet):

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
            if node.skillsets and not node.retired:
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
                     searchstr in getattr(item, 'label', '').lower() or
                     searchstr in getattr(item, 'description', '').lower()]
        return items


class SkillsetNodesTableDoneLink(flourish.viewlet.Viewlet):

    template = InlineViewPageTemplate('''
    <h3 class="done-link" i18n:domain="schooltool">
      <a tal:attributes="href context/@@absolute_url"
         i18n:translate="">Done</a>
    </h3>
    ''')


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
        collator = ICollator(self.request.locale)
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
            for skill in sorted(skillset.values(),
                                key=lambda x:(collator.key(x.label or ''),
                                              collator.key(x.title))):
                course_skill = course_skillset[skill.__name__]
                title = skill.title
                if skill.label:
                    title = '%s: %s' % (skill.label, title)
                css_class = not course_skill.required and 'optional' or None
                skills.append({
                        'title': title,
                        'css_class': css_class,
                        })
            skillsets.append({
                    'label': skillset.label,
                    'title': skillset.title,
                    'skills': skills,
                    'id': skillset.__name__,
                    'checked': skillset.__name__ in selected_skillsets,
                    })
        self.skillsets = sorted(skillsets,
                                key=lambda x:(collator.key(x['label'] or ''),
                                              collator.key(x['title'])))
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
        collator = ICollator(self.request.locale)
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
                for skill in sorted(skillset.values(),
                                    key=lambda x:(collator.key(x.label or ''),
                                                  collator.key(x.title))):
                    title = skill.title
                    if skill.label:
                        title = '%s: %s' % (skill.label, title)
                    css_class = not skill.required and 'optional' or None
                    skills.append({
                            'label': skill.label,
                            'raw_title': skill.title,
                            'title': title,
                            'css_class': css_class,
                            })
                skillsets.append({
                        'label': skillset.label,
                        'title': skillset.title,
                        'skills': skills,
                        'id': skillset.__name__,
                        'checked': skillset.__name__ in selected_skillsets or 'SUBMIT_BUTTON' not in self.request,
                        })
        self.skillsets = sorted(skillsets,
                                key=lambda x:(collator.key(x['label'] or ''),
                                              collator.key(x['title'])))
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


class EditCourseSkillsView(UseCourseTitleMixin, flourish.page.Page):

    content_template = ViewPageTemplateFile(
        'templates/edit_course_skills.pt')

    @Lazy
    def submitted(self):
        return 'SUBMIT_BUTTON' in self.request

    def nextURL(self):
        return absoluteURL(self.context, self.request)

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())
            return
        skillsets = []
        required_prefix = 'required.'
        visible_prefix = 'visible.'
        collator = ICollator(self.request.locale)
        for course_skillset_id in self.context:
            skillset_modified = False
            course_skillset = self.context[course_skillset_id]
            skillset = course_skillset.skillset
            title = skillset.title
            if skillset.label:
                title = '%s: %s' % (skillset.label, title)
            skills = []
            for skill in sorted(skillset.values(),
                                key=lambda x:(collator.key(x.label or ''),
                                              collator.key(x.title))):
                course_skill = course_skillset[skill.__name__]
                skill_title = skill.title
                if skill.label:
                    skill_title = '%s: %s' % (skill.label, skill_title)
                skill_id = self.getId(course_skill)
                required_name = required_prefix + skill_id
                visible_name = visible_prefix + skill_id
                if self.submitted:
                    required = required_name in self.request
                    if course_skill.required != required:
                        course_skill.required = required
                        skillset_modified = True
                    deprecated = visible_name in self.request
                    if course_skill.retired != deprecated:
                        course_skill.retired = deprecated
                        skillset_modified = True
                skills.append({
                        'id': skill_id,
                        'title': skill_title,
                        'required_checked': course_skill.required,
                        'required_name': required_name,
                        'visible_checked': course_skill.retired,
                        'visible_name': visible_name,
                        })
            skillsets.append({
                    'label': skillset.label,
                    'raw_title': skillset.title,
                    'title': title,
                    'skills': skills,
                    })
            if skillset_modified:
                zope.lifecycleevent.modified(course_skillset)
        if self.submitted:
            self.request.response.redirect(self.nextURL())
            return
        self.skillsets = sorted(skillsets,
                                key=lambda x:(collator.key(x['label'] or ''),
                                              collator.key(x['raw_title'])))

    def getId(self, skill):
        skillset = skill.__parent__
        return '%s.%s' % (skillset.__name__, skill.__name__)


class CanDoCoursesActionsLinks(flourish.page.RefineLinksViewlet):
    pass


class CoursesSkillsAssignmentView(flourish.page.Page):

    matched = []
    not_matched = []
    container_class = 'container widecontainer'
    content_template = ViewPageTemplateFile(
        'templates/courses_skills_assignment.pt')

    @property
    def course_attrs(self):
        attrs = ['__name__', 'title', 'description',
                 'course_id', 'government_id']
        return [{'title': ICourse[attr].title, 'value': attr}
                for attr in attrs]

    @property
    def node_attrs(self):
        attrs = ['label', 'title', 'description']
        return [{'title': INode[attr].title, 'value': attr}
                for attr in attrs]

    @property
    def courses(self):
        return ICourseContainer(self.context)

    @property
    def layers(self):
        app = ISchoolToolApplication(None)
        return ILayerContainer(app)

    @property
    def nodes(self):
        app = ISchoolToolApplication(None)
        return INodeContainer(app)

    @property
    def skills(self):
        app = ISchoolToolApplication(None)
        return ISkillSetContainer(app)

    def getSkillSetID(self, skillset):
        return skillset.__name__.split('-')[0]

    def requiredSubmitted(self):
        required = ['course_attr', 'layer', 'node_attr']
        for attr in required:
            if not self.request.get(attr, ''):
                return False
        return True

    def nextURL(self):
        app = ISchoolToolApplication(None)
        schoolyear = ISchoolYear(self.context)
        return '%s/courses?schoolyear_id=%s' % (absoluteURL(app, self.request),
                                                schoolyear.__name__)

    def updateMatches(self):
        assignments = []
        not_assigned = []
        course_attr = self.request['course_attr']
        layer = self.layers[self.request['layer']]
        node_attr = self.request['node_attr']
        nodes = list(getRelatedObjects(layer, URINode, URINodeLayer))
        for course in self.courses.values():
            course_attr_value = getattr(course, course_attr, '')
            skills = ICourseSkills(course)
                # only use courses with no skills
            if skills:
                not_assigned.append({
                        'course': course,
                        'course_attr': course_attr_value,
                        'reason': _('Course has skills assigned already'),
                        })
                continue
            if course_attr_value:
                assigned = False
                for node in nodes:
                    node_attr_value = getattr(node, node_attr, '')
                    if node_attr_value:
                        if (node_attr_value == course_attr_value and
                            not node.retired):
                            assignments.append({
                                    'course': course,
                                    'course_attr': course_attr_value,
                                    'node': node,
                                    'node_attr': node_attr_value,
                                    })
                            assigned = True
                if not assigned:
                    not_assigned.append({
                            'course': course,
                            'course_attr': course_attr_value,
                            'reason': _("Couldn't find a matching node"),
                            })
            else:
                not_assigned.append({
                        'course': course,
                        'course_attr': course_attr_value,
                        'reason': _('Course attribute is empty'),
                        })
        self.matched = assignments
        self.not_matched = not_assigned

    def update(self):
        collator = ICollator(self.request.locale)
        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())
            return
        if self.requiredSubmitted():
            self.updateMatches()
            if 'ASSIGN_BUTTON' in self.request:
                for info in self.matched:
                    course = info['course']
                    node = info['node']
                    skills = ICourseSkills(course)
                    for skillset in node.skillsets:
                        skills[skillset.__name__] = CourseSkillSet(skillset)
                self.request.response.redirect(self.nextURL())
                return
            if 'SEARCH_BUTTON' in self.request:
                self.matched = sorted(
                    self.matched,
                    key=lambda x:(x['course_attr'],
                                  collator.key(x['course'].title))
                    )
                self.not_matched = sorted(
                    self.not_matched,
                    key=lambda x:(x['course_attr'],
                                  collator.key(x['course'].title))
                    )


class BatchAssignSkillsLinkViewlet(flourish.page.LinkViewlet):

    @property
    def schoolyear(self):
        schoolyears = ISchoolYearContainer(self.context)
        result = schoolyears.getActiveSchoolYear()
        if 'schoolyear_id' in self.request:
            schoolyear_id = self.request['schoolyear_id']
            result = schoolyears.get(schoolyear_id, result)
        return result

    @property
    def courses(self):
        return ICourseContainer(self.schoolyear)

    @property
    def enabled(self):
        return bool(self.courses)

    @property
    def url(self):
        return '%s/%s' % (absoluteURL(self.courses, self.request),
                          'assign-courses-skills.html')
