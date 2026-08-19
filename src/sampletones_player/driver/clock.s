.setcpu "6502"

.include "song.inc"

.export clock_reset
.export clock_advance
.exportzp current_tick

.import song_data

.segment "ZEROPAGE"

accumulator:    .res 2
current_tick:   .res 2
finished:       .res 1

.segment "CODE"

clock_reset:
    lda #$00
    sta accumulator
    sta accumulator + 1
    sta current_tick
    sta current_tick + 1
    sta finished
    rts

; Advances the stream by one play call's worth of ticks.
; Answers with A = 0 where the console is to be left alone, either because the stream holds its
; tick through this call or because the song has ended.
clock_advance:
    lda finished
    bne @hold

    clc
    lda accumulator
    adc song_data + STEP_FRACTION_OFFSET
    sta accumulator
    lda accumulator + 1
    adc song_data + STEP_FRACTION_OFFSET + 1
    sta accumulator + 1
    lda song_data + STEP_WHOLE_OFFSET
    adc #$00
    beq @hold

    clc
    adc current_tick
    sta current_tick
    bcc @wrap
    inc current_tick + 1
@wrap:
    jsr wrap_tick
    lda finished
    bne @hold

    lda #$01
    rts
@hold:
    lda #$00
    rts

; Brings a tick that has run past the song's end back to where the song repeats, or marks the song
; finished where it has no loop. Each pass takes off the whole of the looping part, so a call that
; advances by more ticks than the loop is long still lands inside it.
wrap_tick:
    lda current_tick + 1
    cmp song_data + TOTAL_TICKS_OFFSET + 1
    bcc @within
    bne @past
    lda current_tick
    cmp song_data + TOTAL_TICKS_OFFSET
    bcc @within
@past:
    lda song_data + LOOP_TICK_OFFSET
    cmp #<NO_LOOP
    bne @rewind
    lda song_data + LOOP_TICK_OFFSET + 1
    cmp #>NO_LOOP
    bne @rewind

    lda #$01
    sta finished
    rts
@rewind:
    sec
    lda current_tick
    sbc song_data + TOTAL_TICKS_OFFSET
    sta current_tick
    lda current_tick + 1
    sbc song_data + TOTAL_TICKS_OFFSET + 1
    sta current_tick + 1

    clc
    lda current_tick
    adc song_data + LOOP_TICK_OFFSET
    sta current_tick
    lda current_tick + 1
    adc song_data + LOOP_TICK_OFFSET + 1
    sta current_tick + 1
    jmp wrap_tick
@within:
    rts
