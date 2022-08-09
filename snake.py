# created by kalle
import curses
import os
from enum import Enum, auto
from math import ceil
from random import choice
from typing import Tuple
from itertools import chain


class Direction(Enum):
    RIGHT = auto()
    LEFT = auto()
    DOWN = auto()
    UP = auto()
    HORIZONTAL = auto()
    VERTICAL = auto()


def relative_direction(pos1, pos2):
    if pos1[0] != pos2[0]:
        return Direction.VERTICAL
    else:
        return Direction.HORIZONTAL


HIGHSCORE_FILE_PATH = os.path.join(os.path.expanduser("~"), "snake_highscore")


def get_highscore() -> int:
    if os.path.isfile(HIGHSCORE_FILE_PATH):
        with open(HIGHSCORE_FILE_PATH, "r") as fd:
            try:
                return int(fd.readline())
            except:
                ...
    return 0


def write_highscore(score: int) -> None:
    try:
        with open(HIGHSCORE_FILE_PATH, "w") as fd:
            fd.write(str(score))
    except:
        ...


class Snake:
    def __init__(self, start_pos: Tuple[int, int]):
        self.dir = Direction.RIGHT
        self.head = start_pos
        self.tail = [start_pos for _ in range(3)]
        self.old_pos = None

    def update(self):
        self.old_pos = self.tail[-1]
        self.tail = [self.head] + self.tail[:-1]
        if self.dir == Direction.RIGHT:
            self.head = (self.head[0], self.head[1] + 1)
        elif self.dir == Direction.LEFT:
            self.head = (self.head[0], self.head[1] - 1)
        elif self.dir == Direction.DOWN:
            self.head = (self.head[0] + 1, self.head[1])
        elif self.dir == Direction.UP:
            self.head = (self.head[0] - 1, self.head[1])

    def grow(self):
        self.tail += [self.tail[-1]]


