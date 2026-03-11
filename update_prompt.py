import sys
import os
sys.path.append(os.getcwd())
try:
    from app.database import SessionLocal
    from app.models.prompt import Prompt

    db = SessionLocal()
    prompt = db.query(Prompt).filter(Prompt.agent_name == 'ai_structure_analysis').first()

    if not prompt:
        print('Prompt not found')
        sys.exit(0)

    print('--- CURRENT SYSTEM PROMPT ---')
    print(prompt.system_prompt)

    # Check if JSON instruction is present
    if '{"intent":' not in prompt.system_prompt:
        print('\n--- UPDATING PROMPT ---')
        addition = '\n\nIMPORTANT: You must reply ONLY with a valid JSON object without any markdown wrapping (no ```json). The JSON must exactly follow this structure:\n{\n  "intent": "...",\n  "Taxonomy": "...",\n  "Attention": "...",\n  "structura": "..."\n}'
        prompt.system_prompt += addition
        db.commit()
        print('Prompt updated.')
    else:
        print('\nPrompt already contains JSON instructions.')

except Exception as e:
    print(f"Error: {e}")
