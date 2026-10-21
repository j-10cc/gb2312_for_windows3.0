; Real-mode CGA Big5 overlay for Windows 3.0 DDK STRBLT.ASM.
; One outer draw owns this static context. Reentrant draws use the DDK path
; without touching it, so nested callbacks cannot corrupt our pointers.

chinese_save_context proc near
    pushf
    push ax
    push si
    push ds
    cmp byte ptr cs:[co_busy],0
    jne co_save_done
    mov byte ptr cs:[co_busy],1
    mov cs:[co_owner_bp],bp
    mov byte ptr cs:[co_skip_base],0
    mov ax,count
    mov cs:[co_count],ax
    mov ax,x
    mov cs:[co_x],ax
    mov ax,y
    mov cs:[co_y],ax
    mov ax,lfd.font_height
    mov cs:[co_font_height],ax
    lds si,lp_device
    mov word ptr cs:[co_device],si
    mov word ptr cs:[co_device+2],ds
    pop ds
    push ds
    lds si,lp_string
    mov word ptr cs:[co_string],si
    mov word ptr cs:[co_string+2],ds
    pop ds
    push ds
    lds si,lp_draw_mode
    mov al,[si].TextColor.SPECIAL
    mov cs:[co_fg],al
    mov al,[si].bkColor.SPECIAL
    mov cs:[co_bg],al
    mov ax,[si].bkMode
    mov cs:[co_bk_mode],ax
    mov ax,[si].CharExtra
    mov cs:[co_char_extra],ax
    pop ds
    mov ax,off_lp_dx
    mov cs:[co_dx_off],ax
    mov ax,seg_lp_dx
    mov cs:[co_dx_seg],ax
co_save_done:
    pop si
    pop ax
    popf
    ret
chinese_save_context endp

chinese_finish proc near
    pushf
    push ax
    push bx
    push cx
    push dx
    push si
    push di
    push ds
    push es
    cmp byte ptr cs:[co_busy],0
    je co_finish_done
    cmp cs:[co_owner_bp],bp
    jne co_finish_done
    ; DOS handles are owned by the current Windows task's PSP. A handle
    ; cached across StrBlt calls can be reused for the next application's
    ; EXE, making its bytes look like random Chinese glyphs. Keep a font
    ; handle only for the duration of the owning draw call.
    mov bx,cs:[co_font_handle_main]
    mov word ptr cs:[co_font_handle_main],0FFFFh
    cmp bx,0FFFEh
    jae co_finish_small
    mov ah,3Eh
    int 21h
co_finish_small:
    mov bx,cs:[co_font_handle_small]
    mov word ptr cs:[co_font_handle_small],0FFFFh
    cmp bx,0FFFEh
    jae co_finish_medium
    mov ah,3Eh
    int 21h
co_finish_medium:
    mov bx,cs:[co_font_handle_medium]
    mov word ptr cs:[co_font_handle_medium],0FFFFh
    cmp bx,0FFFEh
    jae co_finish_release
    mov ah,3Eh
    int 21h
co_finish_release:
    mov byte ptr cs:[co_busy],0
co_finish_done:
    pop es
    pop ds
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop ax
    popf
    ret
chinese_finish endp

; Keep the base renderer for targets the overlay cannot address.
co_target_supported proc near
    push ax
    push bx
    push dx
    push si
    push ds
    lds si,dword ptr cs:[co_device]
    cmp word ptr [si].bmType,0
    jne co_target_early_yes
    cmp byte ptr [si].bmPlanes,1
    jne co_target_early_no
    cmp byte ptr [si].bmBitsPixel,1
    jne co_target_early_no
    mov ax,[si].bmWidth
    or ax,ax
    jz co_target_early_no
    cmp ax,4096
    ja co_target_early_no
    add ax,7
    shr ax,1
    shr ax,1
    shr ax,1
    mov bx,[si].bmWidthBytes
    or bx,bx
    jz co_target_early_no
    cmp ax,bx
    ja co_target_early_no
    mov ax,[si].bmHeight
    or ax,ax
    jz co_target_early_no
    cmp ax,32767
    ja co_target_early_no
    jmp co_target_format_valid
co_target_early_yes:
    jmp co_target_supported_yes
co_target_early_no:
    jmp co_target_supported_no
