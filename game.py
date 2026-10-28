import pygame
import sys

pygame.init()

# 視窗:自由拉伸
screen_width, screen_height = 800, 600
screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
pygame.display.set_caption("萬徑.歸一 - 介面與道具欄整合系統")

# 音量和外型
volume = 50 
looks = [(255, 50, 50), (50, 255, 50), (50, 50, 255)] # 紅、綠、藍
current_look_index = 0

# 遊戲狀態管理
STATE_MENU = 0
STATE_PLAYING = 1
current_state = STATE_MENU

# 設定選單開啟狀態 (開啟時會暫停背景)
is_settings_open = False

# 5 格道具欄
NUM_SLOTS = 5
selected_slot = 0

# 道具資料(1, 2, 3, 4, 5)
items = [
    {"label": "1", "color": (220, 80, 80)},
    {"label": "2", "color": (80, 180, 80)},
    {"label": "3", "color": (80, 120, 220)},
    {"label": "4", "color": (220, 180, 50)},
    {"label": "5", "color": (160, 80, 220)},
]

# 字體設定
font_title = pygame.font.SysFont("microsoftjhenghei", 40)
font_ui = pygame.font.SysFont("microsoftjhenghei", 20)
font_number = pygame.font.SysFont("arial", 28, bold=True)

# ================= 繪製元件函式 =================

