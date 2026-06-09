#!/usr/bin/env python3
"""Regenerate dictionaries/freq_uk_clean.txt from the raw OpenSubtitles list.

The raw freq_uk.txt is ~25% Russian («что», «как», «нет»…) plus Latin junk.
Keep only words that Ukrainian morphology (pymorphy2-dicts-uk) recognises.

Usage:  python tools/clean_freq_uk.py
"""
import inspect
import os
import re
import sys

if not hasattr(inspect, 'getargspec'):
    def _getargspec(func):
        spec = inspect.getfullargspec(func)
        return (spec.args, spec.varargs, spec.varkw, spec.defaults)
    inspect.getargspec = _getargspec

import pymorphy2

HERE = os.path.dirname(os.path.abspath(__file__))
DICT_DIR = os.path.join(HERE, '..', 'layout_switcher', 'dictionaries')

# Ukrainian alphabet (incl. apostrophe for words like комп'ютер)
_UK_WORD = re.compile(r"^[а-щьюяіїєґА-ЩЬЮЯІЇЄҐ']+$")
# Letters that exist in Russian but not Ukrainian — hard rejects
_RU_ONLY = set('ыэъёЫЭЪЁ')


def main():
    morph = pymorphy2.MorphAnalyzer(lang='uk')
    src = os.path.join(DICT_DIR, 'freq_uk.txt')
    dst = os.path.join(DICT_DIR, 'freq_uk_clean.txt')

    kept = dropped = 0
    with open(src, encoding='utf-8') as fin, \
         open(dst, 'w', encoding='utf-8') as fout:
        for line in fin:
            parts = line.split()
            if len(parts) < 2:
                continue
            word, count = parts[0], parts[1]
            if (not _UK_WORD.match(word)
                    or set(word) & _RU_ONLY
                    or len(word) < 2 and word not in ('а', 'б', 'в', 'е',
                                                      'є', 'ж', 'з', 'і',
                                                      'й', 'о', 'у', 'я')
                    or not morph.word_is_known(word)):
                dropped += 1
                continue
            fout.write(f"{word} {count}\n")
            kept += 1
    print(f"kept {kept}, dropped {dropped} -> {dst}")


if __name__ == '__main__':
    main()
