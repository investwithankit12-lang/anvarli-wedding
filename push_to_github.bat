@echo off
title Push Rishan Events Website to GitHub
cd /d "C:\Users\ghosh\OneDrive\Desktop\wedding"
powershell -NoProfile -ExecutionPolicy Bypass -File "push_to_github.ps1"
pause
