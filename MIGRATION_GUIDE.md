# Migration Guide: BattleSimulator to BattleEngine

This guide helps you migrate from the legacy `BattleSimulator` to the new modular `BattleEngine` architecture.

## Quick Migration Checklist

- [ ] Identify current `BattleSimulator` usage
- [ ] Choose migration strategy (Direct, Adapter, or Custom)
- [ ] Update imports
- [ ] Test functionality
- [ ] Optimize with new features (optional)

## Migration Strategies

### Strategy 1: Drop-in Replacement (Recommended for Quick Migration)

Use `BattleEngineAdapter` for immediate compatibility:

```python
# Before
from wuxia_battle_simulator import BattleSimulator
simulator = BattleSimulator(game_state, ai, clock, rng)

# After (minimal change)
from wuxia_battle_simulator import BattleEngineAdapter
simulator = BattleEngineAdapter(game_state, ai, clock, rng)

# All existing methods work unchanged:
while not simulator.is_battle_over():
    simulator.step()
events = simulator.get_events()
```

**Pros:**
- Zero code changes required
- Immediate benefits of new architecture
- Gradual migration path

**Cons:**
- Doesn't leverage new features
- Slight adapter overhead

### Strategy 2: Direct Migration (Recommended for New Development)

Migrate directly to `BattleEngine`:

```python
# Before
from wuxia_battle_simulator import BattleSimulator
simulator = BattleSimulator(game_state, ai, clock, rng)
while not simulator.is_battle_over():
    simulator.step()
events = simulator.get_events()

# After
from wuxia_battle_simulator import BattleEngine
engine = BattleEngine(game_state, ai, clock, rng)
while not engine.is_battle_over():
    engine.step()
events = engine.get_events()
```

**Pros:**
- Full access to new features
- Better performance
- Cleaner architecture

**Cons:**
- Requires code review
- Method names might differ slightly

### Strategy 3: Custom Processors (For Advanced Users)

Extend the engine with custom battle logic:

```python
from wuxia_battle_simulator import BattleEngine, StepProcessor

class CustomMechanicProcessor(StepProcessor):
    def can_process(self, context):
        return True  # Always process
    
    def process(self, context):
        # Your custom battle logic here
        pass

engine = BattleEngine(game_state, ai, clock, rng)
engine.add_processor(CustomMechanicProcessor(), position=6)
```

## Common Migration Patterns

### Pattern 1: Basic Battle Loop

```python
# Old pattern
simulator = BattleSimulator(game_state, ai, clock, rng)
while not simulator.is_battle_over():
    simulator.step()
result = simulator.get_battle_result()

# New pattern (Option A: Adapter)
simulator = BattleEngineAdapter(game_state, ai, clock, rng)
while not simulator.is_battle_over():
    simulator.step()
result = simulator.get_battle_result()

# New pattern (Option B: Direct)
engine = BattleEngine(game_state, ai, clock, rng)
while not engine.is_battle_over():
    engine.step()
result = engine.get_battle_result()
```

### Pattern 2: Event Processing

```python
# Old pattern
events = simulator.get_events()
for event in events:
    process_event(event)

# New pattern (same for both adapter and direct)
events = engine.get_events()  # or simulator.get_events() with adapter
for event in events:
    process_event(event)  # Events have same structure
```

### Pattern 3: Battle Configuration

```python
# Old pattern
simulator = BattleSimulator(
    game_state=my_game_state,
    ai=my_ai,
    clock=my_clock,
    rng=my_rng
)

# New pattern (identical)
engine = BattleEngine(
    game_state=my_game_state,
    ai=my_ai,
    clock=my_clock,
    rng=my_rng
)
```

## API Compatibility Matrix

| BattleSimulator Method | BattleEngine Method | BattleEngineAdapter | Notes |
|------------------------|---------------------|---------------------|-------|
| `step()` | `step()` | `step()` | ✅ Identical |
| `is_battle_over()` | `is_battle_over()` | `is_battle_over()` | ✅ Identical |
| `get_events()` | `get_events()` | `get_events()` | ✅ Identical |
| `get_battle_result()` | `get_battle_result()` | `get_battle_result()` | ✅ Identical |
| `run_to_completion()` | `run_to_completion()` | `run_to_completion()` | ✅ Identical |
| `create_actor_views()` | `create_actor_views()` | `create_actor_views()` | ✅ Identical |
| `map_event_for_narration()` | `map_event_for_narration()` | `map_event_for_narration()` | ✅ Identical |

## Step-by-Step Migration Process

### Step 1: Backup and Test

```bash
# Create a backup of your current code
git commit -am "Backup before BattleEngine migration"

# Run existing tests to establish baseline
python -m pytest tests/
```

### Step 2: Update Imports

