.setcpu "6502"

.include "nes.inc"
.include "song.inc"

.export nsf_init
.export nsf_play
.export song_data

.import clock_reset
.import clock_advance
.import clock_step
.import channels_reset
.import channels_rewind
.import channels_advance
.import channels_write

.segment "ZEROPAGE"

pending_ticks:  .res 1

.segment "CODE"

nsf_init:
    jmp start_song
nsf_play:
    jmp advance_song

start_song:
    jsr silence_channels
    lda #CHANNELS_ENABLED
    sta APU_STATUS
    lda #FRAME_COUNTER_SEQUENCE
    sta APU_FRAME_COUNTER
    lda #SWEEP_DISABLED
    sta PULSE1_SWEEP
    sta PULSE2_SWEEP
    lda #NOISE_LENGTH_COUNTER_LOAD
    sta NOISE_LENGTH_COUNTER
    jsr clock_reset
    jsr channels_reset
    jsr channels_advance
    jmp channels_write

; Advances the streams by the ticks this call is due and writes the tick they land on. A call
; crossing the song's end either brings the planes back to where the song repeats and plays on,
; or leaves the console holding what the final tick wrote.
advance_song:
    jsr clock_advance
    beq @held
    sta pending_ticks
@next:
    jsr clock_step
    beq @held
    cmp #TICK_REPEATED
    bne @plays
    jsr channels_rewind
@plays:
    jsr channels_advance
    dec pending_ticks
    bne @next
    jmp channels_write
@held:
    rts

silence_channels:
    lda #SILENCED_REGISTER
    ldx #$00
@next:
    sta FIRST_CHANNEL_REGISTER,x
    inx
    cpx #CHANNEL_REGISTER_COUNT
    bne @next
    rts

.segment "SONG"

song_data:
