;---- Begin import: example_lib.s
bar:
    pha
.bar_baz__loop_begin:
        lda #20
        jmp .bar_baz__loop_begin
.bar_baz__loop_end:
.bar_bar__loop_begin:
        jmp .bar_bar__loop_end
        lda #40
        jmp .bar_bar__loop_begin
.bar_bar__loop_end:
.bar__cookie:
    bne .bar__cookie
.bar__return:
    pla
    rts
;---- End import: example_lib.s

;---- Skipping: example_lib.s
; Only imported once.

delay_ms:
    tax
.delay_ms_outer__loop_begin:
        ldy #20
.delay_ms_outer_inner__loop_begin:
            dey
            beq .delay_ms_outer_inner__loop_end
            jmp .delay_ms_outer_inner__loop_begin
.delay_ms_outer_inner__loop_end:
        dex
        beq .delay_ms_outer__loop_end
        jmp .delay_ms_outer__loop_begin
.delay_ms_outer__loop_end:
.delay_ms__return:
    rts
