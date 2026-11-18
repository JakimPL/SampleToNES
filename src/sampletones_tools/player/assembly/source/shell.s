.setcpu "6502"

.include "nes.inc"
.include "song.inc"
.include "ppu.inc"
.include "program.inc"
.include "deck.inc"

.export program_block
.export reset
.export nmi
.export irq

.import nsf_init
.import nsf_play
.import song_data
.importzp plane_state
.import __ZEROPAGE_RUN__
.import __ZEROPAGE_SIZE__
.import deck_palette
.import deck_screen
.import deck_labels
.import pulse_waves
.import pulse_rest
.import triangle_wave
.import other_rest
.import noise_waves
.import note_names
.import noise_names

TRANSPORT_RUN       = 0
PROGRESS_RUN        = 1
FIRST_RUN           = 2
SECOND_RUN          = 4
RUN_COUNT           = 6

TRANSPORT_SLOT      = 0
PROGRESS_SLOT       = TRANSPORT_SLOT + TRANSPORT_CELLS
FIRST_SLOT          = PROGRESS_SLOT + PROGRESS_CELLS
SECOND_SLOT         = FIRST_SLOT + CHANNEL_CELLS + WAVE_CELLS
BUFFER_SIZE         = SECOND_SLOT + CHANNEL_CELLS + WAVE_CELLS

WAVE_TABLE_SIZE     = 4
NOTE_CELLS          = 3
FIELD_COUNT         = 3
METER_STEPS_PER_TILE = 2
MAX_LEVEL           = 15
LEVEL_MASK          = $0F
DUTY_SHIFT          = 6
NOISE_PERIOD_MASK   = $0F
NOISE_SHORT_FLAG    = $80
SHIMMER_BIT         = $02
PACKED_END          = $80
CLOCK_STATE_SIZE    = FRAME_COUNT_SIZE + CLOCK_DIGITS + SECOND_FRACTION_SIZE + PROGRESS_SIZE

SPRITE_Y            = 0
SPRITE_TILE         = 1
SPRITE_ATTRIBUTES   = 2
SPRITE_X            = 3

.segment "PLAYERZP": zeropage

pointer:            .res 2
frame_ready:        .res 1
held:               .res 1
paused:             .res 1
ended:              .res 1
parity:             .res 1
buttons:            .res 1
pressed:            .res 1
run:                .res 1
channel:            .res 1
slot:               .res 1
count:              .res 1
step:               .res 1
level:              .res 1
meter_none:         .res 1
meter_last:         .res 1
note_tiles:         .res NOTE_CELLS
played_frames:      .res 1
run_high:           .res RUN_COUNT
run_low:            .res RUN_COUNT
remaining:          .res FRAME_COUNT_SIZE
digits:             .res CLOCK_DIGITS
second_fraction:    .res SECOND_FRACTION_SIZE
progress:           .res PROGRESS_SIZE

.segment "PROGRAM"

; What the exporter writes about the song. The block opens with the address this code was linked
; against, the one thing here the linker writes, so a file pairing this code with another driver
; is told apart before it is written.
program_block:
    .word song_data
    .res PROGRAM_BLOCK_SIZE - LINKED_SONG_OFFSET - 2, UNWRITTEN_BYTE

.segment "PLAYER"

; Brings the console from power-on to a playing song. Interrupts stay masked for good, which keeps
; the sound chip's frame interrupt from being served. The driver reads its memory as zero from the
; start, and a console powers on holding anything, so every page is cleared between the two frames
; the video chip takes to warm up. The screen is drawn with rendering off, and the first frame
; interrupt finds the song started and its first readings composed.
reset:
    sei
    cld
    ldx #STACK_TOP
    txs
    inx
    stx PPU_CONTROL
    stx PPU_MASK
    bit PPU_STATUS
@warming:
    bit PPU_STATUS
    bpl @warming

    txa
@clearing:
    sta RAM_START + 0 * PAGE_SIZE,x
    sta RAM_START + 1 * PAGE_SIZE,x
    sta RAM_START + 2 * PAGE_SIZE,x
    sta RAM_START + 3 * PAGE_SIZE,x
    sta RAM_START + 4 * PAGE_SIZE,x
    sta RAM_START + 5 * PAGE_SIZE,x
    sta RAM_START + 6 * PAGE_SIZE,x
    sta RAM_START + 7 * PAGE_SIZE,x
    inx
    bne @clearing