def draw_button(screen, text, x, y, width, height, is_hovered, bg_color=(50, 100, 150)):
    """繪製通用按鈕"""
    color = (bg_color[0]+30, bg_color[1]+30, bg_color[2]+30) if is_hovered else bg_color
    pygame.draw.rect(screen, color, (x, y, width, height), border_radius=8)
    pygame.draw.rect(screen, (255, 255, 255), (x, y, width, height), 2, border_radius=8)
    
    text_surf = font_ui.render(text, True, (255, 255, 255))
    text_rect = text_surf.get_rect(center=(x + width//2, y + height//2))
    screen.blit(text_surf, text_rect)


def draw_hotbar(surface, selected_idx, screen_w, screen_h):
    """繪製 5 格道具欄 (自動根據畫面大小置中擺放於底部)"""
    slot_size = 55       # 每格大小
    padding = 8          # 格子間距
    border_thick = 4     # 外框厚度
    
    total_width = NUM_SLOTS * slot_size + (NUM_SLOTS - 1) * padding + (border_thick * 2)
    total_height = slot_size + (border_thick * 2)
    
    # 根據當前視窗大小動態計算置中位置
    start_x = (screen_w - total_width) // 2
    start_y = screen_h - total_height - 30

    # 1. 外底座黑框
    pygame.draw.rect(surface, (20, 20, 20), (start_x, start_y, total_width, total_height), border_radius=6)

    # 2. 繪製 5 個格子與數字標示
    for i in range(NUM_SLOTS):
        x = start_x + border_thick + i * (slot_size + padding)
        y = start_y + border_thick

        # 底色與邊框
        pygame.draw.rect(surface, (120, 120, 120), (x, y, slot_size, slot_size))
        pygame.draw.rect(surface, (50, 50, 50), (x, y, slot_size, slot_size), 2)

        # 道具底色方塊
        item = items[i]
        icon_rect = pygame.Rect(x + 4, y + 4, slot_size - 8, slot_size - 8)
        pygame.draw.rect(surface, item["color"], icon_rect, border_radius=4)

        # 道具中央的數字 (1 ~ 5)
        label_surf = font_number.render(item["label"], True, (255, 255, 255))
        label_rect = label_surf.get_rect(center=icon_rect.center)
        
        # 數字文字加陰影
        shadow_surf = font_number.render(item["label"], True, (30, 30, 30))
        surface.blit(shadow_surf, (label_rect.x + 2, label_rect.y + 2))
        surface.blit(label_surf, label_rect)

    # 3. 選中高亮外框
    selected_x = start_x + border_thick + selected_idx * (slot_size + padding) - 4
    selected_y = start_y + border_thick - 4
    selected_size = slot_size + 8

    pygame.draw.rect(surface, (0, 0, 0), (selected_x, selected_y, selected_size, selected_size), 4, border_radius=6)
    pygame.draw.rect(surface, (255, 255, 255), (selected_x + 2, selected_y + 2, selected_size - 4, selected_size - 4), 3, border_radius=4)

# ================= 主程式迴圈 =================

clock = pygame.time.Clock()
dragging_volume = False
running = True

while running:
    screen.fill((30, 30, 40)) # 背景底色

    mouse_x, mouse_y = pygame.mouse.get_pos()
    mouse_click = False

    # --- A. 事件處理 ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # 視窗大小拖曳調整
        if event.type == pygame.VIDEORESIZE:
            screen_width, screen_height = event.w, event.h
            screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_click = True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            dragging_volume = False

        # 滑鼠滾輪切換道具 (僅在遊戲進行中且未開啟設定時觸發)
        if event.type == pygame.MOUSEWHEEL and current_state == STATE_PLAYING and not is_settings_open:
            if event.y > 0:
                selected_slot = (selected_slot - 1) % NUM_SLOTS
            elif event.y < 0:
                selected_slot = (selected_slot + 1) % NUM_SLOTS

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if is_settings_open:
                    is_settings_open = False # 關閉設定
                elif current_state == STATE_PLAYING:
                    current_state = STATE_MENU # 退回主畫面

            # 【道具欄鍵盤切換功能】(僅在遊戲中且未開啟設定時生效)
            if current_state == STATE_PLAYING and not is_settings_open:
                if event.key == pygame.K_LEFT:
                    selected_slot = (selected_slot - 1) % NUM_SLOTS
                elif event.key == pygame.K_RIGHT:
                    selected_slot = (selected_slot + 1) % NUM_SLOTS
                elif pygame.K_1 <= event.key <= pygame.K_5:
                    selected_slot = event.key - pygame.K_1

    # --- B. 畫面繪製與互動邏輯 ---

    if current_state == STATE_MENU:
        # 主畫面標題
        title_surf = font_title.render("萬徑.歸一", True, (255, 255, 255))
        screen.blit(title_surf, (screen_width//2 - title_surf.get_width()//2, screen_height//2 - 160))

        # 主畫面三個垂直按鈕
        btn_w, btn_h = 180, 45
        btn_x = screen_width//2 - btn_w//2
        start_y = screen_height//2 - 60

        rect_start = pygame.Rect(btn_x, start_y, btn_w, btn_h)
        rect_setting = pygame.Rect(btn_x, start_y + 60, btn_w, btn_h)
        rect_exit = pygame.Rect(btn_x, start_y + 120, btn_w, btn_h)

        if not is_settings_open:
            hover_start = rect_start.collidepoint(mouse_x, mouse_y)
            hover_setting = rect_setting.collidepoint(mouse_x, mouse_y)
            hover_exit = rect_exit.collidepoint(mouse_x, mouse_y)

            if mouse_click:
                if hover_start:
                    current_state = STATE_PLAYING
                elif hover_setting:
                    is_settings_open = True
                elif hover_exit:
                    running = False
        else:
            hover_start = hover_setting = hover_exit = False

        draw_button(screen, "開始遊戲", rect_start.x, rect_start.y, btn_w, btn_h, hover_start)
        draw_button(screen, "設 定", rect_setting.x, rect_setting.y, btn_w, btn_h, hover_setting)
        draw_button(screen, "退出遊戲", rect_exit.x, rect_exit.y, btn_w, btn_h, hover_exit)

    elif current_state == STATE_PLAYING:
        # 繪製當前外型角色 (置中)
        current_color = looks[current_look_index]
        pygame.draw.rect(screen, current_color, (screen_width//2 - 50, screen_height//2 - 50, 100, 100), border_radius=12)

        # 右上角的「⚙ 設定」按鈕
        top_right_btn = pygame.Rect(screen_width - 110, 20, 90, 40)
        hover_top_setting = top_right_btn.collidepoint(mouse_x, mouse_y) if not is_settings_open else False

        if mouse_click and hover_top_setting:
            is_settings_open = True # 開啟設定選單 (暫停畫面)

        draw_button(screen, "⚙ 設定", top_right_btn.x, top_right_btn.y, 90, 40, hover_top_setting, bg_color=(70, 70, 90))

        # 【繪製 5 格道具欄】
        draw_hotbar(screen, selected_slot, screen_width, screen_height)

    # 共用設定選單彈窗 (Settings Overlay)
    if is_settings_open:
        # 半透明背景遮罩
        overlay = pygame.Surface((screen_width, screen_height))
        overlay.set_alpha(160)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # 選單視窗主體
        modal_w, modal_h = 460, 370
        modal_x = screen_width//2 - modal_w//2
        modal_y = screen_height//2 - modal_h//2
        pygame.draw.rect(screen, (45, 45, 60), (modal_x, modal_y, modal_w, modal_h), border_radius=12)
        pygame.draw.rect(screen, (255, 255, 255), (modal_x, modal_y, modal_w, modal_h), 2, border_radius=12)

        # 標題
        settings_title = font_title.render("系統設定", True, (255, 215, 0))
        screen.blit(settings_title, (screen_width//2 - settings_title.get_width()//2, modal_y + 20))

        # 音效控制 (Slider)
        vol_label = font_ui.render(f"音量大小: {volume}%", True, (255, 255, 255))
        screen.blit(vol_label, (modal_x + 40, modal_y + 90))
        
        slider_x, slider_y, slider_w = modal_x + 180, modal_y + 95, 220
        pygame.draw.rect(screen, (80, 80, 80), (slider_x, slider_y, slider_w, 12), border_radius=6)
        fill_w = int((volume / 100) * slider_w)
        if fill_w > 0:
            pygame.draw.rect(screen, (100, 255, 100), (slider_x, slider_y, fill_w, 12), border_radius=6)
        pygame.draw.circle(screen, (255, 255, 255), (slider_x + fill_w, slider_y + 6), 10)

        slider_hitbox = pygame.Rect(slider_x - 5, slider_y - 10, slider_w + 10, 32)
        if mouse_click and slider_hitbox.collidepoint(mouse_x, mouse_y):
            dragging_volume = True

        if dragging_volume:
            rel_x = max(0, min(mouse_x - slider_x, slider_w))
            volume = int((rel_x / slider_w) * 100)

        # 畫面大小控制
        res_label = font_ui.render(f"視窗大小: {screen_width} x {screen_height}", True, (255, 255, 255))
        screen.blit(res_label, (modal_x + 40, modal_y + 150))
        
        res_hint = font_ui.render("(可直接拖動視窗邊框任意調整大小)", True, (160, 160, 160))
        screen.blit(res_hint, (modal_x + 40, modal_y + 180))

        btn_800 = pygame.Rect(modal_x + 280, modal_y + 145, 65, 30)
        btn_1024 = pygame.Rect(modal_x + 355, modal_y + 145, 65, 30)
        
        h_800 = btn_800.collidepoint(mouse_x, mouse_y)
        h_1024 = btn_1024.collidepoint(mouse_x, mouse_y)

        if mouse_click:
            if h_800:
                screen_width, screen_height = 800, 600
                screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
            elif h_1024:
                screen_width, screen_height = 1024, 768
                screen = pygame.display.set_mode((1024, 768), pygame.RESIZABLE)

        draw_button(screen, "800", btn_800.x, btn_800.y, 65, 30, h_800)
        draw_button(screen, "1024", btn_1024.x, btn_1024.y, 65, 30, h_1024)

        # 更換外型控制
        look_label = font_ui.render("更換外型 / 顏色:", True, (255, 255, 255))
        screen.blit(look_label, (modal_x + 40, modal_y + 225))

        pygame.draw.rect(screen, looks[current_look_index], (modal_x + 200, modal_y + 220, 30, 30), border_radius=4)
        
        btn_change_look = pygame.Rect(modal_x + 250, modal_y + 220, 110, 30)
        h_look = btn_change_look.collidepoint(mouse_x, mouse_y)
        if mouse_click and h_look:
            current_look_index = (current_look_index + 1) % len(looks)

        draw_button(screen, "切換外型", btn_change_look.x, btn_change_look.y, 110, 30, h_look)

        # 底部按鈕：[回到主選單] 與 [確定關閉]
        btn_menu = pygame.Rect(modal_x + 50, modal_y + 300, 160, 40)
        btn_close = pygame.Rect(modal_x + 250, modal_y + 300, 160, 40)

        h_menu = btn_menu.collidepoint(mouse_x, mouse_y)
        h_close = btn_close.collidepoint(mouse_x, mouse_y)

        if mouse_click:
            if h_menu:
                current_state = STATE_MENU  # 返回主選單
                is_settings_open = False     # 關閉設定視窗
            elif h_close:
                is_settings_open = False     # 關閉設定視窗

        draw_button(screen, "回到主選單", btn_menu.x, btn_menu.y, 160, 40, h_menu, bg_color=(90, 90, 110))
        draw_button(screen, "確定關閉", btn_close.x, btn_close.y, 160, 40, h_close, bg_color=(180, 60, 60))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()