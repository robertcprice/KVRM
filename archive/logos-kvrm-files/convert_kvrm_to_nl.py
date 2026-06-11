#!/usr/bin/env python3
"""
Convert KVRM training data to Natural Language format.

KVRM Format:
  User: "What does John 3:16 say?"
  Assistant: {"key": "nt:jhn:3:16", "type": "direct"}

NL Format:
  User: "What does John 3:16 say?"
  Assistant: "John 3:16 - For God so loved the world, that he gave his only begotten Son..."

This script enables the KVRM vs NL comparison experiment.
"""

import json
import sqlite3
import re
from pathlib import Path
from typing import Optional, Dict
from tqdm import tqdm

# Book abbreviation mapping (KVRM key -> database book name)
BOOK_MAP = {
    # Old Testament
    'gen': 'Genesis', 'exod': 'Exodus', 'lev': 'Leviticus',
    'num': 'Numbers', 'deut': 'Deuteronomy', 'josh': 'Joshua',
    'judg': 'Judges', 'ruth': 'Ruth',
    '1sam': 'I Samuel', '2sam': 'II Samuel',
    '1kgs': 'I Kings', '2kgs': 'II Kings',
    '1chr': 'I Chronicles', '2chr': 'II Chronicles',
    'ezra': 'Ezra', 'neh': 'Nehemiah', 'esth': 'Esther',
    'job': 'Job', 'ps': 'Psalms', 'prov': 'Proverbs',
    'eccl': 'Ecclesiastes', 'song': 'Song of Solomon',
    'isa': 'Isaiah', 'jer': 'Jeremiah', 'lam': 'Lamentations',
    'ezek': 'Ezekiel', 'dan': 'Daniel',
    'hos': 'Hosea', 'joel': 'Joel', 'amos': 'Amos',
    'obad': 'Obadiah', 'jonah': 'Jonah', 'mic': 'Micah',
    'nah': 'Nahum', 'hab': 'Habakkuk', 'zeph': 'Zephaniah',
    'hag': 'Haggai', 'zech': 'Zechariah', 'mal': 'Malachi',
    # New Testament
    'matt': 'Matthew', 'mark': 'Mark', 'luke': 'Luke',
    'jhn': 'John', 'john': 'John', 'acts': 'Acts',
    'rom': 'Romans', '1cor': 'I Corinthians', '2cor': 'II Corinthians',
    'gal': 'Galatians', 'eph': 'Ephesians', 'php': 'Philippians', 'phil': 'Philippians',
    'col': 'Colossians', '1thess': 'I Thessalonians', '2thess': 'II Thessalonians',
    '1tim': 'I Timothy', '2tim': 'II Timothy', 'titus': 'Titus',
    'phlm': 'Philemon', 'heb': 'Hebrews', 'jas': 'James',
    '1pet': 'I Peter', '2pet': 'II Peter',
    '1jn': 'I John', '2jn': 'II John', '3jn': 'III John',
    'jude': 'Jude', 'rev': 'Revelation of John',
}

# Friendly book names for output
FRIENDLY_NAMES = {
    'I Samuel': '1 Samuel', 'II Samuel': '2 Samuel',
    'I Kings': '1 Kings', 'II Kings': '2 Kings',
    'I Chronicles': '1 Chronicles', 'II Chronicles': '2 Chronicles',
    'I Corinthians': '1 Corinthians', 'II Corinthians': '2 Corinthians',
    'I Thessalonians': '1 Thessalonians', 'II Thessalonians': '2 Thessalonians',
    'I Timothy': '1 Timothy', 'II Timothy': '2 Timothy',
    'I Peter': '1 Peter', 'II Peter': '2 Peter',
    'I John': '1 John', 'II John': '2 John', 'III John': '3 John',
    'Revelation of John': 'Revelation',
}


