#!/bin/bash

cd /Users/mauriciogonzalez/Documents/caribbean_retail_ai

source venv/bin/activate

caffeinate -dimsu python master_pipeline.py

python price_alerts.py
python regional_insights.py

./sync_raspberry.sh

git add -f streamlit_data/*
git add dashboard_streamlit.py master_pipeline.py price_alerts.py regional_insights.py sync_raspberry.sh

git commit -m "Dashboard refresh $(date '+%Y-%m-%d %H:%M')" || true
git push origin main
