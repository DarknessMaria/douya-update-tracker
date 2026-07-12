#!/usr/bin/env python3
"""
语雀更新记录爬虫 - 自动抓取最新更新数据并生成网页
"""
import re
import json
import os
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from urllib.parse import unquote

# 中国时区 (UTC+8)
CN_TZ = timezone(timedelta(hours=8))

def now_cn():
    """获取中国时区的当前时间"""
    return datetime.now(CN_TZ)

# ========== 配置 ==========
YUQUE_URL = "https://www.yuque.com/douyamoli/2026/wt13txo97lyeqwk0"
OUTPUT_DIR = "./dist"
# ==========================

def fetch_yuque_page():
    """抓取语雀页面HTML，提取appData"""
    try:
        req = Request(
            YUQUE_URL,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
        )
        with urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        print(f"[警告] 抓取语雀页面失败: {e}")
        return None

def extract_doc_info(html):
    """从页面HTML中提取book_id和doc_id"""
    if not html:
        return None, None
    
    try:
        # 从 appData 中提取
        m = re.search(r'window\.appData\s*=\s*JSON\.parse\(decodeURIComponent\("(.*?)"\)\)', html)
        if m:
            data = json.loads(unquote(m.group(1)))
            book_id = data.get("book", {}).get("id")
            # 从目录中找到"维护更新记录"对应的doc_id
            target_doc_id = None
            for item in data.get("book", {}).get("toc", []):
                if "维护更新记录" in str(item.get("title", "")):
                    target_doc_id = item.get("doc_id")
                    break
            if book_id and target_doc_id:
                return str(book_id), str(target_doc_id)
    except Exception as e:
        print(f"[警告] 提取doc信息失败: {e}")
    
    return None, None

def fetch_doc_content(book_id, doc_id):
    """通过语雀API获取文档内容"""
    try:
        api_url = f"https://www.yuque.com/api/docs/{doc_id}?book_id={book_id}"
        req = Request(api_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": YUQUE_URL
        })
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("data", {}).get("content", "")
    except Exception as e:
        print(f"[警告] API获取文档内容失败: {e}")
        return None

def extract_dates_from_lake(content):
    """从Lake格式HTML中提取日期和更新内容"""
    if not content:
        return None
    
    updates = []
    try:
        # Lake格式: <strong><span style="color: #DF2A3F">2026-07-02</span></strong>
        # 内容格式: <span>1、更新内容</span>
        
        # 按日期分段
        sections = re.split(r'(?=<strong>.*?\d{4}-\d{2}-\d{2})', content)
        
        for section in sections:
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', section)
            if date_match:
                date_str = date_match.group(1)
                # 提取所有更新项 (1、xxx)
                items = re.findall(r'\d+、([^<]+)', section)
                items = [i.strip() for i in items if i.strip()]
                # 解码HTML实体
                items = [i.replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">") for i in items]
                if items:
                    updates.append({"date": date_str, "items": items})
        
        updates.sort(key=lambda x: x["date"])
        print(f"[调试] Lake格式提取到 {len(updates)} 条记录")
        return updates
    except Exception as e:
        print(f"[警告] Lake格式解析失败: {e}")
        return None

def extract_dates_from_html(html):
    """从纯文本HTML中提取日期和更新内容（备用方法）"""
    if not html:
        return None
    
    updates = []
    # 匹配日期行：2026-06-27 格式，后面跟着更新列表
    date_pattern = r'(\d{4}-\d{2}-\d{2})\s*\n((?:\d+[、．.]\s*[^\n]+\n?)+)'
    matches = re.findall(date_pattern, html)
    
    for date_str, content in matches:
        items = re.findall(r'\d+[、．.]\s*([^\n]+)', content)
        updates.append({
            "date": date_str,
            "items": [item.strip() for item in items if item.strip()]
        })
    
    updates.sort(key=lambda x: x["date"])
    return updates

