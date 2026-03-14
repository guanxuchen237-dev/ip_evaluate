"""
Virtual reader service.
Coordinates reader group creation, simulation execution, and task persistence.
"""

import concurrent.futures
import random
import re
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from .agent import VirtualReaderAgent
from .manager import persona_manager
from .profile_generator import reader_profile_generator
from .story_context_service import story_context_service
from .task_store import task_store


class VirtualReaderService:
    def __init__(self) -> None:
        self.active_groups: Dict[str, List[Any]] = {}
        self.simulation_results: Dict[str, Any] = {}
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
        task_store.ensure_db()

    def create_reader_group(self, count: int, category: str) -> Dict[str, Any]:
        group_id = str(uuid.uuid4())
        profiles = reader_profile_generator.generate_profiles(count, category)
        self.active_groups[group_id] = profiles
        return {
            "group_id": group_id,
            "count": len(profiles),
            "profiles": [p.to_dict() for p in profiles],
        }

    def create_group_from_personas(self, persona_ids: List[str]) -> Dict[str, Any]:
        group_id = str(uuid.uuid4())
        profiles = []
        for pid in persona_ids:
            persona = persona_manager.get_persona(pid)
            if persona:
                profiles.append(persona)

        self.active_groups[group_id] = profiles
        return {
            "group_id": group_id,
            "count": len(profiles),
            "profiles": [p.to_dict() for p in profiles],
        }

    def get_group(self, group_id: str) -> List[Dict[str, Any]]:
        profiles = self.active_groups.get(group_id, [])
        return [p.to_dict() for p in profiles]

    def simulate_reading(
        self,
        group_id: str,
        novel_title: str,
        chapter_title: str,
        content: str,
        category: Optional[str] = None,
        persona_ids: Optional[List[str]] = None,
        source_title: Optional[str] = None,
        source_author: Optional[str] = None,
        source_platform: Optional[str] = None,
        source_book_key: Optional[str] = None,
        dedup_mode: str = "balanced",
        use_story_context: bool = True,
        force_refresh_story_context: bool = False,
        use_web_search: bool = True,
    ) -> Dict[str, Any]:
        dedup_mode = self._normalize_dedup_mode(dedup_mode)
        payload = self._build_request_payload(
            group_id,
            novel_title,
            chapter_title,
            content,
            category,
            persona_ids,
            source_title,
            source_author,
            source_platform,
            source_book_key,
            dedup_mode,
            use_story_context,
            force_refresh_story_context,
            use_web_search,
        )
        task_id = task_store.create_task(
            group_id=group_id,
            category=category,
            novel_title=novel_title,
            chapter_title=chapter_title,
            source_title=source_title or novel_title,
            source_author=source_author,
            source_platform=source_platform,
            source_book_key=source_book_key
            or self._build_source_book_key(
                source_platform, source_title or novel_title, source_author
            ),
            persona_ids=persona_ids,
            request_payload=payload,
        )
        summary = self._run_simulation_task(
            task_id,
            group_id,
            novel_title,
            chapter_title,
            content,
            source_title=source_title or novel_title,
            source_book_key=source_book_key
            or self._build_source_book_key(
                source_platform, source_title or novel_title, source_author
            ),
            dedup_mode=dedup_mode,
            use_story_context=use_story_context,
            force_refresh_story_context=force_refresh_story_context,
            use_web_search=use_web_search,
        )
        summary["task_id"] = task_id
        return summary

    def simulate_reading_async(
        self,
        group_id: str,
        novel_title: str,
        chapter_title: str,
        content: str,
        category: Optional[str] = None,
        persona_ids: Optional[List[str]] = None,
        source_title: Optional[str] = None,
        source_author: Optional[str] = None,
        source_platform: Optional[str] = None,
        source_book_key: Optional[str] = None,
        dedup_mode: str = "balanced",
        use_story_context: bool = True,
        force_refresh_story_context: bool = False,
        use_web_search: bool = True,
    ) -> Dict[str, Any]:
        dedup_mode = self._normalize_dedup_mode(dedup_mode)
        payload = self._build_request_payload(
            group_id,
            novel_title,
            chapter_title,
            content,
            category,
            persona_ids,
            source_title,
            source_author,
            source_platform,
            source_book_key,
            dedup_mode,
            use_story_context,
            force_refresh_story_context,
            use_web_search,
        )
        task_id = task_store.create_task(
            group_id=group_id,
            category=category,
            novel_title=novel_title,
            chapter_title=chapter_title,
            source_title=source_title or novel_title,
            source_author=source_author,
            source_platform=source_platform,
            source_book_key=source_book_key
            or self._build_source_book_key(
                source_platform, source_title or novel_title, source_author
            ),
            persona_ids=persona_ids,
            request_payload=payload,
        )
        thread = threading.Thread(
            target=self._run_simulation_task,
            args=(task_id, group_id, novel_title, chapter_title, content),
            kwargs={
                "source_title": source_title or novel_title,
                "source_book_key": source_book_key
                or self._build_source_book_key(
                    source_platform, source_title or novel_title, source_author
                ),
                "dedup_mode": dedup_mode,
                "use_story_context": use_story_context,
                "force_refresh_story_context": force_refresh_story_context,
                "use_web_search": use_web_search,
            },
            daemon=True,
        )
        thread.start()
        return {"task_id": task_id, "status": "pending"}

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return task_store.get_task(task_id)

    def get_comments(
        self, task_id: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        return task_store.get_comments(task_id, limit=limit, offset=offset)

    def get_tasks_by_source(
        self,
        *,
        source_title: Optional[str] = None,
        source_author: Optional[str] = None,
        source_platform: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        return task_store.get_tasks_by_source(
            source_title=source_title,
            source_author=source_author,
            source_platform=source_platform,
            limit=limit,
            offset=offset,
        )

    def get_story_context(
        self,
        *,
        novel_title: str,
        chapter_title: str,
        content: str,
        source_title: Optional[str] = None,
        source_author: Optional[str] = None,
        source_platform: Optional[str] = None,
        force_refresh: bool = False,
        use_web_search: bool = True,
    ) -> Dict[str, Any]:
        return story_context_service.build_story_context(
            novel_title=novel_title,
            chapter_title=chapter_title,
            chapter_content=content,
            source_title=source_title or novel_title,
            source_author=source_author,
            source_platform=source_platform,
            force_refresh=force_refresh,
            use_web_search=use_web_search,
        )

    def _build_request_payload(
        self,
        group_id: str,
        novel_title: str,
        chapter_title: str,
        content: str,
        category: Optional[str],
        persona_ids: Optional[List[str]],
        source_title: Optional[str],
        source_author: Optional[str],
        source_platform: Optional[str],
        source_book_key: Optional[str],
        dedup_mode: str,
        use_story_context: bool,
        force_refresh_story_context: bool,
        use_web_search: bool,
    ) -> Dict[str, Any]:
        content_preview = content[:2000]
        if len(content) > 2000:
            content_preview += "\n...(content truncated)..."
        return {
            "group_id": group_id,
            "category": category,
            "novel_title": novel_title,
            "chapter_title": chapter_title,
            "persona_ids": persona_ids or [],
            "source_title": source_title or novel_title,
            "source_author": source_author,
            "source_platform": source_platform,
            "source_book_key": source_book_key
            or self._build_source_book_key(
                source_platform, source_title or novel_title, source_author
            ),
            "dedup_mode": dedup_mode,
            "use_story_context": bool(use_story_context),
            "force_refresh_story_context": bool(force_refresh_story_context),
            "use_web_search": bool(use_web_search),
            "content_length": len(content),
            "content_preview": content_preview,
        }

    @staticmethod
    def _build_source_book_key(
        source_platform: Optional[str],
        source_title: Optional[str],
        source_author: Optional[str],
    ) -> Optional[str]:
        if not source_title:
            return None
        platform = (source_platform or "unknown").strip().lower()
        title = source_title.strip().lower()
        author = (source_author or "").strip().lower()
        return f"{platform}|{title}|{author}"

    @staticmethod
    def _normalize_dedup_mode(mode: Optional[str]) -> str:
        value = str(mode or "balanced").strip().lower()
        if value in {"strict", "balanced", "lenient"}:
            return value
        return "balanced"

    @staticmethod
    def _resolve_dedup_policy(mode: str) -> Dict[str, float]:
        # strict: more aggressive dedup (lower threshold)
        # balanced: default
        # lenient: keep diversity (higher threshold)
        profiles = {
            "strict": {
                "duplicate_threshold": 0.74,
                "rebuilt_threshold": 0.76,
                "global_threshold": 0.68,
            },
            "balanced": {
                "duplicate_threshold": 0.82,
                "rebuilt_threshold": 0.82,
                "global_threshold": 0.75,
            },
            "lenient": {
                "duplicate_threshold": 0.9,
                "rebuilt_threshold": 0.9,
                "global_threshold": 0.84,
            },
        }
        return profiles.get(mode, profiles["balanced"])

    def _run_simulation_task(
        self,
        task_id: str,
        group_id: str,
        novel_title: str,
        chapter_title: str,
        content: str,
        source_title: Optional[str] = None,
        source_book_key: Optional[str] = None,
        dedup_mode: str = "balanced",
        use_story_context: bool = True,
        force_refresh_story_context: bool = False,
        use_web_search: bool = True,
    ) -> Dict[str, Any]:
        profiles = self.active_groups.get(group_id)
        if not profiles:
            task_store.update_task(task_id, status="failed", error="Group not found")
            return {"error": "Group not found"}

        book_title_for_match = (source_title or novel_title or "").strip()
        task_meta = task_store.get_task(task_id) or {}
        request_payload = task_meta.get("request_payload") or {}
        if not isinstance(request_payload, dict):
            request_payload = {}
        dedup_mode = self._normalize_dedup_mode(
            dedup_mode or str(request_payload.get("dedup_mode", "balanced"))
        )
        use_story_context = bool(
            request_payload.get("use_story_context", use_story_context)
        )
        force_refresh_story_context = bool(
            request_payload.get(
                "force_refresh_story_context", force_refresh_story_context
            )
        )
        use_web_search = bool(request_payload.get("use_web_search", use_web_search))
        dedup_policy = self._resolve_dedup_policy(dedup_mode)
        book_key = str(source_book_key or task_meta.get("source_book_key") or "").strip()
        if not book_key:
            book_key = (
                self._build_source_book_key(
                    str(task_meta.get("source_platform") or "").strip() or None,
                    book_title_for_match,
                    str(task_meta.get("source_author") or "").strip() or None,
                )
                or ""
            )
        semantic_query = (
            f"书名:{book_title_for_match}\n章节:{chapter_title}\n"
            f"内容摘要:{content[:1800]}"
        )
        story_context: Dict[str, Any] = {}
        if use_story_context:
            try:
                story_context = story_context_service.build_story_context(
                    novel_title=novel_title,
                    chapter_title=chapter_title,
                    chapter_content=content,
                    source_title=book_title_for_match,
                    source_author=str(task_meta.get("source_author") or "").strip()
                    or None,
                    source_platform=str(task_meta.get("source_platform") or "").strip()
                    or None,
                    force_refresh=force_refresh_story_context,
                    use_web_search=use_web_search,
                )
            except Exception as exc:  # noqa: BLE001
                print(f"Story context build failed: {exc}")
                story_context = {}

        story_context_event: Optional[Dict[str, Any]] = None
        if story_context:
            story_context_event = {
                "type": "story_context",
                "message": "剧情上下文已加载",
                "confidence": float(story_context.get("confidence", 0.0)),
                "source_count": len(story_context.get("source_refs", []) or []),
                "timestamp": time.time(),
            }
        hot_regions = task_store.get_book_hot_regions(source_title=book_title_for_match, limit=12)
        region_pool: List[str] = []
        for item in hot_regions:
            region_name = str(item.get("region") or "").strip()
            region_count = int(item.get("count") or 0)
            if not region_name:
                continue
            region_pool.extend([region_name] * max(1, min(region_count, 20)))

        # Assign a default region to profiles that do not have one.
        for profile in profiles:
            region = str(getattr(profile, "region", "") or "").strip()
            if region:
                continue
            if region_pool:
                region = random.choice(region_pool)
            else:
                region = random.choice(["北京", "上海", "广东", "江苏", "浙江", "四川"])
            try:
                setattr(profile, "region", region)
            except Exception:
                pass

        global_samples = task_store.get_real_comment_samples(
            source_title=book_title_for_match,
            limit=260,
            query_text=semantic_query,
            pool_size=480,
        )
        global_distribution = self._build_distribution_profile(global_samples)
        samples_by_region: Dict[str, List[Dict[str, str]]] = {}

        def resolve_style_examples(region_name: str) -> List[Dict[str, str]]:
            if not region_name:
                return global_samples
            if region_name not in samples_by_region:
                samples_by_region[region_name] = task_store.get_real_comment_samples(
                    source_title=book_title_for_match,
                    region=region_name,
                    limit=120,
                    query_text=semantic_query,
                    pool_size=300,
                )
            return samples_by_region[region_name] or global_samples

        agents = [VirtualReaderAgent(p) for p in profiles]
        total = len(agents)
        detected_events: List[Dict[str, Any]] = [story_context_event] if story_context_event else []
        task_store.update_task(
            task_id,
            status="running",
            progress=0,
            total_readers=total,
            completed_readers=0,
            events=detected_events,
        )

        print(f"Start simulation with {total} readers for {novel_title}...", flush=True)

        results: List[Dict[str, Any]] = []
        emotion_counts: Dict[str, int] = {}
        score_sum = 0.0
        completed = 0
        last_error = None
        seen_comments: List[str] = []
        
        # Interaction Context: list of dicts with id, reader_name, comment
        context_accumulator: List[Dict[str, Any]] = []
        
        # Chunk agents for sequential processing to enable replies
        chunk_size = 5
        agent_chunks = [agents[i:i + chunk_size] for i in range(0, len(agents), chunk_size)]

        for chunk_agents in agent_chunks:
            chunk_futures: Dict[concurrent.futures.Future, Dict[str, Any]] = {}

            # Prepare context for this chunk (snapshot)
            # Use last 8 comments to keep context relevant and prompt short
            current_context = list(context_accumulator[-8:])
            
            for agent in chunk_agents:
                region_name = str(getattr(agent.profile, "region", "") or "").strip()
                reader_id = str(
                    getattr(agent.profile, "user_id", getattr(agent.profile, "id", "unknown"))
                ).strip()
                if book_key:
                    history = task_store.get_reader_memory(reader_id, book_key, limit=6)
                    if history:
                        agent.seed_memory(history)
                candidate_samples = resolve_style_examples(region_name)
                style_examples = self._pick_style_examples(candidate_samples, limit=6)
                distribution = self._build_distribution_profile(
                    candidate_samples if len(candidate_samples) >= 20 else global_samples
                ) or global_distribution
                
                # Submit with context
                future = self._executor.submit(
                    agent.read_and_comment,
                    novel_title,
                    chapter_title,
                    content,
                    style_examples,
                    story_context=story_context,
                    context_comments=current_context,
                )
                chunk_futures[future] = {
                    "agent": agent,
                    "style_examples": style_examples,
                    "distribution": distribution,
                    "history": history if book_key else [],
                    "context_snapshot": current_context,
                }

            # Process chunk completion
            for future in concurrent.futures.as_completed(chunk_futures):
                try:
                    context = chunk_futures[future]
                    distribution = context.get("distribution", global_distribution)
                    style_examples = context.get("style_examples", [])
                    context_snapshot = context.get("context_snapshot", [])
                    profile = context["agent"].profile
                    
                    result = future.result()
                    result = self._calibrate_result(result, distribution)
                    comment_text = str(result.get("comment", "") or "").strip()
                    if self._is_system_comment(comment_text):
                        result["comment"] = "这章信息量有了，人物张力还能再往上提。"
                    else:
                        result["comment"] = self._apply_duplicate_penalty(
                            comment_text,
                            seen_comments,
                            style_examples,
                            context.get("history", []),
                            dedup_policy=dedup_policy,
                        )
                        result["comment"] = self._enforce_global_similarity_penalty(
                            str(result.get("comment", "")).strip(),
                            seen_comments,
                            style_examples,
                            dedup_policy=dedup_policy,
                        )
                    seen_comments.append(str(result.get("comment", "")).strip())

                    results.append(result)

                    score = float(result.get("score", 0))
                    score_sum += score
                    emotion = result.get("emotion", "neutral")
                    emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
                    
                    # Resolve reply_to_comment_id
                    reply_id = None
                    reply_index = result.get("reply_to_index")
                    if isinstance(reply_index, int) and 0 <= reply_index < len(context_snapshot):
                        target = context_snapshot[reply_index]
                        reply_id = target.get("id")
                        # Add extra metadata for frontend display if needed
                        result["reply_to_reader_name"] = target.get("reader_name")

                    snapshot = profile.to_dict() if hasattr(profile, "to_dict") else {}
                    inserted_id = task_store.insert_comment(
                        task_id,
                        reader_id=result.get("reader_id", "unknown"),
                        reader_name=result.get("reader_name", "unknown"),
                        vip_level=int(result.get("vip_level", 0)),
                        score=score,
                        confidence=float(result.get("confidence", 0.0) or 0.0),
                        emotion=emotion,
                        comment=result.get("comment", ""),
                        evidence_ids=result.get("evidence_ids") or [],
                        reader_region=str(
                            result.get("reader_region")
                            or getattr(profile, "region", "")
                            or ""
                        ).strip(),
                        simulated_duration=int(result.get("simulated_duration", 0)),
                        profile_snapshot=snapshot,
                        reply_to_comment_id=reply_id,
                    )
                    
                    # Add to context accumulator
                    if inserted_id:
                        result["id"] = inserted_id # Populate ID in result (though result is dict)
                        context_accumulator.append({
                            "id": inserted_id,
                            "reader_name": result.get("reader_name", "unknown"),
                            "comment": result.get("comment", ""),
                        })

                    if book_key:
                        task_store.append_reader_memory(
                            reader_id=str(result.get("reader_id", "unknown")),
                            reader_name=str(result.get("reader_name", "unknown")),
                            source_book_key=book_key,
                            new_comments=[str(result.get("comment", "")).strip()],
                        )
                except Exception as e:
                    last_error = str(e)
                    print(f"Agent execution failed: {e}")

                completed += 1
                avg_score = (score_sum / completed) if completed else 0
                progress = int((completed / max(total, 1)) * 100)

                # Event Detection
                new_event = None
                total_emotions = sum(emotion_counts.values())
                if total_emotions >= 3: # Lowered from 5
                    angry_ratio = emotion_counts.get("angry", 0) / total_emotions
                    excited_ratio = emotion_counts.get("excited", 0) / total_emotions
                    
                    # 获取作者和平台以备日志使用
                    _author = str(task_meta.get("source_author") or "").strip() or None
                    _platform = str(task_meta.get("source_platform") or "").strip() or None

                    # Check for "storm" (high controversy/anger) - Threshold lowered to 0.2
                    if not any(e["type"] == "storm" for e in detected_events) and angry_ratio > 0.2:
                        new_event = {"type": "storm", "message": "检测到大规模争议情绪", "timestamp": time.time()}
                        self._trigger_audit_log(novel_title, _author, _platform, "High", "PLOT_TOXIC", f"在【{chapter_title}】检测到大规模争议/负面情绪(Angry={angry_ratio:.1%})", avg_score)
                    
                    # Check for "fire" (high excitement) - Threshold lowered to 0.2
                    elif not any(e["type"] == "fire" for e in detected_events) and excited_ratio > 0.2:
                         new_event = {"type": "fire", "message": "读者反响异常热烈", "timestamp": time.time()}

                    # Check for "rain" (low score) - Threshold raised to 3.0, count lowered to 5
                    elif not any(e["type"] == "rain" for e in detected_events) and avg_score < 3.0 and completed > 5:
                         new_event = {"type": "rain", "message": "即时口碑出现下滑趋势", "timestamp": time.time()}
                         self._trigger_audit_log(novel_title, _author, _platform, "Medium", "PLOT_TOXIC", f"在【{chapter_title}】即时口碑出现明显下滑趋势", avg_score)


                if new_event:
                    detected_events.append(new_event)

                task_store.update_task(
                    task_id,
                    progress=progress,
                    completed_readers=completed,
                    avg_score=round(avg_score, 2),
                    emotion_distribution=emotion_counts,
                    events=detected_events,
                    error=last_error,
                )

        summary = {
            "simulation_id": task_id,
            "novel_title": novel_title,
            "chapter_title": chapter_title,
            "dedup_mode": dedup_mode,
            "use_story_context": use_story_context,
            "timestamp": time.time(),
            "total_readers": len(results),
            "avg_score": round((score_sum / len(results)) if results else 0, 1),
            "emotion_distribution": emotion_counts,
            "story_context": story_context,
            "comments": results,
        }

        task_store.update_task(
            task_id,
            status="completed",
            progress=100,
            total_readers=len(results),
            completed_readers=len(results),
            avg_score=summary["avg_score"],
            emotion_distribution=emotion_counts,
            error=last_error,
        )

        self.simulation_results[task_id] = summary
        return summary

    @staticmethod
    def _pick_style_examples(
        samples: List[Dict[str, str]], limit: int = 6
    ) -> List[Dict[str, str]]:
        if not samples:
            return []
        filtered: List[Dict[str, str]] = []
        deny_patterns = (
            "全是问号",
            "几个意思",
            "求更新",
            "快更新",
            "打卡",
            "签到",
        )
        for item in samples:
            text = str(item.get("content", "")).strip()
            if not text:
                continue
            if len(text) < 16 or len(text) > 120:
                continue
            if any(p in text for p in deny_patterns):
                continue
            filtered.append(
                {"content": text, "region": str(item.get("region", "")).strip()}
            )
        pool = filtered if len(filtered) >= max(3, limit) else samples
        if len(pool) <= limit:
            return list(pool)
        return random.sample(pool, limit)

    @staticmethod
    def _build_distribution_profile(samples: List[Dict[str, str]]) -> Dict[str, Any]:
        lengths: List[int] = []
        emotion_counter: Dict[str, int] = {}
        for item in samples or []:
            text = str(item.get("content", "")).strip()
            if not text:
                continue
            lengths.append(len(text))
            emo = VirtualReaderService._infer_emotion_hint(text)
            emotion_counter[emo] = emotion_counter.get(emo, 0) + 1

        if not lengths:
            return {
                "target_len": 48,
                "max_len": 110,
                "emotion_weights": {"happy": 0.35, "neutral": 0.4, "angry": 0.25},
            }

        lengths.sort()
        p50 = lengths[len(lengths) // 2]
        p90 = lengths[min(len(lengths) - 1, int(len(lengths) * 0.9))]
        total_emotion = sum(emotion_counter.values()) or 1
        emotion_weights = {
            key: float(val) / float(total_emotion) for key, val in emotion_counter.items()
        }
        return {
            "target_len": max(20, min(p50, 120)),
            "max_len": max(40, min(p90, 180)),
            "emotion_weights": emotion_weights,
        }

    @staticmethod
    def _infer_emotion_hint(text: str) -> str:
        value = (text or "").strip()
        low = value.lower()
        pos_words = ("好看", "精彩", "上头", "爽", "牛", "期待", "喜欢", "绝了", "爱了", "惊喜")
        neg_words = ("水", "烂", "毒", "尬", "崩", "无聊", "拖", "降智", "弃", "失望")
        if any(word in value for word in pos_words) or "!!!" in value or "！！" in value:
            return "happy"
        if any(word in value for word in neg_words):
            return "angry"
        if "?" in low or "？" in value:
            return "bored"
        return "neutral"

    def _trigger_audit_log(self, title: str, author: Optional[str], platform: Optional[str], risk_level: str, risk_type: str, snippet: str, score: float):
        try:
            import pymysql
            from auth import AUTH_DB_CONFIG
            conn = pymysql.connect(**AUTH_DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO ip_audit_logs (book_title, book_author, platform, risk_level, risk_type, content_snippet, score, trigger_source) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (title, author, platform, risk_level, risk_type, snippet, score, "virtual_reader")
                )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Failed to write audit log: {e}")

    def _calibrate_result(self, result: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
        calibrated = dict(result or {})
        text = str(calibrated.get("comment", "") or "").strip()
        if not text:
            return calibrated

        max_len = int(profile.get("max_len", 120) or 120)
        target_len = int(profile.get("target_len", 50) or 50)
        if len(text) > max_len:
            text = text[:max_len].rstrip("，,。.;； ")
        elif len(text) < max(14, target_len // 2):
            text = f"{text}，后劲还在。"

        emotion = str(calibrated.get("emotion", "neutral")).strip().lower()
        weights = profile.get("emotion_weights", {}) or {}
        if weights and emotion not in weights and len(weights) >= 2:
            keys = list(weights.keys())
            probs = [max(float(weights[k]), 0.0) for k in keys]
            if sum(probs) > 0:
                emotion = random.choices(keys, weights=probs, k=1)[0]

        calibrated["comment"] = text
        calibrated["emotion"] = emotion if emotion else "neutral"
        return calibrated

    def _apply_duplicate_penalty(
        self,
        comment: str,
        seen_comments: List[str],
        style_examples: List[Dict[str, str]],
        history_comments: Optional[List[str]] = None,
        dedup_policy: Optional[Dict[str, float]] = None,
    ) -> str:
        text = str(comment or "").strip()
        if not text:
            return text
        policy = dedup_policy or {}
        duplicate_threshold = float(policy.get("duplicate_threshold", 0.82))
        rebuilt_threshold = float(policy.get("rebuilt_threshold", 0.82))
        recent = list(seen_comments)
        if history_comments:
            recent.extend([str(x or "").strip() for x in history_comments if str(x or "").strip()])
        too_similar = any(self._semantic_similarity(text, old) >= duplicate_threshold for old in recent)
        if not too_similar:
            return text

        seed = ""
        for item in style_examples or []:
            seed_text = str(item.get("content", "")).strip()
            if seed_text and self._semantic_similarity(seed_text, text) < 0.65:
                seed = seed_text[:26]
                break

        suffix_pool = [
            "这段情绪拉起来了。",
            "再把冲突压紧会更炸。",
            "人物动机再补一笔会更稳。",
            "节奏再快一点就上头了。",
        ]
        extra = random.choice(suffix_pool)
        if seed:
            rebuilt = f"{seed}。{extra}"
        else:
            rebuilt = f"{text[:34]}，{extra}"
        if any(self._semantic_similarity(rebuilt, old) >= rebuilt_threshold for old in recent):
            rebuilt = f"{extra}（换个角度看）"
        return rebuilt

    @staticmethod
    def _semantic_similarity(text_a: str, text_b: str) -> float:
        def units(value: str) -> set:
            value = (value or "").lower()
            words = set(re.findall(r"[a-z0-9]{2,}", value))
            for token in re.findall(r"[\u4e00-\u9fff]+", value):
                if len(token) == 1:
                    continue
                if len(token) == 2:
                    words.add(token)
                    continue
                for i in range(len(token) - 1):
                    words.add(token[i : i + 2])
            return words

        a = units(text_a)
        b = units(text_b)
        if not a or not b:
            return 0.0
        return len(a & b) / float(max(len(a | b), 1))

    def _max_similarity(self, text: str, candidates: List[str]) -> float:
        value = str(text or "").strip()
        if not value or not candidates:
            return 0.0
        max_score = 0.0
        for item in candidates:
            old = str(item or "").strip()
            if not old:
                continue
            score = self._semantic_similarity(value, old)
            if score > max_score:
                max_score = score
        return max_score

    def _enforce_global_similarity_penalty(
        self,
        comment: str,
        seen_comments: List[str],
        style_examples: List[Dict[str, str]],
        dedup_policy: Optional[Dict[str, float]] = None,
    ) -> str:
        text = str(comment or "").strip()
        if not text:
            return text
        if not seen_comments:
            return text
        policy = dedup_policy or {}
        global_threshold = float(policy.get("global_threshold", 0.75))
        if self._max_similarity(text, seen_comments) < global_threshold:
            return text

        seed_pool: List[str] = []
        for item in style_examples or []:
            seed = str(item.get("content", "")).strip()
            if len(seed) < 10:
                continue
            if self._semantic_similarity(seed, text) >= 0.6:
                continue
            seed_pool.append(seed)

        angle_pool = ["人物动机", "冲突推进", "节奏控制", "世界观细节", "情感拉扯", "文笔画面"]
        finish_pool = [
            "后续再把因果钉牢会更上头。",
            "如果补上关键动机会更有说服力。",
            "这一块再压紧会更有张力。",
            "继续沿这条线深挖会更抓人。",
        ]

        for _ in range(6):
            angle = random.choice(angle_pool)
            finish = random.choice(finish_pool)
            if seed_pool:
                seed = random.choice(seed_pool)[:22].rstrip("，,。 ")
                rebuilt = f"{angle}这条线我更在意：{seed}，{finish}"
            else:
                snippet = text[:18].rstrip("，,。 ")
                rebuilt = f"{angle}这条线我更在意：{snippet}，{finish}"
            if self._max_similarity(rebuilt, seen_comments) < global_threshold:
                return rebuilt

        fallback_angle = random.choice(angle_pool)
        fallback_finish = random.choice(finish_pool)
        return f"换个角度看，{fallback_angle}这块信息量有了，{fallback_finish}"

    @staticmethod
    def _is_system_comment(text: str) -> bool:
        comment = (text or "").strip()
        if not comment:
            return True
        lowered = comment.lower()
        for token in ("任务已提交", "已暂停模拟", "system"):
            if token.lower() in lowered:
                return True
        return False


virtual_reader_service = VirtualReaderService()
