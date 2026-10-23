#!/usr/bin/env python3
"""列出 Chromium/Electron userData 下所有分区的 token 类 cookie 及长度。

用法（在源机器上跑，只读，不影响运行中的 app）:
    python3 dump_electron_cookies.py ~/Library/Application\ Support/chat2api
    python3 dump_electron_cookies.py <userData> --dump glm-session   # 打印该分区完整字段

判读:
    vlen > 40 且 jw t=True  -> 明文 refresh token / JWT，可直接注入目标端
    vlen == 0 且 elen > 0   -> 密文（access token 常见），别指望跨机复用
"""
import base64
import json
import os
import sqlite3
import sys

PAT = ('%token%', '%session%', '%auth%', '%jwt%', '%sid%', '%ticket%', '%pass%')


def jwt_exp(v: str):
    try:
        p = v.split('.')[1]
        p += '=' * (-len(p) % 4)
        d = json.loads(base64.urlsafe_b64decode(p))
        return d.get('exp')
    except Exception:
        return None


def connect(path: str):
    return sqlite3.connect(f'file:{path}?mode=ro', uri=True, timeout=5)


def scan(root: str, dump_part: str | None):
    parts = []
    pdir = os.path.join(root, 'Partitions')
    if os.path.isdir(pdir):
        parts = sorted(os.listdir(pdir))
    targets = [(p, os.path.join(pdir, p, 'Cookies')) for p in parts]
    targets.append(('(default)', os.path.join(root, 'Cookies')))

    for part, db in targets:
        if not os.path.exists(db):
            continue
        if dump_part and part != dump_part:
            continue
        try:
            con = connect(db)
            cur = con.cursor()
            if dump_part:
                cur.execute('select host_key,name,value,length(value),length(encrypted_value),path,is_secure,is_httponly from cookies order by host_key')
                for row in cur.fetchall():
                    print(f'[{part}] host={row[0]} name={row[1]} vlen={row[3]} elen={row[4]} secure={row[6]} http={row[7]}')
                    if row[2]:
                        print(f'    value={row[2][:120]}')
            else:
                where = ' or '.join("name like ?" for _ in PAT)
                cur.execute(f'select host_key,name,value,length(value),length(encrypted_value) from cookies where {where} order by length(value) desc', PAT)
                rows = [r for r in cur.fetchall() if (r[3] or 0) > 40 or (r[4] or 0) > 0]
                if rows:
                    print(f'--- {part} ({len(rows)}) ---')
                for host, name, val, vlen, elen in rows:
                    exp = jwt_exp(val) if val and val.count('.') == 2 else None
                    tag = 'PLAINTEXT' if (vlen or 0) > 40 else 'ENCRYPTED'
                    extra = f' exp={exp}' if exp else ''
                    print(f'  {tag:9} {host:28} {name:34} vlen={vlen} elen={elen}{extra}')
            con.close()
        except Exception as e:
            print(f'[{part}] ERR {type(e).__name__}: {e}')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    root = os.path.expanduser(sys.argv[1])
    dump = None
    if '--dump' in sys.argv:
        dump = sys.argv[sys.argv.index('--dump') + 1]
    scan(root, dump)
