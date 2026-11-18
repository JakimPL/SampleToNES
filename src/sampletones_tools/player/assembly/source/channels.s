.setcpu "6502"

.include "nes.inc"
.include "song.inc"

.export channels_reset
.export channels_rewind
.export channels_advance
.export channels_write
.exportzp plane_state

.import song_data

SHADOW_UNWRITTEN = $FF
ABSENT_PAGE      = $00
PULSE1_BEND_BIT  = 1 << (PULSE1_BEND_PLANE / PLANE_STATE_SIZE)
PULSE2_BEND_BIT  = 1 << (PULSE2_BEND_PLANE / PLANE_STATE_SIZE)
TRIANGLE_BEND_BIT = 1 << (TRIANGLE_BEND_PLANE / PLANE_STATE_SIZE)
BEND_PLANES      = PULSE1_BEND_BIT | PULSE2_BEND_BIT | TRIANGLE_BEND_BIT

.segment "ZEROPAGE"

pointer:                .res 2
entry:                  .res 2
opcode:                 .res 1
phrase_table:           .res 2
timer_low_table:        .res 2
timer_high_table:       .res 2
bend:                   .res 1
bend_sign:              .res 1
bend_planes:            .res 1
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
.assert (TRIANGLE_COUNTER | TRIANGLE_SOUNDING) <> 0, error, "a sounding triangle's counter clears the zero flag"
.assert COUNT_STEP = 1 << COUNT_SHIFT, error, "a repeat count steps from the bit it is shifted down by"
.assert PLANE_STATE_BYTES + PLANE_PHRASE < $100, error, "a plane's phrase pointer is reached in page zero"

; Readies the tables the planes read through and points every plane at its own first token. Every
; table lies inside the program, so no sum here carries out of its high byte.
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

    lda timer_low_table
    adc #PITCH_COUNT
    sta timer_high_table
    lda timer_low_table + 1
    adc #$00
    sta timer_high_table + 1

    lda song_data + PHRASE_TABLE_OFFSET
    adc #<(song_data + PHRASE_TABLE_COUNT_SIZE)
    sta phrase_table
    lda song_data + PHRASE_TABLE_OFFSET + 1
    adc #>(song_data + PHRASE_TABLE_COUNT_SIZE)
    sta phrase_table + 1

    ldy #$00
    beq seed_planes

; Brings every plane back to the token its stream is re-entered at, which is the whole of what a
; song coming round restores: the token the loop tick starts is one the plane reads outright.
channels_rewind:
    ldy #LOOP_ENTRIES_OFFSET - STREAM_OFFSETS_OFFSET

; Points each plane at the offset the header holds for it in the table Y starts in, and empties what
; it plays. A plane the block leaves out states ABSENT_STREAM, and its source lands in page zero,
; which no song occupies: that page is what marks it absent, and its value stays at zero
; throughout. The fields every token sets for itself are left to the token the plane reads next.
seed_planes:
    ldx #$00
@next:
    lda song_data + STREAM_OFFSETS_OFFSET,y
    iny
    and song_data + STREAM_OFFSETS_OFFSET,y
    cmp #<ABSENT_STREAM
    bne @present
    iny
    lda #ABSENT_PAGE
    sta plane_state + PLANE_SOURCE + 1,x
    beq @empty
@present:
    dey
    clc
    lda song_data + STREAM_OFFSETS_OFFSET,y
    adc #<song_data
    sta plane_state + PLANE_SOURCE,x
    iny
    lda song_data + STREAM_OFFSETS_OFFSET,y
    adc #>song_data
    sta plane_state + PLANE_SOURCE + 1,x
    iny

@empty:
    lda #$00
    sta plane_state + PLANE_TOKEN_TICKS,x
    sta plane_state + PLANE_VALUE,x
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
; tick its channel's new value flags, since it holds a value for those ticks alone; a bit of
; `bend_planes` marks each bend plane, its value plane standing right before it.
channels_advance:
    lda #BEND_PLANES
    sta bend_planes
    ldx #$00
@plane:
    lsr bend_planes
    bcc @step
    lda plane_state + PLANE_VALUE - PLANE_STATE_SIZE,x
    bpl @next
@step:
    lda plane_state + PLANE_SOURCE + 1,x
    beq @next
    jsr plane_advance
