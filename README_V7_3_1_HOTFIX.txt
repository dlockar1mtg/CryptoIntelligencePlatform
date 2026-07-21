Crypto Intelligence Platform v7.3.1
scikit-learn Compatibility & Stabilization Hotfix
=================================================

Cause
-----

Module 28 used:

    LogisticRegression(multi_class="auto")

The installed scikit-learn 1.9.0 API no longer accepts the multi_class
argument, causing Module 28 to fail before feature selection began.

Correction
----------

v7.3.1:

- Backs up crypto_platform/module28.py.
- Removes the obsolete multi_class argument in place.
- Scans Module 28 for other removed sklearn constructor arguments.
- Compiles the patched Module 28 file.
- Runs a synthetic multiclass LogisticRegression fit.
- Imports Module 28 and verifies its schema.
- Updates platform version metadata to 7.3.1.

No database migration is required. Existing v7.3 tables, configuration,
backups, and failed run history are preserved.

Installation
------------

Extract directly into:

C:\Users\DevonLockard\Crypto

Then run:

    apply_v7_3_1_compatibility_hotfix.bat

After it succeeds:

    python run_module28.py
    python inspect_module28.py
