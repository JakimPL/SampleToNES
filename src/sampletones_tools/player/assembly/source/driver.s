.setcpu "6502"

.include "nes.inc"
.include "song.inc"

.export nsf_init
.export nsf_play
.export song_data

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
    lsr a
    bcs @plays
    jsr channels_rewind
@plays:
    jsr channels_advance
    dec pending_ticks
    bne @next
    jmp channels_write
@held:
    rts

; Silences every channel, switches the channels on and plays the song's first tick. The driver's
; memory starts cleared, as an NSF player and the cartridge both leave it, so the clock starts on
; the song's first tick.
start_song:
    lda #SILENCED_REGISTER
    tax
@silencing:
    sta FIRST_CHANNEL_REGISTER,x
    inx
    cpx #CHANNEL_REGISTER_COUNT
    bne @silencing
    lda #CHANNELS_ENABLED
    sta APU_STATUS
    lda #FRAME_COUNTER_SEQUENCE
    sta APU_FRAME_COUNTER
    lda #SWEEP_DISABLED
    sta PULSE1_SWEEP
    sta PULSE2_SWEEP
    lda #NOISE_LENGTH_COUNTER_LOAD
    sta NOISE_LENGTH_COUNTER
    jsr channels_reset
    jsr channels_advance
    jmp channels_write

.segment "SONG"

song_data:

.assert SILENCED_REGISTER = 0, error, "the silenced value doubles as the first register's index"
.assert TICK_FINISHED = 0 && TICK_PLAYS = 1 && TICK_REPEATED = 2, error, "a step's outcome is read from its two lowest bits"
