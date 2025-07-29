# file_io.py

import os
from mutagen.mp4 import MP4
from config import TAG_MAP, REVERSE_TAG_MAP

def get_m4a_files(path):
    """カレントディレクトリのM4Aファイル一覧を取得"""
    files = [f for f in os.listdir(path) if f.lower().endswith('.m4a')]
    return sorted(files)

def get_tags(filename):
    """mutagenを使ってM4Aファイルのタグを読み込む"""
    try:
        audio = MP4(filename)
        tags = {}
        for key, name in TAG_MAP.items():
            value = audio.get(key)
            if value is not None:
                if key == 'trkn':
                    tags[name] = f"{value[0]}/{value[1]}" if len(value) > 1 and value[1] > 0 else str(value[0])
                else:
                    tags[name] = str(value[0])
            else:
                tags[name] = ""
        return tags
    except Exception:
        return None

def save_tags(filename, tags_to_save):
    """mutagenを使ってM4Aファイルにタグを書き込む"""
    audio = MP4(filename)
    for name, value in tags_to_save.items():
        key = REVERSE_TAG_MAP.get(name)
        if key:
            if not value:
                if key in audio:
                    del audio[key]
            else:
                if key == 'trkn':
                    try:
                        if '/' in value:
                            track, total = map(int, value.split('/'))
                            audio[key] = [(track, total)]
                        else:
                            audio[key] = [(int(value), 0)]
                    except (ValueError, IndexError):
                        pass
                else:
                    audio[key] = [value]
    audio.save()
