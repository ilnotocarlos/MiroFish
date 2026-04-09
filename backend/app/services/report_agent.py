"""
Report Agent Service
Implements ReACT pattern simulation report generation using LangChain + Zep

Features:
1. Generate reports based on simulation requirements and Zep graph information
2. Plan outline structure first, then generate section by section
3. Each section uses ReACT multi-round thinking and reflection mode
4. Support user conversation with autonomous retrieval tool invocation
"""

import os
import json
import time
import re
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from ..i18n import get_prompt
from .zep_tools import (
    ZepToolsService, 
    SearchResult, 
    InsightForgeResult, 
    PanoramaResult,
    InterviewResult
)

logger = get_logger('mirofish.report_agent')


class ReportLogger:
    """
    Report Agent 详细日志记录器
    
    在reportfile夹中generating agent_log.jsonl file，记录每一步详细动作。
    每行是一units完整的 JSON object，包含时间戳、动作类型、详细content等。
    """
    
    def __init__(self, report_id: str):
        """
        initializing日志记录器
        
        Args:
            report_id: reportID，用于确定日志file路径
        """
        self.report_id = report_id
        self.log_file_path = os.path.join(
            Config.UPLOAD_FOLDER, 'reports', report_id, 'agent_log.jsonl'
        )
        self.start_time = datetime.now()
        self._ensure_log_file()
    
    def _ensure_log_file(self):
        """Ensure log file directory exists"""
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)
    
    def _get_elapsed_time(self) -> float:
        """Get elapsed time since start (seconds)"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def log(
        self, 
        action: str, 
        stage: str,
        details: Dict[str, Any],
        section_title: str = None,
        section_index: int = None
    ):
        """
        记录一items日志
        
        Args:
            action: 动作类型，如 'start', 'tool_call', 'llm_response', 'section_complete' 等
            stage: 当前阶段，如 'planning', 'generating', 'completed'
            details: 详细content字典，不截断
            section_title: 当前sectiontitle（可选）
            section_index: 当前section索引（可选）
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(self._get_elapsed_time(), 2),
            "report_id": self.report_id,
            "action": action,
            "stage": stage,
            "section_title": section_title,
            "section_index": section_index,
            "details": details
        }
        
        # AppendWrite JSONL File
        with open(self.log_file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def log_start(self, simulation_id: str, graph_id: str, simulation_requirement: str):
        """RecordReportgenerateStart"""
        self.log(
            action="report_start",
            stage="pending",
            details={
                "simulation_id": simulation_id,
                "graph_id": graph_id,
                "simulation_requirement": simulation_requirement,
                "message": "reportgenerating任务开始"
            }
        )
    
    def log_planning_start(self):
        """RecordOutlineplanningStart"""
        self.log(
            action="planning_start",
            stage="planning",
            details={"message": "start planning report outline"}
        )
    
    def log_planning_context(self, context: Dict[str, Any]):
        """Recordplanning时get的contextinfo"""
        self.log(
            action="planning_context",
            stage="planning",
            details={
                "message": "get simulation context信息",
                "context": context
            }
        )
    
    def log_planning_complete(self, outline_dict: Dict[str, Any]):
        """RecordOutlineplanningComplete"""
        self.log(
            action="planning_complete",
            stage="planning",
            details={
                "message": "outline planning completed",
                "outline": outline_dict
            }
        )
    
    def log_section_start(self, section_title: str, section_index: int):
        """RecordsectiongenerateStart"""
        self.log(
            action="section_start",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={"message": f"开始generate section: {section_title}"}
        )
    
    def log_react_thought(self, section_title: str, section_index: int, iteration: int, thought: str):
        """Record ReACT 思考过程"""
        self.log(
            action="react_thought",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "thought": thought,
                "message": f"ReACT 第{iteration}rounds思考"
            }
        )
    
    def log_tool_call(
        self, 
        section_title: str, 
        section_index: int,
        tool_name: str, 
        parameters: Dict[str, Any],
        iteration: int
    ):
        """RecordToolcall"""
        self.log(
            action="tool_call",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "tool_name": tool_name,
                "parameters": parameters,
                "message": f"调用tool: {tool_name}"
            }
        )
    
    def log_tool_result(
        self,
        section_title: str,
        section_index: int,
        tool_name: str,
        result: str,
        iteration: int
    ):
        """RecordToolcallResult（完整Content，不截断）"""
        self.log(
            action="tool_result",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "tool_name": tool_name,
                "result": result,  # 完整Result，不截断
                "result_length": len(result),
                "message": f"tool {tool_name} returned结果"
            }
        )
    
    def log_llm_response(
        self,
        section_title: str,
        section_index: int,
        response: str,
        iteration: int,
        has_tool_calls: bool,
        has_final_answer: bool
    ):
        """Record LLM Response（完整Content，不截断）"""
        self.log(
            action="llm_response",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "response": response,  # 完整Response，不截断
                "response_length": len(response),
                "has_tool_calls": has_tool_calls,
                "has_final_answer": has_final_answer,
                "message": f"LLM response (tool调用: {has_tool_calls}, 最终答案: {has_final_answer})"
            }
        )
    
    def log_section_content(
        self,
        section_title: str,
        section_index: int,
        content: str,
        tool_calls_count: int
    ):
        """RecordsectionContentgenerateComplete（onlyRecordContent，不代Table整unitssectionComplete）"""
        self.log(
            action="section_content",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "content": content,  # 完整Content，不截断
                "content_length": len(content),
                "tool_calls_count": tool_calls_count,
                "message": f"section {section_title} contentgeneratingcompleted"
            }
        )
    
    def log_section_full_complete(
        self,
        section_title: str,
        section_index: int,
        full_content: str
    ):
        """
        记录sectiongeneratingcompleted

        前端应watch此日志来判断一unitssection是否真正completed，并get完整content
        """
        self.log(
            action="section_complete",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "content": full_content,
                "content_length": len(full_content),
                "message": f"section {section_title} generatingcompleted"
            }
        )
    
    def log_report_complete(self, total_sections: int, total_time_seconds: float):
        """RecordReportgenerateComplete"""
        self.log(
            action="report_complete",
            stage="completed",
            details={
                "total_sections": total_sections,
                "total_time_seconds": round(total_time_seconds, 2),
                "message": "report generation completed"
            }
        )
    
    def log_error(self, error_message: str, stage: str, section_title: str = None):
        """RecordError"""
        self.log(
            action="error",
            stage=stage,
            section_title=section_title,
            section_index=None,
            details={
                "error": error_message,
                "message": f"发生错误: {error_message}"
            }
        )


class ReportConsoleLogger:
    """
    Report Agent 控制台日志记录器
    
    将控制台风格的日志（INFO、WARNING等）写入reportfile夹中的 console_log.txt file。
    这些日志与 agent_log.jsonl 不同，是纯文本格式的控制台输出。
    """
    
    def __init__(self, report_id: str):
        """
        initializing控制台日志记录器
        
        Args:
            report_id: reportID，用于确定日志file路径
        """
        self.report_id = report_id
        self.log_file_path = os.path.join(
            Config.UPLOAD_FOLDER, 'reports', report_id, 'console_log.txt'
        )
        self._ensure_log_file()
        self._file_handler = None
        self._setup_file_handler()
    
    def _ensure_log_file(self):
        """Ensure log file directory exists"""
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)
    
    def _setup_file_handler(self):
        """setfile handling器，将LogsimultaneouslyWriteFile"""
        import logging
        
        # Createfile handling器
        self._file_handler = logging.FileHandler(
            self.log_file_path,
            mode='a',
            encoding='utf-8'
        )
        self._file_handler.setLevel(logging.INFO)
        
        # use与console相同的简洁Format
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        self._file_handler.setFormatter(formatter)
        
        # Add到 report_agent related的 logger
        loggers_to_attach = [
            'mirofish.report_agent',
            'mirofish.zep_tools',
        ]
        
        for logger_name in loggers_to_attach:
            target_logger = logging.getLogger(logger_name)
            # Avoid重复add
            if self._file_handler not in target_logger.handlers:
                target_logger.addHandler(self._file_handler)
    
    def close(self):
        """关闭file handling器并from logger 中移除"""
        import logging
        
        if self._file_handler:
            loggers_to_detach = [
                'mirofish.report_agent',
                'mirofish.zep_tools',
            ]
            
            for logger_name in loggers_to_detach:
                target_logger = logging.getLogger(logger_name)
                if self._file_handler in target_logger.handlers:
                    target_logger.removeHandler(self._file_handler)
            
            self._file_handler.close()
            self._file_handler = None
    
    def __del__(self):
        """析构时ensure关闭file handling器"""
        self.close()


