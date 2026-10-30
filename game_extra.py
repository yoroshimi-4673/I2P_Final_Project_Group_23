#1. 全域變數與圖鑑資料結構

# 遊戲狀態管理
STATE_CODEX = 2          # 【新增】圖鑑狀態[cite: 2]
current_state = STATE_MENU
previous_state = STATE_MENU  # 【新增】紀錄進入圖鑑前的狀態[cite: 2]

# 字體設定
font_small = pygame.font.SysFont("microsoftjhenghei", 16) # 【新增】微型字體[cite: 2]

# ================= 【新增】圖鑑資料結構與捲動控制變數 =================[cite: 2]
codex_chapters = [
    {
        "title": "Chapter 1",
        "items": [
            {"name": "照片", "unlocked": True, "color": (200, 80, 80), "desc": "我是照片。"},
            {"name": "未知物品", "unlocked": False, "color": (50, 50, 50), "desc": "尚待解鎖..."},
            {"name": "未知物品", "unlocked": False, "color": (50, 50, 50), "desc": "尚待解鎖..."},
            {"name": "未知物品", "unlocked": False, "color": (50, 50, 50), "desc": "尚待解鎖..."},
        ]
    },
    {
        "title": "Chapter 2",
        "items": [
            {"name": "未知物品", "unlocked": False, "color": (50, 50, 50), "desc": "尚待解鎖..."},
            {"name": "未知物品", "unlocked": False, "color": (50, 50, 50), "desc": "尚待解鎖..."},
            {"name": "未知物品", "unlocked": False, "color": (50, 50, 50), "desc": "尚待解鎖..."},
        ]
    },
    {
        "title": "Chapter 3",
        "items": [
            {"name": "未知物品", "unlocked": False, "color": (50, 50, 50), "desc": "尚待解鎖..."},
            {"name": "未知物品", "unlocked": False, "color": (50, 50, 50), "desc": "尚待解鎖..."},
        ]
    },
    {
        "title": "Chapter 4",
        "items": [
            {"name": "未知物品", "unlocked": False, "color": (50, 50, 50), "desc": "尚待解鎖..."},
        ]
    }
]

left_scroll_y = 0        # 左側滾動偏移[cite: 2]
right_scroll_y = 0       # 右側滾動偏移[cite: 2]
selected_codex_item = None # 當前點擊放大的物品[cite: 2]
dragging_scrollbar = False # 是否正在拖曳右側拉桿[cite: 2]


#2. 圖鑑繪製函式 draw_codex_view

# ================= 【新增】圖鑑畫面繪製函式 =================[cite: 2]

