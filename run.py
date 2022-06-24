from application import create_app
from core_lib.utils.global_config import Config

app = create_app()
if __name__ == '__main__':
    app.run(debug=Config.get('development'), port=Config.get('port'), host=Config.get('host'))
