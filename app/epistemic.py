from pydantic import BaseModel

class EpistemicAnswer(BaseModel):
    claim: str
    source: str
    uncertainty: float  # 0 = certain, 1 = guess
    falsifiable_test: str

    def explain(self):
        level = "certain" if self.uncertainty < 0.2 else "likely" if self.uncertainty < 0.5 else "guess"
        return f"{self.claim} ({level}, uncertainty {self.uncertainty:.2f}). Test: {self.falsifiable_test}"
    
    def to_dict(self):
        return {
            "claim": self.claim,
            "source": self.source,
            "uncertainty": self.uncertainty,
            "falsifiable_test": self.falsifiable_test,
            "confidence": 1 - self.uncertainty
        }