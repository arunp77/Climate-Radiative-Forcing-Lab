import pytest
from radforce.data import ar6_concentrations, ar6_erf


@pytest.fixture(scope="session")
def conc():
    return ar6_concentrations()


@pytest.fixture(scope="session")
def erf_best():
    return ar6_erf("best")
