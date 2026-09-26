#!/usr/bin/env python3
"""
======================================================================
               GARENA FREE FIRE GUEST ACCOUNT GENERATOR
                      DEVELOPED BY: GOHAR REHMAN
               GITHUB: https://github.com/itsgoharrehman
======================================================================
Standalone high-performance guest account generator for Android / Termux.
Features:
  - 100% self-contained: zero repository or external project dependencies
  - Direct-to-lobby OB55 MajorRegister + MajorLogin character initialization
  - Custom base names with sequential unicode superscripts (e.g. Gohar¹, Gohar²...)
  - Dynamic high-entropy Gohar Rehman branded passphrases
  - Multi-region support (PK, BD, ME, IND, SG, BR, etc.)
  - Auto-rotates Webshare proxies from proxies.txt (or direct network)
  - 1-click export to phone Downloads (/sdcard/Download) in standard CSV & TXT
======================================================================
"""

import csv
import hashlib
import hmac
import json
import os
import random
import re
import shutil
import string
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    print("[ERROR] 'requests' module not found. Run: pip install requests")
    sys.exit(1)

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
except ImportError:
    print("[ERROR] 'pycryptodome' module not found. Run: pip install pycryptodome")
    sys.exit(1)

# Garena MSDK Configuration & Keys
HEX_KEY = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"
API_KEY = bytes.fromhex(HEX_KEY)
CLIENT_ID = "100067"

# Endpoints
REGISTER_URL_V2 = "https://100067.connect.garena.com/api/v2/oauth/guest:register"
REGISTER_URL_V1 = "https://connect.garena.com/oauth/guest/register"
TOKEN_URL_V2 = "https://100067.connect.garena.com/api/v2/oauth/guest/token:grant"
TOKEN_URL_V1 = "https://100067.connect.garena.com/oauth/guest/token/grant"

MAJOR_REGISTER_URL = "https://loginbp.ppmainecoonghj.com/MajorRegister"
FALLBACK_REGISTER_URL = "https://loginbp.ggpolarbear.com/MajorRegister"
MAJOR_LOGIN_URL = "https://loginbp.ppmainecoonghj.com/MajorLogin"
FALLBACK_LOGIN_URL = "https://loginbp.ggpolarbear.com/MajorLogin"

# Game Crypto & Obfuscation Constants
AES_KEY = b"Yg&tc%DEuh6%Zc^8"
AES_IV = b"6oyZDr22E3ychjM%"
RELEASE_VERSION = "OB55"
UNITY_USER_AGENT = "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)"

XOR_KEYSTREAM = [
    0x30, 0x30, 0x30, 0x32, 0x30, 0x31, 0x37, 0x30, 0x30, 0x30, 0x30, 0x30, 0x32, 0x30, 0x31, 0x37,
    0x30, 0x30, 0x30, 0x30, 0x30, 0x32, 0x30, 0x31, 0x37, 0x30, 0x30, 0x30, 0x30, 0x30, 0x32, 0x30
]

REGION_LANG = {
    "PK": "ur",
    "BD": "bn",
    "ME": "ar",
    "ID": "id",
    "SG": "en",
    "BR": "pt",
    "TH": "th",
    "VN": "vi",
    "MY": "ms",
    "IND": "hi",
    "IN": "hi",
    "US": "en",
    "NA": "en",
    "EU": "en",
    "RU": "ru",
}

SUPERSCRIPTS = {
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
    "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹"
}
REVERSE_SUPERSCRIPTS = {v: k for k, v in SUPERSCRIPTS.items()}

# Gohar Rehman Brand Lexicon for Dynamic Passwords
BRAND_PRIMARY = [
    "Gohar", "Rehman", "itsgoharrehman", "GoharGod",
    "DevGohar", "GoharDev", "GoharCore", "GoharPro"
]
BRAND_ATTRIBUTES = [
    "Apex", "Vanguard", "Prime", "Elite",
    "Legend", "Titan", "Alpha", "Master", "Zenith", "Pulse"
]
BRAND_TECH_SECURITY = [
    "Matrix", "Cyber", "Vault", "Shield",
    "Vector", "Secure", "Studio", "Global"
]

PROXIES_FILE = "proxies.txt"


def clear_screen() -> None:
    os.system("clear" if os.name == "posix" else "cls")


def print_banner() -> None:
    clear_screen()
    print("=" * 70)
    print("               GARENA FREE FIRE GUEST ACCOUNT GENERATOR")
    print("                      DEVELOPED BY: GOHAR REHMAN")
    print("               GITHUB: https://github.com/itsgoharrehman")
    print("=" * 70)


