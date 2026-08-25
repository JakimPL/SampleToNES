.setcpu "6502"

.include "song.inc"

.export clock_reset
.export clock_advance
.export clock_step

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

; Answers with the ticks this play call advances the streams by, which the accumulator reads off
; the top of a step added once a call. A song standing still between its own ticks, and one that
; has ended, both answer with none.
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
    lda #$00
    rts

; Moves the clock on by a single tick and answers what the channels are to do with it: play it
; where the song still runs, play it from the loop entry where the song has just come round, or
; leave the console alone where the song has ended.
clock_step:
    inc current_tick
    bne @reached
    inc current_tick + 1
@reached:
    lda current_tick + 1
    cmp song_data + TOTAL_TICKS_OFFSET + 1
    bcc @plays
    bne @ended
    lda current_tick
    cmp song_data + TOTAL_TICKS_OFFSET
    bcc @plays
@ended:
    lda song_data + LOOP_TICK_OFFSET
    cmp #<NO_LOOP
    bne @repeats
    lda song_data + LOOP_TICK_OFFSET + 1
    cmp #>NO_LOOP
    bne @repeats

    lda #$01
    sta finished
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
