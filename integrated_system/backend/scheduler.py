import threading
import time
import subprocess
import os
import sys
from datetime import datetime, timedelta
from collections import deque

class SpiderScheduler:
    def __init__(self):
        self.is_running = False
        self.interval_minutes = 120  # 默认 2 小时运行一次
        self.last_run_time = None
        self.next_run_time = None
        self.status = "已停止"
        self._thread = None
        self.target_platform = "all"  # qidian / zongheng / all
        self.crawl_history = deque(maxlen=20)  # 最近 20 条爬取记录
        self.current_run_logs = deque(maxlen=300)  # 实时日志缓冲

        # 爬虫脚本路径映射
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scrapy'))
        self.spider_scripts = {
            'qidian': os.path.join(base, 'qidian_realtime_spider.py'),
            'zongheng': os.path.join(base, 'zongheng_realtime_spider.py'),
        }
        # 缓存已验证的 Python 可执行文件路径
        self._cached_python_exe = None

    def _find_spider_python(self):
        """智能探测包含爬虫依赖的 Python 环境"""
        if self._cached_python_exe:
            return self._cached_python_exe

        candidates = []

        # 1) 探测 Anaconda spider3_env 环境（已知具备完整爬虫依赖）
        anaconda_bases = [
            os.path.expanduser('~/anaconda3'),
            os.path.expanduser('~/miniconda3'),
            'D:/ANACONDA',
            'C:/ProgramData/anaconda3',
            'C:/Users/' + os.getenv('USERNAME', '') + '/anaconda3',
        ]
        for ab in anaconda_bases:
            spider_env = os.path.join(ab, 'envs', 'spider3_env', 'python.exe')
            if os.path.exists(spider_env):
                candidates.append(spider_env)
                break

        # 2) 项目 .venv 环境
        venv_python = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.venv/Scripts/python.exe'))
        if os.path.exists(venv_python):
            candidates.append(venv_python)

        # 3) 当前解释器作为兜底
        candidates.append(sys.executable)

        # 验证每个候选环境是否可以导入 requests（爬虫核心依赖）
        import subprocess as _sp
        for py in candidates:
            try:
                result = _sp.run(
                    [py, '-c', 'import requests'],
                    capture_output=True, timeout=10
                )
                if result.returncode == 0:
                    self._cached_python_exe = py
                    print(f"[Scheduler] 已选定爬虫 Python 环境: {py}")
                    return py
            except Exception:
                continue

        # 所有验证均失败，回退到当前解释器
        print("[Scheduler] ⚠️ 未找到包含 requests 的 Python 环境，回退到当前解释器")
        self._cached_python_exe = sys.executable
        return sys.executable

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.status = "等待下一次调度中..."
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.is_running = False
        self.status = "已停止"
        self.next_run_time = None

    def set_interval(self, minutes):
        """更新调度间隔（分钟）"""
        self.interval_minutes = max(30, min(minutes, 480))  # 30分钟 ~ 8小时
        # 如果正在运行，重新计算下次执行时间
        if self.is_running and self.last_run_time:
            last = datetime.strptime(self.last_run_time, "%Y-%m-%d %H:%M:%S")
            self.next_run_time = (last + timedelta(minutes=self.interval_minutes)).strftime("%Y-%m-%d %H:%M:%S")

    def set_platform(self, platform):
        """设置目标爬取平台"""
        if platform in ('qidian', 'zongheng', 'all'):
            self.target_platform = platform

    def trigger_now(self):
        if self.status == "正在抓取数据 (防封IP代理轮换中)...":
            return
        threading.Thread(target=self._execute_spider, daemon=True).start()

    def _execute_spider(self):
        self.status = "正在抓取数据 (防封IP代理轮换中)..."
        start_time = datetime.now()
        self.last_run_time = start_time.strftime("%Y-%m-%d %H:%M:%S")

        # 确定要运行的爬虫
        targets = []
        if self.target_platform == 'all':
            targets = list(self.spider_scripts.items())
        else:
            script = self.spider_scripts.get(self.target_platform)
            if script:
                targets = [(self.target_platform, script)]

        # 智能探测虚拟环境 Python 路径（优先选择拥有爬虫依赖的环境）
        python_exe = self._find_spider_python()

        results = []
        self.current_run_logs.clear()
        for platform_name, script_path in targets:
            record = {
                'platform': platform_name,
                'start_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'running',
                'books_updated': 0,
                'duration_sec': 0,
                'error': None
            }
            try:
                start_msg = f"[Scheduler] 开始爬取 {platform_name} | 脚本: {script_path}"
                print(start_msg)
                self.current_run_logs.append(start_msg)
                # Prepare environment to force UTF-8 stdout
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                
                proc = subprocess.Popen(
                    [python_exe, script_path],
                    cwd=os.path.dirname(script_path),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    env=env,
                    bufsize=1
                )
                
                output_lines = []
                # Read stdout line by line (raw bytes to avoid decode crash)
                for line_bytes in proc.stdout:
                    try:
                        line = line_bytes.decode('utf-8').strip()
                    except UnicodeDecodeError:
                        try:
                            line = line_bytes.decode('gbk').strip()
                        except UnicodeDecodeError:
                            line = line_bytes.decode('utf-8', errors='replace').strip()
                    if line:
                        self.current_run_logs.append(line)
                        output_lines.append(line)
                
                proc.wait(timeout=600)  # wait for finish
                
                output = "\\n".join(output_lines)
                count = output.count('[√]') + output.count('✅') + output.count('[OK]')
                record['books_updated'] = count if count > 0 else len([l for l in output_lines if '更新' in l or 'success' in l.lower()])
                record['status'] = 'success' if proc.returncode == 0 else 'partial'
                if proc.returncode != 0:
                    record['error'] = f"Process exited with code {proc.returncode}"
            except subprocess.TimeoutExpired:
                proc.kill()
                record['status'] = 'timeout'
                record['error'] = '执行超时(>10min)'
                self.current_run_logs.append(f"❌ [TimeoutError] 执行超时被强制终止")
            except Exception as e:
                record['status'] = 'error'
                record['error'] = str(e)[:200]
                self.current_run_logs.append(f"❌ [Error] 调度器异常: {e}")
            finally:
                record['duration_sec'] = int((datetime.now() - datetime.strptime(record['start_time'], "%Y-%m-%d %H:%M:%S")).total_seconds())
                results.append(record)
                self.crawl_history.appendleft(record)

        # 运行 S 级遗珠深度发掘扫描 (作为每次数据更新后的风控策略验证)
        try:
            from scan_potential_gems import scan_and_trigger_gems
            inserted = scan_and_trigger_gems()
            if inserted > 0:
                self.current_run_logs.append(f"✅ [Gem Scanner] 发掘并录入了 {inserted} 本 S 级商业遗珠")
            else:
                self.current_run_logs.append("ℹ️ [Gem Scanner] 本轮未发现新增 S 级商业遗珠")
        except Exception as e:
            self.current_run_logs.append(f"❌ [Gem Scanner] 扫描阶段异常: {e}")

        # 更新状态
        if self.is_running:
            self.status = "等待下一次调度中..."
            self.next_run_time = (datetime.now() + timedelta(minutes=self.interval_minutes)).strftime("%Y-%m-%d %H:%M:%S")
        else:
            self.status = "已停止"

        return results

    def _run_loop(self):
        # 启动时首先进入等待状态
        self.next_run_time = (datetime.now() + timedelta(minutes=self.interval_minutes)).strftime("%Y-%m-%d %H:%M:%S")
        while self.is_running:
            elapsed = 0
            while elapsed < self.interval_minutes * 60 and self.is_running:
                time.sleep(5)
                elapsed += 5
            if self.is_running:
                self._execute_spider()

    def get_status_dict(self):
        """返回完整的调度器状态"""
        return {
            'is_running': self.is_running,
            'status': self.status,
            'last_run_time': self.last_run_time,
            'next_run_time': self.next_run_time,
            'interval_minutes': self.interval_minutes,
            'target_platform': self.target_platform,
            'crawl_history': list(self.crawl_history)
        }

scheduler_instance = SpiderScheduler()
