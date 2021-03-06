import numpy as np
import glotaran as gta

sim_model = gta.KineticModel.from_dict({
    'initial_concentration': {
        'j1': {
            'compartments': ['s1', 's2', 's3'],
            'parameters': ['j.1', 'j.0', 'j.0'],
        },
    },
    'k_matrix': {
        "k1": {'matrix': {
            ("s2", "s1"): 'kinetic.1',
            ("s3", "s2"): 'kinetic.2',
            ("s3", "s3"): 'kinetic.3',
        }}
    },

    'megacomplex': {
        'm1': {
           'k_matrix': ['k1'],
        }
    },
    'shape': {
        'sh1': {
            'type': "gaussian",
            'amplitude': "shape.amps.1",
            'location': "shape.locs.1",
            'width': "shape.width.1",
        },
        'sh2': {
            'type': "gaussian",
            'amplitude': "shape.amps.2",
            'location': "shape.locs.2",
            'width': "shape.width.2",
        },
        'sh3': {
            'type': "gaussian",
            'amplitude': "shape.amps.3",
            'location': "shape.locs.3",
            'width': "shape.width.3",
        },
    },
    'irf': {
        'irf1': {'type': 'gaussian', 'center': ['irf.center'], 'width': ['irf.width']},
    },
    'dataset': {
        'dataset1': {
            'initial_concentration': 'j1',
            'megacomplex': ['m1'],
            'shape': {
                's1': 'sh1',
                's2': 'sh2',
                's3': 'sh3',
            },
            'irf': 'irf1',
        }
    }
    })

wanted_parameter = gta.ParameterGroup.from_dict({
    'j': [
            ['1', 1, {'non-negative': False, 'vary': False}],
            ['0', 0, {'non-negative': False, 'vary': False}],
        ],
    'kinetic': [
        ["1", 0.5],
        ["2", 0.3],
        ["3", 0.1],
    ],
    'osc': [
        ['freq', 25],
        ['rate', 1],
    ],
    'shape': {'amps': [30, 20, 40], 'locs': [620, 630, 650], 'width': [40, 20, 60]},
    'irf': [['center', 0.3], ['width', 0.1]],
    })

parameter = gta.ParameterGroup.from_dict({
    'j': [
            ['1', 1, {'vary': False, 'non-negative': False}],
            ['0', 0, {'vary': False, 'non-negative': False}],
        ],
    'kinetic': [
        ["1", 0.5],
        ["2", 0.3],
        ["3", 0.1],
    ],
    'irf': [['center', 0.3], ['width', 0.1]],
    })

_time = np.arange(-1, 20, 0.01)
_spectral = np.arange(600, 700, 1.4)

dataset = sim_model.simulate('dataset1', wanted_parameter,
                             {'time': _time, 'spectral': _spectral},
                             noise=True, noise_std_dev=1e-2)

model = gta.KineticModel.from_dict({
    'initial_concentration': {
        'j1': {
                'compartments': ['s1', 's2', 's3'],
                'parameters': ['j.1', 'j.0', 'j.0']
              },
    },
    'k_matrix': {
        "k1": {'matrix': {
            ("s2", "s1"): 'kinetic.1',
            ("s3", "s2"): 'kinetic.2',
            ("s3", "s3"): 'kinetic.3',
        }}
    },

    'megacomplex': {
        'm1': {
           'k_matrix': ['k1'],
        }
    },
    'irf': {
        'irf1': {'type': 'gaussian', 'center': 'irf.center', 'width': 'irf.width'},
    },
    'dataset': {
        'dataset1': {
            'initial_concentration': 'j1',
            'megacomplex': ['m1'],
            'irf': 'irf1',
        }
    }
})
