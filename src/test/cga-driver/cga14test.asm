; 8086 real-mode hardware test for CHCGA14.FNT. Assemble with:
;   nasm -f bin cga14test.asm -o CGA14T.COM
; Run in the directory containing CHCGA14.FNT, then press any key to exit.
; This exercises the same Big5 lookup and CGA mode 06h pixel path intended
; for the future Windows 3.0 DISPLAY driver. It is a DOS diagnostic, not a DRV.

cpu 8086
bits 16
org 100h

start:
    cld
    push cs
    pop ds
    cmp byte [82h], '/'
    jne .no_dump
    cmp byte [83h], 'D'
    jne .no_dump
    mov byte [dump_mode], 1
.no_dump:
    mov ax, 3d00h
    mov dx, font_name
    int 21h
    jc open_failed
    mov [font_handle], ax
    mov bx, ax
    mov ah, 3fh
    mov cx, 24
    mov dx, header_buffer
    int 21h
    jc font_invalid
    cmp ax, 24
    jne font_invalid
    cmp byte [header_buffer], 'C'
    jne font_invalid
    cmp byte [header_buffer+1], 'H'
    jne font_invalid
    cmp byte [header_buffer+2], '1'
    jne font_invalid
    cmp byte [header_buffer+3], '4'
    jne font_invalid
    cmp byte [header_buffer+4], 1
    jne font_invalid
    cmp byte [header_buffer+5], 14
    jne font_invalid
    cmp byte [header_buffer+6], 14
    jne font_invalid
    cmp byte [header_buffer+7], 7
    jne font_invalid
    cmp word [header_buffer+8], 19782
    jne font_invalid
    cmp word [header_buffer+10], 28
    jne font_invalid
    cmp word [header_buffer+12], 24
    jne font_invalid
    cmp word [header_buffer+14], 0
    jne font_invalid
    cmp word [header_buffer+16], 1816
    jne font_invalid
    cmp word [header_buffer+18], 0
    jne font_invalid

    mov ax, 0006h             ; CGA 640x200 monochrome
    int 10h
    push cs
    pop ds
    cld
    mov word [pen_x], 8
    mov word [pen_y], 24
    mov si, sample

.next_character:
    lodsb
    test al, al
    jz .done
    cmp al, 13
    je .new_line
    cmp al, 80h
    jb .ascii

    mov [lead_byte], al
    lodsb
    mov [trail_byte], al
    push si
    call load_dbcs
    jc .skip_dbcs
    mov byte [glyph_width], 14
    call draw_glyph
.skip_dbcs:
    pop si
    add word [pen_x], 14
    jmp .next_character

.ascii:
    push si
    xor ah, ah
    mov bx, 14
    mul bx                  ; AX = ASCII code * 14
    add ax, 24             ; font header length
    xor cx, cx
    mov dx, ax
    call seek_and_read_ascii
    jc .skip_ascii
    mov byte [glyph_width], 7
    call draw_glyph
.skip_ascii:
    pop si
    add word [pen_x], 7
    jmp .next_character

.new_line:
    mov word [pen_x], 8
    add word [pen_y], 28
    jmp .next_character

.done:
    cmp byte [dump_mode], 0
    je .wait_for_key
    call dump_screen
    jmp .restore
.wait_for_key:
    xor ah, ah
    int 16h
.restore:
    push cs
    pop ds
    mov ax, 0003h
    int 10h
    push cs
    pop ds
    mov bx, [font_handle]
    mov ah, 3eh
    int 21h
    mov ax, 4c00h
    int 21h

open_failed:
    mov ah, 09h
    mov dx, error_message
    int 21h
    mov ax, 4c01h
    int 21h

font_invalid:
    mov bx, [font_handle]
    mov ah, 3eh
    int 21h
    mov ah, 09h
    mov dx, invalid_message
    int 21h
    mov ax, 4c02h
    int 21h

; /D diagnostic writes raw CGA B800:0000 memory to CGA14.SCR.
dump_screen:
    xor cx, cx
    mov dx, dump_name
    mov ah, 3ch
    int 21h
    jc .done
    mov [dump_handle], ax
    mov bx, ax
    mov ax, 0b800h
    mov ds, ax
    xor dx, dx
    mov cx, 16384
    mov ah, 40h
    int 21h
    push cs
    pop ds
    mov bx, [dump_handle]
    mov ah, 3eh
    int 21h
.done:
    ret

