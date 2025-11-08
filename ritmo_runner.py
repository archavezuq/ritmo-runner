import pygame
import random
import math
import numpy as np
import io
from collections import deque
from pygame.locals import *

# === INICIALIZACIÓN ===
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

WIDTH, HEIGHT = 1200, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Ritmo Runner - Aprende Ritmos con Música 🎵")
clock = pygame.time.Clock()

# Fuentes mejoradas
try:
    font = pygame.font.SysFont('arial', 48, bold=True)
    small_font = pygame.font.SysFont('arial', 32)
    tiny_font = pygame.font.SysFont('arial', 24)
    title_font = pygame.font.SysFont('arial', 72, bold=True)
except:
    font = pygame.font.Font(None, 48)
    small_font = pygame.font.Font(None, 32)
    tiny_font = pygame.font.Font(None, 24)
    title_font = pygame.font.Font(None, 72)

# === COLORES ===
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (220, 50, 50)
GREEN = (50, 220, 50)
BLUE = (50, 120, 220)
YELLOW = (255, 220, 50)
PURPLE = (180, 50, 255)
ORANGE = (255, 150, 50)
CYAN = (50, 220, 220)
GOLD = (255, 215, 0)
DARK_GRAY = (40, 40, 40)
LIGHT_GRAY = (200, 200, 200)

# === CONFIGURACIÓN RÍTMICA ===
BPM = 120
BEAT_DURATION = 60 / BPM
HIT_WINDOW_PERFECT = 0.08
HIT_WINDOW_GOOD = 0.15
HIT_WINDOW_OK = 0.25

# === TECLAS Y NOTAS ===
KEYS = [K_a, K_s, K_d, K_f]
KEY_NAMES = ['A', 'S', 'D', 'F']
NOTE_PITCHES = [60, 62, 64, 65]  # C4, D4, E4, F4
LANE_COLORS = [(255, 100, 100), (100, 255, 100), (100, 100, 255), (255, 255, 100)]

# === FIGURAS RÍTMICAS ===
FIGURES = {
    'redonda': {'duration': 4.0, 'color': (255, 50, 50), 'name': 'Redonda'},
    'blanca': {'duration': 2.0, 'color': (100, 150, 255), 'name': 'Blanca'},
    'negra': {'duration': 1.0, 'color': (255, 200, 50), 'name': 'Negra'},
    'corchea': {'duration': 0.5, 'color': (50, 255, 150), 'name': 'Corchea'},
    'semicorchea': {'duration': 0.25, 'color': (255, 100, 255), 'name': 'Semicorchea'},
}

# === NIVELES ===
LEVELS = [
    {
        'name': 'Principiante',
        'figures': ['negra', 'blanca', 'corchea'],
        'speed': 300,
        'spawn_rate': 2.5,
        'bg_color': (135, 206, 235)
    },
    {
        'name': 'Intermedio',
        'figures': ['negra', 'blanca', 'corchea', 'redonda'],
        'speed': 380,
        'spawn_rate': 2.0,
        'bg_color': (100, 149, 237)
    },
    {
        'name': 'Avanzado',
        'figures': ['negra', 'blanca', 'corchea', 'semicorchea', 'redonda'],
        'speed': 450,
        'spawn_rate': 1.5,
        'bg_color': (75, 0, 130)
    },
]

# === ESTADOS ===
MENU, TUTORIAL, PLAYING, PAUSED, GAMEOVER = 0, 1, 2, 3, 4


# === CLASE PARTÍCULA MEJORADA ===
class Particle:
    def __init__(self, x, y, color, velocity=(0, 0)):
        self.x = x
        self.y = y
        self.vx, self.vy = velocity
        self.life = 60
        self.max_life = 60
        self.color = color
        self.size = random.randint(3, 8)
    
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.2  # Gravedad
        self.vx *= 0.98  # Fricción
        self.life -= 1
        return self.life > 0
    
    def draw(self, surface):
        alpha = int(255 * (self.life / self.max_life))
        size = int(self.size * (self.life / self.max_life))
        if size > 0:
            s = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, alpha), (size, size), size)
            surface.blit(s, (int(self.x - size), int(self.y - size)))


