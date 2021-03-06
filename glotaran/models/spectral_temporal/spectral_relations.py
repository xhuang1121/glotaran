""" Glotaran Spectral Relation """

import typing

from glotaran.model import model_attribute
from glotaran.parameter import Parameter


@model_attribute(
    properties={
        'compartment': str,
        'target': str,
        'parameter': Parameter,
        'interval': typing.List[typing.Tuple[float, float]],
    }, no_label=True)
class SpectralRelation:
    def applies(self, index: any) -> bool:
        """
        Returns true if the index is in one of the intervals.

        Parameters
        ----------
        index : any

        Returns
        -------
        applies : bool

        """
        return any(interval[0] <= index <= interval[1] for interval in self.interval)