class ReportStatus(str, Enum):
    """ReportStatus"""
    PENDING = "pending"
    PLANNING = "planning"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReportSection:
    """Reportsection"""
    title: str
    content: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content
        }

    def to_markdown(self, level: int = 2) -> str:
        """convert为MarkdownFormat"""
        md = f"{'#' * level} {self.title}\n\n"
        if self.content:
            md += f"{self.content}\n\n"
        return md


@dataclass
class ReportOutline:
    """ReportOutline"""
    title: str
    summary: str
    sections: List[ReportSection]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "sections": [s.to_dict() for s in self.sections]
        }
    
    def to_markdown(self) -> str:
        """convert为MarkdownFormat"""
        md = f"# {self.title}\n\n"
        md += f"> {self.summary}\n\n"
        for section in self.sections:
            md += section.to_markdown()
        return md


@dataclass
class Report:
    """完整Report"""
    report_id: str
    simulation_id: str
    graph_id: str
    simulation_requirement: str
    status: ReportStatus
    outline: Optional[ReportOutline] = None
    markdown_content: str = ""
    created_at: str = ""
    completed_at: str = ""
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "simulation_id": self.simulation_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "status": self.status.value,
            "outline": self.outline.to_dict() if self.outline else None,
            "markdown_content": self.markdown_content,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error": self.error
        }


# ═══════════════════════════════════════════════════════════════
# Prompt TemplateConstant（i18n）
# ═══════════════════════════════════════════════════════════════

# ── Lazy prompt loader (avoid caching prompts at import time before locale is set) ──

_prompt_cache: Dict[str, str] = {}

def _get_prompt_lazy(key: str) -> str:
    """Load a prompt lazily on first use, respecting the current APP_LOCALE."""
    if key not in _prompt_cache:
        _prompt_cache[key] = get_prompt(key)
    return _prompt_cache[key]

# Convenience accessors used throughout this module.  Each property-style
# read goes through the lazy loader so the locale is resolved at call time,
# not at import time.

def _tool_desc_insight_forge():     return _get_prompt_lazy('TOOL_DESC_INSIGHT_FORGE')
def _tool_desc_panorama_search():   return _get_prompt_lazy('TOOL_DESC_PANORAMA_SEARCH')
def _tool_desc_quick_search():      return _get_prompt_lazy('TOOL_DESC_QUICK_SEARCH')
def _tool_desc_interview_agents():  return _get_prompt_lazy('TOOL_DESC_INTERVIEW_AGENTS')
def _plan_system_prompt():          return _get_prompt_lazy('PLAN_SYSTEM_PROMPT')
def _plan_user_prompt_template():   return _get_prompt_lazy('PLAN_USER_PROMPT_TEMPLATE')
def _section_system_prompt_template(): return _get_prompt_lazy('SECTION_SYSTEM_PROMPT_TEMPLATE')
def _section_user_prompt_template():   return _get_prompt_lazy('SECTION_USER_PROMPT_TEMPLATE')
def _react_observation_template():     return _get_prompt_lazy('REACT_OBSERVATION_TEMPLATE')
def _react_insufficient_tools_msg():   return _get_prompt_lazy('REACT_INSUFFICIENT_TOOLS_MSG')
def _react_insufficient_tools_msg_alt(): return _get_prompt_lazy('REACT_INSUFFICIENT_TOOLS_MSG_ALT')
def _react_tool_limit_msg():           return _get_prompt_lazy('REACT_TOOL_LIMIT_MSG')
def _react_unused_tools_hint():        return _get_prompt_lazy('REACT_UNUSED_TOOLS_HINT')
def _react_force_final_msg():          return _get_prompt_lazy('REACT_FORCE_FINAL_MSG')
def _chat_system_prompt_template():    return _get_prompt_lazy('CHAT_SYSTEM_PROMPT_TEMPLATE')
def _chat_observation_suffix():        return _get_prompt_lazy('CHAT_OBSERVATION_SUFFIX')


# ═══════════════════════════════════════════════════════════════
# ReportAgent 主Class
# ═══════════════════════════════════════════════════════════════


