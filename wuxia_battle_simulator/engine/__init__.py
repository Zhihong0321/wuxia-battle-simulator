"""Wuxia Battle Engine - Modular processor-based battle system.

This package contains the new modular battle engine that replaces the monolithic
BattleSimulator with a flexible processor pipeline architecture.

Main Components:
- BattleEngine: The main engine class that orchestrates battles
- BattleContext: Central data container for battle processing
- ProcessorPipeline: Manages the execution flow of processors
- StepProcessor: Base class for all battle step processors

Processors:
- ATBProcessor: Handles ATB clock and actor selection
- AIDecisionProcessor: Manages AI decision making
- ResourceValidationProcessor: Validates Qi and cooldowns
- MovementSkillProcessor: Handles dodge mechanics
- DefenseSkillProcessor: Handles defensive abilities
- DamageCalculationProcessor: Computes damage and outcomes
- StateUpdateProcessor: Applies state changes
- EventGenerationProcessor: Creates battle events
"""

# New modular engine components
from .battle_engine import BattleEngine
from .battle_context import BattleContext
from .processor_pipeline import ProcessorPipeline
from .step_processor import StepProcessor

# Import battle simulator components for compatibility
from .battle_simulator import BattleSimulator, BattleEvent, _SkillTierParams

# Import all processors
from .processors import (
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
    # New engine components
    'BattleEngine',
    'BattleContext',
    'ProcessorPipeline',
    'StepProcessor',
    
    # Legacy compatibility
    'BattleSimulator',
    'BattleEvent',
    '_SkillTierParams',
    
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