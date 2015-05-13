# clize -- A command-line argument parser for Python
# Copyright (C) 2011-2015 by Yann Kaiser <kaiser.yann@gmail.com>
# See COPYING for details.

from datetime import datetime
import unittest
import tempfile
import shutil
import os
import stat

from sigtools import support, modifiers

from clize import parser, errors, converters
from clize.tests import util


@util.repeated_test
class ConverterRepTests(object):
    def _test_func(self, conv, rep):
        sig = support.s('*, par: c', locals={'c': conv})
        csig = parser.CliSignature.from_signature(sig)
        self.assertEqual(str(csig), rep)

    datetime = converters.datetime, '--par=TIME'
    file = converters.file(), '--par=FILE'


@util.repeated_test
class ConverterTests(object):
    def _test_func(self, conv, inp, out):
        sig = support.s('*, par: c', locals={'c': conv})
        csig = parser.CliSignature.from_signature(sig)
        ba = util.read_arguments(csig, ['--par', inp])
        self.assertEqual(out, ba.kwargs['par'])

    dt_jan1 = (
        converters.datetime, '2014-01-01 12:00', datetime(2014, 1, 1, 12, 0))


class FileConverterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp)

    def run_conv(self, conv, path):
        sig = support.s('*, par: c', locals={'c': conv})
        csig = parser.CliSignature.from_signature(sig)
        ba = util.read_arguments(csig, ['--par', path])
        return ba.kwargs['par']

    def test_ret_type(self):
        path = os.path.join(self.temp, 'afile')
        arg = self.run_conv(converters.file(mode='w'), path)
        self.assertTrue(isinstance(arg, converters._FileOpener))
        type(arg).__enter__

    def test_file_read(self):
        path = os.path.join(self.temp, 'afile')
        open(path, 'w').close()
        @modifiers.annotate(afile=converters.file())
        def func(afile):
            with afile as f:
                self.assertEqual(f.name, path)
                self.assertEqual(f.mode, 'r')
            self.assertTrue(f.closed)
        o, e = util.run(func, ['test', path])
        self.assertFalse(o.getvalue())
        self.assertFalse(e.getvalue())

    def test_file_write(self):
        path = os.path.join(self.temp, 'afile')
        @modifiers.annotate(afile=converters.file(mode='w'))
        def func(afile):
            self.assertFalse(os.path.exists(path))
            with afile as f:
                self.assertEqual(f.name, path)
                self.assertEqual(f.mode, 'w')
            self.assertTrue(f.closed)
            self.assertTrue(os.path.exists(path))
        o, e = util.run(func, ['test', path])
        self.assertFalse(o.getvalue())
        self.assertFalse(e.getvalue())

    def test_file_missing(self):
        path = os.path.join(self.temp, 'afile')
        self.assertRaises(errors.BadArgumentFormat,
                          self.run_conv, converters.file(), path)
        @modifiers.annotate(afile=converters.file())
        def func(afile):
            raise NotImplementedError
        stdout, stderr = util.run(func, ['test', path])
        self.assertFalse(stdout.getvalue())
        self.assertTrue(stderr.getvalue().startswith(
            'test: Bad value for afile: File does not exist: '))

    def test_dir_missing(self):
        path = os.path.join(self.temp, 'adir/afile')
        self.assertRaises(errors.BadArgumentFormat,
                          self.run_conv, converters.file(mode='w'), path)
        @modifiers.annotate(afile=converters.file(mode='w'))
        def func(afile):
            raise NotImplementedError
        stdout, stderr = util.run(func, ['test', path])
        self.assertFalse(stdout.getvalue())
        self.assertTrue(stderr.getvalue().startswith(
            'test: Bad value for afile: Directory does not exist: '))

    def test_noperm_file_write(self):
        path = os.path.join(self.temp, 'afile')
        open(path, mode='w').close()
        os.chmod(path, stat.S_IRUSR)
        self.assertRaises(errors.BadArgumentFormat,
                          self.run_conv, converters.file(mode='w'), path)

    def test_noperm_dir(self):
        dpath = os.path.join(self.temp, 'adir')
        path = os.path.join(self.temp, 'adir/afile')
        os.mkdir(dpath)
        os.chmod(dpath, stat.S_IRUSR)
        self.assertRaises(errors.BadArgumentFormat,
                          self.run_conv, converters.file(mode='w'), path)

    def test_race(self):
        path = os.path.join(self.temp, 'afile')
        open(path, mode='w').close()
        @modifiers.annotate(afile=converters.file(mode='w'))
        def func(afile):
            os.chmod(path, stat.S_IRUSR)
            with afile:
                raise NotImplementedError
        stdout, stderr = util.run(func, ['test', path])
        self.assertFalse(stdout.getvalue())
        self.assertTrue(stderr.getvalue().startswith(
            'test: Permission denied: '))


@util.repeated_test
class ConverterErrorTests(object):
    def _test_func(self, conv, inp):
        sig = support.s('*, par: c', locals={'c': conv})
        csig = parser.CliSignature.from_signature(sig)
        self.assertRaises(errors.BadArgumentFormat,
                          util.read_arguments, csig, ['--par', inp])

    dt_baddate = converters.datetime, 'not a date'