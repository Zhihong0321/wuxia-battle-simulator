# Battle Processor Pipeline Architecture

This document describes the modular processor-based architecture that replaces the monolithic BattleSimulator with a flexible, extensible pipeline system.

## Overview

The new battle system uses a processor pipeline pattern where each battle step is handled by an independent processor. This design provides:

- **Modularity**: Each battle phase is isolated and can be modified independently
- **Extensibility**: New battle mechanics can be added by creating new processors
- **Testability**: Individual processors can be tested in isolation
- **Maintainability**: Clear separation of concerns and well-defined interfaces
- **Configurability**: Battle flow can be modified at runtime through processor registry

## Core Components

### BattleContext

Carries all battle data through the processing pipeline:

```python
@dataclass
class BattleContext:
    # Core battle state
    game_state: GameState
    current_actor_id: Optional[str]
    target_id: Optional[str]
    
    # Action data
    selected_skill: Optional[str]
    selected_tier: Optional[int]
    
    # Processing results
    hit_result: Optional[HitResult]
    damage_result: Optional[DamageResult]
    
    # Events generated during processing
    events: List[BattleEvent]
    
    # Processing metadata
    processing_log: List[str]
    should_continue: bool = True
    error_occurred: bool = False
```

### StepProcessor Interface

Common interface for all battle processing steps:

```python
class StepProcessor(ABC):
    @abstractmethod
    def process(self, context: BattleContext) -> None:
        """Process the battle context and modify it as needed."""
        pass
    
    @abstractmethod
    def can_process(self, context: BattleContext) -> bool:
        """Check if this processor should run given the current context."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Processor name for logging and debugging."""
        pass
```

### ProcessorPipeline

Executes processors in sequence with error handling:

```python
class ProcessorPipeline:
    def __init__(self, processors: List[StepProcessor]):
        self.processors = processors
    
    def execute(self, context: BattleContext) -> BattleContext:
        """Execute all processors in sequence."""
        for processor in self.processors:
            if not context.should_continue:
                break
            
            if processor.can_process(context):
                try:
                    processor.process(context)
                    context.processing_log.append(f"Executed: {processor.name}")
                except Exception as e:
                    context.error_occurred = True
                    context.processing_log.append(f"Error in {processor.name}: {e}")
                    # Handle error based on processor criticality
        
        return context
```

### ProcessorRegistry

Manages processor configuration and allows runtime modification:

```python
class ProcessorRegistry:
    def __init__(self):
        self.processors: List[StepProcessor] = []
    
    def register(self, processor: StepProcessor) -> None:
        """Add a processor to the pipeline."""
        self.processors.append(processor)
    
    def unregister(self, processor_name: str) -> None:
        """Remove a processor from the pipeline."""
        self.processors = [p for p in self.processors if p.name != processor_name]
    
    def get_pipeline(self) -> ProcessorPipeline:
        """Create a pipeline with current processors."""
        return ProcessorPipeline(self.processors.copy())
```

## Core Processors

### 1. ATBProcessor

**Purpose**: Manages ATB timing and selects the next actor to act.

**Responsibilities**:
- Advance ATB clock
- Select next actor based on time_units
- Handle turn start logic

**Implementation Notes**:
- Only processes when no current actor is set
- Updates context.current_actor_id
- Decrements cooldowns for the acting actor

### 2. AIDecisionProcessor

**Purpose**: Handles AI decision making for action selection.

**Responsibilities**:
- Query AI policy for action selection
- Validate selected action
- Handle no-action scenarios

**Implementation Notes**:
- Only processes when current_actor_id is set but no skill selected
- Updates context.selected_skill, context.target_id, context.selected_tier
- May set should_continue=False for no-op turns

### 3. ResourceValidationProcessor

**Purpose**: Validates qi costs and cooldown requirements.

**Responsibilities**:
- Check qi availability
- Verify cooldown status
- Handle insufficient resources

**Implementation Notes**:
- Only processes when action is selected
- May modify action or set error state
- Critical processor - errors should abort the turn

### 4. MovementSkillProcessor

**Purpose**: Handles target's movement and dodge skills.

**Responsibilities**:
- Check target's movement skills
- Calculate miss chances
- Handle partial misses
- Generate dodge events

**Implementation Notes**:
- Only processes when target has movement skills
- Updates context.hit_result with dodge information
- Generates independent dodge events

### 5. DefenseSkillProcessor

**Purpose**: Handles target's defense skills and counter-attacks.

