@echo off
REM 基金评分系统 - Windows 开机自启动脚本
REM 将此脚本的快捷方式放入 shell:startup 文件夹即可开机自动运行
REM 快捷方式创建方法: Win+R → shell:startup → 新建快捷方式指向本文件

cd /d "%~dp0"
echo [%date% %time%] Starting Fund Scorer Server...
start "FundScorer" /MIN python app.py
echo Server started on http://localhost:8000
