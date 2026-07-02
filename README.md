# 豆芽魔力 更新间隔统计 - 自动同步版

自动抓取语雀维护更新记录，生成间隔天数折线图，每12小时同步一次。

## 快速开始（推荐：全自动方案）

### 步骤1：Fork 或创建 GitHub 仓库

1. 在 GitHub 创建一个新仓库（如 `douya-update-tracker`）
2. 把本文件夹内所有文件上传到仓库

### 步骤2：配置语雀 Cookie（关键步骤）

由于语雀需要登录态才能获取完整数据，需要配置你的语雀 Cookie：

1. **获取 Cookie**：
   - 用浏览器打开 https://www.yuque.com/douyamoli/2026/wt13txo97lyeqwk0
   - 按 F12 打开开发者工具 → 切换到 Network 标签
   - 刷新页面，找到第一个请求，复制 Request Headers 中的 `Cookie` 字段
   
2. **添加到 GitHub Secrets**：
   - 打开仓库 → Settings → Secrets and variables → Actions
   - 点击 "New repository secret"
   - Name: `YUQUE_COOKIE`
   - Value: 粘贴你复制的 Cookie 字符串
   - 点击 Add secret

### 步骤3：启用 GitHub Pages

1. 仓库 → Settings → Pages
2. Source 选择 "GitHub Actions"
3. 保存

### 步骤4：手动触发首次部署

1. 仓库 → Actions → 找到 "自动同步语雀更新记录"
2. 点击 "Run workflow" 手动运行一次
3. 等待完成后，访问 `https://你的用户名.github.io/仓库名/`

---

## 替代方案：本地定时任务（更简单）

如果你不想用 GitHub Actions，可以在自己电脑上设置定时任务：

### Windows 任务计划程序

1. 安装 Python 3.11+
2. 把本文件夹放到本地（如 `C:\douya-tracker`）
3. 打开 任务计划程序 → 创建基本任务
4. 名称：豆芽魔力更新同步
5. 触发器：每天
6. 操作：启动程序
7. 程序：`python`
8. 参数：`crawler.py`
9. 起始于：`C:\douya-tracker`

### Mac/Linux Cron

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天早上8点和晚上8点运行）
0 8,20 * * * cd /path/to/douya-tracker && python3 crawler.py
```

然后用任意 Web 服务器托管 `dist` 文件夹即可：

```bash
# Python 简易服务器
cd dist && python3 -m http.server 8080
# 访问 http://localhost:8080
```

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `crawler.py` | 爬虫脚本，抓取语雀数据并生成网页 |
| `.github/workflows/auto-sync.yml` | GitHub Actions 定时任务配置 |
| `dist/index.html` | 生成的网页（会自动覆盖） |

## 手动更新数据

如果自动抓取失败，可以手动编辑 `crawler.py` 中的 `get_fallback_data()` 函数，添加新的更新记录，然后重新运行 `python crawler.py`。

---

## 特性

- 每12小时自动抓取语雀最新更新
- 实时计算距上次更新天数
- 点击更新记录可展开查看详细内容
- 响应式设计，支持手机访问
