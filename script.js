// ============================================
// 微信分享配置 - 可自定义分享卡片内容
// ============================================
const WECHAT_SHARE_CONFIG = {
    title: '星元检验工具箱',              // 分享标题
    desc: '专业、便捷的检验工具集合，助力高效工作',  // 分享描述
    // 分享图片URL（必须是绝对路径，建议使用 https）
    // 如果留空，会自动生成当前页面的二维码作为分享图
    imgUrl: '',
    // 是否使用当前页面二维码作为分享图
    useCurrentPageQrCode: true
};
// ============================================

// ============================================
// 微信分享初始化
// ============================================
function initWechatShare() {
    const currentUrl = window.location.href;

    // 确定分享图片URL
    let shareImageUrl = WECHAT_SHARE_CONFIG.imgUrl;
    if (!shareImageUrl && WECHAT_SHARE_CONFIG.useCurrentPageQrCode) {
        // 使用当前页面URL生成二维码
        shareImageUrl = `https://api.2dcode.biz/v1/create-qr-code?data=${encodeURIComponent(currentUrl)}&size=500x500`;
    }

    // 更新 Open Graph Meta 标签
    const ogImage = document.getElementById('ogImage');
    if (ogImage && shareImageUrl) {
        ogImage.setAttribute('content', shareImageUrl);
    }

    // 如果页面中已加载微信 JS-SDK，配置分享
    if (typeof wx !== 'undefined' && wx.ready) {
        wx.ready(function() {
            // 分享给朋友
            wx.updateAppMessageShareData({
                title: WECHAT_SHARE_CONFIG.title,
                desc: WECHAT_SHARE_CONFIG.desc,
                link: currentUrl,
                imgUrl: shareImageUrl,
                success: function() {
                    console.log('微信分享配置成功');
                }
            });

            // 分享到朋友圈
            wx.updateTimelineShareData({
                title: WECHAT_SHARE_CONFIG.title,
                link: currentUrl,
                imgUrl: shareImageUrl,
                success: function() {
                    console.log('微信朋友圈分享配置成功');
                }
            });
        });
    }
}

// ============================================
// 站点切换菜单
// ============================================
const SITE_URLS = {site_urls_json};

function getSiteBaseUrl(site) {
    return new URL(site.url);
}

function getCurrentSiteIndex() {
    const currentUrl = new URL(window.location.href);
    let currentIndex = SITE_URLS.findIndex(function(site) {
        const siteUrl = getSiteBaseUrl(site);
        const basePath = siteUrl.pathname.endsWith('/') ? siteUrl.pathname : `${siteUrl.pathname}/`;
        const basePathWithoutSlash = basePath.replace(/\/$/, '');
        return currentUrl.hostname === siteUrl.hostname &&
            (currentUrl.pathname === basePathWithoutSlash || currentUrl.pathname.startsWith(basePath));
    });

    if (currentIndex === -1) {
        currentIndex = SITE_URLS.findIndex(function(site) {
            return currentUrl.hostname === getSiteBaseUrl(site).hostname;
        });
    }

    return currentIndex;
}

function getCurrentRelativePath() {
    const currentUrl = new URL(window.location.href);
    const currentIndex = getCurrentSiteIndex();

    if (currentIndex >= 0) {
        const currentSiteUrl = getSiteBaseUrl(SITE_URLS[currentIndex]);
        const basePath = currentSiteUrl.pathname.endsWith('/') ? currentSiteUrl.pathname : `${currentSiteUrl.pathname}/`;
        const basePathWithoutSlash = basePath.replace(/\/$/, '');
        if (currentUrl.pathname === basePathWithoutSlash) {
            return '';
        }
        if (currentUrl.pathname.startsWith(basePath)) {
            return currentUrl.pathname.slice(basePath.length);
        }
    }

    return currentUrl.pathname.replace(/^\/+/, '');
}

function getSiteUrl(site) {
    const targetUrl = getSiteBaseUrl(site);
    const currentUrl = new URL(window.location.href);
    targetUrl.search = currentUrl.search;
    targetUrl.hash = currentUrl.hash;
    return targetUrl.href;
}

function renderSiteMenu() {
    const siteMenu = document.getElementById('siteMenu');
    if (!siteMenu || !SITE_URLS.length) {
        return;
    }

    const currentIndex = getCurrentSiteIndex();
    siteMenu.innerHTML = '';

    SITE_URLS.forEach(function(site, index) {
        const item = document.createElement('button');
        item.type = 'button';
        item.className = `site-menu-item${index === currentIndex ? ' active' : ''}`;
        item.setAttribute('role', 'menuitem');
        item.title = site.desc || site.name || site.url;
        const nameSpan = document.createElement('span');
        nameSpan.className = 'site-menu-item-name';
        nameSpan.textContent = site.name || site.url;
        const descSpan = document.createElement('span');
        descSpan.className = 'site-menu-item-desc';
        descSpan.textContent = site.desc || '';
        item.appendChild(nameSpan);
        if (site.desc) item.appendChild(descSpan);
        item.addEventListener('click', function() {
            window.location.href = getSiteUrl(site);
        });
        siteMenu.appendChild(item);
    });
}

