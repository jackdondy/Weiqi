# -*- coding: utf-8 -*-
# 记住上面这行是必须的，而且保存文件的编码要一致！

# 改变鼠标点击逻辑：鼠标左键点击，下黑子，右键点击，下白子

import math
import os
import sys
import threading
import tkinter
from tkinter import LEFT, BOTH, YES, Y, ttk, RIGHT, BOTTOM, X, HORIZONTAL, TOP, NW, GROOVE, W

import pygame
from pygame import RESIZABLE, QUIT, WINDOWRESIZED, MOUSEMOTION, SRCALPHA, VIDEORESIZE
from pygame.rect import Rect

from WeiQiLib.default import *
from WeiQiLib.Board import Piece
from WeiQiLib.GlobalConfigManager import GlobalConfigManager
from WeiQiLib.RoundFileManager import RoundFileManager, get_new_folder, get_all_folder

bg_image_path = "WeiQiSrc/Background.png"
black_piece_image_path = "WeiQiSrc/BlackPiece.png"
white_piece_image_path = "WeiQiSrc/WhitePiece.png"
cursor_image_path = "WeiQiSrc/cursor.png"
font_chs_path = "WeiQiSrc/SIMLI.TTF"
font_en_path = "WeiQiSrc/Cascadia.ttf"

# 不同棋盘的九星的横坐标序号
jiuxin = {"9": [2, 4, 6],
          "13": [3, 6, 9],
          "19": [3, 9, 15]}

my_global_config = GlobalConfigManager()

default_window_size = None

bg = None


