"""
Italian (it) API messages for MiroFish backend.
All user-facing messages from graph.py, report.py, and simulation.py API routes.
"""

# ============== graph.py ==============

# Project management
PROJECT_NOT_FOUND = "Progetto non trovato: {project_id}"
PROJECT_NOT_FOUND_OR_DELETE_FAILED = "Progetto non trovato o eliminazione fallita: {project_id}"
PROJECT_DELETED = "Progetto eliminato: {project_id}"
PROJECT_RESET = "Progetto reimpostato: {project_id}"

# Ontology generation
PROVIDE_SIMULATION_REQUIREMENT = "Fornire la descrizione del requisito di simulazione (simulation_requirement)"
UPLOAD_AT_LEAST_ONE_FILE = "Caricare almeno un file documento"
NO_DOCUMENTS_PROCESSED = "Nessun documento elaborato con successo, verificare il formato dei file"

# Graph building
CONFIG_ERROR = "Errore di configurazione: {errors}"
PROVIDE_PROJECT_ID = "Fornire project_id"
ONTOLOGY_NOT_GENERATED = "L'ontologia del progetto non e stata ancora generata, chiamare prima /ontology/generate"
GRAPH_BUILDING_IN_PROGRESS = "Costruzione del grafo in corso, non inviare richieste duplicate. Per forzare la ricostruzione, aggiungere force: true"
EXTRACTED_TEXT_NOT_FOUND = "Contenuto testuale estratto non trovato"
ONTOLOGY_NOT_FOUND = "Definizione dell'ontologia non trovata"
GRAPH_BUILD_TASK_STARTED = "Attivita di costruzione del grafo avviata, consultare lo stato tramite /task/{task_id}"
GRAPH_BUILD_COMPLETED = "Costruzione del grafo completata"
GRAPH_BUILD_FAILED = "Costruzione fallita: {error}"

# Task management
TASK_NOT_FOUND = "Attivita non trovata: {task_id}"

# Graph data
ZEP_API_KEY_NOT_CONFIGURED = "ZEP_API_KEY non configurata"
GRAPH_DELETED = "Grafo eliminato: {graph_id}"

# ============== report.py ==============

# Report generation
PROVIDE_SIMULATION_ID = "Fornire simulation_id"
SIMULATION_NOT_FOUND = "Simulazione non trovata: {simulation_id}"
REPORT_ALREADY_EXISTS = "Il report esiste gia"
MISSING_GRAPH_ID = "ID del grafo mancante, assicurarsi di aver costruito il grafo"
MISSING_SIMULATION_REQUIREMENT = "Descrizione del requisito di simulazione mancante"
REPORT_GENERATE_TASK_STARTED = "Attivita di generazione del report avviata, consultare lo stato tramite /api/report/generate/status"
REPORT_GENERATION_FAILED = "Generazione del report fallita"

# Report generation status
REPORT_ALREADY_GENERATED = "Report gia generato"
PROVIDE_TASK_ID_OR_SIMULATION_ID = "Fornire task_id o simulation_id"

# Report retrieval
REPORT_NOT_FOUND = "Report non trovato: {report_id}"
NO_REPORT_FOR_SIMULATION = "Nessun report disponibile per questa simulazione: {simulation_id}"

# Report management
REPORT_DELETED = "Report eliminato: {report_id}"

# Report progress
REPORT_NOT_FOUND_OR_PROGRESS_UNAVAILABLE = "Report non trovato o informazioni sullo stato non disponibili: {report_id}"

# Report sections
SECTION_NOT_FOUND = "Sezione non trovata: section_{section_index:02d}.md"

# Report tools
PROVIDE_GRAPH_ID_AND_QUERY = "Fornire graph_id e query"
PROVIDE_GRAPH_ID = "Fornire graph_id"

# Report chat
PROVIDE_MESSAGE = "Fornire message"
MISSING_GRAPH_ID_SHORT = "ID del grafo mancante"

# ============== simulation.py ==============

# Simulation directory check
SIMULATION_DIR_NOT_FOUND = "Directory della simulazione non trovata"
MISSING_REQUIRED_FILES = "File necessari mancanti"
STATE_NOT_PREPARED = "Stato non nella lista preparata o config_generated e false: status={status}, config_generated={config_generated}"
READ_STATE_FILE_FAILED = "Lettura del file di stato fallita: {error}"

# Simulation creation
GRAPH_NOT_BUILT = "Il grafo del progetto non e stato ancora costruito, chiamare prima /api/graph/build"

# Entity management
ENTITY_NOT_FOUND = "Entita non trovata: {entity_uuid}"

