# 纵横小说榜单爬虫 (Data Analysis Project)

这是一个经过优化的纵横小说数据采集系统，能够获取完整的榜单书籍数据，包括点击量、推荐数、月票、字数、书粉、签约状态等核心指标。

## 目录结构

- `main_crawler.py`: **主爬虫脚本**。功能包括：
    - 自动清空旧数据
    - 获取实时月票榜单（可配置）
    - 使用Selenium精准提取详情页数据（解决了0值、重复值问题）
    - 数据清洗与存储（MongoDB）
- `check_data.py`: **数据查看工具**。用于在终端漂亮地打印数据库中的书籍数据。
- `requirements.txt`: 项目依赖库。

## 快速开始

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```
   *注意：需要确保已安装 Chrome 浏览器和对应的 ChromeDriver。*

2. **运行爬虫**
   ```bash
   python main_crawler.py
   ```
   爬虫会自动清空数据库并开始抓取前10名书籍（默认配置）。

3. **查看数据**
   ```bash
   python check_data.py
   ```

## 数据说明

爬取的数据存储在本地 MongoDB 的 `novel_analysis` 数据库中，集合名为 `novels`。
主要字段包括：
- `rank`: 榜单排名
- `title`: 书名
- `click_count`: 总点击
- `total_recommendation_count`: 总推荐
- `monthly_ticket_count`: 月票
- `total_words`: 字数
- `status`: 连载状态
- `contract_status`: 签约状态

---
*Created by DeepMind Antigravity*