# 初始化屏幕
def init():
    global screen, bg, black_piece, white_piece, cursor, default_window_size
    pygame.init()
    os.environ['SDL_VIDEO_CENTERED'] = '1'  # 居中显示
    screen = pygame.display.set_mode((1, 1), RESIZABLE | SRCALPHA)
    pygame.mouse.set_visible(False)  # 隐藏鼠标，自定义图像

    if bg is None:
        bg = pygame.image.load(bg_image_path).convert()  # (1024, 1024)
        black_piece = pygame.image.load(black_piece_image_path).convert_alpha()  # (146, 146)
        white_piece = pygame.image.load(white_piece_image_path).convert_alpha()  # (146, 146)
        cursor = pygame.image.load(cursor_image_path).convert_alpha()  # 43x48

        default_window_size = [s // 2 for s in pygame.display.list_modes()[0]]


def paint_board_bg(bg, board_size):
    # 绘制格线
    line_gap = bg.get_size()[0] / (board_size + 3)
    start_x = start_y = 2 * line_gap  # 棋盘左上角横纵坐标（相对于self.bg_piece_board）
    for i in range(board_size):
        pygame.draw.line(bg, (0, 0, 0), (start_x + i * line_gap, start_y),
                         (start_x + i * line_gap, start_y + (board_size - 1) * line_gap))
    for i in range(board_size):
        pygame.draw.line(bg, (0, 0, 0), (start_x, start_y + i * line_gap),
                         (start_x + (board_size - 1) * line_gap, start_y + i * line_gap))
    # 绘制外框线（加粗）
    pygame.draw.rect(bg, (0, 0, 0), [int(start_x),
                                     start_y,
                                     (board_size - 1) * line_gap,
                                     (board_size - 1) * line_gap], width=2)
    # 绘制九星
    index_list = jiuxin.get(str(board_size))
    if index_list is None:
        print("Board Size Error")
        return
    for i in index_list:
        for j in index_list:
            pygame.draw.circle(bg, (0, 0, 0), (start_x + i * line_gap, start_y + j * line_gap), 4)
    # 绘制坐标轴,使用英文字体
    my_font = pygame.font.Font(font_en_path, int(line_gap / 2))
    # 绘制两个纵轴：1,2,3...
    for i in range(1, board_size + 1):
        text_surf = my_font.render(str(i), True, (0, 0, 0))
        bg.blit(text_surf,
                (start_x - line_gap - text_surf.get_width() / 2,
                 start_y + (i - 1 - 1 / 4) * line_gap))
        bg.blit(text_surf, (start_x + board_size * line_gap - text_surf.get_width() / 2,
                            start_y + (i - 1 - 1 / 4) * line_gap))
    # 绘制两个横轴：A,B,C...
    for i in range(board_size):
        text_surf = my_font.render(chr(i + ord('A')), True, (0, 0, 0))
        bg.blit(text_surf,
                (start_x + i * line_gap - text_surf.get_width() / 2, start_y - line_gap))
        bg.blit(text_surf, (start_x + i * line_gap - text_surf.get_width() / 2,
                            start_y + board_size * line_gap - line_gap / 2))


class GUI:
    def __init__(self,
                 window_size,
                 round_manager: RoundFileManager):
        self.round_manager = round_manager
        self.board_size = round_manager.get_size()
        self.last_move = None  # 上一步下在哪个位置，可以是黑子或白子，用整数元组(x, y)表示
        self.hover_pos = None  # 当前鼠标悬停在棋盘上的坐标，用整数元组(x, y)表示
        self.mouse_pos = None  # 当前鼠标悬停在screen上的坐标
        self.line_gap = None
        self.start_x = self.start_y = None
        self.user_name_list = round_manager.get_user_name()

        self.size = None
        self.bg_all = self.piece_board = self.bg_piece_board = None
        self.black_piece_scale = self.white_piece_scale = self.black_piece_scale_trans2 = self.white_piece_scale_trans2 = None

        self.init_size(window_size)

    # size应为长度为2的元祖或列表，每个元素为float或int
    def init_size(self, size):
        # size[0] > size[1]
        # 缩小法以调节比例到黄金分割（放大法可能会超出屏幕最大分辨率）
        ratio = 0.618  # 高比宽(size[1] / size[0])
        if size[0] * ratio < size[1]:
            size = (int(size[0]), int(size[0] * ratio))
        else:
            size = (int(size[1] / ratio), int(size[1]))

        self.size = size

        os.environ['SDL_VIDEO_CENTERED'] = '1'  # 居中显示
        screen = pygame.display.set_mode(size, RESIZABLE | SRCALPHA)
        # screen = pygame.display.set_mode(size, SRCALPHA)

        button_board_height = size[1] / 16
        piece_board_heigth = size[1] - button_board_height
        left_board_width = (size[0] - piece_board_heigth) / 2

        try:
            # 测试
            self.button_board = screen.subsurface([0, 0,
                                                   size[0], button_board_height])
            self.piece_board = screen.subsurface([left_board_width, button_board_height,
                                                  piece_board_heigth, piece_board_heigth])
            self.left_board = screen.subsurface([0, button_board_height,
                                                 left_board_width, piece_board_heigth])
            self.right_board = screen.subsurface([left_board_width + piece_board_heigth, button_board_height,
                                                  left_board_width, piece_board_heigth])
        except ValueError:
            # 加入容错，因为参数size可能是从配置文件中读取的
            self.init_size([s / 2 for s in pygame.display.list_modes()[0]])
            return

        # 改变全局配置中的窗口历史大小
        my_global_config.update_window_size(size)

        self.bg_all = pygame.transform.smoothscale(bg, (size[0], size[0]))
        self.bg_piece_board = self.bg_all.subsurface([left_board_width, button_board_height,
                                                      piece_board_heigth, piece_board_heigth])  # bg_board为标准正方形

        self.fg = self.bg_all.copy()
        # 定义fg图层
        self.button_board = self.fg.subsurface([0, 0,
                                                size[0], button_board_height])
        self.piece_board = self.fg.subsurface([left_board_width, button_board_height,
                                               piece_board_heigth, piece_board_heigth])
        self.left_board = self.fg.subsurface([0, button_board_height,
                                              left_board_width, piece_board_heigth])
        self.right_board = self.fg.subsurface([left_board_width + piece_board_heigth, button_board_height,
                                               left_board_width, piece_board_heigth])
        self.rect_of_button_board = Rect(0, 0, size[0], button_board_height)
        self.rect_of_piece_board = Rect(left_board_width, button_board_height, piece_board_heigth, piece_board_heigth)

        self.line_gap = self.bg_piece_board.get_size()[0] / (self.board_size + 3)
        self.start_x = self.start_y = 2 * self.line_gap  # 棋盘左上角横纵坐标（相对于self.bg_piece_board）
        paint_board_bg(self.bg_piece_board, self.board_size)

        piece_width = int(math.ceil(self.line_gap))
        self.black_piece_scale = pygame.transform.smoothscale(black_piece, (piece_width, piece_width))
        self.white_piece_scale = pygame.transform.smoothscale(white_piece, (piece_width, piece_width))
        # 鼠标图像
        ratio = piece_width / cursor.get_height()
        self.cursor_scale = pygame.transform.smoothscale(cursor, (int(ratio * cursor.get_width()), piece_width))

        # 鼠标悬停在空位时，使用以下图像
        self.black_piece_scale_trans2 = self.black_piece_scale.copy()
        self.black_piece_scale_trans2.set_alpha(120)
        self.white_piece_scale_trans2 = self.white_piece_scale.copy()
        self.white_piece_scale_trans2.set_alpha(120)

        screen.blit(self.bg_all, (0, 0))
        # 绘制按钮
        self.paint_buttons()

        self.set_user_name()
        self.paint_all_pieces()

    def paint_buttons(self):
        self.button_board.blit(self.bg_all, (0, 0))
        # 绘制按钮
        self.rect_of_buttons = []
        my_font = pygame.font.Font(font_chs_path, int(self.button_board.get_height() * 3 / 4))
        texts = [u"新建棋盘", u"虚着", u"判断胜负"]
        text_surfs = [my_font.render(t, True, (0, 0, 0)) for t in texts]
        gap = (self.button_board.get_width() - sum([s.get_width() for s in text_surfs])) / (len(texts) + 1)
        v_gap = int(self.button_board.get_height() / 8)
        offset = 0
        for s in text_surfs:
            offset += gap
            self.rect_of_buttons.append(
                Rect(offset, v_gap, s.get_width(), s.get_height()))  # 便于碰撞检测：使用Rect的collidepoint方法
            self.button_board.blit(s, (offset, v_gap))
            offset += s.get_width()
        screen.blit(self.fg, (0, 0))
        pygame.display.flip()

    # 绘制棋盘上的所有子
    def paint_all_pieces(self):
        # 绘制圆形棋盘背景
        self.piece_board.blit(self.bg_piece_board, (0, 0))
        r = self.line_gap / 2
        # 绘制已下的子，半径为line_gap的一半
        for i in range(self.board_size):
            for j in range(self.board_size):
                p = self.round_manager.getState(i, j)
                if p == Piece.Black():
                    self.piece_board.blit(self.black_piece_scale,
                                          (self.start_x + i * self.line_gap - r, self.start_y + j * self.line_gap - r))
                if p == Piece.White():
                    self.piece_board.blit(self.white_piece_scale,
                                          (self.start_x + i * self.line_gap - r, self.start_y + j * self.line_gap - r))
        # 绘制上一步下子
        if self.last_move is not None:
            pygame.draw.circle(self.piece_board, (255, 0, 0), (
                self.start_x + self.last_move[0] * self.line_gap, self.start_y + self.last_move[1] * self.line_gap),
                               self.line_gap / 8)
        screen.blit(self.fg, (0, 0))
        pygame.display.flip()

    def resize(self, size):
        self.init_size(size)

    # 返回鼠标位置在棋盘上的对应坐标，横纵坐标都从0开始。如果超出棋盘范围，返回None, None
    # 注意输入参数是相对于screen的坐标，需要减去self.piece_board相对于screen的偏移
    def convert_pos(self, mouse_pos):
        mouse_pos = (mouse_pos[0] - self.piece_board.get_offset()[0], mouse_pos[1] - self.piece_board.get_offset()[1])
        # 转换为棋盘上的坐标
        # 基准坐标
        y0 = self.start_y
        x0 = self.start_x
        pos_x = math.ceil((mouse_pos[0] - x0) / self.line_gap)
        pos_y = math.ceil((mouse_pos[1] - y0) / self.line_gap)
        if pos_x not in range(self.board_size) or pos_y not in range(self.board_size):
            return None, None
        return pos_x, pos_y

    # 更新棋盘上的一个位置的图像
    def paint_pos(self, pos, piece_image=None):
        pos_rect = Rect(self.start_x + (pos[0] - 1 / 2) * self.line_gap,
                        self.start_y + (pos[1] - 1 / 2) * self.line_gap,
                        self.line_gap,
                        self.line_gap)
        # 绘制圆形棋盘背景
        self.piece_board.blit(self.bg_piece_board, pos_rect, pos_rect)

        # 绘制图案
        if piece_image is not None:
            r = self.line_gap / 2
            self.piece_board.blit(piece_image, (self.start_x + pos[0] * self.line_gap - r,
                                                self.start_y + pos[1] * self.line_gap - r))
        if self.last_move == pos:
            pygame.draw.circle(self.piece_board, (255, 0, 0), (
                self.start_x + self.last_move[0] * self.line_gap, self.start_y + self.last_move[1] * self.line_gap),
                               self.line_gap / 8)
        screen.blit(self.fg, (0, 0))
        pygame.display.flip()

    # 处理鼠标悬停
    def hover(self, mouse_pos):
        # 还原旧悬停位置上的图像
        if self.hover_pos is not None:
            if self.round_manager.getState(self.hover_pos[0], self.hover_pos[1]) == Piece.Black():
                self.paint_pos(self.hover_pos, self.black_piece_scale)
            elif self.round_manager.getState(self.hover_pos[0], self.hover_pos[1]) == Piece.White():
                self.paint_pos(self.hover_pos, self.white_piece_scale)
            else:
                self.paint_pos(self.hover_pos, None)
            self.hover_pos = None

        self.mouse_pos = mouse_pos
        self.paint_buttons()
        if not self.rect_of_piece_board.collidepoint(mouse_pos[0], mouse_pos[1]):
            if self.rect_of_button_board.collidepoint(mouse_pos[0], mouse_pos[1]):
                for r in self.rect_of_buttons:
                    if r.collidepoint(mouse_pos[0], mouse_pos[1]):
                        pygame.draw.lines(self.button_board, (255, 255, 255), True,
                                          [r.bottomleft, r.bottomright, r.topright, r.topleft])
            screen.blit(self.fg, (0, 0))
            # 在mouse_pos上画鼠标图像
            screen.blit(self.cursor_scale, mouse_pos)
            pygame.display.flip()
            return

        pos_x, pos_y = self.convert_pos(mouse_pos)
        print((pos_x, pos_y))
        if pos_x is None:
            screen.blit(self.fg, (0, 0))
            # 在mouse_pos上画鼠标图像
            screen.blit(self.cursor_scale, mouse_pos)
            pygame.display.flip()
            return
        self.hover_pos = (pos_x, pos_y)

        # print(self.hover_pos)
        self.clear_tip()
        # 当前坐标已有子
        if self.round_manager.getState(pos_x, pos_y) != Piece.Free():
            # 绘制棋子正中的十字交叉线，颜色为灰色
            grey = (128, 128, 128)
            for _z in [0, 1]:
                pygame.draw.line(self.piece_board, grey,
                                 (self.start_x + (pos_x + _z / 4) * self.line_gap,
                                  self.start_y + (pos_y + (1 - _z) / 4) * self.line_gap),
                                 (self.start_x + (pos_x - _z / 4) * self.line_gap,
                                  self.start_y + (pos_y + (_z - 1) / 4) * self.line_gap),
                                 width=3)
        else:

            # 绘制光标
            for _x in [- 1, 1]:
                for _y in [- 1, 1]:
                    for _z in [0, 1]:
                        pygame.draw.line(self.piece_board, (240, 0, 0),
                                         (self.start_x + (pos_x + _x / 4) * self.line_gap,
                                          self.start_y + (pos_y + _y / 4) * self.line_gap),
                                         (self.start_x + (pos_x + _x / 4 - (1 - _z) * _x / 8) * self.line_gap,
                                          self.start_y + (pos_y + _y / 4 - _z * _y / 8) * self.line_gap),
                                         width=2)

        screen.blit(self.fg, (0, 0))
        pygame.display.flip()

    def click_button(self, index):
        # texts = [u"新建棋盘", u"虚着", u"判断胜负"]
        if index == 0:
            pass
        if index == 1:
            pass
        if index == 2:
            j, points = self.round_manager.judge()
            _str = "和"
            if j == Piece.Black():
                _str = "黑方胜"
            elif j == Piece.White():
                _str = "白方胜"

            _str += "，点数比为 "
            _str += str(points[0])
            _str += ":"
            _str += str(points[1])
            self.show_tip(_str + " (中国规则)")

    # 判断输入的鼠标坐标是否是“新建棋局”按钮
    def is_new_round_button(self, mouse_pos):
        return self.rect_of_buttons[0].collidepoint(mouse_pos[0], mouse_pos[1])

    # 鼠标点击动作
    def click(self, mouse_pos, piece):
        # 如果点击按钮
        if self.rect_of_button_board.collidepoint(mouse_pos[0], mouse_pos[1]):
            i = 0
            for r in self.rect_of_buttons:
                if r.collidepoint(mouse_pos[0], mouse_pos[1]):
                    self.click_button(i)
                i += 1

        pos_x, pos_y = self.convert_pos(mouse_pos)
        if pos_x is None:
            return
        # 如果下子成功
        if self.round_manager.placePiece(pos_x, pos_y, piece):
            self.last_move = (pos_x, pos_y)
            self.paint_all_pieces()

    # 只要含有一个中文字符（不包括中文标点符号），即返回True
    def is_chs(self, _str):
        for i in _str:
            if u'\u4e00' <= i <= u'\u9fff':
                return True
        return False

    def set_user_name(self):
        user_name_height = self.left_board.get_height() / 16
        chs_font = pygame.font.Font(font_chs_path, int(user_name_height))
        en_font = pygame.font.Font(font_en_path, int(user_name_height))
        # 黑白子图案
        piece_width = int(self.left_board.get_height() / 12)
        black_piece_scale = pygame.transform.smoothscale(black_piece, (piece_width, piece_width))
        white_piece_scale = pygame.transform.smoothscale(white_piece, (piece_width, piece_width))
        piece_list = [black_piece_scale, white_piece_scale]
        # 绘制黑白方用户名
        board_list = [self.left_board, self.right_board]
        # 根据中英文选择不同字体
        for i in range(2):
            if self.is_chs(self.user_name_list[i]):
                my_font = chs_font
            else:
                my_font = en_font
            text_surf = my_font.render(self.user_name_list[i], True, (0, 0, 0))
            # 如果text_surf太长，截断
            if text_surf.get_width() > board_list[i].get_width():
                text_surf = text_surf.subsurface(Rect(0, 0, board_list[i].get_width(), user_name_height))
            board_list[i].blit(text_surf, (
                board_list[i].get_width() / 2 - text_surf.get_width() / 2, board_list[i].get_height() / 6))
            board_list[i].blit(piece_list[i],
                               (board_list[i].get_width() / 2 - piece_width / 2, board_list[i].get_height() / 3))
        screen.blit(self.fg, (0, 0))
        pygame.display.flip()
        pass

    # 展示提示字符串（包括当前位置是否可下等），展示于棋盘下部
    def show_tip(self, tip):
        my_font = pygame.font.Font(font_chs_path, int(self.line_gap * 3 / 4))
        text_surf = my_font.render(tip, True, (255, 255, 255), (0, 0, 0))
        self.piece_board.blit(text_surf, (self.piece_board.get_width() / 2 - text_surf.get_width() / 2,
                                          self.piece_board.get_height() - text_surf.get_height()))
        screen.blit(self.fg, (0, 0))
        pygame.display.flip()

    def clear_tip(self):
        self.piece_board.blit(self.bg_piece_board, (0, self.piece_board.get_height() - self.line_gap),
                              Rect(0, self.piece_board.get_height() - self.line_gap,
                                   self.piece_board.get_width(), self.piece_board.get_height()))
        screen.blit(self.fg, (0, 0))

    def quit(self):
        pygame.quit()

top = None
board_size = None
black_name = white_name = None
time_entry = None

round_manager = None


def create_new_round():
    global round_manager, black_name, white_name
    black_name2 = black_name.get()
    white_name2 = white_name.get()
    time_limit = int(time_entry.get())
    board_size_2 = board_size.get()
    print(black_name2)
    print(white_name2)
    print(time_limit)
    print(board_size_2)
    top.destroy()
    round_manager = RoundFileManager(get_new_folder(), [black_name2, white_name2], board_size_2, time_limit)


def view_round(folder):
    init()
    pygame.mouse.set_visible(True)
    print(default_window_size)
    screen = pygame.display.set_mode((default_window_size[1], default_window_size[1]), SRCALPHA)
    screen.blit(bg, (0, 0))
    temp_round_manager = RoundFileManager(folder)
    board_size = temp_round_manager.get_size()
    line_gap = screen.get_size()[0] / (board_size + 3)
    start_x = start_y = 2 * line_gap  # 棋盘左上角横纵坐标
    paint_board_bg(screen, board_size)

    piece_width = int(math.ceil(line_gap))
    black_piece_scale = pygame.transform.smoothscale(black_piece, (piece_width, piece_width))
    white_piece_scale = pygame.transform.smoothscale(white_piece, (piece_width, piece_width))
    r = line_gap / 2
    # 绘制已下的子，半径为line_gap的一半
    for i in range(board_size):
        for j in range(board_size):
            p = temp_round_manager.getState(i, j)
            if p == Piece.Black():
                screen.blit(black_piece_scale,
                            (start_x + i * line_gap - r, start_y + j * line_gap - r))
            if p == Piece.White():
                screen.blit(white_piece_scale,
                            (start_x + i * line_gap - r, start_y + j * line_gap - r))
    pygame.display.flip()


def enter_round(folder):
    global round_manager
    round_manager = RoundFileManager(folder)
    top.destroy()


def main():
    global top, board_size, black_name, white_name, time_entry, default_window_size, round_manager
    while True:
        round_manager = None
        # 展示开始界面，可以选择历史棋局，可以新建棋局，最后进入棋局或者退出游戏
        # 使用tkinter
        top = tkinter.Tk()
        notebook = ttk.Notebook(top)
        # 新建棋局 页面
        new_round_frame = tkinter.Frame(notebook)
        board_size = tkinter.IntVar()
        board_size.set(default_board_size)

        black_name = tkinter.StringVar()
        white_name = tkinter.StringVar()

        label1 = tkinter.Label(new_round_frame, text="enter black user name:")
        label1.grid(column=0, row=0, sticky=W)
        black_name_box = ttk.Combobox(new_round_frame, textvariable=black_name)
        black_name_box['values'] = my_global_config.get_all_user()
        black_name_box.grid(column=1, row=0)

        label2 = tkinter.Label(new_round_frame, text="enter white user name:")
        label2.grid(column=0, row=1, sticky=W)
        white_name_box = ttk.Combobox(new_round_frame, textvariable=white_name)
        white_name_box['values'] = my_global_config.get_all_user()
        white_name_box.grid(column=1, row=1)

        label3 = tkinter.Label(new_round_frame, text="choose board size:")
        label3.grid(column=0, row=2, sticky=W)
        _frame = tkinter.Frame(new_round_frame)
        rad1 = tkinter.Radiobutton(_frame, text="9", value=9, variable=board_size)
        rad2 = tkinter.Radiobutton(_frame, text="13", value=13, variable=board_size)
        rad3 = tkinter.Radiobutton(_frame, text="19", value=19, variable=board_size)
        rad3.select()
        rad1.pack(side=LEFT)
        rad2.pack(side=LEFT)
        rad3.pack(side=LEFT)
        _frame.grid(column=1, row=2)

        label4 = tkinter.Label(new_round_frame, text="enter time limit(seconds) per step:")
        label4.grid(column=0, row=3, sticky=W)
        time_entry = tkinter.Entry(new_round_frame)
        time_entry.grid(column=1, row=3)
        time_entry.insert(0, str(default_time_limit))

        button = tkinter.Button(new_round_frame, text="Ok", command=create_new_round)
        button.grid(column=0, row=4)

        notebook.add(new_round_frame, text="Create New Round")

        old_round_frame_outer = tkinter.Frame(notebook)
        old_round_canvas = tkinter.Canvas(old_round_frame_outer, confine=False)
        s1 = tkinter.Scrollbar(old_round_frame_outer)
        s1.pack(side=RIGHT, fill=Y)
        s1.configure(command=old_round_canvas.yview)
        s2 = tkinter.Scrollbar(old_round_frame_outer, orient=HORIZONTAL)
        s2.pack(side=BOTTOM, fill=X)
        s2.configure(command=old_round_canvas.xview)
        old_round_canvas.config(xscrollcommand=s2.set, yscrollcommand=s1.set)

        old_round_frame = tkinter.Frame(old_round_canvas)

        colors = ["LightBlue", "Snow"]
        colors2 = ["LightGreen", "Snow"]
        i = 1
        for folder in get_all_folder():
            i += 1
            _frame = tkinter.Frame(old_round_frame, relief=GROOVE, bd=5)
            _round_manager = RoundFileManager(folder)
            _label = tkinter.Label(_frame, text=folder, bg=colors[i % 2])
            _label.pack(side=LEFT, expand=True, fill=BOTH)
            _label2 = tkinter.Label(_frame, text=str(_round_manager.get_user_name()[0]) + " vs " + str(_round_manager.get_user_name()[1]), bg=colors[i % 2])
            _label2.pack(side=LEFT, expand=True, fill=BOTH)
            _label3 = tkinter.Label(_frame, text=str(_round_manager.get_trace_len()) + " steps", bg=colors[i % 2])
            _label3.pack(side=LEFT, expand=True, fill=BOTH)
            _button = tkinter.Button(_frame, text="View", command=lambda f=folder: view_round(f), bg=colors2[i % 2 - 1])
            _button.pack(side=RIGHT)
            _button2 = tkinter.Button(_frame, text="Enter", command=lambda f=folder: enter_round(f), bg=colors2[i % 2 - 1])
            _button2.pack(side=RIGHT)
            _frame.pack(expand=True, fill=BOTH)

        old_round_frame.pack(expand=True, fill=BOTH)
        old_round_canvas.create_window((0, 0), window=old_round_frame, anchor=NW)
        old_round_canvas.pack(expand=True, fill=BOTH)
        old_round_frame_outer.pack(expand=True, fill=BOTH)
        notebook.add(old_round_frame_outer, text="Continue Old Round")
        notebook.pack(expand=True, fill=BOTH)
        top.update()
        old_round_canvas.config(scrollregion=old_round_canvas.bbox("all"))  # 需在top.update()后运行
        top.mainloop()

        if round_manager is None:
            sys.exit()
            # exit()  # 说明未点击ok按钮，而是右上角退出

        my_global_config.update_user(round_manager.get_user_name()[0])
        my_global_config.update_user(round_manager.get_user_name()[1])

        # 开始棋局
        init()
        if my_global_config.get_window_size() is None:
            my_global_config.update_window_size(default_window_size)
        my_gui = GUI(my_global_config.get_window_size(), round_manager)
        while True:
            event = pygame.event.wait()
            # print(event)
            if event.type == QUIT:
                my_gui.quit()
                sys.exit()
                # exit()
            if event.type == WINDOWRESIZED:
                my_gui.resize((event.x, event.y))
                # print(event)
            if event.type == MOUSEMOTION:
                # print(event)
                # my_gui.hover(event.pos)
                my_gui.hover(pygame.mouse.get_pos())
            if event.type == pygame.MOUSEBUTTONUP:
                if my_gui.is_new_round_button(event.pos):
                    my_gui.quit()
                    break
                if event.button == 1:
                    my_gui.click(event.pos, Piece.Black())     # 左键
                elif event.button == 3:
                    my_gui.click(event.pos, Piece.White())     # 右键


if __name__ == "__main__":
    main()
