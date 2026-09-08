.setcpu "6502"

.include "nes.inc"
.include "song.inc"

.export channels_reset
.export channels_rewind
.export channels_advance
.export channels_write

.import song_data

SHADOW_UNWRITTEN = $FF

.segment "ZEROPAGE"

pointer:                .res 2
entry:                  .res 2
opcode:                 .res 1
phrase_table:           .res 2
timer_low_table:        .res 2
timer_high_table:       .res 2
bend:                   .res 1
bend_sign:              .res 1
plane_state:            .res PLANE_STATE_BYTES
timer_high_shadows:     .res TRIANGLE_REGISTERS + 1

.segment "CODE"

.assert OPCODE_SIZE = 1, error, "a token's operands follow its opcode by one byte"
.assert PHRASE_TABLE_ENTRY_SIZE = 2, error, "a table entry is reached by one doubling"
.assert PHRASE_LENGTH_SIZE = 1, error, "a phrase body follows its length by one byte"

; Readies the tables the planes read through and points every plane at its own first token.
channels_reset:
    lda #SHADOW_UNWRITTEN
    sta timer_high_shadows + PULSE1_REGISTERS
    sta timer_high_shadows + PULSE2_REGISTERS
    sta timer_high_shadows + TRIANGLE_REGISTERS

    clc
    lda song_data + TIMER_TABLE_OFFSET
    adc #<song_data
    sta timer_low_table
    lda song_data + TIMER_TABLE_OFFSET + 1
    adc #>song_data
    sta timer_low_table + 1

    clc
    lda timer_low_table
    adc #PITCH_COUNT
    sta timer_high_table
    lda timer_low_table + 1
    adc #$00
    sta timer_high_table + 1

    clc
    lda song_data + PHRASE_TABLE_OFFSET
    adc #<(song_data + PHRASE_TABLE_COUNT_SIZE)
    sta phrase_table
    lda song_data + PHRASE_TABLE_OFFSET + 1
    adc #>(song_data + PHRASE_TABLE_COUNT_SIZE)
    sta phrase_table + 1

    lda #<(song_data + STREAM_OFFSETS_OFFSET)
    sta pointer
    lda #>(song_data + STREAM_OFFSETS_OFFSET)
    sta pointer + 1
    jmp seed_planes

; Brings every plane back to the token its stream is re-entered at, which is the whole of what a
; song coming round restores: the token the loop tick starts is one the plane reads outright.
channels_rewind:
    lda #<(song_data + LOOP_ENTRIES_OFFSET)
    sta pointer
    lda #>(song_data + LOOP_ENTRIES_OFFSET)
    sta pointer + 1
    jmp seed_planes

; Points each plane at the offset the header holds for it at (pointer), and empties what it plays.
seed_planes:
    ldx #$00
    ldy #$00
@next:
    clc
    lda (pointer),y
    adc #<song_data
    sta plane_state + PLANE_SOURCE,x
    iny
    lda (pointer),y
    adc #>song_data
    sta plane_state + PLANE_SOURCE + 1,x
    iny

    lda #$00
    sta plane_state + PLANE_PHRASE_TICKS,x
    sta plane_state + PLANE_TOKEN_TICKS,x
    sta plane_state + PLANE_VALUE,x
    sta plane_state + PLANE_SHIFT,x

    txa
    clc
    adc #PLANE_STATE_SIZE
    tax
    cpx #PLANE_STATE_BYTES
    bne @next
    rts

; Advances every plane by one tick of the song.
channels_advance:
    ldx #$00
@next:
    jsr plane_advance
    txa
    clc
    adc #PLANE_STATE_SIZE
    tax
    cpx #PLANE_STATE_BYTES
    bne @next
    rts

; Advances the plane whose state lies at X by one tick, leaving the value it plays in that state.
; A token states the ticks it covers beyond the one it is fetched for, so a plane reaches for the
; next token the moment the one it stands on has none left.
;
; The values a tick plays come from wherever the token put them: a phrase body, the bytes spelled
; out behind a literal, or the value the plane already reached. A body played out holds its last
; value onward, which is what carries a note whose envelope has finished.
plane_advance:
    lda plane_state + PLANE_TOKEN_TICKS,x
    bne @within
    jsr fetch_token
    jmp @plays
@within:
    dec plane_state + PLANE_TOKEN_TICKS,x
@plays:
    lda plane_state + PLANE_PHRASE_TICKS,x
    beq @held
    lda (plane_state + PLANE_PHRASE,x)
    clc
    adc plane_state + PLANE_SHIFT,x
    sta plane_state + PLANE_VALUE,x
    dec plane_state + PLANE_PHRASE_TICKS,x
    beq @held
    inc plane_state + PLANE_PHRASE,x
    bne @held
    inc plane_state + PLANE_PHRASE + 1,x
@held:
    rts

; Reads the token the plane at X stands on into that plane's own state.
fetch_token:
    lda plane_state + PLANE_SOURCE,x
    sta pointer
    lda plane_state + PLANE_SOURCE + 1,x
    sta pointer + 1

    ldy #$00
    lda (pointer),y
    sta opcode
    iny

    and #TOKEN_TAG_MASK
    beq @holds
    cmp #TAG_LITERAL
    beq @spells
    jmp @plays_phrase

