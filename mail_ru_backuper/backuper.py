try:
    import os
    import shutil
    import zipfile
    import datetime
    import time
    import os.path
    from webdav3.client import Client
    import random
    import json
    import sys

    application_path = os.path.abspath(os.path.dirname(__file__))
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)

    settings_filename = "settings.json"
    settings_path = os.path.join(application_path, settings_filename)

    with open(settings_path, 'r') as file:
        settings = json.load(file)

    MAILRU_WEBDAV3_USERNAME = settings["MAILRU_WEBDAV3_USERNAME"]
    MAILRU_WEBDAV3_PASSWORD = settings["MAILRU_WEBDAV3_PASSWORD"]
    MAILRU_WEBDAV3_HOSTNAME = settings["MAILRU_WEBDAV3_HOSTNAME"]
    MAILRU_DIRNAME          = settings["MailRuDirName"]
    DIRECTORYS_NEED_SAVE    = settings["DirsToBackup"]



    class Misc():
        def get_backup_time(self):
            _date = datetime.datetime.now()
            return f"{_date.day:02d}_{_date.month:02d}_{_date.year}_{_date.hour:02d}_{_date.minute:02d}"

        def create_zip(self, path, _temp_directiry_all_saved_7z):

            _zipnamepath = f"{_temp_directiry_all_saved_7z}/{path.split('/')[-1]}_{self.get_backup_time()}.zip"

            start_time = time.time()

            with zipfile.ZipFile(_zipnamepath, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(path):
                    for file in files:
                        zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), path))


            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f"{_zipnamepath.split('/')[-1]} создан за {elapsed_time:.2f} секунд")
            return _zipnamepath


    class FileCollector():
        def __init__(self):
            self._temp_directiry_all_saved_7z = f"{application_path}/save5555555555555"
            self._directorys_need_save = DIRECTORYS_NEED_SAVE
            self.start_time = time.time()

        def delete_everything_in_folder(self):
            if not os.path.exists(self._temp_directiry_all_saved_7z):
                os.makedirs(self._temp_directiry_all_saved_7z)


            shutil.rmtree(self._temp_directiry_all_saved_7z)
            os.mkdir(self._temp_directiry_all_saved_7z)

        def cleanup(self, _zipnamepath):
            shutil.rmtree(self._temp_directiry_all_saved_7z)
            os.remove(_zipnamepath)


        def start_creating_backup(self):
            _files = []
            self.delete_everything_in_folder()

            for path in self._directorys_need_save:
                _files.append(Misc().create_zip(path, self._temp_directiry_all_saved_7z))


            name = f"FULL_BACKUP_{Misc().get_backup_time()}.zip"
            _zipnamepath = f"{application_path}/{name}"
    
            if os.path.exists(_zipnamepath):
                os.remove(_zipnamepath)


            with zipfile.ZipFile(_zipnamepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(self._temp_directiry_all_saved_7z):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, os.path.relpath(file_path, self._temp_directiry_all_saved_7z))

            BackupMailRuCloud().uploadMailRuDirectory(_zipnamepath)

            end_time = time.time()
            elapsed_time = end_time - self.start_time

            print(f"Время выполнения: {elapsed_time:.2f} секунд")
            self.cleanup(_zipnamepath)


    class BackupMailRuCloud:
        def __init__(self):
            self.mail_ru_options = {
                 'webdav_hostname': MAILRU_WEBDAV3_HOSTNAME,
                 'webdav_login':    MAILRU_WEBDAV3_USERNAME,
                 'webdav_password': MAILRU_WEBDAV3_PASSWORD
            }
            self.main_ru_temp_dir = None
            self.main_ru_temp_dirs = []

            if None in self.mail_ru_options.values():
                raise ValueError("Отсутствуют один или несколько параметров для авторизации в WEBDAV_MAILRU. Проверьте переменные settings.json")
    


        def uploadMailRuDirectory(self, file_path, max_retries=3):
            mailRuDirectoryBacups = MAILRU_DIRNAME
            client = Client(self.mail_ru_options)
            if not client.check(mailRuDirectoryBacups):
                client.mkdir(mailRuDirectoryBacups)

            local_directory = self.createDirectoryWithFile(file_path)
            filename = file_path.split("/")[-1]
            for attempt in range(max_retries):
                try:
                    print(f"Попытка {attempt + 1} из {max_retries}: Отправить файл {filename} на MailRu Cloud")
                    client.push(remote_directory=mailRuDirectoryBacups, local_directory=local_directory)

                    # Если файл загружен успешно, можем выйти из цикла
                    print(f"Файл '{filename}' успешно сохранен на MailRu Cloud")
                    return None

                except Exception as e:
                    print(f"Неудачная попытка отправки файла. Ошибка: {e}")
                    if attempt < max_retries - 1:
                        print(f"Следующая попытка через 2 секунды...")
                        time.sleep(2)  # Ждем перед повторной попыткой

            print(f"Не получилось отправить файл '{filename}' на MailRu Cloud за {max_retries} попытки...")
            return None
        
    
        def createDirectoryWithFile(self, file_path):
            directoryName = self.create_unique_directory()
            shutil.copy(file_path, directoryName)
            self.main_ru_temp_dir = directoryName
            self.main_ru_temp_dirs.append(directoryName)
            return directoryName

        def create_unique_directory(self, base_path=application_path, prefix='dir_'):
            # Генерируем уникальное имя на основе времени и случайного числа
            timestamp = int(time.time())
            random_number = random.randint(1000, 9999)
            unique_dir_name = f"{prefix}{timestamp}_{random_number}"
    
            # Полный путь к новой директории
            full_path = os.path.join(base_path, unique_dir_name)
    
            # Создаём директорию
            os.makedirs(full_path)
    
            return full_path

        def __del__(self):
            for dir in self.main_ru_temp_dirs:
                shutil.rmtree(dir)



    filecollector = FileCollector()
    print("Начат процесс создания бэкапа")
    filecollector.start_creating_backup()
except Exception as e:
    print(f"Ошибка: {e}")
    while True:
        pass