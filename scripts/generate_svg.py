#!/usr/bin/env python3
"""
纯第一方 GitHub 统计 SVG 生成器
仅使用 Python 标准库 + GitHub 官方 API (api.github.com)
不依赖任何第三方服务或库
"""

import json
import os
import sys
import urllib.request
import urllib.parse
from collections import Counter
from datetime import datetime, timedelta

USERNAME = "BunNiuNai"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": USERNAME,
}

# 主题色（浅色主题，适配白色 GitHub 背景）
BG = "#ffffff"
TITLE = "#667eea"
ICON = "#667eea"
TEXT = "#1f2937"
SUBTLE = "#6b7280"
STROKE = "#e5e7eb"
FIRE = "#f59e0b"
GREEN = "#10b981"

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "svg")


def api_get(url):
    """调用 GitHub 官方 API"""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_user():
    return api_get(f"https://api.github.com/users/{USERNAME}")


def fetch_repos():
    repos = []
    page = 1
    while True:
        data = api_get(
            f"https://api.github.com/users/{USERNAME}/repos?per_page=100&page={page}&type=owner&sort=updated"
        )
        if not data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1
    return repos


def search_count(query):
    """用 GitHub Search API 统计数量"""
    url = f"https://api.github.com/search/issues?q={urllib.parse.quote(query)}"
    try:
        data = api_get(url)
        return data.get("total_count", 0)
    except Exception:
        return 0


