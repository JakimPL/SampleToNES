.setcpu "6502"

.include "nes.inc"
.include "song.inc"

.export channels_reset
.export channels_write_tick

.import song_data
.importzp current_tick

SHADOW_UNWRITTEN = $FF

.segment "ZEROPAGE"

pointer:                .res 2
record_offset:          .res 2
timer_high_shadows:     .res TRIANGLE_REGISTERS + 1

.segment "CODE"

channels_reset:
    lda #SHADOW_UNWRITTEN
    sta timer_high_shadows + PULSE1_REGISTERS
    sta timer_high_shadows + PULSE2_REGISTERS
    sta timer_high_shadows + TRIANGLE_REGISTERS
    rts

channels_write_tick:
    jsr set_tone_offset
    ldx #PULSE1_REGISTERS
    ldy #PULSE1_STREAM
    jsr write_tone_channel
    ldx #PULSE2_REGISTERS
    ldy #PULSE2_STREAM
    jsr write_tone_channel
    ldx #TRIANGLE_REGISTERS
    ldy #TRIANGLE_STREAM
    jsr write_tone_channel

    jsr set_noise_offset
    ldx #NOISE_REGISTERS
    ldy #NOISE_STREAM
    jmp write_noise_channel

.assert NOISE_RECORD_SIZE = 2, error, "the noise record is reached by one doubling"
.assert TONE_RECORD_SIZE = 3, error, "the tone record is reached by a doubling and one more tick"

set_noise_offset:
    lda current_tick
    asl
    sta record_offset
    lda current_tick + 1
    rol
    sta record_offset + 1
    rts

set_tone_offset:
    jsr set_noise_offset
    clc
    lda record_offset
    adc current_tick
    sta record_offset
    lda record_offset + 1
    adc current_tick + 1
    sta record_offset + 1
    rts

; Points at the current tick's record in the stream whose header offset lies at Y.
set_pointer:
    clc
    lda song_data + STREAM_OFFSETS_OFFSET,y
    adc record_offset
    sta pointer
    lda song_data + STREAM_OFFSETS_OFFSET + 1,y
    adc record_offset + 1
    sta pointer + 1

    clc
    lda pointer
    adc #<song_data
    sta pointer
    lda pointer + 1
    adc #>song_data
    sta pointer + 1
    rts

; Writes one tick to a channel, with the channel's register base in X and its header offset in Y.
; A timer's high half reaches the register only where it differs from the last one written, since
; storing it restarts a pulse waveform and reloads the triangle's counter.
write_tone_channel:
    jsr set_pointer
    ldy #$00
    lda (pointer),y
    sta CHANNEL_CONTROL,x
    iny
    lda (pointer),y
    sta CHANNEL_TIMER_LOW,x
    iny
    lda (pointer),y
    cmp timer_high_shadows,x
    beq @held
    sta timer_high_shadows,x
    sta CHANNEL_TIMER_HIGH,x
@held:
    rts

write_noise_channel:
    jsr set_pointer
    ldy #$00
    lda (pointer),y
    sta CHANNEL_CONTROL,x
    iny
    lda (pointer),y
    sta CHANNEL_TIMER_LOW,x
    rts