co_target_format_valid:
    cmp word ptr [si].bmSegmentIndex,0
    je co_target_small
    mov ax,[si].bmScanSegment
    or ax,ax
    jz co_target_supported_no
    mul bx
    or dx,dx
    jz co_huge_scan_under_64k
    ; A full 64 KiB segment is valid when the bitmap starts at offset zero.
    cmp dx,1
    jne co_target_supported_no
    or ax,ax
    jne co_target_supported_no
    cmp wptr [si].bmBits[0],0
    jne co_target_supported_no
    jmp co_huge_scan_valid
co_huge_scan_under_64k:
    add ax,wptr [si].bmBits[0]
    jc co_target_supported_no
co_huge_scan_valid:
    mov ax,[si].bmHeight
    dec ax
    xor dx,dx
    div word ptr [si].bmScanSegment
    mul word ptr [si].bmSegmentIndex
    or dx,dx
    jnz co_target_supported_no
    add ax,wptr [si].bmBits[2]
    jc co_target_supported_no
    jmp co_target_bits
co_target_small:
    mul bx
    or dx,dx
    jnz co_target_supported_no
    add ax,wptr [si].bmBits[0]
    jc co_target_supported_no
co_target_bits:
    mov ax,wptr [si].bmBits[2]
    or ax,ax
    jz co_target_supported_no
co_target_supported_yes:
    clc
    jmp co_target_supported_done
co_target_supported_no:
    stc
co_target_supported_done:
    pop ds
    pop si
    pop dx
    pop bx
    pop ax
    ret
co_target_supported endp

; For GB2312, render the entire mixed run ourselves. The DDK's single-byte
; renderer otherwise leaves lead/trail artifacts between narrow ASCII fields
; in status bars and dialogs. ETO_OPAQUE's extra rectangle is still painted
; by STRBLT after this decision. co_skip_base=1 repaints all bytes.
chinese_should_skip_base proc near
    push ax
    push cx
    push si
    push ds
    cmp byte ptr cs:[co_busy],0
    je co_skip_no
    cmp cs:[co_owner_bp],bp
    jne co_skip_no
    call co_target_supported
    jc co_skip_no
    mov cx,cs:[co_count]
    or cx,cx
    jle co_skip_no
    lds si,dword ptr cs:[co_string]
    mov ax,si
    add ax,cx
    jc co_skip_no
co_skip_scan:
    cmp cx,2
    jb co_skip_no
    mov al,[si]
ifdef CHCGA_GB2312
    cmp al,0A1h
    jb co_skip_ascii
    cmp al,0F7h
    ja co_skip_ascii
    mov al,[si+1]
    cmp al,0A1h
    jb co_skip_ascii
    cmp al,0FEh
    ja co_skip_ascii
else
    cmp al,081h
    jb co_skip_ascii
    cmp al,0FEh
    ja co_skip_ascii
    mov al,[si+1]
    cmp al,040h
    jb co_skip_ascii
    cmp al,07Eh
    jbe co_skip_yes
    cmp al,0A1h
    jb co_skip_ascii
    cmp al,0FEh
    ja co_skip_ascii
endif
co_skip_yes:
ifdef CHCGA_GB2312
    mov byte ptr cs:[co_skip_base],1
    stc
    jmp co_skip_done
else
    cmp word ptr cs:[co_bk_mode],OPAQUE
    je co_skip_opaque
    mov byte ptr cs:[co_skip_base],1
    stc
    jmp co_skip_done
co_skip_opaque:
    mov byte ptr cs:[co_skip_base],2
    clc
    jmp co_skip_done
endif
co_skip_ascii:
    inc si
    dec cx
    jmp co_skip_scan
co_skip_no:
    clc
co_skip_done:
    pop ds
    pop si
    pop cx
    pop ax
    ret
chinese_should_skip_base endp

chinese_overlay proc near
    push ax
    push bx
    push cx
    push dx
    push si
    push di
    push ds
    push es

    cmp byte ptr cs:[co_busy],0
    je co_no_owner
    cmp cs:[co_owner_bp],bp
    jne co_no_owner
ifdef CHCGA_TRACE
    mov bx,cs:[co_x]
    mov dx,cs:[co_y]
    mov cx,cs:[co_count]
    lds si,dword ptr cs:[co_string]
    mov word ptr cs:[co_trace_event],0
    call co_trace
