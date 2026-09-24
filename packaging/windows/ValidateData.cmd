@echo off
title Validate Stakeholder Dashboard Data
"%~dp0StakeholderDashboard.exe" validate "%~dp0data\import.json"
pause
