.setcpu "6502"

.include "nes.inc"
.include "song.inc"

.export channels_reset
.export channels_rewind
.export channels_advance
.export channels_write

.import song_data

SHADOW_UNWRITTEN = $FF
ABSENT_PAGE      = $00
LOWEST_PITCH_INDEX = $00

.segment "ZEROPAGE"

pointer:                .res 2
entry:                  .res 2
opcode:                 .res 1
phrase_table:           .res 2
timer_low_table:        .res 2
timer_high_table:       .res 2
bend:                   .res 1
bend_sign:              .res 1
triangle_pitch:         .res 1
plane_state:            .res PLANE_STATE_BYTES
timer_high_shadows:     .res TRIANGLE_REGISTERS + 1

.segment "CODE"

.assert OPCODE_SIZE = 1, error, "a token's operands follow its opcode by one byte"
.assert PHRASE_TABLE_ENTRY_SIZE = 2, error, "a table entry is reached by one doubling"
.assert PHRASE_LENGTH_SIZE = 1, error, "a phrase body follows its length by one byte"
.assert DEFAULT_COUNT_FLAG = PHRASE_ID_MASK + 1, error, "the count flag stands above every id an opcode names"
.assert >song_data <> ABSENT_PAGE, lderror, "a song loaded in page zero reads as an absent plane"
.assert ABSENT_STREAM = $FFFF, error, "an absent stream is told apart by both its bytes reading $FF"
.assert BEND_FLAG = $80, error, "a value's flag is read as the sign bit"
.assert PITCH_COUNT <= BEND_FLAG, error, "every pitch index fits below the flag"
.assert SILENT_PITCH_INDEX >= PITCH_COUNT, error, "the index standing for silence sounds no pitch"
.assert SILENT_PITCH_INDEX < BEND_FLAG, error, "the index standing for silence bends nowhere"
.assert COUNT_STEP = 1 << COUNT_SHIFT, error, "a repeat count steps from the bit it is shifted down by"
.assert PLANE_STATE_BYTES + PLANE_PHRASE < $100, error, "a plane's phrase pointer is reached in page zero"

; Readies the tables the planes read through and points every plane at its own first token.
channels_reset:
    lda #LOWEST_PITCH_INDEX
    sta triangle_pitch

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
; A plane the block leaves out states ABSENT_STREAM, and its source lands in page zero, which no
; song occupies: that page is what marks it absent, and its value stays at zero throughout.
seed_planes:
    ldx #$00
    ldy #$00
@next:
    lda (pointer),y
    iny
    and (pointer),y
    cmp #<ABSENT_STREAM
    bne @present
    lda #ABSENT_PAGE
    sta plane_state + PLANE_SOURCE + 1,x
    iny
    jmp @empty
@present:
    dey
    clc
    lda (pointer),y
    adc #<song_data
    sta plane_state + PLANE_SOURCE,x
    iny
    lda (pointer),y
    adc #>song_data
    sta plane_state + PLANE_SOURCE + 1,x
    iny

@empty:
    lda #$00
    sta plane_state + PLANE_PHRASE_TICKS,x
    sta plane_state + PLANE_TOKEN_TICKS,x
    sta plane_state + PLANE_VALUE,x
    sta plane_state + PLANE_SHIFT,x
    sta plane_state + PLANE_REPEATS,x

    txa
    clc
    adc #PLANE_STATE_SIZE
    tax
    cpx #PLANE_STATE_BYTES
    bne @next

; States what each plane's byte holds: the bits its register leaves for a repeat count, and for
; the triangle the index its value plane stands at while the channel rests. Every other plane
; keeps the zero it was seeded with, which is what makes one symbol cover one tick.
plane_forms:
    lda #(PULSE_CONTROL_MASK ^ $FF)
    sta plane_state + PULSE1_CONTROL_PLANE + PLANE_COUNT_MASK
    sta plane_state + PULSE2_CONTROL_PLANE + PLANE_COUNT_MASK
    lda #(NOISE_CONTROL_MASK ^ $FF)
    sta plane_state + NOISE_CONTROL_PLANE + PLANE_COUNT_MASK
    lda #(NOISE_VALUE_MASK ^ $FF)
    sta plane_state + NOISE_VALUE_PLANE + PLANE_COUNT_MASK
    lda #SILENT_PITCH_INDEX
    sta plane_state + TRIANGLE_VALUE_PLANE + PLANE_VALUE
    rts

; Advances every plane the block holds by one tick of the song. A bend plane advances only on a
; tick its channel's new value flags, since it holds a value for those ticks alone.
channels_advance:
    ldx #PULSE1_CONTROL_PLANE
    jsr plane_step
    ldx #PULSE1_VALUE_PLANE
    jsr plane_step
    bit plane_state + PULSE1_VALUE_PLANE + PLANE_VALUE
    bpl @pulse2
    ldx #PULSE1_BEND_PLANE
    jsr plane_step
@pulse2:
    ldx #PULSE2_CONTROL_PLANE
    jsr plane_step
    ldx #PULSE2_VALUE_PLANE
    jsr plane_step
    bit plane_state + PULSE2_VALUE_PLANE + PLANE_VALUE
    bpl @triangle
    ldx #PULSE2_BEND_PLANE
    jsr plane_step
