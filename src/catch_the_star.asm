; Catch the Star -- a first Commodore 64 game, written for ACME.
; Build: acme -f cbm -o build/catch-the-star.prg src/catch_the_star.asm
; A semicolon starts a comment, like # in Python.
!cpu 6510

SCREEN       = $0400             ; 40 columns * 25 rows of character numbers
COLOR        = $d800             ; one color byte per screen position
JOY2         = $dc00             ; CIA 1 port A: joystick port 2
JOY2_DDR     = $dc02             ; 0 bits mean input pins
PTR          = $fb               ; $fb/$fc form a 16-bit address (zero page)
PLAYER_CHAR  = 0                 ; screen code for @ in uppercase character ROM
STAR_CHAR    = 42                ; screen code for *
TOP_ROW      = 3                 ; rows 0, 1, 2 belong to the heading
BOTTOM_ROW   = 23                ; row 24 is the bottom border
MOVE_FRAMES  = 5                 ; one move per 5 frames: PAL 10 / NTSC 12 per sec
SCORE_SCREEN = SCREEN + (title_score - title)

; A PRG begins with a load address, added by ACME's '-f cbm' option.
; These bytes describe the BASIC line: 10 SYS2064
* = $0801
    !word basic_end             ; pointer to the next BASIC line
    !word 10                    ; BASIC line number
    !byte $9e                   ; token for SYS
    !text "2064"                ; decimal $0810: start of our machine code
    !byte 0                     ; end of this line
basic_end:
    !word 0                     ; no more BASIC lines
    !fill $0810 - *, 0

start:
    sei                         ; pause normal IRQs; we handle timing ourselves
    cld                         ; use ordinary binary arithmetic, not decimal mode

    ; Select VIC bank 0 and the usual $0400 screen / uppercase ROM font.
    lda $dd02
    ora #3                      ; like value | 3 in Python
    sta $dd02                   ; make VIC bank-select pins outputs
    lda $dd00
    ora #3
    sta $dd00
    lda #$14
    sta $d018
    lda #$1b                    ; normal 25-row text mode, screen on
    sta $d011
    lda #$08                    ; normal 40-column text mode
    sta $d016
    lda #0
    sta $d015                   ; hide sprites
    sta $d021                   ; black background
    sta JOY2_DDR                ; joystick port A pins are all inputs
    lda #6
    sta $d020                   ; blue border

    ; Fill exactly 1000 screen/color cells. The final 256-byte block overlaps
    ; the previous one slightly, avoiding writes past the screen into memory.
    ldx #0                      ; X is a tiny loop counter (0..255)
clear_screen:
    lda #32                     ; space character
    sta SCREEN,x
    sta SCREEN+256,x
    sta SCREEN+512,x
    sta SCREEN+744,x
    lda #1                      ; white
    sta COLOR,x
    sta COLOR+256,x
    sta COLOR+512,x
    sta COLOR+744,x
    inx                         ; like x = (x + 1) % 256
    bne clear_screen            ; loop until X wraps back to zero

    ldx #0
copy_title:
    lda title,x                 ; like title[x]
    sta SCREEN,x
    inx
    cpx #title_end-title
    bne copy_title
    ldx #0
copy_help:
    lda help_text,x
    sta SCREEN+40,x
    inx
    cpx #help_end-help_text
    bne copy_help
    ldx #39
draw_borders:
    lda #45                     ; hyphen screen code
    sta SCREEN+80,x
    sta SCREEN+960,x
    dex                         ; like x -= 1
    bpl draw_borders            ; continue through X=0; stop at X=$ff (-1)

    ; Initialize every mutable variable so RUN also starts a fresh game.
    lda #10
    sta player_x
    lda #12
    sta player_y
    lda #0
    sta score_digits
    sta score_digits+1
    sta score_digits+2
    sta score_digits+3
    sta joy_state
    lda #MOVE_FRAMES
    sta frames_left
    lda $dc04                   ; timer + raster provide a variable starting seed
    eor $d012                   ; EOR is Python's ^ (exclusive OR)
    ora #1                      ; the random generator must never start at zero
    sta random_state
    jsr show_score
    jsr new_star
    jsr draw_star
    jsr draw_player

main_loop:
    jsr wait_frame              ; JSR is like calling a Python function
    dec frames_left
    bne main_loop
    lda #MOVE_FRAMES
    sta frames_left
    jsr move_player
    jmp main_loop               ; like while True: ...

; Wait for raster line 250 once. $d011 bit 7 excludes lines 256..311 on PAL.
; Waiting to leave the line prevents counting the same frame more than once.
wait_frame:
    lda $d011
    bmi wait_frame
    lda $d012
    cmp #250
    bne wait_frame
wait_leave:
    lda $d012
    cmp #250
    beq wait_leave
    rts                         ; like returning from a function