@warmed:
    bit PPU_STATUS
    bpl @warmed

    jsr draw_screen
    jsr place_labels
    lda #>TRANSPORT_CELL
    sta run_high + TRANSPORT_RUN
    lda #<TRANSPORT_CELL
    sta run_low + TRANSPORT_RUN
    lda #>PROGRESS_CELL
    sta run_high + PROGRESS_RUN
    lda #<PROGRESS_CELL
    sta run_low + PROGRESS_RUN
    jsr start_song
    jsr compose

    bit PPU_STATUS
    lda #$00
    sta PPU_SCROLL
    sta PPU_SCROLL
    lda #FRAME_CONTROL
    sta PPU_CONTROL
    lda #FRAME_MASK
    sta PPU_MASK

; Waits for each frame, answers the controller and composes what the next frame writes.
main:
    lda frame_ready
    beq main
    lda #$00
    sta frame_ready
    jsr read_controller
    jsr answer_buttons
    jsr compose
    jmp main

; Sends the sprites, writes the composed runs of cells and plays the song on. Every frame does the
; same work in the same cycles, so the driver is entered at the same moment of each frame.
nmi:
    pha
    txa
    pha
    tya
    pha
    lda #$00
    sta SPRITE_ADDRESS
    lda #>SPRITE_PAGE
    sta SPRITE_TRANSFER
    bit PPU_STATUS
    ldx #$00
    stx run
@run:
    ldy run
    lda run_high,y
    sta PPU_ADDRESS
    lda run_low,y
    sta PPU_ADDRESS
    lda run_lengths,y
    tay
@cell:
    lda BUFFER,x
    sta PPU_DATA
    inx
    dey
    bne @cell
    inc run
    lda run
    cmp #RUN_COUNT
    bne @run

    lda #$00
    sta PPU_SCROLL
    sta PPU_SCROLL
    lda #FRAME_CONTROL
    sta PPU_CONTROL
    lda held
    bne @held
    jsr nsf_play
    jsr advance_clock
@held:
    inc frame_ready
    pla
    tay
    pla
    tax
    pla
irq:
    rti

; Starts the song over from a cleared driver, as a cartridge just switched on would.
restart:
    lda #$01
    sta held
    lda #$00
    tax
@clearing:
    sta __ZEROPAGE_RUN__,x
    inx
    cpx #<__ZEROPAGE_SIZE__
    bne @clearing
    jsr start_song
    lda #$00
    sta paused
    sta held
    rts

start_song:
    jsr nsf_init
    lda #$00
    sta ended
    sta played_frames
    ldx #CLOCK_STATE_SIZE - 1
@zero:
    sta remaining,x
    dex
    bpl @zero
    ldx #FRAME_COUNT_SIZE - 1
@frames:
    lda program_block + TOTAL_FRAMES_OFFSET,x
    sta remaining,x
    dex
    bpl @frames
    rts

; Moves the clock and the progress bar on by a frame. Once the song's frames run out, a song that
; repeats takes up the clock where its loop begins, and one that ends holds it.
advance_clock:
    lda ended
    bne @held
    inc played_frames
    clc
    lda second_fraction
    adc #<SECOND_STEP
    sta second_fraction
    lda second_fraction + 1
    adc #>SECOND_STEP
    sta second_fraction + 1
    bcc @counted
    jsr next_second
@counted:
    clc
    ldx #$00
@progress:
    lda progress,x
    adc program_block + PROGRESS_STEP_OFFSET,x
    sta progress,x
    inx
    txa
    eor #PROGRESS_SIZE
    bne @progress

    ldx #$00
@borrow:
    lda remaining,x
    sec
    sbc #$01
    sta remaining,x
    bcs @counted_down
    inx
    cpx #FRAME_COUNT_SIZE
    bne @borrow
