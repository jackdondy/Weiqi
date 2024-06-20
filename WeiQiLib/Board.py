# -*- coding: utf-8 -*-
# 记住上面这行是必须的，而且保存文件的编码要一致！

# 定义常量：黑子，白子与空
import copy

from WeiQiLib.default import *


class Piece:
    @staticmethod
    def Free():
        return 0

    @staticmethod
    def Black():
        return 1

    @staticmethod
    def White():
        return 2


class Board:
    def __init__(self, width: int):
        print("Board init Width:" + str(width))
        if width not in sizes:
            print("Board: Width illegal, please change the width")
            return
        self.__width = width
        self.__mat = [[Piece.Free()] * width for _ in range(width)]  # 棋盘当前状态，注意[[0] * width ] * width的所有一维数组是同一个
        self._trace = []  # 记录下子历史，存储结构为[[<黑或白>(如Piece.Black()), 行数(从0开始), 列数(从0开始), 棋盘矩阵], []...]

    def getWidth(self):
        return self.__width

    # 假设b为Board的一个实例，用print(b)打印出b
    def __str__(self):
        return "\n".join([str(row_arr) for row_arr in self.__mat])

    def getState(self, row, col):
        return self.__mat[row][col]

    # 添加历史
    def _addTrace(self, piece, row, col, mat):
        self._trace.append([piece, row, col, copy.deepcopy(mat)])

    # 转为格式化字符串，便于传输
    def format_str(self):
        f_s = '$' + chr(ord('A') + self.__width)
        # print(self._trace)
        for piece, row, col, _ in self._trace:
            if piece == Piece.Black():
                f_s += chr(ord('A') + row)
                f_s += chr(ord('A') + col)
            if piece == Piece.White():
                f_s += chr(ord('a') + row)
                f_s += chr(ord('a') + col)
        return f_s + '$'

    def get_trace_len(self):
        return len(self._trace)

    def get_current_user(self):
        if not self._trace:
            return Piece.Black()
        if self._trace[-1][0] == Piece.Black():
            return Piece.White()
        else:
            return Piece.Black()

    # 下子，输入的位置可下时请返回True，不可下时请打印错误(print)，并返回False
    # 包括检查row和col是否合法
    # 调用__addTrace，并修改self.__mat（包括下子及吃子）
    # 实现：先调用isPlaceableForBlack，返回真时，应用吃子规则。
    def placePiece(self, row, col, piece):
        b, new_mat = self.isPlaceableForPiece(row, col, piece, return_new_mat=True)
        if not b:
            return False
        self.__mat = new_mat
        self._addTrace(piece, row, col, new_mat)
        return True

    # 判断(x,y)上是否为target
    def isTarget(self, x, y, target):
        if 0 <= x < self.__width and 0 <= y < self.__width and self.__mat[x][y] == target:
            return True
        return False

    # 判断mat[x][y]上是否为target
    @staticmethod
    def isTargetForMat(mat, x, y, target):
        if 0 <= x < len(mat) and 0 <= y < len(mat[0]) and mat[x][y] == target:
            return True
        return False

    # 根据pos_mat矩阵清除self.__mat
    def eat(self, pos_mat):
        for i in range(self.__width):
            for j in range(self.__width):
                if pos_mat[i][j]:
                    self.__mat[i][j] = Piece.Free()

    # 根据pos_mat矩阵清除mat
    @staticmethod
    def eatForMat(mat, pos_mat):
        for i in range(len(mat)):
            for j in range(len(mat[0])):
                if pos_mat[i][j]:
                    mat[i][j] = Piece.Free()

    # 如果可下，返回 True, None
    # 如果不可下，(包括检查row和col是否合法),返回 False, "已占用"/"无气"/"全局同形"（等提示信息），字符串前请加 u
    # 实现：先填入棋盘（在拷贝的新棋盘上），并应用吃子规则，
    #       吃子或不吃子后，若所在块气为0，则返回False，
    #                    若全局同形(此时气不为0)，则返回False，
    #       否则返回True
    # 吃子规则： 分别对当前位置的上、下、左、右判断是否为对方的子，是则判断所在的块是否气为0，是则吃子
    def isPlaceableForPiece(self, row, col, piece, return_new_mat=False):
        if row < 0 or row > self.__width - 1 or col < 0 or col > self.__width - 1:
            return False, u"位置不合法"
        if self.__mat[row][col] != Piece.Free():
            return False, u"已占用"
        new_mat = copy.deepcopy(self.__mat)  # self.__mat.copy()是浅拷贝
        new_mat[row][col] = piece
        poslist = [[row - 1, col], [row + 1, col], [row, col + 1], [row, col - 1]]
        if piece == Piece.Black():
            opp = Piece.White()
        else:
            opp = Piece.Black()

        for pos in poslist:
            if Board.isTargetForMat(new_mat, pos[0], pos[1], opp):
                block_mat, target_v = MatCalculator.get_block_and_target_v(new_mat, pos[0], pos[1], Piece.Free())
                if target_v == 0:
                    Board.eatForMat(new_mat, block_mat)
        # 判断当前位置气是否为0
        block_mat, target_v = MatCalculator.get_block_and_target_v(new_mat, row, col, Piece.Free())
        if target_v == 0:
            return False, u"无气"
        # 判断是否全局同形
        for trace in self._trace:
            if trace[-1] == new_mat:
                return False, u"全局同形"

        if return_new_mat:
            return True, new_mat
        return True, None

    # 判断获胜方
    # 除了双方的子数，还有包围的空穴数
    # 返回：
    #   获胜方：如Piece.Black()，如果平手，则为Piece.Free()
    #   [黑方的点数，白方的点数]
    # 采用中国规则，黑子数-3.75 > 180.5则黑胜, 白子数+3.75 > 180.5则白胜，其他情况为和
    def judge(self):
        black_point = sum([l.count(Piece.Black()) for l in self.__mat])
        white_point = sum([l.count(Piece.White()) for l in self.__mat])
        done_free_mat = [[False] * self.__width for _ in range(self.__width)]  # True表示已经处理的空穴
        for i in range(self.__width):
            for j in range(self.__width):
                if self.__mat[i][j] == Piece.Free() and not done_free_mat[i][j]:
                    # 返回(i, j)空穴所在的块以及该块的边界上的黑白子数目
                    block_mat, target_v_list = MatCalculator.get_block_and_target_v_list(self.__mat, i, j,
                                                                                         Piece.Black(), Piece.White())
                    if target_v_list[0] == 0 and target_v_list[1] != 0:
                        white_point += sum([l.count(True) for l in block_mat])
                    if target_v_list[1] == 0 and target_v_list[0] != 0:
                        black_point += sum([l.count(True) for l in block_mat])
                    # 记录done_free_mat
                    for m in range(self.__width):
                        for n in range(self.__width):
                            done_free_mat[m][n] = block_mat[m][n] or done_free_mat[m][n]
        if black_point - 3.75 > 180.5:
            j = Piece.Black()
        elif white_point + 3.75 > 180.5:
            j = Piece.White()
        else:
            j = Piece.Free()
        return j, [black_point, white_point]