move_player:
    ; Erase the old @ before changing its coordinates.
    ldx player_y
    ldy player_x
    lda #32
    jsr plot
    lda JOY2
    sta joy_state               ; read once so all directions use one snapshot

    ; Joystick bits are ACTIVE LOW: a pressed direction is 0, not 1.
    ; AND #1 is like joy_state & 1; BNE skips when the direction is released.
    lda joy_state
    and #1                      ; bit 0 = up
    bne check_down
    lda player_y
    cmp #TOP_ROW                ; CMP sets flags, like the comparison in an if
    beq check_down
    dec player_y
check_down:
    lda joy_state
    and #2                      ; bit 1 = down
    bne check_left
    lda player_y
    cmp #BOTTOM_ROW
    beq check_left
    inc player_y
check_left:
    lda joy_state
    and #4                      ; bit 2 = left
    bne check_right
    lda player_x
    beq check_right             ; already at column 0
    dec player_x
check_right:
    lda joy_state
    and #8                      ; bit 3 = right; bit 4 (fire) is unused
    bne check_catch
    lda player_x
    cmp #39
    beq check_catch
    inc player_x

check_catch:
    lda player_x
    cmp star_x
    bne redraw_player
    lda player_y
    cmp star_y
    bne redraw_player
    ; Both coordinates match: score += 1, then relocate the star.
    jsr increment_score
    jsr show_score
    jsr new_star
    jsr draw_star
redraw_player:
    jmp draw_player             ; draw_player's RTS returns to our caller

draw_player:
    ldx player_y
    ldy player_x
    lda #PLAYER_CHAR
    jsr plot
    lda #1                      ; white @
    jmp plot_color
draw_star:
    ldx star_y
    ldy star_x
    lda #STAR_CHAR
    jsr plot
    lda #7                      ; yellow *
    jmp plot_color

; Input: A = character, X = row, Y = column.
; A row lookup table avoids multiplication: address = $0400 + row*40 + column.
plot:
    pha                         ; save A on the stack, like a temporary variable
    lda row_low,x
    sta PTR
    lda row_high,x
    sta PTR+1
    pla                         ; restore A
    sta (PTR),y                 ; like memory[row_address + column] = character
    rts
; Call just after plot: A = color; PTR and Y still point to the same cell.
plot_color:
    pha
    lda PTR+1
    clc                         ; clear carry before adding (no extra +1)
    adc #$d4                    ; $0400 + $d400 = $d800, the color RAM
    sta PTR+1
    pla
    sta (PTR),y
    rts

; Store four separate decimal digits, like a Python list [0, 0, 0, 0].
; Carry to the left at 10; after 9999 the display wraps to 0000.
increment_score:
    ldx #3
next_digit:
    inc score_digits,x
    lda score_digits,x
    cmp #10
    bne score_done
    lda #0
    sta score_digits,x
    dex
    bpl next_digit
score_done:
    rts
show_score:
    ldx #0
score_loop:
    lda score_digits,x
    clc
    adc #48                     ; convert 0..9 to screen codes for '0'..'9'
    sta SCORE_SCREEN,x
    inx
    cpx #4
    bne score_loop
    rts

; An 8-bit LFSR: shift, then conditionally XOR a feedback value.
; It cycles through 255 nonzero states; this is for a game, not security.
random_byte:
    lda random_state
    asl                         ; like a = (a << 1) & 255; old bit 7 goes to carry
    bcc random_ready
    eor #$1d
random_ready:
    sta random_state
    rts
new_star:
    jsr random_byte
    and #63                     ; candidate column 0..63
    cmp #40
    bcs new_star                ; reject 40..63 instead of biasing with modulo
    sta star_x
new_star_row:
    jsr random_byte
    and #31                     ; candidate row offset 0..31
    cmp #21
    bcs new_star_row            ; only 21 playable rows
    clc
    adc #TOP_ROW
    sta star_y
    lda star_x
    cmp player_x
    bne star_ready
    lda star_y
    cmp player_y
    beq new_star                ; never hide the new star under the player
star_ready:
    rts

; With ACME's default text encoding, lowercase source letters under !scr become
; screen codes 1..26: UPPERCASE letters in the C64's uppercase/graphics font.
title:
    !scr "catch the star   score: "
title_score:
    !scr "0000"
title_end:
help_text:
    !scr "joystick port 2   you: @   star: *"
help_end:
row_low:
    !for row, 0, 24 { !byte <(SCREEN + row*40) }
row_high:
    !for row, 0, 24 { !byte >(SCREEN + row*40) }

player_x:     !byte 10
player_y:     !byte 12
star_x:       !byte 0
star_y:       !byte 0
joy_state:    !byte 0
frames_left:  !byte MOVE_FRAMES
random_state: !byte 1
score_digits: !byte 0, 0, 0, 0
