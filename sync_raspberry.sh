#!/bin/bash

cd ~/Documents/caribbean_retail_ai

echo "Sincronizando outputs a Raspberry..."

rsync -avz --progress outputs/ \
gonzalezmauricio2@192.168.50.36:/mnt/caribbean/caribbean_retail_ai/outputs/

rsync -avz --progress lmstudio/ \
gonzalezmauricio2@192.168.50.36:/mnt/caribbean/caribbean_retail_ai/lmstudio/

rsync -avz --progress streamlit_data/ \
gonzalezmauricio2@192.168.50.36:/mnt/caribbean/caribbean_retail_ai/streamlit_data/

echo "Sync Raspberry terminado."
