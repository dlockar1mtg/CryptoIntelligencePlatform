from __future__ import annotations
import hashlib, json
import numpy as np
from .parameter_space import ParameterSpace

class CandidateGenerator:
    def __init__(self, space: ParameterSpace, seed: int):
        self.space = space
        self.seed = int(seed)
        self.rng = np.random.default_rng(self.seed)

    @staticmethod
    def parameter_hash(parameters: dict) -> str:
        payload = json.dumps(parameters, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def generate(self, count: int) -> list[dict]:
        candidates=[]; seen=set()
        attempts=0
        while len(candidates) < int(count):
            attempts += 1
            if attempts > int(count) * 100:
                raise RuntimeError("Unable to generate enough unique candidates")
            parameters = self.space.sample(self.rng)
            parameters = {k: round(float(v), 8) for k,v in parameters.items()}
            # Restore the tiny rounding residual to the largest scoring weight.
            weight_keys = [
                "trend_weight", "momentum_weight", "value_weight",
                "risk_adjusted_weight", "relative_strength_weight",
                "liquidity_weight", "derivatives_weight",
            ]
            residual = 1.0 - sum(parameters[key] for key in weight_keys)
            largest = max(weight_keys, key=lambda key: parameters[key])
            parameters[largest] = round(parameters[largest] + residual, 8)
            self.space.validate(parameters)
            digest = self.parameter_hash(parameters)
            if digest in seen: continue
            seen.add(digest)
            candidates.append({
                "candidate_id": f"C{len(candidates)+1:05d}",
                "parameter_hash": digest,
                "parameters": parameters,
                "generation_seed": self.seed,
            })
        return candidates
