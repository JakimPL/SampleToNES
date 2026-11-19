PPU_CONTROL             = $2000
PPU_MASK                = $2001
PPU_STATUS              = $2002
SPRITE_ADDRESS          = $2003
PPU_SCROLL              = $2005
PPU_ADDRESS             = $2006
PPU_DATA                = $2007
SPRITE_TRANSFER         = $4014
CONTROLLER_PORT         = $4016

NMI_ENABLED             = $80
SPRITES_IN_SECOND_TABLE = $08
VIDEO_OFF               = $00
BACKGROUND_SHOWN        = $08
SPRITES_SHOWN           = $10
LEFT_EDGE_SHOWN         = $06
FRAME_CONTROL           = NMI_ENABLED | SPRITES_IN_SECOND_TABLE
FRAME_MASK              = BACKGROUND_SHOWN | SPRITES_SHOWN | LEFT_EDGE_SHOWN

PALETTE_START           = $3F00
PALETTE_SIZE            = $20

RAM_START               = $0000
RAM_PAGES               = 8
PAGE_SIZE               = $0100
STACK_TOP               = $FF
SPRITE_PAGE             = $0200
SPRITE_COUNT            = 64
SPRITE_BYTES            = 4
BUFFER                  = $0300
SCREEN_WINDOW           = $0400

CONTROLLER_STROBE       = $01
CONTROLLER_RELEASE      = $00
BUTTON_COUNT            = 8
BUTTON_SELECT           = $20
BUTTON_START            = $10

PULSE_MUTED             = $30
TRIANGLE_MUTED          = $80
