import sys
import pygame

# 初始化 Pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("《陪伴日記》拖放解謎 - 佔位測試")
clock = pygame.time.Clock()


# 載入支援繁體中文的系統字型
def get_font(size):
  for font_name in ["microsoftjhenghei", "pingfangtc", "notosanstc", "simhei"]:
    path = pygame.font.match_font(font_name)
    if path:
      return pygame.font.Font(path, size)
  return pygame.font.SysFont(None, size)


font_title = get_font(32)
font_item = get_font(22)
font_msg = get_font(22)

# 顏色定義
BG_COLOR = (28, 28, 32)
BORDER_COLOR = (200, 200, 200)
FIXED_SLOT_BG = (55, 60, 70)
EMPTY_SLOT_BG = (40, 42, 48)
ITEM_BG = (75, 115, 165)
ITEM_DRAG_BG = (105, 155, 215)
BTN_BG = (65, 65, 75)
BTN_HOVER_BG = (90, 90, 105)
TEXT_COLOR = (240, 240, 240)
SUCCESS_COLOR = (100, 220, 120)
ERROR_COLOR = (235, 95, 95)


class DraggablePage:

  def __init__(self, page_id, label, home_x, home_y, w=130, h=70):
    self.page_id = page_id
    self.label = label
    self.home_pos = (home_x, home_y)
    self.rect = pygame.Rect(home_x, home_y, w, h)
    self.dragging = False
    self.offset_x = 0
    self.offset_y = 0
    self.snapped_slot = None  # 紀錄目前吸附在哪個槽位

  def reset(self):
    self.rect.topleft = self.home_pos
    self.dragging = False
    self.snapped_slot = None


class EmptySlot:

  def __init__(self, slot_index, expected_page_id, x, y, w=130, h=70):
    self.slot_index = slot_index
    self.expected_page_id = expected_page_id
    self.rect = pygame.Rect(x, y, w, h)
    self.occupant = None  # 紀錄目前放入此槽位的 DraggablePage


def setup_puzzle():
  # 固定的頁面 (Page 1, Page 3, Page 6)
  fixed_pages = [
      {"label": "Page 1", "rect": pygame.Rect(155, 140, 130, 70)},
      {"label": "Page 3", "rect": pygame.Rect(515, 140, 130, 70)},
      {"label": "Page 6", "rect": pygame.Rect(515, 245, 130, 70)},
  ]

  # 三個可放入的空槽 (對應答案順序: 第2頁, 第4頁, 第5頁)
  slots = [
      EmptySlot(0, 2, 335, 140),  # 第一排中間
      EmptySlot(1, 4, 155, 245),  # 第二排左側
      EmptySlot(2, 5, 335, 245),  # 第二排中間
  ]

  # 下方待拖曳的三個素材
  items = [
      DraggablePage(2, "[第2頁]", 155, 410),
      DraggablePage(4, "[第4頁]", 335, 410),
      DraggablePage(5, "[第5頁]", 515, 410),
  ]
  return fixed_pages, slots, items


fixed_pages, slots, items = setup_puzzle()

# 按鈕區域
btn_confirm = pygame.Rect(460, 515, 100, 42)
btn_reset = pygame.Rect(580, 515, 100, 42)

dragging_item = None
status_message = ""
status_color = TEXT_COLOR

