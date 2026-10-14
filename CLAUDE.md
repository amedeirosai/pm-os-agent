# Working agreements

- This repo is worked on from multiple machines. Start of session: run `git pull`
  automatically (safe, no need to ask). End of session: remind the user to commit
  and push, and wait for confirmation before doing it — don't commit or push
  silently/automatically.
- `.env` (in `00-build/`) holds the API key and is gitignored. Never commit it,
  never paste its contents into chat.
