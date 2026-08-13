import re
import random
from typing import Dict
from faker import Faker

class StatefulMapper:
    """
    A stateful mapper that generates consistent fake replacements for PII entities.
    It stores the mapping of original_text -> fake_text to ensure that if the same
    real entity appears multiple times, it is replaced with the exact same fake entity.
    """

    def __init__(self, seed: int = None):
        """
        Initializes the StatefulMapper.
        
        Args:
            seed: An optional integer seed for the Faker instance to ensure 
                  reproducible replacements across runs.
        """
        self.fake = Faker()
        if seed is not None:
            Faker.seed(seed)
            random.seed(seed)
            
        # Dictionary structure: { "clean_key": "fake_text" }
        self.mappings: Dict[str, str] = {}

    def get_replacement(self, entity_type: str, original_text: str) -> str:
        """
        Retrieves or generates a fake replacement for the given original text.
        
        Args:
            entity_type: The type of the PII entity (e.g., "NAME", "EMAIL").
            original_text: The actual PII text found in the document.
            
        Returns:
            The fake replacement string.
        """
        # Strip honorifics and titles for a consistent base name
        clean_text = re.sub(r'\b(mr\.|mrs\.|dr\.|shri|smt\.?)\b', '', original_text, flags=re.IGNORECASE)
        # Normalize keys as requested: strip commas, punctuation, spaces
        lookup_key = re.sub(r'[^a-z0-9]', '', clean_text.lower())

        # Check if we already have a mapping for this entity regardless of type
        if lookup_key in self.mappings:
            return self.mappings[lookup_key]

        # Generate a new fake value based on the entity type
        fake_value = self._generate_fake(entity_type, original_text)
        
        # Store for future lookups
        self.mappings[lookup_key] = fake_value
        
        return fake_value

    def _generate_fake(self, entity_type: str, original_text: str = "") -> str:
        """
        Internal method to generate a fake string for a specific entity type.
        """
        if entity_type == "NAME":
            return self.fake.name()
        elif entity_type == "COMPANY":
            return self.fake.company()
        elif entity_type == "ADDRESS":
            # Generate short, concise street and city strings
            return self.fake.street_address() + ", " + self.fake.city()
        elif entity_type == "EMAIL":
            return self.fake.safe_email()
        elif entity_type in ("PHONE", "PHONE_KEYWORD"):
            # Generating a standard phone format
            return self.fake.numerify(text="###-###-####")
        elif entity_type == "SSN":
            return self.fake.ssn()
        elif entity_type == "IP_ADDRESS":
            return self.fake.ipv4()
        elif entity_type == "CREDIT_CARD":
            # Generating a generic 16 digit number to represent CC
            return self.fake.credit_card_number(card_type=None)
        elif entity_type == "DOB":
            # Generate a date of birth (MM/DD/YYYY)
            date_obj = self.fake.date_of_birth(minimum_age=18, maximum_age=90)
            return date_obj.strftime("%m/%d/%Y")
        elif entity_type == "URL":
            # Strict generation as per request
            return "www." + self.fake.domain_name()
        
        return "[REDACTED]"