class Manager:
    EVENT_TIMEOUT = 200
    MIN_WINDOW_SIZE = 6

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.__set_bounds()
        self.snake = None
        self.walls = []
        self.food = None
        self.score = 0
        self.highscore = get_highscore()

    def start(self):
        self.stdscr.timeout(Manager.EVENT_TIMEOUT)
        self.snake = Snake(self.center)
        self.food = None
        self.score = 0
        self.stdscr.clear()
        self.__create_walls()
        self.__loop()

    def __set_bounds(self):
        self.scrheight, self.scrwidth = self.stdscr.getmaxyx()
        if (
            self.scrheight < Manager.MIN_WINDOW_SIZE
            or self.scrwidth < Manager.MIN_WINDOW_SIZE
        ):
            self.__await_resize()

        self.center = (round(self.scrheight / 2), (round(self.scrwidth / 2)))

        mapsize_max = 20
        half_mapsize = ceil(mapsize_max / 2)
        self.bounds_x = (
            max(self.center[1] - half_mapsize, 0),
            min(self.center[1] + half_mapsize, self.scrwidth - 1),
        )
        self.bounds_y = (
            max(self.center[0] - half_mapsize, 0),
            min(self.center[0] + half_mapsize, self.scrheight - 2),
        )

        self.all_positions = set(
            chain.from_iterable(
                [
                    list(
                        zip(
                            [i] * self.bounds_x[1],
                            range(self.bounds_x[0] + 1, self.bounds_x[1]),
                        )
                    )
                    for i in range(self.bounds_y[0] + 1, self.bounds_y[1])
                ]
            )
        )

    def offset_screen_position(self, pos, offset):
        # Offset the position, clamping to bounds
        return (
            min(max(pos[0] + offset[0], self.bounds_y[0]), self.bounds_y[1]),
            min(max(pos[1] + offset[1], self.bounds_x[0]), self.bounds_x[1]),
        )

    def __create_walls(self):
        self.walls = []
        for x in range(self.bounds_x[0], self.bounds_x[1] + 1):
            self.walls.append((self.bounds_y[0], x))
            self.walls.append((self.bounds_y[1] + 1, x))
        for y in range(self.bounds_y[0], self.bounds_y[1] + 2):
            self.walls.append((y, self.bounds_x[0]))
            self.walls.append((y, self.bounds_x[1]))
        # Draw the walls
        self.__draw_walls()

    def __on_resize(self):
        # Set new bounds
        old_center = self.center
        self.__set_bounds()

        # Offset food + snake
        offset = (self.center[0] - old_center[0], self.center[1] - old_center[1])
        self.food = self.offset_screen_position(self.food, offset)
        self.snake.head = self.offset_screen_position(self.snake.head, offset)
        for i, pos in enumerate(self.snake.tail):
            self.snake.tail[i] = self.offset_screen_position(pos, offset)

        # Create walls and redraw
        self.__create_walls()
        self.__redraw_all()

    def __check_resize(self):
        tmp_scrheight, tmp_scrwidth = self.stdscr.getmaxyx()
        if self.scrheight != tmp_scrheight or self.scrwidth != tmp_scrwidth:
            self.__on_resize()
            return True
        else:
            return False

    def __draw(self):
        if self.__check_resize():
            return
        # Clear old tail piece of snake
        if self.snake.old_pos is not None and self.food != self.snake.old_pos:
            self.stdscr.addstr(self.snake.old_pos[0], self.snake.old_pos[1], " ")
        # Draw the new head and first tail position
        self.__draw_snake()
        # Move cursor out of the way
        self.stdscr.move(0, 0)
        self.stdscr.refresh()

    def __redraw_all(self):
        self.stdscr.clear()
        self.__draw_walls()
        self.__draw_snake(redraw=True)
        self.__draw_food()
        self.stdscr.move(0, 0)
        self.stdscr.refresh()

    def __draw_walls(self):
        for (y, x) in self.walls:
            self.stdscr.addstr(y, x, "#")
        # Write dimensions
        width = self.bounds_x[1] - self.bounds_x[0]
        text = "%dx%d" % (
            self.bounds_x[1] - self.bounds_x[0],
            self.bounds_y[1] - self.bounds_y[0],
        )
        self.stdscr.addstr(
            self.bounds_y[0],
            self.bounds_x[0] + round(width / 2) - round(len(text) / 2),
            text,
        )

    def __draw_snake(self, redraw=False):
        self.stdscr.addstr(self.snake.head[0], self.snake.head[1], "X")
        if redraw:
            body = [self.snake.head] + self.snake.tail
            for i, pos in enumerate(body[1:], start=1):
                self.__draw_snake_piece(pos, body[i - 1])
        else:
            # Only draw head and first tail piece (head in last frame)
            self.__draw_snake_piece(self.snake.tail[0], self.snake.head)

    def __draw_snake_piece(self, pos, rel_pos):
        rel_dir = relative_direction(pos, rel_pos)
        shape = "-" if rel_dir == Direction.HORIZONTAL else "|"
        self.stdscr.addstr(pos[0], pos[1], shape)

    def __draw_food(self):
        self.stdscr.addstr(self.food[0], self.food[1], "O")

    def __spawn_food(self):
        occupied_positions = set([self.food, self.snake.head] + self.snake.tail)
        free_positions = list(self.all_positions.difference(occupied_positions))
        self.food = choice(free_positions)
        # Draw the new food
        self.__draw_food()

    def __handle_input(self):
        key = self.stdscr.getch()
        if key == curses.KEY_RIGHT and self.snake.dir != Direction.LEFT:
            self.snake.dir = Direction.RIGHT
        elif key == curses.KEY_LEFT and self.snake.dir != Direction.RIGHT:
            self.snake.dir = Direction.LEFT
        elif key == curses.KEY_UP and self.snake.dir != Direction.DOWN:
            self.snake.dir = Direction.UP
        elif key == curses.KEY_DOWN and self.snake.dir != Direction.UP:
            self.snake.dir = Direction.DOWN
        elif key == ord(" "):
            self.__pause()

    def __update(self):
        self.snake.update()
        if self.food == self.snake.head:
            self.snake.grow()
            self.score += 1
            # Clear food
            self.stdscr.addstr(self.food[0], self.food[1], " ")
            self.food = None
        if self.food is None:
            self.__spawn_food()

    def __pause(self):
        self.stdscr.timeout(-1)
        text = "PAUSED"
        self.stdscr.addstr(self.center[0], self.center[1] - round(len(text) / 2), text)
        key = None
        while key not in [" "]:
            key = self.stdscr.getkey()
            self.__check_resize()
        self.__redraw_all()
        self.stdscr.timeout(Manager.EVENT_TIMEOUT)

    def __await_resize(self):
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Window is too small. Please resize.")
        while True:
            _ = self.stdscr.getkey()
            if self.__check_resize():
                break
        self.__redraw_all()

    def __check_death(self):
        for pos in self.snake.tail + self.walls:
            if self.snake.head == pos:
                return True
        return False

    def __game_over(self):
        self.stdscr.timeout(-1)
        text_top = "YOU DIED"
        text_mid = "SCORE: %d" % self.score
        new_highscore = False
        if self.score > self.highscore:
            self.highscore = self.score
            new_highscore = True
            write_highscore(self.highscore)
        text_bot = "HIGHSCORE: %d" % self.highscore
        if new_highscore:
            text_bot += " (NEW)"

        self.stdscr.addstr(
            self.center[0] - 2, self.center[1] - round(len(text_top) / 2), text_top
        )
        self.stdscr.addstr(
            self.center[0], self.center[1] - round(len(text_mid) / 2), text_mid
        )
        self.stdscr.addstr(
            self.center[0] + 1, self.center[1] - round(len(text_bot) / 2), text_bot
        )

        self.stdscr.move(0, 0)
        self.stdscr.refresh()
        key = None
        while key not in ["\n", "\r\n", curses.KEY_ENTER, "r", " "]:
            key = self.stdscr.getkey()
            self.__check_resize()
        self.start()

    def __loop(self):
        while True:
            self.__draw()
            self.__handle_input()
            self.__update()
            if self.__check_death():
                break
        self.__game_over()


def main(stdscr):
    manager = Manager(stdscr)
    manager.start()


try:
    curses.wrapper(main)
except KeyboardInterrupt:
    ...
