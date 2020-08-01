#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import sys
import pytest
import shutil
import tempfile

from unittest.mock import patch
from io import StringIO

from contextlib import contextmanager
from cacheman.cacher import get_cache_manager
from hunspell import Hunspell, HunspellFilePathError

DICT_DIR = os.path.join(os.path.dirname(__file__), '..', 'dictionaries')


@contextmanager
def captured_c_stderr_file():
    '''
    Handles flipping the stderr file descriptor to a temp file and back.
    This is the only way to capture stderr messages sent by Hunspell.

    Yields: path to the captured stderr file
    '''
    old_err = sys.stderr
    try:
        sys.stderr.flush()
        new_err = os.dup(sys.stderr.fileno()) # Clone the err file handler

        # Can't use tempdir context because os.dup2 needs a filename
        temp_dir = tempfile.mkdtemp()
        temp_name = os.path.join(temp_dir, 'errcap')
        with open(temp_name, 'a'):
            os.utime(temp_name, None)
        temp_file = os.open(temp_name, os.O_WRONLY)
        os.dup2(temp_file, 2)
        os.close(temp_file)
        sys.stderr = os.fdopen(new_err, 'w')
        yield temp_name
    finally:
        try:
            try:
                os.close(temp_file)
            except:
                pass
            shutil.rmtree(temp_dir) # Nuke temp content
        except:
            pass
        sys.stderr = old_err # Reset back
        os.dup2(sys.stderr.fileno(), 2)


@pytest.fixture
def hunspell():
    return Hunspell('test', hunspell_data_dir=DICT_DIR)


def test_create_destroy(hunspell):
    del hunspell


def test_missing_dict():
    with pytest.raises(HunspellFilePathError):
        Hunspell('not_avail', hunspell_data_dir=DICT_DIR)


def test_add_dic(hunspell):
    assert not hunspell.spell('AA')
    hunspell.add_dic(os.path.join(DICT_DIR, 'a.dic'))
    assert hunspell.spell('AA')


@patch('os.path.isfile', return_value=True)
@patch('os.access', return_value=True)
def test_bad_path_encoding(isfile_mock, access_mock):
    with pytest.raises(HunspellFilePathError):
        Hunspell('not_checked',
            hunspell_data_dir=u'bad/\udcc3/decoding')


@patch('hunspell.hunspell.WIN32_LONG_PATH_PREFIX', '/not/valid')
def test_windows_utf_8_encoding_applies_prefix():
    with captured_c_stderr_file() as caperr:
        with patch("os.name", 'nt'):
            # If python file existance checks used prefix, this would raise a HunspellFilePathError
            Hunspell('test', system_encoding='UTF-8')
        with open(caperr, 'r') as err:
            # But the Hunspell library lookup had the prefix applied
            assert re.search(r'error:[^\n]*/not/valid[^\n]*', err.read())


def test_spell(hunspell):
    assert not hunspell.spell('dpg')
    assert hunspell.spell('dog')


def test_spell_utf8(hunspell):
    assert hunspell.spell(u'café')
    assert not hunspell.spell(u'uncafé')


def test_spell_empty(hunspell):
    assert hunspell.spell('')


def test_suggest(hunspell):
    required = set(['dog', 'pg', 'deg', 'dig', 'dpt', 'dug', 'mpg', 'd pg'])
    suggest = hunspell.suggest('dpg')
    assert isinstance(suggest, tuple)
    assert required == set(suggest).intersection(required)


def test_suggest_utf8(hunspell):
    suggest = hunspell.suggest('cefé')
    assert isinstance(suggest, tuple)
    assert 'café' in suggest


def test_suggest_empty(hunspell):
    assert hunspell.suggest('') == ()


def test_suffix_suggest(hunspell):
    required = set(['doing', 'doth', 'doer', 'doings', 'doers', 'doest'])
    suffix_suggest = hunspell.suffix_suggest('do')
    assert isinstance(suffix_suggest, tuple)
    assert required == set(suffix_suggest).intersection(required)


def test_suffix_suggest_utf8(hunspell):
    suffix_suggest = hunspell.suffix_suggest('café')
    assert isinstance(suffix_suggest, tuple)
    assert set(['cafés', "café's"]) == set(suffix_suggest)


def test_suffix_suggest_empty(hunspell):
    assert hunspell.suffix_suggest('') == ()


def test_stem(hunspell):
    assert hunspell.stem('dog') == ('dog',)
    assert hunspell.stem('permanently') == ('permanent',)


def test_add(hunspell):
    word = 'outofvocabularyword'
    assert not hunspell.spell(word)
    hunspell.add(word)
    assert hunspell.spell(word)
    typo = word + 'd'
    assert word in hunspell.suggest(typo)


def test_bulk_suggest(hunspell):
    hunspell.set_concurrency(3)
    suggest = hunspell.bulk_suggest(['dog', 'dpg'])
    assert sorted(suggest.keys()) == ['dog', 'dpg']
    assert isinstance(suggest['dog'], tuple)
    assert ('dog',) == suggest['dog']

    required = set(['dog', 'pg', 'deg', 'dig', 'dpt', 'dug', 'mpg', 'd pg'])
    assert isinstance(suggest['dpg'], tuple)
    assert required == set(suggest['dpg']).intersection(required)

    checked = ['bjn', 'dog', 'dpg', 'dyg', 'foo', 'frg', 'opg', 'pgg', 'qre', 'twg']
    suggest = hunspell.bulk_suggest(checked)
    assert sorted(suggest.keys()) == checked


