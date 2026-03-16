-- 迁移脚本：将 zongheng_chapters 表从 qidian_data 移动到 zongheng_analysis_v8
-- 在 MySQL 客户端中执行此脚本

-- 第1步：在 zongheng_analysis_v8 中创建表结构（如果不存在）
CREATE DATABASE IF NOT EXISTS zongheng_analysis_v8 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE zongheng_analysis_v8;

-- 创建表结构（匹配原表）
CREATE TABLE IF NOT EXISTS zongheng_chapters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    novel_id VARCHAR(50) DEFAULT NULL,
    title VARCHAR(255) NOT NULL,
    chapter_num INT NOT NULL,
    chapter_title VARCHAR(255) DEFAULT NULL,
    content LONGTEXT,
    source VARCHAR(50) DEFAULT 'qidian_data',
    crawl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_title_chapter (title, chapter_num),
    INDEX idx_novel_id (novel_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 第2步：从 qidian_data 复制数据
INSERT INTO zongheng_analysis_v8.zongheng_chapters 
    (id, novel_id, title, chapter_num, chapter_title, content, source, crawl_time)
SELECT 
    id, novel_id, title, chapter_num, chapter_title, content, 'qidian_data', crawl_time
FROM qidian_data.zongheng_chapters
ON DUPLICATE KEY UPDATE
    novel_id = VALUES(novel_id),
    chapter_title = VALUES(chapter_title),
    content = VALUES(content),
    source = VALUES(source),
    crawl_time = VALUES(crawl_time);

-- 第3步：验证迁移结果
SELECT '迁移完成' as status, 
       COUNT(*) as total_rows, 
       COUNT(DISTINCT title) as unique_books
FROM zongheng_analysis_v8.zongheng_chapters;
