#!/bin/bash

echo "📦 Installing dependencies..."
pip install -r crypto_signals_bot/requirements.txt

echo "🚀 Starting signal bot in background..."
nohup python runner.py > runner.log 2>&1 &

echo "✅ Bot running. Output logging to runner.log"
