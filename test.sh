#!/bin/bash

./preasm.py -x example.s && vasm6502_oldstyle -Fbin -dotdir example.out.s && echo ================= && hexdump -C a.out