# === CLASE NOTA MEJORADA ===
class Note:
    def __init__(self, note_type, lane, beat_time, level):
        self.type = note_type
        self.lane = lane
        self.beat_time = beat_time
        self.duration = FIGURES[note_type]['duration']
        self.x = WIDTH + 100
        self.y = 0
        self.hit = False
        self.missed = False
        self.level = level
        self.color = FIGURES[note_type]['color']
        self.pulse = 0
    
    def update(self, dt, current_level):
        speed = LEVELS[current_level]['speed']
        self.x -= speed * dt
        self.pulse += dt * 5
        return self.x > -100
    
    def draw(self, surface, lane_y):
        if self.hit or self.missed:
            return
        
        # Efecto de pulso
        pulse_size = 3 * abs(math.sin(self.pulse))
        size = 40 + pulse_size
        
        # Sombra
        shadow_surf = pygame.Surface((int(size + 10), int(size + 10)), pygame.SRCALPHA)
        pygame.draw.circle(shadow_surf, (0, 0, 0, 100), (int(size/2 + 5), int(size/2 + 5)), int(size/2))
        surface.blit(shadow_surf, (int(self.x - size/2), int(lane_y - size/2)))
        
        # Nota principal
        pygame.draw.circle(surface, self.color, (int(self.x), int(lane_y)), int(size/2))
        pygame.draw.circle(surface, WHITE, (int(self.x), int(lane_y)), int(size/2), 3)
        
        # Letra del tipo
        text = tiny_font.render(FIGURES[self.type]['name'][:3], True, BLACK)
        text_rect = text.get_rect(center=(int(self.x), int(lane_y)))
        surface.blit(text, text_rect)


# === CLASE JUGADOR ===
class Player:
    def __init__(self):
        self.x = 150
        self.y = HEIGHT - 180
        self.frame = 0
        self.scale = 1.0
        self.target_scale = 1.0
    
    def update(self, dt):
        self.frame += dt * 12
        self.scale += (self.target_scale - self.scale) * 0.2
    
    def jump_animation(self):
        self.target_scale = 1.3
    
    def reset_scale(self):
        self.target_scale = 1.0
    
    def draw(self, surface):
        # Animación de caminar
        bob = math.sin(self.frame) * 5
        
        # Cuerpo (escalado)
        scale = self.scale
        w, h = int(40 * scale), int(60 * scale)
        
        # Sombra
        pygame.draw.ellipse(surface, (0, 0, 0, 50), 
                          (self.x - 20, self.y + 20, 40, 10))
        
        # Cabeza
        head_y = self.y - 30 + bob
        pygame.draw.circle(surface, (255, 200, 150), 
                         (int(self.x), int(head_y)), int(15 * scale))
        pygame.draw.circle(surface, BLACK, 
                         (int(self.x), int(head_y)), int(15 * scale), 2)
        
        # Ojos
        eye_offset = int(5 * scale)
        pygame.draw.circle(surface, BLACK, 
                         (int(self.x - eye_offset), int(head_y - 2)), 3)
        pygame.draw.circle(surface, BLACK, 
                         (int(self.x + eye_offset), int(head_y - 2)), 3)
        
        # Sonrisa
        pygame.draw.arc(surface, BLACK, 
                       (int(self.x - 8*scale), int(head_y - 5), int(16*scale), int(12*scale)),
                       3.14, 6.28, 2)
        
        # Cuerpo
        body_rect = pygame.Rect(int(self.x - 10*scale), int(self.y - 15 + bob), 
                               int(20*scale), int(25*scale))
        pygame.draw.rect(surface, BLUE, body_rect, border_radius=5)
        
        # Brazos
        arm_wave = math.sin(self.frame * 2) * 10
        pygame.draw.line(surface, (255, 200, 150), 
                        (int(self.x - 10*scale), int(self.y - 5 + bob)),
                        (int(self.x - 20*scale), int(self.y + 5 + bob + arm_wave)), 5)
        pygame.draw.line(surface, (255, 200, 150), 
                        (int(self.x + 10*scale), int(self.y - 5 + bob)),
                        (int(self.x + 20*scale), int(self.y + 5 + bob - arm_wave)), 5)
        
        # Piernas
        leg_offset = math.sin(self.frame * 2) * 8
        pygame.draw.line(surface, BLACK, 
                        (int(self.x - 5*scale), int(self.y + 10 + bob)),
                        (int(self.x - 8*scale), int(self.y + 25 + leg_offset)), 6)
        pygame.draw.line(surface, BLACK, 
                        (int(self.x + 5*scale), int(self.y + 10 + bob)),
                        (int(self.x + 8*scale), int(self.y + 25 - leg_offset)), 6)


