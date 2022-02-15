!import "example_lib.s"

!import "../6502-stuff/example_lib.s" ; Only imported once.

!fn [-svy] delay_ms {
    !loop outer {
        ldx #20
        stz $FF
        !loop inner {
            dex
            beq !break
        }
        dea
        bra !label yolo
    }
    !label yolo
}

!label yolo