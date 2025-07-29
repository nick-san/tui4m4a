# main.py

import curses
import os
import tempfile
import subprocess
from config import TAG_MAP
from file_io import get_m4a_files, get_tags, save_tags
from ui import init_colors, draw_panes, draw_statusbar, draw_confirmation_dialog

def perform_save(changes_cache):
    """変更キャッシュの内容をファイルに書き込む"""
    if not changes_cache:
        return "No changes to save."
    
    count = 0
    for filename, changes in changes_cache.items():
        tags_to_save = get_tags(filename) or {}
        tags_to_save.update(changes)
        save_tags(filename, tags_to_save)
        count += 1
    
    return f"Saved {count} file(s)."

def vim_bulk_edit(stdscr, app_state, tag_to_edit):
    """Vimを起動して選択されたファイルのタグを一括編集する"""
    marked_indices = sorted(list(app_state['marked_files']))
    if not marked_indices:
        app_state['status_message'] = "No files marked for bulk edit."
        return

    selected_files = [app_state['files'][i] for i in marked_indices]

    original_values = []
    for filename in selected_files:
        # --- 修正: 表示用のタグバッファではなく、キャッシュとファイルを元に値を取得 ---
        current_tags = get_tags(filename) or {}
        if filename in app_state['changes_cache']:
            current_tags.update(app_state['changes_cache'][filename])
        original_values.append(current_tags.get(tag_to_edit, ""))

    try:
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt", encoding='utf-8') as tmpfile:
            tmpfile.write("\n".join(original_values))
            tmp_filename = tmpfile.name

        curses.endwin()
        editor = os.getenv('EDITOR', 'vim')
        subprocess.run([editor, tmp_filename])
        
        # cursesを再初期化
        stdscr.clear()
        curses.doupdate()

        with open(tmp_filename, 'r', encoding='utf-8') as tmpfile:
            new_values = [line.strip() for line in tmpfile.readlines()]

        if original_values != new_values and len(new_values) == len(selected_files):
            if draw_confirmation_dialog(stdscr, f"Apply changes to {len(selected_files)} files?"):
                for i, filename in enumerate(selected_files):
                    if filename not in app_state['changes_cache']:
                        app_state['changes_cache'][filename] = {}
                    app_state['changes_cache'][filename][tag_to_edit] = new_values[i]
                app_state['status_message'] = f"Staged bulk changes for {len(selected_files)} files. Press Ctrl+S to save."
            else:
                app_state['status_message'] = "Bulk edit cancelled."
        else:
            app_state['status_message'] = "Bulk edit cancelled or no changes made."

    finally:
        # 一時ファイルを確実に削除
        if 'tmp_filename' in locals() and os.path.exists(tmp_filename):
            os.unlink(tmp_filename)
        # 画面を再描画するためにリフレッシュ
        stdscr.clear()
        stdscr.refresh()


def main(stdscr):
    if curses.has_colors(): init_colors()
    stdscr.keypad(True)
    
    app_state = {
        'files': get_m4a_files('.'), 'selected_row': 0, 'selected_tag_idx': 0,
        'active_pane': 0, 'display_tags': {}, 'status_message': "", 'marked_files': set(),
        'edit_mode': False, 'edit_buffer': "", 'changes_cache': {},
    }

    while True:
        is_batch_mode = len(app_state['marked_files']) > 0
        if app_state['files']:
            current_file = app_state['files'][app_state['selected_row']]
            if not is_batch_mode:
                tags_from_file = get_tags(current_file) or {}
                if current_file in app_state['changes_cache']:
                    tags_from_file.update(app_state['changes_cache'][current_file])
                app_state['display_tags'] = tags_from_file
            elif not app_state['display_tags']:
                 app_state['display_tags'] = { tag: "" for tag in TAG_MAP.values() }

        draw_panes(stdscr, app_state)
        draw_statusbar(stdscr, app_state)

        if app_state['edit_mode']:
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
            if key in [curses.KEY_ENTER, 10, 13]:
                selected_key = list(TAG_MAP.values())[app_state['selected_tag_idx']]
                if is_batch_mode:
                    app_state['display_tags'][selected_key] = app_state['edit_buffer']
                else:
                    current_file = app_state['files'][app_state['selected_row']]
                    if current_file not in app_state['changes_cache']:
                        app_state['changes_cache'][current_file] = {}
                    app_state['changes_cache'][current_file][selected_key] = app_state['edit_buffer']
                app_state['edit_mode'] = False
            elif key in [curses.KEY_BACKSPACE, 127, 263]:
                app_state['edit_buffer'] = app_state['edit_buffer'][:-1]
            elif key >= 32 and key < 127:
                app_state['edit_buffer'] += chr(key)
        
        # --- ここから通常モードのキー処理 ---
        elif key == ord('q'):
            if app_state['changes_cache']:
                app_state['status_message'] = "E37: No write since last change (add ! to override)"
            else:
                break
        elif key == ord('j') or key == curses.KEY_DOWN:
            if app_state['active_pane'] == 0 and app_state['selected_row'] < len(app_state['files']) - 1:
                app_state['selected_row'] += 1
            elif app_state['active_pane'] == 1 and app_state['selected_tag_idx'] < len(TAG_MAP) - 1:
                app_state['selected_tag_idx'] += 1
        elif key == ord('k') or key == curses.KEY_UP:
            if app_state['active_pane'] == 0 and app_state['selected_row'] > 0:
                app_state['selected_row'] -= 1
            elif app_state['active_pane'] == 1 and app_state['selected_tag_idx'] > 0:
                app_state['selected_tag_idx'] -= 1
        elif key == ord('h'):
            app_state['active_pane'] = 0
        elif key == ord('l'):
            app_state['active_pane'] = 1
        elif key == ord(' '):
            if app_state['active_pane'] == 0:
                row = app_state['selected_row']
                if row in app_state['marked_files']:
                    app_state['marked_files'].remove(row)
                else:
                    app_state['marked_files'].add(row)
                if len(app_state['marked_files']) == 1:
                    app_state['display_tags'] = { tag: "" for tag in TAG_MAP.values() }
                elif len(app_state['marked_files']) == 0:
                    app_state['display_tags'] = {}

        elif key in [curses.KEY_ENTER, 10, 13] and app_state['active_pane'] == 1:
            if is_batch_mode:
                selected_key = list(TAG_MAP.values())[app_state['selected_tag_idx']]
                vim_bulk_edit(stdscr, app_state, selected_key)
            else:
                app_state['edit_mode'] = True
                selected_key = list(TAG_MAP.values())[app_state['selected_tag_idx']]
                app_state['edit_buffer'] = app_state['display_tags'].get(selected_key, "")

        elif key == 19: # Ctrl+S
            # バッチ編集のテンプレートの内容をキャッシュに反映
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
