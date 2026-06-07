from pydantic import BaseModel

class EpistemicAnswer(BaseModel):
    claim: str
    source: str
    uncertainty: float  # 0 = certain, 1 = guess
    falsifiable_test: str

    def explain(self):
        return f"{self.claim} (uncertainty {self.uncertainty:.2f}). Test: {self.falsifiable_test}"
