#!/usr/bin/env python3

import codecs
import sys


class HtmlLiText:
    class LiState:
        def __init__(self):
            self.lbuf = ''
            self.lic = False

    def __init__(self):
        pass

    def __call__(self, fname, *args, **kwargs):
        state = self.LiState()
        with codecs.open(fname, 'r', encoding='utf-8') as fd:
            for line in fd:
                line = line.strip()
                if not line:
                    continue
                if line.find('<li>') >= 0:
                    if line.find('</li>') >= 0:
                        if state.lic:
                            state.lbuf += line
                            print('1]',state.lbuf)
                        else:
                            print('2]',line)
                        state.lic = False
                        state.lbuf = ''
                        continue
                    state.lbuf += line
                    state.lic = True
                    continue
                if line.find('</li>') >= 0:
                    if state.lic:
                        state.lbuf += line
                        print('3]',state.lbuf)
                    else:
                        print('4]',line)
                    state.lic = False
                    state.lbuf = ''


litext = HtmlLiText()
litext(sys.argv[1])
