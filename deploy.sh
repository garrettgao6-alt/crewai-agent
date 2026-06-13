#!/bin/bash

echo "🚀 Deploy started..."

cd /root/crewai-agent || exit

echo "📦 Pulling latest code..."
git fetch origin
git reset --hard origin/main

echo "🧹 Cleaning Python cache..."
find . -name "**pycache**" -type d -exec rm -rf {} +

echo "🔄 Restarting service..."
systemctl restart crewai

echo "⏱ Waiting for restart..."
sleep 2

echo "🔍 Checking service..."
systemctl status crewai --no-pager

echo "✅ Deployment finished!"
