# config.py

# タグの内部キーと表示名の対応
TAG_MAP = {
    '©nam': 'Title',
    '©ART': 'Artist',
    '©alb': 'Album',
    'aART': 'Album Artist',
    '©day': 'Year',
    'trkn': 'Track',
    '©gen': 'Genre',
}

# 保存時に逆引きするためのマップ
REVERSE_TAG_MAP = {v: k for k, v in TAG_MAP.items()}
