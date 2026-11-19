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
.import deck_palette
.import deck_screen
.import deck_labels
.import deck_waves
.import note_names

TRANSPORT_RUN       = 5
PROGRESS_RUN        = 4
FIRST_RUN           = 2
SECOND_RUN          = 0
RUN_COUNT           = 6

TRANSPORT_SLOT      = RUN_COUNT - 1
PROGRESS_SLOT       = TRANSPORT_SLOT + TRANSPORT_CELLS
FIRST_SLOT          = PROGRESS_SLOT + PROGRESS_CELLS + WAVE_CELLS
SECOND_SLOT         = FIRST_SLOT + CHANNEL_CELLS + WAVE_CELLS
BUFFER_SIZE         = SECOND_SLOT + CHANNEL_CELLS
BOTTOM_ROW          = -WAVE_CELLS

WAVE_TABLE_SIZE     = 4
NOTE_CELLS          = 3
FIELD_COUNT         = 5
TOTAL_SECONDS_CELL  = TOTAL_CELL + CLOCK_DIGITS / 2 + 1
METER_STEPS_PER_TILE = 2
MAX_LEVEL           = 15
LEVEL_MASK          = $0F
DUTY_SHIFT          = 6
DUTY_WAVES          = 3 * WAVE_TABLE_SIZE
NOISE_PERIOD_MASK   = $0F
SHIMMER_BIT         = $02
CLOCK_STATE_SIZE    = FRAME_COUNT_SIZE + CLOCK_DIGITS + SECOND_FRACTION_SIZE + PROGRESS_SIZE

SPRITE_Y            = 0
SPRITE_TILE         = 1
SPRITE_ATTRIBUTES   = 2
SPRITE_X            = 3

.segment "PLAYERZP": zeropage

; A restart clears the driver's memory and these together, so they open the shell's page zero
; right behind the driver's.
ended:              .res 1
played_frames:      .res 1
remaining:          .res FRAME_COUNT_SIZE
digits:             .res CLOCK_DIGITS
second_fraction:    .res SECOND_FRACTION_SIZE
progress:           .res PROGRESS_SIZE
restarted_end:
wave:               .res 1
frame_ready:        .res 1
paused:             .res 1
buttons:            .res 1
pressed:            .res 1
run:                .res 1
channel:            .res 1
slot:               .res 1
count:              .res 1
step:               .res 1
level:              .res 1
meter_none:         .res 1
note_tiles:         .res NOTE_CELLS
run_high:           .res RUN_COUNT
run_low:            .res RUN_COUNT

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
; the video chip takes to warm up. The screen is drawn with rendering off: the palette, the packed
; screen, the program block's text and times, and the label sprites. The first frame interrupt
; finds the song started and its first readings composed.
;
; The packed screen is a run of tokens, each a header stating a length above its lowest bit. A
; literal's bytes follow its header; a copy names the place in a 256-byte window of the bytes
; written so far it reads from. Every byte written lands in the window at the count of bytes
; written so far, kept in X, and a zero header ends the screen.
reset:
    sei
    ldx #$00
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

    lda #>PALETTE_START
    sta PPU_ADDRESS
    stx PPU_ADDRESS
@palette:
    lda deck_palette,x
    sta PPU_DATA
    inx
    cpx #PALETTE_SIZE
    bne @palette

    ldx #$00
    ldy #$00
    lda #>NAMETABLE_START
    sta PPU_ADDRESS
    stx PPU_ADDRESS
@header:
    lda deck_screen,y
    beq @unpacked
    iny
    lsr a
    sta count
    bcs @copy
@literal:
    lda deck_screen,y
    iny
    jsr put_packed
    dec count
    bne @literal
    beq @header
@copy:
    lda deck_screen,y
    iny
    sty step
    tay
@repeat:
    lda SCREEN_WINDOW,y
    jsr put_packed
    iny
    dec count
    bne @repeat
    ldy step
    bne @header
@unpacked:

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
    clc
    adc field_tiles,y
    sta PPU_DATA
    inx
    dec count
    bne @character
    iny
    cpy #FIELD_COUNT
    bne @field

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

    lda #>TRANSPORT_CELL
    sta run_high + TRANSPORT_RUN
    .if >PROGRESS_CELL <> >TRANSPORT_CELL
    lda #>PROGRESS_CELL
    .endif
    sta run_high + PROGRESS_RUN
    lda #<TRANSPORT_CELL
    sta run_low + TRANSPORT_RUN
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