endif
ifdef CHCGA_GB2312
    mov byte ptr cs:[co_replay_only],0
    cmp byte ptr cs:[co_skip_base],0
    jne co_owner_ok
    ; Write can paint an opaque ASCII run immediately after a DBCS run.
    ; Its background starts before the ASCII origin, erasing the last glyphs.
    cmp byte ptr cs:[co_cache_count],0
    je co_no_owner
    mov ax,cs:[co_y]
    cmp ax,cs:[co_cache_y]
    jne co_cache_discard
    mov ax,cs:[co_x]
    cmp ax,cs:[co_cache_end_x]
    jne co_cache_discard
    mov byte ptr cs:[co_replay_only],1
    jmp co_owner_ok
co_cache_discard:
    mov byte ptr cs:[co_cache_count],0
else
    cmp byte ptr cs:[co_skip_base],0
    je co_no_owner
endif
    cmp byte ptr cs:[co_skip_base],0
    jne co_owner_ok
    jmp co_no_owner
co_no_owner:
    jmp co_done
co_owner_ok:

    mov cx,cs:[co_count]
    or cx,cx
    jg co_has_count
    jmp co_done
co_has_count:
    ; Use the DDK's final clip: ETO_CLIPPED may intersect two rectangles.
    mov ax,clip.left
    mov cs:[co_clip_left],ax
    mov ax,clip.top
    mov cs:[co_clip_top],ax
    mov ax,clip.right
    mov cs:[co_clip_right],ax
    mov ax,clip.bottom
    mov cs:[co_clip_bottom],ax
    mov word ptr cs:[co_active_height],CHCGA_HEIGHT
    mov word ptr cs:[co_cell_width],16
    mov byte ptr cs:[co_compact],0
    mov byte ptr cs:[co_force_advance],0
    ; Icons use a short clip and can fit the 10-pixel bank. Dense document
    ; rows retain the 8-pixel bank below in the compact drawing path.
    cmp word ptr cs:[co_font_height],8
    ja co_normal_size
    mov ax,cs:[co_clip_bottom]
    sub ax,cs:[co_clip_top]
    cmp ax,10
    ja co_normal_size
    mov word ptr cs:[co_active_height],CHCGA_MEDIUM_HEIGHT
co_normal_size:
ifdef CHCGA_GB2312
    ; Document controls can report an 8-pixel line height while exposing a
    ; tall clip. Their following ASCII run starts after 10 pixels per DBCS
    ; character. Use the 10x8 font so our overlay occupies the same width.
    cmp word ptr cs:[co_font_height],8
    ja co_compact_done
    cmp word ptr cs:[co_clip_top],30
    jb co_compact_done
    mov ax,cs:[co_clip_bottom]
    sub ax,cs:[co_clip_top]
    cmp ax,32
    jbe co_compact_done
    mov word ptr cs:[co_active_height],CHCGA_SMALL_HEIGHT
    mov word ptr cs:[co_cell_width],10
    mov byte ptr cs:[co_compact],1
    cmp word ptr cs:[co_dx_seg],0
    jne co_compact_done
    mov byte ptr cs:[co_force_advance],1
co_compact_done:
endif
    lds si,dword ptr cs:[co_device]
    cmp word ptr [si].bmType,0
    je co_bitmap_target
    mov byte ptr cs:[co_bitmap],0
    mov word ptr cs:[co_target_width],640
    mov word ptr cs:[co_target_height],200
    mov ax,0B800h
    mov es,ax
    jmp co_target_ready

co_bitmap_target:
    call co_target_supported
    jc co_invalid_target
    cmp byte ptr [si].bmPlanes,1
    jne co_invalid_target
    cmp byte ptr [si].bmBitsPixel,1
    jne co_invalid_target
    mov ax,[si].bmWidth
    or ax,ax
    jz co_invalid_target
    cmp ax,4096
    ja co_invalid_target
    mov cs:[co_target_width],ax
    add ax,7
    shr ax,1
    shr ax,1
    shr ax,1
    cmp ax,[si].bmWidthBytes
    ja co_invalid_target
    mov ax,[si].bmHeight
    or ax,ax
    jz co_invalid_target
    mov cs:[co_target_height],ax
    mov ax,[si].bmWidthBytes
    or ax,ax
    jz co_invalid_target
    mov cs:[co_stride],ax
    mov bx,wptr [si].bmBits[0]
    mov cs:[co_base],bx
    mov ax,[si].bmSegmentIndex
    mov cs:[co_seg_index],ax
    mov ax,[si].bmScanSegment
    mov cs:[co_scan_segment],ax
    mov ax,wptr [si].bmBits[2]
    or ax,ax
    jz co_invalid_target
    mov cs:[co_segment],ax
    mov es,ax
    mov byte ptr cs:[co_bitmap],1
    jmp co_target_ready