def search_commits_count():
    url = f"https://api.github.com/search/commits?q=author:{USERNAME}"
    req = urllib.request.Request(url, headers={**HEADERS, "Accept": "application/vnd.github.cloak-preview+json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data.get("total_count", 0)
    except Exception:
        return 0


def fetch_contributions_streak():
    """抓取 GitHub 官方贡献页面 HTML，计算连续提交天数和总贡献数"""
    try:
        url = f"https://github.com/users/{USERNAME}/contributions"
        req = urllib.request.Request(url, headers={"User-Agent": USERNAME})
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8")

        # 解析贡献天数
        import re
        # 匹配 data-count="N" data-date="YYYY-MM-DD"
        pattern = r'data-count="(\d+)" data-date="(\d{4}-\d{2}-\d{2})"'
        matches = re.findall(pattern, html)

        if not matches:
            return 0, 0, 0

        dates = []
        total = 0
        for count_str, date_str in matches:
            count = int(count_str)
            total += count
            if count > 0:
                dates.append(date_str)

        if not dates:
            return 0, 0, total

        dates.sort()

        # 计算当前连续天数（从最后一天往前数）
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        current_streak = 0
        # 从最后有贡献的日期开始往前数
        last_date = dates[-1]
        if last_date >= yesterday:
            current_streak = 0
            check_date = datetime.now()
            for _ in range(400):
                ds = check_date.strftime("%Y-%m-%d")
                if ds in dates:
                    current_streak += 1
                    check_date -= timedelta(days=1)
                else:
                    break

        # 计算最长连续天数
        longest_streak = 0
        temp_streak = 0
        prev_date = None
        for d in dates:
            if prev_date:
                diff = (datetime.strptime(d, "%Y-%m-%d") - datetime.strptime(prev_date, "%Y-%m-%d")).days
                if diff == 1:
                    temp_streak += 1
                else:
                    temp_streak = 1
            else:
                temp_streak = 1
            longest_streak = max(longest_streak, temp_streak)
            prev_date = d

        return current_streak, longest_streak, total
    except Exception as e:
        print(f"Warning: Could not fetch contributions: {e}", file=sys.stderr)
        return 0, 0, 0


def escape_xml(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def generate_stats_svg(user, repos, commits, prs, issues, total_stars, total_forks):
    """生成主统计卡片 SVG"""
    width = 420
    height = 200

    rows = [
        ("★", "星标总数", f"{total_stars}"),
        ("⬇", "总提交数", f"{commits}"),
        ("⑂", "合并 PR", f"{prs}"),
        ("⚑", "Issue 数", f"{issues}"),
        ("📦", "仓库数", f"{user['public_repos']}"),
        ("👥", "关注者", f"{user['followers']}"),
    ]

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" rx="8" fill="{BG}" stroke="{STROKE}" stroke-width="1"/>
  <text x="20" y="32" fill="{TITLE}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="18" font-weight="700">📊 GitHub 统计</text>
  <line x1="20" y1="42" x2="{width-20}" y2="42" stroke="{STROKE}" stroke-width="0.5" opacity="0.3"/>
'''

    y_start = 66
    row_h = 24
    for i, (icon, label, value) in enumerate(rows):
        y = y_start + i * row_h
        svg += f'''  <text x="24" y="{y}" fill="{ICON}" font-family="Segoe UI, sans-serif" font-size="14">{icon}</text>
  <text x="48" y="{y}" fill="{TEXT}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="13">{escape_xml(label)}</text>
  <text x="{width-24}" y="{y}" fill="{TEXT}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="13" text-anchor="end" font-weight="600">{value}</text>
'''

    svg += "</svg>"
    return svg


def generate_top_langs_svg(repos):
    """生成 Top Languages SVG"""
    lang_counter = Counter()

    # 按语言统计仓库数（非 fork 仓库）
    for r in repos:
        if r.get("language") and not r.get("fork"):
            lang_counter[r["language"]] += 1

    total = sum(lang_counter.values())
    if total == 0:
        lang_counter["Python"] = 1
        lang_counter["Java"] = 1
        total = 2

    top_langs = lang_counter.most_common(6)

    width = 420
    height = 200

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" rx="8" fill="{BG}" stroke="{STROKE}" stroke-width="1"/>
  <text x="20" y="32" fill="{TITLE}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="18" font-weight="700">🔧 最常用语言</text>
  <line x1="20" y1="42" x2="{width-20}" y2="42" stroke="{STROKE}" stroke-width="0.5" opacity="0.3"/>
'''

    y_start = 62
    bar_x = 110
    bar_max_w = width - bar_x - 24
    row_h = 24

    # 语言颜色映射
    lang_colors = {
        "Python": "#3776AB",
        "Java": "#ED8B00",
        "JavaScript": "#F7DF1E",
        "TypeScript": "#3178C6",
        "HTML": "#E34F26",
        "CSS": "#1572B6",
        "Shell": "#89E051",
        "C": "#555555",
        "C++": "#00599C",
        "Go": "#00ADD8",
        "Rust": "#DEA584",
        "Jupyter Notebook": "#DA5B0B",
        "Batchfile": "#C1F12E",
    }

    for i, (lang, count) in enumerate(top_langs):
        pct = round(count / total * 100, 1)
        bar_w = max(int(bar_max_w * count / max(c for _, c in top_langs)), 4)
        color = lang_colors.get(lang, "#764ba2")
        y = y_start + i * row_h

        svg += f'''  <text x="24" y="{y}" fill="{TEXT}" font-family="Segoe UI, sans-serif" font-size="12">{escape_xml(lang)}</text>
  <rect x="{bar_x}" y="{y-10}" width="{bar_w}" height="12" rx="2" fill="{color}" opacity="0.8"/>
  <text x="{width-24}" y="{y}" fill="{SUBTLE}" font-family="Segoe UI, sans-serif" font-size="11" text-anchor="end">{pct}%</text>
'''

    svg += "</svg>"
    return svg


def generate_streak_svg(current, longest, total_contrib):
    """生成连续提交 SVG"""
    width = 420
    height = 120

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" rx="8" fill="{BG}" stroke="{STROKE}" stroke-width="1"/>

  <!-- 标题 -->
  <text x="{width//2}" y="28" fill="{TITLE}" font-family="Segoe UI, sans-serif" font-size="14" font-weight="700" text-anchor="middle">🔥 GitHub 连续提交</text>

  <!-- 当前连续 -->
  <text x="70" y="68" fill="{TEXT}" font-family="Segoe UI, sans-serif" font-size="28" font-weight="700" text-anchor="middle">{current}</text>
  <text x="70" y="88" fill="{SUBTLE}" font-family="Segoe UI, sans-serif" font-size="11" text-anchor="middle">当前连续（天）</text>

  <!-- 最长连续 -->
  <text x="210" y="68" fill="{FIRE}" font-family="Segoe UI, sans-serif" font-size="28" font-weight="700" text-anchor="middle">{longest}</text>
  <text x="210" y="88" fill="{SUBTLE}" font-family="Segoe UI, sans-serif" font-size="11" text-anchor="middle">最长连续（天）</text>

  <!-- 总贡献 -->
  <text x="350" y="68" fill="{GREEN}" font-family="Segoe UI, sans-serif" font-size="28" font-weight="700" text-anchor="middle">{total_contrib}</text>
  <text x="350" y="88" fill="{SUBTLE}" font-family="Segoe UI, sans-serif" font-size="11" text-anchor="middle">总贡献数</text>

  <!-- 分割线 -->
  <line x1="140" y1="50" x2="140" y2="100" stroke="{STROKE}" stroke-width="0.5" opacity="0.2"/>
  <line x1="280" y1="50" x2="280" y2="100" stroke="{STROKE}" stroke-width="0.5" opacity="0.2"/>
</svg>'''
    return svg


def generate_typing_svg():
    """生成标题 SVG"""
    lines = ["👋 Hi, I'm BunNiuNai", "→ Hello World"]
    width = 500
    height = 80

    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
    for i, line in enumerate(lines):
        y = 32 + i * 30
        color = "#000000"
        svg += f'  <text x="{width//2}" y="{y}" fill="{color}" font-family="Segoe UI, sans-serif" font-size="22" font-weight="700" text-anchor="middle">{escape_xml(line)}</text>\n'
    svg += "</svg>"
    return svg


def generate_badges_svg(followers, stars, repos_count):
    """生成徽章行 SVG"""
    items = [
        ("👁", "访问量", None, None),  # GitHub API 无此数据，用占位
        ("👥", "关注者", followers, TITLE),
        ("★", "星标数", stars, FIRE),
    ]

    width = 400
    height = 30

    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
    svg += f'  <rect width="{width}" height="{height}" rx="6" fill="{BG}" stroke="{STROKE}" stroke-width="1"/>\n'

    x = 20
    for icon, label, value, color in items:
        svg += f'  <text x="{x}" y="20" fill="{ICON}" font-family="Segoe UI, sans-serif" font-size="12">{icon}</text>\n'
        x += 22
        if value is not None:
            svg += f'  <text x="{x}" y="20" fill="{TEXT}" font-family="Segoe UI, sans-serif" font-size="12">{label}: </text>\n'
            text_w = len(label) * 7 + 12
            x += text_w
            svg += f'  <text x="{x}" y="20" fill="{color}" font-family="Segoe UI, sans-serif" font-size="12" font-weight="600">{value}</text>\n'
            x += len(str(value)) * 8 + 20
        else:
            svg += f'  <text x="{x}" y="20" fill="{SUBTLE}" font-family="Segoe UI, sans-serif" font-size="12">{label}</text>\n'
            x += len(label) * 7 + 20

    svg += "</svg>"
    return svg


def generate_tech_stack_svg():
    """生成技术栈 SVG"""
    techs = [
        ("Python", "#3776AB"),
        ("Java", "#ED8B00"),
        ("Git", "#F05032"),
        ("VS Code", "#007ACC"),
    ]

    width = 420
    height = 44

    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
    svg += f'  <rect width="{width}" height="{height}" rx="6" fill="{BG}" stroke="{STROKE}" stroke-width="1"/>\n'

    x = 15
    for name, color in techs:
        w = len(name) * 9 + 30
        svg += f'  <rect x="{x}" y="8" width="{w}" height="28" rx="4" fill="{color}" opacity="0.85"/>\n'
        svg += f'  <text x="{x + w // 2}" y="26" fill="#ffffff" font-family="Segoe UI, sans-serif" font-size="12" font-weight="600" text-anchor="middle">{escape_xml(name)}</text>\n'
        x += w + 8

    svg += "</svg>"
    return svg


def generate_footer_svg():
    """生成页脚波浪 SVG"""
    import math
    width = 800
    height = 120

    colors = ["#667eea", "#764ba2", "#00d4ff"]

    waves = ""
    for layer, color in enumerate(colors):
        amp = 8 + layer * 4
        offset = layer * 15
        phase = layer * 30
        points = []
        for x in range(0, width + 1, 2):
            y = height - 20 + offset + amp * math.sin((x / width) * 2 * math.pi + phase)
            points.append(f"{x},{y:.1f}")
        path_d = f"M0,{height} L0,{height-20+offset}"
        for x, y in zip(range(0, width + 1, 2), [p.split(",")[1] for p in points]):
            path_d += f" L{x},{float(y):.1f}"
        path_d += f" L{width},{height} Z"
        waves += f'  <path d="{path_d}" fill="{color}" opacity="{round(0.15 + layer * 0.15, 2)}"/>\n'

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="{BG}"/>
{waves}</svg>'''


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(">>> 获取用户数据...")
    user = fetch_user()

    print(">>> 获取仓库数据...")
    repos = fetch_repos()

    print(">>> 计算星标和 Fork...")
    total_stars = sum(r["stargazers_count"] for r in repos)
    total_forks = sum(r["forks_count"] for r in repos)

    print(">>> 统计提交数...")
    commits = search_commits_count()

    print(">>> 统计 PR 和 Issue...")
    prs = search_count(f"author:{USERNAME} type:pr is:merged")
    issues = search_count(f"author:{USERNAME} type:issue")

    print(">>> 获取贡献连续天数...")
    current_streak, longest_streak, total_contrib = fetch_contributions_streak()

    print(">>> 生成 SVG 文件...")
    svgs = {
        "stats.svg": generate_stats_svg(user, repos, commits, prs, issues, total_stars, total_forks),
        "top-langs.svg": generate_top_langs_svg(repos),
        "streak.svg": generate_streak_svg(current_streak, longest_streak, total_contrib),
        "typing.svg": generate_typing_svg(),
        "badges.svg": generate_badges_svg(user["followers"], total_stars, user["public_repos"]),
        "tech-stack.svg": generate_tech_stack_svg(),
        "footer.svg": generate_footer_svg(),
    }

    for name, content in svgs.items():
        path = os.path.join(OUTPUT_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"    已生成: svg/{name}")

    print(">>> 全部完成！")


if __name__ == "__main__":
    main()