; Waits for each frame, answers the controller and composes what the next frame writes. The
; controller is read through a ring: the strobe's bit is rolled in first and comes out into the
; carry with the eighth button. START pauses and resumes, SELECT starts the song over. A pause
; silences the channels, and the driver sounds them again with the first tick it writes.
main:
    lda frame_ready
    beq main
    lda #$00
    sta frame_ready
    ldx buttons
    lda #CONTROLLER_STROBE
    sta CONTROLLER_PORT
    sta buttons
    lsr a
    sta CONTROLLER_PORT
@reading:
    lda CONTROLLER_PORT
    lsr a
    rol buttons
    bcc @reading
    txa
    eor #$FF
    and buttons
    sta pressed
    and #BUTTON_START
    beq @select
    lda paused
    eor #$01
    sta paused
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
    jsr restart
@answered:
    jsr compose
    jmp main

; Sends the sprites, writes the composed runs of cells and plays the song on. Every frame does the
; same work in the same cycles, so the driver is entered at the same moment of each frame. The runs
; are written from the last to the first, which is the order their cells stand in the buffer.
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
    ldx #RUN_COUNT - 1
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
    dec run
    bpl @run

    lda #$00
    sta PPU_SCROLL
    sta PPU_SCROLL
    lda #FRAME_CONTROL
    sta PPU_CONTROL
    lda paused
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

; Starts the song over from a cleared driver, as a cartridge just switched on would. The pause
; holds the frame interrupt off the driver while its memory is cleared, and starting the song
; takes the pause off.
restart:
    lda #$01
    sta paused
    lda #$00
    tax
@clearing:
    sta __ZEROPAGE_RUN__,x
    inx
    cpx #<restarted_end
    bne @clearing
start_song:
    jsr nsf_init
    ldx #FRAME_COUNT_SIZE - 1
@frames:
    lda program_block + TOTAL_FRAMES_OFFSET,x
    sta remaining,x
    dex
    bpl @frames
    inx
    stx paused
    rts

; Moves the clock and the progress bar on by a frame. The frame count is stored negated and counts
; up to zero. Once it gets there, a song that repeats takes up the clock where its loop begins, and
; one that ends holds it.
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
    clc
    ldx #<-PROGRESS_SIZE
@progress:
    lda progress + PROGRESS_SIZE,x
    adc program_block + PROGRESS_STEP_OFFSET + PROGRESS_SIZE - PAGE_SIZE,x
    sta progress + PROGRESS_SIZE,x
    inx
    bne @progress
@counting:
    inc remaining,x
    bne @held
    inx
    cpx #FRAME_COUNT_SIZE
    bne @counting
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

; Writes a byte of the packed screen to video memory and into the window copies read from.
put_packed:
    sta PPU_DATA
    sta SCREEN_WINDOW,x
    inx
    rts

; Composes what the next frame writes: two of the four channels, the pulses on one frame and the
; triangle and the noise on the next, then the playing state and the time, the progress bar and the
; markers. The gap and the colon of the transport run take the same tiles on every frame.
compose:
    lda channel
    eor #$02
    and #$02
    sta channel
    ldx #FIRST_SLOT
    ldy #FIRST_RUN
    jsr compose_channel
    inc channel
    ldx #SECOND_SLOT
    ldy #SECOND_RUN
    jsr compose_channel

compose_transport:
    lda #TRANSPORT_GAP_TILE
    sta BUFFER + TRANSPORT_SLOT + 1
    lda #COLON_TILE
    sta BUFFER + TRANSPORT_SLOT + PLAYED_OFFSET + CLOCK_DIGITS / 2
    lda paused
    ldx ended
    beq @stated
    lda #STOP_TILE - PLAY_TILE
@stated:
    clc
    adc #PLAY_TILE
    sta BUFFER + TRANSPORT_SLOT
    ldx #CLOCK_DIGITS - 1
@digit:
    lda digits,x
    adc #DIGIT_ZERO_TILE
    ldy digit_cells,x
    sta BUFFER,y
    dex
    bpl @digit