def get_fallback_data():
    """获取本地兜底数据（最后一次已知的更新记录）"""
    return [
        {"date": "2026-05-09", "items": ["封印商店上架封印卡100张道具", "修复传承坐骑道具说明错误", "传承佣兵技能耗魔降低50%", "宠物市场传送员增加传送点", "特殊仓库增加可存放物品", "家园宠物鉴定费用降低为8万魔币"]},
        {"date": "2026-05-10", "items": ["修复山贼盗贼破坏狂无法封印", "技能守护领域设置为守护神得意技", "家园宠物采集制作工费降低为30", "宠物家园增加家园仓库功能", "取消家园宠物背包金币", "修复小石像怪宠物蛋问题"]},
        {"date": "2026-05-11", "items": ["钓鱼产出几率增加", "特殊仓库取消采集材料放入", "所有佣兵宠物属性更新", "特殊仓库调整位置至最下方", "家园工作部署页面增加详情", "家园宠物放生页面增加技能详情", "精品商店增加售卖高级助手"]},
        {"date": "2026-05-13", "items": ["打开宠物蛋时自动刷新忠诚度", "修复宝藏猎人技能寻觅问题", "灵魂封印卡更改为单局可封印多个", "家园宠物鉴定出现10级技能概率增加"]},
        {"date": "2026-05-15", "items": ["家园宠物鉴定10级技能概率增加", "获取家园卡增加兑换功能", "黑白钥匙起司任务取消职业限制", "失落的文明系列任务取消职业限制", "宠物回收皮肤增加", "宠物丢地消失时间更改为24小时", "特殊仓库增加可存放物品"]},
        {"date": "2026-05-19", "items": ["任务狮鹫兽捕捉修改", "神兽传送掉落率提高", "树精神兽双王增加佣兵之证掉落", "每日任务找寻物品调整", "特殊仓库增加可存储物品", "流星山丘黄金树精任务取消职业限制", "任务凤凰的羽毛修改"]},
        {"date": "2026-05-22", "items": ["狩猎采集增加螃蟹选项", "佣兵巫师和咒术修正技能显示", "部分任务采集统一修改为1级挖掘", "任务索奇亚古文明调查修改", "特殊仓库增加可存放任务物品", "修复守护领域4技能异常", "道具豆芽宝石开放使用", "法兰城竞技场连战增加首饰掉落"]},
        {"date": "2026-05-27", "items": ["修复佣兵奥义复活之光可选中死亡玩家", "特殊仓库增加可存放道具", "每日任务取消寻找装备", "在线答题增加周三晚上八点开启"]},
        {"date": "2026-06-04", "items": ["宠物寄售管理页面调整", "宠物摆摊续期价格降低", "修复野外任务采集点无效", "添加道具聚魔100可存放特殊仓库", "狮鹫捕捉任务孵化时间降低"]},
        {"date": "2026-06-07", "items": ["宠物皮卡丘更改为固定血攻档位", "增加地狱看门犬和迷你龙Lv1级点位", "人物宠物佣兵物理输出技能增加20%伤害", "黑白钥匙起司任务等待时间降低", "修复法兰竞技场地狱连战问题", "任务七宗罪修改", "家园宠物寿命归0不再直接删除", "家园宠物制作委托可设置数量", "砸蛋显示时间缩短", "砸蛋增加奖品", "娱乐大厅增加NPC银行职员"]},
        {"date": "2026-06-14", "items": ["再生花园香草药剂使用时间降低", "特殊仓库允许在娱乐大厅内使用", "娱乐大厅增加NPC万能收购", "道具砂糖800袋取消确认选项", "特殊仓库允许存放道具", "追月得意技修改为剑士职业", "任务半山3阿鲁卡那斯的蛋孵化时间降低", "世界BOSS神兽传说合成系统重制"]},
        {"date": "2026-06-17", "items": ["开启端午节活动", "杂货商店上架道具磁石定位仪", "无尽神器增加查看已献祭道具列表功能"]},
        {"date": "2026-06-23", "items": ["修复茱萸木采集无效", "人物宠物佣兵物理输出技能伤害提高至30%", "功能NPC道具管理增加回收砸蛋称号", "竞技场10连新增4把武器掉落", "神兽武器新增弓杖回力小刀", "关闭端午礼包限购NPC"]},
        {"date": "2026-06-27", "items": ["奥义技能支持守护神职业学习", "增加奥义技能必须要转生才可以学习", "树精长老神兽双王传送凭证掉率增加5%", "取消阿尔戈斯任务2贝亚掉落魔族之角", "法兰竞技场10连和砸蛋活动增加低概率获取魔族之角", "进阶区域任务勇闯恶魔城获得宠物蛋几率调整", "武器神兽小刀增加精神属性"]},
        {"date": "2026-07-02", "items": ["修复\"战神铠甲\"物品栏中重叠消失的问题", "修复宠物\"暗黑僧侣\"无法捕捉的问题", "魔珠系列任务调整,取消两个步骤的物品需求", "裂空挑战合成NPC移动到法兰城\"裂空守护者\"旁边位置", "进阶区域\"豆芽商店\"中的道具\"职业存储(绑)\"价格由188降低为88豆芽币", "宝石装饰系统增加2次确认窗口,防止误触", "道具\"荣誉勋章\"耐久提高至100点", "兰国8道具\"豪华的头巾\"\"缓慢的小刀\"\"超级内裤\"耐久提高至10点", "兰国4道具\"祈祷的围巾\"取消兑换次数限制", "进阶区域\"豆芽商店\"中增加道具\"特殊仓库扩展[绑]\""]},
    ]