const siteSwitcher = document.getElementById('siteSwitcher');
const siteMenuToggle = document.getElementById('siteMenuToggle');
const siteMenu = document.getElementById('siteMenu');

if (siteMenuToggle && siteMenu) {
    renderSiteMenu();

    siteMenuToggle.addEventListener('click', function(event) {
        event.stopPropagation();
        const isOpen = siteMenu.classList.toggle('open');
        siteMenuToggle.setAttribute('aria-expanded', String(isOpen));
    });

    document.addEventListener('click', function(event) {
        if (siteSwitcher && !siteSwitcher.contains(event.target)) {
            siteMenu.classList.remove('open');
            siteMenuToggle.setAttribute('aria-expanded', 'false');
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            siteMenu.classList.remove('open');
            siteMenuToggle.setAttribute('aria-expanded', 'false');
        }
    });
}

// ============================================
// 点击 Logo 展示当前页面二维码
// ============================================
const qrCodeLogo = document.getElementById('qrCodeLogo');
const qrModalOverlay = document.getElementById('qrModalOverlay');
const qrModalClose = document.getElementById('qrModalClose');
const qrModalImage = document.getElementById('qrModalImage');
const qrModalUrl = document.getElementById('qrModalUrl');
const qrModalCopy = document.getElementById('qrModalCopy');

function showQrModal() {
    const currentUrl = window.location.href;
    const qrApiUrl = `https://api.2dcode.biz/v1/create-qr-code?data=${encodeURIComponent(currentUrl)}&size=256x256`;
    qrModalImage.src = qrApiUrl;
    qrModalUrl.textContent = currentUrl;
    qrModalOverlay.classList.add('open');
}

function hideQrModal() {
    qrModalOverlay.classList.remove('open');
}

if (qrCodeLogo) {
    qrCodeLogo.addEventListener('click', showQrModal);

    qrCodeLogo.addEventListener('keydown', function(event) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            showQrModal();
        }
    });
}

if (qrModalClose) {
    qrModalClose.addEventListener('click', hideQrModal);
}

if (qrModalOverlay) {
    qrModalOverlay.addEventListener('click', function(event) {
        if (event.target === qrModalOverlay) {
            hideQrModal();
        }
    });
}

document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape' && qrModalOverlay && qrModalOverlay.classList.contains('open')) {
        hideQrModal();
    }
});

if (qrModalCopy) {
    qrModalCopy.addEventListener('click', function() {
        copyToClipboard(qrModalUrl.textContent, qrModalCopy, '复制', '已复制');
    });
}
// ============================================

// ============================================
// 通用复制到剪贴板
// ============================================
function copyToClipboard(text, buttonEl, defaultText, successText) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function() {
            buttonEl.textContent = successText;
            buttonEl.classList.add('copied');
            setTimeout(function() {
                buttonEl.textContent = defaultText;
                buttonEl.classList.remove('copied');
            }, 2000);
        });
    } else {
        // 降级方案
        var textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        buttonEl.textContent = successText;
        buttonEl.classList.add('copied');
        setTimeout(function() {
            buttonEl.textContent = defaultText;
            buttonEl.classList.remove('copied');
        }, 2000);
    }
}
// ============================================

// ============================================
// 搜索 + 标签筛选（统一过滤）+ 键盘导航
// ============================================
const searchInput = document.getElementById('searchInput');
const searchClear = document.getElementById('searchClear');
const tagFilters = document.querySelectorAll('.tag-filter');
const toolCards = document.querySelectorAll('.tool-card');
const toolsGrid = document.querySelector('.tools-grid');
const RECENT_KEY = 'recentTools';
const MAX_RECENT = 6;
let activeTag = 'all';
let searchQuery = '';

function getVisibleCards() {
    var visible = [];
    toolCards.forEach(function(card) {
        if (card.style.display !== 'none') {
            visible.push(card);
        }
    });
    return visible;
}

function focusCard(card) {
    // 移除所有卡片的键盘焦点
    toolCards.forEach(function(c) { c.classList.remove('keyboard-focus'); });
    card.classList.add('keyboard-focus');
    // 确保卡片在可视区域内
    card.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}

