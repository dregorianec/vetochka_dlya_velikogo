import arcade
from pyglet.graphics import Batch
import math
import enum
import random
from classes import Hero, Bullet, Slime, Boss, BossProjectile


class FaceDirection(enum.Enum):
    LEFT = 0
    RIGHT = 1

# Задаём размеры окна
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
SCREEN_TITLE = "Спрайтовый герой"

CHUNK_SIZE = 12  # Размер чанка в тайлах
TILE_SIZE = 32
RENDER_DISTANCE = 3  # Сколько чанков вокруг игрока генерировать

# Биомы и их эффекты
# 0 - Синий (Лёд) - игрок и мобы скользят (инерция)
# 1 - Серый (Камень) - нейтральный
# 2 - Красный (Лава) - мобы быстрее на 50%
# 3 - Зелёный (Лес) - игрок быстрее на 30%
# 4 - Коричневый (Болото) - мобы медленнее на 50%

BIOME_COLORS = [
    (55, 95, 130, 255),   # 0 - Синий (Лёд)
    (95, 95, 95, 255),    # 1 - Серый (Камень)
    (120, 40, 40, 255),   # 2 - Красный (Лава)
    (60, 100, 60, 255),   # 3 - Зелёный (Лес)
    (100, 70, 50, 255),   # 4 - Коричневый (Болото)
]

BIOME_NAMES = ["Лёд", "Камень", "Лава", "Лес", "Болото"]