co_invalid_target:
    jmp co_done

co_target_ready:
ifdef CHCGA_GB2312
    cmp byte ptr cs:[co_replay_only],0
    je co_cache_new_run
    cmp byte ptr cs:[co_bitmap],0
    jne co_replay_done
    cmp word ptr cs:[co_cell_width],10
    jne co_replay_done
    mov ax,cs:[co_clip_left]
    cmp ax,cs:[co_cache_clip_left]
    jne co_replay_done
    mov ax,cs:[co_clip_top]
    cmp ax,cs:[co_cache_clip_top]
    jne co_replay_done
    mov ax,cs:[co_clip_right]
    cmp ax,cs:[co_cache_clip_right]
    jne co_replay_done
    mov ax,cs:[co_clip_bottom]
    cmp ax,cs:[co_cache_clip_bottom]
    jne co_replay_done
    mov al,cs:[co_fg]
    cmp al,cs:[co_cache_fg]
    jne co_replay_done
    mov al,cs:[co_bg]
    cmp al,cs:[co_cache_bg]
    jne co_replay_done
    mov ax,cs:[co_bk_mode]
    cmp ax,cs:[co_cache_bk_mode]
    jne co_replay_done
    call co_replay_glyphs
co_replay_done:
    mov byte ptr cs:[co_cache_count],0
    jmp co_done
co_cache_new_run:
    mov byte ptr cs:[co_cache_count],0
    mov byte ptr cs:[co_cache_next],0
    cmp byte ptr cs:[co_bitmap],0
    jne co_cache_ready
    cmp word ptr cs:[co_cell_width],10
    jne co_cache_ready
    mov ax,cs:[co_y]
    mov cs:[co_cache_y],ax
    mov ax,cs:[co_clip_left]
    mov cs:[co_cache_clip_left],ax
    mov ax,cs:[co_clip_top]
    mov cs:[co_cache_clip_top],ax
    mov ax,cs:[co_clip_right]
    mov cs:[co_cache_clip_right],ax
    mov ax,cs:[co_clip_bottom]
    mov cs:[co_cache_clip_bottom],ax
    mov al,cs:[co_fg]
    mov cs:[co_cache_fg],al
    mov al,cs:[co_bg]
    mov cs:[co_cache_bg],al
    mov ax,cs:[co_bk_mode]
    mov cs:[co_cache_bk_mode],ax
co_cache_ready:
endif
    mov bx,cs:[co_x]
    mov dx,cs:[co_y]
lds si,dword ptr cs:[co_string]
co_next:
ifdef CHCGA_TRACE
    mov word ptr cs:[co_trace_event],0
    call co_trace
endif
    or cx,cx
    jnz co_more
ifdef CHCGA_GB2312
    cmp byte ptr cs:[co_cache_count],0
    je co_no_cache_end
    mov cs:[co_cache_end_x],bx
co_no_cache_end:
endif
    jmp co_done
co_more:
    mov al,[si]
ifdef CHCGA_GB2312
    cmp al,0A1h
    jae co_lead_min_ok
    jmp co_ascii
co_lead_min_ok:
    cmp al,0F7h
    jbe co_lead_max_ok
    jmp co_ascii
co_lead_max_ok:
    cmp cx,2
    jae co_pair_available
    jmp co_ascii
co_pair_available:
    mov ah,[si+1]
    cmp ah,0A1h
    jae co_trail_min_ok
    jmp co_ascii
co_trail_min_ok:
    cmp ah,0FEh
    jbe co_trail_max_ok
    jmp co_ascii
co_trail_max_ok:
else
    cmp al,081h
    jb co_ascii
    cmp al,0FEh
    ja co_ascii
    cmp cx,2
    jb co_ascii
    mov ah,[si+1]
    cmp ah,040h
    jb co_ascii
    cmp ah,07Eh
    jbe co_find
    cmp ah,0A1h
    jb co_ascii
    cmp ah,0FEh
    ja co_ascii
endif

co_find:
    call co_load_glyph
    jc co_find_embedded
ifdef CHCGA_TRACE
    mov word ptr cs:[co_trace_event],1
    call co_trace
endif
    call chglyph_draw
ifdef CHCGA_GB2312
    cmp word ptr cs:[co_cell_width],10
    jne co_no_cache_glyph
    cmp byte ptr cs:[co_bitmap],0
    jne co_no_cache_glyph
    call co_cache_glyph
