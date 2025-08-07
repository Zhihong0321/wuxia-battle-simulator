#!/usr/bin/env python3
"""Example usage of the new BattleEngine.

This script demonstrates how to use the new modular BattleEngine
to run battles and customize the processor pipeline.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wuxia_battle_simulator import GameState, Character, CharacterStats, EquippedSkill, SimpleAI, ATBClock
from wuxia_battle_simulator.engine.ai_policy import SkillDB, _SkillTierParams
import random
from wuxia_battle_simulator.engine import BattleEngine
from wuxia_battle_simulator.engine.migration import quick_migrate, BattleEngineAdapter


class SimpleSkillDB(SkillDB):
    """Simple skills database for examples"""
    def __init__(self):
        self._skills = {
            "basic_strike": {
                1: dict(base_damage=15, power_multiplier=1.0, qi_cost=5, cooldown=0, hit_chance=0.8, critical_chance=0.1)
            },
            "fireball": {
                1: dict(base_damage=25, power_multiplier=1.2, qi_cost=10, cooldown=1, hit_chance=0.75, critical_chance=0.15)
            }
        }
    
    def get_tier_params(self, skill_id: str, tier: int) -> _SkillTierParams:
        p = self._skills[skill_id][tier]
        return _SkillTierParams(
            base_damage=p["base_damage"],
            power_multiplier=p["power_multiplier"],
            qi_cost=p["qi_cost"],
            cooldown=p["cooldown"],
            hit_chance=p["hit_chance"],
            critical_chance=p["critical_chance"]
        )
    
    def get_tier_name(self, skill_id: str, tier: int) -> str:
        return f"{skill_id}_tier_{tier}"


def create_warrior(char_id: str, name: str, team: int) -> Character:
    """Create a warrior character"""
    stats = CharacterStats(
        max_hp=120,
        max_qi=40,
        strength=25,
        defense=15,
        agility=10
    )
    
    skills = [
        EquippedSkill(skill_id="sword_strike", tier=2),
        EquippedSkill(skill_id="parry", tier=1),
        EquippedSkill(skill_id="sidestep", tier=1)
    ]
    
    return Character(
        id=char_id,
        name=name,
        faction=f"team_{team}",
        faction_terminology={},
        stats=stats,
        hp=stats.max_hp,
        qi=stats.max_qi,
        skills=skills
    )


def create_mage(char_id: str, name: str, team: int) -> Character:
    """Create a mage character"""
    stats = CharacterStats(
        max_hp=80,
        max_qi=80,
        strength=15,
        defense=8,
        agility=20
    )
    
    skills = [
        EquippedSkill(skill_id="fireball", tier=3),
        EquippedSkill(skill_id="magic_shield", tier=2),
        EquippedSkill(skill_id="teleport", tier=2)
    ]
    
    return Character(
        id=char_id,
        name=name,
        faction=f"team_{team}",
        faction_terminology={},
        stats=stats,
        hp=stats.max_hp,
        qi=stats.max_qi,
        skills=skills
    )


def example_basic_usage():
    """Example 1: Basic BattleEngine usage"""
    print("=" * 50)
    print("Example 1: Basic BattleEngine Usage")
    print("=" * 50)
    
    # Create characters
    warrior = create_warrior("warrior", "Brave Warrior", 1)
    mage = create_mage("mage", "Wise Mage", 2)
    
    # Create game state
    game_state = GameState([warrior, mage])
    
    # Create battle components
    rng = random.Random(42)
    skills_db = SimpleSkillDB()
    ai = SimpleAI(rng=rng, skills_db=skills_db)
    clock = ATBClock()
    
    # Create battle engine
    engine = BattleEngine(game_state, ai, clock, rng)
    
    print(f"Battle setup complete!")
    team1_chars = [c for c in game_state.all_characters() if c.faction == "team_1"]
    team2_chars = [c for c in game_state.all_characters() if c.faction == "team_2"]
    print(f"Team 1: {[c.name for c in team1_chars]}")
    print(f"Team 2: {[c.name for c in team2_chars]}")
    print(f"Processors: {engine.get_pipeline_info()['processor_count']}")
    
    # Run battle step by step
    print("\nRunning battle step by step:")
    for step in range(5):
        if engine.is_battle_finished():
            print("Battle finished!")
            break
        
        print(f"\nStep {step + 1}:")
        events = engine.step()
        
        for event in events:
            print(f"  {event.event_type}: {event.actor} -> {event.target}")
            if event.damage > 0:
                print(f"    Damage: {event.damage} ({event.damage_percent})")
    
    print(f"\nBattle summary:")
    print(f"Total steps: {engine.get_step_count()}")
    print(f"Total events: {len(engine.get_battle_events())}")
    print(f"Battle finished: {engine.is_battle_finished()}")


def example_migration_adapter():
    """Example 2: Using the migration adapter for compatibility"""
    print("\n" + "=" * 50)
    print("Example 2: Migration Adapter Usage")
    print("=" * 50)
    
    # Create characters
    warrior = create_warrior("hero", "Hero", 1)
    mage = create_mage("villain", "Villain", 2)
    
    # Create game state
    game_state = GameState([warrior, mage])
    
    # Create battle components
    rng = random.Random(123)
    skills_db = SimpleSkillDB()
    ai = SimpleAI(rng=rng, skills_db=skills_db)
    clock = ATBClock()
    
    # Use the adapter for compatibility with old code
    simulator = BattleEngineAdapter(game_state, ai, clock, rng)
    
    print("Using BattleEngineAdapter for compatibility...")
    
    # This works exactly like the old BattleSimulator
    actor_views = simulator.create_actor_views()
    print(f"Actor views: {list(actor_views.keys())}")
    
    # Run a few steps
    for i in range(3):
        events = simulator.step()
        print(f"Step {i+1}: {len(events)} events")
        
        if simulator.is_battle_finished():
            break
    
    print(f"Final state: {simulator.step_count} steps, {len(simulator.events)} total events")


def example_processor_customization():
    """Example 3: Customizing the processor pipeline"""
    print("\n" + "=" * 50)
    print("Example 3: Processor Customization")
    print("=" * 50)
    
    # Create a simple battle setup
    warrior = create_warrior("fighter", "Fighter", 1)
    mage = create_mage("wizard", "Wizard", 2)
    game_state = GameState([warrior, mage])
    
    rng = random.Random(999)
    skills_db = SimpleSkillDB()
    ai = SimpleAI(rng=rng, skills_db=skills_db)
    clock = ATBClock()
    
    # Create engine
    engine = BattleEngine(game_state, ai, clock, rng)
    
    # Show initial pipeline
    pipeline_info = engine.get_pipeline_info()
    print("Initial pipeline:")
    for i, proc in enumerate(pipeline_info['processors']):
        print(f"  {i+1}. {proc['name']} (critical: {proc['critical']})")
    
    # Remove a non-critical processor
    print("\nRemoving Defense Skill Processor...")
    removed = engine.remove_processor("Defense Skill Processor")
    print(f"Removal successful: {removed}")
    
    # Show updated pipeline
    new_pipeline_info = engine.get_pipeline_info()
    print(f"\nUpdated pipeline ({new_pipeline_info['processor_count']} processors):")
    for i, proc in enumerate(new_pipeline_info['processors']):
        print(f"  {i+1}. {proc['name']}")
    
    # Run a step with the modified pipeline
    print("\nRunning step with modified pipeline:")
    events = engine.step()
    print(f"Generated {len(events)} events")
    
    # Access individual processors
    atb_processor = engine.get_processor("ATB Processor")
    if atb_processor:
        print(f"\nFound ATB processor: {atb_processor.name}")
        print(f"Critical: {atb_processor.critical}")


def example_complete_battle():
    """Example 4: Running a complete battle"""
    print("\n" + "=" * 50)
    print("Example 4: Complete Battle")
    print("=" * 50)
    
    # Create a more interesting battle with multiple characters
    team1 = [
        create_warrior("warrior1", "Knight", 1),
        create_mage("mage1", "Cleric", 1)
    ]
    
    team2 = [
        create_warrior("warrior2", "Orc", 2),
        create_mage("mage2", "Dark Wizard", 2)
    ]
    
    game_state = GameState(team1 + team2)
    
    rng = random.Random(777)
    skills_db = SimpleSkillDB()
    ai = SimpleAI(rng=rng, skills_db=skills_db)
    clock = ATBClock()
    
    engine = BattleEngine(game_state, ai, clock, rng)
    
    print("Starting complete battle...")
    print(f"Team 1: {[c.name for c in team1]}")
    print(f"Team 2: {[c.name for c in team2]}")
    
    # Run to completion
    all_events = engine.run_to_completion(max_steps=50)
    
    print(f"\nBattle completed!")
    print(f"Total steps: {engine.get_step_count()}")
    print(f"Total events: {len(all_events)}")
    print(f"Battle finished: {engine.is_battle_finished()}")
    
    # Show final character states
    print("\nFinal character states:")
    for char in team1 + team2:
        status = "ALIVE" if char.hp > 0 else "DEFEATED"
        print(f"  {char.name}: {char.hp}/{char.stats.max_hp} HP ({status})")
    
    # Show event summary
    event_types = {}
    for event in all_events:
        event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
    
    print("\nEvent summary:")
    for event_type, count in event_types.items():
        print(f"  {event_type}: {count}")


def main():
    """Run all examples"""
    print("BattleEngine Usage Examples")
    print("This demonstrates the new modular battle engine.")
    
    try:
        example_basic_usage()
        example_migration_adapter()
        example_processor_customization()
        example_complete_battle()
        
        print("\n" + "=" * 50)
        print("🎉 All examples completed successfully!")
        print("The new BattleEngine is working correctly.")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Error running examples: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())