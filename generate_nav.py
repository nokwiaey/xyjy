#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
星元检验工具箱导航页生成脚本
读取 tools.json 文件，自动生成 index.html 导航页面
"""

import json
import os
import sys
from pathlib import Path

# 设置 stdout 编码为 utf-8
sys.stdout.reconfigure(encoding='utf-8')


def parse_json(file_path):
    """
    解析 JSON 配置文件，提取工具信息
    返回: (工具列表, 站点地址列表)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    site_urls = data.get('siteUrls', [])
    tools = []
    for tool in data.get('tools', []):
        title = tool.get('title', '')
        url = tool.get('url', '')
        desc = tool.get('desc', '')
        icon = tool.get('icon')
        color = tool.get('color')
        tags = tool.get('tags', [])
        tools.append((title, url, desc, icon, color, tags))
    
    return tools, site_urls


def get_icon_and_color(index, custom_icon=None, custom_color=None):
    """
    获取图标和颜色
    如果提供了自定义值则使用自定义值，否则根据索引自动分配
    """
    # 默认图标列表
    default_icons = ['📊', '📋', '🔍', '🧮', '📅', '⚙️', '📈', '🔬', '📝', '🔧']
    # 默认颜色列表
    default_colors = ['blue', 'green', 'orange', 'purple', 'red', 'cyan']
    
    # 可用的颜色名称（用于验证）
    valid_colors = ['blue', 'green', 'orange', 'purple', 'red', 'cyan']
    
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