; Fills the progress bar a cell at a time from the pixels left in Y: a full cell takes eight of
; them, and the cell they run out in shows what is left.
compose_progress:
    ldy progress + PROGRESS_SIZE - 1
    ldx #<-PROGRESS_CELLS
@cell:
    cpy #PROGRESS_STEPS
    bcc @partial
    tya
    sbc #PROGRESS_STEPS
    tay
    lda #PROGRESS_EMPTY_TILE + PROGRESS_STEPS
    bne @put
@partial:
    tya
    adc #PROGRESS_EMPTY_TILE
    ldy #$00
@put:
    sta BUFFER + PROGRESS_SLOT + PROGRESS_CELLS - PAGE_SIZE,x
    inx
    bne @cell

; Stands a marker over the key each sounding tone channel plays, and hides the others. X holds the
; marker's sprite and Y a pulse's control plane.
compose_markers:
    ldx #0 * SPRITE_BYTES
    ldy #PULSE1_CONTROL_PLANE
    jsr pulse_marker
    ldx #1 * SPRITE_BYTES
    ldy #PULSE2_CONTROL_PLANE
    jsr pulse_marker
    ldx #2 * SPRITE_BYTES
    lda plane_state + TRIANGLE_VALUE_PLANE + PLANE_VALUE
    and #PITCH_INDEX_MASK
    cmp #SILENT_PITCH_INDEX
    bne place_marker
    beq hide_marker

pulse_marker:
    lda plane_state + PLANE_VALUE,y
    and #LEVEL_MASK
    beq hide_marker
    lda plane_state + PLANE_STATE_SIZE + PLANE_VALUE,y
    and #PITCH_INDEX_MASK
place_marker:
    asl a
    adc #KEYBOARD_LEFT
    sta SPRITE_PAGE + SPRITE_X,x
    lda #LANE_TOP
    sta SPRITE_PAGE + SPRITE_Y,x
    lda marker_sprites + SPRITE_TILE,x
    sta SPRITE_PAGE + SPRITE_TILE,x
    lda marker_sprites + SPRITE_ATTRIBUTES,x
    sta SPRITE_PAGE + SPRITE_ATTRIBUTES,x
    rts

hide_marker:
    lda #HIDDEN_SPRITE_Y
    sta SPRITE_PAGE + SPRITE_Y,x
    lda #$00
    sta SPRITE_PAGE + SPRITE_TILE,x
    sta SPRITE_PAGE + SPRITE_ATTRIBUTES,x
    sta SPRITE_PAGE + SPRITE_X,x
    rts

; Composes the channel named in `channel` into the slot in X, pointing the runs from Y on at its two
; rows: one period of the wave twice over two rows, the gaps, the note and the meter, whose tiles
; hold two steps each and the last tile the fifteenth alone.
compose_channel:
    stx slot
    ldx channel
    lda channel_cell_low,x
    sta run_low,y
    ora #SCREEN_COLUMNS
    sta run_low + 1,y
    lda channel_cell_high,x
    sta run_high,y
    sta run_high + 1,y
    jsr gather

    ldx slot
    ldy wave
    lda deck_waves,y
    sta BUFFER,x
    sta BUFFER + 2,x
    lda deck_waves + 1,y
    sta BUFFER + 1,x
    sta BUFFER + 3,x
    lda deck_waves + 2,y
    sta BUFFER + BOTTOM_ROW,x
    sta BUFFER + BOTTOM_ROW + 2,x
    lda deck_waves + 3,y
    sta BUFFER + BOTTOM_ROW + 1,x
    sta BUFFER + BOTTOM_ROW + 3,x

    lda #CHANNEL_GAP_TILE
    .repeat NOTE_OFFSET - WAVE_CELLS, gap
    sta BUFFER + WAVE_CELLS + gap,x
    .endrepeat
    .repeat METER_OFFSET - NOTE_OFFSET - NOTE_CELLS, gap
    sta BUFFER + NOTE_OFFSET + NOTE_CELLS + gap,x
    .endrepeat

    lda note_tiles
    sta BUFFER + NOTE_OFFSET,x
    lda note_tiles + 1
    sta BUFFER + NOTE_OFFSET + 1,x
    lda note_tiles + 2
    sta BUFFER + NOTE_OFFSET + 2,x

    ldy channel
    lda meter_nones,y
    sta meter_none
    ldy level
    lda #METER_PAIRS
    sta count
