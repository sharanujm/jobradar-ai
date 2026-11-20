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

    from .database import get_system_setting

    # Read email credentials from environment variables (.env), with database fallback
    sender_email = (os.getenv("SENDER_EMAIL") or get_system_setting("sender_email") or "sharanujm@gmail.com").strip()
    sender_password = (os.getenv("SENDER_APP_PASSWORD") or get_system_setting("sender_password") or "").strip()
    recipient_email = (os.getenv("RECIPIENT_EMAIL") or get_system_setting("recipient_email") or "").strip()
    smtp_host = (os.getenv("SMTP_HOST") or get_system_setting("smtp_host") or "smtp.gmail.com").strip()
    smtp_port_val = os.getenv("SMTP_PORT") or get_system_setting("smtp_port") or "465"
    use_ssl_val = os.getenv("USE_SSL") or get_system_setting("use_ssl") or "true"

    email_creds = {
        "sender_email": sender_email,
        "sender_password": sender_password,
        "recipient_email": recipient_email,
        "smtp_host": smtp_host,
        "smtp_port": int(smtp_port_val),
        "use_ssl": str(use_ssl_val).lower() in ("true", "1", "yes")
    }

    config["email"] = email_creds
    return config

if __name__ == "__main__":
    cfg = load_config()
    print("Config loaded successfully!")
    print("Roles:", cfg.get("search", {}).get("roles"))
    print("Recipient:", cfg.get("email", {}).get("recipient_email"))
