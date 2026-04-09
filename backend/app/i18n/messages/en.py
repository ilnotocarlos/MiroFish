"""
English (en) API messages for MiroFish backend.
All user-facing messages from graph.py, report.py, and simulation.py API routes.
"""

# ============== graph.py ==============

# Project management
PROJECT_NOT_FOUND = "Project not found: {project_id}"
PROJECT_NOT_FOUND_OR_DELETE_FAILED = "Project not found or deletion failed: {project_id}"
PROJECT_DELETED = "Project deleted: {project_id}"
PROJECT_RESET = "Project reset: {project_id}"

# Ontology generation
PROVIDE_SIMULATION_REQUIREMENT = "Please provide the simulation requirement description (simulation_requirement)"
UPLOAD_AT_LEAST_ONE_FILE = "Please upload at least one document file"
NO_DOCUMENTS_PROCESSED = "No documents were processed successfully, please check the file format"

# Graph building
CONFIG_ERROR = "Configuration error: {errors}"
PROVIDE_PROJECT_ID = "Please provide project_id"
ONTOLOGY_NOT_GENERATED = "The project ontology has not been generated yet, please call /ontology/generate first"
GRAPH_BUILDING_IN_PROGRESS = "Graph construction is in progress, do not send duplicate requests. To force a rebuild, add force: true"
EXTRACTED_TEXT_NOT_FOUND = "Extracted text content not found"
ONTOLOGY_NOT_FOUND = "Ontology definition not found"
GRAPH_BUILD_TASK_STARTED = "Graph construction task started, check status via /task/{task_id}"
GRAPH_BUILD_COMPLETED = "Graph construction completed"
GRAPH_BUILD_FAILED = "Construction failed: {error}"

# Task management
TASK_NOT_FOUND = "Task not found: {task_id}"

# Graph data
ZEP_API_KEY_NOT_CONFIGURED = "ZEP_API_KEY not configured"
GRAPH_DELETED = "Graph deleted: {graph_id}"

# ============== report.py ==============

# Report generation
PROVIDE_SIMULATION_ID = "Please provide simulation_id"
SIMULATION_NOT_FOUND = "Simulation not found: {simulation_id}"
REPORT_ALREADY_EXISTS = "The report already exists"
MISSING_GRAPH_ID = "Graph ID missing, make sure you have built the graph"
MISSING_SIMULATION_REQUIREMENT = "Simulation requirement description missing"
REPORT_GENERATE_TASK_STARTED = "Report generation task started, check status via /api/report/generate/status"
REPORT_GENERATION_FAILED = "Report generation failed"

# Report generation status
REPORT_ALREADY_GENERATED = "Report already generated"
PROVIDE_TASK_ID_OR_SIMULATION_ID = "Please provide task_id or simulation_id"

# Report retrieval
REPORT_NOT_FOUND = "Report not found: {report_id}"
NO_REPORT_FOR_SIMULATION = "No report available for this simulation: {simulation_id}"

# Report management
REPORT_DELETED = "Report deleted: {report_id}"

# Report progress
REPORT_NOT_FOUND_OR_PROGRESS_UNAVAILABLE = "Report not found or progress information unavailable: {report_id}"

# Report sections
SECTION_NOT_FOUND = "Section not found: section_{section_index:02d}.md"

# Report tools
PROVIDE_GRAPH_ID_AND_QUERY = "Please provide graph_id and query"
PROVIDE_GRAPH_ID = "Please provide graph_id"

# Report chat
PROVIDE_MESSAGE = "Please provide message"
MISSING_GRAPH_ID_SHORT = "Graph ID missing"

# ============== simulation.py ==============

# Simulation directory check
SIMULATION_DIR_NOT_FOUND = "Simulation directory not found"
MISSING_REQUIRED_FILES = "Required files missing"
STATE_NOT_PREPARED = "State not in prepared list or config_generated is false: status={status}, config_generated={config_generated}"
READ_STATE_FILE_FAILED = "Failed to read state file: {error}"

# Simulation creation
GRAPH_NOT_BUILT = "The project graph has not been built yet, please call /api/graph/build first"

# Entity management
ENTITY_NOT_FOUND = "Entity not found: {entity_uuid}"