@triangle:
    ldx #TRIANGLE_VALUE_PLANE
    jsr plane_step
    bit plane_state + TRIANGLE_VALUE_PLANE + PLANE_VALUE
    bpl @noise
    ldx #TRIANGLE_BEND_PLANE
    jsr plane_step
@noise:
    ldx #NOISE_CONTROL_PLANE
    jsr plane_step
    ldx #NOISE_VALUE_PLANE
    jmp plane_step

; Advances the plane at X by one tick where the block holds it, an absent plane standing still.
plane_step:
    lda plane_state + PLANE_SOURCE + 1,x
    beq @absent
    jmp plane_advance
@absent:
    rts

; Advances the plane whose state lies at X by one tick, leaving the value it plays in that state.
; A token states the ticks it covers beyond the one it is fetched for, so a plane reaches for the
; next token the moment the one it stands on has none left.
;
; The values a tick plays come from wherever the token put them: a phrase body, the bytes spelled
; out behind a literal, or the value the plane already reached. A body played out holds its last
; value onward, which is what carries a note whose envelope has finished.
plane_advance:
    lda plane_state + PLANE_REPEATS,x
    beq @symbol
    dec plane_state + PLANE_REPEATS,x
    rts
@symbol:
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
    lda plane_state + PLANE_VALUE,x
    and plane_state + PLANE_COUNT_MASK,x
    lsr
    lsr
    lsr
    lsr
    sta plane_state + PLANE_REPEATS,x
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
    and #PHRASE_ID_MASK
    cmp #PHRASE_ID_ESCAPE
    bne @named
    lda (pointer),y
    iny
@named:
    jsr set_phrase
    lda opcode
    and #DEFAULT_COUNT_FLAG
    bne @shifts
    lda (pointer),y
    iny
    sta plane_state + PLANE_TOKEN_TICKS,x
@shifts:
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
    iny
    lda (entry),y
    sta plane_state + PLANE_TOKEN_TICKS,x

    clc
    lda plane_state + PLANE_PHRASE,x
    adc #(PHRASE_LENGTH_SIZE + PHRASE_DEFAULT_SIZE)
    sta plane_state + PLANE_PHRASE,x
    bcc @body
    inc plane_state + PLANE_PHRASE + 1,x
@body:
    pla
    tay
    rts

; Writes what every plane last played to the registers its channel owns. The triangle names its
; silence in the pitch its value plane carries: the index standing above every pitch the table
; holds silences the linear counter and leaves the divider where the channel last sounded.
channels_write:
    lda plane_state + PULSE1_CONTROL_PLANE + PLANE_VALUE
    and #PULSE_CONTROL_MASK
    ora #PULSE_CONTROL_FIXED
    sta CHANNEL_CONTROL + PULSE1_REGISTERS
    lda plane_state + PULSE1_BEND_PLANE + PLANE_VALUE
    sta bend
    ldx #PULSE1_REGISTERS
    lda plane_state + PULSE1_VALUE_PLANE + PLANE_VALUE
    jsr write_timer

    lda plane_state + PULSE2_CONTROL_PLANE + PLANE_VALUE
    and #PULSE_CONTROL_MASK
    ora #PULSE_CONTROL_FIXED
    sta CHANNEL_CONTROL + PULSE2_REGISTERS
    lda plane_state + PULSE2_BEND_PLANE + PLANE_VALUE
    sta bend
    ldx #PULSE2_REGISTERS
    lda plane_state + PULSE2_VALUE_PLANE + PLANE_VALUE
    jsr write_timer

    lda plane_state + TRIANGLE_VALUE_PLANE + PLANE_VALUE
    cmp #SILENT_PITCH_INDEX
    beq @resting
    sta triangle_pitch
    lda #TRIANGLE_COUNTER | TRIANGLE_SOUNDING
    bne @counter
@resting:
    lda #TRIANGLE_COUNTER | TRIANGLE_SILENT
@counter:
    sta CHANNEL_CONTROL + TRIANGLE_REGISTERS
    lda plane_state + TRIANGLE_BEND_PLANE + PLANE_VALUE
    sta bend
    ldx #TRIANGLE_REGISTERS
    lda triangle_pitch
    jsr write_timer

    lda plane_state + NOISE_CONTROL_PLANE + PLANE_VALUE
    and #NOISE_CONTROL_MASK
    ora #NOISE_CONTROL_FIXED
    sta CHANNEL_CONTROL + NOISE_REGISTERS
    lda plane_state + NOISE_VALUE_PLANE + PLANE_VALUE
    and #NOISE_VALUE_MASK
    ora #NOISE_VALUE_FIXED
    sta CHANNEL_TIMER_LOW + NOISE_REGISTERS
    rts

; Writes the timer the value byte in A names to the channel whose register base lies in X, the
; byte loaded last so its sign stands in N. The low seven bits index the pitch table, and the top
; bit says the tick carries the bend standing in `bend`; an unflagged tick sounds its pitch's own
; divider. The bend states divider steps in two's complement, so it reaches the timer's high half
; as $00 or $FF beside the carry the low half raised. A high half reaches the register only where
; it differs from the last one written, since storing it restarts a pulse waveform and reloads
; the triangle's counter.
write_timer:
    bmi @bent
    ldy #$00
    sty bend
    tay
    jmp @indexed
@bent:
    and #PITCH_INDEX_MASK
    tay
@indexed:
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
