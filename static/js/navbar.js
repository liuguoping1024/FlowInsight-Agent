/**
 * 导航栏组件（侧边栏 + 顶部栏）
 */
class NavBar extends HTMLElement {
    connectedCallback() {
        this.render();
        this.setupToggle();
    }
    
    render() {
        const user = Auth.getUser();
        const isAdmin = user && user.group_id === 1; // group_id=1 是管理员组
        
        // 菜单项配置
        const menuItems = [
            { icon: '📊', text: '看板', href: 'index.html', id: 'nav-index' },
            { icon: '🤖', text: 'AI分析', href: 'chat.html', id: 'nav-chat' },
            { icon: '📈', text: '资金分析', href: 'stock-analysis.html', id: 'nav-stock-analysis' },
            { icon: '📉', text: '技术分析', href: 'technical-analysis.html', id: 'nav-technical-analysis' },
            { icon: '💰', text: '交易分析', href: 'capital-flow.html', id: 'nav-capital-flow' }
        ];
        
        // 如果是管理员，添加管理菜单
        if (isAdmin) {
            menuItems.push({ icon: '⚙️', text: '管理', href: 'admin.html', id: 'nav-admin' });
        }
        
        // 设置菜单
        menuItems.push({ icon: '🔧', text: '设置', href: 'settings.html', id: 'nav-settings' });
        
        // 构建菜单HTML
        const menuHtml = menuItems.map(item => `
            <a href="${item.href}" class="menu-item" id="${item.id}">
                <span class="menu-item-icon">${item.icon}</span>
                <span class="menu-item-text">${item.text}</span>
            </a>
        `).join('');
        
        this.innerHTML = `
            <!-- 侧边栏 -->
            <div class="sidebar" id="sidebar">
                <div class="sidebar-header">
                    <div class="sidebar-logo">📊 FlowInsight</div>
                </div>
                <div class="sidebar-menu">
                    ${menuHtml}
                </div>
                <div class="sidebar-footer">
                    <div class="footer-item">
                        <span>联系方式：</span>
                        <a href="mailto:support@flowinsight.com" class="footer-link">support@flowinsight.com</a>
                    </div>
                    <div class="footer-item">
                        <span>GitHub：</span>
                        <a href="https://github.com/your-repo" target="_blank" class="footer-link">FlowInsight</a>
                    </div>
                    <div class="footer-item">
                        <span>备案号：</span>
                        <span>京ICP备XXXXXXXX号</span>
                    </div>
                    <div class="footer-item">
                        <a href="#" class="footer-link">用户协议</a>
                        <span> | </span>
                        <a href="#" class="footer-link">隐私协议</a>
                    </div>
                    <div class="footer-item" style="margin-top: 8px;">
                        <span>© 2024 FlowInsight. All rights reserved.</span>
                    </div>
                </div>
            </div>
        `;
        
        // 在主内容区域添加顶部导航栏
        setTimeout(() => {
            const mainContent = document.querySelector('.main-content');
            if (mainContent && !document.querySelector('.top-navbar')) {
                const topNavbar = document.createElement('div');
                topNavbar.className = 'top-navbar';
                topNavbar.innerHTML = `
                    <div class="top-navbar-left">
                        <button class="menu-toggle-btn" id="menu-toggle-btn" title="显示/隐藏菜单">
                            <span id="menu-toggle-icon">☰</span>
                        </button>
                    </div>
                    <div class="top-navbar-right">
                        <span class="navbar-user">${user ? user.username : ''}</span>
                        <button class="btn-settings" onclick="window.location.href='settings.html'">⚙️ 设置</button>
                        <button class="btn-logout" onclick="logout()">退出</button>
                    </div>
                `;
                mainContent.insertBefore(topNavbar, mainContent.firstChild);
            }
        }, 50);
        
        // 高亮当前页面
        const currentPage = window.location.pathname.split('/').pop() || 'index.html';
        const pageMap = {
            'index.html': 'nav-index',
            'dashboard.html': 'nav-index',
            'chat.html': 'nav-chat',
            'stock-analysis.html': 'nav-stock-analysis',
            'technical-analysis.html': 'nav-technical-analysis',
            'capital-flow.html': 'nav-capital-flow',
            'admin.html': 'nav-admin',
            'settings.html': 'nav-settings'
        };
        
        const navId = pageMap[currentPage] || 'nav-index';
        const navElement = document.getElementById(navId);
        if (navElement) {
            navElement.classList.add('active');
        }
    }
    
    setupToggle() {
        // 等待DOM渲染完成
        const initToggle = () => {
            const sidebar = document.getElementById('sidebar');
            const toggleBtn = document.getElementById('menu-toggle-btn');
            const toggleIcon = document.getElementById('menu-toggle-icon');
            const mainContent = document.querySelector('.main-content');
            
            if (!toggleBtn || !sidebar) {
                // 如果元素还没准备好，稍后重试
                setTimeout(initToggle, 50);
                return;
            }
            
            // 从localStorage读取隐藏状态
            const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
            if (isCollapsed) {
                sidebar.classList.add('collapsed');
                if (toggleIcon) toggleIcon.textContent = '☰';
            }
            
            // 绑定点击事件
            toggleBtn.addEventListener('click', () => {
                sidebar.classList.toggle('collapsed');
                const collapsed = sidebar.classList.contains('collapsed');
                localStorage.setItem('sidebarCollapsed', collapsed ? 'true' : 'false');
                if (toggleIcon) {
                    toggleIcon.textContent = collapsed ? '☰' : '✕';
                }
            });
        };
        
        // 立即尝试初始化，如果失败则延迟重试
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initToggle);
        } else {
            initToggle();
        }
    }
}

customElements.define('nav-bar', NavBar);

function logout() {
    if (confirm('确定要退出登录吗？')) {
        Auth.logout();
    }
}

