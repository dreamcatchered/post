#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Production entry point for Post application
"""
import os
from app import app, db

if __name__ == '__main__':
    # Инициализация базы данных
    with app.app_context():
        db.create_all()
    
    # Получаем порт из переменной окружения, по умолчанию 5032
    port = int(os.environ.get('PORT', '5032'))
    host = os.environ.get('HOST', '127.0.0.1')
    debug = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')
    
    print(f"🚀 Запуск Post приложения на {host}:{port}")
    print(f"🌐 Приложение будет доступно на https://post.dreampartners.online")
    
    app.run(host=host, port=port, debug=debug)

