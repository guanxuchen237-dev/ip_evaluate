"""
Story context retrieval and synthesis for virtual reader simulation.

Builds a structured plot context from:
1) local corpus (real comment table)
2) optional web search evidence (provider-driven)
3) optional chapter snippet supplied by caller
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional
from urllib import parse, request

try:
    from backend.ai_service import ai_service
    from .task_store import task_store
except ImportError:
    try:
        from ..ai_service import ai_service
        from .task_store import task_store
    except (ImportError, ValueError):
        import sys

        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(current_dir)
        if backend_dir not in sys.path:
            sys.path.append(backend_dir)
        from ai_service import ai_service
        from virtual_reader.task_store import task_store


class StoryContextService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cache_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "cache", "story_context"
        )
        os.makedirs(self._cache_dir, exist_ok=True)

    def build_story_context(
        self,
        *,
        novel_title: str,
        chapter_title: str,
        chapter_content: str,
        source_title: Optional[str] = None,
        source_author: Optional[str] = None,
        source_platform: Optional[str] = None,
        force_refresh: bool = False,
        use_web_search: bool = True,
    ) -> Dict[str, Any]:
        title = (source_title or novel_title or "").strip()
        chapter = (chapter_title or "").strip()
        cache_key = self._build_cache_key(
            source_platform=source_platform,
            source_title=title,
            source_author=source_author,
            chapter_title=chapter,
        )
        ttl_sec = int(os.getenv("VR_STORY_CACHE_TTL_SEC", "21600"))

        if not force_refresh:
            cached = self._load_cache(cache_key, ttl_sec=ttl_sec)
            if cached:
                return cached

        local_refs = self._collect_local_evidence(
            source_title=title,
            chapter_title=chapter,
            chapter_content=chapter_content,
        )
        web_refs = self._collect_web_evidence(
            title=title,
            author=source_author,
            chapter_title=chapter,
            use_web_search=use_web_search,
        )
        manual_ref = self._build_manual_content_ref(chapter_content)

        refs = self._merge_and_rank_refs(local_refs, web_refs, manual_ref)
        context = self._synthesize_context(
            title=title,
            author=source_author,
            chapter_title=chapter,
            refs=refs,
        )
        context["source_refs"] = refs
        context["meta"] = {
            "source_title": title,
            "source_author": source_author,
            "source_platform": source_platform,
            "chapter_title": chapter,
            "retrieved_at": int(time.time()),
            "use_web_search": bool(use_web_search),
        }
        self._save_cache(cache_key, context)
        return context

    @staticmethod
    def _build_cache_key(
        *,
        source_platform: Optional[str],
        source_title: Optional[str],
        source_author: Optional[str],
        chapter_title: Optional[str],
    ) -> str:
        raw = "|".join(
            [
                str(source_platform or "").strip().lower(),
                str(source_title or "").strip().lower(),
                str(source_author or "").strip().lower(),
                str(chapter_title or "").strip().lower(),
            ]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    def _cache_path(self, cache_key: str) -> str:
        return os.path.join(self._cache_dir, f"{cache_key}.json")

    def _load_cache(self, cache_key: str, ttl_sec: int) -> Optional[Dict[str, Any]]:
        path = self._cache_path(cache_key)
        if not os.path.exists(path):
            return None
        if ttl_sec > 0:
            age = time.time() - os.path.getmtime(path)
            if age > ttl_sec:
                return None
        try:
            with open(path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            if isinstance(data, dict):
                return data
        except Exception:
            return None
        return None

    def _save_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        path = self._cache_path(cache_key)
        tmp_path = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
        with self._lock:
            with open(tmp_path, "w", encoding="utf-8") as fp:
                json.dump(data, fp, ensure_ascii=False, indent=2)
            replaced = False
            for _ in range(3):
                try:
                    os.replace(tmp_path, path)
                    replaced = True
                    break
                except PermissionError:
                    # On Windows the destination file can be briefly locked.
                    time.sleep(0.05)
                except OSError:
                    break
            if not replaced:
                # Fallback: write final file directly if atomic replace is blocked.
                with open(path, "w", encoding="utf-8") as fp:
                    json.dump(data, fp, ensure_ascii=False, indent=2)
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    def _collect_local_evidence(
        self, *, source_title: str, chapter_title: str, chapter_content: str
    ) -> List[Dict[str, Any]]:
        query_text = f"书名:{source_title}\n章节:{chapter_title}\n内容:{chapter_content[:1200]}"
        samples = task_store.get_real_comment_samples(
            source_title=source_title,
            limit=10,
            query_text=query_text,
            pool_size=300,
        )
        refs: List[Dict[str, Any]] = []
        for idx, item in enumerate(samples[:10], start=1):
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            refs.append(
                {
                    "ref_id": f"L{idx}",
                    "title": "本地评论语料",
                    "url": "",
                    "snippet": content[:220],
                    "source_type": "local_corpus",
                    "score": 0.45,
                }
            )
        return refs

    def _collect_web_evidence(
        self,
        *,
        title: str,
        author: Optional[str],
        chapter_title: str,
        use_web_search: bool,
    ) -> List[Dict[str, Any]]:
        if not use_web_search:
            return []
        query = " ".join(
            part
            for part in [
                title,
                author or "",
                chapter_title,
                "剧情 角色 章节",
            ]
            if str(part or "").strip()
        )
        provider = str(os.getenv("VR_WEB_SEARCH_PROVIDER", "jina")).strip().lower()
        if provider == "tavily":
            refs = self._search_with_tavily(query)
        elif provider == "serpapi":
            refs = self._search_with_serpapi(query)
        else:
            refs = self._search_with_jina(query)
        for idx, item in enumerate(refs, start=1):
            item["ref_id"] = f"W{idx}"
            item.setdefault("source_type", "web_search")
            item.setdefault("score", 0.6)
        return refs[:8]

    def _search_with_tavily(self, query: str) -> List[Dict[str, Any]]:
        api_key = str(os.getenv("TAVILY_API_KEY", "")).strip()
        if not api_key:
            return []
        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": "advanced",
            "max_results": 8,
            "include_answer": False,
            "include_raw_content": False,
        }
        raw = self._http_post_json("https://api.tavily.com/search", payload, timeout=20)
        results = raw.get("results") if isinstance(raw, dict) else None
        if not isinstance(results, list):
            return []
        refs: List[Dict[str, Any]] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            snippet = str(item.get("content") or "").strip()
            if not snippet:
                continue
            refs.append(
                {
                    "title": title[:160] or "网页结果",
                    "url": url[:600],
                    "snippet": snippet[:320],
                    "source_type": "web_tavily",
                    "score": 0.7,
                }
            )
        return refs

    def _search_with_serpapi(self, query: str) -> List[Dict[str, Any]]:
        api_key = str(os.getenv("SERPAPI_API_KEY", "")).strip()
        if not api_key:
            return []
        params = parse.urlencode(
            {
                "engine": "google",
                "q": query,
                "hl": "zh-cn",
                "num": 8,
                "api_key": api_key,
            }
        )
        url = f"https://serpapi.com/search.json?{params}"
        raw = self._http_get_json(url, timeout=20)
        organic = raw.get("organic_results") if isinstance(raw, dict) else None
        if not isinstance(organic, list):
            return []
        refs: List[Dict[str, Any]] = []
        for item in organic:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            link = str(item.get("link") or "").strip()
            snippet = str(item.get("snippet") or "").strip()
            if not snippet:
                continue
            refs.append(
                {
                    "title": title[:160] or "网页结果",
                    "url": link[:600],
                    "snippet": snippet[:320],
                    "source_type": "web_serpapi",
                    "score": 0.7,
                }
            )
        return refs

    def _search_with_jina(self, query: str) -> List[Dict[str, Any]]:
        # jina search is a no-key fallback. It returns a textual digest of search results.
        encoded = parse.quote(query, safe="")
        url = f"https://s.jina.ai/{encoded}"
        try:
            text = self._http_get_text(url, timeout=20)
        except Exception:
            return []
        text = str(text or "").strip()
        if not text:
            return []
        text = re.sub(r"\n{3,}", "\n\n", text)
        digest = text[:2600]
        urls = re.findall(r"https?://[^\s)]+", digest)
        first_url = urls[0] if urls else url
        return [
            {
                "title": "Web 搜索摘要",
                "url": first_url[:600],
                "snippet": digest[:360],
                "source_type": "web_jina",
                "score": 0.62,
            }
        ]

    @staticmethod
    def _http_get_text(url: str, timeout: int = 20) -> str:
        req = request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "text/plain,application/json;q=0.9,*/*;q=0.8",
            },
            method="GET",
        )
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
        return body.decode("utf-8", errors="ignore")

    @staticmethod
    def _http_get_json(url: str, timeout: int = 20) -> Dict[str, Any]:
        text = StoryContextService._http_get_text(url, timeout=timeout)
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _http_post_json(url: str, payload: Dict[str, Any], timeout: int = 20) -> Dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            url,
            data=body,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _build_manual_content_ref(chapter_content: str) -> Optional[Dict[str, Any]]:
        text = str(chapter_content or "").strip()
        if len(text) < 80:
            return None
        return {
            "ref_id": "C1",
            "title": "用户提供章节片段",
            "url": "",
            "snippet": text[:420],
            "source_type": "chapter_input",
            "score": 0.9,
        }

    @staticmethod
    def _merge_and_rank_refs(
        local_refs: List[Dict[str, Any]],
        web_refs: List[Dict[str, Any]],
        manual_ref: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        merged: List[Dict[str, Any]] = []
        seen = set()
        for item in ([manual_ref] if manual_ref else []) + web_refs + local_refs:
            if not item:
                continue
            snippet = str(item.get("snippet") or "").strip()
            if not snippet:
                continue
            key = snippet[:120]
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
        merged.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)
        return merged[:12]

    def _synthesize_context(
        self,
        *,
        title: str,
        author: Optional[str],
        chapter_title: str,
        refs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        evidence_lines: List[str] = []
        for item in refs:
            ref_id = str(item.get("ref_id") or "").strip() or "R?"
            ref_title = str(item.get("title") or "").strip()
            snippet = str(item.get("snippet") or "").strip()
            url = str(item.get("url") or "").strip()
            evidence_lines.append(
                f"[{ref_id}] {ref_title}\nURL: {url or 'N/A'}\n片段: {snippet[:320]}"
            )

        if not evidence_lines:
            return {
                "storyline_summary": "缺少可用剧情证据，当前仅能基于读者共识做弱推断。",
                "key_plot_points": [],
                "character_state": [],
                "conflict_axes": [],
                "recent_progress": [],
                "likely_next": [],
                "confidence": 0.2,
                "source_refs": [],
            }

        system_prompt = (
            "你是小说剧情证据整合器。必须严格基于提供证据做摘要，不得臆造。"
            "若证据冲突，优先保留可交叉验证的信息。"
            "输出 JSON，不要输出任何解释。"
        )
        user_prompt = (
            f"书名: {title}\n作者: {author or '未知'}\n章节: {chapter_title or '未知'}\n\n"
            "证据列表:\n"
            + "\n\n".join(evidence_lines)
            + "\n\n请输出 JSON:\n"
            "{\n"
            '  "storyline_summary": "120字以内剧情摘要",\n'
            '  "key_plot_points": ["点1", "点2"],\n'
            '  "character_state": ["人物状态1", "人物状态2"],\n'
            '  "conflict_axes": ["冲突线1", "冲突线2"],\n'
            '  "recent_progress": ["最新进展1", "最新进展2"],\n'
            '  "likely_next": ["可能发展1", "可能发展2"],\n'
            '  "confidence": 0.0,\n'
            '  "source_refs": [{"ref_id":"W1","reason":"支撑了哪条结论"}]\n'
            "}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            raw = ai_service._call_model("chat", messages, temperature=0.2, max_tokens=360)
            parsed = self._parse_json(raw)
            normalized = self._normalize_context(parsed)
            if normalized:
                return normalized
        except Exception:
            pass

        fallback_summary = str(refs[0].get("snippet") or "").strip()[:120]
        return {
            "storyline_summary": fallback_summary or "证据不足。",
            "key_plot_points": [fallback_summary] if fallback_summary else [],
            "character_state": [],
            "conflict_axes": [],
            "recent_progress": [],
            "likely_next": [],
            "confidence": 0.35,
            "source_refs": [{"ref_id": str(refs[0].get("ref_id") or ""), "reason": "fallback"}],
        }

    @staticmethod
    def _parse_json(raw: Any) -> Dict[str, Any]:
        text = str(raw or "").strip()
        text = text.replace("```json", "").replace("```", "").strip()
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", text)
            if not match:
                return {}
            try:
                data = json.loads(match.group(0))
                return data if isinstance(data, dict) else {}
            except json.JSONDecodeError:
                return {}

    @staticmethod
    def _normalize_list(items: Any, limit: int = 6) -> List[str]:
        if not isinstance(items, list):
            return []
        result: List[str] = []
        seen = set()
        for item in items:
            text = str(item or "").strip()
            if not text:
                continue
            if text in seen:
                continue
            seen.add(text)
            result.append(text[:80])
            if len(result) >= limit:
                break
        return result

    def _normalize_context(self, data: Dict[str, Any]) -> Dict[str, Any]:
        summary = str(data.get("storyline_summary") or "").strip()[:160]
        if not summary:
            return {}
        confidence = data.get("confidence", 0.4)
        try:
            confidence_value = float(confidence)
        except Exception:
            confidence_value = 0.4
        confidence_value = min(max(confidence_value, 0.0), 1.0)

        refs = data.get("source_refs", [])
        ref_list: List[Dict[str, str]] = []
        if isinstance(refs, list):
            for item in refs:
                if not isinstance(item, dict):
                    continue
                ref_id = str(item.get("ref_id") or "").strip()
                reason = str(item.get("reason") or "").strip()
                if not ref_id:
                    continue
                ref_list.append({"ref_id": ref_id[:24], "reason": reason[:120]})
                if len(ref_list) >= 6:
                    break

        return {
            "storyline_summary": summary,
            "key_plot_points": self._normalize_list(data.get("key_plot_points")),
            "character_state": self._normalize_list(data.get("character_state")),
            "conflict_axes": self._normalize_list(data.get("conflict_axes")),
            "recent_progress": self._normalize_list(data.get("recent_progress")),
            "likely_next": self._normalize_list(data.get("likely_next")),
            "confidence": round(confidence_value, 3),
            "source_refs": ref_list,
        }


story_context_service = StoryContextService()