# === CLASE JUEGO ===
class Game:
    def __init__(self):
        self.state = MENU
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.current_level = 0
        self.notes = []
        self.particles = []
        self.player = Player()
        self.scroll_x = 0
        self.start_time = 0
        self.beat_timer = 0
        self.feedback_text = None
        self.feedback_timer = 0
        self.stats = {'perfect': 0, 'good': 0, 'ok': 0, 'miss': 0}
        self.tutorial_step = 0
        self.lane_flash = [0, 0, 0, 0]
        self.streak_particles = []
        
        # Pre-cargar sonidos
        self.sounds = self.generate_sounds()
    
    def generate_sounds(self):
        sounds = {}
        for i, pitch in enumerate(NOTE_PITCHES):
            for fig_name, fig_data in FIGURES.items():
                sounds[f"{fig_name}_{i}"] = self.generate_sine_sound(pitch, fig_data['duration'])
        return sounds
    
    def generate_sine_sound(self, pitch, duration_beats):
        duration = duration_beats * BEAT_DURATION * 0.5  # Sonidos más cortos
        sample_rate = 44100
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        freq = 440 * (2 ** ((pitch - 69) / 12))
        
        # Envolvente ADSR mejorada
        attack = int(sample_rate * 0.01)
        decay = int(sample_rate * 0.05)
        release = int(sample_rate * 0.1)
        sustain_level = 0.7
        
        envelope = np.ones_like(t)
        if len(envelope) > attack:
            envelope[:attack] = np.linspace(0, 1, attack)
        if len(envelope) > attack + decay:
            envelope[attack:attack+decay] = np.linspace(1, sustain_level, decay)
        if len(envelope) > release:
            envelope[-release:] = np.linspace(sustain_level, 0, release)
        
        # Onda con armónicos
        wave = 0.4 * np.sin(2 * np.pi * freq * t)
        wave += 0.2 * np.sin(4 * np.pi * freq * t)  # Octava
        wave += 0.1 * np.sin(6 * np.pi * freq * t)  # Quinta
        wave *= envelope
        
        wave = (wave * 32767).astype(np.int16)
        stereo = np.column_stack((wave, wave))
        return pygame.mixer.Sound(pygame.sndarray.make_sound(stereo))
    
    def spawn_note(self):
        level_data = LEVELS[self.current_level]
        fig = random.choice(level_data['figures'])
        lane = random.randint(0, 3)
        current_time = (pygame.time.get_ticks() / 1000.0) - self.start_time
        current_beat = current_time / BEAT_DURATION
        beat_time = current_beat + random.uniform(3, 5)
        
        note = Note(fig, lane, beat_time, self.current_level)
        self.notes.append(note)
    
    def check_hit(self, key):
        current_time = (pygame.time.get_ticks() / 1000.0) - self.start_time
        lane = KEYS.index(key)
        
        # Encontrar nota más cercana en el carril
        best_note = None
        best_diff = float('inf')
        
        for note in self.notes:
            if note.hit or note.missed or note.lane != lane:
                continue
            expected = note.beat_time * BEAT_DURATION
            diff = abs(current_time - expected)
            if diff < best_diff and diff < HIT_WINDOW_OK:
                best_diff = diff
                best_note = note
        
        if best_note:
            best_note.hit = True
            accuracy = 1 - (best_diff / HIT_WINDOW_OK)
            
            # Clasificar hit
            if best_diff < HIT_WINDOW_PERFECT:
                hit_type = 'PERFECT!'
                color = GOLD
                multiplier = 1.5
                self.stats['perfect'] += 1
            elif best_diff < HIT_WINDOW_GOOD:
                hit_type = 'GOOD'
                color = GREEN
                multiplier = 1.2
                self.stats['good'] += 1
            else:
                hit_type = 'OK'
                color = YELLOW
                multiplier = 1.0
                self.stats['ok'] += 1
            
            # Puntuación
            base_points = int(100 * accuracy)
            combo_bonus = self.combo * 10
            points = int((base_points + combo_bonus) * multiplier)
            self.score += points
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            
            # Feedback
            self.feedback_text = f"{hit_type} +{points}"
            self.feedback_timer = 1.0
            
            # Efectos
            self.player.jump_animation()
            self.lane_flash[lane] = 1.0
            
            # Sonido
            sound_key = f"{best_note.type}_{lane}"
            if sound_key in self.sounds:
                self.sounds[sound_key].play()
            
            # Partículas
            self.add_particles(self.player.x, self.player.y - 20, color, 15)
            
            # Streak particles
            if self.combo > 0 and self.combo % 10 == 0:
                self.add_streak_effect()
            
            return True
        
        # Miss
        self.combo = 0
        self.feedback_text = "MISS"
        self.feedback_timer = 0.5
        self.add_particles(self.player.x, self.player.y - 20, RED, 8)
        return False
    
    def add_particles(self, x, y, color, count):
        for _ in range(count):
            vx = random.uniform(-4, 4)
            vy = random.uniform(-6, -2)
            self.particles.append(Particle(x, y, color, (vx, vy)))
    
    def add_streak_effect(self):
        for i in range(20):
            angle = (i / 20) * math.pi * 2
            vx = math.cos(angle) * 6
            vy = math.sin(angle) * 6
            self.particles.append(Particle(self.player.x, self.player.y - 20, GOLD, (vx, vy)))
    
    def update(self, dt):
        if self.state == PLAYING:
            # Scroll
            self.scroll_x += LEVELS[self.current_level]['speed'] * dt * 0.5
            
            # Player
            self.player.update(dt)
            self.player.reset_scale()
            
            # Spawn notes
            self.beat_timer += dt
            spawn_rate = LEVELS[self.current_level]['spawn_rate']
            if self.beat_timer > spawn_rate:
                self.spawn_note()
                self.beat_timer = 0
            
            # Update notes
            self.notes = [n for n in self.notes if n.update(dt, self.current_level)]
            
            # Check misses
            current_time = (pygame.time.get_ticks() / 1000.0) - self.start_time
            for note in self.notes:
                if not note.hit and not note.missed:
                    expected = note.beat_time * BEAT_DURATION
                    if current_time - expected > HIT_WINDOW_OK:
                        note.missed = True
                        self.combo = 0
                        self.stats['miss'] += 1
            
            # Update particles
            self.particles = [p for p in self.particles if p.update()]
            
            # Lane flash decay
            for i in range(4):
                self.lane_flash[i] *= 0.9
            
            # Feedback timer
            if self.feedback_timer > 0:
                self.feedback_timer -= dt
            
            # Level up
            level_threshold = 2000 * (self.current_level + 1)
            if self.score > level_threshold and self.current_level < len(LEVELS) - 1:
                self.current_level += 1
                self.add_particles(WIDTH//2, HEIGHT//2, PURPLE, 30)
    
    def draw_background(self):
        level_data = LEVELS[self.current_level]
        bg_color = level_data['bg_color']
        
        # Gradiente de cielo
        for y in range(HEIGHT):
            ratio = y / HEIGHT
            r = int(bg_color[0] * (1 - ratio) + 30 * ratio)
            g = int(bg_color[1] * (1 - ratio) + 30 * ratio)
            b = int(bg_color[2] * (1 - ratio) + 50 * ratio)
            pygame.draw.line(screen, (r, g, b), (0, y), (WIDTH, y))
        
        # Nubes animadas
        for i in range(5):
            x = (i * 300 + self.scroll_x * 0.3) % (WIDTH + 200) - 100
            y = 80 + i * 40
            pygame.draw.circle(screen, (255, 255, 255, 100), (int(x), int(y)), 40)
            pygame.draw.circle(screen, (255, 255, 255, 100), (int(x + 30), int(y)), 50)
            pygame.draw.circle(screen, (255, 255, 255, 100), (int(x + 60), int(y)), 35)
    
    def draw_lanes(self):
        # Líneas de carriles con efectos
        lane_y_start = 350
        for i in range(4):
            lane_y = lane_y_start + i * 60
            
            # Flash effect
            flash = self.lane_flash[i]
            alpha = int(100 + flash * 155)
            color = (*LANE_COLORS[i], alpha)
            
            # Línea del carril
            line_surf = pygame.Surface((WIDTH, 4), pygame.SRCALPHA)
            line_surf.fill(color)
            screen.blit(line_surf, (0, lane_y))
            
            # Zona de hit (en la posición del jugador)
            hit_zone_surf = pygame.Surface((80, 60), pygame.SRCALPHA)
            pygame.draw.rect(hit_zone_surf, (*LANE_COLORS[i], 80 + int(flash * 100)), 
                           (0, 0, 80, 60), border_radius=10)
            pygame.draw.rect(hit_zone_surf, WHITE, (0, 0, 80, 60), 3, border_radius=10)
            screen.blit(hit_zone_surf, (self.player.x - 40, lane_y - 30))
            
            # Etiqueta de tecla
            key_text = small_font.render(KEY_NAMES[i], True, WHITE)
            key_rect = key_text.get_rect(center=(self.player.x, lane_y))
            screen.blit(key_text, key_rect)
    
    def draw_ui(self):
        # Panel superior con sombra
        panel_surf = pygame.Surface((WIDTH, 120), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, (0, 0, 0, 150), (0, 0, WIDTH, 120))
        screen.blit(panel_surf, (0, 0))
        
        # Score
        score_text = font.render(f"PUNTOS: {self.score}", True, GOLD)
        screen.blit(score_text, (20, 15))
        
        # Combo
        combo_color = GOLD if self.combo > 20 else YELLOW if self.combo > 10 else WHITE
        combo_text = font.render(f"COMBO: {self.combo}x", True, combo_color)
        screen.blit(combo_text, (20, 65))
        
        # Nivel
        level_name = LEVELS[self.current_level]['name']
        level_text = small_font.render(f"Nivel: {level_name}", True, ORANGE)
        screen.blit(level_text, (WIDTH - 300, 20))
        
        # Barra de progreso al siguiente nivel
        if self.current_level < len(LEVELS) - 1:
            next_threshold = 2000 * (self.current_level + 1)
            progress = min(self.score / next_threshold, 1.0)
            bar_width = 250
            bar_height = 20
            bar_x = WIDTH - 300
            bar_y = 60
            
            # Fondo
            pygame.draw.rect(screen, DARK_GRAY, (bar_x, bar_y, bar_width, bar_height), border_radius=10)
            # Progreso
            pygame.draw.rect(screen, GREEN, (bar_x, bar_y, int(bar_width * progress), bar_height), border_radius=10)
            # Borde
            pygame.draw.rect(screen, WHITE, (bar_x, bar_y, bar_width, bar_height), 2, border_radius=10)
            
            progress_text = tiny_font.render(f"{int(progress*100)}%", True, WHITE)
            screen.blit(progress_text, (bar_x + bar_width//2 - 20, bar_y + 2))
        
        # Feedback
        if self.feedback_timer > 0:
            alpha = int(255 * self.feedback_timer)
            feedback_surf = font.render(self.feedback_text, True, WHITE)
            feedback_surf.set_alpha(alpha)
            feedback_rect = feedback_surf.get_rect(center=(WIDTH//2, 200))
            screen.blit(feedback_surf, feedback_rect)
        
        # Beat indicator
        current_time = (pygame.time.get_ticks() / 1000.0) - self.start_time
        current_beat = current_time / BEAT_DURATION
        beat_pulse = abs(math.sin(current_beat * math.pi))
        beat_size = 15 + int(beat_pulse * 15)
        pygame.draw.circle(screen, RED, (WIDTH - 50, HEIGHT - 50), beat_size)
        pygame.draw.circle(screen, WHITE, (WIDTH - 50, HEIGHT - 50), beat_size, 3)
    
    def draw_menu(self):
        # Fondo animado
        for i in range(10):
            x = (i * 150 + self.scroll_x) % (WIDTH + 100)
            y = 300 + math.sin(self.scroll_x * 0.01 + i) * 50
            size = 30 + math.sin(self.scroll_x * 0.02 + i) * 10
            color = FIGURES[list(FIGURES.keys())[i % len(FIGURES)]]['color']
            pygame.draw.circle(screen, color, (int(x), int(y)), int(size))
        
        # Título
        title = title_font.render("RITMO RUNNER", True, GOLD)
        title_shadow = title_font.render("RITMO RUNNER", True, BLACK)
        screen.blit(title_shadow, (WIDTH//2 - title.get_width()//2 + 5, 105))
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
        
        # Subtítulo
        subtitle = small_font.render("🎵 Aprende Ritmos con Música 🎵", True, WHITE)
        screen.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, 200))
        
        # Opciones
        options = [
            ("ESPACIO - Jugar", GREEN),
            ("T - Tutorial", CYAN),
            ("ESC - Salir", RED)
        ]
        
        for i, (text, color) in enumerate(options):
            opt = small_font.render(text, True, color)
            screen.blit(opt, (WIDTH//2 - opt.get_width()//2, 320 + i * 60))
        
        # Best score
        if self.max_combo > 0:
            best = tiny_font.render(f"Mejor Combo: {self.max_combo}x | Puntuación: {self.score}", True, YELLOW)
            screen.blit(best, (WIDTH//2 - best.get_width()//2, 550))
    
    def draw_tutorial(self):
        # Panel
        panel_w, panel_h = 800, 500
        panel_x = (WIDTH - panel_w) // 2
        panel_y = (HEIGHT - panel_h) // 2
        
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, (0, 0, 0, 200), (0, 0, panel_w, panel_h), border_radius=20)
        pygame.draw.rect(panel_surf, GOLD, (0, 0, panel_w, panel_h), 5, border_radius=20)
        screen.blit(panel_surf, (panel_x, panel_y))
        
        # Título
        title = font.render("TUTORIAL", True, GOLD)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, panel_y + 30))
        
        # Instrucciones
        instructions = [
            "🎹 Presiona A, S, D, F cuando las notas lleguen a la zona",
            "⏱️ Timing PERFECTO = Más puntos",
            "🔥 Mantén combos para multiplicadores",
            "📈 Completa niveles para desbloquear nuevas figuras",
            "⏸️ ESPACIO = Pausa | R = Reiniciar"