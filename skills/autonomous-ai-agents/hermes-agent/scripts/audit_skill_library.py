#!/usr/bin/env python3
"""技能库体检：统计技能数量与 description token 成本，按名字前缀聚合找肥尾。

用法:
  python3 audit_skill_library.py [--dirs d1,d2] [--top 25] [--json out.json]

只读，不改任何文件。--json 输出全部条目，供生成 skills.disabled 列表。
"""
import os, re, sys, json, argparse, collections

DEFAULT_DIRS = ['/opt/data/skills', '/opt/nas/volume2/2-AI/skills']


def parse(path):
    try:
        txt = open(path, encoding='utf-8', errors='replace').read()
    except OSError:
        return None, ''
    m = re.match(r'^---\s*\r?\n(.*?)\r?\n---', txt, re.S)
    fm = m.group(1) if m else ''
    n = re.search(r'^name:\s*(.+)$', fm, re.M)
    d = re.search(r'^description:\s*(.+)$', fm, re.M)
    name = n.group(1).strip().strip('"\'') if n else ''
    desc = d.group(1).strip().strip('"\'') if d else ''
    return name, desc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dirs', default=','.join(DEFAULT_DIRS))
    ap.add_argument('--top', type=int, default=25)
    ap.add_argument('--json', default='')
    a = ap.parse_args()

    rows = {}
    for root_dir in a.dirs.split(','):
        root_dir = root_dir.strip()
        if not os.path.isdir(root_dir):
            print(f'[skip] {root_dir} 不存在')
            continue
        for root, _, files in os.walk(root_dir):
            if 'SKILL.md' not in files:
                continue
            p = os.path.join(root, 'SKILL.md')
            name, desc = parse(p)
            name = name or os.path.basename(root)   # frontmatter 坏了就退化成目录名
            prev = rows.get(name)
            if prev is None or len(desc) > len(prev[1]):
                rows[name] = (p, desc)

    total_chars = sum(len(v[1]) for v in rows.values())
    print(f'唯一技能 {len(rows)} 个 | description 合计 {total_chars} 字符 ≈ {total_chars // 3} tokens')

    groups = collections.defaultdict(lambda: [0, 0])
    for name, (_, desc) in rows.items():
        g = name.split('-')[0] + '-' if '-' in name else '其他'
        groups[g][0] += 1
        groups[g][1] += len(desc)
    print('\n按前缀（肥尾优先）:')
    for g, (c, ch) in sorted(groups.items(), key=lambda kv: -kv[1][1])[:15]:
        print(f'  {ch:6d}ch  {c:3d} 个  {g}')

    print(f'\n描述最长的 {a.top} 个:')
    for name, (_, desc) in sorted(rows.items(), key=lambda kv: -len(kv[1][1]))[:a.top]:
        print(f'  {len(desc):5d}  {name}')

    usage = os.path.join(os.path.dirname(a.dirs.split(',')[0].strip()), '.usage.json')
    if os.path.exists(usage):
        try:
            u = json.load(open(usage, encoding='utf-8'))
            dead = [k for k, v in u.items() if not any(v.get(f) for f in ('view_count', 'use_count', 'loads'))]
            print(f'\n.usage.json: 记录 {len(u)} 条，零使用 {len(dead)} 条（优先砍）')
        except Exception as e:
            print(f'\n.usage.json 读取失败: {e}')

    if a.json:
        json.dump({k: {'path': v[0], 'desc_chars': len(v[1])} for k, v in rows.items()},
                  open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'\n明细已写 {a.json}')


if __name__ == '__main__':
    main()
