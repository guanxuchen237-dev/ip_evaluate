USE qidian_data;
ALTER TABLE novel_monthly_stats ADD COLUMN cover_url VARCHAR(255) AFTER book_url;
ALTER TABLE novel_monthly_stats ADD COLUMN abstract TEXT AFTER synopsis;
ALTER TABLE novel_monthly_stats ADD COLUMN latest_chapter VARCHAR(255) AFTER abstract;
ALTER TABLE novel_monthly_stats ADD COLUMN updated_at VARCHAR(50) AFTER latest_chapter;

USE zongheng_analysis_v8;
ALTER TABLE zongheng_book_ranks ADD COLUMN cover_url VARCHAR(255) AFTER book_url;
ALTER TABLE zongheng_book_ranks ADD COLUMN abstract TEXT AFTER cover_url;
ALTER TABLE zongheng_book_ranks ADD COLUMN latest_chapter VARCHAR(255) AFTER abstract;
ALTER TABLE zongheng_book_ranks ADD COLUMN updated_at VARCHAR(50) AFTER latest_chapter;