@holds:
    lda opcode
    and #TOKEN_OPERAND_MASK
    sta plane_state + PLANE_TOKEN_TICKS,x
    lda #$00
    sta plane_state + PLANE_PHRASE_TICKS,x
    jmp advance_source

@spells:
    lda opcode
    and #TOKEN_OPERAND_MASK
    sta plane_state + PLANE_TOKEN_TICKS,x
    clc
    adc #$01
    sta plane_state + PLANE_PHRASE_TICKS,x

    lda #$00
    sta plane_state + PLANE_SHIFT,x

    clc
    lda pointer
    adc #OPCODE_SIZE
    sta plane_state + PLANE_PHRASE,x
    lda pointer + 1
    adc #$00
    sta plane_state + PLANE_PHRASE + 1,x

    clc
    tya
    adc plane_state + PLANE_PHRASE_TICKS,x
    tay
    jmp advance_source

@plays_phrase:
    lda opcode
    and #TOKEN_OPERAND_MASK
    cmp #PHRASE_ID_ESCAPE
    bne @named
    lda (pointer),y
    iny
@named:
    jsr set_phrase
    lda (pointer),y
    iny
    sta plane_state + PLANE_TOKEN_TICKS,x
    lda #$00
    sta plane_state + PLANE_SHIFT,x
    bit opcode
    bvc advance_source
    lda (pointer),y
    iny
    sta plane_state + PLANE_SHIFT,x

; Moves the plane's source on by the Y bytes its token took.
advance_source:
    clc
    tya
    adc plane_state + PLANE_SOURCE,x
    sta plane_state + PLANE_SOURCE,x
    bcc @done
    inc plane_state + PLANE_SOURCE + 1,x
@done:
    rts

; Points the plane at X at the body of the phrase whose id lies in A, and states how many of that
; body's own values are left to play.
set_phrase:
    asl
    sta entry
    lda #$00
    rol
    sta entry + 1

    clc
    lda entry
    adc phrase_table
    sta entry
    lda entry + 1
    adc phrase_table + 1
    sta entry + 1

    tya
    pha
    ldy #$00
    clc
    lda (entry),y
    adc #<song_data
    sta plane_state + PLANE_PHRASE,x
    iny
    lda (entry),y
    adc #>song_data
    sta plane_state + PLANE_PHRASE + 1,x

    lda plane_state + PLANE_PHRASE,x
    sta entry
    lda plane_state + PLANE_PHRASE + 1,x
    sta entry + 1
    ldy #$00
    lda (entry),y
    sta plane_state + PLANE_PHRASE_TICKS,x

    inc plane_state + PLANE_PHRASE,x
    bne @body
    inc plane_state + PLANE_PHRASE + 1,x
@body:
    pla
    tay
    rts

; Writes what every plane last played to the registers its channel owns.
channels_write:
    lda plane_state + PULSE1_CONTROL_PLANE + PLANE_VALUE
    sta CHANNEL_CONTROL + PULSE1_REGISTERS
    ldx #PULSE1_REGISTERS
    ldy plane_state + PULSE1_VALUE_PLANE + PLANE_VALUE
    lda plane_state + PULSE1_BEND_PLANE + PLANE_VALUE
    jsr write_timer

    lda plane_state + PULSE2_CONTROL_PLANE + PLANE_VALUE
    sta CHANNEL_CONTROL + PULSE2_REGISTERS
    ldx #PULSE2_REGISTERS
    ldy plane_state + PULSE2_VALUE_PLANE + PLANE_VALUE
    lda plane_state + PULSE2_BEND_PLANE + PLANE_VALUE
    jsr write_timer

    lda plane_state + TRIANGLE_CONTROL_PLANE + PLANE_VALUE
    sta CHANNEL_CONTROL + TRIANGLE_REGISTERS
    ldx #TRIANGLE_REGISTERS
    ldy plane_state + TRIANGLE_VALUE_PLANE + PLANE_VALUE
    lda plane_state + TRIANGLE_BEND_PLANE + PLANE_VALUE
    jsr write_timer

    lda plane_state + NOISE_CONTROL_PLANE + PLANE_VALUE
    sta CHANNEL_CONTROL + NOISE_REGISTERS
    lda plane_state + NOISE_VALUE_PLANE + PLANE_VALUE
    sta CHANNEL_TIMER_LOW + NOISE_REGISTERS
    rts

; Writes the timer the pitch at Y sounds at, moved by the bend in A, to the channel whose
; register base lies in X. The bend states divider steps in two's complement, so it reaches the
; timer's high half as $00 or $FF beside the carry the low half raised. A high half reaches the
; register only where it differs from the last one written, since storing it restarts a pulse
; waveform and reloads the triangle's counter.
write_timer:
    sta bend
    lda #$00
    bit bend
    bpl @extended
    lda #$FF
@extended:
    sta bend_sign

    lda (timer_low_table),y
    clc
    adc bend
    sta CHANNEL_TIMER_LOW,x
    lda (timer_high_table),y
    adc bend_sign
    cmp timer_high_shadows,x
    beq @held
    sta timer_high_shadows,x
    sta CHANNEL_TIMER_HIGH,x
@held:
    rts
