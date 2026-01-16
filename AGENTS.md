# Global Agent Safety Policy (macOS)

## Absolute safety constraints (apply even in YOLO mode)
- Do NOT modify macOS system settings, security/privacy settings, or OS preferences.
- Do NOT touch system directories such as `/System`, `/Library`, `/Applications` (unless explicitly requested).
- Do NOT manage users, passwords, Keychain, or authentication settings.
- Do NOT alter network settings, firewall, VPN, or Wi-Fi configuration.
- Do NOT install, remove, or update system software without explicit approval.
- Do NOT run destructive commands (e.g., `rm -rf`, `diskutil`, `sudo`) unless explicitly requested.

## Scope limits
- Only operate within the user’s workspace/project directories unless explicitly asked.
- Avoid accessing personal data locations (`~/Library`, `~/Documents`, etc.) unless the task requires it.

## When in doubt
- Ask for confirmation before any action that could affect the OS, user data, or security.
