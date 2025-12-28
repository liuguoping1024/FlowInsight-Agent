/**
 * 认证工具
 * 处理 token 验证、路由保护等
 */
const API_BASE = 'http://localhost:8887/api';

class Auth {
    /**
     * 获取 token
     */
    static getToken() {
        return localStorage.getItem('token');
    }
    
    /**
     * 获取用户信息
     */
    static getUser() {
        const userStr = localStorage.getItem('user');
        return userStr ? JSON.parse(userStr) : null;
    }
    
    /**
     * 保存 token 和用户信息
     */
    static setAuth(token, user) {
        localStorage.setItem('token', token);
        localStorage.setItem('user', JSON.stringify(user));
    }
    
    /**
     * 清除认证信息
     */
    static clearAuth() {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
    }
    
    /**
     * 检查是否已登录
     */
    static isAuthenticated() {
        return !!this.getToken();
    }
    
    /**
     * 验证 token 是否有效
     */
    static async verifyToken() {
        const token = this.getToken();
        if (!token) {
            return false;
        }
        
        try {
            const response = await fetch(`${API_BASE}/auth/verify`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            return response.ok;
        } catch (error) {
            console.error('Token 验证失败:', error);
            return false;
        }
    }
    
    /**
     * 路由保护：检查认证状态，未登录则跳转到登录页
     */
    static async requireAuth() {
        const token = this.getToken();
        
        if (!token) {
            // 没有 token，跳转到登录页
            window.location.href = 'login.html';
            return false;
        }
        
        // 验证 token 是否有效
        const isValid = await this.verifyToken();
        
        if (!isValid) {
            // Token 无效，清除并跳转到登录页
            this.clearAuth();
            window.location.href = 'login.html';
            return false;
        }
        
        return true;
    }
    
    /**
     * 获取带认证头的 fetch 配置
     */
    static getAuthHeaders() {
        const token = this.getToken();
        return {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        };
    }
    
    /**
     * 带认证的 fetch 请求
     */
    static async authFetch(url, options = {}) {
        try {
            const headers = {
                ...this.getAuthHeaders(),
                ...(options.headers || {})
            };
            
            // 如果 options 中有 body，确保是字符串
            const fetchOptions = {
                ...options,
                headers
            };
            
            if (options.body && typeof options.body !== 'string') {
                fetchOptions.body = JSON.stringify(options.body);
            }
            
            const response = await fetch(url, fetchOptions);
            
            // 如果 token 无效，清除并跳转到登录页
            if (response.status === 401) {
                console.error('认证失败，跳转到登录页');
                this.clearAuth();
                window.location.href = 'login.html';
                return null;
            }
            
            return response;
        } catch (error) {
            console.error('authFetch 错误:', error);
            throw error;
        }
    }
    
    /**
     * 登出
     */
    static logout() {
        this.clearAuth();
        window.location.href = 'login.html';
    }
}