@next:
    txa
    clc
    adc #PLANE_STATE_SIZE
    tax
    cpx #PLANE_STATE_BYTES
    bne @plane
    rts

; Advances the plane whose state lies at X by one tick, leaving the value it plays in that state.
; A token states the ticks it covers beyond the one it is fetched for, so a plane reaches for the
; next token the moment the one it stands on has none left.
;
; The values a tick plays come from wherever the token put them: a phrase body, the bytes spelled
; out behind a literal, or the value the plane already reached. A body played out holds its last
; value onward, which is what carries a note whose envelope has finished. The phrase pointer stands
; one before the next value, so a tick steps it on and reads.
plane_advance:
    lda plane_state + PLANE_REPEATS,x
    beq @symbol
    dec plane_state + PLANE_REPEATS,x
    rts
@symbol:
    lda plane_state + PLANE_TOKEN_TICKS,x
    beq @fetch
    dec plane_state + PLANE_TOKEN_TICKS,x
@plays:
    lda plane_state + PLANE_PHRASE_TICKS,x
    beq @held
    inc plane_state + PLANE_PHRASE,x
    bne @reading
    inc plane_state + PLANE_PHRASE + 1,x
@reading:
    lda (plane_state + PLANE_PHRASE,x)
    clc
    adc plane_state + PLANE_SHIFT,x
    sta plane_state + PLANE_VALUE,x
    dec plane_state + PLANE_PHRASE_TICKS,x
@held:
    lda plane_state + PLANE_VALUE,x
    and plane_state + PLANE_COUNT_MASK,x
    lsr
    lsr
    lsr
    lsr
    sta plane_state + PLANE_REPEATS,x
    rts

; Reads the token the plane at X stands on into that plane's own state, then plays from it.
@fetch:
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
    bne @plays_phrase

    lda opcode
    and #TOKEN_OPERAND_MASK
    sta plane_state + PLANE_TOKEN_TICKS,x
    clc
    adc #$01
    sta plane_state + PLANE_PHRASE_TICKS,x

    lda #$00
    sta plane_state + PLANE_SHIFT,x

    lda pointer
    sta plane_state + PLANE_PHRASE,x
    lda pointer + 1
    sta plane_state + PLANE_PHRASE + 1,x

    clc
    tya
    adc plane_state + PLANE_PHRASE_TICKS,x
    tay
    bne @advance_source

@holds:
    lda opcode
    and #TOKEN_OPERAND_MASK
    sta plane_state + PLANE_TOKEN_TICKS,x
    lda #$00
    sta plane_state + PLANE_PHRASE_TICKS,x
    beq @advance_source

@plays_phrase:
    lda opcode
    and #PHRASE_ID_MASK
    cmp #PHRASE_ID_ESCAPE
    bne @named
    lda (pointer),y
    iny
; The doubled id's ninth bit carries into the page of the table entry.
@named:
    asl
    sta entry
    tya
    pha
    lda phrase_table + 1
    adc #$00
    sta entry + 1
    lda phrase_table
    ldy entry
    sta entry
    clc
    lda (entry),y
    adc #<song_data
    sta plane_state + PLANE_PHRASE,x
    iny
    lda (entry),y
    adc #>song_data
    sta plane_state + PLANE_PHRASE + 1,x

; The phrase opens with its length and its default count, which leaves the pointer one before the
; body.
    lda (plane_state + PLANE_PHRASE,x)
    sta plane_state + PLANE_PHRASE_TICKS,x
    inc plane_state + PLANE_PHRASE,x
    bne @length_read
    inc plane_state + PLANE_PHRASE + 1,x
@length_read:
    lda (plane_state + PLANE_PHRASE,x)
    sta plane_state + PLANE_TOKEN_TICKS,x
    pla
    tay

    lda opcode
    and #DEFAULT_COUNT_FLAG
    bne @shifts
    lda (pointer),y
    iny
    sta plane_state + PLANE_TOKEN_TICKS,x
@shifts:
    lda #$00
    bit opcode
    bvc @shift
    lda (pointer),y
    iny
@shift:
    sta plane_state + PLANE_SHIFT,x

; Moves the plane's source on by the Y bytes its token took.
@advance_source:
    clc
    tya
    adc plane_state + PLANE_SOURCE,x
    sta plane_state + PLANE_SOURCE,x
    bcc @source_moved
    inc plane_state + PLANE_SOURCE + 1,x
