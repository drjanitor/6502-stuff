#!/bin/bash

DASHES="\n==========================\n\n"
./preasm.py -x example.s && \
printf $DASHES && \
cat example.out.s && \
printf $DASHES && \
vasm6502_oldstyle -Fbin -dotdir -c02 example.out.s && \
printf $DASHES && \
hexdump -C a.out && \
rm example.out.s a.out