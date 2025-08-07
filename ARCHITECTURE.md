# Wuxia Battle Simulator - Modular Architecture

## Overview

The Wuxia Battle Simulator has been redesigned with a modular, processor-based architecture that provides better maintainability, extensibility, and testability while maintaining full backward compatibility.

## Architecture Components

### Core Engine

#### BattleEngine
The new main battle engine that orchestrates the entire battle simulation process using a processor pipeline.

```python
from wuxia_battle_simulator import BattleEngine, GameState, SimpleAI, ATBClock, RNG

# Create engine
engine = BattleEngine(
    game_state=GameState(...),
    ai=SimpleAI(),
    clock=ATBClock(),
    rng=RNG(seed=42)
)

# Run battle
while not engine.is_battle_over():
    engine.step()

events = engine.get_events()
```

#### BattleContext
A central data container that flows through the processor pipeline, holding:
- Battle state and configuration
- Current step data (actor, skill, target)
- Processing results and intermediate calculations
- Events and metadata

#### ProcessorPipeline
Orchestrates the execution of battle step processors in sequence, handling data flow and error management.

### Processor System

The battle logic is broken down into specialized processors:

#### 1. ATBProcessor
- Advances ATB clock
- Selects next acting character
- Updates time units and cooldowns

#### 2. AIDecisionProcessor
- Determines AI actions (skill and target selection)
- Validates AI decisions
- Provides fallback to "defend" action

#### 3. ResourceValidationProcessor
- Checks Qi availability
- Validates skill cooldowns
- Can abort step if resources insufficient

#### 4. MovementSkillProcessor
- Handles target dodge attempts
- Calculates hit/miss/partial hit results
- Generates dodge events

#### 5. DefenseSkillProcessor
- Processes defensive abilities
- Generates defense events
- Retrieves defense parameters

#### 6. DamageCalculationProcessor
- Computes base damage
- Applies critical hits and damage reduction
- Categorizes damage levels

#### 7. StateUpdateProcessor
- Applies damage to targets
- Updates actor Qi and cooldowns
- Critical processor (cannot be skipped)

#### 8. EventGenerationProcessor
- Creates final battle events
- Handles special events (critical hits, defeats)
- Critical processor (always generates events)

## Migration Guide

### Option 1: Direct Migration

Replace `BattleSimulator` with `BattleEngine`:

```python
# Old code
from wuxia_battle_simulator import BattleSimulator
simulator = BattleSimulator(game_state, ai, clock, rng)

# New code
from wuxia_battle_simulator import BattleEngine
engine = BattleEngine(game_state, ai, clock, rng)
```

### Option 2: Compatibility Adapter

Use the adapter for gradual migration:

```python
from wuxia_battle_simulator import BattleEngineAdapter

# Drop-in replacement for BattleSimulator
simulator = BattleEngineAdapter(game_state, ai, clock, rng)
# All existing BattleSimulator methods work unchanged
```

### Option 3: Custom Processors

Extend the engine with custom logic:

```python
from wuxia_battle_simulator import BattleEngine, StepProcessor

class CustomProcessor(StepProcessor):
    def can_process(self, context):
        return True  # Always run
    
    def process(self, context):
        # Custom battle logic
        pass

engine = BattleEngine(game_state, ai, clock, rng)
engine.add_processor(CustomProcessor(), position=5)  # Insert at position 5
```

## Benefits of the New Architecture

### 1. Modularity
- Each processor handles a specific aspect of battle logic
- Easy to understand, test, and modify individual components
- Clear separation of concerns

### 2. Extensibility
- Add custom processors for new mechanics
- Remove or replace existing processors
- Modify processor order for different battle systems

### 3. Maintainability
- Smaller, focused code units
- Easier debugging and testing
- Clear data flow through BattleContext

### 4. Backward Compatibility
- Existing code continues to work with BattleEngineAdapter
- Gradual migration path
- Same API surface for basic usage

### 5. Testability
- Individual processors can be unit tested
- Mock contexts for isolated testing
- Pipeline can be tested with custom processor combinations

## Advanced Usage

### Custom Processor Development

```python
from wuxia_battle_simulator import StepProcessor

class StatusEffectProcessor(StepProcessor):
    """Handles poison, buffs, debuffs, etc."""
    
    def __init__(self, critical=False):
        super().__init__(critical)
    
    def can_process(self, context):
        # Only process if target has status effects
        return hasattr(context.target, 'status_effects')
    
    def process(self, context):
        # Apply status effect logic
        for effect in context.target.status_effects:
            self._apply_effect(effect, context)
    
    def handle_error(self, context, error):
        context.log_error(f"Status effect error: {error}")
        # Continue processing (non-critical)
```

### Pipeline Customization

```python
# Create custom pipeline
from wuxia_battle_simulator import ProcessorPipeline

pipeline = ProcessorPipeline()
pipeline.add_processor(ATBProcessor())
pipeline.add_processor(AIDecisionProcessor())
pipeline.add_processor(StatusEffectProcessor())  # Custom processor
pipeline.add_processor(DamageCalculationProcessor())
pipeline.add_processor(StateUpdateProcessor())

engine = BattleEngine(game_state, ai, clock, rng, pipeline=pipeline)
```

### Error Handling

```python
# Processors can handle errors gracefully
engine.step()
if engine.context.has_errors():
    for error in engine.context.errors:
        print(f"Battle error: {error}")
```

## Performance Considerations

- Processors are lightweight and fast
- Context passing is efficient (single object)
- Pipeline overhead is minimal
- Memory usage is optimized through context reuse

## Future Extensions

The modular architecture enables easy addition of:
- Status effects and conditions
- Environmental factors
- Team-based combat
- Turn-based alternatives to ATB
- Complex skill interactions
- Battle replay systems
- AI learning and adaptation

## Conclusion

The new modular architecture provides a solid foundation for current and future battle simulation needs while maintaining compatibility with existing code. The processor-based design makes the system more maintainable, testable, and extensible.