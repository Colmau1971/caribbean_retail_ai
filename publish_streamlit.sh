#!/bin/bash

cd ~/Documents/caribbean_retail_ai

echo "Publicando datos a Streamlit Cloud..."

git add -f streamlit_data/*
git add dashboard_streamlit.py master_pipeline.py price_alerts.py regional_insights.py

git commit -m "Dashboard refresh"

git push origin main

echo "Publicación terminada."
