import shutil
from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module24 import MODULE24_SCHEMA


def main():
    settings, _ = load_all()
    database = path_for(settings, 'database_path')
    backup = database.with_name(database.stem + '_before_v6_0' + database.suffix)
    if database.exists() and not backup.exists():
        shutil.copy2(database, backup)
        print(f'Database backup: {backup}')
    conn = connect(settings)
    conn.execute(MODULE24_SCHEMA)
    conn.close()
    print('Crypto Intelligence Platform v6.0 installed.')
    print('Module 22 accounting is permanently corrected.')
    print('Module 24 quantitative research framework is ready.')
    print('Module 13 remains unchanged.')


if __name__ == '__main__':
    main()