```python
# Replace this:
from wuxia_battle_simulator import BattleSimulator

# With this (for adapter approach):
from wuxia_battle_simulator import BattleEngineAdapter as BattleSimulator

# Or this (for direct approach):
from wuxia_battle_simulator import BattleEngine
```

### Step 3: Update Instantiation

```python
# Adapter approach (minimal change)
simulator = BattleSimulator(game_state, ai, clock, rng)  # Works unchanged

# Direct approach
engine = BattleEngine(game_state, ai, clock, rng)
```

### Step 4: Test and Validate

```python
# Use the validation helper
from wuxia_battle_simulator.engine.migration import validate_migration

# Run a test battle with both engines
old_events = old_simulator.run_to_completion()
new_events = new_engine.run_to_completion()

# Validate results are equivalent
is_valid = validate_migration(old_events, new_events)
print(f"Migration validation: {'✅ PASSED' if is_valid else '❌ FAILED'}")
```

### Step 5: Optimize (Optional)

Once migration is complete, consider leveraging new features:

```python
# Add custom processors
engine.add_processor(MyCustomProcessor())

# Remove unnecessary processors
engine.remove_processor('MovementSkillProcessor')

# Access detailed context information
context = engine.get_context()
print(f"Current actor: {context.actor.name}")
print(f"Processing errors: {context.errors}")
```

## Troubleshooting Common Issues

### Issue 1: Import Errors

```python
# Problem
from wuxia_battle_simulator.battle_simulator import BattleSimulator  # Old path

# Solution
from wuxia_battle_simulator import BattleSimulator  # Use package-level import
# or
from wuxia_battle_simulator import BattleEngineAdapter as BattleSimulator
```

### Issue 2: Different Battle Results

```python
# Use the migration validation tool
from wuxia_battle_simulator.engine.migration import validate_migration

# Compare results
if not validate_migration(old_events, new_events):
    print("Results differ - check RNG seed and configuration")
```

### Issue 3: Performance Differences

```python
# The new engine should be faster, but if you notice slowdowns:
# 1. Ensure you're using BattleEngine directly (not adapter)
# 2. Check for custom processors that might be inefficient
# 3. Profile your code to identify bottlenecks

import cProfile
cProfile.run('engine.run_to_completion()')
```

## Testing Your Migration

### Unit Tests

```python
import unittest
from wuxia_battle_simulator import BattleEngine, BattleEngineAdapter

class TestMigration(unittest.TestCase):
    def setUp(self):
        # Set up test data
        self.game_state = create_test_game_state()
        self.ai = SimpleAI()
        self.clock = ATBClock()
        self.rng = RNG(seed=42)
    
    def test_adapter_compatibility(self):
        """Test that adapter produces same results as original."""
        adapter = BattleEngineAdapter(self.game_state, self.ai, self.clock, self.rng)
        
        # Run battle
        events = adapter.run_to_completion()
        
        # Verify expected behavior
        self.assertGreater(len(events), 0)
        self.assertTrue(adapter.is_battle_over())
    
    def test_direct_engine(self):
        """Test direct BattleEngine usage."""
        engine = BattleEngine(self.game_state, self.ai, self.clock, self.rng)
        
        # Run battle
        events = engine.run_to_completion()
        
        # Verify expected behavior
        self.assertGreater(len(events), 0)
        self.assertTrue(engine.is_battle_over())
```

### Integration Tests

```python
def test_full_battle_migration():
    """Test complete battle with both old and new systems."""
    # Create identical initial conditions
    game_state1 = create_test_game_state()
    game_state2 = create_test_game_state()  # Identical copy
    
    # Run with adapter
    adapter = BattleEngineAdapter(game_state1, SimpleAI(), ATBClock(), RNG(42))
    adapter_events = adapter.run_to_completion()
    
    # Run with direct engine
    engine = BattleEngine(game_state2, SimpleAI(), ATBClock(), RNG(42))
    engine_events = engine.run_to_completion()
    
    # Results should be identical
    assert len(adapter_events) == len(engine_events)
    assert adapter.get_battle_result() == engine.get_battle_result()
```

## Performance Expectations

- **BattleEngineAdapter**: ~5-10% overhead compared to original
- **BattleEngine**: ~10-20% faster than original
- **Custom Processors**: Performance depends on implementation

## Getting Help

If you encounter issues during migration:

1. Check this guide for common patterns
2. Review the `ARCHITECTURE.md` for detailed component information
3. Look at `example_battle_engine_usage.py` for working examples
4. Use the migration validation tools
5. Run the test suite to verify functionality

## Migration Timeline Recommendation

- **Week 1**: Test with `BattleEngineAdapter`
- **Week 2**: Migrate to direct `BattleEngine` usage
- **Week 3**: Add custom processors if needed
- **Week 4**: Performance optimization and cleanup

The modular architecture provides a solid foundation for future enhancements while maintaining full backward compatibility.