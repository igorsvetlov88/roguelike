import pygame

from glob import glob
from PIL import Image
from random import choices, choice, randint, uniform, random
from math import ceil

STRUCTURES_RANGE = [10, 50]  # from: _ to: _
EXTENDED_RANGE = [-5, 5]  # from: _ to: _
ENEMIES_MULTI_RANGE = [0.1, 0.3]  # from: _ to: _
FOCUSE_RANGE = [5, 100]
start = {(0, 0): 1, (1, 0): 1, (2, 0): 1, (1, 1): 1, (0, 1): 1, (0, 2): 1, (-1, 1): 1, (-1, 0): 1,
         (-2, 0): 1, (-1, -1): 1, (0, -1): 1, (0, -2): 1, (1, -1): 1}
FPS = 60


def load_image(name, colorkey=None):
    image = pygame.image.load(f"data/{name}")
    if colorkey is not None:
        image.set_colorkey(image.get_at((0, 0)))
    return image


class Weapon:
    def __init__(self, place, damage, im_name):
        self.place = place
        self.damage = damage
        self.image = load_image("weapons/" + im_name)


class Item(pygame.sprite.Sprite):
    def __init__(self, index, im_name, pos, group):
        super().__init__(group)
        self.image = pygame.image.load(f"data/items/{im_name}")
        self.index = index
        self.rect = self.image.get_rect().move(pos)

    def update(self, pos):
        if self.rect.collidepoint(pos):
            return self.index


