"""
Фикс: убедиться что все активные промпты имеют корректные значения 
temperature/frequency_penalty/presence_penalty/top_p.
Заменяет NULL на дефолты.
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.prompt import Prompt

def fix():
    db = SessionLocal()
    try:
        prompts = db.query(Prompt).filter(Prompt.is_active == True).all()
        for p in prompts:
            changed = False
            if p.temperature is None:
                p.temperature = 0.7
                changed = True
            if p.frequency_penalty is None:
                p.frequency_penalty = 0.0
                changed = True
            if p.presence_penalty is None:
                p.presence_penalty = 0.0
                changed = True
            if p.top_p is None:
                p.top_p = 1.0
                changed = True
            
            # Special default overwrites mentioned in the instructions for generation agents
            if p.agent_name in ["primary_generation", "improver"]:
                if p.temperature == 0.7:  # If it was accidentally set to 0.7
                    p.temperature = 0.8
                    changed = True

            if changed:
                print(f"Fixed: {p.agent_name}")
        db.commit()
        print("Done fixing defaults.")
    except Exception as e:
        db.rollback()
        print("Error:", e)
    finally:
        db.close()

if __name__ == "__main__":
    fix()
