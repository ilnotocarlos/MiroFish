"""
Chinese (zh) API messages for MiroFish backend.
All user-facing messages from graph.py, report.py, and simulation.py API routes.
"""

# ============== graph.py ==============

# Project management
PROJECT_NOT_FOUND = "项目不存在: {project_id}"
PROJECT_NOT_FOUND_OR_DELETE_FAILED = "项目不存在或删除失败: {project_id}"
PROJECT_DELETED = "项目已删除: {project_id}"
PROJECT_RESET = "项目已重置: {project_id}"

# Ontology generation
PROVIDE_SIMULATION_REQUIREMENT = "请提供模拟需求描述 (simulation_requirement)"
UPLOAD_AT_LEAST_ONE_FILE = "请至少上传一个文档文件"
NO_DOCUMENTS_PROCESSED = "没有成功处理任何文档，请检查文件格式"

# Graph building
CONFIG_ERROR = "配置错误: {errors}"
PROVIDE_PROJECT_ID = "请提供 project_id"
ONTOLOGY_NOT_GENERATED = "项目尚未生成本体，请先调用 /ontology/generate"
GRAPH_BUILDING_IN_PROGRESS = "图谱正在构建中，请勿重复提交。如需强制重建，请添加 force: true"
EXTRACTED_TEXT_NOT_FOUND = "未找到提取的文本内容"
ONTOLOGY_NOT_FOUND = "未找到本体定义"
GRAPH_BUILD_TASK_STARTED = "图谱构建任务已启动，请通过 /task/{task_id} 查询进度"
GRAPH_BUILD_COMPLETED = "图谱构建完成"
GRAPH_BUILD_FAILED = "构建失败: {error}"

# Task management
TASK_NOT_FOUND = "任务不存在: {task_id}"

# Graph data
ZEP_API_KEY_NOT_CONFIGURED = "ZEP_API_KEY未配置"
GRAPH_DELETED = "图谱已删除: {graph_id}"

# ============== report.py ==============

# Report generation
PROVIDE_SIMULATION_ID = "请提供 simulation_id"
SIMULATION_NOT_FOUND = "模拟不存在: {simulation_id}"
REPORT_ALREADY_EXISTS = "报告已存在"
MISSING_GRAPH_ID = "缺少图谱ID，请确保已构建图谱"
MISSING_SIMULATION_REQUIREMENT = "缺少模拟需求描述"
REPORT_GENERATE_TASK_STARTED = "报告生成任务已启动，请通过 /api/report/generate/status 查询进度"
REPORT_GENERATION_FAILED = "报告生成失败"

# Report generation status
REPORT_ALREADY_GENERATED = "报告已生成"
PROVIDE_TASK_ID_OR_SIMULATION_ID = "请提供 task_id 或 simulation_id"

# Report retrieval
REPORT_NOT_FOUND = "报告不存在: {report_id}"
NO_REPORT_FOR_SIMULATION = "该模拟暂无报告: {simulation_id}"

# Report management
REPORT_DELETED = "报告已删除: {report_id}"

# Report progress
REPORT_NOT_FOUND_OR_PROGRESS_UNAVAILABLE = "报告不存在或进度信息不可用: {report_id}"

# Report sections
SECTION_NOT_FOUND = "章节不存在: section_{section_index:02d}.md"

# Report tools
PROVIDE_GRAPH_ID_AND_QUERY = "请提供 graph_id 和 query"
PROVIDE_GRAPH_ID = "请提供 graph_id"

# Report chat
PROVIDE_MESSAGE = "请提供 message"
MISSING_GRAPH_ID_SHORT = "缺少图谱ID"

# ============== simulation.py ==============

# Simulation directory check
SIMULATION_DIR_NOT_FOUND = "模拟目录不存在"
MISSING_REQUIRED_FILES = "缺少必要文件"
STATE_NOT_PREPARED = "状态不在已准备列表中或config_generated为false: status={status}, config_generated={config_generated}"
READ_STATE_FILE_FAILED = "读取状态文件失败: {error}"

# Simulation creation
GRAPH_NOT_BUILT = "项目尚未构建图谱，请先调用 /api/graph/build"

# Entity management
ENTITY_NOT_FOUND = "实体不存在: {entity_uuid}"

