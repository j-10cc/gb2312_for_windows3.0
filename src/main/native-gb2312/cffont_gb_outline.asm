bits 16
org 0

; Replacement for CFFONT.FOD segment 17:0000. One WORD arg, far caller
; cleans stack. Keep the original 2000-207F half-width identity range.
push bp
mov bp, sp
push bx
mov ax, [bp+6]
cmp ax, 2000h
jb gb
cmp ax, 207Fh
ja gb
sub ax, 2000h
inc ax
jmp done
gb:
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
add ax, 5000
jmp done
invalid:
xor ax, ax
done:
xor dx, dx
pop bx
pop bp
retf
