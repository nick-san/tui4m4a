# main.py

import curses
import os
from config import TAG_MAP
from file_io import get_m4a_files, get_tags, save_tags
from ui import init_colors, draw_panes, draw_statusbar

# --- 修正: perform_saveはキャッシュを書き込むだけのシンプルな作りに ---
def perform_save(changes_cache):
    """変更キャッシュの内容をファイルに書き込む"""
    if not changes_cache:
        return "No changes to save."
    
    count = 0
    for filename, changes in changes_cache.items():
        # 元のタグを読み込み、変更をマージしてから保存
        tags_to_save = get_tags(filename) or {}
        tags_to_save.update(changes)
        save_tags(filename, tags_to_save)
        count += 1
    
    return f"Saved {count} file(s)."

def main(stdscr):
    if curses.has_colors():
        init_colors()
    stdscr.keypad(True)
    
    app_state = {
        'files': get_m4a_files('.'), 'selected_row': 0, 'selected_tag_idx': 0,
        'active_pane': 0, 'display_tags': {}, 'status_message': "", 'marked_files': set(),
        'edit_mode': False, 'edit_buffer': "",
        'changes_cache': {},
    }

    while True:
        # (タグ表示ロジックは変更なし)
        is_batch_mode = len(app_state['marked_files']) > 0
        if app_state['files']:
            current_file = app_state['files'][app_state['selected_row']]
            
            # バッチモードでなく、かつ表示中のタグ情報が古い場合のみ更新
            if not is_batch_mode:
                tags_from_file = get_tags(current_file) or {}
                if current_file in app_state['changes_cache']:
                    tags_from_file.update(app_state['changes_cache'][current_file])
                app_state['display_tags'] = tags_from_file

        draw_panes(stdscr, app_state)
        draw_statusbar(stdscr, app_state)

        if app_state['edit_mode']:
            # (編集モードのカーソル表示は変更なし)
            curses.curs_set(1)
            h, w = stdscr.getmaxyx()
            tag_keys = list(TAG_MAP.values())
            selected_key = tag_keys[app_state['selected_tag_idx']]
            cursor_y = app_state['selected_tag_idx'] + 1
            cursor_x = (w // 3) + 2 + len(selected_key) + 2 + len(app_state['edit_buffer'])
            stdscr.move(cursor_y, cursor_x)
        else:
            curses.curs_set(0)

        key = stdscr.getch()

        if app_state['edit_mode']:
            # (編集モードのキー処理は変更なし)
            if key in [curses.KEY_ENTER, 10, 13]:
                # 編集内容はキャッシュに保存
                selected_key = list(TAG_MAP.values())[app_state['selected_tag_idx']]
                
                # --- 修正: 一括編集と単一編集でキャッシュへの書き込み方を統一 ---
                if is_batch_mode:
                    # バッチモード時はdisplay_tags(テンプレート)を直接編集
                     app_state['display_tags'][selected_key] = app_state['edit_buffer']
                else:
                    # シングルモード時はキャッシュへ
                    current_file = app_state['files'][app_state['selected_row']]
                    if current_file not in app_state['changes_cache']:
                        app_state['changes_cache'][current_file] = {}
                    app_state['changes_cache'][current_file][selected_key] = app_state['edit_buffer']
                
                app_state['edit_mode'] = False
            elif key in [curses.KEY_BACKSPACE, 127, 263]:
                app_state['edit_buffer'] = app_state['edit_buffer'][:-1]
            elif key >= 32 and key < 127:
                app_state['edit_buffer'] += chr(key)
            continue

        # --- 通常モードのキー処理 ---
        # (j, k, h, l, space, q のキー処理は変更なし)
        if key == ord('q'):
            if app_state['changes_cache']:
                app_state['status_message'] = "E37: No write since last change (add ! to override)"
            else:
                break
        elif key == ord('j') or key == curses.KEY_DOWN:
            if app_state['active_pane'] == 0 and app_state['selected_row'] < len(app_state['files']) - 1: app_state['selected_row'] += 1
            elif app_state['active_pane'] == 1 and app_state['selected_tag_idx'] < len(TAG_MAP) - 1: app_state['selected_tag_idx'] += 1
        elif key == ord('k') or key == curses.KEY_UP:
            if app_state['active_pane'] == 0 and app_state['selected_row'] > 0: app_state['selected_row'] -= 1
            elif app_state['active_pane'] == 1 and app_state['selected_tag_idx'] > 0: app_state['selected_tag_idx'] -= 1
        elif key == ord('h'): app_state['active_pane'] = 0
        elif key == ord('l'): app_state['active_pane'] = 1
        elif key == ord(' '):
            if app_state['active_pane'] == 0:
                row = app_state['selected_row']
                if row in app_state['marked_files']:
                    app_state['marked_files'].remove(row)
                else:
                    app_state['marked_files'].add(row)
                # バッチモードに入ったら、右ペインの表示をクリアする
                if len(app_state['marked_files']) == 1:
                    app_state['display_tags'] = {}

        elif key in [curses.KEY_ENTER, 10, 13] and app_state['active_pane'] == 1:
            app_state['edit_mode'] = True
            selected_key = list(TAG_MAP.values())[app_state['selected_tag_idx']]
            app_state['edit_buffer'] = app_state['display_tags'].get(selected_key, "")

        elif key == 19: # Ctrl+S
            # --- 修正: 保存前にバッチ編集の内容をキャッシュに反映させる ---
            if is_batch_mode:
                tags_to_apply = {k: v for k, v in app_state['display_tags'].items() if v}
                for idx in app_state['marked_files']:
                    filename = app_state['files'][idx]
                    if filename not in app_state['changes_cache']:
                        app_state['changes_cache'][filename] = {}
                    app_state['changes_cache'][filename].update(tags_to_apply)
            
            app_state['status_message'] = perform_save(app_state['changes_cache'])
            app_state['changes_cache'].clear()
            if is_batch_mode: app_state['marked_files'].clear()
        
        elif key == ord(':'):
            h, w = stdscr.getmaxyx()
            curses.curs_set(1)
            stdscr.addstr(h-1, 0, " " * (w-1), curses.A_REVERSE)
            stdscr.addstr(h-1, 0, ":", curses.A_REVERSE)
            curses.echo()
            command_str = stdscr.getstr(h-1, 1, 20).decode('utf-8')
            curses.noecho(); curses.curs_set(0)
            
            if command_str == 'wq':
                # --- 修正: :wqでもバッチ編集をキャッシュに反映させる ---
                if is_batch_mode:
                    tags_to_apply = {k: v for k, v in app_state['display_tags'].items() if v}
                    for idx in app_state['marked_files']:
                        filename = app_state['files'][idx]
                        if filename not in app_state['changes_cache']:
                            app_state['changes_cache'][filename] = {}
                        app_state['changes_cache'][filename].update(tags_to_apply)

                app_state['status_message'] = perform_save(app_state['changes_cache'])
                app_state['changes_cache'].clear()
                draw_statusbar(stdscr, app_state)
                stdscr.refresh()
                curses.napms(500)
                break
            elif command_str == 'q!':
                break
            elif command_str == 'q':
                if app_state['changes_cache']:
                    app_state['status_message'] = "E37: No write since last change (add ! to override)"
                else:
                    break
            else: app_state['status_message'] = f"Not an editor command: {command_str}"

if __name__ == '__main__':
    curses.wrapper(main)
