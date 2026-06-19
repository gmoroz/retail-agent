"""Domain constants for the retail agent.

Pure data: table allowlist, PII columns, the read-only SQL deny-list, model slugs
and reference prices. Imports nothing from the application, so it can be imported
anywhere without side effects.

SQL table validation is a subset rule: every referenced table must be in
``ALLOWED_TABLES``. PII masking is column-aware for known ``users`` identity and
precise-location fields and has no generic phone regex because the audited thelook
schema has no phone column. The SQL deny-list is stored as sqlglot expression-type
names so this module stays independent from parser imports.
"""

from pydantic import BaseModel, ConfigDict

THELOOK_PROJECT = "bigquery-public-data"
THELOOK_DATASET = "thelook_ecommerce"

THELOOK_TABLES: tuple[str, ...] = (
    "orders",
    "order_items",
    "products",
    "users",
)

ALLOWED_TABLES: frozenset[str] = frozenset(
    {f"{THELOOK_DATASET}.{table}" for table in THELOOK_TABLES}
    | {f"{THELOOK_PROJECT}.{THELOOK_DATASET}.{table}" for table in THELOOK_TABLES}
)

PII_COLUMNS: dict[str, frozenset[str]] = {
    "users": frozenset(
        {
            "email",
            "first_name",
            "last_name",
            "latitude",
            "longitude",
            "postal_code",
            "street_address",
            "user_geom",
        }
    ),
}

PII_COLUMN_NAMES: frozenset[str] = frozenset().union(*PII_COLUMNS.values())

READONLY_SQL_DENYLIST: frozenset[str] = frozenset(
    {
        "Insert",
        "Update",
        "Delete",
        "Merge",
        "Create",
        "Drop",
        "Alter",
        "TruncateTable",
    }
)

EMBEDDING_MODEL = "baai/bge-m3"
EMBEDDING_DIMENSION = 1024
EMBEDDING_MAX_RETRIES = 3
EMBEDDING_REQUEST_TIMEOUT_SEC = 30.0

MAX_SELF_CORRECT_ITERATIONS = 3
MAX_BIGQUERY_BYTES_BILLED = 1_073_741_824
MAX_RESULT_ROWS = 1_000
BIGQUERY_JOB_TIMEOUT_MS = 60_000
RETRIEVAL_TOP_K = 3
LLM_MAX_RETRIES = 3
LLM_REQUEST_TIMEOUT_SEC = 60.0

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
PINNED_DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
QUALITY_BAND_EPSILON = 0.05
# The deployed default serves interactive CLI requests; 95s qwen latency is too slow,
# while 45s keeps deepseek/glm/kimi eligible.
MAX_DEFAULT_LATENCY_SEC = 45.0

AB_MODELS: tuple[str, ...] = (
    PINNED_DEFAULT_MODEL,
    "qwen/qwen3.7-plus",
    "moonshotai/kimi-k2",
    "z-ai/glm-5.2",
)

JUDGE_MODEL = "google/gemini-3.5-flash"


class ModelPricing(BaseModel):
    """Reference price for display only ($ per 1M tokens).

    Actual charged cost is read from the OpenRouter ``usage`` response (PR-006);
    this table only renders reference prices in the eval report and HLD.
    """

    model_config = ConfigDict(frozen=True)

    input_per_million: float
    output_per_million: float


MODEL_PRICING: dict[str, ModelPricing] = {
    "deepseek/deepseek-v4-flash": ModelPricing(input_per_million=0.09, output_per_million=0.18),
    "qwen/qwen3.7-plus": ModelPricing(input_per_million=0.32, output_per_million=1.28),
    "moonshotai/kimi-k2": ModelPricing(input_per_million=0.57, output_per_million=2.30),
    "z-ai/glm-5.2": ModelPricing(input_per_million=1.40, output_per_million=4.40),
    JUDGE_MODEL: ModelPricing(input_per_million=1.50, output_per_million=9.00),
}
