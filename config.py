from dataclasses import dataclass

from environs import Env


@dataclass
class TgBot:
    token: str


@dataclass
class Config:
    tg_bot: TgBot


def load_config(path: str | None = None) -> Config:
    """
    Считывается файл .env и возвращать экземпляр класса Config с заполненными
    полями token
    Args:
        path (str | None, optional): указываем путь до директории, в которой
        находится файл .env. Defaults to None.
    Returns:
        Config: _description_
    """
    env = Env()
    env.read_env(path)
    return Config(tg_bot=TgBot(token=env('TOKEN')))
