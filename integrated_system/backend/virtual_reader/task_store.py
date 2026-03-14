"""
Virtual Reader task and comment persistence (MySQL).
Creates database/tables on first use and provides simple CRUD helpers.
"""

from __future__ import annotations

import json
import os
import random
import re
import threading
import uuid
import math
from decimal import Decimal
from datetime import datetime
from collections import Counter
from typing import Any, Dict, List, Optional

import pymysql

def _load_base_db_config() -> Dict[str, Any]:
    """
    Build DB config with environment defaults and optional data_manager override.
    This avoids hard dependency on heavy data_manager imports.
    """
    env_cfg: Dict[str, Any] = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", "root"),
        "database": os.getenv("ZONGHENG_DB", "zongheng_analysis_v8"),
        "charset": os.getenv("DB_CHARSET", "utf8mb4"),
    }

    for import_path in (
        "backend.data_manager",
        "integrated_system.backend.data_manager",
        "data_manager",
    ):
        try:
            module = __import__(import_path, fromlist=["ZONGHENG_CONFIG"])
            cfg = getattr(module, "ZONGHENG_CONFIG", None)
            if isinstance(cfg, dict):
                merged = dict(env_cfg)
                merged.update(cfg)
                return merged
        except Exception:
            continue

    return env_cfg


ZONGHENG_CONFIG = _load_base_db_config()


INSIGHTS_DB_NAME = os.getenv("INSIGHTS_DB_NAME", "novel_insights")
REAL_COMMENT_TABLE_NAME = os.getenv("REAL_COMMENT_TABLE_NAME", "zongheng_book_comments")
REAL_COMMENT_DB_NAME = os.getenv("REAL_COMMENT_DB_NAME", "").strip()


def _build_insights_config() -> Dict[str, Any]:
    base = dict(ZONGHENG_CONFIG)
    base["database"] = INSIGHTS_DB_NAME
    base.setdefault("charset", "utf8mb4")
    return base


def _get_admin_config() -> Dict[str, Any]:
    cfg = _build_insights_config()
    cfg.pop("database", None)
    return cfg


class VirtualReaderTaskStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._db_ready = False
        self._comment_source: Optional[Dict[str, Any]] = None

    def _connect(self, admin: bool = False) -> pymysql.connections.Connection:
        cfg = _get_admin_config() if admin else _build_insights_config()
        return pymysql.connect(
            **cfg,
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def ensure_db(self) -> None:
        if self._db_ready:
            return
        with self._lock:
            if self._db_ready:
                return
            self._create_database()
            self._create_tables()
            self._ensure_columns()
            self._db_ready = True

    def _create_database(self) -> None:
        conn = self._connect(admin=True)
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{INSIGHTS_DB_NAME}` "
                    "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
        finally:
            conn.close()

    def _create_tables(self) -> None:
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS vr_task (
                        task_id VARCHAR(36) PRIMARY KEY,
                        status VARCHAR(20) NOT NULL,
                        progress INT NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        group_id VARCHAR(36),
                        category VARCHAR(50),
                        novel_title VARCHAR(255),
                        chapter_title VARCHAR(255),
                        source_title VARCHAR(255),
                        source_author VARCHAR(255),
                        source_platform VARCHAR(64),
                        source_book_key VARCHAR(512),
                        persona_ids JSON,
                        total_readers INT DEFAULT 0,
                        completed_readers INT DEFAULT 0,
                        avg_score DECIMAL(4,2),
                        emotion_distribution JSON,
                        error TEXT
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS vr_comment (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        task_id VARCHAR(36) NOT NULL,
                        reader_id VARCHAR(64),
                        reader_name VARCHAR(100),
                        score DECIMAL(3,1),
                        emotion VARCHAR(32),
                        comment TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_task_id (task_id),
                        INDEX idx_emotion (emotion)
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS vr_reader_memory (
                        reader_id VARCHAR(64) NOT NULL,
                        source_book_key VARCHAR(512) NOT NULL,
                        reader_name VARCHAR(100),
                        memory_json JSON,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (reader_id, source_book_key),
                        INDEX idx_source_book_key (source_book_key)
                    )
                    """
                )
        finally:
            conn.close()

    def _ensure_columns(self) -> None:
        required_columns = {
            "source_title": "VARCHAR(255)",
            "source_author": "VARCHAR(255)",
            "source_platform": "VARCHAR(64)",
            "source_book_key": "VARCHAR(512)",
        }

        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                for column_name, column_type in required_columns.items():
                    cursor.execute(
                        """
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = %s
                          AND table_name = 'vr_task'
                          AND column_name = %s
                        LIMIT 1
                        """,
                        (INSIGHTS_DB_NAME, column_name),
                    )
                    exists = cursor.fetchone() is not None
                    if not exists:
                        cursor.execute(
                            f"ALTER TABLE vr_task ADD COLUMN {column_name} {column_type}"
                        )

                cursor.execute(
                    """
                    SELECT 1
                    FROM information_schema.statistics
                    WHERE table_schema = %s
                      AND table_name = 'vr_task'
                      AND index_name = 'idx_source_lookup'
                    LIMIT 1
                    """,
                    (INSIGHTS_DB_NAME,),
                )
                idx_exists = cursor.fetchone() is not None
                if not idx_exists:
                    cursor.execute(
                        """
                        ALTER TABLE vr_task
                        ADD INDEX idx_source_lookup (source_platform, source_title, source_author)
                        """
                    )
        finally:
            conn.close()

    def create_task(
        self,
        *,
        group_id: Optional[str],
        category: Optional[str],
        novel_title: str,
        chapter_title: str,
        source_title: Optional[str],
        source_author: Optional[str],
        source_platform: Optional[str],
        source_book_key: Optional[str],
        persona_ids: Optional[List[str]],
        request_payload: Optional[Dict[str, Any]] = None, # kept but unused
    ) -> str:
        self.ensure_db()
        task_id = str(uuid.uuid4())
        persona_json = json.dumps(persona_ids or [], ensure_ascii=False)

        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO vr_task (
                        task_id, status, progress, group_id, category,
                        novel_title, chapter_title,
                        source_title, source_author, source_platform, source_book_key,
                        persona_ids
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        task_id,
                        "pending",
                        0,
                        group_id,
                        category,
                        novel_title,
                        chapter_title,
                        source_title,
                        source_author,
                        source_platform,
                        source_book_key,
                        persona_json,
                    ),
                )
        finally:
            conn.close()

        return task_id

    def update_task(self, task_id: str, **fields: Any) -> None:
        self.ensure_db()
        # 移除请求更新已删除字段的数据
        fields = {k: v for k, v in fields.items() if k not in {"request_payload", "events"}}
        if not fields:
            return

        updates = []
        values = []
        for key, value in fields.items():
            if key in {"persona_ids", "emotion_distribution"} and value is not None:
                value = json.dumps(value, ensure_ascii=False)
            updates.append(f"{key} = %s")
            values.append(value)
        values.append(task_id)

        sql = f"UPDATE vr_task SET {', '.join(updates)} WHERE task_id = %s"
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, values)
        finally:
            conn.close()

    def insert_comment(
        self,
        task_id: str,
        *,
        reader_id: str,
        reader_name: str,
        vip_level: int = 0, # kept but unused
        score: float,
        confidence: Optional[float] = None, # kept but unused
        emotion: str,
        comment: str,
        evidence_ids: Optional[List[str]] = None, # kept but unused
        reader_region: Optional[str] = None, # kept but unused
        simulated_duration: int = 0, # kept but unused
        profile_snapshot: Optional[Dict[str, Any]] = None, # kept but unused
        reply_to_comment_id: Optional[int] = None, # kept but unused
    ) -> Optional[int]:
        self.ensure_db()

        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO vr_comment (
                        task_id, reader_id, reader_name,
                        score, emotion, comment
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        task_id,
                        reader_id,
                        reader_name,
                        score,
                        emotion,
                        comment,
                    ),
                )
                return cursor.lastrowid
        finally:
            conn.close()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        self.ensure_db()
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM vr_task WHERE task_id = %s", (task_id,))
                row = cursor.fetchone()
                return self._normalize_task_row(row) if row else None
        finally:
            conn.close()

    def get_reader_memory(
        self, reader_id: str, source_book_key: Optional[str], limit: int = 6
    ) -> List[str]:
        self.ensure_db()
        reader_id = str(reader_id or "").strip()
        source_book_key = str(source_book_key or "").strip()
        if not reader_id or not source_book_key:
            return []

        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT memory_json
                    FROM vr_reader_memory
                    WHERE reader_id = %s AND source_book_key = %s
                    LIMIT 1
                    """,
                    (reader_id, source_book_key),
                )
                row = cursor.fetchone() or {}
        finally:
            conn.close()

        memories = self._parse_json_field(row.get("memory_json"), [])
        if not isinstance(memories, list):
            return []
        cleaned = []
        for item in memories:
            text = self._sanitize_comment_text(item)
            if text:
                cleaned.append(text[:200])
        if limit > 0:
            cleaned = cleaned[-limit:]
        return cleaned

    def append_reader_memory(
        self,
        *,
        reader_id: str,
        reader_name: str,
        source_book_key: Optional[str],
        new_comments: List[str],
        max_items: int = 20,
    ) -> None:
        self.ensure_db()
        reader_id = str(reader_id or "").strip()
        source_book_key = str(source_book_key or "").strip()
        if not reader_id or not source_book_key:
            return

        existing = self.get_reader_memory(reader_id, source_book_key, limit=max_items)
        merged = list(existing)
        for text in new_comments:
            value = self._sanitize_comment_text(text)
            if not value:
                continue
            duplicate_idx = None
            for idx, old in enumerate(merged):
                if value == old or self._jaccard_similarity(value, old) >= 0.88:
                    duplicate_idx = idx
                    break
            if duplicate_idx is not None:
                merged.pop(duplicate_idx)
            merged.append(value[:200])

        if max_items > 0:
            merged = merged[-max_items:]

        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO vr_reader_memory (
                        reader_id, source_book_key, reader_name, memory_json
                    )
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        reader_name = VALUES(reader_name),
                        memory_json = VALUES(memory_json)
                    """,
                    (
                        reader_id,
                        source_book_key,
                        str(reader_name or "").strip()[:100],
                        json.dumps(merged, ensure_ascii=False),
                    ),
                )
        finally:
            conn.close()

    def get_comments(self, task_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        self.ensure_db()
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT c.*
                    FROM vr_comment c
                    WHERE c.task_id = %s
                      AND (c.comment IS NULL OR c.comment NOT LIKE '%%任务已提交%%')
                      AND (c.comment IS NULL OR c.comment NOT LIKE '%%已暂停模拟%%')
                      AND (c.reader_name IS NULL OR LOWER(c.reader_name) <> 'system')
                    ORDER BY c.id ASC
                    LIMIT %s OFFSET %s
                    """,
                    (task_id, limit, offset),
                )
                rows = cursor.fetchall()
                # 为每条评论计算 sentiment（从 score 转换）
                results = []
                for row in rows:
                    item = dict(row) if row else {}
                    # score 1-5 转换为 sentiment -1 到 1
                    score = float(item.get('score', 3.0) or 3.0)
                    item['sentiment'] = round((score - 3.0) / 2.0, 2)
                    results.append(item)
                return results
        finally:
            conn.close()
    def get_tasks_by_source(
        self,
        *,
        source_title: Optional[str] = None,
        source_author: Optional[str] = None,
        source_platform: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        self.ensure_db()
        conditions: List[str] = []
        values: List[Any] = []

        if source_title:
            conditions.append("source_title = %s")
            values.append(source_title)
        if source_author:
            conditions.append("source_author = %s")
            values.append(source_author)
        if source_platform:
            conditions.append("source_platform = %s")
            values.append(source_platform)

        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        values.extend([limit, offset])
        sql = (
            "SELECT * FROM vr_task "
            f"{where_sql} "
            "ORDER BY created_at DESC LIMIT %s OFFSET %s"
        )

        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, values)
                rows = cursor.fetchall()
                return [self._normalize_task_row(row) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def _safe_ident(name: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_]+", name or ""):
            raise ValueError(f"unsafe identifier: {name}")
        return name

    @staticmethod
    def _normalize_region(text: str) -> str:
        value = (text or "").strip()
        if not value:
            return ""
        value = re.sub(r"\s+", "", value)
        value = value.replace("\u7701", "").replace("\u5e02", "").replace("\u81ea\u6cbb\u533a", "")
        value = value.replace("\u7279\u522b\u884c\u653f\u533a", "").replace("\u58ee\u65cf", "").replace("\u56de\u65cf", "")
        value = value.replace("\u7ef4\u543e\u5c14", "")
        return value[:16]

    @staticmethod
    def _sanitize_comment_text(text: Any) -> str:
        value = str(text or "").strip()
        if not value:
            return ""
        value = re.sub(r"\s+", " ", value)
        value = re.sub(r"<[^>]+>", "", value)
        value = value.replace("\u3000", " ")
        if len(value) < 8:
            return ""
        banned = ("任务已提交", "已暂停模拟", "system")
        lowered = value.lower()
        if any(token in lowered for token in banned):
            return ""
        noisy_patterns = ("全是问号", "几个意思", "玩猜谜", "整页的问号", "猜谜呢")
        if any(p in value for p in noisy_patterns):
            return ""
        # Drop noisy corpus rows with little semantic value.
        if re.search(r"(.)\1{5,}", value):
            return ""
        punctuation = re.findall(r"[!！?？,，.。;；:：~～\-_=+*^`'\"()（）\[\]{}<>/\\|@#$%&]", value)
        if len(punctuation) / max(len(value), 1) > 0.35:
            return ""
        if value.count("?") + value.count("？") >= max(3, len(value) // 8):
            return ""
        if not re.search(r"[\u4e00-\u9fffA-Za-z0-9]", value):
            return ""
        return value[:220]

    @staticmethod
    def _semantic_units(text: str) -> List[str]:
        value = str(text or "").lower()
        if not value:
            return []
        units: List[str] = []
        for token in re.findall(r"[a-z0-9]{2,}", value):
            units.append(token)
        for token in re.findall(r"[\u4e00-\u9fff]+", value):
            if len(token) <= 1:
                continue
            if len(token) == 2:
                units.append(token)
                continue
            for i in range(len(token) - 1):
                units.append(token[i : i + 2])
        return units

    @staticmethod
    def _jaccard_similarity(text_a: str, text_b: str) -> float:
        units_a = set(VirtualReaderTaskStore._semantic_units(text_a))
        units_b = set(VirtualReaderTaskStore._semantic_units(text_b))
        if not units_a or not units_b:
            return 0.0
        return len(units_a & units_b) / max(len(units_a | units_b), 1)

    def _discover_comment_source(self) -> Optional[Dict[str, Any]]:
        if self._comment_source is not None:
            return self._comment_source

        db_candidates: List[str] = []
        if REAL_COMMENT_DB_NAME:
            db_candidates.append(REAL_COMMENT_DB_NAME)
        db_candidates.extend(
            [
                INSIGHTS_DB_NAME,
                str(ZONGHENG_CONFIG.get("database") or "").strip(),
                "zongheng_analysis_v8",
                "zongheng_analys_v8",
            ]
        )

        deduped = []
        for db in db_candidates:
            if db and db not in deduped:
                deduped.append(db)

        conn = self._connect(admin=True)
        try:
            with conn.cursor() as cursor:
                for db_name in deduped:
                    cursor.execute(
                        """
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema = %s
                          AND table_name = %s
                        """,
                        (db_name, REAL_COMMENT_TABLE_NAME),
                    )
                    fetched = cursor.fetchall()
                    cols = set()
                    for row in fetched:
                        if isinstance(row, dict):
                            if "column_name" in row:
                                cols.add(str(row["column_name"]))
                            elif "COLUMN_NAME" in row:
                                cols.add(str(row["COLUMN_NAME"]))
                            elif row:
                                cols.add(str(next(iter(row.values()))))
                    if not cols:
                        continue

                    def pick(*candidates: str) -> Optional[str]:
                        for key in candidates:
                            if key in cols:
                                return key
                        return None

                    content_col = pick("content", "comment", "comment_content")
                    title_col = pick("book_title", "title", "novel_title")
                    region_col = pick("ip_region", "region", "province", "location")
                    date_col = pick("comment_date", "create_time", "created_at", "crawl_time")
                    if not content_col:
                        continue

                    self._comment_source = {
                        "db": db_name,
                        "table": REAL_COMMENT_TABLE_NAME,
                        "content_col": content_col,
                        "title_col": title_col,
                        "region_col": region_col,
                        "date_col": date_col,
                    }
                    return self._comment_source
        finally:
            conn.close()

        self._comment_source = None
        return None

    def get_real_comment_samples(
        self,
        *,
        source_title: Optional[str],
        region: Optional[str] = None,
        limit: int = 24,
        query_text: Optional[str] = None,
        pool_size: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        source = self._discover_comment_source()
        if not source:
            return []

        source_title = (source_title or "").strip()
        normalized_region = self._normalize_region(region or "")
        if limit <= 0:
            return []

        db_name = self._safe_ident(str(source["db"]))
        table_name = self._safe_ident(str(source["table"]))
        content_col = self._safe_ident(str(source["content_col"]))
        title_col = source.get("title_col")
        region_col = source.get("region_col")
        date_col = source.get("date_col")
        if title_col:
            title_col = self._safe_ident(str(title_col))
        if region_col:
            region_col = self._safe_ident(str(region_col))
        if date_col:
            date_col = self._safe_ident(str(date_col))

        def _query(use_title: bool) -> List[Dict[str, Any]]:
            clauses = [
                f"`{content_col}` IS NOT NULL",
                f"CHAR_LENGTH(TRIM(`{content_col}`)) BETWEEN 6 AND 220",
            ]
            values: List[Any] = []

            if use_title and title_col and source_title:
                clauses.append(f"(`{title_col}` = %s OR `{title_col}` LIKE %s)")
                values.extend([source_title, f"%{source_title}%"])

            if normalized_region and region_col:
                clauses.append(
                   f"REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(`{region_col}`, '省', ''), '市', ''), '自治区', ''), '特别行政区', ''), '壮族', ''), '回族', ''), '维吾尔', '') LIKE %s"
                )
                values.append(f"{normalized_region}%")

            where_sql = " AND ".join(clauses)
            order_sql = f"`{date_col}` DESC" if date_col else "RAND()"
            fetch_limit = max(limit * 10, pool_size or 180)
            values.append(fetch_limit)
            sql = (
                f"SELECT `{content_col}` AS content"
                + (f", `{region_col}` AS region" if region_col else ", '' AS region")
                + (f", `{date_col}` AS created_at_ts" if date_col else ", NULL AS created_at_ts")
                + f" FROM `{db_name}`.`{table_name}`"
                + f" WHERE {where_sql} ORDER BY {order_sql} LIMIT %s"
            )

            conn = self._connect()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql, values)
                    return cursor.fetchall()
            finally:
                conn.close()

        rows = _query(use_title=True)
        if not rows:
            rows = _query(use_title=False)
        if not rows:
            return []

        cleaned: List[Dict[str, Any]] = []
        seen = set()
        for row in rows:
            text = self._sanitize_comment_text(row.get("content"))
            if not text or text in seen:
                continue
            seen.add(text)
            cleaned.append(
                {
                    "content": text,
                    "region": str(row.get("region") or "").strip(),
                    "created_at_ts": row.get("created_at_ts"),
                }
            )
        if not cleaned:
            return []

        if not query_text:
            random.shuffle(cleaned)
            return [
                {"content": item["content"], "region": item["region"]}
                for item in cleaned[:limit]
            ]

        query_units = Counter(self._semantic_units(query_text))
        if not query_units:
            random.shuffle(cleaned)
            return [
                {"content": item["content"], "region": item["region"]}
                for item in cleaned[:limit]
            ]

        query_norm = math.sqrt(sum(v * v for v in query_units.values()))
        ranked: List[Dict[str, Any]] = []
        for item in cleaned:
            units = self._semantic_units(item["content"])
            if not units:
                continue
            freq = Counter(units)
            dot = 0.0
            for token, q_count in query_units.items():
                dot += q_count * float(freq.get(token, 0))
            base = dot / (math.sqrt(sum(v * v for v in freq.values())) * max(query_norm, 1e-9))
            region_bonus = 0.0
            if normalized_region and item.get("region"):
                item_region = self._normalize_region(str(item["region"]))
                if item_region.startswith(normalized_region):
                    region_bonus = 0.08
            if base <= 0.01 and region_bonus <= 0:
                continue
            ranked.append(
                {
                    "score": base + region_bonus,
                    "content": item["content"],
                    "region": item["region"],
                }
            )

        if not ranked:
            random.shuffle(cleaned)
            return [
                {"content": item["content"], "region": item["region"]}
                for item in cleaned[:limit]
            ]

        ranked.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)
        top_pool = ranked[: max(limit * 6, 60)]

        selected: List[Dict[str, str]] = []
        for item in top_pool:
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            if float(item.get("score", 0.0)) < 0.035 and len(selected) >= max(4, limit // 2):
                continue
            duplicated = False
            for existing in selected:
                if self._jaccard_similarity(content, existing["content"]) >= 0.86:
                    duplicated = True
                    break
            if duplicated:
                continue
            selected.append(
                {
                    "content": content,
                    "region": str(item.get("region") or "").strip(),
                }
            )
            if len(selected) >= limit:
                break

        if len(selected) < limit:
            for item in top_pool:
                content = str(item.get("content") or "").strip()
                if not content:
                    continue
                if any(content == x["content"] for x in selected):
                    continue
                selected.append(
                    {
                        "content": content,
                        "region": str(item.get("region") or "").strip(),
                    }
                )
                if len(selected) >= limit:
                    break

        return selected[:limit]

    def get_book_hot_regions(
        self, *, source_title: Optional[str], limit: int = 12
    ) -> List[Dict[str, Any]]:
        source = self._discover_comment_source()
        if not source:
            return []

        source_title = (source_title or "").strip()
        region_col = source.get("region_col")
        title_col = source.get("title_col")
        if not source_title or not region_col or not title_col:
            return []

        db_name = self._safe_ident(str(source["db"]))
        table_name = self._safe_ident(str(source["table"]))
        region_col = self._safe_ident(str(region_col))
        title_col = self._safe_ident(str(title_col))

        sql = (
            f"SELECT `{region_col}` AS region, COUNT(*) AS cnt "
            f"FROM `{db_name}`.`{table_name}` "
            f"WHERE `{region_col}` IS NOT NULL AND `{region_col}` <> '' "
            f"  AND (`{title_col}` = %s OR `{title_col}` LIKE %s) "
            f"GROUP BY `{region_col}` "
            f"ORDER BY cnt DESC LIMIT %s"
        )

        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, (source_title, f"%{source_title}%", max(1, limit)))
                rows = cursor.fetchall()
        finally:
            conn.close()

        result: List[Dict[str, Any]] = []
        for row in rows:
            region = str(row.get("region") or "").strip()
            if not region:
                continue
            result.append({"region": region, "count": int(row.get("cnt") or 0)})
        return result

    @staticmethod
    def _parse_json_field(value: Any, default: Any) -> Any:
        if value is None:
            return default
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return default
        return default

    @staticmethod
    def _normalize_scalar(value: Any) -> Any:
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    def _normalize_task_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {k: self._normalize_scalar(v) for k, v in row.items()}
        normalized["persona_ids"] = self._parse_json_field(
            normalized.get("persona_ids"), []
        )
        normalized["emotion_distribution"] = self._parse_json_field(
            normalized.get("emotion_distribution"), {}
        )
        normalized["request_payload"] = self._parse_json_field(
            normalized.get("request_payload"), {}
        )
        normalized["events"] = self._parse_json_field(
            normalized.get("events"), []
        )
        return normalized

    def _normalize_comment_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {k: self._normalize_scalar(v) for k, v in row.items()}
        normalized["profile_snapshot"] = self._parse_json_field(
            normalized.get("profile_snapshot"), {}
        )
        return normalized


task_store = VirtualReaderTaskStore()
