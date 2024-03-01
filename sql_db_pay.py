import aiosqlite
import yaml
import os.path

try:
    with open("config.yml") as yaml_file:
        config = yaml.load(yaml_file, Loader=yaml.FullLoader)
except FileNotFoundError:
    with open("~/course_work/config.yml") as yaml_file:
        config = yaml.load(yaml_file, Loader=yaml.FullLoader)

async def db_check(isFirst=False):
    path_to_db = config['db']['source_db_path']
    path_to_dest = config['db']['dest_db_path']
        
    if not isFirst and not os.path.isfile(path_to_db):
        if os.path.isfile(config['db']['dest_db_path']):
            path_to_db = config['db']['dest_db_path']
            path_to_dest = config['db']['source_db_path']
        else:
            return -1

    return path_to_db, path_to_dest


async def connect_and_create_db(isFirst=True): 
    returned_value = await db_check(isFirst)  
    if returned_value == -1:
        return "Not having db files"
    else:
        path_to_db, path_to_dest = returned_value

    async with aiosqlite.connect(path_to_db) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users
                            (id INTEGER PRIMARY KEY, username TEXT, ispay BIT)''')
        await db.commit()

        async with aiosqlite.connect(path_to_dest) as backup_db:
            await db.backup(backup_db)


async def add_user(user_id, username, ispay):
    returned_value = await db_check()  
    if returned_value == -1:
        return "Not having db files"
    else:
        path_to_db, path_to_dest = returned_value

    async with aiosqlite.connect(path_to_db) as db:
        await db.execute("INSERT INTO users (id, username, ispay) VALUES (?, ?, ?)",
                         (user_id, username, ispay))
        await db.commit()

        async with aiosqlite.connect(path_to_dest) as backup_db:
            await db.backup(backup_db)

async def get_users():
    returned_value = await db_check()  
    if returned_value == -1:
        return "Not having db files"
    else:
        path_to_db, path_to_dest = returned_value

    async with aiosqlite.connect(path_to_db) as db:
        async with db.execute("SELECT * FROM users") as cursor:
            async with aiosqlite.connect(path_to_dest) as backup_db:
                await db.backup(backup_db)

            return await cursor.fetchall()
        
        
async def update_payment_info(user_id, new_value):
    returned_value = await db_check()  
    if returned_value == -1:
        return "Not having db files"
    else:
        path_to_db, path_to_dest = returned_value

    assert new_value == 0 or new_value == 1, "InCorrect type for payment. It should be a int bool"
    async with aiosqlite.connect(path_to_db) as db:
        await db.execute("UPDATE users SET ispay = ? WHERE id = ?", (new_value, user_id))
        await db.commit()

        async with aiosqlite.connect(path_to_dest) as backup_db:
            await db.backup(backup_db)
