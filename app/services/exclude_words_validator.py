import re
from typing import Tuple, Dict

class ExcludeWordsValidator:
    def __init__(self, exclude_words_csv: str):
        """
        Парсит строку (через запятую) в set слов, нормализуя: lowercase, strip, убираем пустые.
        """
        self.words = set()
        if not exclude_words_csv:
            return
            
        for w in exclude_words_csv.split(','):
            cleaned = w.strip().lower()
            if cleaned:
                self.words.add(cleaned)
                
    def validate(self, text: str) -> Dict:
        """
        Проверяет text на наличие запрещённых слов.
        Поиск — case-insensitive, по whole-word boundaries (regex \b).
        """
        if not self.words or not text:
            return {"passed": True, "found_words": {}, "total_violations": 0}
            
        found_words = {}
        total_violations = 0
        
        text_lower = text.lower()
        
        for word in self.words:
            # Escape regex special chars just in case the word has any
            escaped_word = re.escape(word)
            # Use \b for word boundaries. Note: \b is sensitive to non-ascii words sometimes, 
            # but usually fine. For advanced unicode regex, using `(?u)\b` or similar might be needed.
            pattern = re.compile(rf'\b{escaped_word}\b', re.IGNORECASE)
            matches = pattern.findall(text)
            
            if matches:
                count = len(matches)
                found_words[word] = count
                total_violations += count
                
        return {
            "passed": total_violations == 0,
            "found_words": found_words,
            "total_violations": total_violations
        }
        
    def remove_violations(self, text: str) -> Tuple[str, Dict]:
        """
        Заменяет найденные запрещённые слова на пустую строку.
        Возвращает (очищенный_текст, report).
        """
        report = self.validate(text)
        if report["passed"]:
            return text, report
            
        cleaned_text = text
        for word in report["found_words"].keys():
            escaped_word = re.escape(word)
            pattern = re.compile(rf'\b{escaped_word}\b', re.IGNORECASE)
            # Replace with empty string (can leave double spaces, but it's a fallback)
            cleaned_text = pattern.sub('', cleaned_text)
            
        # Optional space cleanup
        cleaned_text = re.sub(r' {2,}', ' ', cleaned_text)
            
        return cleaned_text, report
