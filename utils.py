"""
Вспомогательные утилиты.
"""

import uuid
from datetime import datetime
from urllib.parse import quote


def generate_uuid() -> str:
    """Сгенерировать новый UUID v4."""
    return str(uuid.uuid4())


def format_date(dt) -> str:
    """Привести дату к формату ДД.ММ.ГГГГ."""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    return dt.strftime("%d.%m.%Y")


def build_vless_link(
    uuid_str: str,
    ip: str,
    port: int,
    host: str,
    path: str,
) -> str:
    """Сформировать VLESS-ссылку для подключения."""
    enc_path = quote(path, safe="")
    return (
        f"vless://{uuid_str}@{ip}:{port}"
        f"?type=tcp&security=tls&sni={host}&host={host}&path={enc_path}"
        f"#VPN-SWAGA"
    )
