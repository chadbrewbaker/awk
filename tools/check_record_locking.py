#!/usr/bin/env python3
"""Compare an unmodified awk executable with a candidate on record-reading cases.

Usage: python3 tools/check_record_locking.py /path/to/baseline ./a.out
"""
import argparse
import itertools
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('candidate', type=Path)
    args = parser.parse_args()
    binaries = [str(args.baseline.resolve()), str(args.candidate.resolve())]
    cases = []
    programs = [
        '{print NR,NF,$2}',
        '{print NF; $0="a b c"; print NF,$2}',
        '{print NF; $2="changed"; print NF,$0}',
        '{print NF; NF=2; print NF,$0}',
        '{if (NR%2) FS=","; else FS=" "; print NF,$1,$2}',
        'BEGIN {FS=","} {print NF,$1,$2}',
        '{if (NR%2) next; print NF,$2}',
        '{print NF; NF=0; print NF,$0}',
        'END {print NR,NF,$0}',
    ]
    inputs = [b'a b c\nx\n\ny z', b'a,b,,c\n,,\nlast,\n',
              b'\t one  two\tthree\n\nlast\n',
              b' '.join([b'field'] * 4096) + b'\nx\n\ny z\n']
    cases.extend(([program], data) for program, data in itertools.product(programs, inputs))
    for data, rs in itertools.product(
        [b'\n\na b\nc d\n\ne f', b'a:b::c:', b'a\0b\nc\n', b'x' * 200000 + b'\nlast'],
        ['\\n', ':', '', 'ab+'],
    ):
        cases.append((['BEGIN {RS="' + rs + '"} {print NR,NF,length($0),$0}'], data))
    for data in [b'a,b\n1,2\n', b'"a\nb",c\nlast,x', b'"a""b",c\r\n', b'']:
        cases.append((['--csv', '{print NR,NF,$1,$2}'], data))
    for index, (flags, data) in enumerate(cases):
        outputs = []
        for binary in binaries:
            result = subprocess.run([binary, *flags], input=data, capture_output=True,
                                    env=dict(os.environ, LC_ALL='C'), timeout=10)
            if result.returncode != 0:
                raise RuntimeError(f'case {index}, {binary}: {result.stderr!r}')
            outputs.append((result.stdout, result.stderr))
        if outputs[0] != outputs[1]:
            raise AssertionError(f'case {index}: outputs differ; arguments={flags!r}')
    print(f'{len(cases)} record-reading differential cases passed')


if __name__ == '__main__':
    main()
