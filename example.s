import "example_lib.s"

import "example_lib.s" ; Only imported once.

fn [nopush] delay_ms {
    tax
    loop outer {
        ldy #20
        loop inner {
            dey
            beq break
        }
        dex
        beq break
    }
}