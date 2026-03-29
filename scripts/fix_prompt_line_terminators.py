"""Fix unusual Unicode line terminators (U+2028, U+2029) in all prompts."""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.prompt import Prompt


def fix():
    db = SessionLocal()
    try:
        prompts = db.query(Prompt).all()
        fixed = 0
        for p in prompts:
            changed = False
            for field in ("system_prompt", "user_prompt"):
                val = getattr(p, field) or ""
                clean = (
                    val.replace("\u2028", "\n")
                    .replace("\u2029", "\n\n")
                    .replace("\u00a0", " ")
                    .replace("\ufeff", "")
                )
                if clean != val:
                    setattr(p, field, clean)
                    changed = True
                    print(f"  Fixed {field} in {p.agent_name} v{p.version}")
            if changed:
                fixed += 1
        db.commit()
        print(f"Done. Fixed {fixed} prompts.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    fix()