# Simulation preparation
ALREADY_PREPARED_MESSAGE = "已有完成的准备工作，无需重复生成"
MISSING_SIMULATION_REQUIREMENT_PROJECT = "项目缺少模拟需求描述 (simulation_requirement)"
PREPARE_TASK_STARTED = "准备任务已启动，请通过 /api/simulation/prepare/status 查询进度"

# Prepare status
ALREADY_PREPARED_STATUS = "已有完成的准备工作"
NOT_STARTED_MESSAGE = "尚未开始准备，请调用 /api/simulation/prepare 开始"
TASK_COMPLETED_ALREADY_PREPARED = "任务已完成（准备工作已存在）"

# Simulation config
SIMULATION_CONFIG_NOT_FOUND = "模拟配置不存在，请先调用 /prepare 接口"
CONFIG_FILE_NOT_FOUND = "配置文件不存在，请先调用 /prepare 接口"

# Simulation scripts
UNKNOWN_SCRIPT = "未知脚本: {script_name}，可选: {allowed_scripts}"
SCRIPT_FILE_NOT_FOUND = "脚本文件不存在: {script_name}"

# Profile generation
NO_MATCHING_ENTITIES = "没有找到符合条件的实体"

# Simulation running
MAX_ROUNDS_MUST_BE_POSITIVE = "max_rounds 必须是正整数"
MAX_ROUNDS_MUST_BE_INTEGER = "max_rounds 必须是有效的整数"
INVALID_PLATFORM_TYPE = "无效的平台类型: {platform}，可选: twitter/reddit/parallel"
SIMULATION_RUNNING_STOP_FIRST = "模拟正在运行中，请先调用 /stop 接口停止，或使用 force=true 强制重新开始"
SIMULATION_NOT_READY = "模拟未准备好，当前状态: {status}，请先调用 /prepare 接口"
GRAPH_MEMORY_UPDATE_REQUIRES_GRAPH_ID = "启用图谱记忆更新需要有效的 graph_id，请确保项目已构建图谱"

# Database messages
DB_NOT_EXISTS_MESSAGE = "数据库不存在，模拟可能尚未运行"

# Interview
PROVIDE_AGENT_ID = "请提供 agent_id"
PROVIDE_PROMPT = "请提供 prompt（采访问题）"
PLATFORM_INVALID = "platform 参数只能是 'twitter' 或 'reddit'"
SIMULATION_ENV_NOT_RUNNING = "模拟环境未运行或已关闭。请确保模拟已完成并进入等待命令模式。"
INTERVIEW_TIMEOUT = "等待Interview响应超时: {error}"

# Interview batch
PROVIDE_INTERVIEWS_LIST = "请提供 interviews（采访列表）"
INTERVIEW_ITEM_MISSING_AGENT_ID = "采访列表第{index}项缺少 agent_id"
INTERVIEW_ITEM_MISSING_PROMPT = "采访列表第{index}项缺少 prompt"
INTERVIEW_ITEM_INVALID_PLATFORM = "采访列表第{index}项的platform只能是 'twitter' 或 'reddit'"
BATCH_INTERVIEW_TIMEOUT = "等待批量Interview响应超时: {error}"

# Interview all
GLOBAL_INTERVIEW_TIMEOUT = "等待全局Interview响应超时: {error}"

# Environment status
ENV_RUNNING_MESSAGE = "环境正在运行，可以接收Interview命令"
ENV_NOT_RUNNING_MESSAGE = "环境未运行或已关闭"

# Close environment
CLOSE_ENV_COMMAND_SENT = "环境关闭命令已发送"

# Task progress messages (used in background tasks)
INIT_GRAPH_BUILD_SERVICE = "初始化图谱构建服务..."
TEXT_CHUNKING = "文本分块中..."
CREATING_ZEP_GRAPH = "创建Zep图谱..."
SETTING_ONTOLOGY = "设置本体定义..."
ADDING_TEXT_CHUNKS = "开始添加 {total_chunks} 个文本块..."
WAITING_ZEP_PROCESSING = "等待Zep处理数据..."
FETCHING_GRAPH_DATA = "获取图谱数据..."
INIT_REPORT_AGENT = "初始化Report Agent..."
START_PREPARING_SIMULATION = "开始准备模拟环境..."
