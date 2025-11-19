// Live2D Web 预览器 - 主应用逻辑
class Live2DApp {
    constructor() {
        this.app = null;
        this.model = null;
        this.modelData = null;
        this.modelPath = null;
        this.currentExpression = null;
        this.currentMotion = null;
        this.ws = null;
        this.wsReconnectTimer = null;
        
        // 模型变换状态
        this.transform = {
            x: 0,
            y: 0,
            scale: 1.0,
            rotation: 0,
            opacity: 1.0,
            baseScale: 1.0  // 自动适配时的基准缩放
        };
        
        // 设置
        this.settings = {
            autoFit: true,
            showInfo: true,
            defaultBg: 'transparent',
            quality: 'high',
            antialias: true,
            debug: false,
            wsReconnect: true,
            language: 'en'
        };

        this.i18n = { lang: 'en', messages: {} };
        
        this.init();
    }
    
    async init() {
        try {
            // 检查 PIXI 和 Live2D 库
            if (typeof PIXI === 'undefined') {
                throw new Error('PIXI.js not loaded');
            }
            
            // 初始化画布
            await this.initCanvas();
            
            // 绑定UI事件
            this.bindEvents();
            
            // 隐藏加载动画
            document.getElementById('loading-overlay').style.display = 'none';
            
            // 延迟连接 WebSocket，确保服务器完全启动
            setTimeout(() => {
                this.connectWebSocket();
            }, 1500);
            
            // 从 localStorage 加载设置
            this.loadSettings();

            await this.loadLanguage(this.settings.language || 'en');
            this.applyTranslations();
            if (this.placeholderText) {
                const ph = this.t('placeholder.noModel');
                if (ph) this.placeholderText.text = ph;
            }
            
            // 更新代理状态
            this.updateProxyStatus();
            
            this.log('✅ Live2D previewer initialized');
            
        } catch (error) {
            this.showError('Initialization failed: ' + error.message);
            this.log('❌ Initialization error:', error);
        }
    }
    
    async initCanvas() {
        const canvas = document.getElementById('canvas');
        const container = document.getElementById('canvas-container');
        
        // 计算画布尺寸
        const width = Math.max(400, Math.floor(container.clientWidth * 0.9));
        const height = Math.max(300, Math.floor(container.clientHeight * 0.9));
        
        this.log(`初始化画布: ${width}x${height}`);
        
        // 创建 PIXI 应用
        this.app = new PIXI.Application({
            view: canvas,
            width: width,
            height: height,
            backgroundColor: 0x667eea,
            backgroundAlpha: 0.1,
            resolution: window.devicePixelRatio || 1,
            autoDensity: true,
            antialias: this.settings.antialias
        });
        
        // 添加背景
        this.background = new PIXI.Graphics();
        this.drawBackground();
        this.app.stage.addChild(this.background);
        
        // 添加占位符文字
        const ph = this.t('placeholder.noModel');
        const phText = ph && ph !== 'placeholder.noModel'
            ? ph
            : 'Select a Live2D model in the main app\nor visit this page in a browser';
        this.placeholderText = new PIXI.Text(phText, {
            fontFamily: 'Arial, sans-serif',
            fontSize: 24,
            fill: 0xffffff,
            align: 'center',
            dropShadow: true,
            dropShadowColor: 0x000000,
            dropShadowBlur: 4,
            dropShadowDistance: 2
        });
        this.placeholderText.anchor.set(0.5);
        this.placeholderText.x = width / 2;
        this.placeholderText.y = height / 2;
        this.app.stage.addChild(this.placeholderText);
        
        // 监听窗口大小变化
        window.addEventListener('resize', () => this.handleResize());
    }
    
    drawBackground() {
        if (!this.background || !this.app) return;
        
        const width = this.app.renderer.width;
        const height = this.app.renderer.height;
        
        this.background.clear();
        
        if (this.settings.defaultBg === 'transparent') {
            this.app.renderer.backgroundAlpha = 0;
        } else {
            this.background.beginFill(0x667eea, 0.1);
            this.background.drawRect(0, 0, width, height);
            this.background.endFill();
            this.app.renderer.backgroundAlpha = 1;
        }
    }
    
    handleResize() {
        if (!this.app) return;
        
        const container = document.getElementById('canvas-container');
        const width = Math.max(400, Math.floor(container.clientWidth * 0.9));
        const height = Math.max(300, Math.floor(container.clientHeight * 0.9));
        
        this.app.renderer.resize(width, height);
        this.drawBackground();
        
        if (this.placeholderText) {
            this.placeholderText.x = width / 2;
            this.placeholderText.y = height / 2;
        }
        
        if (this.model && this.settings.autoFit) {
            this.autoFitModel();
        }
    }
    