**Responsibilities**:
- Check target's defense skills
- Calculate damage reduction
- Handle counter-attack mechanics
- Generate defense events

**Implementation Notes**:
- Only processes when target has defense skills
- Updates context.damage_result with defense modifications
- May generate counter-attack events

### 6. DamageCalculationProcessor

**Purpose**: Computes final damage with all modifiers.

**Responsibilities**:
- Calculate base damage
- Apply hit/miss logic
- Handle critical hits
- Determine damage buckets

**Implementation Notes**:
- Processes for all attack actions
- Uses RNG for hit/crit calculations
- Updates context.damage_result with final values

### 7. StateUpdateProcessor

**Purpose**: Applies all state changes to the game.

**Responsibilities**:
- Update target HP
- Consume actor qi
- Set skill cooldowns
- Update any other game state

**Implementation Notes**:
- Critical processor - must execute successfully
- Updates game_state directly
- Validates state consistency

### 8. EventGenerationProcessor

**Purpose**: Creates BattleEvent objects for narration.

**Responsibilities**:
- Generate attack result events
- Create summary events
- Format events for narration

**Implementation Notes**:
- Always processes (even for no-op turns)
- Adds events to context.events
- Ensures events have all required fields

## Implementation Guidelines

### Adding New Processors

1. **Create Processor Class**:
   ```python
   class MyNewProcessor(StepProcessor):
       def process(self, context: BattleContext) -> None:
           # Implementation here
           pass
       
       def can_process(self, context: BattleContext) -> bool:
           # Conditional logic here
           return True
       
       @property
       def name(self) -> str:
           return "MyNewProcessor"
   ```

2. **Register with Registry**:
   ```python
   registry.register(MyNewProcessor())
   ```

3. **Position in Pipeline**:
   - Consider dependencies on other processors
   - Insert at appropriate position in the sequence

### Modifying Battle Flow

1. **Disable Processor**:
   ```python
   registry.unregister("ProcessorName")
   ```

2. **Conditional Processing**:
   ```python
   def can_process(self, context: BattleContext) -> bool:
       return context.some_condition and super().can_process(context)
   ```

3. **Runtime Configuration**:
   ```python
   # Enable/disable features based on game mode
   if game_mode == "simple":
       registry.unregister("DefenseSkillProcessor")
   ```

### Error Handling

1. **Critical Processors**: Errors should abort the turn
   - ATBProcessor
   - ResourceValidationProcessor
   - StateUpdateProcessor

2. **Optional Processors**: Errors should be logged but not abort
   - MovementSkillProcessor
   - DefenseSkillProcessor

3. **Error Recovery**:
   ```python
   try:
       processor.process(context)
   except CriticalError:
       context.should_continue = False
       context.error_occurred = True
   except OptionalError as e:
       context.processing_log.append(f"Warning: {e}")
   ```

### Debugging and Testing

1. **Processor Isolation**:
   ```python
   # Test individual processor
   context = BattleContext(...)
   processor = MovementSkillProcessor()
   processor.process(context)
   assert context.hit_result.dodged
   ```

2. **Pipeline Testing**:
   ```python
   # Test processor sequence
   pipeline = ProcessorPipeline([proc1, proc2, proc3])
   result_context = pipeline.execute(initial_context)
   ```

3. **Logging**:
   ```python
   # Enable detailed logging
   context.processing_log  # Contains step-by-step execution log
   ```

## Migration from BattleSimulator

The new architecture maintains the same external interface:

- `step()` method returns `List[BattleEvent]`
- `run_to_completion()` behavior unchanged
- `map_event_for_narration()` interface preserved

Internal changes:
- Monolithic step logic replaced with processor pipeline
- State management centralized in BattleContext
- Error handling improved with processor-level granularity
- Debugging capabilities enhanced with processing logs

## Performance Considerations

- **Processor Overhead**: Minimal - simple method calls
- **Memory Usage**: BattleContext carries all data but is short-lived
- **Extensibility Cost**: New processors add minimal overhead
- **Debugging Impact**: Processing logs can be disabled in production

## Future Extensions

- **Status Effects**: Add StatusEffectProcessor for buffs/debuffs
- **Area Damage**: Add AreaDamageProcessor for multi-target skills
- **Environmental Effects**: Add EnvironmentProcessor for terrain/weather
- **Combo System**: Add ComboProcessor for skill combinations
- **AI Enhancements**: Add multiple AI processors for different decision types