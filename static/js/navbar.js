/**
 * 导航栏组件
 */
class NavBar extends HTMLElement {
    connectedCallback() {
        this.render();
    }
    
    render() {
        const user = Auth.getUser();
        this.innerHTML = `
            <div class="navbar">
                <div class="navbar-left">
                    <h1 class="navbar-logo">📊 FlowInsight</h1>
                    <div class="navbar-tabs">
                        <a href="index.html" class="nav-link" id="nav-index">🏠 首页</a>
                        <a href="dashboard.html" class="nav-link" id="nav-dashboard">📊 我的看板</a>
                        <a href="capital-flow.html" class="nav-link" id="nav-capital-flow">💰 历史股票资金</a>
                        <a href="chat.html" class="nav-link" id="nav-chat">💬 智能聊天</a>
                    </div>
                </div>
                <div class="navbar-right">
                    <span class="navbar-user">${user ? user.username : ''}</span>
                    <button class="btn-settings" onclick="window.location.href='settings.html'">⚙️ 设置</button>
                    <button class="btn-logout" onclick="logout()">退出</button>
                </div>
            </div>
        `;
        
        // 高亮当前页面
        const currentPage = window.location.pathname.split('/').pop() || 'dashboard.html';
        const navId = currentPage.replace('.html', '');
        const navElement = document.getElementById(`nav-${navId}`);
        if (navElement) {
            navElement.classList.add('active');
        }
    }
}

customElements.define('nav-bar', NavBar);

function logout() {
    if (confirm('确定要退出登录吗？')) {
        Auth.logout();
    }
}

