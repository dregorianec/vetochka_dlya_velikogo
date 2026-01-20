import arcade
import enum
import math


class FaceDirection(enum.Enum):
    LEFT = 0
    RIGHT = 1


SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 1100
SCREEN_TITLE = "Спрайтовый герой"


class Hero(arcade.Sprite):
    def __init__(self):
        super().__init__()

        # Основные характеристики
        self.scale = 1.0
        self.speed = 250
        self.health = 100   
        
        # Загрузка текстур
        self.idle_texture = arcade.load_texture("pictures/anim/скелет/стоять на месте.png")
        self.texture = self.idle_texture
        
        self.walk_textures = []
        texture = arcade.load_texture("pictures/anim/скелет/идти в право 1.png")
        self.walk_textures.append(texture)
        texture = arcade.load_texture("pictures/anim/скелет/идти в право 2.png")
        self.walk_textures.append(texture)
            
        self.current_texture = 0
        self.texture_change_time = 0
        self.texture_change_delay = 0.1  # секунд на кадр
        
        self.is_walking = False # Никуда не идём
        self.face_direction = FaceDirection.RIGHT  # и смотрим вправо

        # Центрируем персонажа
        self.center_x = SCREEN_WIDTH // 2
        self.center_y = SCREEN_HEIGHT // 2

    def update_animation(self, delta_time: float = 1/60):
        """ Обновление анимации """
        if self.is_walking:
            self.texture_change_time += delta_time
            if self.texture_change_time >= self.texture_change_delay:
                self.texture_change_time = 0
                self.current_texture += 1
                if self.current_texture >= len(self.walk_textures):
                    self.current_texture = 0
                # Поворачиваем текстуру в зависимости от направления взгляда
                if self.face_direction == FaceDirection.RIGHT:
                    self.texture = self.walk_textures[self.current_texture]
                else:
                    self.texture = self.walk_textures[self.current_texture].flip_horizontally()

        else:
            # Если не идём, то просто показываем текстуру покоя
            # и поворачиваем её в зависимости от направления взгляда
            if self.face_direction == FaceDirection.RIGHT:
                self.texture = self.idle_texture
            else:
                self.texture = self.idle_texture.flip_horizontally()

       
    def update(self, delta_time, keys_pressed):
        """ Перемещение персонажа """
        # В зависимости от нажатых клавиш определяем направление движения
        dx, dy = 0, 0
        if arcade.key.LEFT in keys_pressed or arcade.key.A in keys_pressed:
            dx -= self.speed * delta_time
        if arcade.key.RIGHT in keys_pressed or arcade.key.D in keys_pressed:
            dx += self.speed * delta_time
        if arcade.key.UP in keys_pressed or arcade.key.W in keys_pressed:
            dy += self.speed * delta_time
        if arcade.key.DOWN in keys_pressed or arcade.key.S in keys_pressed:
            dy -= self.speed * delta_time

        if dx != 0 and dy != 0:
            factor = 0.7071
            dx *= factor
            dy *= factor

        self.center_x += dx
        self.center_y += dy
        # Поворачиваем персонажа в зависимости от направления движения
        # Если никуда не идём, то не меняем направление взгляда
        if dx < 0:
            self.face_direction = FaceDirection.LEFT
        elif dx > 0:
            self.face_direction = FaceDirection.RIGHT

        # Проверка на движение
        self.is_walking = dx or dy