# Simulation preparation
ALREADY_PREPARED_MESSAGE = "Preparation already completed, no need to regenerate"
MISSING_SIMULATION_REQUIREMENT_PROJECT = "The project does not have a simulation requirement description (simulation_requirement)"
PREPARE_TASK_STARTED = "Preparation task started, check status via /api/simulation/prepare/status"

# Prepare status
ALREADY_PREPARED_STATUS = "Preparation already completed"
NOT_STARTED_MESSAGE = "Preparation not yet started, call /api/simulation/prepare to begin"
TASK_COMPLETED_ALREADY_PREPARED = "Task completed (preparation already exists)"

# Simulation config
SIMULATION_CONFIG_NOT_FOUND = "Simulation configuration not found, please call the /prepare interface first"
CONFIG_FILE_NOT_FOUND = "Configuration file not found, please call the /prepare interface first"

# Simulation scripts
UNKNOWN_SCRIPT = "Unknown script: {script_name}, available options: {allowed_scripts}"
SCRIPT_FILE_NOT_FOUND = "Script file not found: {script_name}"

# Profile generation
NO_MATCHING_ENTITIES = "No entities matching the criteria were found"

# Simulation running
MAX_ROUNDS_MUST_BE_POSITIVE = "max_rounds must be a positive integer"
MAX_ROUNDS_MUST_BE_INTEGER = "max_rounds must be a valid integer"
INVALID_PLATFORM_TYPE = "Invalid platform type: {platform}, options: twitter/reddit/parallel"
SIMULATION_RUNNING_STOP_FIRST = "Simulation is running, please call /stop first, or use force=true to force restart"
SIMULATION_NOT_READY = "Simulation not ready, current status: {status}, please call the /prepare interface first"
GRAPH_MEMORY_UPDATE_REQUIRES_GRAPH_ID = "Graph memory update requires a valid graph_id, make sure you have built the graph"

# Database messages
DB_NOT_EXISTS_MESSAGE = "Database does not exist, the simulation may not have been run yet"

# Interview
PROVIDE_AGENT_ID = "Please provide agent_id"
PROVIDE_PROMPT = "Please provide prompt (interview question)"
PLATFORM_INVALID = "The platform parameter can only be 'twitter' or 'reddit'"
SIMULATION_ENV_NOT_RUNNING = "The simulation environment is not running or has been closed. Make sure the simulation is completed and in command-waiting mode."
INTERVIEW_TIMEOUT = "Timeout waiting for interview response: {error}"

# Interview batch
PROVIDE_INTERVIEWS_LIST = "Please provide interviews (interview list)"
INTERVIEW_ITEM_MISSING_AGENT_ID = "Interview list item {index} is missing agent_id"
INTERVIEW_ITEM_MISSING_PROMPT = "Interview list item {index} is missing prompt"
INTERVIEW_ITEM_INVALID_PLATFORM = "Interview list item {index} platform can only be 'twitter' or 'reddit'"
BATCH_INTERVIEW_TIMEOUT = "Timeout waiting for batch interview responses: {error}"

# Interview all
GLOBAL_INTERVIEW_TIMEOUT = "Timeout waiting for global interview responses: {error}"

# Environment status
ENV_RUNNING_MESSAGE = "Environment running, ready to receive interview commands"
ENV_NOT_RUNNING_MESSAGE = "Environment not running or closed"

# Close environment
CLOSE_ENV_COMMAND_SENT = "Environment close command sent"

# Task progress messages (used in background tasks)
INIT_GRAPH_BUILD_SERVICE = "Initializing graph construction service..."
TEXT_CHUNKING = "Splitting text into chunks..."
CREATING_ZEP_GRAPH = "Creating Zep graph..."
SETTING_ONTOLOGY = "Setting ontology definition..."
ADDING_TEXT_CHUNKS = "Starting to add {total_chunks} text chunks..."
WAITING_ZEP_PROCESSING = "Waiting for Zep to process data..."
FETCHING_GRAPH_DATA = "Fetching graph data..."
INIT_REPORT_AGENT = "Initializing Report Agent..."
START_PREPARING_SIMULATION = "Starting simulation environment preparation..."