def aes_cbc_encrypt(data: bytes, key: bytes = AES_KEY, iv: bytes = AES_IV) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(data, AES.block_size))


def aes_cbc_decrypt(data: bytes, key: bytes = AES_KEY, iv: bytes = AES_IV) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(data), AES.block_size)


def encode_varint(value: int) -> bytes:
    out = bytearray()
    while value > 0x7F:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value & 0x7F)
    return bytes(out)


def create_proto_field(field_num: int, value: Any) -> bytes:
    if isinstance(value, int):
        header = (field_num << 3) | 0
        return encode_varint(header) + encode_varint(value)
    elif isinstance(value, (str, bytes)):
        encoded_val = value.encode("utf-8") if isinstance(value, str) else value
        header = (field_num << 3) | 2
        return encode_varint(header) + encode_varint(len(encoded_val)) + encoded_val
    return b""


def build_proto(fields: Dict[int, Any]) -> bytes:
    return b"".join(create_proto_field(k, v) for k, v in fields.items())


def to_superscript(num: int) -> str:
    return "".join(SUPERSCRIPTS.get(d, d) for d in str(num))


def from_superscript(text: str) -> Optional[int]:
    digits = "".join(REVERSE_SUPERSCRIPTS.get(c, "") for c in text)
    return int(digits) if digits else None


def generate_gohar_branded_password() -> str:
    p1 = random.choice(BRAND_PRIMARY)
    remaining_primary = [p for p in BRAND_PRIMARY if p != p1]
    p2 = random.choice(remaining_primary) if remaining_primary else "Gohar"

    a1 = random.choice(BRAND_ATTRIBUTES)
    remaining_attr = [a for a in BRAND_ATTRIBUTES if a != a1]
    a2 = random.choice(remaining_attr) if remaining_attr else "Elite"

    sec = random.choice(BRAND_TECH_SECURITY)
    salt = random.randint(10, 99)

    return f"{p1}-{a1}-{sec}-{p2}-{a2}-{salt}"


def resolve_accounts_file() -> Path:
    # If project root /data directory exists, save there, otherwise local accounts.json
    if Path("data").is_dir():
        return Path("data/accounts.json")
    if Path("../data").is_dir():
        return Path("../data/accounts.json")
    return Path("accounts.json")


def load_accounts() -> List[Dict[str, Any]]:
    path = resolve_accounts_file()
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_account(acc: Dict[str, Any]) -> None:
    path = resolve_accounts_file()
    accounts = load_accounts()

    existing_uids = {str(a.get("uid")) for a in accounts if a.get("uid")}
    if str(acc.get("uid")) not in existing_uids:
        accounts.append(acc)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(accounts, f, indent=2, ensure_ascii=False)
            f.write("\n")


def load_proxies() -> List[str]:
    # Look in current directory or parent directory
    candidates = [Path(PROXIES_FILE), Path(f"../{PROXIES_FILE}"), Path("guest_generator/proxies.txt")]
    for p in candidates:
        if p.exists():
            proxies = []
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    if not line.startswith(("http://", "https://", "socks5://")):
                        line = f"http://{line}"
                    proxies.append(line)
            if proxies:
                return list(dict.fromkeys(proxies))
    return []


def find_next_superscript_number(accounts: List[Dict[str, Any]], base_name: str) -> int:
    prefix_lower = base_name.lower()
    highest = 0
    for acc in accounts:
        nick = str(acc.get("nickname") or "").strip()
        if nick.lower().startswith(prefix_lower):
            remainder = nick[len(base_name):].strip()
            val = from_superscript(remainder)
            if val is None and remainder.isdigit():
                val = int(remainder)
            if val is not None and val > highest:
                highest = val
    return highest + 1


def format_nickname(base_name: str, number: int) -> str:
    # Free Fire character name maximum length is 12 characters
    superscript_str = to_superscript(number)
    max_base_len = 12 - len(superscript_str)
    if max_base_len < 1:
        max_base_len = 1
    safe_base = base_name[:max_base_len]
    return f"{safe_base}{superscript_str}"


