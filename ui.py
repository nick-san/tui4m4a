# ui.py

import curses
from config import TAG_MAP

def init_colors():
    """TUIで使用するカラーペアを初期化する"""
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_YELLOW)

def draw_panes(stdscr, app_state):
    """メインの2ペインを描画する"""
    h, w = stdscr.getmaxyx()
    file_pane_width = w // 3
    tag_pane_width = w - file_pane_width
    pane_height = h - 2

    file_win = curses.newwin(pane_height, file_pane_width, 0, 0)
    tag_win = curses.newwin(pane_height, tag_pane_width, 0, file_pane_width)

    active_pane = app_state['active_pane']
    
    file_win.box()
    file_win.addstr(0, 2, " Files ", curses.color_pair(1) | curses.A_BOLD)
    for idx, filename in enumerate(app_state['files']):
        if idx > pane_height - 3: break
        
        prefix = "* " if idx in app_state['marked_files'] else "  "
        suffix = " [+]" if filename in app_state['changes_cache'] else ""
        display_name = f"{prefix}{filename}{suffix}"
        
        style = curses.A_REVERSE if active_pane == 0 and idx == app_state['selected_row'] else curses.A_NORMAL
        file_win.addstr(idx + 1, 1, display_name[:file_pane_width-3], style)

    tag_win.box()
    pane_title = " BATCH EDIT " if len(app_state['marked_files']) > 0 else " Tags "
    tag_win.addstr(0, 2, pane_title, curses.color_pair(1) | curses.A_BOLD)

    tag_keys = list(TAG_MAP.values())
    for idx, key in enumerate(tag_keys):
        is_selected = active_pane == 1 and idx == app_state['selected_tag_idx']
        is_editing = is_selected and app_state['edit_mode']
        
        # --- 修正箇所 ---
        # 'display_tags' を 'tags_buffer' に変更
        value = app_state['edit_buffer'] if is_editing else app_state['tags_buffer'].get(key, "")
        
        line_style = curses.A_NORMAL
        if is_editing: line_style = curses.color_pair(4)
        elif is_selected: line_style = curses.color_pair(2)

        if is_selected or is_editing:
             tag_win.addstr(idx + 1, 1, ' ' * (tag_pane_width - 2), line_style)

        tag_win.addstr(idx + 1, 2, f"{key}: ", line_style | curses.A_BOLD)
        tag_win.addstr(f"{value}", line_style)
    
    stdscr.noutrefresh()
    file_win.noutrefresh()
    tag_win.noutrefresh()
    curses.doupdate()

def draw_statusbar(stdscr, app_state):
    h, w = stdscr.getmaxyx()
    status_message = app_state['status_message']

    status_bar_y = h - 2
    stdscr.addstr(status_bar_y, 0, " " * (w - 1))
    if "Saved" in status_message:
        stdscr.addstr(status_bar_y, 1, status_message, curses.color_pair(3))
    else:
        stdscr.addstr(status_bar_y, 1, status_message)
    app_state['status_message'] = ""

    help_text = "[j/k]Move [h/l]Pane [Space]Mark [Enter]Edit [S]Save [:]Cmd [q]Quit"
    stdscr.addstr(h - 1, 0, help_text.ljust(w - 1), curses.A_REVERSE)

def draw_confirmation_dialog(stdscr, question):
    h, w = stdscr.getmaxyx()
    dialog_h, dialog_w = 5, len(question) + 4
    dialog_y, dialog_x = (h - dialog_h) // 2, (w - dialog_w) // 2

    dialog_win = curses.newwin(dialog_h, dialog_w, dialog_y, dialog_x)
    dialog_win.bkgd(' ', curses.color_pair(5))
    dialog_win.box()
    dialog_win.addstr(1, 2, question)
    dialog_win.addstr(3, 2, "[y]es / [n]o", curses.A_BOLD)
    dialog_win.refresh()

    while True:
        key = dialog_win.getch()
        if key == ord('y'):
            return True
        elif key == ord('n'):
            return False