function handleSearchKeyboard(e) {
    // 只在下方向键和上方向键时拦截
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;

    var visible = getVisibleCards();
    if (visible.length === 0) return;

    var currentIndex = -1;
    visible.forEach(function(card, i) {
        if (card.classList.contains('keyboard-focus')) {
            currentIndex = i;
        }
    });

    e.preventDefault();

    if (e.key === 'ArrowDown') {
        // 如果当前没有聚焦的卡片，选择第一个
        if (currentIndex < 0) {
            focusCard(visible[0]);
        } else if (currentIndex < visible.length - 1) {
            focusCard(visible[currentIndex + 1]);
        }
    } else if (e.key === 'ArrowUp') {
        if (currentIndex > 0) {
            focusCard(visible[currentIndex - 1]);
        }
    }
}

function applyFilters() {
    var visibleCount = 0;
    toolCards.forEach(function(card) {
        var name = (card.querySelector('.tool-name')?.textContent || '').toLowerCase();
        var desc = (card.querySelector('.tool-desc')?.textContent || '').toLowerCase();
        var tags = (card.getAttribute('data-tags') || '').toLowerCase();
        var matchesSearch = !searchQuery || name.indexOf(searchQuery) !== -1 || desc.indexOf(searchQuery) !== -1 || tags.indexOf(searchQuery) !== -1;
        var matchesTag = activeTag === 'all' || (card.getAttribute('data-tags') || '').split(',').includes(activeTag);
        if (matchesSearch && matchesTag) {
            card.style.display = '';
            visibleCount++;
        } else {
            card.style.display = 'none';
            card.classList.remove('keyboard-focus');
        }
    });
    var noResults = document.getElementById('noResults');
    if (visibleCount === 0) {
        if (!noResults) {
            noResults = document.createElement('div');
            noResults.id = 'noResults';
            noResults.className = 'no-results';
            noResults.textContent = '未找到匹配的工具';
            toolsGrid.insertAdjacentElement('afterend', noResults);
        }
        noResults.classList.add('visible');
    } else if (noResults) {
        noResults.classList.remove('visible');
    }
}

searchInput.addEventListener('input', function() {
    searchQuery = this.value.toLowerCase().trim();
    if (searchQuery) {
        searchClear.classList.add('visible');
    } else {
        searchClear.classList.remove('visible');
    }
    applyFilters();
});

searchInput.addEventListener('keydown', function(e) {
    // 在下方向键时导航卡片
    handleSearchKeyboard(e);
    // Enter 键打开当前聚焦的卡片
    if (e.key === 'Enter') {
        var focused = document.querySelector('.tool-card.keyboard-focus');
        if (focused) {
            e.preventDefault();
            window.open(focused.getAttribute('href'), '_blank');
        }
    }
});

// 全局键盘快捷键 - 在非输入区域时也可以用 / 聚焦搜索
document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey && e.key === 'k') || (e.key === '/' && document.activeElement !== searchInput && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA')) {
        e.preventDefault();
        searchInput.focus();
        searchInput.select();
    }
});

searchClear.addEventListener('click', function() {
    searchInput.value = '';
    searchQuery = '';
    searchClear.classList.remove('visible');
    applyFilters();
    searchInput.focus();
});

tagFilters.forEach(function(filter) {
    filter.addEventListener('click', function() {
        tagFilters.forEach(function(f) { f.classList.remove('active'); });
        filter.classList.add('active');
        activeTag = filter.getAttribute('data-tag');
        applyFilters();
    });
});

// ============================================
// 最近访问
// ============================================
var recentSection = document.getElementById('recentSection');
var recentList = document.getElementById('recentList');
var recentClearBtn = document.getElementById('recentClear');

