# -*- coding: utf-8 -*-

# Copyright © 2012-2013 Puneeth Chaganti and others.

# Permission is hereby granted, free of charge, to any
# person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the
# Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice
# shall be included in all copies or substantial portions of
# the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
# OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

""" Implementation of compile_html based on Emacs Org-mode.

You will need to install emacs and org-mode (v8.x or greater).

"""

from __future__ import unicode_literals
import codecs
import os
import re
from os.path import abspath, dirname, join
import subprocess

import nikola.utils
logger = nikola.utils.get_logger('plugin.orgmode', nikola.utils.STDERR_HANDLER)

try:
    from collections import OrderedDict
except ImportError:
    OrderedDict = dict  # NOQA

from nikola.plugin_categories import PageCompiler
from nikola.utils import req_missing, makedirs

# v6 compat
try:
    from nikola.utils import write_metadata
except ImportError:
    write_metadata = None  # NOQA


class CompileOrgmode(PageCompiler):
    """ Compile org-mode markup into HTML using emacs. """

    name = "orgmode"
    mode = "pipe"

    def __init__(self):
        self._compile_regexp()
        self._standby_compiler()

    @classmethod
    def _compile_regexp(cls):
        for attrmarker in cls.attrmarkers:
            for index, regexp in enumerate(attrmarker['regexps']):
                attrmarker['regexps'][index] = re.compile(regexp, re.IGNORECASE | re.MULTILINE)
        for maskmarker in cls.maskmarkers:
            maskmarker['begin'] = re.compile(maskmarker['begin'], re.IGNORECASE | re.MULTILINE)
            maskmarker['end'] = re.compile(maskmarker['end'], re.IGNORECASE | re.MULTILINE)
        logger.debug('All regexps were compiled.')

    def _standby_compiler(self):
        if self.mode == 'pipe':
            logger.debug('Spawning emacs process...')
            try:
                self._FNULL = open(os.devnull, 'w')
                self._emacs = subprocess.Popen(
                    ['emacs', '--batch',
                     '--load', join(dirname(abspath(__file__)), 'init.el'),
                     '--eval', '(nikola-start-pipe-mode)'],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=self._FNULL,
                    universal_newlines=True,
                )
            except OSError as err:
                self.mode = 'batch'
                self.compile_html = self.compile_html_batch_mode
                logger.error('Failed to spawn Emacs with pipe mode. Using batch mode instead. reason: {}'.format(err))
            else:
                self.compile_html = self.compile_html_pipe_mode
                logger.debug('Emacs process spawned. pid:{}'.format(self._emacs.pid))
        elif self.mode == 'batch':
            self.compile_html = self.compile_html_batch_mode
        else:
            self.compile_html = self.compile_html_batch_mode
            logger.warning('Compile mode is not selected.')

    def __del__(self):
        if hasattr(self, '_emacs') and not self._emacs.poll():
            self._FNULL.close()
            self._emacs.kill()

    def compile_html_pipe_mode(self, source, dest, is_two_file=True):
        if self.mode == 'batch':
            return self.compile_html_batch_mode(source, dest, is_two_file=True)
        makedirs(os.path.dirname(dest))

        try:
            if os.name == 'nt':
                self._emacs.stdin.write(abspath(source).replace('\\', '\\\\')+'\r\n')
                self._emacs.stdin.write(abspath(dest).replace('\\', '\\\\')+'\r\n')
            else:
                self._emacs.stdin.write(abspath(source)+'\n')
                self._emacs.stdin.write(abspath(dest)+'\n')
            self._emacs.stdin.flush()
            msg = self._emacs.stdout.readline()  # wait for emacs

        except OSError as err:
            import errno
            if err.errno == errno.EPIPE or err.errno == errno.ESHUTDOWN:
                logger.error('Pipe is broken. Maybe Emacs exited? Fallback to batch mode... reason: {}'.format(err))
            else:
                logger.error('OSError reported. Fallback to batch mode... reason: {}'.format(err))
            self.mode = 'batch'
            self.compile_html_batch_mode(source, dest, is_two_file)

        else:
            if '200 OK' in msg:
                logger.debug('Succeeded compile with pipe mode. status: {}'.format(msg))
            else:
                logger.error('Something happend during compile. Fallback to batch mode... reason: {}'.format(msg))
                self.compile_html_batch_mode(source, dest, is_two_file)

    def compile_html_batch_mode(self, source, dest, is_two_file=True):
        makedirs(os.path.dirname(dest))
        try:
            command = [
                'emacs', '--batch',
                '-l', join(dirname(abspath(__file__)), 'init.el'),
                '--eval', '(nikola-html-export "{0}" "{1}")'.format(
                    abspath(source), abspath(dest))
            ]

            # Dirty walkaround for this plugin to run on Windows platform.
            if os.name == 'nt':
                command[5] = command[5].replace("\\", "\\\\")

            subprocess.check_call(command)
        except OSError as e:
            import errno
            if e.errno == errno.ENOENT:
                req_missing(['emacs', 'org-mode'],
                            'use the orgmode compiler', python=False)
        except subprocess.CalledProcessError as e:
                raise Exception('Cannot compile {0} -- bad org-mode '
                                'configuration (return code {1})'.format(
                                    source, e.returncode))

    attrmarkers = (
        {'keyword': 'annotations', 'regexps': [r'^\.\.\s+annotations?\s?:\s*(?P<value>.*)$', r'^\#\+ANNOTATIONS?\s?:\s*(?P<value>.*)$']},
        {'keyword': 'author', 'regexps': [r'^\.\.\s+author\s?:\s*(?P<value>.*)$', r'^\#\+AUTHOR\s?:\s*(?P<value>.*)$']},
        {'keyword': 'category', 'regexps': [r'^\.\.\s+categor(?:y|ies)\s?:\s*(?P<value>.*)$', r'^\#\+CATEGOR(?:Y|IES)\s?:\s*(?P<value>.*)$']},
        {'keyword': 'date', 'regexps': [r'^\.\.\s+date\s?:\s*(?P<value>.*)$', r'^\#\+DATE\s?:\s*(?P<value>.*)$']},
        {'keyword': 'description', 'regexps': [r'^\.\.\s+description\s?:\s*(?P<value>.*)$', r'^\#\+DESCRIPTION\s?:\s*(?P<value>.*)$']},
        {'keyword': 'enclosure', 'regexps': [r'^\.\.\s+enclosure\s?:\s*(?P<value>.*)$', r'^\#\+ENCLOSURE\s?:\s*(?P<value>.*)$']},
        {'keyword': 'filters', 'regexps': [r'^\.\.\s+filters?\s?:\s*(?P<value>.*)$', r'^\#\+FILTERS?\s?:\s*(?P<value>.*)$']},
        {'keyword': 'hidetitle', 'regexps': [r'^\.\.\s+hidetitle\s?:\s*(?P<value>.*)$', r'^\#\+HIDETITLE\s?:\s*(?P<value>.*)$']},
        {'keyword': 'link', 'regexps': [r'^\.\.\s+link\s?:\s*(?P<value>.*)$', r'^\#\+N[-_]?LINK\s?:\s*(?P<value>.*)$']},  # #+LINK is omitted; Emacs uses this attribute as another purpose. Use #+NIKOLA_LINK instead.
        {'keyword': 'noannotations', 'regexps': [r'^\.\.\s+noannotations?\s?:\s*(?P<value>.*)$', r'^\#\+NOANNOTATIONS?\s?:\s*(?P<value>.*)$']},
        {'keyword': 'nocomments', 'regexps': [r'^\.\.\s+nocomments?\s?:\s*(?P<value>.*)$', r'^\#\+NOCOMMENTS?\s?:\s*(?P<value>.*)$']},
        {'keyword': 'password', 'regexps': [r'^\.\.\s+password\s?:\s*(?P<value>.*)$', r'^\#\+PASSWORD\s?:\s*(?P<value>.*)$']},
        {'keyword': 'previewimage', 'regexps': [r'^\.\.\s+previewimage\s?:\s*(?P<value>.*)$', r'^\#\+PREVIEWIMAGE\s?:\s*(?P<value>.*)$']},
        {'keyword': 'slug', 'regexps': [r'^\.\.\s+slug\s?:\s*(?P<value>.*)$', r'^\#\+SLUG\s?:\s*(?P<value>.*)$']},
        {'keyword': 'tags', 'regexps': [r'^\.\.\s+tags?\s?:\s*(?P<value>.*)$', r'^\#\+N[-_]?TAGS?\s?:\s*(?P<value>.*)$']},  # #+TAGS is omitted; Emacs uses this attribute more advanced. Use #+NIKOLA_TAGS instead.
        {'keyword': 'template', 'regexps': [r'^\.\.\s+template\s?:\s*(?P<value>.*)$', r'^\#\+TEMPLATE\s?:\s*(?P<value>.*)$']},
        {'keyword': 'title', 'regexps': [r'^\.\.\s+title\s?:\s*(?P<value>.*)$', r'^\#\+TITLE\s?:\s*(?P<value>.*)$']},
        {'keyword': 'type', 'regexps': [r'^\.\.\s+type\s?:\s*(?P<value>.*)$', r'^\#\+TYPE\s?:\s*(?P<value>.*)$']},
    )
    maskmarkers = (
        {'begin': r'^\#\+BEGIN[-_]EXAMPLE', 'end': r'^\#\+END[-_]EXAMPLE'},
        {'begin': r'^\#\+BEGIN[-_]NIKOLA[-_]IGNORE', 'end': r'^\#\+END[-_]NIKOLA[-_]IGNORE'},
        {'begin': r'^\#\+BEGIN[-_]SRC', 'end': r'^\#\+END[-_]SRC'},
    )

    def read_metadata(self, post, *args, **kwargs):
        """This function parse metadata.
        Parse will be disabled in special section
        '#+BEGIN_NIKOLA_IGNORE ... #+END_NIKOLA_IGNORE'.
        You can write metadata in your .org decument with following syntax.
        Lower number is high priority.

        1. #+NIKOLA_TITLE: Awesome title
           #+NIKOLA_DATE: 2015-01-01 09:00:00 UTC+09:00
           #+NIKOLA_SLUG: this-is-an-awesome-page

        2. #+BEGIN_COMMENT
           .. title: Awesome title
           .. date: 2015-01-01 09:00:00 UTC+09:00
           .. slug: this-is-an-awesome-page
           #+END_COMMENT

        3. #+TITLE: Awesome title
           #+DATE: 2015-01-01 09:00:00 UTC+09:00
           #+SLUG: this-is-an-awesome-page
           #+N_TAGS: this, is, special, case
           #+N_LINK: http://this.is.special.case/too
        """

        if hasattr(post, 'orgmode_testdata'):  # for unittest
            content = post.orgmode_testdata
            post.source_path = 'unittest'
        else:
            try:
                with codecs.open(post.source_path, 'r', "utf8") as fd:
                    content = fd.read()
            except OSError as err:
                logger.critical('Couln\'t open the file. Stop processing. reason: {} file: {}'.format(err, post.source_path))
                raise

        logger.debug('*** Start metadata parsing. file: {} ***'.format(post.source_path))

        def find_section(regexps, content):
            pos_pairs = set()
            for marker in regexps:
                logger.debug('Looking for blocks with regexp. begin: {} end: {}'.format(marker['begin'], marker['end']))
                if isinstance(marker['begin'], type(re.compile(''))):
                    begin_match = marker['begin'].finditer(content)
                else:
                    begin_match = re.finditer(marker['begin'], content, re.IGNORECASE | re.MULTILINE)
                begin_pos = (match.start() for match in begin_match)
                if isinstance(marker['end'], type(re.compile(''))):
                    end_match = marker['end'].finditer(content)
                else:
                    end_match = re.finditer(marker['end'], content, re.IGNORECASE | re.MULTILINE)
                end_pos = (match.end() for match in end_match)
                pos_pairs.update(x for x in zip(begin_pos, end_pos))
            for pos_pair in pos_pairs:
                logger.debug('A block was found. blocks: {}'.format(content[pos_pair[0]:pos_pair[1]]))
            return pos_pairs

        # convert maskmarkers to maskranges #
        maskranges = find_section(self.maskmarkers, content)

        def check_mask_range(span, maskranges):
            for maskrange in maskranges:
                if maskrange[0] < span[0] < maskrange[1] or maskrange[0] < span[1] < maskrange[1]:
                    return False
            return True

        def find_attr_gen(match_iter, maskranges):
            for match in match_iter:
                if check_mask_range(match.span(), maskranges):
                    yield match
                else:
                    logger.debug('Masked metadata was found. masked: {}'.format(match.group()))

        # find metadata #
        metadata = dict()
        for attrmarker in self.attrmarkers:
            for regexp in attrmarker['regexps']:
                match_iter = find_attr_gen(regexp.finditer(content), maskranges)
                logger.debug('Looking for metadata with compiled regexp. attrmarker: {}'.format(regexp.pattern))
                try:
                    match = next(match_iter)
                except StopIteration: pass
                else:
                    metadata[attrmarker['keyword']] = match.group('value')
                    logger.debug('Valid metadata was found. key: {}, value: {}'.format(attrmarker['keyword'], match.group('value')))
                    break
        local_metadata = dict()
        match_iter = find_attr_gen(re.finditer(r'^\#\+NIKOLA[-_](?P<keyword>\w+?)\s?:\s*(?P<value>.*)$', content, re.IGNORECASE | re.MULTILINE), maskranges)
        for match in match_iter:
            keyword = match.group('keyword').lower()
            value = match.group('value')
            if keyword not in local_metadata:
                local_metadata[keyword] = value
                logger.debug('Valid metadata was found. key: {}, value: {}'.format(keyword, value))
        metadata.update(local_metadata)

        logger.debug('*** End metadata parsing. file: {} ***'.format(post.source_path))

        return metadata

    def create_post(self, path, **kw):
        content = kw.pop('content', None)
        onefile = kw.pop('onefile', False)
        kw.pop('is_page', False)

        metadata = OrderedDict()
        metadata.update(self.default_metadata)
        metadata.update(kw)
        makedirs(os.path.dirname(path))

        with codecs.open(path, "wb+", "utf8") as fd:
            if onefile:
                fd.write("#+BEGIN_COMMENT\n")
                if write_metadata:
                    fd.write(write_metadata(metadata))
                else:
                    for k, v in metadata.items():
                        fd.write('.. {0}: {1}\n'.format(k, v))
                fd.write("#+END_COMMENT\n")
                fd.write("\n\n")

            if content:
                fd.write(content)
            else:
                fd.write('Write your post here.')
