#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
星元检验工具箱导航页生成脚本
读取 tools.json 文件，自动生成 index.html 导航页面
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 设置 stdout 编码为 utf-8
sys.stdout.reconfigure(encoding='utf-8')


def get_version():
    """从 git tag 获取版本号，失败时返回默认值"""
    try:
        result = subprocess.run(
            ['git', 'describe', '--tags', '--abbrev=0'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            tag = result.stdout.strip()
            return tag.lstrip('v')
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return '1.1.0'


def validate_tools(data):
    """校验 tools.json 数据，返回错误列表"""
    errors = []

    if 'tools' not in data:
        errors.append("缺少 'tools' 字段")
        return errors

    tools = data['tools']
    if not isinstance(tools, list):
        errors.append("'tools' 必须是数组")
        return errors

    urls = []
    titles = []
    for i, tool in enumerate(tools):
        idx = f"tools[{i}]"
        if not tool.get('title'):
            errors.append(f"{idx}: 缺少必填字段 'title'")
        else:
            titles.append(tool['title'])

        if not tool.get('url'):
            errors.append(f"{idx}: 缺少必填字段 'url'")
        else:
            urls.append((idx, tool['url']))

    # 检查重复 URL
    seen_urls = {}
    for idx, url in urls:
        if url in seen_urls:
            errors.append(f"{idx}: URL '{url}' 与 {seen_urls[url]} 重复")
        else:
            seen_urls[url] = idx

    return errors


def parse_json(file_path):
    """
    解析 JSON 配置文件，提取工具信息
    返回: (工具列表, 站点地址列表)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 校验数据
    errors = validate_tools(data)
    if errors:
        print("❌ tools.json 校验失败:")
        for e in errors:
            print(f"   • {e}")
        sys.exit(1)

    site_urls = [s for s in data.get('siteUrls', []) if s.get('enabled', True)]
    tools = []
    for tool in data.get('tools', []):
        title = tool.get('title', '')
        url = tool.get('url', '')
        desc = tool.get('desc', '')
        icon = tool.get('icon')
        color = tool.get('color')
        tags = tool.get('tags', [])
        intranet = tool.get('intranet', False)
        tools.append((title, url, desc, icon, color, tags, intranet))

    return tools, site_urls


def get_icon_and_color(index, custom_icon=None, custom_color=None):
    """
    获取图标和颜色
    如果提供了自定义值则使用自定义值，否则根据索引自动分配
    """
    # 默认图标列表
    default_icons = ['📊', '📋', '🔍', '🧮', '📅', '⚙️', '📈', '🔬', '📝', '🔧']
    # 默认颜色列表
    default_colors = ['blue', 'green', 'orange', 'purple', 'red', 'cyan', 'white']

    # 可用的颜色名称（用于验证）
    valid_colors = ['blue', 'green', 'orange', 'purple', 'red', 'cyan', 'white']

    # 确定图标
    if custom_icon:
        icon = custom_icon
    else:
        icon = default_icons[index % len(default_icons)]

    # 确定颜色
    if custom_color and custom_color.lower() in valid_colors:
        color = custom_color.lower()
    else:
        color = default_colors[index % len(default_colors)]

    return icon, color


def read_asset(script_dir, filename):
    """读取资源文件内容"""
    filepath = script_dir / filename
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    print(f"⚠️ 警告: 未找到 {filename}，将跳过")
    return ''


def generate_html(tools, site_urls):
    """生成 HTML 内容"""
    script_dir = Path(__file__).parent
    site_urls_json = json.dumps(site_urls, ensure_ascii=False)
    tz_cn = timezone(timedelta(hours=8))
    build_date = datetime.now(tz_cn).strftime('%Y-%m-%d %H:%M')

    # 读取外部 CSS 和 JS
    css_content = read_asset(script_dir, 'style.css')
    js_content = read_asset(script_dir, 'script.js')

    # 替换 JS 中的站点URL占位符
    js_content = js_content.replace('{site_urls_json}', site_urls_json)

    # 收集所有标签
    all_tags = set()
    for tool in tools:
        all_tags.update(tool[5])
    all_tags = sorted(list(all_tags))

    # 生成标签筛选器 HTML
    tags_html = '<button class="tag-filter active" data-tag="all">全部</button>'
    for tag in all_tags:
        tags_html += f'\n            <button class="tag-filter" data-tag="{tag}">{tag}</button>'

    # 生成工具卡片
    tool_cards = []
    for i, (title, url, desc, custom_icon, custom_color, tags, intranet) in enumerate(tools):
        icon, color = get_icon_and_color(i, custom_icon, custom_color)
        # 如果没有描述，使用默认描述
        if not desc:
            desc = f"点击访问{title}"

        # 生成标签 HTML
        tags_attr = ','.join(tags) if tags else ''
        tags_display = ''
        if tags:
            tags_display = '<div class="tool-tags">' + ''.join([f'<span class="tool-tag">{tag}</span>' for tag in tags]) + '</div>'

        # 生成图标 HTML
        if custom_icon and (custom_icon.startswith('http://') or custom_icon.startswith('https://')):
            icon_html = f'<div class="tool-icon {color} favicon-icon"><img src="{custom_icon}" alt="" loading="lazy" decoding="async" width="32" height="32" onerror="this.style.display=\'none\'; this.parentElement.innerHTML=\'🔗\';"></div>'
        elif custom_icon:
            icon_html = f'<div class="tool-icon {color}">{custom_icon}</div>'
        else:
            icon_html = f'<div class="tool-icon {color} favicon-icon"><img src="https://www.google.com/s2/favicons?domain={url}&sz=64" alt="" loading="lazy" decoding="async" width="32" height="32" onerror="this.style.display=\'none\'; this.parentElement.innerHTML=\'🔗\';"></div>'

        intranet_attr = ' data-intranet="true"' if intranet else ''

        card = f'''            <a href="{url}" class="tool-card" target="_blank" rel="noopener noreferrer" data-tags="{tags_attr}"{intranet_attr}>
                {icon_html}
                <h3 class="tool-name">{title}</h3>
                <p class="tool-desc">{desc}</p>
                {tags_display}
            </a>'''
        tool_cards.append(card)

    tools_html = '\n'.join(tool_cards)

    html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>星元检验工具箱</title>
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Cdefs%3E%3ClinearGradient id='bg' x1='0%25' y1='0%25' x2='100%25' y2='100%25'%3E%3Cstop offset='0%25' stop-color='%231a5fb4'/%3E%3Cstop offset='100%25' stop-color='%233584e4'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='32' height='32' rx='7' fill='url(%23bg)'/%3E%3Cg transform='translate(4,4)'%3E%3Cpath d='M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5' fill='white'/%3E%3C/g%3E%3C/svg%3E">
    <!-- Open Graph Meta 标签 - 用于微信分享卡片 -->
    <meta property="og:title" content="星元检验工具箱" />
    <meta property="og:description" content="专业、便捷的检验工具集合，助力高效工作" />
    <meta property="og:image" content="" id="ogImage" />
    <!-- 资源预连接 - 加速第三方域名解析与连接 -->
    <link rel="dns-prefetch" href="https://www.vercount.one">
    <link rel="dns-prefetch" href="https://res.wx.qq.com">
    <link rel="dns-prefetch" href="https://api.2dcode.biz">

    <link rel="preconnect" href="https://www.vercount.one" crossorigin>
    <link rel="preconnect" href="https://res.wx.qq.com" crossorigin>
    <style>
{css_content}
    </style>
</head>
<body>
    <!-- 站点切换菜单 -->
    <div class="site-switcher" id="siteSwitcher">
        <button class="site-menu-toggle" id="siteMenuToggle" aria-label="切换访问网址" aria-expanded="false" aria-controls="siteMenu" title="切换访问网址">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M4 7h16M4 12h16M4 17h16"/>
            </svg>
        </button>
        <div class="site-menu" id="siteMenu" role="menu"></div>
    </div>

    <!-- 返回顶部按钮 -->
    <button class="back-to-top" id="backToTop" aria-label="返回顶部">
        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <polyline points="18 15 12 9 6 15"/>
        </svg>
    </button>

    <!-- 主题切换按钮 -->
    <button class="theme-toggle" id="themeToggle" aria-label="切换主题">
        <svg class="sun-icon" xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#1f1f1f"><path d="M565-395q35-35 35-85t-35-85q-35-35-85-35t-85 35q-35 35-35 85t35 85q35 35 85 35t85-35Zm-226.5 56.5Q280-397 280-480t58.5-141.5Q397-680 480-680t141.5 58.5Q680-563 680-480t-58.5 141.5Q563-280 480-280t-141.5-58.5ZM200-440H40v-80h160v80Zm720 0H760v-80h160v80ZM440-760v-160h80v160h-80Zm0 720v-160h80v160h-80ZM256-650l-101-97 57-59 96 100-52 56Zm492 496-97-101 53-55 101 97-57 59Zm-98-550 97-101 59 57-100 96-56-52ZM154-212l101-97 55 53-97 101-59-57Zm326-268Z"/></svg>
        <svg class="moon-icon" xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#1f1f1f"><path d="M480-120q-150 0-255-105T120-480q0-150 105-255t255-105q14 0 27.5 1t26.5 3q-41 29-65.5 75.5T444-660q0 90 63 153t153 63q55 0 101-24.5t75-65.5q2 13 3 26.5t1 27.5q0 150-105 255T480-120Zm0-80q88 0 158-48.5T740-375q-20 5-40 8t-40 3q-123 0-209.5-86.5T364-660q0-20 3-40t8-40q-78 32-126.5 102T200-480q0 116 82 198t198 82Zm-10-270Z"/></svg>
    </button>

    <div class="container">
        <!-- 头部 -->
        <header class="header">
            <div class="logo" id="qrCodeLogo" role="button" tabindex="0" aria-label="查看网站二维码" title="查看网站二维码">
                <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                </svg>
            </div>
            <h1 class="title">星元检验工具箱</h1>
            <p class="subtitle">专业、便捷的检验工具集合，助力高效工作</p>
        </header>

        <!-- 搜索框 -->
        <div class="search-wrapper">
            <div class="search-box">
                <svg class="search-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="11" cy="11" r="8" stroke="currentColor" stroke-width="2"/><path d="M21 21l-4.35-4.35" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
                <input class="search-input" id="searchInput" type="text" placeholder="搜索工具名称、描述..." autocomplete="off" autofocus>
                <span class="search-shortcut">Ctrl+K</span>
                <button class="search-clear" id="searchClear" aria-label="清除搜索">&times;</button>
            </div>
        </div>

        <!-- 标签筛选器 -->
        <div class="tag-filters">
{tags_html}
        </div>

        <!-- 最近访问 -->
        <div class="recent-section" id="recentSection">
            <div class="recent-header">
                <span class="recent-title">最近访问</span>
                <button class="recent-clear" id="recentClear">清除记录</button>
            </div>
            <div class="recent-list" id="recentList"></div>
        </div>

        <!-- 工具网格 -->
        <div class="tools-grid">
{tools_html}
        </div>

        <!-- 页脚 -->
        <footer class="footer">
            <p class="footer-text">
                星元检验工具箱
                <span class="update-date">最后更新: {build_date}</span>
                <a href="https://f.kdocs.cn/g/sn7KOMnc/" class="feedback-link" target="_blank" rel="noopener noreferrer">反馈建议</a>
            </p>
            <div class="stats">
                 <span class="stat-item">
                     <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                         <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/>
                     </svg>
                     总访问量: <span id="busuanzi_value_site_pv">--</span>
                 </span>
                 <span class="stat-item">
                     <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                         <path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/>
                     </svg>
                     总访客: <span id="busuanzi_value_site_uv">--</span>
                 </span>
             </div>
        </footer>
    </div>

    <!-- 二维码弹窗 -->
    <div class="qr-modal-overlay" id="qrModalOverlay">
        <div class="qr-modal">
            <button class="qr-modal-close" id="qrModalClose" aria-label="关闭二维码">&times;</button>
            <div class="qr-modal-title">扫码访问本页</div>
            <img class="qr-modal-image" id="qrModalImage" src="" alt="当前页面二维码" />
            <div class="qr-modal-url-row">
                <div class="qr-modal-url" id="qrModalUrl"></div>
                <button class="qr-modal-copy" id="qrModalCopy">复制</button>
            </div>
            <div class="qr-modal-hint">使用手机扫描二维码即可访问</div>
        </div>
    </div>

    <!-- 页面加载动画 -->
    <div class="page-loader" id="pageLoader">
        <div class="loader-spinner"></div>
        <div class="loader-text">正在加载...</div>
    </div>

    <!-- Vercount 访问统计 -->
    <script src="https://www.vercount.one/js" defer></script>

    <!-- 微信 JS-SDK -->
    <script src="https://res.wx.qq.com/open/js/jweixin-1.6.0.js" defer></script>

    <script>
{js_content}
    </script>
</body>
</html>'''

    return html_content


def main():
    """主函数"""
    # 获取脚本所在目录
    script_dir = Path(__file__).parent

    # 文件路径
    json_path = script_dir / 'tools.json'
    output_path = script_dir / 'index.html'

    # 检查 tools.json 是否存在
    if not json_path.exists():
        print(f"❌ 错误: 未找到 {json_path}")
        print("请确保 tools.json 文件与脚本在同一目录下")
        return

    # 解析 JSON
    print(f"📖 正在读取 {json_path}...")
    tools, site_urls = parse_json(json_path)

    if not tools:
        print("⚠️ 警告: 未在 tools.json 中找到任何工具")
        return

    # 收集所有标签用于显示
    all_tags = set()
    for tool in tools:
        all_tags.update(tool[5])

    version = get_version()
    print(f"📌 版本: v{version}")
    print(f"✅ 找到 {len(tools)} 个工具链接:")
    for title, url, desc, icon, color, tags, intranet in tools:
        desc_str = f' - {desc}' if desc else ''
        icon_str = f' icon={icon}' if icon else ''
        color_str = f' color={color}' if color else ''
        tags_str = f' tags={",".join(tags)}' if tags else ''
        intranet_str = ' [内网]' if intranet else ''
        print(f"   • {title}{desc_str}{icon_str}{color_str}{tags_str}{intranet_str}")

    if all_tags:
        print(f"\n🏷️ 发现 {len(all_tags)} 个标签: {', '.join(sorted(all_tags))}")

    if site_urls:
        print(f"\n🌐 配置 {len(site_urls)} 个访问网址: {', '.join(site.get('name', site.get('url', '')) for site in site_urls)}")

    # 生成 HTML
    print("\n🔨 正在生成 HTML...")
    html_content = generate_html(tools, site_urls)

    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✅ 导航页已生成: {output_path}")
    print("\n💡 提示: 修改 tools.json 后重新运行此脚本即可更新导航页")


if __name__ == '__main__':
    main()