def generate_html(tools, site_urls):
    """生成 HTML 内容"""
    site_urls_json = json.dumps(site_urls, ensure_ascii=False)
    
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
    for i, (title, url, desc, custom_icon, custom_color, tags) in enumerate(tools):
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
        # 1. 如果是 URL（以 http:// 或 https:// 开头），直接使用该 URL 作为图标
        # 2. 如果是 Emoji，直接显示
        # 3. 如果为空，自动获取网站 favicon
        if custom_icon and (custom_icon.startswith('http://') or custom_icon.startswith('https://')):
            # 使用指定的图标 URL
            icon_html = f'<div class="tool-icon {color} favicon-icon"><img src="{custom_icon}" alt="" onerror="this.style.display=\'none\'; this.parentElement.innerHTML=\'🔗\';"></div>'
        elif custom_icon:
            # 使用 Emoji 图标
            icon_html = f'<div class="tool-icon {color}">{custom_icon}</div>'
        else:
            # 使用 Google Favicon 服务获取网站图标
            icon_html = f'<div class="tool-icon {color} favicon-icon"><img src="https://www.google.com/s2/favicons?domain={url}&sz=64" alt="" onerror="this.style.display=\'none\'; this.parentElement.innerHTML=\'🔗\';"></div>'

        card = f'''            <a href="{url}" class="tool-card" target="_blank" rel="noopener noreferrer" data-tags="{tags_attr}">
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
    <!-- Open Graph Meta 标签 - 用于微信分享卡片 -->
    <meta property="og:title" content="星元检验工具箱" />
    <meta property="og:description" content="专业、便捷的检验工具集合，助力高效工作" />
    <meta property="og:image" content="" id="ogImage" />
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        :root {{
            --bg-primary: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
            --bg-card: white;
            --text-primary: #1a1a1a;
            --text-secondary: #666;
            --text-tertiary: #999;
            --border-color: rgba(0, 0, 0, 0.04);
            --shadow-color: rgba(0, 0, 0, 0.08);
            --footer-border: rgba(0, 0, 0, 0.06);
            --stats-bg: rgba(0, 0, 0, 0.03);
        }}

        [data-theme="dark"] {{
            --bg-primary: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            --bg-card: #252542;
            --text-primary: #e4e4e4;
            --text-secondary: #a0a0a0;
            --text-tertiary: #707070;
            --border-color: rgba(255, 255, 255, 0.06);
            --shadow-color: rgba(0, 0, 0, 0.3);
            --footer-border: rgba(255, 255, 255, 0.08);
            --stats-bg: rgba(255, 255, 255, 0.05);
        }}

        /* 页面加载动画 */
        .page-loader {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: var(--bg-primary);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            transition: opacity 0.5s ease, visibility 0.5s ease;
        }}

        .page-loader.hidden {{
            opacity: 0;
            visibility: hidden;
        }}

        .loader-spinner {{
            width: 50px;
            height: 50px;
            border: 3px solid var(--border-color);
            border-top-color: #1a5fb4;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }}

        .loader-text {{
            margin-top: 16px;
            font-size: 14px;
            color: var(--text-secondary);
        }}

        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            background: var(--bg-primary);
            min-height: 100vh;
            color: var(--text-primary);
            transition: background 0.3s ease, color 0.3s ease;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 60px 20px;
        }}

        /* 头部区域 */
        .header {{
            text-align: center;
            margin-bottom: 60px;
        }}

        .logo {{
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, #1a5fb4 0%, #3584e4 100%);
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 24px;
            box-shadow: 0 10px 30px rgba(26, 95, 180, 0.2);
            cursor: pointer;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}

        .logo:hover {{
            transform: translateY(-2px);
            box-shadow: 0 14px 34px rgba(26, 95, 180, 0.28);
        }}

        .logo:focus-visible {{
            outline: 3px solid rgba(26, 95, 180, 0.35);
            outline-offset: 4px;
        }}

        .logo svg {{
            width: 40px;
            height: 40px;
            fill: white;
        }}

        .title {{
            font-size: 32px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 12px;
            letter-spacing: 2px;
        }}

        .subtitle {{
            font-size: 16px;
            color: var(--text-secondary);
            font-weight: 400;
        }}

        /* 主题切换按钮 */
        .theme-toggle {{
            position: fixed;
            top: 20px;
            right: 20px;
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 12px var(--shadow-color);
            transition: all 0.3s ease;
            z-index: 1000;
        }}

        .theme-toggle:hover {{
            transform: scale(1.1);
            box-shadow: 0 6px 20px var(--shadow-color);
        }}

        .theme-toggle svg {{
            width: 24px;
            height: 24px;
            fill: var(--text-primary);
            transition: transform 0.3s ease;
        }}

        .theme-toggle:hover svg {{
            transform: rotate(20deg);
        }}

        [data-theme="dark"] .theme-toggle .sun-icon {{
            display: none;
        }}

        [data-theme="light"] .theme-toggle .moon-icon,
        :root:not([data-theme]) .theme-toggle .moon-icon {{
            display: none;
        }}

        /* 站点切换菜单 */
        .site-switcher {{
            position: fixed;
            top: 20px;
            left: 20px;
            z-index: 1000;
        }}

        .site-menu-toggle {{
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 12px var(--shadow-color);
            transition: all 0.3s ease;
        }}

        .site-menu-toggle:hover {{
            transform: scale(1.1);
            box-shadow: 0 6px 20px var(--shadow-color);
        }}

        .site-menu-toggle svg {{
            width: 24px;
            height: 24px;
            stroke: var(--text-primary);
            stroke-width: 2;
            stroke-linecap: round;
        }}

        .site-menu {{
            position: absolute;
            top: 58px;
            left: 0;
            min-width: 180px;
            padding: 8px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            box-shadow: 0 12px 30px var(--shadow-color);
            display: none;
        }}

        .site-menu.open {{
            display: block;
        }}

        .site-menu-item {{
            width: 100%;
            border: 0;
            background: transparent;
            color: var(--text-primary);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 10px 12px;
            border-radius: 6px;
            font-size: 14px;
            text-align: left;
            white-space: nowrap;
        }}

        .site-menu-item:hover,
        .site-menu-item.active {{
            background: rgba(26, 95, 180, 0.1);
            color: #1a5fb4;
        }}

        .site-menu-item.active::after {{
            content: '';
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #1a5fb4;
            flex: 0 0 auto;
        }}

        /* 标签筛选器 */
        .tag-filters {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            justify-content: center;
            margin-bottom: 32px;
            padding: 0 20px;
        }}

        .tag-filter {{
            padding: 8px 16px;
            border: 1px solid var(--border-color);
            background: var(--bg-card);
            color: var(--text-secondary);
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
        }}

        .tag-filter:hover {{
            background: rgba(26, 95, 180, 0.1);
            color: #1a5fb4;
            border-color: rgba(26, 95, 180, 0.3);
        }}

        .tag-filter.active {{
            background: #1a5fb4;
            color: white;
            border-color: #1a5fb4;
        }}

        /* 工具网格 */
        .tools-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
            margin-bottom: 40px;
        }}

        .tool-card {{
            background: var(--bg-card);
            border-radius: 16px;
            padding: 32px;
            text-decoration: none;
            color: inherit;
            transition: all 0.3s ease;
            border: 1px solid var(--border-color);
            position: relative;
            overflow: hidden;
        }}

        .tool-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #1a5fb4, #3584e4);
            transform: scaleX(0);
            transition: transform 0.3s ease;
        }}

        .tool-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 20px 40px var(--shadow-color);
        }}

        .tool-card:hover::before {{
            transform: scaleX(1);
        }}

        .tool-icon {{
            width: 56px;
            height: 56px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 20px;
            font-size: 24px;
            overflow: hidden;
        }}

        .tool-icon.favicon-icon img {{
            width: 32px;
            height: 32px;
            object-fit: contain;
        }}

        .tool-icon.blue {{
            background: rgba(26, 95, 180, 0.1);
            color: #1a5fb4;
        }}

        .tool-icon.green {{
            background: rgba(46, 160, 67, 0.1);
            color: #2ea043;
        }}

        .tool-icon.orange {{
            background: rgba(232, 121, 0, 0.1);
            color: #e87900;
        }}

        .tool-icon.purple {{
            background: rgba(130, 80, 200, 0.1);
            color: #8250c8;
        }}

        .tool-icon.red {{
            background: rgba(207, 54, 54, 0.1);
            color: #cf3636;
        }}

        .tool-icon.cyan {{
            background: rgba(0, 150, 150, 0.1);
            color: #009696;
        }}

        .tool-name {{
            font-size: 18px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 8px;
        }}

        .tool-desc {{
            font-size: 14px;
            color: var(--text-secondary);
            line-height: 1.6;
        }}

        .tool-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 12px;
        }}

        .tool-tag {{
            font-size: 12px;
            padding: 3px 10px;
            background: rgba(26, 95, 180, 0.08);
            color: #1a5fb4;
            border-radius: 12px;
        }}

        [data-theme="dark"] .tool-tag {{
            background: rgba(26, 95, 180, 0.2);
            color: #5a9fd4;
        }}

        /* 页脚 */
        .footer {{
            text-align: center;
            padding-top: 40px;
            border-top: 1px solid var(--footer-border);
        }}

        .footer-text {{
            font-size: 14px;
            color: var(--text-tertiary);
            margin-bottom: 16px;
        }}

        .version {{
            display: inline-block;
            background: rgba(26, 95, 180, 0.1);
            color: #1a5fb4;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            margin-left: 8px;
        }}

        .feedback-link {{
            display: inline-block;
            background: rgba(26, 95, 180, 0.1);
            color: #1a5fb4;
            text-decoration: none;
            font-size: 12px;
            padding: 4px 12px;
            border-radius: 20px;
            margin-left: 8px;
            transition: all 0.3s ease;
        }}

        .feedback-link:hover {{
            background: rgba(26, 95, 180, 0.2);
        }}

        /* 访问统计 */
        .stats {{
            display: flex;
            justify-content: center;
            gap: 24px;
            margin: 16px 0;
            flex-wrap: wrap;
        }}

        .stat-item {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 13px;
            color: var(--text-tertiary);
            padding: 6px 12px;
            background: var(--stats-bg);
            border-radius: 20px;
        }}

        .stat-item svg {{
            width: 14px;
            height: 14px;
            fill: var(--text-tertiary);
        }}

        .stat-item span {{
            color: #1a5fb4;
            font-weight: 500;
        }}

        /* 二维码弹窗 */
        .qr-modal-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.3s ease, visibility 0.3s ease;
        }}

        .qr-modal-overlay.open {{
            opacity: 1;
            visibility: visible;
        }}

        .qr-modal {{
            background: var(--bg-card);
            border-radius: 20px;
            padding: 32px;
            text-align: center;
            box-shadow: 0 20px 60px var(--shadow-color);
            max-width: 360px;
            width: 90%;
            transform: translateY(20px);
            transition: transform 0.3s ease;
        }}

        .qr-modal-overlay.open .qr-modal {{
            transform: translateY(0);
        }}

        .qr-modal-close {{
            position: absolute;
            top: 12px;
            right: 12px;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            border: none;
            background: var(--stats-bg);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-secondary);
            font-size: 18px;
            transition: all 0.2s ease;
        }}

        .qr-modal-close:hover {{
            background: rgba(207, 54, 54, 0.15);
            color: #cf3636;
        }}

        .qr-modal {{
            position: relative;
        }}

        .qr-modal-title {{
            font-size: 18px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 20px;
        }}

        .qr-modal-image {{
            width: 200px;
            height: 200px;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            padding: 8px;
            background: white;
        }}

        .qr-modal-url {{
            margin-top: 16px;
            font-size: 13px;
            color: var(--text-secondary);
            word-break: break-all;
            padding: 8px 12px;
            background: var(--stats-bg);
            border-radius: 8px;
            line-height: 1.5;
        }}

        .qr-modal-hint {{
            margin-top: 12px;
            font-size: 12px;
            color: var(--text-tertiary);
        }}

        /* 响应式 */
        @media (max-width: 768px) {{
            .container {{
                padding: 40px 16px;
            }}

            .title {{
                font-size: 24px;
            }}

            .tools-grid {{
                grid-template-columns: 1fr;
                gap: 16px;
            }}

            .tool-card {{
                padding: 24px;
            }}

            .theme-toggle {{
                top: 16px;
                right: 16px;
                width: 40px;
                height: 40px;
            }}

            .site-switcher {{
                top: 16px;
                left: 16px;
            }}

            .site-menu-toggle {{
                width: 40px;
                height: 40px;
            }}

            .theme-toggle svg {{
                width: 20px;
                height: 20px;
            }}

            .site-menu-toggle svg {{
                width: 20px;
                height: 20px;
            }}
        }}
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

    <!-- 主题切换按钮 -->
    <button class="theme-toggle" id="themeToggle" aria-label="切换主题">
        <svg class="sun-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 7c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zM2 13h2c.55 0 1-.45 1-1s-.45-1-1-1H2c-.55 0-1 .45-1 1s.45 1 1 1zm18 0h2c.55 0 1-.45 1-1s-.45-1-1-1h-2c-.55 0-1 .45-1 1s.45 1 1 1zM11 2v2c0 .55.45 1 1 1s1-.45 1-1V2c0-.55-.45-1-1-1s-1 .45-1 1zm0 18v2c0 .55.45 1 1 1s1-.45 1-1v-2c0-.55-.45-1-1-1s-1 .45-1 1zM5.99 4.58a.996.996 0 00-1.41 0 .996.996 0 000 1.41l1.06 1.06c.39.39 1.03.39 1.41 0s.39-1.03 0-1.41L5.99 4.58zm12.37 12.37a.996.996 0 00-1.41 0 .996.996 0 000 1.41l1.06 1.06c.39.39 1.03.39 1.41 0 .39-.39.39-1.03 0-1.41l-1.06-1.06zm1.06-10.96a.996.996 0 000-1.41.996.996 0 00-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06zM7.05 18.36a.996.996 0 000 1.41.996.996 0 001.41 0l1.06-1.06c.39-.39.39-1.03 0-1.41s-1.03-.39-1.41 0l-1.06 1.06z"/>
        </svg>
        <svg class="moon-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9c0-.46-.04-.92-.1-1.36-.98 1.37-2.58 2.26-4.4 2.26-3.03 0-5.5-2.47-5.5-5.5 0-1.82.89-3.42 2.26-4.4-.44-.06-.9-.1-1.36-.1z"/>
        </svg>
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

        <!-- 标签筛选器 -->
        <div class="tag-filters">
{tags_html}
        </div>

        <!-- 工具网格 -->
        <div class="tools-grid">
{tools_html}
        </div>

        <!-- 页脚 -->
        <footer class="footer">
            <p class="footer-text">
                星元检验工具箱
                <span class="version">v1.1.0</span>
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
            <div class="qr-modal-url" id="qrModalUrl"></div>
            <div class="qr-modal-hint">使用手机扫描二维码即可访问</div>
        </div>
    </div>

    <!-- 页面加载动画 -->
    <div class="page-loader" id="pageLoader">
        <div class="loader-spinner"></div>
        <div class="loader-text">正在加载...</div>
    </div>

    <!-- Vercount 访问统计 -->
    <script src="https://vercount.one/js"></script>
    
    <!-- 微信 JS-SDK -->
    <script src="https://res.wx.qq.com/open/js/jweixin-1.6.0.js"></script>
    
    <script>
        // ============================================
        // 微信分享配置 - 可自定义分享卡片内容
        // ============================================
        const WECHAT_SHARE_CONFIG = {{
            title: '星元检验工具箱',              // 分享标题
            desc: '专业、便捷的检验工具集合，助力高效工作',  // 分享描述
            // 分享图片URL（必须是绝对路径，建议使用 https）
            // 如果留空，会自动生成当前页面的二维码作为分享图
            imgUrl: '',
            // 是否使用当前页面二维码作为分享图
            useCurrentPageQrCode: true
        }};
        // ============================================

        // ============================================
        // 微信分享初始化
        // ============================================
        function initWechatShare() {{
            const currentUrl = window.location.href;

            // 确定分享图片URL
            let shareImageUrl = WECHAT_SHARE_CONFIG.imgUrl;
            if (!shareImageUrl && WECHAT_SHARE_CONFIG.useCurrentPageQrCode) {{
                // 使用当前页面URL生成二维码
                shareImageUrl = `https://api.2dcode.biz/v1/create-qr-code?data=${{encodeURIComponent(currentUrl)}}&size=500x500`;
            }}

            // 更新 Open Graph Meta 标签
            const ogImage = document.getElementById('ogImage');
            if (ogImage && shareImageUrl) {{
                ogImage.setAttribute('content', shareImageUrl);
            }}

            // 如果页面中已加载微信 JS-SDK，配置分享
            if (typeof wx !== 'undefined' && wx.ready) {{
                wx.ready(function() {{
                    // 分享给朋友
                    wx.updateAppMessageShareData({{
                        title: WECHAT_SHARE_CONFIG.title,
                        desc: WECHAT_SHARE_CONFIG.desc,
                        link: currentUrl,
                        imgUrl: shareImageUrl,
                        success: function() {{
                            console.log('微信分享配置成功');
                        }}
                    }});
                    
                    // 分享到朋友圈
                    wx.updateTimelineShareData({{
                        title: WECHAT_SHARE_CONFIG.title,
                        link: currentUrl,
                        imgUrl: shareImageUrl,
                        success: function() {{
                            console.log('微信朋友圈分享配置成功');
                        }}
                    }});
                }});
            }}
        }}

        // ============================================
        // 点击 Logo 切换访问网址
        // ============================================
        const SITE_URLS = {site_urls_json};

        function getSiteBaseUrl(site) {{
            return new URL(site.url);
        }}

        function getCurrentSiteIndex() {{
            const currentUrl = new URL(window.location.href);
            let currentIndex = SITE_URLS.findIndex(function(site) {{
                const siteUrl = getSiteBaseUrl(site);
                const basePath = siteUrl.pathname.endsWith('/') ? siteUrl.pathname : `${{siteUrl.pathname}}/`;
                const basePathWithoutSlash = basePath.replace(/\/$/, '');
                return currentUrl.hostname === siteUrl.hostname &&
                    (currentUrl.pathname === basePathWithoutSlash || currentUrl.pathname.startsWith(basePath));
            }});

            if (currentIndex === -1) {{
                currentIndex = SITE_URLS.findIndex(function(site) {{
                    return currentUrl.hostname === getSiteBaseUrl(site).hostname;
                }});
            }}

            return currentIndex;
        }}

        function getCurrentRelativePath() {{
            const currentUrl = new URL(window.location.href);
            const currentIndex = getCurrentSiteIndex();

            if (currentIndex >= 0) {{
                const currentSiteUrl = getSiteBaseUrl(SITE_URLS[currentIndex]);
                const basePath = currentSiteUrl.pathname.endsWith('/') ? currentSiteUrl.pathname : `${{currentSiteUrl.pathname}}/`;
                const basePathWithoutSlash = basePath.replace(/\/$/, '');
                if (currentUrl.pathname === basePathWithoutSlash) {{
                    return '';
                }}
                if (currentUrl.pathname.startsWith(basePath)) {{
                    return currentUrl.pathname.slice(basePath.length);
                }}
            }}

            return currentUrl.pathname.replace(/^\/+/, '');
        }}

        function getSiteUrl(site) {{
            const currentUrl = new URL(window.location.href);
            const targetUrl = getSiteBaseUrl(site);
            const basePath = targetUrl.pathname.endsWith('/') ? targetUrl.pathname : `${{targetUrl.pathname}}/`;
            const relativePath = getCurrentRelativePath();

            targetUrl.pathname = `${{basePath}}${{relativePath}}`.replace(/\/+$/, '/');
            targetUrl.search = currentUrl.search;
            targetUrl.hash = currentUrl.hash;
            return targetUrl.href;
        }}

        function renderSiteMenu() {{
            const siteMenu = document.getElementById('siteMenu');
            if (!siteMenu || !SITE_URLS.length) {{
                return;
            }}

            const currentIndex = getCurrentSiteIndex();
            siteMenu.innerHTML = '';

            SITE_URLS.forEach(function(site, index) {{
                const item = document.createElement('button');
                item.type = 'button';
                item.className = `site-menu-item${{index === currentIndex ? ' active' : ''}}`;
                item.textContent = site.name || site.url;
                item.setAttribute('role', 'menuitem');
                item.addEventListener('click', function() {{
                    window.location.href = getSiteUrl(site);
                }});
                siteMenu.appendChild(item);
            }});
        }}

        const siteSwitcher = document.getElementById('siteSwitcher');
        const siteMenuToggle = document.getElementById('siteMenuToggle');
        const siteMenu = document.getElementById('siteMenu');

        if (siteMenuToggle && siteMenu) {{
            renderSiteMenu();

            siteMenuToggle.addEventListener('click', function(event) {{
                event.stopPropagation();
                const isOpen = siteMenu.classList.toggle('open');
                siteMenuToggle.setAttribute('aria-expanded', String(isOpen));
            }});

            document.addEventListener('click', function(event) {{
                if (siteSwitcher && !siteSwitcher.contains(event.target)) {{
                    siteMenu.classList.remove('open');
                    siteMenuToggle.setAttribute('aria-expanded', 'false');
                }}
            }});

            document.addEventListener('keydown', function(event) {{
                if (event.key === 'Escape') {{
                    siteMenu.classList.remove('open');
                    siteMenuToggle.setAttribute('aria-expanded', 'false');
                }}
            }});
        }}

        // ============================================
        // 点击 Logo 展示当前页面二维码
        // ============================================
        const qrCodeLogo = document.getElementById('qrCodeLogo');
        const qrModalOverlay = document.getElementById('qrModalOverlay');
        const qrModalClose = document.getElementById('qrModalClose');
        const qrModalImage = document.getElementById('qrModalImage');
        const qrModalUrl = document.getElementById('qrModalUrl');

        function showQrModal() {{
            const currentUrl = window.location.href;
            const qrApiUrl = `https://api.2dcode.biz/v1/create-qr-code?data=${{encodeURIComponent(currentUrl)}}&size=256x256`;
            qrModalImage.src = qrApiUrl;
            qrModalUrl.textContent = currentUrl;
            qrModalOverlay.classList.add('open');
        }}

        function hideQrModal() {{
            qrModalOverlay.classList.remove('open');
        }}

        if (qrCodeLogo) {{
            qrCodeLogo.addEventListener('click', showQrModal);

            qrCodeLogo.addEventListener('keydown', function(event) {{
                if (event.key === 'Enter' || event.key === ' ') {{
                    event.preventDefault();
                    showQrModal();
                }}
            }});
        }}

        if (qrModalClose) {{
            qrModalClose.addEventListener('click', hideQrModal);
        }}

        if (qrModalOverlay) {{
            qrModalOverlay.addEventListener('click', function(event) {{
                if (event.target === qrModalOverlay) {{
                    hideQrModal();
                }}
            }});
        }}

        document.addEventListener('keydown', function(event) {{
            if (event.key === 'Escape' && qrModalOverlay && qrModalOverlay.classList.contains('open')) {{
                hideQrModal();
            }}
        }});
        // ============================================

        // ============================================
        // 标签筛选功能
        // ============================================
        const tagFilters = document.querySelectorAll('.tag-filter');
        const toolCards = document.querySelectorAll('.tool-card');

        tagFilters.forEach(function(filter) {{
            filter.addEventListener('click', function() {{
                // 更新按钮状态
                tagFilters.forEach(function(f) {{ f.classList.remove('active'); }});
                filter.classList.add('active');

                const selectedTag = filter.getAttribute('data-tag');

                // 筛选工具卡片
                toolCards.forEach(function(card) {{
                    if (selectedTag === 'all') {{
                        card.style.display = 'block';
                        setTimeout(function() {{
                            card.style.opacity = '1';
                            card.style.transform = 'scale(1)';
                        }}, 10);
                    }} else {{
                        const cardTags = card.getAttribute('data-tags');
                        if (cardTags && cardTags.split(',').includes(selectedTag)) {{
                            card.style.display = 'block';
                            setTimeout(function() {{
                                card.style.opacity = '1';
                                card.style.transform = 'scale(1)';
                            }}, 10);
                        }} else {{
                            card.style.opacity = '0';
                            card.style.transform = 'scale(0.95)';
                            setTimeout(function() {{
                                card.style.display = 'none';
                            }}, 300);
                        }}
                    }}
                }});
            }});
        }});
        // ============================================

        // ============================================
        // 主题切换功能
        // ============================================
        const themeToggle = document.getElementById('themeToggle');
        const root = document.documentElement;

        // 从 localStorage 读取主题设置
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {{
            root.setAttribute('data-theme', savedTheme);
        }}

        // 切换主题
        themeToggle.addEventListener('click', () => {{
            const currentTheme = root.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            if (newTheme === 'light') {{
                root.removeAttribute('data-theme');
                localStorage.removeItem('theme');
            }} else {{
                root.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
            }}
        }});
        // ============================================

        // ============================================
        // 页面加载动画
        // ============================================
        window.addEventListener('load', function() {{
            const loader = document.getElementById('pageLoader');
            if (loader) {{
                loader.classList.add('hidden');
                setTimeout(function() {{
                    loader.style.display = 'none';
                }}, 500);
            }}
        }});
        // ============================================

        // 页面加载完成后初始化微信分享
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', initWechatShare);
        }} else {{
            initWechatShare();
        }}
        // ============================================
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
    
    print(f"✅ 找到 {len(tools)} 个工具链接:")
    for title, url, desc, icon, color, tags in tools:
        desc_str = f' - {desc}' if desc else ''
        icon_str = f' icon={icon}' if icon else ''
        color_str = f' color={color}' if color else ''
        tags_str = f' tags={",".join(tags)}' if tags else ''
        print(f"   • {title}{desc_str}{icon_str}{color_str}{tags_str}")
    
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
