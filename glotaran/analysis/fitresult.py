"""This package contains the FitResult object"""

import multiprocessing
import numpy as np
from lmfit.minimizer import Minimizer


from glotaran.model.dataset import Dataset
from glotaran.model.parameter_group import ParameterGroup


from .grouping import create_group, create_data_group
from .grouping import calculate_group_item
from .variable_projection import clp_variable_projection, residual_variable_projection


class FitResult:
    """The result of a fit."""

    def __init__(self,
                 model,
                 data,
                 initital_parameter,
                 nnls,
                 atol=0,
                 ):
        """

        Parameters
        ----------
        lm_result: MinimizerResult
        dataset_results: Dict[str, DatasetResult]

        Returns
        -------
        """
        self.model = model
        self.data = data
        self.initial_parameter = initital_parameter
        self.nnls = nnls
        self._group = create_group(model, data, atol)
        self._data_group = create_data_group(model, self._group, data)
        self._lm_result = None
        self._clp = {}
        self._original_clp = {}
        self._clp_labels = {}
        self._concentrations = {}
        self._residuals = {}
        self._pool = None

    def minimize(self, verbose: int = 2, max_nfev: int = None, nr_worker: int = 1):
        parameter = self.initial_parameter.as_parameter_dict(only_fit=True)
        self._old = parameter
        minimizer = Minimizer(
            self._flat_residual,
            parameter,
            fcn_args=[],
            fcn_kws=None,
            iter_cb=self._iter_cb,
            scale_covar=True,
            nan_policy='omit',
            reduce_fcn=None,
            **{})

        multicore = nr_worker > 1

        if multicore:
            nr_worker = min(nr_worker, multiprocessing.cpu_count())
            self._init_worker_pool(nr_worker)

        self._lm_result = minimizer.minimize(method='least_squares',
                                             verbose=verbose,
                                             max_nfev=max_nfev)

        if multicore:
            self._close_worker_pool()

        if not self.nnls and self._clp is None:
            self._clp = clp_variable_projection(self.best_fit_parameter,
                                                self._group, self.model,
                                                self.data, self._data_group)

    @property
    def best_fit_parameter(self) -> ParameterGroup:
        """The best fit parameters."""
        return ParameterGroup.from_parameter_dict(self._lm_result.params)

    def get_concentrations(self, dataset):

        indices = self._get_group_indices(dataset)

        clp_labels = []
        for idx in indices:
            for label in self._original_clp[idx][self._get_dataset_idx(idx, dataset)]:
                if label not in clp_labels:
                    clp_labels.append(label)

        dim1 = self.data[dataset].get_axis(self.model.estimated_axis).size
        dim2 = len(clp_labels)
        dim3 = self.data[dataset].get_axis(self.model.calculated_axis).size

        concentrations = np.empty((dim1, dim2, dim3), dtype=np.float64)

        for i, index in enumerate(indices):
            dataset_idx = self._get_dataset_idx(index, dataset)
            concentration = self._concentrations[index][dataset_idx]
            labels = self._clp_labels[index]
            idx = [labels.index(label) for label in clp_labels]
            concentrations[i, :, :] = concentration[idx, :]

        return clp_labels, concentrations

    def get_clp(self, dataset):

        indices = self._get_group_indices(dataset)

        clp_labels = []
        for idx in indices:
            for label in self._original_clp[idx][self._get_dataset_idx(idx, dataset)]:
                if label not in clp_labels:
                    clp_labels.append(label)

        dim1 = len(self._clp)
        dim2 = len(clp_labels)

        clp = np.empty((dim1, dim2), dtype=np.float64)

        for i, index in enumerate(indices):
            idx = [self._clp_labels[index].index(label) for label in clp_labels]
            clp[i, :] = self._clp[index][idx]
        return clp_labels, clp

    def get_fitted_dataset(self, label: str):
        """get_dataset returns the DatasetResult for the given dataset.

        Parameters
        ----------
        label : str
            The label of the dataset.

        Returns
        -------
        dataset_result: DatasetResult
        print(a_matrix)
            The result for the dataset.
        """
        dataset = self.data[label]

        calculated_axis = dataset.get_axis(self.model.calculated_axis)
        estimated_axis = dataset.get_axis(self.model.estimated_axis)

        result = np.zeros((estimated_axis.size, calculated_axis.size), dtype=np.float64)

        indices = self._get_group_indices(label)
        for i, index in enumerate(indices):

            dataset_idx = self._get_dataset_idx(index, label)

            result[i, :] = np.dot(self._clp[index],
                                  self._concentrations[index][dataset_idx])

        dataset = Dataset()
        dataset.set_axis(self.model.calculated_axis, calculated_axis)
        dataset.set_axis(self.model.estimated_axis, estimated_axis)
        dataset.set_data(result)
        return dataset

    def _get_group_indices(self, dataset_label):
        return [index for index, item in self._group.items()
                if dataset_label in [val[1].label for val in item]]

    def _get_dataset_idx(self, index, dataset):
            datasets = [val[1].label for val in self._group[index]]
            return datasets.index(dataset)

    def _iter_cb(self, params, i, resid, *args, **kws):
        pass

    def final_residual(self, dataset):
        indices = self._get_group_indices(dataset)

        dim1 = len(indices)
        dim2 = self.data[dataset].get_axis(self.model.calculated_axis).size

        residual = np.zeros((dim1, dim2), dtype=np.float64)

        for i, index in enumerate(indices):
            residual[i, :] = self._residuals[index][self._get_dataset_idx(index, dataset)]

        return residual

    def final_residual_svd(self, dataset):
        lsv, svals, rsv = np.linalg.svd(self.final_residual(dataset).T)
        return lsv, svals, rsv.T

    def _calculate_residual(self, parameter):
        residuals = None
        if self._pool is None:

            residuals = []
            for index, item in self._group.items():
                self._concentrations[index], self._clp_labels[index], self._original_clp[index] = \
                    calculate_group_item(item, self.model, parameter, self.data)
                concentration = np.concatenate(self._concentrations[index],
                                               axis=1).T
                self._clp[index], self._residuals[index] = \
                    residual_variable_projection(
                        concentration,
                        self._data_group[index]
                    )
                residuals.append(self._residuals[index])
        else:
            jobs = [(i, parameter) for i, _ in enumerate(self._group)]
            residuals = self._pool.map(worker_fun, jobs)

        return np.asarray(residuals)

    def _flat_residual(self, parameter):
        parameter = ParameterGroup.from_parameter_dict(parameter)
        return np.concatenate(self._calculate_residual(parameter))

    def _init_worker_pool(self, nr_worker):

        def init_worker(items, model, data, data_group):
            global worker_items, worker_model, worker_data, worker_data_group
            worker_items = items
            worker_model = model
            worker_data = data
            worker_data_group = data_group

        self._pool = multiprocessing.Pool(nr_worker,
                                          initializer=init_worker,
                                          initargs=(list(self._group.values()),
                                                    self.model,
                                                    self.data,
                                                    self._data_group))

    def _close_worker_pool(self):
        self._pool.close()
        self._pool = None

    def __str__(self):
        string = "# Fitresult\n\n"

        # pylint: disable=invalid-name

        ll = 32
        lr = 13

        string += "Optimization Result".ljust(ll-1)
        string += "|"
        string += "|".rjust(lr)
        string += "\n"
        string += "|".rjust(ll, "-")
        string += "|".rjust(lr, "-")
        string += "\n"

        string += "Number of residual evaluation |".rjust(ll)
        string += f"{self._lm_result.nfev} |".rjust(lr)
        string += "\n"
        string += "Number of variables |".rjust(ll)
        string += f"{self._lm_result.nvarys} |".rjust(lr)
        string += "\n"
        string += "Number of datapoints |".rjust(ll)
        string += f"{self._lm_result.ndata} |".rjust(lr)
        string += "\n"
        string += "Negrees of freedom |".rjust(ll)
        string += f"{self._lm_result.nfree} |".rjust(lr)
        string += "\n"
        string += "Chi Square |".rjust(ll)
        string += f"{self._lm_result.chisqr:.6f} |".rjust(lr)
        string += "\n"
        string += "Reduced Chi Square |".rjust(ll)
        string += f"{self._lm_result.redchi:.6f} |".rjust(lr)
        string += "\n"

        string += "\n"
        string += "## Best Fit Parameter\n\n"
        string += f"{self.best_fit_parameter}"
        string += "\n"

        return string


def worker_fun(job):
    (i, parameter) = job
    return residual_variable_projection(
        calculate_group_item(worker_items[i], worker_model, parameter, worker_data)[0],
        worker_data_group[i])
