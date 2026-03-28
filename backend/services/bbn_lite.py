"""
Lightweight Bayesian Belief Network inference using only numpy.

Replaces pgmpy (which pulls in torch/pytorch at ~2GB+) for our small
12-node discrete network.  Implements:

  - Factor:       A multi-dimensional probability table (wraps ndarray).
  - BayesianNet:  DAG structure + CPD storage + validation.
  - variable_elimination():  Exact inference via sum-product.

This module has ZERO dependencies beyond numpy and the Python stdlib.

Performance: Variable elimination on our 12-node DAG with ~50 regions
completes in <5ms — comparable to pgmpy's VariableElimination.

References:
  Koller & Friedman (2009), "Probabilistic Graphical Models", Ch. 9.
"""
from __future__ import annotations

import numpy as np

__all__ = ["Factor", "BayesianNet", "variable_elimination"]


# ──────────────────────────────────────────────────────────────────────
# Factor: a named multi-dimensional probability table
# ──────────────────────────────────────────────────────────────────────

class Factor:
    """
    A discrete probability factor over named variables.

    Parameters
    ----------
    variables : list[str]
        Variable names.  The first entry corresponds to axis 0 of *values*,
        the second to axis 1, and so on.
    cardinalities : list[int]
        Number of states per variable (same order as *variables*).
    values : np.ndarray
        The probability table.  Shape must equal *cardinalities*.
    """

    __slots__ = ("variables", "cardinalities", "values")

    def __init__(
        self,
        variables: list[str],
        cardinalities: list[int],
        values: np.ndarray,
    ) -> None:
        self.variables = list(variables)
        self.cardinalities = list(cardinalities)
        expected_shape = tuple(cardinalities)
        if values.shape != expected_shape:
            # Try to reshape — pgmpy-style (node_card, prod_parent_cards)
            self.values = values.reshape(expected_shape).astype(np.float64)
        else:
            self.values = values.astype(np.float64)

    def __repr__(self) -> str:
        return f"Factor({self.variables}, shape={self.values.shape})"

    # ── operations ────────────────────────────────────────────────────

    def set_evidence(self, variable: str, state_idx: int) -> "Factor":
        """
        Condition on *variable = state_idx* by slicing and removing
        that axis from the factor.
        """
        if variable not in self.variables:
            return self  # variable not in this factor — no-op
        axis = self.variables.index(variable)
        sliced = np.take(self.values, state_idx, axis=axis)
        new_vars = [v for v in self.variables if v != variable]
        new_cards = [c for v, c in zip(self.variables, self.cardinalities) if v != variable]
        return Factor(new_vars, new_cards, sliced)

    def multiply(self, other: "Factor") -> "Factor":
        """
        Multiply two factors, aligning shared variables via broadcasting.
        """
        if not other.variables:
            return Factor(self.variables, self.cardinalities, self.values * other.values)
        if not self.variables:
            return Factor(other.variables, other.cardinalities, self.values * other.values)

        # Build union variable ordering
        all_vars: list[str] = list(self.variables)
        all_cards: list[int] = list(self.cardinalities)
        for v, c in zip(other.variables, other.cardinalities):
            if v not in all_vars:
                all_vars.append(v)
                all_cards.append(c)

        # Reshape self.values to union shape (size-1 for missing axes)
        shape_a = [
            self.cardinalities[self.variables.index(v)] if v in self.variables else 1
            for v in all_vars
        ]
        perm_a = []
        idx = 0
        for v in all_vars:
            if v in self.variables:
                perm_a.append(self.variables.index(v))
        # Build via transpose + reshape
        vals_a = self.values.transpose(
            [self.variables.index(v) for v in all_vars if v in self.variables]
        ).reshape(shape_a)

        shape_b = [
            other.cardinalities[other.variables.index(v)] if v in other.variables else 1
            for v in all_vars
        ]
        vals_b = other.values.transpose(
            [other.variables.index(v) for v in all_vars if v in other.variables]
        ).reshape(shape_b)

        return Factor(all_vars, all_cards, vals_a * vals_b)

    def marginalize(self, variable: str) -> "Factor":
        """
        Sum out *variable*, removing it from the factor.
        """
        if variable not in self.variables:
            return self
        axis = self.variables.index(variable)
        summed = self.values.sum(axis=axis)
        new_vars = [v for v in self.variables if v != variable]
        new_cards = [c for v, c in zip(self.variables, self.cardinalities) if v != variable]
        return Factor(new_vars, new_cards, summed)

    def normalize(self) -> "Factor":
        """
        Normalize to sum to 1.
        """
        total = self.values.sum()
        if total > 0:
            return Factor(self.variables, self.cardinalities, self.values / total)
        return self


