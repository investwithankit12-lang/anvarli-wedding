@echo off
title Push Anvarli Wedding Website to GitHub
cd /d "C:\Users\ghosh\OneDrive\Desktop\wedding"
powershell -NoProfile -ExecutionPolicy Bypass -File "push_to_github.ps1"
pause