def calculate_intervals(updates):
    """计算相邻更新的间隔天数"""
    for i in range(len(updates)):
        if i == 0:
            updates[i]["interval"] = None
        else:
            d1 = datetime.strptime(updates[i-1]["date"], "%Y-%m-%d")
            d2 = datetime.strptime(updates[i]["date"], "%Y-%m-%d")
            updates[i]["interval"] = (d2 - d1).days
    return updates

def generate_html(updates):
    """生成最终的 HTML 文件"""
    updates = calculate_intervals(updates)
    
    # 读取 Git commit hash（GitHub Actions 会自动注入 GITHUB_SHA）
    git_sha = os.environ.get("GITHUB_SHA", "")
    version = f"{git_sha[:7]}" if git_sha else "local"
    
    # 准备图表数据 - X轴只显示目标日期
    chart_labels = []
    chart_data = []
    chart_colors = []
    chart_sizes = []
    
    for i in range(1, len(updates)):
        curr = updates[i]["date"][5:]
        chart_labels.append(curr)
        chart_data.append(updates[i]["interval"])
        chart_colors.append("#667eea")
        chart_sizes.append(6)
    
    # 最后一个数据点：到今天的间隔
    last_date = datetime.strptime(updates[-1]["date"], "%Y-%m-%d").replace(tzinfo=CN_TZ)
    today = now_cn()
    days_since = (today - last_date).days
    today_label = today.strftime("%m-%d")
    chart_labels.append(today_label)
    chart_data.append(days_since)
    chart_colors.append("#e74c3c")
    chart_sizes.append(8)
    
    # 统计数据
    intervals_only = [u["interval"] for u in updates[1:]]
    avg_interval = round(sum(intervals_only) / len(intervals_only), 1) if intervals_only else 0
    min_interval = min(intervals_only) if intervals_only else 0
    max_interval = max(intervals_only) if intervals_only else 0
    
    # 生成明细列表HTML - 倒序排列（最新在前），带data-idx正确对应数据
    list_html = ""
    
    today_str = today.strftime("%Y-%m-%d")
    list_html += f'''
        <div class="update-item now-item">
            <span class="update-date"><span id="todayListDate"></span>（今天）</span>
            <span class="update-content summary">等待下次更新...</span>
            <span class="update-interval"><span class="waiting" id="daysSinceWaiting"></span></span>
        </div>'''
    
    for i in range(len(updates) - 1, -1, -1):
        u = updates[i]
        if i == 0:
            interval_str = '<span style="color:#999;">首次</span>'
        else:
            interval_str = f'<span class="days">{u["interval"]} 天</span>'
        summary = u["items"][0][:20] + "..." if len(u["items"][0]) > 20 else u["items"][0]
        if len(u["items"]) > 1:
            summary += f" 等{len(u['items'])}条"
        list_html += f'''
            <div class="update-item" data-idx="{i}">
                <span class="update-date">{u["date"]}</span>
                <span class="update-content summary">{summary}</span>
                <span class="update-interval">{interval_str}</span>
            </div>'''
    
    updates_json = json.dumps(updates, ensure_ascii=False)
    chart_labels_json = json.dumps(chart_labels, ensure_ascii=False)
    chart_data_json = json.dumps(chart_data)
    chart_colors_json = json.dumps(chart_colors)
    chart_sizes_json = json.dumps(chart_sizes)
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>豆芽魔力 更新间隔统计</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            background: #f5f7fa;
            color: #333;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 30px 20px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            font-size: 28px;
            color: #2c3e50;
            margin-bottom: 8px;
        }}
        .header .subtitle {{
            font-size: 14px;
            color: #7f8c8d;
        }}
        .current-date {{
            text-align: center;
            font-size: 16px;
            color: #555;
            margin-bottom: 20px;
            padding: 12px;
            background: #fff;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }}
        .current-date .date-label {{ color: #999; font-size: 13px; }}
        .current-date .date-value {{ font-weight: 600; color: #2c3e50; }}
        .stats-bar {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }}
        .stat-card {{
            background: #fff;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 12px rgba(0,0,0,0.06);
            transition: transform 0.2s;
        }}
        .stat-card:hover {{ transform: translateY(-2px); }}
        .stat-card.highlight {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
        }}
        .stat-card.highlight .stat-label {{ color: rgba(255,255,255,0.8); }}
        .stat-card.highlight .stat-value {{ color: #fff; }}
        .stat-label {{ font-size: 13px; color: #999; margin-bottom: 6px; }}
        .stat-value {{ font-size: 28px; font-weight: 700; color: #2c3e50; }}
        .chart-container {{
            background: #fff;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.06);
            margin-bottom: 20px;
        }}
        .chart-title {{
            font-size: 16px;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
        }}
        .chart-wrapper {{ position: relative; height: 400px; }}
        .update-list {{
            background: #fff;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        }}
        .update-list h3 {{
            font-size: 16px;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
        }}
        .update-item {{
            display: grid;
            grid-template-columns: 90px 1fr 55px;
            align-items: center;
            padding: 7px 10px;
            border-bottom: 1px solid #f0f0f0;
            font-size: 14px;
            line-height: 1.4;
            gap: 8px;
            cursor: pointer;
            transition: background 0.15s;
        }}
        .update-item:hover {{ background: #f8f9ff; }}
        .update-item:last-child {{ border-bottom: none; }}
        .update-item.now-item {{
            background: #fff8f8;
            border-radius: 8px;
            margin-bottom: 4px;
            border-bottom: 2px solid #ffe0e0;
            cursor: default;
        }}
        .update-item.now-item:hover {{ background: #fff8f8; }}
        .update-date {{ font-weight: 600; color: #2c3e50; font-size: 13px; }}
        .update-content.summary {{
            color: #888;
            font-size: 12px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .update-interval {{
            color: #666;
            font-size: 13px;
            text-align: right;
            font-variant-numeric: tabular-nums;
        }}
        .update-interval .days {{ font-weight: 600; color: #667eea; }}
        .update-interval .waiting {{
            font-weight: 600;
            color: #e74c3c;
            animation: pulse 1.5s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.6; }}
        }}
        .sync-info {{
            text-align: center;
            margin: 15px 0;
            font-size: 12px;
            color: #999;
            padding: 8px;
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        }}
        .sync-info .last-sync {{ color: #667eea; font-weight: 500; }}
        .detail-toggle {{
            display: inline-block;
            margin-top: 8px;
            font-size: 12px;
            color: #667eea;
            cursor: pointer;
            text-decoration: underline;
        }}
        .detail-content {{
            display: none;
            margin-top: 8px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 8px;
            font-size: 13px;
            color: #666;
            line-height: 1.6;
        }}
        .detail-content.active {{ display: block; }}
        .detail-content ol {{
            margin: 0;
            padding-left: 20px;
        }}
        .detail-content li {{
            margin: 3px 0;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            font-size: 12px;
            color: #aaa;
        }}
        .version {{
            display: inline-block;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
            font-size: 11px;
            color: #888;
            background: #f0f0f0;
            padding: 2px 8px;
            border-radius: 10px;
            margin-left: 6px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>豆芽魔力 更新间隔统计</h1>
            <p class="subtitle">统计每次维护更新之间的间隔天数</p>
        </div>

        <div class="sync-info">
            <span>数据自动同步于 </span>
            <span class="last-sync">{today_str} {today.strftime("%H:%M")}</span>
            <span> · 每4小时自动抓取语雀最新数据</span>
        </div>

        <div class="current-date">
            <span class="date-label">今天是 </span>
            <span class="date-value" id="todayDisplay"></span>
        </div>

        <div class="stats-bar">
            <div class="stat-card">
                <div class="stat-label">总更新次数</div>
                <div class="stat-value">{len(updates)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">平均间隔</div>
                <div class="stat-value">{avg_interval} 天</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">最短间隔</div>
                <div class="stat-value">{min_interval} 天</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">最长间隔</div>
                <div class="stat-value">{max_interval} 天</div>
            </div>
            <div class="stat-card highlight">
                <div class="stat-label">距上次更新已</div>
                <div class="stat-value" id="daysSinceUpdate">--</div>
            </div>
        </div>

        <div class="chart-container">
            <div class="chart-title">更新间隔天数折线图</div>
            <div class="chart-wrapper">
                <canvas id="intervalChart"></canvas>
            </div>
        </div>

        <div class="update-list">
            <h3>更新记录明细（点击日期查看详情）</h3>
            <div id="updateList">{list_html}</div>
        </div>

        <div class="footer">
            数据来源：语雀 · 豆芽魔力赛季服攻略 · 维护更新记录 · 自动同步
            <span class="version">{version}</span>
        </div>
    </div>

    <script>
        const updates = {updates_json};
        const chartLabels = {chart_labels_json};
        const chartData = {chart_data_json};
        const chartColors = {chart_colors_json};
        const chartSizes = {chart_sizes_json};
        // 中国时区 (UTC+8)
        const CN_OFFSET = 8 * 60 * 60 * 1000;

        function getCNDate(date) {{
            // 转换为北京时间 (UTC+8)
            const utc = date.getTime() + date.getTimezoneOffset() * 60 * 1000;
            return new Date(utc + CN_OFFSET);
        }}

        const lastUpdateDate = getCNDate(new Date(updates[updates.length - 1].date + "T00:00:00+08:00"));

        function getDaysDiff(date1, date2) {{
            const d1 = new Date(date1.getFullYear(), date1.getMonth(), date1.getDate());
            const d2 = new Date(date2.getFullYear(), date2.getMonth(), date2.getDate());
            return Math.floor((d2 - d1) / (1000 * 60 * 60 * 24));
        }}

        function formatDate(date) {{
            const y = date.getFullYear();
            const m = String(date.getMonth() + 1).padStart(2, "0");
            const d = String(date.getDate()).padStart(2, "0");
            const weekDays = ["日", "一", "二", "三", "四", "五", "六"];
            return `${{y}}年${{m}}月${{d}}日 星期${{weekDays[date.getDay()]}}`;
        }}

        function updateToday() {{
            const now = getCNDate(new Date());
            document.getElementById("todayDisplay").textContent = formatDate(now);
            const daysSince = getDaysDiff(lastUpdateDate, now);
            document.getElementById("daysSinceUpdate").textContent = daysSince + " 天";
            // 同步更新明细列表顶部的"今天"条目
            const listDate = document.getElementById("todayListDate");
            if (listDate) {{
                const m = String(now.getMonth() + 1).padStart(2, "0");
                const d = String(now.getDate()).padStart(2, "0");
                listDate.textContent = `${{now.getFullYear()}}-${{m}}-${{d}}`;
            }}
            const waiting = document.getElementById("daysSinceWaiting");
            if (waiting) waiting.textContent = daysSince + " 天";
        }}

        updateToday();
        setInterval(updateToday, 60000);

        // 渲染更新详情 - 通过data-idx正确对应数据（不受倒序影响）
        document.querySelectorAll('.update-item[data-idx]').forEach(item => {{
            const idx = parseInt(item.dataset.idx);
            const data = updates[idx];
            if (!data || !data.items || data.items.length === 0) return;
            
            const detailDiv = document.createElement("div");
            detailDiv.className = "detail-content";
            detailDiv.style.cssText = "display:none; margin-top:6px; padding:8px 12px; background:#f8f9fa; border-radius:6px; font-size:13px; color:#666; line-height:1.6; grid-column:1/-1;";
            const ol = document.createElement("ol");
            ol.style.cssText = "margin:0; padding-left:18px;";
            data.items.forEach(content => {{
                const li = document.createElement("li");
                li.style.cssText = "margin:2px 0;";
                li.textContent = content;
                ol.appendChild(li);
            }});
            detailDiv.appendChild(ol);
            item.appendChild(detailDiv);
            
            // 箭头放在内容列
            const contentSpan = item.querySelector(".update-content");
            contentSpan.innerHTML += ' <span class="arrow" style="color:#667eea;font-size:10px;">▼</span>';
            
            item.addEventListener("click", function() {{
                detailDiv.style.display = detailDiv.style.display === "none" ? "block" : "none";
                const arrow = item.querySelector(".update-content .arrow");
                arrow.textContent = detailDiv.style.display === "none" ? "▼" : "▲";
            }});
        }});

        // 绘制折线图
        const ctx = document.getElementById("intervalChart").getContext("2d");
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, "rgba(102, 126, 234, 0.2)");
        gradient.addColorStop(1, "rgba(102, 126, 234, 0.02)");

        new Chart(ctx, {{
            type: "line",
            data: {{
                labels: chartLabels,
                datasets: [{{
                    label: "间隔天数",
                    data: chartData,
                    borderColor: "#667eea",
                    backgroundColor: gradient,
                    fill: true,
                    tension: 0.3,
                    pointBackgroundColor: chartColors,
                    pointBorderColor: chartColors,
                    pointRadius: chartSizes,
                    pointHoverRadius: 10,
                    borderWidth: 2.5
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        backgroundColor: "rgba(0,0,0,0.8)",
                        titleFont: {{ size: 13 }},
                        bodyFont: {{ size: 14, weight: "bold" }},
                        padding: 12,
                        cornerRadius: 8,
                        callbacks: {{
                            label: function(context) {{
                                if (context.dataIndex === chartData.length - 1) {{
                                    return "已等待 " + context.parsed.y + " 天（未更新）";
                                }}
                                return "间隔 " + context.parsed.y + " 天";
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: "间隔天数",
                            font: {{ size: 13, weight: "bold" }}
                        }},
                        grid: {{ color: "rgba(0,0,0,0.05)" }}
                    }},
                    x: {{
                        grid: {{ display: false }},
                        ticks: {{
                            font: {{ size: 11 }},
                            maxRotation: 45,
                            minRotation: 30
                        }}
                    }}
                }},
                animation: {{
                    duration: 1000,
                    easing: "easeOutQuart"
                }}
            }},
            plugins: [{{
                afterDatasetsDraw: function(chart) {{
                    const ctx = chart.ctx;
                    chart.data.datasets.forEach((dataset, i) => {{
                        const meta = chart.getDatasetMeta(i);
                        meta.data.forEach((point, index) => {{
                            const value = dataset.data[index];
                            const isLast = index === chartData.length - 1;
                            ctx.save();
                            ctx.font = isLast ? "bold 13px sans-serif" : "bold 12px sans-serif";
                            ctx.fillStyle = isLast ? "#e74c3c" : "#555";
                            ctx.textAlign = "center";
                            ctx.textBaseline = "bottom";
                            ctx.fillText(value + "天", point.x, point.y - 12);
                            ctx.restore();
                        }});
                    }});
                }}
            }}]
        }});
    </script>
</body>
</html>'''
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"[成功] 已生成 {OUTPUT_DIR}/index.html")
    print(f"  - 共 {len(updates)} 条更新记录")
    print(f"  - 平均间隔: {avg_interval} 天")
    print(f"  - 距上次更新已 {days_since} 天")

def main():
    print(f"[{now_cn().strftime('%Y-%m-%d %H:%M:%S')}] 开始抓取语雀数据...")
    print(f"目标: {YUQUE_URL}")
    
    updates = None
    
    # 方法1: 从页面提取book_id和doc_id，然后调用API获取Lake格式内容
    print("[方法1] 尝试从语雀API获取...")
    html = fetch_yuque_page()
    if html:
        book_id, doc_id = extract_doc_info(html)
        if book_id and doc_id:
            print(f"[调试] book_id={book_id}, doc_id={doc_id}")
            content = fetch_doc_content(book_id, doc_id)
            if content:
                updates = extract_dates_from_lake(content)
        else:
            print("[警告] 无法从页面提取book_id和doc_id")
    
    # 方法2: 尝试从HTML直接提取（备用）
    if not updates and html:
        print("[方法2] 尝试从HTML直接提取...")
        updates = extract_dates_from_html(html)
    
    # 方法3: 使用本地兜底数据
    if not updates:
        print("[警告] 所有抓取方法均失败，使用本地兜底数据")
        updates = get_fallback_data()
    else:
        print(f"[成功] 抓取到 {len(updates)} 条更新记录")
        # 更新兜底数据（可选：将新数据保存到文件）
    
    # 生成网页
    generate_html(updates)
    print("[完成] 处理完毕！")

if __name__ == "__main__":
    main()
