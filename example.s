!import "example_lib.s"

!import "../6502-stuff/example_lib.s" ; Only imported once.

!fn [-sva svx svy] delay_ms {
    tax
    !loop outer {
        ldy #20
        !loop inner {
            dey
            beq !break
        }
        dex
        beq !label(yolo)
    }
    !label yolo
}

!label yolo