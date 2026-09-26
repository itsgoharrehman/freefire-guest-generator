# Garena Free Fire Guest Account Generator
**DEVELOPED BY: GOHAR REHMAN**  
**GITHUB:** [https://github.com/itsgoharrehman](https://github.com/itsgoharrehman)

Standalone, high-performance guest account generator for Android (Termux) and PC environments.

---

## Key Features

- **Direct-to-Lobby Initialization:** Completes authentic Free Fire OB55 `MajorRegister` and `MajorLogin` so character creation is already registered on Garena servers. Opening Free Fire goes straight to the lobby without showing the nickname creation screen.
- **Custom Superscript Sequential Naming:** Automatically names accounts with superscript numbers (`Gohar¹`, `Gohar²`... or custom `Shadow¹`, `Shadow²`...) with smart sequence detection and 12-character limit safety.
- **Dynamic Gohar Rehman Branded Passwords:** Generates unique, high-entropy 6-part branded passphrases per account (e.g., `Gohar-Apex-Vault-Rehman-Elite-47`).
- **1-Click Phone Export:** Automatically exports standard CSV (`accounts.csv`) and plain text (`accounts.txt`) directly to your phone's `/sdcard/Download/` folder.
- **Streamlined 4-Option Menu:** Clean, direct interactive CLI with zero clutter.

---

## Termux Quickstart

1. Open Termux and install Python and dependencies:
```bash
pkg update -y && pkg install python -y
pip install requests pycryptodome
```

2. Run the generator:
```bash
python termux_guest_gen.py
```

3. Menu Options:
- `[1] Batch Account Generation`: Enter account count, region code (default PK), base name, and password scheme.
- `[2] Single Account Generation`: Enter region code, custom name, and password.
- `[3] Export Accounts`: Exports accounts to `accounts.csv`, `accounts.txt`, and copies them to `/sdcard/Download/`.
- `[0] Exit`: Exit the application.
