# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys
import unittest

sys.path.append(os.path.join('v6', 'orgmode'))
import orgmode

class OrgmodeTestBase(unittest.TestCase):
    def setUp(self):
        self.target = orgmode.CompileOrgmode
        self.target.no_guess = True
        self.post = type(str('testpost'), (object,), {})

    def tearDown(self):
        if hasattr(self, 'result'):
            del self.result

    def setData(self, *testdatas):
        testdata = '\n'.join(testdatas)
        setattr(self.post, 'orgmode_testdata', testdata)

    def chk(self, correct, answer=None):
        if not answer:
            answer = self.result
        return self.assertFalse(
            self.compDict(correct, answer),
            'The right answer is: {}, but the output is: {}'
            .format(correct, answer))

    def req(self, post=None, target=None):
        if not post:
            post = self.post
        if not target:
            target = self.target.__new__(self.target)  # avoid to execute __init__
        self.result = self.target.read_metadata(target, post)
        return self.result

    @staticmethod
    def compDict(dictl, dictr):
        return set(dictl.items()) ^ set(dictr.items())

class SyntaxTest(OrgmodeTestBase):
    sampledata = {
        'annotations': 'True',
        'author': 'John Doe <john@example.com>',
        'category': 'sampledata',
        'date': '2018-08-08 20:02',
        'description': 'This is sample description,',
        'enclosure': 'http://example.com/test.mp3',
        'filters': 'filters.html_tidy_nowrap, "sed s/foo/bar"',
        'hidetitle': 'True',
        'link': 'http://example.com/test/data',
        'noannotations': 'True',
        'nocomments': 'True',
        'password': 'drowssap',
        'previewimage': 'images/testimage.png',
        'slug': 'this-is-sample-slug',
        'tags': 'sample, data, unittest',
        'template': 'testtemplate.tmpl',
        'title': 'This is sample title',
        'type': 'text',
    }

    @staticmethod
    def generate_test(key, value):
        def syntaxA(self):
            self.setData('#+NIKOLA_{}: {}'.format(key.upper(), value))
            self.req()
            self.chk({key: value})
        def syntaxB(self):
            self.setData('.. {}: {}'.format(key.lower(), value))
            self.req()
            self.chk({key: value})
        def syntaxC(self):
            key_ = key
            if key == 'link':
                key_ = 'n_link'
            elif key == 'tags':
                key_ = 'n_tags'
            self.setData('#+{}: {}'.format(key_.upper(), value))
            self.req()
            self.chk({key: value})
        return (syntaxA, syntaxB, syntaxC,)

    def testMDa1(self):
        self.setData('#+TITLE: This is test')
        self.req()
        self.chk({'title': 'This is test'})

    def testMDa2(self):
        self.setData(
            '#+BEGIN_COMMENT',
            '.. title: This is test',
            '#+END_COMMENT',)
        self.req()
        self.chk({'title': 'This is test'})

    def testMDa3(self):
        self.setData('#+NIKOLA_TITLE: This is test')
        self.req()
        self.chk({'title': 'This is test'})

    def testMDa4(self):
        self.setData('#+tItLe: tHIS IS tEST')
        self.req()
        self.chk({'title': 'tHIS IS tEST'})

    def testMDa5(self):
        self.setData(
            '#+BEGIN_COMMENT',
            '.. tItLe: tHIS IS tEST',
            '#+END_COMMENT',)
        self.req()
        self.chk({'title': 'tHIS IS tEST'})

    def testMDa6(self):
        self.setData('#+nIkOlA-tItLe: tHIS IS tEST')
        self.req()
        self.chk({'title': 'tHIS IS tEST'})

    def testMDa7(self):
        self.setData('#+nIkOlA_tItLe :   tHIS IS tEST')
        self.req()
        self.chk({'title': 'tHIS IS tEST'})

    def testMDa8(self):
        self.setData('#+tItLe :   tHIS IS tEST')
        self.req()
        self.chk({'title': 'tHIS IS tEST'})

    def testMDb1(self):
        self.setData(
            '#+TITLE: This is title1',
            '#+TITLE: This is title2',
            '#+TITLE: This is title3',)
        self.req()
        self.chk({'title': 'This is title1'})

    def testMDb2(self):
        self.setData(
            '#+NIKOLA_TITLE: This is title1',
            '#+NIKOLA_TITLE: This is title2',
            '#+NIKOLA_TITLE: This is title3',)
        self.req()
        self.chk({'title': 'This is title1'})

    def testMDb3(self):
        self.setData(
            '.. title: This is title1',
            '.. title: This is title2',
            '.. title: This is title3',)
        self.req()
        self.chk({'title': 'This is title1'})

    def testMDc1(self):
        self.setData(
            '.. title: This is title2',
            '#+NIKOLA_TITLE: This is title1',
            '#+TITLE: This is title3',)
        self.req()
        self.chk({'title': 'This is title1'})

    def testMDc2(self):
        self.setData(
            '#+TITLE: This is title1',
            '.. title: This is title2',
            '#+TITLE: This is title3',)
        self.req()
        self.chk({'title': 'This is title2'})

    def testMDd1(self):
        self.setData(
            '#+BEGIN_NIKOLA_IGNORE',
            '#+NIKOLA_TITLE: This is title',
            '#+END_NIKOLA_IGNORE',)
        self.req()
        self.chk({})

    def testMDd2(self):
        self.setData(
            '#+BEGIN_EXAMPLE',
            '#+TITLE: This is title',
            '#+END_EXAMPLE',)
        self.req()
        self.chk({})

    def testMDd3(self):
        self.setData(
            '#+BEGIN_SRC',
            '#+BEGIN_COMMENT',
            '.. title: This is title',
            '#+END_COMMENT',
            '#+END_SRC',)
        self.req()
        self.chk({})

    def testMDe1(self):
        self.setData(
            '#+NIKOLA_AUTHOR: John Doe',
            '#+BEGIN_NIKOLA_IGNORE',
            '#+NIKOLA_TITLE: This is title',
            '#+BEGIN_NIKOLA_IGNORE',
            '#+NIKOLA_DATE: 2038-07-29',
            '#+END_NIKOLA_IGNORE',
            '#+NIKOLA_SLUG: this-is-slug',
            '#+END_NIKOLA_IGNORE',
            '#+NIKOLA_CATEGORY: testcase',)
        self.req()
        self.chk({'author': 'John Doe', 'category': 'testcase'})

    def testMDe2(self):
        self.setData(
            '#+NIKOLA_AUTHOR: John Doe',
            '#+BEGIN_EXAMPLE',
            '#+NIKOLA_TITLE: This is title',
            '#+BEGIN_SRC',
            '#+NIKOLA_DATE: 2038-07-29',
            '#+END_SRC',
            '#+NIKOLA_SLUG: this-is-slug',
            '#+END_EXAMPLE',
            '#+NIKOLA_CATEGORY: testcase',)
        self.req()
        self.chk({'author': 'John Doe', 'category': 'testcase'})

    def testMDe3(self):
        self.setData(
            '#+BEGIN_NIKOLA_IGNORE',
            '#+NIKOLA_AUTHOR: John Doe',
            '#+BEGIN_EXAMPLE',
            '#+NIKOLA_TITLE: This is title',
            '#+BEGIN_SRC',
            '#+NIKOLA_DATE: 2038-07-29',
            '#+END_SRC',
            '#+NIKOLA_SLUG: this-is-slug',
            '#+END_EXAMPLE',
            '#+NIKOLA_CATEGORY: testcase',
            '#+END_NIKOLA_IGNORE',)
        self.req()
        self.chk({})

    def testMDf1(self):
        self.setData(
            '#+NIKOLA_AUTHOR: John Doe',
            '#+BEGIN_EXAMPLE',
            '#+NIKOLA_TITLE: This is title',
            '#+BEGIN_SRC',
            '#+NIKOLA_DATE: 2038-07-29',
            '#+END_EXAMPLE',
            '#+NIKOLA_SLUG: this-is-slug',
            '#+END_SRC',
            '#+NIKOLA_CATEGORY: testcase',)
        self.req()
        self.chk({'author': 'John Doe', 'category': 'testcase'})

    def testMDf2(self):
        self.setData(
            '#+END_NIKOLA_IGNORE',
            '#+NIKOLA_AUTHOR: John Doe',
            '#+BEGIN_EXAMPLE',
            '#+NIKOLA_TITLE: This is title',
            '#+BEGIN_SRC',
            '#+NIKOLA_DATE: 2038-07-29',
            '#+END_SRC',
            '#+NIKOLA_SLUG: this-is-slug',
            '#+END_EXAMPLE',
            '#+NIKOLA_CATEGORY: testcase',
            '#+BEGIN_NIKOLA_IGNORE',)
        self.req()
        self.chk({'author': 'John Doe', 'category': 'testcase'})

orgmode.CompileOrgmode._compile_regexp()
for k, v in SyntaxTest.sampledata.items():
    for f in SyntaxTest.generate_test(k, v):
        setattr(SyntaxTest, 'testMDauto_{}_{}'.format(f.__name__, k), f)

if __name__ == '__main__':
    unittest.main()