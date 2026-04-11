import os, json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SelfImproveAgent:
    def __init__(self, llm_client, allow_modify=False):
        self.llm = llm_client
        self.allow_modify = allow_modify

    def run(self, instruction: str, workspace_dir: str = "workspace") -> str:
        context = self._gather()
        analysis = self.llm.chat(
            "你是Multi-Agent系统优化专家。分析执行数据，找出瓶颈，给出具体改进建议（按优先级列出）。",
            f"系统数据：\n{context}\n\n请求：{instruction}", temperature=0.3, max_tokens=800
        )
        self._log(instruction, analysis)
        mode = "【分析模式，不自动修改】" if not self.allow_modify else "【已记录改进建议】"
        return f"{mode}\n\n{analysis}"

    def _gather(self):
        parts = []
        mf = os.path.join(BASE_DIR,"logs","system_metrics.jsonl")
        if os.path.exists(mf):
            lines = []
            with open(mf,"r",encoding="utf-8") as f:
                for line in f:
                    try: lines.append(json.loads(line))
                    except: pass
            recent = lines[-30:]
            stats = {}
            for r in recent:
                a = r.get("agent","?")
                stats.setdefault(a,{"n":0,"dur":0,"err":0})
                stats[a]["n"]+=1; stats[a]["dur"]+=r.get("dur",0)
                if r.get("status")!="ok": stats[a]["err"]+=1
            parts.append("Agent性能：" + " | ".join(
                f"{a}: {s['n']}次 avg{round(s['dur']/s['n'],1)}s 失败{s['err']}次"
                for a,s in stats.items()
            ))
        return "\n".join(parts) or "暂无足够数据"

    def _log(self, instruction, analysis):
        lf = os.path.join(BASE_DIR,"improvement_log.json")
        log = []
        if os.path.exists(lf):
            try:
                with open(lf,"r",encoding="utf-8") as f: log = json.load(f)
            except: pass
        import time
        log.insert(0,{"timestamp":time.strftime("%Y-%m-%d %H:%M:%S"),"instruction":instruction,"analysis":analysis[:500]})
        with open(lf,"w",encoding="utf-8") as f: json.dump(log[:50],f,ensure_ascii=False,indent=2)
