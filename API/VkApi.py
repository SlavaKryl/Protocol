import os
import requests

from pathlib import Path


class VKAPI:
    def __init__(self):
        self.token = self._load_token()
        self.api_version = "5.199"
        self.response = None
        self.user_info = None
        self.user_id = None

    def _load_token(self):
        """Загружает токен из файла config/vk_token.txt"""
        try:
            # Определяем путь к файлу с токеном
            token_path = Path(__file__).parent / "config" / "vk_token.txt"

            # Читаем токен из файла
            with open(token_path, "r") as f:
                token = f.read().strip()

            if not token:
                raise ValueError("Файл с токеном пуст")

            return token

        except FileNotFoundError:
            raise FileNotFoundError(
                f"Файл с токеном не найден. Создайте файл {token_path} "
                "и поместите в него ваш VK access_token"
            )
        except Exception as e:
            raise Exception(f"Ошибка при чтении токена: {str(e)}")

    def print_albums(self) -> None:
        if self.response:
            print(f"\nФотоальбомы пользователя {self.user_info['first_name']} {self.user_info['last_name']}:\n")

            if "items" in self.response.json()["response"]:
                counter = 1
                for album in self.response.json()["response"]["items"]:
                    print(f'{counter}) {album["title"]} (количество фото: {album["size"]})')
                    counter += 1
            else:
                print("У пользователя нет альбомов или они скрыты настройками приватности")
        else:
            self.response = requests.get("https://api.vk.com/method/photos.getAlbums", params={
                "access_token": self.token,
                "v": "5.199",
                "owner_id": self.user_id,
                "need_system": 1  # Включаем системные альбомы (например, "Фотографии на стене")
            })
            self.print_albums()

    def get_user_info(self, user_id):
        """Получает информацию о пользователе"""
        response = requests.get(
            "https://api.vk.com/method/users.get",
            params={
                "access_token": self.token,
                "v": self.api_version,
                "user_ids": user_id,
                "fields": "first_name,last_name,photo_200,domain,city,bdate",
            }
        )
        data = response.json()

        if "response" in data:
            user_info = data["response"][0]
            self.user_info = user_info
            self.user_id = data["response"][0]["id"]
            print("\nИнформация о пользователе:")
            print(f"Имя: {user_info['first_name']} {user_info['last_name']}")
            print(f"Ссылка: vk.com/{user_info['domain']}")
            print(f"Аватар: {user_info.get('photo_200', 'Нет фото')}")
            print(f"Город: {user_info.get('city', {}).get('title', 'Не указан')}")
            print(f"Дата рождения: {user_info.get('bdate', 'Не указана')}")
            return user_info
        else:
            error = data.get("error", {})
            raise Exception(
                f"VK API Error {error.get('error_code')}: {error.get('error_msg')}"
            )

def main():
    try:
        api = VKAPI()
        user_id = input("Введите user_id (без @) или короткое имя пользователя: ")

        api.get_user_info(user_id)
        api.print_albums()

    except Exception as e:
        print(f"Произошла ошибка: {e}")


if __name__ == '__main__':
    main()