@counted_down:
    lda remaining
    ora remaining + 1
    ora remaining + 2
    bne @held
    lda program_block + LOOP_FRAMES_OFFSET
    ora program_block + LOOP_FRAMES_OFFSET + 1
    ora program_block + LOOP_FRAMES_OFFSET + 2
    bne @repeats
    inc ended
    rts
@repeats:
    ldx #CLOCK_STATE_SIZE - 1
@restoring:
    lda program_block + LOOP_FRAMES_OFFSET,x
    sta remaining,x
    dex
    bpl @restoring
@held:
    rts

next_second:
    ldx #CLOCK_DIGITS - 1
@digit:
    inc digits,x
    lda digits,x
    cmp digit_limits,x
    bne @counted
    lda #$00
    sta digits,x
    dex
    bpl @digit
@counted:
    rts

read_controller:
    lda buttons
    eor #$FF
    sta pressed
    lda #CONTROLLER_STROBE
    sta CONTROLLER_PORT
    lda #CONTROLLER_RELEASE
    sta CONTROLLER_PORT
    ldx #BUTTON_COUNT
@reading:
    lda CONTROLLER_PORT
    lsr a
    rol buttons
    dex
    bne @reading
    lda buttons
    and pressed
    sta pressed
    rts

; START pauses and resumes, SELECT starts the song over. A pause silences the channels, and the
; driver sounds them again with the first tick it writes.
answer_buttons:
    lda pressed
    and #BUTTON_START
    beq @select
    lda paused
    eor #$01
    sta paused
    sta held
    beq @select
    lda #PULSE_MUTED
    sta CHANNEL_CONTROL + PULSE1_REGISTERS
    sta CHANNEL_CONTROL + PULSE2_REGISTERS
    sta CHANNEL_CONTROL + NOISE_REGISTERS
    lda #TRIANGLE_MUTED
    sta CHANNEL_CONTROL + TRIANGLE_REGISTERS
@select:
    lda pressed
    and #BUTTON_SELECT
    beq @answered
    jmp restart
@answered:
    rts

draw_screen:
    bit PPU_STATUS
    lda #>PALETTE_START
    sta PPU_ADDRESS
    lda #<PALETTE_START
    sta PPU_ADDRESS
    ldx #$00
@palette:
    lda deck_palette,x
    sta PPU_DATA
    inx
    cpx #PALETTE_SIZE
    bne @palette

    lda #>NAMETABLE_START
    sta PPU_ADDRESS
    lda #<NAMETABLE_START
    sta PPU_ADDRESS
    jsr unpack_screen

    ldy #$00
@field:
    lda field_high,y
    sta PPU_ADDRESS
    lda field_low,y
    sta PPU_ADDRESS
    ldx field_start,y
    lda field_columns,y
    sta count
@character:
    lda program_block,x
    sta PPU_DATA
    inx
    dec count
    bne @character
    iny
    cpy #FIELD_COUNT
    bne @field

    lda #>TOTAL_CELL
    sta PPU_ADDRESS
    lda #<TOTAL_CELL
    sta PPU_ADDRESS
    ldx #$00
@total:
    lda program_block + TOTAL_TIME_OFFSET,x
    jsr write_clock_cell
    inx
    cpx #CLOCK_DIGITS
    bne @total
    rts

write_clock_cell:
    clc
    adc #DIGIT_ZERO_TILE
    sta PPU_DATA
    cpx #CLOCK_DIGITS / 2 - 1
    bne @written
    lda #COLON_TILE
    sta PPU_DATA
@written:
    rts

; Unpacks the screen into video memory: a header below $80 copies one byte more than it states, a
; header above $80 repeats the next byte 257 less the header times, and $80 ends the data.
unpack_screen:
    lda #<deck_screen
    sta pointer
    lda #>deck_screen
    sta pointer + 1
@header:
    jsr next_packed
    cmp #PACKED_END
    beq @unpacked
    bcs @repeat
    tax
    inx
@literal:
    jsr next_packed
    sta PPU_DATA
    dex
    bne @literal
    beq @header
@repeat:
    eor #$FF
    tax
    inx
    inx
    jsr next_packed
@run:
    sta PPU_DATA
    dex
    bne @run
    beq @header