co_no_cache_glyph:
endif
    jmp co_advance_dbcs
co_find_embedded:
    cmp word ptr cs:[co_active_height],CHCGA_HEIGHT
    jne co_advance_dbcs
    mov di,offset chglyph_table
co_search:
    cmp di,offset chglyph_table_end
    jae co_advance_dbcs
    cmp ax,word ptr cs:[di]
    je co_found
    add di,CHCGA_RECORD
    jmp co_search
co_found:
    add di,2
ifdef CHCGA_TRACE
    mov word ptr cs:[co_trace_event],2
    call co_trace
endif
    call chglyph_draw
co_advance_dbcs:
    add si,2
    sub cx,2
    call co_advance_byte
    cmp byte ptr cs:[co_force_advance],0
    je co_first_advance_ready
    mov ax,5
    add ax,cs:[co_char_extra]
co_first_advance_ready:
    add bx,ax
    jo co_done
    call co_advance_byte
    cmp byte ptr cs:[co_force_advance],0
    je co_second_advance_ready
    mov ax,5
    add ax,cs:[co_char_extra]
co_second_advance_ready:
    add bx,ax
    jo co_done
    jmp co_next
co_ascii:
    cmp byte ptr cs:[co_skip_base],2
    je co_ascii_advance
    call co_draw_ascii
co_ascii_advance:
    inc si
    dec cx
    call co_advance_byte
    add bx,ax
    jo co_done
    jmp co_next

co_done:
    pop es
    pop ds
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop ax
    ret
chinese_overlay endp

; Render embedded ASCII cells when the original English renderer was skipped.
co_draw_ascii proc near
    push ax
    push bx
    push cx
    push dx
    push si
    push di
    mov al,[si]
    cmp al,128
    jb co_ascii_index
    mov al,'?'
co_ascii_index:
    xor ah,ah
    mov cx,cs:[co_active_height]
    mul cx
    mov si,offset ch_ascii_main
    cmp word ptr cs:[co_active_height],CHCGA_HEIGHT
    je co_ascii_source
    mov si,offset ch_ascii_small
    cmp word ptr cs:[co_active_height],CHCGA_MEDIUM_HEIGHT
    jne co_ascii_source
    mov si,offset ch_ascii_medium
co_ascii_source:
    add si,ax
    mov di,offset co_glyph
    mov cx,cs:[co_active_height]
co_ascii_copy:
    mov al,cs:[si]
    mov cs:[di],al
    mov byte ptr cs:[di+1],0
    inc si
    add di,2
    loop co_ascii_copy
    mov di,offset co_glyph
    mov word ptr cs:[co_cell_width],8
    mov dx,cs:[co_y] ; MUL above writes DX as well as AX.
    call chglyph_draw
    mov word ptr cs:[co_cell_width],16
    cmp byte ptr cs:[co_compact],0
    je co_ascii_width_restored
    mov word ptr cs:[co_cell_width],10
co_ascii_width_restored:
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop ax
    ret
co_draw_ascii endp

; Return the GDI advance for one source byte. Big5 pairs consume two entries.
co_advance_byte proc near
    push bx
    push si
    push ds
    mov ax,8
    mov bx,cs:[co_dx_off]
    mov si,cs:[co_dx_seg]
    or si,si
    jz co_advance_extra
    cmp bx,0FFFFh
    jne co_advance_read
    mov word ptr cs:[co_dx_seg],0
    jmp co_advance_extra
co_advance_read:
    mov ds,si
    mov ax,[bx]
    cmp bx,0FFFEh
    jae co_advance_last
    add word ptr cs:[co_dx_off],2
    jmp co_advance_extra
co_advance_last:
    mov word ptr cs:[co_dx_seg],0
co_advance_extra:
    add ax,cs:[co_char_extra]
    pop ds
    pop si
    pop bx
    ret
co_advance_byte endp

co_count dw 0
co_busy db 0
co_owner_bp dw 0
co_skip_base db 0
co_x dw 0
co_y dw 0
co_font_height dw 0
co_active_height dw CHCGA_HEIGHT
co_cell_width dw 16
co_compact db 0
co_force_advance db 0
co_device dd 0
co_string dd 0
co_fg db 0
co_bg db 0
co_bk_mode dw OPAQUE
co_char_extra dw 0
co_dx_off dw 0
co_dx_seg dw 0
co_bitmap db 0
co_base dw 0
co_segment dw 0
co_stride dw 0
co_seg_index dw 0
co_scan_segment dw 0
co_target_width dw 640
co_target_height dw 200
co_clip_left dw 0
co_clip_top dw 0
co_clip_right dw 640
co_clip_bottom dw 200
co_font_handle_main dw 0FFFFh
co_font_handle_small dw 0FFFFh
co_font_handle_medium dw 0FFFFh
co_handle_slot dw 0
co_pair dw 0
co_glyph db CHCGA_HEIGHT*2 dup(0)