running = True
while running:
  mouse_pos = pygame.mouse.get_pos()

  for event in pygame.event.get():
    if event.type == pygame.QUIT:
      running = False

    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
      # 1. 檢查是否點擊下方素材（反向遍歷以優先選取最上層圖層）
      for item in reversed(items):
        if item.rect.collidepoint(event.pos):
          dragging_item = item
          item.dragging = True
          item.offset_x = item.rect.x - event.pos[0]
          item.offset_y = item.rect.y - event.pos[1]

          # 若原本在某個槽位中，先解除該槽位佔用
          if item.snapped_slot is not None:
            item.snapped_slot.occupant = None
            item.snapped_slot = None

          # 將正在拖曳的物件移至列表最後方（繪製在最上層）
          items.remove(item)
          items.append(item)
          status_message = ""
          break

      # 2. 檢查 [確認] 按鈕
      if btn_confirm.collidepoint(event.pos):
        if any(slot.occupant is None for slot in slots):
          status_message = "請先將所有素材拖入空槽中！"
          status_color = ERROR_COLOR
        elif all(
            slot.occupant.page_id == slot.expected_page_id for slot in slots
        ):
          status_message = "順序正確！《陪伴日記》已還原。"
          status_color = SUCCESS_COLOR
        else:
          status_message = "頁碼順序不對，請再檢查一下。"
          status_color = ERROR_COLOR

      # 3. 檢查 [重設] 按鈕
      elif btn_reset.collidepoint(event.pos):
        for slot in slots:
          slot.occupant = None
        for item in items:
          item.reset()
        status_message = ""

    elif event.type == pygame.MOUSEMOTION:
      if dragging_item is not None:
        dragging_item.rect.x = event.pos[0] + dragging_item.offset_x
        dragging_item.rect.y = event.pos[1] + dragging_item.offset_y

    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
      if dragging_item is not None:
        dragging_item.dragging = False
        snapped = False

        # 檢查放開時是否與任一空槽重疊
        for slot in slots:
          if dragging_item.rect.colliderect(slot.rect):
            # 若該槽位原本已有其他素材，將舊素材退回下方原位
            if slot.occupant is not None:
              slot.occupant.reset()

            dragging_item.rect.center = slot.rect.center
            dragging_item.snapped_slot = slot
            slot.occupant = dragging_item
            snapped = True
            break

        # 若未放入任何空槽，則自動彈回下方初始位置
        if not snapped:
          dragging_item.reset()

        dragging_item = None

  # --- 畫面繪製 ---
  screen.fill(BG_COLOR)

  # 外框線
  pygame.draw.rect(
      screen, BORDER_COLOR, (60, 30, WIDTH - 120, HEIGHT - 60), width=2
  )

  # 標題
  title_surf = font_title.render("《陪伴日記》", True, TEXT_COLOR)
  screen.blit(title_surf, title_surf.get_rect(center=(WIDTH // 2, 80)))

  # Page 1, 3, 6
  for fp in fixed_pages:
    pygame.draw.rect(screen, FIXED_SLOT_BG, fp["rect"], border_radius=6)
    pygame.draw.rect(
        screen, BORDER_COLOR, fp["rect"], width=2, border_radius=6
    )
    txt = font_item.render(fp["label"], True, TEXT_COLOR)
    screen.blit(txt, txt.get_rect(center=fp["rect"].center))

  # [空槽]
  for slot in slots:
    pygame.draw.rect(screen, EMPTY_SLOT_BG, slot.rect, border_radius=6)
    pygame.draw.rect(
        screen, (140, 140, 150), slot.rect, width=2, border_radius=6
    )
    if slot.occupant is None:
      txt = font_item.render("[空槽]", True, (150, 150, 160))
      screen.blit(txt, txt.get_rect(center=slot.rect.center))

  # 中間分隔線
  pygame.draw.line(screen, BORDER_COLOR, (100, 355), (WIDTH - 100, 355), width=2)

  # [第2頁], [第4頁], [第5頁]
  for item in items:
    bg = ITEM_DRAG_BG if item.dragging else ITEM_BG
    pygame.draw.rect(screen, bg, item.rect, border_radius=6)
    pygame.draw.rect(screen, TEXT_COLOR, item.rect, width=2, border_radius=6)
    txt = font_item.render(item.label, True, TEXT_COLOR)
    screen.blit(txt, txt.get_rect(center=item.rect.center))

  # [確認] 與 [重設] 按鈕
  for btn_rect, label in [(btn_confirm, "[確認]"), (btn_reset, "[重設]")]:
    color = BTN_HOVER_BG if btn_rect.collidepoint(mouse_pos) else BTN_BG
    pygame.draw.rect(screen, color, btn_rect, border_radius=6)
    pygame.draw.rect(screen, BORDER_COLOR, btn_rect, width=1, border_radius=6)
    txt = font_item.render(label, True, TEXT_COLOR)
    screen.blit(txt, txt.get_rect(center=btn_rect.center))

  # 繪製狀態提示文字
  if status_message:
    msg_surf = font_msg.render(status_message, True, status_color)
    screen.blit(msg_surf, (100, 522))

  pygame.display.flip()
  clock.tick(60)

pygame.quit()
sys.exit()