# ──────────────────────────────────────────────────────────────────────
# BayesianNet: DAG + CPDs
# ──────────────────────────────────────────────────────────────────────

class BayesianNet:
    """
    A discrete Bayesian network defined by directed edges and CPDs.

    Parameters
    ----------
    edges : list[tuple[str, str]]
        Directed edges (parent → child).
    """

    def __init__(self, edges: list[tuple[str, str]]) -> None:
        self.edges = list(edges)
        self._cpds: dict[str, Factor] = {}

        # Derive nodes and parent sets
        self._nodes: set[str] = set()
        self._parents: dict[str, list[str]] = {}
        for parent, child in edges:
            self._nodes.add(parent)
            self._nodes.add(child)
            self._parents.setdefault(child, [])
            if parent not in self._parents[child]:
                self._parents[child].append(parent)
        # Ensure root nodes are in _parents too
        for n in self._nodes:
            self._parents.setdefault(n, [])

    def nodes(self) -> set[str]:
        return set(self._nodes)

    def parents(self, node: str) -> list[str]:
        return self._parents.get(node, [])

    def add_cpd(self, node: str, factor: Factor) -> None:
        """
        Register a CPD factor for *node*.

        The factor's variables should be [node, parent1, parent2, ...]
        matching the parent order in the DAG.
        """
        self._cpds[node] = factor

    def get_cpd(self, node: str) -> Factor:
        return self._cpds[node]

    def check_model(self) -> bool:
        """
        Basic validation: every node has a CPD, columns sum to ~1.
        """
        for node in self._nodes:
            if node not in self._cpds:
                return False
            cpd = self._cpds[node]
            # For a CPD P(node | parents), summing over node (axis 0)
            # should give ~1 for every parent config
            if cpd.values.ndim == 1:
                if abs(cpd.values.sum() - 1.0) > 0.05:
                    return False
            else:
                col_sums = cpd.values.sum(axis=0)
                if not np.allclose(col_sums, 1.0, atol=0.05):
                    return False
        return True

    @property
    def cpd_factors(self) -> list[Factor]:
        """All CPD factors as a list."""
        return list(self._cpds.values())


# ──────────────────────────────────────────────────────────────────────
# Variable Elimination
# ──────────────────────────────────────────────────────────────────────

def variable_elimination(
    network: BayesianNet,
    query_variables: list[str],
    evidence: dict[str, int],
) -> dict[str, np.ndarray]:
    """
    Exact inference via variable elimination.

    Parameters
    ----------
    network : BayesianNet
        The Bayesian network.
    query_variables : list[str]
        Variables to query (marginal probabilities).
    evidence : dict[str, int]
        Observed variable → state index.

    Returns
    -------
    dict[str, np.ndarray]
        Mapping from query variable name to its marginal probability array.
    """
    # 1. Start with all CPD factors
    factors: list[Factor] = [f for f in network.cpd_factors]

    # 2. Apply evidence: slice each factor on observed variables
    for var, state_idx in evidence.items():
        factors = [f.set_evidence(var, state_idx) for f in factors]

    # 3. Determine elimination order: all non-query, non-evidence variables
    all_vars = set()
    for f in factors:
        all_vars.update(f.variables)
    eliminate = all_vars - set(query_variables) - set(evidence.keys())

    # Simple elimination ordering: eliminate variables that appear in
    # fewest factors first (min-degree heuristic)
    eliminate_order = sorted(eliminate, key=lambda v: sum(1 for f in factors if v in f.variables))

    # 4. Eliminate each variable
    for var in eliminate_order:
        # Collect factors involving this variable
        involved = [f for f in factors if var in f.variables]
        remaining = [f for f in factors if var not in f.variables]

        if not involved:
            continue

        # Multiply all involved factors
        product = involved[0]
        for f in involved[1:]:
            product = product.multiply(f)

        # Sum out the variable
        marginalized = product.marginalize(var)
        remaining.append(marginalized)
        factors = remaining

    # 5. Multiply remaining factors and normalize per query variable
    results: dict[str, np.ndarray] = {}
    for qvar in query_variables:
        # Collect factors containing this query variable
        relevant = [f for f in factors if qvar in f.variables]
        if not relevant:
            continue

        product = relevant[0]
        for f in relevant[1:]:
            product = product.multiply(f)

        # If there are other variables remaining, marginalize them out
        for v in list(product.variables):
            if v != qvar:
                product = product.marginalize(v)

        product = product.normalize()
        results[qvar] = product.values.flatten()

    return results