ifdef CHCGA_GB2312
; Keep only the final four compact cells. A following opaque ASCII StrBlt
; can clear up to the end of the preceding DBCS run in Write's text lines.
co_replay_only db 0
co_cache_count db 0
co_cache_next db 0
co_cache_x dw 4 dup(0)
co_cache_y dw 0
co_cache_end_x dw 0
co_cache_clip_left dw 0
co_cache_clip_top dw 0
co_cache_clip_right dw 0
co_cache_clip_bottom dw 0
co_cache_fg db 0
co_cache_bg db 0
co_cache_bk_mode dw 0
co_cache_bits db 4*CHCGA_SMALL_HEIGHT*2 dup(0)

co_cache_glyph proc near
    push ax
    push cx
    push si
    push di
    mov al,cs:[co_cache_next]
    xor ah,ah
    shl ax,1
    mov si,ax
    mov cs:[co_cache_x+si],bx
    shl ax,1
    shl ax,1
    shl ax,1
    mov di,offset co_cache_bits
    add di,ax
    mov si,offset co_glyph
    mov cx,CHCGA_SMALL_HEIGHT*2
co_cache_copy:
    mov al,cs:[si]
    mov cs:[di],al
    inc si
    inc di
    loop co_cache_copy
    mov al,cs:[co_cache_next]
    inc al
    and al,3
    mov cs:[co_cache_next],al
    cmp byte ptr cs:[co_cache_count],4
    jae co_cache_full
    inc byte ptr cs:[co_cache_count]
co_cache_full:
    pop di
    pop si
    pop cx
    pop ax
    ret
co_cache_glyph endp

co_replay_glyphs proc near
    push ax
    push bx
    push cx
    push dx
    push si
    push di
    xor ch,ch
    mov cl,cs:[co_cache_count]
    xor si,si
co_replay_next:
    mov ax,si
    shl ax,1
    mov di,ax
    mov bx,cs:[co_cache_x+di]
    shl ax,1
    shl ax,1
    shl ax,1
    mov di,offset co_cache_bits
    add di,ax
    mov dx,cs:[co_cache_y]
    call chglyph_draw
    inc si
    loop co_replay_next
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop ax
    ret
co_replay_glyphs endp
endif

; Fetch a 2-byte Big5 glyph from the disk font. CF=0 and DI=bitmap on success.
; The unmodified 35-glyph table remains a fallback when the font is absent.
co_load_glyph proc near
    mov cs:[co_pair],ax
    push ax
    push bx
    push cx
    push dx
    push si
    push ds
    push es
    mov si,offset co_font_handle_main
    mov dx,offset co_font_path
    cmp word ptr cs:[co_active_height],CHCGA_HEIGHT
    je co_load_selected
    mov si,offset co_font_handle_small
    mov dx,offset co_small_font_path
    cmp word ptr cs:[co_active_height],CHCGA_MEDIUM_HEIGHT
    jne co_load_selected
    mov si,offset co_font_handle_medium
    mov dx,offset co_medium_font_path
co_load_selected:
    mov cs:[co_handle_slot],si
    mov bx,cs:[si]
    cmp bx,0FFFEh
    jne co_load_not_missing
    jmp co_load_failed
co_load_not_missing:
    cmp bx,0FFFFh
    jne co_load_open
    push cs
    pop ds
    mov ax,3D00h
    int 21h
    jnc co_load_opened
    mov si,cs:[co_handle_slot]
    mov word ptr cs:[si],0FFFEh
    jmp co_load_failed
co_load_opened:
    mov si,cs:[co_handle_slot]
    mov cs:[si],ax
    mov bx,ax
co_load_open:
    mov ax,cs:[co_pair]
    xor ah,ah
    sub al,081h
    mov cx,157
    mul cx
    mov si,ax
    mov ax,cs:[co_pair]
    mov al,ah
    xor ah,ah
    cmp al,07Eh
    jbe co_load_low_trail
    sub al,0A1h
    add al,63
    jmp co_load_index