class BibleDatabase:
    """Interface to the KJVA Bible database."""

    def __init__(self, db_path: str = "KJVA.db"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._load_books()

    def _load_books(self):
        """Load book name to ID mapping."""
        self.cursor.execute("SELECT id, name FROM KJVA_books")
        self.book_ids = {name: id for id, name in self.cursor.fetchall()}

    def get_verse(self, book: str, chapter: int, verse: int) -> Optional[str]:
        """Get verse text from database."""
        book_id = self.book_ids.get(book)
        if not book_id:
            return None

        self.cursor.execute(
            "SELECT text FROM KJVA_verses WHERE book_id = ? AND chapter = ? AND verse = ?",
            (book_id, chapter, verse)
        )
        result = self.cursor.fetchone()
        return result[0] if result else None

    def close(self):
        self.conn.close()


def parse_kvrm_key(key: str) -> Optional[Dict]:
    """
    Parse KVRM key into components.

    Example: "nt:jhn:3:16" -> {"testament": "nt", "book": "jhn", "chapter": 3, "verse": 16}
    """
    parts = key.split(':')
    if len(parts) != 4:
        return None

    try:
        return {
            'testament': parts[0],
            'book': parts[1],
            'chapter': int(parts[2]),
            'verse': int(parts[3])
        }
    except ValueError:
        return None


def kvrm_to_nl_response(kvrm_response: str, db: BibleDatabase) -> Optional[str]:
    """
    Convert KVRM JSON response to natural language response.

    KVRM: {"key": "nt:jhn:3:16", "type": "direct"}
    NL: "John 3:16 - For God so loved the world..."
    """
    try:
        data = json.loads(kvrm_response)
        key = data.get('key', '')

        if not key or key.upper() == 'UNKNOWN':
            return "I don't have a specific verse for that question."

        parsed = parse_kvrm_key(key)
        if not parsed:
            return None

        # Get database book name
        book_abbr = parsed['book'].lower()
        db_book = BOOK_MAP.get(book_abbr)
        if not db_book:
            return None

        # Get verse text
        verse_text = db.get_verse(db_book, parsed['chapter'], parsed['verse'])
        if not verse_text:
            return None

        # Format friendly book name
        friendly_book = FRIENDLY_NAMES.get(db_book, db_book)

        # Create NL response
        reference = f"{friendly_book} {parsed['chapter']}:{parsed['verse']}"

        # Truncate long verses
        if len(verse_text) > 200:
            verse_text = verse_text[:200] + "..."

        return f'{reference} - "{verse_text}"'

    except (json.JSONDecodeError, KeyError):
        return None


def convert_dataset(input_path: str, output_path: str, db: BibleDatabase) -> Dict:
    """Convert KVRM dataset to NL format."""

    stats = {
        'total': 0,
        'converted': 0,
        'skipped': 0,
        'no_verse': 0,
        'parse_error': 0
    }

    output_lines = []

    with open(input_path, 'r') as f:
        lines = f.readlines()

    for line in tqdm(lines, desc="Converting"):
        stats['total'] += 1

        try:
            data = json.loads(line)
            messages = data.get('messages', [])

            if len(messages) < 2:
                stats['skipped'] += 1
                continue

            user_msg = messages[0]['content']
            kvrm_response = messages[1]['content']

            # Convert to NL
            nl_response = kvrm_to_nl_response(kvrm_response, db)

            if nl_response:
                # Create NL training example
                nl_data = {
                    'messages': [
                        {'role': 'user', 'content': user_msg},
                        {'role': 'assistant', 'content': nl_response}
                    ]
                }
                output_lines.append(json.dumps(nl_data, ensure_ascii=False))
                stats['converted'] += 1
            else:
                stats['no_verse'] += 1

        except Exception as e:
            stats['parse_error'] += 1

    # Write output
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write('\n'.join(output_lines))

    return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Convert KVRM to NL training data")
    parser.add_argument("--input", "-i", type=str,
                       default="data/tier1/train.jsonl",
                       help="Input KVRM training file")
    parser.add_argument("--output", "-o", type=str,
                       default="data/natural_language/train.jsonl",
                       help="Output NL training file")
    parser.add_argument("--db", type=str,
                       default="KJVA.db",
                       help="Bible database path")
    parser.add_argument("--valid-input", type=str,
                       default="data/tier1/valid.jsonl",
                       help="Input validation file")
    parser.add_argument("--valid-output", type=str,
                       default="data/natural_language/valid.jsonl",
                       help="Output validation file")

    args = parser.parse_args()

    print("=" * 60)
    print("KVRM to Natural Language Dataset Converter")
    print("=" * 60)

    # Connect to database
    print(f"\nConnecting to database: {args.db}")
    db = BibleDatabase(args.db)

    # Convert training data
    print(f"\nConverting training data: {args.input}")
    train_stats = convert_dataset(args.input, args.output, db)

    print(f"\nTraining conversion results:")
    print(f"  Total examples: {train_stats['total']:,}")
    print(f"  Converted: {train_stats['converted']:,} ({100*train_stats['converted']/train_stats['total']:.1f}%)")
    print(f"  No verse found: {train_stats['no_verse']:,}")
    print(f"  Parse errors: {train_stats['parse_error']:,}")
    print(f"  Skipped: {train_stats['skipped']:,}")
    print(f"  Output: {args.output}")

    # Convert validation data if exists
    if Path(args.valid_input).exists():
        print(f"\nConverting validation data: {args.valid_input}")
        valid_stats = convert_dataset(args.valid_input, args.valid_output, db)

        print(f"\nValidation conversion results:")
        print(f"  Total examples: {valid_stats['total']:,}")
        print(f"  Converted: {valid_stats['converted']:,}")
        print(f"  Output: {args.valid_output}")

    db.close()

    print("\n" + "=" * 60)
    print("Conversion complete!")
    print("=" * 60)

    # Show sample
    print("\nSample NL training example:")
    with open(args.output, 'r') as f:
        sample = json.loads(f.readline())
        print(f"  User: {sample['messages'][0]['content'][:80]}...")
        print(f"  Assistant: {sample['messages'][1]['content'][:100]}...")


if __name__ == "__main__":
    main()
