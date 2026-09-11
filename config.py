"""
Centralized configuration settings for Useless Project.
Coordinates chances, timers, exhaustion penalties, and stamina rates.
"""

# ==========================================
# Audio Drop & Pump Mini-Game
# ==========================================
# 80% chance of volume dropping to 0 when sound is detected
AUDIO_DROP_CHANCE = 0.80

# 30 seconds cooldown after successfully restoring volume
AUDIO_COOLDOWN_SECONDS = 30.0

# Sensitivity threshold to detect audio playback
AUDIO_PEAK_THRESHOLD = 0.02

# Audio poll interval in seconds
AUDIO_POLL_INTERVAL = 0.1

# Volume lost per second when user stops pumping
PUMP_DECAY_RATE_PER_SEC = 14.0

# Volume level restored on success (100%)
VOLUME_RESTORE_LEVEL = 1.0

# ==========================================
# Screen Flashbang Hazard
# ==========================================
# Periodic check every minute (60s)
HAZARD_INTERVAL_SECONDS = 30.0

# 60% chance of screen flashbang each minute
FLASHBANG_CHANCE = 0.70

# Flashbang visual fade duration in seconds
FLASHBANG_FADE_SECONDS = 2.5

# Flashbang peak hold duration in seconds
FLASHBANG_HOLD_SECONDS = 0.2

# ==========================================
# Mouse Stamina System
# ==========================================
# Maximum stamina capacity
MOUSE_MAX_STAMINA = 100.0

# Stamina drain per pixel of mouse travel
MOUSE_DRAIN_PER_PIXEL = 0.045

# Stamina recovery rate per second when resting
MOUSE_RECOVERY_RATE_PER_SEC = 20.0

# Duration of the 'ONE MOMENT OF SILENCE' freeze when stamina runs out (in seconds)
MOMENT_OF_SILENCE_SECONDS = 60.0

# Stamina recovery rate per second during exhaustion (fills exactly during the 60s silence)
MOUSE_EXHAUSTED_RECOVERY_RATE_PER_SEC = MOUSE_MAX_STAMINA / MOMENT_OF_SILENCE_SECONDS

# Windows mouse speed parameter when exhausted (1 is the lowest Windows setting)
MOUSE_EXHAUSTED_SPEED = 1

# Active cursor drag damping factor when exhausted (0.12 = cursor moves at 12% speed)
# Guarantees the mouse feels extremely slow regardless of mouse hardware DPI!
MOUSE_EXHAUSTED_DAMPING_FACTOR = 0.12

# HUD update rate in ms (~60 FPS)
MOUSE_HUD_TICK_MS = 16

# Visual colors for stamina states
STAMINA_COLOR_HIGH = "#FFFFFF"    # White: 50% - 100%
STAMINA_COLOR_MID = "#FFA500"     # Orange: 20% - 50%
STAMINA_COLOR_LOW = "#FF2222"     # Red: 0% - 20%

# Floating bar dimensions
BAR_WIDTH = 56
BAR_HEIGHT = 8
BAR_Y_OFFSET = -28                # Pixels above the cursor tip

# ==========================================
# Keyboard Random Scrambler
# ==========================================
# 40% chance of a typed letter being randomly changed to an adjacent/different letter
KEYBOARD_SCRAMBLE_CHANCE = 0.40

# ==========================================
# Click-Triggered Media Chaos
# ==========================================
# 60% chance for each chaos event on every click
CLICK_CHAOS_CHANCE = 0.60

# 500 tiny bouncing cats
CLICK_CAT_COUNT = 500

# 50 spinning low-poly rats
CLICK_RAT_COUNT = 50

# 4 soul-staring corner Furbys
CLICK_FURBY_COUNT = 4

# 60% chance for each music track in music/ folder (except meow.m4a)
CLICK_MUSIC_CHANCE = 0.60

# Stagger interval in milliseconds when spawning cats
CAT_SPAWN_STAGGER_MS = 20

# Duration in seconds for which click visual entities (cats, rats, furbys, videos) stay on screen
CLICK_VISUAL_DURATION_SECONDS = 10.0

# Rectangular video frame counts and dimensions (2-5 small frames anywhere on display)
CLICK_VIDEO_MIN_COUNT = 2
CLICK_VIDEO_MAX_COUNT = 5
CLICK_VIDEO_WIDTH = 160
CLICK_VIDEO_HEIGHT = 218

# ==========================================
# Reddit Meme Sourcing (Images & Videos Only)
# ==========================================
# Target meme subreddits to source media from
REDDIT_SUBREDDITS = ["memes", "dankmemes"]

# Maximum number of downloaded meme media files to keep in local cache
REDDIT_CACHE_MAX_FILES = 50

# Interval in seconds between background meme refreshes (5 minutes)
REDDIT_FETCH_INTERVAL_SECONDS = 300.0

# Optional Reddit OAuth app credentials (leave empty to use public endpoints out of the box)
REDDIT_CLIENT_ID = ""
REDDIT_CLIENT_SECRET = ""

