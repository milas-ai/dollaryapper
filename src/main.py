import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("MARIKEY")

print(key)