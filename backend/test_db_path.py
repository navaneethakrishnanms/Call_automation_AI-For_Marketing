import os
base_dir=os.path.dirname(os.path.abspath(__file__))
db_url='sqlite+aiosqlite:///./marketing_ai.db'
db_name=db_url.replace('sqlite+aiosqlite:///./', '')
db_path=os.path.join(base_dir, db_name)
print(f'sqlite+aiosqlite:///{db_path.replace(os.sep, "/")}')
