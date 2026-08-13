import re
from typing import List, Dict, Any
from gliner import GLiNER

class HybridDetector:
    """
    A hybrid PII detection engine that uses both regex-based pattern matching
    and GLiNER for zero-shot NLP-based context analysis to find sensitive entities.
    """

    def __init__(self, whitelist: List[str] = None):
        """
        Initializes the HybridDetector.
        
        Args:
            whitelist: A list of exact string matches (e.g., standard financial terms)
                       that should be masked before passing to GLiNER.
        """
        # Sort whitelist by length descending to match longest phrases first
        self.whitelist = sorted(list(set(whitelist) if whitelist else set()), key=len, reverse=True)
        
        # Initialize GLiNER
        self.gliner_model = GLiNER.from_pretrained("urchade/gliner_multi_pii-v1")
        self.gliner_labels = ["person", "organization", "address"]
        self.gliner_threshold = 0.65
        
        # Define regex patterns for structured data types
        self.regex_patterns = {
            "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "PHONE": r'\b(?:\+?91[\s.-]?)?(?:\(?0?\d{2,4}\)?[\s.-]?)?\d{6,8}\b',
            "PHONE_KEYWORD": r'\b(?:Telephone|Tel|Phone|Mobile):?\s*([+\d\s.-]{8,})\b',
            "SSN": r'\b\d{3}-\d{2}-\d{4}\b',
            "IP_ADDRESS": r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
            "CREDIT_CARD": r'\b(?:\d{4}[ -]?){3}\d{4}\b',
            "DOB": r'\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b',
            "URL": r'(?:https?://)?(?:www\.)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            "NAME": r'\b(?:OUR PROMOTERS|PROMOTER SELLING SHAREHOLDER|CONTACT PERSON):?\s*([A-Z][a-z]+\s(?:[A-Z][a-z]+\s)?[A-Z][a-z]+)\b'
        }
        
        # Map GLiNER entity types to our standardized types
        self.gliner_type_mapping = {
            "person": "NAME",
            "organization": "COMPANY",
            "address": "ADDRESS",
        }

    def _mask_whitelist(self, text: str) -> str:
        """
        Masks all whitelisted terms with spaces of the same length.
        This ensures GLiNER ignores them while preserving exact character indices.
        """
        masked_text = text
        for term in self.whitelist:
            # Case-insensitive replacement with spaces
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            masked_text = pattern.sub(lambda m: " " * len(m.group(0)), masked_text)
        return masked_text

    def analyze(self, text: str) -> List[Dict[str, Any]]:
        """
        Analyzes the given text for PII entities.
        """
        if not text or not text.strip():
            return []

        detected_entities = []

        # 0. Fast-path Address Block Detection (Indian PIN Codes)
        if re.search(r'\b\d{6}\b|\b\d{3}\s?\d{3}\b', text):
            detected_entities.append({
                "entity_type": "ADDRESS",
                "start": 0,
                "end": len(text),
                "text": text
            })

        # 1. Regex-based Detection (Structured Data)
        for entity_type, pattern in self.regex_patterns.items():
            for match in re.finditer(pattern, text):
                if match.lastindex and match.lastindex >= 1:
                    detected_text = match.group(1)
                    start = match.start(1)
                    end = match.end(1)
                else:
                    detected_text = match.group()
                    start = match.start()
                    end = match.end()
                    
                detected_entities.append({
                    "entity_type": entity_type,
                    "start": start,
                    "end": end,
                    "text": detected_text
                })

        # 2. Pre-NLP Masking
        masked_text = self._mask_whitelist(text)

        # 3. NLP-based Detection using GLiNER
        try:
            gliner_results = []
            chunk_size = 250
            start_idx = 0
            
            while start_idx < len(masked_text):
                end_idx = min(start_idx + chunk_size, len(masked_text))
                
                # If not at end, break at last space or punctuation
                if end_idx < len(masked_text):
                    last_break = max(
                        masked_text.rfind('. ', start_idx, end_idx),
                        masked_text.rfind('\n', start_idx, end_idx),
                        masked_text.rfind(' ', start_idx, end_idx)
                    )
                    if last_break != -1 and last_break > start_idx:
                        end_idx = last_break + 1
                
                chunk_text = masked_text[start_idx:end_idx]
                
                if chunk_text.strip():
                    chunk_res = self.gliner_model.predict_entities(
                        chunk_text, 
                        self.gliner_labels, 
                        flat_ner=True, 
                        threshold=self.gliner_threshold
                    )
                    for res in chunk_res:
                        res['start'] += start_idx
                        res['end'] += start_idx
                        gliner_results.append(res)
                        
                start_idx = end_idx
            
            for result in gliner_results:
                detected_text = result["text"]
                mapped_type = self.gliner_type_mapping.get(result["label"].lower(), result["label"].upper())
                
                # Check for empty or all-space text due to masking
                if not detected_text.strip():
                    continue
                    
                # Recover original text from original string
                original_detected_text = text[result["start"]:result["end"]]
                
                if self._is_valid_entity(mapped_type, original_detected_text):
                    detected_entities.append({
                        "entity_type": mapped_type,
                        "start": result["start"],
                        "end": result["end"],
                        "text": original_detected_text
                    })
        except Exception as e:
            print(f"Warning: GLiNER analysis failed for text segment. Error: {e}")

        # Split concatenated entities (e.g. lists of names separated by commas/AND)
        detected_entities = self._split_entities(detected_entities)

        # Resolve Overlaps
        resolved_entities = self._resolve_overlaps(detected_entities)
        
        # Sort by start position
        resolved_entities.sort(key=lambda x: x['start'])
        
        return resolved_entities

    def _resolve_overlaps(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not entities:
            return []
            
        entities.sort(key=lambda x: (x['start'], -x['end']))
        
        resolved = []
        current = entities[0]
        
        for next_entity in entities[1:]:
            if next_entity['start'] < current['end']:
                current_len = current['end'] - current['start']
                next_len = next_entity['end'] - next_entity['start']
                
                if next_len > current_len:
                    if current['entity_type'] == 'URL':
                        pass # Protect regex URLs from being swallowed by longer GLiNER matches
                    else:
                        current = next_entity
            else:
                resolved.append(current)
                current = next_entity
                
        resolved.append(current)
        return resolved

    def _is_valid_entity(self, entity_type: str, text: str) -> bool:
        """Applies safety guardrails to prevent over-redaction."""
        # Whitelist specific phrases just in case they slipped through
        if "India (\"SEBI\")" in text or "SEBI guarantee the accuracy" in text:
            return False
            
        lower_text = text.lower()
        ignore_phrases = [
            "our company", "the company", "our statutory auditors", 
            "statutory auditors", "our promoters", "the offer",
            "bidders", "bidder", "anchor investor", "anchor investors", 
            "retail individual investor", "retail individual investors", 
            "qibs", "niis", "riis", "promoters", "promoter group"
        ]
        if any(phrase in lower_text for phrase in ignore_phrases):
            return False
            
        # Max Length Guard (discard if > 80 chars or > 10 words, unless it's an Address)
        if entity_type != "ADDRESS":
            if len(text) > 80 or len(text.split()) > 10:
                return False
                
        # Sentence Boundary Guard
        if re.search(r'[.!?]\s+[A-Z]', text):
            return False
        
        # Punctuation guards
        if '"' in text:
            return False
        if '(' in text or ')' in text:
            if len(text.split()) > 5:
                return False
                
        return True

    def _split_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Splits concatenated entities (e.g., 'NAME1, NAME2 AND NAME3') into individual entities."""
        split_results = []
        for entity in entities:
            e_text = entity['text']
            e_type = entity['entity_type']
            e_start = entity['start']
            
            # Split NAME entities if they contain commas, AND, &, or \n
            if e_type == "NAME" and re.search(r',|\b(?:and|AND)\b|&|\n', e_text):
                # Strictly split by delimiters
                parts = re.split(r',|\b(?:and|AND)\b|&|\n', e_text)
                
                current_search_idx = 0
                for part in parts:
                    sub_text = part.strip()
                    if len(sub_text) > 2 and re.search(r'[A-Za-z]', sub_text):
                        # Find exactly where this sub_text occurs after the current search index
                        sub_start = e_text.find(sub_text, current_search_idx)
                        if sub_start != -1:
                            split_results.append({
                                "entity_type": e_type,
                                "start": e_start + sub_start,
                                "end": e_start + sub_start + len(sub_text),
                                "text": sub_text
                            })
                            current_search_idx = sub_start + len(sub_text)
            else:
                split_results.append(entity)
        return split_results
