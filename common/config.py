# -*- coding: utf-8 -*-
"""
Konfigurasi bersama: pemuatan .env dan resolusi broker MQTT.

Urutan prioritas nilai: argumen CLI > variabel lingkungan / .env > default.
Jika MQTT_BROKER tidak di-set, dipakai broker publik (khusus uji coba).
"""

import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MQTT_DIR = os.path.join(ROOT_DIR, "MQTT")
DEFAULT_LOG_DIR = os.path.join(ROOT_DIR, "logs")

PUBLIC_BROKER = "broker.hivemq.com"
PUBLIC_PORT = 1883
DEFAULT_TOPIC = "sister/temp"


def load_dotenv(path=None):
    """Muat KEY=VALUE dari file .env tanpa menimpa variabel yang sudah ada."""
    path = path or os.path.join(MQTT_DIR, ".env")
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key.strip(), value)
    return True


def _as_bool(value, default=False):
    if value is None or value == "":
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "y", "on")


def mqtt_settings():
    """Kembalikan dict konfigurasi broker dari .env (atau fallback publik)."""
    load_dotenv()
    broker = os.environ.get("MQTT_BROKER", "").strip()
    if broker:
        port = int(os.environ.get("MQTT_PORT") or 8883)
        tls = _as_bool(os.environ.get("MQTT_TLS"), default=True)
        source = ".env"
    else:
        broker, port, tls, source = PUBLIC_BROKER, PUBLIC_PORT, False, "fallback publik"

    ca_cert = os.environ.get("MQTT_CA_CERT", "").strip() or None
    if ca_cert and not os.path.isabs(ca_cert):
        ca_cert = os.path.join(MQTT_DIR, ca_cert)

    return {
        "broker": broker,
        "port": port,
        "tls": tls,
        "ca_cert": ca_cert,
        "username": os.environ.get("MQTT_USERNAME") or None,
        "password": os.environ.get("MQTT_PASSWORD") or None,
        "topic": os.environ.get("MQTT_TOPIC") or DEFAULT_TOPIC,
        "source": source,
    }


def add_mqtt_args(parser):
    """Tambahkan argumen koneksi broker standar ke argparse parser."""
    s = mqtt_settings()
    g = parser.add_argument_group("koneksi broker (default dari MQTT/.env, sumber: %s)" % s["source"])
    g.add_argument("--broker", default=s["broker"], help="Host broker MQTT")
    g.add_argument("--port", type=int, default=s["port"], help="Port broker MQTT")
    g.add_argument("--tls", dest="tls", action="store_true", default=s["tls"], help="Aktifkan TLS")
    g.add_argument("--no-tls", dest="tls", action="store_false", help="Nonaktifkan TLS")
    g.add_argument("--ca-cert", default=s["ca_cert"], help="Path file CA (opsional)")
    g.add_argument("--username", default=s["username"], help="Username broker")
    g.add_argument("--password", default=s["password"], help="Password broker")
    g.add_argument("--topic", default=s["topic"], help="Topik MQTT")
    return parser


def apply_mqtt_connection(client, args):
    """Terapkan kredensial & TLS dari args ke paho client."""
    if args.username:
        client.username_pw_set(args.username, args.password)
    if args.tls:
        if args.ca_cert and not os.path.exists(args.ca_cert):
            raise FileNotFoundError("File CA tidak ditemukan: %s" % args.ca_cert)
        client.tls_set(ca_certs=args.ca_cert)
    client.reconnect_delay_set(min_delay=1, max_delay=5)