; Big5 lead 81h-FEh, trails 40h-7Eh or A1h-FEh.
; Returns CF=0 and a 28-byte buffer for a valid code.
load_dbcs:
    mov al, [lead_byte]
    cmp al, 81h
    jb .invalid
    cmp al, 0feh
    ja .invalid
    sub al, 81h
    xor ah, ah
    mov bx, 157
    mul bx
    mov bx, ax
    mov al, [trail_byte]
    cmp al, 40h
    jb .invalid
    cmp al, 7eh
    jbe .low_trail
    cmp al, 0a1h
    jb .invalid
    cmp al, 0feh
    ja .invalid
    sub al, 0a1h
    add al, 63
    jmp .have_trail
.low_trail:
    sub al, 40h
.have_trail:
    xor ah, ah
    add ax, bx              ; slot within 19782 glyphs
    mov bx, 28
    mul bx                  ; DX:AX = byte offset (32-bit)
    add ax, 1816            ; 24-byte header + 128*14 ASCII bytes
    adc dx, 0
    mov cx, dx
    mov dx, ax
    mov si, 28
    call seek_and_read
    ret
.invalid:
    stc
    ret

seek_and_read_ascii:
    mov si, 14
seek_and_read:
    mov bx, [font_handle]
    mov ax, 4200h           ; DOS seek from beginning, CX:DX offset
    int 21h
    jc .failed
    mov ah, 3fh             ; DOS read glyph into 28-byte buffer
    mov cx, si
    mov dx, glyph_buffer
    int 21h
    jc .failed
    cmp ax, si
    jne .failed
    clc
    ret
.failed:
    stc
    ret

; Plot a 7x14 or 14x14 glyph at pen_x,pen_y into CGA mode 06h B800 memory.
; Physical row address = (y/2)*80 + (y mod 2)*8192.
draw_glyph:
    mov ax, 0b800h
    mov es, ax
    mov byte [row_number], 0
.row:
    xor ah, ah
    mov al, [row_number]
    cmp al, 14
    jae .finished
    cmp byte [glyph_width], 7
    je .ascii_row
    shl ax, 1
    mov si, glyph_buffer
    add si, ax
    mov ah, [si]
    mov al, [si+1]
    jmp .row_ready
.ascii_row:
    mov si, glyph_buffer
    add si, ax
    mov ah, [si]
    xor al, al
.row_ready:
    mov [glyph_bits], ax
    mov byte [column_number], 0
.column:
    mov al, [column_number]
    cmp al, [glyph_width]
    jae .next_row
    xor ch, ch
    mov cl, al
    mov dx, 8000h
    shr dx, cl
    test [glyph_bits], dx
    jz .next_column

    mov ax, [pen_y]
    xor bx, bx
    mov bl, [row_number]
    add ax, bx
    mov bx, ax
    and bx, 1
    shr ax, 1
    mov cx, 80
    mul cx
    test bx, bx
    jz .even_row
    add ax, 8192
.even_row:
    mov di, ax
    mov ax, [pen_x]
    xor bx, bx
    mov bl, [column_number]
    add ax, bx
    mov bx, ax
    shr bx, 1
    shr bx, 1
    shr bx, 1
    add di, bx
    and al, 7
    mov cl, al
    mov al, 80h
    shr al, cl
    or [es:di], al
.next_column:
    inc byte [column_number]
    jmp .column
.next_row:
    inc byte [row_number]
    jmp .row
.finished:
    ret

font_name db 'CHCGA14.FNT',0
dump_name db 'CGA14.SCR',0
error_message db 'CHCGA14.FNT not found in current directory.$'
invalid_message db 'CHCGA14.FNT has an unsupported format.$'
sample db 'CHCGA 14x14 BIG5 CGA TEST',13
       db 0c1h,063h,0c5h,0e9h,0a4h,0a4h,0a4h,0e5h,0c5h,0e3h,0a5h,0dch,0b4h,0fah,0b8h,0d5h,13
       db 0c0h,0c9h,0aeh,0d7h,0bah,0deh,0b2h,07ah,0adh,0fbh,0

font_handle dw 0
dump_handle dw 0
dump_mode db 0
header_buffer times 24 db 0
pen_x dw 0
pen_y dw 0
lead_byte db 0
trail_byte db 0
glyph_width db 0
row_number db 0
column_number db 0
glyph_bits dw 0
glyph_buffer times 28 db 0