co_load_low_trail:
    sub al,040h
co_load_index:
    add si,ax
    mov ax,si
    mov cx,cs:[co_active_height]
    shl cx,1
    mul cx
    mov bx,cs:[co_active_height]
    shl bx,1
    shl bx,1
    shl bx,1
    shl bx,1
    shl bx,1
    shl bx,1
    shl bx,1
    add bx,24
    add ax,bx
    adc dx,0
    mov cx,dx
    mov dx,ax
    mov si,cs:[co_handle_slot]
    mov bx,cs:[si]
    mov ax,4200h
    int 21h
    jc co_load_failed
    push cs
    pop ds
    mov dx,offset co_glyph
    mov cx,cs:[co_active_height]
    shl cx,1
    mov ah,3Fh
    int 21h
    jc co_load_failed
    mov cx,cs:[co_active_height]
    shl cx,1
    cmp ax,cx
    jne co_load_failed
    mov di,offset co_glyph
    clc
    jmp co_load_done
co_load_failed:
    stc
co_load_done:
    pop es
    pop ds
    pop si
    pop dx
    pop cx
    pop bx
    pop ax
    ret
co_load_glyph endp

; Input BX=X, DX=Y, DI=CS offset of the compact bitmap (ink bit=1).
; Paint a 16-pixel cell to CGA VRAM or a validated small 1-bit bitmap.
chglyph_draw proc near
    push bp
    mov bp,sp
    sub sp,12
    mov [bp-2],bx
    mov [bp-4],dx
    mov [bp-6],di
    mov word ptr [bp-8],0
    push ax
    push bx
    push cx
    push dx
    push si
    push di

chglyph_row:
    mov di,[bp-6]
    mov ax,word ptr cs:[di]
    xchg al,ah
    mov [bp-10],ax
    mov word ptr [bp-12],0
chglyph_col:
    mov ax,[bp-4]
    add ax,[bp-8]
    cmp ax,cs:[co_clip_top]
    jge chglyph_after_top
    jmp chglyph_skip_pixel
chglyph_after_top:
    cmp ax,cs:[co_clip_bottom]
    jl chglyph_before_bottom
    jmp chglyph_skip_pixel
chglyph_before_bottom:
    cmp ax,0
    jge chglyph_nonnegative_y
    jmp chglyph_skip_pixel
chglyph_nonnegative_y:
    cmp ax,cs:[co_target_height]
    jb chglyph_within_height
    jmp chglyph_skip_pixel
chglyph_within_height:
    mov ax,[bp-2]
    add ax,[bp-12]
    cmp ax,cs:[co_clip_left]
    jl chglyph_reject_x
    cmp ax,cs:[co_clip_right]
    jge chglyph_reject_x
    cmp ax,0
    jl chglyph_reject_x
    cmp ax,cs:[co_target_width]
    jae chglyph_reject_x
    jmp chglyph_valid_x
chglyph_reject_x:
    jmp chglyph_skip_pixel
chglyph_valid_x:
    cmp byte ptr cs:[co_bitmap],0
    jne chglyph_bitmap_offset
    mov ax,[bp-4]
    add ax,[bp-8]
    mov si,ax
    and si,1
    shr ax,1
    mov cx,80
    mul cx
    or si,si
    jz chglyph_even
    add ax,2000h
chglyph_even:
    mov di,ax
    mov ax,[bp-2]
    add ax,[bp-12]
    mov si,ax
    shr ax,1
    shr ax,1
    shr ax,1
    add di,ax
    jmp chglyph_have_offset
chglyph_bitmap_offset:
    mov ax,[bp-4]
    add ax,[bp-8]
    cmp word ptr cs:[co_seg_index],0
    je chglyph_bitmap_scan
    xor dx,dx
    div word ptr cs:[co_scan_segment]
    mov cx,dx
    mul word ptr cs:[co_seg_index]
    or dx,dx
    jnz chglyph_skip_pixel
    mov dx,cs:[co_segment]
    add ax,dx
    jc chglyph_skip_pixel
    mov es,ax
    mov ax,cx
chglyph_bitmap_scan:
    mul word ptr cs:[co_stride]
    or dx,dx
    jnz chglyph_skip_pixel
    mov di,ax
    mov ax,[bp-2]
    add ax,[bp-12]
    shr ax,1
    shr ax,1
    shr ax,1
    add di,ax
    jc chglyph_skip_pixel
    add di,cs:[co_base]
    jc chglyph_skip_pixel
