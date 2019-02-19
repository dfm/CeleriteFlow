# -*- coding: utf-8 -*-

from __future__ import division, print_function

import pytest
import numpy as np

import tensorflow as tf

import celeriteflow as cf
from celeriteflow import terms


def _get_tf_kernel(celerite_kernel):
    import celerite.terms as cterms  # NOQA

    if isinstance(celerite_kernel, cterms.TermSum):
        result = _get_tf_kernel(celerite_kernel.terms[0])
        for k in celerite_kernel.terms[1:]:
            result += _get_tf_kernel(k)
        return result
    elif isinstance(celerite_kernel, cterms.TermProduct):
        return (
            _get_tf_kernel(celerite_kernel.k1) *
            _get_tf_kernel(celerite_kernel.k2))
    elif isinstance(celerite_kernel, cterms.RealTerm):
        return terms.RealTerm(log_a=celerite_kernel.log_a,
                              log_c=celerite_kernel.log_c)
    elif isinstance(celerite_kernel, cterms.ComplexTerm):
        if not celerite_kernel.fit_b:
            return terms.ComplexTerm(log_a=celerite_kernel.log_a,
                                     b=0.0,
                                     log_c=celerite_kernel.log_c,
                                     log_d=celerite_kernel.log_d)
        return terms.ComplexTerm(log_a=celerite_kernel.log_a,
                                 log_b=celerite_kernel.log_b,
                                 log_c=celerite_kernel.log_c,
                                 log_d=celerite_kernel.log_d)
    elif isinstance(celerite_kernel, cterms.SHOTerm):
        return terms.SHOTerm(log_S0=celerite_kernel.log_S0,
                             log_Q=celerite_kernel.log_Q,
                             log_w0=celerite_kernel.log_omega0)
    elif isinstance(celerite_kernel, cterms.Matern32Term):
        return terms.Matern32Term(log_sigma=celerite_kernel.log_sigma,
                                  log_rho=celerite_kernel.log_rho)
    raise NotImplementedError()


@pytest.mark.parametrize(
    "celerite_kernel",
    [
        "cterms.RealTerm(log_a=0.1, log_c=0.5)",
        "cterms.RealTerm(log_a=0.1, log_c=0.5) + "
        "cterms.RealTerm(log_a=-0.1, log_c=0.7)",
        "cterms.ComplexTerm(log_a=0.1, log_c=0.5, log_d=0.1)",
        "cterms.ComplexTerm(log_a=0.1, log_b=-0.2, log_c=0.5, log_d=0.1)",
        "cterms.SHOTerm(log_S0=0.1, log_Q=-1, log_omega0=0.5)",
        "cterms.SHOTerm(log_S0=0.1, log_Q=1.0, log_omega0=0.5)",
        "cterms.SHOTerm(log_S0=0.1, log_Q=1.0, log_omega0=0.5) + "
        "cterms.RealTerm(log_a=0.1, log_c=0.4)",
        "cterms.SHOTerm(log_S0=0.1, log_Q=1.0, log_omega0=0.5) * "
        "cterms.RealTerm(log_a=0.1, log_c=0.4)",
        "cterms.Matern32Term(log_sigma=0.1, log_rho=0.4)",
    ]
)
def test_gp(celerite_kernel, seed=1234):
    import celerite
    import celerite.terms as cterms  # NOQA
    celerite_kernel = eval(celerite_kernel)
    np.random.seed(seed)
    x = np.sort(np.random.rand(100))
    yerr = np.random.uniform(0.1, 0.5, len(x))
    y = np.sin(x)
    diag = yerr**2

    celerite_gp = celerite.GP(celerite_kernel)
    celerite_gp.compute(x, yerr)
    celerite_loglike = celerite_gp.log_likelihood(y)

    kernel = _get_tf_kernel(celerite_kernel)
    gp = cf.GaussianProcess(kernel, x, diag)
    loglike_t = gp.log_likelihood(y)

    with tf.Session() as sess:
        sess.run(tf.global_variables_initializer())
        loglike = sess.run(loglike_t)

    assert np.allclose(loglike, celerite_loglike)