class Character(pygame.sprite.Sprite):
    def __init__(self, hp, pos, damage, image):
        super().__init__()
        self.image_orig = load_image(image)
        self.image = pygame.transform.scale(self.image_orig, (size, size))
        self.rect = self.image.get_rect()
        self.hp = hp
        self.max_hp = hp
        self.pos = pos
        self.rect.x = 0
        self.rect.y = 0
        self.average_pos = [0, 0]
        self.animated_row = []
        self.damage = damage
        self.cells_per_move = 1 if self.__class__.__name__ == "Player" else self.moves_per_step
        self.animations = [cut_sheet(load_image(f"{self.__class__.__name__.lower()}_walk.png"),
                                     {"Player": 3, "Enemy": 3, "FastEnemy": 3}[
                                         self.__class__.__name__], 1)[0],
                           cut_sheet(load_image(f"{self.__class__.__name__.lower()}_attack.png"),
                                     {"Player": 3, "Enemy": 3, "FastEnemy": 3}[
                                         self.__class__.__name__], 1)[0]]
        self.frame = 0

    def update(self, offset=None):
        if self.animated_row:
            if self.animated_row[0] == "attack":
                if len(self.animated_row) > 1 or self.frame // (FPS // 6) >= len(self.animations[1]):
                    self.frame = 0
                    self.animated_row = self.animated_row[1:]
                else:
                    self.image = pygame.transform.scale(self.animations[1]
                                                        [self.frame // (FPS // 6)], (size, size))
            else:
                self.image = pygame.transform.scale(self.animations[0]
                                                    [self.frame // (FPS // 12) %
                                                     len(self.animations[0])], (size, size))
                next_pos = [self.animated_row[0][0] - self.pos[0],
                            self.animated_row[0][1] - self.pos[1]]
                self.average_pos = [self.average_pos[0] + next_pos[0] / (
                        FPS / (self.cells_per_move / (time_rest * 0.001))),
                                    self.average_pos[1] + next_pos[1] / (
                                            FPS / (self.cells_per_move / (time_rest * 0.001)))]
                if not (-1 < self.average_pos[0] < 1 and -1 < self.average_pos[1] < 1
                        and self.average_pos != [0, 0]):
                    self.pos = tuple(self.animated_row[0])
                    self.animated_row = self.animated_row[1:]
                    self.average_pos = [0, 0]
            self.frame += 1
        else:
            self.frame = 0
            self.image = pygame.transform.scale(self.image_orig, (size, size))
        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = (
            width // 2 - size // 2 - offset[0] + (self.pos[0] + self.average_pos[0]) * size,
            height // 2 - size // 2 - offset[1] + (self.pos[1] + self.average_pos[1]) * size)


class Player(Character):
    def __init__(self, max_hp, pos, damage, image):
        super().__init__(max_hp, pos, damage, image)
        self.floor = 1
        self.moves_per_step = 1
        self.moves_last = self.moves_per_step
        self.kills = 0
        self.items = []
        self.weapon_now = Weapon([[0, -1]], 5, "sword.png")

    def pressed_key(self, event):
        if event[pygame.K_w] or event[pygame.K_s] or event[pygame.K_a] or event[pygame.K_d]:
            self.move(event)
        elif event[pygame.K_UP] or event[pygame.K_DOWN] or event[pygame.K_LEFT] or event[
            pygame.K_RIGHT]:
            self.attack(event)
        if self.hp <= 0:
            global state, focused, drag_offset
            player_death = pygame.mixer.Sound('data\\sounds\\deaths\\player.ogg')
            player_death.play()
            state = "end window"
            focused = False
            drag_offset = [self.pos[0] * size, self.pos[1] * size]

    def move(self, event):
        for args in [[[0, -1], pygame.K_w], [[0, 1], pygame.K_s],
                     [[-1, 0], pygame.K_a], [[1, 0], pygame.K_d]]:
            if check_condition([1, 1, 0, 1], pos=(self.pos[0] + args[0][0],
                                                  self.pos[1] + args[0][1]),
                               event=event, key=args[1]) and self.average_pos == [0, 0]:
                self.animated_row.append([self.pos[0] + args[0][0], self.pos[1] + args[0][1]])
                self.moves_last -= 1
                global can_go_next
                can_go_next = False
                break
        if self.moves_last <= 0:
            self.moves_last = self.moves_per_step
            enemies.update(your_move=True)

    def attack(self, event):
        for args in [[self.weapon_now.place, pygame.K_UP],
                     [rotate(self.weapon_now.place, 2), pygame.K_DOWN],
                     [rotate(self.weapon_now.place, 1), pygame.K_LEFT],
                     [rotate(self.weapon_now.place, 3), pygame.K_RIGHT]]:
            if event[args[1]]:
                for arg in args[0]:
                    AnimatedAttack((width // 2 + (self.pos[0] + arg[0]) * size,
                                    height // 2 + (self.pos[1] + arg[1]) * size))
                self.animated_row.append("attack")
                sound_attack = pygame.mixer.Sound(choice(glob("data\\sounds\\sword\\*.ogg")))
                sound_attack.play()
                global can_go_next
                can_go_next = False
                self.moves_last = self.moves_per_step
                break
        else:
            return
        enemies.update(your_move=True)


class BasicEnemy(Character):
    def __init__(self, hp, damage, pos, view, moves_per_step, image):
        self.moves_per_step = moves_per_step
        super().__init__(hp, pos, damage, image)
        self.pos = pos
        self.cells_of_view = sphere_of_cells(view)
        self.found_radius = view // 2
        self.show_hp = False

    def update(self, offset=None, size_changed=None, your_move=None, check_attack=None, rect=None):
        if self.show_hp:
            pygame.draw.rect(screen, "black", (self.rect.x, self.rect.y, self.rect.width, 1))
            pygame.draw.rect(screen, "red", (self.rect.x, self.rect.y,
                                             round(self.hp / self.max_hp * self.rect.width), 1))
        if self.hp <= 0:
            self.kill()
            # добавить шанс на хилку после смерти?
            # исправить звуки смерти и ударов противников
            death = pygame.mixer.Sound('data\\sounds\\deaths\\FastEnemy.ogg')
            if True:
                heart = Heart(self.pos)
                screen.blit(pygame.Surface((30, 30)), heart.rect)
            death.set_volume(0.3)
            death.play()
        if your_move:
            self.make_step()
        elif check_attack:
            if self.rect.colliderect(rect):
                self.hp -= player.damage + player.weapon_now.damage
                self.show_hp = True
        else:
            super().update(offset)

    def make_step(self):
        if abs(self.pos[0] - player.pos[0]) + abs(self.pos[1] - player.pos[1]) <= self.found_radius:
            lb = {}
            for cell in self.cells_of_view:
                if (self.pos[0] + cell[0], self.pos[1] + cell[1]) in card:
                    lb[(self.pos[0] + cell[0], self.pos[1] + cell[1])] = 0
            sorted_row = [el for el in player.animated_row if el != "attack"]
            need_pos = tuple(sorted_row[0]) if sorted_row else player.pos
            # восклицательный знак над головой
            result = self.find_path(lb, self.pos, need_pos)
            if result and (path := [cell for cell in result if cell != need_pos]):  # <-- path
                self.animated_row.extend(path[:self.moves_per_step])
            elif result is None:  # если нельзя пройти до игрока
                self.make_random_step()
            if result and len(path) < self.moves_per_step:  # если остались ходы
                player.hp -= self.damage
                self.animated_row.append("attack")
                # сделать проверку на класс
                if __class__.__name__ == Enemy:
                    skele_attack = pygame.mixer.Sound(choice(glob("data\\sounds\\skeleton\\*.ogg")))
                    skele_attack.play()
                else:
                    spider_attack = pygame.mixer.Sound(choice(glob("data\\sounds\\spider\\*.ogg")))
                    spider_attack.play()
                AnimatedAttack((width // 2 + need_pos[0] * size, height // 2 + need_pos[1] * size))
        else:
            self.make_random_step()

    def make_random_step(self):
        pos_now = self.pos
        for _ in range(self.moves_per_step):
            variants = []
            for args in [[1, 0], [-1, 0], [0, 1], [0, -1]]:
                if check_condition([1, 1], pos=(pos_now[0] + args[0], pos_now[1] + args[1])):
                    variants.append((pos_now[0] + args[0], pos_now[1] + args[1]))
            if variants:
                pos_now = choice(variants)
                self.animated_row.append(pos_now)

    def find_path(self, lab, start, end):
        copy_lab = lab.copy()
        self.find_lab_tuples([start], copy_lab)
        now = end
        path = []
        while now != start:
            path.append(now)
            now = copy_lab.get(now, None)
            if not now:
                path = None
                break
        if path:
            path.reverse()
        return path

    def find_lab_tuples(self, nexts, lb):
        new_nexts = []
        for now in nexts:
            for args in [[-1, 0], [1, 0], [0, -1], [0, 1]]:
                if check_condition([1, 1, 1, 0, 1], pos=(now[0] + args[0], now[1] + args[1]),
                                   flat=lb):
                    lb[now[0] + args[0], now[1] + args[1]] = now
                    new_nexts.append((now[0] + args[0], now[1] + args[1]))
        if new_nexts:
            self.find_lab_tuples(new_nexts, lb)


class Enemy(BasicEnemy):
    def __init__(self, hp, damage, pos, view, moves_per_step, image):
        super().__init__(hp, damage, pos, view, moves_per_step, image)


class FastEnemy(BasicEnemy):
    def __init__(self, hp, damage, pos, view, moves_per_step, image):
        super().__init__(hp, damage, pos, view, moves_per_step, image)


class AnimatedAttack(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__(attacks_group)
        self.frames, self.width, self.height = \
            cut_sheet(load_image("attack.png"), 5, 1)
        self.cur_frame = 0
        self.x, self.y = pos
        self.checked = False
        self.image = pygame.transform.scale(self.frames[self.cur_frame], (size, size))
        self.rect = self.image.get_rect()
        self.delitel = 5

    def update(self, offset=None, check_attack=False):
        if check_attack:
            if not self.checked:
                enemies.update(check_attack=True,
                               rect=(self.x - offset[0] - self.image.get_width() // 2,
                                     self.y - offset[1] - self.image.get_height() // 2, size, size))
                self.checked = True
        elif self.cur_frame < len(self.frames) * self.delitel:
            self.rect.x = self.x - offset[0] - self.image.get_width() // 2
            self.rect.y = self.y - offset[1] - self.image.get_height() // 2
            self.image = pygame.transform.scale(self.frames[self.cur_frame // self.delitel],
                                                (size, size))
            self.cur_frame += 1
        else:
            self.kill()


def on_pickup():
    if player.hp + 3 > player.max_hp:
        diff = player.max_hp - player.hp
        player.hp += diff
    else:
        player.hp += 3


class Heart(pygame.sprite.Sprite):
    def __init__(self, pos=None, ):
        super().__init__()
        pygame.sprite.Sprite.__init__(self)
        self.pos = pos
        self.image = pygame.image.load('heart.png')
        self.rect = self.image.get_rect(topleft=(self.pos[0], self.pos[1]))


items = [[0, "item1.png"], [1, "item2.png"], [2, "item3.png"]]
weapons = [Weapon([[0, -1], [0, -2]], 10, "sword1.png")]


def cut_sheet(sheet, columns, rows):
    rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                       sheet.get_height() // rows)
    frames = []
    for j in range(rows):
        for i in range(columns):
            frame_location = (rect.w * i, rect.h * j)
            frames.append(sheet.subsurface(pygame.Rect(
                frame_location, rect.size)))
    return frames, rect.w, rect.h


def get_offset():
    global size, focused, drag_offset
    return [(player.pos[0] + player.average_pos[0]) * size,
            (player.pos[1] + player.average_pos[1]) * size] if focused else drag_offset


def check_condition(variants, pos=None, flat=None, event=None, key=None):
    if flat is None:
        flat = card
    flag = True
    if len(variants) >= 1 and variants[0]:
        flag = flag and pos in flat
    if len(variants) >= 2 and variants[1]:
        flag = flag and all([pos != en.pos for en in enemies])
    if len(variants) >= 3 and variants[2]:
        flag = flag and type(flat[pos]) != tuple
    if len(variants) >= 4 and variants[3]:
        flag = flag and event[key]
    if len(variants) >= 5 and variants[4]:
        flag = flag and pos != player.animated_row[0]
    return flag


def load_new_place(filename):
    new = []
    f = open("data/" + filename, "r", encoding="utf-8")
    firsts = []
    for i, row in enumerate(f.read().split("\n")):
        for j, symb in enumerate(row):
            if symb == "*":
                if not firsts:
                    firsts = [j, i]
                new.append([j - firsts[0], i - firsts[1]])
    return new


def rotate(place, to):
    if to == 0:
        return place
    elif to == 1:
        return [[coord[1], coord[0]] for coord in place]
    elif to == 2:
        return [[-coord[0], -coord[1]] for coord in place]
    elif to == 3:
        return [[-coord[1], -coord[0]] for coord in place]


def sphere_of_cells(diametr):
    cells_of_diametr = []
    for i in range(-(diametr // 2), diametr // 2 + 1):
        for j in range(-(diametr // 2 - abs(i)), diametr // 2 - abs(i) + 1):
            cells_of_diametr.append((j, i))
    return cells_of_diametr


# добавить фоновую музыку
# изменить цвет платформ?
def make_new_level():
    global card, exit_ladder, enemies, focused, chest, field_rect, drag_offset, chest_looted, usually_lvl, floor_weapons
    usually_lvl = player.floor <= 1 or randint(0, round(5 * (2 - hardness))) != 0
    structures = int(randint(STRUCTURES_RANGE[0], STRUCTURES_RANGE[1]) * hardness)
    extended = uniform(EXTENDED_RANGE[0], EXTENDED_RANGE[1]) if usually_lvl else -10
    card = start.copy()
    for i in range(structures):
        draw_loading_bar(i / structures)
        cells = []
        for cell in card:
            if (cell[0] + 1, cell[1]) not in card:
                cells.append((cell[0] + 1, cell[1]))
            if (cell[0] - 1, cell[1]) not in card:
                cells.append((cell[0] - 1, cell[1]))
            if (cell[0], cell[1] + 1) not in card:
                cells.append((cell[0], cell[1] + 1))
            if (cell[0], cell[1] - 1) not in card:
                cells.append((cell[0], cell[1] - 1))

        first = choices(cells,
                        weights=[pow((abs(cell[0]) + abs(cell[1])), extended) for cell in cells])[0]
        for coord in rotate(choice(places), randint(0, 3)):
            card[first[0] + coord[0], first[1] + coord[1]] = 1

    max_cell = (0, 0)
    for key in card:
        if abs(key[0]) + abs(key[1]) > abs(max_cell[0]) + abs(max_cell[1]):
            max_cell = key
    exit_ladder = choice([(max_cell[0] + cell[0], max_cell[1] + cell[1])
                          for cell in sphere_of_cells(20)
                          if (max_cell[0] + cell[0], max_cell[1] + cell[1]) in card])

    enemies = pygame.sprite.Group()
    flat = card.copy()
    flat2 = flat.copy()
    [flat.pop(cell) for cell in sphere_of_cells(20) if cell in flat]
    numb_enemies = int(structures * uniform(ENEMIES_MULTI_RANGE[0], ENEMIES_MULTI_RANGE[1]))
    for i in range(numb_enemies):
        cell = choice(list(flat))
        enemies.add(choices([Enemy(30 * hardness, 1, cell, round(10 * hardness), 1, "Enemy_test.png"),
                             FastEnemy(20, 1, cell, round(15 * hardness), 3, "FastEnemy_test.png")],
                            weights=[6, player.floor])[0])
        flat.pop(cell)

    flat2.pop((0, 0))
    flat2.pop(exit_ladder)
    chest = choices(list(flat2), weights=[pow(abs(cell[0] - exit_ladder[0]) +
                                              abs(cell[1] - exit_ladder[1]) + abs(cell[0]) +
                                              abs(cell[1]), 3 * hardness) for cell in flat2])[0]

    focused = True
    chest_looted = False
    player.pos = (0, 0)
    field_rect = [sorted(card.keys(), key=lambda x: x[0])[0][0],
                  sorted(card.keys(), key=lambda x: x[1])[0][1],
                  sorted(card.keys(), key=lambda x: x[0], reverse=True)[0][0] + 1,
                  sorted(card.keys(), key=lambda x: x[1], reverse=True)[0][1] + 1]
    drag_offset = [0, 0]

    flat2.pop(chest)
    floor_weapons = []
    if randint(0, round(0.5 + hardness * 2)) == 0:
        for _ in range(randint(1, round(2.5 - hardness))):
            floor_weapons.append([choice(list(flat2.keys())), choice(weapons)])

    enemies.update(offset=get_offset())
    make_surface_field()


def make_surface_field():
    global floor_field, floor_field_sized, usually_lvl
    """ниже создается surface, где отображены все клетки сразу, которые не будут меняться"""
    list_of_tiles = []
    for tile in [f"floor{i}.png" for i in range(1, 5)]:
        floor = load_image("floors/floor1_test.png")
        floor = pygame.transform.scale(floor, (FOCUSE_RANGE[1], FOCUSE_RANGE[1]))
        list_of_tiles.append(floor)

    floor_field = pygame.Surface(
        ((field_rect[2] - field_rect[0]) * FOCUSE_RANGE[1], (field_rect[3] -
                                                             field_rect[1]) * FOCUSE_RANGE[1]))
    for cell in card.keys():
        tile = choices(list_of_tiles, weights=[1, 0.05, 0.05, 0.005])[0]
        tile = pygame.transform.rotate(tile, randint(0, 3) * 90)
        floor_field.blit(tile, ((cell[0] - field_rect[0]) * FOCUSE_RANGE[1],
                                (cell[1] - field_rect[1]) * FOCUSE_RANGE[1]))
        if cell == exit_ladder and usually_lvl:
            tile = load_image("exit_ladder.png")
            tile = pygame.transform.scale(tile, (FOCUSE_RANGE[1], FOCUSE_RANGE[1]))
        else:
            continue
        floor_field.blit(tile, ((cell[0] - field_rect[0]) * FOCUSE_RANGE[1],
                                (cell[1] - field_rect[1]) * FOCUSE_RANGE[1]))
    pygame.image.save(floor_field, "picture.png")

    floor_field_sized = pygame.transform.scale(floor_field,
                                               ((field_rect[2] - field_rect[0]) * size,
                                                (field_rect[3] - field_rect[1]) * size))


def end():
    pygame.quit()
    exit()


def draw_main_game():
    global drag_offset, drag, focused, can_go_next, time_for_next, floor_field_sized, size, \
        state, chest_looted, usually_lvl, floor_weapons
    screen.fill('black')
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            end()
        elif event.type == pygame.MOUSEWHEEL:
            last_size = size
            if size + ceil(event.y * (size / 10)) > FOCUSE_RANGE[1]:
                size = FOCUSE_RANGE[1]
            elif size + ceil(event.y * (size / 10)) < FOCUSE_RANGE[0]:
                size = FOCUSE_RANGE[0]
            else:
                size += ceil(event.y * (size / 10))
            drag_offset = [round(drag_offset[0] * (size / last_size)),
                           round(drag_offset[1] * (size / last_size))]
            floor_field_sized = pygame.transform.scale(floor_field,
                                                       ((field_rect[2] - field_rect[0]) * size,
                                                        (field_rect[3] - field_rect[1]) * size))
            enemies.update(offset=get_offset())
            player_group.update(offset=get_offset())
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            drag = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            drag = False
        elif event.type == pygame.MOUSEMOTION and drag:
            drag_offset = [drag_offset[i] - event.rel[i] for i in range(2)]
            focused = False
            focused = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_f:
                focused = not focused
                drag_offset = [player.pos[0] * size, player.pos[1] * size]
            elif event.key == pygame.K_e:
                if player.pos == exit_ladder and (usually_lvl or len(enemies) == 0):
                    player.floor += 1
                    exit_sound = pygame.mixer.Sound('data\\sounds\\other\\exit_sound.ogg')
                    exit_sound.play()
                    make_new_level()
                elif player.pos == chest and not chest_looted:
                    state = "choice item"
                elif result := [weapon for weapon in floor_weapons if weapon[0] == (
                        tuple(player.animated_row[0]) if player.animated_row else player.pos)]:
                    floor_weapons.remove(result[0])
                    floor_weapons.append([result[0][0], player.weapon_now])
                    player.weapon_now = result[0][1]
                elif player.pos == Heart and player.hp != player.max_hp:
                    on_pickup()
        elif event.type == MYEVENTTYPE:
            if not can_go_next:
                time_for_next += timer_speed
            if time_for_next >= time_rest:
                can_go_next = True
                time_for_next = 0
        if pygame.key.get_pressed() and can_go_next and all(
                [len(enemy.animated_row) == 0 for enemy in enemies]):
            player.pressed_key(pygame.key.get_pressed())
    offset = get_offset()
    draw_field(offset)
    draw_player(offset)
    attacks_group.update(offset)
    attacks_group.update(check_attack=True, offset=offset)
    attacks_group.draw(screen)
    # зачем тебе время до следующего хода?
    pygame.draw.arc(screen, (255, 255, 0), (50, height - 100, 50, 50), 90 / 57.2958,
                    360 / 57.2958 * (time_for_next / time_rest) +
                    90 / 57.2958, 25)
    pygame.draw.arc(screen, (255, 150, 0), (50, height - 100, 50, 50), 90 / 57.2958,
                    360 / 57.2958 * (time_for_next / time_rest) +
                    90 / 57.2958, 5)  # время до следующего хода

    text = pygame.font.Font(None, 50).render(str(player.moves_last), True, (255, 255, 255))
    screen.blit(text, (50 + 25 - text.get_width() // 2, height - 100 + 25 - text.get_height() // 2))
    # мне кажется такая полоска выглядит лучше
    draw_ui(screen)
    # hp_bar_height = 200
    # hp_bar_line_width = 2
    # pygame.draw.rect(screen, (100, 100, 100), (10, 10, 30, hp_bar_height))
    # for i in range(player.max_hp):
    #     pygame.draw.rect(
    #         screen, (255, 0, 0) if i < player.hp else (10, 10, 10),
    #         (12, 12 + i * ((hp_bar_height - hp_bar_line_width * (player.max_hp + 1)) /
    #                        player.max_hp + hp_bar_line_width), 26,
    #          (hp_bar_height - hp_bar_line_width * (player.max_hp + 1)) / player.max_hp))
    pygame.display.flip()
    clock.tick(FPS)


def draw_ui(screen):
    font = pygame.font.SysFont('comic sans', 32)
    health = font.render(f'Здоровье: {player.hp} / {player.max_hp}', False, (255, 255, 255))
    screen.blit(health, (20, 50))
    if player.hp <= 0:
        pass
    else:
        pygame.draw.line(screen, (54, 54, 54), start_pos=(20, 30), end_pos=(100 * player.max_hp, 30), width=23)
        pygame.draw.line(screen, (240, 0, 0), start_pos=(20, 30), end_pos=(100 * player.hp, 30), width=20)


def draw_loading_bar(percent, width_lb=500, height_lb=50, text_under_lb=50):
    screen.fill("black")
    pygame.draw.rect(screen, (255, 255, 255), (
        (width - width_lb) // 2, (height - height_lb) // 2, width_lb, height_lb), 1)
    pygame.draw.rect(screen, (255, 255, 255), (
        (width - width_lb) // 2, (height - height_lb) // 2, percent * width_lb,
        height_lb))
    text = pygame.font.Font(None, 50).render(f"{round(percent * 100, 1)}%", True, (255, 255, 255))
    screen.blit(text, ((width - text.get_width()) // 2, (height - height_lb) // 2 +
                       height_lb + text_under_lb))
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            end()
    pygame.display.flip()


def draw_start_window(start_window_sizes=[800, 100], hardness_under=100):
    global state, player, drag, can_go_next, time_for_next, drag_offset, size, player_group, hardness

    drag_hd = False

    start_window_borders = [(width - start_window_sizes[0]) // 2,
                            (height - start_window_sizes[1]) // 2]
    start_window_borders.extend([start_window_borders[0] + start_window_sizes[0],
                                 start_window_borders[1] + start_window_sizes[1]])
    while True:
        screen.fill("black")
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                end()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 \
                    and start_window_borders[0] <= event.pos[0] <= start_window_borders[2] \
                    and start_window_borders[1] <= event.pos[1] <= start_window_borders[3]:
                state = "main"
                drag = False
                can_go_next = True
                time_for_next = 0
                drag_offset = [0, 0]
                size = FOCUSE_RANGE[1]
                player_group = pygame.sprite.Group()
                player = Player(10, (0, 0), 5, "player.png")
                player_group.add(player)

                make_new_level()
                return
            elif event.type == pygame.MOUSEBUTTONDOWN and start_window_borders[0] <= \
                    event.pos[0] <= start_window_borders[2] and start_window_borders[3] + \
                    hardness_under - 10 <= event.pos[1] <= start_window_borders[3] + \
                    hardness_under + 10:
                drag_hd = True
                hardness = (event.pos[0] - start_window_borders[0]) / start_window_sizes[0] + 0.5
            elif event.type == pygame.MOUSEBUTTONUP:
                drag_hd = False
            elif event.type == pygame.MOUSEMOTION and drag_hd:
                next_hardness = \
                    (event.pos[0] - start_window_borders[0]) / start_window_sizes[0] + 0.5
                if next_hardness > 1.5:
                    next_hardness = 1.5
                elif next_hardness < 0.5:
                    next_hardness = 0.5
                hardness = next_hardness

        pygame.draw.rect(screen, "green", (start_window_borders[0], start_window_borders[1],
                                           start_window_sizes[0], start_window_sizes[1]), 1)
        text = pygame.font.Font(None, 100).render("START", True, "green")
        screen.blit(text, ((width - text.get_width()) // 2, (height - text.get_height()) // 2))

        pygame.draw.rect(screen, "white", (start_window_borders[0], start_window_borders[3] +
                                           hardness_under, start_window_sizes[0], 2))
        pygame.draw.rect(screen, "white", (start_window_borders[0] + (hardness - 0.5) *
                                           start_window_sizes[0] - 2, start_window_borders[3] +
                                           hardness_under - 10, 4, 22))

        pygame.draw.rect(screen, "white", (start_window_borders[0], start_window_borders[3] +
                                           hardness_under - 2, 2, 6))
        text = pygame.font.Font(None, 50).render("0.5", True, "white")
        screen.blit(text, (start_window_borders[0] - text.get_width() // 2, start_window_borders[3] +
                           hardness_under + text.get_height() // 2))

        pygame.draw.rect(screen, "white", (start_window_borders[0] + start_window_sizes[0] // 2,
                                           start_window_borders[3] + hardness_under - 2, 2, 6))
        text = pygame.font.Font(None, 50).render("1.0", True, "white")
        screen.blit(text, (start_window_borders[0] + start_window_sizes[0] // 2 -
                           text.get_width() // 2, start_window_borders[3] +
                           hardness_under + text.get_height() // 2))

        pygame.draw.rect(screen, "white", (start_window_borders[2],
                                           start_window_borders[3] + hardness_under - 2, 2, 6))
        text = pygame.font.Font(None, 50).render("1.5", True, "white")
        screen.blit(text, (start_window_borders[2] - text.get_width() // 2, start_window_borders[3] +
                           hardness_under + text.get_height() // 2))

        pygame.display.flip()


def draw_end_window(end_window_sizes=[200, 400], exit_button_sizes=[200, 50],
                    text_under_end_window=20):
    global size, drag_offset, drag, focused, state, floor_field_sized, chest_looted, usually_lvl
    end_window_borders = [width - end_window_sizes[0] - 20, 20, end_window_sizes[0],
                          end_window_sizes[1]]
    screen.fill("black")
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            end()
        elif event.type == pygame.MOUSEWHEEL and (size != FOCUSE_RANGE[0] or event.y > 0) and \
                (size != FOCUSE_RANGE[1] or event.y < 0):
            if size + event.y > FOCUSE_RANGE[1]:
                event.y = FOCUSE_RANGE[1]
            elif size + event.y < FOCUSE_RANGE[0]:
                event.y = FOCUSE_RANGE[0]
            size += event.y
            drag_offset = [round(drag_offset[0] * (size / (size - event.y))),
                           round(drag_offset[1] * (size / (size - event.y)))]
            floor_field_sized = pygame.transform.scale(floor_field,
                                                       ((field_rect[2] - field_rect[0]) * size,
                                                        (field_rect[3] - field_rect[1]) * size))
            enemies.update(offset=get_offset())
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if end_window_borders[0] + end_window_borders[2] // 2 - exit_button_sizes[0] // 2 <= \
                    event.pos[0] <= end_window_borders[0] + end_window_borders[2] // 2 - \
                    exit_button_sizes[0] // 2 + exit_button_sizes[0] and end_window_borders[1] + \
                    end_window_borders[3] + text_under_end_window <= event.pos[1] <= \
                    end_window_borders[1] + end_window_borders[3] + \
                    text_under_end_window + exit_button_sizes[1]:
                attacks_group.empty()
                state = "start window"
            drag = True
        elif event.type == pygame.MOUSEBUTTONUP:
            drag = False
        elif event.type == pygame.MOUSEMOTION and drag:
            drag_offset = [drag_offset[i] - event.rel[i] for i in range(2)]
            focused = False

    draw_field(get_offset())

    pygame.draw.rect(screen, (255, 255, 255), (end_window_borders[0], end_window_borders[1],
                                               end_window_borders[2], end_window_borders[3]), 1)
    pygame.draw.rect(screen, (0, 0, 0), (end_window_borders[0] + 1, end_window_borders[1] + 1,
                                         end_window_borders[2] - 2, end_window_borders[3] - 2))
    text = pygame.font.Font(None, 30).render(f"floor - {player.floor}", True, (255, 255, 255))
    screen.blit(text, (end_window_borders[0] + 10, end_window_borders[1] + 10))
    text = pygame.font.Font(None, 30).render(f"kills - {player.kills}", True, (255, 255, 255))
    screen.blit(text, (end_window_borders[0] + 10, end_window_borders[1] + 30))

    pygame.draw.rect(screen, (255, 255, 255), (end_window_borders[0] +
                                               end_window_borders[2] // 2 -
                                               exit_button_sizes[0] // 2,
                                               end_window_borders[1] +
                                               end_window_borders[3] + text_under_end_window,
                                               exit_button_sizes[0], exit_button_sizes[1]), 1)
    pygame.draw.rect(screen, (0, 0, 0), (end_window_borders[0] +
                                         end_window_borders[2] // 2 -
                                         exit_button_sizes[0] // 2 + 1,
                                         end_window_borders[1] +
                                         end_window_borders[3] + text_under_end_window + 1,
                                         exit_button_sizes[0] - 2, exit_button_sizes[1] - 2))
    text = pygame.font.Font(None, 50).render("EXIT", True, (255, 255, 255))
    screen.blit(text, (end_window_borders[0] +
                       end_window_borders[2] // 2 -
                       exit_button_sizes[0] // 2 + (exit_button_sizes[0] - text.get_width()) // 2,
                       end_window_borders[1] +
                       end_window_borders[3] + text_under_end_window + (
                               exit_button_sizes[1] - text.get_height()) // 2,
                       exit_button_sizes[0], exit_button_sizes[1]))
    pygame.display.flip()


# имхо в сундуке должен лежать один предмет, лучше на переходе в след этаж давать выбор
def draw_choice_item(item_size=200):
    global player, size, focused, drag_offset, state, chest_looted
    offset = get_offset()
    copy_items = items.copy()
    items_for_choice = []
    for _ in range(3):
        items_for_choice.append(
            choices(copy_items, weights=[len(player.items) - player.items.count(item) + 1
                                         for item in copy_items])[0])
        copy_items.remove(items_for_choice[-1])
    items_group = pygame.sprite.Group()
    for i, coord in enumerate([[width // 4 - item_size // 2, height // 4 - item_size // 2],
                               [width // 4 * 2 - item_size // 2, height // 4 * 3 - item_size // 2],
                               [width // 4 * 3 - item_size // 2, height // 4 - item_size // 2]]):
        Item(items_for_choice[i][0], items_for_choice[i][1], coord, items_group)

    while state == "choice item":
        screen.fill("black")

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                end()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if result := [item.update(event.pos) for item in items_group
                              if item.update(event.pos) is not None]:
                    use_item(result[0])
                    chest_sound = pygame.mixer.Sound('data\\sounds\\other\\chest_open.ogg')
                    chest_sound.set_volume(0.4)
                    chest_sound.play()
                    chest_looted = True
                    state = "main"
                    break
        draw_field(offset)
        draw_chest(offset)
        draw_player(offset)
        items_group.draw(screen)
        pygame.display.flip()


# добавить картинок к вещам
# добавить ещё вещей?
def use_item(index):
    player.items.append(index)
    if index == 0:
        player.max_hp += 1
        player.hp = player.max_hp
    elif index == 1:
        player.damage += 5
    elif index == 2:
        player.moves_per_step += 1


def draw_field(offset):
    screen.blit(floor_field_sized,
                (width // 2 - offset[0] - size // 2 + field_rect[0] * size,
                 height // 2 - offset[1] - size // 2 + field_rect[1] * size))  # поле
    draw_floor_weapons(offset)
    if not chest_looted:
        draw_chest(offset)
    if usually_lvl or len(enemies) == 0:
        draw_exit_ladder(offset)
    enemies.update(offset)
    enemies.draw(screen)


def draw_player(offset):
    player_group.update(offset)
    player_group.draw(screen)


def draw_chest(offset):
    global chest_looted
    if not chest_looted:
        copy_chest = pygame.transform.scale(chest_im, (size, size))
        screen.blit(copy_chest, (width // 2 + chest[0] * size - size // 2 - offset[0],
                                 height // 2 + chest[1] * size - size // 2 - offset[1]))


def draw_exit_ladder(offset):
    copy_exit_ladder = pygame.transform.scale(exit_ladder_im, (size, size))
    screen.blit(copy_exit_ladder, (width // 2 + exit_ladder[0] * size - size // 2 - offset[0],
                                   height // 2 + exit_ladder[1] * size - size // 2 - offset[1]))


def draw_floor_weapons(offset):
    global floor_weapons
    for weapon in floor_weapons:
        image = pygame.transform.scale(weapon[1].image, (size, size))
        screen.blit(image, (width // 2 - image.get_width() // 2 - offset[0] + weapon[0][0] * size,
                            height // 2 - image.get_height() // 2 - offset[1] + weapon[0][1] * size))


# сделаю меню чуть позже
pygame.init()
width, height = (1000, 1000) if input() == "" else (pygame.display.Info().current_w, pygame.display.Info().current_h)
screen = pygame.display.set_mode((width, height))
hardness = 1
MYEVENTTYPE = pygame.USEREVENT + 1
timer_speed = 10
time_rest = 250  # промежуток между ходами в миллисекундах
clock = pygame.time.Clock()
pygame.time.set_timer(MYEVENTTYPE, timer_speed)
attacks_group = pygame.sprite.Group()
places = [load_new_place(f"places/place{i}.txt") for i in range(1, 6)]
chest_im = load_image("chest_test.png")
exit_ladder_im = load_image("exit_ladder.png")
icon = pygame.image.load('heart.png')
pygame.display.set_icon(icon)
pygame.display.set_caption('roguelike dungeon')
print('testing')

if __name__ == '__main__':
    state = "start window"
    while True:
        if state == "main":
            draw_main_game()
        elif state == "start window":
            draw_start_window()
        elif state == "end window":
            draw_end_window()
        elif state == "choice item":
            draw_choice_item()
