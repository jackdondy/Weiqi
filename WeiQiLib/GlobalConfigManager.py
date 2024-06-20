# -*- coding: utf-8 -*-
# 记住上面这行是必须的，而且保存文件的编码要一致！
import json
import os.path
import sys

# 服务器配置 server.txt，待实现

all_config_name = os.path.join(os.getcwd(), "all_config.txt")

# 全局配置 all_config.txt，保存于本地的项目目录下， 以下为一个示例
'''
all_config = {
    "all_user": [u"Ammy", u"我"],  # 用户名列表
    "window_size": [1920, 1080],  # 窗口大小
    "last_round": None  # 上一局的文件夹路径（如"1"），所有棋局保存在项目根目录的 WeiQiData 文件夹下
}
'''


# 全局配置管理
class GlobalConfigManager:
    def __init__(self):
        self.__all_config = {}
        try:
            with open(all_config_name, encoding="utf-8") as f:
                self.__all_config = json.load(f)
                print(self.__all_config)
        except (FileNotFoundError, json.decoder.JSONDecodeError, UnicodeDecodeError):
            pass
        if "all_user" not in self.__all_config or type(self.__all_config["all_user"]) != list:
            self.__all_config["all_user"] = []

        if "window_size" not in self.__all_config or len(self.__all_config["window_size"]) != 2:
            self.__all_config["window_size"] = None

        if "last_round" not in self.__all_config:
            self.__all_config["last_round"] = None

    def update_user(self, username):
        if username is None:
            return
        if username not in self.__all_config["all_user"]:
            self.__all_config["all_user"].append(username)
            self.save_config()

    def get_all_user(self):
        return self.__all_config["all_user"].copy()

    def update_window_size(self, size):
        if len(size) != 2:
            print("update_window_size failed")
            return
        self.__all_config["window_size"] = size
        self.save_config()

    def get_window_size(self):
        return self.__all_config["window_size"]

    def update_last_round(self, last_round_path):
        self.__all_config["last_round"] = last_round_path
        self.save_config()

    def get_last_round(self):
        return self.__all_config["last_round"]

    def save_config(self):
        with open(all_config_name, "w", encoding="utf-8") as f:
            json.dump(self.__all_config, f)
