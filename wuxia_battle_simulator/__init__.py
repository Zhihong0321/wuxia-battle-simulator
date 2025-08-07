"""Wuxia Battle Simulator - A modular battle engine for wuxia combat simulation.

This package provides both the legacy BattleSimulator and the new modular BattleEngine.

Legacy Components:
- BattleSimulator: The original monolithic battle simulator

New Modular Engine:
- BattleEngine: The new processor-based battle engine
- BattleEngineAdapter: Compatibility adapter for migration

Core Components:
- GameState: Battle state management
- Character: Character data structures
- AI: Artificial intelligence interfaces
- Clock: ATB timing system
- RNG: Deterministic random number generation
"""

# Legacy engine (for backward compatibility)
from .engine import BattleSimulator, BattleEvent

# New modular engine
from .engine import BattleEngine, BattleContext, ProcessorPipeline
from .engine.migration import BattleEngineAdapter

# Core components
from .engine.game_state import GameState, Stats as CharacterStats, EquippedSkill, CharacterState as Character
from .engine.ai_policy import HeuristicAI as SimpleAI
from .engine.atb_system import ATBClock

# Processors (for advanced customization)
from .engine import (
    ATBProcessor,
    AIDecisionProcessor,
    ResourceValidationProcessor,
    MovementSkillProcessor,
    DefenseSkillProcessor,
    DamageCalculationProcessor,
    StateUpdateProcessor,
    EventGenerationProcessor
)

__all__ = [
    # Legacy components
    'BattleSimulator',
    'BattleEvent',
    
    # New engine components
    'BattleEngine',
    'BattleContext',
    'ProcessorPipeline',
    'BattleEngineAdapter',
    
    # Core components
    'GameState',
    'Character',
    'CharacterStats',
    'EquippedSkill',
    'SimpleAI',
    'ATBClock',
    
    # Processors
    'ATBProcessor',
    'AIDecisionProcessor',
    'ResourceValidationProcessor',
    'MovementSkillProcessor',
    'DefenseSkillProcessor',
    'DamageCalculationProcessor',
    'StateUpdateProcessor',
    'EventGenerationProcessor'
]

# Version information
__version__ = '2.0.0'
__author__ = 'Wuxia Battle Engine Team'
__description__ = 'Modular battle engine for wuxia combat simulation'