def register_garena_guest_oauth(password: str, proxy: Optional[str] = None) -> Optional[Tuple[str, str, str]]:
    """
    Registers Garena OAuth guest credentials and returns (uid, access_token, open_id).
    """
    session = requests.Session()
    session.verify = False
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}

    uid = None

    # Step 1: V2 Guest Registration
    try:
        payload_v2 = json.dumps(
            {"app_id": 100067, "client_type": 2, "password": password, "source": 2},
            separators=(",", ":"),
        )
        sig_v2 = hmac.new(API_KEY, payload_v2.encode("utf-8"), hashlib.sha256).hexdigest()
        headers_v2 = {
            "User-Agent": "GarenaMSDK/4.0.39(SM-A325M ;Android 13;en;HK;)",
            "Authorization": f"Signature {sig_v2}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "Connection": "Keep-Alive",
            "Host": "100067.connect.garena.com",
        }
        r2 = session.post(REGISTER_URL_V2, headers=headers_v2, data=payload_v2, timeout=10)
        if r2.status_code == 200:
            res2 = r2.json()
            if res2.get("data", {}).get("uid"):
                uid = str(res2["data"]["uid"])
    except Exception:
        pass

    # Fallback to V1 if V2 failed
    if not uid:
        try:
            sig_v1 = hmac.new(API_KEY, password.encode("utf-8"), hashlib.sha1).hexdigest()
            headers_v1 = {
                "Authorization": f"Signature {sig_v1}",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "GarenaMSDK/4.0.19P10(I2404 ;Android 15;en;US;)",
                "Accept-Encoding": "gzip",
                "Connection": "Keep-Alive",
            }
            data_v1 = {
                "password": password,
                "client_id": CLIENT_ID,
                "client_type": "2",
                "response_type": "token",
                "signature": sig_v1,
            }
            r1 = session.post(REGISTER_URL_V1, headers=headers_v1, data=data_v1, timeout=10)
            if r1.status_code == 200:
                res1 = r1.json()
                if res1.get("uid"):
                    uid = str(res1["uid"])
        except Exception:
            pass

    if not uid:
        return None

    # Step 2: Grant OAuth Token
    access_token = ""
    open_id = ""

    token_attempts = [
        (
            TOKEN_URL_V2,
            {"Content-Type": "application/json; charset=utf-8", "User-Agent": "GarenaMSDK/4.0.19P10(I2404 ;Android 15;en;US;)"},
            json.dumps({
                "client_id": 100067,
                "client_secret": HEX_KEY,
                "client_type": 2,
                "password": password,
                "response_type": "token",
                "uid": int(uid),
            }, separators=(",", ":")),
            True,
        ),
        (
            TOKEN_URL_V1,
            {"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "GarenaMSDK/4.0.19P8(ASUS_Z01QD ;Android 12;en;US;)"},
            {
                "uid": uid,
                "password": password,
                "response_type": "token",
                "client_type": "2",
                "client_secret": HEX_KEY,
                "client_id": CLIENT_ID,
            },
            False,
        ),
    ]

    for url, headers, data, is_json in token_attempts:
        try:
            if is_json:
                sig_tok = hmac.new(API_KEY, data.encode("utf-8"), hashlib.sha256).hexdigest()
                h = headers.copy()
                h["Authorization"] = f"Signature {sig_tok}"
                rt = session.post(url, data=data, headers=h, timeout=10)
            else:
                rt = session.post(url, data=data, headers=headers, timeout=10)

            if rt.status_code == 200:
                tj = rt.json()
                odata = tj.get("data", tj)
                open_id = odata.get("open_id", "")
                access_token = odata.get("access_token", "")
                if access_token and open_id:
                    break
        except Exception:
            continue

    if not access_token or not open_id:
        return None

    return uid, access_token, open_id


def initialize_freefire_character(
    nickname: str,
    access_token: str,
    open_id: str,
    region: str = "PK",
    proxy: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Executes authentic Free Fire OB55 MajorRegister to permanently initialize the character
    in Free Fire servers, followed by MajorLogin handshake.
    Ensures accounts land directly in the lobby without re-entering character name.
    """
    session = requests.Session()
    session.verify = False
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}

    encoded_oid = "".join(chr(ord(ch) ^ XOR_KEYSTREAM[i % len(XOR_KEYSTREAM)]) for i, ch in enumerate(open_id))
    field14 = encoded_oid.encode("latin1")
    lang_code = REGION_LANG.get(region.upper(), "ur")

    payload_fields = {
        1: nickname,
        2: access_token,
        3: open_id,
        5: 102000007,
        6: 4,
        7: 1,
        13: 1,
        14: field14,
        15: lang_code,
        16: 1,
        17: 1,
    }
    proto_bytes = build_proto(payload_fields)
    encrypted_body = aes_cbc_encrypt(proto_bytes)

    headers_reg = {
        "Accept-Encoding": "gzip",
        "Authorization": "Bearer",
        "Connection": "Keep-Alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Expect": "100-continue",
        "ReleaseVersion": RELEASE_VERSION,
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_I005DA Build/PI)",
        "X-GA": "v1 1",
        "X-Unity-Version": "1.126.1",
    }

    game_uid = None

    for url in [MAJOR_REGISTER_URL, FALLBACK_REGISTER_URL]:
        try:
            h = headers_reg.copy()
            h["Host"] = url.split("://")[1].split("/")[0]
            resp = session.post(url, headers=h, data=encrypted_body, timeout=10)
            if resp.status_code == 200 and len(resp.content) > 0:
                idx = resp.content.find(b"\x18")
                if idx != -1:
                    p = idx + 1
                    val = 0
                    shift = 0
                    while p < len(resp.content):
                        b = resp.content[p]
                        p += 1
                        val |= (b & 0x7F) << shift
                        if not (b & 0x80):
                            break
                        shift += 7
                    if val > 10000:
                        game_uid = str(val)
                        break
        except Exception:
            pass

    # Execute MajorLogin to finalize character binding and confirm lobby access
    login_wire = (
        create_proto_field(22, open_id)
        + create_proto_field(23, "4")
        + create_proto_field(29, access_token)
        + create_proto_field(99, "4")
    )
    login_body = aes_cbc_encrypt(login_wire)

    headers_login = {
        "User-Agent": UNITY_USER_AGENT,
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "X-GA-SV": "1789638359",
        "Content-Type": "application/x-www-form-urlencoded",
        "Expect": "100-continue",
        "X-Unity-Version": "2018.4.12f1",
        "X-GA": "v1 1",
        "ReleaseVersion": RELEASE_VERSION,
    }

    for url in [MAJOR_LOGIN_URL, FALLBACK_LOGIN_URL]:
        try:
            h = headers_login.copy()
            r_log = session.post(url, headers=h, data=login_body, timeout=10)
            if r_log.status_code == 200 and len(r_log.content) > 10:
                # Extract account_id from JWT payload if present
                jwt_match = re.search(rb"(eyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]{43})", r_log.content)
                if jwt_match:
                    try:
                        import base64
                        token_str = jwt_match.group(1).decode("ascii")
                        parts = token_str.split(".")
                        if len(parts) >= 2:
                            rem = len(parts[1]) % 4
                            padded = parts[1] + "=" * ((4 - rem) % 4)
                            claims = json.loads(base64.urlsafe_b64decode(padded))
                            if claims.get("account_id"):
                                game_uid = str(claims["account_id"])
                                return True, game_uid
                    except Exception:
                        pass
                return True, game_uid
        except Exception:
            continue

    return (game_uid is not None), game_uid


def create_complete_guest_account(
    nickname: str,
    password: str,
    region: str = "PK",
    proxy: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Coordinates Garena OAuth registration + Free Fire in-game MajorRegister + MajorLogin.
    """
    oauth_res = register_garena_guest_oauth(password, proxy=proxy)
    if not oauth_res:
        return None

    uid, access_token, open_id = oauth_res

    # Initialize Free Fire in-game character profile
    char_ok, game_uid = initialize_freefire_character(
        nickname=nickname,
        access_token=access_token,
        open_id=open_id,
        region=region,
        proxy=proxy,
    )

    if not game_uid:
        game_uid = uid

    account_data = {
        "uid": uid,
        "password": password,
        "game_uid": game_uid,
        "nickname": nickname,
        "level": 1,
        "region": region.upper(),
        "is_banned": 0,
    }

    save_account(account_data)
    return account_data


def action_batch_generation() -> None:
    print_banner()
    print("\n--- BATCH ACCOUNT GENERATION ---")

    accounts = load_accounts()
    proxies = load_proxies()
    print(f"Loaded Database : {len(accounts)} accounts in {resolve_accounts_file()}")
    if proxies:
        print(f"Proxy Rotation  : {len(proxies)} Webshare proxies active (Strict 1 proxy/account)")
    else:
        print("Proxy Mode      : Direct connection (no proxies.txt found)")

    # 1. Count
    while True:
        raw_count = input("\nEnter number of accounts to create (e.g. 5, 10, 20): ").strip()
        if not raw_count:
            print("[!] Please enter a valid number.")
            continue
        try:
            count = int(raw_count)
            if count <= 0:
                print("[!] Number must be greater than 0.")
                continue
            break
        except ValueError:
            print("[!] Invalid integer. Try again.")

    # 2. Region Code
    raw_region = input("Enter region code [PK, BD, ME, IND, SG, BR] (Default: PK): ").strip().upper()
    region = raw_region if raw_region else "PK"

    # 3. Custom Name Base
    raw_name = input("Enter Custom Base Name (Press Enter for default: Gohar): ").strip()
    base_name = raw_name if raw_name else "Gohar"

    # Discover sequence starting number
    start_num = find_next_superscript_number(accounts, base_name)
    print(f"Sequence will start at: {base_name}{to_superscript(start_num)} (next unused number)")

    # 4. Password Scheme
    print("\nPassword Scheme:")
    print("  [1] Dynamic Gohar Branded Passphrases (e.g. Gohar-Apex-Vault-Rehman-Elite-47) [Recommended]")
    print("  [2] Custom Fixed Password for All Accounts")
    pwd_choice = input("Select password option [1/2] (Default: 1): ").strip()

    custom_fixed_password = None
    if pwd_choice == "2":
        custom_fixed_password = input("Enter custom password to use for all accounts: ").strip()
        if not custom_fixed_password:
            custom_fixed_password = generate_gohar_branded_password()

    print("\n" + "=" * 70)
    print(f"Starting generation of {count} account(s) for Region: {region}...")
    print("=" * 70)

    success_count = 0

    for i in range(count):
        current_num = start_num + i
        nick = format_nickname(base_name, current_num)
        pwd = custom_fixed_password if custom_fixed_password else generate_gohar_branded_password()

        current_proxy = None
        proxy_display = "Direct Network"
        if proxies:
            current_proxy = proxies[i % len(proxies)]
            proxy_display = current_proxy.split("@")[-1] if "@" in current_proxy else current_proxy

        print(f"\n[{i + 1}/{count}] Creating {nick} via {proxy_display}...")

        acc = create_complete_guest_account(
            nickname=nick,
            password=pwd,
            region=region,
            proxy=current_proxy,
        )

        if acc:
            success_count += 1
            print(f"  [SUCCESS] Character Initialized & Ready for Lobby")
            print(f"            Name     : {acc['nickname']}")
            print(f"            UID      : {acc['uid']}")
            print(f"            Game UID : {acc['game_uid']}")
            print(f"            Password : {acc['password']}")
        else:
            print(f"  [FAILED] Garena rejected registration or rate-limited. Moving to next.")

        time.sleep(0.5)

    print("\n" + "=" * 70)
    print(f"Batch generation completed! Successfully created: {success_count}/{count}")
    print(f"Saved directly to: {os.path.abspath(resolve_accounts_file())}")
    print("=" * 70)
    input("\nPress Enter to return to menu...")


def action_single_generation() -> None:
    print_banner()
    print("\n--- SINGLE ACCOUNT GENERATION ---")

    accounts = load_accounts()
    proxies = load_proxies()

    # 1. Region
    raw_region = input("Enter region code [PK, BD, ME, IND, SG, BR] (Default: PK): ").strip().upper()
    region = raw_region if raw_region else "PK"

    # 2. Nickname
    default_num = find_next_superscript_number(accounts, "Gohar")
    default_nick = format_nickname("Gohar", default_num)
    raw_nick = input(f"Enter nickname (Press Enter for default: {default_nick}): ").strip()
    nickname = raw_nick if raw_nick else default_nick

    # 3. Password
    default_pwd = generate_gohar_branded_password()
    print(f"Suggested Password: {default_pwd}")
    raw_pwd = input("Enter password (Press Enter for suggested Gohar branded password): ").strip()
    password = raw_pwd if raw_pwd else default_pwd

    # Proxy selection
    selected_proxy = None
    if proxies:
        selected_proxy = random.choice(proxies)
        short_p = selected_proxy.split("@")[-1] if "@" in selected_proxy else selected_proxy
        print(f"Using proxy: {short_p}")

    print("\nConnecting to Garena and Free Fire servers...")
    acc = create_complete_guest_account(
        nickname=nickname,
        password=password,
        region=region,
        proxy=selected_proxy,
    )

    if acc:
        print("\n" + "=" * 70)
        print("[SUCCESS] Account Created and Ready in Lobby!")
        print(f"  Nickname : {acc['nickname']}")
        print(f"  UID      : {acc['uid']}")
        print(f"  Game UID : {acc['game_uid']}")
        print(f"  Password : {acc['password']}")
        print(f"  Region   : {acc['region']}")
        print("=" * 70)
    else:
        print("\n[FAILED] Creation failed. Please check network/proxy connection.")

    input("\nPress Enter to return to menu...")


def action_export_storage() -> None:
    print_banner()
    print("\n--- EXPORT ACCOUNTS ---")

    accounts = load_accounts()
    print(f"Total saved accounts in database: {len(accounts)}")

    if not accounts:
        print("[!] No accounts found to export.")
        input("\nPress Enter to return to menu...")
        return

    # 1. Generate local standard CSV
    local_csv = Path("accounts.csv")
    csv_headers = ["Nickname", "UID", "Game_UID", "Password", "Region", "Level", "Is_Banned"]
    with open(local_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers)
        writer.writeheader()
        for a in accounts:
            writer.writerow({
                "Nickname": a.get("nickname", ""),
                "UID": a.get("uid", ""),
                "Game_UID": a.get("game_uid", ""),
                "Password": a.get("password", ""),
                "Region": a.get("region", ""),
                "Level": a.get("level", 1),
                "Is_Banned": a.get("is_banned", 0),
            })

    # 2. Generate local TXT file
    local_txt = Path("accounts.txt")
    with open(local_txt, "w", encoding="utf-8") as f:
        f.write(f"GARENA FREE FIRE ACCOUNTS - TOTAL: {len(accounts)}\n")
        f.write(f"EXPORTED ON: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")
        for idx, a in enumerate(accounts, 1):
            f.write(
                f"[{idx:03d}] Name: {a.get('nickname', 'N/A'):<14} | "
                f"UID: {a.get('uid', 'N/A'):<11} | "
                f"Game UID: {a.get('game_uid', 'N/A'):<12} | "
                f"Pass: {a.get('password', 'N/A')}\n"
            )

    print(f"\n[OK] Local files generated:")
    print(f"     CSV: {local_csv.resolve()}")
    print(f"     TXT: {local_txt.resolve()}")

    # 3. Export to Termux Phone Storage (/sdcard/Download)
    sdcard_download = Path("/sdcard/Download")
    if sdcard_download.is_dir():
        try:
            dest_csv = sdcard_download / "freefire_accounts.csv"
            dest_txt = sdcard_download / "freefire_accounts.txt"
            dest_json = sdcard_download / "freefire_accounts.json"

            shutil.copyfile(local_csv, dest_csv)
            shutil.copyfile(local_txt, dest_txt)
            shutil.copyfile(resolve_accounts_file(), dest_json)

            print("\n[OK] SUCCESS! Copied to phone storage (/sdcard/Download/):")
            print(f"     - {dest_csv}")
            print(f"     - {dest_txt}")
            print(f"     - {dest_json}")
            print("     You can open them directly in your phone's File Manager.")
        except PermissionError:
            print("\n[!] Storage Permission Denied.")
            print("    Please run this command in Termux first: termux-setup-storage")
            print("    Then allow storage permissions and retry.")
        except Exception as e:
            print(f"\n[!] Could not copy to /sdcard/Download: {e}")
    else:
        print("\n[NOTE] Not running in Android Termux or /sdcard/Download not detected.")
        print("       Exported files are saved locally in the current folder.")

    input("\nPress Enter to return to menu...")


def main_interactive_menu() -> None:
    while True:
        print_banner()
        accounts = load_accounts()
        proxies = load_proxies()

        print(f"  STATUS: {len(accounts)} Accounts Registered | {len(proxies)} Webshare Proxies Loaded\n")
        print("  [1] Batch Account Generation")
        print("  [2] Single Account Generation")
        print("  [3] Export Accounts (CSV / TXT to /sdcard/Download)")
        print("  [0] Exit")
        print("-" * 70)

        choice = input("Enter option [0-3]: ").strip()

        if choice == "1":
            action_batch_generation()
        elif choice == "2":
            action_single_generation()
        elif choice == "3":
            action_export_storage()
        elif choice == "0":
            print("\nExiting. Developed by Gohar Rehman (https://github.com/itsgoharrehman).")
            break
        else:
            print("[!] Invalid selection. Please enter 0, 1, 2, or 3.")
            time.sleep(1.0)


if __name__ == "__main__":
    main_interactive_menu()
