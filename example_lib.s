fn bar {
    loop baz {
        lda #20
    }
    skip bar {
        lda #40
    }
    label cookie
    bne label(cookie)
}