def draw_codex_view(screen, screen_w, screen_h, mouse_x, mouse_y, mouse_click):
    global left_scroll_y, right_scroll_y, selected_codex_item, current_state, dragging_scrollbar

    sidebar_w = 180
    
    # ---------------- 1. 左側章節列表 ----------------[cite: 2]
    pygame.draw.rect(screen, (25, 25, 35), (0, 0, sidebar_w, screen_h))
    pygame.draw.line(screen, (60, 60, 80), (sidebar_w, 0), (sidebar_w, screen_h), 2)

    sidebar_title = font_ui.render("章節列表", True, (200, 200, 220))
    screen.blit(sidebar_title, (20, 15))

    chap_btn_h = 45
    total_left_h = len(codex_chapters) * chap_btn_h
    max_left_scroll = min(0, (screen_h - 120) - total_left_h)
    left_scroll_y = max(max_left_scroll, min(0, left_scroll_y))

    for idx, chap in enumerate(codex_chapters):
        btn_y = 60 + left_scroll_y + idx * chap_btn_h
        if 50 <= btn_y <= screen_h - 70:
            btn_rect = pygame.Rect(10, btn_y, sidebar_w - 20, 38)
            is_hover = btn_rect.collidepoint(mouse_x, mouse_y) and not selected_codex_item

            pygame.draw.rect(screen, (50, 70, 90) if is_hover else (35, 40, 55), btn_rect, border_radius=6)
            pygame.draw.rect(screen, (100, 100, 130), btn_rect, 1, border_radius=6)

            txt_surf = font_ui.render(chap["title"], True, (255, 255, 255))
            screen.blit(txt_surf, (btn_rect.x + 15, btn_rect.y + 7))

            # 點擊左側章節按鈕快速定位右側[cite: 2]
            if mouse_click and is_hover:
                target_y = 0
                card_w, card_h, padding = 85, 85, 15
                cols = max(1, (screen_w - sidebar_w - 60) // (card_w + padding))
                for prev_i in range(idx):
                    rows = (len(codex_chapters[prev_i]["items"]) + cols - 1) // cols
                    target_y += 45 + rows * (card_h + padding) + 20
                right_scroll_y = -target_y

    # 左下角返回按鈕[cite: 2]
    back_btn = pygame.Rect(10, screen_h - 50, sidebar_w - 20, 40)
    is_back_hover = back_btn.collidepoint(mouse_x, mouse_y) and not selected_codex_item
    draw_button(screen, "返回", back_btn.x, back_btn.y, back_btn.width, back_btn.height, is_back_hover, bg_color=(100, 50, 50))
    if mouse_click and is_back_hover:
        current_state = previous_state

    # ---------------- 2. 右側物品列表 (Chapter 1~4 連續接續) ----------------[cite: 2]
    content_x = sidebar_w + 20
    content_w = screen_w - sidebar_w - 60
    card_w, card_h = 85, 85
    padding = 15
    cols = max(1, content_w // (card_w + padding))

    total_right_h = 0
    for chap in codex_chapters:
        rows = (len(chap["items"]) + cols - 1) // cols
        total_right_h += 45 + rows * (card_h + padding) + 20

    max_right_scroll = min(0, (screen_h - 60) - total_right_h)
    right_scroll_y = max(max_right_scroll, min(0, right_scroll_y))

    current_y = 20 + right_scroll_y
    total_items_count = 0
    unlocked_items_count = 0

    for chap in codex_chapters:
        # 章節標題
        if -30 <= current_y <= screen_h - 30:
            chap_title = font_title.render(chap["title"], True, (240, 240, 240))
            screen.blit(chap_title, (content_x, current_y))
        current_y += 45

        # 章節物品
        for i, item in enumerate(chap["items"]):
            total_items_count += 1
            if item["unlocked"]:
                unlocked_items_count += 1

            row, col = i // cols, i % cols
            cx = content_x + col * (card_w + padding)
            cy = current_y + row * (card_h + padding)

            if -card_h <= cy <= screen_h:
                card_rect = pygame.Rect(cx, cy, card_w, card_h)
                is_card_hover = card_rect.collidepoint(mouse_x, mouse_y) and not selected_codex_item

                pygame.draw.rect(screen, (40, 45, 60), card_rect, border_radius=8)
                pygame.draw.rect(screen, (255, 215, 0) if is_card_hover else (80, 80, 100), card_rect, 2, border_radius=8)

                if item["unlocked"]:
                    icon_rect = pygame.Rect(cx + 8, cy + 8, card_w - 16, card_h - 16)
                    pygame.draw.rect(screen, item["color"], icon_rect, border_radius=6)
                else:
                    # 未解鎖顯示純問號[cite: 2]
                    q_surf = font_title.render("?", True, (120, 120, 140))
                    screen.blit(q_surf, q_surf.get_rect(center=card_rect.center))

                if mouse_click and is_card_hover:
                    selected_codex_item = item

        rows = (len(chap["items"]) + cols - 1) // cols
        current_y += rows * (card_h + padding) + 20

    # ---------------- 3. 右側滾動條拉桿與上下按鈕 ----------------[cite: 2]
    sb_x = screen_w - 30
    sb_y = 50
    sb_h = screen_h - 100
    pygame.draw.rect(screen, (20, 20, 25), (sb_x, sb_y, 15, sb_h), border_radius=4)

    btn_up = pygame.Rect(sb_x, 20, 15, 25)
    btn_down = pygame.Rect(sb_x, screen_h - 45, 15, 25)
    
    pygame.draw.rect(screen, (70, 70, 90), btn_up, border_radius=3)
    pygame.draw.rect(screen, (70, 70, 90), btn_down, border_radius=3)
    
    screen.blit(font_small.render("▲", True, (200, 200, 200)), (sb_x + 1, 23))
    screen.blit(font_small.render("▼", True, (200, 200, 200)), (sb_x + 1, screen_h - 42))

    if mouse_click:
        if btn_up.collidepoint(mouse_x, mouse_y): right_scroll_y += 40
        if btn_down.collidepoint(mouse_x, mouse_y): right_scroll_y -= 40

    thumb_h = max(30, int(sb_h * (sb_h / max(1, total_right_h))))
    scroll_ratio = abs(right_scroll_y) / max(1, (total_right_h - sb_h))
    thumb_y = sb_y + scroll_ratio * (sb_h - thumb_h)
    thumb_rect = pygame.Rect(sb_x, thumb_y, 15, thumb_h)

    pygame.draw.rect(screen, (100, 120, 160), thumb_rect, border_radius=4)

    if mouse_click and thumb_rect.collidepoint(mouse_x, mouse_y):
        dragging_scrollbar = True

    # ---------------- 4. 右下角收集進度 ----------------[cite: 2]
    progress_txt = f"蒐集進度: {unlocked_items_count} / {total_items_count}"
    prog_surf = font_ui.render(progress_txt, True, (255, 215, 0))
    screen.blit(prog_surf, (screen_w - prog_surf.get_width() - 40, screen_h - 35))

    # ---------------- 5. 點擊物品放大檢視彈窗 ----------------[cite: 2]
    if selected_codex_item:
        modal = pygame.Surface((screen_w, screen_h))
        modal.set_alpha(180)
        modal.fill((0, 0, 0))
        screen.blit(modal, (0, 0))

        mw, mh = 380, 240
        mx, my = (screen_w - mw) // 2, (screen_h - mh) // 2
        pygame.draw.rect(screen, (40, 45, 55), (mx, my, mw, mh), border_radius=12)
        pygame.draw.rect(screen, (200, 200, 220), (mx, my, mw, mh), 2, border_radius=12)

        close_btn = pygame.Rect(mx + mw - 35, my + 10, 25, 25)
        is_close_hover = close_btn.collidepoint(mouse_x, mouse_y)
        pygame.draw.rect(screen, (200, 60, 60) if is_close_hover else (100, 100, 100), close_btn, border_radius=4)
        screen.blit(font_small.render("X", True, (255, 255, 255)), (close_btn.x + 7, close_btn.y + 2))

        if mouse_click and is_close_hover:
            selected_codex_item = None
            return

        big_icon = pygame.Rect(mx + 25, my + 40, 90, 90)
        if selected_codex_item["unlocked"]:
            pygame.draw.rect(screen, selected_codex_item["color"], big_icon, border_radius=8)
            t_surf = font_ui.render(selected_codex_item["name"], True, (255, 215, 0))
            d_surf = font_small.render(selected_codex_item["desc"], True, (220, 220, 220))
        else:
            pygame.draw.rect(screen, (30, 35, 45), big_icon, border_radius=8)
            pygame.draw.rect(screen, (80, 80, 100), big_icon, 2, border_radius=8)
            big_q = font_title.render("?", True, (120, 120, 140))
            screen.blit(big_q, big_q.get_rect(center=big_icon.center))
            t_surf = font_ui.render("未知物品", True, (150, 150, 150))
            d_surf = font_small.render("尚待解鎖...", True, (120, 120, 120))

        screen.blit(t_surf, (mx + 130, my + 40))
        screen.blit(d_surf, (mx + 130, my + 80))


#3. 主迴圈事件處理（新增與修改）

# --- A. 事件處理 ---[cite: 2]
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            dragging_volume = False
            dragging_scrollbar = False  # 【新增】放開滑鼠時停止拖曳拉桿[cite: 2]

        # 【修改】滑鼠滾輪獨立判斷左/右側與遊戲狀態[cite: 2]
        if event.type == pygame.MOUSEWHEEL:
            if current_state == STATE_PLAYING and not is_settings_open:
                if event.y > 0:
                    selected_slot = (selected_slot - 1) % NUM_SLOTS
                elif event.y < 0:
                    selected_slot = (selected_slot + 1) % NUM_SLOTS
            elif current_state == STATE_CODEX:  # 【新增】圖鑑區域滾動[cite: 2]
                if mouse_x < 180:
                    left_scroll_y += event.y * 20
                else:
                    right_scroll_y += event.y * 30

        # 【修改】ESC 按鍵層級響應[cite: 2]
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if selected_codex_item:         # 【新增】關閉物品詳情彈窗[cite: 2]
                    selected_codex_item = None
                elif is_settings_open:
                    is_settings_open = False
                elif current_state == STATE_CODEX: # 【新增】退回上一頁[cite: 2]
                    current_state = previous_state
                elif current_state == STATE_PLAYING:
                    current_state = STATE_MENU

    # 【新增】滑鼠按住拖曳右側拉桿[cite: 2]
    if dragging_scrollbar:
        rel_y = max(0, min(mouse_y - 50, screen_height - 100))
        ratio = rel_y / (screen_height - 100)
        right_scroll_y = -ratio * (300) # 動態捲動偏移量[cite: 2]


#4. 畫面渲染分支（新增與修改）

# --- B. 畫面繪製與互動邏輯 ---[cite: 2]

    if current_state == STATE_MENU:
        # 主畫面標題 (調整位置)[cite: 2]
        title_surf = font_title.render("萬徑.歸一", True, (255, 255, 255))
        screen.blit(title_surf, (screen_width//2 - title_surf.get_width()//2, screen_height//2 - 190))

        # 【修改】主畫面按鈕 (增加「圖鑑」與純按鈕「存檔」)[cite: 2]
        btn_w, btn_h = 180, 42
        btn_x = screen_width//2 - btn_w//2
        start_y = screen_height//2 - 110

        rect_start = pygame.Rect(btn_x, start_y, btn_w, btn_h)
        rect_codex = pygame.Rect(btn_x, start_y + 50, btn_w, btn_h)   # 【新增】[cite: 2]
        rect_setting = pygame.Rect(btn_x, start_y + 100, btn_w, btn_h)
        rect_save = pygame.Rect(btn_x, start_y + 150, btn_w, btn_h)    # 【新增】[cite: 2]
        rect_exit = pygame.Rect(btn_x, start_y + 200, btn_w, btn_h)

        if not is_settings_open:
            hover_start = rect_start.collidepoint(mouse_x, mouse_y)
            hover_codex = rect_codex.collidepoint(mouse_x, mouse_y)   # 【新增】[cite: 2]
            hover_setting = rect_setting.collidepoint(mouse_x, mouse_y)
            hover_save = rect_save.collidepoint(mouse_x, mouse_y)     # 【新增】[cite: 2]
            hover_exit = rect_exit.collidepoint(mouse_x, mouse_y)

            if mouse_click:
                if hover_start:
                    current_state = STATE_PLAYING
                elif hover_codex:                                     # 【新增】進入圖鑑[cite: 2]
                    previous_state = STATE_MENU
                    current_state = STATE_CODEX
                elif hover_setting:
                    is_settings_open = True
                elif hover_exit:
                    running = False
        else:
            hover_start = hover_codex = hover_setting = hover_save = hover_exit = False

        draw_button(screen, "開始遊戲", rect_start.x, rect_start.y, btn_w, btn_h, hover_start)
        draw_button(screen, "圖 鑑", rect_codex.x, rect_codex.y, btn_w, btn_h, hover_codex) # 【新增】[cite: 2]
        draw_button(screen, "設 定", rect_setting.x, rect_setting.y, btn_w, btn_h, hover_setting)
        draw_button(screen, "存 檔", rect_save.x, rect_save.y, btn_w, btn_h, hover_save)   # 【新增】[cite: 2]
        draw_button(screen, "退出遊戲", rect_exit.x, rect_exit.y, btn_w, btn_h, hover_exit)

    elif current_state == STATE_PLAYING:
        # 繪製當前外型角色 (置中)
        current_color = looks[current_look_index]
        pygame.draw.rect(screen, current_color, (screen_width//2 - 50, screen_height//2 - 50, 100, 100), border_radius=12)

        # 【修改】右上角新增「圖鑑」按鈕[cite: 2]
        top_right_codex = pygame.Rect(screen_width - 210, 20, 90, 40) # 【新增】[cite: 2]
        top_right_btn = pygame.Rect(screen_width - 110, 20, 90, 40)
        
        hover_top_codex = top_right_codex.collidepoint(mouse_x, mouse_y) if not is_settings_open else False # 【新增】[cite: 2]
        hover_top_setting = top_right_btn.collidepoint(mouse_x, mouse_y) if not is_settings_open else False

        if mouse_click:
            if hover_top_codex:                                       # 【新增】[cite: 2]
                previous_state = STATE_PLAYING
                current_state = STATE_CODEX
            elif hover_top_setting:
                is_settings_open = True

        draw_button(screen, "圖鑑", top_right_codex.x, top_right_codex.y, 90, 40, hover_top_codex, bg_color=(50, 80, 110)) # 【新增】[cite: 2]
        draw_button(screen, "設定", top_right_btn.x, top_right_btn.y, 90, 40, hover_top_setting, bg_color=(70, 70, 90))

        # 【繪製 5 格道具欄】
        draw_hotbar(screen, selected_slot, screen_width, screen_height)

    # 【新增】圖鑑畫面繪製分支[cite: 2]
    elif current_state == STATE_CODEX:
        draw_codex_view(screen, screen_width, screen_height, mouse_x, mouse_y, mouse_click)

