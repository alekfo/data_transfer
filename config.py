from dotenv import load_dotenv
import os
load_dotenv()

BOT_TOKEN = os.getenv('TELEGRAM_TOKEN')
admin_id_first = int(os.getenv('ADMIN_ID'))
admin_id_second = int(os.getenv('ADMIN_ID2'))
# db_path = os.getenv('DATABASE_PATH')

SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')