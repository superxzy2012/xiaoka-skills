#!/usr/bin/env python3
"""回源补全抖音笔记的 author 字段。

问题：ingest.py 的 author 取自 yt-dlp %(uploader)s，抖音上返回的是作者数字 UID
（如 41506980594）而非昵称，导致 8 篇笔记 author 是数字。
本脚本走 CDP 读页面里的真实昵称回填；读不到的原样保留，不猜。

用法：
    /opt/data/.venv-browser/bin/python dy_author_fix.py            # 查全部待修
    /opt/data/.venv-browser/bin/python dy_author_fix.py --dry      # 只看不改
"""
import os
import re
import sys
import time

sys.path.insert(0, "/opt/data/memories")
import cdp  # noqa: E402

V = "/opt/nas/volume2/2-AI/obsidian_vault/08-抖音视频学习"
DRY = "--dry" in sys.argv


def get_browser():
    """连不上就别让它在 import 阶段炸掉整个脚本。"""
    try:
        return cdp.CDP()
    except Exception as e:
        print(f"❌ 连不上 CDP 端点 {cdp.CDP_URL}：{type(e).__name__}: {e}")
        print("   BOSS 的 Chrome 是否开着？9224→9223 转发是否还在？")
        return None

# author 是纯数字（或空）才需要修 —— 昵称一律不动
BAD = re.compile(r'^\d+$')


def get_aid(path, text):
    """douyin_id 优先；退化到文件名里的 19 位数字。"""
    m = re.search(r'douyin_id: "(\d{19})"', text)
    if m:
        return m.group(1)
    m = re.search(r'(\d{19})', os.path.basename(path))
    return m.group(1) if m else None


JS = """(()=>{
  // 🔴 实测（2026-10-07）：[data-e2e="user-info"] 的 innerText 是【单行】，
  // 形如「清华鑫哥讲AI智能体粉丝19.6万获赞38.5万关注」——昵称和统计数之间没有换行符。
  // 所以不能按 \\n 切行，必须用正则把统计尾巴切掉。
  const ui = document.querySelector('[data-e2e="user-info"]');
  if (!ui) return null;
  const raw = (ui.innerText||'').trim();
  if (!raw) return null;
  // 昵称 = 开头那段，后面跟着「粉丝/获赞/关注/徽章/认证」等统计词
  const m = raw.match(/^(.+?)(?=(粉丝|获赞|关注|徽章|认证|企业号|作品|喜欢))/);
  const nick = (m ? m[1] : raw).trim();
  return nick.length <= 40 ? nick : null;})()"""


def read_nickname(BR, aid, tries=3):
    """抖音详情页异步渲染，实测要 15s+。每轮都校验真的导航到了目标 URL。"""
    want = f"https://www.douyin.com/video/{aid}"
    for i in range(tries):
        BR.goto(want, wait=16)
        # 🔴 页面没真正加载时 document.title 为空且 user-info 还不存在，
        #    只看 nickname 会误判成「读取失败」。先确认落在目标 URL 上。
        at = BR.eval_js("location.href")
        if at and "/video/" not in str(at):
            print(f"     (未跳到视频页，当前 {str(at)[:50]}，重试)")
            time.sleep(4)
            continue
        nick = BR.eval_js(JS)
        if nick:
            return nick
        print(f"     (第{i+1}次读到空，等 4s 重试)")
        time.sleep(4)
    return None


def main():
    BR = get_browser()
    if BR is None:
        return
    # 健康检查必须用「真实标签」，因为 CDP 只在有 target 时才回 Runtime.evaluate。
    # 空会话读什么都返回 None —— 那是假阴性，不是断线。
    BR.new_tab("about:blank", background=True)
    try:
        probe = BR.eval_js("document.title")
    except Exception as e:
        print(f"❌ CDP 会话异常({e})")
        BR.close()
        return
    BR.close_tab()          # 🔴 只关标签，不动连接
    print(f"CDP 连通，当前标签: {str(probe)[:40] or '(about:blank)'}")

    targets = []
    for f in sorted(os.listdir(V)):
        if not f.endswith(".md"):
            continue
        p = os.path.join(V, f)
        head = open(p, encoding="utf-8", errors="ignore").read(600)
        m = re.search(r'^author: "?(.*?)"?$', head, re.M)
        name = (m.group(1) if m else "").strip('"').strip()
        # 只修「author 是纯数字」的——yt-dlp %(uploader)s 在抖音上返回的是
        # 作者数字 UID 而非昵称。author 缺失/为空的是手写笔记，不该动。
        # 只修「author 是纯数字」或标着「待回源」的
        BAD = re.compile(r"^(\d+|待回源)$")
        if not BAD.match(name):
            continue
        aid = get_aid(p, head)
        if not aid:
            print(f"  ⚠️ 无 douyin_id，无法回源：{f[:55]}")
            continue
        targets.append((f, p, name, aid))
        if os.environ.get("ONE"): break

    print(f"待修 {len(targets)} 篇（author 为数字或空）\n")
    if not targets:
        return
    # 全程只开 1 个后台标签，循环复用（BOSS 硬要求：抖音最多 2 页、绝不抢前台）
    BR.new_tab("about:blank", background=True)
    ok = fail = 0
    for f, p, old, aid in targets:
        try:
            nickname = read_nickname(BR, aid)
        except Exception as e:
            print(f"  ❌ {aid} CDP 失败: {e}")
            fail += 1
            continue
        if not nickname:
            print(f"  ❌ {aid} 读到空昵称（页面未就绪），不猜：{f[:45]}")
            fail += 1
            continue
        if BAD.match(nickname):          # 还是数字，不写
            print(f"  ❌ {aid} 页面也只给数字 {nickname}，跳过：{f[:45]}")
            fail += 1
            continue
        print(f"  ✅ {aid}  {old or '(空)'} → {nickname}   {f[:42]}")
        if not DRY:
            t = open(p, encoding="utf-8", errors="ignore").read()
            t = re.sub(r'^author: "?.*?"?$', f'author: "{nickname}"', t,
                       count=1, flags=re.M)
            # 正文头部「> 🎬 抖音 · X ·」也要跟着换，否则和 frontmatter 不一致
            if old:
                t = re.sub(r'(> 🎬 抖音 · )' + re.escape(old) + r'( ·)',
                           r'\g<1>' + nickname + r'\g<2>', t)
            open(p, "w", encoding="utf-8").write(t)
        ok += 1
        time.sleep(2)
    print(f"\n{'DRY-RUN ' if DRY else ''}完成：修正 {ok} 篇，失败 {fail} 篇")
    BR.close()           # 循环结束才关连接（循环内只复用不关）
    print("已关闭自己开的标签")


if __name__ == "__main__":
    main()