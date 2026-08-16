"""
Rotation data for the prompter overlay.

Ticks are RS3 game ticks (1 tick = 0.6s). Timings here are approximations
meant to train muscle memory against the tick metronome -- they are NOT
derived from reading the game's actual adrenaline/cooldown state. Tune
`loop_interval_ticks` per style to match your own adrenaline generation
speed (gear, aura, style) if the default cadence feels off.

Each style is built for "Revo Basics" bars: basics auto-fire under
Revolution, so this only prompts the manual threshold/ultimate presses --
the stuff Revolution won't press for you.
"""

STYLES = {
    "necromancy": {
        "label": "Necromancy",
        "color": "#a780f2",
        "opener": [
            ("Volley of Souls", 0),
            ("Bloat", 3),
            ("Command Vengeful Ghost", 3),
            ("Invoke Death", 6),
            ("Living Death", 2),
        ],
        "loop": ["Death Skulls", "Bloodsplicer"],
        "loop_interval_ticks": 8,
    },
    "magic": {
        "label": "Magic",
        "color": "#6ea3ff",
        "opener": [
            ("Combust", 0),
            ("Wild Magic", 5),
            ("Asphyxiate", 2),
            ("Sunshine", 6),
        ],
        "loop": ["Concentrated Blast", "Asphyxiate"],
        "loop_interval_ticks": 8,
    },
    "ranged": {
        "label": "Ranged",
        "color": "#57c98a",
        "opener": [
            ("Rapid Fire", 0),
            ("Snipe", 5),
        ],
        "loop": ["Snipe", "Ricochet"],
        "loop_interval_ticks": 8,
    },
    "melee": {
        "label": "Melee",
        "color": "#ff7a70",
        "opener": [
            ("Fury", 0),
            ("Assault", 4),
            ("Meteor Strike / Death's Swiftness", 6),
        ],
        "loop": ["Fury", "Assault"],
        "loop_interval_ticks": 8,
    },
}

STYLE_ORDER = ["necromancy", "magic", "ranged", "melee"]
