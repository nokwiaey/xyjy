#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查找网站 Favicon 工具
按照浏览器同样的方式，从网页 HTML 中提取图标地址
"""

import urllib.request
import urllib.parse
import re
import sys

# 设置 stdout 编码
sys.stdout.reconfigure(encoding='utf-8')


def find_favicon(url):
    """
    查找网站的 favicon，按照浏览器同样的逻辑
    """
    print(f"🔍 正在查找: {url}\n")
    
    # 确保 URL 有协议
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url
    
    try:
        # 1. 获取网页内容
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
        
        # 解析基础 URL
        parsed = urllib.parse.urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # 2. 使用正则表达式查找 <link rel="icon"> 标签
        # 匹配各种形式的 icon 链接
        patterns = [
            r'<link[^>]*rel=["\'](?:shortcut\s+)?icon["\'][^>]*href=["\']([^"\']+)["\'][^>]*>',
            r'<link[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\'](?:shortcut\s+)?icon["\'][^>]*>',
            r'<link[^>]*rel=["\']apple-touch-icon["\'][^>]*href=["\']([^"\']+)["\'][^>]*>',
        ]
        
        found_icons = []
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                # 转换为绝对 URL
                full_url = urllib.parse.urljoin(base_url, match)
                found_icons.append(full_url)
        
        # 3. 显示找到的图标
        if found_icons:
            # 去重并保持顺序
            seen = set()
            unique_icons = []
            for icon in found_icons:
                if icon not in seen:
                    seen.add(icon)
                    unique_icons.append(icon)
            
            print(f"✅ 找到 {len(unique_icons)} 个图标:\n")
            for i, icon in enumerate(unique_icons, 1):
                print(f"  {i}. {icon}")
            
            print(f"\n💡 推荐使用: {unique_icons[0]}")
            return unique_icons[0]
        else:
            print("⚠️  未在 HTML 中找到 <link> 标签定义的图标")
            
    except Exception as e:
        print(f"❌ 获取网页失败: {e}")
    
    # 4. 尝试常见路径
    print("\n🔍 尝试常见 favicon 路径...")
    common_paths = [
        '/favicon.ico',
        '/static/favicon.ico',
        '/img/favicon.ico',
        '/assets/favicon.ico',
        '/images/favicon.ico',
        '/favicon.png',
    ]
    
    parsed = urllib.parse.urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    for path in common_paths:
        favicon_url = base_url + path
        try:
            req = urllib.request.Request(favicon_url, headers=headers, method='HEAD')
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    print(f"✅ 找到: {favicon_url}")
                    return favicon_url
        except:
            pass
    
    # 5. 使用 Google Favicon 服务作为备选
    google_favicon = f"https://www.google.com/s2/favicons?domain={url}&sz=128"
    print(f"\n💡 使用 Google Favicon 服务:")
    print(f"   {google_favicon}")
    return google_favicon


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='查找网站 Favicon')
    parser.add_argument('url', help='网站 URL')
    args = parser.parse_args()
    
    find_favicon(args.url)


if __name__ == '__main__':
    main()