@pair:
    lda meter_none
    cpy #$01
    bcc @put
    sbc #$01
    dey
    beq @put
    sbc #$01
    dey
@put:
    sta BUFFER + METER_OFFSET,x
    inx
    dec count
    bne @pair
    tya
    eor #$01
    sec
    adc meter_none
    sta BUFFER + METER_OFFSET,x
    rts

; Reads a pulse from its control plane, whose offset stands in X, and its value plane behind it.
gather_pulse:
    lda plane_state + PLANE_VALUE,x
    and #LEVEL_MASK
    sta level
    beq @resting
    lda plane_state + PLANE_VALUE,x
    .repeat DUTY_SHIFT - 2
    lsr a
    .endrepeat
    and #DUTY_WAVES
    sta wave
    lda plane_state + PLANE_STATE_SIZE + PLANE_VALUE,x
    and #PITCH_INDEX_MASK
    bpl name_pitch
@resting:
    lda #PULSE_REST_OFFSET
    sta wave
    bne name_rest

gather_triangle:
    lda #$00
    sta level
    lda plane_state + TRIANGLE_VALUE_PLANE + PLANE_VALUE
    and #PITCH_INDEX_MASK
    cmp #SILENT_PITCH_INDEX
    beq other_resting
    ldx #MAX_LEVEL
    stx level
    ldx #TRIANGLE_WAVE_OFFSET
    stx wave
    bne name_pitch

; Gathers the readings of the channel named in `channel`: its level, its wave and its note.
gather:
    ldx #PULSE1_CONTROL_PLANE
    lda channel
    beq gather_pulse
    ldx #PULSE2_CONTROL_PLANE
    lsr a
    beq gather_pulse
    bcc gather_triangle

; Reads the noise: its wave is the long or the short one, shimmering every two played frames, and
; its name is the hex digit of its period counted down from the last, then one suffix.
gather_noise:
    lda plane_state + NOISE_CONTROL_PLANE + PLANE_VALUE
    and #LEVEL_MASK
    sta level
    beq other_resting
    lda plane_state + NOISE_VALUE_PLANE + PLANE_VALUE
    asl a
    lda played_frames
    and #SHIMMER_BIT
    bcc @long
    adc #NOISE_SHORT_OFFSET - 1
@long:
    adc #NOISE_WAVES_OFFSET
    sta wave
    lda plane_state + NOISE_VALUE_PLANE + PLANE_VALUE
    and #NOISE_PERIOD_MASK
    eor #NOISE_PERIOD_MASK
    cmp #DIGIT_BASE
    bcc @digit
    adc #HEX_TEN_TILE - OCTAVE_ZERO_TILE - DIGIT_BASE - 1
@digit:
    adc #OCTAVE_ZERO_TILE
    sta note_tiles
    lda #NOISE_SUFFIX_TILE
    sta note_tiles + 1
    lda #NOISE_SUFFIX_END_TILE
    sta note_tiles + 2
    rts

other_resting:
    lda #OTHER_REST_OFFSET
    sta wave
name_rest:
    lda #REST_TILE
    sta note_tiles
    sta note_tiles + 1
    sta note_tiles + 2
    rts

; Names the pitch index in A: its note within the octave, then the octave's digit, counted in Y.
name_pitch:
    ldy #OCTAVE_ZERO_TILE - 1
    sec
@octave:
    iny
    sbc #NOTES_PER_OCTAVE
    bcs @octave
    adc #NOTES_PER_OCTAVE
    asl a
    tax
    lda note_names,x
    sta note_tiles
    lda note_names + 1,x
    sta note_tiles + 1
    sty note_tiles + 2
    rts

run_lengths:        .byte CHANNEL_CELLS, WAVE_CELLS, CHANNEL_CELLS, WAVE_CELLS, PROGRESS_CELLS, TRANSPORT_CELLS
digit_cells:        .byte TRANSPORT_SLOT + PLAYED_OFFSET, TRANSPORT_SLOT + PLAYED_OFFSET + 1
                    .byte TRANSPORT_SLOT + PLAYED_OFFSET + 3, TRANSPORT_SLOT + PLAYED_OFFSET + 4
