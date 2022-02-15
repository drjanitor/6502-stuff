#!/usr/bin/env python3

import sys
import re
import argparse
import pathlib
from enum import Enum


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('infile')
    parser.add_argument('-o', '--outfile')
    parser.add_argument('-x', '--exclam', action=argparse.BooleanOptionalAction)
    return parser.parse_args(argv[1:])


def main(argv):
    args = parse_args(argv)
    infile = pathlib.Path(args.infile).resolve()
    outfile = args.outfile or infile.with_suffix('.out.s')
    processed = process(infile, outfile, make_patterns(args.exclam))
    with open(outfile, 'w') as f:
        f.write(processed)


def process(infile, outfile, patterns):
    processor = Processor(indent='    ', patterns=patterns)
    processor.process_file(infile)
    return '\n'.join(processor.out) + '\n'


LEADING_WS = r'(?P<leading>\s*)'
TRAILING_WS = r'(?P<trailing>\s*([;].*)?)'


def make_patterns(with_exclam):
    def make_re(s):
        s = s.replace('EXCLAM ', '!' if with_exclam else '')
        return re.compile(LEADING_WS + s + TRAILING_WS, re.X | re.I)

    JUMP_INSTR = r'((?P<jump_instr> [a-z]{3}) \s+)'
    
    class Patterns:
        IMPORT = make_re(r' EXCLAM import \s+ "(?P<path>.+)" ')
        FUNCTION = make_re(r' EXCLAM fn (\s* \[ (?P<flags>[ a-z_-]+) \] )? \s+ (?P<name>[a-z_]+) \s* \{')
        MAKE_LABEL = make_re(r' EXCLAM label \s+ (?P<name>[a-z_]+) ')
        JUMP_LABEL = make_re(JUMP_INSTR + r' EXCLAM label \s+ (?P<name>[a-z_]+)')
        LOOP = make_re(r' EXCLAM (loop|(?P<skip>skip)) \s+ (?P<name>[a-z_]+) \s* \{ ')
        END = make_re(r' \} ')
        RETURN = make_re(JUMP_INSTR + r'? EXCLAM return (\s+ (?P<value>[^;]+) )')
        NEXT = make_re(JUMP_INSTR + r'? EXCLAM next (\s+ (?P<name>[a-z_]+) )? ')
        BREAK = make_re(JUMP_INSTR + r'? EXCLAM break (\s+ (?P<name>[a-z_]+) )? ')

    return Patterns


class FunctionFlag(Enum):
    SAVE_A = 'sva'
    SAVE_X = 'svx'
    SAVE_Y = 'svy'


class LoopFlag(Enum):
    SKIP = 'skip'


class CompilationError(Exception):
    def __init__(self, file, line, msg):
        self.file = file
        self.line = line
        self.msg = msg
        super().__init__("{0}\nline {1}: {2}".format(file, line, msg))


