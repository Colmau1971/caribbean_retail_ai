#!/bin/bash

echo "==================================="
echo " SINCRONIZANDO RASPBERRY"
echo "==================================="

rsync -avz outputs/ \
gonzalezmauricio2@192.168.50.36:/mnt/caribbean/caribbean_retail_ai/outputs/

rsync -avz lmstudio/ \
gonzalezmauricio2@192.168.50.36:/mnt/caribbean/caribbean_retail_ai/lmstudio/

echo ""
echo "Verificando Streamlit..."

ssh gonzalezmauricio2@192.168.50.36 \
'ps aux | grep streamlit | grep -v grep'

echo ""
echo "Proceso completado."