digit_limits:       .byte DIGIT_BASE, DIGIT_BASE, 6, DIGIT_BASE
field_high:         .byte >TITLE_CELL, >ARTIST_CELL, >COPYRIGHT_CELL, >TOTAL_CELL, >TOTAL_SECONDS_CELL
field_low:          .byte <TITLE_CELL, <ARTIST_CELL, <COPYRIGHT_CELL, <TOTAL_CELL, <TOTAL_SECONDS_CELL
field_start:        .byte TITLE_OFFSET, ARTIST_OFFSET, COPYRIGHT_OFFSET
                    .byte TOTAL_TIME_OFFSET, TOTAL_TIME_OFFSET + CLOCK_DIGITS / 2
field_columns:      .byte TITLE_COLUMNS, ARTIST_COLUMNS, COPYRIGHT_COLUMNS, CLOCK_DIGITS / 2, CLOCK_DIGITS / 2
field_tiles:        .byte 0, 0, 0, DIGIT_ZERO_TILE, DIGIT_ZERO_TILE
channel_cell_high:  .byte >PULSE1_CELL, >PULSE2_CELL, >TRIANGLE_CELL, >NOISE_CELL
channel_cell_low:   .byte <PULSE1_CELL, <PULSE2_CELL, <TRIANGLE_CELL, <NOISE_CELL
meter_nones:        .byte PULSE_METER_NONE, PULSE_METER_NONE, OTHER_METER_NONE, OTHER_METER_NONE
; Each marker's tile and palette stand at its sprite's offset, so one index reads both.
marker_sprites = * - SPRITE_TILE
                    .byte PULSE1_PIN_TILE, PULSE1_PIN_PALETTE, 0, 0
                    .byte PULSE2_PIN_TILE, PULSE2_PIN_PALETTE, 0, 0
                    .byte TRIANGLE_PIN_TILE, TRIANGLE_PIN_PALETTE

.segment "VECTORS"

    .word nmi
    .word reset
    .word irq

.assert RAM_PAGES = 8, error, "the clearing loop spells out one store per page of memory"
.assert WAVE_CELLS = 2 * 2, error, "a wave fills two periods of two cells"
.assert BUFFER_SIZE <= PAGE_SIZE, error, "the composed cells fit one page"
.assert PLAYED_OFFSET + CLOCK_DIGITS + 1 = TRANSPORT_CELLS, error, "the time closes the transport run"
.assert PLAYED_OFFSET = 2, error, "one gap stands between the playing state and the time"
.assert PROGRESS_PIXELS = PROGRESS_CELLS * PROGRESS_STEPS, error, "the progress bar spans the pixels the exporter fills"
.assert MARKER_SLOTS = 3, error, "a marker stands for each tone channel"
.assert METER_STEPS_PER_TILE = 2, error, "a meter tile holds two steps"
.assert METER_PAIRS * METER_STEPS_PER_TILE + 1 = MAX_LEVEL, error, "the last meter tile holds the fifteenth step"
.assert PULSE_METER_LAST_LIT = PULSE_METER_NONE + 1, error, "a pulse's last lit meter tile follows its empty one"
.assert OTHER_METER_LAST_LIT = OTHER_METER_NONE + 1, error, "the other channels' last lit meter tile follows their empty one"
.assert PAUSE_TILE = PLAY_TILE + 1, error, "the pause tile follows the play tile"
.assert DIGIT_ZERO_TILE + DIGIT_BASE <= $100, error, "a digit's tile is reached without a carry"
.assert PULSE_WAVES_OFFSET = 0, error, "a duty's wave stands at its duty times the size of a wave"
.assert SHIMMER_BIT = NOISE_SHIMMER_OFFSET, error, "the shimmer bit steps over to the shimmering noise wave"
.assert (PULSE1_CELL | PULSE2_CELL | TRIANGLE_CELL | NOISE_CELL) & SCREEN_COLUMNS = 0, error, "a channel's wave starts on an even row"
.assert PITCH_INDEX_MASK < $80, error, "doubling a pitch index leaves the carry clear"
.assert CONTROLLER_STROBE = 1 && CONTROLLER_RELEASE = 0, error, "the strobe bit rings once through the eight buttons"
.assert __ZEROPAGE_RUN__ = 0, lderror, "a restart clears page zero from the driver's memory up to the clock"