class Processor:

    def __init__(self, indent, patterns):
        self.indent = indent
        self.files = set()
        self.current_file = None
        self.current_line = -1
        self.out = []
        self.context = []
        self.imported_files = set()
        self.patterns = patterns

    def process_file(self, path):
        if path in self.imported_files:
            self.out.append(';---- Skipping: %s' % path.name)
            return
        first_file = len(self.imported_files) == 0
        self.imported_files.add(path)
        if not first_file:
            self.out.append(';---- Begin import: ' + str(path.name))
        with open(path, 'r') as f:
            for (lineno, line) in enumerate(f):
                self.current_file = path
                self.current_line = lineno + 1
                self.out.extend(self.process_line(line))
        if len(self.context) > 0:
            raise self.error(
                'File ends with unclosed contexts:\n' + '\n'.join(
                    '%s %s' % c for c in self.context))
        if not first_file:
            self.out.append(';---- End import: ' + str(path.name))
        
    def process_line(self, line):
        line = line.rstrip('\n')
        p = self.patterns
        return self.handle_cases(line, [
            (p.IMPORT, self.handle_import),
            (p.FUNCTION, self.handle_function),
            (p.LOOP, self.handle_loop),
            (p.END, self.handle_end),
            (p.RETURN, self.handle_return),
            (p.NEXT, self.handle_next),
            (p.BREAK, self.handle_break),
            (p.MAKE_LABEL, self.handle_label),
            (p.JUMP_LABEL, self.handle_label),
        ])

    def handle_cases(self, line, cases):
        for (r, f) in cases:
            m = r.match(line)
            if m:
                g = m.groupdict()
                leading = g.pop('leading')
                trailing = g.pop('trailing')
                out = f(**g)
                if isinstance(out, str):
                    out = [out]
                out = [o for o in out if o is not None]
                out = [
                    o.replace('\t ', self.indent, 1)
                    for o in out
                ]
                out = [
                    o[3:] if o.startswith('<< ')
                    else leading + o
                    for o in out
                ]
                if len(out) > 0:
                    out[0] = out[0] + trailing
                elif trailing:
                    out.append(leading + trailing.lstrip())
                return out
        return [line]

    def error(self, msg):
        return CompilationError(self.current_file, self.current_line, msg)

    @property
    def current_loop_label(self):
        return Processor.make_loop_label(self.context)

    @staticmethod
    def make_loop_label(context):
        return '.' + '_'.join(cname for ctype, cname, cflags in context)

    def handle_function(self, name, flags):
        if len(self.context) > 0:
            raise self.error('Functions can only be defined at the top level.')
    
        cflags = set()
        if flags:
            for f in flags.split(' '):
                try:
                    cflags.add(FunctionFlag(f))
                except ValueError:
                    raise self.error('Unknown function flag: %s' % f)
        
        self.context.append(('function', name, cflags))
        return [
            Processor.define_label(name),
            '\t pha' if FunctionFlag.SAVE_A in cflags else None,
            '\t phx' if FunctionFlag.SAVE_X in cflags else None,
            '\t phy' if FunctionFlag.SAVE_Y in cflags else None,
        ]

    def handle_loop(self, name, skip):
        cflags = set()
        if skip:
            cflags.add(LoopFlag.SKIP)
        self.context.append(('loop', name, cflags))
        label = self.current_loop_label
        return [
            Processor.define_label(label + '__loop_begin'),
            ('\t jmp ' + label + '__loop_end' if skip else None)
        ]

    def handle_end(self):
        if len(self.context) == 0:
            raise self.error('Cannot call end outside of function or loop.')
        label = self.current_loop_label
        ctype, cname, cflags = self.context.pop()
        if ctype == 'loop':
            return [
                '\t jmp ' + label + '__loop_begin',
                Processor.define_label(label + '__loop_end'),
            ]
        elif ctype == 'function':
            return [
                Processor.define_label('.' + cname + '__return'),
                '\t ply' if FunctionFlag.SAVE_Y in cflags else None,
                '\t plx' if FunctionFlag.SAVE_X in cflags else None,
                '\t pla' if FunctionFlag.SAVE_A in cflags else None,
                '\t rts',
            ]

    def handle_label(self, name, jump_instr=None):
        prefix = ''
        if len(self.context) > 0 and self.context[0][0] == 'function':
            prefix = '.' + self.context[0][1] + '__'
        label = prefix + name
        if jump_instr:
            return [jump_instr + ' ' + label]
        else:
            return [Processor.define_label(label)]

    def handle_return(self, jump_instr):
        if len(self.context) == 0  or self.context[0][0] != 'function':
            raise self.error('Cannot call return outside of a function.')
        return (jump_instr or 'jmp') + ' .' + self.context[0][1] + '__return'

    def handle_break(self, name, jump_instr):
        return self.handle_loop_jump('break', jump_instr, name, '__loop_end')

    def handle_next(self, name, jump_instr):
        return self.handle_loop_jump('next', jump_instr, name, '__loop_begin')

    def handle_loop_jump(self, type, jump_instr, name, label_suffix):
        if len(self.context) == 0 or self.context[-1][0] != 'loop':
            raise self.error('Cannot call %s outside of a loop.' % type)
        if name == None:
            return [(jump_instr or 'jmp') + ' ' + self.current_loop_label + label_suffix]
        partial_context = []
        found = False
        for ctype, cname, cflags in self.context:
            partial_context.append((ctype, cname, cflags))
            if ctype == 'loop' and cname == name:
                found = True
                break
        if not found:
            raise self.error('Cannot find loop label %s' % name)
        return [(jump_instr or 'jmp') + ' ' + Processor.make_loop_label(partial_context) + label_suffix]


    def handle_import(self, path):
        if len(self.context) > 0:
            raise self.error('Imports can only happen at the top level.')
        p = self.current_file.parent / path
        self.process_file(p.resolve())
        return []

    @staticmethod
    def define_label(name):
        return '<< ' + name + ':'


if __name__ == '__main__':
    main(sys.argv)