import json
from collections import defaultdict
from typing import List, Dict, Any
from src.detectors.hybrid_detector import HybridDetector

class Evaluator:
    """
    Evaluates the performance of the PII detection engine against a ground truth dataset.
    Calculates Precision, Recall, and F1-Score for each entity type.
    """
    
    def __init__(self, detector: HybridDetector):
        self.detector = detector
        
    def evaluate_from_file(self, ground_truth_path: str):
        """
        Loads ground truth from a JSON file and runs evaluation.
        Expected JSON format:
        [
            {
                "text": "Paragraph text containing PII",
                "entities": [
                    {"entity_type": "NAME", "start": 0, "end": 8, "text": "John Doe"}
                ]
            }
        ]
        """
        with open(ground_truth_path, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
            
        return self.evaluate(dataset)

    def evaluate(self, dataset: List[Dict[str, Any]]):
        """
        Runs evaluation on a list of ground truth examples.
        """
        # Data structure to hold counts per entity type
        # format: { "NAME": {"tp": 0, "fp": 0, "fn": 0}, ... }
        metrics = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
        
        for item in dataset:
            text = item.get("text", "")
            gt_entities = item.get("entities", [])
            
            # Run detection
            pred_entities = self.detector.analyze(text)
            
            # To easily match, let's create a set of tuples: (entity_type, start, end)
            gt_set = {(e["entity_type"], e["start"], e["end"]) for e in gt_entities}
            pred_set = {(e["entity_type"], e["start"], e["end"]) for e in pred_entities}
            
            # Calculate True Positives (TP) and False Positives (FP)
            for pred in pred_set:
                e_type = pred[0]
                if pred in gt_set:
                    metrics[e_type]["tp"] += 1
                else:
                    metrics[e_type]["fp"] += 1
                    
            # Calculate False Negatives (FN)
            for gt in gt_set:
                e_type = gt[0]
                if gt not in pred_set:
                    metrics[e_type]["fn"] += 1
                    
        # Calculate Precision, Recall, F1 for each type
        results = {}
        for e_type, counts in metrics.items():
            tp = counts["tp"]
            fp = counts["fp"]
            fn = counts["fn"]
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            
            results[e_type] = {
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1, 4),
                "support": tp + fn # Total true instances
            }
            
        self._print_report(results)
        return results

    def _print_report(self, results: Dict[str, Dict[str, float]]):
        """
        Prints a formatted classification report.
        """
        print(f"{'Entity Type':<15} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'Support':<10}")
        print("-" * 65)
        
        for e_type, mets in sorted(results.items()):
            print(f"{e_type:<15} | {mets['precision']:<10.4f} | {mets['recall']:<10.4f} | {mets['f1_score']:<10.4f} | {mets['support']:<10}")
            
        print("-" * 65)