    bindEvents() {
        // 导航切换
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const view = e.target.dataset.view;
                this.switchView(view);
            });
        });
        
        // 模型控制
        this.bindControl('pos-x-slider', (val) => {
            this.transform.x = parseFloat(val);
            this.updateModelTransform();
        });
        
        this.bindControl('pos-y-slider', (val) => {
            this.transform.y = parseFloat(val);
            this.updateModelTransform();
        });
        
        this.bindControl('scale-slider', (val) => {
            this.transform.scale = parseFloat(val) / 100;
            this.updateModelTransform();
        });
        
        this.bindControl('rotation-slider', (val) => {
            this.transform.rotation = parseFloat(val);
            this.updateModelTransform();
        });
        
        this.bindControl('opacity-slider', (val) => {
            this.transform.opacity = parseFloat(val) / 100;
            this.updateModelTransform();
        });
        
        // 表情选择
        const exprSelect = document.getElementById('expression-select');
        if (exprSelect) {
            exprSelect.addEventListener('change', (e) => {
                this.setExpression(e.target.value);
            });
        }
        
        // 分辨率选择
        const resSelect = document.getElementById('resolution-select');
        if (resSelect) {
            resSelect.addEventListener('change', (e) => {
                this.setResolution(e.target.value);
            });
        }
        
        // 背景设置
        const bgTransparent = document.getElementById('bg-transparent');
        const bgColor = document.getElementById('bg-color');
        
        if (bgTransparent) {
            bgTransparent.addEventListener('change', () => {
                this.updateBackground();
            });
        }
        
        if (bgColor) {
            bgColor.addEventListener('input', () => {
                this.updateBackground();
            });
        }
        
        // 设置项
        this.bindSetting('auto-fit', 'autoFit');
        this.bindSetting('show-info', 'showInfo');
        this.bindSetting('antialias', 'antialias');
        this.bindSetting('debug', 'debug');
        this.bindSetting('ws-reconnect', 'wsReconnect');

        const qualitySelect = document.getElementById('setting-quality');
        if (qualitySelect) {
            qualitySelect.addEventListener('change', (e) => {
                this.settings.quality = e.target.value;
                this.saveSettings();
            });
        }

        const defaultBgSelect = document.getElementById('setting-default-bg');
        if (defaultBgSelect) {
            defaultBgSelect.addEventListener('change', (e) => {
                this.settings.defaultBg = e.target.value;
                this.saveSettings();
                this.drawBackground();
            });
        }

        const langSelect = document.getElementById('setting-language');
        if (langSelect) {
            langSelect.addEventListener('change', async (e) => {
                this.settings.language = e.target.value;
                this.saveSettings();
                await this.loadLanguage(this.settings.language);
                this.applyTranslations();
            });
        }
    }
    
    bindControl(id, callback) {
        const el = document.getElementById(id);
        const valueEl = document.getElementById(id.replace('-slider', '-value'));
        
        if (el) {
            el.addEventListener('input', (e) => {
                const val = e.target.value;
                callback(val);
                
                if (valueEl) {
                    let displayVal = val;
                    if (id.includes('scale')) {
                        displayVal = val + '%';
                    } else if (id.includes('rotation')) {
                        displayVal = val + '°';
                    } else if (id.includes('opacity')) {
                        displayVal = val + '%';
                    }
                    valueEl.textContent = displayVal;
                }
            });
        }
    }
    
    bindSetting(id, key) {
        const el = document.getElementById('setting-' + id);
        if (el) {
            el.addEventListener('change', (e) => {
                this.settings[key] = e.target.checked;
                this.saveSettings();
            });
        }
    }
    
    switchView(viewName) {
        // 切换导航按钮状态
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.view === viewName) {
                btn.classList.add('active');
            }
        });
        
        // 切换视图
        document.querySelectorAll('.view').forEach(view => {
            view.classList.remove('active');
        });
        
        const targetView = document.getElementById(viewName + '-view');
        if (targetView) {
            targetView.classList.add('active');
        }
        
        // 如果切换到预览视图，强制渲染一次
        if (viewName === 'preview' && this.app) {
            setTimeout(() => {
                this.handleResize();
            }, 100);
        }
    }
    
    connectWebSocket() {
        try {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${location.host}/ws/preview`;
            
            this.log('Connecting WebSocket:', wsUrl);
            
            document.getElementById('ws-url').textContent = wsUrl;
            
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                this.log('✅ WebSocket connected');
                this.updateWSStatus(true);
                if (this.wsReconnectTimer) {
                    clearTimeout(this.wsReconnectTimer);
                    this.wsReconnectTimer = null;
                }
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    this.handleMessage(msg);
                } catch (err) {
                    this.log('⚠️ Failed to parse WebSocket message:', err);
                }
            };
            
            this.ws.onerror = (err) => {
                this.log('❌ WebSocket error:', err);
                this.updateWSStatus(false);
            };
            
            this.ws.onclose = () => {
                this.log('🔌 WebSocket disconnected');
                this.updateWSStatus(false);
                
                // 自动重连
                if (this.settings.wsReconnect && !this.wsReconnectTimer) {
                    this.wsReconnectTimer = setTimeout(() => {
                        this.log('⏱️ Trying to reconnect...');
                        this.connectWebSocket();
                    }, 3000);
                }
            };
            
        } catch (err) {
            this.log('❌ WebSocket connection failed:', err);
            this.updateWSStatus(false);
        }
    }
    
    updateWSStatus(connected) {
        const statusEl = document.getElementById('ws-status');
        if (statusEl) {
            if (connected) {
                statusEl.textContent = this.t('ws.connected');
                statusEl.className = 'proxy-status connected';
            } else {
                statusEl.textContent = this.t('ws.disconnected');
                statusEl.className = 'proxy-status disconnected';
            }
        }
    }
    
    updateProxyStatus() {
        const statusEl = document.getElementById('proxy-status');
        const urlEl = document.getElementById('proxy-url');
        
        if (statusEl && urlEl) {
            statusEl.textContent = this.t('proxy.running');
            statusEl.className = 'proxy-status connected';
            urlEl.textContent = location.origin;
        }
    }
    
    handleMessage(data) {
        this.log('📨 Message received:', data.type);
        
        try {
            switch(data.type) {
                case 'loadModel':
                    this.loadModel(data.modelUrl || data.modelPath, data.modelData);
                    break;
                case 'setExpression':
                    this.setExpression(data.expression);
                    break;
                case 'playMotion':
                    this.playMotion(data.motion);
                    break;
                case 'clearModel':
                    this.clearModel();
                    break;
                case 'updateCanvas':
                    this.handleResize();
                    break;
            }
        } catch (error) {
            this.log('❌ Message handling failed:', error);
        }
    }
    
    async loadModel(modelPath, modelData) {
        try {
            this.log('🎭 Loading model:', modelPath);
            
            // 移除占位符
            if (this.placeholderText) {
                this.app.stage.removeChild(this.placeholderText);
                this.placeholderText = null;
            }
            
            // 移除旧模型
            if (this.model) {
                this.app.stage.removeChild(this.model);
                this.model.destroy();
                this.model = null;
            }
            
            this.modelPath = modelPath;
            this.modelData = modelData;
            
            // 加载 Live2D 模型
            if (PIXI.live2d) {
                this.model = await PIXI.live2d.Live2DModel.from(modelPath);
                this.app.stage.addChild(this.model);
                
                // 等待一帧
                await new Promise(resolve => requestAnimationFrame(resolve));
                
                this.model.visible = true;
                this.model.alpha = 1.0;
                
                // 启用交互
                this.model.interactive = true;
                this.model.on('pointerdown', () => {
                    this.playRandomMotion();
                });
                
                // 自动适配
                if (this.settings.autoFit) {
                    this.autoFitModel();
                }
                
                // 更新UI
                this.updateModelInfo();
                
                // 延迟再次适配
                setTimeout(() => {
                    if (this.settings.autoFit) {
                        this.autoFitModel();
                    }
                }, 100);
                
                this.log('✅ Model loaded');
                
            } else {
                throw new Error('Live2D library not loaded');
            }
            
        } catch (error) {
            this.log('❌ Model load failed:', error);
            this.showError('Model load failed: ' + error.message);
        }
    }
    
    async updateModelInfo() {
        // 更新模型名称
        const name = (this.modelPath || '').split(/[\\\/]/).pop();
        document.getElementById('model-name').textContent = name || '未知';
        
        // 获取模型数据
        let data = this.modelData;
        if (!data && this.modelPath) {
            try {
                const resp = await fetch(this.modelPath);
                data = await resp.json();
                this.modelData = data;
            } catch (e) {
                this.log('⚠️ 无法获取模型 JSON:', e);
            }
        }
        
        // 更新表情列表
        const exprSelect = document.getElementById('expression-select');
        if (exprSelect) {
            exprSelect.innerHTML = '<option value="">无表情</option>';
            
            const expressions = data && data.FileReferences && Array.isArray(data.FileReferences.Expressions)
                ? data.FileReferences.Expressions
                : [];
            
            expressions.forEach(item => {
                const name = item && (item.Name || item.name || item.Id || item.id) || '';
                if (name) {
                    const opt = document.createElement('option');
                    opt.value = name;
                    opt.textContent = name;
                    exprSelect.appendChild(opt);
                }
            });
        }
        
        // 更新动作列表
        const motionList = document.getElementById('motion-list');
        if (motionList) {
            motionList.innerHTML = '';
            
            const groups = this.getMotionGroups();
            
            if (groups.length === 0) {
                motionList.innerHTML = '<div style="padding: 20px; text-align: center; color: rgba(255,255,255,0.5); font-size: 13px;">暂无动作</div>';
            } else {
                groups.forEach(group => {
                    const item = document.createElement('div');
                    item.className = 'list-item';
                    item.textContent = group;
                    item.onclick = () => this.playMotion(group);
                    motionList.appendChild(item);
                });
            }
        }
    }
    
    autoFitModel() {
        if (!this.model || !this.app) {
            this.log('⚠️ 无法自动适配：模型或应用未就绪');
            return;
        }
        
        try {
            const width = this.app.renderer.width;
            const height = this.app.renderer.height;
            const margin = 50;
            const availW = Math.max(100, width - margin * 2);
            const availH = Math.max(100, height - margin * 2);
            
            // 获取模型边界
            const bounds = this.model.getLocalBounds();
            const w0 = Math.max(1, bounds.width);
            const h0 = Math.max(1, bounds.height);
            
            // 计算缩放比例
            let scale = Math.min(availW / w0, availH / h0);
            scale = Math.max(0.1, Math.min(scale * 0.85, 5));
            
            // 保存基准缩放
            this.transform.baseScale = scale;
            this.transform.scale = 1.0;
            this.transform.x = 0;
            this.transform.y = 0;
            this.transform.rotation = 0;
            
            // 设置pivot到模型中心
            this.model.pivot.set(bounds.x + w0 / 2, bounds.y + h0 / 2);
            
            // 应用变换
            this.updateModelTransform();
            
            // 更新UI
            document.getElementById('pos-x-slider').value = 0;
            document.getElementById('pos-x-value').textContent = '0';
            document.getElementById('pos-y-slider').value = 0;
            document.getElementById('pos-y-value').textContent = '0';
            document.getElementById('scale-slider').value = 100;
            document.getElementById('scale-value').textContent = '100%';
            document.getElementById('rotation-slider').value = 0;
            document.getElementById('rotation-value').textContent = '0°';
            
            this.log('✅ Auto fit completed');
            
        } catch (error) {
            this.log('❌ Auto fit failed:', error);
        }
    }
    
    updateModelTransform() {
        if (!this.model || !this.app) return;
        
        const width = this.app.renderer.width;
        const height = this.app.renderer.height;
        
        // 应用缩放（基准缩放 × 用户缩放）
        const finalScale = this.transform.baseScale * this.transform.scale;
        this.model.scale.set(finalScale);
        
        // 应用位置（中心 + 偏移）
        this.model.position.set(
            width / 2 + this.transform.x,
            height / 2 + this.transform.y
        );
        
        // 应用旋转
        this.model.rotation = (this.transform.rotation * Math.PI) / 180;
        
        // 应用透明度
        this.model.alpha = this.transform.opacity;
        
        // 强制渲染
        this.app.renderer.render(this.app.stage);
    }
    
    setExpression(expression) {
        if (!this.model || !this.model.internalModel) {
            this.log('⚠️ 无法设置表情：模型未加载');
            return;
        }
        
        try {
            this.model.expression(expression);
            this.currentExpression = expression;
            document.getElementById('current-expression').textContent = expression || '无';
            this.log('✅ 表情已设置:', expression);
        } catch (error) {
            this.log('❌ 设置表情失败:', error);
        }
    }
    
    playMotion(motionData) {
        if (!this.model || !this.model.internalModel) {
            this.log('⚠️ 无法播放动作：模型未加载');
            return;
        }
        
        let motion, index = 0;
        
        if (typeof motionData === 'string') {
            motion = motionData;
        } else if (typeof motionData === 'object' && motionData.motion) {
            motion = motionData.motion;
            index = motionData.index || 0;
        } else {
            this.log('⚠️ 无效的动作数据:', motionData);
            return;
        }
        
        try {
            const groups = this.getMotionGroups();
            let group = motion;
            
            // 如果组名不存在，尝试回退
            if (!groups.includes(group)) {
                this.log(`⚠️ 动作组 "${group}" 不存在，尝试回退...`);
                
                const commonGroups = ['idle', 'Idle', 'IDLE', 'tap_body', 'Tap', 'TapBody', 'tap'];
                const fallback = commonGroups.find(g => groups.includes(g));
                
                if (fallback) {
                    group = fallback;
                } else if (groups.length > 0) {
                    group = groups[0];
                } else {
                    this.log('❌ 没有可用的动作组');
                    return;
                }
            }
            
            // 播放动作
            if (typeof index === 'number' && index >= 0) {
                this.model.motion(group, index);
            } else {
                this.model.motion(group);
            }
            
            this.currentMotion = group;
            document.getElementById('current-motion').textContent = `${group}${index !== undefined ? ` [${index}]` : ''}`;
            this.log('✅ 动作已播放:', group);
            
        } catch (error) {
            this.log('❌ 播放动作失败:', error);
        }
    }
    
    playRandomMotion() {
        const groups = this.getMotionGroups();
        if (groups.length > 0) {
            const group = groups[Math.floor(Math.random() * groups.length)];
            this.playMotion(group);
        }
    }
    
    getMotionGroups() {
        if (!this.model || !this.model.internalModel || !this.model.internalModel.settings) {
            return [];
        }
        
        const settings = this.model.internalModel.settings;
        const motions = settings.motions || {};
        return Object.keys(motions);
    }
    
    setResolution(value) {
        if (!this.app) return;
        
        try {
            if (value === 'auto') {
                this.handleResize();
            } else {
                const [w, h] = value.split('x').map(v => parseInt(v, 10));
                this.app.renderer.resize(w, h);
                this.drawBackground();
                
                if (this.placeholderText) {
                    this.placeholderText.x = w / 2;
                    this.placeholderText.y = h / 2;
                }
                
                if (this.model && this.settings.autoFit) {
                    this.autoFitModel();
                }
            }
            
            this.log('✅ 分辨率已设置:', value);
            
        } catch (error) {
            this.log('❌ 设置分辨率失败:', error);
        }
    }
    
    updateBackground() {
        if (!this.app || !this.background) return;
        
        const transparent = document.getElementById('bg-transparent').checked;
        const color = document.getElementById('bg-color').value;
        
        this.background.clear();
        
        if (transparent) {
            this.app.renderer.backgroundAlpha = 0;
        } else {
            const colorValue = parseInt(color.replace('#', ''), 16);
            const width = this.app.renderer.width;
            const height = this.app.renderer.height;
            
            this.background.beginFill(colorValue, 1);
            this.background.drawRect(0, 0, width, height);
            this.background.endFill();
            this.app.renderer.backgroundColor = colorValue;
            this.app.renderer.backgroundAlpha = 1;
        }
        
        this.log('✅ Background updated');
    }
    
    clearModel() {
        if (!this.model) {
            this.log('⚠️ 没有要清除的模型');
            return;
        }
        
        try {
            this.app.stage.removeChild(this.model);
            this.model.destroy();
            this.model = null;
            this.modelData = null;
            this.modelPath = null;
            this.currentExpression = null;
            this.currentMotion = null;
            
            // 重置变换
            this.transform = {
                x: 0,
                y: 0,
                scale: 1.0,
                rotation: 0,
                opacity: 1.0,
                baseScale: 1.0
            };
            
            // 重置UI
            document.getElementById('model-name').textContent = '未加载';
            document.getElementById('current-expression').textContent = '无';
            document.getElementById('current-motion').textContent = '无';
            document.getElementById('expression-select').innerHTML = '<option value="">无表情</option>';
            document.getElementById('motion-list').innerHTML = '<div style="padding: 20px; text-align: center; color: rgba(255,255,255,0.5); font-size: 13px;">暂无动作</div>';
            
            // 显示占位符
            if (!this.placeholderText) {
                const width = this.app.renderer.width;
                const height = this.app.renderer.height;
                
                this.placeholderText = new PIXI.Text(this.t('placeholder.noModel'), {
                    fontFamily: 'Arial, sans-serif',
                    fontSize: 24,
                    fill: 0xffffff,
                    align: 'center',
                    dropShadow: true,
                    dropShadowColor: 0x000000,
                    dropShadowBlur: 4,
                    dropShadowDistance: 2
                });
                this.placeholderText.anchor.set(0.5);
                this.placeholderText.x = width / 2;
                this.placeholderText.y = height / 2;
                this.app.stage.addChild(this.placeholderText);
            }
            
            this.log('✅ Model cleared');
            
        } catch (error) {
            this.log('❌ Clear model failed:', error);
        }
    }
    
    showError(message) {
        const overlay = document.getElementById('error-overlay');
        const messageEl = document.getElementById('error-message');
        
        if (overlay && messageEl) {
            messageEl.textContent = message;
            overlay.classList.remove('hidden');
            
            // 3秒后自动隐藏
            setTimeout(() => {
                overlay.classList.add('hidden');
            }, 5000);
        }
    }
    
    loadSettings() {
        try {
            const saved = localStorage.getItem('live2d-settings');
            if (saved) {
                const settings = JSON.parse(saved);
                Object.assign(this.settings, settings);
                
                // 应用到UI
                document.getElementById('setting-auto-fit').checked = this.settings.autoFit;
                document.getElementById('setting-show-info').checked = this.settings.showInfo;
                document.getElementById('setting-antialias').checked = this.settings.antialias;
                document.getElementById('setting-debug').checked = this.settings.debug;
                document.getElementById('setting-ws-reconnect').checked = this.settings.wsReconnect;
                document.getElementById('setting-quality').value = this.settings.quality;
                document.getElementById('setting-default-bg').value = this.settings.defaultBg;
                const langSelect = document.getElementById('setting-language');
                if (langSelect) langSelect.value = this.settings.language || 'en';
                
                this.log('✅ Settings loaded');
            }
        } catch (error) {
            this.log('⚠️ Load settings failed:', error);
        }
    }
    
    saveSettings() {
        try {
            localStorage.setItem('live2d-settings', JSON.stringify(this.settings));
            this.log('✅ Settings saved');
        } catch (error) {
            this.log('⚠️ Save settings failed:', error);
        }
    }
    
    log(...args) {
        if (this.settings.debug) {
            console.log('[Live2D]', ...args);
        }
    }

    async loadLanguage(lang) {
        try {
            const res = await fetch(`i18n/${lang}.json`);
            const json = await res.json();
            this.i18n.lang = lang;
            this.i18n.messages = json;
            document.documentElement.setAttribute('lang', lang === 'zh' ? 'zh-CN' : 'en');
        } catch (e) {}
    }

    t(key) {
        const m = this.i18n.messages;
        const parts = key.split('.');
        let cur = m;
        for (const p of parts) {
            if (!cur || !(p in cur)) return key;
            cur = cur[p];
        }
        return typeof cur === 'string' ? cur : key;
    }

    applyTranslations() {
        const nodes = document.querySelectorAll('[data-i18n]');
        nodes.forEach(n => {
            const k = n.getAttribute('data-i18n');
            const v = this.t(k);
            if (v) n.textContent = v;
        });
    }
}

// 全局函数
function togglePanel(headerEl) {
    const panel = headerEl.parentElement;
    panel.classList.toggle('collapsed');
}

function resetModelTransform() {
    if (window.app) {
        window.app.transform.x = 0;
        window.app.transform.y = 0;
        window.app.transform.scale = 1.0;
        window.app.transform.rotation = 0;
        
        document.getElementById('pos-x-slider').value = 0;
        document.getElementById('pos-x-value').textContent = '0';
        document.getElementById('pos-y-slider').value = 0;
        document.getElementById('pos-y-value').textContent = '0';
        document.getElementById('scale-slider').value = 100;
        document.getElementById('scale-value').textContent = '100%';
        document.getElementById('rotation-slider').value = 0;
        document.getElementById('rotation-value').textContent = '0°';
        
        window.app.updateModelTransform();
    }
}

function autoFitModel() {
    if (window.app) {
        window.app.autoFitModel();
    }
}

function clearModel() {
    if (window.app) {
        window.app.clearModel();
    }
}

function reconnectWebSocket() {
    if (window.app) {
        if (window.app.ws) {
            window.app.ws.close();
        }
        window.app.connectWebSocket();
    }
}

// 初始化应用
window.addEventListener('load', () => {
    window.app = new Live2DApp();
});

