from openai import OpenAI
import os
import json
import traceback

# NVIDIA API (不可用)
USER_NVIDIA_KEY = "nvapi-..." 
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1"

# GitHub Models (通过学生包 Token - 从环境变量读取)
# Endpoint: https://models.inference.ai.azure.com
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_ENDPOINT = "https://models.inference.ai.azure.com"

# 本地 Gemini CLI (备用)
# 本地 Gemini CLI (备用)
GEMINI_CLI_URL = "http://127.0.0.1:7861/v1"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "pwd")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config', 'ai_config.json')

class AIService:
    def __init__(self):
        self.config = self.load_config()
        
        # 兼容旧配置：如果没有 models 列表，转换为新结构
        if 'models' not in self.config:
            old_id = "default_legacy_model"
            self.config = {
                "primary_chat_id": old_id,
                "primary_logic_id": old_id,
                "models": [{
                    "id": old_id,
                    "provider": self.config.get('provider', 'github'),
                    "model_name": self.config.get('model_name', 'gpt-4o'),
                    "base_url": self.config.get('base_url', GITHUB_ENDPOINT),
                    "api_key": self.config.get('api_key', GITHUB_TOKEN)
                }]
            }
            # 顺便写回以固化新结构
            self.save_config(self.config)

        self.clients = {}  # { model_id: {'client': OpenAI_client, 'model_name': '...', 'provider': '...'} }
        import httpx
        
        for m in self.config.get('models', []):
            m_id = m.get('id')
            provider = m.get('provider')
            base_url = m.get('base_url')
            # 保证空字符串或没有 key 时能默认 fallback 到 TOKEN，虽然管理端应该强制填入
            api_key = m.get('api_key') or os.getenv("GITHUB_TOKEN", "")
            model_name = m.get('model_name')
            
            connection_configs = [
                {"verify": False, "timeout": 60.0, "trust_env": False},
                {"verify": False, "timeout": 60.0, "trust_env": True}
            ]
            
            client_instance = None
            for config_opts in connection_configs:
                try:
                    print(f"Attempting AI connection for {m_id}: trust_env={config_opts['trust_env']} (Provider: {provider})...", flush=True)
                    http_client = httpx.Client(**config_opts)
                    
                    api_base = base_url
                    if provider == 'gemini' and base_url == GITHUB_ENDPOINT:
                        api_base = GEMINI_CLI_URL
                    
                    temp_client = OpenAI(
                        base_url=api_base,
                        api_key=api_key,
                        http_client=http_client
                    )
                    
                    # 取消初始化时的强制发请求验证，防止加载过慢。验证由专门的 /test 接口负责。
                    client_instance = temp_client
                    print(f"[OK] AI Service {m_id} Initialized! (Config: trust_env={config_opts['trust_env']})")
                    break
                except Exception as e:
                    print(f"[ERROR] Config failed for {m_id}: {e}")
            
            if client_instance:
                self.clients[m_id] = {
                    'client': client_instance,
                    'model_name': model_name,
                    'provider': provider
                }

        if not self.clients:
             print("[ERROR] All model clients failed to initialize.")

        # 2. 备用: 本地 Gemini CLI
        try:
            gemini_http = httpx.Client(timeout=120.0)
            self.gemini_client = OpenAI(
                base_url=GEMINI_CLI_URL,
                api_key=GEMINI_API_KEY, 
                http_client=gemini_http
            )
            print(f"[OK] Fallback AI Service Initialized: Local Gemini CLI")
        except Exception as e:
            print(f"[WARN] Gemini CLI Init Failed: {e}")
            self.gemini_client = None
        
        # 🔥 API 预热
        self._warmup_api()
    
    def _warmup_api(self):
        """启动时预热 API"""
        if not self.clients: return
        
        # 取 primary chat client 预热
        model_id = self.config.get('primary_chat_id')
        if not model_id or model_id not in self.clients:
            model_id = list(self.clients.keys())[0]
            
        client_info = self.clients[model_id]
        
        # ⚡ 优化：防止 Flask Debug 模式下的二次启动/预热
        import os
        if os.environ.get("FLASK_ENV") == "development" or os.environ.get("FLASK_DEBUG") == "1":
             if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
                 return

        import threading
        def warmup_task():
            import time
            print(f"[INFO] Warming up Primary Model {client_info['model_name']}...", flush=True)
            try:
                client_info['client'].chat.completions.create(
                    model=client_info['model_name'],
                    messages=[{"role": "user", "content": "Hi"}],
                    max_tokens=5
                )
                print(f"[OK] Primary Model ({client_info['model_name']}) Warmup Success!", flush=True)
            except Exception as e:
                print(f"[WARN] Primary Model Warmup Failed: {e}", flush=True)
                import traceback
                traceback.print_exc()
        
        thread = threading.Thread(target=warmup_task, daemon=True)
        thread.start()

    def _log(self, msg):
        try:
            with open("debug_ai.log", "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except: pass

    def _record_token_usage(self, token_count):
        if not token_count or token_count <= 0: return
        try:
            import pymysql
            from datetime import datetime
            from auth import AUTH_DB_CONFIG
            
            conn = pymysql.connect(**AUTH_DB_CONFIG)
            with conn.cursor() as cursor:
                now = datetime.now()
                hour_time = now.replace(minute=0, second=0, microsecond=0)
                
                sql = """
                INSERT INTO hourly_metrics (record_time, pv_count, uv_count, api_calls, ai_tokens_consumed)
                VALUES (%s, 0, 0, 0, %s)
                ON DUPLICATE KEY UPDATE ai_tokens_consumed = ai_tokens_consumed + %s
                """
                cursor.execute(sql, (hour_time, token_count, token_count))
                conn.commit()
            conn.close()
        except Exception as e:
            print(f"[METRICS ERROR] Failed to record AI tokens: {e}")

    def _call_model(self, model_key, messages, temperature=0.7, max_tokens=1024, json_mode=False):
        # 根据 model_key('chat' 或 'logic') 查找对应的模型 id
        model_id = self.config.get(f'primary_{model_key}_id')
        
        # 如果未找到对应设定，或该客户端未初始化，则 fallback 到第一个可用客户端
        if not model_id or model_id not in self.clients:
            if self.clients:
                model_id = list(self.clients.keys())[0]
        
        if model_id and model_id in self.clients:
            client_info = self.clients[model_id]
            client = client_info['client']
            model_name = client_info['model_name']
            
            print(f"[AI] 调用模型: model_key={model_key}, model_id={model_name}, provider={client_info['provider']}")
            try:
                params = {
                    "model": model_name,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                if json_mode:
                    params["response_format"] = {"type": "json_object"}
                
                resp = client.chat.completions.create(**params, timeout=60.0)
                
                try:
                    # 真实记录大模型 Token 开销
                    usage = getattr(resp, 'usage', None)
                    if usage and getattr(usage, 'total_tokens', None):
                        self._record_token_usage(usage.total_tokens)
                    else:
                        # 兜底：若没有返回确切 usage，用字数进行粗略 token 估算
                        estimated_tokens = len(str(messages)) // 2 + len(resp.choices[0].message.content or "")
                        self._record_token_usage(estimated_tokens)
                except: pass

                return resp.choices[0].message.content
            except Exception as e:
                self._log(f"Model {model_name} failed: {e}")
                print(f"⚠️ Model {model_name} failed: {e}")
                # Fallback to next
        
        # Fallback to Gemini CLI if explicitly running out of models
        print("[WARN] All defined clients failed, falling back to local Gemini CLI")
        return self._call_gemini(messages, temperature, max_tokens)

    def _call_model_stream(self, model_key, messages, temperature=0.6, max_tokens=1500):
        model_id = self.config.get(f'primary_{model_key}_id')
        if not model_id or model_id not in self.clients:
            if self.clients:
                model_id = list(self.clients.keys())[0]
        
        if model_id and model_id in self.clients:
            client_info = self.clients[model_id]
            client = client_info['client']
            model_name = client_info['model_name']
            
            print(f"[AI] 流式调用: model={model_name}, provider={client_info['provider']}")
            try:
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                    timeout=60.0
                )
                for chunk in resp:
                    if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            except Exception as e:
                self._log(f"Stream Model {model_name} failed: {e}")
                print(f"⚠️ Stream Model {model_name} failed: {e}")
                yield f"\n\n**提示**: AI网络波动，生成中断 ({e})"
        else:
            yield "\n\n**错误**: 无可用的大模型配置。"

    def generate_swot_report(self, title, abstract, stats=None):
        """Generates a SWOT analysis report for the book with data awareness."""
        
        # 构建数据背景字符串
        data_context = ""
        if stats:
            fin = stats.get('finance', 0)
            inter = stats.get('interaction', 0)
            pop = stats.get('popularity', 0)
            wc = stats.get('word_count', 0)
            data_context = f"\n该作品目前实时表现如下：月票实绩约为 {fin}，全网互动约 {inter} 次，累计点击约 {pop}，当前总字数约 {wc} 字。"

        system_prompt = f"""
        你是资深的网文IP评估专家。请基于小说标题、简介以及提供的【实时运营数据】，生成一份专业的【IP价值评估报告】。
        {data_context}
        
        请严格按照 JSON 格式返回，包含以下字段：
        - summary: 200字以内的一句话简评 (One-liner).
        - swot: {{
            "strengths": ["优势1", "优势2"...],
            "weaknesses": ["劣势1", "劣势2"...],
            "opportunities": ["改编机会1", "机会2"...],
            "threats": ["风险1", "风险2"...]
        }}
        - radar_scores: {{ "innovation": 0-10, "story": 0-10, "character": 0-10, "world": 0-10, "commercial": 0-10 }}
        
        【特别要求】: 
        1. 必须参考实时运营数据。如果月票很高（>10000），则 Commercial 评分应显著提高（建议 8-10 分）。
        2. 请确保分析犀利、专业，不要说空话。
        """
        
        user_prompt = f"小说标题：{title}\n简介：{abstract}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            # content = self._call_model('logic', messages, temperature=0.5, json_mode=True)
            # GLM4.7 sometimes struggles with strict JSON mode flag on some platforms, let's try strict prompt first
            # GLM4.7 is unstable, switching to MiniMax (chat model) for better stability
            print(f"=> generate_swot_report: calling model (using 'chat' model)...", flush=True)
            content = self._call_model('chat', messages, temperature=0.5)
            print(f"<= generate_swot_report: received content type={type(content)}", flush=True)
            
            # Sanitize JSON
            if content:
                print(f"[DATA] Raw Content: {content[:100]}...", flush=True)
                content = content.replace("```json", "").replace("```", "").strip()
                return json.loads(content)
            else:
                print("[ERROR] Content is None", flush=True)
                with open("swot_debug.txt", "w") as f: f.write("Content is None")
        except Exception as e:
            print(f"[ERROR] SWOT Report Gen Failed: {e}", flush=True)
            with open("swot_debug.txt", "w") as f: f.write(str(e))
            import traceback; traceback.print_exc()
            
        # Fallback
        # Fallback (Mock Generation if API fails)
        print("[WARN] Generating Mock SWOT Report due to API failure...", flush=True)
        mock_summary = f"由于AI服务暂时繁忙，以下为基于《{title}》文本特征的初步评估。该作品在设定上展现了一定潜力，建议关注后续剧情展开。"
        
        return {
            "summary": mock_summary,
            "swot": {
                "strengths": ["题材具有一定受众基础", "核心设定较为清晰", "叙事节奏平稳"],
                "weaknesses": ["开篇冲突可进一步加强", "人物性格需更多细节铺垫"],
                "opportunities": ["适合尝试多媒体短剧改编", "可拓展支线剧情增加粘性"],
                "threats": ["同类题材市场竞争激烈"]
            },
            "radar_scores": {
                "innovation": 7, 
                "story": 7, 
                "character": 6, 
                "world": 7, 
                "commercial": 6
            }
        }

    def analyze_global_potential(self, title, abstract, category):
        """Generates a global market potential analysis."""
        system_prompt = """
        你是资深的网文出海与IP全球化评估专家。请基于小说标题、类型和简介，分析该作品的【全球化潜力】。
        
        请严格按照 JSON 格式返回，包含以下字段：
        - overall_score: 综合全球化潜力评分 (0-100的整数)
        - target_countries: [{"country": "国家/地区名称(如:北美,东南亚,日韩)", "fit_score": 匹配度(0-100), "reason": "匹配原因(20-30字)"}, ...] (推荐前3-5个最匹配的市场)
        - cultural_elements: [{"element": "包含的传统文化元素(如:修仙,茶道,中医)", "impact_score": 吸引力(0-100), "attraction": "为什么对海外有吸引力(20-30字)"}, ...] (提取1-3个核心元素)
        - localization_advice: "一句话出海本地化改编建议(30-50字)"
        - risks: ["文化碰撞雷点或出海风险1", "风险2"...] (列举1-3个潜在出海阻碍)
        
        请确保分析客观、专业，不要说空话。
        """
        
        user_prompt = f"小说标题：{title}\n类型：{category}\n简介：{abstract}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            print(f"=> analyze_global_potential: calling model (using 'chat' model)...", flush=True)
            content = self._call_model('chat', messages, temperature=0.6)
            
            # Sanitize JSON
            if content:
                content = content.replace("```json", "").replace("```", "").strip()
                import json
                return json.loads(content)
        except Exception as e:
            print(f"[ERROR] Global Potential Gen Failed: {e}", flush=True)
            import traceback; traceback.print_exc()
            
        # Fallback Mock
        print("[WARN] Generating Mock Global Analysis due to API failure...", flush=True)
        return {
            "overall_score": 75,
            "target_countries": [
                {"country": "东南亚", "fit_score": 85, "reason": "文化底色相近，读者容易接受修仙或系统设定。"},
                {"country": "北美", "fit_score": 60, "reason": "需要进一步的本地化改编才能被主流英语区读者接受。"}
            ],
            "cultural_elements": [
                {"element": "升级流/打怪", "impact_score": 80, "attraction": "直观的反馈机制与游戏化体验，具备全球通吃潜力。"}
            ],
            "localization_advice": "建议在翻译中适当淡化过于生僻的专有名词，强调清晰的主线目标和爽点逻辑。",
            "risks": ["复杂的世界观在初期可能会让部分海外读者感到费解。"]
        }

    def assess_quality(self, text_segment):
        """Assess text quality (Fluency, Novelty, Attraction)."""
        prompt = f"""
        请对以下小说开篇片段进行评分 (1-10分):
        片段: {text_segment[:800]}
        
        返回 JSON: {{ "fluency": 0, "novelty": 0, "attraction": 0, "reason": "简评" }}
        """
        messages = [{"role": "user", "content": prompt}]
        
        try:
            # Use 'chat' model instead of 'logic' for stability
            content = self._call_model('chat', messages, temperature=0.2)
            if content:
                content = content.replace("```json", "").replace("```", "").strip()
                return json.loads(content)
        except:
            pass
        return {"fluency": 5, "novelty": 5, "attraction": 5, "reason": "分析失败"}

    def chat_with_character(self, profile, history, user_input):
        """
        深度角色扮演对话。
        profile: {name, persona, scenario, background(可选)}
        history: [{role: user/assistant, content: ...}]
        """
        character_name = profile.get('name', '角色')
        persona = profile.get('persona', '')
        scenario = profile.get('scenario', '')
        background = profile.get('background', '')
        
        system_prompt = f"""【角色扮演指令】
你现在是小说中的角色「{character_name}」。请完全沉浸在这个角色中与用户对话。

【你的身份】
{scenario}

【你的性格与说话风格】
{persona}

【你的背景】
{background if background else '根据上述人设自行补充'}

【核心要求：自然、生动、有互动】
1. **必须包含动作/神态描写**：用（括号）标注。
   - 重点：描写要**点到为止**，不要写长篇大论。
   - 好的描写是为对话服务的，例如：（轻轻点头） "嗯，我在。"
   - 增加互动感：多描写眼神接触或对用户的细微反应（如 （微笑着看向你））。

2. **拒绝敷衍**：
   - 不要用一句话就结束对话！即使是冷淡的角色，也要**有实质回应**。
   - 回复要有**延展性**，可以反问、追忆往事、或流露情绪，让对话能继续下去。
   - 错误示例：（冷哼）"不关你事。"（太敷衍）
   - 正确示例：（冷哼一声，目光却微微闪烁）"不关你事...不过，你倒是第一个敢这么问我的人。"

3. **内容把控**：
   - 回复长度适中（**50-120字**），要有内容，不能干巴巴。
【语气参考】
- 冷峻型：（眼神微冷） "不必多问。"（动作少而精）
- 活泼型：（拍拍你的肩膀） "嘿，这就对了嘛！"（动作幅度大）
- 温柔型：（温柔地注视着你） "别担心，有我在。"（注重眼神和语气）"""
        
        messages = [{"role": "system", "content": system_prompt}]
        # 添加历史对话（限制最近8轮以提高速度）
        messages.extend(history[-8:])
        messages.append({"role": "user", "content": user_input})
        
        try:
            print(f"👉 chat_with_character: {character_name} responding...", flush=True)
            response = self._call_model('chat', messages, temperature=0.85)
            print(f"👈 chat_with_character: received response", flush=True)
            
            if response:
                import re
                # 清理思考标签
                response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
                return response
        except Exception as e:
            print(f"❌ Chat failed: {e}")
            import traceback
            traceback.print_exc()
            
        return f"（{character_name}沉思了一会儿...）"

    def extract_characters(self, title: str, abstract: str) -> list:
        """
        从书籍简介中提取主要角色（深度分析版）
        
        Args:
            title: 书籍标题
            abstract: 书籍简介
            
        Returns:
            角色列表 [{name, persona, description, avatar, background}]
        """
        system_prompt = """你是一位资深的小说评论家和文学分析师，对网络小说非常熟悉。请根据小说标题和简介，深度分析并提取书中的主要角色。

【重要要求】
1. 角色名必须是具体的人名，不能用"主角"、"女主"、"男主"等代称
2. 如果简介中明确提到了角色名，必须使用该名字
3. 如果简介没有提到具体名字，请根据小说类型、时代背景合理推测一个符合情境的真实姓名
4. 人设描述要体现角色的核心性格特质、说话风格、情感特点

【返回JSON格式】
[
  {
    "name": "角色真实姓名",
    "persona": "详细的性格描述（80-120字）：包括性格特点、说话方式、情感态度、价值观、与他人的相处模式。这是AI扮演该角色时的核心设定。",
    "description": "角色在故事中的身份定位（30字以内）",
    "avatar": "代表角色的emoji",
    "background": "角色的背景故事和关键经历（50字以内）"
  }
]

【示例】
对于《捞尸人》这类悬疑小说：
[
  {"name": "陆沉", "persona": "性格冷峻内敛，见惯生死后对世事淡然处之。说话简洁有力，不喜欢废话。表面冷漠实则重情重义，对委托人的案件认真负责。有自己的职业道德底线，不为钱财出卖原则。", "description": "职业捞尸人，故事主角", "avatar": "🎭", "background": "从事捞尸行业多年，见过无数离奇死亡案件"},
  {"name": "沈若溪", "persona": "聪明伶俐，性格直爽不做作。对神秘事物充满好奇心，遇事冷静但偶尔冲动。说话带点俏皮，喜欢调侃但不失分寸。内心善良，愿意帮助他人。", "description": "法医实习生，女主", "avatar": "🌸", "background": "医学院高材生，因一次意外与主角相识"}
]

请提取4-6个核心角色，确保每个角色都有独特鲜明的个性。"""
        
        user_prompt = f"""请分析以下小说并提取主要角色：

【小说标题】{title}

【小说简介】
{abstract if abstract else '（简介暂缺，请根据标题类型合理推测角色设定）'}

请以JSON格式返回角色列表。"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            print(f"[AI] Extracting characters from '{title}'...", flush=True)
            content = self._call_model('chat', messages, temperature=0.7)
            
            if content:
                # 清理 JSON
                content = content.replace("```json", "").replace("```", "").strip()
                # 找到JSON数组
                start = content.find('[')
                end = content.rfind(']') + 1
                if start >= 0 and end > start:
                    content = content[start:end]
                characters = json.loads(content)
                
                # 确保格式正确
                if isinstance(characters, list) and len(characters) > 0:
                    print(f"[OK] Extracted {len(characters)} characters", flush=True)
                    return characters
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON parse error: {e}", flush=True)
        except Exception as e:
            print(f"[ERROR] Character extraction failed: {e}", flush=True)
            import traceback
            traceback.print_exc()
        
        # 返回基于标题推测的默认角色
        print("[WARN] Returning default characters based on title", flush=True)
        return [
            {"name": "林逸", "persona": f"《{title}》的主人公，性格坚韧沉稳，处事冷静。面对困难从不退缩，有强烈的责任感和正义感。说话不多但句句在理，是值得信赖的人。", "description": "故事主角", "avatar": "🎭", "background": "有着不为人知的过去"},
            {"name": "苏婉", "persona": "温柔聪慧，外柔内刚。待人真诚温和，但在关键时刻展现出坚强的一面。善于观察细节，常常一语道破关键。", "description": "重要女性角色", "avatar": "🌸", "background": "与主角命运交织"}
        ]

    # Keep legacy method for compatibility but upgrade it
    def analyze_prediction(self, title, category, score, abstract, **kwargs):
        # Use new SWOT report logic
        report = self.generate_swot_report(title, abstract)
        
        # Transform to match old `analyze_prediction` format expected by Frontend
        # Old format: pros, cons, comment, trend, scores
        return {
            "pros": report['swot'].get('strengths', [])[:3],
            "cons": report['swot'].get('weaknesses', [])[:3] + report['swot'].get('threats', [])[:1],
            "comment": report.get('summary', ''),
            "trend": [score, score+2, score+1, score+3, score+2, score+4], # Mock trend
            "scores": {
                "Innovation": report['radar_scores'].get('innovation', 0) * 10,
                "Story": report['radar_scores'].get('story', 0) * 10,
                "Commercial": report['radar_scores'].get('commercial', 0) * 10,
                "World": report['radar_scores'].get('world', 0) * 10,
                "Character": report['radar_scores'].get('character', 0) * 10
            }
        }

    def generate_comprehensive_audit(self, title, author, base_stats, ai_eval_stats, vr_comments, global_stats, model_score, realtime_trend=None, market_analysis=None, book_status='未知'):
        """
        融合六维多源数据 + 动态市场价值模型 + AI大模型知识库，生成全维度商业决策审计报告。
        """
        system_prompt = """你是顶级的网文商业数据分析师与出海战略参谋，拥有深厚的数据敏感度和IP价值评估经验。你绝对不会只套用空洞的死公式，而是从理性的“数据层面”深度挖掘一部作品的真实商业潜力。
我将为你提供一本网文IP的全维度多源数据，包括：
1. 【基础运营数据】与【完结状态】
2. 【六维AI拆解评分】
3. 【虚拟读者样本反馈】
4. 【全球化出海预判】
5. 最核心的【市场价值大盘测算】—— 涵盖市场热度、IP潜力、粉丝粘性、商业变现、内容质量、时效活跃度这6大数据指标。

请基于客观的数据表现，理性、犀利地产出【全维度商业决策审计报告】。拒绝千篇一律的废话，所有论断必须与提供的数据指标（如粉丝粘性的低或高、商业变现的量级）挂钩！

要求：
1. 必须使用 Markdown 格式（不可使用外层代码块包裹）。
2. 语言极速、专业、一针见血。
3. 结构包含：
   - **核心判定** (结合大盘测算评分，一句话严厉/中肯判定作品等级：现象级S/头部A/腰部B/扑街C等)
   - **多维数据洞察** (重点解读提供的“市场价值大盘测算”6大指标，挖掘财务和互动背后的真相，例如高互动低月票暗示了什么，高月票低互动又说明了什么)
   - **实时态势研判** (结合连载/完结状态及实时趋势指标诊断项目生命周期)
   - **出海战略建议** (结合文化壁垒客观评价：不建议出海就果断说不，需要特定方向就明确指路)
   - **读者舆情折射** (提炼虚拟反馈并预判舆论风险)
   - **商业预警与提升空间** (给版权方/运营方最核心的商业避坑或变现建议)
"""

        # 构建实时趋势描述
        trend_text = "暂无实时监控数据"
        if realtime_trend and isinstance(realtime_trend, dict):
            trend_direction = realtime_trend.get('direction', '稳定')
            latest_tickets = realtime_trend.get('latest_tickets', 0)
            growth_rate = realtime_trend.get('growth_rate', 0)
            data_points = realtime_trend.get('data_points', 0)
            trend_text = f"趋势方向: {trend_direction}, 最新月票: {latest_tickets}, 近期增幅: {growth_rate}%, 采集点数: {data_points}"

        market_analysis = market_analysis or {}
        user_prompt = f"""请犀利、基于数据地分析以下作品：
【书名】《{title}》
【状态】{book_status}

【基础数据】
- 巅峰月票：{base_stats.get('finance', '未知')}
- 总互动量：{base_stats.get('interaction', '未知')}
- 预估字数：{base_stats.get('word_count', '未知')}
- 大模型/大盘锚定评分：{model_score} / 100

【市场价值大盘指标】 (核心挖潜依据)
- 市场热度：{market_analysis.get('market_heat', '未测算')} / 100
- 商业变现能力：{market_analysis.get('commercial_value', '未测算')} / 100
- 粉丝参与粘性：{market_analysis.get('fan_loyalty', '未测算')} / 100
- 内容质量指数：{market_analysis.get('content_quality', '未测算')} / 100
- IP改编潜力：{market_analysis.get('ip_potential', '未测算')} / 100
- 时效活跃度(完结衰减/连载加成)：{market_analysis.get('timeliness', '未测算')} / 100

【AI拆解评分】(辅助参考)
- 综合:{ai_eval_stats.get('overall', '?')} | 故事:{ai_eval_stats.get('story', '?')} | 角色:{ai_eval_stats.get('character', '?')} | 设定:{ai_eval_stats.get('world', '?')} | 商业:{ai_eval_stats.get('commercial', '?')}

【全球化出海特征】
- 翻译适配度(高越好)：{global_stats.get('translation_suitability', '暂无')}
- 文化壁垒指数(低越好)：{global_stats.get('cultural_barrier', '暂无')}
- 推荐阵地：{global_stats.get('target_regions', '暂无')}

【实时监控】: {trend_text}
【虚拟舆情】: {vr_comments}

请摒弃套话模版，以数据为骨架，产出极具含金量、直接面向操盘手/投资人的深度报告（字数控制在600-800字以保证生成速度）。
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            print(f"=> generate_comprehensive_audit: calling 'chat' model for fast analysis...", flush=True)
            # 使用 chat 模型保证极大的速度提升，不使用容易卡死或输出废话太多的 reasoning logic 模型
            content = self._call_model('chat', messages, temperature=0.6, max_tokens=1500)
            if content:
                content = content.replace("```markdown", "").replace("```", "").strip()
                return content
        except Exception as e:
            print(f"[ERROR] generate_comprehensive_audit failed: {e}")
            
        return f"✅ **生成报告遭遇网络拥堵**\n\n- 基础预测分：**{model_score}**\n- 推荐出海区域：**{global_stats.get('target_regions', '暂无')}**\n该作品具备较好的数据稳定性，可尝试轻量级出海试水。"

    def generate_comprehensive_audit_stream(self, title, author, base_stats, ai_eval_stats, vr_comments, global_stats, model_score, realtime_trend=None, market_analysis=None, book_status='未知'):
        """
        流式生成全维度审计报告 Generator。
        逻辑及提示词完全等价于 generate_comprehensive_audit，但通过 yield 逐句抛出提升体验。
        """
        system_prompt = """你是顶级的网文商业数据分析师与出海战略参谋，拥有深厚的数据敏感度和IP价值评估经验。你绝对不会只套用空洞的死公式，而是从理性的“数据层面”深度挖掘一部作品的真实商业潜力。
我将为你提供一本网文IP的全维度多源数据，包括：
1. 【基础运营数据】与【完结状态】
2. 【六维AI拆解评分】
3. 【虚拟读者样本反馈】
4. 【全球化出海预判】
5. 最核心的【市场价值大盘测算】—— 涵盖市场热度、IP潜力、粉丝粘性、商业变现、内容质量、时效活跃度这6大数据指标。

请基于客观的数据表现，理性、犀利地产出【全维度商业决策审计报告】。拒绝千篇一律的废话，所有论断必须与提供的数据指标挂钩！

要求：
1. 必须使用 Markdown 格式（不可使用外层代码块包裹）。
2. 语言极速、专业、一针见血。
3. 结构包含：
   - **核心判定** (结合大盘测算评分，一句话严厉/中肯判定作品等级：现象级S/头部A/腰部B/扑街C等)
   - **多维数据洞察** (解读大盘测算6大指标挖掘财务背后的真相)
   - **实时态势研判** (结合连载/完结状态及实时趋势诊断生命周期)
   - **出海战略建议** (结合文化壁垒客观评价：不建议出海就说不，需要特定方向就指路)
   - **读者舆情折射** (提炼虚拟反馈并预判舆论风险)
   - **商业预警与提升空间** (给版权方核心的商业避坑建议)
"""
        trend_direction = realtime_trend.get('direction', '稳定') if isinstance(realtime_trend, dict) else '稳定'
        latest_tickets = realtime_trend.get('latest_tickets', 0) if isinstance(realtime_trend, dict) else 0
        trend_text = f"趋势方向: {trend_direction}, 最新月票: {latest_tickets}"

        market_analysis = market_analysis or {}
        user_prompt = f"""请犀利、基于数据地分析以下作品：
【书名】《{title}》
【状态】{book_status}

【基础数据】
- 巅峰月票：{base_stats.get('finance', '未知')}
- 总互动量：{base_stats.get('interaction', '未知')}
- 预估字数：{base_stats.get('word_count', '未知')}
- 大模型/大盘锚定评分：{model_score} / 100

【市场价值大盘指标】 (核心挖潜依据)
- 市场热度：{market_analysis.get('market_heat', '未测算')} / 100
- 商业变现能力：{market_analysis.get('commercial_value', '未测算')} / 100
- 粉丝参与粘性：{market_analysis.get('fan_loyalty', '未测算')} / 100
- 内容质量指数：{market_analysis.get('content_quality', '未测算')} / 100
- IP改编潜力：{market_analysis.get('ip_potential', '未测算')} / 100
- 时效活跃度(完结衰减/连载加成)：{market_analysis.get('timeliness', '未测算')} / 100

【AI拆解评分】(辅助参考)
- 综合评级: {ai_eval_stats.get('grade', '?')} (整体:{ai_eval_stats.get('overall', '?')})
- 细项评分: 故事:{ai_eval_stats.get('story', '?')} | 角色:{ai_eval_stats.get('character', '?')} | 设定:{ai_eval_stats.get('world', '?')} | 商业:{ai_eval_stats.get('commercial', '?')} 
- 衍生与安全: 改编度:{ai_eval_stats.get('adaptation', '?')} | 安全性:{ai_eval_stats.get('safety', '?')} | 风险因子: {ai_eval_stats.get('risk_factor', '暂无')}

【全球化出海特征】
- 翻译适配度(高越好)：{global_stats.get('translation_suitability', '暂无')}
- 文化壁垒指数(低越好)：{global_stats.get('cultural_barrier', '暂无')}
- 推荐阵地：{global_stats.get('target_regions', '暂无')}

【实时监控】: {trend_text}
【虚拟舆情】: {vr_comments}

请摒弃套话模版，以数据为骨架，产出极具含金量、直接面向操盘手/投资人的深度流式汇报（字数控制在600-800字以保证快速完稿）。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            print(f"=> generate_comprehensive_audit_stream: streaming...", flush=True)
            for chunk in self._call_model_stream('chat', messages, temperature=0.6, max_tokens=1500):
                if chunk:
                    # 洗掉多余代码块包裹
                    clean_chunk = chunk.replace("```markdown\n", "").replace("```", "")
                    yield clean_chunk
        except Exception as e:
            print(f"[ERROR] Stream generator failed: {e}")
            yield f"\n\n*(分析流意外中断: {str(e)})*"

    def _call_gemini(self, messages, temperature=0.7, max_tokens=1024):
        """备用：使用本地 Gemini CLI (OpenAI 兼容格式)"""
        if not self.gemini_client:
            print("[ERROR] Gemini CLI Client not initialized", flush=True)
            return None
        
        try:
            print("[INFO] Attempting Local Gemini CLI...", flush=True)
            
            response = self.gemini_client.chat.completions.create(
                model="gemini",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=120.0
            )
            
            content = response.choices[0].message.content
            
            try:
                # 真实记录大模型 Token 开销
                usage = getattr(response, 'usage', None)
                if usage and getattr(usage, 'total_tokens', None):
                    self._record_token_usage(usage.total_tokens)
                else:
                    estimated_tokens = len(str(messages)) // 2 + len(content or "")
                    self._record_token_usage(estimated_tokens)
            except: pass

            msg = f"[OK] Gemini CLI Response Success ({len(content)} chars)"
            self._log(msg)
            print(msg, flush=True)
            return content
            
        except Exception as e:
            msg = f"[ERROR] Gemini CLI Error: {e}"
            self._log(msg)
            print(msg, flush=True)
            return None

    def load_config(self):
        """Load AI configuration from JSON file."""
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] Failed to load config: {e}")
        return {}

    def save_config(self, new_config):
        """Save AI configuration to JSON file."""
        try:
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=4)
            print("[OK] AI Config saved.")
        except Exception as e:
            print(f"[ERROR] Failed to save config: {e}")

    def update_config(self, new_config):
        """Update config and re-initialize client."""
        # Directly save the new_config as it is assumed to be the full JSON structure
        self.save_config(new_config)
        
        # Re-init
        print("[INFO] Re-initializing AI Service with new config...", flush=True)
        self.__init__()
        return {"status": "success", "config": self.config}

    def _mock_response(self, *args, **kwargs):
        # Deprecated
        return {}

ai_service = AIService()