# Simulation preparation
ALREADY_PREPARED_MESSAGE = "Preparazione gia completata, non e necessario rigenerare"
MISSING_SIMULATION_REQUIREMENT_PROJECT = "Il progetto non ha una descrizione del requisito di simulazione (simulation_requirement)"
PREPARE_TASK_STARTED = "Attivita di preparazione avviata, consultare lo stato tramite /api/simulation/prepare/status"

# Prepare status
ALREADY_PREPARED_STATUS = "Preparazione gia completata"
NOT_STARTED_MESSAGE = "Preparazione non ancora iniziata, chiamare /api/simulation/prepare per avviare"
TASK_COMPLETED_ALREADY_PREPARED = "Attivita completata (la preparazione esiste gia)"

# Simulation config
SIMULATION_CONFIG_NOT_FOUND = "Configurazione della simulazione non trovata, chiamare prima l'interfaccia /prepare"
CONFIG_FILE_NOT_FOUND = "File di configurazione non trovato, chiamare prima l'interfaccia /prepare"

# Simulation scripts
UNKNOWN_SCRIPT = "Script sconosciuto: {script_name}, opzioni disponibili: {allowed_scripts}"
SCRIPT_FILE_NOT_FOUND = "File dello script non trovato: {script_name}"

# Profile generation
NO_MATCHING_ENTITIES = "Nessuna entita corrispondente ai criteri trovata"

# Simulation running
MAX_ROUNDS_MUST_BE_POSITIVE = "max_rounds deve essere un intero positivo"
MAX_ROUNDS_MUST_BE_INTEGER = "max_rounds deve essere un intero valido"
INVALID_PLATFORM_TYPE = "Tipo di piattaforma non valido: {platform}, opzioni: twitter/reddit/parallel"
SIMULATION_RUNNING_STOP_FIRST = "Simulazione in esecuzione, chiamare prima /stop per fermarla, oppure usare force=true per forzare il riavvio"
SIMULATION_NOT_READY = "Simulazione non pronta, stato attuale: {status}, chiamare prima l'interfaccia /prepare"
GRAPH_MEMORY_UPDATE_REQUIRES_GRAPH_ID = "L'aggiornamento della memoria del grafo richiede un graph_id valido, assicurarsi di aver costruito il grafo"

# Database messages
DB_NOT_EXISTS_MESSAGE = "Database non esistente, la simulazione potrebbe non essere stata ancora eseguita"

# Interview
PROVIDE_AGENT_ID = "Fornire agent_id"
PROVIDE_PROMPT = "Fornire prompt (domanda dell'intervista)"
PLATFORM_INVALID = "Il parametro platform puo essere solo 'twitter' o 'reddit'"
SIMULATION_ENV_NOT_RUNNING = "L'ambiente di simulazione non e in esecuzione o e stato chiuso. Assicurarsi che la simulazione sia completata e in modalita di attesa comandi."
INTERVIEW_TIMEOUT = "Timeout in attesa della risposta dell'intervista: {error}"

# Interview batch
PROVIDE_INTERVIEWS_LIST = "Fornire interviews (lista delle interviste)"
INTERVIEW_ITEM_MISSING_AGENT_ID = "L'elemento {index} della lista interviste non ha agent_id"
INTERVIEW_ITEM_MISSING_PROMPT = "L'elemento {index} della lista interviste non ha prompt"
INTERVIEW_ITEM_INVALID_PLATFORM = "Il platform dell'elemento {index} della lista interviste puo essere solo 'twitter' o 'reddit'"
BATCH_INTERVIEW_TIMEOUT = "Timeout in attesa delle risposte delle interviste batch: {error}"

# Interview all
GLOBAL_INTERVIEW_TIMEOUT = "Timeout in attesa delle risposte dell'intervista globale: {error}"

# Environment status
ENV_RUNNING_MESSAGE = "Ambiente in esecuzione, pronto a ricevere comandi di intervista"
ENV_NOT_RUNNING_MESSAGE = "Ambiente non in esecuzione o chiuso"

# Close environment
CLOSE_ENV_COMMAND_SENT = "Comando di chiusura dell'ambiente inviato"

# Task progress messages (used in background tasks)
INIT_GRAPH_BUILD_SERVICE = "Inizializzazione del servizio di costruzione del grafo..."
TEXT_CHUNKING = "Suddivisione del testo in blocchi..."
CREATING_ZEP_GRAPH = "Creazione del grafo Zep..."
SETTING_ONTOLOGY = "Configurazione della definizione dell'ontologia..."
ADDING_TEXT_CHUNKS = "Inizio aggiunta di {total_chunks} blocchi di testo..."
WAITING_ZEP_PROCESSING = "In attesa dell'elaborazione dei dati da parte di Zep..."
FETCHING_GRAPH_DATA = "Recupero dei dati del grafo..."
INIT_REPORT_AGENT = "Inizializzazione del Report Agent..."
START_PREPARING_SIMULATION = "Inizio preparazione dell'ambiente di simulazione..."