class MatCalculator:
    def __init__(self, mat, block_target, target, target2=None):
        self.mat = mat
        self.row = len(mat)
        self.col = len(mat[0])
        self.block_mat = [[False] * self.col for _ in range(self.row)]
        self.block_target = block_target
        self.target = target
        self.target_mat = [[False] * self.col for _ in range(self.row)]  # 标记为True的地方为target
        self.target2 = target2
        self.target_mat2 = [[False] * self.col for _ in range(self.row)]  # 标记为True的地方为target2
        pass

    def step(self, x, y):
        if x < 0 or x > self.row - 1 or y < 0 or y > self.col - 1:
            return
        if self.mat[x][y] == self.block_target:
            if self.block_mat[x][y]:
                return
            self.block_mat[x][y] = True
            self.step(x + 1, y)
            self.step(x - 1, y)
            self.step(x, y + 1)
            self.step(x, y - 1)
            return
        if self.mat[x][y] == self.target:
            self.target_mat[x][y] = True
        if self.mat[x][y] == self.target2:
            self.target_mat2[x][y] = True

    # 返回:
    #   block_mat: 二维数组，与mat同大小，但每个元素的取值只有True和False，mat[x][y]所在的块的元素标记为True
    #   target_v: 该块的边界上值为target的点数
    @staticmethod
    def get_block_and_target_v(mat, x, y, target):
        c = MatCalculator(mat, mat[x][y], target)
        c.step(x, y)
        target_v = sum([l.count(True) for l in c.target_mat])
        return c.block_mat, target_v

    # 返回:
    #   block_mat: 二维数组，与mat同大小，但每个元素的取值只有True和False，mat[x][y]所在的块的元素标记为True
    #   [target_v, target_v2]: 该块的边界上值为target1和target2的点数
    @staticmethod
    def get_block_and_target_v_list(mat, x, y, target, target2):
        c = MatCalculator(mat, mat[x][y], target, target2)
        c.step(x, y)
        target_v = sum([l.count(True) for l in c.target_mat])
        target_v2 = sum([l.count(True) for l in c.target_mat2])
        return c.block_mat, [target_v, target_v2]


if __name__ == "__main__":
    pass
