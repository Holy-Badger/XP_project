import os
from waitress import serve
from app import app

host = os.getenv('HOST', '0.0.0.0')
port = int(os.getenv('PORT', '5000'))
threads = int(os.getenv('THREADS', '8'))

if __name__ == '__main__':
    print(f'Публичный сервер запущен: http://{host}:{port}')
    print('Для доступа из локальной сети используйте IP вашего ПК, например http://192.168.1.10:5000')
    serve(app, host=host, port=port, threads=threads)
