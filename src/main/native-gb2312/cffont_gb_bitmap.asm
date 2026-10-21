bits 16
org 0

; Replacement for CFFONT.FOD segment 10:0001. Pascal far call, one WORD arg.
; Return B5Q full-width image index 275 + GB2312 94-column ordinal.
push bp
mov bp, sp
push bx
mov ax, [bp+6]
mov bl, ah
mov bh, al
cmp bl, 0A1h
jb invalid
cmp bl, 0F7h
ja invalid
cmp bh, 0A1h
jb invalid
cmp bh, 0FEh
ja invalid
sub bl, 0A1h
sub bh, 0A1h
mov al, bl
xor ah, ah
mov cx, 94
mul cx
mov bl, bh
xor bh, bh
add ax, bx
add ax, 275
jmp done
invalid:
mov ax, 0FFFFh
done:
pop bx
pop bp
retf 2
