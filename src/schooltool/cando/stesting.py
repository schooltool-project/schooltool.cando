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
Selenium Functional Testing Utilities for skills.
"""
import os

from schooltool.testing.selenium import SeleniumLayer

dir = os.path.abspath(os.path.dirname(__file__))
filename = os.path.join(dir, 'stesting.zcml')

skill_selenium_layer = SeleniumLayer(filename,
                                      __name__,
                                      'skill_selenium_layer')

def registerSeleniumSetup():
    try:
        import selenium
    except ImportError:
        return
    from schooltool.testing import registry
    import schooltool.testing.selenium

    def importGlobalSkills(browser, filename):
        browser.query.link('School').click()
        browser.query.link('Import Skill Data').click()
        if filename:
            browser.query.name('xlsfile').type(filename)
        page = browser.query.tag('html')
        browser.query.button('Submit').click()
        browser.wait(lambda: page.expired)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'skill.import_xls', importGlobalSkills))

    def addSkillSet(browser, title, label=None):
        browser.query.link('School').click()
        browser.query.link('Skills').click()
        browser.query.link('Skill Sets').click()
        browser.query.link('Skill Set').click()
        browser.query.name('form.widgets.title').type(title)
        if label is not None:
            browser.query.name('form.widgets.label').type(label)
        page = browser.query.tag('html')
        browser.query.button('Submit').click()
        browser.wait(lambda: page.expired)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'skillset.add', addSkillSet))

    def addSkill(browser, skillset, title, label=None, required=True,
                 external_id=None, scoresystem=None):
        browser.query.link('School').click()
        browser.query.link('Skills').click()
        browser.query.link('Skill Sets').click()
        browser.query.link(skillset).click()
        browser.query.link('Skill').click()
        browser.query.name('form.widgets.title').type(title)
        if label is not None:
            browser.query.name('form.widgets.label').type(label)
        if required:
            browser.query.id('form-widgets-required-0').click()
        else:
            browser.query.id('form-widgets-required-1').click()
        if external_id is not None:
            browser.query.name('form.widgets.external_id').type(external_id)
        if scoresystem is not None:
            browser.query.name('form.widgets.scoresystem:list').ui.set_value(scoresystem)
        else:
            browser.query.name('form.widgets.scoresystem:list').ui.set_value('Competency')
        page = browser.query.tag('html')
        browser.query.button('Submit').click()
        browser.wait(lambda: page.expired)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'skill.add', addSkill))

    def addLayer(browser, title):
        browser.query.link('School').click()
        browser.query.link('Skills').click()
        browser.query.link('Layers').click()
        browser.query.link('Layer').click()
        browser.query.name('form.widgets.title').type(title)
        page = browser.query.tag('html')
        browser.query.button('Submit').click()
        browser.wait(lambda: page.expired)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'layer.add', addLayer))

    def addNode(browser, title, label=None):
        browser.query.link('School').click()
        browser.query.link('Skills').click()
        browser.query.link('Search').click()
        browser.query.link('Node').click()
        browser.query.name('form.widgets.title').type(title)
        if label is not None:
            browser.query.name('form.widgets.label').type(label)
        page = browser.query.tag('html')
        browser.query.button('Submit').click()
        browser.wait(lambda: page.expired)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'node.add', addNode))

registerSeleniumSetup()
del registerSeleniumSetup