class ReportAgent:
    """
    Report Agent - simulationreportgeneratingAgent

    采用ReACT（Reasoning + Acting）模式：
    1. planning阶段：analysissimulationrequirements，planningreport目录结构
    2. generating阶段：逐sectiongeneratingcontent，每section可多次调用toolget信息
    3. 反思阶段：检查content完整性和准确性
    """
    
    # MaximumToolcall次数（Eachsection）
    MAX_TOOL_CALLS_PER_SECTION = 5
    
    # Maximum反思rounds数
    MAX_REFLECTION_ROUNDS = 3
    
    # 对话中的MaximumToolcall次数
    MAX_TOOL_CALLS_PER_CHAT = 2
    
    def __init__(
        self, 
        graph_id: str,
        simulation_id: str,
        simulation_requirement: str,
        llm_client: Optional[LLMClient] = None,
        zep_tools: Optional[ZepToolsService] = None
    ):
        """
        initializingReport Agent
        
        Args:
            graph_id: graphID
            simulation_id: simulationID
            simulation_requirement: simulationrequirements描述
            llm_client: LLM客户端（可选）
            zep_tools: Zeptool服务（可选）
        """
        self.graph_id = graph_id
        self.simulation_id = simulation_id
        self.simulation_requirement = simulation_requirement
        
        self.llm = llm_client or LLMClient()
        self.zep_tools = zep_tools or ZepToolsService()
        
        # ToolDefinition
        self.tools = self._define_tools()
        
        # LogRecord器（在 generate_report 中Initialize）
        self.report_logger: Optional[ReportLogger] = None
        # consoleLogRecord器（在 generate_report 中Initialize）
        self.console_logger: Optional[ReportConsoleLogger] = None
        
        logger.info(f"ReportAgent initializingcompleted: graph_id={graph_id}, simulation_id={simulation_id}")
    
    def _define_tools(self) -> Dict[str, Dict[str, Any]]:
        """definitionavailableTool"""
        return {
            "insight_forge": {
                "name": "insight_forge",
                "description": _tool_desc_insight_forge(),
                "parameters": {
                    "query": "Domanda o argomento da analizzare in profondità",
                    "report_context": "Contesto della sezione del report (opzionale, aiuta a generare sotto-domande più precise)"
                }
            },
            "panorama_search": {
                "name": "panorama_search",
                "description": _tool_desc_panorama_search(),
                "parameters": {
                    "query": "Query di ricerca, per ordinamento per pertinenza",
                    "include_expired": "Includere contenuti scaduti/storici (predefinito True)"
                }
            },
            "quick_search": {
                "name": "quick_search",
                "description": _tool_desc_quick_search(),
                "parameters": {
                    "query": "Stringa di ricerca",
                    "limit": "Numero di risultati da restituire (opzionale, predefinito 10)"
                }
            },
            "interview_agents": {
                "name": "interview_agents",
                "description": _tool_desc_interview_agents(),
                "parameters": {
                    "interview_topic": "Tema o descrizione dell'intervista (es.: 'comprendere il punto di vista degli studenti sull'evento')",
                    "max_agents": "Numero massimo di Agent da intervistare (opzionale, predefinito 5, massimo 10)"
                }
            }
        }
    
    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any], report_context: str = "") -> str:
        """
        execute tool调用
        
        Args:
            tool_name: tool名称
            parameters: toolparameters
            report_context: report上下文（用于InsightForge）
            
        Returns:
            toolexecute结果（文本格式）
        """
        logger.info(f"execute tool: {tool_name}, parameters: {parameters}")
        
        try:
            if tool_name == "insight_forge":
                query = parameters.get("query", "")
                ctx = parameters.get("report_context", "") or report_context
                result = self.zep_tools.insight_forge(
                    graph_id=self.graph_id,
                    query=query,
                    simulation_requirement=self.simulation_requirement,
                    report_context=ctx
                )
                return result.to_text()
            
            elif tool_name == "panorama_search":
                # 广度Search - get全貌
                query = parameters.get("query", "")
                include_expired = parameters.get("include_expired", True)
                if isinstance(include_expired, str):
                    include_expired = include_expired.lower() in ['true', '1', 'yes']
                result = self.zep_tools.panorama_search(
                    graph_id=self.graph_id,
                    query=query,
                    include_expired=include_expired
                )
                return result.to_text()
            
            elif tool_name == "quick_search":
                # SimpleSearch - 快速Retrieval
                query = parameters.get("query", "")
                limit = parameters.get("limit", 10)
                if isinstance(limit, str):
                    limit = int(limit)
                result = self.zep_tools.quick_search(
                    graph_id=self.graph_id,
                    query=query,
                    limit=limit
                )
                return result.to_text()
            
            elif tool_name == "interview_agents":
                # DepthInterview - call真实的OASISInterviewAPIgetSimulationAgent的回答（双Platform）
                interview_topic = parameters.get("interview_topic", parameters.get("query", ""))
                max_agents = parameters.get("max_agents", 5)
                if isinstance(max_agents, str):
                    max_agents = int(max_agents)
                max_agents = min(max_agents, 10)
                result = self.zep_tools.interview_agents(
                    simulation_id=self.simulation_id,
                    interview_requirement=interview_topic,
                    simulation_requirement=self.simulation_requirement,
                    max_agents=max_agents
                )
                return result.to_text()
            
            # ========== 向后兼容的旧Tool（Internal重定向到新Tool） ==========
            
            elif tool_name == "search_graph":
                # 重定向到 quick_search
                logger.info("search_graph 已重定向到 quick_search")
                return self._execute_tool("quick_search", parameters, report_context)
            
            elif tool_name == "get_graph_statistics":
                result = self.zep_tools.get_graph_statistics(self.graph_id)
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            elif tool_name == "get_entity_summary":
                entity_name = parameters.get("entity_name", "")
                result = self.zep_tools.get_entity_summary(
                    graph_id=self.graph_id,
                    entity_name=entity_name
                )
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            elif tool_name == "get_simulation_context":
                # 重定向到 insight_forge，Because它更强大
                logger.info("get_simulation_context 已重定向到 insight_forge")
                query = parameters.get("query", self.simulation_requirement)
                return self._execute_tool("insight_forge", {"query": query}, report_context)
            
            elif tool_name == "get_entities_by_type":
                entity_type = parameters.get("entity_type", "")
                nodes = self.zep_tools.get_entities_by_type(
                    graph_id=self.graph_id,
                    entity_type=entity_type
                )
                result = [n.to_dict() for n in nodes]
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            else:
                return f"Strumento sconosciuto: {tool_name}. Utilizzare uno dei seguenti: insight_forge, panorama_search, quick_search"
                
        except Exception as e:
            logger.error(f"toolexecutefailed: {tool_name}, 错误: {str(e)}")
            return f"Esecuzione strumento fallita: {str(e)}"
    
    # 合法的ToolNameSet，for裸 JSON 兜底解析时校验
    VALID_TOOL_NAMES = {"insight_forge", "panorama_search", "quick_search", "interview_agents"}

    def _parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """
        fromLLMresponse中解析tool调用

        支持的格式（按优先级）：
        1. <tool_call>{"name": "tool_name", "parameters": {...}}</tool_call>
        2. 裸 JSON（response整体或单行就是一unitstool调用 JSON）
        """
        tool_calls = []

        # Format1: XML风格（标准Format）
        xml_pattern = r'<tool_call>\s*(\{.*?\})\s*</tool_call>'
        for match in re.finditer(xml_pattern, response, re.DOTALL):
            try:
                call_data = json.loads(match.group(1))
                tool_calls.append(call_data)
            except json.JSONDecodeError:
                pass

        if tool_calls:
            return tool_calls

        # Format2: 兜底 - LLM 直接output裸 JSON（没包 <tool_call> tab/label）
        # 只在Format1未匹配时尝试，avoid误匹配Body中的 JSON
        stripped = response.strip()
        if stripped.startswith('{') and stripped.endswith('}'):
            try:
                call_data = json.loads(stripped)
                if self._is_valid_tool_call(call_data):
                    tool_calls.append(call_data)
                    return tool_calls
            except json.JSONDecodeError:
                pass

        # ResponsePossibleContains思考文chars + 裸 JSON，尝试提取Finally一units JSON Object
        json_pattern = r'(\{"(?:name|tool)"\s*:.*?\})\s*$'
        match = re.search(json_pattern, stripped, re.DOTALL)
        if match:
            try:
                call_data = json.loads(match.group(1))
                if self._is_valid_tool_call(call_data):
                    tool_calls.append(call_data)
            except json.JSONDecodeError:
                pass

        return tool_calls

    def _is_valid_tool_call(self, data: dict) -> bool:
        """校验解析出的 JSON 是否是合法的Toolcall"""
        # Support {"name": ..., "parameters": ...} 和 {"tool": ..., "params": ...} 两种键名
        tool_name = data.get("name") or data.get("tool")
        if tool_name and tool_name in self.VALID_TOOL_NAMES:
            # 统一键名为 name / parameters
            if "tool" in data:
                data["name"] = data.pop("tool")
            if "params" in data and "parameters" not in data:
                data["parameters"] = data.pop("params")
            return True
        return False
    
    def _get_tools_description(self) -> str:
        """generateToolDescriptiontext"""
        desc_parts = ["Strumenti disponibili:"]
        for name, tool in self.tools.items():
            params_desc = ", ".join([f"{k}: {v}" for k, v in tool["parameters"].items()])
            desc_parts.append(f"- {name}: {tool['description']}")
            if params_desc:
                desc_parts.append(f"  Parametri: {params_desc}")
        return "\n".join(desc_parts)
    
    def plan_outline(
        self, 
        progress_callback: Optional[Callable] = None
    ) -> ReportOutline:
        """
        planningreportoutline
        
        useLLManalysissimulationrequirements，planningreport的目录结构
        
        Args:
            progress_callback: 进度callback函数
            
        Returns:
            ReportOutline: reportoutline
        """
        logger.info("start planning report outline...")
        
        if progress_callback:
            progress_callback("planning", 0, "Analisi dei requisiti di simulazione...")
        
        # FirstgetSimulationcontext
        context = self.zep_tools.get_simulation_context(
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement
        )
        
        if progress_callback:
            progress_callback("planning", 30, "Generazione struttura del report...")
        
        system_prompt = _plan_system_prompt()
        user_prompt = _plan_user_prompt_template().format(
            simulation_requirement=self.simulation_requirement,
            total_nodes=context.get('graph_statistics', {}).get('total_nodes', 0),
            total_edges=context.get('graph_statistics', {}).get('total_edges', 0),
            entity_types=list(context.get('graph_statistics', {}).get('entity_types', {}).keys()),
            total_entities=context.get('total_entities', 0),
            related_facts_json=json.dumps(context.get('related_facts', [])[:10], ensure_ascii=False, indent=2),
        )

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            if progress_callback:
                progress_callback("planning", 80, "Analisi della struttura...")
            
            # ParseOutline
            sections = []
            for section_data in response.get("sections", []):
                sections.append(ReportSection(
                    title=section_data.get("title", ""),
                    content=""
                ))
            
            outline = ReportOutline(
                title=response.get("title", "Report Analisi Simulazione"),
                summary=response.get("summary", ""),
                sections=sections
            )
            
            if progress_callback:
                progress_callback("planning", 100, "Struttura completata")
            
            logger.info(f"outline planning completed: {len(sections)} unitssection")
            return outline
            
        except Exception as e:
            logger.error(f"outlineplanningfailed: {str(e)}")
            # ReturndefaultOutline（3unitssection，作为fallback）
            return ReportOutline(
                title="Report Previsioni Future",
                summary="Analisi delle tendenze future e dei rischi basata sulla simulazione predittiva",
                sections=[
                    ReportSection(title="Scenario di Previsione e Scoperte Principali"),
                    ReportSection(title="Analisi Predittiva del Comportamento"),
                    ReportSection(title="Prospettive e Avvertenze sui Rischi")
                ]
            )
    
    def _generate_section_react(
        self, 
        section: ReportSection,
        outline: ReportOutline,
        previous_sections: List[str],
        progress_callback: Optional[Callable] = None,
        section_index: int = 0
    ) -> str:
        """
        useReACT模式generating单unitssectioncontent
        
        ReACT循环：
        1. Thought（思考）- analysisneed什么信息
        2. Action（行动）- 调用toolget信息
        3. Observation（观察）- analysistoolreturned结果
        4. 重复直到信息足够或达到最大次数
        5. Final Answer（最终回答）- generate sectioncontent
        
        Args:
            section: 要generating的section
            outline: 完整outline
            previous_sections: 之前section的content（用于保持连贯性）
            progress_callback: 进度callback
            section_index: section索引（用于日志记录）
            
        Returns:
            sectioncontent（Markdown格式）
        """
        logger.info(f"ReACTgenerate section: {section.title}")
        
        # RecordsectionStartLog
        if self.report_logger:
            self.report_logger.log_section_start(section.title, section_index)
        
        system_prompt = _section_system_prompt_template().format(
            report_title=outline.title,
            report_summary=outline.summary,
            simulation_requirement=self.simulation_requirement,
            section_title=section.title,
            tools_description=self._get_tools_description(),
        )

        # Build用户prompt - EachCompletedsection各传入Maximum4000chars
        if previous_sections:
            previous_parts = []
            for sec in previous_sections:
                # Eachsection最多4000chars
                truncated = sec[:4000] + "..." if len(sec) > 4000 else sec
                previous_parts.append(truncated)
            previous_content = "\n\n---\n\n".join(previous_parts)
        else:
            previous_content = "(Questa è la prima sezione)"
        
        user_prompt = _section_user_prompt_template().format(
            previous_content=previous_content,
            section_title=section.title,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # ReACT循环
        tool_calls_count = 0
        max_iterations = 5  # Max迭代rounds数
        min_tool_calls = 3  # 最少Toolcall次数
        conflict_retries = 0  # Toolcall与Final Answersimultaneously出现的连续冲突次数
        used_tools = set()  # Record已call过的Tool名
        all_tools = {"insight_forge", "panorama_search", "quick_search", "interview_agents"}

        # Reportcontext，forInsightForge的子issuegenerate
        report_context = f"Titolo sezione: {section.title}\nRequisiti simulazione: {self.simulation_requirement}"
        
        for iteration in range(max_iterations):
            if progress_callback:
                progress_callback(
                    "generating", 
                    int((iteration / max_iterations) * 100),
                    f"Ricerca approfondita e scrittura in corso ({tool_calls_count}/{self.MAX_TOOL_CALLS_PER_SECTION})"
                )
            
            # CallLLM
            response = self.llm.chat(
                messages=messages,
                temperature=0.5,
                max_tokens=16384
            )

            # Check LLM return是否为 None（API Exception或Content为Empty/Null）
            if response is None:
                logger.warning(f"section {section.title} 第 {iteration + 1} 次迭代: LLM returned None")
                # If还有迭代次数，addMessage并Retry
                if iteration < max_iterations - 1:
                    messages.append({"role": "assistant", "content": "(Risposta vuota)"})
                    messages.append({"role": "user", "content": "Continuare a generare il contenuto."})
                    continue
                # Finallyonce迭代也return None，跳出循环enter强制收尾
                break

            logger.debug(f"LLMresponse: {response[:200]}...")

            # Parseonce，复用Result
            tool_calls = self._parse_tool_calls(response)
            has_tool_calls = bool(tool_calls)
            has_final_answer = "Final Answer:" in response

            # ── 冲突process：LLM simultaneouslyoutput了Toolcall和 Final Answer ──
            if has_tool_calls and has_final_answer:
                conflict_retries += 1
                logger.warning(
                    f"section {section.title} 第 {iteration+1} rounds: "
                    f"LLM 同时输出tool调用和 Final Answer（第 {conflict_retries} 次冲突）"
                )

                if conflict_retries <= 2:
                    # first两次：Discard本次Response，要求 LLM Re-回复
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": (
                            "【格式错误】你在一次回复中同时包含了tool调用和 Final Answer，这是不允许的。\n"
                            "每次回复只能做以下两件事之一：\n"
                            "- 调用一unitstool（输出一units <tool_call> 块，不要写 Final Answer）\n"
                            "- output final content（以 'Final Answer:' 开头，不要包含 <tool_call>）\n"
                            "请重新回复，只做其中一件事。"
                        ),
                    })
                    continue
                else:
                    # 第三次：降级process，截断到FirstToolcall，强制execute
                    logger.warning(
                        f"section {section.title}: 连续 {conflict_retries} 次冲突，"
                        "降级为截断execute第一unitstool调用"
                    )
                    first_tool_end = response.find('</tool_call>')
                    if first_tool_end != -1:
                        response = response[:first_tool_end + len('</tool_call>')]
                        tool_calls = self._parse_tool_calls(response)
                        has_tool_calls = bool(tool_calls)
                    has_final_answer = False
                    conflict_retries = 0

            # Record LLM ResponseLog
            if self.report_logger:
                self.report_logger.log_llm_response(
                    section_title=section.title,
                    section_index=section_index,
                    response=response,
                    iteration=iteration + 1,
                    has_tool_calls=has_tool_calls,
                    has_final_answer=has_final_answer
                )

            # ── 情况1：LLM output了 Final Answer ──
            if has_final_answer:
                # Toolcall次数不足，拒绝并要求Continue调Tool
                if tool_calls_count < min_tool_calls:
                    messages.append({"role": "assistant", "content": response})
                    unused_tools = all_tools - used_tools
                    unused_hint = f"（这些tool还未use，推荐用一下他们: {', '.join(unused_tools)}）" if unused_tools else ""
                    messages.append({
                        "role": "user",
                        "content": _react_insufficient_tools_msg().format(
                            tool_calls_count=tool_calls_count,
                            min_tool_calls=min_tool_calls,
                            unused_hint=unused_hint,
                        ),
                    })
                    continue

                # 正常End
                final_answer = response.split("Final Answer:")[-1].strip()
                logger.info(f"section {section.title} generatingcompleted（tool调用: {tool_calls_count}次）")

                if self.report_logger:
                    self.report_logger.log_section_content(
                        section_title=section.title,
                        section_index=section_index,
                        content=final_answer,
                        tool_calls_count=tool_calls_count
                    )
                return final_answer

            # ── 情况2：LLM 尝试callTool ──
            if has_tool_calls:
                # Tool额度已耗尽 → 明确告知，要求output Final Answer
                if tool_calls_count >= self.MAX_TOOL_CALLS_PER_SECTION:
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": _react_tool_limit_msg().format(
                            tool_calls_count=tool_calls_count,
                            max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        ),
                    })
                    continue

                # 只executeFirstToolcall
                call = tool_calls[0]
                if len(tool_calls) > 1:
                    logger.info(f"LLM 尝试调用 {len(tool_calls)} unitstool，只execute第一units: {call['name']}")

                if self.report_logger:
                    self.report_logger.log_tool_call(
                        section_title=section.title,
                        section_index=section_index,
                        tool_name=call["name"],
                        parameters=call.get("parameters", {}),
                        iteration=iteration + 1
                    )

                result = self._execute_tool(
                    call["name"],
                    call.get("parameters", {}),
                    report_context=report_context
                )

                if self.report_logger:
                    self.report_logger.log_tool_result(
                        section_title=section.title,
                        section_index=section_index,
                        tool_name=call["name"],
                        result=result,
                        iteration=iteration + 1
                    )

                tool_calls_count += 1
                used_tools.add(call['name'])

                # Build未useTooltooltip/hint
                unused_tools = all_tools - used_tools
                unused_hint = ""
                if unused_tools and tool_calls_count < self.MAX_TOOL_CALLS_PER_SECTION:
                    unused_hint = _react_unused_tools_hint().format(unused_list="、".join(unused_tools))

                messages.append({"role": "assistant", "content": response})
                messages.append({
                    "role": "user",
                    "content": _react_observation_template().format(
                        tool_name=call["name"],
                        result=result,
                        tool_calls_count=tool_calls_count,
                        max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        used_tools_str=", ".join(used_tools),
                        unused_hint=unused_hint,
                    ),
                })
                continue

            # ── 情况3：既没有Toolcall，也没有 Final Answer ──
            messages.append({"role": "assistant", "content": response})

            if tool_calls_count < min_tool_calls:
                # Toolcall次数不足，Recommended未用过的Tool
                unused_tools = all_tools - used_tools
                unused_hint = f"（这些tool还未use，推荐用一下他们: {', '.join(unused_tools)}）" if unused_tools else ""

                messages.append({
                    "role": "user",
                    "content": _react_insufficient_tools_msg_alt().format(
                        tool_calls_count=tool_calls_count,
                        min_tool_calls=min_tool_calls,
                        unused_hint=unused_hint,
                    ),
                })
                continue

            # Toolcall已足够，LLM output了Content但没带 "Final Answer:" first缀
            # 直接将这段Content作为Final答案，不再Empty/Null转
            logger.info(f"section {section.title} 未检测到 'Final Answer:' 前缀，直接采纳LLM输出作为最终content（tool调用: {tool_calls_count}次）")
            final_answer = response.strip()

            if self.report_logger:
                self.report_logger.log_section_content(
                    section_title=section.title,
                    section_index=section_index,
                    content=final_answer,
                    tool_calls_count=tool_calls_count
                )
            return final_answer
        
        # 达到Maximum迭代次数，强制generateContent
        logger.warning(f"section {section.title} 达到最大迭代次数，强制generating")
        messages.append({"role": "user", "content": _react_force_final_msg()})
        
        response = self.llm.chat(
            messages=messages,
            temperature=0.5,
            max_tokens=16384
        )

        # Check强制收尾时 LLM return是否为 None
        if response is None:
            logger.error(f"section {section.title} 强制收尾时 LLM returned None，use默认错误提示")
            final_answer = f"(Generazione sezione fallita: LLM ha restituito una risposta vuota, riprovare più tardi)"
        elif "Final Answer:" in response:
            final_answer = response.split("Final Answer:")[-1].strip()
        else:
            final_answer = response
        
        # RecordsectionContentgenerateCompleteLog
        if self.report_logger:
            self.report_logger.log_section_content(
                section_title=section.title,
                section_index=section_index,
                content=final_answer,
                tool_calls_count=tool_calls_count
            )
        
        return final_answer
    
    def generate_report(
        self, 
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
        report_id: Optional[str] = None
    ) -> Report:
        """
        generating完整report（分section实时输出）
        
        每unitssectiongeneratingcompleted后立即保存到file夹，不need等pending整unitsreportcompleted。
        file结构：
        reports/{report_id}/
            meta.json       - report元信息
            outline.json    - reportoutline
            progress.json   - generating进度
            section_01.md   - 第1section
            section_02.md   - 第2section
            ...
            full_report.md  - 完整report
        
        Args:
            progress_callback: 进度callback函数 (stage, progress, message)
            report_id: reportID（可选，如果不传则自动generating）
            
        Returns:
            Report: 完整report
        """
        import uuid
        
        # If没有传入 report_id，则Autogenerate
        if not report_id:
            report_id = f"report_{uuid.uuid4().hex[:12]}"
        start_time = datetime.now()
        
        report = Report(
            report_id=report_id,
            simulation_id=self.simulation_id,
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement,
            status=ReportStatus.PENDING,
            created_at=datetime.now().isoformat()
        )
        
        # Completed的sectionTitleList（forProgressTrace）
        completed_section_titles = []
        
        try:
            # Initialize：CreateReportFile夹并saveInitialStatus
            ReportManager._ensure_report_folder(report_id)
            
            # InitializeLogRecord器（结构化Log agent_log.jsonl）
            self.report_logger = ReportLogger(report_id)
            self.report_logger.log_start(
                simulation_id=self.simulation_id,
                graph_id=self.graph_id,
                simulation_requirement=self.simulation_requirement
            )
            
            # InitializeconsoleLogRecord器（console_log.txt）
            self.console_logger = ReportConsoleLogger(report_id)
            
            ReportManager.update_progress(
                report_id, "pending", 0, "Inizializzazione report...",
                completed_sections=[]
            )
            ReportManager.save_report(report)
            
            # 阶段1: planningOutline
            report.status = ReportStatus.PLANNING
            ReportManager.update_progress(
                report_id, "planning", 5, "Inizio pianificazione struttura report...",
                completed_sections=[]
            )
            
            # RecordplanningStartLog
            self.report_logger.log_planning_start()
            
            if progress_callback:
                progress_callback("planning", 0, "Inizio pianificazione struttura report...")
            
            outline = self.plan_outline(
                progress_callback=lambda stage, prog, msg: 
                    progress_callback(stage, prog // 5, msg) if progress_callback else None
            )
            report.outline = outline
            
            # RecordplanningCompleteLog
            self.report_logger.log_planning_complete(outline.to_dict())
            
            # SaveOutline到File
            ReportManager.save_outline(report_id, outline)
            ReportManager.update_progress(
                report_id, "planning", 15, f"Struttura completata, {len(outline.sections)} sezioni",
                completed_sections=[]
            )
            ReportManager.save_report(report)
            
            logger.info(f"outline saved to file: {report_id}/outline.json")
            
            # 阶段2: 逐sectiongenerate（分sectionsave）
            report.status = ReportStatus.GENERATING
            
            total_sections = len(outline.sections)
            generated_sections = []  # SaveContentforcontext
            
            for i, section in enumerate(outline.sections):
                section_num = i + 1
                base_progress = 20 + int((i / total_sections) * 70)
                
                # UpdateProgress
                ReportManager.update_progress(
                    report_id, "generating", base_progress,
                    f"Generazione sezione: {section.title} ({section_num}/{total_sections})",
                    current_section=section.title,
                    completed_sections=completed_section_titles
                )

                if progress_callback:
                    progress_callback(
                        "generating",
                        base_progress,
                        f"Generazione sezione: {section.title} ({section_num}/{total_sections})"
                    )
                
                # Generate主sectionContent
                section_content = self._generate_section_react(
                    section=section,
                    outline=outline,
                    previous_sections=generated_sections,
                    progress_callback=lambda stage, prog, msg:
                        progress_callback(
                            stage, 
                            base_progress + int(prog * 0.7 / total_sections),
                            msg
                        ) if progress_callback else None,
                    section_index=section_num
                )
                
                section.content = section_content
                generated_sections.append(f"## {section.title}\n\n{section_content}")

                # Savesection
                ReportManager.save_section(report_id, section_num, section)
                completed_section_titles.append(section.title)

                # RecordsectionCompleteLog
                full_section_content = f"## {section.title}\n\n{section_content}"

                if self.report_logger:
                    self.report_logger.log_section_full_complete(
                        section_title=section.title,
                        section_index=section_num,
                        full_content=full_section_content.strip()
                    )

                logger.info(f"section已保存: {report_id}/section_{section_num:02d}.md")
                
                # UpdateProgress
                ReportManager.update_progress(
                    report_id, "generating", 
                    base_progress + int(70 / total_sections),
                    f"Sezione {section.title} completata",
                    current_section=None,
                    completed_sections=completed_section_titles
                )
            
            # 阶段3: assembling完整Report
            if progress_callback:
                progress_callback("generating", 95, "Assemblaggio report completo...")
            
            ReportManager.update_progress(
                report_id, "generating", 95, "Assemblaggio report completo...",
                completed_sections=completed_section_titles
            )
            
            # useReportManagerassembling完整Report
            report.markdown_content = ReportManager.assemble_full_report(report_id, outline)
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.now().isoformat()
            
            # Calculate总耗时
            total_time_seconds = (datetime.now() - start_time).total_seconds()
            
            # RecordReportCompleteLog
            if self.report_logger:
                self.report_logger.log_report_complete(
                    total_sections=total_sections,
                    total_time_seconds=total_time_seconds
                )
            
            # SaveFinalReport
            ReportManager.save_report(report)
            ReportManager.update_progress(
                report_id, "completed", 100, "Generazione report completata",
                completed_sections=completed_section_titles
            )
            
            if progress_callback:
                progress_callback("completed", 100, "Generazione report completata")
            
            logger.info(f"report generation completed: {report_id}")
            
            # CloseconsoleLogRecord器
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None
            
            return report
            
        except Exception as e:
            logger.error(f"report generation failed: {str(e)}")
            report.status = ReportStatus.FAILED
            report.error = str(e)
            
            # RecordErrorLog
            if self.report_logger:
                self.report_logger.log_error(str(e), "failed")
            
            # SaveFailedStatus
            try:
                ReportManager.save_report(report)
                ReportManager.update_progress(
                    report_id, "failed", -1, f"Generazione report fallita: {str(e)}",
                    completed_sections=completed_section_titles
                )
            except Exception:
                pass  # IgnoresaveFailed的Error
            
            # CloseconsoleLogRecord器
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None
            
            return report
    
    def chat(
        self, 
        message: str,
        chat_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        与Report Agent对话
        
        在对话中Agentcan自主调用retrievaltool来回答questions
        
        Args:
            message: 用户消息
            chat_history: 对话historical
            
        Returns:
            {
                "response": "Agent回复",
                "tool_calls": [调用的toollist],
                "sources": [信息来源]
            }
        """
        logger.info(f"Report Agent对话: {message[:50]}...")
        
        chat_history = chat_history or []
        
        # Get已generate的ReportContent
        report_content = ""
        try:
            report = ReportManager.get_report_by_simulation(self.simulation_id)
            if report and report.markdown_content:
                # 限制ReportLength，avoidcontext过长
                report_content = report.markdown_content[:15000]
                if len(report.markdown_content) > 15000:
                    report_content += "\n\n... [Contenuto report troncato] ..."
        except Exception as e:
            logger.warning(f"getreportcontentfailed: {e}")
        
        system_prompt = _chat_system_prompt_template().format(
            simulation_requirement=self.simulation_requirement,
            report_content=report_content if report_content else "(Nessun report disponibile)",
            tools_description=self._get_tools_description(),
        )

        # BuildMessage
        messages = [{"role": "system", "content": system_prompt}]
        
        # Addhistorical对话
        for h in chat_history[-10:]:  # 限制historicalLength
            messages.append(h)
        
        # Add用户Message
        messages.append({
            "role": "user", 
            "content": message
        })
        
        # ReACT循环（简化版）
        tool_calls_made = []
        max_iterations = 2  # 减少迭代rounds数
        
        for iteration in range(max_iterations):
            response = self.llm.chat(
                messages=messages,
                temperature=0.5
            )
            
            # ParseToolcall
            tool_calls = self._parse_tool_calls(response)
            
            if not tool_calls:
                # 没有Toolcall，直接returnResponse
                clean_response = re.sub(r'<tool_call>.*?</tool_call>', '', response, flags=re.DOTALL)
                clean_response = re.sub(r'\[TOOL_CALL\].*?\)', '', clean_response)
                
                return {
                    "response": clean_response.strip(),
                    "tool_calls": tool_calls_made,
                    "sources": [tc.get("parameters", {}).get("query", "") for tc in tool_calls_made]
                }
            
            # ExecuteToolcall（限制Quantity）
            tool_results = []
            for call in tool_calls[:1]:  # 每rounds最多execute1次Toolcall
                if len(tool_calls_made) >= self.MAX_TOOL_CALLS_PER_CHAT:
                    break
                result = self._execute_tool(call["name"], call.get("parameters", {}))
                tool_results.append({
                    "tool": call["name"],
                    "result": result[:1500]  # 限制ResultLength
                })
                tool_calls_made.append(call)
            
            # 将Resultadd到Message
            messages.append({"role": "assistant", "content": response})
            observation = "\n".join([f"[Risultato {r['tool']}]\n{r['result']}" for r in tool_results])
            messages.append({
                "role": "user",
                "content": observation + _chat_observation_suffix()
            })
        
        # 达到Maximum迭代，getFinalResponse
        final_response = self.llm.chat(
            messages=messages,
            temperature=0.5
        )
        
        # Clean upResponse
        clean_response = re.sub(r'<tool_call>.*?</tool_call>', '', final_response, flags=re.DOTALL)
        clean_response = re.sub(r'\[TOOL_CALL\].*?\)', '', clean_response)
        
        return {
            "response": clean_response.strip(),
            "tool_calls": tool_calls_made,
            "sources": [tc.get("parameters", {}).get("query", "") for tc in tool_calls_made]
        }


class ReportManager:
    """
    reportmanage器
    
    负责report的持久化store和retrieval
    
    file结构（分section输出）：
    reports/
      {report_id}/
        meta.json          - report元信息和state
        outline.json       - reportoutline
        progress.json      - generating进度
        section_01.md      - 第1section
        section_02.md      - 第2section
        ...
        full_report.md     - 完整report
    """
    
    # ReportstoreDirectory
    REPORTS_DIR = os.path.join(Config.UPLOAD_FOLDER, 'reports')
    
    @classmethod
    def _ensure_reports_dir(cls):
        """ensureReport根Directoryexists"""
        os.makedirs(cls.REPORTS_DIR, exist_ok=True)
    
    @classmethod
    def _get_report_folder(cls, report_id: str) -> str:
        """getReportFile夹Path"""
        return os.path.join(cls.REPORTS_DIR, report_id)
    
    @classmethod
    def _ensure_report_folder(cls, report_id: str) -> str:
        """ensureReportFile夹exists并returnPath"""
        folder = cls._get_report_folder(report_id)
        os.makedirs(folder, exist_ok=True)
        return folder
    
    @classmethod
    def _get_report_path(cls, report_id: str) -> str:
        """getReport元infoFilePath"""
        return os.path.join(cls._get_report_folder(report_id), "meta.json")
    
    @classmethod
    def _get_report_markdown_path(cls, report_id: str) -> str:
        """get完整ReportMarkdownFilePath"""
        return os.path.join(cls._get_report_folder(report_id), "full_report.md")
    
    @classmethod
    def _get_outline_path(cls, report_id: str) -> str:
        """getOutlineFilePath"""
        return os.path.join(cls._get_report_folder(report_id), "outline.json")
    
    @classmethod
    def _get_progress_path(cls, report_id: str) -> str:
        """getProgressFilePath"""
        return os.path.join(cls._get_report_folder(report_id), "progress.json")
    
    @classmethod
    def _get_section_path(cls, report_id: str, section_index: int) -> str:
        """getsectionMarkdownFilePath"""
        return os.path.join(cls._get_report_folder(report_id), f"section_{section_index:02d}.md")
    
    @classmethod
    def _get_agent_log_path(cls, report_id: str) -> str:
        """get Agent LogFilePath"""
        return os.path.join(cls._get_report_folder(report_id), "agent_log.jsonl")
    
    @classmethod
    def _get_console_log_path(cls, report_id: str) -> str:
        """getconsoleLogFilePath"""
        return os.path.join(cls._get_report_folder(report_id), "console_log.txt")
    
    @classmethod
    def get_console_log(cls, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        """
        get控制台日志content
        
        这是reportgenerating过程中的控制台输出日志（INFO、WARNING等），
        与 agent_log.jsonl 的结构化日志不同。
        
        Args:
            report_id: reportID
            from_line: from第几行开始读取（用于增量get，0 表示from头开始）
            
        Returns:
            {
                "logs": [日志行list],
                "total_lines": 总行数,
                "from_line": 起始行号,
                "has_more": 是否还有更多日志
            }
        """
        log_path = cls._get_console_log_path(report_id)
        
        if not os.path.exists(log_path):
            return {
                "logs": [],
                "total_lines": 0,
                "from_line": 0,
                "has_more": False
            }
        
        logs = []
        total_lines = 0
        
        with open(log_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= from_line:
                    # KeepOriginalLog行，去掉末尾换行符
                    logs.append(line.rstrip('\n\r'))
        
        return {
            "logs": logs,
            "total_lines": total_lines,
            "from_line": from_line,
            "has_more": False  # 已Read到末尾
        }
    
    @classmethod
    def get_console_log_stream(cls, report_id: str) -> List[str]:
        """
        get完整的控制台日志（一次性getall）
        
        Args:
            report_id: reportID
            
        Returns:
            日志行list
        """
        result = cls.get_console_log(report_id, from_line=0)
        return result["logs"]
    
    @classmethod
    def get_agent_log(cls, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        """
        get Agent 日志content
        
        Args:
            report_id: reportID
            from_line: from第几行开始读取（用于增量get，0 表示from头开始）
            
        Returns:
            {
                "logs": [日志items目list],
                "total_lines": 总行数,
                "from_line": 起始行号,
                "has_more": 是否还有更多日志
            }
        """
        log_path = cls._get_agent_log_path(report_id)
        
        if not os.path.exists(log_path):
            return {
                "logs": [],
                "total_lines": 0,
                "from_line": 0,
                "has_more": False
            }
        
        logs = []
        total_lines = 0
        
        with open(log_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= from_line:
                    try:
                        log_entry = json.loads(line.strip())
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        # Skip解析Failed的行
                        continue
        
        return {
            "logs": logs,
            "total_lines": total_lines,
            "from_line": from_line,
            "has_more": False  # 已Read到末尾
        }
    
    @classmethod
    def get_agent_log_stream(cls, report_id: str) -> List[Dict[str, Any]]:
        """
        get完整的 Agent 日志（用于一次性getall）
        
        Args:
            report_id: reportID
            
        Returns:
            日志items目list
        """
        result = cls.get_agent_log(report_id, from_line=0)
        return result["logs"]
    
    @classmethod
    def save_outline(cls, report_id: str, outline: ReportOutline) -> None:
        """
        保存reportoutline
        
        在planning阶段completed后立即调用
        """
        cls._ensure_report_folder(report_id)
        
        with open(cls._get_outline_path(report_id), 'w', encoding='utf-8') as f:
            json.dump(outline.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"outline saved: {report_id}")
    
    @classmethod
    def save_section(
        cls,
        report_id: str,
        section_index: int,
        section: ReportSection
    ) -> str:
        """
        保存单unitssection

        在每unitssectiongeneratingcompleted后立即调用，实现分section输出

        Args:
            report_id: reportID
            section_index: section索引（from1开始）
            section: sectionobject

        Returns:
            保存的file路径
        """
        cls._ensure_report_folder(report_id)

        # BuildsectionMarkdownContent - cleanupPossibleExists的重复Title
        cleaned_content = cls._clean_section_content(section.content, section.title)
        md_content = f"## {section.title}\n\n"
        if cleaned_content:
            md_content += f"{cleaned_content}\n\n"

        # SaveFile
        file_suffix = f"section_{section_index:02d}.md"
        file_path = os.path.join(cls._get_report_folder(report_id), file_suffix)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        logger.info(f"section已保存: {report_id}/{file_suffix}")
        return file_path
    
    @classmethod
    def _clean_section_content(cls, content: str, section_title: str) -> str:
        """
        清理sectioncontent
        
        1. 移除content开头与sectiontitle重复的Markdowntitle行
        2. 将所有 ### 及以下级别的Titleconvert为粗体text
        
        Args:
            content: 原始content
            section_title: sectiontitle
            
        Returns:
            清理后的content
        """
        import re
        
        if not content:
            return content
        
        content = content.strip()
        lines = content.split('\n')
        cleaned_lines = []
        skip_next_empty = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Check是否是MarkdownTitle行
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            
            if heading_match:
                level = len(heading_match.group(1))
                title_text = heading_match.group(2).strip()
                
                # Check是否是与sectionTitle重复的Title（Skipfirst5行内的重复）
                if i < 5:
                    if title_text == section_title or title_text.replace(' ', '') == section_title.replace(' ', ''):
                        skip_next_empty = True
                        continue
                
                # 将All级别的Title（#, ##, ###, ####etc.）convert为粗体
                # BecausesectionTitle由Systemadd，Content中不应有任何Title
                cleaned_lines.append(f"**{title_text}**")
                cleaned_lines.append("")  # AddEmpty/Null行
                continue
            
            # If上一行是被Skip的Title，且CurrentbehaviorEmpty/Null，也Skip
            if skip_next_empty and stripped == '':
                skip_next_empty = False
                continue
            
            skip_next_empty = False
            cleaned_lines.append(line)
        
        # Remove开头的Empty/Null行
        while cleaned_lines and cleaned_lines[0].strip() == '':
            cleaned_lines.pop(0)
        
        # Remove开头的分隔线
        while cleaned_lines and cleaned_lines[0].strip() in ['---', '***', '___']:
            cleaned_lines.pop(0)
            # simultaneously移除分隔线后的Empty/Null行
            while cleaned_lines and cleaned_lines[0].strip() == '':
                cleaned_lines.pop(0)
        
        return '\n'.join(cleaned_lines)
    
    @classmethod
    def update_progress(
        cls, 
        report_id: str, 
        status: str, 
        progress: int, 
        message: str,
        current_section: str = None,
        completed_sections: List[str] = None
    ) -> None:
        """
        更新reportgenerating进度
        
        前端can通过读取progress.jsonget实时进度
        """
        cls._ensure_report_folder(report_id)
        
        progress_data = {
            "status": status,
            "progress": progress,
            "message": message,
            "current_section": current_section,
            "completed_sections": completed_sections or [],
            "updated_at": datetime.now().isoformat()
        }
        
        with open(cls._get_progress_path(report_id), 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def get_progress(cls, report_id: str) -> Optional[Dict[str, Any]]:
        """getReportgenerateProgress"""
        path = cls._get_progress_path(report_id)
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @classmethod
    def get_generated_sections(cls, report_id: str) -> List[Dict[str, Any]]:
        """
        get已generating的sectionlist
        
        returned所有已保存的sectionfile信息
        """
        folder = cls._get_report_folder(report_id)
        
        if not os.path.exists(folder):
            return []
        
        sections = []
        for filename in sorted(os.listdir(folder)):
            if filename.startswith('section_') and filename.endswith('.md'):
                file_path = os.path.join(folder, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # fromFilename解析sectionIndex
                parts = filename.replace('.md', '').split('_')
                section_index = int(parts[1])

                sections.append({
                    "filename": filename,
                    "section_index": section_index,
                    "content": content
                })

        return sections
    
    @classmethod
    def assemble_full_report(cls, report_id: str, outline: ReportOutline) -> str:
        """
        assembling完整report
        
        from已保存的sectionfileassembling完整report，并进行title清理
        """
        folder = cls._get_report_folder(report_id)
        
        # BuildReportHeader
        md_content = f"# {outline.title}\n\n"
        md_content += f"> {outline.summary}\n\n"
        md_content += f"---\n\n"
        
        # 按顺序ReadAllsectionFile
        sections = cls.get_generated_sections(report_id)
        for section_info in sections:
            md_content += section_info["content"]
        
        # post-process：cleanup整unitsReport的Titleissue
        md_content = cls._post_process_report(md_content, outline)
        
        # Save完整Report
        full_path = cls._get_report_markdown_path(report_id)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"完整report已assembling: {report_id}")
        return md_content
    
    @classmethod
    def _post_process_report(cls, content: str, outline: ReportOutline) -> str:
        """
        后处理reportcontent
        
        1. 移除重复的title
        2. KeepReport主Title(#)和sectionTitle(##)，移除其他级别的Title(###, ####etc.)
        3. 清理多余的空行和分隔线
        
        Args:
            content: 原始reportcontent
            outline: reportoutline
            
        Returns:
            处理后的content
        """
        import re
        
        lines = content.split('\n')
        processed_lines = []
        prev_was_heading = False
        
        # 收集Outline中的AllsectionTitle
        section_titles = set()
        for section in outline.sections:
            section_titles.add(section.title)
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Check是否是Title行
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                
                # Check是否是重复Title（在连续5行内出现相同Content的Title）
                is_duplicate = False
                for j in range(max(0, len(processed_lines) - 5), len(processed_lines)):
                    prev_line = processed_lines[j].strip()
                    prev_match = re.match(r'^(#{1,6})\s+(.+)$', prev_line)
                    if prev_match:
                        prev_title = prev_match.group(2).strip()
                        if prev_title == title:
                            is_duplicate = True
                            break
                
                if is_duplicate:
                    # Skip重复Title及其后的Empty/Null行
                    i += 1
                    while i < len(lines) and lines[i].strip() == '':
                        i += 1
                    continue
                
                # Title层级process：
                # - # (level=1) 只KeepReport主Title
                # - ## (level=2) KeepsectionTitle
                # - ### 及Below (level>=3) convert为粗体text
                
                if level == 1:
                    if title == outline.title:
                        # KeepReport主Title
                        processed_lines.append(line)
                        prev_was_heading = True
                    elif title in section_titles:
                        # SectionTitleErroruse了#，修正为##
                        processed_lines.append(f"## {title}")
                        prev_was_heading = True
                    else:
                        # 其他一级Titleconvert to粗体
                        processed_lines.append(f"**{title}**")
                        processed_lines.append("")
                        prev_was_heading = False
                elif level == 2:
                    if title in section_titles or title == outline.title:
                        # KeepsectionTitle
                        processed_lines.append(line)
                        prev_was_heading = True
                    else:
                        # 非section的二级Titleconvert to粗体
                        processed_lines.append(f"**{title}**")
                        processed_lines.append("")
                        prev_was_heading = False
                else:
                    # ### 及Below级别的Titleconvert为粗体text
                    processed_lines.append(f"**{title}**")
                    processed_lines.append("")
                    prev_was_heading = False
                
                i += 1
                continue
            
            elif stripped == '---' and prev_was_heading:
                # SkipTitle后紧跟的分隔线
                i += 1
                continue
            
            elif stripped == '' and prev_was_heading:
                # Title后只Keep一unitsEmpty/Null行
                if processed_lines and processed_lines[-1].strip() != '':
                    processed_lines.append(line)
                prev_was_heading = False
            
            else:
                processed_lines.append(line)
                prev_was_heading = False
            
            i += 1
        
        # Clean up连续的MultipleEmpty/Null行（Keep最多2units）
        result_lines = []
        empty_count = 0
        for line in processed_lines:
            if line.strip() == '':
                empty_count += 1
                if empty_count <= 2:
                    result_lines.append(line)
            else:
                empty_count = 0
                result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    @classmethod
    def save_report(cls, report: Report) -> None:
        """saveReport元info和完整Report"""
        cls._ensure_report_folder(report.report_id)
        
        # Save元infoJSON
        with open(cls._get_report_path(report.report_id), 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        
        # SaveOutline
        if report.outline:
            cls.save_outline(report.report_id, report.outline)
        
        # Save完整MarkdownReport
        if report.markdown_content:
            with open(cls._get_report_markdown_path(report.report_id), 'w', encoding='utf-8') as f:
                f.write(report.markdown_content)
        
        logger.info(f"report saved: {report.report_id}")
    
    @classmethod
    def get_report(cls, report_id: str) -> Optional[Report]:
        """getReport"""
        path = cls._get_report_path(report_id)
        
        if not os.path.exists(path):
            # 兼容旧Format：check直接store在reportsDirectory下的File
            old_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.json")
            if os.path.exists(old_path):
                path = old_path
            else:
                return None
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 重建ReportObject
        outline = None
        if data.get('outline'):
            outline_data = data['outline']
            sections = []
            for s in outline_data.get('sections', []):
                sections.append(ReportSection(
                    title=s['title'],
                    content=s.get('content', '')
                ))
            outline = ReportOutline(
                title=outline_data['title'],
                summary=outline_data['summary'],
                sections=sections
            )
        
        # Ifmarkdown_content为Empty/Null，尝试fromfull_report.mdRead
        markdown_content = data.get('markdown_content', '')
        if not markdown_content:
            full_report_path = cls._get_report_markdown_path(report_id)
            if os.path.exists(full_report_path):
                with open(full_report_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
        
        return Report(
            report_id=data['report_id'],
            simulation_id=data['simulation_id'],
            graph_id=data['graph_id'],
            simulation_requirement=data['simulation_requirement'],
            status=ReportStatus(data['status']),
            outline=outline,
            markdown_content=markdown_content,
            created_at=data.get('created_at', ''),
            completed_at=data.get('completed_at', ''),
            error=data.get('error')
        )
    
    @classmethod
    def get_report_by_simulation(cls, simulation_id: str) -> Optional[Report]:
        """根据SimulationIDgetReport"""
        cls._ensure_reports_dir()
        
        for item in os.listdir(cls.REPORTS_DIR):
            item_path = os.path.join(cls.REPORTS_DIR, item)
            # 新Format：File夹
            if os.path.isdir(item_path):
                report = cls.get_report(item)
                if report and report.simulation_id == simulation_id:
                    return report
            # 兼容旧Format：JSONFile
            elif item.endswith('.json'):
                report_id = item[:-5]
                report = cls.get_report(report_id)
                if report and report.simulation_id == simulation_id:
                    return report
        
        return None
    
    @classmethod
    def list_reports(cls, simulation_id: Optional[str] = None, limit: int = 50) -> List[Report]:
        """列出Report"""
        cls._ensure_reports_dir()
        
        reports = []
        for item in os.listdir(cls.REPORTS_DIR):
            item_path = os.path.join(cls.REPORTS_DIR, item)
            # 新Format：File夹
            if os.path.isdir(item_path):
                report = cls.get_report(item)
                if report:
                    if simulation_id is None or report.simulation_id == simulation_id:
                        reports.append(report)
            # 兼容旧Format：JSONFile
            elif item.endswith('.json'):
                report_id = item[:-5]
                report = cls.get_report(report_id)
                if report:
                    if simulation_id is None or report.simulation_id == simulation_id:
                        reports.append(report)
        
        # 按CreateTime倒序
        reports.sort(key=lambda r: r.created_at, reverse=True)
        
        return reports[:limit]
    
    @classmethod
    def delete_report(cls, report_id: str) -> bool:
        """DeleteReport（整unitsFile夹）"""
        import shutil
        
        folder_path = cls._get_report_folder(report_id)
        
        # 新Format：Delete整unitsFile夹
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            shutil.rmtree(folder_path)
            logger.info(f"reportfile夹已删除: {report_id}")
            return True
        
        # 兼容旧Format：Delete单独的File
        deleted = False
        old_json_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.json")
        old_md_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.md")
        
        if os.path.exists(old_json_path):
            os.remove(old_json_path)
            deleted = True
        if os.path.exists(old_md_path):
            os.remove(old_md_path)
            deleted = True
        
        return deleted
