import os

from hypothesis import settings

# `HYPOTHESIS_PROFILE=ci` makes property tests derandomized (reproducible across runs).
settings.register_profile("ci", derandomize=True, deadline=None, print_blob=True)
settings.register_profile("dev", deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))