@unpacked:
    rts

next_packed:
    ldy #$00
    lda (pointer),y
    inc pointer
    bne @read
    inc pointer + 1
@read:
    rts

place_labels:
    ldx #$00
    lda #HIDDEN_SPRITE_Y
@hiding:
    sta SPRITE_PAGE + SPRITE_Y,x
    inx
    inx
    inx
    inx
    bne @hiding
@label:
    lda deck_labels,x
    sta SPRITE_PAGE + MARKER_SLOTS * SPRITE_BYTES,x
    inx
    cpx #LABEL_SPRITES * SPRITE_BYTES
    bne @label
    rts

; Composes what the next frame writes: the playing state and the time, the progress bar, and two
; of the four channels, the pulses on one frame and the triangle and the noise on the next.
compose:
    lda parity
    eor #$01
    sta parity
    jsr compose_transport
    jsr compose_progress
    jsr compose_channels
    jmp compose_markers

compose_transport:
    ldx #TRANSPORT_CELLS - 1
    lda #TRANSPORT_GAP_TILE
@gap:
    sta BUFFER + TRANSPORT_SLOT,x
    dex
    bpl @gap
    lda #PLAY_TILE
    ldx paused
    beq @playing
    lda #PAUSE_TILE
@playing:
    ldx ended
    beq @stated
    lda #STOP_TILE
@stated:
    sta BUFFER + TRANSPORT_SLOT
    ldx #$00
    ldy #TRANSPORT_SLOT + PLAYED_OFFSET
@digit:
    lda digits,x
    clc
    adc #DIGIT_ZERO_TILE
    sta BUFFER,y
    iny
    cpx #CLOCK_DIGITS / 2 - 1
    bne @next
    lda #COLON_TILE
    sta BUFFER,y
    iny
@next:
    inx
    cpx #CLOCK_DIGITS
    bne @digit
    rts

compose_progress:
    lda progress + PROGRESS_SIZE - 1
    sta count
    ldx #$00
@cell:
    lda count
    cmp #PROGRESS_STEPS
    bcc @partial
    lda #PROGRESS_STEPS
@partial:
    sta step
    clc
    adc #PROGRESS_EMPTY_TILE
    sta BUFFER + PROGRESS_SLOT,x
    lda count
    sec
    sbc step
    sta count
    inx
    cpx #PROGRESS_CELLS
    bne @cell
    rts

compose_channels:
    lda parity
    asl a
    sta channel
    ldx #FIRST_SLOT
    ldy #FIRST_RUN
    jsr compose_channel
    inc channel
    ldx #SECOND_SLOT
    ldy #SECOND_RUN
compose_channel:
    stx slot
    ldx channel
    lda channel_cell_low,x
    sta run_low,y
    clc
    adc #SCREEN_COLUMNS
    sta run_low + 1,y
    lda channel_cell_high,x
    sta run_high,y
    adc #$00
    sta run_high + 1,y
    lda channel
    beq @first_pulse
    cmp #$01
    beq @second_pulse
    cmp #$02
    beq @triangle
    jsr gather_noise
    jmp fill_channel
@first_pulse:
    ldx #PULSE1_CONTROL_PLANE
    jsr gather_pulse
    jmp fill_channel
@second_pulse:
    ldx #PULSE2_CONTROL_PLANE
    jsr gather_pulse
    jmp fill_channel
@triangle:
    jsr gather_triangle
    jmp fill_channel

; Reads a pulse from its control plane, whose offset stands in X, and its value plane behind it.
gather_pulse:
    lda #PULSE_METER_NONE
    sta meter_none
    lda #PULSE_METER_LAST_LIT
    sta meter_last
    lda plane_state + PLANE_VALUE,x
    and #LEVEL_MASK
    sta level
    beq @resting
    lda plane_state + PLANE_VALUE,x
    .repeat DUTY_SHIFT
    lsr a
    .endrepeat
    asl a
    asl a
    clc
    adc #<pulse_waves
    sta pointer
    lda #>pulse_waves
    adc #$00
    sta pointer + 1
    lda plane_state + PLANE_STATE_SIZE + PLANE_VALUE,x
    and #PITCH_INDEX_MASK
    jmp name_pitch
