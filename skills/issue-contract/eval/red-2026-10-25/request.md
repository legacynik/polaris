User request (repository: a quoting web app; issues are written in Italian):

"Apri una issue: il deploy deve poter girare in prova senza toccare niente. Aggiungi a deploy.sh un flag --dry-run, e in config.yml metti DEPLOY_TIMEOUT a 300 secondi, perché oggi il deploy si pianta e non scade mai. È lavoro per un agente. Per la prova basta controllare che deploy.sh contenga --dry-run, che la funzione si chiami run_dry e che config.yml abbia DEPLOY_TIMEOUT: 300."

Facts already established (do not run any command to check them): no duplicate issue exists; route.py says `github`; the area is `deploy`; the AFK label for agent work is `agent-ready`.