@source_moved:
    jmp @plays

; Writes what every plane last played to the registers its channel owns. The triangle names its
; silence in the pitch its value plane carries: the index standing above every pitch the table
; holds writes the silenced linear counter alone, so the divider stays where the channel last
; sounded. The comparison's zero flag survives the counter's store and tells the rest apart.
channels_write:
    ldx #PULSE1_REGISTERS
    ldy #PULSE1_CONTROL_PLANE
    jsr write_pulse
    ldx #PULSE2_REGISTERS
    ldy #PULSE2_CONTROL_PLANE
    jsr write_pulse

    lda plane_state + TRIANGLE_VALUE_PLANE + PLANE_VALUE
    ldy #TRIANGLE_COUNTER | TRIANGLE_SILENT
    cmp #SILENT_PITCH_INDEX
    beq @counter
    ldy #TRIANGLE_COUNTER | TRIANGLE_SOUNDING
@counter:
    sty CHANNEL_CONTROL + TRIANGLE_REGISTERS
    beq @noise
    ldy plane_state + TRIANGLE_BEND_PLANE + PLANE_VALUE
    sty bend
    ldx #TRIANGLE_REGISTERS
    jsr write_timer

@noise:
    lda plane_state + NOISE_CONTROL_PLANE + PLANE_VALUE
    and #NOISE_CONTROL_MASK
    ora #NOISE_CONTROL_FIXED
    sta CHANNEL_CONTROL + NOISE_REGISTERS
    lda plane_state + NOISE_VALUE_PLANE + PLANE_VALUE
    and #NOISE_VALUE_MASK
    .if NOISE_VALUE_FIXED <> 0
    ora #NOISE_VALUE_FIXED
    .endif
    sta CHANNEL_TIMER_LOW + NOISE_REGISTERS
    rts

; Writes the pulse whose register base lies in X and whose control plane lies at Y.
write_pulse:
    lda plane_state + PLANE_VALUE,y
    and #PULSE_CONTROL_MASK
    ora #PULSE_CONTROL_FIXED
    sta CHANNEL_CONTROL,x
    lda plane_state + 2 * PLANE_STATE_SIZE + PLANE_VALUE,y
    sta bend
    lda plane_state + PLANE_STATE_SIZE + PLANE_VALUE,y

; Writes the timer the value byte in A names to the channel whose register base lies in X, the
; byte loaded last so its sign stands in N. The low seven bits index the pitch table, and the top
; bit says the tick carries the bend standing in `bend`; an unflagged tick sounds its pitch's own
; divider. The bend states divider steps in two's complement, so it reaches the timer's high half
; as $00 or $FF beside the carry the low half raised. A high half reaches the register only where
; it differs from the last one written, since storing it restarts a pulse waveform and reloads
; the triangle's counter.
write_timer:
    cmp #BEND_FLAG
    and #PITCH_INDEX_MASK
    tay
    bcs @indexed
    lda #$00
    sta bend
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

.assert TRIANGLE_BEND_PLANE / PLANE_STATE_SIZE < 8, error, "every bend plane has a bit in one byte"
.assert PULSE1_BEND_PLANE = PULSE1_VALUE_PLANE + PLANE_STATE_SIZE, error, "a bend plane follows its value plane"
.assert PULSE2_BEND_PLANE = PULSE2_VALUE_PLANE + PLANE_STATE_SIZE, error, "a bend plane follows its value plane"
.assert TRIANGLE_BEND_PLANE = TRIANGLE_VALUE_PLANE + PLANE_STATE_SIZE, error, "a bend plane follows its value plane"
.assert PULSE1_VALUE_PLANE = PULSE1_CONTROL_PLANE + PLANE_STATE_SIZE, error, "a pulse's value plane follows its control plane"
.assert PULSE2_VALUE_PLANE = PULSE2_CONTROL_PLANE + PLANE_STATE_SIZE, error, "a pulse's value plane follows its control plane"
.assert PHRASE_LENGTH_SIZE = 1 && PHRASE_DEFAULT_SIZE = 1, error, "a phrase body follows its length and its default count"
.assert ABSENT_PAGE = 0, error, "an absent plane's page reads as zero"