class Bullet(arcade.Sprite):
    __texture = arcade.load_texture("pictures/photo/missile.png")

    def __init__(self, start_x, start_y, target_x, target_y, speed=800, damage=10, pierce_count=0):
        super().__init__()
        self.texture = self.__texture
        self.center_x = start_x
        self.center_y = start_y
        self.start_x = start_x
        self.start_y = start_y
        self.scale = 0.1
        self.speed = speed
        self.damage = damage
        self.max_distance = 1500  # Максимальная дистанция полёта
        self.pierce_count = pierce_count  # Сколько врагов может пробить
        self.pierced_enemies = set()  # Уже пробитые враги (их id)
        
        x_diff = target_x - start_x
        y_diff = target_y - start_y
        angle = math.atan2(y_diff, x_diff)

        self.change_x = math.cos(angle) * speed
        self.change_y = math.sin(angle) * speed
        self.angle = math.degrees(-angle)  # Поворот пули
        
    def update(self, delta_time):
        self.center_x += self.change_x * delta_time
        self.center_y += self.change_y * delta_time
        
        # Удаляем пулю, если она улетела слишком далеко от точки выстрела
        dist = math.sqrt((self.center_x - self.start_x)**2 + (self.center_y - self.start_y)**2)
        if dist > self.max_distance:
            self.remove_from_sprite_lists()


class Slime(arcade.Sprite):
    def __init__(self, x, y, speed=100, damage=10, hp=1):
        super().__init__(scale=0.3)
        self.walk_textures = []
        for i in range(1, 9):
            self.walk_textures.append(
                arcade.load_texture(f"pictures/anim/слизень/{i}.png")
            )
        self.current_texture = 0
        self.texture_change_time = 0
        self.texture_change_delay = 0.12  # секунд на кадр
        self.texture = self.walk_textures[self.current_texture]
        self.speed = speed
        self.damage = damage
        self.hp = hp  # Здоровье врага
        self.max_hp = hp
        self.center_x = x
        self.center_y = y
        
    def follow_player(self, player, delta_time, wall_list):
        dx = player.center_x - self.center_x
        dy = player.center_y - self.center_y
        
        distance = math.sqrt(dx**2 + dy**2)
        if distance > 0:
            dx = dx / distance
            dy = dy / distance
            old_x = self.center_x
            old_y = self.center_y
            
            self.center_x += dx * self.speed * delta_time
            self.center_y += dy * self.speed * delta_time
            hit_wall = arcade.check_for_collision_with_list(self, wall_list)
            if hit_wall:
                self.center_x = old_x
                self.center_y = old_y
                self.center_x = old_x + dx * self.speed * delta_time
                self.center_y = old_y
                hit_wall_x = arcade.check_for_collision_with_list(self, wall_list)
                if hit_wall_x:
                    self.center_x = old_x
                
                self.center_y = old_y + dy * self.speed * delta_time
                hit_wall_y = arcade.check_for_collision_with_list(self, wall_list)
                if hit_wall_y:
                    self.center_y = old_y

    def update_animation(self, delta_time: float = 1 / 60):
        self.texture_change_time += delta_time
        if self.texture_change_time >= self.texture_change_delay:
            self.texture_change_time = 0
            self.current_texture += 1
            if self.current_texture >= len(self.walk_textures):
                self.current_texture = 0
            self.texture = self.walk_textures[self.current_texture]


