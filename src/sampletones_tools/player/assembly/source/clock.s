.setcpu "6502"

.include "song.inc"

.export clock_advance
.export clock_step

.import song_data

.segment "ZEROPAGE"

accumulator:    .res 2
current_tick:   .res 2
finished:       .res 1

.segment "CODE"

; Answers with the ticks this play call advances the streams by, which the accumulator reads off
; the top of a step added once a call. A song standing still between its own ticks, and one that
; has ended, both answer with none: an ended song holds one in `finished`, which a shift turns
; into none.
clock_advance:
    lda finished
    bne @none

    clc
    lda accumulator
    adc song_data + STEP_FRACTION_OFFSET
    sta accumulator
    lda accumulator + 1
    adc song_data + STEP_FRACTION_OFFSET + 1
    sta accumulator + 1
    lda song_data + STEP_WHOLE_OFFSET
    adc #$00
    rts
@none:
    lsr a
    rts

; Moves the clock on by a single tick and answers what the channels are to do with it: play it
; where the song still runs, play it from the loop entry where the song has just come round, or
; leave the console alone where the song has ended.
clock_step:
    inc current_tick
    bne @reached
    inc current_tick + 1
@reached:
    lda current_tick
    cmp song_data + TOTAL_TICKS_OFFSET
    lda current_tick + 1
    sbc song_data + TOTAL_TICKS_OFFSET + 1
    bcc @plays
    lda song_data + LOOP_TICK_OFFSET
    and song_data + LOOP_TICK_OFFSET + 1
    cmp #<NO_LOOP
    bne @repeats

    inc finished
    lda #TICK_FINISHED
    rts
@repeats:
    lda song_data + LOOP_TICK_OFFSET
    sta current_tick
    lda song_data + LOOP_TICK_OFFSET + 1
    sta current_tick + 1
    lda #TICK_REPEATED
    rts
@plays:
    lda #TICK_PLAYS
    rts

.assert <NO_LOOP = >NO_LOOP, error, "a song that ends is told apart by both its loop bytes reading the same"
