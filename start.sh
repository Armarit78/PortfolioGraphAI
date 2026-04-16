#!/bin/bash

# ─────────────────────────────────────────
#  Script de lancement du projet
#  Lance le backend (FastAPI) et le frontend (npm) en parallèle
# ─────────────────────────────────────────

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Détection de l'environnement virtuel Python ──────────────────────────────
if [ -n "$VIRTUAL_ENV" ]; then
    PYTHON="$VIRTUAL_ENV/bin/python"
    UVICORN="$VIRTUAL_ENV/bin/uvicorn"
    echo -e "${GREEN} Environnement virtuel détecté : $VIRTUAL_ENV${NC}"
else
    for VENV_PATH in "$ROOT_DIR/.venv" "$ROOT_DIR/venv" "$ROOT_DIR/backend/.venv" "$ROOT_DIR/backend/venv"; do
        if [ -f "$VENV_PATH/bin/activate" ]; then
            source "$VENV_PATH/bin/activate"
            PYTHON="$VENV_PATH/bin/python"
            UVICORN="$VENV_PATH/bin/uvicorn"
            echo -e "${GREEN} Environnement virtuel trouvé et activé : $VENV_PATH${NC}"
            break
        fi
    done
fi

PYTHON="${PYTHON:-python}"
UVICORN="${UVICORN:-uvicorn}"

echo -e "${YELLOW}──────────────────────────────────────────${NC}"
echo -e "${YELLOW}   Démarrage du projet                    ${NC}"
echo -e "${YELLOW}──────────────────────────────────────────${NC}"

# ── Fonction de préfixage des logs ───────────────────────────────────────────
prefix_logs() {
    local label="$1"
    local color="$2"
    while IFS= read -r line; do
        echo -e "${color}${label}${NC} $line"
    done
}

# ── Lancement du backend ──────────────────────────────────────────────────────
#echo -e "${BLUE} Lancement du backend  (FastAPI / uvicorn)...${NC}"
#cd "$ROOT_DIR/backend" || { echo -e "${RED} Dossier 'backend' introuvable.${NC}"; exit 1; }

# FIFO pour récupérer le vrai PID (un pipe | retournerait le PID du sous-shell)
BACKEND_FIFO=$(mktemp -u)
mkfifo "$BACKEND_FIFO"
"$UVICORN" backend.appRouter:app --reload > "$BACKEND_FIFO" 2>&1 &
BACKEND_PID=$!
prefix_logs "[BACKEND ]" "${BLUE}" < "$BACKEND_FIFO" &
rm -f "$BACKEND_FIFO"

# ── Lancement du frontend ─────────────────────────────────────────────────────
echo -e "${GREEN} Lancement du frontend (npm start)...${NC}"
cd "$ROOT_DIR/frontend" || { echo -e "${RED} Dossier 'frontend' introuvable.${NC}"; kill "$BACKEND_PID" 2>/dev/null; exit 1; }

FRONTEND_FIFO=$(mktemp -u)
mkfifo "$FRONTEND_FIFO"
npm run dev > "$FRONTEND_FIFO" 2>&1 &
FRONTEND_PID=$!
prefix_logs "[FRONTEND]" "${GREEN}" < "$FRONTEND_FIFO" &
rm -f "$FRONTEND_FIFO"

# ── Nettoyage à l'arrêt (Ctrl+C) ─────────────────────────────────────────────
cleanup() {
    echo -e "\n${RED} Arrêt des services...${NC}"
    kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
    wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
    echo -e "${RED} Services arrêtés.${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

echo -e "${GREEN} Backend  PID : $BACKEND_PID${NC}"
echo -e "${GREEN} Frontend PID : $FRONTEND_PID${NC}"
echo -e "${YELLOW}──────────────────────────────────────────${NC}"
echo -e "  Appuie sur ${RED}Ctrl+C${NC} pour tout arrêter."
echo -e "${YELLOW}──────────────────────────────────────────${NC}"

wait "$BACKEND_PID" "$FRONTEND_PID"