class MyGame(arcade.Window):
    def __init__(self, width, height, title):
        super().__init__(width, height, title, fullscreen=False)
        arcade.set_background_color((20, 20, 25, 255))
        self.set_mouse_visible(False)  # Скрываем системный курсор
        self.world_camera = arcade.camera.Camera2D()
        self.gui_camera = arcade.camera.Camera2D()
        self.world_camera.zoom = 1.0
        self.all_sprites = arcade.SpriteList()
        self.player_sprite = Hero()
        self.collision_list = list()
        self.tile_size = TILE_SIZE
        self.score = 0
        self.batch = Batch()
        self.health = 100
        self.is_dead = False
        self.auto_fire_unlocked = False
        self.auto_fire_key_down = False
        self.auto_fire_cooldown = 0.35  # Медленнее автовыстрелы
        self.auto_fire_timer = 0
        self.lmb_held = False
        self.lmb_fire_timer = 0
        self.mouse_position = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.ammo_max = 7
        self.ammo_current = 7
        self.reload_time = 2.0  # Базовая перезарядка 2 секунды
        self.is_reloading = False
        self.reload_timer = 0
        self.show_powerup_message = False
        
        # Бонус с таймером
        self.powerup_timer = 0  # Таймер бонуса (30 секунд)
        self.powerup_active = False
        
        # Система улучшений
        self.upgrade_menu_open = False
        self.available_upgrades = []  # 3 улучшения на выбор
        self.upgrades_taken = {}  # {"upgrade_id": count}
        self.bullet_speed_mult = 1.0
        self.bullet_range_mult = 1.0
        self.triple_shot = False
        self.double_shot = False
        self.auto_fire_lmb = False
        self.slow_on_hit = False
        self.ammo_save_chance = 0  # Шанс не тратить патрон (0-30%)
        self.lifesteal_chance = 0  # Шанс восстановить выносливость при убийстве
        self.crit_chance = 0  # Шанс крита (убить 2х врагов рядом)
        self.pierce_count = 0  # Сколько врагов может пробить пуля
        
        # Позиции карточек улучшений для клика мышкой
        self.upgrade_card_rects = []
        self.mouse_position = (0, 0)  # Для отслеживания позиции мыши
        
        # Чанковая система
        self.chunks = {}  # {(chunk_x, chunk_y): {'walls': [], 'floors': [], 'biome': int}}
        self.chunk_data = {}
        self.biome_seeds = []
        self.collected_powerups = set()  # Координаты чанков с подобранными бонусами
        
        # Текущий биом игрока
        self.current_biome = 1  # По умолчанию камень
        self.player_base_speed = 152  # Базовая скорость игрока (на 1% больше чем у врага 150)
        
        # Система спринта
        self.stamina = 30  # Текущая выносливость
        self.stamina_max = 30  # Максимальная выносливость (сильно уменьшена)
        self.stamina_drain = 30  # Расход выносливости в секунду при спринте
        self.stamina_regen = 20  # Восстановление выносливости в секунду
        self.is_sprinting = False
        self.sprint_speed_mult = 1.6  # Множитель скорости при спринте
        self.stamina_regen_cooldown = 0  # КД на регенерацию выносливости
        
        # Отсчёт перед началом
        self.countdown_timer = 5.0
        self.game_started = False
        
        # Игровое время и прогрессия
        self.game_time = 0  # Время игры в секундах (4:30 для теста)
        self.game_won = False  # Победа
        self.last_minute = 0  # Последняя засчитанная минута (для увеличения опыта)
        self.xp_per_kill = 1  # Базовый опыт за убийство
        
        # Система спавна врагов
        self.base_max_slimes = 120  # Базовый лимит врагов
        self.max_slimes = 120  # Текущий лимит врагов
        self.slime_spawn_timer = 0
        self.base_spawn_delay = 0.8  # Базовая задержка между спавнами
        self.slime_spawn_delay = 0.8  # Текущая задержка между спавнами
        self.slime_base_hp = 2  # Базовое HP врагов (минимум 2 чтобы был виден HP бар)
        
        # Система отложенных выстрелов (для double_shot)
        self.pending_bullets = []  # [(время_создания, target_x, target_y, speed, range, pierce)]
        
        # Система боссов
        self.boss_list = []  # Активные боссы
        self.boss_projectiles = []  # Снаряды боссов
        self.boss_spawned = {5: False, 10: False}  # Какие боссы уже появились
        self.boss_warning_timer = 0  # Таймер предупреждения о боссе
        self.boss_warning_text = ""
        self.total_kills = 0  # Общий счётчик убийств
        
        # Система уровней
        self.level = 1
        self.xp = 0
        self.xp_to_next_level = 10  # Начальный опыт для 2 уровня
        
        # Все возможные улучшения: (id, название, описание, макс_раз)
        self.ALL_UPGRADES = [
            ("speed", "Скорость +5%", "Увеличивает базовую скорость", 3),
            ("ammo", "Боезапас +2", "Увеличивает магазин", 5),
            ("triple_shot", "Тройной выстрел", "Стреляет в 3 стороны (тратит 2 патрона)", 1),
            ("double_shot", "Двойной выстрел", "2 пули за 1 патрон", 1),
            ("reload_speed", "Быстрая перезарядка -20%", "Ускоряет перезарядку", 3),
            ("stamina", "Выносливость +15", "Увеличивает макс. выносливость", 3),
            ("stamina_regen", "Регенерация +25%", "Быстрее восстанавливает выносливость", 3),
            ("bullet_speed", "Скорость пули +20%", "Пули летят быстрее", 3),
            ("bullet_range", "Дальность +25%", "Пули летят дальше", 3),
            ("sprint_speed", "Скорость спринта +15%", "Быстрее бегать с Shift", 3),
            ("pierce", "Пробитие +1", "Пуля пролетает сквозь врага", 3),
            ("stamina_drain", "Экономия выносливости -20%", "Меньше тратит выносливость", 3),
            ("auto_lmb", "Авто-огонь ЛКМ", "Зажатый ЛКМ = авто-стрельба", 1),
            ("slow_on_hit", "Замедление врагов", "Попадание замедляет врага на 2с", 1),
            ("ammo_save", "Экономия патронов 15%", "Шанс не потратить патрон", 2),
        ]


    def setup(self):
        self.wall_list = arcade.SpriteList(use_spatial_hash=True)
        self.floor_list = arcade.SpriteList(use_spatial_hash=False)
        self.bullet_list = arcade.SpriteList()
        self.chunk_update_timer = 0
        self.player_list = arcade.SpriteList()
        self.slime_list = arcade.SpriteList()
        self.powerup_list = arcade.SpriteList()
        
        # Генерируем глобальные сиды биомов
        random.seed(42)
        for _ in range(20):
            self.biome_seeds.append((
                random.randint(-500, 500),
                random.randint(-500, 500),
            ))
        random.seed()
        
        self.player = Hero()
        self.player_list.append(self.player)
        self.player.center_x = 0
        self.player.center_y = 0
        
        # Генерируем начальные чанки вокруг игрока
        self.update_chunks()
        
        self.update_camera(instant=True)
        
        # Слизни спавнятся после отсчёта

        self.physics_engine = arcade.PhysicsEngineSimple(
            self.player, self.wall_list
        )
        self.shoot_sound = arcade.load_sound("sound/пистолет.mp3")
        self.slime_dead_sound = arcade.load_sound("sound/slime_dead.mp3")
        
        self.keys_pressed = set()
        # Score в левом верхнем углу
        self.lable_score = arcade.Text(f"Score: {self.score}", 20, SCREEN_HEIGHT - 20, 
                                        font_size=24, color=arcade.color.WHITE,
                                        anchor_x="left", anchor_y="top")
        # Уровень под счётом
        self.label_level = arcade.Text(f"Уровень {self.level}", 20, SCREEN_HEIGHT - 50,
                                        font_size=18, color=arcade.color.YELLOW,
                                        anchor_x="left", anchor_y="top")
        # XP под уровнем
        self.label_xp = arcade.Text(f"XP: {self.xp}/{self.xp_to_next_level}", 20, SCREEN_HEIGHT - 75,
                                     font_size=14, color=arcade.color.LIGHT_GRAY,
                                     anchor_x="left", anchor_y="top")
        self.label_ammo = arcade.Text(
            f"Ammo: {self.ammo_current}/{self.ammo_max}",
            SCREEN_WIDTH - 20,
            20,
            batch=self.batch,
            font_size=26,
            color=arcade.color.WHITE,
            anchor_x="right",
            anchor_y="bottom",
        )
        
        # Метка биома
        self.label_biome = arcade.Text(
            "",
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT - 60,
            font_size=14,
            color=arcade.color.WHITE,
            anchor_x="center",
            anchor_y="center",
        )
        
        self.gui_sprite_list = arcade.SpriteList()
        ammo_bg_sprite = arcade.SpriteSolidColor(200, 40, color=(15, 15, 20, 230))
        ammo_bg_sprite.center_x = SCREEN_WIDTH - 20 - 100
        ammo_bg_sprite.center_y = 20 + 20
        self.gui_sprite_list.append(ammo_bg_sprite)
        
        # Полоса выносливости
        self.stamina_bar_width = 200
        self.stamina_bar_height = 12
        self.stamina_bar_x = SCREEN_WIDTH // 2
        self.stamina_bar_y = 30
        
        # Спрайты для полосы выносливости
        self.stamina_bar_list = arcade.SpriteList()
        
        self.stamina_bar_bg = arcade.SpriteSolidColor(
            self.stamina_bar_width + 4, self.stamina_bar_height + 4, 
            color=(30, 30, 30, 200)
        )
        self.stamina_bar_bg.center_x = self.stamina_bar_x
        self.stamina_bar_bg.center_y = self.stamina_bar_y
        self.stamina_bar_list.append(self.stamina_bar_bg)
        
        self.stamina_bar_fill = arcade.SpriteSolidColor(
            self.stamina_bar_width, self.stamina_bar_height,
            color=(100, 200, 100, 255)
        )
        self.stamina_bar_fill.center_x = self.stamina_bar_x
        self.stamina_bar_fill.center_y = self.stamina_bar_y

        self.label_powerup_hint = arcade.Text(
            "БОНУС АКТИВЕН! ПКМ - авто-стрельба",
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT - 30,
            font_size=16,
            color=arcade.color.LIGHT_GREEN,
            anchor_x="center",
            anchor_y="center",
        )
        
        # Текст отсчёта
        self.label_countdown = arcade.Text(
            "5",
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT // 2,
            font_size=120,
            color=arcade.color.WHITE,
            anchor_x="center",
            anchor_y="center",
        )

                                        

    def on_draw(self):
        self.clear()
        self.world_camera.use()
        self.floor_list.draw()
        self.wall_list.draw()
        self.player_list.draw()
        self.bullet_list.draw()
        self.slime_list.draw()
        self.powerup_list.draw()
        
        # HP бары над врагами
        self.draw_enemy_hp_bars()
        
        # Отрисовка боссов
        self.draw_bosses()

        self.gui_camera.use()
        self.gui_sprite_list.draw()
        self.batch.draw()
        
        # Улучшенный интерфейс - панель статистики
        self.draw_stats_panel()
        
        # Показываем отсчёт
        if not self.game_started:
            if self.countdown_timer > 0:
                self.label_countdown.text = str(int(self.countdown_timer) + 1)
            else:
                self.label_countdown.text = "GO!"
                self.label_countdown.color = arcade.color.LIGHT_GREEN
            self.label_countdown.draw()
        
        # Показываем информацию о бонусе
        if self.powerup_active:
            self.label_powerup_hint.text = f"БОНУС: {self.powerup_timer:.1f}с | ПКМ - авто-стрельба"
            self.label_powerup_hint.draw()
        
        # Показываем биом
        self.label_biome.draw()
        
        # Показываем уровень и XP
        self.label_level.draw()
        self.label_xp.draw()
        
        # Полоса выносливости
        self.draw_stamina_bar()
        
        # Предупреждение о боссе
        if self.boss_warning_timer > 0:
            self.draw_boss_warning()
        
        # HP бара боссов
        self.draw_boss_hp_bars()
        
        # Меню улучшений
        if self.upgrade_menu_open:
            self.draw_upgrade_menu()
        
        # Экран победы
        if self.game_won:
            self.draw_victory_screen()
        
        # Прицел
        self.draw_crosshair()


    def on_update(self, delta_time):
        if self.is_dead:
            return
        
        # Пауза при открытом меню улучшений
        if self.upgrade_menu_open:
            return
        
        # Отсчёт перед началом игры
        if not self.game_started:
            self.countdown_timer -= delta_time
            if self.countdown_timer <= -0.5:  # Небольшая задержка после "GO!"
                self.game_started = True
                # Спавним начальных слизней после отсчёта
                for _ in range(15):
                    slime_x, slime_y = self.get_random_spawn_position(min_distance=6)
                    self.slime_list.append(Slime(slime_x, slime_y, hp=self.slime_base_hp))
            # Во время отсчёта можно только двигаться
            self.player_list.update(delta_time, self.keys_pressed)
            self.physics_engine.update()
            self.update_camera()
            self.player_list.update_animation()
            self.chunk_update_timer += delta_time
            if self.chunk_update_timer > 0.2:
                self.chunk_update_timer = 0
                self.update_chunks()
            return
        
        # Обработка спринта
        is_moving = (arcade.key.W in self.keys_pressed or arcade.key.A in self.keys_pressed or
                     arcade.key.S in self.keys_pressed or arcade.key.D in self.keys_pressed or
                     arcade.key.UP in self.keys_pressed or arcade.key.DOWN in self.keys_pressed or
                     arcade.key.LEFT in self.keys_pressed or arcade.key.RIGHT in self.keys_pressed)
        
        shift_pressed = (arcade.key.LSHIFT in self.keys_pressed or arcade.key.RSHIFT in self.keys_pressed)
        
        if shift_pressed and is_moving and self.stamina > 0:
            self.is_sprinting = True
            self.stamina -= self.stamina_drain * delta_time
            self.stamina = max(0, self.stamina)
            self.stamina_regen_cooldown = 1.0  # Сброс КД регенерации при спринте
        else:
            self.is_sprinting = False
            # КД на регенерацию выносливости
            if self.stamina_regen_cooldown > 0:
                self.stamina_regen_cooldown -= delta_time
            elif self.stamina < self.stamina_max:
                # Восстанавливаем выносливость когда не спринтуем и КД прошёл
                self.stamina += self.stamina_regen * delta_time
                self.stamina = min(self.stamina_max, self.stamina)
        
        # Определяем биом игрока и применяем эффекты
        self.update_player_biome()
        
        self.player_list.update(delta_time, self.keys_pressed)
        self.physics_engine.update()
        
        # Обновляем чанки не каждый кадр
        self.chunk_update_timer += delta_time
        if self.chunk_update_timer > 0.2:
            self.chunk_update_timer = 0
            self.update_chunks()
        
        # Слизень двигается к игроку с учётом биома
        for slime in self.slime_list:
            self.move_slime_smart(slime, delta_time)
        
        self.update_camera()
        self.player_list.update_animation()
        self.slime_list.update_animation(delta_time)
        
        for bullet in self.bullet_list:
            bullet.update(delta_time)
        
        for bullet in self.bullet_list:
            hit_wall = arcade.check_for_collision_with_list(bullet, self.wall_list)
            if hit_wall:
                bullet.remove_from_sprite_lists()

        if arcade.check_for_collision_with_list(self.player, self.slime_list):
            self.is_dead = True
            self.close()
            return

        # Подбор бонуса
        if self.powerup_list:
            picked = arcade.check_for_collision_with_list(self.player, self.powerup_list)
            if picked:
                for sprite in picked:
                    # Запоминаем координаты подобранного бонуса
                    chunk_x, chunk_y = self.world_to_chunk(sprite.center_x, sprite.center_y)
                    self.collected_powerups.add((chunk_x, chunk_y))
                    sprite.remove_from_sprite_lists()
                self.activate_powerup()

        # Таймер бонуса
        if self.powerup_active:
            self.powerup_timer -= delta_time
            if self.powerup_timer <= 0:
                self.deactivate_powerup()

        if self.auto_fire_unlocked and self.auto_fire_key_down:
            self.auto_fire_timer += delta_time
            if self.auto_fire_timer >= self.auto_fire_cooldown:
                self.auto_fire_timer = 0
                self.fire_bullet()

        # Авто-стрельба ЛКМ (улучшение)
        if self.auto_fire_lmb and self.lmb_held:
            self.lmb_fire_timer += delta_time
            if self.lmb_fire_timer >= 0.15:  # Быстрее чем ПКМ
                self.lmb_fire_timer = 0
                self.fire_bullet()

        if self.is_reloading:
            self.reload_timer -= delta_time
            if self.reload_timer <= 0:
                self.is_reloading = False
                self.ammo_current = self.ammo_max
        
        for slime in list(self.slime_list):
            hit_bullets = arcade.check_for_collision_with_list(slime, self.bullet_list)
            for bullet in hit_bullets:
                # Проверяем, не пробили ли мы уже этого врага
                slime_id = id(slime)
                if slime_id in bullet.pierced_enemies:
                    continue
                
                # Помечаем врага как пробитого этой пулей
                bullet.pierced_enemies.add(slime_id)
                
                # Наносим урон врагу
                slime.hp -= 1
                
                # Замедление соседних врагов при slow_on_hit
                if self.slow_on_hit:
                    for other_slime in self.slime_list:
                        dist = math.sqrt((other_slime.center_x - slime.center_x)**2 + 
                                        (other_slime.center_y - slime.center_y)**2)
                        if dist < 150:  # В радиусе 150 пикселей
                            other_slime.slow_timer = 2.0  # Замедлен на 2 секунды
                
                # Проверяем пробитие: если пробитий больше нет, удаляем пулю
                if len(bullet.pierced_enemies) > bullet.pierce_count:
                    bullet.remove_from_sprite_lists()
                
                # Проверяем смерть врага
                if slime.hp <= 0:
                    slime.remove_from_sprite_lists()
                    self.score += 1
                    self.total_kills += 1
                    self.gain_xp(self.xp_per_kill)  # XP за убийство (растёт каждую минуту)
                    arcade.play_sound(self.slime_dead_sound, volume=0.01)
                
                break  # Попадание обработано
        
        # Обновляем игровое время и прогрессию
        self.game_time += delta_time
        current_minute = int(self.game_time // 60)
        
        # Победа после 15 минут
        if self.game_time >= 15 * 60 and not self.game_won:
            self.game_won = True
        
        # Увеличение опыта за убийство каждую минуту
        if current_minute > self.last_minute:
            self.last_minute = current_minute
            self.xp_per_kill += 1
        
        # Прогрессия сложности со временем
        # Плавное увеличение: каждую минуту спавнрейт уменьшается на 5%, лимит увеличивается на 5%
        time_multiplier = 1 + (current_minute * 0.05)  # +5% сложности за минуту
        
        # На 10-й минуте и далее - удвоение спавнрейта
        if current_minute >= 10:
            spawn_mult = 2.0
        else:
            spawn_mult = 1.0
        
        self.slime_spawn_delay = self.base_spawn_delay / (time_multiplier * spawn_mult)
        self.slime_spawn_delay = max(0.15, self.slime_spawn_delay)  # Минимум 0.15с между спавнами
        
        self.max_slimes = int(self.base_max_slimes * time_multiplier)
        self.max_slimes = min(300, self.max_slimes)  # Максимум 300 врагов
        
        # Расчёт HP врагов: базовое 2, +1 каждые 3 минуты, +3 на 12-й минуте и далее
        hp_from_time = current_minute // 3  # +1 HP за каждые 3 минуты
        if current_minute >= 12:
            hp_bonus = (current_minute - 12) * 3 // 3  # Дополнительно +3 каждые 3 минуты после 12-й
            self.slime_base_hp = 2 + 4 + hp_bonus  # 2 базовый + 4 за первые 12 минут + бонус
        else:
            self.slime_base_hp = 2 + hp_from_time
        
        # Спавн новых врагов по таймеру
        self.slime_spawn_timer += delta_time
        if self.slime_spawn_timer >= self.slime_spawn_delay:
            self.slime_spawn_timer = 0
            if len(self.slime_list) < self.max_slimes:
                slime_x, slime_y = self.get_random_spawn_position(min_distance=8)
                self.slime_list.append(Slime(slime_x, slime_y, hp=self.slime_base_hp))
        
        # Спавн боссов на 5-й и 10-й минуте
        for boss_minute in [5, 10]:
            if current_minute >= boss_minute and not self.boss_spawned[boss_minute]:
                self.boss_spawned[boss_minute] = True
                boss_type = 1 if boss_minute == 5 else 2
                boss_x, boss_y = self.get_random_spawn_position(min_distance=10)
                boss = Boss(boss_x, boss_y, boss_type=boss_type, base_hp=self.slime_base_hp)
                self.boss_list.append(boss)
                self.boss_warning_timer = 3.0
                self.boss_warning_text = boss.name
        
        # Обновление боссов
        self.update_bosses(delta_time)
        
        # Обновление снарядов боссов
        for proj in list(self.boss_projectiles):
            proj.update(delta_time)
            # Проверка попадания в игрока
            dist = math.sqrt((proj.center_x - self.player.center_x)**2 + 
                           (proj.center_y - self.player.center_y)**2)
            if dist < 30:  # Радиус попадания
                proj.remove_from_sprite_lists()
                self.boss_projectiles.remove(proj)
                # Урон игроку (можно добавить систему HP игрока позже)
        
        # Удаляем мёртвые снаряды
        self.boss_projectiles = [p for p in self.boss_projectiles if p.max_distance > 0]
        
        # Таймер предупреждения о боссе
        if self.boss_warning_timer > 0:
            self.boss_warning_timer -= delta_time
        
        # Обработка отложенных выстрелов (double_shot)
        new_pending = []
        for delay, tx, ty, speed, brange, pierce in self.pending_bullets:
            delay -= delta_time
            if delay <= 0:
                # Создаём отложенную пулю
                bullet = Bullet(
                    self.player.center_x,
                    self.player.center_y,
                    tx, ty,
                    speed=speed,
                    pierce_count=pierce
                )
                bullet.max_distance = brange
                self.bullet_list.append(bullet)
            else:
                new_pending.append((delay, tx, ty, speed, brange, pierce))
        self.pending_bullets = new_pending
        
        # Форматируем время для отображения
        minutes = int(self.game_time // 60)
        seconds = int(self.game_time % 60)
        time_str = f"{minutes:02d}:{seconds:02d}"
        
        self.lable_score.text = f"Score: {self.score} | Время: {time_str}"
        self.label_level.text = f"Уровень {self.level}"
        self.label_xp.text = f"XP: {self.xp}/{self.xp_to_next_level}"
        if self.is_reloading:
            self.label_ammo.text = f"Reloading: {max(0, self.reload_timer):.1f}s"
        else:
            self.label_ammo.text = f"Ammo: {self.ammo_current}/{self.ammo_max}"

    def gain_xp(self, amount):
        """Получение опыта"""
        self.xp += amount
        while self.xp >= self.xp_to_next_level and not self.upgrade_menu_open:
            self.level_up()

    def level_up(self):
        """Повышение уровня"""
        self.xp -= self.xp_to_next_level
        self.level += 1
        self.xp_to_next_level = int(10 * (1.5 ** (self.level - 1)))
        self.open_upgrade_menu()

    def open_upgrade_menu(self):
        """Открывает меню выбора улучшений"""
        self.upgrade_menu_open = True
        # Выбираем 3 случайных доступных улучшения
        available = []
        for upgrade in self.ALL_UPGRADES:
            upgrade_id, name, desc, max_count = upgrade
            current_count = self.upgrades_taken.get(upgrade_id, 0)
            if current_count < max_count:
                available.append(upgrade)
        
        # Перемешиваем и берём до 3х
        random.shuffle(available)
        self.available_upgrades = available[:3]

    def select_upgrade(self, index):
        """Выбирает улучшение по индексу (0, 1, 2)"""
        if index >= len(self.available_upgrades):
            return
        
        upgrade = self.available_upgrades[index]
        upgrade_id = upgrade[0]
        
        # Записываем что взяли
        self.upgrades_taken[upgrade_id] = self.upgrades_taken.get(upgrade_id, 0) + 1
        
        # Применяем эффект
        self.apply_upgrade(upgrade_id)
        
        # Закрываем меню
        self.upgrade_menu_open = False
        self.available_upgrades = []

    def draw_upgrade_menu(self):
        """Отрисовка меню выбора улучшений"""
        # Затемнение фона
        overlay = arcade.SpriteSolidColor(SCREEN_WIDTH, SCREEN_HEIGHT, color=(0, 0, 0, 180))
        overlay.center_x = SCREEN_WIDTH // 2
        overlay.center_y = SCREEN_HEIGHT // 2
        overlay_list = arcade.SpriteList()
        overlay_list.append(overlay)
        overlay_list.draw()
        
        # Заголовок
        title = arcade.Text(
            f"УРОВЕНЬ {self.level}! Выберите улучшение (кликните):",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100,
            font_size=28, color=arcade.color.YELLOW,
            anchor_x="center"
        )
        title.draw()
        
        # Карточки улучшений
        card_width = 280
        card_height = 200
        start_x = SCREEN_WIDTH // 2 - (len(self.available_upgrades) - 1) * 150
        
        # Сохраняем позиции карточек для клика
        self.upgrade_card_rects = []
        
        for i, upgrade in enumerate(self.available_upgrades):
            upgrade_id, name, desc, max_count = upgrade
            current_count = self.upgrades_taken.get(upgrade_id, 0)
            
            card_x = start_x + i * 300
            card_y = SCREEN_HEIGHT // 2
            
            # Сохраняем прямоугольник карточки
            self.upgrade_card_rects.append((
                card_x - card_width // 2,  # left
                card_x + card_width // 2,  # right
                card_y - card_height // 2, # bottom
                card_y + card_height // 2, # top
                i  # index
            ))
            
            # Проверяем, наведена ли мышь
            mx, my = self.mouse_position
            is_hovered = (card_x - card_width // 2 <= mx <= card_x + card_width // 2 and
                         card_y - card_height // 2 <= my <= card_y + card_height // 2)
            
            # Фон карточки (светлее при наведении)
            if is_hovered:
                card_color = (60, 60, 80, 250)
            else:
                card_color = (40, 40, 50, 250)
            
            card_bg = arcade.SpriteSolidColor(card_width, card_height, color=card_color)
            card_bg.center_x = card_x
            card_bg.center_y = card_y
            card_list = arcade.SpriteList()
            card_list.append(card_bg)
            card_list.draw()
            
            # Рамка при наведении
            if is_hovered:
                border = arcade.SpriteSolidColor(card_width + 4, card_height + 4, color=(100, 200, 100, 255))
                border.center_x = card_x
                border.center_y = card_y
                inner = arcade.SpriteSolidColor(card_width, card_height, color=card_color)
                inner.center_x = card_x
                inner.center_y = card_y
                border_list = arcade.SpriteList()
                border_list.append(border)
                border_list.append(inner)
                border_list.draw()
            
            # Название
            name_text = arcade.Text(
                name,
                card_x, card_y + 50,
                font_size=18, color=arcade.color.WHITE,
                anchor_x="center"
            )
            name_text.draw()
            
            # Описание
            desc_text = arcade.Text(
                desc,
                card_x, card_y,
                font_size=12, color=arcade.color.LIGHT_GRAY,
                anchor_x="center"
            )
            desc_text.draw()
            
            # Сколько раз взято
            count_text = arcade.Text(
                f"({current_count}/{max_count})",
                card_x, card_y - 50,
                font_size=14, color=arcade.color.YELLOW_ORANGE,
                anchor_x="center"
            )
            count_text.draw()

    def apply_upgrade(self, upgrade_id):
        """Применяет эффект улучшения"""
        if upgrade_id == "speed":
            self.player_base_speed = int(self.player_base_speed * 1.05)
        elif upgrade_id == "ammo":
            self.ammo_max += 2
        elif upgrade_id == "triple_shot":
            self.triple_shot = True
        elif upgrade_id == "double_shot":
            self.double_shot = True
        elif upgrade_id == "reload_speed":
            self.reload_time *= 0.8
        elif upgrade_id == "stamina":
            self.stamina_max += 15
            self.stamina = min(self.stamina + 15, self.stamina_max)
        elif upgrade_id == "stamina_regen":
            self.stamina_regen = int(self.stamina_regen * 1.25)
        elif upgrade_id == "bullet_speed":
            self.bullet_speed_mult *= 1.2
        elif upgrade_id == "bullet_range":
            self.bullet_range_mult *= 1.25
        elif upgrade_id == "sprint_speed":
            self.sprint_speed_mult *= 1.15
        elif upgrade_id == "stamina_drain":
            self.stamina_drain *= 0.8
        elif upgrade_id == "auto_lmb":
            self.auto_fire_lmb = True
        elif upgrade_id == "slow_on_hit":
            self.slow_on_hit = True
        elif upgrade_id == "ammo_save":
            self.ammo_save_chance += 15
        elif upgrade_id == "pierce":
            self.pierce_count += 1

    def draw_stats_panel(self):
        """Улучшенная панель статистики"""
        # Фон панели
        panel_width = 160
        panel_height = 70
        panel_x = 90
        panel_y = SCREEN_HEIGHT - 45
        
        panel_bg = arcade.SpriteSolidColor(panel_width, panel_height, color=(20, 20, 30, 200))
        panel_bg.center_x = panel_x
        panel_bg.center_y = panel_y
        panel_list = arcade.SpriteList()
        panel_list.append(panel_bg)
        panel_list.draw()
        
        # Рамка
        border = arcade.SpriteSolidColor(panel_width + 4, panel_height + 4, color=(80, 80, 100, 255))
        border.center_x = panel_x
        border.center_y = panel_y
        inner = arcade.SpriteSolidColor(panel_width, panel_height, color=(20, 20, 30, 200))
        inner.center_x = panel_x
        inner.center_y = panel_y
        border_list = arcade.SpriteList()
        border_list.append(border)
        border_list.append(inner)
        border_list.draw()
        
        # Время
        minutes = int(self.game_time // 60)
        seconds = int(self.game_time % 60)
        time_text = arcade.Text(
            f"Время: {minutes:02d}:{seconds:02d}",
            panel_x - 65, panel_y + 10,
            font_size=18, color=arcade.color.YELLOW,
            bold=True
        )
        time_text.draw()
        
        # Убийства
        kills_text = arcade.Text(
            f"Убийства: {self.total_kills}",
            panel_x - 65, panel_y - 15,
            font_size=14, color=arcade.color.WHITE
        )
        kills_text.draw()

    def draw_enemy_hp_bars(self):
        """Маленькие HP бары над врагами"""
        for slime in self.slime_list:
            # Показываем бар только если враг ранен и имеет больше 1 HP
            if slime.hp < slime.max_hp and slime.max_hp > 1:
                bar_width = 30
                bar_height = 4
                bar_x = slime.center_x
                bar_y = slime.center_y + 25  # Над врагом
                
                # Фон
                bg = arcade.SpriteSolidColor(bar_width + 2, bar_height + 2, color=(30, 30, 30, 200))
                bg.center_x = bar_x
                bg.center_y = bar_y
                
                # Заполнение
                hp_ratio = slime.hp / slime.max_hp
                fill_width = int(bar_width * hp_ratio)
                
                if fill_width > 0:
                    # Цвет зависит от HP
                    if hp_ratio > 0.6:
                        hp_color = (100, 200, 100, 255)  # Зелёный
                    elif hp_ratio > 0.3:
                        hp_color = (200, 200, 100, 255)  # Жёлтый
                    else:
                        hp_color = (200, 100, 100, 255)  # Красный
                    
                    fill = arcade.SpriteSolidColor(fill_width, bar_height, color=hp_color)
                    fill.center_x = bar_x - (bar_width - fill_width) / 2
                    fill.center_y = bar_y
                    
                    bar_list = arcade.SpriteList()
                    bar_list.append(bg)
                    bar_list.append(fill)
                    bar_list.draw()

    def draw_bosses(self):
        """Отрисовка боссов в мировых координатах"""
        for boss in self.boss_list:
            # Анимация появления
            if boss.is_spawning:
                alpha = int(255 * (1 - boss.spawn_timer / 2.0))
                scale = 1.0 + boss.spawn_timer * 0.5
            else:
                alpha = 255
                scale = 1.0 + 0.1 * math.sin(boss.pulse_timer)
            
            # Тело босса
            size = int(boss.base_size * scale)
            boss_color = (boss.color[0], boss.color[1], boss.color[2], alpha)
            boss_sprite = arcade.SpriteSolidColor(size, size, color=boss_color)
            boss_sprite.center_x = boss.center_x
            boss_sprite.center_y = boss.center_y
            boss_sprite.angle = boss.pulse_timer * 10  # Медленное вращение
            boss_list = arcade.SpriteList()
            boss_list.append(boss_sprite)
            boss_list.draw()
            
            # Внутренний круг (глаз/ядро)
            core_size = int(size * 0.4)
            core_color = (255, 255, 200, alpha) if boss.boss_type == 1 else (200, 200, 255, alpha)
            core = arcade.SpriteSolidColor(core_size, core_size, color=core_color)
            core.center_x = boss.center_x
            core.center_y = boss.center_y
            core_list = arcade.SpriteList()
            core_list.append(core)
            core_list.draw()
            
            # Орбиты для первого босса
            if boss.boss_type == 1 and not boss.is_spawning:
                for ox, oy in boss.get_orb_positions():
                    # Орбита
                    orb_size = 25
                    orb_pulse = 1.0 + 0.2 * math.sin(boss.pulse_timer * 3)
                    orb = arcade.SpriteSolidColor(
                        int(orb_size * orb_pulse), int(orb_size * orb_pulse),
                        color=(255, 150, 50, 230)
                    )
                    orb.center_x = ox
                    orb.center_y = oy
                    orb_list = arcade.SpriteList()
                    orb_list.append(orb)
                    orb_list.draw()
                    
                    # Свечение орбиты
                    glow = arcade.SpriteSolidColor(
                        int(orb_size * 1.5), int(orb_size * 1.5),
                        color=(255, 200, 100, 100)
                    )
                    glow.center_x = ox
                    glow.center_y = oy
                    glow_list = arcade.SpriteList()
                    glow_list.append(glow)
                    glow_list.draw()
            
            # Для второго босса - эффект заряда
            if boss.boss_type == 2 and boss.attack_timer > boss.attack_cooldown - 0.5:
                charge_alpha = int(200 * (boss.attack_timer - (boss.attack_cooldown - 0.5)) * 2)
                charge = arcade.SpriteSolidColor(size + 20, size + 20, color=(100, 100, 255, charge_alpha))
                charge.center_x = boss.center_x
                charge.center_y = boss.center_y
                charge_list = arcade.SpriteList()
                charge_list.append(charge)
                charge_list.draw()
        
        # Снаряды боссов
        for proj in self.boss_projectiles:
            pulse = 1.0 + 0.3 * math.sin(proj.pulse_timer)
            proj_size = int(proj.size * pulse)
            
            # Внешний круг
            outer = arcade.SpriteSolidColor(proj_size + 10, proj_size + 10, color=(255, 50, 50, 150))
            outer.center_x = proj.center_x
            outer.center_y = proj.center_y
            
            # Внутренний круг
            inner = arcade.SpriteSolidColor(proj_size, proj_size, color=(255, 200, 100, 255))
            inner.center_x = proj.center_x
            inner.center_y = proj.center_y
            
            proj_list = arcade.SpriteList()
            proj_list.append(outer)
            proj_list.append(inner)
            proj_list.draw()

    def draw_boss_warning(self):
        """Предупреждение о появлении босса"""
        # Мигающий фон
        flash_alpha = int(100 * abs(math.sin(self.boss_warning_timer * 5)))
        flash = arcade.SpriteSolidColor(SCREEN_WIDTH, 100, color=(200, 50, 50, flash_alpha))
        flash.center_x = SCREEN_WIDTH // 2
        flash.center_y = SCREEN_HEIGHT // 2
        flash_list = arcade.SpriteList()
        flash_list.append(flash)
        flash_list.draw()
        
        # Текст
        warning = arcade.Text(
            f"⚠ БОСС: {self.boss_warning_text} ⚠",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
            font_size=36, color=arcade.color.RED,
            anchor_x="center", anchor_y="center", bold=True
        )
        warning.draw()

    def draw_boss_hp_bars(self):
        """HP бары боссов вверху экрана"""
        y_offset = SCREEN_HEIGHT - 130
        for i, boss in enumerate(self.boss_list):
            if boss.hp <= 0:
                continue
                
            bar_width = 400
            bar_height = 25
            bar_x = SCREEN_WIDTH // 2
            bar_y = y_offset - i * 50
            
            # Фон бара
            bg = arcade.SpriteSolidColor(bar_width + 4, bar_height + 4, color=(50, 50, 50, 255))
            bg.center_x = bar_x
            bg.center_y = bar_y
            bg_list = arcade.SpriteList()
            bg_list.append(bg)
            bg_list.draw()
            
            # Заполнение HP
            hp_ratio = boss.hp / boss.max_hp
            fill_width = int(bar_width * hp_ratio)
            if fill_width > 0:
                # Цвет зависит от HP
                if hp_ratio > 0.5:
                    hp_color = (boss.color[0], boss.color[1], boss.color[2], 255)
                elif hp_ratio > 0.25:
                    hp_color = (255, 150, 50, 255)
                else:
                    hp_color = (255, 50, 50, 255)
                
                fill = arcade.SpriteSolidColor(fill_width, bar_height, color=hp_color)
                fill.center_x = bar_x - (bar_width - fill_width) // 2
                fill.center_y = bar_y
                fill_list = arcade.SpriteList()
                fill_list.append(fill)
                fill_list.draw()
            
            # Имя босса
            name = arcade.Text(
                f"{boss.name} - {boss.hp}/{boss.max_hp}",
                bar_x, bar_y + 20,
                font_size=14, color=arcade.color.WHITE,
                anchor_x="center", bold=True
            )
            name.draw()

    def update_bosses(self, delta_time):
        """Обновление логики боссов"""
        for boss in list(self.boss_list):
            boss.update(delta_time, self.player, self.wall_list)
            
            # Проверка столкновения орбит с игроком (первый босс)
            if boss.boss_type == 1 and not boss.is_spawning:
                for ox, oy in boss.get_orb_positions():
                    dist = math.sqrt((ox - self.player.center_x)**2 + (oy - self.player.center_y)**2)
                    if dist < 35:  # Радиус попадания орбиты
                        # Урон игроку
                        pass
            
            # Стрельба для второго босса
            if boss.boss_type == 2 and boss.should_attack() and not boss.is_spawning:
                # Создаём снаряд
                proj = BossProjectile(
                    boss.center_x, boss.center_y,
                    self.player.center_x, self.player.center_y,
                    speed=350
                )
                self.boss_projectiles.append(proj)
            
            # Телепортация для второго босса
            if boss.boss_type == 2 and boss.is_teleporting:
                boss.is_teleporting = False
                # Телепортируемся в случайное место рядом с игроком
                angle = random.uniform(0, math.pi * 2)
                dist = random.uniform(300, 500)
                boss.center_x = self.player.center_x + math.cos(angle) * dist
                boss.center_y = self.player.center_y + math.sin(angle) * dist
            
            # Проверка попадания пуль в босса
            for bullet in list(self.bullet_list):
                dist = math.sqrt((bullet.center_x - boss.center_x)**2 + 
                               (bullet.center_y - boss.center_y)**2)
                if dist < boss.base_size / 2:
                    boss_id = id(boss)
                    if boss_id not in bullet.pierced_enemies:
                        bullet.pierced_enemies.add(boss_id)
                        boss.hp -= 1
                        
                        if len(bullet.pierced_enemies) > bullet.pierce_count:
                            bullet.remove_from_sprite_lists()
                        
                        # Босс убит
                        if boss.hp <= 0:
                            self.boss_list.remove(boss)
                            self.score += 100  # Много очков за босса
                            self.total_kills += 1
                            self.gain_xp(50)  # Много XP
                            arcade.play_sound(self.slime_dead_sound, volume=0.05)
                        break

    def draw_victory_screen(self):
        """Отрисовка экрана победы"""
        # Затемнение фона
        overlay = arcade.SpriteSolidColor(SCREEN_WIDTH, SCREEN_HEIGHT, color=(0, 50, 0, 200))
        overlay.center_x = SCREEN_WIDTH // 2
        overlay.center_y = SCREEN_HEIGHT // 2
        overlay_list = arcade.SpriteList()
        overlay_list.append(overlay)
        overlay_list.draw()
        
        # Заголовок ПОБЕДА
        victory_text = arcade.Text(
            "ПОБЕДА!",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100,
            font_size=72, color=arcade.color.GOLD,
            anchor_x="center", bold=True
        )
        victory_text.draw()
        
        # Статистика
        stats_text = arcade.Text(
            f"Вы выжили 15 минут!\n\nСчёт: {self.score}\nУровень: {self.level}\nУбито врагов: {self.total_kills}",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30,
            font_size=24, color=arcade.color.WHITE,
            anchor_x="center", multiline=True, width=500, align="center"
        )
        stats_text.draw()
        
        # Подсказка
        hint_text = arcade.Text(
            "Нажмите ESC для выхода",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 150,
            font_size=18, color=arcade.color.LIGHT_GRAY,
            anchor_x="center"
        )
        hint_text.draw()

    def draw_crosshair(self):
        """Отрисовка прицела"""
        mx, my = self.mouse_position
        size = 12  # Размер прицела
        gap = 4    # Отступ от центра
        thickness = 2
        
        # Создаём линии прицела (горизонтальные и вертикальные)
        crosshair_sprites = arcade.SpriteList()
        
        # Верхняя линия
        top = arcade.SpriteSolidColor(thickness, size, color=(255, 255, 255, 220))
        top.center_x = mx
        top.center_y = my + gap + size // 2
        crosshair_sprites.append(top)
        
        # Нижняя линия
        bottom = arcade.SpriteSolidColor(thickness, size, color=(255, 255, 255, 220))
        bottom.center_x = mx
        bottom.center_y = my - gap - size // 2
        crosshair_sprites.append(bottom)
        
        # Левая линия
        left = arcade.SpriteSolidColor(size, thickness, color=(255, 255, 255, 220))
        left.center_x = mx - gap - size // 2
        left.center_y = my
        crosshair_sprites.append(left)
        
        # Правая линия
        right = arcade.SpriteSolidColor(size, thickness, color=(255, 255, 255, 220))
        right.center_x = mx + gap + size // 2
        right.center_y = my
        crosshair_sprites.append(right)
        
        # Центральная точка
        center = arcade.SpriteSolidColor(3, 3, color=(255, 50, 50, 255))
        center.center_x = mx
        center.center_y = my
        crosshair_sprites.append(center)
        
        crosshair_sprites.draw()

    def draw_stamina_bar(self):
        """Отрисовка полосы выносливости"""
        # Фон
        self.stamina_bar_list.draw()
        
        # Заполнение
        fill_ratio = self.stamina / self.stamina_max
        if fill_ratio > 0:
            # Цвет зависит от уровня выносливости
            if self.stamina > 60:
                bar_color = (100, 200, 100, 255)  # Зелёный
            elif self.stamina > 30:
                bar_color = (200, 200, 100, 255)  # Жёлтый
            else:
                bar_color = (200, 100, 100, 255)  # Красный
            
            fill_width = int(self.stamina_bar_width * fill_ratio)
            if fill_width > 0:
                self.stamina_bar_fill.width = fill_width
                self.stamina_bar_fill.color = bar_color
                self.stamina_bar_fill.center_x = self.stamina_bar_x - (self.stamina_bar_width - fill_width) / 2
                # Временно добавляем в список для отрисовки
                temp_list = arcade.SpriteList()
                temp_list.append(self.stamina_bar_fill)
                temp_list.draw()

    def activate_powerup(self):
        """Активирует бонус на 30 секунд"""
        self.powerup_active = True
        self.powerup_timer = 30.0
        self.auto_fire_unlocked = True
        self.ammo_max = 31
        self.ammo_current = 31
        self.show_powerup_message = True

    def deactivate_powerup(self):
        """Деактивирует бонус"""
        self.powerup_active = False
        self.powerup_timer = 0
        self.auto_fire_unlocked = False
        self.ammo_max = 7
        self.ammo_current = min(self.ammo_current, 7)
        self.show_powerup_message = False

    def update_player_biome(self):
        """Определяет биом игрока и применяем эффекты скорости"""
        chunk_x, chunk_y = self.world_to_chunk(self.player.center_x, self.player.center_y)
        
        if (chunk_x, chunk_y) in self.chunks:
            self.current_biome = self.chunks[(chunk_x, chunk_y)].get('biome', 1)
        else:
            self.current_biome = 1
        
        # Базовая скорость с учётом биома
        if self.current_biome == 3:  # Зелёный (Лес) - ускорение
            base_speed = int(self.player_base_speed * 1.3)
            biome_effect = "+30% скорость"
        elif self.current_biome == 0:  # Синий (Лёд) - скольжение (чуть быстрее)
            base_speed = int(self.player_base_speed * 1.15)
            biome_effect = "скольжение"
        else:
            base_speed = self.player_base_speed
            biome_effect = ""
        
        # Применяем спринт
        if self.is_sprinting:
            self.player.speed = int(base_speed * self.sprint_speed_mult)
        else:
            self.player.speed = base_speed
        
        # Обновляем метку биома (белый цвет для читаемости)
        biome_name = BIOME_NAMES[self.current_biome]
        self.label_biome.color = arcade.color.WHITE
        if biome_effect:
            self.label_biome.text = f"Биом: {biome_name} ({biome_effect})"
        else:
            self.label_biome.text = f"Биом: {biome_name}"

    def get_slime_speed_multiplier(self, slime):
        """Возвращает множитель скорости слизня в зависимости от биома"""
        chunk_x, chunk_y = self.world_to_chunk(slime.center_x, slime.center_y)
        
        if (chunk_x, chunk_y) in self.chunks:
            biome = self.chunks[(chunk_x, chunk_y)].get('biome', 1)
        else:
            biome = 1
        
        if biome == 2:  # Красный (Лава) - мобы быстрее
            return 1.5
        elif biome == 4:  # Коричневый (Болото) - мобы медленнее
            return 0.5
        elif biome == 0:  # Синий (Лёд) - немного быстрее
            return 1.2
        return 1.0

    def move_slime_smart(self, slime, delta_time):
        """Улучшенное движение слизня с обходом препятствий и эффектами биома"""
        # Обновляем таймер замедления
        if not hasattr(slime, 'slow_timer'):
            slime.slow_timer = 0
        if slime.slow_timer > 0:
            slime.slow_timer -= delta_time
        
        dx = self.player.center_x - slime.center_x
        dy = self.player.center_y - slime.center_y
        
        distance = math.sqrt(dx**2 + dy**2)
        if distance < 1:
            return
        
        # Получаем множитель скорости от биома
        speed_mult = self.get_slime_speed_multiplier(slime)
        
        # Замедление от slow_on_hit
        if slime.slow_timer > 0:
            speed_mult *= 0.3  # 70% замедление
        
        current_speed = slime.speed * speed_mult
            
        dx = dx / distance
        dy = dy / distance
        
        old_x = slime.center_x
        old_y = slime.center_y
        
        slime.center_x += dx * current_speed * delta_time
        slime.center_y += dy * current_speed * delta_time
        
        hit_wall = arcade.check_for_collision_with_list(slime, self.wall_list)
        if not hit_wall:
            if not hasattr(slime, 'stuck_timer'):
                slime.stuck_timer = 0
            slime.stuck_timer = 0
            return
        
        slime.center_x = old_x
        slime.center_y = old_y
        
        if not hasattr(slime, 'stuck_timer'):
            slime.stuck_timer = 0
        slime.stuck_timer += delta_time
        
        slime.center_x = old_x + dx * current_speed * delta_time
        hit_x = arcade.check_for_collision_with_list(slime, self.wall_list)
        if hit_x:
            slime.center_x = old_x
        
        slime.center_y = old_y + dy * current_speed * delta_time
        hit_y = arcade.check_for_collision_with_list(slime, self.wall_list)
        if hit_y:
            slime.center_y = old_y
        
        if hit_x and hit_y:
            if not hasattr(slime, 'perpendicular_dir'):
                slime.perpendicular_dir = random.choice([-1, 1])
            
            perp_dx = -dy * slime.perpendicular_dir
            perp_dy = dx * slime.perpendicular_dir
            
            slime.center_x = old_x + perp_dx * current_speed * delta_time
            slime.center_y = old_y + perp_dy * current_speed * delta_time
            
            if arcade.check_for_collision_with_list(slime, self.wall_list):
                slime.center_x = old_x
                slime.center_y = old_y
                slime.perpendicular_dir *= -1
        
        if slime.stuck_timer > 3.0:
            new_x, new_y = self.get_random_spawn_position(min_distance=4)
            slime.center_x = new_x
            slime.center_y = new_y
            slime.stuck_timer = 0

    def on_mouse_press(self, x, y, button, modifiers):
        # Проверяем клик по карточкам улучшений
        if self.upgrade_menu_open:
            if button == arcade.MOUSE_BUTTON_LEFT:
                for left, right, bottom, top, idx in self.upgrade_card_rects:
                    if left <= x <= right and bottom <= y <= top:
                        self.select_upgrade(idx)
                        break
            return
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.fire_bullet((x, y))
            self.lmb_held = True  # Для auto_fire_lmb
        elif button == arcade.MOUSE_BUTTON_RIGHT:
            self.auto_fire_key_down = True

    def on_mouse_release(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.lmb_held = False
        elif button == arcade.MOUSE_BUTTON_RIGHT:
            self.auto_fire_key_down = False

    def on_mouse_motion(self, x, y, dx, dy):
        self.mouse_position = (x, y)

    def on_key_press(self, key, modifiers):
        # ESC при победе - выход из игры
        if self.game_won and key == arcade.key.ESCAPE:
            arcade.close_window()
            return
        # Меню улучшений открыто - блокируем управление
        if self.upgrade_menu_open:
            return
        self.keys_pressed.add(key)
        
    def on_key_release(self, key, modifiers):
        if key in self.keys_pressed:
            self.keys_pressed.remove(key)

    def fire_bullet(self, screen_pos=None):
        if self.is_reloading:
            return
        
        # Сколько патронов нужно для выстрела
        ammo_cost = 2 if self.triple_shot else 1
        
        if self.ammo_current < ammo_cost:
            self.is_reloading = True
            self.reload_timer = self.reload_time
            return
        if screen_pos is None:
            screen_pos = self.mouse_position
        world_coords = self.world_camera.unproject(screen_pos)
        world_x = world_coords[0]
        world_y = world_coords[1]
        
        # Рассчитываем угол
        dx = world_x - self.player.center_x
        dy = world_y - self.player.center_y
        base_angle = math.atan2(dy, dx)
        
        # Базовая скорость и дальность пули
        bullet_speed = int(800 * self.bullet_speed_mult)
        bullet_range = int(1500 * self.bullet_range_mult)
        
        bullets_to_fire = []
        
        if self.triple_shot:
            # Три пули: -15°, 0°, +15°
            for angle_offset in [-0.26, 0, 0.26]:  # ~15 градусов
                angle = base_angle + angle_offset
                target_x = self.player.center_x + math.cos(angle) * 1000
                target_y = self.player.center_y + math.sin(angle) * 1000
                bullets_to_fire.append((target_x, target_y))
        else:
            bullets_to_fire.append((world_x, world_y))
        
        # Создаём пули
        for target_x, target_y in bullets_to_fire:
            bullet = Bullet(
                self.player.center_x,
                self.player.center_y,
                target_x,
                target_y,
                speed=bullet_speed,
                pierce_count=self.pierce_count
            )
            bullet.max_distance = bullet_range
            self.bullet_list.append(bullet)
        
        # Двойной выстрел - вторая пуля с задержкой
        if self.double_shot:
            for target_x, target_y in bullets_to_fire:
                self.pending_bullets.append((
                    0.08,  # Задержка 80мс
                    target_x, target_y,
                    bullet_speed, bullet_range, self.pierce_count
                ))
        
        arcade.play_sound(self.shoot_sound, volume=0.01)
        
        # Шанс не потратить патрон
        if random.randint(1, 100) > self.ammo_save_chance:
            self.ammo_current -= ammo_cost
        
        if self.ammo_current <= 0:
            self.is_reloading = True
            self.reload_timer = self.reload_time

    def update_camera(self, instant=False):
        target_x = self.player.center_x
        target_y = self.player.center_y
        if instant:
            self.world_camera.position = (target_x, target_y)
        else:
            self.world_camera.position = arcade.math.lerp_2d(
                self.world_camera.position,
                (target_x, target_y),
                0.15,
            )

    def world_to_chunk(self, world_x, world_y):
        """Конвертирует мировые координаты в координаты чанка"""
        chunk_size_pixels = CHUNK_SIZE * TILE_SIZE
        chunk_x = math.floor(world_x / chunk_size_pixels)
        chunk_y = math.floor(world_y / chunk_size_pixels)
        return chunk_x, chunk_y

    def update_chunks(self):
        """Обновляет чанки вокруг игрока"""
        player_chunk_x, player_chunk_y = self.world_to_chunk(self.player.center_x, self.player.center_y)
        
        needed_chunks = set()
        for dx in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1):
            for dy in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1):
                needed_chunks.add((player_chunk_x + dx, player_chunk_y + dy))
        
        chunks_to_remove = []
        for chunk_pos in self.chunks:
            if chunk_pos not in needed_chunks:
                chunks_to_remove.append(chunk_pos)
        
        for chunk_pos in chunks_to_remove:
            chunk = self.chunks[chunk_pos]
            for wall in chunk['walls']:
                wall.remove_from_sprite_lists()
            for floor in chunk['floors']:
                floor.remove_from_sprite_lists()
            # Удаляем бонусы из этого чанка
            for powerup in chunk.get('powerups', []):
                if powerup in self.powerup_list:
                    powerup.remove_from_sprite_lists()
            del self.chunks[chunk_pos]
        
        for chunk_pos in needed_chunks:
            if chunk_pos not in self.chunks:
                self.generate_chunk(chunk_pos[0], chunk_pos[1])

    def generate_chunk(self, chunk_x, chunk_y):
        """Генерирует один чанк"""
        chunk_walls = []
        chunk_floors = []
        chunk_powerups = []
        
        chunk_seed = hash((chunk_x, chunk_y, 12345))
        rng = random.Random(chunk_seed)
        
        base_world_x = chunk_x * CHUNK_SIZE * TILE_SIZE
        base_world_y = chunk_y * CHUNK_SIZE * TILE_SIZE
        
        # Находим ближайший биом
        chunk_center_x = chunk_x * CHUNK_SIZE + CHUNK_SIZE // 2
        chunk_center_y = chunk_y * CHUNK_SIZE + CHUNK_SIZE // 2
        best_biome = 0
        best_dist = float('inf')
        for idx, (sx, sy) in enumerate(self.biome_seeds):
            dist = abs(chunk_center_x - sx) + abs(chunk_center_y - sy)
            if dist < best_dist:
                best_dist = dist
                best_biome = idx % len(BIOME_COLORS)
        
        base_color = BIOME_COLORS[best_biome]
        
        # Создаём пол чанка
        chunk_floor = arcade.SpriteSolidColor(
            CHUNK_SIZE * TILE_SIZE, 
            CHUNK_SIZE * TILE_SIZE, 
            color=base_color
        )
        chunk_floor.center_x = base_world_x + (CHUNK_SIZE * TILE_SIZE) // 2
        chunk_floor.center_y = base_world_y + (CHUNK_SIZE * TILE_SIZE) // 2
        self.floor_list.append(chunk_floor)
        chunk_floors.append(chunk_floor)
        
        # Генерируем стены
        for local_x in range(CHUNK_SIZE):
            for local_y in range(CHUNK_SIZE):
                world_x = base_world_x + local_x * TILE_SIZE + TILE_SIZE // 2
                world_y = base_world_y + local_y * TILE_SIZE + TILE_SIZE // 2
                
                is_wall = self.is_wall_at(chunk_x * CHUNK_SIZE + local_x, chunk_y * CHUNK_SIZE + local_y, rng)
                
                if is_wall:
                    wall = arcade.SpriteSolidColor(
                        TILE_SIZE,
                        TILE_SIZE,
                        color=(40, 40, 40, 255),
                    )
                    wall.center_x = world_x
                    wall.center_y = world_y
                    self.wall_list.append(wall)
                    chunk_walls.append(wall)
        
        # Спавн бонуса с шансом 1/20 (раз в ~20 чанков)
        # Не спавним в стартовой зоне и если уже подобран
        if (abs(chunk_x) > 2 or abs(chunk_y) > 2) and (chunk_x, chunk_y) not in self.collected_powerups:
            # Используем хеш координат для детерминированного шанса
            powerup_hash = hash((chunk_x, chunk_y, 99999))
            if powerup_hash % 20 == 0:
                powerup = arcade.Sprite("pictures/photo/missile.png", scale=0.5)
                # Случайная позиция внутри чанка (но не на краю)
                offset_x = ((powerup_hash >> 8) % (CHUNK_SIZE - 4) + 2) * TILE_SIZE
                offset_y = ((powerup_hash >> 16) % (CHUNK_SIZE - 4) + 2) * TILE_SIZE
                powerup.center_x = base_world_x + offset_x
                powerup.center_y = base_world_y + offset_y
                self.powerup_list.append(powerup)
                chunk_powerups.append(powerup)
        
        self.chunks[(chunk_x, chunk_y)] = {
            'walls': chunk_walls, 
            'floors': chunk_floors, 
            'biome': best_biome,
            'powerups': chunk_powerups
        }

    def is_wall_at(self, grid_x, grid_y, rng=None):
        """Определяет, является ли клетка стеной"""
        if abs(grid_x) < 5 and abs(grid_y) < 5:
            return False
        
        tile_hash = hash((grid_x, grid_y, 777))
        if tile_hash % 100 < 2:
            return True
        
        cluster_x = grid_x // 12
        cluster_y = grid_y // 12
        cluster_hash = hash((cluster_x, cluster_y, 555))
        
        if cluster_hash % 30 == 0:
            local_x = grid_x % 12
            local_y = grid_y % 12
            if 5 <= local_x <= 6 and 5 <= local_y <= 6:
                return True
        
        return False

    def jitter_color(self, color, amount, rng=None):
        if rng is None:
            rng = random
        r = min(255, max(0, int(color[0] * (1 + rng.uniform(-amount, amount)))))
        g = min(255, max(0, int(color[1] * (1 + rng.uniform(-amount, amount)))))
        b = min(255, max(0, int(color[2] * (1 + rng.uniform(-amount, amount)))))
        return (r, g, b, 255)

    def get_random_spawn_position(self, min_distance=0, offscreen=True):
        """Возвращает случайную позицию для спавна (за экраном если offscreen=True)"""
        # Минимальное расстояние для спавна за экраном
        if offscreen:
            screen_half = max(SCREEN_WIDTH, SCREEN_HEIGHT) // 2 + 100  # За пределами экрана
            min_dist = screen_half
            max_dist = screen_half + 400
        else:
            min_dist = min_distance * TILE_SIZE
            max_dist = (min_distance + 10) * TILE_SIZE
        
        for _ in range(100):
            angle = random.uniform(0, math.pi * 2)
            dist = random.uniform(min_dist, max_dist)
            
            x = self.player.center_x + math.cos(angle) * dist
            y = self.player.center_y + math.sin(angle) * dist
            
            grid_x = int(x // TILE_SIZE)
            grid_y = int(y // TILE_SIZE)
            
            if not self.is_wall_at(grid_x, grid_y):
                return x, y
        
        # Фоллбэк - за экраном в случайном направлении
        angle = random.uniform(0, math.pi * 2)
        return (self.player.center_x + math.cos(angle) * 800, 
                self.player.center_y + math.sin(angle) * 800)


def main():
    game = MyGame(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    game.setup()
    arcade.run()


if __name__ == "__main__":
    main()
