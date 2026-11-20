import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(dotenv_path=BASE_DIR / ".env")

def load_config(config_path: str = None) -> dict:
    """Load configuration from config.yaml with environment fallback."""
    if config_path is None:
        config_path = BASE_DIR / "config.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found at {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    # Read email credentials from environment variables (.env)
    email_creds = {
        "sender_email": os.getenv("SENDER_EMAIL", "").strip(),
        "sender_password": os.getenv("SENDER_APP_PASSWORD", "").strip(),
        "recipient_email": os.getenv("RECIPIENT_EMAIL", "").strip(),
        "smtp_host": os.getenv("SMTP_HOST", "smtp.gmail.com").strip(),
        "smtp_port": int(os.getenv("SMTP_PORT", "465")),
        "use_ssl": os.getenv("USE_SSL", "true").lower() in ("true", "1", "yes")
    }

    config["email"] = email_creds
    return config

if __name__ == "__main__":
    cfg = load_config()
    print("Config loaded successfully!")
    print("Roles:", cfg.get("search", {}).get("roles"))
    print("Recipient:", cfg.get("email", {}).get("recipient_email"))
