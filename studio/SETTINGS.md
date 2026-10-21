# MG Studio settings (macOS)

MG Studio now has a settings section above the R5 reviewer panel:
- Save/delete a DeepSeek API credential in **macOS Keychain**.
- Enable/disable paid R5 review without Bash environment flags.
- Select system, none, or custom HTTP(S) proxy. Example:
  `http://127.0.0.1:7897`.

The API never sends a saved credential back to the browser. The local
nonsecret settings file is `work/mg_studio/settings.json` with owner-only
permissions; it is not part of the repository's tracked source. The
credential is saved via the macOS `security` utility, provided over stdin,
and used only during an explicitly confirmed R5 request.

This does not provide a token budget, free retries, or automatic publishing.
DeepSeek currently reviews **sampled frames only** and never generates
complete R5 approval. The app remains bound to localhost, and every paid
review still requires a separate confirmation.

After updating the PR branch, restart `python3 studio/server.py`, open the
settings panel, enter your key once, select your proxy, enable R5 and save.
Then run R5 preflight. Do not trigger a paid request until tests and local
preflight are approved.
