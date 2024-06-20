# -*- coding: utf-8 -*-
# 记住上面这行是必须的，而且保存文件的编码要一致！
import json
import os.path
import shutil
import sys

from WeiQiLib.Board import Board, Piece
from WeiQiLib.default import *

# 棋局文件保存路径，一个棋局的数据保存于round_data_path下的一个文件夹中，文件夹名称为递增的自然数
round_data_path = os.path.join(os.getcwd(), "WeiQiData")


# 遍历round_data_path下的文件夹名称，返回可供使用的新文件夹名
def get_new_folder():
    new_folder = "1"
    folders = get_all_folder()
    if folders:
        new_folder = str(int(folders[-1]) + 1)
    return new_folder


# 返回round_data_path下的所有文件夹名称
def get_all_folder():
    if not os.path.isdir(round_data_path):
        return []
    folders = [f for f in os.listdir(round_data_path) if f.isdigit()]
    folders.sort(key=lambda x: int(x), reverse=False)
    return folders


def delete_folder(folder):
    if not os.path.isdir(os.path.join(round_data_path, folder)):
        return
    shutil.rmtree(os.path.join(round_data_path, folder))


def copy_folder(folder, new_folder):
    if not os.path.isdir(os.path.join(round_data_path, folder)):
        return
    shutil.copytree(os.path.join(round_data_path, folder), os.path.join(round_data_path, new_folder))


'''
 棋局保存格式:
 棋局文件夹命名为 <棋局序号（从1开始递增）>
 棋局文件夹下包含：
    棋局配置 config.txt
    每一步下子信息，用空文件的文件名表示，文件名格式为:  1-B-13-A（步数序号，B或W（黑子或白子），下子位置（与可视化界面一致））

 '''
round_config_name = "config.txt"
# config.txt中为以下字典的json格式
'''
config = {
    "user": [u"甲", u"罗"],  # 黑方， 白方
    "size": 19,  # 或 9, 13
    "time_limit": 180   # 单位秒
}
'''


# 管理棋局配置文件和棋局数据
class RoundFileManager(Board):
    # 如果文件夹下有配置文件，则自动读入，并读入历史步骤
    def __init__(self,
                 folder: str,
                 username: list = None,
                 size: int = default_board_size,
                 time_limit: int = default_time_limit,
                 format_str: str = None):
        self.folder = folder
        print("RoundFileManager init: " + folder)
        # 如果路径不存在，则创建
        if not os.path.isdir(round_data_path):
            os.mkdir(round_data_path)
        if not os.path.isdir(os.path.join(round_data_path, folder)):
            os.mkdir(os.path.join(round_data_path, folder))

        self.__round_config = {}
        if username is None:
            # 如果已存在配置文件，且合法，则读入配置
            try:
                print(os.path.join(round_data_path, self.folder, round_config_name))
                with open(os.path.join(round_data_path, self.folder, round_config_name), encoding="utf-8") as f:
                    self.__round_config = json.load(f)
                    print(self.__round_config)
            except (FileNotFoundError, json.decoder.JSONDecodeError, UnicodeDecodeError):
                pass

            if "user" not in self.__round_config or len(self.__round_config["user"]) != 2:
                self.__round_config["user"] = ["", ""]
            if "size" not in self.__round_config or self.__round_config["size"] not in sizes:
                self.__round_config["size"] = default_board_size
            if "time_limit" not in self.__round_config or self.__round_config["time_limit"] < 0:
                self.__round_config["time_limit"] = default_time_limit
        else:
            # 如果指定了输入参数，则新建配置
            if len(username) != 2:
                print("make_config: username illegal")
                return
            # 从format_str中恢复size
            if format_str is not None:
                if format_str[0] != '$' or format_str[-1] != '$' or len(format_str) < 3:
                    print("make_config: format_str illegal")
                    return
                size = ord(format_str[1]) - ord('A')

            if size not in sizes:
                print("make_config: size illegal")
                return
            if time_limit < 0:
                print("make_config: time_limit illegal")
                return
            self.__round_config["user"] = username
            self.__round_config["size"] = size
            self.__round_config["time_limit"] = time_limit
            with open(os.path.join(round_data_path, self.folder, round_config_name), "w", encoding="utf-8") as f:
                json.dump(self.__round_config, f)

        super(RoundFileManager, self).__init__(width=self.__round_config["size"])
        # 从format_str中恢复历史数据
        if format_str is not None:
            if format_str[0] != '$' or format_str[-1] != '$' or len(format_str) < 3 or len(format_str) % 2 == 0:
                print("Format String Damaged")
                return
            print(format_str)
            i = 2
            while i < len(format_str) - 1:
                if format_str[i].isupper():
                    if not self.placePiece(ord(format_str[i]) - ord('A'),
                                                                    ord(format_str[i + 1]) - ord('A'),
                                                                    Piece.Black()):
                        print("History Error")
                        return
                else:
                    if not self.placePiece(ord(format_str[i]) - ord('a'),
                                                                    ord(format_str[i + 1]) - ord('a'),
                                                                    Piece.White()):
                        print("History Error")
                        return
                i += 2
        else:
            # 读取文件
            self.read_trace()
        self.has_init = True

    def get_user_name(self):
        return self.__round_config["user"]

    def get_size(self):
        return self.__round_config["size"]

    def get_time_limit(self):
        return self.__round_config["time_limit"]

    # 写入本地文件，注意下子的位置的横纵坐标从1或A开始
    def _save_file(self, piece, row, col):
        # 每一步下子信息，用空文件的文件名表示，文件名格式为:  1-B-13-A
        # 步数序号，B或W（黑子或白子），下子位置（与可视化界面一致）
        filename = str(len(self._trace))
        if piece == Piece.Black():
            filename += "-B"
        else:
            filename += "-W"
        # col对应数字坐标
        filename += ("-" + str(col + 1))
        # row对应字母坐标
        filename += ("-" + chr(row + ord('A')))
        try:
            with open(os.path.join(round_data_path, self.folder, filename), "w") as f:
                pass
        except PermissionError as e:
            print(e)

    def placePiece(self, row, col, piece):
        if super(RoundFileManager, self).placePiece(row, col, piece):
            self._save_file(piece, row, col)
            return True
        return False

    # 扫描棋盘文件夹下的所有文件，筛选出以数字开头的文件，读取历史步骤，并更新父类
    # 当文件名组成的列表的格式不合法时，从不合法处中断
    def read_trace(self):
        files = []
        for filename in os.listdir(os.path.join(round_data_path, self.folder)):
            if filename[: filename.find('-')].isdigit():
                files.append(filename.split("-"))
        files.sort(key=lambda x: int(x[0]))
        # print(files)
        index = 1
        for step in files:
            if len(step) != 4:
                return
            if int(step[0]) != index:
                return
            index += 1

            if not step[2].isdigit():
                return
            col = int(step[2]) - 1
            if col >= self.__round_config["size"] or col < 0:
                return

            try:
                row = ord(step[3]) - ord('A')
                if row >= self.__round_config["size"] or row < 0:
                    return
            except:
                return
            # 下子
            if step[1] == 'B':
                if not super(RoundFileManager, self).placePiece(row, col, Piece.Black()):
                    print("History Error")
            elif step[1] == 'W':
                if not super(RoundFileManager, self).placePiece(row, col, Piece.White()):
                    print("History Error")
            else:
                return


if __name__ == "__main__":
    a = RoundFileManager("1")
    print(a.format_str())