class Boss(arcade.Sprite):
    """Мини-босс с уникальными механиками"""
    
    def __init__(self, x, y, boss_type=1, base_hp=1):
        super().__init__()
        self.boss_type = boss_type
        self.center_x = x
        self.center_y = y
        self.speed = 80  # Медленнее обычных врагов
        
        # HP в 30 раз больше базового HP врагов
        self.max_hp = base_hp * 30
        self.hp = self.max_hp
        
        # Визуальные параметры
        self.base_size = 80  # Большой размер
        self.pulse_timer = 0
        self.pulse_speed = 2.0
        
        # Атаки
        self.attack_timer = 0
        self.attack_cooldown = 3.5  # 3-4 секунды между атаками
        
        # Орбиты для первого босса
        self.orbit_angle = 0
        self.orbit_speed = 2.5  # Скорость вращения орбит
        self.num_orbs = 4 if boss_type == 1 else 0
        self.orb_distance = 100  # Расстояние орбит от центра
        
        # Для второго босса - телепортация
        self.teleport_timer = 0
        self.teleport_cooldown = 8.0  # Телепортируется каждые 8 секунд
        self.is_teleporting = False
        self.teleport_flash = 0
        
        # Цвета для разных боссов
        if boss_type == 1:
            self.color = (200, 50, 50)  # Красный - "Страж"
            self.name = "СТРАЖ ОРБИТ"
        else:
            self.color = (50, 50, 200)  # Синий - "Снайпер"  
            self.name = "АСТРАЛЬНЫЙ СТРЕЛОК"
            self.attack_cooldown = 3.0
        
        # Эффект появления
        self.spawn_timer = 2.0  # 2 секунды анимации появления
        self.is_spawning = True
        
    def update(self, delta_time, player, wall_list):
        """Обновление босса"""
        # Анимация появления
        if self.is_spawning:
            self.spawn_timer -= delta_time
            if self.spawn_timer <= 0:
                self.is_spawning = False
            return
        
        # Пульсация размера
        self.pulse_timer += delta_time * self.pulse_speed
        pulse = 1.0 + 0.1 * math.sin(self.pulse_timer)
        
        # Движение к игроку
        dx = player.center_x - self.center_x
        dy = player.center_y - self.center_y
        distance = math.sqrt(dx**2 + dy**2)
        
        if distance > 0:
            dx /= distance
            dy /= distance
            
            old_x, old_y = self.center_x, self.center_y
            self.center_x += dx * self.speed * delta_time
            self.center_y += dy * self.speed * delta_time
            
            # Ломаем стены на пути
            hit_walls = arcade.check_for_collision_with_list(self, wall_list)
            for wall in hit_walls:
                wall.remove_from_sprite_lists()
        
        # Вращение орбит для первого босса
        if self.boss_type == 1:
            self.orbit_angle += self.orbit_speed * delta_time
        
        # Телепортация для второго босса
        if self.boss_type == 2:
            self.teleport_timer += delta_time
            if self.teleport_timer >= self.teleport_cooldown:
                self.teleport_timer = 0
                self.is_teleporting = True
                self.teleport_flash = 0.5
        
        # Таймер атаки
        self.attack_timer += delta_time
        
    def get_orb_positions(self):
        """Возвращает позиции орбит для первого босса"""
        positions = []
        for i in range(self.num_orbs):
            angle = self.orbit_angle + (2 * math.pi * i / self.num_orbs)
            ox = self.center_x + math.cos(angle) * self.orb_distance
            oy = self.center_y + math.sin(angle) * self.orb_distance
            positions.append((ox, oy))
        return positions
    
    def should_attack(self):
        """Проверяет, нужно ли атаковать"""
        if self.attack_timer >= self.attack_cooldown:
            self.attack_timer = 0
            return True
        return False


class BossProjectile(arcade.Sprite):
    """Снаряд босса"""
    
    def __init__(self, start_x, start_y, target_x, target_y, speed=300):
        super().__init__()
        self.center_x = start_x
        self.center_y = start_y
        self.start_x = start_x
        self.start_y = start_y
        self.speed = speed
        self.max_distance = 2000
        self.size = 20
        self.color = (255, 100, 100)
        self.pulse_timer = 0
        
        # Направление
        dx = target_x - start_x
        dy = target_y - start_y
        dist = math.sqrt(dx**2 + dy**2)
        if dist > 0:
            self.change_x = (dx / dist) * speed
            self.change_y = (dy / dist) * speed
        else:
            self.change_x = speed
            self.change_y = 0
            
    def update(self, delta_time):
        self.center_x += self.change_x * delta_time
        self.center_y += self.change_y * delta_time
        self.pulse_timer += delta_time * 5
        
        # Удаляем если улетел далеко
        dist = math.sqrt((self.center_x - self.start_x)**2 + (self.center_y - self.start_y)**2)
        if dist > self.max_distance:
            self.remove_from_sprite_lists()