.setcpu "6502"

.include "nes.inc"

.export nsf_init
.export nsf_play
.export song_data

.import clock_reset
.import clock_advance
.import channels_reset
.import channels_write_tick

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
    jmp channels_write_tick

advance_song:
    jsr clock_advance
    beq @held
    jmp channels_write_tick
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