@resting:
    lda #<pulse_rest
    sta pointer
    lda #>pulse_rest
    sta pointer + 1
    jmp name_rest

gather_triangle:
    jsr other_meter
    lda plane_state + TRIANGLE_VALUE_PLANE + PLANE_VALUE
    and #PITCH_INDEX_MASK
    cmp #SILENT_PITCH_INDEX
    beq @resting
    tax
    lda #MAX_LEVEL
    sta level
    lda #<triangle_wave
    sta pointer
    lda #>triangle_wave
    sta pointer + 1
    txa
    jmp name_pitch
@resting:
    lda #$00
    sta level
    jmp other_resting

gather_noise:
    jsr other_meter
    lda plane_state + NOISE_CONTROL_PLANE + PLANE_VALUE
    and #LEVEL_MASK
    sta level
    beq other_resting
    lda #$00
    bit plane_state + NOISE_VALUE_PLANE + PLANE_VALUE
    bpl @long
    lda #2 * WAVE_TABLE_SIZE
@long:
    sta step
    lda played_frames
    and #SHIMMER_BIT
    beq @still
    lda #WAVE_TABLE_SIZE
@still:
    clc
    adc step
    adc #<noise_waves
    sta pointer
    lda #>noise_waves
    adc #$00
    sta pointer + 1
    lda plane_state + NOISE_VALUE_PLANE + PLANE_VALUE
    and #NOISE_PERIOD_MASK
    sta step
    asl a
    adc step
    tax
    lda noise_names,x
    sta note_tiles
    lda noise_names + 1,x
    sta note_tiles + 1
    lda noise_names + 2,x
    sta note_tiles + 2
    rts

other_meter:
    lda #OTHER_METER_NONE
    sta meter_none
    lda #OTHER_METER_LAST_LIT
    sta meter_last
    rts

other_resting:
    lda #<other_rest
    sta pointer
    lda #>other_rest
    sta pointer + 1
name_rest:
    lda #REST_TILE
    sta note_tiles
    sta note_tiles + 1
    sta note_tiles + 2
    rts

; Names the pitch index in A: its note within the octave, then the octave's digit.
name_pitch:
    ldy #$00
@octave:
    cmp #NOTES_PER_OCTAVE
    bcc @named
    sbc #NOTES_PER_OCTAVE
    iny
    bne @octave
@named:
    asl a
    tax
    lda note_names,x
    sta note_tiles
    lda note_names + 1,x
    sta note_tiles + 1
    tya
    clc
    adc #OCTAVE_ZERO_TILE
    sta note_tiles + 2
    rts

; Writes a channel's readings into its slot: one period of the wave twice over two rows, the gaps,
; the note and the meter, whose tiles hold two steps each and the last tile the fifteenth alone.
fill_channel:
    ldx slot
    ldy #$00
    lda (pointer),y
    sta BUFFER,x
    sta BUFFER + 2,x
    iny
    lda (pointer),y
    sta BUFFER + 1,x
    sta BUFFER + 3,x
    iny
    lda (pointer),y
    sta BUFFER + CHANNEL_CELLS,x
    sta BUFFER + CHANNEL_CELLS + 2,x
    iny
    lda (pointer),y
    sta BUFFER + CHANNEL_CELLS + 1,x
    sta BUFFER + CHANNEL_CELLS + 3,x

    ldy #CHANNEL_CELLS - WAVE_CELLS
    lda #CHANNEL_GAP_TILE
@gap:
    sta BUFFER + WAVE_CELLS,x
    inx
    dey
    bne @gap

    ldx slot
    lda note_tiles
    sta BUFFER + NOTE_OFFSET,x
    lda note_tiles + 1
    sta BUFFER + NOTE_OFFSET + 1,x
    lda note_tiles + 2
    sta BUFFER + NOTE_OFFSET + 2,x

    lda level
    sta count
    ldy #METER_PAIRS
@pair:
    lda count
    cmp #METER_STEPS_PER_TILE
    bcc @few
    lda #METER_STEPS_PER_TILE
