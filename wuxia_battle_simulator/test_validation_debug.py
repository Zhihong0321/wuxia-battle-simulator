#!/usr/bin/env python3
import sys
import traceback
try:
    from wuxia_battle_simulator.validation.validator import Validator
    from wuxia_battle_simulator.utils.data_loader import DataManager
    print("Imports successful")
    
    v = Validator('schemas')
    print("Validator created")
    
    v.load_schemas()
    print("Schemas loaded")
    
    dm = DataManager(v)
    print("DataManager created")
    
    skills = dm.load_skills('data/skills.json')
    print(f"Skills loaded successfully: {len(skills._skills)} skills")
    
except Exception as e:
    print(f"Error: {e}")
    print(f"Error type: {type(e).__name__}")
    traceback.print_exc()
    sys.exit(1)