function getRecentTools() {
    try { return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'); } catch(e) { return []; }
}

function saveRecentTools(recent) {
    try { localStorage.setItem(RECENT_KEY, JSON.stringify(recent)); } catch(e) {}
}

function recordVisit(card) {
    var name = card.querySelector('.tool-name')?.textContent || '';
    var url = card.getAttribute('href') || '';
    var iconEl = card.querySelector('.tool-icon');
    var iconHtml = '';
    if (iconEl) {
        var img = iconEl.querySelector('img');
        if (img) {
            iconHtml = '<img src="' + img.getAttribute('src') + '" alt="" width="16" height="16" style="object-fit:contain;border-radius:2px;">';
        } else {
            iconHtml = iconEl.textContent?.trim() || '🔗';
        }
    }
    var recent = getRecentTools();
    recent = recent.filter(function(item) { return item.url !== url; });
    recent.unshift({ name: name, url: url, iconHtml: iconHtml, time: Date.now() });
    recent = recent.slice(0, MAX_RECENT);
    saveRecentTools(recent);
    renderRecentVisits();
}

function renderRecentVisits() {
    var recent = getRecentTools();
    if (recent.length === 0) {
        recentSection.classList.remove('visible');
        return;
    }
    recentSection.classList.add('visible');
    recentList.innerHTML = '';
    recent.forEach(function(item) {
        var a = document.createElement('a');
        a.href = item.url;
        a.className = 'recent-item';
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        a.title = item.name;
        a.innerHTML = '<span class="recent-item-icon">' + item.iconHtml + '</span><span class="recent-item-name">' + item.name + '</span>';
        recentList.appendChild(a);
    });
}

function attachCardEvents() {
    toolCards.forEach(function(card) {
        // 点击记录访问
        card.addEventListener('click', function(e) {
            // 如果点击的是复制按钮，不记录访问
            if (e.target.closest('.tool-card-copy')) return;
            recordVisit(card);
        });
    });
}

attachCardEvents();

recentClearBtn.addEventListener('click', function() {
    localStorage.removeItem(RECENT_KEY);
    recentSection.classList.remove('visible');
    recentList.innerHTML = '';
});

renderRecentVisits();
// ============================================

// ============================================
// 工具卡片 - 添加复制链接按钮
// ============================================
function initCopyButtons() {
    toolCards.forEach(function(card) {
        // 避免重复添加
        if (card.querySelector('.tool-card-copy')) return;

        var url = card.getAttribute('href') || '';
        var btn = document.createElement('button');
        btn.className = 'tool-card-copy';
        btn.setAttribute('aria-label', '复制链接');
        btn.title = '复制链接';
        btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="9" y="9" width="13" height="13" rx="1.5" stroke="currentColor" stroke-width="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';

        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            // 将相对路径转换为绝对URL
            var absoluteUrl = url;
            if (!/^https?:\/\//i.test(absoluteUrl)) {
                var a = document.createElement('a');
                a.href = absoluteUrl;
                absoluteUrl = a.href;
            }
            // 直接写入剪贴板，不通过 copyToClipboard（它会用 textContent 清空 SVG）
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(absoluteUrl);
            } else {
                var textarea = document.createElement('textarea');
                textarea.value = absoluteUrl;
                textarea.style.position = 'fixed';
                textarea.style.opacity = '0';
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
            }
            // 显示勾号，保持可见直到恢复
            btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><polyline points="20 6 9 17 4 12" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
            btn.classList.add('copied');
            setTimeout(function() {
                btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="9" y="9" width="13" height="13" rx="1.5" stroke="currentColor" stroke-width="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
                btn.classList.remove('copied');
            }, 1500);
        });

        card.appendChild(btn);
    });
}

initCopyButtons();
// ============================================

// ============================================
// 返回顶部按钮
// ============================================
const backToTop = document.getElementById('backToTop');

function toggleBackToTop() {
    if (window.scrollY > 300) {
        backToTop.classList.add('visible');
    } else {
        backToTop.classList.remove('visible');
    }
}

window.addEventListener('scroll', toggleBackToTop, { passive: true });

backToTop.addEventListener('click', function() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
});

// ============================================
// 主题切换功能
// ============================================
const themeToggle = document.getElementById('themeToggle');
const root = document.documentElement;

// 从 localStorage 读取主题设置
const savedTheme = localStorage.getItem('theme');
if (savedTheme) {
    root.setAttribute('data-theme', savedTheme);
}

// 切换主题
themeToggle.addEventListener('click', function() {
    const currentTheme = root.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    if (newTheme === 'light') {
        root.removeAttribute('data-theme');
        localStorage.removeItem('theme');
    } else {
        root.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
    }
});
// ============================================

// ============================================
// 页面加载动画
// ============================================
// 注意：不使用 DOMContentLoaded 事件，因为外部 defer 脚本（vercount、微信 JS-SDK）
// 在离线时会阻塞该事件直到超时，导致 loading 动画长时间遮挡页面。
// 此脚本位于 </body> 末尾，DOM 在此时已解析完毕，直接隐藏即可。
(function() {
    var loader = document.getElementById('pageLoader');
    if (loader) {
        loader.classList.add('hidden');
        setTimeout(function() {
            loader.style.display = 'none';
        }, 500);
    }
})();
// ============================================

// ============================================
// Service Worker 注册 - 离线缓存
// ============================================
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('sw.js').catch(function(err) {
            // Service Worker 注册失败不影响页面正常使用
            console.log('Service Worker 注册失败:', err);
        });
    });
}
// ============================================

// 页面加载完成后初始化微信分享
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWechatShare);
} else {
    initWechatShare();
}
// ============================================
// ============================================
(function() {
    var removeBadge = function() {
        var el = document.getElementById('devfile-badge-content');
        if (el) { el.remove(); }
        var els = document.querySelectorAll('[id^="devfile-badge"]');
        els.forEach(function(e) { e.remove(); });
    };
    removeBadge();
    var observer = new MutationObserver(removeBadge);
    observer.observe(document.documentElement, { childList: true, subtree: true });
})();
// ============================================