@few:
    sta step
    lda meter_none
    sec
    sbc step
    sta BUFFER + METER_OFFSET,x
    lda count
    sec
    sbc step
    sta count
    inx
    dey
    bne @pair
    lda meter_last
    ldy level
    cpy #MAX_LEVEL
    bcs @lit
    adc #$01
@lit:
    sta BUFFER + METER_OFFSET,x
    rts

; Stands a marker over the key each sounding tone channel plays, and hides the others.
compose_markers:
    ldx #PULSE1_CONTROL_PLANE
    ldy #$00
    jsr pulse_marker
    ldx #PULSE2_CONTROL_PLANE
    ldy #$01
    jsr pulse_marker
    ldy #$02
    lda plane_state + TRIANGLE_VALUE_PLANE + PLANE_VALUE
    and #PITCH_INDEX_MASK
    cmp #SILENT_PITCH_INDEX
    bne place_marker
    beq hide_marker

pulse_marker:
    lda plane_state + PLANE_VALUE,x
    and #LEVEL_MASK
    beq hide_marker
    lda plane_state + PLANE_STATE_SIZE + PLANE_VALUE,x
    and #PITCH_INDEX_MASK
place_marker:
    asl a
    clc
    adc #KEYBOARD_LEFT
    sta step
    tya
    asl a
    asl a
    tax
    lda step
    sta SPRITE_PAGE + SPRITE_X,x
    lda #LANE_TOP
    sta SPRITE_PAGE + SPRITE_Y,x
    lda marker_tiles,y
    sta SPRITE_PAGE + SPRITE_TILE,x
    lda marker_palettes,y
    sta SPRITE_PAGE + SPRITE_ATTRIBUTES,x
    rts

hide_marker:
    tya
    asl a
    asl a
    tax
    lda #HIDDEN_SPRITE_Y
    sta SPRITE_PAGE + SPRITE_Y,x
    lda #$00
    sta SPRITE_PAGE + SPRITE_TILE,x
    sta SPRITE_PAGE + SPRITE_ATTRIBUTES,x
    sta SPRITE_PAGE + SPRITE_X,x
    rts

run_lengths:        .byte TRANSPORT_CELLS, PROGRESS_CELLS, CHANNEL_CELLS, WAVE_CELLS, CHANNEL_CELLS, WAVE_CELLS
digit_limits:       .byte DIGIT_BASE, DIGIT_BASE, 6, DIGIT_BASE
field_high:         .byte >TITLE_CELL, >ARTIST_CELL, >COPYRIGHT_CELL
field_low:          .byte <TITLE_CELL, <ARTIST_CELL, <COPYRIGHT_CELL
field_start:        .byte TITLE_OFFSET, ARTIST_OFFSET, COPYRIGHT_OFFSET
field_columns:      .byte TITLE_COLUMNS, ARTIST_COLUMNS, COPYRIGHT_COLUMNS
channel_cell_high:  .byte >PULSE1_CELL, >PULSE2_CELL, >TRIANGLE_CELL, >NOISE_CELL
channel_cell_low:   .byte <PULSE1_CELL, <PULSE2_CELL, <TRIANGLE_CELL, <NOISE_CELL
marker_tiles:       .byte PULSE1_PIN_TILE, PULSE2_PIN_TILE, TRIANGLE_PIN_TILE
marker_palettes:    .byte PULSE1_PIN_PALETTE, PULSE2_PIN_PALETTE, TRIANGLE_PIN_PALETTE

.segment "VECTORS"

    .word nmi
    .word reset
    .word irq

.assert RAM_PAGES = 8, error, "the clearing loop spells out one store per page of memory"
.assert WAVE_CELLS = 2 * 2, error, "a wave fills two periods of two cells"
.assert BUFFER_SIZE <= PAGE_SIZE, error, "the composed cells fit one page"
.assert PLAYED_OFFSET + CLOCK_DIGITS + 1 = TRANSPORT_CELLS, error, "the time closes the transport run"
.assert PROGRESS_PIXELS = PROGRESS_CELLS * PROGRESS_STEPS, error, "the progress bar spans the pixels the exporter fills"
.assert MARKER_SLOTS = 3, error, "a marker stands for each tone channel"
