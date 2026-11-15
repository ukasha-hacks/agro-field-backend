import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_VERSION = "0.3.1"
METHODS_VERSION = "1.2.1"
DEFAULT_CORS_ORIGINS = (
    "https://agrofields.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
)


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    rules_file: Path
    cors_origins: tuple[str, ...]
    environment: str = "development"

    @classmethod
    def from_environment(cls):
        data_dir = os.getenv("DATA_DIR", str(ROOT / "data/Field_Shift_Relevant_Data"))
        origins = os.getenv("CORS_ORIGINS", ",".join(DEFAULT_CORS_ORIGINS))
        return cls(
            data_dir=Path(data_dir).resolve(),
            rules_file=ROOT / "config/rotation_rules.json",
            cors_origins=tuple(
                item.strip().rstrip("/") for item in origins.split(",") if item.strip()
            ),
            environment=os.getenv("APP_ENV", "development"),
        )