def test_bulk_stem(hunspell):
    hunspell.set_concurrency(3)
    assert hunspell.bulk_stem(['dog', 'permanently']) == {
        'permanently': ('permanent',),
        'dog': ('dog',)
    }
    assert hunspell.bulk_stem(['dog', 'twigs', 'permanently', 'unrecorded']) == {
        'unrecorded': ('recorded',),
        'permanently': ('permanent',),
        'twigs': ('twig',),
        'dog': ('dog',)
    }


def test_non_overlapping_caches(hunspell):
    test_suggest = hunspell.suggest('testing')
    test_suffix = hunspell.suffix_suggest('testing')
    test_stem = hunspell.stem('testing')

    hunspell._suggest_cache['made-up'] = test_suggest
    assert hunspell.suggest('made-up') == test_suggest
    hunspell._suffix_cache['made-up'] = test_suffix
    assert hunspell.suffix_suggest('made-up') == test_suffix
    hunspell._stem_cache['made-up'] = test_stem
    assert hunspell.stem('made-up') == test_stem

    h2 = Hunspell('en_US', hunspell_data_dir=DICT_DIR)
    assert h2.suggest('made-up') != test_suggest
    assert h2.stem('made-up') != test_stem


def test_overlapping_caches(hunspell):
    test_suggest = hunspell.suggest('testing')
    test_suffix = hunspell.suffix_suggest('testing')
    test_stem = hunspell.stem('testing')

    hunspell._suggest_cache['made-up'] = test_suggest
    assert hunspell.suggest('made-up') == test_suggest
    hunspell._suffix_cache['made-up'] = test_suffix
    assert hunspell.suffix_suggest('made-up') == test_suffix
    hunspell._stem_cache['made-up'] = test_stem
    assert hunspell.stem('made-up') == test_stem

    del hunspell
    hunspell = Hunspell('test', hunspell_data_dir=DICT_DIR)
    assert hunspell.suggest('made-up') == test_suggest
    assert hunspell.suffix_suggest('made-up') == test_suffix
    assert hunspell.stem('made-up') == test_stem


def test_save_caches_persistance(hunspell):
    temp_dir = tempfile.mkdtemp()
    try:
        h1 = Hunspell('test',
            hunspell_data_dir=DICT_DIR,
            disk_cache_dir=temp_dir,
            cache_manager='disk_hun')
        test_suggest = h1.suggest('testing')
        test_suffix = h1.suffix_suggest('testing')
        test_stem = h1.stem('testing')

        h1._suggest_cache['made-up'] = test_suggest
        assert h1.suggest('made-up') == test_suggest
        h1._suffix_cache['made-up'] = test_suffix
        assert h1.suffix_suggest('made-up') == test_suffix
        h1._stem_cache['made-up'] = test_stem
        assert h1.stem('made-up') == test_stem

        h1.save_cache()
        del h1

        cacheman = get_cache_manager('disk_hun')
        cacheman.deregister_all_caches()
        assert len(cacheman.cache_by_name) == 0

        h2 = Hunspell('test',
            hunspell_data_dir=DICT_DIR,
            disk_cache_dir=temp_dir,
            cache_manager='disk_hun')

        assert len(h2._suggest_cache) != 0
        assert len(h2._stem_cache) != 0
        assert h2.suggest('made-up') == test_suggest
        assert h2.suffix_suggest('made-up') == test_suffix
        assert h2.stem('made-up') == test_stem
    finally:
        shutil.rmtree(temp_dir) # Nuke temp content


def test_clear_caches_persistance(hunspell):
    temp_dir = tempfile.mkdtemp()
    try:
        h1 = Hunspell('test',
            hunspell_data_dir=DICT_DIR,
            disk_cache_dir=temp_dir,
            cache_manager='disk_hun')
        test_suggest = h1.suggest('testing')
        test_suffix = h1.suffix_suggest('testing')
        test_stem = h1.stem('testing')

        h1._suggest_cache['made-up'] = test_suggest
        assert h1.suggest('made-up') == test_suggest
        h1._suffix_cache['made-up'] = test_suffix
        assert h1.suffix_suggest('made-up') == test_suffix
        h1._stem_cache['made-up'] = test_stem
        assert h1.stem('made-up') == test_stem

        h1.save_cache()
        h1.clear_cache()
        del h1

        cacheman = get_cache_manager('disk_hun')
        cacheman.deregister_all_caches()
        assert len(cacheman.cache_by_name) == 0

        h2 = Hunspell('test',
            hunspell_data_dir=DICT_DIR,
            disk_cache_dir=temp_dir,
            cache_manager='disk_hun')

        assert len(h2._suggest_cache) == 0
        assert len(h2._stem_cache) == 0
        assert h2.suggest('made-up') != test_suggest
        assert h2.suffix_suggest('made-up') != test_suffix
        assert h2.stem('made-up') != test_stem
    finally:
        shutil.rmtree(temp_dir) # Nuke temp content


def test_clear_caches_non_peristance(hunspell):
    test_suggest = hunspell.suggest('testing')
    test_suffix = hunspell.suffix_suggest('testing')
    test_stem = hunspell.stem('testing')

    hunspell._suggest_cache['made-up'] = test_suggest
    assert hunspell.suggest('made-up') == test_suggest
    hunspell._suffix_cache['made-up'] = test_suffix
    assert hunspell.suffix_suggest('made-up') == test_suffix
    hunspell._stem_cache['made-up'] = test_stem
    assert hunspell.stem('made-up') == test_stem

    hunspell.clear_cache()

    del hunspell
    hunspell = Hunspell('test', hunspell_data_dir=DICT_DIR)
    assert hunspell.suggest('made-up') != test_suggest
    assert hunspell.suffix_suggest('made-up') != test_suffix
    assert hunspell.stem('made-up') != test_stem