chglyph_have_offset:
    mov si,[bp-2]
    add si,[bp-12]
    and si,7
    mov cx,si
    mov bl,80h
    shr bl,cl
    mov ax,[bp-10]
    mov cx,[bp-12]
    mov si,8000h
    shr si,cl
    test ax,si
    jnz chglyph_ink
    cmp word ptr cs:[co_bk_mode],OPAQUE
    jne chglyph_pixel_done
    mov al,cs:[co_bg]
    jmp chglyph_apply_color
chglyph_ink:
    mov al,cs:[co_fg]
chglyph_apply_color:
    test al,10h
    jnz chglyph_set_pixel
    mov al,bl
    not al
    and byte ptr es:[di],al
    jmp chglyph_pixel_done
chglyph_set_pixel:
    or byte ptr es:[di],bl
    jmp chglyph_pixel_done
chglyph_skip_pixel:
chglyph_pixel_done:
    inc word ptr [bp-12]
    mov ax,cs:[co_cell_width]
    cmp word ptr [bp-12],ax
    jae chglyph_next_row
    jmp chglyph_col
chglyph_next_row:
    add word ptr [bp-6],2
    inc word ptr [bp-8]
    mov ax,cs:[co_active_height]
    cmp word ptr [bp-8],ax
    jae chglyph_rows_done
    jmp chglyph_row
chglyph_rows_done:

    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop ax
    mov sp,bp
    pop bp
    ret
chglyph_draw endp

ifdef CHCGA_TRACE
co_trace_handle dw 0FFFFh
co_trace_count dw 0
co_trace_initialized db 0
co_trace_event dw 0
co_trace_record dw 13 dup(0)
co_trace_path db 'C:\METRICS.BIN',0
co_trace proc near
    pushf
    push ax
    push bx
    push cx
    push dx
    push si
    push di
    push ds
    cmp word ptr cs:[co_trace_count],1000
    jb co_trace_room
    jmp co_trace_done
co_trace_room:
    cmp cx,2
    jae co_trace_count_ready
    jmp co_trace_done
co_trace_count_ready:
    inc word ptr cs:[co_trace_count]
    mov ax,bx
    mov cs:[co_trace_record],ax
    mov ax,dx
    mov cs:[co_trace_record+2],ax
    mov ax,cs:[co_font_height]
    mov cs:[co_trace_record+4],ax
    mov ax,cs:[co_clip_left]
    mov cs:[co_trace_record+6],ax
    mov ax,cs:[co_clip_top]
    mov cs:[co_trace_record+8],ax
    mov ax,cs:[co_clip_right]
    mov cs:[co_trace_record+10],ax
    mov ax,cs:[co_clip_bottom]
    mov cs:[co_trace_record+12],ax
    mov ax,cx
    mov cs:[co_trace_record+14],ax
    mov ax,[si]
    mov cs:[co_trace_record+16],ax
    xor ax,ax
    cmp cx,4
    jb co_trace_no_next
    mov ax,[si+2]
co_trace_no_next:
    mov cs:[co_trace_record+18],ax
    mov ax,cs:[co_trace_event]
    mov cs:[co_trace_record+20],ax
    or ax,ax
    jz co_trace_no_glyph
    mov ax,word ptr cs:[di]
    mov cs:[co_trace_record+22],ax
    mov ax,word ptr cs:[di+2]
    mov cs:[co_trace_record+24],ax
    jmp co_trace_glyph_done
co_trace_no_glyph:
    mov word ptr cs:[co_trace_record+22],0
    mov word ptr cs:[co_trace_record+24],0
co_trace_glyph_done:
    push cs
    pop ds
    mov dx,offset co_trace_path
    cmp byte ptr cs:[co_trace_initialized],0
    jne co_trace_open
    xor cx,cx
    mov ah,3Ch
    int 21h
    jc co_trace_done
    mov byte ptr cs:[co_trace_initialized],1
    mov bx,ax
    jmp co_trace_write
co_trace_open:
    mov ax,3D02h
    int 21h
    jc co_trace_done
    mov bx,ax
    mov ax,4202h
    xor cx,cx
    xor dx,dx
    int 21h
co_trace_write:
    push cs
    pop ds
    mov dx,offset co_trace_record
    mov cx,26
    mov ah,40h
    int 21h
    mov ah,3Eh
    int 21h
co_trace_done:
    pop ds
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop ax
    popf
    ret
co_trace endp
endif
